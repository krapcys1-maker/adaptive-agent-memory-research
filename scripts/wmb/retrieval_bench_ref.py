"""WMB-R1 reference implementation of the P1 readings: an independent re-implementation, written from the preregistration only.

Source of truth: data/lab/wmb-r1-retrieval/README.md (amended) and config.json. This module was written WITHOUT reading scripts/wmb/retrieval_bench.py,
scripts/wmb/stats.py or tests/test_wmb_retrieval_bench.py; the only other code consulted for the logic is the original splitmix64 `bootstrap_indices`
of scripts/analyze_writer_memory_sim.py that the README names. It imports no local module (standard library and numpy only), so that its digest in
config.json depends on nothing but this file.

Style: plain loops, one rule per function. `fire_set` is the literal text of the rule and is the specification; the bootstrap loop uses a counting
engine (`bootstrap_differences`) that is proved equal to the literal rule in the tests, because 100,000 draws x 4 seeds x 2 schemes x 3 methods of
sort-based fire sets would take about ten minutes.

Public functions: p1_readings, overlap_table, decisive_pairs, wilson, cohen_kappa_same, plus the building blocks bootstrap_indices, fire_count, fire_set,
relevance_vector, percentile_interval, base_verdict.
"""

from __future__ import annotations

import math
from fractions import Fraction
from statistics import NormalDist
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import numpy as np

NEG_INF = float("-inf")

# splitmix64, constants as in scripts/analyze_writer_memory_sim.bootstrap_indices
MASK = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15
MIX_1 = 0xBF58476D1CE4E5B9
MIX_2 = 0x94D049BB133111EB

EMB = "EMB_MINILM"
LEX = "LEX_KERNEL"
HYB = "HYB_KERNEL"
CONTRASTS = ((EMB, LEX), (HYB, LEX))                 # P1 (primary) and P1b (fusion check); B is always LEX_KERNEL

HELPS = "EMBEDDER_HELPS_GATE"
SUFFICIENT = "LEXICAL_SUFFICIENT_FOR_GATE"
UNRESOLVED = "UNRESOLVED"
BASE_VERDICTS = (HELPS, SUFFICIENT, UNRESOLVED)
UNRESOLVED_BOUNDARY = "UNRESOLVED (resampling boundary)"
UNRESOLVED_LABELS = "UNRESOLVED (labels)"
NOT_EVALUABLE = "NOT_EVALUABLE (prevalence)"
FUSION_FLAG = "refit_channel_weights"
STRICT = "SAME"                                       # strict relevance is the only primary relevance

# Two readings of the text that the README leaves open. The defaults are this module's reading; the switches exist so that a cross-check against another
# implementation can be run under either reading (see the final report of the build).
DAY_ORDER = "sorted"                 # how the distinct days are numbered for the day-block stream: "sorted" (sorted(set(days))) or "first_seen"
ASSISTANT_PREVALENCE = "recompute"   # the assistant variant applies the prevalence rule to the substituted labels ("recompute") or inherits the judge's ("judge")


# ---------------------------------------------------------------- the resample stream (splitmix64)

def splitmix64_outputs_py(seed: int, count: int) -> List[int]:
    """The first `count` outputs of the splitmix64 stream that starts at `seed`, by the literal loop (slow; the reference for the numpy path)."""
    state = seed & MASK
    out = []
    for _ in range(count):
        state = (state + GOLDEN) & MASK
        z = ((state ^ (state >> 30)) * MIX_1) & MASK
        z = ((z ^ (z >> 27)) * MIX_2) & MASK
        out.append(z ^ (z >> 31))
    return out


def bootstrap_indices_py(n: int, draws: int, seed: int) -> List[List[int]]:
    """Resample d, pick k is output number d * n + k of the stream, taken modulo n (the stream is not restarted between draws)."""
    stream = splitmix64_outputs_py(seed, n * draws)
    return [[stream[d * n + k] % n for k in range(n)] for d in range(draws)]


