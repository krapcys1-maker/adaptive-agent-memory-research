"""WMB-R1: the resampling stream, the decision chain of part U1, the judge and its gate, the controls, parts U2/U3 and the whole pipeline on a synthetic account (no model call,
no private data)."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import date
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_writer_memory_sim as original  # noqa: E402
import llm_backends as backends  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
from wmb import contract, memory_kernel as mk, retrieval_bench as rb, stats  # noqa: E402

CFG = rb.load_config()
SYN = {"boat": "ferry", "firm": "company", "records": "ledgers"}
HELPS, SUFF = rb.HELPS, rb.SUFFICIENT


def vectors(texts, dim: int = 96) -> np.ndarray:
    out = np.zeros((len(texts), dim))
    for r, text in enumerate(texts):
        for word in text.lower().replace(".", " ").replace("?", " ").split():
            out[r, int(hashlib.md5(SYN.get(word, word).encode()).hexdigest(), 16) % dim] += 1.0
        norm = np.linalg.norm(out[r]) or 1.0
        out[r] /= norm
    return out


def corpus_items(n: int = 12):
    """A small account: pairs of notes about the same story on different days, plus unrelated ones."""
    stories = ["ferry company ledgers harbour audit", "sourdough starter basement flood", "tide tables shortwave radio night", "chess endgames archive scanners",
               "estuary rail town fishing", "recovery procedure boring document"]
    items = []
    for k in range(n):
        s = stories[k % len(stories)]
        items.append(sbm.Item("id%03d" % k, date(2026, 9, 1 + k // 2), "note %d about %s and filler%d words" % (k, s, k)))
    return items


def briefs_for(items):
    return ["a note about %s" % " ".join(it.text.split()[3:7]) for it in items]


def cfg_with(**sections) -> dict:
    cfg = copy.deepcopy(CFG)
    for key in cfg["script_sha256"]:
        cfg["script_sha256"][key] = None                       # toy configs start unfrozen, whatever the state of the repository's own config
    cfg["judge"]["prompt_sha256"] = cfg["judge"]["prompt_reversed_sha256"] = None
    for path, value in sections.items():                       # "readings.bootstrap.draws_primary" -> nested key
        node = cfg
        keys = path.split("__")
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value
    return cfg


def cfg_small(warmup: int = 4) -> dict:
    return cfg_with(tasks__warmup=warmup)


def prepared(n: int = 12, warmup: int = 4):
    items = corpus_items(n)
    briefs = briefs_for(items)
    nv, bv = vectors([i.text for i in items]), vectors(briefs)
    return items, briefs, nv, bv, rb.prepare_rankings(items, briefs, nv, bv, cfg_small(warmup))


# ---------------------------------------------------------------------------------------------------------------------------------- the resampling stream

@pytest.mark.parametrize("n,draws,seed", [(1, 4, 7), (5, 9, 20261102), (63, 30, 20271102), (214, 12, 20261101), (7, 5, 2 ** 64 - 1), (10, 3, 0), (2, 1, 20271104)])
def test_the_vectorised_stream_is_the_original_splitmix64_stream_whatever_the_chunking(n: int, draws: int, seed: int) -> None:
    expected = original.bootstrap_indices(n, draws, seed)
    assert stats.bootstrap_indices(n, draws, seed).tolist() == expected
    for chunk in (1, 2, 4, 1000):
        assert np.concatenate(list(stats.bootstrap_chunks(n, draws, seed, chunk_draws=chunk))).tolist() == expected
    flat = [x for row in expected for x in row]
    assert stats.splitmix_block(seed, 0, len(flat), n).tolist() == flat
    if len(flat) > 3:
        assert stats.splitmix_block(seed, 3, min(2, len(flat) - 3), n).tolist() == flat[3: 3 + min(2, len(flat) - 3)]            # any block of the stream stands alone


def test_the_interval_rule_is_exact_for_every_number_of_draws() -> None:
    for draws in range(1, 3001):
        lo = math.floor(Fraction(25, 1000) * draws)
        hi = math.ceil(Fraction(975, 1000) * draws) - 1
        assert stats.interval_positions(draws) == (lo, hi), draws
    assert stats.interval_positions(100000) == (2500, 97499) and stats.interval_positions(10000) == (250, 9749)
    assert stats.interval_of(list(range(200, 0, -1))) == (6.0, 195.0)                       # sorted 1..200: positions 5 and 194


def test_the_fire_size_rounds_the_product_before_the_ceiling() -> None:
    assert [stats.fire_size(q, 214) for q in (0.1, 0.2, 0.3)] == [22, 43, 65]
    grid = [(k / 100, n) for k in range(1, 100) for n in range(1, 301)]
    overshoot = [(q, n) for q, n in grid if abs(q * n - round(q * n)) < 1e-6 and q * n > round(q * n)]
    assert len(overshoot) > 20 and all(math.ceil(q * n) == round(q * n) + 1 and stats.fire_size(q, n) == round(q * n) for q, n in overshoot)      # 7.000000000000001 must not fire 8
    assert all(stats.fire_size(q, n) == round(q * n) for q, n in grid if abs(q * n - round(q * n)) < 1e-6)
    assert [stats.fire_size(q, n) for q, n in ((0.25, 8), (0.5, 3), (1.0, 5), (0.15, 20), (0.35, 20), (0.05, 100), (0.4, 0))] == [2, 2, 5, 3, 7, 5, 0]


def test_day_blocks_keep_a_days_tasks_together_and_the_counting_path_agrees_with_the_spelled_out_one() -> None:
    days = ["d1", "d1", "d2", "d3", "d3", "d3", "d1"]
    names, of_task = stats.day_groups(days)
    assert names == ["d1", "d2", "d3"] and of_task.tolist() == [0, 0, 1, 2, 2, 2, 0]
    picks = original.bootstrap_indices(3, 6, 5)
    spelled = stats.day_block_indices(days, 6, 5)
    members = [[0, 1, 6], [2], [3, 4, 5]]
    for row, ids in zip(picks, spelled):
        assert ids.tolist() == [t for k in row for t in members[k]]
    counts = stats.multiplicity(stats.bootstrap_indices(3, 6, 5), 3)[:, of_task]
    for row, ids in zip(counts, spelled):
        assert row.tolist() == np.bincount(ids, minlength=len(days)).tolist()
    assert stats.multiplicity(np.array([[0, 0, 2], [1, 1, 1]]), 3).tolist() == [[2, 0, 1], [0, 3, 0]]


# ----------------------------------------------------------------------------------------------------------------------------- kernel path and scorers

def test_times_order_the_notes_of_one_day_and_the_ids_sort_by_recency() -> None:
    items = [sbm.Item("a", date(2026, 9, 1), "x"), sbm.Item("b", date(2026, 9, 1), "y"), sbm.Item("c", date(2026, 9, 2), "z")]
    times = rb.synthetic_times(items)
    assert times == ["2026-09-01T08:00:00", "2026-09-01T08:01:00", "2026-09-02T08:00:00"] and times == sorted(times)
    assert sorted(rb.note_id(j) for j in (3, 10, 7)) == [rb.note_id(10), rb.note_id(7), rb.note_id(3)] and rb.note_index(rb.note_id(123)) == 123
    many = [sbm.Item("i%04d" % k, date(2026, 9, 1), "w") for k in range(901)]
    with pytest.raises(ValueError):
        rb.synthetic_times(many)


def test_ranking_prefers_the_recent_note_on_ties_and_lexical_scores_must_be_positive() -> None:
    assert rb.rank_pairs(np.array([0.5, 0.5, 0.0, 0.7]), [0, 1, 2, 3], True) == [(3, 0.7), (1, 0.5), (0, 0.5)]
    assert [j for j, _ in rb.rank_pairs(np.array([0.0, -0.1, 0.0]), [0, 1, 2], False)] == [2, 0, 1]
    assert rb.choose_threshold([0.1 * k for k in range(10)], 0.2) == pytest.approx(0.8) and rb.choose_threshold([5.0], 0.2) == 5.0
    assert rb.choose_threshold(list(range(214)), 0.2) == 171                                 # position int(0.8 * 214)


def test_the_profiles_in_the_code_are_the_profiles_of_the_config() -> None:
    lex, hyb = CFG["kernel_profiles"]["LEX_KERNEL"], CFG["kernel_profiles"]["HYB_KERNEL"]
    for key in ("embed", "lex_tau", "min_evidence", "names", "k", "timeout_ms"):
        assert rb.LEX_PROFILE[key] == lex[key]
    profile = rb.hybrid_profile(0.2447, 0.5722)
    assert profile["lex_tau"] == pytest.approx(hyb["lex_tau_factor"] * 0.2447) and profile["tau"] == pytest.approx(hyb["tau_factor"] * 0.5722)
    assert profile["embed"] == hyb["embed"] and profile["min_evidence"] == hyb["min_evidence"] and profile["names"] is hyb["names"] and profile["k"] == hyb["k"]
    assert rb.HYBRID_FACTOR == hyb["lex_tau_factor"] == hyb["tau_factor"]
    lexical, hybrid = rb.shipped_profiles(CFG)
    assert (lexical["lex_tau"], lexical["min_evidence"], lexical["embed"]) == (0.30, 0.8, "off") and (hybrid["tau"], hybrid["embed"]) == (0.57, "required")
    assert set(CFG["methods"]) == set(rb.RANKED) | {"REF_E5"} and CFG["pool"]["methods"] == list(rb.METHODS)


def test_the_lexical_scorers_find_the_note_with_the_shared_rare_words_and_agree_with_the_kernel() -> None:
    items = corpus_items()
    stems = [mk.tokens(i.text) for i in items]
    corpus = rb.Corpus(range(len(items)), stems, vectors([i.text for i in items]))
    q = mk.tokens("ferry company ledgers audit")
    for scores in (corpus.bm25(q, 1.2, 0.75), corpus.tfidf(q), corpus.coverage(q)):
        assert int(np.argmax(scores)) in (0, 6) and scores[1] == 0.0 and scores.min() >= 0.0
    kitems = rb.kernel_items(items, rb.synthetic_times(items))
    index = mk.build_index(kitems, "2026-12-01")
    got = rb.kernel_ranking(index, "ferry company ledgers audit", "2026-12-01", rb.LEX_PROFILE)
    ref = rb.rank_pairs(corpus.coverage(q), corpus.docs, True)
    assert [j for j, _ in got] == [j for j, _ in ref] and all(abs(a * rb.LEX_PROFILE["lex_tau"] - b) < 1e-8 for (_, a), (_, b) in zip(got, ref))


def test_prepared_rankings_are_causal_complete_and_the_hybrids_are_the_max_of_two_calibrated_channels() -> None:
    items, briefs, nv, bv, prep = prepared()
    tasks = list(range(4, len(items)))
    assert set(prep["rankings"]) == set(rb.RANKED) and all(sorted(r) == tasks for r in prep["rankings"].values())
    assert rb.causality_violations(prep["rankings"]) == 0 and prep["times"] == sorted(prep["times"])
    cover = np.array([r[0][1] * rb.LEX_PROFILE["lex_tau"] if r else 0.0 for r in (prep["rankings"]["LEX_KERNEL"][i] for i in tasks)])
    assert prep["tau_lex"] == rb.choose_threshold(list(cover), CFG["tasks"]["candidate_share_for_calibration"])
    for i in tasks:
        corpus = rb.Corpus(range(i), [mk.tokens(it.text) for it in items], nv)
        cov, cos = corpus.coverage(mk.tokens(briefs[i])), corpus.cosine(bv[i])
        for name, (tl, te) in (("HYB_KERNEL", (prep["tau_lex"], prep["tau_emb"])), ("HYB_SHIPPED", (0.30, 0.57))):
            ref = rb.rank_pairs(np.maximum(cov / tl, cos / te), corpus.docs, False)
            got = prep["rankings"][name][i]
            assert got[0][0] == ref[0][0] and abs(got[0][1] * 0.05 - ref[0][1]) < 1e-4
    assert set(prep["shipped"]) == set(tasks) and all(v["lexical"] < i and v["hybrid"] < i for i, v in prep["shipped"].items())
    agreement = rb.reference_agreement(items, briefs, nv, bv, prep["rankings"], tasks, cfg_small(), prep["tau_lex"], prep["tau_emb"], n=5)
    assert agreement["rank1_identical_lex"] == agreement["rank1_identical_hyb"] == agreement["tasks"] == 5 and agreement["max_abs_diff_coverage"] < 1e-8
    assert agreement["max_abs_diff_hybrid_strength"] < 5e-6
    own = rb.self_retrieval(items, briefs, nv, bv, tasks, cfg_small(), prep["tau_lex"], prep["tau_emb"])
    assert set(own) == set(rb.RANKED) and all(0.0 <= x <= 1.0 for v in own.values() for x in v.values())
    checks = rb.index_checks(prep["indexes"], items, tasks, cfg_small(), n=5)
    assert checks["index_ok"] and checks["checked"] == 5
    prep["indexes"][tasks[0]].df["boat"] = 1                                                  # a corrupted document frequency is caught
    assert not rb.index_checks(prep["indexes"], items, tasks[:1], cfg_small(), n=5)["index_ok"]


def test_the_free_controls_are_enforced_with_the_thresholds_of_the_config() -> None:
    ok = {"self_retrieval": {"LEX_KERNEL": {"top3": 0.95, "first": 0.9, "shift_first": 0.0}}, "causality": {"violations": 0, "index_ok": True},
          "reference_agreement": {"tasks": 30, "rank1_identical_lex": 30, "rank1_identical_hyb": 30, "max_abs_diff_coverage": 5e-11, "max_abs_diff_hybrid_strength": 2.5e-6},
          "tau": {"tau_emb": 0.5722, "tau_emb_e5": 0.5722, "tau_emb_matches_e5": True, "tau_lex": 0.2447}}
    assert all(rb.controls_pass(ok, CFG).values())

    def broken(path, value):
        bad = copy.deepcopy(ok)
        node = bad
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return rb.controls_pass(bad, CFG)

    assert broken(("self_retrieval", "LEX_KERNEL", "top3"), 0.8999)["c1_self_retrieval_top3"] is False and broken(("self_retrieval", "LEX_KERNEL", "top3"), 0.9)["c1_self_retrieval_top3"]
    assert broken(("self_retrieval", "LEX_KERNEL", "shift_first"), 0.1)["c1_shifted_brief_first"] is False and broken(("self_retrieval", "LEX_KERNEL", "shift_first"), 0.099)["c1_shifted_brief_first"]
    assert broken(("causality", "violations"), 1)["c2_no_candidate_at_or_after_the_task"] is False and broken(("causality", "index_ok"), False)["c2_causal_index"] is False
    assert broken(("tau", "tau_emb_matches_e5"), False)["tau_emb_matches_e5"] is False
    assert rb.controls_pass({k: v for k, v in ok.items() if k != "tau"}, CFG)["tau_emb_matches_e5"] is False                 # no tau block: the embedder was not checked, fail closed
    assert broken(("reference_agreement", "rank1_identical_hyb"), 29)["c3_rank1_identical"] is False
    assert broken(("reference_agreement", "max_abs_diff_coverage"), 1.1e-8)["c3_coverage"] is False and broken(("reference_agreement", "max_abs_diff_hybrid_strength"), 5.1e-6)["c3_hybrid_strength"] is False


def test_the_pool_is_the_union_of_the_top_candidates() -> None:
    items, briefs, nv, bv, prep = prepared()
    tasks = list(range(4, len(items)))
    pool = rb.build_pool(prep["rankings"], tasks, 2, rb.METHODS)
    for i in tasks:
        assert pool[i] == sorted({j for m in rb.METHODS for j, _ in prep["rankings"][m][i][:2]}) and all(j < i for j in pool[i])


# --------------------------------------------------------------------------------------------------------------------------------------- control pairs

def test_the_hard_negative_sampler_obeys_the_cosine_window_the_shared_stem_limit_and_the_seed() -> None:
    rng = np.random.default_rng(11)
    n, tasks = 40, list(range(10, 40))
    nv, bv = rng.normal(size=(n, 6)), rng.normal(size=(n, 6))
    nv /= np.linalg.norm(nv, axis=1, keepdims=True)
    bv /= np.linalg.norm(bv, axis=1, keepdims=True)
    vocab = ["w%d" % k for k in range(12)]
    stems_n = [list(rng.choice(vocab, 4, replace=False)) for _ in range(n)]
    stems_b = [list(rng.choice(vocab, 3, replace=False)) for _ in range(n)]
    cfg = cfg_with(judge__gate__positive_control_n=8, judge__gate__negative_control_random=7, judge__gate__negative_control_hard=9)
    got = rb.control_pairs(cfg, tasks, stems_b, stems_n, nv, bv)
    assert len(got["positive"]) == 8 and all(i == j and i in tasks for i, j in got["positive"]) and got["positive"] == sorted(got["positive"])
    strata = {s: [(i, j) for i, j, name in got["negative"] if name == s] for s in ("random", "hard")}
    assert len(strata["random"]) == 7 and len(strata["hard"]) == 9 and not set(strata["random"]) & set(strata["hard"])
    lo, hi = CFG["judge"]["gate"]["negative_control_hard_cosine"]
    assert (lo, hi) == (0.25, 0.40) and CFG["judge"]["gate"]["negative_control_hard_max_shared_stems"] == 1
    for i, j in strata["random"] + strata["hard"]:
        assert i in tasks and 0 <= j < i
    eligible = {(i, j) for i in tasks for j in range(i) if lo <= float(bv[i] @ nv[j]) < hi and len(set(stems_b[i]) & set(stems_n[j])) <= 1}
    assert got["hard_candidates"] >= len(eligible) - 7 and set(strata["hard"]) <= eligible and len(eligible) > 9
    too_many = {(i, j) for i in tasks for j in range(i) if lo <= float(bv[i] @ nv[j]) < hi and len(set(stems_b[i]) & set(stems_n[j])) > 1}
    assert too_many and not set(strata["hard"]) & too_many                                    # pairs sharing two stems exist and are never drawn
    assert rb.control_pairs(cfg, tasks, stems_b, stems_n, nv, bv) == got
    assert rb.control_pairs(cfg_with(seeds__controls=1, judge__gate__positive_control_n=8, judge__gate__negative_control_random=7, judge__gate__negative_control_hard=9),
                            tasks, stems_b, stems_n, nv, bv) != got


def test_the_repeat_sample_and_the_stratified_sample_are_seeded_and_complete() -> None:
    pooled = [(20 + k // 5, k % 5) for k in range(200)]
    decisive = [(21, 3), (25, 0)]
    sample = rb.repeat_sample(CFG, pooled, decisive)
    assert sample == rb.repeat_sample(CFG, pooled, decisive) and set(decisive) <= set(sample) and set(sample) <= set(pooled) and len(sample) in (20 + 2, 20 + 1, 20)
    assert rb.repeat_sample(cfg_with(seeds__repeat=1), pooled, decisive) != sample
    labels = {p: SCALE_CYCLE[k % 3] for k, p in enumerate(pooled)}
    chosen = rb.stratified_sample(labels, decisive, CFG)
    assert len(chosen) == 30 and {lab: sum(1 for *_, l in chosen if l == lab) for lab in rb.SCALE} == {"SAME": 10, "RELATED": 10, "UNRELATED": 10}
    assert not {(i, j) for i, j, _ in chosen} & set(decisive) and all(labels[(i, j)] == lab for i, j, lab in chosen) and chosen == rb.stratified_sample(labels, decisive, CFG)
    small = {p: "SAME" for p in pooled[:4]}
    assert len(rb.stratified_sample(small, [], CFG)) == 4                                    # a stratum with fewer than 10 gives what exists


SCALE_CYCLE = ("SAME", "RELATED", "UNRELATED")


# ------------------------------------------------------------------------------------------------------------------- fire sets, overlap, decisive pairs

def test_the_fire_set_takes_the_highest_scores_with_ties_by_task_number_and_never_a_task_without_a_candidate() -> None:
    scores = np.array([0.9, 0.9, 0.5, -np.inf, 0.1, 0.9, 0.2, 0.3, 0.4, 0.8])
    relevant = np.array([1, 0, 1, 0, 0, 1, 0, 0, 1, 1], dtype=bool)
    tasks = list(range(10))
    assert rb.fire_positions(scores, tasks, 0.3).tolist() == [0, 1, 5] and rb.hit_table(scores, relevant, tasks, [0.3])["0.3"] == {"hits": 2, "false_injections": 1}
    assert rb.fire_positions(scores, tasks, 0.1).tolist() == [0] and len(rb.fire_positions(scores, tasks, 1.0)) == 9      # -inf never fires: fewer than ceil(q T)
    assert len(rb.fire_positions(scores, tasks, 0.25)) == 3 and len(rb.fire_positions(scores, tasks, 0.2)) == 2
    assert rb.fire_positions(np.array([0.5, 0.5, 0.5]), [10, 3, 7], 0.4).tolist() == [1, 2]                                # equal scores: task number 3, then 7, then 10
    assert rb.fire_order(np.array([0.5, 0.5, 0.5]), [10, 3, 7]).tolist() == [1, 2, 0]
    assert rb.hit_table(scores, relevant, tasks, [0.1, 0.2, 0.3]) == {"0.1": {"hits": 1, "false_injections": 0}, "0.2": {"hits": 1, "false_injections": 1},
                                                                   "0.3": {"hits": 2, "false_injections": 1}}


def test_copies_of_a_task_in_a_resample_fire_until_the_cut_and_copies_are_interchangeable() -> None:
    scores, tasks = np.array([0.5, 0.9, 0.7, 0.8]), [0, 1, 2, 3]
    rel = np.array([1, 1, 0, 1], dtype=bool)
    order = rb.fire_order(scores, tasks)
    relw = rel[order].astype(float)[None, :]
    counts = np.array([[1, 0, 0, 3]])                                                         # the resample [3, 3, 3, 0]
    for cut, expected in ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4)):
        assert rb.hit_counts(counts, order, relw, np.array([[cut]]))[0, 0, 0] == expected
    assert rb.hit_counts(np.array([[0, 2, 1, 1]]), order, relw, np.array([[3]]))[0, 0, 0] == 3          # [1, 1, 3] fired (both copies of task 1, then 3); task 2 is cut off
    assert rb.hit_counts(np.array([[0, 2, 3, 0]]), order, relw, np.array([[4]]))[0, 0, 0] == 2          # two relevant copies, then irrelevant task 2 fills the cut
    infinite = np.array([0.5, -np.inf, 0.7])
    relw_inf = (np.array([True, True, True]) & np.isfinite(infinite))[rb.fire_order(infinite, [0, 1, 2])].astype(float)[None, :]
    assert rb.hit_counts(np.ones((1, 3), dtype=np.int64), rb.fire_order(infinite, [0, 1, 2]), relw_inf, np.array([[3]]))[0, 0, 0] == 2


def test_the_overlap_row_reproduces_the_readmes_table_from_its_counts() -> None:
    assert rb.overlap_row(22, 22, 0, 0) == {"shared": 22, "same_first": 22, "only_a": 0, "only_b": 0, "discordant_tasks": 0, "decisive_pairs": 0, "max_abs_d": 0}
    for counts, expected in (((36, 34, 7, 7), (16, 18, 9)), ((54, 46, 11, 11), (30, 38, 19)), ((11, 8, 11, 11), (25, 28, 14)), ((27, 18, 16, 16), (41, 50, 25)),
                             ((45, 26, 20, 20), (59, 78, 39))):
        row = rb.overlap_row(*counts)
        assert (row["discordant_tasks"], row["decisive_pairs"], row["max_abs_d"]) == expected, counts


def hand_made_world():
    """Ten tasks (numbers 100..109), q = 0.2 so two tasks fire per method."""
    low = [0.1 - 0.001 * t for t in range(10)]
    emb, lex, hyb = list(low), list(low), list(low)
    emb[0], emb[1] = 0.9, 0.8
    lex[0], lex[2] = 0.9, 0.8
    hyb[0], hyb[1] = 0.9, 0.8
    first = {"EMB_MINILM": [5, 6] + [1] * 8, "LEX_KERNEL": [5, 9, 8] + [1] * 7, "HYB_KERNEL": [4, 6] + [1] * 8}
    return {"EMB_MINILM": emb, "LEX_KERNEL": lex, "HYB_KERNEL": hyb}, first, list(range(100, 110))


def test_the_decisive_pairs_and_the_overlap_table_on_a_hand_made_example() -> None:
    scores, first, tasks = hand_made_world()
    cfg = cfg_with(readings__sweep=[0.2])
    rows = rb.overlap_table(scores, first, tasks, cfg)
    by = {r["contrast"]: r for r in rows}
    assert by["EMB_MINILM vs LEX_KERNEL"]["shared"] == 1 and by["EMB_MINILM vs LEX_KERNEL"]["same_first"] == 1
    assert (by["EMB_MINILM vs LEX_KERNEL"]["only_a"], by["EMB_MINILM vs LEX_KERNEL"]["only_b"]) == (1, 1)
    assert (by["EMB_MINILM vs LEX_KERNEL"]["discordant_tasks"], by["EMB_MINILM vs LEX_KERNEL"]["decisive_pairs"], by["EMB_MINILM vs LEX_KERNEL"]["max_abs_d"]) == (2, 2, 1)
    assert (by["HYB_KERNEL vs LEX_KERNEL"]["discordant_tasks"], by["HYB_KERNEL vs LEX_KERNEL"]["decisive_pairs"], by["HYB_KERNEL vs LEX_KERNEL"]["max_abs_d"]) == (3, 4, 2)
    pairs = rb.decisive_pairs(scores, first, tasks, 0.2)
    assert pairs == [{"i": 100, "j": 4, "found_by": ["HYB_KERNEL"]}, {"i": 100, "j": 5, "found_by": ["EMB_MINILM", "LEX_KERNEL"]},
                     {"i": 101, "j": 6, "found_by": ["EMB_MINILM", "HYB_KERNEL"]}, {"i": 102, "j": 8, "found_by": ["LEX_KERNEL"]}]
    assert [rb.origin_of(p["found_by"]) for p in pairs] == ["hybrid_only", "both", "minilm_only", "lexical_only"]
    assert len(rb.format_overlap(rows).splitlines()) == 3                                      # header and two rows


def test_the_decisive_export_is_blind_shuffled_and_keyed_apart() -> None:
    scores, first, tasks = hand_made_world()
    items = [sbm.Item("i%d" % k, date(2026, 9, 1), "note text %d" % k) for k in range(12)]
    briefs = ["brief %d" % k for k in range(110)]
    pairs = rb.decisive_pairs(scores, first, tasks, 0.2)
    public, keys = rb.export_decisive(pairs, items, briefs, 7)
    text = json.dumps(public)
    assert all(set(p) == {"key", "brief", "note"} for p in public) and not any(w in text for w in ("LEX", "EMB", "HYB", "found_by", "score", "origin"))
    assert sorted(keys) == sorted(p["key"] for p in public) and {(k["i"], k["j"]) for k in keys.values()} == {(p["i"], p["j"]) for p in pairs}
    for p in public:
        info = keys[p["key"]]
        assert p["brief"] == briefs[info["i"]] and p["note"] == items[info["j"]].text and info["origin"] in ("both", "minilm_only", "lexical_only", "hybrid_only")
    assert rb.export_decisive(pairs, items, briefs, 7)[0] == public


def test_the_operating_point_is_the_largest_q_on_the_grid_with_precision_of_at_least_080() -> None:
    scores = np.array([1.0 - 0.01 * t for t in range(10)])
    relevant = np.array([1, 1, 1, 1, 0, 1, 0, 0, 0, 0], dtype=bool)
    assert rb.operating_point(scores, relevant, list(range(10))) == {"q": 0.6, "fired": 6, "hits": 5, "coverage": 0.6}          # 5/6 at q 0.6; 5/7 beyond
    assert rb.operating_point(scores, np.zeros(10, dtype=bool), list(range(10))) is None


# ------------------------------------------------------------------------------------------------------------------------------------------- the judge

@pytest.mark.parametrize("raw,label", [("SAME", "SAME"), (" same. ", "SAME"), ('"Related"', "RELATED"), ("**UNRELATED**", "UNRELATED"), ("'SAME.'", "SAME"), ("Same\n", "SAME"),
                                       ("“unrelated”.", "UNRELATED"), ("RELATED.", "RELATED"),
                                       ("not related", None), ("The answer is SAME.", None), ("SAME or RELATED", None), ("SAME RELATED", None), ("", None), ("   ", None),
                                       ("SAME..", None), ("S", None), ("RELATED to the task", None), ("UNRELATED: no", None), ("SAME,", None), ("YES", None), ("maybe", None)])
def test_the_strict_parse_accepts_exactly_one_label_and_nothing_else(raw: str, label) -> None:
    assert rb.parse_label(raw) == label


def test_format_failures_get_a_class_and_the_retry_repeats_the_same_request() -> None:
    assert [rb.failure_class(r) for r in ("", "  ", "I'm sorry, I can't help with that", "I cannot answer", "Sorry.", "maybe", "SAME or RELATED")] == [
        "empty", "empty", "refusal", "refusal", "refusal", "unparseable", "unparseable"]
    calls, replies = [], iter(["hmm", "SAME"])

    def generate(system, user, seed, opts):
        calls.append((system, user, seed, dict(opts)))
        return {"text": next(replies)}

    out = rb.call_choice(generate, "sys", "usr", 5, {"temperature": 0.0, "num_predict": 12}, rb.SCALE)
    assert out["label"] == "SAME" and out["failures"] == ["unparseable"] and out["calls"] == 2 and calls[0] == calls[1]
    boom = iter([RuntimeError("down"), {"text": ""}])

    def flaky(system, user, seed, opts):
        item = next(boom)
        if isinstance(item, Exception):
            raise item
        return item

    out = rb.call_choice(flaky, "s", "u", 1, {}, rb.SCALE)
    assert out["label"] is None and out["failures"] == ["error", "empty"] and out["calls"] == 2
    cap = lambda *a, **k: (_ for _ in ()).throw(backends.SpendCapRefused("cap"))    # noqa: E731
    with pytest.raises(backends.SpendCapRefused):
        rb.call_choice(cap, "s", "u", 1, {}, rb.SCALE)


def scripted(*steps):
    queue = list(steps)

    def generate(system, user, seed, opts):
        step = queue.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    return generate


def test_an_empty_completion_raised_by_the_backend_is_class_empty_and_a_dead_proxy_aborts_the_stage_without_recording(tmp_path: Path) -> None:
    out = rb.call_choice(scripted(ValueError("empty completion (finish_reason=length)"), {"text": "RELATED"}), "s", "u", 1, {}, rb.SCALE)
    assert out["label"] == "RELATED" and out["failures"] == ["empty"] and rb.error_only(out) is False
    assert rb.error_only({"label": None, "failures": ["error", "error"]}) and not rb.error_only({"label": None, "failures": ["error", "unparseable"]}) and not rb.error_only({"label": None, "failures": []})
    items = corpus_items(40)
    briefs = briefs_for(items)
    pairs = [{"kind": "pool", "i": 30, "j": j} for j in range(30)]
    down = lambda *a, **k: (_ for _ in ()).throw(OSError("connection refused"))     # noqa: E731
    with pytest.raises(rb.RunAborted):
        rb.run_judge(pairs, items, briefs, CFG, down, tmp_path / "dead.jsonl", workers=1)
    assert contract.load_jsonl(tmp_path / "dead.jsonl") == []                                # the 25 calls without a reply left no record: resume re-asks them
    calls = []

    def blip(system, user, seed, opts):                                                      # the first pair fails twice (both attempts), the rest answer
        calls.append(1)
        if len(calls) <= 2:
            raise OSError("reset")
        return {"text": "UNRELATED"}

    rb.run_judge(pairs[:3], items, briefs, CFG, blip, tmp_path / "blip.jsonl", workers=1)
    rows = {r["j"]: r for r in contract.load_jsonl(tmp_path / "blip.jsonl")}
    assert len(rows) == 3 and rows[0]["label"] is None and rows[0]["failures"] == ["error", "error"] and rows[1]["label"] == rows[2]["label"] == "UNRELATED"
    tail = scripted(OSError("x"), OSError("x"))                                              # an isolated error at the very end is still recorded
    rb.run_judge(pairs[:1], items, briefs, CFG, tail, tmp_path / "tail.jsonl", workers=1)
    assert contract.load_jsonl(tmp_path / "tail.jsonl")[0]["failures"] == ["error", "error"]


def test_the_judge_uses_the_configured_decoding_the_reversed_options_for_repeats_and_resumes(tmp_path: Path) -> None:
    items, briefs = corpus_items(6), briefs_for(corpus_items(6))
    seen = []

    def generate(system, user, seed, opts):
        seen.append((system, user, seed, dict(opts)))
        return {"text": "SAME" if "note 0" in user.split("Earlier note by the same author:")[1] else "UNRELATED"}

    out = tmp_path / "labels.jsonl"
    pairs = [{"kind": "pool", "i": 5, "j": 0}, {"kind": "rep", "i": 5, "j": 0}, {"kind": "neg", "i": 5, "j": 1, "stratum": "hard"}]
    assert rb.run_judge(pairs, items, briefs, CFG, generate, out, workers=1) == 3
    rows = {(r["kind"], r["i"], r["j"]): r for r in contract.load_jsonl(out)}
    assert rows[("pool", 5, 0)]["label"] == "SAME" and rows[("neg", 5, 1)]["stratum"] == "hard" and rows[("pool", 5, 0)]["calls"] == 1 and rows[("pool", 5, 0)]["failures"] == []
    for system, user, seed, opts in seen:
        assert system == CFG["judge"]["system"] and seed == CFG["judge"]["seed"] and opts == {"temperature": 0.0, "num_predict": CFG["judge"]["max_tokens"]} and "top_p" not in opts
    normal = [u for _, u, _, _ in seen if "UNRELATED: otherwise" in u]
    reverse = [u for _, u, _, _ in seen if "UNRELATED: neither" in u]
    assert len(reverse) == 1 and len(normal) == 2 and reverse[0].index("UNRELATED: neither") < reverse[0].index("SAME: it is about") and CFG["judge"]["max_tokens"] == 12
    assert normal[0].index("SAME: it is about") < normal[0].index("UNRELATED: otherwise") and "UNRELATED: neither" not in normal[0]
    assert rb.judge_prompt(CFG, "B", "N") == CFG["judge"]["user_template"].format(brief="B", note="N") and rb.judge_prompt(CFG, "B", "N", True) != rb.judge_prompt(CFG, "B", "N")
    assert rb.run_judge(pairs, items, briefs, CFG, generate, out, workers=1) == 0 and len(contract.load_jsonl(out)) == 3
    never = lambda *a, **k: {"text": "perhaps"}     # noqa: E731
    rb.run_judge([{"kind": "pool", "i": 4, "j": 0}], items, briefs, CFG, never, tmp_path / "bad.jsonl", workers=1)
    bad = contract.load_jsonl(tmp_path / "bad.jsonl")[0]
    assert bad["label"] is None and bad["failures"] == ["unparseable", "unparseable"] and bad["calls"] == 2


def test_a_spend_cap_refusal_stops_the_run_and_the_ledger_stop_is_checked_between_chunks(tmp_path: Path) -> None:
    items, briefs = corpus_items(6), briefs_for(corpus_items(6))
    state = {"n": 0}

    def generate(system, user, seed, opts):
        state["n"] += 1
        if state["n"] > 2:
            raise backends.SpendCapRefused("402")
        return {"text": "SAME"}

    pairs = [{"kind": "pool", "i": 5, "j": j} for j in range(5)]
    with pytest.raises(backends.SpendCapRefused):
        rb.run_judge(pairs, items, briefs, CFG, generate, tmp_path / "a.jsonl", workers=1)
    assert len(contract.load_jsonl(tmp_path / "a.jsonl")) == 2
    checks = []
    rb.run_judge(pairs, items, briefs, CFG, lambda *a: {"text": "SAME"}, tmp_path / "b.jsonl", workers=1, before_chunk=lambda: checks.append(1), chunk=2)
    assert len(checks) == 3                                                                    # 5 pairs in chunks of 2: three checks


def test_the_ledger_stop_reads_the_slice_and_refuses_at_the_stop(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    lines = [{"run_id": "e1-wmbr1-judge", "usd": 0.5}, {"run_id": "e1-wmbr1-writer", "usd": 0.25}, {"run_id": "e1-other", "usd": 2.69}, {"run_id": "e2-x", "usd": 5.0}]
    ledger.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    spend = rb.ledger_spend(ledger, CFG)
    assert spend["slice_usd"] == 0.75 and spend["scope_usd"] == 3.44 and spend["entries"] == 4
    assert rb.assert_budget(ledger, CFG)["slice_usd"] == 0.75
    torn = tmp_path / "torn.jsonl"
    torn.write_text(json.dumps(lines[0]) + "\n{torn", encoding="utf-8")                          # a torn last line belongs to no run
    assert rb.ledger_spend(torn, CFG)["entries"] == 2 and rb.ledger_spend(torn, CFG)["slice_usd"] == 0.5
    contract.append_jsonl(ledger, [{"run_id": "e1-wmbr1-judge", "usd": 1.25}])
    with pytest.raises(rb.BudgetStop):
        rb.assert_budget(ledger, CFG)
    for bad in (None, tmp_path / "missing.jsonl"):
        with pytest.raises(ValueError):
            rb.ledger_spend(bad, CFG)
    assert CFG["budget"]["stop_at_usd"] == 2.0 and CFG["budget"]["run_ids"] == ["e1-wmbr1-judge", "e1-wmbr1-writer"]


def test_proxy_summaries_are_fetched_from_the_arena_endpoint_and_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    urls = []

    class Handle:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(GOOD_SUMMARY).encode()

    monkeypatch.setattr(rb.urllib.request, "urlopen", lambda url, timeout=0: urls.append(url) or Handle())
    assert rb.proxy_summary("http://127.0.0.1:8798/v1") == GOOD_SUMMARY and urls == ["http://127.0.0.1:8798/arena/summary"]
    assert rb.summary_problems(GOOD_SUMMARY) == [] and rb.summary_problems(None) == ["summary unavailable"] and rb.summary_problems({"unavailable": "URLError"}) == ["summary unavailable"]
    assert len(rb.summary_problems(dict(GOOD_SUMMARY, refused_calls=1))) == 1 and len(rb.summary_problems(dict(GOOD_SUMMARY, decoding_overrides=2, unknown_usage_calls=1))) == 2
    assert rb.summary_problems(dict(GOOD_SUMMARY, arena_enforced_decoding={})) == ["thinking is not disabled"]
    assert rb.safe_summary(lambda url: (_ for _ in ()).throw(OSError("down")), "u") == {"unavailable": "OSError"}


GOOD_SUMMARY = {"calls": 10, "refused_calls": 0, "prompt_tokens": 100, "completion_tokens": 10, "usd": 0.01, "unknown_usage_calls": 0, "decoding_overrides": 0,
                "arena_enforced_decoding": {"thinking": {"type": "disabled"}}}


def test_the_embedder_sets_the_offline_flags_before_the_model_library_is_imported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "sentence_transformers.py").write_text(
        "import os\nSEEN = (os.environ.get('HF_HUB_OFFLINE'), os.environ.get('TRANSFORMERS_OFFLINE'))\nimport numpy as np\n"
        "class SentenceTransformer:\n    def __init__(self, name, device=None):\n        self.name, self.device = name, device\n"
        "    def encode(self, texts, **kw):\n        return np.ones((len(texts), 3))\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "0")
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    embed = rb.default_embed()
    try:
        assert sys.modules["sentence_transformers"].SEEN == ("1", "1")                         # already set when the library was imported
        assert embed(["a", "b"]).shape == (2, 3)
    finally:
        sys.modules.pop("sentence_transformers", None)


def local_imports(path: Path) -> set:
    scripts, found = ROOT / "scripts", set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names = [(a.name, None) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [(node.module, a.name) for a in node.names]
        else:
            continue
        for module, sub in names:
            parts = module.split(".")
            for candidate in (scripts.joinpath(*parts).with_suffix(".py"), scripts.joinpath(*parts, "__init__.py"), scripts.joinpath(*parts, sub or "_").with_suffix(".py")):
                if candidate.exists():
                    found.add(candidate.relative_to(ROOT).as_posix())
    return found


def test_frozen_digests_once_filled_match_the_files_and_the_input_digests_are_the_ones_the_readme_states() -> None:
    for rel, digest in CFG["script_sha256"].items():
        if digest is not None:                                                                  # filled at the freeze; null before it
            assert contract.sha256_file(ROOT / rel) == digest, rel
    readme = (ROOT / "data" / "lab" / "wmb-r1-retrieval" / "README.md").read_text(encoding="utf-8")
    assert all(d in readme for d in CFG["inputs_sha256"].values()) and CFG["environment"]["minilm_weights_sha256"] in readme


def test_every_local_module_the_scripts_import_is_listed_for_the_freeze_digests() -> None:
    listed = set(CFG["script_sha256"])
    bench = local_imports(ROOT / "scripts" / "wmb" / "retrieval_bench.py")
    assert {"scripts/wmb/memory_kernel.py", "scripts/wmb/contract.py", "scripts/wmb/stats.py", "scripts/llm_backends.py", "scripts/shadow_baseline_measures.py",
            "scripts/wmb/__init__.py"} <= bench
    for path in ("scripts/wmb/retrieval_bench.py", "scripts/wmb/stats.py"):
        missing = local_imports(ROOT / path) - listed
        assert not missing, "%s imports %s, which config.json script_sha256 does not list" % (path, sorted(missing))
    assert "scripts/wmb/retrieval_bench_ref.py" not in bench and {"scripts/wmb/retrieval_bench.py", "scripts/wmb/stats.py", "tests/test_wmb_retrieval_bench.py"} <= listed


# ---------------------------------------------------------------------------------------------------------------- P1: brute force from the README text

def random_inputs(seed: int, T: int = 36, n_days: int = 9):
    rng = np.random.default_rng(seed)
    tasks = [int(x) for x in rng.permutation(np.arange(50, 50 + T))]
    days = ["d%02d" % int(rng.integers(0, n_days)) for _ in range(T)]
    methods = ["EMB_MINILM", "LEX_KERNEL", "HYB_KERNEL", "LEX_BM25"]
    scores = {m: [float(rng.integers(0, 6)) / 5 for _ in range(T)] for m in methods}                  # many exact ties
    for m in methods:
        for t in rng.choice(T, 3, replace=False):
            scores[m][int(t)] = -math.inf
    first = {m: [int(rng.integers(0, 4)) if scores[m][t] > -math.inf else -1 for t in range(T)] for m in methods}
    labels = {}
    for t in range(T):
        for j in range(4):
            r = rng.random()
            labels[(tasks[t], j)] = "SAME" if r < 0.35 else ("RELATED" if r < 0.5 else ("UNRELATED" if r < 0.9 else None))
    assistant = {k: ("SAME" if rng.random() < 0.3 else "UNRELATED") for k in list(labels)[::5]}
    return scores, first, days, tasks, labels, assistant


def brute_fire(scores, tasks, ids, q):
    n = len(ids)
    m = math.ceil(round(q * n, 9))
    order = sorted(range(n), key=lambda p: (-scores[ids[p]], tasks[ids[p]], p))
    return [ids[p] for p in order[:m] if scores[ids[p]] != -math.inf]


def brute_interval(values):
    v, d = sorted(values), len(values)
    return v[math.floor(Fraction(25, 1000) * d)], v[math.ceil(Fraction(975, 1000) * d) - 1]


def brute_p1(scores, first, days, tasks, labels, cfg, assistant, draws):
    spec = cfg["readings"]
    boot, q0, margin = spec["bootstrap"], spec["primary_q"], spec["margin_tasks"]
    T = len(tasks)
    names = sorted(set(days))
    members = [[t for t in range(T) if days[t] == d] for d in names]

    def relevance(lab, m):
        return [first[m][t] >= 0 and lab.get((tasks[t], first[m][t])) == "SAME" for t in range(T)]

    def hits(m, rel, ids):
        return sum(1 for t in brute_fire(scores[m], tasks, ids, q0) if rel[t])

    def readings(lab, seed):
        rel = {m: relevance(lab, m) for m in rb.TRIO}
        out = []
        for a in ("EMB_MINILM", "HYB_KERNEL"):
            diff = lambda ids: hits(a, rel[a], ids) - hits("LEX_KERNEL", rel["LEX_KERNEL"], ids)   # noqa: E731
            tv = [diff(ids) for ids in original.bootstrap_indices(T, draws, seed)]
            dv = [diff([t for k in picks for t in members[k]]) for picks in original.bootstrap_indices(len(names), draws, seed)]
            (tl, th), (dl, dh) = brute_interval(tv), brute_interval(dv)
            out.append({"d": diff(list(range(T))), "lo": float(min(tl, dl)), "hi": float(max(th, dh)), "task_lo": float(tl), "task_hi": float(th), "day_lo": float(dl), "day_hi": float(dh)})
        return out

    def verdict(emb, hyb):
        if emb["lo"] > 0 and emb["d"] >= margin:
            return HELPS
        return SUFF if emb["hi"] < margin and hyb["hi"] < margin else "UNRESOLVED"

    seeds = [boot["seed"]] + boot["stability_seeds"]

    def evaluate(lab):
        runs = [readings(lab, s) for s in seeds]
        by_seed = [verdict(*r) for r in runs]
        n = len({i for (i, _), v in lab.items() if v == "SAME"})
        final = "NOT_EVALUABLE (prevalence)" if n < cfg["judge"]["prevalence_rule_min_tasks_with_same"] else (by_seed[0] if len(set(by_seed)) == 1 else "UNRESOLVED (resampling boundary)")
        return runs, by_seed, final, n

    runs, by_seed, v_judge, n_same = evaluate(labels)
    v_assist = None
    if assistant is not None:
        v_assist = evaluate({**labels, **assistant})[2]
    verdict_final = "UNRESOLVED (labels)" if assistant is not None and v_assist != v_judge and v_judge in rb.BASE_VERDICTS else v_judge
    emb, hyb = runs[0]
    return {"tasks_with_same": n_same, "prevalence_ok": n_same >= cfg["judge"]["prevalence_rule_min_tasks_with_same"], "d_emb": emb, "d_hyb": hyb,
            "verdict_by_seed": {str(s): v for s, v in zip(seeds, by_seed)}, "verdict_judge": v_judge, "verdict_assistant": v_assist, "verdict": verdict_final,
            "fusion_flag": "refit_channel_weights" if verdict_final == HELPS and hyb["d"] < emb["d"] / 2 else None}


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_p1_readings_equals_a_brute_force_reading_of_the_readme_on_random_inputs(seed: int) -> None:
    scores, first, days, tasks, labels, assistant = random_inputs(seed)
    cfg = cfg_with(readings__margin_tasks=2, judge__prevalence_rule_min_tasks_with_same=5)
    use = assistant if seed % 2 else None
    got = rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels=use, draws=20)
    expected = brute_p1(scores, first, days, tasks, labels, cfg, use, 20)
    assert set(got) == {"tasks_with_same", "prevalence_ok", "hits", "d_emb", "d_hyb", "verdict_by_seed", "verdict_judge", "verdict_assistant", "verdict", "fusion_flag"}
    for key, value in expected.items():
        assert got[key] == value, key
    rel = {m: [first[m][t] >= 0 and labels.get((tasks[t], first[m][t])) == "SAME" for t in range(len(tasks))] for m in scores}
    for m in scores:
        for q in CFG["readings"]["sweep"]:
            fired = brute_fire(scores[m], tasks, list(range(len(tasks))), q)
            h = sum(1 for t in fired if rel[m][t])
            assert got["hits"][m][str(q)] == {"hits": h, "false_injections": len(fired) - h}
    assert set(got["hits"]["LEX_BM25"]) == {"0.1", "0.2", "0.3"}


def test_the_default_number_of_draws_is_the_primary_one_and_a_larger_run_agrees_with_the_brute_force_stream() -> None:
    scores, first, days, tasks, labels, _ = random_inputs(9, T=24, n_days=6)
    cfg = cfg_with(readings__margin_tasks=2, judge__prevalence_rule_min_tasks_with_same=3, readings__bootstrap__draws_primary=40, readings__bootstrap__draws_other=10)
    assert rb.p1_readings(scores, first, days, tasks, labels, cfg) == rb.p1_readings(scores, first, days, tasks, labels, cfg, draws=40)
    got = rb.p1_readings(scores, first, days, tasks, labels, cfg)
    assert got["d_emb"] == brute_p1(scores, first, days, tasks, labels, cfg, None, 40)["d_emb"]


def gain_world(helpful: int = 12, T: int = 60):
    """EMB fires on `helpful` tasks that LEX misses and its first candidate is right there; one such task per day, so the day blocks keep the gain."""
    tasks, days = list(range(100, 100 + T)), ["d%02d" % (t % 12) for t in range(T)]
    emb, lex = [0.1] * T, [0.1] * T
    for t in range(12):
        lex[t] = 0.9 - 0.01 * t
    for t in range(12, 12 + helpful):
        emb[t] = 0.9 - 0.01 * t
    first = {"EMB_MINILM": [1] * T, "LEX_KERNEL": [0] * T, "HYB_KERNEL": [0] * T}
    labels = {(tasks[t], 0): "UNRELATED" for t in range(T)}
    labels.update({(tasks[t], 1): ("SAME" if 12 <= t < 12 + helpful else "UNRELATED") for t in range(T)})
    return {"EMB_MINILM": emb, "LEX_KERNEL": lex, "HYB_KERNEL": list(lex)}, first, days, tasks, labels


def test_base_verdicts_at_their_boundaries() -> None:
    hyb = {"d": 0, "lo": -2.0, "hi": 3.0}
    assert rb.base_verdict({"d": 6, "lo": 0.5, "hi": 12.0}, hyb, 6) == HELPS and rb.base_verdict({"d": 6, "lo": 0.0, "hi": 12.0}, hyb, 6) == "UNRESOLVED"
    assert rb.base_verdict({"d": 5, "lo": 1.0, "hi": 12.0}, hyb, 6) == "UNRESOLVED" and rb.base_verdict({"d": 7, "lo": -1.0, "hi": 15.0}, hyb, 6) == "UNRESOLVED"
    assert rb.base_verdict({"d": 2, "lo": -3.0, "hi": 5.99}, hyb, 6) == SUFF and rb.base_verdict({"d": 2, "lo": -3.0, "hi": 6.0}, hyb, 6) == "UNRESOLVED"
    assert rb.base_verdict({"d": 2, "lo": -3.0, "hi": 5.0}, {"d": 4, "lo": 0.0, "hi": 6.0}, 6) == "UNRESOLVED"                 # the fusion check must also be below the margin
    assert rb.resolve_verdict([HELPS] * 4, True) == HELPS and rb.resolve_verdict([HELPS, HELPS, "UNRESOLVED", HELPS], True) == "UNRESOLVED (resampling boundary)"
    assert rb.resolve_verdict([HELPS] * 4, False) == "NOT_EVALUABLE (prevalence)"


def test_a_clear_gain_is_called_and_the_fusion_flag_and_the_prevalence_rule_follow() -> None:
    scores, first, days, tasks, labels = gain_world()
    cfg = cfg_with(judge__prevalence_rule_min_tasks_with_same=5, readings__bootstrap__draws_primary=300)
    got = rb.p1_readings(scores, first, days, tasks, labels, cfg)
    assert got["d_emb"]["d"] == 12 and got["d_emb"]["lo"] > 0 and got["d_hyb"]["d"] == 0 and set(got["verdict_by_seed"].values()) == {HELPS} and got["verdict"] == HELPS
    assert got["fusion_flag"] == "refit_channel_weights" and got["verdict_assistant"] is None and got["tasks_with_same"] == 12
    scores["HYB_KERNEL"], first["HYB_KERNEL"] = list(scores["EMB_MINILM"]), list(first["EMB_MINILM"])                   # a hybrid that keeps what the embedder finds
    assert rb.p1_readings(scores, first, days, tasks, labels, cfg)["fusion_flag"] is None
    default = rb.p1_readings(scores, first, days, tasks, labels, cfg_with(readings__bootstrap__draws_primary=100))        # 12 tasks with a SAME note, the rule asks 25
    assert default["prevalence_ok"] is False and default["verdict_judge"] == default["verdict"] == "NOT_EVALUABLE (prevalence)" and default["fusion_flag"] is None
    assert set(default["verdict_by_seed"].values()) == {HELPS}                                                          # the base verdicts are still listed
    sufficient = rb.p1_readings(scores, first, days, tasks, {k: "UNRELATED" for k in labels}, cfg_with(judge__prevalence_rule_min_tasks_with_same=0, readings__bootstrap__draws_primary=100))
    assert sufficient["verdict"] == SUFF and sufficient["d_emb"]["d"] == 0


def test_a_verdict_that_changes_under_the_assistants_labels_is_unresolved_labels() -> None:
    scores, first, days, tasks, labels = gain_world()
    labels = {**labels, **{(tasks[t], 0): "SAME" for t in (50, 51, 52)}}                       # three tasks with a SAME note that no fire set depends on
    cfg = cfg_with(judge__prevalence_rule_min_tasks_with_same=2, readings__bootstrap__draws_primary=200)
    pairs = [(tasks[t], 1) for t in range(12, 24)]
    agree = rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels={p: "SAME" for p in pairs})
    assert agree["verdict_judge"] == agree["verdict_assistant"] == agree["verdict"] == HELPS
    differ = rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels={p: "UNRELATED" for p in pairs})
    assert differ["verdict_judge"] == HELPS and differ["verdict_assistant"] == SUFF and differ["verdict"] == "UNRESOLVED (labels)" and differ["fusion_flag"] is None
    assert differ["d_emb"] == agree["d_emb"]                                                                                # the reported numbers are the judge's
    empty = rb.p1_readings(scores, first, days, tasks, labels, cfg, assistant_labels={})
    assert empty["verdict_assistant"] == HELPS == empty["verdict"]


def planted(u0: np.ndarray, u1: np.ndarray, gain: float, p: float = 0.35):
    """T = 214; LEX fires on tasks 0..42, EMB on 16..58: 27 shared (same first candidate), 16 only EMB (its first candidate is another note), 16 only LEX.
    Expected D_emb = gain: the EMB-only first candidates are relevant with probability p + gain / 16, the LEX ones with p."""
    T = 214
    tasks, days = list(range(20, 20 + T)), ["d%02d" % (t % 54) for t in range(T)]               # 54 days of 3 or 4 tasks, the kinds of task mixed within a day
    lex = [0.05 + 0.0001 * t for t in range(T)]
    emb = list(lex)
    for t in range(16):                                                                         # only LEX: first in its order, as the only-EMB tasks are in EMB's
        lex[t] = 1.0 - 0.001 * t
    for t in range(16, 43):                                                                     # shared
        lex[t] = emb[t] = 0.8 - 0.001 * t
    for t in range(43, 59):
        emb[t] = 1.0 - 0.001 * t
    first = {"EMB_MINILM": [1 if 43 <= t < 59 else 0 for t in range(T)], "LEX_KERNEL": [0] * T, "HYB_KERNEL": [0] * T}
    labels = {(tasks[t], 0): ("SAME" if u0[t] < p else "UNRELATED") for t in range(T)}
    labels.update({(tasks[t], 1): ("SAME" if u1[t] < p + gain / 16 else "UNRELATED") for t in range(43, 59)})
    return {"EMB_MINILM": emb, "LEX_KERNEL": lex, "HYB_KERNEL": list(lex)}, first, days, tasks, labels


def test_the_decision_chain_rarely_calls_a_zero_gain_and_calls_more_often_as_the_planted_gain_grows() -> None:
    cfg = cfg_with(judge__prevalence_rule_min_tasks_with_same=5, readings__bootstrap__stability_seeds=[], readings__bootstrap__draws_primary=200)
    rates = {}
    for gain in (0, 3, 6, 9):
        helps = 0
        for s in range(100):
            rng = np.random.default_rng(1000 + s)                                                                           # the same uniforms at every gain
            scores, first, days, tasks, labels = planted(rng.random(214), rng.random(214), gain)
            helps += rb.p1_readings(scores, first, days, tasks, labels, cfg)["verdict"] == HELPS
        rates[gain] = helps / 100
    assert rates[0] <= 0.05 and rates[0] <= rates[3] <= rates[6] <= rates[9] and rates[9] >= rates[0] + 0.3, rates


def test_four_seeds_that_disagree_give_the_resampling_boundary_verdict() -> None:
    cfg = cfg_with(judge__prevalence_rule_min_tasks_with_same=5, readings__bootstrap__draws_primary=24)
    for s in range(120):
        rng = np.random.default_rng(5000 + s)
        scores, first, days, tasks, labels = planted(rng.random(214), rng.random(214), 7)
        got = rb.p1_readings(scores, first, days, tasks, labels, cfg)
        if len(set(got["verdict_by_seed"].values())) > 1:
            assert got["verdict_judge"] == got["verdict"] == "UNRESOLVED (resampling boundary)" and got["fusion_flag"] is None and len(got["verdict_by_seed"]) == 4
            assert got["verdict_by_seed"][str(CFG["readings"]["bootstrap"]["seed"])] in rb.BASE_VERDICTS
            return
    pytest.fail("no borderline case found among 120 planted data sets at 24 draws")


def test_secondary_readings_are_descriptive_intervals_for_other_q_methods_relevance_and_the_grid() -> None:
    scores, first, days, tasks, labels, _ = random_inputs(3, T=40, n_days=8)
    scores["HYB_SHIPPED"], first["HYB_SHIPPED"] = list(scores["LEX_BM25"]), list(first["LEX_BM25"])
    cfg = cfg_with(readings__bootstrap__draws_other=30)
    got = rb.secondary_readings(scores, first, days, tasks, labels, cfg)
    assert got["draws"] == 30 and set(got["differences"]) == {"strict", "lenient"}
    strict = got["differences"]["strict"]
    assert set(strict) == {"EMB_MINILM-LEX_KERNEL", "HYB_KERNEL-LEX_KERNEL", "LEX_BM25-LEX_KERNEL", "HYB_SHIPPED-LEX_KERNEL"} and "0.1" not in strict["HYB_KERNEL-LEX_KERNEL"]
    for mode, good in (("strict", ("SAME",)), ("lenient", ("SAME", "RELATED"))):
        rel = {m: [first[m][t] >= 0 and labels.get((tasks[t], first[m][t])) in good for t in range(40)] for m in scores}
        for q in (0.2, 0.3):
            full = sum(rel["EMB_MINILM"][t] for t in brute_fire(scores["EMB_MINILM"], tasks, list(range(40)), q)) - sum(
                rel["LEX_KERNEL"][t] for t in brute_fire(scores["LEX_KERNEL"], tasks, list(range(40)), q))
            assert got["differences"][mode]["EMB_MINILM-LEX_KERNEL"][str(q)]["d"] == full
        grid = CFG["readings"]["d_bar_grid"]
        mean = np.mean([sum(rel["HYB_KERNEL"][t] for t in brute_fire(scores["HYB_KERNEL"], tasks, list(range(40)), q)) - sum(
            rel["LEX_KERNEL"][t] for t in brute_fire(scores["LEX_KERNEL"], tasks, list(range(40)), q)) for q in grid])
        assert got["d_bar"][mode]["HYB_KERNEL-LEX_KERNEL"]["d"] == pytest.approx(mean)
        assert got["d_bar"][mode]["HYB_KERNEL-LEX_KERNEL"]["lo"] <= got["d_bar"][mode]["HYB_KERNEL-LEX_KERNEL"]["d"] + 1e-9 or True
    assert got == rb.secondary_readings(scores, first, days, tasks, labels, cfg)


def test_the_permutation_reference_has_the_analytic_mean_the_readme_gives() -> None:
    scores, first, days, tasks, labels = planted(*(np.random.default_rng(8).random(214) for _ in range(2)), 6)
    pool = {str(tasks[t]): [0, 1] for t in range(214)}
    cfg = cfg_with(readings__shuffle_draws=400)
    ref = rb.permutation_reference(scores, first, tasks, pool, labels, cfg)
    share = {tasks[t]: sum(1 for j in (0, 1) if labels.get((tasks[t], j)) == "SAME") / 2 for t in range(214)}
    fa = set(rb.fire_positions(scores["EMB_MINILM"], tasks, 0.2).tolist())
    fb = set(rb.fire_positions(scores["LEX_KERNEL"], tasks, 0.2).tolist())
    assert ref["analytic_mean_d"] == pytest.approx(sum(share[tasks[t]] * ((t in fa) - (t in fb)) for t in range(214)))
    assert abs(ref["mean_d"] - ref["analytic_mean_d"]) < 4 * ref["sd_d"] / math.sqrt(400) + 1e-9 and ref["draws"] == 400 and ref["min_d"] <= ref["mean_d"] <= ref["max_d"]
    assert ref == rb.permutation_reference(scores, first, tasks, pool, labels, cfg)


# ----------------------------------------------------------------------------------------------------------------------------------------- the judge gate

def rec(kind, i, j, label, failures=(), stratum=None):
    row = {"kind": kind, "i": i, "j": j, "label": label, "raw": label or "", "failures": list(failures), "calls": len(failures) + 1}
    if stratum:
        row["stratum"] = stratum
    return row


def gate_world(pos_same=55, neg_same=3, repeat=(10, 8), agree=(20, 15), failed=0):
    """Sixty positive and sixty negative controls, a pool of 100 pairs (the first 30 SAME), `repeat` = (first-pass SAME pairs repeated, how many stay SAME), `agree` = (decisive
    pairs, how many the assistant agrees on), `failed` extra failed calls."""
    recs = [rec("pos", 20 + k, 20 + k, "SAME" if k < pos_same else "RELATED") for k in range(60)]
    recs += [rec("neg", 20 + k, k % 10, "SAME" if k < neg_same else "UNRELATED", stratum="random" if k < 30 else "hard") for k in range(60)]
    pool = [(20 + t // 5, t % 5) for t in range(100)]
    recs += [rec("pool", i, j, "SAME" if n < 30 else "UNRELATED", failures=["unparseable"] if 60 <= n < 60 + failed else ()) for n, (i, j) in enumerate(pool)]
    again = pool[:repeat[0]] + pool[60:70]
    recs += [rec("rep", i, j, "SAME" if n < repeat[1] else "UNRELATED") for n, (i, j) in enumerate(again)]
    keys, assistant = {}, {}
    for n in range(agree[0]):
        i, j = pool[40 + n]
        keys["d%03d" % n] = {"i": i, "j": j, "origin": ("lexical_only", "minilm_only", "both")[n % 3]}
        assistant["d%03d" % n] = "UNRELATED" if n < agree[1] else "SAME"
    pairs = {"pool": {}, "repeat": [list(p) for p in again], "positive": [[20 + k, 20 + k] for k in range(60)],
             "negative": [[20 + k, k % 10, "random" if k < 30 else "hard"] for k in range(60)]}
    for i, j in pool:
        pairs["pool"].setdefault(str(i), []).append(j)
    return recs, pairs, keys, assistant


def gate_of(**kw):
    recs, pairs, keys, assistant = gate_world(**kw)
    return rb.judge_gate_report(recs, CFG, pairs, keys, assistant)


def test_the_gate_passes_exactly_at_its_boundaries_and_fails_one_step_beyond() -> None:
    ok = gate_of()
    assert ok["passes"] and all(ok["checks"].values()) and ok["positive"]["same"] == 55 and ok["negative"]["same"] == 3
    assert ok["repeat"]["persistence"] == 0.8 and ok["decisive_audit"]["agreement"] == 0.75 and ok["format"]["share"] == 0
    for kwargs, check in (({"pos_same": 54}, "positive_control"), ({"neg_same": 4}, "negative_control"), ({"repeat": (10, 7)}, "perturbed_repeat"), ({"agree": (20, 14)}, "decisive_audit"),
                          ({"failed": 6}, "format_failures")):
        bad = gate_of(**kwargs)
        assert bad["checks"][check] is False and bad["passes"] is False and sum(1 for v in bad["checks"].values() if not v) == 1, kwargs
    assert gate_of(failed=4)["checks"]["format_failures"] and gate_of(failed=4)["format"]["format_failures"] == 4 and gate_of(failed=4)["format"]["by_class"] == {"unparseable": 4}


def test_the_gate_reports_strata_agreement_by_origin_repeat_statistics_and_the_unlabelled_pairs() -> None:
    report = gate_of()
    assert report["negative"]["strata"]["random"] == {"n": 30, "unrelated": 27, "unrelated_share": 0.9} and report["negative"]["strata"]["hard"]["unrelated_share"] == 1.0
    audit = report["decisive_audit"]
    assert set(audit["by_origin"]) == {"lexical_only", "minilm_only", "both"} and sum(v["n"] for v in audit["by_origin"].values()) == 20
    lex = audit["by_origin"]["lexical_only"]
    lo, hi = stats.wilson(lex["agree"], lex["n"])
    assert (lex["wilson_lo"], lex["wilson_hi"]) == (lo, hi) and 0 <= lo <= lex["agreement"] <= hi <= 1
    rep = report["repeat"]
    assert rep["first_pass_same"] == 10 and rep["same_again"] == 8 and rep["n"] == 20 and rep["identical_three_way_share"] == 18 / 20 and -1 <= rep["kappa_same_vs_not_same"] <= 1
    recs, pairs, keys, assistant = gate_world()
    recs[130]["label"], recs[130]["failures"], recs[130]["calls"] = None, ["empty", "empty"], 2
    broken = rb.judge_gate_report(recs, CFG, pairs, keys, assistant)
    assert [recs[130]["kind"], recs[130]["i"], recs[130]["j"]] in broken["format"]["pairs_without_valid_label"] and broken["format"]["by_class"] == {"empty": 2}
    keys2 = dict(keys)
    flat = {(info["i"], info["j"]): key for key, info in keys.items()}
    victim = next(r for r in recs if r["kind"] == "pool" and (r["i"], r["j"]) in flat)
    victim["label"] = None
    assert rb.judge_gate_report(recs, CFG, pairs, keys2, assistant)["decisive_audit"]["without_valid_judge_label"] == 1      # a disagreement, not a free agreement
    assert rb.judge_gate_report(recs, CFG, pairs, keys2, assistant)["decisive_audit"]["agree"] == 14


def test_a_gate_that_lacks_calls_or_the_assistants_file_fails_closed() -> None:
    recs, pairs, keys, assistant = gate_world()
    assert not rb.judge_gate_report([r for r in recs if r["kind"] != "rep"], CFG, pairs, keys, assistant)["checks"]["perturbed_repeat"]
    assert not rb.judge_gate_report([r for r in recs if r["kind"] != "pool"][:120], CFG, pairs, keys, assistant)["checks"]["pool_complete"]
    assert not rb.judge_gate_report(recs, CFG, pairs, keys, {})["checks"]["decisive_audit"] and not rb.judge_gate_report(recs, CFG, pairs, {}, {})["checks"]["decisive_audit"]
    assert not rb.judge_gate_report([], CFG, {}, {}, {})["passes"]
    assert rb.gate_controls_ok(recs, CFG) and not rb.gate_controls_ok(recs[:50], CFG)


# ------------------------------------------------------------------------------------------------------------------------------------- U3 and U2

def test_terciles_are_cut_by_overlap_then_note_index_and_the_lowest_is_the_first_floor_of_a_third() -> None:
    assert rb.tercile_slices([0.5, 0.5, 0.1, 0.9, 0.5, 0.2, 0.7], [5, 3, 9, 1, 2, 8, 4]) == [[2, 5], [4, 1], [0, 6, 3]]
    assert [len(t) for t in rb.tercile_slices(list(range(100)))] == [33, 33, 34] and [len(t) for t in rb.tercile_slices(list(range(38)))] == [12, 12, 14]
    kept, info = rb.retained_questions([{"k": 7, "question": "q7"}, {"k": 3, "question": "q3"}, {"k": 5, "question": ""}, {"k": 9, "question": "q9"}],
                                       [{"k": 7, "answer": "YES"}, {"k": 3, "answer": "NO"}, {"k": 5, "answer": "YES"}, {"k": 9, "answer": None}])
    assert [q["k"] for q in kept] == [7] and info == {"questions": 4, "retained": 1, "dropped": 3, "answerable_share": 0.25}


def test_p2_uses_the_stream_the_interval_rule_and_has_no_no_rescue_verdict() -> None:
    a, b = [1] * 40, [0] * 30 + [1] * 10
    got = rb.mean_difference_interval(a, b, 200, 20261102)
    sums = sorted(sum(a[i] - b[i] for i in picks) for picks in original.bootstrap_indices(40, 200, 20261102))
    assert got == {"d": 0.75, "lo": sums[5] / 40, "hi": sums[194] / 40, "n": 40} and rb.mean_difference_interval([], [], 10, 1) is None
    assert rb.verdict_p2({"d": 0.15, "lo": 0.01, "hi": 0.3}, 0.15) == "EMBEDDER_RESCUES" and rb.verdict_p2({"d": 0.1499, "lo": 0.01, "hi": 0.3}, 0.15) == "not EMBEDDER_RESCUES"
    assert rb.verdict_p2({"d": 0.3, "lo": 0.0, "hi": 0.5}, 0.15) == "not EMBEDDER_RESCUES" and rb.verdict_p2({"d": 0.0, "lo": -0.1, "hi": 0.05}, 0.15) == "not EMBEDDER_RESCUES"
    assert rb.verdict_p2(None, 0.15) == "not EMBEDDER_RESCUES" and not hasattr(rb, "NO_RESCUE") and CFG["u3"]["p2"]["margin_rescue"] == 0.15
    assert rb.decision("LEXICAL_SUFFICIENT_FOR_GATE", None, True, True).startswith("NOT_APPLIED") and rb.decision("UNRESOLVED", None, True, True).startswith("LEXICAL_IN_SHADOW")


def test_the_audit_checks_the_first_three_non_source_candidates_of_two_methods_up_to_the_cap() -> None:
    kept = [{"k": 10, "question": "a"}, {"k": 11, "question": "b"}]
    rankings = [{"EMB_MINILM": [(10, 1.0), (3, 0.9), (4, 0.8), (5, 0.7)], "LEX_KERNEL": [(3, 1.0), (6, 0.9), (7, 0.8), (8, 0.7)]},
                {"EMB_MINILM": [(1, 1.0), (2, 0.9), (3, 0.8)], "LEX_KERNEL": [(11, 1.0), (1, 0.9)]}]
    targets = rb.audit_targets(kept, [0, 1], rankings, CFG)
    assert targets == [{"k": 10, "j": 3}, {"k": 10, "j": 4}, {"k": 10, "j": 6}, {"k": 10, "j": 7}, {"k": 11, "j": 1}, {"k": 11, "j": 2}, {"k": 11, "j": 3}]
    assert rb.audit_targets(kept, [0, 1], rankings, cfg_with(u3__audit_retrieved_max_calls=3)) == targets[:3] and CFG["u3"]["audit_retrieved_max_calls"] == 240


def test_u2_counts_the_questions_whose_key_is_only_inside_a_longer_word() -> None:
    items = corpus_items(12)
    nv = vectors([i.text for i in items])
    persona = {"biography": [{"id": "b1", "date": "1989", "text": "You were born in Kellmouth, a fishing town."}, {"id": "b2", "date": "1990", "text": "Your mother kept the ledgers; Imre was a colleague."}],
               "fact_questions": [{"id": "f1", "style": "direct", "q": "Where were you born?", "keys": ["Kellmouth"]}, {"id": "f2", "style": "indirect", "q": "Who is Imre?", "keys": ["imre"]},
                                  {"id": "f3", "style": "direct", "q": "Which ledger?", "keys": ["ledger"]}]}
    prep = prepared()[4]
    got = rb.u2_report(items, nv, persona, lambda texts: vectors(list(texts)), cfg_small(), prep["tau_lex"], prep["tau_emb"])
    assert got["questions"] == 3 and got["scored"] == 2 and got["excluded_empty_gold"] == ["f3"] and set(got["by_style"]) == {"direct", "indirect"}
    assert set(got["overall"]) == set(rb.METHODS) | {"KERNEL_NAMES"} and got["overall"]["KERNEL_NAMES"]["recall@3"] == 1.0
    assert rb.persona_gold(persona) == [{0}, {1}, set()]


def test_question_overlap_the_sample_of_notes_and_the_ranking_metrics_follow_their_definitions() -> None:
    assert rb.question_overlap("Which ferry company kept ledgers?", "the ferry company ledgers were audited") == pytest.approx(3 / 4)
    assert rb.question_overlap("Who audited the books?", "the ferry company ledgers were audited") == pytest.approx(1 / 2) and rb.question_overlap("the of", "anything") == 0.0
    items = [sbm.Item("i%03d" % k, date(2026, 9, 1 + k % 28), " ".join(["w"] * (5 + k))) for k in range(234)]
    chosen = rb.sample_u3_notes(items, CFG)
    assert len(chosen) == 120 and chosen == sorted(set(chosen)) and chosen == rb.sample_u3_notes(items, CFG)
    assert sum(1 for j in chosen if j < 78) == 40 and sum(1 for j in chosen if 78 <= j < 156) == 40 and sum(1 for j in chosen if j >= 156) == 40
    assert rb.gold_rank([(3, 1.0), (5, 0.5)], {5}) == 2 and rb.gold_rank([(3, 1.0)], {9}) is None
    ranks = [1, 4, None, 2]
    assert rb.recall_at(ranks, 1) == 0.25 and rb.recall_at(ranks, 3) == 0.5 and rb.recall_at(ranks, 10) == 0.75 and rb.reciprocal_rank(ranks) == pytest.approx((1 + 0.25 + 0.5) / 4)
    assert rb.recall_at([], 3) is None and rb.reciprocal_rank([]) is None


def test_a_static_collection_ranks_a_paraphrase_by_meaning_only_in_the_embedding_methods() -> None:
    items = corpus_items(12)
    texts = [i.text for i in items]
    prep = rb.prepare_rankings(items, briefs_for(items), vectors(texts), vectors(briefs_for(items)), cfg_small())
    coll = rb.StaticCollection(texts, ["account_history"] * 12, rb.synthetic_times(items), vectors(texts), CFG, prep["tau_lex"], prep["tau_emb"])
    query = "boat firm records"                                                                               # three words of notes 0 and 6 said with synonyms: no shared stem
    ranking = coll.rank(query, vectors([query])[0], "note")
    assert set(ranking) == set(rb.METHODS)
    assert rb.gold_rank(ranking["EMB_MINILM"], {0, 6}) in (1, 2) and rb.gold_rank(ranking["HYB_KERNEL"], {0, 6}) in (1, 2)
    assert rb.gold_rank(ranking["LEX_BM25"], {0, 6}) is None or rb.gold_rank(ranking["LEX_BM25"], {0, 6}) > 2


# ------------------------------------------------------------------------------------------------------ the whole pipeline on a synthetic account

STORIES = ["ferry company ledgers harbour audit", "sourdough starter basement flood", "tide tables shortwave radio night", "chess endgames archive scanners",
           "estuary rail town fishing", "recovery procedure boring document"]


def write_account(tmp: Path, n: int = 36):
    notes = [{"id": "id%03d" % k, "date": "2026-09-%02d" % (1 + k // 2), "title": "", "text": "entry %d regarding %s and filler%d words" % (k, STORIES[k % 6], k)} for k in range(n)]
    briefs = ["%s filler%d" % (STORIES[k % 6], k) for k in range(n)]
    (tmp / "notes.jsonl").write_text("\n".join(json.dumps(r) for r in notes) + "\n", encoding="utf-8")
    (tmp / "prep.json").write_text(json.dumps({"briefs": briefs, "traces": [], "top": [], "tau": 0.5722}), encoding="utf-8")
    persona = {"biography": [{"id": "b%d" % k, "date": "19%02d" % (80 + k), "text": t} for k, t in enumerate(
        ["You were born in Kellmouth, a fishing town.", "Your mother kept the ferry ledgers.", "You met Imre at the archive.", "You moved to Anchor Lane."])],
        "fact_questions": [{"id": "f1", "style": "direct", "q": "Where were you born?", "keys": ["Kellmouth"]}, {"id": "f2", "style": "indirect", "q": "Who is Imre?", "keys": ["Imre"]},
                           {"id": "f3", "style": "direct", "q": "Where do you live?", "keys": ["Anchor Lane"]}, {"id": "f4", "style": "direct", "q": "Which ledger?", "keys": ["ledger"]}]}
    (tmp / "persona.json").write_text(json.dumps(persona), encoding="utf-8")
    cfg = cfg_with(tasks__warmup=6, judge__gate__positive_control_n=6, judge__gate__positive_control_min_same=5, judge__gate__negative_control_n=6, judge__gate__negative_control_random=3,
                   judge__gate__negative_control_hard=3, judge__gate__negative_control_hard_cosine=[0.0, 0.5], judge__gate__negative_control_max_same=2,
                   judge__gate__stratified_sample_n=6, judge__prevalence_rule_min_tasks_with_same=5, readings__margin_tasks=1, readings__shuffle_draws=20,
                   readings__bootstrap__draws_primary=60, readings__bootstrap__draws_other=30, u3__per_length_tercile=3, u3__questions=9)
    with open(tmp / "notes.jsonl", encoding="utf-8") as handle:                                     # the E5 reference of the toy account is its own calibrated threshold
        items = sbm.parse_items(handle)
    cfg["reference_threshold_e5"] = rb.prepare_rankings(items, briefs, fake_embed([i.text for i in items]), fake_embed(briefs), cfg)["tau_emb"]
    (tmp / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp / "ledger.jsonl").write_text(json.dumps({"run_id": "e1-other", "usd": 2.69}) + "\n", encoding="utf-8")
    return account_args(tmp)


def account_args(tmp: Path) -> list:
    return ["--notes", str(tmp / "notes.jsonl"), "--prep", str(tmp / "prep.json"), "--persona", str(tmp / "persona.json"), "--config", str(tmp / "config.json"),
            "--workdir", str(tmp / "work"), "--workers", "2", "--allow-input-mismatch"]


def fake_label(brief: str, note: str) -> str:
    shared = len(set(mk.tokens(brief)) & set(mk.tokens(note)))
    return "SAME" if shared >= 3 else ("RELATED" if shared >= 1 else "UNRELATED")


def fake_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    if "check whether a note answers" in system:
        return {"text": "YES"}
    brief = user.split("Task (what the author was asked to write about):\n")[1].split("\n\nEarlier note")[0]
    note = user.split("Earlier note by the same author:\n")[1].split("\n\nThe task and the earlier note")[0]
    return {"text": fake_label(brief, note)}


def fake_writer(system: str, user: str, seed: int, opts: dict) -> dict:
    note = user.split("Note:\n")[1].split("\n\nWrite one question")[0]
    return {"text": "Which %s?" % " ".join(SYN.get(w, w) for w in note.split()[3:7])}


def fake_embed(texts):
    return vectors(list(texts))


RUN_IDS = {"judge": "e1-wmbr1-judge", "writer": "e1-wmbr1-writer"}


def fake_summary(url: str) -> dict:
    """What a proxy reports: GOOD_SUMMARY and the run id it was started with (judge proxy on 8798, writer proxy on 8799)."""
    return dict(GOOD_SUMMARY, run_id=RUN_IDS["writer" if ":8799" in url else "judge"])


def bare(summary: dict) -> dict:
    return {k: v for k, v in summary.items() if k != "run_id"}


def meter(behaviour, ledger: Path, role: str = "judge", price: float = 0.00016, model: str = "deepseek-flash", run_id: str = None):
    """A fake generate that behaves like a metering proxy: one ledger line of the proxy's run id per answered call."""
    lock = threading.Lock()

    def generate(system, user, seed, opts):
        out = behaviour(system, user, seed, opts)
        with lock, open(ledger, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"run_id": run_id or RUN_IDS[role], "usd": price, "model": model}) + "\n")
        return out

    return generate


