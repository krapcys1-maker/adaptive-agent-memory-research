"""Tests for lifesim.gates (LifeSim D1-E): every gate must FIRE on its planted artefact and PASS on a clean input.

No model, no network, no clock. The statistical gates run on a few real L1 worlds (dev seeds 5-8); where the
current generator is known to fail a gate (G-TELL, G-FEAS with the novelty baselines) the test pins the finding
without asserting the failure, so that fixing the generator does not break it.
"""

from __future__ import annotations

import dataclasses
import functools
import itertools
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import channel as C  # noqa: E402
from corpus.lifesim import queries as Q  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import world as W  # noqa: E402
from lifesim import gates as G  # noqa: E402
from lifesim import interface as I  # noqa: E402
from lifesim import systems as SY  # noqa: E402

CFG0 = S.TierCfg.for_tier("L0")
CFG1 = S.TierCfg.for_tier("L1")
SEEDS1 = (5, 6, 7, 8)


@functools.lru_cache(maxsize=None)
def bundle(tier: str, seed: int, cell: str = "C0", affect: str = "A0") -> G.Bundle:
    cfg = S.TierCfg.for_tier(tier)
    if affect != "A0":
        cfg = dataclasses.replace(cfg, affect=affect, r_aff=0.6 if affect == "A2" else 0.0)
    return G.make_bundle(seed, cfg, cell)


def l1(cell="C0", affect="A0"):
    return [bundle("L1", s, cell, affect) for s in SEEDS1]


def l0():
    return [bundle("L0", s) for s in (0, 1, 2)]


# ------------------------------------------------------------------------------ helpers


def test_auc_hand_values():
    assert G.auc([1, 2, 3], [0, 1, 2]) == pytest.approx(7 / 9)            # 1.5 + 2.5 + 3 over 9 pairs
    assert G.auc([5, 6], [1, 2]) == 1.0 and G.auc([1, 2], [5, 6]) == 0.0
    assert G.auc([1, 1, 1], [1, 1]) == 0.5
    assert G.auc([], [1]) == 0.5 and G.auc([1], []) == 0.5
    assert G.auc([0.2, 0.9], [0.5]) == 0.5                                   # one win, one loss


def test_wilson_upper_known_values():
    assert G.wilson_upper(0, 10) == pytest.approx(0.2775, abs=1e-3)
    assert G.wilson_upper(5, 10) == pytest.approx(0.7634, abs=1e-3)
    assert G.wilson_upper(10, 10) == 1.0 and G.wilson_upper(0, 0) == 1.0
    ups = [G.wilson_upper(k, 50) for k in range(0, 51)]
    assert ups == sorted(ups) and all(u >= k / 50 for k, u in enumerate(ups))


def test_gate_result_is_json_and_truthy_only_when_passed():
    r = G.GateResult("G-X", True, {"a": 1.5}, {"t": 2}, "d", 3)
    assert json.loads(json.dumps(r.to_dict()))["passed"] is True and bool(r)
    assert not G.GateResult("G-X", False) and not G.GateResult("G-X", None)


def test_make_bundle_aligns_lines_queries_and_parts():
    b = bundle("L0", 1)
    assert [o.oid for o in b.obs] == [s.oid for s in b.world.obs_specs] == [p.oid for p in b.parts]
    assert all(o.text == p.text for o, p in zip(b.obs, b.parts))
    assert b.report is not None and G.is_null_cell(b.cell) and not G.is_null_cell("C+")
    nb = G.naive_bundle(1, CFG0, leaks=("length",))
    assert nb.parts is None and [o.text for o in nb.obs] != [o.text for o in b.obs]


# ------------------------------------------------------------------- G-DET, G-INV, G-SOLVE


def test_g_det_passes_and_fires_on_a_nondeterministic_builder():
    r = G.g_det(0, CFG0)
    assert r.passed is True and r.values["distinct"] == 1
    counter = itertools.count()
    flaky = lambda seed, cfg: W.build_world(seed, cfg).with_extra("call", next(counter))  # noqa: E731
    bad = G.g_det(0, CFG0, build=flaky)
    assert bad.passed is False and bad.values["distinct"] == 2


