"""wmb.retrieval_bench_ref: the independent reference implementation of the WMB-R1 P1 readings, on synthetic data only.

Hand-made examples with worked answers, the resample stream pinned to scripts/analyze_writer_memory_sim.bootstrap_indices, every verdict branch, the
stability, prevalence and label-stability rules, the fusion flag, the ceil(round(q * n, 9)) rule on awkward values, -inf scores, ties by task number and
then by position in the resample, and a naive sort-based oracle (written in this file, driven by the ORIGINAL bootstrap stream) that p1_readings must equal
on random inputs. No model, network or file outside the repository is used.
"""

from __future__ import annotations

import copy
import json
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "wmb"))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_writer_memory_sim as aw  # noqa: E402
import retrieval_bench_ref as ref  # noqa: E402

NEG_INF = float("-inf")
EMB, LEX, HYB, BM25 = "EMB_MINILM", "LEX_KERNEL", "HYB_KERNEL", "LEX_BM25"
HELPS, SUFFICIENT, UNRESOLVED = "EMBEDDER_HELPS_GATE", "LEXICAL_SUFFICIENT_FOR_GATE", "UNRESOLVED"
BOUNDARY, BY_LABELS, NOT_EVALUABLE = "UNRESOLVED (resampling boundary)", "UNRESOLVED (labels)", "NOT_EVALUABLE (prevalence)"
CONFIG = ROOT / "data" / "lab" / "wmb-r1-retrieval" / "config.json"


# ---------------------------------------------------------------- builders

def make_cfg(draws=40, margin=6, min_same=25, seed=20261102, stability=(20271102, 20271103, 20271104), sweep=(0.1, 0.2, 0.3)):
    return {"readings": {"sweep": list(sweep), "primary_q": 0.2, "margin_tasks": margin,
                         "bootstrap": {"seed": seed, "stability_seeds": list(stability), "draws_primary": draws, "draws_other": draws, "alpha": 0.05}},
            "judge": {"prevalence_rule_min_tasks_with_same": min_same}}


def random_case(seed, T=30, n_days=10, levels=0, ninf=0.1, labelled=0.8, p_same=0.35, methods=(EMB, LEX, HYB, BM25)):
    """Random scores (optionally quantised to `levels` values so that ties are common), task numbers that are NOT in position order, day names that
    do not appear in sorted order, and labels on a share of the first candidates. Only random.Random.random() is used: its stream never changes."""
    rng = random.Random(seed)
    order = sorted(range(T), key=lambda p: rng.random())
    tasks = [100 + rank for rank in order]
    days = ["d%02d" % int(rng.random() * n_days) for _ in range(T)]
    scores, first = {}, {}
    for name in methods:
        s, f = [], []
        for _ in range(T):
            gone, value, note = rng.random(), rng.random(), rng.random()
            if gone < ninf:
                s.append(NEG_INF)
                f.append(-1)
            else:
                s.append(round(value * levels) / levels if levels else value)
                f.append(int(note * 50))
        scores[name], first[name] = s, f
    labels = {}
    for name in methods:
        for p in range(T):
            if first[name][p] >= 0 and rng.random() < labelled:
                r = rng.random()
                labels[(tasks[p], first[name][p])] = "SAME" if r < p_same else ("RELATED" if r < p_same + 0.3 else "UNRELATED")
    return scores, first, days, tasks, labels