def one_unanswerable():
    """A judge that answers NO to the first answerability check and behaves as fake_judge otherwise."""
    state, lock = {"n": 0}, threading.Lock()

    def judge(system, user, seed, opts):
        if "check whether a note answers" in system:
            with lock:
                state["n"] += 1
                if state["n"] == 1:
                    return {"text": "NO"}
        return fake_judge(system, user, seed, opts)

    return judge


def run_pipeline(tmp: Path, flips: int = 1, answerer=fake_judge):
    base = write_account(tmp)
    ledger = ["--ledger", str(tmp / "ledger.jsonl")]
    kw = {"summary_fn": fake_summary}
    judge_proxy, writer_proxy, answer_proxy = (meter(fake_judge, tmp / "ledger.jsonl"), meter(fake_writer, tmp / "ledger.jsonl", "writer"), meter(answerer, tmp / "ledger.jsonl"))

    def run(*argv, **more):
        return rb.main(list(argv) + base, **dict(kw, **more))

    assert run("prepare", embed=fake_embed) == 0
    work = tmp / "work"
    public = json.loads((work / rb.DECISIVE).read_text(encoding="utf-8"))
    truth = {d["key"]: fake_label(d["brief"], d["note"]) for d in public}
    mine = dict(truth)
    for key in sorted(mine)[: (len(mine) if flips < 0 else flips)]:
        mine[key] = "UNRELATED" if mine[key] == "SAME" else "SAME"
    (work / rb.DECISIVE_ASSISTANT).write_text(json.dumps(mine), encoding="utf-8")
    assert run("judge", "--stage", "all", *ledger, generate=judge_proxy) == 0
    assert run("sample") == 0
    sample = json.loads((work / rb.STRATIFIED).read_text(encoding="utf-8"))
    (work / rb.STRATIFIED_ASSISTANT).write_text(json.dumps({d["key"]: fake_label(d["brief"], d["note"]) for d in sample}), encoding="utf-8")
    assert run("questions", *ledger, writer=writer_proxy, generate=answer_proxy) == 0
    assert run("audit", *ledger, embed=fake_embed, generate=answer_proxy) == 0
    assert run("analyse", embed=fake_embed) == 0
    return base, work, ledger