def test_g_inv_passes_and_fires_on_a_pipeline_that_moves_the_structure():
    b = bundle("L0", 1)
    r = G.g_inv(b)
    assert r.passed is True, r.values
    sabotaged = lambda w, arm: w.with_extra("arm", arm)  # noqa: E731
    bad = G.g_inv(b, attach=sabotaged)
    assert bad.passed is False and "digest_moved_by_arm" in bad.values["problems"]


def test_g_solve_passes_and_fires_on_corrupted_gold():
    assert G.g_solve(l1()).passed is True
    b = bundle("L0", 1)
    qs = [dataclasses.replace(x, gold=dataclasses.replace(x.gold, value="zzz")) if i % 6 == 0 else x
          for i, x in enumerate(b.queries)]
    bad = G.g_solve([dataclasses.replace(b, queries=qs)])
    assert bad.passed is False and len(bad.values["mismatched"]) > 0


# --------------------------------------------------------------------------------- G-SCORE


def test_g_score_passes_and_fires_on_a_shuffled_label_scorer():
    r = G.g_score(l1())
    assert r.passed is True and r.values["structure_accuracy"] == 1.0 and r.values["scramble_above_chance"] == []
    b = bundle("L1", 5)
    bad = G.g_score([b], score=G.shuffled_label_scorer(b))
    assert bad.passed is False and bad.values["structure_accuracy"] < 0.8


def test_g_score_fires_when_the_scrambled_world_solver_works():
    b = bundle("L1", 5)
    r = G.g_score([b, b])                      # the 'other seed's log' is the very same log: the solver is right
    assert r.passed is False and r.values["scramble_above_chance"]
    assert r.values["structure_accuracy"] == 1.0


def test_g_score_adversarial_table_must_agree_exactly():
    b = bundle("L1", 5)
    q = next(x for x in b.queries if x.family == "EP1")
    table = [(q, q.gold.value, True), (q, q.gold.value + " CONF: 90", True), (q, "UNKNOWN", False),
             (q, "no idea", False)]
    assert G.g_score([b], adversarial=table).passed is True
    wrong = table + [(q, q.gold.value, False)]
    r = G.g_score([b], adversarial=wrong)
    assert r.passed is False and r.values["adversarial_agree"] is False


# ---------------------------------------------------------------------- G-HOST, G-SUPPORT


def test_g_host_passes_on_situation_first_hosting_and_fires_on_a_type_hosted_world():
    r = G.g_host(l1())
    assert r.passed is True and r.values["p"] >= 0.2
    planted = [dataclasses.replace(b, world=G.plant_type_hosted(b.world)) for b in l1()]
    bad = G.g_host(planted)
    assert bad.passed is False and bad.values["p"] < 1e-6
    # the marginal arousal distribution is untouched by the fixture
    b = l1()[0]
    assert sorted(s.A for s in b.world.situations) == sorted(s.A for s in planted[0].world.situations)


def test_g_support_thresholds_depend_on_the_cell():
    def with_short(short, demand=100):
        rep = Q.BuildReport()
        rep.pooled_shortfall, rep.pooled_demand = short, demand
        return dataclasses.replace(bundle("L0", 1), report=rep)

    assert G.g_support([with_short(2)], "C0").passed is True            # 2% is allowed at the null
    assert G.g_support([with_short(3)], "C0").passed is False
    assert G.g_support([with_short(5)], "C+").passed is True            # 5% elsewhere
    assert G.g_support([with_short(6)], "C+").passed is False
    assert G.g_support(l1()).passed is True
    assert G.g_support([dataclasses.replace(bundle("L0", 1), report=None)]).passed is None


# --------------------------------------------------------------------------------- G-ARO


def test_g_aro_null_cell_passes_and_fires_on_leaky_importance():
    r = G.g_aro(l1())
    assert r.passed is True, r.values
    assert 0.8 <= r.values["E_0.10"] <= 1.2 and 0.45 <= r.values["AUC_ev"] <= 0.55 and abs(r.values["d"]) <= 0.10
    leaky = [G.plant_leaky_bundle(b) for b in l1()]
    bad = G.g_aro(leaky)
    assert bad.passed is False and bad.values["AUC_ev"] > 0.7
    # the same statistics over the evidence LINES are reported, and sit below the null by design
    assert r.values["AUC_ev_lines"] < r.values["AUC_ev"]


