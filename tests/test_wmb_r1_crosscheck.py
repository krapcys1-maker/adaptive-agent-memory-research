"""WMB-R1: the analysis (retrieval_bench) and its independent reference implementation (retrieval_bench_ref, written from the README alone) must agree exactly.

Synthetic inputs only. The reference was written without reading the analysis code, so an agreement is evidence that the README says what the code computes.
"""

from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wmb import retrieval_bench as rb, retrieval_bench_ref as ref  # noqa: E402

CFG = json.loads((ROOT / "data" / "lab" / "wmb-r1-retrieval" / "config.json").read_text(encoding="utf-8"))
METHODS = ("EMB_MINILM", "LEX_KERNEL", "HYB_KERNEL", "LEX_BM25", "LEX_TFIDF", "HYB_SHIPPED")
LABELS = ("SAME", "RELATED", "UNRELATED")


def plain(x):
    """Numbers as plain Python, so that numpy scalars compare equal to ints and floats."""
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if hasattr(x, "item"):
        return x.item()
    return x


def make_inputs(seed: int, t: int = 60, days: int = 21, same_share: float = 0.3, ties: bool = True):
    rng = random.Random(seed)
    tasks = list(range(20, 20 + t))
    day_of = sorted(rng.randrange(days) for _ in range(t))                # chronological: both implementations number the days in this order
    day_names = ["2026-09-%02d" % (1 + d) for d in day_of]
    scores, first, labels = {}, {}, {}
    for m in METHODS:
        s, f = [], []
        for i in tasks:
            if rng.random() < 0.03:
                s.append(float("-inf"))
                f.append(-1)
            else:
                s.append(round(rng.random(), 1 if ties else 6))
                f.append(rng.randrange(0, i))
        scores[m], first[m] = s, f
    for k, i in enumerate(tasks):
        for m in METHODS:
            j = first[m][k]
            if j >= 0 and (i, j) not in labels:
                r = rng.random()
                labels[(i, j)] = "SAME" if r < same_share else ("RELATED" if r < same_share + 0.2 else ("UNRELATED" if r < 0.97 else None))
    assistant = {key: ("SAME" if rng.random() < 0.3 else "UNRELATED") for key in rng.sample(sorted(labels), 12)}
    return scores, first, day_names, tasks, labels, assistant


def small_cfg(prevalence: int = 5) -> dict:
    cfg = json.loads(json.dumps(CFG))
    cfg["judge"]["prevalence_rule_min_tasks_with_same"] = prevalence
    return cfg


@pytest.mark.parametrize("seed", list(range(12)))
def test_the_two_implementations_return_identical_readings_on_random_inputs(seed: int) -> None:
    scores, first, days, tasks, labels, assistant = make_inputs(seed, ties=bool(seed % 2))
    cfg = small_cfg()
    for assistant_labels in (None, assistant):
        a = plain(rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels, 120))
        b = plain(ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels, 120))
        assert set(a) == set(b), (set(a) ^ set(b))
        for key in sorted(a):
            assert a[key] == b[key], (key, a[key], b[key])


def test_both_agree_when_prevalence_fails_when_scores_are_all_equal_and_when_a_method_has_no_candidates() -> None:
    scores, first, days, tasks, labels, assistant = make_inputs(3, same_share=0.02)
    cfg = small_cfg(prevalence=25)
    a = plain(rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant, 100))
    b = plain(ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant, 100))
    assert a == b and a["prevalence_ok"] is False and a["verdict"].startswith("NOT_EVALUABLE")
    flat = {m: [0.5] * len(tasks) for m in METHODS}
    s2, f2, d2, t2, l2, a2 = make_inputs(4)
    assert plain(rb.p1_readings(flat, f2, d2, t2, l2, small_cfg(), None, 100)) == plain(ref.p1_readings(flat, f2, d2, t2, l2, small_cfg(), None, 100))
    none = {m: ([float("-inf")] * len(tasks) if m == "EMB_MINILM" else s2[m]) for m in METHODS}
    nf = {m: ([-1] * len(tasks) if m == "EMB_MINILM" else f2[m]) for m in METHODS}
    assert plain(rb.p1_readings(none, nf, d2, t2, l2, small_cfg(), None, 100)) == plain(ref.p1_readings(none, nf, d2, t2, l2, small_cfg(), None, 100))


def test_both_agree_on_the_full_size_of_the_real_slice() -> None:
    scores, first, days, tasks, labels, assistant = make_inputs(99, t=214, days=63, same_share=0.25)
    cfg = json.loads(json.dumps(CFG))
    a = plain(rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant, 2000))
    b = plain(ref.p1_readings(scores, first, days, tasks, labels, cfg, assistant, 2000))
    assert a == b
    assert {"d_emb", "d_hyb", "hits", "verdict", "verdict_by_seed", "tasks_with_same"} <= set(a) and len(a["verdict_by_seed"]) == 4