def _stream_block(seed: int, first: int, count: int) -> np.ndarray:
    """Outputs number first .. first + count - 1 (0-based) of the stream as uint64. The state after t + 1 steps is seed + (t + 1) * GOLDEN mod 2^64."""
    with np.errstate(over="ignore"):
        steps = np.arange(first + 1, first + count + 1, dtype=np.uint64)
        state = np.uint64(seed & MASK) + steps * np.uint64(GOLDEN)
        z = (state ^ (state >> np.uint64(30))) * np.uint64(MIX_1)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(MIX_2)
        return z ^ (z >> np.uint64(31))


def iter_bootstrap_rows(n: int, draws: int, seed: int, chunk_values: int = 1 << 20) -> Iterator[List[int]]:
    """Yield the `draws` resamples of size n one at a time, in chunks; the rows are those of bootstrap_indices(n, draws, seed)."""
    if n < 1 or draws < 0:
        raise ValueError("bootstrap needs n >= 1 and draws >= 0")
    rows_per_chunk = max(1, chunk_values // n)
    done = 0
    while done < draws:
        rows = min(rows_per_chunk, draws - done)
        block = _stream_block(seed, done * n, rows * n) % np.uint64(n)
        for row in block.reshape(rows, n).tolist():
            yield row
        done += rows


def bootstrap_indices(n: int, draws: int, seed: int) -> List[List[int]]:
    """Same signature and same output as scripts/analyze_writer_memory_sim.bootstrap_indices, computed with numpy."""
    return list(iter_bootstrap_rows(n, draws, seed))


# ---------------------------------------------------------------- the fire set

def fire_count(q: float, n: int) -> int:
    """m = ceil(round(q * n, 9)): the number of tasks that fire in a multiset of n tasks (the rounding removes float noise such as 7.000000000000001)."""
    return int(math.ceil(round(q * n, 9)))


def fire_set(scores: Sequence[float], tasks: Sequence[int], slots: Sequence[int], q: float) -> List[int]:
    """The literal rule. `slots` is a resample: a list of task positions, repeats allowed (copies count separately); n = len(slots).

    m = fire_count(q, n) slots fire: the m with the highest score, ties by task number ascending, then by position in the resample. A slot whose score
    is -inf never fires, so fewer than m may fire. Returns the positions k in `slots` of the fired slots, best first.
    """
    n = len(slots)
    m = fire_count(q, n)
    order = sorted(range(n), key=lambda k: (-scores[slots[k]], tasks[slots[k]], k))
    fired: List[int] = []
    for k in order:
        if len(fired) == m or scores[slots[k]] == NEG_INF:        # -inf sorts last, so nothing after it can fire either
            break
        fired.append(k)
    return fired


def fire_set_full(scores: Sequence[float], tasks: Sequence[int], q: float) -> List[int]:
    """Fire set of the full sample (the identity resample): task positions p, best first."""
    return fire_set(scores, tasks, list(range(len(scores))), q)


def relevance_vector(labels: Dict[Tuple[int, int], Optional[str]], tasks: Sequence[int], first_candidates: Sequence[int]) -> List[int]:
    """1 when the method's first candidate j for task i is labelled SAME (strict relevance), else 0. No label, None and first = -1 are not relevant."""
    return [1 if labels.get((int(tasks[p]), int(first_candidates[p]))) == STRICT else 0 for p in range(len(tasks))]


def hits_and_false(scores: Sequence[float], tasks: Sequence[int], relevant: Sequence[int], q: float) -> Tuple[int, int]:
    """(hits, false_injections) of the full-sample fire set: hits = fired tasks whose first candidate is relevant, false = fired - hits."""
    fired = fire_set_full(scores, tasks, q)
    hits = sum(relevant[p] for p in fired)
    return hits, len(fired) - hits


# ---------------------------------------------------------------- the bootstrap

def firing_order(scores: Sequence[float], tasks: Sequence[int]) -> List[int]:
    """Task positions that can fire (finite score), best first: score descending, task number ascending."""
    able = [p for p in range(len(scores)) if scores[p] != NEG_INF]
    able.sort(key=lambda p: (-scores[p], tasks[p]))
    return able


def fired_copies(order: Sequence[int], counts: Sequence[int], m: int) -> List[Tuple[int, int]]:
    """Counting form of fire_set for a resample given as copies per task position: walk down the firing order and take copies until m slots fire.

    Copies of one task are interchangeable (same score, same first candidate), so which copies are cut does not change any count. Returns (position, copies).
    """
    left = m
    taken: List[Tuple[int, int]] = []
    for p in order:
        if left <= 0:
            break
        c = counts[p]
        if c:
            t = c if c < left else left
            taken.append((p, t))
            left -= t
    return taken


def bootstrap_differences(rows: Iterable[Sequence[int]], blocks: Sequence[Sequence[int]], n_positions: int, q: float,
                          orders: Dict[str, Sequence[int]], rel_sets: Sequence[Dict[str, Sequence[int]]],
                          contrasts: Sequence[Tuple[str, str]] = CONTRASTS) -> List[List[List[int]]]:
    """D* of every resample, for every label set and contrast.

    rows: resamples, each a list of block numbers. blocks[b]: the task positions of block b (one task for the task bootstrap, a day's tasks for the
    day-block bootstrap). A resample's slots are the tasks of its blocks (a block picked twice contributes its tasks twice); its size n is their number and
    m = fire_count(q, n) of them fire. D* = hits(method a) - hits(method b) over the two fire sets, recomputed in every resample.
    Returns result[label_set][contrast] = list of D* (ints), one per resample.
    """
    methods = sorted({name for pair in contrasts for name in pair})
    result: List[List[List[int]]] = [[[] for _ in contrasts] for _ in rel_sets]
    for picks in rows:
        counts = [0] * n_positions
        size = 0
        for b in picks:
            members = blocks[b]
            size += len(members)
            for p in members:
                counts[p] += 1
        m = fire_count(q, size)
        hits: Dict[Tuple[int, str], int] = {}
        for name in methods:
            taken = fired_copies(orders[name], counts, m)
            for s, rel in enumerate(rel_sets):
                hits[(s, name)] = sum(t * rel[name][p] for p, t in taken)
        for s in range(len(rel_sets)):
            for c, (a, b) in enumerate(contrasts):
                result[s][c].append(hits[(s, a)] - hits[(s, b)])
    return result


def percentile_interval(values: Sequence[int], alpha: float = 0.05) -> Tuple[int, int]:
    """[sorted(D*)[floor(alpha/2 * B)], sorted(D*)[ceil((1 - alpha/2) * B) - 1]] with B = len(values); for alpha 0.05 these are floor(0.025 * B) and
    ceil(0.975 * B) - 1. Evaluated in exact arithmetic on the decimal text of alpha, so float noise cannot move an index."""
    draws = len(values)
    if draws < 1:
        raise ValueError("an interval needs at least one resample")
    tail = Fraction(str(alpha)) / 2
    low_index = math.floor(tail * draws)
    high_index = math.ceil((1 - tail) * draws) - 1
    ordered = sorted(values)
    return ordered[low_index], ordered[high_index]


# ---------------------------------------------------------------- the verdict

def base_verdict(d_emb: float, lo_emb: float, hi_emb: float, hi_hyb: float, margin: float) -> str:
    """EMBEDDER_HELPS_GATE: lower bound of the D_emb interval above 0 and D_emb >= margin. LEXICAL_SUFFICIENT_FOR_GATE: the upper bounds of both the D_emb
    and the D_hyb intervals below margin. UNRESOLVED otherwise. (The first two cannot both hold unless the interval excludes its own point estimate;
    the first is tested first, as in the text.)"""
    if lo_emb > 0 and d_emb >= margin:
        return HELPS
    if hi_emb < margin and hi_hyb < margin:
        return SUFFICIENT
    return UNRESOLVED


def combine_seed_verdicts(by_seed: Dict[str, str], primary_seed: str, evaluable: bool) -> str:
    """NOT_EVALUABLE (prevalence) when the prevalence check fails; otherwise the primary seed's verdict if all seeds give the same one, else
    UNRESOLVED (resampling boundary)."""
    if not evaluable:
        return NOT_EVALUABLE
    if len(set(by_seed.values())) == 1:
        return by_seed[primary_seed]
    return UNRESOLVED_BOUNDARY


def tasks_with_same(labels: Dict[Tuple[int, int], Optional[str]]) -> int:
    """Number of distinct tasks i that have at least one pair (i, j) labelled SAME."""
    return len({pair[0] for pair, label in labels.items() if label == STRICT})


# ---------------------------------------------------------------- the P1 readings

def _clean_inputs(scores, first, days, tasks):
    """Python floats and ints, the sizes checked, NaN refused, task numbers required to be distinct (they are the tie-break and the label key)."""
    tasks = [int(t) for t in tasks]
    T = len(tasks)
    if T == 0:
        raise ValueError("no tasks")
    if len(set(tasks)) != T:
        raise ValueError("task numbers must be distinct")
    if len(days) != T:
        raise ValueError("days must have one entry per task")
    for name in (EMB, LEX, HYB):
        if name not in scores or name not in first:
            raise ValueError("scores and first must hold %s" % name)
    clean_scores, clean_first = {}, {}
    for name, values in scores.items():
        if len(values) != T:
            raise ValueError("scores[%s] must have one entry per task" % name)
        if name not in first or len(first[name]) != T:
            raise ValueError("first[%s] must have one entry per task" % name)
        clean_scores[name] = [float(v) for v in values]
        if any(v != v for v in clean_scores[name]):
            raise ValueError("scores[%s] holds NaN" % name)
        clean_first[name] = [int(v) for v in first[name]]
    return clean_scores, clean_first, list(days), tasks


def day_block_structure(days: Sequence, order: Optional[str] = None) -> Tuple[list, List[List[int]]]:
    """The distinct days and, for each, the task positions of that day: the blocks of the day-block bootstrap. A resample draws day numbers 0 .. D-1 with
    bootstrap_indices(D, ...), so the numbering matters: "sorted" numbers the days in sorted order (chronological for ISO dates), "first_seen" in order of
    first appearance in `days` (the same thing when the tasks are listed by date, as they are on the real data)."""
    order = DAY_ORDER if order is None else order
    if order == "sorted":
        names = sorted(set(days))
    elif order == "first_seen":
        names = list(dict.fromkeys(days))
    else:
        raise ValueError("day order must be 'sorted' or 'first_seen'")
    return names, [[p for p in range(len(days)) if days[p] == name] for name in names]


def _wider(task_interval: Tuple[int, int], day_interval: Tuple[int, int]) -> Tuple[int, int]:
    """The interval used for the verdict: the wider of the task and day-block intervals at each end."""
    return min(task_interval[0], day_interval[0]), max(task_interval[1], day_interval[1])


def p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=None, draws=None) -> dict:
    """The P1 readings of WMB-R1 U1: hits table, D_emb and D_hyb with their intervals, the verdict under the judge's labels and under the assistant's,
    the stability and prevalence rules, and the fusion flag. See the module docstring and the README section Readings; the keys returned are
    tasks_with_same, prevalence_ok, hits, d_emb, d_hyb, verdict_by_seed, verdict_judge, verdict_assistant, verdict, fusion_flag.
    """
    readings = cfg["readings"]
    boot = readings["bootstrap"]
    sweep = readings["sweep"]
    q_primary = readings["primary_q"]
    margin = readings["margin_tasks"]
    alpha = boot.get("alpha", 0.05)
    n_draws = int(draws) if draws is not None else int(boot["draws_primary"])    # `draws` overrides draws_primary and draws_other alike
    min_same = cfg["judge"]["prevalence_rule_min_tasks_with_same"]
    seeds = [boot["seed"]] + list(boot["stability_seeds"])

    scores, first, days, tasks = _clean_inputs(scores, first, days, tasks)
    T = len(tasks)

    # label set 0: the judge's labels; label set 1 (if any): the judge's labels with the assistant's substituted on the pairs it covers
    label_sets = [labels]
    if assistant_labels is not None:
        merged = dict(labels)
        merged.update(assistant_labels)
        label_sets.append(merged)
    rel_sets = [{name: relevance_vector(L, tasks, first[name]) for name in scores} for L in label_sets]

    # resample structure: the task bootstrap resamples the T tasks; the day-block bootstrap resamples the distinct days (numbered as DAY_ORDER says),
    # a day's tasks together
    orders = {name: firing_order(scores[name], tasks) for name in (EMB, LEX, HYB)}
    task_blocks = [[p] for p in range(T)]
    day_names, day_blocks = day_block_structure(days)

    intervals: Dict[int, List[List[Tuple[Tuple[int, int], Tuple[int, int]]]]] = {}   # seed -> label set -> contrast -> (task interval, day interval)
    for seed in seeds:
        by_task = bootstrap_differences(iter_bootstrap_rows(T, n_draws, seed), task_blocks, T, q_primary, orders, rel_sets)
        by_day = bootstrap_differences(iter_bootstrap_rows(len(day_names), n_draws, seed), day_blocks, T, q_primary, orders, rel_sets)
        intervals[seed] = [[(percentile_interval(by_task[s][c], alpha), percentile_interval(by_day[s][c], alpha)) for c in range(len(CONTRASTS))]
                           for s in range(len(label_sets))]

    summaries = []
    for s, label_set in enumerate(label_sets):
        d = []
        for a, b in CONTRASTS:
            ha, _ = hits_and_false(scores[a], tasks, rel_sets[s][a], q_primary)
            hb, _ = hits_and_false(scores[b], tasks, rel_sets[s][b], q_primary)
            d.append(ha - hb)
        by_seed = {}
        for seed in seeds:
            lo_emb, hi_emb = _wider(*intervals[seed][s][0])
            _, hi_hyb = _wider(*intervals[seed][s][1])
            by_seed[str(seed)] = base_verdict(d[0], lo_emb, hi_emb, hi_hyb, margin)
        same = tasks_with_same(label_set)
        evaluable = same >= min_same
        if s == 1 and ASSISTANT_PREVALENCE == "judge":
            evaluable = summaries[0]["evaluable"]
        elif s == 1 and ASSISTANT_PREVALENCE != "recompute":
            raise ValueError("ASSISTANT_PREVALENCE must be 'recompute' or 'judge'")
        summaries.append({"d": d, "by_seed": by_seed, "same": same, "evaluable": evaluable,
                          "verdict": combine_seed_verdicts(by_seed, str(seeds[0]), evaluable)})

    judge = summaries[0]
    primary = intervals[seeds[0]][0]

    def d_block(c: int) -> dict:
        (task_lo, task_hi), (day_lo, day_hi) = primary[c]
        lo, hi = _wider(primary[c][0], primary[c][1])
        return {"d": judge["d"][c], "lo": float(lo), "hi": float(hi), "task_lo": float(task_lo), "task_hi": float(task_hi),
                "day_lo": float(day_lo), "day_hi": float(day_hi)}

    d_emb, d_hyb = d_block(0), d_block(1)
    hits_table = {}
    for name in scores:
        hits_table[name] = {}
        for q in sweep:
            h, f = hits_and_false(scores[name], tasks, rel_sets[0][name], q)
            hits_table[name][str(q)] = {"hits": h, "false_injections": f}

    verdict_judge = judge["verdict"]
    verdict_assistant = summaries[1]["verdict"] if assistant_labels is not None else None
    verdict = verdict_judge
    if assistant_labels is not None and verdict_assistant != verdict_judge and verdict_judge in BASE_VERDICTS:
        verdict = UNRESOLVED_LABELS
    fusion_flag = FUSION_FLAG if verdict == HELPS and d_hyb["d"] < d_emb["d"] / 2 else None

    return {"tasks_with_same": judge["same"], "prevalence_ok": judge["evaluable"], "hits": hits_table, "d_emb": d_emb, "d_hyb": d_hyb,
            "verdict_by_seed": judge["by_seed"], "verdict_judge": verdict_judge, "verdict_assistant": verdict_assistant, "verdict": verdict,
            "fusion_flag": fusion_flag}


