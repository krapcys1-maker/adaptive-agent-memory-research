#!/usr/bin/env python3
"""ONE calibration case: does the model actually use a correct session
reference date when extracting facts, or does the patch only change the
prompt text without changing behavior?

Answers exactly one question: given the SAME synthetic/diagnostic input,
does BASE (reference_date=None, i.e. the pinned, unpatched 1.0.6 behavior)
differ from TREATMENT (reference_date=2022-11-17, the
PER_SESSION_REFERENCE_DATE_AT_EXTRACTION patch) in how a relative-time phrase
gets resolved? Not a benchmark run: no unit selection, no reader, no judge.

BASE and TREATMENT ingest the identical message into two separate, isolated
banks (different user_id) so neither run's "existing memories" search can see
the other's writes. BASE omits timestamp metadata entirely so
`_add_to_vector_store` receives `reference_date=None` through the same,
already-patched code path -- this is the real unpatched behavior, not a
simulation of it, because reference_date=None is verified (see
tests/test_mem0_per_session_reference_date_patch.py) to be byte-identical to
calling the function before the patch existed.

Hard cap $0.02, enforced by the same SpendLedger + provider-proxy mechanism
used everywhere else in this arena.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.02)
    parser.add_argument("--total-cap-usd", type=float, default=0.02)
    parser.add_argument("--cap-scope", default="calibration-refdate-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/base-plus-x-calibration-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/base-plus-x-v1/calibration-per-session-reference-date.json"))
    args = parser.parse_args()

    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import build_mem0  # noqa: F401

    # run_id must itself START WITH --cap-scope (the prefix ledger.scoped_usd()
    # matches against) or scoped_usd() finds nothing and this script's own cost
    # reporting reads zero -- even though the provider proxy's separate,
    # in-process cap (ProxyState.spent_usd/check()) still enforces the real
    # ceiling regardless of this mismatch. Found by this script's own first
    # run reporting $0.0000 against a real $0.0016 spent -- see
    # calibration-per-session-reference-date.json's cost_usd.note.
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=f"{args.cap_scope}run",
                         cap_scope=args.cap_scope)
    built = build_mem0(args, ledger)
    memory = built["adapter"]._memory

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))
    from mem0.memory.utils import get_fact_retrieval_messages, parse_messages

    # One synthetic/diagnostic input, patterned directly on the real evidence
    # from this session's own archaeology finding (gpt4_f420262c: a Mem0
    # memory phrased as "...from San Francisco to Boston" with the relative
    # word "today" and no absolute date anywhere in the stored text).
    INPUT_TEXT = ("I took a red-eye flight on JetBlue from San Francisco to Boston "
                 "today and managed to sleep for almost the entire flight.")
    SESSION_DATE = "2022-11-17"
    messages = [{"role": "user", "content": INPUT_TEXT}]
    parsed = parse_messages(messages)

    base_system_prompt, base_user_prompt = get_fact_retrieval_messages(
        parsed, is_agent_memory=False, reference_date=None)
    treatment_system_prompt, treatment_user_prompt = get_fact_retrieval_messages(
        parsed, is_agent_memory=False, reference_date=SESSION_DATE)
    assert base_system_prompt != treatment_system_prompt, "calibration input didn't exercise the patch"

    def ingest_and_read(bank: str, metadata):
        adapter = built["adapter"]
        adapter._bank = bank
        adapter.reset()
        assert adapter.stored_count() == 0, f"{bank}: scratch bank not empty before calibration"
        memory.add(messages=messages, user_id=bank, metadata=metadata)
        stored = memory.get_all(user_id=bank, limit=1000)
        rows = stored.get("results") if isinstance(stored, dict) else stored
        return [{"memory": r.get("memory"), "metadata": r.get("metadata")} for r in (rows or [])]

    before = ledger.scoped_usd()
    base_facts = ingest_and_read("calibration-base", metadata=None)
    after_base = ledger.scoped_usd()
    treatment_facts = ingest_and_read("calibration-treatment", metadata={"timestamp": SESSION_DATE})
    after_treatment = ledger.scoped_usd()

    base_texts = [f["memory"] for f in base_facts]
    treatment_texts = [f["memory"] for f in treatment_facts]
    date_appears_base = any(SESSION_DATE in (t or "") for t in base_texts)
    date_appears_treatment = any(SESSION_DATE in (t or "") for t in treatment_texts)

    record = {
        "artifact": "arena-base-plus-x-v1-calibration",
        "treatment_name": "PER_SESSION_REFERENCE_DATE_AT_EXTRACTION",
        "question": ("does the model, given a correct session reference date, actually "
                     "change temporal extraction in the predicted way? BASE vs TREATMENT "
                     "on the identical input. Not a benchmark accuracy measurement."),
        "input": {"text": INPUT_TEXT, "session_date_given_to_treatment": SESSION_DATE},
        "base_system_prompt": base_system_prompt,
        "treatment_system_prompt": treatment_system_prompt,
        "user_prompt_identical_both_arms": base_user_prompt,
        "base_extracted_facts": base_facts,
        "treatment_extracted_facts": treatment_facts,
        "session_date_appears_verbatim_in_base_facts": date_appears_base,
        "session_date_appears_verbatim_in_treatment_facts": date_appears_treatment,
        "cost_usd": {
            "base": round(after_base - before, 6),
            "treatment": round(after_treatment - after_base, 6),
            "total": round(after_treatment - before, 6),
            "cap_usd": args.total_cap_usd,
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in record.items()
                      if k not in ("base_system_prompt", "treatment_system_prompt")},
                     indent=2, ensure_ascii=False))
    print(f"total spend ${after_treatment - before:.4f} against cap ${args.total_cap_usd:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