def uniform_case(T=30, per_day=3, emb_same=False, lex_same=False, hyb_same=(), hyb_all=False):
    """All three methods share one strictly decreasing score, so every fire set (in every resample) is the best-placed slots and the three methods differ
    only in their first candidates' relevance. Days hold `per_day` tasks each, so every day-block resample has T tasks too and m = ceil(0.2 * T) = 6
    (T = 30): then D* is the same number in every resample and the intervals are known without simulation."""
    tasks = list(range(200, 200 + T))
    days = ["d%02d" % (p // per_day) for p in range(T)]
    base = [1.0 - p / T for p in range(T)]
    scores = {name: list(base) for name in (EMB, LEX, HYB)}
    first = {EMB: [1] * T, LEX: [2] * T, HYB: [3] * T}
    labels = {}
    for p in range(T):
        if emb_same:
            labels[(tasks[p], 1)] = "SAME"
        if lex_same:
            labels[(tasks[p], 2)] = "SAME"
        if hyb_all or p in hyb_same:
            labels[(tasks[p], 3)] = "SAME"
    return scores, first, days, tasks, labels


def hand_case():
    """Ten tasks 100..109, four methods; the answers in test_hits_table_by_hand are worked out on paper."""
    tasks = list(range(100, 110))
    days = ["a", "a", "b", "b", "c", "c", "d", "d", "e", "e"]
    lex = [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6, 0.5, 0.0]
    scores = {EMB: [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0],
              LEX: lex,
              HYB: [0.9, 0.9, 0.5, 0.5, 0.5, 0.1, 0.1, NEG_INF, NEG_INF, NEG_INF],
              BM25: list(lex)}
    first = {EMB: [1] * 10, LEX: [2] * 10, HYB: [3] * 10, BM25: [4] * 10}
    labels = {}
    for task in (100, 102, 103):
        labels[(task, 1)] = "SAME"
    for task in (101, 105, 108):
        labels[(task, 2)] = "SAME"
    for task in (100, 101, 103):
        labels[(task, 3)] = "SAME"
    labels[(101, 1)] = "RELATED"      # lenient relevance only: not a hit
    labels[(103, 2)] = "RELATED"
    labels[(102, 3)] = "UNRELATED"
    labels[(104, 1)] = None           # no valid label: not relevant
    return scores, first, days, tasks, labels


# ---------------------------------------------------------------- the naive oracle (sort-based, original bootstrap stream)

def oracle_hits(method_scores, method_first, tasks, labels, slots, q):
    n = len(slots)
    m = math.ceil(round(q * n, 9))
    order = sorted(range(n), key=lambda k: (-method_scores[slots[k]], tasks[slots[k]], k))
    fired = [k for k in order if method_scores[slots[k]] != NEG_INF][:m]
    return sum(1 for k in fired if labels.get((tasks[slots[k]], method_first[slots[k]])) == "SAME")


def oracle_resamples(days, T, scheme, draws, seed, day_order="sorted"):
    if scheme == "task":
        return [list(picks) for picks in aw.bootstrap_indices(T, draws, seed)]
    names = sorted(set(days)) if day_order == "sorted" else list(dict.fromkeys(days))        # the distinct days, numbered in this order, are the blocks
    members = [[p for p in range(T) if days[p] == name] for name in names]
    return [[p for d in picks for p in members[d]] for picks in aw.bootstrap_indices(len(names), draws, seed)]


def oracle_hits_table(scores, first, tasks, labels, sweep):
    out = {}
    T = len(tasks)
    for name in scores:
        out[name] = {}
        for q in sweep:
            m = math.ceil(round(q * T, 9))
            order = sorted(range(T), key=lambda p: (-scores[name][p], tasks[p], p))
            fired = [p for p in order if scores[name][p] != NEG_INF][:m]
            h = sum(1 for p in fired if labels.get((tasks[p], first[name][p])) == "SAME")
            out[name][str(q)] = {"hits": h, "false_injections": len(fired) - h}
    return out


def oracle_verdict(d, lo, hi, hi_hyb, margin):
    if lo > 0 and d >= margin:
        return HELPS
    if hi < margin and hi_hyb < margin:
        return SUFFICIENT
    return UNRESOLVED


def oracle_p1(scores, first, days, tasks, labels, cfg, assistant_labels=None, draws=None, day_order="sorted"):
    rd = cfg["readings"]
    boot = rd["bootstrap"]
    n_draws = boot["draws_primary"] if draws is None else draws
    q, margin = rd["primary_q"], rd["margin_tasks"]
    seeds = [boot["seed"]] + list(boot["stability_seeds"])
    T = len(tasks)
    contrasts = [(EMB, LEX), (HYB, LEX)]
    low_index, high_index = math.floor(0.025 * n_draws), math.ceil(0.975 * n_draws) - 1

    def evaluate(lab):
        full = list(range(T))
        d = [oracle_hits(scores[a], first[a], tasks, lab, full, q) - oracle_hits(scores[b], first[b], tasks, lab, full, q) for a, b in contrasts]
        per_seed = {}
        for seed in seeds:
            ends = []
            for a, b in contrasts:
                got = {}
                for scheme in ("task", "day"):
                    vals = sorted(oracle_hits(scores[a], first[a], tasks, lab, s, q) - oracle_hits(scores[b], first[b], tasks, lab, s, q)
                                  for s in oracle_resamples(days, T, scheme, n_draws, seed, day_order))
                    got[scheme] = (vals[low_index], vals[high_index])
                ends.append(got)
            per_seed[seed] = ends
        by_seed = {}
        for seed in seeds:
            lo = min(per_seed[seed][0]["task"][0], per_seed[seed][0]["day"][0])
            hi = max(per_seed[seed][0]["task"][1], per_seed[seed][0]["day"][1])
            hi_hyb = max(per_seed[seed][1]["task"][1], per_seed[seed][1]["day"][1])
            by_seed[str(seed)] = oracle_verdict(d[0], lo, hi, hi_hyb, margin)
        same = len({i for (i, j), label in lab.items() if label == "SAME"})
        ok = same >= cfg["judge"]["prevalence_rule_min_tasks_with_same"]
        if not ok:
            verdict = NOT_EVALUABLE
        elif len(set(by_seed.values())) == 1:
            verdict = by_seed[str(seeds[0])]
        else:
            verdict = BOUNDARY
        return {"d": d, "per_seed": per_seed, "by_seed": by_seed, "same": same, "ok": ok, "verdict": verdict}

    judge = evaluate(labels)
    primary = judge["per_seed"][seeds[0]]

    def block(c):
        task_lo, task_hi = primary[c]["task"]
        day_lo, day_hi = primary[c]["day"]
        return {"d": judge["d"][c], "lo": min(task_lo, day_lo), "hi": max(task_hi, day_hi), "task_lo": task_lo, "task_hi": task_hi,
                "day_lo": day_lo, "day_hi": day_hi}

    verdict_assistant = None
    if assistant_labels is not None:
        merged = dict(labels)
        merged.update(assistant_labels)
        verdict_assistant = evaluate(merged)["verdict"]
    verdict = judge["verdict"]
    if assistant_labels is not None and verdict_assistant != verdict and verdict in (HELPS, SUFFICIENT, UNRESOLVED):
        verdict = BY_LABELS
    d_emb, d_hyb = block(0), block(1)
    return {"tasks_with_same": judge["same"], "prevalence_ok": judge["ok"], "hits": oracle_hits_table(scores, first, tasks, labels, rd["sweep"]),
            "d_emb": d_emb, "d_hyb": d_hyb, "verdict_by_seed": judge["by_seed"], "verdict_judge": judge["verdict"], "verdict_assistant": verdict_assistant,
            "verdict": verdict, "fusion_flag": "refit_channel_weights" if verdict == HELPS and d_hyb["d"] < d_emb["d"] / 2 else None}


def flip_some(labels, tasks, seed, share=0.4):
    """An 'assistant' label set: a share of the judged pairs relabelled SAME <-> UNRELATED, plus a few pairs the judge never saw."""
    rng = random.Random(seed)
    out = {}
    for pair, label in sorted(labels.items()):
        if rng.random() < share:
            out[pair] = "UNRELATED" if label == "SAME" else "SAME"
    for task in tasks[:3]:
        out[(task, 777)] = "SAME"
    return out


# ---------------------------------------------------------------- the resample stream

@pytest.mark.parametrize("n", [1, 2, 3, 7, 20, 63, 214, 215])
@pytest.mark.parametrize("seed", [20261102, 20271102, 20271103, 20271104, 0, 1, (1 << 64) - 1, 12345678901234567890])
def test_stream_equals_the_original_splitmix_bootstrap(n, seed):
    expected = aw.bootstrap_indices(n, 9, seed)
    assert ref.bootstrap_indices(n, 9, seed) == expected
    assert ref.bootstrap_indices_py(n, 9, seed) == expected


def test_stream_is_one_continuous_sequence_and_independent_of_chunking():
    n, draws, seed = 214, 40, 20261102
    outputs = ref.splitmix64_outputs_py(seed, 2 * n)
    rows = ref.bootstrap_indices(n, draws, seed)
    assert rows[0] == [z % n for z in outputs[:n]]
    assert rows[1] == [z % n for z in outputs[n:2 * n]]           # draw 1 starts where draw 0 ended; the stream is not restarted
    assert list(ref.iter_bootstrap_rows(n, draws, seed, chunk_values=1000)) == rows == aw.bootstrap_indices(n, draws, seed)
    assert list(ref.iter_bootstrap_rows(n, draws, seed, chunk_values=1)) == rows        # one row per chunk
    assert ref.bootstrap_indices(5, 0, seed) == []
    with pytest.raises(ValueError):
        ref.bootstrap_indices(0, 3, seed)


# ---------------------------------------------------------------- the cut: ceil(round(q * n, 9))

def test_fire_count_on_the_readme_sizes_and_awkward_values():
    assert [ref.fire_count(q, 214) for q in (0.1, 0.2, 0.3)] == [22, 43, 65]       # the README's 22, 43 and 65 tasks
    assert [ref.fire_count(0.2, n) for n in (214, 215, 216)] == [43, 43, 44]        # 42.8 -> 43, exactly 43.0 -> 43, 43.2 -> 44
    assert ref.fire_count(0.2, 0) == 0 and ref.fire_count(0.2, 1) == 1
    assert math.ceil(0.07 * 100) == 8 and ref.fire_count(0.07, 100) == 7            # 7.000000000000001 must not become 8
    assert math.ceil(0.14 * 50) == 8 and ref.fire_count(0.14, 50) == 7
    assert ref.fire_count(0.35, 20) == 7 and ref.fire_count(0.15, 20) == 3


def test_fire_count_equals_exact_decimal_arithmetic_on_a_grid():
    for k in range(1, 100):
        q = k / 100
        exact = Fraction(str(q))
        for n in range(1, 401):
            assert ref.fire_count(q, n) == math.ceil(exact * n), (q, n)
    for q in (0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4):                                 # the D_bar grid
        for n in range(1, 700):
            assert ref.fire_count(q, n) == math.ceil(Fraction(str(q)) * n), (q, n)


# ---------------------------------------------------------------- the fire set, by hand

def test_fire_set_full_sample_by_hand_ties_by_task_number_and_minus_inf():
    #          p0   p1   p2   p3       p4   p5
    scores = [0.5, 0.9, 0.9, NEG_INF, 0.5, 0.1]
    tasks = [30, 20, 10, 40, 5, 50]
    # best first: 0.9 -> task 10 (p2), task 20 (p1); 0.5 -> task 5 (p4), task 30 (p0) although p0 comes first; 0.1 -> p5; p3 (-inf) never fires
    assert ref.fire_set_full(scores, tasks, 0.1) == [2]                  # m = ceil(0.6) = 1
    assert ref.fire_set_full(scores, tasks, 0.2) == [2, 1]               # m = ceil(1.2) = 2
    assert ref.fire_set_full(scores, tasks, 0.5) == [2, 1, 4]            # m = 3: the 0.5 tie goes to task 5
    assert ref.fire_set_full(scores, tasks, 0.6) == [2, 1, 4, 0]         # m = ceil(3.6) = 4
    assert ref.fire_set_full(scores, tasks, 1.0) == [2, 1, 4, 0, 5]      # m = 6 but only five tasks have a candidate: five fire
    assert ref.fire_set_full([NEG_INF] * 3, [1, 2, 3], 0.5) == []        # nobody has a candidate


def test_fire_set_resample_ties_by_task_number_then_position_and_copies_are_split():
    scores = [0.9, 0.9, 0.2]
    tasks = [7, 5, 6]
    slots = [1, 0, 1, 2]       # the resample: position 0 -> p1 (task 5), 1 -> p0 (task 7), 2 -> p1 (task 5), 3 -> p2 (task 6)
    # best first: (task 5, position 0), (task 5, position 2), (task 7, position 1), (task 6, position 3)
    assert ref.fire_set(scores, tasks, slots, 0.25) == [0]               # m = 1: ONE of the two copies of task 5 fires (the earlier position)
    assert ref.fire_set(scores, tasks, slots, 0.5) == [0, 2]             # m = 2: both copies
    assert ref.fire_set(scores, tasks, slots, 0.75) == [0, 2, 1]
    assert ref.fire_set(scores, tasks, slots, 1.0) == [0, 2, 1, 3]
    # the same resample as copies per task position, in the counting form used by the bootstrap loop
    order = ref.firing_order(scores, tasks)
    assert order == [1, 0, 2]
    counts = [1, 2, 1]
    assert ref.fired_copies(order, counts, 1) == [(1, 1)]
    assert ref.fired_copies(order, counts, 2) == [(1, 2)]
    assert ref.fired_copies(order, counts, 3) == [(1, 2), (0, 1)]
    assert ref.fired_copies(order, counts, 4) == [(1, 2), (0, 1), (2, 1)]
    assert ref.fired_copies(order, counts, 9) == [(1, 2), (0, 1), (2, 1)]
    assert ref.fired_copies(order, counts, 0) == []


def test_minus_inf_never_fires_in_a_resample_and_fewer_than_m_may_fire():
    scores = [0.3, NEG_INF]
    tasks = [1, 2]
    slots = [1, 1, 1, 0]                                                  # n = 4, q = 0.5 -> m = 2, but only one slot has a candidate
    assert ref.fire_set(scores, tasks, slots, 0.5) == [3]
    assert ref.fire_set(scores, tasks, [1, 1], 1.0) == []
    assert ref.firing_order(scores, tasks) == [0]
    assert ref.fired_copies([0], [1, 3], 2) == [(0, 1)]


def test_counting_engine_equals_the_literal_rule_on_random_resamples():
    rng = random.Random(11)
    for trial in range(120):
        T = rng.randrange(1, 35)
        scores_all, first, days, tasks, labels = random_case(1000 + trial, T=T, n_days=max(2, T // 3), levels=rng.choice([0, 3, 5]),
                                                           ninf=rng.choice([0.0, 0.2, 0.9, 1.0]))
        rel_sets = [{name: ref.relevance_vector(labels, tasks, first[name]) for name in scores_all}]
        orders = {name: ref.firing_order(scores_all[name], tasks) for name in scores_all}
        q = rng.choice([0.1, 0.2, 0.3, 0.5, 0.9, 1.0])
        names = sorted(set(days))
        schemes = {"task": ([[p] for p in range(T)], ref.bootstrap_indices(T, 15, rng.randrange(1 << 30))),
                   "day": ([[p for p in range(T) if days[p] == name] for name in names],
                           ref.bootstrap_indices(len(names), 15, rng.randrange(1 << 30)))}
        for blocks, rows in schemes.values():
            got = ref.bootstrap_differences(rows, blocks, T, q, orders, rel_sets)
            for r, picks in enumerate(rows):
                slots = [p for b in picks for p in blocks[b]]
                for c, (a, b) in enumerate(ref.CONTRASTS):
                    ha = sum(rel_sets[0][a][slots[k]] for k in ref.fire_set(scores_all[a], tasks, slots, q))
                    hb = sum(rel_sets[0][b][slots[k]] for k in ref.fire_set(scores_all[b], tasks, slots, q))
                    assert got[0][c][r] == ha - hb


def test_day_block_resample_keeps_a_days_tasks_together_and_cuts_at_the_resampled_size():
    # days: A = {p0, p1}, B = {p2}; EMB fires p0, p1, p2 in that order, LEX fires p2, p1, p0; q = 0.5
    scores = {EMB: [0.9, 0.8, 0.7], LEX: [0.1, 0.2, 0.9], HYB: [0.9, 0.8, 0.7]}
    tasks = [1, 2, 3]
    rel = {EMB: [1, 1, 0], LEX: [0, 0, 1], HYB: [0, 0, 0]}
    orders = {name: ref.firing_order(scores[name], tasks) for name in scores}
    blocks = [[0, 1], [2]]
    # picks [A, A]: 4 tasks, m = 2: EMB fires p0 twice (2 hits); LEX: p2 absent, p1 twice (0 hits)         -> D* = 2
    # picks [B, B]: 2 tasks, m = 1: EMB fires one p2 (0 hits); LEX fires one p2 (1 hit)                      -> D* = -1
    # picks [A, B]: 3 tasks, m = ceil(1.5) = 2: EMB fires p0, p1 (2 hits); LEX fires p2 (1 hit), p1 (0 hits) -> D* = 1
    got = ref.bootstrap_differences([[0, 0], [1, 1], [0, 1]], blocks, 3, 0.5, orders, [rel])
    assert got[0][0] == [2, -1, 1]


# ---------------------------------------------------------------- hits, by hand

def test_hits_table_by_hand_strict_relevance_only():
    scores, first, days, tasks, labels = hand_case()
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=20, min_same=5), draws=20)
    # fire sets (T = 10, m = 1, 2, 3): EMB {100}, {100,101}, {100,101,102}; LEX {101}, {101,103}, {101,103,105};
    # HYB {100}, {100,101}, {100,101,102} (the 0.9 tie by task number, then the 0.5 tie 102/103/104 by task number); BM25 as LEX
    expected = {EMB: {"0.1": (1, 0), "0.2": (1, 1), "0.3": (2, 1)},        # 101 is RELATED for EMB: a false injection
                LEX: {"0.1": (1, 0), "0.2": (1, 1), "0.3": (2, 1)},        # 103 is RELATED for LEX: a false injection
                HYB: {"0.1": (1, 0), "0.2": (2, 0), "0.3": (2, 1)},        # 102 is UNRELATED for HYB
                BM25: {"0.1": (0, 1), "0.2": (0, 2), "0.3": (0, 3)}}       # nothing labelled SAME
    assert result["hits"] == {name: {key: {"hits": h, "false_injections": f} for key, (h, f) in row.items()} for name, row in expected.items()}
    assert result["d_emb"]["d"] == 1 - 1 and result["d_hyb"]["d"] == 2 - 1
    assert result["tasks_with_same"] == 6                                   # tasks 100, 101, 102, 103, 105, 108
    assert result["prevalence_ok"] is True
    assert ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=20, min_same=7), draws=20)["prevalence_ok"] is False