# ---------------------------------------------------------------- the label-free overlap and the decisive pairs

def overlap_table(scores, first, tasks, q: float, a: str, b: str) -> dict:
    """One row of the README overlap table for methods a (first) and b, from the scores alone.

    shared: tasks in both fire sets; same_first: shared tasks with the same first candidate; only_a, only_b: tasks in one fire set only;
    discordant_tasks = only_a + only_b + (shared - same_first); decisive_pairs = only_a + only_b + 2 * (shared - same_first);
    max_abs_d = max(only_a, only_b) + (shared - same_first).
    """
    tasks = [int(t) for t in tasks]
    fire_a = set(fire_set_full([float(v) for v in scores[a]], tasks, q))
    fire_b = set(fire_set_full([float(v) for v in scores[b]], tasks, q))
    shared = fire_a & fire_b
    same_first = sum(1 for p in shared if first[a][p] == first[b][p])
    different_first = len(shared) - same_first
    only_a, only_b = len(fire_a - fire_b), len(fire_b - fire_a)
    return {"shared": len(shared), "same_first": same_first, "only_a": only_a, "only_b": only_b,
            "discordant_tasks": only_a + only_b + different_first,
            "decisive_pairs": only_a + only_b + 2 * different_first,
            "max_abs_d": max(only_a, only_b) + different_first}


