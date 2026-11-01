#!/usr/bin/env python3
"""E2 CALIBRATION-ONLY: does Mem0 1.0.6 extraction, given a correct per-session
reference_date PLUS an explicit instruction to resolve relative temporal
expressions against it, represent EVENT_TIME as an absolute date -- vs.
CONTROL (same reference_date, no instruction), which prior calibration
already showed is INERT (data/lab/arena/base-plus-x-v1/
calibration-per-session-reference-date.json)?

Capability calibration of the EXTRACTION step only. This calls
get_fact_retrieval_messages() + a single llm.generate_response() directly --
the exact same call shape Mem0's own `_add_to_vector_store` uses for its
fact-retrieval phase (main.py:449-454) -- and stops there. It deliberately
does NOT go through memory.add()'s full pipeline: no update-memory-decision
call, no dedup, no vector-store write, no retrieval. That keeps this to
exactly one model call per (case, arm) = 10 calls total for 5 cases, matches
the pre-registered call discipline, and stays inside "extraction only" scope
(PM-20260824-e9f15438).

Preregistration: PM-20260824-e9f15438 (E2_CALIBRATION_PREREGISTRATION).
Treatment: EVENT_TIME_RESOLUTION_AT_EXTRACTION (patch: data/lab/arena/
event-time-resolution-calibration-v1/vendor-patch/
EVENT_TIME_RESOLUTION_AT_EXTRACTION.patch).

Hard cap $0.03, enforced by the same SpendLedger + provider-proxy mechanism
used everywhere else in this arena, cap_scope="e2-calib-" (must be a literal
prefix of run_id).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

CASES = [
    {
        "case_id": "CASE1_TODAY",
        "reference_date": "2022-11-17",
        "input_text": "I went grocery shopping today and bought a lot of fresh vegetables.",
        "expected_event_time": "2022-11-17",
        "expected_precision": "day",
    },
    {
        "case_id": "CASE2_YESTERDAY",
        "reference_date": "2023-01-28",
        "input_text": "I had a dentist appointment yesterday and got my teeth cleaned.",
        "expected_event_time": "2023-01-27",
        "expected_precision": "day",
    },
    {
        "case_id": "CASE3_NEXT_YEAR",
        "reference_date": "2022-06-15",
        "input_text": "I'm planning to run my first marathon next year.",
        "expected_event_time": "2023",
        "expected_precision": "year",
    },
    {
        "case_id": "CASE4_LAST_MONTH",
        "reference_date": "2023-03-10",
        "input_text": "I adopted a rescue dog last month and named her Luna.",
        "expected_event_time": "2023-02",
        "expected_precision": "month",
    },
    {
        "case_id": "CASE5_NO_DATE",
        "reference_date": "2023-02-10",
        "input_text": "My favorite color is teal and I prefer tea over coffee.",
        "expected_event_time": None,
        "expected_precision": "none -- negative control, no temporal expression present",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.03)
    parser.add_argument("--total-cap-usd", type=float, default=0.03)
    parser.add_argument("--cap-scope", default="e2-calib-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/e2-calibration-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/event-time-resolution-calibration-v1/calibration.json"))
    args = parser.parse_args()

    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import build_mem0

    assert args.cap_scope and (args.cap_scope + "run").startswith(args.cap_scope), "sanity"
    run_id = f"{args.cap_scope}run"
    assert run_id.startswith(args.cap_scope), "cap_scope must be a literal prefix of run_id"
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=run_id, cap_scope=args.cap_scope)

    built = build_mem0(args, ledger)
    memory = built["adapter"]._memory

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))
    from mem0.memory.utils import (
        get_fact_retrieval_messages, parse_messages, ensure_json_instruction,
        remove_code_blocks, extract_json,
    )

    def extract(input_text: str, reference_date: str, resolve_relative_time: bool):
        messages = [{"role": "user", "content": input_text}]
        parsed = parse_messages(messages)
        system_prompt, user_prompt = get_fact_retrieval_messages(
            parsed, is_agent_memory=False, reference_date=reference_date,
            resolve_relative_time=resolve_relative_time)
        system_prompt, user_prompt = ensure_json_instruction(system_prompt, user_prompt)
        before = ledger.scoped_usd()
        raw = memory.llm.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        after = ledger.scoped_usd()
        cleaned = remove_code_blocks(raw)
        try:
            facts = json.loads(cleaned)["facts"] if cleaned.strip() else []
        except json.JSONDecodeError:
            facts = json.loads(extract_json(cleaned))["facts"]
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_response": raw,
            "facts": facts,
            "cost_usd": round(after - before, 6),
        }

    # ---- cost gate: projected vs actual, checked live via ledger scoped_usd() ----
    before_all = ledger.scoped_usd()

    results = []
    for case in CASES:
        control = extract(case["input_text"], case["reference_date"], resolve_relative_time=False)
        treatment = extract(case["input_text"], case["reference_date"], resolve_relative_time=True)
        results.append({
            "case_id": case["case_id"],
            "reference_date": case["reference_date"],
            "input_text": case["input_text"],
            "expected_event_time": case["expected_event_time"],
            "expected_precision": case["expected_precision"],
            "control_output": control,
            "treatment_output": treatment,
        })
        print(f"{case['case_id']}: control ${control['cost_usd']:.6f}, "
              f"treatment ${treatment['cost_usd']:.6f}, "
              f"cumulative ${ledger.scoped_usd():.6f} / cap ${args.total_cap_usd:.2f}")

    after_all = ledger.scoped_usd()
    total_spend = round(after_all - before_all, 6)

    record = {
        "artifact": "arena-event-time-resolution-calibration-v1",
        "parent_commit": "d82afa42c1997b7a3be79e0a02a205e80eeb81bc",
        "preregistration": "PM-20260824-e9f15438",
        "treatment_definition": (
            "EVENT_TIME_RESOLUTION_AT_EXTRACTION: PER_SESSION_REFERENCE_DATE_AT_EXTRACTION's "
            "correct reference_date PLUS one explicit instruction bullet, inserted immediately "
            "after the 'Today's date is ...' line, telling the model to resolve relative time "
            "expressions (today/yesterday/tomorrow/last month/next year) against that date when "
            "unambiguous, and never fabricate one otherwise. CONTROL = same reference_date, "
            "resolve_relative_time=False (byte-identical to the already-calibrated-INERT prior "
            "treatment). TREATMENT = resolve_relative_time=True."
        ),
        "prompt_diff": ("data/lab/arena/event-time-resolution-calibration-v1/vendor-patch/"
                        "EVENT_TIME_RESOLUTION_AT_EXTRACTION.patch"),
        "call_shape": ("get_fact_retrieval_messages() + ensure_json_instruction() + a single "
                       "llm.generate_response(response_format=json_object) -- the exact "
                       "fact-retrieval call shape memory.add() uses internally "
                       "(main.py:449-454) -- with no update-memory-decision call, no dedup, "
                       "no vector-store write, no retrieval. 1 call per (case, arm) = 10 total."),
        "cases": results,
        "usage": {
            "total_calls": len(CASES) * 2,
            "ledger_entries_this_scope": [
                e for e in ledger.entries() if str(e.get("run_id", "")).startswith(args.cap_scope)
            ],
        },
        "spend": {
            "total_usd": total_spend,
            "cap_usd": args.total_cap_usd,
            "remaining_usd": round(args.total_cap_usd - total_spend, 6),
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\ntotal spend ${total_spend:.6f} against cap ${args.total_cap_usd:.2f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
