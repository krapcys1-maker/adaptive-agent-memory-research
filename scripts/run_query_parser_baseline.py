#!/usr/bin/env python3
"""Evaluate a measurable entity/time parser without answer-label access.

The parser receives only query text and a catalog derived from corpus metadata.
Challenge labels are used after retrieval for scoring, never during parsing.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import tempfile
import unicodedata
from collections import defaultdict
from datetime import date
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
    from scripts.run_query_scope_factorial import normalized_text
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
    from run_query_scope_factorial import normalized_text


OUTPUT = DEFAULT_DATASET / "parser-v0"
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(ch for ch in folded if not unicodedata.combining(ch))))


def build_catalog(corpus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in corpus:
        grouped[record["history_id"]].append(record)
    catalog = []
    for history_id, records in sorted(grouped.items()):
        ordered = sorted(records, key=lambda row: (row["version"], row["valid_from"]))
        catalog.append(
            {
                "history_id": history_id,
                "entity": ordered[0]["entity"],
                "topic": ordered[0]["topic"],
                "versions": [
                    {"version": row["version"], "valid_from": row["valid_from"]}
                    for row in ordered
                ],
            }
        )
    return catalog


def natural_date(text: str) -> str | None:
    iso = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso:
        try:
            return date.fromisoformat(iso.group(1)).isoformat()
        except ValueError:
            return None
    match = re.search(
        r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})\s*,?\s*(20\d{2})\b",
        text,
    )
    if not match:
        return None
    try:
        return date(int(match.group(3)), MONTHS[match.group(1)], int(match.group(2))).isoformat()
    except ValueError:
        return None


def parse_query(text: str, catalog: list[dict[str, Any]]) -> dict[str, Any]:
    clean = normalize(text)
    entity_candidates = [row for row in catalog if normalize(row["entity"]) in clean]
    if not entity_candidates:
        return {"status": "abstain", "reason": "unknown-entity", "history_id": None, "target_date": None}

    scored = []
    query_tokens = set(clean.split())
    for row in entity_candidates:
        topic_tokens = set(normalize(row["topic"]).split())
        scored.append((len(query_tokens & topic_tokens) / len(topic_tokens), row))
    best_score = max(score for score, _ in scored)
    best = [row for score, row in scored if score == best_score]
    if len(best) != 1 and best_score == 0:
        return {"status": "abstain", "reason": "ambiguous-entity", "history_id": None, "target_date": None}
    if len(best) != 1:
        return {"status": "abstain", "reason": "ambiguous-topic", "history_id": None, "target_date": None}
    history = best[0]

    versions = history["versions"]
    target_date = natural_date(text.casefold())
    temporal_mode = "date" if target_date else None
    if "two revisions before the latest" in clean or "dwie zmiany przed najnowsza" in clean:
        temporal_mode = "relative-version"
        target_index = len(versions) - 3
        if target_index < 0:
            return {"status": "abstain", "reason": "relative-time-out-of-range", "history_id": history["history_id"], "target_date": None}
        target_date = versions[target_index]["valid_from"]
    elif target_date is None and any(marker in clean.split() for marker in ("current", "currently", "now")):
        temporal_mode = "current"
        target_date = versions[-1]["valid_from"]
    elif target_date is None:
        return {"status": "abstain", "reason": "unresolved-time", "history_id": history["history_id"], "target_date": None}

    valid_dates = {row["valid_from"] for row in versions}
    if target_date not in valid_dates:
        return {"status": "abstain", "reason": "date-out-of-range", "history_id": history["history_id"], "target_date": target_date}
    return {
        "status": "parsed",
        "reason": None,
        "history_id": history["history_id"],
        "entity": history["entity"],
        "topic": history["topic"],
        "temporal_mode": temporal_mode,
        "target_date": target_date,
        "retrieval_text": f"{history['entity']} {history['topic']} {target_date}",
    }


def retrieve(
    corpus: list[dict[str, Any]],
    text: str,
    root: Path,
    name: str,
) -> list[str]:
    backend = FTS5Retriever(corpus, root / f"{name}.sqlite")
    try:
        return backend.retrieve(text, TOP_K)
    finally:
        backend.close()


def run() -> dict[str, Any]:
    corpus = make_f2_corpus()
    queries = make_f2_queries()
    catalog = build_catalog(corpus)
    records_by_id = {row["evidence_id"]: row for row in corpus}
    parser_outputs = []
    results = []
    with tempfile.TemporaryDirectory(prefix="pmlab-parser-v0-") as temporary:
        root = Path(temporary)
        for index, query in enumerate(queries):
            parsed = parse_query(query["query"], catalog)
            parser_outputs.append({"example_id": query["example_id"], "query": query["query"], **parsed})
            arm_inputs: list[tuple[str, list[dict[str, Any]], str | None]] = [
                ("raw-all", corpus, query["query"]),
                ("oracle-normalized-all", corpus, normalized_text(query, records_by_id)),
            ]
            if parsed["status"] == "parsed":
                arm_inputs.extend(
                    [
                        ("parser-all", corpus, parsed["retrieval_text"]),
                        (
                            "parser-history",
                            [row for row in corpus if row["history_id"] == parsed["history_id"]],
                            parsed["retrieval_text"],
                        ),
                    ]
                )
            else:
                arm_inputs.extend((("parser-all", corpus, None), ("parser-history", [], None)))
            for arm, candidates, retrieval_text in arm_inputs:
                retrieved = [] if retrieval_text is None else retrieve(candidates, retrieval_text, root, f"{index:03d}-{arm}")
                results.append(
                    {
                        "arm": arm,
                        "example_id": query["example_id"],
                        "category": query["category"],
                        "parser_status": parsed["status"] if arm.startswith("parser") else "not-applicable",
                        "retrieved": retrieved,
                        **score_query(query, retrieved),
                    }
                )

    summaries = []
    for arm in sorted({row["arm"] for row in results}):
        rows = [row for row in results if row["arm"] == arm]
        answerable = [row for row in rows if row["recall_at_5"] is not None]
        unanswerable = [row for row in rows if row["correct_abstention"] is not None]
        summaries.append(
            {
                "arm": arm,
                "answerable_recall_at_5": statistics.mean(row["recall_at_5"] for row in answerable),
                "answerable_mrr": statistics.mean(row["reciprocal_rank"] for row in answerable),
                "forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in answerable),
                "unanswerable_abstention_rate": statistics.mean(row["correct_abstention"] for row in unanswerable),
            }
        )
    answerable_pairs = [
        (output, query)
        for output, query in zip(parser_outputs, queries)
        if query["answerable"]
    ]
    parser_exact_history = statistics.mean(
        output.get("history_id") == query["history_id"]
        for output, query in answerable_pairs
    )
    parser_exact_target_date = statistics.mean(
        output.get("target_date")
        == records_by_id[query["gold_evidence_ids"][0]]["valid_from"]
        for output, query in answerable_pairs
    )
    parser_correct_abstention = statistics.mean(
        output["status"] == "abstain"
        for output, query in zip(parser_outputs, queries)
        if not query["answerable"]
    )
    summary = {
        "status": "completed-development-parser-baseline",
        "queries": len(queries),
        "catalog_histories": len(catalog),
        "parser_answerable_history_accuracy": parser_exact_history,
        "parser_answerable_target_date_accuracy": parser_exact_target_date,
        "parser_unanswerable_abstention": parser_correct_abstention,
        "arms": summaries,
        "boundary": "Parser v0 was authored after challenge templates were observed and uses corpus metadata. It is measurable and label-free at runtime but is not held out.",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUTPUT / "parser-outputs.jsonl", parser_outputs)
    write_jsonl(OUTPUT / "results.jsonl", results)
    write_json(OUTPUT / "summary.json", summary)
    write_json(
        OUTPUT / "manifest.json",
        {
            "status": summary["status"],
            "script": "scripts/run_query_parser_baseline.py",
            "dataset": "data/lab/pmlab-forgetting-challenge-v0",
            "parser_inputs": "query text plus catalog built from corpus entity/topic/version/valid_from metadata",
            "forbidden_runtime_inputs": ["query history_id", "gold_evidence_ids", "expected answer", "category"],
            "catalog_sha256": hashlib.sha256(json.dumps(catalog, sort_keys=True).encode()).hexdigest(),
            "authority": "template-observed development baseline only",
        },
    )
    return summary


def main() -> int:
    print(json.dumps(run(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
