#!/usr/bin/env python3
"""Continuation of MECHANISM_D_RETRIEVAL_CONFIDENCE_SIGNAL_V1 after the
provider proxy's own cap correctly stopped ingest mid-way through the 5th
unit (openai.APIStatusError 402, $0.3455 spent of the $0.35 cap -- see the
bug-discipline note in run_retrieval_confidence_v1.py: the ingest loop had
no cap-reached handling, so the crash discarded the record of which units
had already been cleanly, fully ingested, even though their on-disk stores
were untouched and real).

Does NOT re-ingest anything -- reopens the SAME persisted Qdrant store used
by the interrupted run and queries (free, no LLM call) the 4 banks that
completed fully and cleanly (118b2229, 0a995998, 09ba9854, 0db4c65d).
08e075c7 (knowledge-update) is dropped entirely, not resumed -- resuming a
partial ingest correctly is nontrivial (Mem0's own dedup/update logic on a
partially-populated bank is not a state this project's methodology has ever
relied on) and re-ingesting it from scratch would double-pay for nothing;
dropping it is the clean, honest, zero-waste choice. n=4 for this
exploratory test, not the preregistered n=5 -- disclosed, not hidden.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SELECTION = ROOT / "data/lab/arena/retrieval-confidence-signal-v1/selection.json"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")
COMPLETED_UNITS = ["118b2229", "0a995998", "09ba9854", "0db4c65d"]
DROPPED_UNIT = "08e075c7"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.05)
    parser.add_argument("--total-cap-usd", type=float, default=0.05)
    parser.add_argument("--cap-scope", default="mechd-v1-cont-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/retrieval-confidence-v1-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/retrieval-confidence-signal-v1/results.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    sel_units = {u["question_id"]: u for u in selection["units"]}
    with CORPUS.open(encoding="utf-8") as fh:
        corpus = {r["question_id"]: r for r in json.load(fh) if r["question_id"] in sel_units}
    corpus = {qid: corpus[qid] for qid in COMPLETED_UNITS}
    assert len(corpus) == 4

    from arena.spend_ledger import SpendLedger, TotalCapReached
    from arena.decoding import SpendCapReached
    from arena.run_pilot import build_mem0, load_key
    from arena.retrieval_truth import canonical_time, session_map
    from arena.retrieval_confidence_signal import retrieval_confidence_signal, MARGIN_THRESHOLD
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    print("=== COST GATE (continuation -- reader/judge only, no re-ingest) ===")
    print("RESEARCH_QUESTION: same as the original preregistration, n reduced 5->4 "
          "after the provider cap stopped mid-ingest on the 5th unit (disclosed, not hidden)")
    print("WHY_THIS_CALL_IS_NEEDED: 4 units are already cleanly, fully ingested on disk "
          "(real, paid-for work) -- retrieval is free (no LLM call); only reader+judge remain")
    print("CHEAPEST_ALTERNATIVE: none -- re-ingesting anything would double-pay for already-done work")
    print("PROJECTED_CALLS: 0 ingest (reusing persisted store) + 8 reader (2 arms x 4 units) + ~16-24 judge")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f} (small, reader/judge-only continuation)")
    if args.project_only:
        return 0

    run_id = f"{args.cap_scope}run"
    assert run_id.startswith(args.cap_scope)
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=run_id,
                         cap_scope=args.cap_scope)
    before_scope = ledger.scoped_usd()
    print(f"GLOBAL_SPEND_SO_FAR (this new scope): ${before_scope:.6f}")
    print(f"GLOBAL_REMAINING (this scope cap): ${args.total_cap_usd - before_scope:.6f}")
    print("=== END COST GATE -- proceeding ===\n")

    built = build_mem0(args, ledger)
    adapter = built["adapter"]

    retrieval_by_qid = {}
    ingest_records = []
    for qid, row in corpus.items():
        bank = f"mechd-{qid}"
        adapter._bank = bank
        stored = adapter.stored_count()
        assert stored > 0, f"{bank}: expected an already-ingested store, found {stored} items"

        answer = adapter.query(row["question"])
        context_texts = list(answer.system_metadata["context_texts"])
        evidence_times = list(answer.system_metadata["evidence_times"])
        scores = list(answer.system_metadata.get("scores") or [])

        mapping = session_map(row)
        foreign = (sum(1 for t in evidence_times if mapping.get(canonical_time(t)) is None)
                  if mapping is not None else None)
        contamination_status = ("UNOBSERVABLE" if mapping is None
                                else ("PASS" if foreign == 0 else "FAIL"))
        retrieval_by_qid[qid] = {"context_texts": context_texts, "scores": scores}
        ingest_records.append({
            "question_id": qid, "question_type": row["question_type"],
            "store_after_ingest_reused_from_prior_run": stored,
            "contamination_status": contamination_status, "foreign_from_other_units": foreign,
        })
        print(f"{qid:12s} reused store ({stored} items), contamination={contamination_status}")

    if any(r["contamination_status"] == "FAIL" for r in ingest_records):
        bad = [r["question_id"] for r in ingest_records if r["contamination_status"] == "FAIL"]
        raise RuntimeError(f"contamination FAIL on {bad}; stopping before any reader/judge call")

    from openai import OpenAI
    from arena.judge_pilot import prompt_for, label_of, JUDGE_PARAMS
    from arena.decoding import FixedDecoding

    client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1"),
                           fixed={"temperature": 0}, spend_cap_usd=None, shared_ledger=ledger)

    def reader_call(question, context):
        msg = user_message(question, context)
        resp = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "system", "content": READER_PROMPT},
                      {"role": "user", "content": msg}],
            max_tokens=READER_PARAMS["max_tokens"])
        return (resp.choices[0].message.content or "").strip()

    def judge_call(qtype, question, gold, response):
        prompt = prompt_for(qtype, question, gold, response, abstention=False)

        def one_pass(name):
            resp = client.chat.completions.create(
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
            base_ctx = retrieval_by_qid[qid]["context_texts"]
            scores = retrieval_by_qid[qid]["scores"]
            plus_d_ctx, trace = retrieval_confidence_signal(base_ctx, scores)

            base_answer = reader_call(row["question"], base_ctx)
            plus_d_answer = reader_call(row["question"], plus_d_ctx)

            gold = str(row.get("answer", ""))
            qtype = row["question_type"]
            base_judged = judge_call(qtype, row["question"], gold, base_answer)
            plus_d_judged = judge_call(qtype, row["question"], gold, plus_d_answer)

            results.append({
                "question_id": qid, "question_type": qtype, "question": row["question"],
                "gold": gold, "scores": scores, "mechanism_trace": trace,
                "base_context": base_ctx, "plus_d_context": plus_d_ctx,
                "base_answer": base_answer, "plus_d_answer": plus_d_answer,
                "base_judged": base_judged, "plus_d_judged": plus_d_judged,
                "base_correct": base_judged["label"], "plus_d_correct": plus_d_judged["label"],
            })
            print(f"{qid:12s} margin={trace.get('margin')}  flagged={trace['flagged']}  "
                  f"BASE={'OK ' if base_judged['label'] else 'WRONG'}  "
                  f"+D={'OK ' if plus_d_judged['label'] else 'WRONG'}  "
                  f"cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    record = {
        "artifact": "arena-retrieval-confidence-signal-v1",
        "selection": str(SELECTION.relative_to(ROOT)),
        "margin_threshold": MARGIN_THRESHOLD,
        "reader_prompt_sha256": prompt_hash(),
        "ingest": ingest_records,
        "dropped_unit": DROPPED_UNIT,
        "dropped_unit_reason": ("provider cap stopped mid-ingest on this unit in the original "
                                "run; not resumed to avoid double-paying or relying on an "
                                "untested partial-store state; see run_retrieval_confidence_v1.py's "
                                "bug-discipline note"),
        "n_units_preregistered": 5, "n_units": len(corpus), "stopped_by_cap": stopped,
        "spend_this_continuation": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                                    "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
        "spend_original_ingest_run": {"cap_scope": "mechd-v1-", "total_usd": 0.345535,
                                      "cap_usd": 0.35, "note": "4 units fully ingested before the cap stopped"},
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/4 units, continuation spend ${total_spend:.6f} "
          f"against cap ${args.total_cap_usd:.2f} "
          f"(plus $0.345535 already spent on ingest in the original, interrupted run)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
