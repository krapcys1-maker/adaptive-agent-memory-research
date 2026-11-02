"""End-to-end test of the LifeSim D1 slice: world -> text -> queries -> exact scorers -> systems -> gates.

A real L0 world is built, rendered, queried, scored from the structure, run through the evidence-level
ladder and the gates, twice from scratch, and everything must be byte-identical. A mini X1 (the value of the
channel at the retention gate) checks that the whole chain responds to the coupling cell. No model, no network.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.lifesim import channel as C  # noqa: E402
from corpus.lifesim import queries as Q  # noqa: E402
from corpus.lifesim import schema as S  # noqa: E402
from corpus.lifesim import verbalise as V  # noqa: E402
from corpus.lifesim import world as W  # noqa: E402
from corpus.lifesim.scorers import Scorer  # noqa: E402
from lifesim import gates as G  # noqa: E402
from lifesim import interface as I  # noqa: E402
from lifesim import systems as SY  # noqa: E402


def sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def pipeline(seed: int, tier: str = "L0", cell: str = "C0"):
    """The whole slice for one seed; returns the artefacts and a dict of digests."""
    cfg = S.TierCfg.for_tier(tier)
    world = W.build_world(seed, cfg)
    assert W.check_world(world) == []
    part = cfg.resolved_partition(seed)
    obs = V.render(world, cfg, seed, part)
    queries = Q.build_queries(world, cfg, cell, render=V.render_question, partition=part)
    world = world.with_channel(C.make_channel(world, "TRUE", cfg.reliability_primary, None, seed))
    recs = I.records_from_world(world, obs)
    need = frozenset(o for q in queries for o in q.evidence_oids)
    scorer = Scorer(world)

    # structure answers score 1.000, abstention included, and the independent solver agrees with the generator
    for q, a in I.run_stream(SY.OracleStruct(world), recs, queries, cfg.context_words, card=world.card):
        r = scorer.score(q, a)
        assert r.correct and r.score == 1.0, (q.qid, q.family, q.gold.value, a.text, r.error_type)
        g = Q.gold_slow(world, q)
        assert (g.kind, g.value) == (q.gold.kind, q.gold.value), q.qid

    # the evidence-level ladder
    ladder = {}
    h_answers = hashlib.sha256()
    for name, make in SY.ladder_factories(world, need=need, seed=seed).items():
        pairs = I.run_stream(make(), recs, queries, cfg.context_words, card=world.card)
        rows = [I.evidence_metrics(q, a) for q, a in pairs]
        ladder[name] = I.summarise_evidence(rows)["macro"]
        ladder[name]["accuracy"] = sum(scorer.score(q, a).correct for q, a in pairs) / len(pairs)
        for q, a in pairs:
            h_answers.update(a.to_json().encode("utf-8"))

    # the gate grid at the retention gate (store S-LEX), R in {1, 0.25}, all policies
    grid = {}
    for R in (1.0, 0.25):
        for pol in S.GATE_POLICIES:
            if pol == "GL":
                continue
            mem = SY.GatedMemory(SY.BM25Time(cfg.start_date), pol, R, seed, need=need)
            rows = []
            pairs = I.run_stream(mem, recs, queries, cfg.context_words, card=world.card,
                                 on_query=lambda q, a, m: rows.append(I.evidence_metrics(q, a, m.stored_ids())))
            grid[(R, pol)] = I.summarise_evidence(rows, keys=("complete", "recall", "stored_complete"))["macro"]
            for q, a in pairs:
                h_answers.update(a.to_json().encode("utf-8"))

    bundle = G.Bundle(world=world, cfg=cfg, seed=seed, partition=part, obs=list(obs), queries=list(queries),
                      parts=V.render_all_parts(world, cfg, seed, part),
                      report=Q.build_queries_ex(world, cfg, cell, render=V.render_question, partition=part).report,
                      cell=S.CELLS[cell])
    gates = G.x0_gates([bundle], tell=False)
    digests = {
        "world": world.digest(), "text": sha(*[o.text for o in obs]),
        "queries": sha(*[q.to_json() for q in queries]), "channel": sha(world.channel.to_json()),
        "answers": h_answers.hexdigest(),
        "gates": sha(json.dumps({k: v.to_dict() for k, v in gates.items()}, sort_keys=True)),
        "ladder": sha(json.dumps(ladder, sort_keys=True)),
        "grid": sha(json.dumps({"%s|%s" % k: v for k, v in grid.items()}, sort_keys=True)),
    }
    return dict(cfg=cfg, world=world, obs=obs, queries=queries, recs=recs, need=need, ladder=ladder, grid=grid,
                gates=gates, digests=digests, bundle=bundle)


@pytest.fixture(scope="module")
def run_a():
    return pipeline(1)


def test_the_whole_slice_is_deterministic_across_two_fresh_builds(run_a):
    run_b = pipeline(1)
    assert run_a["digests"] == run_b["digests"]
    assert len(set(run_a["digests"].values())) == len(run_a["digests"])      # eight different things were hashed
    other = pipeline(2)
    assert other["digests"]["world"] != run_a["digests"]["world"]


def test_structure_answers_score_one_with_abstention_present(run_a):
    fams = {q.family for q in run_a["queries"]}
    assert "ME1" in fams and len(fams) >= 6
    assert run_a["ladder"]["oracle_struct"]["accuracy"] == 1.0
    # the pipeline() call already asserted gold_slow == gold and score 1.0 on every query


def test_gold_slow_equals_the_generator_on_twenty_l0_seeds():
    for seed in range(20):
        cfg = S.TierCfg.for_tier("L0")
        world = W.build_world(seed, cfg)
        for q in Q.build_queries(world, cfg, "C0", render=V.render_question):
            g = Q.gold_slow(world, q)
            assert (g.kind, g.value) == (q.gold.kind, q.gold.value), (seed, q.qid)
            assert Q.evidence_check(world, q) == [], (seed, q.qid)


def test_the_evidence_ladder_has_its_expected_shape(run_a):
    lad = run_a["ladder"]
    assert lad["oracle_text"]["complete"] == 1.0 and lad["oracle_text"]["recall"] == 1.0
    # blind floors: an L0 life is short (30 days, few cities, a modal job), so the habit guess B0h is better than at L1
    assert lad["B0a"]["accuracy"] < 0.2 and lad["B0h"]["accuracy"] < 0.3
    for name in ("B1", "random", "B2", "B2t", "oracle_store"):
        assert lad[name]["accuracy"] == 0.0                              # no reader: the answer text is empty
        assert 0.0 <= lad[name]["complete"] <= 1.0
    assert lad["B2t"]["complete"] >= lad["B1"]["complete"]
    assert lad["B2t"]["complete"] >= lad["random"]["complete"]


def test_the_ladder_orders_recency_bm25_bm25time_at_l1():
    run = pipeline(3, "L1")
    lad = run["ladder"]
    assert lad["B1"]["complete"] <= lad["B2"]["complete"] <= lad["B2t"]["complete"] <= lad["oracle_store"]["complete"] + 1e-9
    assert lad["B2t"]["complete"] > 0.5 and lad["B1"]["complete"] < 0.15
    assert lad["oracle_struct"]["accuracy"] == 1.0 and lad["oracle_text"]["complete"] == 1.0


def test_the_retention_gate_end_to_end(run_a):
    grid = run_a["grid"]
    base = grid[(1.0, "ALL")]
    for pol in S.GATE_POLICIES:
        if pol != "GL":
            assert grid[(1.0, pol)] == base, pol                         # R = 1.0: identical, and stored-gold is 1.0
    assert base["stored_complete"] == 1.0
    for pol in S.GATE_POLICIES:
        if pol not in ("GL", "ALL"):
            g = grid[(0.25, pol)]
            assert g["stored_complete"] <= 1.0 and g["complete"] <= g["stored_complete"] + 1e-9, pol
    assert grid[(0.25, "GO")]["stored_complete"] >= max(grid[(0.25, p)]["stored_complete"] for p in ("GU", "GR", "GH"))


def test_structural_gates_pass_on_the_real_l0_world(run_a):
    g = run_a["gates"]
    must = ("G-DET", "G-INV", "G-SOLVE", "G-SCORE", "G-HOST", "G-ORACLE", "G-LEAK", "G-AFF")
    failed = {k: g[k].to_dict() for k in must if g[k].passed is not True}
    assert not failed, failed
    assert set(g) == set(G.GATE_NAMES) - {"G-TELL"}
    assert all(r.passed in (True, False, None) for r in g.values())
    # an L0 life (30 days) is too small to fill the decile quotas of the null cell: G-SUPPORT says so instead of
    # letting the cell through (the same gate passes at L1, see test_lifesim_gates)
    assert g["G-SUPPORT"].passed is False and g["G-SUPPORT"].values["share"] > 0.05
    assert g["G-DEPTH"].passed is False                                     # 50 queries cannot give 40 per family


def test_mini_x1_the_channel_helps_where_it_is_coupled_and_the_controls_behave():
    """The chain channel -> gate -> store -> metric responds to the coupling cell (L1, dev seeds 5-8, R = 0.10,
    reliability 0.7, store S-LEX, complete@C). Numbers at the time of writing: GH[TRUE] - GH[SHUF_TYPE] is about
    +0.05 at C+ and -0.02 at the null C0r; the dose check below needs only the difference of the two."""
    cfg = S.TierCfg.for_tier("L1")

    def complete(bundle, arm, policy="GH"):
        w = bundle.world
        need = G.evidence_oids(bundle.queries)
        ch = C.make_channel(w, arm, 0.7, None, bundle.seed, need=need if arm == "LEAKY" else None)
        recs = I.records_from_world(w, bundle.obs, channel=ch)
        mem = SY.GatedMemory(SY.BM25Time(cfg.start_date), policy, 0.10, bundle.seed, need=need)
        pairs = I.run_stream(mem, recs, bundle.queries, cfg.context_words, card=w.card)
        return I.summarise_evidence([I.evidence_metrics(q, a) for q, a in pairs], keys=("complete",))["macro"]["complete"]

    def mean(bs, arm, policy="GH"):
        return sum(complete(b, arm, policy) for b in bs) / len(bs)

    out = {}
    for cell in ("C+", "C0r"):
        bs = [G.make_bundle(s, cfg, cell) for s in (5, 6, 7, 8)]
        out[cell] = {"TRUE": mean(bs, "TRUE"), "SHUF_TYPE": mean(bs, "SHUF_TYPE"), "GU": mean(bs, "TRUE", "GU"),
                     "GO": mean(bs, "TRUE", "GO"), "LEAKY": mean(bs, "LEAKY")}
    signal = {c: v["TRUE"] - v["SHUF_TYPE"] for c, v in out.items()}
    assert signal["C+"] - signal["C0r"] >= 0.03, (signal, out)          # dose: coupled > null
    for cell, v in out.items():
        assert v["GO"] > v["GU"] + 0.2, (cell, v)                       # the feasibility bound has headroom over blind retention
        assert v["LEAKY"] > v["GU"] + 0.1, (cell, v)                    # the leaky channel is detectable as a positive control


def test_deleting_the_evidence_situations_removes_the_answer_end_to_end(run_a):
    world, cfg = run_a["world"], run_a["cfg"]
    qs = [q for q in run_a["queries"] if q.family not in ("ME1",) and q.evidence_fids][:6]
    sids = sorted({world.host(f).sid for q in qs for f in q.evidence_fids})
    ablated = W.delete_events(world, sids)
    assert W.check_world(ablated) == []
    text_a = {o.oid: o.text for o in V.render(ablated, cfg, run_a["bundle"].seed, run_a["bundle"].partition)}
    original = {o.oid: o.text for o in run_a["obs"]}
    assert all(original[oid] == t for oid, t in text_a.items())          # surviving lines are byte-identical
    lines = {oid for q in qs for oid in q.evidence_oids}
    assert not (lines & set(text_a))                                      # the evidence lines are gone
    for q in qs:
        assert Q.slow_answers(ablated, q) != [q.gold.value]               # the ablated world cannot answer it
    recs = [r for r in run_a["recs"] if r.id in text_a]
    pairs = I.run_stream(SY.BM25Time(cfg.start_date), recs, qs, cfg.context_words, card=world.card)
    assert all(I.evidence_metrics(q, a)["complete"] is False for q, a in pairs)


def test_save_and_load_world_reproduces_text_and_queries(run_a):
    world, cfg = run_a["world"], run_a["cfg"]
    with tempfile.TemporaryDirectory() as tmp:
        S.save_world(world, tmp)
        loaded = S.load_world(tmp)
    assert loaded.digest() == world.digest() and loaded.channel is not None
    seed, part = run_a["bundle"].seed, run_a["bundle"].partition
    assert [o.text for o in V.render(loaded, loaded.cfg, seed, part)] == [o.text for o in run_a["obs"]]
    again = Q.build_queries(loaded, loaded.cfg, "C0", render=V.render_question, partition=part)
    assert [q.to_json() for q in again] == [q.to_json() for q in run_a["queries"]]


def test_forced_choice_forks_flow_through_the_systems_and_the_scorer():
    cfg = S.TierCfg.for_tier("L0").with_extra(choice_fork_share=0.6)
    world = W.build_world(2, cfg)
    obs = V.render(world, cfg, 2, "dev")
    queries = Q.build_queries(world, cfg, "C0", render=V.render_question)
    forks = [q for q in queries if q.fmt == "choice"]
    assert forks and all(q.twin_of and len(q.options) >= 2 and q.gold.value in q.options for q in forks)
    recs = I.records_from_world(world, obs)
    scorer = Scorer(world)
    for q, a in I.run_stream(SY.OracleStruct(world), recs, queries, cfg.context_words, card=world.card):
        assert scorer.score(q, a).correct, (q.qid, q.fmt)
    pairs = I.run_stream(SY.BM25Time(cfg.start_date), recs, queries, cfg.context_words, card=world.card)
    shares = [I.evidence_metrics(q, a)["complete"] for q, a in pairs if q.fmt == "choice"]
    assert shares and all(x in (True, False) for x in shares)           # the options put the answer into the question text


def test_a_dev_world_can_be_rendered_with_the_test_banks_as_a_renderer_ood_stress(run_a):
    world, cfg = run_a["world"], run_a["cfg"]
    ood = V.render(world, cfg, run_a["bundle"].seed, "test")
    dev = run_a["obs"]
    assert [o.oid for o in ood] == [o.oid for o in dev] and [o.text for o in ood] != [o.text for o in dev]
    for spec, o in zip(world.obs_specs, ood):
        assert V.missing_slots(spec, o.text) == []
    # the systems and the scorer do not care which banks wrote the text
    recs = I.records_from_world(world, ood)
    qs = Q.build_queries(world, cfg, "C0", render=V.render_question, partition="test")
    pairs = I.run_stream(SY.BM25Time(cfg.start_date), recs, qs, cfg.context_words, card=world.card)
    summ = I.summarise_evidence([I.evidence_metrics(q, a) for q, a in pairs])["macro"]["complete"]
    assert 0.0 <= summ <= 1.0