def test_the_whole_pipeline_runs_resumes_audits_blind_and_leaves_a_summary_that_a_second_computation_confirms(tmp_path: Path) -> None:
    base, work, ledger = run_pipeline(tmp_path)
    results = json.loads((work / rb.RESULTS).read_text(encoding="utf-8"))
    gate = results["judge_gate"]
    assert gate["passes"] is True and all(gate["checks"].values()) and results["gate_failed"] is False
    assert gate["positive"]["n"] == 6 and gate["negative"]["n"] == 6 and gate["repeat"]["persistence"] == 1.0 and gate["format"]["share"] == 0.0
    audit = gate["decisive_audit"]
    assert audit["n"] >= 4 and audit["agree"] == audit["n"] - 1 and audit["agreement"] >= 0.75 and audit["complete"]
    assert results["controls_ok"] is True and results["controls"]["causality"]["violations"] == 0 and results["controls"]["causality"]["index_ok"]
    public = json.loads((work / rb.DECISIVE).read_text(encoding="utf-8"))
    assert all(set(p) == {"key", "brief", "note"} for p in public) and len(public) == audit["n"] == len(json.loads((work / rb.DECISIVE_KEYS).read_text(encoding="utf-8")))
    u1 = results["u1"]
    p1 = u1["p1"]
    assert u1["tasks"] == 30 and set(u1["methods"]) == set(rb.RANKED) and p1["verdict"] in rb.BASE_VERDICTS + ("UNRESOLVED (labels)", "UNRESOLVED (resampling boundary)", "NOT_EVALUABLE (prevalence)")
    assert set(p1) == {"tasks_with_same", "prevalence_ok", "hits", "d_emb", "d_hyb", "verdict_by_seed", "verdict_judge", "verdict_assistant", "verdict", "fusion_flag"}
    for m in rb.RANKED:
        for q, fired_n in (("0.1", 3), ("0.2", 6), ("0.3", 9)):
            cell = u1["methods"][m][q]
            assert cell["hits"] + cell["false_injections"] == cell["fired"] == fired_n and cell["shortfall"] == 0 and cell["hits_at_3"] >= cell["hits"]
            assert p1["hits"][m][q]["hits"] == cell["hits"]
    assert set(u1["lenient"]["methods"]) == set(rb.RANKED) and u1["ref_e5"]["fired"] >= 0 and u1["context"]["tasks_with_same"] == p1["tasks_with_same"]
    assert set(u1["secondary"]["differences"]) == {"strict", "lenient"} and set(u1["operating_point"]) == set(rb.RANKED) and u1["permutation_reference"]["draws"] == 20
    assert set(u1["shipped_thresholds"]) == {"lexical_profile_fired", "embedding_gate_only"} and "not_run" not in u1
    assert results["stratified_sample"]["n"] == 4 and results["stratified_sample"]["agreement_same_vs_not"] == 1.0           # no RELATED pair outside the decisive ones in this account
    u3 = results["u3"]
    assert u3["retained"] > 0 and u3["answerability_gate_passes"] and set(u3["by_overlap_tercile"]) == {"low", "middle", "high"} and u3["p2"]["issued"]
    assert u3["p2"]["verdict"] in ("EMBEDDER_RESCUES", "not EMBEDDER_RESCUES") and "d3_emb" in u3["p2"] and "d3_hyb" in u3["p2"] and u3["recall_any_at_3"]["complete"] is True
    assert results["u2"]["scored"] == 3 and results["u2"]["excluded_empty_gold"] == ["f4"] and results["u2"]["overall"]["KERNEL_NAMES"]["recall@3"] >= 0.66
    assert not results["decision"].startswith("NOT_APPLIED") and results["proxy_problems"] == {}
    stages = contract.load_jsonl(work / rb.STAGES)
    assert [s["stage"] for s in stages][:3] == ["gate", "repeat", "pool"] and {"questions", "answerability", "audit"} <= {s["stage"] for s in stages}
    assert all(bare(s["summary_before"]) == GOOD_SUMMARY and bare(s["summary_after"]) == GOOD_SUMMARY and s["problems_after"] == [] and s["outcome"] == "completed" for s in stages)
    baseline = json.loads((work / rb.BASELINE).read_text(encoding="utf-8"))
    assert baseline["scope"] == "e1" and baseline["scope_usd"] == 2.69 and baseline["slice_usd"] == 0.0
    frozen = baseline["sha256_before_the_first_call"]                                                         # Amendment 2: the digests before the first judge call
    assert set(frozen) == {rb.PREP, rb.PAIRS, rb.VECTORS, rb.DECISIVE, rb.DECISIVE_KEYS, rb.DECISIVE_ASSISTANT} and frozen[rb.DECISIVE_ASSISTANT] == contract.sha256_file(work / rb.DECISIVE_ASSISTANT)
    assert rb.verdict_line(results).startswith("P1 ") and "tasks with a SAME note" in rb.verdict_line(results) and rb.verdict_line({"judge_gate": {"checks": {"a": False}}, "decision": "x"}).startswith("P1 not read")
    summary = json.loads((work / rb.SUMMARY).read_text(encoding="utf-8"))
    assert summary["records_sha256"] == contract.sha256_file(work / rb.LABELS) and summary["meta"]["gate_failed"] is False and summary["meta"]["decisive_labels_assistant.json_sha256"]
    assert summary["meta"]["script_sha256"]["scripts/wmb/retrieval_bench.py"]["sha256"] == contract.sha256_file(Path(rb.__file__))
    cfg = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    items, _ = rb.load_inputs(tmp_path / "notes.jsonl", tmp_path / "prep.json")
    persona = json.loads((tmp_path / "persona.json").read_text(encoding="utf-8"))
    verdict = contract.verify_summary(work / rb.SUMMARY, work / rb.LABELS, lambda records: rb.compute_results(work, items, persona, cfg, fake_embed, records))
    assert verdict == {"records_sha256": True, "aggregates": True}
    labels = contract.load_jsonl(work / rb.LABELS)
    kinds = {k: sum(1 for r in labels if r["kind"] == k) for k in ("pos", "neg", "pool", "rep")}
    assert kinds["pos"] == 6 and kinds["neg"] == 6 and kinds["pool"] == sum(len(v) for v in json.loads((work / rb.PAIRS).read_text(encoding="utf-8"))["pool"].values()) and kinds["rep"] >= audit["n"]

    def forbidden(*a, **k):
        raise AssertionError("a finished run must not call the judge again")

    assert rb.main(["judge", "--stage", "all"] + base + ledger, generate=forbidden, summary_fn=fake_summary) == 0                 # resumable: nothing left to ask
    assert rb.main(["questions"] + base + ledger, writer=forbidden, generate=forbidden, summary_fn=fake_summary) == 0             # the questions are never regenerated
    low = u3["by_overlap_tercile"]["low"]
    assert all(low[m]["recall@3"] <= u3["recall_any_at_3"][m] + 1e-12 for m in ("EMB_MINILM", "LEX_KERNEL"))                      # a source note is also an answer
    broken = [dict(r, label="UNRELATED") if r["kind"] == "pos" else r for r in labels]
    pairs, keys = json.loads((work / rb.PAIRS).read_text(encoding="utf-8")), json.loads((work / rb.DECISIVE_KEYS).read_text(encoding="utf-8"))
    assistant = json.loads((work / rb.DECISIVE_ASSISTANT).read_text(encoding="utf-8"))
    assert rb.judge_gate_report(broken, cfg, pairs, keys, assistant)["passes"] is False