def test_output_keys_and_types_are_exactly_the_documented_ones():
    scores, first, days, tasks, labels = hand_case()
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=20, min_same=5), draws=20)
    assert set(result) == {"tasks_with_same", "prevalence_ok", "hits", "d_emb", "d_hyb", "verdict_by_seed", "verdict_judge", "verdict_assistant", "verdict",
                           "fusion_flag"}
    for block in (result["d_emb"], result["d_hyb"]):
        assert set(block) == {"d", "lo", "hi", "task_lo", "task_hi", "day_lo", "day_hi"}
        assert isinstance(block["d"], int) and all(isinstance(block[k], float) for k in block if k != "d")
    assert list(result["verdict_by_seed"]) == ["20261102", "20271102", "20271103", "20271104"]
    assert result["verdict_assistant"] is None
    assert set(result["hits"]) == {EMB, LEX, HYB, BM25} and set(result["hits"][EMB]) == {"0.1", "0.2", "0.3"}


def test_inputs_are_not_modified_and_bad_inputs_are_refused():
    scores, first, days, tasks, labels = hand_case()
    snapshot = copy.deepcopy((scores, first, days, tasks, labels))
    assistant = {(100, 1): "UNRELATED"}
    ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=10, min_same=5), assistant_labels=assistant, draws=10)
    assert (scores, first, days, tasks, labels) == snapshot and assistant == {(100, 1): "UNRELATED"}
    cfg = make_cfg(draws=10, min_same=5)
    with pytest.raises(ValueError):
        ref.p1_readings(scores, first, days, [100] * 10, labels, cfg)                      # task numbers must be distinct
    with pytest.raises(ValueError):
        ref.p1_readings(scores, first, days[:-1], tasks, labels, cfg)                      # one day per task
    with pytest.raises(ValueError):
        ref.p1_readings({EMB: scores[EMB], LEX: scores[LEX]}, first, days, tasks, labels, cfg)       # HYB_KERNEL missing
    bad = copy.deepcopy(scores)
    bad[EMB][3] = float("nan")
    with pytest.raises(ValueError):
        ref.p1_readings(bad, first, days, tasks, labels, cfg)


