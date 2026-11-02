"""The instrument gates of experiment X0 as pure functions, and the planted artefacts they must catch.

What this module provides
-------------------------
A gate takes built worlds with their rendered observations and queries (a ``Bundle``, made by
``make_bundle``) and returns a ``GateResult(name, passed, values, thresholds, detail, n)``;
``passed`` is True, False, or None when the gate cannot be evaluated (too little data, not applicable).
Gates are deterministic: every number in ``values`` is rounded to 6 decimals.

=========  ====================================================================================
G-DET      two builds of (seed, cfg) give byte-identical world, text and query digests
G-INV      invariances: ``check_world`` clean; the structure digest does not move with the channel
           arm; the candidate pool is identical across cells; deleting events leaves the other
           lines byte-identical; R = 1.0 is byte-identical across gate policies; save/load round trip
G-SOLVE    ``gold_slow`` == the generator's gold on every query; ambiguous items <= 15% per family
G-SCORE    answering from the structure scores 1.000 incl. abstention; the scrambled-world solver (the
           independent solver run on another seed's log) is at chance (+ 0.02) per answerable family;
           an adversarial table (if given) agrees 100%
G-HOST     chi-square of fact type by arousal tercile, pooled over worlds: p >= 0.2
G-SUPPORT  quota shortfall <= 2% at the null cell and <= 5% elsewhere (else the cell is void)
G-ARO      coupling realised: null cell E_0.10 and E_0.25 in [0.8, 1.2], AUC_ev in [0.45, 0.55],
           |d| <= 0.10 (AUC_ev and d compare the TARGETS' arousal with the stream's; the evidence-LINE
           versions are reported as diagnostics); other cells E_0.10 within 15% of target
           (``g_aro_grid``: monotone in the target)
G-LEN      AUC of line length, evidence vs other, in [0.45, 0.55]; |corr(length, arousal)| <= 0.05
G-AFF      A0: zero affect words (lexicon scan); A1: |Spearman(arousal, affect phrases)| <= 0.10
G-POS      position of the target clause (quartile of the words before it) and of the answer token
           (quartile of its word position) vs evidence status: chi-square p >= 0.2
G-TELL     world-grouped cross-validated AUC from surface features (L2 logistic regression via scipy)
           <= 0.55 and one-sided 95% upper bound <= 0.60, for evidence-vs-other and top-arousal-tercile
           vs rest; needs >= 300 positives and >= 3000 negatives
G-BLIND    the blind arms B0a and B0h are within chance + 0.05 (Wilson bound below 200 items per
           family replaced by a sampling slack) on families covering >= 90% of memory-dependent items
G-ORACLE   oracle_struct = 1.000 on every family and oracle_text evidence-complete = 1.000
G-DEPTH    at least 40 retained items per scored family
G-FEAS     H_cell = GO - max(GU, GR, GS, GN, GM) >= 0.20 in complete@C (else the cell is void)
G-LEAK     no lookahead and no query state (canaries after the last query, snapshot replay equals the
           online replay, repeated queries agree) and, at the null cell, the channel does not predict
           the later-need label (mean reading at the host lines of the targets vs all lines: AUC in
           [0.45, 0.55])
=========  ====================================================================================

Planted artefacts (the positive controls; every gate must FIRE on its fixture): ``plant_type_hosted``
(fact type depends on arousal: G-HOST), ``plant_leaky_importance`` (arousal depends on later need:
G-ARO, G-LEAK), the naive renderer of ``verbalise.render_planted_naive`` (G-LEN, G-AFF, G-TELL),
``plant_position_leak`` (G-POS), ``shuffled_label_scorer`` (G-SCORE), ``plant_guessable`` (G-BLIND).
``x0_gates`` runs all gates on a list of bundles.

Interpretation choices that the (partly truncated) design leaves open and that are written down here:
"evidence" lines are the union of ``evidence_oids`` of the queries of the bundle; G-INV is the set of
invariance checks above; the G-BLIND item chance is the sum of squared prior shares (else 1 over the
closed vocabulary); G-POS compares evidence with other lines among the lines that have slots (answer
token) or all lines (target clause); G-TELL adds the capitalised-token count (names) and the channel kind
to the surface features of the specification. A band on an estimated AUC, d or correlation (G-ARO, G-LEN,
G-LEAK) is applied to the estimate itself when its standard error is at most 0.02 (the pooled dev seeds);
a less precise estimate (one world) fails only if its 95% interval lies wholly outside the band, so a
clean world is not rejected by sampling noise while a planted leak (AUC 0.8) still fires. Small-sample
slack is added to the chance bounds of G-SCORE and G-BLIND below 200 items per family. The gates are
meant to be pooled over several worlds: G-HOST, G-POS and G-DEPTH need it, and G-TELL needs 300 positives.

What this module does NOT do: it calls no model, reads no clock, uses neither ``random`` nor
``hash()``; it has no power analysis (G-POWER), no mutation set (I0), no adversarial scorer table of its
own (pass one in), no sealed-seed bookkeeping and no report writer; G-TELL needs scipy and numpy
(imported on use). A gate that fails on the real generator is reported as failed, never tuned away.
"""

from __future__ import annotations

import dataclasses
import math
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from corpus.lifesim import queries as Qm
from corpus.lifesim import verbalise as V
from corpus.lifesim import world as W
from corpus.lifesim.appraisal import pearson, spearman
from corpus.lifesim.rng import q as quant
from corpus.lifesim.rng import stream
from corpus.lifesim.schema import CELLS, CHANNELS, Cell, Obs, Query, World, digest_of, load_world, save_world
from corpus.lifesim.scorers import Scorer
from corpus.lifesim.vocab import closed_vocab

from . import systems as SY
from .interface import (count_units, evidence_metrics, make_answer, records_from_world, run_stream,
                        summarise_evidence)

__all__ = [
    "GateResult", "Bundle", "make_bundle", "auc", "wilson_upper", "g_det", "g_inv", "g_solve", "g_score",
    "g_host", "g_support", "g_aro", "g_aro_grid", "g_len", "g_aff", "g_pos", "g_tell", "g_blind", "g_oracle",
    "g_depth", "g_feas", "g_leak", "x0_gates", "plant_type_hosted", "plant_leaky_importance",
    "plant_leaky_bundle", "plant_position_leak", "position_bins", "shuffled_label_scorer", "plant_guessable", "naive_bundle", "is_null_cell",
    "evidence_oids", "line_arousal", "GATE_NAMES",
]

GATE_NAMES = ("G-DET", "G-INV", "G-SOLVE", "G-SCORE", "G-HOST", "G-SUPPORT", "G-ARO", "G-LEN", "G-AFF",
              "G-POS", "G-TELL", "G-BLIND", "G-ORACLE", "G-DEPTH", "G-FEAS", "G-LEAK")


# ---------------------------------------------------------------------------------- types


@dataclass(frozen=True)
class GateResult:
    """Outcome of one gate: ``passed`` True / False / None (not evaluable), the measured ``values``, the
    ``thresholds`` applied, a one-line ``detail`` and the number ``n`` of items it looked at."""

    name: str
    passed: bool | None
    values: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)
    detail: str = ""
    n: int = 0

    def __bool__(self) -> bool:
        return self.passed is True

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "values": self.values,
                "thresholds": self.thresholds, "detail": self.detail, "n": self.n}


@dataclass
class Bundle:
    """One world with what the gates read: rendered lines, queries, the pieces of every line (for G-POS and
    G-TELL), the query build report (G-SUPPORT) and the coupling cell the queries were built for."""

    world: World
    cfg: Any
    seed: int
    partition: str
    obs: list
    queries: list
    parts: list | None = None
    report: Any = None
    cell: Any = None


