#!/usr/bin/env python3
"""Run an authored adversarial challenge against the F1/F2 development rules.

The entity/template split is new relative to pmlab-forgetting-dev, but labels
are still authored locally. This is a challenge-development set, not an
independently annotated confirmatory test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    from scripts.run_forgetting_benchmark import (
        FTS5Retriever,
        NoMemory,
        OracleRetriever,
        RipgrepRetriever,
        RuleEntityTimeRetriever,
        TextBackend,
    )
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from run_forgetting_benchmark import (
        FTS5Retriever,
        NoMemory,
        OracleRetriever,
        RipgrepRetriever,
        RuleEntityTimeRetriever,
        TextBackend,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "lab" / "pmlab-forgetting-challenge-v0"
TOP_K = 5


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


STAGE_PROBES = {
    "F0": ("write_receipt",),
    "F1": ("canonical_found", "canonical_bytes_recoverable", "checksum_match", "schema_valid", "provenance_valid"),
    "F2": ("gold_retrieved",),
    "F3": ("gold_in_context",),
    "F4": ("reader_answer_correct",),
    "F5": ("action_correct", "judge_correct"),
}


def healthy_isolated_probes() -> dict[str, bool | None]:
    return {probe: True for probes in STAGE_PROBES.values() for probe in probes}


def diagnose_fault_set(probes: dict[str, bool | None]) -> dict[str, Any]:
    """Diagnose isolated stage probes while preserving missing telemetry."""
    known_faults: list[str] = []
    unknown_stages: list[str] = []
    for stage, names in STAGE_PROBES.items():
        values = [probes.get(name) for name in names]
        if any(value is False for value in values):
            known_faults.append(stage)
        elif any(value is None for value in values):
            unknown_stages.append(stage)
    recoverable = probes.get("canonical_bytes_recoverable")
    data_loss = None if recoverable is None else not recoverable
    return {
        "known_faults": known_faults,
        "unknown_stages": unknown_stages,
        "data_loss_diagnosed": data_loss,
        "complete": not unknown_stages,
    }


def make_f1_challenges() -> list[dict[str, Any]]:
    specs = [
        ("storage-plus-index", {"canonical_found": False, "canonical_bytes_recoverable": False, "gold_retrieved": False}, ["F1", "F2"], [], True),
        ("index-plus-reader", {"gold_retrieved": False, "reader_answer_correct": False}, ["F2", "F4"], [], False),
        ("selection-plus-action", {"gold_in_context": False, "action_correct": False}, ["F3", "F5"], [], False),
        ("capture-plus-reader", {"write_receipt": False, "reader_answer_correct": False}, ["F0", "F4"], [], False),
        ("recoverable-schema-plus-selection", {"schema_valid": False, "gold_in_context": False}, ["F1", "F3"], [], False),
        ("provenance-reader-judge", {"provenance_valid": False, "reader_answer_correct": False, "judge_correct": False}, ["F1", "F4", "F5"], [], False),
        ("checksum-plus-action", {"checksum_match": False, "canonical_bytes_recoverable": False, "action_correct": False}, ["F1", "F5"], [], True),
        ("index-selection-reader", {"gold_retrieved": False, "gold_in_context": False, "reader_answer_correct": False}, ["F2", "F3", "F4"], [], False),
        ("unknown-storage", {"checksum_match": None}, [], ["F1"], False),
        ("unknown-index-known-reader", {"gold_retrieved": None, "reader_answer_correct": False}, ["F4"], ["F2"], False),
        ("unknown-selection-known-action", {"gold_in_context": None, "action_correct": False}, ["F5"], ["F3"], False),
        ("unknown-reader-and-judge", {"reader_answer_correct": None, "judge_correct": None}, [], ["F4", "F5"], False),
        ("unknown-recoverability", {"canonical_bytes_recoverable": None}, [], ["F1"], None),
        ("capture-index-unknown-action", {"write_receipt": False, "gold_retrieved": False, "action_correct": None}, ["F0", "F2"], ["F5"], False),
        ("schema-unknown-reader", {"schema_valid": False, "reader_answer_correct": None}, ["F1"], ["F4"], False),
        ("all-healthy", {}, [], [], False),
    ]
    cases = []
    for index, (name, changes, expected_faults, expected_unknown, expected_loss) in enumerate(specs, start=1):
        probes = healthy_isolated_probes()
        probes.update(changes)
        cases.append(
            {
                "case_id": f"F1CH-{index:03d}",
                "name": name,
                "probe_semantics": "each stage is tested under an isolated upstream control",
                "probes": probes,
                "expected_faults": expected_faults,
                "expected_unknown_stages": expected_unknown,
                "expected_data_loss": expected_loss,
            }
        )
    return cases


HISTORIES = (
    ("aster-key", "Aster", "access phrase", 3, "phrase"),
    ("juniper-route", "Juniper", "delivery route", 7, "route"),
    ("nimbus-owner", "Nimbus", "incident owner", 11, "owner"),
    ("vela-threshold", "Vela", "safety threshold", 19, "threshold"),
    ("mercury-project", "Mercury", "project channel", 31, "channel"),
    ("mercury-planet", "Mercury", "observation window", 47, "window"),
    ("jordan-analyst", "Jordan", "review duty", 13, "analyst"),
    ("jordan-station", "Jordan", "station locker", 23, "locker"),
)


def record_date(version: int) -> str:
    return (date(2026, 1, 1) + timedelta(days=version - 1)).isoformat()


def challenge_id(history_id: str, version: int) -> str:
    return f"F2CH-{history_id.upper()}-V{version:03d}"


def make_f2_corpus() -> list[dict[str, Any]]:
    rows = []
    for history_id, entity, topic, length, prefix in HISTORIES:
        for version in range(1, length + 1):
            valid_from = record_date(version)
            valid_to = record_date(version + 1) if version < length else None
            rows.append(
                {
                    "evidence_id": challenge_id(history_id, version),
                    "history_id": history_id,
                    "entity": entity,
                    "topic": topic,
                    "version": version,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                    "title": f"{entity} {topic} revision {version:03d}",
                    "body": f"For {entity}, the {topic} in revision {version:03d} is {prefix}-{version:03d}. Effective date {valid_from}.",
                    "value": f"{prefix}-{version:03d}",
                    "source": "deterministic-authored-challenge",
                }
            )
    return rows


def _query(
    example_id: str,
    history_id: str | None,
    category: str,
    text: str,
    version: int | None,
    forbidden: list[str],
    language: str = "en",
) -> dict[str, Any]:
    gold = [challenge_id(history_id, version)] if history_id and version else []
    return {
        "example_id": example_id,
        "history_id": history_id,
        "category": category,
        "query": text,
        "language": language,
        "answerable": bool(gold),
        "gold_evidence_ids": gold,
        "forbidden_stale_ids": forbidden,
    }


def versions_except(history_id: str, length: int, keep: int) -> list[str]:
    return [challenge_id(history_id, version) for version in range(1, length + 1) if version != keep]


def make_f2_queries() -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    unique = HISTORIES[:4]
    for history_id, entity, topic, length, _prefix in unique:
        queries.append(
            _query(
                f"{history_id}-current",
                history_id,
                "unseen-current",
                f"What is the current {topic} for {entity}?",
                length,
                versions_except(history_id, length, length),
            )
        )
        iso_version = max(1, length // 2)
        queries.append(
            _query(
                f"{history_id}-iso",
                history_id,
                "unseen-iso-time",
                f"What was the {entity} {topic} on {record_date(iso_version)}?",
                iso_version,
                versions_except(history_id, length, iso_version),
            )
        )
        relative_version = max(1, length - 2)
        relative_text = (
            f"Jaka była {topic} dla {entity} dwie zmiany przed najnowszą?"
            if history_id == "nimbus-owner"
            else f"What was the {entity} {topic} two revisions before the latest?"
        )
        queries.append(
            _query(
                f"{history_id}-relative",
                history_id,
                "relative-time",
                relative_text,
                relative_version,
                versions_except(history_id, length, relative_version),
                "pl" if history_id == "nimbus-owner" else "en",
            )
        )

    for history_id, entity, topic, length, _prefix in HISTORIES[4:]:
        queries.append(
            _query(
                f"{history_id}-topic-current",
                history_id,
                "ambiguous-name-current",
                f"What is the current {topic} for {entity}?",
                length,
                versions_except(history_id, length, length),
            )
        )
        natural_version = max(1, length // 3)
        natural_date = date.fromisoformat(record_date(natural_version))
        natural_text = f"What was the {entity} {topic} on {natural_date.strftime('%B')} {natural_date.day}, {natural_date.year}?"
        queries.append(
            _query(
                f"{history_id}-natural-date",
                history_id,
                "natural-language-time",
                natural_text,
                natural_version,
                versions_except(history_id, length, natural_version),
            )
        )

    queries.extend(
        [
            _query("mercury-ambiguous", None, "ambiguous-unanswerable", "What is the current Mercury value?", None, []),
            _query("jordan-ambiguous", None, "ambiguous-unanswerable", "What is currently assigned to Jordan?", None, []),
            _query("missing-entity", None, "unknown-entity-unanswerable", "What is the current recovery code for Zephyr?", None, []),
            _query("missing-date-scope", None, "underspecified-time-unanswerable", "What was the old Vela value?", None, []),
        ]
    )
    return queries


def validate_f2(corpus: list[dict[str, Any]], queries: list[dict[str, Any]]) -> None:
    ids = {row["evidence_id"] for row in corpus}
    if len(ids) != len(corpus):
        raise ValueError("duplicate evidence IDs")
    for query in queries:
        gold = set(query["gold_evidence_ids"])
        forbidden = set(query["forbidden_stale_ids"])
        if not gold.issubset(ids) or not forbidden.issubset(ids):
            raise ValueError(f"unknown evidence in {query['example_id']}")
        if gold & forbidden:
            raise ValueError(f"gold/forbidden overlap in {query['example_id']}")
        if query["answerable"] != bool(gold):
            raise ValueError(f"answerable mismatch in {query['example_id']}")


def score_query(query: dict[str, Any], retrieved: list[str]) -> dict[str, Any]:
    if not query["answerable"]:
        return {
            "recall_at_5": None,
            "reciprocal_rank": None,
            "correct_abstention": not retrieved,
            "forbidden_intrusion": False,
        }
    positions = {item: index + 1 for index, item in enumerate(retrieved)}
    ranks = [positions[item] for item in query["gold_evidence_ids"] if item in positions]
    return {
        "recall_at_5": sum(item in positions for item in query["gold_evidence_ids"]) / len(query["gold_evidence_ids"]),
        "reciprocal_rank": 1 / min(ranks) if ranks else 0.0,
        "correct_abstention": None,
        "forbidden_intrusion": bool(set(query["forbidden_stale_ids"]).intersection(retrieved)),
    }


def run_f1(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = []
    for case in cases:
        diagnosis = diagnose_fault_set(case["probes"])
        results.append(
            {
                "case_id": case["case_id"],
                **diagnosis,
                "fault_set_correct": diagnosis["known_faults"] == case["expected_faults"],
                "unknown_set_correct": diagnosis["unknown_stages"] == case["expected_unknown_stages"],
                "data_loss_correct": diagnosis["data_loss_diagnosed"] == case["expected_data_loss"],
            }
        )
    return results, {
        "status": "authored-challenge-development-only",
        "cases": len(cases),
        "multi_fault_cases": sum(len(case["expected_faults"]) > 1 for case in cases),
        "missing_telemetry_cases": sum(bool(case["expected_unknown_stages"]) for case in cases),
        "exact_fault_set_accuracy": statistics.mean(row["fault_set_correct"] for row in results),
        "exact_unknown_set_accuracy": statistics.mean(row["unknown_set_correct"] for row in results),
        "data_loss_accuracy": statistics.mean(row["data_loss_correct"] for row in results),
        "boundary": "Stage probes are explicitly isolated; this does not solve causal localization from one cascading end-to-end trace.",
    }


def run_f2(corpus: list[dict[str, Any]], queries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = []
    with tempfile.TemporaryDirectory(prefix="pmlab-challenge-") as temporary:
        work = Path(temporary)
        backends: list[Any] = [
            TextBackend(NoMemory()),
            TextBackend(RipgrepRetriever(corpus, work / "rg")),
            TextBackend(FTS5Retriever(corpus, work / "fts5.sqlite")),
            RuleEntityTimeRetriever(corpus),
            OracleRetriever(),
        ]
        try:
            for backend in backends:
                for query in queries:
                    retrieved = backend.retrieve(query, TOP_K)
                    results.append(
                        {
                            "backend": backend.name,
                            "example_id": query["example_id"],
                            "category": query["category"],
                            "retrieved": retrieved,
                            **score_query(query, retrieved),
                        }
                    )
        finally:
            for backend in backends:
                close = getattr(backend, "close", None)
                if close:
                    close()

    summaries = []
    for backend in sorted({row["backend"] for row in results}):
        rows = [row for row in results if row["backend"] == backend]
        answerable = [row for row in rows if row["recall_at_5"] is not None]
        unanswerable = [row for row in rows if row["correct_abstention"] is not None]
        categories: dict[str, list[float]] = defaultdict(list)
        for row in answerable:
            categories[row["category"]].append(row["recall_at_5"])
        summaries.append(
            {
                "backend": backend,
                "answerable_recall_at_5": statistics.mean(row["recall_at_5"] for row in answerable),
                "answerable_mrr": statistics.mean(row["reciprocal_rank"] for row in answerable),
                "forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in answerable),
                "unanswerable_abstention_rate": statistics.mean(row["correct_abstention"] for row in unanswerable),
                "recall_by_category": {name: statistics.mean(values) for name, values in sorted(categories.items())},
            }
        )
    return results, {
        "status": "authored-challenge-development-only",
        "records": len(corpus),
        "queries": len(queries),
        "answerable": sum(query["answerable"] for query in queries),
        "unanswerable": sum(not query["answerable"] for query in queries),
        "top_k": TOP_K,
        "results": summaries,
        "boundary": "Entities and query templates are unseen from development, but corpus and labels were authored by the same project agent and are not independent gold.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F1/F2 adversarial challenge v0")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()

    f1_cases = make_f1_challenges()
    f2_corpus = make_f2_corpus()
    f2_queries = make_f2_queries()
    validate_f2(f2_corpus, f2_queries)
    f1_results, f1_summary = run_f1(f1_cases)
    f2_results, f2_summary = run_f2(f2_corpus, f2_queries)

    args.dataset.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.dataset / "f1-challenges.jsonl", f1_cases)
    write_jsonl(args.dataset / "f2-corpus.jsonl", f2_corpus)
    write_jsonl(args.dataset / "f2-queries.jsonl", f2_queries)
    artifacts = args.dataset / "artifacts"
    write_jsonl(artifacts / "f1-results.jsonl", f1_results)
    write_json(artifacts / "f1-summary.json", f1_summary)
    write_jsonl(artifacts / "f2-results.jsonl", f2_results)
    write_json(artifacts / "f2-summary.json", f2_summary)
    manifest = {
        "status": "authored-challenge-development-only",
        "generator": "scripts/run_forgetting_challenge.py",
        "held_out_from_development": True,
        "independent_annotation": False,
        "f1_fault_contract": "multi-fault isolated probes plus missing telemetry",
        "f2_corpus_description": "eight unequal histories with duplicate surface names and unseen development entities",
        "f2_query_description": "current, ISO, relative, natural-language, ambiguous, and unanswerable queries",
        "b3_input": "query text only; exact entity surface name and optional ISO date; no gold query metadata",
        "f1_cases": len(f1_cases),
        "f2_records": len(f2_corpus),
        "f2_queries": len(f2_queries),
        "f1_sha256": canonical_hash(f1_cases),
        "f2_corpus_sha256": canonical_hash(f2_corpus),
        "f2_queries_sha256": canonical_hash(f2_queries),
        "backends": ["B0-no-memory", "B1-ripgrep", "B2-sqlite-fts5", "B3-rule-entity-time", "O-gold-evidence"],
        "authority": "adversarial development evidence only; no confirmatory or architecture claim",
    }
    write_json(artifacts / "manifest.json", manifest)
    print(json.dumps({"f1": f1_summary, "f2": f2_summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