def decisive_pairs(scores, first, tasks, q: float = 0.2) -> List[Tuple[int, int]]:
    """Sorted distinct pairs (task number i, note index j) that carry D_emb or D_hyb at fraction q.

    For each contrast (EMB_MINILM against LEX_KERNEL, HYB_KERNEL against LEX_KERNEL): a task in exactly one fire set contributes the first candidate of
    the method that fires (the other method adds nothing to the difference); a task in both fire sets with different first candidates contributes both
    first candidates; a task in both with the same first candidate contributes nothing. The union over both contrasts, sorted.
    """
    tasks = [int(t) for t in tasks]
    pairs = set()
    for a, b in CONTRASTS:
        fire_a = set(fire_set_full([float(v) for v in scores[a]], tasks, q))
        fire_b = set(fire_set_full([float(v) for v in scores[b]], tasks, q))
        for p in sorted(fire_a | fire_b):
            if p in fire_a and p in fire_b:
                if first[a][p] != first[b][p]:
                    pairs.add((tasks[p], int(first[a][p])))
                    pairs.add((tasks[p], int(first[b][p])))
            elif p in fire_a:
                pairs.add((tasks[p], int(first[a][p])))
            else:
                pairs.add((tasks[p], int(first[b][p])))
    return sorted(pairs)


