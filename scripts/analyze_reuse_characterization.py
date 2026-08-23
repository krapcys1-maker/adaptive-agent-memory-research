#!/usr/bin/env python3
"""Post-hoc transparent failure analysis for PMLAB-REUSE-CHAR-001."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-reuse-characterization-v0"
EXECUTION = BASE / "execution-v0"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def analyze() -> dict[str, Any]:
    queries = {row["query_id"]: row for row in load_jsonl(BASE / "queries.jsonl")}
    retrieval = load_jsonl(EXECUTION / "retrieval-results.jsonl")
    packs = load_jsonl(EXECUTION / "pack-results.jsonl")
    arms = sorted({row["arm"] for row in retrieval})
    failures: dict[str, list[dict[str, Any]]] = {}
    forbidden_sets: dict[str, set[str]] = {}
    unanswerable: dict[str, list[dict[str, Any]]] = {}
    for arm in arms:
        failures[arm] = []
        forbidden_sets[arm] = set()
        unanswerable[arm] = []
        for row in retrieval:
            if row["arm"] != arm:
                continue
            query = queries[row["query_id"]]
            missing = sorted(set(query["required_ids"]) - set(row["ranked"]))
            forbidden = sorted(set(query["forbidden_ids"]) & set(row["ranked"]))
            if forbidden:
                forbidden_sets[arm].add(row["query_id"])
            if missing or forbidden:
                failures[arm].append(
                    {
                        "query_id": row["query_id"],
                        "query": query["query"],
                        "category": query["category"],
                        "missing_required_ids": missing,
                        "forbidden_returned_ids": forbidden,
                        "ranked": row["ranked"],
                    }
                )
            if not query["answerable"]:
                unanswerable[arm].append(
                    {"query_id": row["query_id"], "query": query["query"], "ranked": row["ranked"]}
                )
    packaging: dict[str, dict[str, Any]] = {}
    for arm in arms:
        packaging[arm] = {}
        for mode in ("raw", "cited", "bucketed"):
            selected = [row for row in packs if row["arm"] == arm and row["mode"] == mode]
            answerable = [row for row in selected if row["answerable"]]
            packaging[arm][mode] = {
                "required_retained": statistics.mean(row["required_retained"] for row in answerable),
                "omitted_items": sum(len(row["omitted"]) for row in selected),
                "mean_utf8_bytes": statistics.mean(row["utf8_bytes"] for row in selected),
                "queries_with_required_pack_loss": [
                    row["query_id"] for row in answerable
                    if row["required_retained"] < next(
                        raw["required_retained"]
                        for raw in packs
                        if raw["arm"] == arm and raw["query_id"] == row["query_id"] and raw["mode"] == "raw"
                    )
                ],
            }
    return {
        "experiment_id": "PMLAB-REUSE-CHAR-001",
        "analysis_status": "post-hoc-transparent-failure-localization-no-retuning",
        "failure_cases": failures,
        "forbidden_query_sets": {arm: sorted(values) for arm, values in forbidden_sets.items()},
        "rrf_forbidden_subset_of_dense": forbidden_sets.get("C2_RRF", set()) <= forbidden_sets.get("C0_FASTEMBED", set()),
        "rrf_dense_forbidden_overlap": sorted(forbidden_sets.get("C2_RRF", set()) & forbidden_sets.get("C0_FASTEMBED", set())),
        "unanswerable_candidates": unanswerable,
        "packaging_by_arm": packaging,
        "authority": "descriptive post-hoc localization over committed output; no tuning or architecture authority",
    }


def main() -> None:
    result = analyze()
    path = EXECUTION / "failure-analysis.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    # Keep stdout usable in the default Windows cp1252 console. The artifact
    # itself remains UTF-8 and preserves the original Polish query text.
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