# ---------------------------------------------------------------- the interval

def test_percentile_interval_uses_floor_and_ceil_order_statistics():
    cases = {100000: (2500, 97499), 10000: (250, 9749), 1000: (25, 974), 100: (2, 97), 60: (1, 58), 40: (1, 38), 7: (0, 6), 1: (0, 0)}
    for draws, (low, high) in cases.items():
        values = list(range(draws))
        random.Random(draws).shuffle(values)
        assert ref.percentile_interval(values) == (low, high), draws
        assert (low, high) == (math.floor(0.025 * draws), math.ceil(0.975 * draws) - 1)
    with pytest.raises(ValueError):
        ref.percentile_interval([])
    assert ref.percentile_interval(list(range(200)), alpha=0.1) == (10, 189)      # alpha is honoured: floor(0.05 * 200), ceil(0.95 * 200) - 1


# ---------------------------------------------------------------- p1_readings against the naive oracle

@pytest.mark.parametrize("case", range(14))
def test_p1_readings_equals_the_naive_oracle_on_random_inputs(case):
    rng = random.Random(500 + case)
    T = rng.randrange(14, 46)
    scores, first, days, tasks, labels = random_case(300 + case, T=T, n_days=rng.randrange(3, 16), levels=rng.choice([0, 4]),
                                                     ninf=rng.choice([0.0, 0.15, 0.5]), p_same=rng.choice([0.2, 0.5]))
    cfg = make_cfg(draws=rng.choice([25, 40, 60]), margin=rng.choice([1, 2, 3, 6]), min_same=rng.choice([1, 5, 25]), seed=rng.randrange(1, 1 << 40),
                   stability=[rng.randrange(1, 1 << 40) for _ in range(3)])
    assistant = flip_some(labels, tasks, 900 + case) if case % 2 else None
    got = ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=assistant)
    assert got == oracle_p1(scores, first, days, tasks, labels, cfg, assistant_labels=assistant)


def test_p1_readings_at_the_real_dimensions_and_config():
    if not CONFIG.exists():
        pytest.skip("config.json not present")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    scores, first, days, tasks, labels = random_case(77, T=214, n_days=63, levels=0, ninf=0.0, labelled=0.9, p_same=0.3)
    assistant = flip_some(labels, tasks, 78, share=0.1)
    got = ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=assistant, draws=30)
    assert got == oracle_p1(scores, first, days, tasks, labels, cfg, assistant_labels=assistant, draws=30)
    assert list(got["verdict_by_seed"]) == ["20261102", "20271102", "20271103", "20271104"]
    assert set(got["hits"][EMB]) == {"0.1", "0.2", "0.3"}


def test_the_interval_used_is_the_wider_of_task_and_day_block_at_each_end():
    seen_task_wider = seen_day_wider = False
    for case in range(25):
        scores, first, days, tasks, labels = random_case(40 + case, T=36, n_days=9)
        for key in ("d_emb", "d_hyb"):
            block = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=50, min_same=1), draws=50)[key]
            assert block["lo"] == min(block["task_lo"], block["day_lo"]) and block["hi"] == max(block["task_hi"], block["day_hi"])
            seen_task_wider |= block["task_hi"] > block["day_hi"] or block["task_lo"] < block["day_lo"]
            seen_day_wider |= block["day_hi"] > block["task_hi"] or block["day_lo"] < block["task_lo"]
    assert seen_task_wider and seen_day_wider               # the test data exercise both directions


