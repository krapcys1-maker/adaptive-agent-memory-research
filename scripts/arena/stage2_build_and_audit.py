#!/usr/bin/env python3
"""Stage 2 fresh replication: contamination audit + wide-arm + +TIME arm builder.

No provider call in this file. Consumes the already-paid-for ingest output
(stage2-mem0.json + raw/arena-stage2-fresh-v1/mem0.json) and:

1. Verifies store_before_reset == store_after_reset == 0 for every unit
   (the reset postcondition) and computes foreign_from_other_units per unit
   the same way mem0_breadth_arms.py does for the original 10, using this
   selection's OWN session_map -- a timestamp that does not resolve to any
   session inside its own unit's haystack is foreign (residue from another
   unit). STOPS (raises) rather than continuing if either check fails.
2. Builds the single WIDE operating-point arm (whole deep_context_texts,
   verified <=3000-ish tokens is not enforced here -- Stage 2 uses the full
   deep slice up to --deep-limit items, same as E1's mem0_3000 construction
   pattern via truncate(), reused unmodified from mem0_breadth_arms.py).
3. Builds BASE (undecorated) and +TIME ("[YYYY-MM-DD] {fact}", date from the
   positionally-aligned deep_evidence_times, canonical_time()-normalised)
   contexts, identical mechanism to E1, single operating point only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.mem0_breadth_arms import truncate  # noqa: E402
from arena.retrieval_truth import canonical_time, gold_session_indices, session_map  # noqa: E402

ARENA = ROOT / "data/lab/arena"
STAGE2 = ARENA / "stage2-fresh-replication"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")
WIDE_BUDGET = 3000


def session_date(raw_timestamp: str) -> str:
    iso = canonical_time(raw_timestamp)
    if iso is None:
        raise SystemExit(f"could not parse a session timestamp deterministically: {raw_timestamp!r}")
    return iso[:10]


def gold_state(row: dict, times: list) -> dict:
    mapping = session_map(row)
    if mapping is None:
        return {"observable": False, "gold_in_context": "UNOBSERVABLE", "gold_rank": "UNOBSERVABLE"}
    gold = gold_session_indices(row)
    hits = [i for i, t in enumerate(times, start=1) if mapping.get(canonical_time(t)) in gold]
    return {"observable": True, "gold_in_context": bool(hits), "gold_rank": hits[0] if hits else None,
            "foreign_from_other_units": sum(1 for t in times if mapping.get(canonical_time(t)) is None)}


def contamination_status(gs: dict) -> str:
    """PASS / FAIL / UNOBSERVABLE -- never conflates "own dates ambiguous" with "contaminated".

    The bug this guards against, caught live on this session's first Stage 2
    run: a unit whose own haystack_dates are not unique makes session_map()
    return None, so gold_state() takes the UNOBSERVABLE branch and never adds
    a `foreign_from_other_units` key at all. Comparing that missing key
    against `== 0` reads False -- indistinguishable from a real contamination
    failure -- and stopped a clean run (0977f2af, 0bb5a684) that had nothing
    wrong with it.
    """
    if not gs.get("observable"):
        return "UNOBSERVABLE"
    return "PASS" if gs.get("foreign_from_other_units") == 0 else "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingest-record", default=str(STAGE2 / "stage2-mem0.json"))
    parser.add_argument("--raw", default=str(ARENA / "raw/arena-stage2-fresh-v1/mem0.json"))
    parser.add_argument("--selection", default=str(STAGE2 / "stage2-selection.json"))
    parser.add_argument("--out-audit", default=str(STAGE2 / "stage2-contamination-audit.json"))
    parser.add_argument("--out-arms", default=str(STAGE2 / "stage2-arms.json"))
    args = parser.parse_args()

    record = json.loads(Path(args.ingest_record).read_text(encoding="utf-8"))
    raw = {e["question_id"]: e for e in json.loads(Path(args.raw).read_text(encoding="utf-8"))}
    selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))
    sel_units = {u["question_id"]: u for u in selection["units"]}
    with CORPUS.open(encoding="utf-8") as fh:
        corpus = {r["question_id"]: r for r in json.load(fh) if r["question_id"] in sel_units}

    # -------------------------------------------------------------- audit
    audit_rows = []
    reset_failures, contamination_failures, unobservable = [], [], []
    for u in record["units"]:
        qid = u["question_id"]
        row = corpus[qid]
        entry = raw.get(qid) or {}
        deep_times = entry.get("deep_evidence_times") or []
        gs = gold_state(row, deep_times)
        ok_reset = u["store_before_reset"] == 0 and u["store_after_reset"] == 0
        contam_status = contamination_status(gs)
        if not ok_reset:
            reset_failures.append(qid)
        if contam_status == "FAIL":
            contamination_failures.append(qid)
        elif contam_status == "UNOBSERVABLE":
            unobservable.append(qid)
        audit_rows.append({
            "question_id": qid, "store_before_reset": u["store_before_reset"],
            "store_after_reset": u["store_after_reset"], "stored_items": u.get("stored_items"),
            "reset_postcondition_pass": ok_reset,
            "foreign_from_other_units": gs.get("foreign_from_other_units"),
            "contamination_status": contam_status,
            "gold_in_context_deep": gs.get("gold_in_context"), "gold_rank_deep": gs.get("gold_rank"),
        })

    audit = {"artifact": "arena-stage2-contamination-audit", "units": audit_rows,
             "all_reset_pass": not reset_failures, "all_contamination_pass": not contamination_failures,
             "reset_failures": reset_failures, "contamination_failures": contamination_failures,
             "unobservable_units": unobservable,
             "unobservable_reason": ("own haystack_dates are not unique, same condition documented "
                                     "throughout this project for 69fee5aa in the original 10-unit set "
                                     "-- not a contamination signal, just an unmappable own-session check")}
    Path(args.out_audit).write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("RESET:", "PASS" if audit["all_reset_pass"] else f"FAIL {reset_failures}")
    print("CONTAMINATION:", "PASS" if audit["all_contamination_pass"] else f"FAIL {contamination_failures}",
         f"(unobservable, not counted as failure: {unobservable})" if unobservable else "")
    if reset_failures or contamination_failures:
        raise SystemExit("Stage 2 contamination/reset check FAILED -- STOP, do not build arms or spend further.")

    # -------------------------------------------------------------- arms
    arms = []
    for qid, sel in sel_units.items():
        row = corpus[qid]
        entry = raw.get(qid) or {}
        deep_items = entry.get("deep_context_texts") or []
        deep_times = entry.get("deep_evidence_times") or []
        if len(deep_items) != len(deep_times):
            raise SystemExit(f"{qid}: evidence_times alignment ambiguous "
                             f"({len(deep_items)} items vs {len(deep_times)} times) -- STOP")
        wide_items = truncate(deep_items, WIDE_BUDGET)
        wide_times = deep_times[:len(wide_items)]
        dates = [session_date(t) for t in wide_times]
        base_ctx = list(wide_items)
        time_ctx = [f"[{d}] {fact}" for d, fact in zip(dates, wide_items)]
        gs = gold_state(row, wide_times)
        common = {"question_id": qid, "question_type": row["question_type"],
                  "predicted_regime": sel["predicted_regime"], "prediction": sel["prediction"],
                  "question": row["question"], "gold": str(row.get("answer", "")),
                  "operating_point": "wide", "gold_state": gs}
        arms.append({**common, "arm": "stage2_base", "context": base_ctx,
                    "context_tokens": sum(len(t.split()) for t in base_ctx)})
        arms.append({**common, "arm": "stage2_time", "context": time_ctx,
                    "context_tokens": sum(len(t.split()) for t in time_ctx)})

    out = {"artifact": "arena-stage2-fresh-replication-arms", "operating_point": "wide",
          "wide_budget": WIDE_BUDGET, "arms": arms}
    Path(args.out_arms).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(arms)} arm entries ({len(arms)//2} units x 2 arms)")
    for a in arms:
        if a["arm"] == "stage2_base":
            print(f"  {a['question_id']:12s} regime={a['predicted_regime']:22s} "
                 f"tok={a['context_tokens']:4d} gold_in_context={a['gold_state'].get('gold_in_context')} "
                 f"gold_rank={a['gold_state'].get('gold_rank')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
