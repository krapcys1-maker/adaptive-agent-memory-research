#!/usr/bin/env python3
"""Factor query normalization from history scoping on challenge v0.

Both interventions use registered gold metadata and are diagnostic ceilings,
not deployable resolvers. This localizes where improvement is possible before
implementing a learned or rule-based query interpreter.
"""

from __future__ import annotations

import json
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.run_forgetting_benchmark import FTS5Retriever
    from scripts.run_forgetting_challenge import (
        DEFAULT_DATASET,
        TOP_K,
        make_f2_corpus,
        make_f2_queries,
        score_query,
        write_json,
        write_jsonl,
    )
except ModuleNotFoundError:
    from run_forgetting_benchmark import FTS5Retriever
    from run_forgetting_challenge import (
        DEFAULT_DATASET,
        TOP_K,
        make_f2_corpus,
        make_f2_queries,
        score_query,
        write_json,
        write_jsonl,
    )


OUTPUT = DEFAULT_DATASET / "factorial"


def normalized_text(query: dict[str, Any], records_by_id: dict[str, dict[str, Any]]) -> str:
    if not query["answerable"]:
        return query["query"]
    record = records_by_id[query["gold_evidence_ids"][0]]
    return f"{record['entity']} {record['topic']} {record['valid_from']}"


def scoped_records(query: dict[str, Any], corpus: list[dict[str, Any]], scoped: bool) -> list[dict[str, Any]]:
    if not scoped or not query["answerable"]:
        return corpus
    return [row for row in corpus if row["history_id"] == query["history_id"]]


def run_arm(
    name: str,
    corpus: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    normalize: bool,
    scope_history: bool,
) -> list[dict[str, Any]]:
    records_by_id = {row["evidence_id"]: row for row in corpus}
    results = []
    with tempfile.TemporaryDirectory(prefix="pmlab-factorial-") as temporary:
        root = Path(temporary)
        for index, query in enumerate(queries):
            candidates = scoped_records(query, corpus, scope_history)
            backend = FTS5Retriever(candidates, root / f"q{index:03d}.sqlite")
            try:
                text = normalized_text(query, records_by_id) if normalize else query["query"]
                retrieved = backend.retrieve(text, TOP_K)
            finally:
                backend.close()
            results.append(
                {
                    "arm": name,
                    "example_id": query["example_id"],
                    "category": query["category"],
                    "query_intervention": "oracle-normalized" if normalize else "raw",
                    "scope_intervention": "oracle-history" if scope_history else "all-records",
                    "retrieved": retrieved,
                    **score_query(query, retrieved),
                }
            )
    return results


def oracle_validity(queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for query in queries:
        retrieved = query["gold_evidence_ids"] if query["answerable"] else []
        rows.append(
            {
                "arm": "O-validity-ceiling",
                "example_id": query["example_id"],
                "category": query["category"],
                "query_intervention": "gold-structured",
                "scope_intervention": "gold-validity",
                "retrieved": retrieved,
                **score_query(query, retrieved),
            }
        )
    return rows


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = []
    for arm in sorted({row["arm"] for row in results}):
        rows = [row for row in results if row["arm"] == arm]
        answerable = [row for row in rows if row["recall_at_5"] is not None]
        unanswerable = [row for row in rows if row["correct_abstention"] is not None]
        by_category: dict[str, list[float]] = defaultdict(list)
        for row in answerable:
            by_category[row["category"]].append(row["recall_at_5"])
        summaries.append(
            {
                "arm": arm,
                "answerable_recall_at_5": statistics.mean(row["recall_at_5"] for row in answerable),
                "answerable_mrr": statistics.mean(row["reciprocal_rank"] for row in answerable),
                "forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in answerable),
                "unanswerable_abstention_rate": statistics.mean(row["correct_abstention"] for row in unanswerable),
                "recall_by_category": {key: statistics.mean(value) for key, value in sorted(by_category.items())},
            }
        )
    lookup = {row["arm"]: row for row in summaries}
    baseline = lookup["Q0-raw_S0-all"]["answerable_recall_at_5"]
    return {
        "status": "oracle-intervention-diagnostic-only",
        "queries": len({row["example_id"] for row in results}),
        "arms": summaries,
        "main_effect_query_normalization_at_all_scope": lookup["Q1-normalized_S0-all"]["answerable_recall_at_5"] - baseline,
        "main_effect_history_scope_at_raw_query": lookup["Q0-raw_S1-history"]["answerable_recall_at_5"] - baseline,
        "combined_gain": lookup["Q1-normalized_S1-history"]["answerable_recall_at_5"] - baseline,
        "boundary": "Q1 and S1 consume registered gold metadata; effects are diagnostic ceilings, not deployable-system results.",
    }


def main() -> int:
    corpus = make_f2_corpus()
    queries = make_f2_queries()
    results = []
    results.extend(run_arm("Q0-raw_S0-all", corpus, queries, False, False))
    results.extend(run_arm("Q1-normalized_S0-all", corpus, queries, True, False))
    results.extend(run_arm("Q0-raw_S1-history", corpus, queries, False, True))
    results.extend(run_arm("Q1-normalized_S1-history", corpus, queries, True, True))
    results.extend(oracle_validity(queries))
    summary = summarize(results)
    write_jsonl(OUTPUT / "results.jsonl", results)
    write_json(OUTPUT / "summary.json", summary)
    write_json(
        OUTPUT / "manifest.json",
        {
            "status": summary["status"],
            "script": "scripts/run_query_scope_factorial.py",
            "dataset": "data/lab/pmlab-forgetting-challenge-v0",
            "top_k": TOP_K,
            "retriever": "SQLite FTS5 for Q0/Q1 x S0/S1",
            "interventions": {"Q1": "gold-normalized entity topic ISO date", "S1": "gold history scope"},
            "authority": "mechanism-localization diagnostic only",
        },
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
