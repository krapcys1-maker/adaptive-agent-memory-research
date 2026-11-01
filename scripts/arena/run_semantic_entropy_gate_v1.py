#!/usr/bin/env python3
"""SEMANTIC_ENTROPY_SUFFICIENCY_GATE -- first genuine causal test.

Per data/lab/arena/semantic-entropy-gate-v1/selection.json (6 fresh,
gold-blind units). BASE = standard unconditional compact context, single
temp=0 final answer. GATE = M=4 samples at temp=0.7 -> semantic entropy
(scripts/arena/calibrate_semantic_entropy_gate.py's own clustering code,
reused not reimplemented) -> if entropy > 0.5 bits, escalate by appending
RAW_PROVENANCE's raw session behind the top-1 hit
(scripts/arena/mechanism_ablation.raw_session(), the same frozen code
Entry H itself uses) -> single temp=0 final answer on whichever context the
gate selected.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SELECTION = ROOT / "data/lab/arena/semantic-entropy-gate-v1/selection.json"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")

ENTROPY_THRESHOLD = 0.5


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--sample-temperature", type=float, default=0.7)
    parser.add_argument("--cluster-threshold", type=float, default=0.85)
    parser.add_argument("--cap-usd", type=float, default=0.60)
    parser.add_argument("--total-cap-usd", type=float, default=0.60)
    parser.add_argument("--cap-scope", default="seg-v1-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/semantic-entropy-gate-v1-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/semantic-entropy-gate-v1/results.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    sel_units = {u["question_id"]: u for u in selection["units"]}
    with CORPUS.open(encoding="utf-8") as fh:
        corpus = {r["question_id"]: r for r in json.load(fh) if r["question_id"] in sel_units}
    assert len(corpus) == 6, f"selection changed shape: {len(corpus)} units found"

    from arena.spend_ledger import SpendLedger, TotalCapReached
    from arena.decoding import SpendCapReached
    from arena.run_pilot import build_mem0, load_key
    from arena.run_arena_pilot import as_records
    from arena.retrieval_truth import canonical_time, session_map
    from arena.mechanism_ablation import raw_session
    from arena.calibrate_semantic_entropy_gate import greedy_cluster, semantic_entropy
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash
    from openai import APIStatusError as ProxyCapReached

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    total_sessions = sum(len(r.get("haystack_sessions") or []) for r in corpus.values())
    print("=== COST GATE (before first paid call) ===")
    print("RESEARCH_QUESTION: does a semantic-entropy-gated escalation (compact-only "
          "when the reader agrees with itself across samples, compact+raw when it "
          "doesn't) match BASE's accuracy while escalating selectively rather than "
          "unconditionally like RAW_PROVENANCE (~21.4x token overhead every time)?")
    print("WHY_THIS_CALL_IS_NEEDED: calibration (PM-20260825-41d5d71e) found a clean, "
          "correctly-directioned entropy separation (sufficient=0.300 vs "
          "insufficient=1.104) on 8 already-labeled units at $0.003 -- this is the "
          "first genuine causal (fresh gold-blind, BASE-vs-GATE) test")
    print("EXPECTED_INFORMATION_GAIN: MECHANISM_SEG_EXPLORATORY_SUPPORTED vs FAIL -- a "
          "pass would be AAMR's 2nd validated-mechanism *candidate* (pending its own "
          "replication), first one sourced from a ResearchOS handoff")
    print("CHEAPEST_ALTERNATIVE: none -- calibration already done at near-$0; this is "
          "the smallest fresh gold-blind sample this project's own convention supports")
    print(f"PROJECTED_CALLS: ~{total_sessions} ingest + {len(corpus) * args.samples} "
          f"entropy-sampling reader calls + up to 12 final-answer reader calls (2 arms "
          f"x 6 units) + ~24-36 judge")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f}")
    if args.project_only:
        return 0

    run_id = f"{args.cap_scope}run"
    assert run_id.startswith(args.cap_scope)
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=run_id,
                         cap_scope=args.cap_scope)
    before_scope = ledger.scoped_usd()
    print(f"GLOBAL_SPEND_SO_FAR (this scope): ${before_scope:.6f}")
    print(f"GLOBAL_REMAINING (this scope cap): ${args.total_cap_usd - before_scope:.6f}")
    print("=== END COST GATE -- proceeding ===\n")

    built = build_mem0(args, ledger)
    adapter = built["adapter"]

    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(str(Path(args.embedding_model_path).resolve()), device="cpu")

    ingest_records: list[dict[str, Any]] = []
    retrieval_by_qid: dict[str, dict[str, Any]] = {}
    ingest_stopped = None
    try:
        for qid, row in corpus.items():
            bank = f"seg-{qid}"
            adapter._bank = bank
            before = adapter.stored_count()
            adapter.reset()
            after = adapter.stored_count()
            if after:
                raise RuntimeError(f"{bank}: {after} memories survived reset")

            sessions, dates = row["haystack_sessions"], row["haystack_dates"]
            sessions_ingested = user_turns = sessions_skipped = 0
            for index, (session, date) in enumerate(zip(sessions, dates)):
                recs = as_records(session, date, index)
                if not recs:
                    sessions_skipped += 1
                    continue
                adapter.ingest(recs)
                sessions_ingested += 1
                user_turns += len(recs)

            answer = adapter.query(row["question"])
            context_texts = list(answer.system_metadata["context_texts"])
            evidence_times = list(answer.system_metadata["evidence_times"])
            stored_after = adapter.stored_count()

            mapping = session_map(row)
            foreign = (sum(1 for t in evidence_times if mapping.get(canonical_time(t)) is None)
                      if mapping is not None else None)
            contamination_status = ("UNOBSERVABLE" if mapping is None
                                    else ("PASS" if foreign == 0 else "FAIL"))

            retrieval_by_qid[qid] = {"context_texts": context_texts, "evidence_times": evidence_times}
            ingest_records.append({
                "question_id": qid, "question_type": row["question_type"],
                "sessions_available": len(sessions), "sessions_ingested": sessions_ingested,
                "user_turns_ingested": user_turns, "sessions_skipped_no_user_turn": sessions_skipped,
                "store_before_reset": before, "store_after_reset": after, "store_after_ingest": stored_after,
                "contamination_status": contamination_status, "foreign_from_other_units": foreign,
                "cumulative_spend_usd": ledger.scoped_usd(),
            })
            print(f"{qid:12s} ingested {sessions_ingested}/{len(sessions)} sessions, "
                  f"{stored_after} stored, contamination={contamination_status}, "
                  f"cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached, ProxyCapReached) as stop:
        ingest_stopped = str(stop)
        print(f"INGEST STOPPED BY CAP: {ingest_stopped}")

    corpus = {qid: row for qid, row in corpus.items() if qid in retrieval_by_qid}
    if not corpus:
        raise RuntimeError("no unit completed ingest before the cap; nothing to run reader/judge on")
    if any(r["contamination_status"] == "FAIL" for r in ingest_records):
        bad = [r["question_id"] for r in ingest_records if r["contamination_status"] == "FAIL"]
        raise RuntimeError(f"contamination FAIL on {bad}; stopping before any reader/judge call")

    from openai import OpenAI
    from arena.decoding import FixedDecoding
    from arena.judge_pilot import prompt_for, label_of, JUDGE_PARAMS

    # Same brotli/httpx2 decoder fix carried forward from Mechanism J.
    sample_client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1",
                                        default_headers={"Accept-Encoding": "gzip, deflate"}),
                                  fixed={"temperature": args.sample_temperature},
                                  spend_cap_usd=None, shared_ledger=ledger)
    final_client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1",
                                       default_headers={"Accept-Encoding": "gzip, deflate"}),
                                 fixed={"temperature": 0}, spend_cap_usd=None, shared_ledger=ledger)

    def sample_call(question: str, context: list[str]) -> str:
        msg = user_message(question, context)
        resp = sample_client.chat.completions.create(
            model=args.model,
            messages=[{"role": "system", "content": READER_PROMPT},
                      {"role": "user", "content": msg}],
            max_tokens=READER_PARAMS["max_tokens"])
        return (resp.choices[0].message.content or "").strip()

    def final_call(question: str, context: list[str]) -> str:
        msg = user_message(question, context)
        resp = final_client.chat.completions.create(
            model=args.model,
            messages=[{"role": "system", "content": READER_PROMPT},
                      {"role": "user", "content": msg}],
            max_tokens=READER_PARAMS["max_tokens"])
        return (resp.choices[0].message.content or "").strip()

    def judge_call(qtype: str, question: str, gold: str, response: str) -> dict:
        prompt = prompt_for(qtype, question, gold, response, abstention=False)

        def one_pass(name: str) -> dict:
            resp = final_client.chat.completions.create(
                model=args.model, messages=[{"role": "user", "content": prompt}],
                n=JUDGE_PARAMS["n"], max_tokens=JUDGE_PARAMS["max_tokens"])
            text = (resp.choices[0].message.content or "").strip()
            return {"pass": name, "raw": text, "label": label_of(text)}

        passes = [one_pass("A"), one_pass("B")]
        if passes[0]["label"] != passes[1]["label"]:
            passes.append(one_pass("C"))
        votes = [p["label"] for p in passes]
        final = sum(votes) > len(votes) / 2
        return {"passes": passes, "label": final,
               "stable": passes[0]["label"] == passes[1]["label"],
               "disputed": len(passes) == 3}

    results = []
    stopped = None
    try:
        for qid, row in corpus.items():
            compact_ctx = retrieval_by_qid[qid]["context_texts"]
            evidence_times = retrieval_by_qid[qid]["evidence_times"]

            samples = [sample_call(row["question"], compact_ctx) for _ in range(args.samples)]
            vectors = embedder.encode(samples, show_progress_bar=False).tolist()
            labels = greedy_cluster(vectors, threshold=args.cluster_threshold)
            entropy = semantic_entropy(labels)
            escalate = entropy > ENTROPY_THRESHOLD

            raw_text, raw_index = (raw_session(row, evidence_times[0]) if evidence_times else (None, None))
            if escalate and raw_text:
                gate_ctx = compact_ctx + [f"[RAW SOURCE PROVENANCE]\n{raw_text}"]
                gate_unobservable = False
            elif escalate and not raw_text:
                gate_ctx = compact_ctx
                gate_unobservable = True
            else:
                gate_ctx = compact_ctx
                gate_unobservable = False

            base_answer = final_call(row["question"], compact_ctx)
            gate_answer = final_call(row["question"], gate_ctx)

            gold = str(row.get("answer", ""))
            qtype = row["question_type"]
            base_judged = judge_call(qtype, row["question"], gold, base_answer)
            gate_judged = judge_call(qtype, row["question"], gold, gate_answer)

            base_tokens = sum(len(t.split()) for t in compact_ctx)
            gate_tokens = sum(len(t.split()) for t in gate_ctx)

            results.append({
                "question_id": qid, "question_type": qtype, "question": row["question"],
                "gold": gold, "samples": samples, "cluster_labels": labels,
                "n_clusters": len(set(labels)), "semantic_entropy": entropy,
                "escalated": escalate, "escalation_unobservable": gate_unobservable,
                "compact_context": compact_ctx, "gate_context": gate_ctx,
                "base_context_tokens": base_tokens, "gate_context_tokens": gate_tokens,
                "base_answer": base_answer, "gate_answer": gate_answer,
                "base_judged": base_judged, "gate_judged": gate_judged,
                "base_correct": base_judged["label"], "gate_correct": gate_judged["label"],
            })
            print(f"{qid:12s} entropy={entropy:.3f}  escalated={escalate!s:5s}  "
                  f"gate_tokens={gate_tokens:4d} (base={base_tokens:3d})  "
                  f"BASE={'OK ' if base_judged['label'] else 'WRONG'}  "
                  f"GATE={'OK ' if gate_judged['label'] else 'WRONG'}  "
                  f"cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    n_escalated = sum(1 for r in results if r["escalated"])
    record = {
        "artifact": "arena-semantic-entropy-gate-v1",
        "selection": str(SELECTION.relative_to(ROOT)),
        "preregistration": "PM-20260825-e88248ff",
        "responds_to": ["rmc-2026-08-24-001", "arr-2026-08-24-001"],
        "entropy_threshold": ENTROPY_THRESHOLD, "samples_per_unit": args.samples,
        "sample_temperature": args.sample_temperature,
        "reader_prompt_sha256": prompt_hash(),
        "ingest": ingest_records, "ingest_stopped_by_cap": ingest_stopped,
        "n_units_preregistered": 6, "n_units": len(corpus), "n_escalated": n_escalated,
        "stopped_by_cap": stopped,
        "spend": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                  "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/6 units, {n_escalated} escalated, total spend "
          f"${total_spend:.6f} against cap ${args.total_cap_usd:.2f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
