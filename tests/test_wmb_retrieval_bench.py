"""wmb.retrieval_bench: the building blocks of WMB-R1, on synthetic notes only (no model call, no private data)."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import shadow_baseline_measures as sbm  # noqa: E402
from wmb import contract, memory_kernel as mk, retrieval_bench as rb  # noqa: E402

CFG = rb.load_config()
SYN = {"boat": "ferry", "firm": "company", "records": "ledgers"}


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


def cfg_small(warmup: int = 4) -> dict:
    cfg = json.loads(json.dumps(CFG))
    cfg["tasks"]["warmup"] = warmup
    return cfg


def prepared(n: int = 12, warmup: int = 4):
    items = corpus_items(n)
    briefs = briefs_for(items)
    nv, bv = vectors([i.text for i in items]), vectors(briefs)
    return items, briefs, nv, bv, rb.prepare_rankings(items, briefs, nv, bv, cfg_small(warmup))


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


def test_prepared_rankings_are_causal_complete_and_the_hybrid_is_the_max_of_the_two_calibrated_channels() -> None:
    items, briefs, nv, bv, prep = prepared()
    tasks = list(range(4, len(items)))
    assert set(prep["rankings"]) == set(rb.METHODS) and all(sorted(r) == tasks for r in prep["rankings"].values())
    assert rb.causality_violations(prep["rankings"]) == 0 and prep["times"] == sorted(prep["times"])
    cover = np.array([r[0][1] * rb.LEX_PROFILE["lex_tau"] if r else 0.0 for r in (prep["rankings"]["LEX_KERNEL"][i] for i in tasks)])
    assert prep["tau_lex"] == rb.choose_threshold(list(cover), CFG["tasks"]["candidate_share_for_calibration"])
    for i in tasks:
        corpus = rb.Corpus(range(i), [mk.tokens(it.text) for it in items], nv)
        strength = np.maximum(corpus.coverage(mk.tokens(briefs[i])) / prep["tau_lex"], corpus.cosine(bv[i]) / prep["tau_emb"])
        ref = rb.rank_pairs(strength, corpus.docs, False)
        got = prep["rankings"]["HYB_KERNEL"][i]
        assert got[0][0] == ref[0][0] and abs(got[0][1] * 0.05 - ref[0][1]) < 1e-4
    agreement = rb.reference_agreement(items, briefs, nv, bv, prep["rankings"], tasks, cfg_small(), prep["tau_lex"], prep["tau_emb"], n=5)
    assert agreement["same_first_candidate"] == agreement["tasks"] == 5 and agreement["max_abs_diff_coverage"] < 1e-8
    own = rb.self_retrieval(items, briefs, nv, bv, tasks, cfg_small(), prep["tau_lex"], prep["tau_emb"])
    assert set(own) == set(rb.METHODS) and all(0.0 <= v <= 1.0 for v in own.values())


def test_the_pool_is_the_union_of_the_top_candidates_and_the_controls_are_what_they_say() -> None:
    items, briefs, nv, bv, prep = prepared()
    tasks = list(range(4, len(items)))
    pool = rb.build_pool(prep["rankings"], tasks, 2, rb.METHODS)
    for i in tasks:
        assert pool[i] == sorted({j for m in rb.METHODS for j, _ in prep["rankings"][m][i][:2]}) and all(j < i for j in pool[i])
    cfg = cfg_small()
    cfg["judge"]["gate"].update({"positive_control_n": 5, "negative_control_n": 4})
    pairs = rb.control_pairs(cfg, tasks, [mk.tokens(b) for b in briefs], [mk.tokens(it.text) for it in items], nv, bv)
    assert len(pairs["positive"]) == 5 and all(i == j and i in tasks for i, j in pairs["positive"])
    for i, j in pairs["negative"]:
        assert j < i and not set(mk.tokens(briefs[i])) & set(mk.tokens(items[j].text)) and float(bv[i] @ nv[j]) < cfg["judge"]["gate"]["negative_control_max_cosine"]
    assert pairs == rb.control_pairs(cfg, tasks, [mk.tokens(b) for b in briefs], [mk.tokens(it.text) for it in items], nv, bv)


def test_labels_are_read_from_one_word_and_a_bad_reply_is_retried_once_with_another_seed(tmp_path: Path) -> None:
    for raw, label in (("SAME", "SAME"), (" related. ", "RELATED"), ("UNRELATED", "UNRELATED"), ("The answer is SAME.", "SAME"), ("SAME or RELATED", None), ("", None), ("maybe", None)):
        assert rb.parse_label(raw) == label, raw
    items, briefs = corpus_items(6), briefs_for(corpus_items(6))
    seeds, replies = [], {"n": 0}

    def generate(system: str, user: str, seed: int, opts: dict) -> dict:
        seeds.append(seed)
        replies["n"] += 1
        return {"text": "hmm" if replies["n"] == 1 else ("SAME" if "note 0" in user else "UNRELATED")}

    out = tmp_path / "labels.jsonl"
    pairs = [{"kind": "pool", "i": 5, "j": 0, "seed_offset": 0}, {"kind": "pool", "i": 5, "j": 1, "seed_offset": 0}]
    assert rb.run_judge(pairs, items, briefs, CFG, generate, out, workers=1) == 2
    rows = {(r["i"], r["j"]): r for r in contract.load_jsonl(out)}
    assert rows[(5, 0)]["label"] == "SAME" and rows[(5, 1)]["label"] == "UNRELATED" and seeds[0] != seeds[1]         # the first reply was malformed: one retry
    assert rb.run_judge(pairs, items, briefs, CFG, generate, out, workers=1) == 0 and len(contract.load_jsonl(out)) == 2     # resumable: nothing left to do
    never = lambda *a, **k: {"text": "perhaps"}
    out2 = tmp_path / "bad.jsonl"
    rb.run_judge(pairs[:1], items, briefs, CFG, never, out2, workers=1)
    assert contract.load_jsonl(out2)[0]["label"] is None


def test_the_fire_set_takes_the_highest_scores_with_ties_by_task_number_and_never_a_task_without_a_candidate() -> None:
    scores = np.array([0.9, 0.9, 0.5, -np.inf, 0.1, 0.9, 0.2, 0.3, 0.4, 0.8])
    relevant = np.array([1, 0, 1, 0, 0, 1, 0, 0, 1, 1], dtype=bool)
    idx = np.arange(10)
    assert list(idx[rb.fired(scores, idx, 0.3)]) == [0, 1, 5] and rb.hits_at(scores, relevant, idx, 0.3) == (2, 1)
    assert list(idx[rb.fired(scores, idx, 0.1)]) == [0] and len(rb.fired(scores, idx, 1.0)) == 9
    assert len(rb.fired(scores, idx, 0.25)) == 3 and len(rb.fired(scores, idx, 0.2)) == 2                    # ceil(q * T) tasks
    resample = np.array([3, 3, 3, 0])                                                                       # duplicates count separately; the empty task stays unfired
    assert list(rb.fired(scores, resample, 0.75)) == [3]


def test_the_paired_bootstrap_finds_a_planted_gain_and_stays_silent_on_identical_methods() -> None:
    rng = np.random.default_rng(3)
    t = 214
    base = rng.random(t)
    rel_lex = rng.random(t) < 0.3
    lex = base.copy()
    hyb = base.copy()
    gain = rng.choice(np.flatnonzero(~rel_lex), 25, replace=False)                                          # tasks the hybrid fires on with a relevant first candidate
    rel_hyb = rel_lex.copy()
    rel_hyb[gain] = True
    hyb[gain] = 2.0 + rng.random(25)
    planted = rb.paired_hits_difference(hyb, rel_hyb, lex, rel_lex, 0.2, 400, 5)
    assert planted["d"] > 6 and planted["lo"] > 0 and rb.verdict_p1(planted, 6) == "EMBEDDER_HELPS_GATE"
    same = rb.paired_hits_difference(lex, rel_lex, lex, rel_lex, 0.2, 400, 5)
    assert same == {"d": 0, "lo": 0.0, "hi": 0.0} and rb.verdict_p1(same, 6) == "LEXICAL_SUFFICIENT_FOR_GATE"
    assert rb.paired_hits_difference(hyb, rel_hyb, lex, rel_lex, 0.2, 400, 5) == planted
    assert rb.verdict_p1({"d": 7, "lo": -1.0, "hi": 15.0}, 6) == "UNRESOLVED" and rb.verdict_p1({"d": 6, "lo": 0.5, "hi": 12.0}, 6) == "EMBEDDER_HELPS_GATE"
    assert rb.verdict_p1({"d": 5, "lo": 0.5, "hi": 9.0}, 6) == "UNRESOLVED" and rb.verdict_p1({"d": 2, "lo": -3.0, "hi": 5.99}, 6) == "LEXICAL_SUFFICIENT_FOR_GATE"
    assert rb.verdict_p2({"d": 0.2, "lo": 0.05, "hi": 0.4}, 0.15, 0.10) == "EMBEDDER_RESCUES" and rb.verdict_p2({"d": 0.0, "lo": -0.1, "hi": 0.09}, 0.15, 0.10) == "NO_RESCUE"
    assert rb.verdict_p2({"d": 0.1, "lo": -0.1, "hi": 0.3}, 0.15, 0.10) == "UNRESOLVED"


def test_a_static_collection_ranks_a_paraphrase_by_meaning_only_in_the_embedding_methods() -> None:
    items = corpus_items(12)
    texts = [i.text for i in items]
    vecs = vectors(texts)
    prep = rb.prepare_rankings(items, briefs_for(items), vectors(texts), vectors(briefs_for(items)), cfg_small())
    coll = rb.StaticCollection(texts, ["account_history"] * 12, rb.synthetic_times(items), vecs, CFG, prep["tau_lex"], prep["tau_emb"])
    query = "boat firm records"                                                                               # three words of notes 0 and 6 said with synonyms: no shared stem
    ranking = coll.rank(query, vectors([query])[0], "note")
    assert set(ranking) == set(rb.METHODS)
    assert rb.gold_rank(ranking["EMB_MINILM"], {0, 6}) in (1, 2) and rb.gold_rank(ranking["HYB_KERNEL"], {0, 6}) in (1, 2)
    assert rb.gold_rank(ranking["LEX_BM25"], {0, 6}) is None or rb.gold_rank(ranking["LEX_BM25"], {0, 6}) > 2
    assert rb.gold_rank([(3, 1.0), (5, 0.5)], {5}) == 2 and rb.gold_rank([(3, 1.0)], {9}) is None
    ranks = [1, 4, None, 2]
    assert rb.recall_at(ranks, 1) == 0.25 and rb.recall_at(ranks, 3) == 0.5 and rb.recall_at(ranks, 10) == 0.75 and rb.reciprocal_rank(ranks) == pytest.approx((1 + 0.25 + 0.5) / 4)


def test_question_overlap_the_sample_of_notes_and_the_persona_gold_follow_their_definitions() -> None:
    assert rb.question_overlap("Which ferry company kept ledgers?", "the ferry company ledgers were audited") == pytest.approx(3 / 4)
    assert rb.question_overlap("Who audited the books?", "the ferry company ledgers were audited") == pytest.approx(1 / 2) and rb.question_overlap("the of", "anything") == 0.0
    items = [sbm.Item("i%03d" % k, date(2026, 9, 1 + k % 28), " ".join(["w"] * (5 + k))) for k in range(234)]
    cfg = json.loads(json.dumps(CFG))
    cfg["u3"]["per_length_tercile"] = 40
    chosen = rb.sample_u3_notes(items, cfg)
    assert len(chosen) == 120 and chosen == sorted(set(chosen)) and chosen == rb.sample_u3_notes(items, cfg)
    assert sum(1 for j in chosen if j < 78) == 40 and sum(1 for j in chosen if 78 <= j < 156) == 40 and sum(1 for j in chosen if j >= 156) == 40
    persona = {"biography": [{"id": "b1", "text": "You were born in Kellmouth, a fishing town."}, {"id": "b2", "text": "Your mother kept the ledgers; Imre was your colleague."}],
               "fact_questions": [{"id": "f1", "q": "Where?", "keys": ["Kellmouth"]}, {"id": "f2", "q": "Who?", "keys": ["imre", "Edda"]}, {"id": "f3", "q": "Part?", "keys": ["ledger"]}]}
    assert rb.persona_gold(persona) == [{0}, {1}, set()]                                                        # whole words only: 'ledger' is not 'ledgers'


# ---------------------------------------------------------------------------------------------------- the whole pipeline on a synthetic account

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
                           {"id": "f3", "style": "direct", "q": "Where do you live?", "keys": ["Anchor Lane"]}]}
    (tmp / "persona.json").write_text(json.dumps(persona), encoding="utf-8")
    cfg = json.loads(json.dumps(CFG))
    cfg["tasks"]["warmup"] = 6
    cfg["judge"]["gate"].update({"positive_control_n": 6, "positive_control_min_same": 5, "negative_control_n": 6, "negative_control_min_unrelated": 5, "hand_sample_n": 10})
    cfg["judge"]["prevalence_rule_min_tasks_with_same"] = 5
    cfg["readings"].update({"margin_tasks": 1, "shuffle_draws": 20})
    cfg["readings"]["bootstrap"]["draws"] = 200
    cfg["u3"]["per_length_tercile"] = 3
    (tmp / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return ["--notes", str(tmp / "notes.jsonl"), "--prep", str(tmp / "prep.json"), "--persona", str(tmp / "persona.json"), "--config", str(tmp / "config.json"), "--workdir", str(tmp / "work"),
            "--workers", "2"]


def fake_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    if "check whether a note answers" in system:
        return {"text": "YES"}
    brief = user.split("Task (what the author was asked to write about):\n")[1].split("\n\nEarlier note")[0]
    note = user.split("Earlier note by the same author:\n")[1].split("\n\nHow does")[0]
    shared = len(set(mk.tokens(brief)) & set(mk.tokens(note)))
    return {"text": "SAME" if shared >= 3 else ("RELATED" if shared >= 1 else "UNRELATED")}


def fake_writer(system: str, user: str, seed: int, opts: dict) -> dict:
    note = user.split("Note:\n")[1].split("\n\nWrite one question")[0]
    return {"text": "Which %s?" % " ".join(SYN.get(w, w) for w in note.split()[3:7])}


def fake_embed(texts):
    return vectors(list(texts))


def run_pipeline(tmp: Path, hand_flips: int = 1):
    base = write_account(tmp)

    def run(*argv, **kw):
        return rb.main(list(argv) + base, **kw)

    assert run("prepare", embed=fake_embed) == 0
    assert run("judge", "--stage", "all", generate=fake_judge) == 0
    assert run("hand-sample") == 0
    work = tmp / "work"
    sample = json.loads((work / rb.HAND).read_text(encoding="utf-8"))
    truth = {r["key"]: rb.parse_label(fake_judge("", "Task (what the author was asked to write about):\n%s\n\nEarlier note by the same author:\n%s\n\nHow does" % (r["task"], r["note"]), 0, {})["text"])
             for r in sample}
    mine = dict(truth)
    for key in sorted(mine)[:hand_flips]:
        mine[key] = "UNRELATED" if mine[key] == "SAME" else "SAME"
    (work / rb.HAND_LABELS).write_text(json.dumps(mine), encoding="utf-8")
    assert run("questions", writer=fake_writer, generate=fake_judge) == 0
    assert run("analyse", embed=fake_embed) == 0
    return base, work


def test_the_whole_pipeline_runs_resumes_and_leaves_a_summary_that_a_second_computation_confirms(tmp_path: Path) -> None:
    base, work = run_pipeline(tmp_path)
    results = json.loads((work / rb.RESULTS).read_text(encoding="utf-8"))
    gate = results["judge_gate"]
    assert gate["positive_n"] == 6 and gate["negative_n"] == 6 and gate["checks"]["positive"] and gate["checks"]["negative"] and gate["repeat_agreement"] == 1.0
    assert gate["format_failure_share"] == 0.0 and gate["hand_n"] == 10 and gate["hand_agreement"] == 0.9 and gate["passes"] is True
    assert results["controls"]["causality_violations"] == 0 and results["primary_relevance"] in ("strict", "lenient")
    u1 = results["u1"][results["primary_relevance"]]
    assert u1["tasks"] == 30 and set(u1["methods"]) >= set(rb.METHODS) | {"REF_E5"} and u1["p1"]["verdict"] in ("EMBEDDER_HELPS_GATE", "LEXICAL_SUFFICIENT_FOR_GATE", "UNRESOLVED")
    for m in rb.METHODS:
        for q, fired_n in (("0.1", 3), ("0.2", 6), ("0.3", 9)):
            cell = u1["methods"][m][q]
            assert cell["hits"] + cell["false_injections"] == fired_n and cell["hits_at_3"] >= cell["hits"]
    assert results["c4_shuffle"]["shuffles"] == 20 and 0.0 <= results["c4_shuffle"]["helps_share"] <= 1.0
    assert results["u3"]["retained"] > 0 and set(results["u3"]["by_overlap_tercile"]) == {"low", "middle", "high"} and "p2" in results["u3"]
    assert results["u2"]["with_gold"] == 3 and "KERNEL_NAMES" in results["u2"]["overall"] and results["u2"]["overall"]["KERNEL_NAMES"]["recall@3"] >= 0.66
    assert results["controls_ok"] is True and results["c4_shuffle"]["passes"] is True and not results["decision"].startswith("NOT_APPLIED")
    summary = json.loads((work / rb.SUMMARY).read_text(encoding="utf-8"))
    assert summary["records_sha256"] == contract.sha256_file(work / rb.LABELS) and summary["meta"]["script_sha256"] == contract.sha256_file(Path(rb.__file__))
    cfg = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    items, _ = rb.load_inputs(tmp_path / "notes.jsonl", tmp_path / "prep.json")
    persona = json.loads((tmp_path / "persona.json").read_text(encoding="utf-8"))
    verdict = contract.verify_summary(work / rb.SUMMARY, work / rb.LABELS, lambda records: rb.compute_results(work, items, persona, cfg, fake_embed, records))
    assert verdict == {"records_sha256": True, "aggregates": True}

    def forbidden(*a, **k):
        raise AssertionError("a finished run must not call the judge again")

    assert rb.main(["judge", "--stage", "all"] + base, generate=forbidden) == 0                              # resumable: nothing left to ask
    labels = contract.load_jsonl(work / rb.LABELS)
    broken = [dict(r, label="UNRELATED") if r["kind"] == "pos" else r for r in labels]
    hand, mine = json.loads((work / rb.HAND).read_text(encoding="utf-8")), json.loads((work / rb.HAND_LABELS).read_text(encoding="utf-8"))
    assert rb.judge_gate_report(broken, hand, mine, cfg)["passes"] is False


def test_a_failed_judge_gate_means_the_decision_is_not_applied(tmp_path: Path) -> None:
    base, work = run_pipeline(tmp_path, hand_flips=6)                                                      # the hand reading disagrees on 6 of 10 pairs
    results = json.loads((work / rb.RESULTS).read_text(encoding="utf-8"))
    assert results["judge_gate"]["checks"]["hand"] is False and results["judge_gate"]["passes"] is False and results["decision"].startswith("NOT_APPLIED")
    assert rb.decision("EMBEDDER_HELPS_GATE", "NO_RESCUE", True, True) == "ADD_EMBEDDER_PROFILE_FOR_NOTE_WRITING_MEMORY"
    assert rb.decision("LEXICAL_SUFFICIENT_FOR_GATE", "EMBEDDER_RESCUES", True, True).startswith("LEXICAL_FOR_NOTES") and rb.decision("LEXICAL_SUFFICIENT_FOR_GATE", None, True, True) == "STAY_LEXICAL"
    assert rb.decision("UNRESOLVED", "NO_RESCUE", True, True) == "LEXICAL_IN_SHADOW_REVISIT_WITH_MORE_TASKS" and rb.decision("UNRESOLVED", None, False, True).startswith("NOT_APPLIED")