def make_bundle(seed: int, cfg: Any, cell: Cell | str = "C0", *, partition: str | None = None,
                renderer: Callable[..., list] | None = None, with_parts: bool = True) -> Bundle:
    """Build a world, render it (with the pieces of every line unless ``renderer`` is given), build the
    queries of ``cell`` with the real question frames. ``renderer(world, cfg, seed, partition)`` replaces
    the real renderer (planted naive fixtures)."""
    part = partition or cfg.resolved_partition(seed)
    world = W.build_world(seed, cfg)
    parts = None
    if renderer is not None:
        obs = renderer(world, cfg, seed, part)
    elif with_parts:
        parts = V.render_all_parts(world, cfg, seed, part)
        obs = [Obs(oid=p.oid, t_obs=s.t_obs, channel=s.channel, text=p.text)
               for p, s in zip(parts, world.obs_specs)]
    else:
        obs = V.render(world, cfg, seed, part)
    cellobj = CELLS[cell] if isinstance(cell, str) else cell
    res = Qm.build_queries_ex(world, cfg, cellobj, render=V.render_question, partition=part)
    return Bundle(world=world, cfg=cfg, seed=seed, partition=part, obs=list(obs), queries=list(res.queries),
                  parts=parts, report=res.report, cell=cellobj)


def naive_bundle(seed: int, cfg: Any, leaks: Sequence[str] = ("length", "affect"), cell: Cell | str = "C0",
                 partition: str | None = None) -> Bundle:
    """A bundle rendered by the PLANTED naive renderer (positive control for G-LEN, G-AFF, G-TELL)."""
    return make_bundle(seed, cfg, cell, partition=partition,
                       renderer=lambda w, c, s, p: V.render_planted_naive(w, c, s, p, leaks=leaks))


# ----------------------------------------------------------------------------- statistics


def _q(x: float) -> float:
    return quant(float(x))