def test_g_aro_checks_the_quarter_enrichment_too():
    def reshaped(b):                           # 10% at the top decile, 30% in the next 15%, 60% low: E_0.10 = 1
        srt = sorted(G.line_arousal(b.world))
        pat = [0.97] + [0.80] * 3 + [0.30] * 6
        i = 0
        out = []
        for x in b.queries:
            if x.family != "ME1":
                x = dataclasses.replace(x, tags=dataclasses.replace(x.tags, target_arousal=srt[int(pat[i % 10] * (len(srt) - 1))]))
                i += 1
            out.append(x)
        return dataclasses.replace(b, queries=out)

    bs = [reshaped(b) for b in l1()]
    r = G.g_aro(bs)
    assert 0.8 <= r.values["E_0.10"] <= 1.2 and abs(r.values["AUC_ev"] - 0.5) < 0.1
    assert r.values["E_0.25"] > 1.4 and r.passed is False


def test_g_aro_non_null_cells_are_checked_against_their_target():
    bs = l1()
    near = S.Cell("X", 1.1, 0.3, 0.3)
    assert G.g_aro(bs, near).passed is True                                    # realised 1.03 is within 15% of 1.1
    assert G.g_aro(bs, "C+").passed is False                                   # the null stream is not a 4.0 cell
    grid = {"C-": [bundle("L1", 5, "C-")], "C0": [bundle("L1", 5, "C0")],
            "C-half": [bundle("L1", 5, "C-half")], "C+": [bundle("L1", 5, "C+")]}
    assert G.g_aro_grid(grid).passed is True
    flipped = {"C-": grid["C+"], "C0": grid["C0"], "C+": grid["C-"]}
    assert G.g_aro_grid(flipped).passed is False


# ------------------------------------------------------------------- G-LEN, G-AFF, G-POS


def test_g_len_passes_and_fires_on_the_naive_renderer():
    r = G.g_len(l1())
    assert r.passed is True, r.values
    naive = [G.naive_bundle(s, CFG1, leaks=("length",)) for s in SEEDS1]
    bad = G.g_len(naive)
    assert bad.passed is False
    assert abs(bad.values["AUC_length"] - 0.5) >= 0.2 or abs(bad.values["corr_length_arousal"]) >= 0.3


def test_g_len_fires_on_the_arousal_correlation_alone():
    def lengthen_loud(b):                       # PLANTED: loud lines are longer, evidence status is untouched
        a = G.line_arousal(b.world)
        obs = [S.Obs(oid=o.oid, t_obs=o.t_obs, channel=o.channel, text=o.text + " pad" * int(round(25 * x)))
               for o, x in zip(b.obs, a)]
        return dataclasses.replace(b, obs=obs)

    r = G.g_len([lengthen_loud(b) for b in l1()])
    assert abs(r.values["corr_length_arousal"]) > 0.05 and 0.45 <= r.values["AUC_length"] <= 0.55
    assert r.passed is False


def test_g_aff_covers_a0_a1_and_the_naive_affect_leak():
    assert G.g_aff(l1()).passed is True and G.g_aff(l1()).values["affect_words"] == 0
    a1 = l1(affect="A1")
    r1 = G.g_aff(a1)
    assert r1.passed is True and r1.values["mode"] == "A1" and r1.values["affect_words"] > 0
    a2 = l1(affect="A2")
    assert G.g_aff(a2).passed is None                                          # correlated by design: not gated
    assert G.g_aff(a2, "A1").passed is False                                   # ... and it would fail an A1 claim
    naive = [G.naive_bundle(s, CFG1, leaks=("affect",)) for s in SEEDS1]
    bad = G.g_aff(naive)
    assert bad.passed is False and bad.values["affect_words"] > 0               # words under A0
    assert G.g_aff(naive, "A1").passed is False and abs(G.g_aff(naive, "A1").values["spearman_arousal_affect"]) >= 0.4