# ---------------------------------------------------------------- statistics of the gate reports

def wilson(k: int, n: int) -> Tuple[float, float]:
    """Wilson score interval for k successes in n trials at 95% (z = 1.959963984540054), clipped to [0, 1]; (0.0, 1.0) when n == 0."""
    if n == 0:
        return 0.0, 1.0
    if not 0 <= k <= n:
        raise ValueError("k must be between 0 and n")
    z = NormalDist().inv_cdf(0.975)
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    low = 0.0 if k == 0 else max(0.0, centre - half)               # exactly 0 at k = 0 and exactly 1 at k = n (float cancellation would leave 2.8e-17)
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high


def cohen_kappa_same(labels_a: Sequence[Optional[str]], labels_b: Sequence[Optional[str]]) -> float:
    """Cohen's kappa between two label sequences collapsed to SAME versus not-SAME (RELATED, UNRELATED and None are all not-SAME).

    kappa = (p_o - p_e) / (1 - p_e) with p_o the share of items on which the two agree and p_e the agreement expected from the two SAME rates.
    NaN when it is undefined: empty input, or both sequences constant at the same value (p_e = 1).
    """
    if len(labels_a) != len(labels_b):
        raise ValueError("the two label sequences must have the same length")
    n = len(labels_a)
    if n == 0:
        return float("nan")
    x = [1 if label == STRICT else 0 for label in labels_a]
    y = [1 if label == STRICT else 0 for label in labels_b]
    observed = sum(1 for u, v in zip(x, y) if u == v) / n
    same_a, same_b = sum(x) / n, sum(y) / n
    expected = same_a * same_b + (1 - same_a) * (1 - same_b)
    if expected == 1.0:
        return float("nan")
    return (observed - expected) / (1 - expected)