def auc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Area under the ROC curve of a score for positives vs negatives (Mann-Whitney U / (n1 n0), ties 1/2)."""
    n1, n0 = len(pos), len(neg)
    if n1 == 0 or n0 == 0:
        return 0.5
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum = 0.0
    i = 0
    n = len(allv)
    while i < n:
        j = i
        while j + 1 < n and allv[j + 1][0] == allv[i][0]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        rank_sum += avg_rank * sum(1 for k in range(i, j + 1) if allv[k][1] == 1)
        i = j + 1
    return (rank_sum - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def wilson_upper(k: int, n: int, z: float = 1.96) -> float:
    """Upper end of the Wilson score interval for k successes in n trials."""
    if n <= 0:
        return 1.0
    p = k / n
    den = 1.0 + z * z / n
    centre = p + z * z / (2.0 * n)
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return min(1.0, (centre + half) / den)


def _auc_se(n1: int, n0: int) -> float:
    """Standard error of an AUC under the null of no association."""
    return math.sqrt((n1 + n0 + 1.0) / (12.0 * n1 * n0)) if n1 and n0 else 1.0


def _d_se(n1: int, n0: int, d: float = 0.0) -> float:
    """Standard error of a standardised mean difference."""
    return math.sqrt((n1 + n0) / (n1 * n0) + d * d / (2.0 * (n1 + n0))) if n1 and n0 else 1.0


def _r_se(r: float, n: int) -> float:
    """Standard error of a correlation coefficient."""
    return (1.0 - r * r) / math.sqrt(max(1, n - 1))


def _in_band(est: float, lo: float, hi: float, se: float, precise: float = 0.02, z: float = 1.96) -> bool:
    """The band of the specification applies to the estimate itself when the estimate is precise (se <= 0.02, the
    pooled dev seeds); a less precise estimate (a single world) passes unless its 95% interval lies wholly outside
    the band. A gate meant to detect a leak (AUC 0.8) still fires on one world; a clean world no longer fails by
    sampling noise."""
    if lo <= est <= hi:
        return True
    if se <= precise:
        return False
    return est + z * se >= lo and est - z * se <= hi


def _mean(xs: Sequence[float]) -> float:
    return math.fsum(xs) / len(xs) if xs else 0.0


def _cohen_d(a: Sequence[float], b: Sequence[float]) -> float:
    n1, n0 = len(a), len(b)
    if n1 < 2 or n0 < 2:
        return 0.0
    m1, m0 = _mean(a), _mean(b)
    v1 = math.fsum((x - m1) ** 2 for x in a) / (n1 - 1)
    v0 = math.fsum((x - m0) ** 2 for x in b) / (n0 - 1)
    sp = math.sqrt(((n1 - 1) * v1 + (n0 - 1) * v0) / (n1 + n0 - 2))
    return (m1 - m0) / sp if sp > 0 else 0.0


def evidence_oids(queries: Iterable[Query]) -> set[str]:
    """Union of the evidence lines of a set of queries."""
    return {o for x in queries for o in x.evidence_oids}


def line_arousal(world: World) -> list[float]:
    """Arousal of every line in stream order (retelling lines at their factor)."""
    return Qm.stream_arousal(world)


def is_null_cell(cell: Cell | str | None) -> bool:
    """The null coupling cell: E_0.10 target 1 and no quiet-critical mass."""
    c = CELLS[cell] if isinstance(cell, str) else cell
    return c is not None and abs(c.e_target - 1.0) < 1e-9 and abs(c.mu) < 1e-9


def _pool(bundles: Sequence[Bundle]) -> tuple[list[float], list[bool], list[int]]:
    """Per line over all bundles: arousal, evidence flag, bundle index."""
    a_all: list[float] = []
    ev_all: list[bool] = []
    which: list[int] = []
    for bi, b in enumerate(bundles):
        ev = evidence_oids(b.queries)
        a = line_arousal(b.world)
        for spec, ai in zip(b.world.obs_specs, a):
            a_all.append(ai)
            ev_all.append(spec.oid in ev)
            which.append(bi)
    return a_all, ev_all, which


# ---------------------------------------------------------------------------------- G-DET


def g_det(seed: int, cfg: Any, *, build: Callable[[int, Any], World] | None = None, n_builds: int = 2,
          partition: str | None = None) -> GateResult:
    """Two (or more) independent builds of (seed, cfg), rendered and queried, must agree on the digest of the
    world, of the rendered text and of the queries."""
    build = build or W.build_world
    part = partition or cfg.resolved_partition(seed)
    digs: list[tuple] = []
    for _ in range(max(2, n_builds)):
        w = build(seed, cfg)
        obs = V.render(w, cfg, seed, part)
        qs = Qm.build_queries(w, cfg, "C0", render=V.render_question, partition=part)
        digs.append((w.digest(), digest_of([o.text for o in obs]), digest_of(qs)))
    ok = len(set(digs)) == 1
    return GateResult("G-DET", ok, {"world": digs[0][0][:12], "text": digs[0][1][:12], "queries": digs[0][2][:12],
                                    "builds": len(digs), "distinct": len(set(digs))},
                      {"distinct_digests": 1}, "" if ok else "builds differ", len(digs))


# ---------------------------------------------------------------------------------- G-INV


def g_inv(bundle: Bundle, *, attach: Callable[[World, str], World] | None = None,
          arms: Sequence[str] = ("TRUE", "SHUF_TYPE", "ORACLE"), cells: Sequence[str] = ("C+", "C-"),
          n_delete: int = 3, n_queries: int = 8) -> GateResult:
    """Invariance checks (see the module docstring). ``attach(world, arm)`` returns the world with a channel
    of that arm (default: ``make_channel`` + ``with_channel``); a sabotaged ``attach`` is the fixture."""
    from corpus.lifesim.channel import make_channel

    world, cfg, seed = bundle.world, bundle.cfg, bundle.seed
    problems: dict[str, Any] = {}
    p = W.check_world(world)
    if p:
        problems["check_world"] = p[:3]
    d0 = world.digest()
    if attach is None:
        def attach(w: World, arm: str) -> World:  # noqa: ANN001
            return w.with_channel(make_channel(w, arm, cfg.reliability_primary, None, seed, need=evidence_oids(bundle.queries)))
    moved = [arm for arm in arms if attach(world, arm).digest() != d0]
    if moved:
        problems["digest_moved_by_arm"] = moved
    pool0 = Qm.candidate_pool(world, cfg).digest()
    pool_bad = []
    for c in cells:
        Qm.build_queries(world, cfg, c, partition=bundle.partition)
        if Qm.candidate_pool(world, cfg).digest() != pool0:
            pool_bad.append(c)
    if pool_bad:
        problems["pool_moved_by_cell"] = pool_bad
    # deletion is byte-clean: the surviving lines render identically
    lined = {o.sid for o in world.obs_specs}
    with_lines = [s.sid for s in world.situations if s.sid in lined]
    sids = with_lines[:: max(1, len(with_lines) // max(1, n_delete))][:n_delete]
    ablated = W.delete_events(world, sids)
    text0 = {o.oid: o.text for o in bundle.obs}
    text1 = {o.oid: o.text for o in V.render(ablated, cfg, seed, bundle.partition)}
    changed = [oid for oid, t in text1.items() if text0.get(oid) != t]
    gone = set(text0) - set(text1)
    if changed or not gone:
        problems["deletion_not_clean"] = {"changed": changed[:3], "removed": len(gone)}
    # R = 1.0 is byte-identical across policies
    recs = records_from_world(world, bundle.obs, channel=attach(world, "TRUE").channel)
    qs = bundle.queries[:n_queries]
    base = None
    differing = []
    for pol in ("ALL", "GU", "GR", "GN", "GM", "GS", "GH", "GTN", "GO", "GA"):
        g = SY.GatedMemory(SY.BM25Time(cfg.start_date), pol, 1.0, seed, need=evidence_oids(bundle.queries))
        out = [a.to_json() for _, a in run_stream(g, recs, qs, cfg.context_words, card=world.card)]
        if base is None:
            base = out
        elif out != base:
            differing.append(pol)
    if differing:
        problems["r1_not_identical"] = differing
    # save / load round trip
    with tempfile.TemporaryDirectory() as tmp:
        save_world(world, tmp)
        if load_world(tmp).digest() != d0:
            problems["roundtrip"] = "digest changed"
    ok = not problems
    return GateResult("G-INV", ok, {"problems": problems, "deleted_situations": len(sids)},
                      {"all_invariances": True}, "" if ok else "; ".join(sorted(problems)), 1)


# --------------------------------------------------------------------------------- G-SOLVE


def g_solve(bundles: Sequence[Bundle], *, max_ambiguous: float = 0.15) -> GateResult:
    """``gold_slow`` equals the generator gold on every query, and few items admit two consistent answers."""
    n = 0
    wrong: list[str] = []
    amb: dict[str, int] = {}
    fam_n: dict[str, int] = {}
    for b in bundles:
        for x in b.queries:
            n += 1
            fam_n[x.family] = fam_n.get(x.family, 0) + 1
            try:
                g = Qm.gold_slow(b.world, x)
                if (g.kind, g.value) != (x.gold.kind, x.gold.value):
                    wrong.append(x.qid)
            except Qm.AmbiguousGold:
                amb[x.family] = amb.get(x.family, 0) + 1
                wrong.append(x.qid)
    share = {f: amb.get(f, 0) / fam_n[f] for f in fam_n}
    ok = n > 0 and not wrong and all(s <= max_ambiguous for s in share.values())
    return GateResult("G-SOLVE", ok if n else None,
                      {"agree": n - len(wrong), "n": n, "mismatched": wrong[:5], "ambiguous_share": {k: _q(v) for k, v in sorted(share.items())}},
                      {"agreement": 1.0, "max_ambiguous_share": max_ambiguous}, "" if ok else "gold_slow differs", n)


# --------------------------------------------------------------------------------- G-SCORE


def shuffled_label_scorer(bundle: Bundle) -> Callable[[Query, Any], Any]:
    """PLANTED ARTEFACT: a scorer whose labels are shuffled (each query is scored against the gold of the next
    query of the same family), the positive control of G-SCORE."""
    by_fam: dict[str, list[Query]] = {}
    for x in bundle.queries:
        by_fam.setdefault(x.family, []).append(x)
    swap: dict[str, Query] = {}
    for fam, lst in by_fam.items():
        for i, x in enumerate(lst):
            swap[x.qid] = lst[(i + 1) % len(lst)]
    sc = Scorer(bundle.world)

    def score(query: Query, answer: Any) -> Any:
        other = swap.get(query.qid, query)
        return sc.score(dataclasses.replace(query, gold=other.gold), answer)

    return score


def _structure_answer(x: Query):
    g = x.gold
    return make_answer(g.value, (), abstained=g.kind == "unknown", confidence=100)


def _item_chance(world: World, x: Query) -> float:
    pr = world.prior(x.ask)
    if pr is not None:
        return pr.chance()
    if x.gold.vocab_id:
        try:
            return 1.0 / len(closed_vocab(world, x.gold.vocab_id).values)
        except KeyError:
            pass
    return 1.0 / 24.0


def g_score(bundles: Sequence[Bundle], *, score: Callable[[Query, Any], Any] | None = None,
            adversarial: Sequence[tuple[Query, str, bool]] | None = None, slack: float = 0.02) -> GateResult:
    """Structure answers score 1.000 (abstention included), the scrambled-world solver (the independent solver
    run on another seed's log) stays within ``slack`` of chance on every answerable family, and an adversarial
    table agrees 100% (if given). Chance is the larger of the prior chance and the best constant guess on the
    family's gold values (an independent guesser cannot beat the modal gold share); below 200 items a sampling
    slack 2.5 sqrt(c (1 - c) / n) is added (about 0.6% per family one-sided, so that seven small families do
    not raise a false alarm). ``score(query, answer)`` replaces the real scorer (the shuffled-label fixture)."""
    n = hits = 0
    wrong: list[str] = []
    for b in bundles:
        sc = Scorer(b.world)
        fn = score or sc.score
        for x in b.queries:
            n += 1
            r = fn(x, _structure_answer(x))
            if r.correct and r.score == 1.0:
                hits += 1
            else:
                wrong.append(x.qid)
    scr: dict[str, list[int]] = {}
    chance: dict[str, list[float]] = {}
    if len(bundles) >= 2:
        for i, b in enumerate(bundles):
            other = bundles[(i + 1) % len(bundles)]
            sc = Scorer(b.world)
            fn = score or sc.score
            for x in b.queries:
                if x.family == "ME1":
                    continue
                try:
                    ans = Qm.slow_answers(other.world, x)
                except Exception:  # noqa: BLE001 - a solver that cannot read the cue answers nothing
                    ans = []
                text = ans[0] if len(ans) == 1 else "UNKNOWN"
                r = fn(x, make_answer(text, (), abstained=text == "UNKNOWN", confidence=100))
                scr.setdefault(x.family, []).append(1 if r.correct else 0)
                chance.setdefault(x.family, []).append(_item_chance(b.world, x))
    best_const: dict[str, float] = {}
    for f in scr:
        golds: dict[str, int] = {}
        for b in bundles:
            for x in b.queries:
                if x.family == f:
                    golds[x.gold.value] = golds.get(x.gold.value, 0) + 1
        best_const[f] = max(golds.values()) / sum(golds.values()) if golds else 0.0
    scr_acc = {f: _mean(v) for f, v in scr.items()}
    scr_ch = {f: max(_mean(chance[f]), best_const[f]) for f in scr}
    scr_slack = {f: slack + (0.0 if len(scr[f]) >= 200
                             else 2.5 * math.sqrt(max(scr_ch[f] * (1 - scr_ch[f]), 1e-12) / len(scr[f])))
                 for f in scr}
    scr_bad = sorted(f for f in scr if scr_acc[f] > scr_ch[f] + scr_slack[f])
    adv_ok = None
    if adversarial:
        sc0 = Scorer(bundles[0].world) if bundles else None
        agree = sum(1 for x, text, expected in adversarial if (sc0.score(x, text).correct == expected))
        adv_ok = agree == len(adversarial)
    ok = n > 0 and hits == n and not scr_bad and (adv_ok is not False)
    return GateResult("G-SCORE", ok if n else None,
                      {"structure_accuracy": _q(hits / n) if n else 0.0, "wrong": wrong[:5],
                       "scramble_accuracy": {f: _q(v) for f, v in sorted(scr_acc.items())},
                       "scramble_chance": {f: _q(v) for f, v in sorted(scr_ch.items())},
                       "scramble_above_chance": scr_bad, "adversarial_agree": adv_ok},
                      {"structure_accuracy": 1.0, "scramble_slack": slack}, "" if ok else "scorer or solver off", n)


def plant_guessable(bundle: Bundle, family: str = "EP1") -> Bundle:
    """PLANTED ARTEFACT (habit leak): the gold of every query of ``family`` is replaced by the prior mode of its
    slot, so a blind prior guess is always right (positive control of G-BLIND)."""
    qs = []
    for x in bundle.queries:
        pr = bundle.world.prior(x.ask)
        if x.family == family and pr is not None:
            x = dataclasses.replace(x, gold=dataclasses.replace(x.gold, value=pr.mode(), near_miss=(), aliases=()))
        qs.append(x)
    return dataclasses.replace(bundle, queries=qs)


# --------------------------------------------------------------------------------- G-HOST

HOST_PREDS = ("breakfast", "errand_visit", "car_colour", "companion", "vehicle_colour")


def g_host(bundles: Sequence[Bundle], *, preds: Sequence[str] = HOST_PREDS, p_min: float = 0.2) -> GateResult:
    """Chi-square test of independence of fact type and arousal tercile of the hosting situation, pooled
    over the worlds: p >= 0.2 (fact type carries no information about the arousal of its host)."""
    table: dict[str, list[int]] = {}
    for b in bundles:
        for pred, row in W.host_profile(b.world, bins=3).items():
            if pred in preds:
                acc = table.setdefault(pred, [0, 0, 0])
                for j in range(3):
                    acc[j] += row[j]
    rows = [table[p_] for p_ in preds if p_ in table]
    chi2, dof, p = W.chi_square_independence(rows)
    n = sum(sum(r) for r in rows)
    ok = dof > 0 and p >= p_min
    return GateResult("G-HOST", ok if dof > 0 else None,
                      {"chi2": _q(chi2), "dof": dof, "p": _q(p), "table": {k: v for k, v in sorted(table.items())}},
                      {"p_min": p_min}, "" if ok else "fact type depends on arousal", n)


def _situation_hosts(world: World) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for s in world.situations:
        out[s.sid] = {world.fact(f).pred for f in s.facts}
    return out


def plant_type_hosted(world: World, high: Sequence[str] = ("car_colour", "companion"),
                      low: Sequence[str] = ("breakfast",)) -> World:
    """PLANTED ARTEFACT (the type-hosted generator of E0): the arousal values of the world are permuted so that
    the situations hosting ``high`` fact types get the highest values and those hosting ``low`` types the lowest;
    the marginal distribution of arousal is unchanged. Positive control of G-HOST."""
    hosts = _situation_hosts(world)
    sits = list(world.situations)
    vals = sorted(s.A for s in sits)
    def group(s) -> int:
        h = hosts[s.sid]
        if h & set(high):
            return 2
        if h & set(low):
            return 0
        return 1
    order = sorted(range(len(sits)), key=lambda i: (group(sits[i]), sits[i].A, i))
    new = list(sits)
    for rank, i in enumerate(order):
        new[i] = dataclasses.replace(sits[i], A=vals[rank])
    return dataclasses.replace(world, situations=tuple(new))


# ------------------------------------------------------------------------------- G-SUPPORT


def g_support(bundles: Sequence[Bundle], cell: Cell | str | None = None, *, null_max: float = 0.02,
              other_max: float = 0.05) -> GateResult:
    """Pooled quota shortfall (what no family can fill) over the bundles: <= 2% at the null cell and <= 5%
    elsewhere, else the cell is void."""
    c = CELLS[cell] if isinstance(cell, str) else (cell or (bundles[0].cell if bundles else None))
    short = sum(b.report.pooled_shortfall for b in bundles if b.report is not None)
    demand = sum(b.report.pooled_demand for b in bundles if b.report is not None)
    share = short / demand if demand else 0.0
    lim = null_max if is_null_cell(c) else other_max
    ok = share <= lim
    return GateResult("G-SUPPORT", ok if demand else None,
                      {"shortfall": short, "demand": demand, "share": _q(share), "cell": getattr(c, "name", "")},
                      {"max_share": lim}, "" if ok else "cell void: support too thin", demand)


# ---------------------------------------------------------------------------------- G-ARO


def plant_leaky_importance(world: World, queries: Sequence[Query], pull: float = 0.8) -> tuple[World, list]:
    """PLANTED ARTEFACT (the leaky-importance generator of E0 v0.1): the arousal of every situation that hosts an
    evidence line is pulled towards 1 by ``pull``, i.e. importance is computed from the later need. Returns the
    world and the queries with ``tags.target_arousal`` recomputed from the new arousal (the mean arousal of the
    situations that host the target facts, as the query builder defines it)."""
    known = {s.oid: s.sid for s in world.obs_specs}
    ev_sids = {known[o] for o in evidence_oids(queries) if o in known}
    new = tuple(dataclasses.replace(s, A=s.A + (1.0 - s.A) * pull) if s.sid in ev_sids else s
                for s in world.situations)
    leaky = dataclasses.replace(world, situations=new)
    out = []
    for x in queries:
        if x.family != "ME1" and x.evidence_fids:
            hosts = [leaky.host(f).A for f in x.evidence_fids]
            x = dataclasses.replace(x, tags=dataclasses.replace(x.tags, target_arousal=_mean(hosts)))
        out.append(x)
    return leaky, out


def plant_leaky_bundle(bundle: Bundle, pull: float = 0.8) -> Bundle:
    """``plant_leaky_importance`` applied to a bundle (the channel, if any, is dropped: it was built from the
    honest arousal)."""
    w, qs = plant_leaky_importance(bundle.world, bundle.queries, pull)
    return dataclasses.replace(bundle, world=w.with_channel(None), queries=qs)


def _enrichment(bundles: Sequence[Bundle], frac: float) -> float:
    hit = n = 0
    for b in bundles:
        srt = sorted(line_arousal(b.world))
        for x in b.queries:
            if x.family == "ME1":
                continue
            n += 1
            if Qm.rank_fraction(x.tags.target_arousal, srt) >= 1.0 - frac:
                hit += 1
    return hit / n / frac if n else 0.0


def g_aro(bundles: Sequence[Bundle], cell: Cell | str | None = None, *, tol: float = 0.15) -> GateResult:
    """The coupling cell is realised. Null cell: E_0.10 and E_0.25 in [0.8, 1.2], AUC_ev in [0.45, 0.55] and
    |d| <= 0.10, where AUC_ev and d compare the arousal of the TARGETS (``tags.target_arousal`` of the answerable
    queries) with that of the stream's lines. Any other cell: E_0.10 within ``tol`` of its target. The same
    statistics over the evidence LINES are reported as ``AUC_ev_lines`` and ``d_lines`` (diagnostics, not gated):
    they sit below the null by design, because IN4 remarks are quiet and the stale versions of a state fact are
    retelling lines at half their situation's arousal."""
    c = CELLS[cell] if isinstance(cell, str) else (cell or (bundles[0].cell if bundles else None))
    e10, e25 = _enrichment(bundles, 0.10), _enrichment(bundles, 0.25)
    a_all, ev, _ = _pool(bundles)
    a_tar = [x.tags.target_arousal for b in bundles for x in b.queries if x.family != "ME1"]
    au, d = auc(a_tar, a_all), _cohen_d(a_tar, a_all)  # item level: the arousal of the targets vs the stream
    a_ev = [a for a, e in zip(a_all, ev) if e]
    a_ot = [a for a, e in zip(a_all, ev) if not e]
    vals = {"E_0.10": _q(e10), "E_0.25": _q(e25), "AUC_ev": _q(au), "d": _q(d), "cell": getattr(c, "name", ""),
            "AUC_ev_lines": _q(auc(a_ev, a_ot)), "d_lines": _q(_cohen_d(a_ev, a_ot))}
    n = sum(1 for b in bundles for x in b.queries if x.family != "ME1")
    if is_null_cell(c):
        n1, n0 = len(a_tar), len(a_all)
        vals["AUC_ev_se"], vals["d_se"] = _q(_auc_se(n1, n0)), _q(_d_se(n1, n0, d))
        ok = (0.8 <= e10 <= 1.2 and 0.8 <= e25 <= 1.2 and _in_band(au, 0.45, 0.55, _auc_se(n1, n0))
              and _in_band(d, -0.10, 0.10, _d_se(n1, n0, d)))
        thr = {"E": [0.8, 1.2], "AUC_ev": [0.45, 0.55], "abs_d": 0.10}
    else:
        ok = abs(e10 / c.e_target - 1.0) <= tol
        thr = {"E_0.10_rel_tol": tol, "target": c.e_target}
    return GateResult("G-ARO", ok if n else None, vals, thr, "" if ok else "coupling not realised", n)


def g_aro_grid(cells: dict[str, Sequence[Bundle]], *, slack: float = 0.05) -> GateResult:
    """Realised E_0.10 is non-decreasing in the target across the cells of a grid (within ``slack``)."""
    rows = sorted(((CELLS[k].e_target if isinstance(k, str) and k in CELLS else k.e_target, _enrichment(v, 0.10))
                   for k, v in cells.items()))
    ok = all(b[1] >= a[1] - slack for a, b in zip(rows, rows[1:]))
    return GateResult("G-ARO", ok, {"E_0.10_by_target": [(t, _q(e)) for t, e in rows]}, {"monotone_slack": slack},
                      "" if ok else "not monotone", len(rows))


# ------------------------------------------------------------------------- G-LEN / G-AFF


def g_len(bundles: Sequence[Bundle], *, auc_band: tuple[float, float] = (0.45, 0.55), r_max: float = 0.05) -> GateResult:
    """Line length carries no information about evidence status or arousal: AUC(length: evidence vs other) in
    [0.45, 0.55] and |corr(length, arousal)| <= 0.05 (pooled over the worlds)."""
    a_all, ev, which = _pool(bundles)
    lens = [float(count_units(o.text)) for b in bundles for o in b.obs]
    l_ev = [l for l, e in zip(lens, ev) if e]
    l_ot = [l for l, e in zip(lens, ev) if not e]
    au = auc(l_ev, l_ot)
    r = pearson(lens, a_all) if len(lens) > 2 else 0.0
    ok = (_in_band(au, auc_band[0], auc_band[1], _auc_se(len(l_ev), len(l_ot)))
          and _in_band(r, -r_max, r_max, _r_se(r, len(lens))))
    return GateResult("G-LEN", ok if l_ev and l_ot else None,
                      {"AUC_length": _q(au), "corr_length_arousal": _q(r), "mean_len_evidence": _q(_mean(l_ev)),
                       "mean_len_other": _q(_mean(l_ot))}, {"AUC": list(auc_band), "abs_corr": r_max},
                      "" if ok else "length tells", len(lens))


def g_aff(bundles: Sequence[Bundle], mode: str | None = None, *, rho_max: float = 0.10) -> GateResult:
    """Affect wording. A0: zero lexicon affect words in every line. A1: |Spearman(arousal, affect phrases per
    line)| <= 0.10. A2 (correlated by design) is not evaluated (passed None)."""
    m = mode or (bundles[0].cfg.affect if bundles else "A0")
    counts = [float(len(V.affect_scan(o.text))) for b in bundles for o in b.obs]
    a_all, _, _ = _pool(bundles)
    total = int(sum(counts))
    rho = spearman(a_all, counts) if len(counts) > 2 and len(set(counts)) > 1 else 0.0
    vals = {"mode": m, "affect_words": total, "spearman_arousal_affect": _q(rho)}
    if m == "A0":
        ok: bool | None = total == 0
        thr: dict = {"affect_words": 0}
    elif m == "A1":
        ok = abs(rho) <= rho_max
        thr = {"abs_spearman": rho_max}
    else:
        ok, thr = None, {}
    return GateResult("G-AFF", ok, vals, thr, "" if ok is not False else "affect leaks", len(counts))


# ------------------------------------------------------------------------------------ G-POS


def plant_position_leak(parts: Sequence[Any], evidence: set[str]) -> list:
    """PLANTED ARTEFACT: the target clause of every evidence line comes first and that of every other line comes
    last (positive control of G-POS)."""
    out = []
    for p in parts:
        if p.oid in evidence:
            out.append(dataclasses.replace(p, post=tuple(p.pre) + tuple(p.post), pre=()))
        else:
            out.append(dataclasses.replace(p, pre=tuple(p.pre) + tuple(p.post), post=()))
    return out


def _core_position(p: Any) -> int:
    """Quartile (0-3) of the share of the line's words that come before the target clause."""
    before = sum(count_units(x) for x in p.pre)
    return min(3, int(4 * before / max(1, count_units(p.text))))


def position_bins(b: Bundle, parts: Sequence[Any] | None = None) -> list[tuple[int, int | None]]:
    """Per line: (quartile of the words before the target clause, quartile of the word position of the first fact
    slot or None if the line has no fact slot)."""
    pl = parts if parts is not None else (b.parts or V.render_all_parts(b.world, b.cfg, b.seed, b.partition))
    out = []
    for spec, p in zip(b.world.obs_specs, pl):
        slot = next((s for s in spec.slots if s.fid), None)
        tok = None
        if slot is not None:
            i = p.text.find(slot.value)
            if i >= 0:
                tok = min(3, int(4 * count_units(p.text[:i]) / max(1, count_units(p.text))))
        out.append((_core_position(p), tok))
    return out


def g_pos(bundles: Sequence[Bundle], *, parts: Sequence[Sequence[Any]] | None = None, p_min: float = 0.2,
          evidence_override: Sequence[set] | None = None) -> GateResult:
    """Where the target clause sits in the line (quartile of the words before it) and where the answer token sits
    (quartile of the word position of the first fact slot) must not depend on whether the line is evidence:
    both chi-square p >= 0.2. ``parts`` (one list of line pieces per bundle) and ``evidence_override`` (one set of
    oids per bundle) replace the bundles' own, for the planted-leak and clean-label controls."""
    t_clause = [[0] * 4, [0] * 4]
    t_token = [[0] * 4, [0] * 4]
    n = 0
    for bi, b in enumerate(bundles):
        ev = evidence_override[bi] if evidence_override is not None else evidence_oids(b.queries)
        bins = position_bins(b, parts[bi] if parts is not None else None)
        for spec, (cp, tp) in zip(b.world.obs_specs, bins):
            row = 0 if spec.oid in ev else 1
            t_clause[row][cp] += 1
            if tp is not None:
                t_token[row][tp] += 1
            n += 1
    c1, d1, p1 = W.chi_square_independence(t_clause)
    c2, d2, p2 = W.chi_square_independence(t_token)
    ok = (p1 >= p_min) and (p2 >= p_min)
    return GateResult("G-POS", ok if (d1 > 0 and d2 > 0) else None,
                      {"p_clause": _q(p1), "p_token": _q(p2), "table_clause": t_clause, "table_token": t_token},
                      {"p_min": p_min}, "" if ok else "position tells", n)


# ----------------------------------------------------------------------------------- G-TELL


def _surface_matrix(b: Bundle, dim: int = 256, tmpl: int = 32):
    """Surface features of every line of a bundle: numeric block (length, digits, rare-token share, capitalised
    tokens, position in the day, day offset), template-id and channel-kind one-hots, hashed uni/bigrams."""
    import hashlib

    import numpy as np

    from .systems import tokens

    specs = b.world.obs_specs
    n = len(specs)
    texts = [o.text for o in b.obs]
    toks = [tokens(t) for t in texts]
    df: dict[str, int] = {}
    for tk in toks:
        for t in set(tk):
            df[t] = df.get(t, 0) + 1
    kinds = list(CHANNELS)
    days = max(1, b.world.cfg.days)
    by_day: dict[int, list[int]] = {}
    for i, s in enumerate(specs):
        by_day.setdefault(s.t_obs // 1440, []).append(i)
    pos_in_day = [0.0] * n
    for lst in by_day.values():
        for k, i in enumerate(lst):
            pos_in_day[i] = k / max(1, len(lst) - 1)
    num = np.zeros((n, 6))
    one = np.zeros((n, tmpl + len(kinds)))
    hashed = np.zeros((n, dim))

    def h(s: str) -> int:
        return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=4).digest(), "big")

    for i in range(n):
        tk = toks[i]
        raw = texts[i].split()
        num[i, 0] = len(raw)
        num[i, 1] = sum(ch.isdigit() for ch in texts[i])
        num[i, 2] = sum(1 for t in tk if df[t] <= 2) / max(1, len(tk))
        num[i, 3] = sum(1 for k, w in enumerate(raw) if k > 0 and w[:1].isupper() and not raw[k - 1].endswith((".", "!", "?")))
        num[i, 4] = pos_in_day[i]
        num[i, 5] = specs[i].t_obs / (days * 1440.0)
        if b.parts is not None:
            one[i, h(repr(b.parts[i].skeleton)) % tmpl] = 1.0
        else:
            one[i, h(" ".join(tk[:3])) % tmpl] = 1.0
        one[i, tmpl + kinds.index(specs[i].channel)] = 1.0
        for t in tk:
            hashed[i, h(t) % dim] += 1.0
        for x, y in zip(tk, tk[1:]):
            hashed[i, h(x + " " + y) % dim] += 1.0
    hashed = np.log1p(hashed)
    return num, np.hstack([one, hashed])