def test_g_pos_passes_on_balanced_labels_and_fires_on_a_position_leak():
    bs = l1()
    def balanced(b):                      # every 4th line inside each (clause, token) position cell
        cells = {}
        for o, bins in zip(b.obs, G.position_bins(b)):
            cells.setdefault(bins, []).append(o.oid)
        return {oid for lst in cells.values() for oid in lst[::4]}

    r = G.g_pos(bs, evidence_override=[balanced(b) for b in bs])
    assert r.passed is True, r.values
    parts = [G.plant_position_leak(b.parts, G.evidence_oids(b.queries)) for b in bs]
    bad = G.g_pos(bs, parts=parts)
    assert bad.passed is False and bad.values["p_clause"] < 1e-6
    # the real renderer: report the finding (a weak dependence of the core position on the number of slots)
    real = G.g_pos(bs)
    assert 0.0 <= real.values["p_clause"] <= 1.0 and 0.0 <= real.values["p_token"] <= 1.0


# ---------------------------------------------------------------------------------- G-TELL


def test_g_tell_passes_on_clean_labels_and_fires_on_a_length_leak():
    pytest.importorskip("scipy")
    bs = l1()
    clean = G.g_tell(bs, evidence_override=[{o.oid for o in b.obs[::5]} for b in bs], targets_to_test=("evidence",))
    assert clean.passed is True, clean.values
    assert clean.values["targets"]["evidence"]["auc"] <= 0.55
    naive = [G.naive_bundle(s, CFG1, leaks=("length",)) for s in SEEDS1]
    bad = G.g_tell(naive, targets_to_test=("evidence",))
    assert bad.passed is False and bad.values["targets"]["evidence"]["auc"] > 0.8


def test_g_tell_upper_bound_and_power_flag():
    pytest.importorskip("scipy")
    b = [bundle("L0", 1)]
    every5 = [{o.oid for o in b[0].obs[::5]}]
    kw = dict(evidence_override=every5, targets_to_test=("evidence",), enforce_power=False)
    ok = G.g_tell(b, **kw)
    assert ok.passed is True and ok.values["powered"] is False
    t = ok.values["targets"]["evidence"]
    assert t["auc"] <= 0.55 < t["upper95"] and t["upper95"] >= t["auc"]
    assert G.g_tell(b, upper_max=0.50, **kw).passed is False                  # the point is fine, the upper bound is not
    two = G.g_tell(l1()[:2], evidence_override=[{o.oid for o in x.obs[::5]} for x in l1()[:2]],
                   targets_to_test=("evidence",), enforce_power=False)
    assert two.values["powered"] is False                                     # >= 300 positives but < 3000 negatives


def test_g_tell_needs_power_and_reports_the_current_generator():
    pytest.importorskip("scipy")
    b = [bundle("L0", 1)]
    r = G.g_tell(b)
    assert r.passed in (None, False) and r.values["powered"] is False         # 30 days are too few lines
    real = G.g_tell(l1())
    ev = real.values["targets"]["evidence"]
    assert 0.5 <= ev["auc"] <= 1.0 and ev["positives"] >= 300 and ev["negatives"] >= 3000
    # FINDING (not asserted as a failure): at the time of writing evidence lines are identifiable from surface
    # features because only slot-bearing lines carry names, digits and colours (AUC about 0.93 at L1).


# --------------------------------------------------------------------------------- G-BLIND


def test_g_blind_passes_on_a_clean_subset_and_fires_on_a_habit_leak():
    r = G.g_blind(l1(), families=("EP1", "EP4", "IN1", "SE4"))
    assert r.passed is True, r.values
    guessable = [G.plant_guessable(b, "EP1") for b in l1()]
    bad = G.g_blind(guessable, families=("EP1", "EP4", "IN1", "SE4"))
    assert bad.passed is False and bad.values["families"]["EP1"]["B0a"] == 1.0
    full = G.g_blind(l1())
    assert 0.0 <= full.values["covered_share"] <= 1.0                          # IN4 sits at its constant-guess cap


# -------------------------------------------------------------- G-ORACLE, G-DEPTH, G-FEAS