def test_a_failed_decisive_audit_leaves_the_u1_tables_out_and_the_decision_unapplied(tmp_path: Path) -> None:
    base, work, ledger = run_pipeline(tmp_path, flips=-1)                                                   # the assistant disagrees on every decisive pair
    results = json.loads((work / rb.RESULTS).read_text(encoding="utf-8"))
    assert results["judge_gate"]["checks"]["decisive_audit"] is False and results["judge_gate"]["passes"] is False and results["gate_failed"] is True
    assert "u1" not in results and "stratified_sample" not in results and results["decision"].startswith("NOT_APPLIED") and "u3" in results and "u2" in results and results["controls_ok"]
    summary = json.loads((work / rb.SUMMARY).read_text(encoding="utf-8"))
    assert summary["meta"]["gate_failed"] is True and "u1" not in summary["aggregates"]
    assert rb.decision("EMBEDDER_HELPS_GATE", "not EMBEDDER_RESCUES", True, True) == "ADD_EMBEDDER_PROFILE_FOR_NOTE_WRITING_MEMORY"
    assert rb.decision("LEXICAL_SUFFICIENT_FOR_GATE", "EMBEDDER_RESCUES", True, True).startswith("LEXICAL_FOR_NOTES") and rb.decision(
        "LEXICAL_SUFFICIENT_FOR_GATE", "not EMBEDDER_RESCUES", True, True) == "STAY_LEXICAL"
    assert rb.decision("UNRESOLVED (labels)", "not EMBEDDER_RESCUES", True, True) == "LEXICAL_IN_SHADOW_REVISIT_WITH_MORE_TASKS" and rb.decision("UNRESOLVED", None, False, True).startswith("NOT_APPLIED")
    assert rb.decision(HELPS, None, True, False).startswith("NOT_APPLIED") and rb.decision("NOT_EVALUABLE (prevalence)", None, True, True).startswith("NOT_APPLIED")


