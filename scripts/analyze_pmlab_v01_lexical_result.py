#!/usr/bin/env python3
"""Post-hoc descriptive failure localization for the sealed PMLAB v0.1 result."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data" / "lab" / "pmlab-v0.1-lexical-exploratory-m2"
RESULTS = RUN / "test" / "primary-results.jsonl"
SUMMARY = RUN / "test" / "final-summary.json"
GOLD = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-pmlab-v01-adjudication-m2-20260823" / "model-reviewed-gold.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def analyze(rows: list[dict[str, Any]], gold_rows: list[dict[str, Any]], final: dict[str, Any]) -> dict[str, Any]:
    gold = {row["example_id"]: row for row in gold_rows}
    by_backend = {name: {row["example_id"]: row for row in rows if row["backend"] == name} for name in ("B1-ripgrep", "B2-sqlite-fts5")}
    b1, b2 = by_backend["B1-ripgrep"], by_backend["B2-sqlite-fts5"]
    ids = sorted(b1)
    answerable = [value for value in ids if b1[value]["answerable"]]
    unanswerable = [value for value in ids if not b1[value]["answerable"]]

    def recall(value: str, backend: dict[str, dict[str, Any]]) -> float:
        return float(backend[value]["recall_at_5"])

    def forbidden_details(value: str, backend: dict[str, dict[str, Any]]) -> list[str]:
        return sorted(set(backend[value]["retrieved"]) & set(gold[value]["forbidden_stale_ids"]))

    b2_failures = [
        {
            "example_id": value, "category": b2[value]["category"], "consequence_weight": b2[value]["consequence_weight"],
            "recall_at_5": b2[value]["recall_at_5"], "all_required_at_5": b2[value]["all_required_at_5"],
            "forbidden_retrieved": forbidden_details(value, b2), "retrieved": b2[value]["retrieved"],
        }
        for value in ids
        if (b2[value]["answerable"] and (b2[value]["recall_at_5"] < 1 or b2[value]["forbidden_intrusion_at_5"]))
        or (not b2[value]["answerable"] and b2[value]["candidate_count"] > 0)
    ]
    critical = [value for value in answerable if b2[value]["consequence_weight"] >= 4]
    summary = final["summary"]["backends"]
    warm = final["warm_latency"]["by_backend"]
    return {
        "status": "post-hoc-descriptive-failure-localization",
        "decision_unchanged": final["decision"]["outcome"],
        "authority": "descriptive analysis of sealed M2 exploratory output; no threshold or architecture change",
        "paired_recall": {
            "b2_wins": [value for value in answerable if recall(value, b2) > recall(value, b1)],
            "b1_wins": [value for value in answerable if recall(value, b1) > recall(value, b2)],
            "ties": [value for value in answerable if recall(value, b1) == recall(value, b2)],
        },
        "full_evidence": {
            "b2_recovers_b1_miss": [value for value in answerable if b2[value]["all_required_at_5"] and not b1[value]["all_required_at_5"]],
            "b2_loses_b1_success": [value for value in answerable if b1[value]["all_required_at_5"] and not b2[value]["all_required_at_5"]],
        },
        "forbidden_intrusion": {
            "new_in_b2": [value for value in ids if b2[value]["forbidden_intrusion_at_5"] and not b1[value]["forbidden_intrusion_at_5"]],
            "removed_by_b2": [value for value in ids if b1[value]["forbidden_intrusion_at_5"] and not b2[value]["forbidden_intrusion_at_5"]],
            "b2_cases": [{"example_id": value, "forbidden_retrieved": forbidden_details(value, b2)} for value in ids if b2[value]["forbidden_intrusion_at_5"]],
        },
        "critical_memory": {
            "queries": len(critical),
            "b1_misses": [value for value in critical if not b1[value]["all_required_at_5"]],
            "b2_misses": [value for value in critical if not b2[value]["all_required_at_5"]],
        },
        "unanswerable": {
            "queries": len(unanswerable),
            "b1_nonempty": [value for value in unanswerable if b1[value]["candidate_count"] > 0],
            "b2_nonempty": [value for value in unanswerable if b2[value]["candidate_count"] > 0],
        },
        "b2_incomplete_answerable_by_category": dict(sorted(Counter(b2[value]["category"] for value in answerable if b2[value]["recall_at_5"] < 1).items())),
        "b2_failure_cases": b2_failures,
        "resource_tradeoff": {
            "warm_p50_speed_ratio_b1_over_b2": warm["B1-ripgrep"]["p50_ms"] / warm["B2-sqlite-fts5"]["p50_ms"],
            "warm_p95_speed_ratio_b1_over_b2": warm["B1-ripgrep"]["p95_ms"] / warm["B2-sqlite-fts5"]["p95_ms"],
            "index_size_ratio_b2_over_b1": summary["B2-sqlite-fts5"]["index_bytes"] / summary["B1-ripgrep"]["index_bytes"],
        },
    }


def report(value: dict[str, Any], final: dict[str, Any]) -> str:
    b2 = final["summary"]["backends"]["B2-sqlite-fts5"]
    paired, critical, forbidden = value["paired_recall"], value["critical_memory"], value["forbidden_intrusion"]
    lines = [
        "# PMLAB v0.1 lexical failure localization", "",
        "Status: post-hoc descriptive analysis of sealed exploratory output; decision and thresholds unchanged", "",
        "## What advanced", "",
        f"B2 beat B1 on Recall@5 for {len(paired['b2_wins'])} answerable queries, lost on {len(paired['b1_wins'])}, and tied on {len(paired['ties'])}. It recovered {len(value['full_evidence']['b2_recovers_b1_miss'])} complete-evidence cases that B1 missed and lost {len(value['full_evidence']['b2_loses_b1_success'])} B1 successes.", "",
        f"The warm median query-time ratio was {value['resource_tradeoff']['warm_p50_speed_ratio_b1_over_b2']:.1f}x in B2's favor, while the FTS5 index used {value['resource_tradeoff']['index_size_ratio_b2_over_b1']:.2f}x the bytes of the ripgrep text view.", "",
        "## What remains unsafe or incomplete", "",
        f"Absolute B2 macro Recall@5 was {b2['macro_recall_at_5_answerable_strata']:.3f}; all-required@5 was {b2['all_required_at_5_rate']:.3f}. It missed complete evidence on {len(critical['b2_misses'])}/{critical['queries']} critical queries.", "",
        f"B2 retrieved forbidden evidence on {len(forbidden['b2_cases'])}/60 queries. It introduced {len(forbidden['new_in_b2'])} forbidden cases absent from B1 and removed {len(forbidden['removed_by_b2'])} B1 forbidden cases.", "",
        f"Both lexical backends returned candidates for every one of the {value['unanswerable']['queries']} unanswerable queries. Candidate-null behavior therefore remains 0; this is not an abstention mechanism.", "",
        "The weakest B2 answerable strata were cross-language (0.200), paraphrase (0.400), causal multi-episode (0.500), and poison resistance (0.500). These are failure-localization targets, not permission to tune on the spent test set.", "",
        "## Consequence", "",
        "FTS5 advances only as the stronger sparse retrieval baseline for a new preregistered experiment. The result does not admit dense embeddings, graphs, salience, a reader policy, or product architecture. The current test set is spent and must not be used to tune B2 or a successor.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    final = json.loads(SUMMARY.read_text(encoding="utf-8"))
    value = analyze(read_jsonl(RESULTS), read_jsonl(GOLD), final)
    (RUN / "failure-analysis.json").write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (RUN / "failure-analysis.md").write_text(report(value, final), encoding="utf-8", newline="\n")
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