def test_g_oracle_passes_and_fires_when_the_evidence_does_not_fit_or_the_gold_is_wrong():
    r = G.g_oracle(l1())
    assert r.passed is True and r.values["oracle_struct_accuracy"] == 1.0
    assert all(v == 1.0 for v in r.values["oracle_text_complete"].values())
    assert G.g_oracle(l1(), budget=15).passed is False                        # the evidence exceeds the budget
    b = bundle("L0", 1)
    qs = [dataclasses.replace(x, gold=dataclasses.replace(x.gold, value="zzz")) if i % 5 == 0 else x
          for i, x in enumerate(b.queries)]
    bad = G.g_oracle([dataclasses.replace(b, queries=qs)])
    assert bad.passed is False and bad.values["oracle_struct_accuracy"] < 1.0


def test_core_position_quartiles_by_hand():
    from types import SimpleNamespace

    def part(pre_words, total):
        return SimpleNamespace(pre=(" ".join(["w"] * pre_words) + ".",) if pre_words else (),
                               text=" ".join(["w"] * total))

    assert [G._core_position(part(k, 40)) for k in (0, 9, 10, 19, 20, 29, 30, 39)] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert G._core_position(part(0, 0)) == 0


def test_g_depth_counts_retained_items_per_family():
    counts = G.g_depth(l1(), min_items=1).values["counts"]
    edge = min(counts.values())
    assert G.g_depth(l1(), min_items=edge).passed is True                      # exactly the minimum is enough
    assert G.g_depth(l1(), min_items=edge + 1).passed is False
    assert G.g_depth(l1(), min_items=10).passed is True
    r = G.g_depth(l1())
    assert r.values["counts"]["EP1"] >= 40 and (r.passed is False) == ("SE5" in r.values["short"])
    one = G.g_depth([bundle("L0", 1)])
    assert one.passed is False and set(one.values["short"]) >= {"EP1"}


def test_g_feas_has_headroom_against_blind_retention_and_none_at_r_one():
    bs = l1()
    r = G.g_feas(bs, 0.25, competitors=("GU", "GR"))
    assert r.passed is True and r.values["H_cell"] >= 0.2, r.values
    full = G.g_feas(bs, 1.0, competitors=("GU", "GR"))
    assert full.passed is False and abs(full.values["H_cell"]) < 1e-9          # nothing is evicted: GO == GU
    # all five competitors: report what the text-novelty baselines do (GS and GN read the lexical tell of the
    # evidence lines, so the headroom shrinks; whether it falls below 0.20 is a property of the generator)
    every = G.g_feas(bs, 0.25)
    cc = every.values["complete_at_C"]
    assert cc["GO"] >= cc["GU"]
    assert every.values["best_competitor"] in ("GU", "GR", "GS", "GN", "GM")
    assert every.values["H_cell"] == pytest.approx(cc["GO"] - max(cc[p] for p in ("GU", "GR", "GS", "GN", "GM")), abs=2e-6)
    assert r.values["H_cell"] == pytest.approx(cc["GO"] - max(cc["GU"], cc["GR"]), abs=2e-6)


# ----------------------------------------------------------------------------------- G-LEAK


class Lookahead(SY.Recency):
    """PLANTED ARTEFACT: a store that ignores the time of the question."""

    name = "lookahead"

    def _ranked_records(self, question, asked_at):
        return list(reversed(self._recs.values()))


class Mutating(SY.Recency):
    """PLANTED ARTEFACT: every query forgets the oldest record (state leaks between queries)."""

    name = "mutating"

    def _query(self, question, asked_at, budget):
        ans = super()._query(question, asked_at, budget)
        if self._recs:
            self._remove(next(iter(self._recs)))
        return ans


class Memoized(SY.Recency):
    """PLANTED ARTEFACT: a new question forgets the oldest record, a repeated one does not (state leaks between
    different questions, so only the online replay can see it)."""

    name = "memoized"

    def _reset(self):
        super()._reset()
        self._last = None

    def _query(self, question, asked_at, budget):
        key = (question, asked_at)
        if key != self._last and self._recs:
            self._remove(next(iter(self._recs)))
        self._last = key
        return super()._query(question, asked_at, budget)