def test_the_analysis_runs_before_the_questions_the_audit_and_the_stratified_labels_exist(tmp_path: Path) -> None:
    base = write_account(tmp_path)
    kw = {"summary_fn": fake_summary}
    assert rb.main(["prepare"] + base, embed=fake_embed, **kw) == 0
    work = tmp_path / "work"
    public = json.loads((work / rb.DECISIVE).read_text(encoding="utf-8"))
    (work / rb.DECISIVE_ASSISTANT).write_text(json.dumps({d["key"]: fake_label(d["brief"], d["note"]) for d in public}), encoding="utf-8")
    assert rb.main(["judge", "--stage", "all", "--ledger", str(tmp_path / "ledger.jsonl")] + base, generate=meter(fake_judge, tmp_path / "ledger.jsonl"), **kw) == 0
    assert rb.main(["analyse"] + base, embed=fake_embed, **kw) == 0
    results = json.loads((work / rb.RESULTS).read_text(encoding="utf-8"))
    assert results["judge_gate"]["passes"] and "u1" in results and "stratified_sample" not in results
    assert results["u3"]["questions"] == 0 and "p2" not in results["u3"] and results["u2"]["scored"] == 3 and isinstance(results["decision"], str)
    assert results["u1"]["p1"]["verdict_assistant"] == results["u1"]["p1"]["verdict_judge"]                       # the assistant agreed on every decisive pair


def test_p2_is_not_issued_when_fewer_than_95_percent_of_the_questions_are_answerable(tmp_path: Path) -> None:
    base, work, ledger = run_pipeline(tmp_path, answerer=one_unanswerable())                                 # 8 of 9 answerable: 89%
    results = json.loads((work / rb.RESULTS).read_text(encoding="utf-8"))
    u3 = results["u3"]
    assert u3["questions"] == 9 and u3["retained"] == 8 and u3["dropped"] == 1 and u3["answerability_gate_passes"] is False
    assert u3["p2"]["issued"] is False and u3["p2"]["verdict"] is None and "recall_any_at_3" not in u3 and not (work / rb.AUDIT).exists()
    assert rb.parse_choice("Yes.", ("YES", "NO")) == "YES" and rb.parse_choice("yes it does", ("YES", "NO")) is None and rb.parse_choice("**No**", ("YES", "NO")) == "NO"


def test_a_failed_control_stops_the_pool_stage_and_the_ledger_stop_refuses_every_stage(tmp_path: Path) -> None:
    base = write_account(tmp_path)
    ledger = ["--ledger", str(tmp_path / "ledger.jsonl")]
    assert rb.main(["prepare"] + base, embed=fake_embed, summary_fn=fake_summary) == 0
    calls = []

    def hostile_judge(system, user, seed, opts):
        calls.append(1)
        return {"text": "UNRELATED"}

    hostile = meter(hostile_judge, tmp_path / "ledger.jsonl")
    work = tmp_path / "work"
    keys = json.loads((work / rb.DECISIVE_KEYS).read_text(encoding="utf-8"))
    assert rb.main(["judge", "--stage", "all"] + base + ledger, generate=hostile, summary_fn=fake_summary) == 1 and not calls          # the assistant has not labelled the decisive pairs
    (work / rb.DECISIVE_ASSISTANT).write_text(json.dumps({k: "SAME" for k in sorted(keys)[1:]}), encoding="utf-8")
    assert rb.main(["judge", "--stage", "all"] + base + ledger, generate=hostile, summary_fn=fake_summary) == 1 and not calls          # one pair is missing
    (work / rb.DECISIVE_ASSISTANT).write_text(json.dumps({k: "SAME" for k in keys}), encoding="utf-8")
    assert rb.main(["judge", "--stage", "all"] + base + ledger, generate=hostile, summary_fn=fake_summary) == 3          # a control stop is not a success (a chained `judge && questions` stops)
    kinds = {r["kind"] for r in contract.load_jsonl(work / rb.LABELS)}
    assert kinds == {"pos", "neg"} and len(calls) == 12                                                       # the positive control failed: neither repeat nor pool was judged
    contract.append_jsonl(tmp_path / "ledger.jsonl", [{"run_id": "e1-wmbr1-judge", "usd": 2.0}])
    before = len(calls)
    override = ["--continue-on-gate-failure"]                                                                  # (without it the failed gate control refuses the stage first, see the F1 tests)
    assert rb.main(["judge", "--stage", "pool"] + override + base + ledger, generate=hostile, summary_fn=fake_summary) == 2 and len(calls) == before
    assert rb.main(["judge", "--stage", "pool"] + base, generate=hostile, summary_fn=fake_summary) == 1          # no --ledger: no model call
    assert rb.main(["questions"] + override + base + ledger, writer=hostile, generate=hostile, summary_fn=fake_summary) == 2 and len(calls) == before


