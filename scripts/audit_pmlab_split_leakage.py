#!/usr/bin/env python3
"""Label-free lexical/template similarity audit for PMLAB dev/test queries."""

from __future__ import annotations

import difflib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "lab" / "project-memory-lab-v0-construction" / "blind" / "queries.jsonl"
OUT = ROOT / "data" / "lab" / "pmlab-v0-split-audit"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]+", text.casefold()))


def ngrams(text: str, n: int = 3) -> set[str]:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    return {normalized[index:index + n] for index in range(max(0, len(normalized) - n + 1))}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left | right else 1.0


def audit(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs = []
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for category in sorted({row["category"] for row in rows}):
        development = [row for row in rows if row["category"] == category and row["split"] == "development"]
        test = [row for row in rows if row["category"] == category and row["split"] == "test"]
        for left in development:
            for right in test:
                row = {
                    "category": category, "development_id": left["example_id"], "test_id": right["example_id"],
                    "sequence_ratio": difflib.SequenceMatcher(None, left["query"].casefold(), right["query"].casefold()).ratio(),
                    "token_jaccard": jaccard(tokens(left["query"]), tokens(right["query"])),
                    "character_trigram_jaccard": jaccard(ngrams(left["query"]), ngrams(right["query"])),
                    "development_query": left["query"], "test_query": right["query"],
                }
                pairs.append(row)
                by_category[category].append(row)
    maxima = {
        category: {metric: max(row[metric] for row in values) for metric in ["sequence_ratio", "token_jaccard", "character_trigram_jaccard"]}
        for category, values in by_category.items()
    }
    flags = [row for row in pairs if row["sequence_ratio"] >= 0.85 or row["token_jaccard"] >= 0.75 or row["character_trigram_jaccard"] >= 0.70]
    summary = {
        "status": "posthoc-label-free-construction-audit",
        "source": "project-memory-lab-v0-construction blind queries frozen at 612eb06",
        "query_count": len(rows), "cross_split_pairs": len(pairs), "flagged_pairs": len(flags),
        "flagged_categories": sorted({row["category"] for row in flags}), "category_maxima": maxima,
        "thresholds_are_confirmatory": False,
        "decision_basis": "registered split policy requires different development/test templates; direct inspection shows repeated authored frames",
        "decision": "reject v0 split for held-out confirmation; preserve as instrument defect; author v0.1 before review or backend execution",
        "labels_read": False, "backend_output_read": False,
    }
    return pairs, summary


def main() -> int:
    rows = read_jsonl(SOURCE)
    pairs, summary = audit(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pairs.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in pairs), encoding="utf-8", newline="\n")
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report = [
        "# PMLAB v0 development/test split audit", "",
        "Status: v0 rejected for held-out confirmation before labels or backend execution", "",
        f"The label-free audit compared {summary['cross_split_pairs']} within-category development/test query pairs. It flagged {summary['flagged_pairs']} pairs across {len(summary['flagged_categories'])} categories: " + ", ".join(summary["flagged_categories"]) + ".", "",
        "The numeric thresholds are descriptive and post-hoc. The rejection does not depend on treating them as preregistered: the registered split policy already required different query templates, while direct paired inspection shows repeated frames with mostly entity/failure substitutions.", "",
        "## Category maxima", "", "| Category | Sequence | Token Jaccard | Character trigram Jaccard |", "| --- | ---: | ---: | ---: |",
    ]
    for category, metrics in summary["category_maxima"].items():
        report.append(f"| {category} | {metrics['sequence_ratio']:.3f} | {metrics['token_jaccard']:.3f} | {metrics['character_trigram_jaccard']:.3f} |")
    report += ["", "## Decision", "", "Do not request independent labels and do not execute B0/B1/B2 on this split. Preserve the corpus, protocol, and audit as a pre-run instrument failure. V0.1 must change test query forms without changing evidence records or reading backend results, rerun this audit, and issue new packet hashes."]
    (OUT / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