class Repeats(SY.Recency):
    """PLANTED ARTEFACT: asking the same question twice gives an empty context the second time."""

    name = "repeats"

    def _reset(self):
        super()._reset()
        self._asked = set()

    def _query(self, question, asked_at, budget):
        key = (question, asked_at)
        again = key in self._asked
        self._asked.add(key)
        return I.make_answer("", ()) if again else super()._query(question, asked_at, budget)


def test_g_leak_names_the_kind_of_state_leak():
    bs = [bundle("L0", 1)]
    a = G.g_leak(bs, systems={"memoized": lambda b: Memoized()}, check_channel=False)
    assert a.passed is False and set(a.values["problems"]) == {"snapshot_differs"}
    b = G.g_leak(bs, systems={"repeats": lambda b: Repeats()}, check_channel=False)
    assert b.passed is False and set(b.values["problems"]) == {"query_mutates"}


def test_g_leak_passes_on_the_real_systems_and_fires_on_the_planted_leaks():
    bs = [bundle("L0", 1), bundle("L0", 2)]
    r = G.g_leak(bs)
    assert r.passed is True, r.values
    look = G.g_leak(bs, systems={"lookahead": lambda b: Lookahead()}, check_channel=False)
    assert look.passed is False and "lookahead" in look.values["problems"]
    mut = G.g_leak(bs, systems={"mutating": lambda b: Mutating()}, check_channel=False)
    assert mut.passed is False and ({"snapshot_differs", "query_mutates"} & set(mut.values["problems"]))


def test_g_leak_fires_on_a_channel_that_encodes_the_later_need():
    b = bundle("L1", 5)
    need = G.evidence_oids(b.queries)
    honest = b.world.with_channel(C.make_channel(b.world, "TRUE", 0.7, None, 5))
    leaky = b.world.with_channel(C.make_channel(b.world, "LEAKY", 0.7, None, 5, need=need))
    ok = G.g_leak([dataclasses.replace(b, world=honest)], systems={"B2": lambda bb: SY.BM25()})
    bad = G.g_leak([dataclasses.replace(b, world=leaky)], systems={"B2": lambda bb: SY.BM25()})
    assert ok.passed is True and 0.45 <= ok.values["channel_auc"] <= 0.55
    assert bad.passed is False and bad.values["channel_auc"] > 0.7
    # a leaky-importance generator is caught at the channel as well
    lb = G.plant_leaky_bundle(b)
    assert G.g_leak([lb], systems={"B2": lambda bb: SY.BM25()}).passed is False


# ------------------------------------------------------------------------------------ all


def test_x0_gates_runs_every_gate_deterministically_on_fresh_builds():
    pytest.importorskip("scipy")

    def run():
        bs = [G.make_bundle(s, CFG0, "C0") for s in (0, 1, 2)]
        res = G.x0_gates(bs)
        assert tuple(res) == G.GATE_NAMES
        return json.dumps({k: v.to_dict() for k, v in res.items()}, sort_keys=True), res

    a, res = run()
    b, _ = run()
    assert a == b
    assert res["G-DET"].passed is True and res["G-INV"].passed is True and res["G-SOLVE"].passed is True
    assert res["G-SCORE"].passed is True and res["G-HOST"].passed is True and res["G-ORACLE"].passed is True
    assert res["G-LEAK"].passed is True and res["G-AFF"].passed is True
    assert res["G-TELL"].passed in (None, False)                              # L0 has too few lines to power it


def test_gates_do_not_modify_their_inputs():
    b = bundle("L0", 2)
    before = (b.world.digest(), tuple(o.text for o in b.obs), tuple(q.to_json() for q in b.queries))
    G.x0_gates([b], include=["G-SOLVE", "G-SCORE", "G-ORACLE", "G-LEAK", "G-HOST", "G-ARO", "G-LEN", "G-AFF",
                             "G-BLIND", "G-DEPTH", "G-SUPPORT", "G-FEAS", "G-INV"])
    after = (b.world.digest(), tuple(o.text for o in b.obs), tuple(q.to_json() for q in b.queries))
    assert before == after