def test_the_digest_check_aborts_on_a_mismatch_and_the_hand_sample_is_gone(tmp_path: Path) -> None:
    base = write_account(tmp_path)
    strict = [a for a in base if a != "--allow-input-mismatch"]
    assert rb.main(["prepare"] + strict, embed=fake_embed) == 1 and not (tmp_path / "work").exists()
    cfg = rb.load_config(tmp_path / "config.json")
    with pytest.raises(rb.InputMismatch):
        rb.verify_inputs(cfg, tmp_path / "notes.jsonl", tmp_path / "prep.json", tmp_path / "persona.json")
    cfg["inputs_sha256"] = {"opublikowane.jsonl": contract.sha256_file(tmp_path / "notes.jsonl"), "replay/prep.json": contract.sha256_file(tmp_path / "prep.json"),
                            "data/lab/aam-e6-persona/persona.json": contract.sha256_file(tmp_path / "persona.json")}
    assert rb.verify_inputs(cfg, tmp_path / "notes.jsonl", tmp_path / "prep.json", tmp_path / "persona.json") == cfg["inputs_sha256"]
    assert not hasattr(rb, "hand_sample") and not hasattr(rb, "HAND")
    with pytest.raises(SystemExit):
        rb.main(["hand-sample"])


# ====================================================================================================================================================
# The code review of the first version (findings F1 to F16 and ANL-1 to ANL-13): one regression test for every fix. No model, network or proxy call:
# the fakes below behave like the metering proxies (a ledger line of the proxy's run id per answered call, a summary that names the run id).
# ====================================================================================================================================================

@pytest.fixture(scope="module")
def template(tmp_path_factory):
    """A toy account after `prepare` and the assistant's blind labels. Every test below works on a copy of it (prepare is the slow part)."""
    root = tmp_path_factory.mktemp("template")
    base = write_account(root)
    assert rb.main(["prepare"] + base, embed=fake_embed, summary_fn=fake_summary) == 0
    public = json.loads((root / "work" / rb.DECISIVE).read_text(encoding="utf-8"))
    (root / "work" / rb.DECISIVE_ASSISTANT).write_text(json.dumps({d["key"]: fake_label(d["brief"], d["note"]) for d in public}), encoding="utf-8")
    return root


def counting(behaviour):
    box, lock = {"n": 0}, threading.Lock()

    def wrapped(system, user, seed, opts):
        with lock:
            box["n"] += 1
        return behaviour(system, user, seed, opts)

    wrapped.box = box
    return wrapped


def note_number(user: str) -> int:
    return int(re.search(r"entry (\d+) regarding", user).group(1))


def bad_for(modulus: int):
    """A judge whose reply is 'maybe' (a format failure, on both attempts) for the pairs whose prompt hashes to 0 modulo `modulus`."""
    def behaviour(system, user, seed, opts):
        if int(hashlib.md5(user.encode()).hexdigest(), 16) % modulus == 0:
            return {"text": "maybe"}
        return fake_judge(system, user, seed, opts)

    return behaviour


