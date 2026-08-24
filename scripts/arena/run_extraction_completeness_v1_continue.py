#!/usr/bin/env python3
"""Continuation of MECHANISM_J_EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1
after the arena's own cost cap correctly stopped ingest mid-way through the
6th of 8 units ($1.196073 spent of the $1.20 cap -- both BASE and +J banks
completed cleanly for 6 units before the 7th unit's ingest was refused).

Does NOT re-ingest anything -- reopens the SAME persisted Qdrant store used
by the interrupted run and queries (free, no LLM call) both banks for the 6
units that completed fully and cleanly on both arms (21436231, 09d032c9,
2311e44b, 21d02d0d, 4dfccbf8, 184da446). 18bc8abd and 1b9b7252 never started
ingest and are dropped entirely, not resumed -- matching this project's own
established precedent (run_retrieval_confidence_v1_continue.py) for exactly
this situation: re-ingesting from scratch would double-pay, and resuming a
partial dual-bank ingest correctly is not a state this project's methodology
has ever relied on. n=6 for this exploratory test, not the preregistered
n=8 -- disclosed, not hidden.
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
COMPLETED_UNITS = ["21436231", "09d032c9", "2311e44b", "21d02d0d", "4dfccbf8", "184da446"]
DROPPED_UNITS = ["18bc8abd", "1b9b7252"]


def _results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [i for i in (payload.get("results") or []) if isinstance(i, dict)]
    if isinstance(payload, list):
        return [i for i in payload if isinstance(i, dict)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.06)
    parser.add_argument("--total-cap-usd", type=float, default=0.06)
    parser.add_argument("--cap-scope", default="mechj-v1-cont-")
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
    corpus = {qid: corpus[qid] for qid in COMPLETED_UNITS}
    assert len(corpus) == 6

    from arena.spend_ledger import SpendLedger, TotalCapReached
    from arena.decoding import SpendCapReached
    from arena.run_pilot import build_mem0, load_key
    from arena.retrieval_truth import canonical_time, session_map
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    print("=== COST GATE (continuation -- reader/judge only, no re-ingest) ===")
    print("RESEARCH_QUESTION: same as the original preregistration (PM-20260824-195a1656), "
          "n reduced 8->6 after the arena cost cap stopped mid-ingest on the 7th unit "
          "(disclosed, not hidden)")
    print("WHY_THIS_CALL_IS_NEEDED: 6 units are already cleanly, fully ingested on both "
          "BASE and +J banks (real, paid-for work, $1.196073 already spent) -- retrieval "
          "is free (no LLM call); only reader+judge remain")
    print("CHEAPEST_ALTERNATIVE: none -- re-ingesting anything would double-pay for already-done work")
    print("PROJECTED_CALLS: 0 ingest (reusing persisted stores) + 12 reader (2 arms x 6 units) "
          "+ ~24-36 judge")
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
    memory = adapter._memory

    retrieval_by_qid: dict[str, dict[str, Any]] = {}
    ingest_records = []
    for qid, row in corpus.items():
        base_bank = f"mechj-{qid}-base"
        plusj_bank = f"mechj-{qid}-plusj"
        adapter._bank = base_bank
        base_stored = adapter.stored_count()
        adapter._bank = plusj_bank
        plusj_stored = adapter.stored_count()
        assert base_stored > 0 and plusj_stored > 0, \
            f"{qid}: expected both banks already ingested, found base={base_stored} plusj={plusj_stored}"

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
            "base_store_reused_from_prior_run": base_stored,
            "plusj_store_reused_from_prior_run": plusj_stored,
            "base_contamination_status": base_status, "base_foreign": base_foreign,
            "plusj_contamination_status": plusj_status, "plusj_foreign": plusj_foreign,
        })
        print(f"{qid:12s} reused base={base_stored} plusj={plusj_stored} stored, "
              f"contamination base={base_status} plusj={plusj_status}")

    bad = [r["question_id"] for r in ingest_records
          if r["base_contamination_status"] == "FAIL" or r["plusj_contamination_status"] == "FAIL"]
    if bad:
        raise RuntimeError(f"contamination FAIL on {bad}; stopping before any reader/judge call")

    from openai import OpenAI
    from arena.decoding import FixedDecoding
    from arena.judge_pilot import prompt_for, label_of, JUDGE_PARAMS

    # Bug found live in this run (2/2 identical failures, not retried a 3rd time
    # per circuit-breaker discipline): a stray system-wide brotli.py shadows the
    # mem0 venv's own brotli decoder and has an incompatible Decompressor.process()
    # signature, crashing httpx2's response decoding whenever DeepSeek's server
    # happens to brotli-encode a response. Client-side, $0 fix: refuse brotli in
    # the Accept-Encoding request header so the server never sends it.
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1",
                                  default_headers={"Accept-Encoding": "gzip, deflate"}),
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
        "ingest": ingest_records,
        "dropped_units": DROPPED_UNITS,
        "dropped_units_reason": ("the arena cost cap stopped mid-ingest before these 2 units' "
                                 "banks were created in the original run; not resumed, to avoid "
                                 "double-paying or relying on an untested partial-store state; "
                                 "see run_extraction_completeness_v1.py's cost-cap behavior"),
        "n_units_preregistered": 8, "n_units": len(corpus), "stopped_by_cap": stopped,
        "spend_this_continuation": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                                    "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
        "spend_original_ingest_run": {"cap_scope": "mechj-v1-", "total_usd": 1.196073,
                                      "cap_usd": 1.20, "note": "6 units fully ingested on both "
                                      "BASE and +J banks before the cap stopped"},
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/6 units, continuation spend ${total_spend:.6f} "
          f"against cap ${args.total_cap_usd:.2f} "
          f"(plus $1.196073 already spent on ingest in the original, interrupted run)")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
