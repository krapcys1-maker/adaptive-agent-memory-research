#!/usr/bin/env python3
"""Transparent post-hoc localization for PMLAB-PACK-002 without retuning."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "data" / "lab" / "pmlab-pack-characterization-v1" / "execution-v0"
BUDGETS = [512, 768, 1024, 1536]
ORDERS = ["O0_RETRIEVAL", "O1_GOVERNED", "O2_REQUIRED_ORACLE"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def analyze() -> dict[str, Any]:
    rows = load_jsonl(EXECUTION / "packs.jsonl")
    paired: list[dict[str, Any]] = []
    for budget in BUDGETS:
        for order in ORDERS:
            full = {
                row["case_id"]: row for row in rows
                if row["budget_utf8"] == budget and row["order_arm"] == order and row["format_arm"] == "C0_FULL_INLINE"
            }
            compact = {
                row["case_id"]: row for row in rows
                if row["budget_utf8"] == budget and row["order_arm"] == order and row["format_arm"] == "C1_SOURCE_FOOTER"
            }
            deltas = {case_id: compact[case_id]["required_retention"] - full[case_id]["required_retention"] for case_id in full}
            paired.append(
                {
                    "budget_utf8": budget,
                    "order_arm": order,
                    "mean_compact_minus_full": statistics.mean(deltas.values()),
                    "improved_cases": sorted(case_id for case_id, delta in deltas.items() if delta > 0),
                    "equal_cases": sorted(case_id for case_id, delta in deltas.items() if delta == 0),
                    "worse_cases": sorted(case_id for case_id, delta in deltas.items() if delta < 0),
                    "per_case_delta": deltas,
                }
            )
    complete_full = [
        row for row in rows
        if row["budget_utf8"] == 1536 and row["order_arm"] == "O0_RETRIEVAL" and row["format_arm"] == "C0_FULL_INLINE"
    ]
    complete_compact = [
        row for row in rows
        if row["budget_utf8"] == 1536 and row["order_arm"] == "O0_RETRIEVAL" and row["format_arm"] == "C1_SOURCE_FOOTER"
    ]
    return {
        "experiment_id": "PMLAB-PACK-002",
        "analysis_status": "post-hoc-transparent-localization-no-retuning",
        "paired_format_deltas": paired,
        "complete_pack_mean_bytes": {
            "C0_FULL_INLINE": statistics.mean(row["utf8_bytes"] for row in complete_full),
            "C1_SOURCE_FOOTER": statistics.mean(row["utf8_bytes"] for row in complete_compact),
            "compact_minus_full": statistics.mean(row["utf8_bytes"] for row in complete_compact)
            - statistics.mean(row["utf8_bytes"] for row in complete_full),
        },
        "integrity_failures": [
            {"case_id": row["case_id"], "format_arm": row["format_arm"], "order_arm": row["order_arm"], "budget": row["budget_utf8"]}
            for row in rows
            if row["citation_errors"]
            or row["evidence_errors"]
            or row["stale_marker_errors"]
            or row["untrusted_exposed"]
            or not row["omission_ledger_complete"]
            or not row["budget_compliant"]
        ],
        "interpretation": "descriptive paired localization over a visible authored fixture; cannot select format or order for a reader",
    }


def main() -> None:
    result = analyze()
    path = EXECUTION / "posthoc-analysis.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