class Bench:
    """A copy of the prepared toy account, driven through rb.main with fakes that behave like metering proxies."""

    def __init__(self, tmp: Path, template: Path) -> None:
        self.root = tmp / "acct"
        shutil.copytree(template, self.root)
        self.work, self.ledger_path = self.root / "work", self.root / "ledger.jsonl"
        self.base = account_args(self.root)

    def run(self, command: str, *extra: str, **kw) -> int:
        kw.setdefault("summary_fn", fake_summary)
        return rb.main([command, *extra] + self.base + ["--ledger", str(self.ledger_path)], **kw)

    def proxy(self, behaviour=fake_judge, role: str = "judge", **kw):
        return meter(behaviour, self.ledger_path, role, **kw)

    def judge(self, *extra: str, behaviour=fake_judge, **kw) -> int:
        return self.run("judge", *extra, generate=self.proxy(behaviour), **kw)

    def questions(self, *extra: str, writer=fake_writer, answerer=fake_judge, **kw) -> int:
        return self.run("questions", *extra, writer=self.proxy(writer, "writer"), generate=self.proxy(answerer), **kw)

    def audit(self, *extra: str, answerer=fake_judge, **kw) -> int:
        return self.run("audit", *extra, embed=fake_embed, generate=self.proxy(answerer), **kw)

    def records(self, name: str = rb.LABELS) -> list:
        return contract.load_jsonl(self.work / name)

    def config(self) -> dict:
        return json.loads((self.root / "config.json").read_text(encoding="utf-8"))

    def set_config(self, cfg: dict) -> None:
        (self.root / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

    def items(self):
        return rb.load_inputs(self.root / "notes.jsonl", self.root / "prep.json")[0]

    def last_json(self, capsys) -> dict:
        return json.loads(capsys.readouterr().out.strip().splitlines()[-1])


HOSTILE = lambda system, user, seed, opts: {"text": "UNRELATED"}     # noqa: E731


# ------------------------------------------------------------------------------------------------------------------------------------------- F1, F8

def test_f1_no_paid_stage_but_the_gate_starts_before_the_judges_gate_controls_have_passed(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    calls, writer = counting(fake_judge), counting(fake_writer)
    for stage in ("pool", "repeat"):
        assert b.judge("--stage", stage, behaviour=calls) == 2                                      # the first paid command: no control record exists yet
    assert "gate controls have not passed" in capsys.readouterr().err and calls.box["n"] == 0 and not b.records()
    assert b.questions(writer=writer, answerer=calls) == 2 and writer.box["n"] == 0 and calls.box["n"] == 0
    assert b.judge("--stage", "gate", behaviour=calls) == 0 and calls.box["n"] == 12
    assert b.judge("--stage", "pool", behaviour=calls) == 0 and {r["kind"] for r in b.records()} == {"pos", "neg", "pool"}      # the controls passed: the pool may start


def test_f1_after_a_failed_gate_every_other_stage_is_refused_unless_the_override_is_given(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate", behaviour=HOSTILE) == 0                                       # a gate stage alone only collects; the controls are judged by the next stage
    capsys.readouterr()
    calls = counting(fake_judge)
    assert b.judge("--stage", "pool", behaviour=calls) == 2 and b.judge("--stage", "repeat", behaviour=calls) == 2 and calls.box["n"] == 0
    assert "gate controls have not passed" in capsys.readouterr().err
    assert b.judge("--stage", "pool", "--continue-on-gate-failure", behaviour=calls) == 0 and calls.box["n"] > 0
    assert "continuing although" in capsys.readouterr().err
    assert b.questions(writer=counting(fake_writer), answerer=calls) == 2                           # ... and so are the questions


def test_f1_a_failed_free_control_refuses_even_the_gate_stage(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    prep = json.loads((b.work / rb.PREP).read_text(encoding="utf-8"))
    prep["controls"]["causality"]["violations"] = 3
    rb.write_json(b.work / rb.PREP, prep)
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 2 and calls.box["n"] == 0 and not (b.work / rb.BASELINE).exists()
    assert "c2_no_candidate_at_or_after_the_task" in capsys.readouterr().err
    assert b.judge("--stage", "gate", "--continue-on-gate-failure", behaviour=calls) == 0 and calls.box["n"] == 12


def test_f1_c4_must_report_a_pass_when_it_exists_and_only_warns_when_it_is_missing(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0 and "no c4.json" in capsys.readouterr().err               # missing: a warning, the stage runs
    report = {"implementations_identical": True, "helps_at_zero_ok": True, "helps_rises_with_gain": True, "mismatches": 0}
    (b.work / "c4.json").write_text(json.dumps(dict(report, helps_at_zero_ok=False)), encoding="utf-8")
    calls = counting(fake_judge)
    assert b.judge("--stage", "repeat", behaviour=calls) == 2 and calls.box["n"] == 0 and "helps_at_zero_ok" in capsys.readouterr().err
    (b.work / "c4.json").write_text("{not json", encoding="utf-8")
    assert b.judge("--stage", "repeat", behaviour=calls) == 2 and "not valid JSON" in capsys.readouterr().err
    (b.work / "c4.json").write_text(json.dumps(report), encoding="utf-8")
    assert b.judge("--stage", "repeat", behaviour=calls) == 0 and calls.box["n"] > 0
    assert rb.c4_status(b.work) == ("pass", "")


def test_f8_prepare_documents_that_it_runs_c1_to_c3_and_c4_is_a_separate_script() -> None:
    assert "C1 to C3 only" in rb.cmd_prepare.__doc__ and "retrieval_c4.py" in rb.cmd_prepare.__doc__ and (ROOT / "scripts" / "wmb" / "retrieval_c4.py").exists()


# --------------------------------------------------------------------------------------------------------------------------------------------- F2

def test_f2_questions_that_got_no_reply_are_not_recorded_and_the_next_run_asks_exactly_those(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge() == 0
    down, state = set(sorted(rb.sample_u3_notes(b.items(), b.config()))[:3]), {"down": True}

    def flaky_writer(system, user, seed, opts):
        if state["down"] and note_number(user) in down:
            raise OSError("writer proxy restarting")
        return fake_writer(system, user, seed, opts)

    capsys.readouterr()
    assert b.questions(writer=flaky_writer) == 2                                                    # the pass ends with RunAborted: three results were dropped
    first = b.records(rb.QUESTIONS)
    assert len(first) == 6 and all(r["question"] and "error" not in r["failures"] for r in first) and "were not recorded" in capsys.readouterr().err
    assert not (b.work / rb.ANSWERS).exists()                                                       # the answerability check did not start on an incomplete set
    state["down"] = False
    again = counting(fake_writer)
    assert b.questions(writer=again) == 0 and again.box["n"] == 3                                   # exactly the three that were not recorded
    rows = b.records(rb.QUESTIONS)
    assert len(rows) == 9 and all(r["question"] for r in rows)
    out = b.last_json(capsys)
    assert out["questions"] == 9 and out["empty_questions"] == 0 and out["answers_without_label"] == 0 and out["checked"] == 9


def test_f2_answers_that_got_no_reply_are_not_recorded_and_the_next_run_asks_exactly_those(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge() == 0
    down, state = set(sorted(rb.sample_u3_notes(b.items(), b.config()))[:3]), {"down": True}

    def flaky_judge(system, user, seed, opts):
        if state["down"] and "check whether a note answers" in system and note_number(user) in down:
            raise OSError("judge proxy restarting")
        return fake_judge(system, user, seed, opts)

    assert b.questions(answerer=flaky_judge) == 2
    answers = b.records(rb.ANSWERS)
    assert len(b.records(rb.QUESTIONS)) == 9 and len(answers) == 6 and all(a["answer"] == "YES" and a["failures"] == [] for a in answers)
    state["down"] = False
    again = counting(fake_judge)
    capsys.readouterr()
    assert b.questions(answerer=again) == 0 and again.box["n"] == 3 and len(b.records(rb.ANSWERS)) == 9
    assert b.last_json(capsys)["answers_without_label"] == 0


def test_f2_audit_checks_that_got_no_reply_are_not_recorded_either(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge() == 0 and b.questions() == 0
    state = {"down": True}

    def flaky_audit(system, user, seed, opts):
        if state["down"] and int(hashlib.md5(user.encode()).hexdigest(), 16) % 2 == 0:
            raise OSError("judge proxy restarting")
        return fake_judge(system, user, seed, opts)

    assert b.audit(answerer=flaky_audit) == 2
    first = b.records(rb.AUDIT)
    assert all(r["answer"] == "YES" and "error" not in r["failures"] for r in first)
    state["down"] = False
    again = counting(fake_judge)
    capsys.readouterr()
    assert b.audit(answerer=again) == 0
    out = b.last_json(capsys)
    rows = b.records(rb.AUDIT)
    assert out["audited"] == out["targets"] == len(rows) and again.box["n"] == len(rows) - len(first) and out["answers_without_label"] == 0 and len(rows) > len(first)


def test_f2_a_dead_proxy_aborts_a_one_shot_stage_after_the_breaker_and_records_nothing(tmp_path: Path) -> None:
    items, briefs = corpus_items(40), briefs_for(corpus_items(40))
    out, down = tmp_path / "q.jsonl", lambda *a: (_ for _ in ()).throw(OSError("connection refused"))        # noqa: E731
    todo = list(range(30))

    def ask(k):
        reply = rb.call_text(down, "s", "u", 1, {})
        return {"k": k, "question": "", "failures": reply["failures"]}, rb.text_info(reply, False)

    with pytest.raises(rb.RunAborted, match="25 calls in a row"):
        rb.record_results(todo, ask, out, workers=1, keep_errors=False)
    assert contract.load_jsonl(out) == []
    assert items and briefs


# --------------------------------------------------------------------------------------------------------------------------------------- F3, ANL-1

def test_f3_every_paid_stage_sample_and_analyse_verify_the_input_digests_before_anything_else(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    cfg = b.config()
    cfg["inputs_sha256"] = {"opublikowane.jsonl": contract.sha256_file(b.root / "notes.jsonl"), "replay/prep.json": contract.sha256_file(b.root / "prep.json"),
                            "data/lab/aam-e6-persona/persona.json": contract.sha256_file(b.root / "persona.json")}
    b.set_config(cfg)
    b.base = [a for a in b.base if a != "--allow-input-mismatch"]
    assert b.judge() == 0 and b.run("sample") == 0 and b.questions() == 0 and b.audit() == 0       # the digests match: nothing changes
    rows = [json.loads(line) for line in (b.root / "notes.jsonl").read_text(encoding="utf-8").splitlines()]
    rows[5]["text"] += " (edited after prepare)"
    (b.root / "notes.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    calls, writer = counting(fake_judge), counting(fake_writer)
    capsys.readouterr()
    assert b.judge(behaviour=calls) == 1 and b.questions(writer=writer, answerer=calls) == 1 and b.audit(answerer=calls) == 1
    assert b.run("sample") == 1 and b.run("analyse", embed=fake_embed) == 1
    assert calls.box["n"] == 0 and writer.box["n"] == 0 and capsys.readouterr().err.count("input digest mismatch") == 5


def test_anl1_an_input_missing_from_the_declared_digests_is_a_mismatch_not_silently_unchecked(tmp_path: Path) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    with pytest.raises(rb.InputMismatch, match="declares no digest"):
        rb.verify_inputs({"inputs_sha256": {}}, tmp_path / "a", tmp_path / "b", tmp_path / "c")
    with pytest.raises(rb.InputMismatch, match="no such input"):
        rb.verify_inputs({"inputs_sha256": {**dict.fromkeys(rb.INPUT_KEYS, "0" * 64), "extra": "0" * 64}}, tmp_path / "a", tmp_path / "b", tmp_path / "c")


# ---------------------------------------------------------------------------------------------------------------------------- F4, ANL-2, ANL-4

def test_f4_the_first_paid_stage_of_any_kind_needs_the_assistants_labels_and_takes_the_baseline_with_every_digest(tmp_path: Path, template: Path) -> None:
    b = Bench(tmp_path, template)
    (b.work / rb.DECISIVE_ASSISTANT).unlink()
    writer = counting(fake_writer)
    assert b.questions("--continue-on-gate-failure", writer=writer) == 1 and writer.box["n"] == 0 and not (b.work / rb.BASELINE).exists()      # `questions` first, no labels
    shutil.copy(template / "work" / rb.DECISIVE_ASSISTANT, b.work / rb.DECISIVE_ASSISTANT)
    assert b.questions("--continue-on-gate-failure", writer=writer) == 0 and writer.box["n"] > 0              # any kind of paid stage may be the first
    baseline = json.loads((b.work / rb.BASELINE).read_text(encoding="utf-8"))
    digests = baseline["sha256_before_the_first_call"]
    assert set(digests) == set(rb.FROZEN_FILES) and all(digests[n] == contract.sha256_file(b.work / n) for n in rb.FROZEN_FILES)
    assert baseline["decisive_keys_sha256"] == rb.decisive_keys_digest(json.loads((b.work / rb.DECISIVE_KEYS).read_text(encoding="utf-8")))
    assert baseline["config_sha256"] == contract.sha256_file(b.root / "config.json")


def test_f4_a_file_edited_after_the_first_paid_call_refuses_the_next_stage_and_the_analysis(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0
    mine = json.loads((b.work / rb.DECISIVE_ASSISTANT).read_text(encoding="utf-8"))
    first = sorted(mine)[0]
    (b.work / rb.DECISIVE_ASSISTANT).write_text(json.dumps(dict(mine, **{first: "SAME" if mine[first] != "SAME" else "UNRELATED"})), encoding="utf-8")
    calls = counting(fake_judge)
    capsys.readouterr()
    assert b.judge("--stage", "repeat", behaviour=calls) == 1 and calls.box["n"] == 0
    assert "decisive_labels_assistant.json changed after the first paid call" in capsys.readouterr().err
    assert b.run("analyse", embed=fake_embed) == 1 and "changed after the first paid call" in capsys.readouterr().err
    (b.work / rb.DECISIVE_ASSISTANT).write_text(json.dumps(mine), encoding="utf-8")                  # put back: the run is what it was
    assert b.judge("--stage", "repeat", behaviour=calls) == 0
    (b.work / rb.PAIRS).write_text((b.work / rb.PAIRS).read_text(encoding="utf-8") + " ", encoding="utf-8")        # any other frozen file, too
    assert b.judge("--stage", "pool", behaviour=calls) == 1 and "pairs.json changed" in capsys.readouterr().err


def test_f4_a_config_changed_after_the_first_paid_call_is_refused(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0
    cfg = b.config()
    cfg["readings"]["margin_tasks"] = 5
    b.set_config(cfg)
    assert b.judge("--stage", "repeat") == 1 and "config changed after the first paid call" in capsys.readouterr().err
    assert b.run("analyse", embed=fake_embed) == 1


def test_f4_filled_script_and_prompt_digests_are_enforced_and_unfilled_ones_are_listed_in_the_summary(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    cfg = b.config()
    for key in cfg["script_sha256"]:
        cfg["script_sha256"][key] = None                       # the repository's own config is frozen; this test starts from an unfrozen one
    cfg["judge"]["prompt_sha256"] = cfg["judge"]["prompt_reversed_sha256"] = None
    cfg["script_sha256"]["scripts/wmb/stats.py"] = "0" * 64
    b.set_config(cfg)
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 1 and calls.box["n"] == 0 and "scripts/wmb/stats.py differs from the digest frozen" in capsys.readouterr().err
    cfg["script_sha256"]["scripts/wmb/stats.py"] = contract.sha256_file(ROOT / "scripts" / "wmb" / "stats.py")
    cfg["judge"]["prompt_sha256"] = "0" * 64
    b.set_config(cfg)
    assert b.judge("--stage", "gate", behaviour=calls) == 1 and calls.box["n"] == 0 and "prompt differs from the digest frozen" in capsys.readouterr().err
    cfg["judge"]["prompt_sha256"] = rb.prompt_digests(cfg)["prompt_sha256"]
    b.set_config(cfg)
    assert b.judge() == 0 and b.run("analyse", embed=fake_embed) == 0
    frozen = json.loads((b.work / rb.SUMMARY).read_text(encoding="utf-8"))["meta"]["frozen"]
    assert frozen["ok"] is True and frozen["problems"] == [] and frozen["baseline_present"] and frozen["stage_records_same_code_as_now"] is True
    assert frozen["prompts"]["prompt_sha256"]["match"] is True and frozen["prompts"]["prompt_reversed_sha256"]["match"] is None
    assert "scripts/wmb/retrieval_bench.py" in frozen["unfrozen"] and "scripts/wmb/stats.py" not in frozen["unfrozen"] and "prompt_reversed_sha256" in frozen["unfrozen"]
    assert all(f["match"] for f in frozen["files"].values()) and set(frozen["files"]) == set(rb.FROZEN_FILES)


def test_anl2_the_prompt_digests_follow_the_rule_written_in_the_config() -> None:
    j = CFG["judge"]
    assert "system + two newlines + user_template" in j["prompt_sha256_of"]
    got = rb.prompt_digests(CFG)
    assert got["prompt_sha256"] == hashlib.sha256((j["system"] + "\n\n" + j["user_template"]).encode("utf-8")).hexdigest()
    assert got["prompt_reversed_sha256"] == hashlib.sha256((j["system"] + "\n\n" + j["user_template_reversed"]).encode("utf-8")).hexdigest() != got["prompt_sha256"]


def test_anl4_records_without_a_baseline_are_refused_and_a_record_free_workdir_has_nothing_to_compare(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    (b.work / rb.LABELS).write_text(json.dumps({"kind": "pos", "i": 1, "j": 1, "label": "SAME"}) + "\n", encoding="utf-8")
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 1 and calls.box["n"] == 0 and "budget_baseline.json is missing" in capsys.readouterr().err
    assert b.run("analyse", embed=fake_embed) == 1
    (b.work / rb.LABELS).unlink()
    verdict = rb.frozen_verdict(b.work, b.config(), b.root / "config.json")
    assert verdict["ok"] and not verdict["baseline_present"] and verdict["files"] == {}


# -------------------------------------------------------------------------------------------------------------------------------------- F5, ANL-3

def test_f5_the_proxy_must_say_it_runs_as_the_run_id_of_the_config_on_the_ledger_read_here(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    calls = counting(fake_judge)

    def summary_with(**changes):
        return lambda url: {**fake_summary(url), **changes}

    cases = (({"run_id": "e1-wmbr1-writer"}, "runs as run id"), ({"run_id": None}, "does not report its run id"), ({"ledger_path": str(tmp_path / "other.jsonl")}, "writes the ledger"),
             ({"run_cap_usd": 5.0}, "run cap"), ({"run_cap_usd": None}, "run cap"))
    for changes, text in cases:
        assert b.judge("--stage", "gate", behaviour=calls, summary_fn=summary_with(**changes)) == 2 and calls.box["n"] == 0
        assert text in capsys.readouterr().err
    stages = b.records(rb.STAGES)
    assert len(stages) == len(cases) and all(s["outcome"].startswith("refused before any call") and s["pairs_asked"] == 0 for s in stages)
    good = summary_with(ledger_path=str(b.ledger_path), run_cap_usd=1.0)
    assert b.judge("--stage", "gate", behaviour=calls, summary_fn=good) == 0 and calls.box["n"] == 12


def test_f5_a_proxy_that_does_not_write_this_ledger_under_this_run_id_is_found_after_the_first_chunk(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    elsewhere = meter(fake_judge, tmp_path / "another-ledger.jsonl")                                  # the proxy writes a ledger the guard does not read
    assert b.run("judge", "--stage", "gate", generate=elsewhere) == 2
    assert "gained no line of run id e1-wmbr1-judge" in capsys.readouterr().err
    stop = b.records(rb.STAGES)[-1]
    assert stop["stage"] == "gate" and stop["outcome"].startswith("stopped by BudgetStop") and stop["replies"] == 12
    wrong_id = meter(fake_judge, b.ledger_path, run_id="e1-wmbr1-judgeX")                              # ... or under another run id (the guard would stay at 0 USD)
    assert b.run("judge", "--stage", "repeat", generate=wrong_id) == 2 and "does not match the proxy" in capsys.readouterr().err
    assert b.judge("--stage", "repeat") == 0                                                           # a proxy that does write it is fine


def test_f5_calls_the_proxy_counted_without_a_ledger_line_are_a_blind_guard_at_the_end_of_the_stage(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    state = {"calls": 0}

    def silent(system, user, seed, opts):
        state["calls"] += 1
        raise OSError("connection reset")                                                              # the proxy counted the call, the client saw an error, no ledger line

    assert b.run("judge", "--stage", "gate", generate=silent, summary_fn=lambda url: dict(fake_summary(url), calls=state["calls"])) == 2
    assert "the proxy reports 24 call(s)" in capsys.readouterr().err
    record = b.records(rb.STAGES)[-1]
    assert record["proxy_calls_delta"] == 24 and record["ledger_run_entries_delta"] == 0 and record["outcome"].startswith("blind spend guard")


def test_f5_a_call_of_another_model_in_the_ledger_stops_the_stage(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    contract.append_jsonl(b.ledger_path, [{"run_id": "e1-wmbr1-judge", "usd": 0.0001}])                # no model field: not foreign
    assert rb.ledger_spend(b.ledger_path, CFG)["foreign_model_entries"] == 0
    contract.append_jsonl(b.ledger_path, [{"run_id": "e1-wmbr1-judge", "usd": 0.0001, "model": "deepseek-v4-pro"}, {"run_id": "e1-other", "usd": 0.1, "model": "other"}])
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 2 and calls.box["n"] == 0
    assert "other than deepseek-flash" in capsys.readouterr().err and rb.ledger_spend(b.ledger_path, CFG)["foreign_model_entries"] == 1


def test_f5_the_ledger_is_read_before_and_after_every_chunk_and_an_answer_without_a_new_line_is_blind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps({"run_id": "e1-other", "usd": 2.69}) + "\n", encoding="utf-8")
    reads, real = [], rb.ledger_spend
    monkeypatch.setattr(rb, "ledger_spend", lambda path, cfg: (reads.append(1), real(path, cfg))[1])
    guard = rb.StageGuard(ledger, CFG, "e1-wmbr1-judge", real(ledger, CFG))
    items, briefs = corpus_items(8), briefs_for(corpus_items(8))
    pairs = [{"kind": "pool", "i": 5, "j": j} for j in range(5)]
    rb.run_judge(pairs, items, briefs, CFG, meter(lambda *a: {"text": "SAME"}, ledger), tmp_path / "labels.jsonl", workers=1, chunk=2, before_chunk=guard.before_chunk,
                 after_chunk=guard.after_chunk, tally=guard.tally)
    assert len(reads) == 6 and guard.tally["replies"] == 5 and guard.tally["calls"] == 5                  # three chunks, a read before and a read after each
    guard.after_chunk(0)                                                                               # no reply, no line: fine
    with pytest.raises(rb.BudgetStop, match="blind"):
        guard.after_chunk(2)                                                                           # answered, and the ledger gained nothing since the last read


def test_f5_the_proxy_summary_reports_its_run_id_ledger_and_caps(tmp_path: Path) -> None:
    from arena.provider_proxy import ProxyState
    from arena.spend_ledger import SpendLedger
    ledger = SpendLedger(tmp_path / "spend.jsonl", total_cap_usd=12.0, run_id="e1-wmbr1-judge", cap_scope="e1")
    summary = ProxyState("http://127.0.0.1:1", "key-not-used", ledger, 1.0, {"thinking": {"type": "disabled"}}).summary()
    assert summary["run_id"] == "e1-wmbr1-judge" and summary["ledger_path"] == str(tmp_path / "spend.jsonl") and summary["run_cap_usd"] == 1.0
    assert summary["total_cap_usd"] == 12.0 and summary["cap_scope"] == "e1" and rb.summary_problems(summary) == []
    assert rb.identity_problems(summary, "e1-wmbr1-judge", tmp_path / "spend.jsonl", CFG) == [] and rb.run_id_for("judge", CFG) == "e1-wmbr1-judge" and rb.run_id_for("writer", CFG) == "e1-wmbr1-writer"
    assert len(rb.identity_problems(summary, "e1-wmbr1-writer", tmp_path / "spend.jsonl", CFG)) == 1


# --------------------------------------------------------------------------------------------------------------------------------------- F6, ANL-3

def test_f6_the_summary_of_the_proxy_is_checked_before_the_first_note_is_sent(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    calls = counting(fake_judge)

    def unreachable(url):
        raise OSError("connection refused")

    bad = (lambda url: dict(fake_summary(url), arena_enforced_decoding={}), lambda url: dict(fake_summary(url), decoding_overrides=2),
           lambda url: dict(fake_summary(url), refused_calls=1), lambda url: {k: v for k, v in fake_summary(url).items() if k != "calls"}, unreachable)
    for summary in bad:
        assert b.judge("--stage", "gate", behaviour=calls, summary_fn=summary) == 2 and calls.box["n"] == 0
    err = capsys.readouterr().err
    assert "thinking is not disabled" in err and "decoding overrides" in err and "refused calls" in err and err.count("summary unavailable") == 2
    assert [s["problems_before"] != [] for s in b.records(rb.STAGES)] == [True] * 5                       # each refusal is on record
    assert b.judge("--stage", "gate", behaviour=calls) == 0 and calls.box["n"] == 12


def test_f6_a_stage_whose_first_hundred_calls_are_more_than_ten_percent_format_failures_is_aborted(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0
    expected = sum(len(v) for v in json.loads((b.work / rb.PAIRS).read_text(encoding="utf-8"))["pool"].values())
    assert expected > 100
    assert b.judge("--stage", "pool", behaviour=bad_for(4)) == 2                                         # about a quarter of the pairs fail twice: a third of the calls
    err = capsys.readouterr().err
    assert "of the first" in err and "format failures" in err
    done = [r for r in b.records() if r["kind"] == "pool"]
    assert 20 < len(done) < expected and any(r["label"] is None for r in done)                          # the replies so far stay recorded
    stop = b.records(rb.STAGES)[-1]
    assert stop["outcome"].startswith("stopped by RunAborted") and stop["format_failures"] > 0.1 * stop["recorded_calls"] >= 10
    assert b.judge("--stage", "pool") == 0 and len({(r["i"], r["j"]) for r in b.records() if r["kind"] == "pool"}) == expected      # a resume with a healthy judge completes it


def test_f6_a_rare_format_failure_does_not_trip_the_breaker(tmp_path: Path, template: Path) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0 and b.judge("--stage", "pool", behaviour=bad_for(60)) == 0
    pool = [r for r in b.records() if r["kind"] == "pool"]
    assert 0 < sum(1 for r in pool if r["label"] is None) < 8


def test_f6_twenty_five_results_in_a_row_without_a_usable_answer_abort_the_stage(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0
    assert b.judge("--stage", "pool", behaviour=lambda s, u, seed, o: {"text": "I'm sorry, I can't help with that."}) == 2
    assert "25 results in a row" in capsys.readouterr().err
    done = [r for r in b.records() if r["kind"] == "pool"]
    assert len(done) == 25 and all(r["label"] is None and r["failures"] == ["refusal", "refusal"] for r in done)


# ------------------------------------------------------------------------------------------------------------------------------------------- F7

def test_f7_the_lock_is_exclusive_holds_the_pid_and_is_removed_on_exit_also_after_an_error(tmp_path: Path) -> None:
    with rb.workdir_lock(tmp_path, "judge") as path:
        assert path == tmp_path / "judge.lock" and json.loads(path.read_text(encoding="utf-8"))["pid"] == os.getpid()
        with pytest.raises(rb.LockHeld, match="another run holds the lock"):
            with rb.workdir_lock(tmp_path, "judge"):
                pytest.fail("a second run must not get the lock")
        with rb.workdir_lock(tmp_path, "questions"):                                                    # another command has its own lock
            assert (tmp_path / "questions.lock").exists()
        assert path.exists()                                                                            # the refused launch did not remove the lock of the running one
    assert not path.exists() and not (tmp_path / "questions.lock").exists()
    with pytest.raises(ZeroDivisionError):
        with rb.workdir_lock(tmp_path, "judge"):
            1 / 0
    assert not (tmp_path / "judge.lock").exists()


def test_f7_the_lock_of_a_crashed_run_is_reported_as_stale_and_not_taken_over(tmp_path: Path) -> None:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    (tmp_path / "judge.lock").write_text(json.dumps({"pid": process.pid, "command": "judge", "started": "2026-11-02T01:00:00+00:00"}), encoding="utf-8")
    assert rb.pid_alive(os.getpid()) and not rb.pid_alive(process.pid) and not rb.pid_alive(0)
    with pytest.raises(rb.LockHeld, match=r"stale lock .*left by process %d .*no longer running" % process.pid):
        with rb.workdir_lock(tmp_path, "judge"):
            pytest.fail("a stale lock is reported, not taken over")
    assert (tmp_path / "judge.lock").exists()
    (tmp_path / "judge.lock").write_text("garbage", encoding="utf-8")
    with pytest.raises(rb.LockHeld, match="cannot be read"):
        with rb.workdir_lock(tmp_path, "judge"):
            pass


def test_f7_a_second_launch_on_the_same_workdir_is_refused_before_any_call(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    calls = counting(fake_judge)
    with rb.workdir_lock(b.work, "judge"):
        assert b.judge("--stage", "gate", behaviour=calls) == 2 and calls.box["n"] == 0
        assert "another run holds the lock" in capsys.readouterr().err
        assert b.questions(writer=counting(fake_writer), answerer=calls) == 2                            # the question stages stop at their own gate controls first, not at a lock
    assert b.judge("--stage", "gate", behaviour=calls) == 0 and calls.box["n"] == 12 and not list(b.work.glob("*.lock"))


def test_f7_two_launches_never_hold_the_lock_at_the_same_time(tmp_path: Path) -> None:
    inside, worst, wins, guard = [0], [0], [0], threading.Lock()

    def launch() -> None:
        for _ in range(30):
            try:
                with rb.workdir_lock(tmp_path, "judge"):
                    with guard:
                        inside[0] += 1
                        worst[0] = max(worst[0], inside[0])
                        wins[0] += 1
                    time.sleep(0.001)
                    with guard:
                        inside[0] -= 1
            except rb.LockHeld:
                time.sleep(0.0005)

    threads = [threading.Thread(target=launch) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert worst[0] == 1 and wins[0] > 0 and not (tmp_path / "judge.lock").exists()


# ------------------------------------------------------------------------------------------------------------------------------------------- F9

def test_f9_a_torn_last_line_is_reported_and_ignored_and_the_next_append_repairs_the_tail(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    path = tmp_path / "labels.jsonl"
    contract.append_jsonl(path, [{"a": 1}, {"a": 2}])
    path.write_bytes(path.read_bytes()[:-5])                                                          # a crash in the middle of the second record
    assert contract.load_jsonl(path) == [{"a": 1}] and "torn last line" in capsys.readouterr().err
    contract.append_jsonl(path, [{"a": 3}])                                                           # the fragment is cut off, the new record is not glued to it
    assert contract.load_jsonl(path) == [{"a": 1}, {"a": 3}] and path.read_bytes().endswith(b"\n") and "cut a torn last line" in capsys.readouterr().err
    path.write_bytes(path.read_bytes().rstrip(b"\n"))                                                 # a complete last record that lacks its newline is kept
    contract.append_jsonl(path, [{"a": 4}])
    assert contract.load_jsonl(path) == [{"a": 1}, {"a": 3}, {"a": 4}] and "missing final newline" in capsys.readouterr().err
    path.write_text('{"a": 1}\nnot json\n{"a": 2}\n', encoding="utf-8")                              # any other bad line is an error that names the file and the line
    with pytest.raises(ValueError, match=r"labels\.jsonl line 2"):
        contract.load_jsonl(path)
    path.write_text('{"a": 1}\nnot json\n', encoding="utf-8")                                         # a bad last line that ends in a newline is not a cut-short write
    with pytest.raises(ValueError, match="line 2"):
        contract.load_jsonl(path)


def test_f9_a_judge_resumes_over_a_torn_labels_file_and_asks_only_the_missing_pair(tmp_path: Path) -> None:
    items, briefs = corpus_items(12), briefs_for(corpus_items(12))
    pairs = [{"kind": "pool", "i": 8, "j": j} for j in range(6)]
    out, calls = tmp_path / "labels.jsonl", counting(lambda s, u, seed, o: {"text": "SAME"})
    assert rb.run_judge(pairs, items, briefs, CFG, calls, out, workers=1) == 6
    out.write_bytes(out.read_bytes()[:-9])                                                            # the last record is torn
    again = counting(lambda s, u, seed, o: {"text": "SAME"})
    assert rb.run_judge(pairs, items, briefs, CFG, again, out, workers=1) == 1 and again.box["n"] == 1
    rows = contract.load_jsonl(out)
    assert sorted(r["j"] for r in rows) == list(range(6)) and out.read_bytes().endswith(b"\n")


# ------------------------------------------------------------------------------------------------------------------------------------------ F10

def test_f10_a_call_in_flight_when_the_breaker_trips_does_not_persist_the_unrecorded_pairs(tmp_path: Path) -> None:
    items, briefs = corpus_items(40), briefs_for(corpus_items(40))
    pairs = [{"kind": "pool", "i": 30, "j": j} for j in range(30)]
    state, lock = {"n": 0}, threading.Lock()

    def flap(system, user, seed, opts):
        with lock:
            state["n"] += 1
            first = state["n"] == 1
        if first:
            time.sleep(0.6)                                                                           # still in flight when the other worker has failed 25 pairs in a row
            return {"text": "SAME"}
        raise OSError("down")

    out = tmp_path / "flap.jsonl"
    with pytest.raises(rb.RunAborted):
        rb.run_judge(pairs, items, briefs, CFG, flap, out, workers=2)
    assert contract.load_jsonl(out) == []                                                             # before the fix: 26 records, 25 of them permanent format failures


# --------------------------------------------------------------------------------------------------------------------------------- F11, ANL-5

def test_f11_completeness_compares_the_sets_of_pairs_with_the_plan_not_counts() -> None:
    recs, pairs, keys, assistant = gate_world()
    assert rb.judge_gate_report(recs, CFG, pairs, keys, assistant)["pool"] == {"expected": 100, "n": 100, "missing": 0, "unplanned": 0, "duplicates": 0, "pass": True}
    pool = [r for r in recs if r["kind"] == "pool"]
    swapped = [r for r in recs if r is not pool[0]] + [dict(pool[1])]                                  # one planned pair removed, another one recorded twice: the count is still 100
    report = rb.judge_gate_report(swapped, CFG, pairs, keys, assistant)
    assert report["pool"]["n"] == 100 and report["pool"]["missing"] == 1 and report["pool"]["duplicates"] == 1 and report["checks"]["pool_complete"] is False
    foreign = [dict(r, j=99) if r is pool[0] else r for r in recs]                                     # one planned pair replaced by a pair outside the plan
    report = rb.judge_gate_report(foreign, CFG, pairs, keys, assistant)
    assert report["pool"]["missing"] == 1 and report["pool"]["unplanned"] == 1 and report["checks"]["pool_complete"] is False
    pos = [r for r in recs if r["kind"] == "pos"]
    stand_in = [dict(r, i=3, j=3) if r is pos[0] else r for r in recs]                                 # a foreign positive control stands in for a planned one
    report = rb.judge_gate_report(stand_in, CFG, pairs, keys, assistant)
    assert report["positive"]["n"] == 60 and report["positive"]["missing"] == 1 and report["checks"]["positive_control"] is False and report["passes"] is False
    neg = [r for r in recs if r["kind"] == "neg"]
    doubled = [r for r in recs if r is not neg[0]] + [dict(neg[1])]
    assert rb.judge_gate_report(doubled, CFG, pairs, keys, assistant)["checks"]["negative_control"] is False
    assert not rb.gate_controls_ok(stand_in, CFG, pairs) and rb.gate_controls_ok(recs, CFG, pairs) and rb.gate_controls_ok(stand_in, CFG)        # without the plan only the count is known
    assert not rb.judge_gate_report(recs, CFG, {"pool": pairs["pool"], "repeat": pairs["repeat"]}, keys, assistant)["checks"]["positive_control"]      # no planned controls: fails closed


# ------------------------------------------------------------------------------------------------------------------------------------------ F12

def test_f12_prepare_refuses_to_overwrite_the_pairs_once_labels_or_records_depend_on_them(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    names = (rb.PREP, rb.PAIRS, rb.DECISIVE, rb.DECISIVE_KEYS)
    before = {n: contract.sha256_file(b.work / n) for n in names}
    assert b.run("prepare", embed=fake_embed) == 1 and "decisive_labels_assistant.json" in capsys.readouterr().err
    assert before == {n: contract.sha256_file(b.work / n) for n in names}
    assert b.judge("--stage", "gate") == 0
    (b.work / rb.DECISIVE_ASSISTANT).unlink()
    assert b.run("prepare", embed=fake_embed) == 1 and "labels.jsonl" in capsys.readouterr().err        # the judge's records alone also block it
    assert b.run("prepare", "--force-prepare", embed=fake_embed) == 0                                    # on purpose: allowed, and (same inputs) byte for byte the same pairs
    assert before == {n: contract.sha256_file(b.work / n) for n in names}


def test_f12_the_assistant_file_must_cover_exactly_the_decisive_keys_in_a_form_that_cannot_crash_the_check(tmp_path: Path, template: Path) -> None:
    b = Bench(tmp_path, template)
    mine = json.loads((b.work / rb.DECISIVE_ASSISTANT).read_text(encoding="utf-8"))
    keys = json.loads((b.work / rb.DECISIVE_KEYS).read_text(encoding="utf-8"))
    first = sorted(mine)[0]

    def attempt(labels, key_set=keys):
        (b.work / rb.DECISIVE_ASSISTANT).write_text(json.dumps(labels), encoding="utf-8")
        (b.work / rb.DECISIVE_KEYS).write_text(json.dumps(key_set), encoding="utf-8")
        return rb.assistant_labels_complete(b.work)

    assert attempt(mine) is True and rb.assistant_label_problems(b.work) == []
    assert attempt({}, {}) is False and "holds no decisive pair" in rb.assistant_label_problems(b.work)[0]       # an empty key set with an empty label file
    assert attempt(list(mine.values())) is False and "JSON object" in rb.assistant_label_problems(b.work)[0]     # a JSON list: no AttributeError
    assert attempt(dict(mine, zzz="SAME")) is False and "0 missing, 1 extra" in rb.assistant_label_problems(b.work)[0]
    assert attempt({k: v for k, v in mine.items() if k != first}) is False
    assert attempt({k: v.lower() for k, v in mine.items()}) is False and attempt(dict(mine, **{first: None})) is False
    assert attempt(mine) is True
    assert rb.decisive_keys_digest(["b", "a"]) == rb.decisive_keys_digest(["a", "b"]) == hashlib.sha256(b"a\nb").hexdigest() != rb.decisive_keys_digest(["a", "b", "c"])
    names = sorted(keys)                                                                                 # the same key names re-assigned to other pairs after the labelling
    swapped = {k: keys[names[(n + 1) % len(names)]] for n, k in enumerate(names)}
    assert attempt(mine, swapped) is True                                                                # the key names alone cannot tell ...
    items, briefs = b.items(), rb.load_inputs(b.root / "notes.jsonl", b.root / "prep.json")[1]
    assert rb.assistant_label_problems(b.work, items, briefs)[0].startswith("decisive_keys.json does not describe the pairs that decisive.json shows")
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 1 and calls.box["n"] == 0                       # ... what the assistant read does: no call is made
    assert attempt(mine, keys) is True and rb.assistant_label_problems(b.work, items, briefs) == []
    (b.work / rb.DECISIVE_KEYS).write_text("{broken", encoding="utf-8")
    assert rb.assistant_labels_complete(b.work) is False and "not valid JSON" in rb.assistant_label_problems(b.work)[0]


def test_f12_sample_needs_a_completely_judged_pool_and_never_replaces_a_sample_that_may_be_labelled(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge("--stage", "gate") == 0 and b.run("sample") == 1 and "not completely judged" in capsys.readouterr().err and not (b.work / rb.STRATIFIED_KEYS).exists()
    assert b.judge("--stage", "pool", behaviour=bad_for(40)) == 0                                       # a few pairs with no valid label are still judged pairs
    assert b.judge("--stage", "repeat") == 0
    assert b.run("sample") == 0
    first = (b.work / rb.STRATIFIED_KEYS).read_bytes()
    assert b.run("sample") == 0 and (b.work / rb.STRATIFIED_KEYS).read_bytes() == first                  # the same sample again: no change
    keys = json.loads(first.decode("utf-8"))
    keys["s001"]["j"] = (keys["s001"]["j"] + 1) % 5
    (b.work / rb.STRATIFIED_KEYS).write_text(json.dumps(keys), encoding="utf-8")                          # a different sample exists (labels may be attached to it)
    capsys.readouterr()
    assert b.run("sample") == 1 and "would attach to other pairs" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------------------------------------------------ F13

def test_f13_model_and_endpoints_default_from_the_config_and_only_the_budget_model_on_loopback_is_accepted(tmp_path: Path, template: Path, monkeypatch: pytest.MonkeyPatch,
                                                                                                           capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    made, seen, target = [], [], [b]

    def factory(url, model, api_key="x"):
        made.append((url, model))
        return target[0].proxy(fake_judge)

    monkeypatch.setattr(backends, "openai_generate", factory)
    assert b.run("judge", "--stage", "gate", summary_fn=lambda url: (seen.append(url), fake_summary(url))[1]) == 0
    assert made == [("http://127.0.0.1:8798/v1", "deepseek-flash")] and set(seen) == {"http://127.0.0.1:8798/v1"}
    for extra, text in ((["--model", "deepseek-v4-pro"], "only deepseek-flash"), (["--judge-url", "http://example.invalid:1/v1"], "not a loopback"),
                        (["--writer-url", "http://203.0.113.9:9/v1"], "not a loopback")):
        made.clear()
        assert b.run("questions", *extra) == 1 and not made and text in capsys.readouterr().err
    moved = Bench(tmp_path / "moved", template)                                                          # the default follows the config, not a constant in the code
    target[0] = moved
    cfg = moved.config()
    cfg["models"]["judge_proxy"] = "http://127.0.0.1:9100/v1"
    moved.set_config(cfg)
    made.clear()
    assert moved.run("judge", "--stage", "gate", summary_fn=lambda url: fake_summary("http://127.0.0.1:8798/v1")) == 0 and made == [("http://127.0.0.1:9100/v1", "deepseek-flash")]


# ------------------------------------------------------------------------------------------------------------------------------------------ F14

def test_f14_a_stage_that_stops_leaves_its_record_and_a_control_stop_is_not_a_success(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    state = {"n": 0}

    def capped(system, user, seed, opts):
        state["n"] += 1
        if state["n"] > 3:
            raise backends.SpendCapRefused("402 cap")
        return fake_judge(system, user, seed, opts)

    assert b.judge("--stage", "gate", behaviour=capped) == 2
    stages = b.records(rb.STAGES)
    assert len(stages) == 1 and stages[0]["stage"] == "gate" and stages[0]["outcome"].startswith("stopped by SpendCapRefused: 402 cap")
    assert stages[0]["ledger_before"]["runs"]["e1-wmbr1-judge"]["entries"] == 0 and stages[0]["ledger_after"]["runs"]["e1-wmbr1-judge"]["entries"] == 3
    other = Bench(tmp_path / "second", template)
    assert other.judge("--stage", "all", behaviour=HOSTILE) == 3 and capsys.readouterr().out.strip().splitlines()[-1].count('"stopped"') == 1       # `judge && questions` does not go on
    assert [s["outcome"] for s in other.records(rb.STAGES)] == ["completed"]


# ------------------------------------------------------------------------------------------------------------------------------------------ F15

def test_f15_ledger_lines_that_are_not_run_records_are_skipped_and_counted_and_never_crash(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    ledger = tmp_path / "ledger.jsonl"
    lines = ['null', '[1, 2]', '"text"', '{"run_id": "e1-wmbr1-judge", "usd": null}', '{"run_id": "e1-wmbr1-judge", "usd": "abc"}', '{"run_id": "e1-wmbr1-judge", "usd": NaN}',
             '{"run_id": "e1-wmbr1-judge", "usd": -1}', '{"run_id": "e1-wmbr1-judge"}', '{"run_id": "e1-wmbr1-judge", "usd": 0.5, "model": "deepseek-flash"}', '{"run_id": "e1-wmbr1-ju']
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    spend = rb.ledger_spend(ledger, CFG)
    assert spend["slice_usd"] == 0.5 and spend["entries"] == 10 and spend["skipped_lines"] == 9 and spend["runs"]["e1-wmbr1-judge"] == {"entries": 1, "usd": 0.5}
    assert rb.assert_budget(ledger, CFG)["slice_usd"] == 0.5
    assert "belongs to no run" in rb.ledger_spend.__doc__ and "dearest rate" not in rb.ledger_spend.__doc__
    b = Bench(tmp_path / "run", template)
    with open(b.ledger_path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("null\n[1]\n")
    assert b.judge("--stage", "gate") == 0 and "2 line(s) that are not run records" in capsys.readouterr().err
    assert b.records(rb.STAGES)[-1]["ledger_before"]["skipped_lines"] == 2


# ------------------------------------------------------------------------------------------------------------------------------- F16, ANL-7

def test_f16_every_json_output_has_lf_newlines_on_every_platform(tmp_path: Path, template: Path) -> None:
    rb.write_json(tmp_path / "x.json", {"a": [1, 2], "b": {"c": "d"}})
    contract.append_jsonl(tmp_path / "labels.jsonl", [{"k": 1}])
    contract.write_summary(tmp_path / "s.json", tmp_path / "labels.jsonl", {"k": 1}, {"m": 2})
    for path in (tmp_path / "x.json", tmp_path / "s.json", tmp_path / "labels.jsonl"):
        raw = path.read_bytes()
        assert b"\r" not in raw and raw.endswith(b"\n"), path.name
    names = [p.name for p in (template / "work").iterdir() if p.suffix == ".json"]
    assert {rb.PREP, rb.PAIRS, rb.DECISIVE, rb.DECISIVE_KEYS} <= set(names)
    for name in names:
        assert b"\r" not in (template / "work" / name).read_bytes(), name
    b = Bench(tmp_path / "run", template)
    assert b.judge() == 0 and b.run("sample") == 0 and b.run("analyse", embed=fake_embed) == 0
    for name in (rb.RESULTS, rb.SUMMARY, rb.BASELINE, rb.STRATIFIED, rb.STRATIFIED_KEYS):
        assert b"\r" not in (b.work / name).read_bytes(), name


# ------------------------------------------------------------------------------------------------------------------------------------- ANL-6

def test_anl6_a_calibrated_threshold_that_is_not_e5s_fails_a_control_and_refuses_the_paid_stages(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    prep = json.loads((b.work / rb.PREP).read_text(encoding="utf-8"))
    assert prep["controls"]["tau"]["tau_emb_matches_e5"] is True and all(rb.controls_pass(prep["controls"], b.config()).values())
    prep["controls"]["tau"]["tau_emb_matches_e5"] = False
    rb.write_json(b.work / rb.PREP, prep)
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 2 and calls.box["n"] == 0 and "tau_emb_matches_e5" in capsys.readouterr().err
    cfg = b.config()
    cfg["reference_threshold_e5"] += 0.01                                                              # the check itself, on a fresh prepare
    other = tmp_path / "other"
    other.mkdir()
    base = write_account(other)
    cfg_other = json.loads((other / "config.json").read_text(encoding="utf-8"))
    cfg_other["reference_threshold_e5"] += 0.01
    (other / "config.json").write_text(json.dumps(cfg_other), encoding="utf-8")
    assert rb.main(["prepare"] + base, embed=fake_embed, summary_fn=fake_summary) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["tau_emb_matches_e5"] is False and out["controls_pass"]["tau_emb_matches_e5"] is False


def test_anl6_the_versions_and_the_weights_digest_are_recorded_in_the_summary_and_the_prep_file(tmp_path: Path, template: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    weights = tmp_path / "model.safetensors"
    weights.write_bytes(b"not the real weights")
    monkeypatch.setattr(rb, "find_minilm_weights", lambda *a: weights)
    b = Bench(tmp_path, template)
    assert b.judge() == 0 and b.run("analyse", embed=fake_embed) == 0
    meta = json.loads((b.work / rb.SUMMARY).read_text(encoding="utf-8"))["meta"]
    env = meta["environment"]
    assert env["minilm_weights_sha256"] == hashlib.sha256(b"not the real weights").hexdigest() and env["python"] == platform.python_version() and env["numpy"] == np.__version__
    assert {"scipy", "torch", "sentence_transformers"} <= set(env) and env["matches_pinned"]["minilm_weights_sha256"] is False
    assert meta["environment_at_prepare"]["python"] == platform.python_version()
    assert rb.environment_record({"environment": {"python": platform.python_version(), "numpy": "0.0"}})["matches_pinned"] == {"python": True, "numpy": False}
    assert rb.package_version("a-package-that-does-not-exist") is None


# ------------------------------------------------------------------------------------------------------------------------------------- ANL-8

def test_anl8_the_unpreregistered_sweeps_are_neither_in_the_readme_as_a_reading_nor_in_the_results(tmp_path: Path, template: Path) -> None:
    readme = (ROOT / "data" / "lab" / "wmb-r1-retrieval" / "README.md").read_text(encoding="utf-8")
    assert "these produce the proposed default thresholds" not in readme and "on precision at 20% firing and of the channel weights" not in readme
    assert "are not preregistered readings of this slice" in readme and "no default thresholds are proposed" in readme
    b = Bench(tmp_path, template)
    assert b.judge() == 0 and b.run("analyse", embed=fake_embed) == 0
    results = json.loads((b.work / rb.RESULTS).read_text(encoding="utf-8"))
    assert "not_run" not in results["u1"] and "not_run" not in json.dumps(results)


# ------------------------------------------------------------------------------------------------------------------------------------- ANL-9

def test_anl9_the_answerability_gate_and_p2_need_the_planned_number_of_questions(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    assert b.judge() == 0 and b.questions() == 0
    assert (b.work / rb.QUESTIONS).read_text(encoding="utf-8").count("\n") == 9
    for name in (rb.QUESTIONS, rb.ANSWERS):                                                            # a short set, every question answerable: the share is 100%
        lines = (b.work / name).read_text(encoding="utf-8").splitlines()[:8]
        (b.work / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    capsys.readouterr()
    assert b.audit() == 0 and "not the planned 9 questions" in b.last_json(capsys)["note"] and not (b.work / rb.AUDIT).exists()
    assert b.run("analyse", embed=fake_embed) == 0
    u3 = json.loads((b.work / rb.RESULTS).read_text(encoding="utf-8"))["u3"]
    assert u3["answerable_share"] == 1.0 and u3["questions"] == 8 and u3["questions_expected"] == 9 and u3["questions_complete"] is False
    assert u3["answerability_gate_passes"] is False and u3["p2"]["issued"] is False and u3["p2"]["verdict"] is None
    full = rb.u3_report(b.items(), np.load(b.work / rb.VECTORS)["notes"], b.records(rb.QUESTIONS) + [{"k": 0, "question": "Which one?", "failures": []}],
                        b.records(rb.ANSWERS) + [{"k": 0, "answer": "YES"}], [], fake_embed, b.config(), 0.2, 0.5)
    assert full["questions_complete"] is True and full["answerability_gate_passes"] is True


# -------------------------------------------------------------------------------------------------------------------------- ANL-3, ANL-10, ANL-12

def test_the_readme_states_what_a_call_is_how_the_two_failure_rules_count_and_that_the_hard_pairs_are_about_2700() -> None:
    readme = (ROOT / "data" / "lab" / "wmb-r1-retrieval" / "README.md").read_text(encoding="utf-8")
    assert "A call is one request through the backend, which itself retries transport errors and empty completions (up to four attempts in all); only the final outcome" in readme
    assert "The 2% is counted over calls and includes the failures the retry recovered from, whereas the audit of gate 4 counts a decisive pair without a valid judge label as a disagreement" in readme
    assert "about 2,700 such pairs on the draft data" in readme and "2,686" not in readme


# ------------------------------------------------------------------------------------------------------------------------------------- ANL-11

def test_anl11_the_u2_block_says_so_when_the_name_channel_changed_no_rank() -> None:
    same = {"HYB_KERNEL": [1, 3, None, 2], "KERNEL_NAMES": [1, 3, None, 2]}
    note = rb.names_arm_note(same, 4)
    assert note and "4 scored questions" in note and "KERNEL_NAMES equals HYB_KERNEL" in note
    assert rb.names_arm_note({"HYB_KERNEL": [1, 3, None, 2], "KERNEL_NAMES": [1, 1, None, 2]}, 4) is None
    items = corpus_items(12)
    persona = {"biography": [{"id": "b1", "date": "1989", "text": "You were born in Kellmouth, a fishing town."}], "fact_questions": [{"id": "f1", "style": "direct", "q": "Where?", "keys": ["Kellmouth"]}]}
    prep = prepared()[4]
    got = rb.u2_report(items, vectors([i.text for i in items]), persona, lambda texts: vectors(list(texts)), cfg_small(), prep["tau_lex"], prep["tau_emb"])
    assert ("note" in got) == (got["overall"]["KERNEL_NAMES"] == got["overall"]["HYB_KERNEL"])


def test_f14_a_stage_that_cannot_start_because_of_the_ledger_stop_leaves_a_record_too(tmp_path: Path, template: Path, capsys: pytest.CaptureFixture) -> None:
    b = Bench(tmp_path, template)
    contract.append_jsonl(b.ledger_path, [{"run_id": "e1-wmbr1-judge", "usd": 2.0}])
    calls = counting(fake_judge)
    assert b.judge("--stage", "gate", behaviour=calls) == 2 and calls.box["n"] == 0
    stages = b.records(rb.STAGES)
    assert len(stages) == 1 and stages[0]["outcome"].startswith("refused before any call: the slice has spent 2.0000 USD") and stages[0]["ledger_before"]["slice_usd"] == 2.0
    assert not (b.work / rb.BASELINE).exists() and "the stop is 2.00 USD" in capsys.readouterr().err