def test_day_numbering_switch_sorted_or_first_seen(monkeypatch):
    # on the real data the tasks are listed by date, so both numberings agree; on arbitrarily ordered days they number the blocks differently
    scores, first, days, tasks, labels = random_case(8, T=36, n_days=9)
    order = sorted(range(36), key=lambda p: days[p])
    scores_s = {name: [v[p] for p in order] for name, v in scores.items()}
    first_s = {name: [v[p] for p in order] for name, v in first.items()}
    days_s, tasks_s = [days[p] for p in order], [tasks[p] for p in order]
    cfg = make_cfg(draws=40, min_same=1)
    by_sorted = ref.p1_readings(scores_s, first_s, days_s, tasks_s, labels, cfg)
    monkeypatch.setattr(ref, "DAY_ORDER", "first_seen")
    assert ref.p1_readings(scores_s, first_s, days_s, tasks_s, labels, cfg) == by_sorted
    assert ref.day_block_structure(days_s, "sorted") == ref.day_block_structure(days_s, "first_seen")
    differs = False
    for case in range(12):
        scores, first, days, tasks, labels = random_case(60 + case, T=36, n_days=9)
        monkeypatch.setattr(ref, "DAY_ORDER", "first_seen")
        first_seen = ref.p1_readings(scores, first, days, tasks, labels, cfg)
        assert first_seen == oracle_p1(scores, first, days, tasks, labels, cfg, day_order="first_seen")
        monkeypatch.setattr(ref, "DAY_ORDER", "sorted")
        sorted_reading = ref.p1_readings(scores, first, days, tasks, labels, cfg)
        assert sorted_reading == oracle_p1(scores, first, days, tasks, labels, cfg, day_order="sorted")
        differs |= (first_seen["d_emb"], first_seen["d_hyb"]) != (sorted_reading["d_emb"], sorted_reading["d_hyb"])
    assert differs                                             # the choice is not cosmetic on unordered days
    with pytest.raises(ValueError):
        ref.day_block_structure(["a"], "alphabetical")


def test_assistant_prevalence_switch(monkeypatch):
    scores, first, days, tasks, labels = uniform_case(emb_same=True)
    lab = {pair: "RELATED" for pair in labels}
    for task in tasks[:25]:
        lab[(task, 1)] = "SAME"
    cfg = make_cfg(draws=30, min_same=25)
    assistant = {(tasks[20], 1): "UNRELATED"}                  # 25 -> 24 tasks with a SAME note under the assistant's labels
    recompute = ref.p1_readings(scores, first, days, tasks, lab, cfg, assistant_labels=assistant)
    assert (recompute["verdict_assistant"], recompute["verdict"]) == (NOT_EVALUABLE, BY_LABELS)
    monkeypatch.setattr(ref, "ASSISTANT_PREVALENCE", "judge")
    inherited = ref.p1_readings(scores, first, days, tasks, lab, cfg, assistant_labels=assistant)
    assert inherited["verdict_assistant"] == HELPS and inherited["verdict"] == HELPS
    monkeypatch.setattr(ref, "ASSISTANT_PREVALENCE", "other")
    with pytest.raises(ValueError):
        ref.p1_readings(scores, first, days, tasks, lab, cfg, assistant_labels=assistant)


def test_alpha_of_the_config_sets_the_level_of_every_interval():
    scores, first, days, tasks, labels = random_case(31, T=40, n_days=12)
    wide, narrow = make_cfg(draws=200, min_same=1), make_cfg(draws=200, min_same=1)
    narrow["readings"]["bootstrap"]["alpha"] = 0.5                       # the central half: sorted(D*)[floor(0.25 * 200)] .. sorted(D*)[ceil(0.75 * 200) - 1]
    a, b = ref.p1_readings(scores, first, days, tasks, labels, wide), ref.p1_readings(scores, first, days, tasks, labels, narrow)
    strictly_narrower = False
    for key in ("d_emb", "d_hyb"):
        for end in ("task_lo", "day_lo"):
            assert b[key][end] >= a[key][end]
            strictly_narrower |= b[key][end] > a[key][end]
        for end in ("task_hi", "day_hi"):
            assert b[key][end] <= a[key][end]
            strictly_narrower |= b[key][end] < a[key][end]
    assert strictly_narrower
    # the same data through the building blocks: the task-bootstrap interval at alpha 0.5 is the (50, 149) order statistics of the 200 values
    rows = ref.bootstrap_indices(len(tasks), 200, narrow["readings"]["bootstrap"]["seed"])
    rel = {name: ref.relevance_vector(labels, tasks, first[name]) for name in (EMB, LEX, HYB)}
    orders = {name: ref.firing_order(scores[name], tasks) for name in rel}
    diffs = ref.bootstrap_differences(rows, [[p] for p in range(len(tasks))], len(tasks), 0.2, orders, [rel])[0][0]
    assert (b["d_emb"]["task_lo"], b["d_emb"]["task_hi"]) == (sorted(diffs)[50], sorted(diffs)[149])


def test_draws_overrides_the_config_and_defaults_to_draws_primary():
    scores, first, days, tasks, labels = random_case(5, T=30)
    cfg = make_cfg(draws=33, min_same=1)
    default = ref.p1_readings(scores, first, days, tasks, labels, cfg)
    assert default == ref.p1_readings(scores, first, days, tasks, labels, cfg, draws=33)
    assert default == oracle_p1(scores, first, days, tasks, labels, cfg, draws=33)
    other = ref.p1_readings(scores, first, days, tasks, labels, cfg, draws=57)
    assert other == oracle_p1(scores, first, days, tasks, labels, cfg, draws=57)
    cfg_other = make_cfg(draws=33, min_same=1)
    cfg_other["readings"]["bootstrap"]["draws_other"] = 5            # draws_other is not what the P1 intervals use
    assert ref.p1_readings(scores, first, days, tasks, labels, cfg_other) == default


# ---------------------------------------------------------------- the verdict branches

def test_base_verdict_boundaries():
    assert ref.base_verdict(6, 1, 9, 9, 6) == HELPS                 # lower bound above 0 and D >= margin
    assert ref.base_verdict(6, 0, 9, 9, 6) == UNRESOLVED            # lower bound 0 is not above 0
    assert ref.base_verdict(5, 1, 9, 9, 6) == UNRESOLVED            # D just below the margin
    assert ref.base_verdict(7, -3, 9, 9, 6) == UNRESOLVED
    assert ref.base_verdict(0, -4, 5, 5, 6) == SUFFICIENT           # both upper bounds below the margin
    assert ref.base_verdict(0, -4, 6, 5, 6) == UNRESOLVED           # D_emb upper bound equal to the margin is not below it
    assert ref.base_verdict(0, -4, 5, 6, 6) == UNRESOLVED           # D_hyb upper bound equal to the margin
    assert ref.base_verdict(0, -4, 5, 99, 6) == UNRESOLVED
    assert ref.base_verdict(8, 2, 3, 3, 6) == HELPS                 # tested first, as in the text (an interval that excludes its own estimate)


