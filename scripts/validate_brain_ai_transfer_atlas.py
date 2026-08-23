#!/usr/bin/env python3
"""Validate the machine-readable Brain-to-AI transfer atlas."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATLAS = ROOT / "docs" / "13-brain-ai-transfer" / "atlas-v0.csv"
FIELDS = [
    "id", "domain", "biological_mechanism", "computational_problem", "abstraction",
    "biology_status", "ml_status", "llm_agent_status", "implementation_examples",
    "benchmark_evidence", "transfer_status", "primary_risk", "next_test",
    "biology_sources", "ai_sources",
]
BIOLOGY = {"established", "supported", "mixed", "contested"}
ML = {"mature", "demonstrated", "partial", "sparse", "none_found"}
AGENT = {"common", "demonstrated", "partial", "sparse", "none_found"}
BENCHMARK = {"strong diagnostic", "strong outside agents", "partial", "weak", "none"}
TRANSFER = {
    "existing_baseline", "active_project_hypothesis", "gap_candidate",
    "background_only", "reject_literal_transfer",
}


def validate(path: Path = DEFAULT_ATLAS) -> dict[str, object]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError("atlas header differs from the v0 contract")
        rows = list(reader)

    expected_ids = [f"BTA-{index:03d}" for index in range(1, 39)]
    ids = [row["id"] for row in rows]
    if ids != expected_ids:
        raise ValueError("atlas must contain ordered unique IDs BTA-001 through BTA-038")

    allowed = {
        "biology_status": BIOLOGY,
        "ml_status": ML,
        "llm_agent_status": AGENT,
        "benchmark_evidence": BENCHMARK,
        "transfer_status": TRANSFER,
    }
    for row in rows:
        empty = [
            field for field in FIELDS
            if not row[field].strip()
            and not (field == "ai_sources" and row["llm_agent_status"] == "none_found")
        ]
        if empty:
            raise ValueError(f"{row['id']}: empty fields: {', '.join(empty)}")
        for field, values in allowed.items():
            if row[field] not in values:
                raise ValueError(f"{row['id']}: invalid {field}: {row[field]}")
        if "http" not in row["biology_sources"]:
            raise ValueError(f"{row['id']}: biology_sources needs a stable HTTP identifier")
        if row["llm_agent_status"] != "none_found" and "http" not in row["ai_sources"]:
            raise ValueError(f"{row['id']}: implemented agent transfer needs an inspectable AI source")
        if len(row["next_test"].split()) < 5:
            raise ValueError(f"{row['id']}: next_test is not operational enough")

    return {
        "status": "valid-research-atlas-not-architecture-approval",
        "path": str(path),
        "rows": len(rows),
        "gap_candidates": sum(row["transfer_status"] == "gap_candidate" for row in rows),
        "agent_status": dict(sorted(Counter(row["llm_agent_status"] for row in rows).items())),
        "transfer_status": dict(sorted(Counter(row["transfer_status"] for row in rows).items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    args = parser.parse_args()
    print(json.dumps(validate(args.atlas), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