def test_the_fire_set_overlap_table_and_the_decisive_pairs_agree() -> None:
    for seed in (7, 8, 9):
        scores, first, days, tasks, labels, assistant = make_inputs(seed, t=214, days=63)
        expected = ref.decisive_pairs(scores, first, tasks, 0.2)
        assert expected == sorted(set(expected))
        assert {(int(d["i"]), int(d["j"])) for d in rb.decisive_pairs(scores, first, tasks, 0.2)} == {(int(i), int(j)) for i, j in expected}
        rows = rb.overlap_table(scores, first, tasks, CFG)
        assert len(rows) == 6
        for row in rows:
            a, b = row["contrast"].split(" vs ")
            table = ref.overlap_table(scores, first, tasks, row["q"], a, b)
            for key in ("shared", "same_first", "only_a", "only_b", "discordant_tasks", "decisive_pairs", "max_abs_d"):
                assert row[key] == table[key], (seed, row["contrast"], row["q"], key, row[key], table[key])
            assert table["discordant_tasks"] == table["only_a"] + table["only_b"] + (table["shared"] - table["same_first"])
            assert table["decisive_pairs"] == table["only_a"] + table["only_b"] + 2 * (table["shared"] - table["same_first"])
            assert table["max_abs_d"] == max(table["only_a"], table["only_b"]) + (table["shared"] - table["same_first"])


def test_the_planted_gain_simulation_gives_the_same_verdicts_in_both_implementations_and_rises_with_the_gain() -> None:
    """A small version of control C4: the planted gain is a number of extra relevant first candidates of EMB_MINILM among its fired tasks."""
    cfg = small_cfg()
    cfg["readings"]["bootstrap"]["stability_seeds"] = []
    helps = {}
    for gain in (0, 3, 6, 9):
        count = 0
        for rep in range(20):
            rng = random.Random(1000 * gain + rep)
            scores, first, days, tasks, labels, _ = make_inputs(rep, t=214, days=63, same_share=0.15)
            same_first = {m: set() for m in ("EMB_MINILM", "LEX_KERNEL")}
            for k, i in enumerate(tasks):
                labels = dict(labels)
            order = sorted(range(len(tasks)), key=lambda p: (-scores["EMB_MINILM"][p], tasks[p]))
            fired_emb = [p for p in order[:43] if first["EMB_MINILM"][p] >= 0]
            candidates = [p for p in fired_emb if labels.get((tasks[p], first["EMB_MINILM"][p])) != "SAME"]
            for p in rng.sample(candidates, min(gain, len(candidates))):
                labels[(tasks[p], first["EMB_MINILM"][p])] = "SAME"
            a = plain(rb.p1_readings(scores, first, days, tasks, labels, cfg, None, 100))
            b = plain(ref.p1_readings(scores, first, days, tasks, labels, cfg, None, 100))
            assert a == b
            count += 1 if a["verdict"] == "EMBEDDER_HELPS_GATE" else 0
        helps[gain] = count / 20
    assert helps[0] <= 0.25 and helps[9] >= helps[0]


def test_the_c4_script_plants_the_requested_gain_and_the_two_implementations_agree_on_every_set(tmp_path: Path) -> None:
    from wmb import retrieval_c4 as c4
    scores, first, days, tasks, labels, assistant = make_inputs(21, t=214, days=63, ties=False)
    times = ["2026-08-01T08:00:00"] * (max(tasks) + 1)
    for k, i in enumerate(tasks):
        times[i] = days[k] + "T08:00:00"
    prep = {"eligible": tasks, "times": times,
            "rankings": {m: {str(i): ([[first[m][k], scores[m][k]]] if first[m][k] >= 0 else []) for k, i in enumerate(tasks)} for m in c4.METHODS}}
    path = tmp_path / "prep.json"
    path.write_text(json.dumps(prep), encoding="utf-8")
    s, f, d, t = c4.load_structure(path)
    assert t == tasks and d == days and s["EMB_MINILM"] == scores["EMB_MINILM"]
    rng = random.Random(5)
    for gain in (0, 3, 6, 9):
        planted = c4.plant(rng, s, f, t, 0.25, gain, 0.2)
        emb, lex = c4.fired_pairs(s["EMB_MINILM"], f["EMB_MINILM"], t, 0.2), c4.fired_pairs(s["LEX_KERNEL"], f["LEX_KERNEL"], t, 0.2)
        assert sum(1 for p in emb if planted[p] == "SAME") - sum(1 for p in lex if planted[p] == "SAME") == gain
    out = tmp_path / "c4.json"
    c4.main(["--prep", str(path), "--out", str(out), "--sets", "3", "--draws", "40"])
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["implementations_identical"] is True and set(report["gains"]) == {"0", "3", "6", "9"} and report["mismatches"] == 0
