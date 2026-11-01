#!/usr/bin/env python3
"""MECHANISM_J CALIBRATION-ONLY: does one extra "what did you miss" LLM call,
re-reading the original text against Mem0's own already-extracted facts,
actually recover standalone facts the first extraction pass merged away or
dropped -- especially individual items within an enumerated list, the
project's own named priority-1 write-time-extraction-loss subtype?

Capability calibration of the completeness-check step only. Calls the real
extraction path (get_fact_retrieval_messages + generate_response, the exact
shape memory.add() uses internally) to get an HONEST baseline -- not a
hand-faked "already extracted" set -- then calls get_completeness_check_
messages() + a second generate_response() against that same model's own
real output. Stops there: no memory.add() pipeline, no update-decision call,
no vector-store write, no retrieval. 2 calls per case = 10 calls for 5 cases.

Preregistration: PM-20260824-<TBD> (recorded before this script runs).
Treatment: EXTRACTION_COMPLETENESS_VERIFICATION_PASS (patch: data/lab/arena/
extraction-completeness-verification-v1/vendor-patch/
EXTRACTION_COMPLETENESS_VERIFICATION_PASS.{utils,main}.patch).

Hard cap $0.05, enforced by the same SpendLedger + provider-proxy mechanism
used everywhere else in this arena, cap_scope="mechj-calib-" (must be a
literal prefix of run_id).
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
        "case_id": "CASE1_INLINE_AND_LIST",
        "reference_date": "2023-04-10",
        "input_text": ("My favorite movies are Inception, Interstellar, and Tenet. "
                       "I could watch them again anytime."),
        "note": ("byte-for-byte matches the extraction prompt's own few-shot pattern "
                 "(2-item 'and' list -> 1 merged fact), extended to 3 items -- the "
                 "clearest, most predictable test of the merge behavior."),
    },
    {
        "case_id": "CASE2_NUMBERED_LIST",
        "reference_date": "2023-04-10",
        "input_text": ("Here are my top 3 goals this year: 1. Run a marathon "
                       "2. Learn Spanish 3. Save $5000 for a trip to Japan."),
        "note": "explicit numbered list, a shape not directly modeled by any existing few-shot example",
    },
    {
        "case_id": "CASE3_SPECIFIC_ENTITIES",
        "reference_date": "2023-04-10",
        "input_text": "I bought 3 books today: Dune, Foundation, and Neuromancer.",
        "note": "specific named entities + a count, testing whether individual titles survive",
    },
    {
        "case_id": "CASE4_LIST_AMID_OTHER_CONTENT",
        "reference_date": "2023-04-10",
        "input_text": ("I've been really busy lately. I signed up for pottery, salsa "
                       "dancing, and rock climbing classes this month. Also thinking "
                       "about getting a new bike."),
        "note": "more realistic: a list embedded among unrelated content, matching this project's real observed failure shape",
    },
    {
        "case_id": "CASE5_NO_LIST_NEGATIVE_CONTROL",
        "reference_date": "2023-04-10",
        "input_text": "I love hiking on weekends and usually go with my dog.",
        "note": "negative control -- no enumerable list; missed_facts should come back empty (no over-triggering/hallucination)",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.05)
    parser.add_argument("--total-cap-usd", type=float, default=0.05)
    parser.add_argument("--cap-scope", default="mechj-calib-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/mechj-calibration-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/extraction-completeness-verification-v1/calibration.json"))
    args = parser.parse_args()

    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import build_mem0

    assert args.cap_scope and (args.cap_scope + "run").startswith(args.cap_scope), "sanity"
    run_id = f"{args.cap_scope}run"
    assert run_id.startswith(args.cap_scope), "cap_scope must be a literal prefix of run_id"
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=run_id, cap_scope=args.cap_scope)

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))
    built = build_mem0(args, ledger)
    memory = built["adapter"]._memory

    from mem0.memory.utils import (
        get_fact_retrieval_messages, get_completeness_check_messages,
        parse_messages, ensure_json_instruction, remove_code_blocks, extract_json,
    )

    def call(system_prompt: str, user_prompt: str) -> tuple[list, float]:
        before = ledger.scoped_usd()
        raw = memory.llm.generate_response(
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"})
        after = ledger.scoped_usd()
        cleaned = remove_code_blocks(raw)
        return raw, cleaned, round(after - before, 6)

    print("=== COST GATE (before first paid call) ===")
    print("RESEARCH_QUESTION: does an extra completeness-check LLM call recover facts "
          "Mem0's own extraction merges away or drops, especially individual items "
          "within an enumerated list (this project's own named priority-1 gap)?")
    print("WHY_THIS_CALL_IS_NEEDED: EXTRACTION_COMPLETENESS_VERIFICATION_PASS is a "
          "write-side vendor patch to Mem0's own extraction pipeline -- the biggest "
          "code-surface change of any mechanism tested this campaign -- and the "
          "project's own precedent (EVENT_TIME_RESOLUTION_AT_EXTRACTION) found a "
          "different write-side instruction inert; calibrate cheaply before any "
          "8-unit exploratory spend")
    print("EXPECTED_INFORMATION_GAIN: does the mechanism visibly change behavior at all "
          "(inert vs not), before spending on whether it helps end-to-end accuracy")
    print(f"PROJECTED_CALLS: {len(CASES) * 2} (2 per case: baseline extraction + completeness check)")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f}")
    print(f"GLOBAL_SPEND_SO_FAR (this scope): ${ledger.scoped_usd():.6f}")
    print("=== END COST GATE -- proceeding ===\n")

    results = []
    for case in CASES:
        parsed = parse_messages([{"role": "user", "content": case["input_text"]}])
        sys_p, usr_p = get_fact_retrieval_messages(
            parsed, is_agent_memory=False, reference_date=case["reference_date"])
        sys_p, usr_p = ensure_json_instruction(sys_p, usr_p)
        raw_extract, cleaned_extract, cost_extract = call(sys_p, usr_p)
        try:
            baseline_facts = (json.loads(cleaned_extract)["facts"] if cleaned_extract.strip() else [])
        except json.JSONDecodeError:
            baseline_facts = json.loads(extract_json(cleaned_extract))["facts"]

        comp_sys, comp_usr = get_completeness_check_messages(parsed, baseline_facts)
        comp_sys, comp_usr = ensure_json_instruction(comp_sys, comp_usr)
        raw_comp, cleaned_comp, cost_comp = call(comp_sys, comp_usr)
        try:
            comp_parsed = json.loads(cleaned_comp) if cleaned_comp.strip() else {}
        except json.JSONDecodeError:
            comp_parsed = json.loads(extract_json(cleaned_comp))
        facts_to_add = comp_parsed.get("facts_to_add", []) or []
        facts_to_replace = comp_parsed.get("facts_to_replace", []) or []

        corrected_facts = list(baseline_facts)
        for replacement in facts_to_replace:
            original = str(replacement.get("original", "")).strip()
            split_into = [str(s).strip() for s in (replacement.get("split_into") or []) if str(s).strip()]
            if not original or not split_into:
                continue
            corrected_facts = [f for f in corrected_facts if f.strip().lower() != original.lower()]
            corrected_facts.extend(split_into)
        for missed in facts_to_add:
            missed = str(missed).strip()
            if missed and not any(missed.lower() in existing.lower()
                                  or existing.lower() in missed.lower()
                                  for existing in corrected_facts):
                corrected_facts.append(missed)

        results.append({
            "case_id": case["case_id"], "note": case["note"],
            "input_text": case["input_text"],
            "baseline_facts": baseline_facts, "baseline_cost_usd": cost_extract,
            "raw_completeness_response": cleaned_comp,
            "facts_to_add": facts_to_add, "facts_to_replace": facts_to_replace,
            "corrected_facts": corrected_facts, "completeness_cost_usd": cost_comp,
            "changed_behavior": corrected_facts != baseline_facts,
        })
        print(f"{case['case_id']}: baseline={baseline_facts}")
        print(f"  -> add={facts_to_add} replace={facts_to_replace}")
        print(f"  -> corrected={corrected_facts} | cumulative ${ledger.scoped_usd():.6f}")

    record = {
        "artifact": "arena-extraction-completeness-verification-v1-calibration",
        "treatment_definition": (
            "EXTRACTION_COMPLETENESS_VERIFICATION_PASS: after Mem0's normal extraction "
            "call returns new_retrieved_facts, one additional LLM call re-reads the "
            "original text against those facts and proposes any standalone facts "
            "omitted, especially individual items within an enumerated list."
        ),
        "prompt_diff": ("data/lab/arena/extraction-completeness-verification-v1/vendor-patch/"
                        "EXTRACTION_COMPLETENESS_VERIFICATION_PASS.{utils,main}.patch"),
        "call_shape": ("get_fact_retrieval_messages() + generate_response() for baseline "
                       "(the real, unmodified extraction path), then "
                       "get_completeness_check_messages() + generate_response() against "
                       "that same real baseline output -- no memory.add() pipeline, no "
                       "update-decision call, no vector-store write. 2 calls per case."),
        "cases": results,
        "cases_with_recovered_facts": sum(1 for r in results if r["changed_behavior"]),
        "spend": {"total_usd": round(ledger.scoped_usd(), 6), "cap_usd": args.total_cap_usd,
                  "remaining_usd": round(args.total_cap_usd - ledger.scoped_usd(), 6)},
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\ntotal spend ${ledger.scoped_usd():.6f} against cap ${args.total_cap_usd:.2f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