def test_each_verdict_branch_end_to_end_on_datasets_with_known_intervals():
    cfg = make_cfg(draws=30, margin=6, min_same=25)
    # EMB's first candidates are all SAME, LEX's none: every resample fires 6 slots, D* = 6 everywhere
    scores, first, days, tasks, labels = uniform_case(emb_same=True)
    helps = ref.p1_readings(scores, first, days, tasks, labels, cfg)
    assert helps["d_emb"] == {"d": 6, "lo": 6.0, "hi": 6.0, "task_lo": 6.0, "task_hi": 6.0, "day_lo": 6.0, "day_hi": 6.0}
    assert helps["d_hyb"] == {"d": 0, "lo": 0.0, "hi": 0.0, "task_lo": 0.0, "task_hi": 0.0, "day_lo": 0.0, "day_hi": 0.0}
    assert helps["verdict"] == helps["verdict_judge"] == HELPS
    assert set(helps["verdict_by_seed"].values()) == {HELPS}
    # the same data with the margin at 7: D_emb = 6 < 7 but its upper bound 6 is below 7 and so is D_hyb's: lexical suffices; margin 5: helps
    assert ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=30, margin=7))["verdict"] == SUFFICIENT
    assert ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=30, margin=5))["verdict"] == HELPS
    # both relevant everywhere: D_emb = 0 and D_hyb = -6 -> LEXICAL_SUFFICIENT_FOR_GATE
    scores, first, days, tasks, labels = uniform_case(emb_same=True, lex_same=True)
    sufficient = ref.p1_readings(scores, first, days, tasks, labels, cfg)
    assert (sufficient["d_emb"]["d"], sufficient["d_emb"]["hi"], sufficient["d_hyb"]["d"], sufficient["d_hyb"]["hi"]) == (0, 0.0, -6, -6.0)
    assert sufficient["verdict"] == SUFFICIENT and sufficient["fusion_flag"] is None
    # only the fusion channel gains 6: D_emb = 0 is not a help and D_hyb's upper bound 6 is not below the margin -> UNRESOLVED
    scores, first, days, tasks, labels = uniform_case(hyb_all=True)
    unresolved = ref.p1_readings(scores, first, days, tasks, labels, cfg)
    assert (unresolved["d_emb"]["d"], unresolved["d_hyb"]["d"], unresolved["d_hyb"]["hi"]) == (0, 6, 6.0)
    assert unresolved["verdict"] == UNRESOLVED and unresolved["fusion_flag"] is None


def test_identical_methods_give_a_zero_interval_and_lexical_sufficient():
    scores, first, days, tasks, labels = random_case(9, T=40)
    for name in (EMB, HYB):
        scores[name], first[name] = list(scores[LEX]), list(first[LEX])
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=50, min_same=1))
    for key in ("d_emb", "d_hyb"):
        assert result[key] == {"d": 0, "lo": 0.0, "hi": 0.0, "task_lo": 0.0, "task_hi": 0.0, "day_lo": 0.0, "day_hi": 0.0}
    assert result["verdict"] == SUFFICIENT


# ---------------------------------------------------------------- the stability rule

def test_combine_seed_verdicts():
    same = {"1": HELPS, "2": HELPS, "3": HELPS, "4": HELPS}
    assert ref.combine_seed_verdicts(same, "1", True) == HELPS
    assert ref.combine_seed_verdicts(dict(same, **{"4": UNRESOLVED}), "1", True) == BOUNDARY
    assert ref.combine_seed_verdicts({"1": UNRESOLVED, "2": SUFFICIENT, "3": SUFFICIENT, "4": SUFFICIENT}, "1", True) == BOUNDARY
    assert ref.combine_seed_verdicts(dict(same, **{"4": UNRESOLVED}), "1", False) == NOT_EVALUABLE      # prevalence overrides everything
    assert ref.combine_seed_verdicts(same, "1", False) == NOT_EVALUABLE


# found offline (a search over case seeds with this generator): with this data and 60 draws the primary seed alone says UNRESOLVED while each of the
# three stability seeds says EMBEDDER_HELPS_GATE (D_emb = 4 >= margin 2 and the lower bound is above 0 for those three)
STABILITY_CASE = dict(case_seed=253, T=40, n_days=14, margin=2, draws=60,
                      by_seed={"20261102": UNRESOLVED, "20271102": HELPS, "20271103": HELPS, "20271104": HELPS})


def stability_inputs():
    scores, first, days, tasks, labels = random_case(STABILITY_CASE["case_seed"], T=STABILITY_CASE["T"], n_days=STABILITY_CASE["n_days"])
    cfg = make_cfg(draws=STABILITY_CASE["draws"], margin=STABILITY_CASE["margin"], min_same=5)
    return scores, first, days, tasks, labels, cfg


def test_four_seeds_that_disagree_give_unresolved_resampling_boundary():
    scores, first, days, tasks, labels, cfg = stability_inputs()
    result = ref.p1_readings(scores, first, days, tasks, labels, cfg)
    assert len(set(result["verdict_by_seed"].values())) > 1
    assert result["verdict_by_seed"] == STABILITY_CASE["by_seed"]
    assert result["verdict_judge"] == result["verdict"] == BOUNDARY
    assert result["fusion_flag"] is None
    assert result == oracle_p1(scores, first, days, tasks, labels, cfg)
    # the primary seed alone would have said something else: the interval of the report is the primary seed's, the verdict is not
    assert result["verdict_by_seed"][str(cfg["readings"]["bootstrap"]["seed"])] != BOUNDARY


# ---------------------------------------------------------------- the prevalence rule

def test_prevalence_rule_counts_distinct_tasks_with_a_same_pair():
    scores, first, days, tasks, labels = uniform_case(emb_same=True)

    def with_same_tasks(count):
        lab = {pair: "RELATED" for pair in labels}
        for task in tasks[:count]:
            lab[(task, 1)] = "SAME"
        lab[(tasks[0], 99)] = "SAME"                       # a second SAME pair on the same task does not count twice
        return lab
    for count, ok in ((24, False), (25, True), (30, True)):
        lab = with_same_tasks(count)
        result = ref.p1_readings(scores, first, days, tasks, lab, make_cfg(draws=20, min_same=25))
        assert result["tasks_with_same"] == count and result["prevalence_ok"] is ok, count
        if ok:
            assert result["verdict_judge"] in (HELPS, SUFFICIENT, UNRESOLVED, BOUNDARY)
        else:
            assert result["verdict_judge"] == result["verdict"] == NOT_EVALUABLE
            assert result["fusion_flag"] is None
            assert set(result["verdict_by_seed"].values()) <= {HELPS, SUFFICIENT, UNRESOLVED}      # the per-seed readings are still reported
    assert ref.tasks_with_same({(1, 1): "SAME", (1, 2): "SAME", (2, 1): "RELATED", (3, 1): None, (4, 4): "SAME"}) == 2


# ---------------------------------------------------------------- the label-stability rule

