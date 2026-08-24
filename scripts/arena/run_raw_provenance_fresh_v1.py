#!/usr/bin/env python3
"""RAW_PROVENANCE_FRESH_REPLICATION_V1 -- Mechanism C for the autonomous
research campaign. Fresh replication of RAW_PROVENANCE_CONDITIONAL_SIGNAL
(E3, docs/research/CLEAN_RAW_PROVENANCE_RETEST_V2.md) on 8 never-used units
(data/lab/arena/raw-provenance-fresh-replication-v1/selection.json).

Per unit: clean isolated Mem0 ingest of every haystack session (same pattern
as run_pilot.py/Stage 2 -- one ingest() call per session, as_records() drops
non-user turns, all turns in a session share that session's date), reset
postcondition + contamination audit, then build three arms with the same
deterministic, already-audited logic as arena.mechanism_ablation.build_arms():

    mem0_compact          native Mem0 retrieval, unmodified
    mem0_compact_plus_raw compact + the raw source session behind the top-1 hit
    mem0_raw_only         the raw source session alone, no compact context

Reader: fixed_reader.py's frozen prompt/params. Judge: judge_pilot.py's
frozen per-category templates, matched to each unit's REAL LongMemEval
question_type (no new criterion).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

SELECTION = ROOT / "data/lab/arena/raw-provenance-fresh-replication-v1/selection.json"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.75)
    parser.add_argument("--total-cap-usd", type=float, default=0.75)
    parser.add_argument("--cap-scope", default="rawprov-fresh-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/raw-provenance-fresh-v1-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/raw-provenance-fresh-replication-v1/results.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    sel_units = {u["question_id"]: u for u in selection["units"]}
    with CORPUS.open(encoding="utf-8") as fh:
        corpus = {r["question_id"]: r for r in json.load(fh) if r["question_id"] in sel_units}
    assert len(corpus) == 8, f"selection changed shape: {len(corpus)} units found"

    from arena.decoding import PRICE_PER_MTOK
    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import build_mem0, load_key
    from arena.run_arena_pilot import as_records
    from arena.retrieval_truth import canonical_time, session_map
    from arena.mechanism_ablation import raw_session, gold_state, truncate
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    n_units = len(corpus)
    total_sessions = sum(len(r.get("haystack_sessions") or []) for r in corpus.values())
    print("=== COST GATE (before first paid call) ===")
    print("RESEARCH_QUESTION: does RAW_PROVENANCE (compact+raw) repair Mem0 compact "
          "failures on 8 fresh, never-used LongMemEval-S units, replicating E3's "
          "CONDITIONAL 1/9 signal (0 regressions)?")
    print("WHY_THIS_CALL_IS_NEEDED: E3's signal is too thin (n=9, 1 repair) to trust "
          "without independent replication; no $0 analysis can substitute for real "
          "reader/judge behavior on fresh data")
    print("EXPECTED_INFORMATION_GAIN: RAW_PROVENANCE_REPLICATED_SUPPORTED vs "
          "RAW_PROVENANCE_FAILED_REPLICATION")
    print("CHEAPEST_ALTERNATIVE: none -- mechanism design/calibration already exist "
          "at $0 marginal cost (reusing E3's audited code)")
    print(f"PROJECTED_CALLS: ~{total_sessions} ingest (8 units, {total_sessions} total "
          f"haystack sessions) + up to {n_units * 3} reader (3 arms x 8 units, fewer if "
          f"raw provenance unresolvable for a unit) + ~{n_units * 3 * 2}-"
          f"{n_units * 3 * 3} judge")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f} (per-mechanism replication preference)")
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

    ingest_records: list[dict[str, Any]] = []
    mem0_by_qid: dict[str, dict[str, Any]] = {}
    for qid, row in corpus.items():
        bank = f"rawprov-{qid}"
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

        mem0_by_qid[qid] = {
            "question_id": qid, "context_texts": context_texts, "evidence_times": evidence_times,
        }
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

    if any(r["contamination_status"] == "FAIL" for r in ingest_records):
        bad = [r["question_id"] for r in ingest_records if r["contamination_status"] == "FAIL"]
        raise RuntimeError(f"contamination FAIL on {bad}; stopping before any reader/judge call")

    # -- build the three arms, exactly mechanism_ablation.build_arms()'s logic --
    arms_by_qid: dict[str, dict[str, Any]] = {}
    for qid, row in corpus.items():
        compact = mem0_by_qid[qid]["context_texts"]
        times = mem0_by_qid[qid]["evidence_times"]
        text, index = raw_session(row, times[0]) if times else (None, None)
        entry = {"question": row["question"], "gold": str(row.get("answer", "")),
                 "question_type": row["question_type"],
                 "mem0_compact": {"context": compact, "gold_state": gold_state(row, times)}}
        if text:
            entry["mem0_compact_plus_raw"] = {
                "context": compact + [f"[RAW SOURCE PROVENANCE]\n{text}"],
                "gold_state": gold_state(row, times), "provenance_session_index": index,
                "provenance_tokens": len(text.split())}
            entry["mem0_raw_only"] = {
                "context": [f"[RAW SOURCE PROVENANCE]\n{text}"],
                "gold_state": gold_state(row, times[:1]), "provenance_session_index": index}
        else:
            entry["mem0_compact_plus_raw"] = {"context": None, "unobservable":
                "top-1 provenance could not be resolved mechanically (ambiguous haystack dates)"}
            entry["mem0_raw_only"] = {"context": None, "unobservable":
                "top-1 provenance could not be resolved mechanically"}
        arms_by_qid[qid] = entry

    from openai import OpenAI
    from arena.decoding import FixedDecoding, SpendCapReached
    from arena.spend_ledger import TotalCapReached
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
        for qid, entry in arms_by_qid.items():
            row_result = {"question_id": qid, "question_type": entry["question_type"],
                         "question": entry["question"], "gold": entry["gold"], "arms": {}}
            for arm_name in ("mem0_compact", "mem0_compact_plus_raw", "mem0_raw_only"):
                arm = entry[arm_name]
                if arm.get("context") is None:
                    row_result["arms"][arm_name] = {"unobservable": arm.get("unobservable")}
                    continue
                ans = reader_call(entry["question"], arm["context"])
                judged = judge_call(entry["question_type"], entry["question"], entry["gold"], ans)
                row_result["arms"][arm_name] = {
                    "answer": ans, "judged": judged, "correct": judged["label"],
                    "context_tokens": sum(len(t.split()) for t in arm["context"]),
                    "gold_state": arm.get("gold_state"),
                }
            results.append(row_result)
            c = row_result["arms"].get("mem0_compact", {})
            p = row_result["arms"].get("mem0_compact_plus_raw", {})
            r = row_result["arms"].get("mem0_raw_only", {})
            print(f"{qid:12s} compact={'OK ' if c.get('correct') else 'WRONG'}  "
                  f"+raw={'OK ' if p.get('correct') else 'WRONG' if 'correct' in p else 'N/A'}  "
                  f"raw_only={'OK ' if r.get('correct') else 'WRONG' if 'correct' in r else 'N/A'}  "
                  f"cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    record = {
        "artifact": "arena-raw-provenance-fresh-replication-v1",
        "selection": str(SELECTION.relative_to(ROOT)),
        "reader_prompt_sha256": prompt_hash(),
        "ingest": ingest_records,
        "n_units": n_units, "stopped_by_cap": stopped,
        "spend": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                  "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/{n_units} units, total spend ${total_spend:.6f} "
          f"against cap ${args.total_cap_usd:.2f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