def _logreg_fit(X, y, lam: float = 1.0):
    import numpy as np
    from scipy.optimize import minimize

    n, d = X.shape

    def fun(w):
        z = X @ w[:-1] + w[-1]
        # stable log(1 + exp(-yz)) with y in {-1, 1}
        t = (2 * y - 1) * z
        loss = np.logaddexp(0.0, -t).mean() + 0.5 * lam * (w[:-1] @ w[:-1]) / n
        p = 0.5 * (1.0 + np.tanh(0.5 * z))
        g = (p - y) / n
        grad = np.concatenate([X.T @ g + lam * w[:-1] / n, [g.sum()]])
        return loss, grad

    res = minimize(fun, np.zeros(d + 1), jac=True, method="L-BFGS-B", options={"maxiter": 200})
    return res.x


def g_tell(bundles: Sequence[Bundle], *, point_max: float = 0.55, upper_max: float = 0.60, min_pos: int = 300,
           min_neg: int = 3000, folds: int = 5, n_boot: int = 200, enforce_power: bool = True,
           evidence_override: Sequence[set] | None = None,
           targets_to_test: Sequence[str] = ("evidence", "top_arousal")) -> GateResult:
    """World-grouped cross-validated AUC of a regularised logistic regression on surface features (see
    ``_surface_matrix``) for two targets, evidence-vs-other and top-arousal-tercile-vs-rest. Passes iff both
    point AUCs are <= 0.55 and both one-sided 95% bootstrap upper bounds (over worlds, over day blocks for a
    single world) <= 0.60. With fewer than 300 positives or 3000 negatives it is not evaluable (passed None)
    unless ``enforce_power`` is False. ``evidence_override`` (one set of oids per bundle) replaces the evidence
    lines, e.g. by a random set for a clean-label control."""
    import numpy as np

    mats = [_surface_matrix(b) for b in bundles]
    targets: dict[str, list[np.ndarray]] = {"evidence": [], "top_arousal": []}
    for bi, b in enumerate(bundles):
        ev = evidence_override[bi] if evidence_override is not None else evidence_oids(b.queries)
        targets["evidence"].append(np.array([1.0 if s.oid in ev else 0.0 for s in b.world.obs_specs]))
        a = np.array(line_arousal(b.world))
        thr = np.sort(a)[int(len(a) * 2 / 3)] if len(a) else 1.0
        targets["top_arousal"].append((a >= thr).astype(float))
    nb = len(bundles)
    groups: list[np.ndarray] = []
    for i, b in enumerate(bundles):
        n = len(b.world.obs_specs)
        if nb >= 2:
            groups.append(np.full(n, i % folds))
        else:
            groups.append((np.arange(n) * folds // max(1, n)).astype(int))  # contiguous blocks of the stream
    cluster = [np.full(len(b.world.obs_specs), i) if nb >= 2
               else np.array([s.t_obs // (7 * 1440) for s in b.world.obs_specs])  # weekly blocks of one world
               for i, b in enumerate(bundles)]
    X_num = np.vstack([m[0] for m in mats])
    X_cat = np.vstack([m[1] for m in mats])
    grp = np.concatenate(groups)
    clu = np.concatenate(cluster)
    out: dict[str, Any] = {}
    n_pos_min = n_neg_min = 10 ** 9
    ok_all = True
    for name, ys in targets.items():
        if name not in targets_to_test:
            continue
        y = np.concatenate(ys)
        n_pos, n_neg = int(y.sum()), int(len(y) - y.sum())
        n_pos_min, n_neg_min = min(n_pos_min, n_pos), min(n_neg_min, n_neg)
        oof = np.zeros(len(y))
        for f in sorted(set(grp.tolist())):
            te = grp == f
            tr = ~te
            if tr.sum() == 0 or te.sum() == 0 or y[tr].sum() == 0 or y[tr].sum() == tr.sum():
                oof[te] = 0.5
                continue
            mu, sd = X_num[tr].mean(axis=0), X_num[tr].std(axis=0)
            sd[sd == 0] = 1.0
            Xtr = np.hstack([(X_num[tr] - mu) / sd, X_cat[tr]])
            Xte = np.hstack([(X_num[te] - mu) / sd, X_cat[te]])
            w = _logreg_fit(Xtr, y[tr])
            oof[te] = Xte @ w[:-1] + w[-1]
        point = auc(oof[y == 1].tolist(), oof[y == 0].tolist())
        rng = stream(0, "gate", "g_tell", name)
        ids = sorted(set(clu.tolist()))
        by = {c: np.where(clu == c)[0] for c in ids}
        boots = []
        for _ in range(n_boot):
            pick = [ids[rng.below(len(ids))] for _ in ids]
            idx = np.concatenate([by[c] for c in pick])
            yy, ss = y[idx], oof[idx]
            if yy.sum() == 0 or yy.sum() == len(yy):
                continue
            boots.append(auc(ss[yy == 1].tolist(), ss[yy == 0].tolist()))
        boots.sort()
        upper = boots[min(len(boots) - 1, int(0.95 * len(boots)))] if boots else 1.0
        out[name] = {"auc": _q(point), "upper95": _q(upper), "positives": n_pos, "negatives": n_neg}
        ok_all = ok_all and point <= point_max and upper <= upper_max
    powered = n_pos_min >= min_pos and n_neg_min >= min_neg
    passed: bool | None = ok_all
    if enforce_power and not powered:
        passed = None if ok_all else False
    return GateResult("G-TELL", passed, {"targets": out, "powered": powered},
                      {"auc": point_max, "upper95": upper_max, "min_pos": min_pos, "min_neg": min_neg},
                      "" if passed else ("underpowered" if passed is None else "surface features predict"),
                      int(sum(len(b.world.obs_specs) for b in bundles)))


# ---------------------------------------------------------------------------------- G-BLIND


def g_blind(bundles: Sequence[Bundle], *, point_slack: float = 0.05, open_bound: float = 0.08,
            choice_bound: float = 0.10, coverage: float = 0.90, min_n: int = 200,
            families: Sequence[str] | None = None) -> GateResult:
    """The blind arms B0a (prior mode) and B0h (stream frequency) must not beat chance on memory-dependent items
    (ME1 and habit-answerable items excluded): per family accuracy <= chance + 0.05 and, with >= 200 items, the
    Wilson 95% upper bound <= chance + 0.08 (0.10 for forced choice); below 200 items the sampling slack
    1.645 sqrt(c (1 - c) / n) is added to the point bound. The gate passes iff the passing families hold
    >= 90% of the memory-dependent items."""
    stats: dict[str, dict] = {}
    for b in bundles:
        sc = Scorer(b.world)
        mem = [x for x in b.queries if x.family != "ME1" and not x.tags.prior_answerable
               and (families is None or x.family in families)]
        recs = records_from_world(b.world, b.obs)
        for name, factory in (("B0a", lambda: SY.Prior(b.world)), ("B0h", lambda: SY.Heuristic.for_world(b.world))):
            pairs = run_stream(factory(), recs, mem, 0, card=b.world.card)
            for x, a in pairs:
                r = sc.score(x, a)
                e = stats.setdefault(x.family, {"n": 0, "choice": 0, "chance": 0.0, "B0a": 0, "B0h": 0})
                if name == "B0a":
                    e["n"] += 1
                    e["choice"] += 1 if x.fmt == "choice" else 0
                    e["chance"] += _item_chance(b.world, x)
                e[name] += 1 if r.correct else 0
    fams: dict[str, dict] = {}
    items = good = 0
    for fam, e in sorted(stats.items()):
        n = e["n"]
        ch = e["chance"] / n
        entry = {"n": n, "chance": _q(ch)}
        fam_ok = True
        for name in ("B0a", "B0h"):
            acc = e[name] / n
            slack = 0.0 if n >= min_n else 1.645 * math.sqrt(max(ch * (1 - ch), 1e-12) / n)
            ok = acc <= ch + point_slack + slack
            if n >= min_n:
                bound = choice_bound if e["choice"] * 2 > n else open_bound
                ok = ok and wilson_upper(e[name], n) <= ch + bound
            entry[name] = _q(acc)
            fam_ok = fam_ok and ok
        entry["ok"] = fam_ok
        entry["underpowered"] = n < min_n
        fams[fam] = entry
        items += n
        good += n if fam_ok else 0
    share = good / items if items else 0.0
    ok = share >= coverage
    return GateResult("G-BLIND", ok if items else None, {"families": fams, "covered_share": _q(share)},
                      {"point_slack": point_slack, "open_bound": open_bound, "choice_bound": choice_bound,
                       "coverage": coverage}, "" if ok else "blind arms beat chance", items)


# --------------------------------------------------------------------------------- G-ORACLE


def g_oracle(bundles: Sequence[Bundle], *, budget: int | None = None) -> GateResult:
    """oracle_struct scores 1.000 on every family (abstention included) and oracle_text delivers every
    evidence line (complete@C = 1.000) on every family."""
    n_struct = ok_struct = 0
    rows = []
    wrong: list[str] = []
    for b in bundles:
        c_words = b.cfg.context_words if budget is None else budget
        recs = records_from_world(b.world, b.obs)
        sc = Scorer(b.world)
        for x, a in run_stream(SY.OracleStruct(b.world), recs, b.queries, c_words, card=b.world.card):
            n_struct += 1
            if sc.score(x, a).correct:
                ok_struct += 1
            else:
                wrong.append(x.qid)
        for x, a in run_stream(SY.OracleText(), recs, b.queries, c_words, card=b.world.card):
            rows.append(evidence_metrics(x, a))
    summ = summarise_evidence(rows, keys=("complete",))
    fam_complete = {f: v["complete"] for f, v in summ["by_family"].items() if v["complete"] is not None}
    text_ok = all(v == 1.0 for v in fam_complete.values())
    ok = n_struct > 0 and ok_struct == n_struct and text_ok
    return GateResult("G-ORACLE", ok if n_struct else None,
                      {"oracle_struct_accuracy": _q(ok_struct / n_struct) if n_struct else 0.0, "wrong": wrong[:5],
                       "oracle_text_complete": {f: _q(v) for f, v in sorted(fam_complete.items())}},
                      {"oracle_struct": 1.0, "oracle_text_complete": 1.0}, "" if ok else "oracle below 1.000", n_struct)


# ---------------------------------------------------------------------------------- G-DEPTH


def g_depth(bundles: Sequence[Bundle], *, min_items: int = 40, families: Sequence[str] | None = None) -> GateResult:
    """At least 40 retained items per scored family (pooled over the bundles)."""
    counts: dict[str, int] = {}
    for b in bundles:
        for x in b.queries:
            counts[x.family] = counts.get(x.family, 0) + 1
    if families is None:
        fams = set(dict(bundles[0].cfg.family_mix)) if bundles else set()
        if bundles and bundles[0].cfg.abstain_share > 0:
            fams.add("ME1")
        families = sorted(fams)
    short = {f: counts.get(f, 0) for f in families if counts.get(f, 0) < min_items}
    ok = not short
    return GateResult("G-DEPTH", ok, {"counts": {f: counts.get(f, 0) for f in families}, "short": short},
                      {"min_items": min_items}, "" if ok else "too few items", sum(counts.values()))


# ----------------------------------------------------------------------------------- G-FEAS


def _complete_macro(bundles: Sequence[Bundle], factory: Callable[[Bundle], Any], budget: int | None) -> float:
    per_world = []
    for b in bundles:
        recs = records_from_world(b.world, b.obs)
        mem = factory(b)
        pairs = run_stream(mem, recs, b.queries, b.cfg.context_words if budget is None else budget, card=b.world.card)
        rows = [evidence_metrics(x, a) for x, a in pairs]
        per_world.append(summarise_evidence(rows, keys=("complete",))["macro"]["complete"] or 0.0)
    return _mean(per_world)


def g_feas(bundles: Sequence[Bundle], R: float, *, budget: int | None = None, h_min: float = 0.20,
           competitors: Sequence[str] = ("GU", "GR", "GS", "GN", "GM")) -> GateResult:
    """Headroom of the cell: H_cell = GO - max(GU, GR, GS, GN, GM) in complete@C (macro over families, mean over
    worlds, store S-LEX, retention ratio ``R``) must be >= 0.20, else the cell is void."""
    def gated(policy: str) -> Callable[[Bundle], Any]:
        return lambda b: SY.GatedMemory(SY.BM25Time(b.cfg.start_date), policy, R, b.seed,
                                        need=evidence_oids(b.queries))
    vals = {p: _complete_macro(bundles, gated(p), budget) for p in (*competitors, "GO")}
    best = max(vals[p] for p in competitors)
    h = vals["GO"] - best
    ok = h >= h_min
    return GateResult("G-FEAS", ok, {"R": R, "H_cell": _q(h), "GO": _q(vals["GO"]),
                                     "best_competitor": max(competitors, key=lambda p: (vals[p], p)),
                                     "complete_at_C": {p: _q(v) for p, v in sorted(vals.items())}},
                      {"H_cell_min": h_min}, "" if ok else "cell void: no headroom", len(bundles))


# ----------------------------------------------------------------------------------- G-LEAK


def g_leak(bundles: Sequence[Bundle], *, n_canaries: int = 8, n_sample: int = 6, budget: int | None = None,
           systems: dict[str, Callable[[Bundle], Any]] | None = None, band: tuple[float, float] = (0.45, 0.55),
           check_channel: bool = True) -> GateResult:
    """No lookahead and no state leakage, and no need information in the channel.

    1. CANARIES: ``n_canaries`` records are placed after the last query time; every system is fed ALL records
       at once and asked every sampled query, and no delivered context item may be younger than the question.
    2. REPLAY: the online replay equals the snapshot replay (a fresh system fed only the records before the
       question), asked in reversed order too, and asking a question twice gives the same answer.
    3. CHANNEL: at the null cell, the channel of the bundle (TRUE if none) predicts evidence status no better
       than chance: the mean reading at the host lines of each target vs the readings of all lines have an
       AUC in [0.45, 0.55] (the LEAKY channel fires it)."""
    from corpus.lifesim.channel import make_channel
    from corpus.lifesim.schema import Record

    problems: dict[str, Any] = {}
    sysd = systems or {
        "B2t": lambda b: SY.BM25Time(b.cfg.start_date),
        "B2": lambda b: SY.BM25(),
        "B1": lambda b: SY.Recency(),
        "random": lambda b: SY.RandomK(b.seed),
        "C2": lambda b: SY.HybridStore(SY.hashing_embedder(32), b.cfg.start_date),
        "GU": lambda b: SY.GatedMemory(SY.BM25Time(b.cfg.start_date), "GU", 0.25, b.seed),
    }
    ch_aucs: list[tuple[list, list]] = []
    for bi, b in enumerate(bundles):
        c_words = b.cfg.context_words if budget is None else budget
        recs = records_from_world(b.world, b.obs, channel=b.world.channel)
        last_q = max((x.t_ask for x in b.queries), default=0)
        canaries = [Record(id="zz%03d" % k, text="canary zzcanary%d zzmarker lookahead probe" % k,
                           timestamp=last_q + 1 + k, channel="note") for k in range(n_canaries)]
        qs = b.queries[:: max(1, len(b.queries) // max(1, n_sample))][:n_sample]
        for name, make in sysd.items():
            # 1. canaries: everything is ingested first, then asked
            m = make(b)
            if not isinstance(m, SY.GatedMemory):  # a gate is online by construction: nothing to ingest early
                m.reset(b.world.card)
                m.ingest(sorted(recs + canaries, key=lambda r: r.timestamp))
                for x in qs:
                    if m.needs_query:
                        m.bind(x)
                    a = m.query(x.text, x.t_ask, c_words)
                    late = [c.oid for c in a.context if c.timestamp >= x.t_ask]
                    if late:
                        problems.setdefault("lookahead", []).append((name, x.qid, late[:2]))
            # 2. replay equalities
            forward = {x.qid: a for x, a in run_stream(make(b), recs, b.queries, c_words, card=b.world.card)}
            for x in reversed(qs):
                m = make(b)
                m.reset(b.world.card)
                m.ingest([r for r in sorted(recs, key=lambda r: r.timestamp) if r.timestamp < x.t_ask])
                snap = m.query(x.text, x.t_ask, c_words)
                if snap.to_json() != forward[x.qid].to_json():
                    problems.setdefault("snapshot_differs", []).append((name, x.qid))
                again = m.query(x.text, x.t_ask, c_words)
                if again.to_json() != snap.to_json():
                    problems.setdefault("query_mutates", []).append((name, x.qid))
        # 3. channel
        if check_channel and is_null_cell(b.cell):
            w = b.world
            chn = w.channel or make_channel(w, "TRUE", b.cfg.reliability_primary, None, b.seed)
            spec_of = {s.oid: s for s in w.obs_specs}
            all_h = [chn.value(o.oid) for o in b.obs]
            tgt = []
            for x in b.queries:
                if x.family == "ME1" or not x.evidence_oids:
                    continue
                lines = [o for o in x.evidence_oids if spec_of[o].frame not in ("retell", "recall")] or list(x.evidence_oids)
                hs = [chn.value(o) for o in lines if chn.value(o) is not None]
                if hs:
                    tgt.append(_mean(hs))
            ch_aucs.append((tgt, [h for h in all_h if h is not None]))
    if ch_aucs:
        pos = [h for p, _ in ch_aucs for h in p]
        neg = [h for _, n in ch_aucs for h in n]
        au = auc(pos, neg)
        if not _in_band(au, band[0], band[1], _auc_se(len(pos), len(neg))):
            problems["channel_predicts_need"] = _q(au)
    else:
        au = None
    ok = not problems
    return GateResult("G-LEAK", ok, {"problems": {k: v[:3] if isinstance(v, list) else v for k, v in problems.items()},
                                     "channel_auc": None if au is None else _q(au), "systems": sorted(sysd)},
                      {"channel_auc": list(band)}, "" if ok else "; ".join(sorted(problems)), len(bundles))


# ------------------------------------------------------------------------------------- all


def x0_gates(bundles: Sequence[Bundle], *, include: Sequence[str] | None = None, R: float = 0.25,
             tell: bool = True, adversarial: Sequence[tuple[Query, str, bool]] | None = None) -> dict[str, GateResult]:
    """Run the gates on a list of bundles that share a tier and a coupling cell. Returns name -> GateResult.
    G-DET and G-INV use the first bundle's seed and config. G-TELL is skipped with ``tell=False``."""
    b0 = bundles[0]
    fns: dict[str, Callable[[], GateResult]] = {
        "G-DET": lambda: g_det(b0.seed, b0.cfg),
        "G-INV": lambda: g_inv(b0),
        "G-SOLVE": lambda: g_solve(bundles),
        "G-SCORE": lambda: g_score(bundles, adversarial=adversarial),
        "G-HOST": lambda: g_host(bundles),
        "G-SUPPORT": lambda: g_support(bundles),
        "G-ARO": lambda: g_aro(bundles),
        "G-LEN": lambda: g_len(bundles),
        "G-AFF": lambda: g_aff(bundles),
        "G-POS": lambda: g_pos(bundles),
        "G-TELL": lambda: g_tell(bundles),
        "G-BLIND": lambda: g_blind(bundles),
        "G-ORACLE": lambda: g_oracle(bundles),
        "G-DEPTH": lambda: g_depth(bundles),
        "G-FEAS": lambda: g_feas(bundles, R),
        "G-LEAK": lambda: g_leak(bundles),
    }
    names = list(include) if include is not None else [n for n in GATE_NAMES if tell or n != "G-TELL"]
    return {n: fns[n]() for n in names}