def test_verdict_is_unresolved_labels_when_the_assistants_labels_change_a_base_verdict():
    cfg = make_cfg(draws=30, margin=6, min_same=20)           # 24 of 30 tasks keep a SAME note under the assistant's labels: prevalence is not under test here
    scores, first, days, tasks, labels = uniform_case(emb_same=True)
    # agreement: the assistant confirms some of EMB's pairs (and adds a pair the judge never saw)
    agree = {(tasks[0], 1): "SAME", (tasks[7], 1): "SAME", (tasks[0], 555): "RELATED"}
    result = ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=agree)
    assert result["verdict_judge"] == result["verdict_assistant"] == result["verdict"] == HELPS and result["fusion_flag"] == "refit_channel_weights"
    # disagreement: the assistant calls EMB's six fired first candidates RELATED -> D_emb = 0 under its labels
    disagree = {(tasks[p], 1): "RELATED" for p in range(6)}
    result = ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=disagree)
    assert result["verdict_judge"] == HELPS and result["verdict_assistant"] in (SUFFICIENT, UNRESOLVED)
    assert result["verdict"] == BY_LABELS and result["fusion_flag"] is None
    assert result["d_emb"]["d"] == 6 and result["hits"][EMB]["0.2"]["hits"] == 6          # d, hits and the judge's verdict keep the JUDGE's labels
    assert result == oracle_p1(scores, first, days, tasks, labels, cfg, assistant_labels=disagree)
    # an empty assistant set changes nothing
    assert ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels={})["verdict"] == HELPS
    # UNRESOLVED is a base verdict too: only the fusion channel gained and the assistant removes it -> a different verdict -> UNRESOLVED (labels)
    cfg = make_cfg(draws=30, margin=6, min_same=0)            # min_same 0: the assistant leaves no SAME note at all, and that must not be what decides
    scores, first, days, tasks, labels = uniform_case(hyb_all=True)
    base = ref.p1_readings(scores, first, days, tasks, labels, cfg)
    assert base["verdict"] == UNRESOLVED
    result = ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels={(task, 3): "UNRELATED" for task in tasks})
    assert result["verdict_judge"] == UNRESOLVED and result["verdict_assistant"] == SUFFICIENT and result["verdict"] == BY_LABELS


def test_label_stability_does_not_touch_verdicts_that_are_not_base_verdicts():
    scores, first, days, tasks, labels = uniform_case(emb_same=True)
    disagree = {(tasks[p], 1): "RELATED" for p in range(6)}
    # not evaluable under the judge's labels (prevalence): stays so, whatever the assistant says
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=30, min_same=31), assistant_labels=disagree)
    assert result["verdict_judge"] == result["verdict"] == NOT_EVALUABLE and result["verdict_assistant"] == NOT_EVALUABLE
    # resampling boundary under the judge's labels: stays so, even though the assistant's verdict differs
    scores, first, days, tasks, labels, cfg = stability_inputs()
    all_unrelated = {pair: "UNRELATED" for pair in labels}
    result = ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=all_unrelated)
    assert result["verdict_judge"] == BOUNDARY and result["verdict_assistant"] != BOUNDARY and result["verdict"] == BOUNDARY
    assert result == oracle_p1(scores, first, days, tasks, labels, cfg, assistant_labels=all_unrelated)


def test_assistant_variant_is_the_whole_computation_on_the_substituted_labels():
    # ASSUMPTION pinned here: "same computation with the assistant's labels substituted" includes the prevalence check on the substituted labels.
    scores, first, days, tasks, labels = uniform_case(emb_same=True)
    lab = {pair: "RELATED" for pair in labels}
    for task in tasks[:25]:
        lab[(task, 1)] = "SAME"                                         # exactly 25 tasks with a SAME note under the judge's labels
    cfg = make_cfg(draws=30, min_same=25)
    judge_only = ref.p1_readings(scores, first, days, tasks, lab, cfg)
    assert judge_only["verdict"] == HELPS
    result = ref.p1_readings(scores, first, days, tasks, lab, cfg, assistant_labels={(tasks[20], 1): "UNRELATED"})      # 24 tasks under the assistant's
    assert result["tasks_with_same"] == 25 and result["prevalence_ok"] is True            # the report's own count is the judge's
    assert result["verdict_judge"] == HELPS and result["verdict_assistant"] == NOT_EVALUABLE and result["verdict"] == BY_LABELS


# ---------------------------------------------------------------- the fusion flag

@pytest.mark.parametrize("hyb_gain, flag", [(0, True), (1, True), (2, True), (3, False), (4, False), (6, False)])
def test_fusion_flag_when_the_hybrid_keeps_less_than_half_of_the_embedders_gain(hyb_gain, flag):
    scores, first, days, tasks, labels = uniform_case(emb_same=True, hyb_same=range(hyb_gain))          # HYB is SAME on the first hyb_gain fired tasks
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=20, margin=6, min_same=1))
    assert result["verdict"] == HELPS and result["d_emb"]["d"] == 6 and result["d_hyb"]["d"] == hyb_gain
    assert result["fusion_flag"] == ("refit_channel_weights" if flag else None)          # d_hyb < d_emb / 2 is strict: 3 < 3 is false


@pytest.mark.parametrize("hyb_gain, flag", [(3, True), (4, False)])
def test_fusion_flag_uses_true_division_when_the_embedders_gain_is_odd(hyb_gain, flag):
    # T = 35, m = 7: d_emb = 7, so the half is 3.5; d_hyb = 3 is below it (integer division would say 3 < 3 and miss it), d_hyb = 4 is not
    scores, first, days, tasks, labels = uniform_case(T=35, per_day=5, emb_same=True, hyb_same=range(hyb_gain))
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=20, margin=6, min_same=1))
    assert result["verdict"] == HELPS and result["d_emb"]["d"] == 7 and result["d_hyb"]["d"] == hyb_gain
    assert result["fusion_flag"] == ("refit_channel_weights" if flag else None)


def test_fusion_flag_needs_the_helps_verdict():
    scores, first, days, tasks, labels = uniform_case(emb_same=True, lex_same=True)         # d_emb = 0, d_hyb = -6 < 0 / 2, but the verdict is SUFFICIENT
    result = ref.p1_readings(scores, first, days, tasks, labels, make_cfg(draws=20, margin=6, min_same=1))
    assert result["d_hyb"]["d"] < result["d_emb"]["d"] / 2 and result["verdict"] == SUFFICIENT and result["fusion_flag"] is None


# ---------------------------------------------------------------- the label-free overlap and the decisive pairs

def overlap_example():
    """T = 10, q = 0.2 (m = 2), tasks 100..109. LEX fires p0, p1; EMB fires p1, p2; HYB fires p0, p1."""
    tasks = list(range(100, 110))
    tail = [0.05, 0.04, 0.03, 0.02, 0.01, 0.005, 0.004]
    scores = {LEX: [0.9, 0.8, 0.3, 0.2, 0.1] + tail[:5],
              EMB: [0.1, 0.9, 0.8, 0.2, 0.3] + tail[:5],
              HYB: [0.9, 0.8, 0.1, 0.2, 0.3] + tail[:5]}
    first = {LEX: [1, 2, 3, 0, 0, 0, 0, 0, 0, 0],
             EMB: [1, 5, 6, 0, 0, 0, 0, 0, 0, 0],
             HYB: [7, 2, 3, 0, 0, 0, 0, 0, 0, 0]}
    return scores, first, tasks


