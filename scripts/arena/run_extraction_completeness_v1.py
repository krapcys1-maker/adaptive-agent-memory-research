#!/usr/bin/env python3
"""MECHANISM_J_EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1 -- exploratory test.

Per data/lab/arena/extraction-completeness-verification-v1/selection.json (8
fresh, gold-blind units). Unlike every prior mechanism (D-I), this changes
WHAT gets extracted and stored, not how already-stored content is rendered
or queried -- so BASE and +J require SEPARATE ingests into separate banks
per unit (mechj-{qid}-base, mechj-{qid}-plusj), the latter ingested with
metadata["completeness_check_enabled"]=True on every message.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SELECTION = ROOT / "data/lab/arena/extraction-completeness-verification-v1/selection.json"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")


def _results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [i for i in (payload.get("results") or []) if isinstance(i, dict)]
    if isinstance(payload, list):
        return [i for i in payload if isinstance(i, dict)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=1.20)
    parser.add_argument("--total-cap-usd", type=float, default=1.20)
    parser.add_argument("--cap-scope", default="mechj-v1-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/extraction-completeness-v1-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/extraction-completeness-verification-v1/results.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    sel_units = {u["question_id"]: u for u in selection["units"]}
    with CORPUS.open(encoding="utf-8") as fh:
        corpus = {r["question_id"]: r for r in json.load(fh) if r["question_id"] in sel_units}
    assert len(corpus) == 8, f"selection changed shape: {len(corpus)} units found"

    from arena.spend_ledger import SpendLedger, TotalCapReached
    from arena.decoding import SpendCapReached
    from arena.run_pilot import build_mem0, load_key
    from arena.run_arena_pilot import as_records
    from arena.retrieval_truth import canonical_time, session_map
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash
    from openai import APIStatusError as ProxyCapReached

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    total_sessions = sum(len(r.get("haystack_sessions") or []) for r in corpus.values())
    print("=== COST GATE (before first paid call) ===")
    print("RESEARCH_QUESTION: does EXTRACTION_COMPLETENESS_VERIFICATION_PASS (+J, one "
          "extra write-time LLM call splitting bundled enumerations and recovering "
          "omitted facts) repair Mem0 compact failures on 8 fresh, never-used units, "
          "targeting write-time extraction loss -- the priority-1 absence subtype "
          "nothing tested this campaign (D-I) has addressed?")
    print("WHY_THIS_CALL_IS_NEEDED: discovery-rebuild + archaeology (STRONG_CANDIDATE "
          "verdict) + calibration (4/4 list cases split, 0 fabrication, "
          "PM-20260824-9d020373) already done at near-$0 cost")
    print("EXPECTED_INFORMATION_GAIN: MECHANISM_J_EXPLORATORY_SUPPORTED vs FAIL")
    print("CHEAPEST_ALTERNATIVE: none -- calibration already confirmed the mechanism "
          "is not inert at near-$0; this is the first test at real corpus scale")
    print(f"PROJECTED_CALLS: ~{total_sessions} BASE-ingest + ~{total_sessions} +J-ingest "
          f"(1 extra completeness call/session) + up to 16 reader (2 arms x 8 units) "
          f"+ ~32-48 judge")
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
    memory = adapter._memory

    def ingest_bank(bank: str, row: dict, completeness_check_enabled: bool) -> dict:
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
            messages = [{"role": "user", "content": r["text"]} for r in recs]
            timestamp = recs[0].get("timestamp", "") if recs else ""
            metadata = {"timestamp": timestamp} if timestamp else {}
            if completeness_check_enabled:
                metadata["completeness_check_enabled"] = True
            memory.add(messages=messages, user_id=bank, metadata=metadata or None)
            sessions_ingested += 1
            user_turns += len(recs)

        stored_after = adapter.stored_count()
        return {"sessions_available": len(sessions), "sessions_ingested": sessions_ingested,
               "user_turns_ingested": user_turns, "sessions_skipped_no_user_turn": sessions_skipped,
               "store_before_reset": before, "store_after_reset": after,
               "store_after_ingest": stored_after}

    ingest_records: list[dict[str, Any]] = []
    retrieval_by_qid: dict[str, dict[str, Any]] = {}
    ingest_stopped = None
    try:
        for qid, row in corpus.items():
            base_bank = f"mechj-{qid}-base"
            plusj_bank = f"mechj-{qid}-plusj"

            base_stats = ingest_bank(base_bank, row, completeness_check_enabled=False)
            plusj_stats = ingest_bank(plusj_bank, row, completeness_check_enabled=True)

            top10_base = _results(memory.search(query=row["question"], user_id=base_bank, limit=10))
            top10_plusj = _results(memory.search(query=row["question"], user_id=plusj_bank, limit=10))

            def audit(top10, mapping):
                times = [str((r.get("metadata") or {}).get("timestamp", "") or "") for r in top10]
                if mapping is None:
                    return "UNOBSERVABLE", None
                foreign = sum(1 for t in times if mapping.get(canonical_time(t)) is None)
                return ("PASS" if foreign == 0 else "FAIL"), foreign

            mapping = session_map(row)
            base_status, base_foreign = audit(top10_base, mapping)
            plusj_status, plusj_foreign = audit(top10_plusj, mapping)

            retrieval_by_qid[qid] = {"top10_base": top10_base, "top10_plusj": top10_plusj}
            ingest_records.append({
                "question_id": qid, "question_type": row["question_type"],
                "base": {**base_stats, "contamination_status": base_status, "foreign": base_foreign},
                "plusj": {**plusj_stats, "contamination_status": plusj_status, "foreign": plusj_foreign},
                "cumulative_spend_usd": ledger.scoped_usd(),
            })
            print(f"{qid:12s} base={base_stats['store_after_ingest']:3d} stored "
                  f"({base_status})  plusj={plusj_stats['store_after_ingest']:3d} stored "
                  f"({plusj_status})  cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached, ProxyCapReached) as stop:
        ingest_stopped = str(stop)
        print(f"INGEST STOPPED BY CAP: {ingest_stopped}")

    corpus = {qid: row for qid, row in corpus.items() if qid in retrieval_by_qid}
    if not corpus:
        raise RuntimeError("no unit completed ingest before the cap; nothing to run reader/judge on")
    bad = [r["question_id"] for r in ingest_records
          if r["base"]["contamination_status"] == "FAIL" or r["plusj"]["contamination_status"] == "FAIL"]
    if bad:
        raise RuntimeError(f"contamination FAIL on {bad}; stopping before any reader/judge call")

    from openai import OpenAI
    from arena.decoding import FixedDecoding
    from arena.judge_pilot import prompt_for, label_of, JUDGE_PARAMS

    client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1"),
                           fixed={"temperature": 0}, spend_cap_usd=None, shared_ledger=ledger)

    def reader_call(question: str, context: list[str] | None) -> str:
        msg = user_message(question, context)
        resp = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "system", "content": READER_PROMPT},
                      {"role": "user", "content": msg}],
            max_tokens=READER_PARAMS["max_tokens"])
        return (resp.choices[0].message.content or "").strip()

    def judge_call(qtype: str, question: str, gold: str, response: str) -> dict:
        prompt = prompt_for(qtype, question, gold, response, abstention=False)

        def one_pass(name: str) -> dict:
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
            base_ctx = [str(r.get("memory", "")).strip() for r in retrieval_by_qid[qid]["top10_base"]
                       if str(r.get("memory", "")).strip()]
            plusj_ctx = [str(r.get("memory", "")).strip() for r in retrieval_by_qid[qid]["top10_plusj"]
                        if str(r.get("memory", "")).strip()]

            base_answer = reader_call(row["question"], base_ctx)
            plusj_answer = reader_call(row["question"], plusj_ctx)

            gold = str(row.get("answer", ""))
            qtype = row["question_type"]
            base_judged = judge_call(qtype, row["question"], gold, base_answer)
            plusj_judged = judge_call(qtype, row["question"], gold, plusj_answer)

            results.append({
                "question_id": qid, "question_type": qtype, "question": row["question"],
                "gold": gold,
                "base_context": base_ctx, "plusj_context": plusj_ctx,
                "base_context_n": len(base_ctx), "plusj_context_n": len(plusj_ctx),
                "base_answer": base_answer, "plusj_answer": plusj_answer,
                "base_judged": base_judged, "plusj_judged": plusj_judged,
                "base_correct": base_judged["label"], "plusj_correct": plusj_judged["label"],
            })
            print(f"{qid:12s} base_n={len(base_ctx):2d} plusj_n={len(plusj_ctx):2d}  "
                  f"BASE={'OK ' if base_judged['label'] else 'WRONG'}  "
                  f"+J={'OK ' if plusj_judged['label'] else 'WRONG'}  "
                  f"cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    record = {
        "artifact": "arena-extraction-completeness-verification-v1",
        "selection": str(SELECTION.relative_to(ROOT)),
        "reader_prompt_sha256": prompt_hash(),
        "ingest": ingest_records, "ingest_stopped_by_cap": ingest_stopped,
        "n_units_preregistered": 8, "n_units": len(corpus), "stopped_by_cap": stopped,
        "spend": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                  "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/8 units, total spend ${total_spend:.6f} "
          f"against cap ${args.total_cap_usd:.2f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