def test_overlap_table_by_hand():
    scores, first, tasks = overlap_example()
    # EMB vs LEX at m = 2: shared {p1} with different first candidates (5 against 2); only EMB {p2}; only LEX {p0}
    assert ref.overlap_table(scores, first, tasks, 0.2, EMB, LEX) == {"shared": 1, "same_first": 0, "only_a": 1, "only_b": 1, "discordant_tasks": 3,
                                                                       "decisive_pairs": 4, "max_abs_d": 2}
    # HYB vs LEX: both fire {p0, p1}; p0 differs (7 against 1), p1 agrees
    assert ref.overlap_table(scores, first, tasks, 0.2, HYB, LEX) == {"shared": 2, "same_first": 1, "only_a": 0, "only_b": 0, "discordant_tasks": 1,
                                                                       "decisive_pairs": 2, "max_abs_d": 1}
    # a method against itself: everything shared with the same first candidate
    assert ref.overlap_table(scores, first, tasks, 0.2, LEX, LEX) == {"shared": 2, "same_first": 2, "only_a": 0, "only_b": 0, "discordant_tasks": 0,
                                                                       "decisive_pairs": 0, "max_abs_d": 0}


def test_decisive_pairs_by_hand_union_over_both_contrasts_distinct_and_sorted():
    scores, first, tasks = overlap_example()
    # EMB vs LEX: (101, 5) and (101, 2) from the shared task with different firsts, (102, 6) from the EMB-only task, (100, 1) from the LEX-only task
    # HYB vs LEX: (100, 7) and (100, 1) from the shared task p0 (the pair (100, 1) is already there); p1 agrees and adds nothing
    assert ref.decisive_pairs(scores, first, tasks, 0.2) == [(100, 1), (100, 7), (101, 2), (101, 5), (102, 6)]
    assert ref.decisive_pairs(scores, first, tasks) == ref.decisive_pairs(scores, first, tasks, q=0.2)        # q defaults to 0.2
    # the per-contrast counts of the table (4 and 2) add up to 6; the union holds 5 because (100, 1) is in both
    counts = [ref.overlap_table(scores, first, tasks, 0.2, a, LEX)["decisive_pairs"] for a in (EMB, HYB)]
    assert counts == [4, 2]


@pytest.mark.parametrize("case", range(8))
def test_overlap_identities_and_the_bound_on_the_difference(case):
    T = 60
    scores, first, days, tasks, labels = random_case(2000 + case, T=T, levels=[0, 4][case % 2], ninf=[0.0, 0.2][case // 4])
    rng = random.Random(case)
    for q in (0.1, 0.2, 0.3):
        for a in (EMB, HYB):
            table = ref.overlap_table(scores, first, tasks, q, a, LEX)
            different = table["shared"] - table["same_first"]
            assert table["discordant_tasks"] == table["only_a"] + table["only_b"] + different
            assert table["decisive_pairs"] == table["only_a"] + table["only_b"] + 2 * different
            assert table["max_abs_d"] == max(table["only_a"], table["only_b"]) + different
            fire_a, fire_b = ref.fire_set_full(scores[a], tasks, q), ref.fire_set_full(scores[LEX], tasks, q)
            assert table["shared"] + table["only_a"] == len(fire_a) and table["shared"] + table["only_b"] == len(fire_b)
            # for any relevance whatsoever |hits_a - hits_b| <= max_abs_d, and the bound is reached when everything that can differ does
            for _ in range(5):
                rel = {name: [rng.randrange(2) for _ in range(T)] for name in (a, LEX)}
                d = sum(rel[a][p] for p in fire_a) - sum(rel[LEX][p] for p in fire_b)
                assert abs(d) <= table["max_abs_d"]
    # decisive pairs: every pair is a first candidate of a fired task, and the union count is at most the sum of the two contrasts' counts
    pairs = ref.decisive_pairs(scores, first, tasks, 0.2)
    assert pairs == sorted(set(pairs))
    counts = [ref.overlap_table(scores, first, tasks, 0.2, a, LEX)["decisive_pairs"] for a in (EMB, HYB)]
    assert max(counts) <= len(pairs) <= sum(counts)          # each contrast's pairs are distinct; the union can only share pairs between contrasts
    position = {task: p for p, task in enumerate(tasks)}
    for task, note in pairs:
        p = position[task]
        assert any(first[name][p] == note and p in ref.fire_set_full(scores[name], tasks, 0.2) for name in (EMB, LEX, HYB))


# ---------------------------------------------------------------- gate statistics

def test_wilson_interval_known_values():
    z = 1.959963984540054
    lo, hi = ref.wilson(5, 10)
    assert (lo, hi) == pytest.approx((0.23659, 0.76341), abs=1e-5)
    lo, hi = ref.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(z * z / (10 + z * z), abs=1e-12) and hi == pytest.approx(0.27754, abs=1e-5)
    lo, hi = ref.wilson(10, 10)
    assert hi == 1.0 and lo == pytest.approx(1 - z * z / (10 + z * z), abs=1e-12)
    assert ref.wilson(8, 10) == pytest.approx((0.49016, 0.94332), abs=1e-5)
    assert ref.wilson(22, 51) == pytest.approx((0.305012, 0.567347), abs=1e-6)             # values of scipy.stats.binomtest(...).proportion_ci(wilson)
    assert ref.wilson(55, 60) == pytest.approx((0.819311, 0.963880), abs=1e-6)
    assert ref.wilson(3, 60) == pytest.approx((0.017150, 0.137005), abs=1e-6)
    assert ref.wilson(0, 0) == (0.0, 1.0)
    for k, n in ((1, 7), (3, 60), (55, 60), (40, 51)):
        lo, hi = ref.wilson(k, n)
        mirror_lo, mirror_hi = ref.wilson(n - k, n)
        assert (lo, hi) == pytest.approx((1 - mirror_hi, 1 - mirror_lo), abs=1e-12)
        assert 0.0 <= lo <= k / n <= hi <= 1.0
    with pytest.raises(ValueError):
        ref.wilson(5, 4)


def test_cohen_kappa_same_by_hand():
    # SAME versus not-SAME: a = 1111000000, b = 1110000001 -> p_o = 0.8, both SAME rates 0.4, p_e = 0.16 + 0.36 = 0.52, kappa = 0.28 / 0.48
    a = ["SAME", "SAME", "SAME", "SAME", "RELATED", "UNRELATED", "UNRELATED", "RELATED", "UNRELATED", None]
    b = ["SAME", "SAME", "SAME", "UNRELATED", "RELATED", "UNRELATED", "UNRELATED", "RELATED", "UNRELATED", "SAME"]
    assert ref.cohen_kappa_same(a, b) == pytest.approx(0.28 / 0.48, abs=1e-12)
    assert ref.cohen_kappa_same(a, a) == 1.0
    assert ref.cohen_kappa_same(["SAME", "SAME", "UNRELATED", "UNRELATED"], ["UNRELATED", "UNRELATED", "SAME", "SAME"]) == -1.0
    assert ref.cohen_kappa_same(["SAME", "SAME", "UNRELATED", "UNRELATED"], ["SAME", "UNRELATED", "SAME", "UNRELATED"]) == 0.0
    assert math.isnan(ref.cohen_kappa_same(["UNRELATED", "RELATED", None], ["RELATED", "RELATED", "UNRELATED"]))       # nobody says SAME: undefined
    assert math.isnan(ref.cohen_kappa_same([], []))
    with pytest.raises(ValueError):
        ref.cohen_kappa_same(["SAME"], ["SAME", "SAME"])
