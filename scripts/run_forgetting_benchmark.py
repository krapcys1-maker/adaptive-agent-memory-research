#!/usr/bin/env python3
"""Build and run deterministic F1/F2 forgetting-development instruments.

This is an authored diagnostic slice. It validates observability and exposes
expected lexical interference; it is not a held-out architecture comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    from scripts.run_memory_benchmark import FTS5Retriever, NoMemory, RipgrepRetriever
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from run_memory_benchmark import FTS5Retriever, NoMemory, RipgrepRetriever


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "lab" / "pmlab-forgetting-dev"
UPDATE_COUNTS = (1, 2, 4, 8, 16, 32, 64)
TOP_K = 5


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def localize_fault(probes: dict[str, bool]) -> str:
    """Return the earliest demonstrably failed stage in a single-fault trace."""
    if not probes["write_receipt"]:
        return "F0"
    if not all(
        probes[name]
        for name in ("canonical_found", "checksum_match", "schema_valid", "provenance_valid")
    ):
        return "F1"
    if not probes["gold_retrieved"]:
        return "F2"
    if not probes["gold_in_context"]:
        return "F3"
    if not probes["reader_answer_correct"]:
        return "F4"
    if not probes["action_correct"] or not probes["judge_correct"]:
        return "F5"
    return "OK"


def _healthy_probes() -> dict[str, bool]:
    return {
        "source_event_present": True,
        "write_receipt": True,
        "canonical_found": True,
        "canonical_bytes_recoverable": True,
        "checksum_match": True,
        "schema_valid": True,
        "provenance_valid": True,
        "full_scan_found": True,
        "gold_retrieved": True,
        "gold_in_context": True,
        "reader_answer_correct": True,
        "action_correct": True,
        "judge_correct": True,
    }


def make_fault_cases() -> list[dict[str, Any]]:
    variants = (
        ("routine", 1),
        ("temporal", 2),
        ("rare-critical", 5),
        ("poison-adjacent", 4),
    )
    mutations: dict[str, tuple[str, ...]] = {
        "OK": (),
        "F0": ("write_receipt", "canonical_found", "full_scan_found", "gold_retrieved", "gold_in_context", "reader_answer_correct", "action_correct", "judge_correct"),
        "F1": ("checksum_match",),
        "F2": ("gold_retrieved", "gold_in_context", "reader_answer_correct", "action_correct", "judge_correct"),
        "F3": ("gold_in_context", "reader_answer_correct", "action_correct", "judge_correct"),
        "F4": ("reader_answer_correct", "action_correct", "judge_correct"),
        "F5": ("action_correct",),
    }
    cases: list[dict[str, Any]] = []
    for label, fields in mutations.items():
        for index, (variant, consequence_weight) in enumerate(variants, start=1):
            probes = _healthy_probes()
            for field in fields:
                probes[field] = False
            if label == "F1":
                storage_failure = ("missing", "checksum", "schema", "provenance")[index - 1]
                if storage_failure == "missing":
                    probes["canonical_found"] = False
                    probes["canonical_bytes_recoverable"] = False
                    probes["full_scan_found"] = False
                elif storage_failure == "checksum":
                    probes["canonical_bytes_recoverable"] = False
                elif storage_failure == "schema":
                    probes["checksum_match"] = True
                    probes["schema_valid"] = False
                elif storage_failure == "provenance":
                    probes["checksum_match"] = True
                    probes["provenance_valid"] = False
            if label == "F5" and index % 2 == 0:
                probes["action_correct"] = True
                probes["judge_correct"] = False
            cases.append(
                {
                    "case_id": f"F1DEV-{label}-{index:02d}",
                    "variant": variant,
                    "consequence_weight": consequence_weight,
                    "fault_contract": "single-fault",
                    "expected_label": label,
                    "expected_data_loss": label == "F1" and not probes["canonical_bytes_recoverable"],
                    "end_to_end_success": label == "OK",
                    "probes": probes,
                }
            )
    return cases


TRACKS = (
    {
        "history_id": "atlas-access",
        "entity": "Atlas",
        "topic": "access code",
        "language": "en",
        "current_query": "What is the current access code for Atlas?",
        "historical_query": "What was the Atlas access code on {date}?",
        "value_prefix": "amber",
        "similarity": "high",
    },
    {
        "history_id": "helios-route",
        "entity": "Helios",
        "topic": "deployment route",
        "language": "en",
        "current_query": "Which deployment route is now valid for Helios?",
        "historical_query": "Which Helios deployment route was valid on {date}?",
        "value_prefix": "corridor",
        "similarity": "high",
    },
    {
        "history_id": "mira-protocol",
        "entity": "Mira",
        "topic": "recovery protocol",
        "language": "pl",
        "current_query": "Jaki protokół odzyskiwania jest teraz ważny dla Mira?",
        "historical_query": "Jaki protokół odzyskiwania dla Mira obowiązywał dnia {date}?",
        "value_prefix": "procedure",
        "similarity": "low",
    },
    {
        "history_id": "quartz-owner",
        "entity": "Quartz",
        "topic": "incident owner",
        "language": "en",
        "current_query": "Who is the current incident owner for Quartz?",
        "historical_query": "Who was the Quartz incident owner on {date}?",
        "value_prefix": "operator",
        "similarity": "low",
    },
)


def version_date(version: int) -> str:
    return (date(2026, 1, 1) + timedelta(days=version - 1)).isoformat()


def make_interference_corpus() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for track in TRACKS:
        for version in range(1, max(UPDATE_COUNTS) + 1):
            valid_from = version_date(version)
            valid_to = version_date(version + 1) if version < max(UPDATE_COUNTS) else None
            evidence_id = f"F2-{track['history_id'].upper()}-V{version:03d}"
            value = f"{track['value_prefix']}-{version:03d}"
            records.append(
                {
                    "evidence_id": evidence_id,
                    "history_id": track["history_id"],
                    "entity": track["entity"],
                    "version": version,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                    "title": f"{track['entity']} {track['topic']} revision {version:03d}",
                    "body": f"{track['entity']} {track['topic']} revision {version:03d} is {value}. Effective date {valid_from}.",
                    "value": value,
                    "similarity": track["similarity"],
                    "source": "deterministic-synthetic",
                }
            )
    return records


def evidence_id(history_id: str, version: int) -> str:
    return f"F2-{history_id.upper()}-V{version:03d}"


def make_interference_queries() -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    for update_count in UPDATE_COUNTS:
        for track in TRACKS:
            current_gold = evidence_id(track["history_id"], update_count)
            prior = [evidence_id(track["history_id"], version) for version in range(1, update_count)]
            queries.append(
                {
                    "example_id": f"F2DEV-N{update_count:02d}-{track['history_id']}-CURRENT",
                    "history_id": track["history_id"],
                    "query_type": "current",
                    "query": track["current_query"],
                    "language": track["language"],
                    "update_count": update_count,
                    "as_of_version": update_count,
                    "gold_evidence_ids": [current_gold],
                    "forbidden_stale_ids": prior,
                }
            )
            as_of = max(1, update_count // 2)
            historical_gold = evidence_id(track["history_id"], as_of)
            future = [
                evidence_id(track["history_id"], version)
                for version in range(as_of + 1, update_count + 1)
            ]
            queries.append(
                {
                    "example_id": f"F2DEV-N{update_count:02d}-{track['history_id']}-HIST",
                    "history_id": track["history_id"],
                    "query_type": "historical-as-of",
                    "query": track["historical_query"].format(date=version_date(as_of)),
                    "language": track["language"],
                    "update_count": update_count,
                    "as_of_version": as_of,
                    "gold_evidence_ids": [historical_gold],
                    "forbidden_stale_ids": future,
                }
            )
    return queries


class TextBackend:
    def __init__(self, backend: Any) -> None:
        self.backend = backend
        self.name = backend.name

    def retrieve(self, query: dict[str, Any], top_k: int) -> list[str]:
        return self.backend.retrieve(query["query"], top_k)

    def close(self) -> None:
        close = getattr(self.backend, "close", None)
        if close:
            close()


class RuleEntityTimeRetriever:
    name = "B3-rule-entity-time"

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records

    def retrieve(self, query: dict[str, Any], top_k: int) -> list[str]:
        del top_k
        query_text = query["query"].casefold()
        entities = sorted(
            {row["entity"] for row in self.records if row["entity"].casefold() in query_text}
        )
        if len(entities) != 1:
            return []
        candidates = [row for row in self.records if row["entity"] == entities[0]]
        if not candidates:
            return []
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", query["query"])
        if dates:
            if len(dates) != 1:
                return []
            target_date = dates[0]
            candidates = [
                row
                for row in candidates
                if row["valid_from"] <= target_date
                and (row["valid_to"] is None or target_date < row["valid_to"])
            ]
            if len(candidates) != 1:
                return []
            return [candidates[0]["evidence_id"]]
        return [max(candidates, key=lambda row: row["version"])["evidence_id"]]


class OracleRetriever:
    name = "O-gold-evidence"

    def retrieve(self, query: dict[str, Any], top_k: int) -> list[str]:
        return query["gold_evidence_ids"][:top_k]


def score_retrieval(query: dict[str, Any], retrieved: list[str]) -> dict[str, Any]:
    positions = {item: index + 1 for index, item in enumerate(retrieved)}
    gold = query["gold_evidence_ids"]
    ranks = [positions[item] for item in gold if item in positions]
    return {
        "recall_at_5": sum(item in positions for item in gold) / len(gold),
        "reciprocal_rank": 1 / min(ranks) if ranks else 0.0,
        "forbidden_intrusion": bool(set(query["forbidden_stale_ids"]).intersection(retrieved)),
    }


def normalized_auc(points: dict[int, float]) -> float:
    ordered = sorted((math.log2(count), value) for count, value in points.items())
    if len(ordered) < 2 or ordered[-1][0] == ordered[0][0]:
        return ordered[0][1] if ordered else 0.0
    area = sum(
        (right_x - left_x) * (left_y + right_y) / 2
        for (left_x, left_y), (right_x, right_y) in zip(ordered, ordered[1:])
    )
    return area / (ordered[-1][0] - ordered[0][0])


def validate_interference(corpus: list[dict[str, Any]], queries: list[dict[str, Any]]) -> None:
    ids = [row["evidence_id"] for row in corpus]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate F2 evidence ID")
    known = set(ids)
    for query in queries:
        if not set(query["gold_evidence_ids"]).issubset(known):
            raise ValueError(f"unknown gold evidence in {query['example_id']}")
        if not set(query["forbidden_stale_ids"]).issubset(known):
            raise ValueError(f"unknown forbidden evidence in {query['example_id']}")
        if set(query["gold_evidence_ids"]) & set(query["forbidden_stale_ids"]):
            raise ValueError(f"gold/forbidden overlap in {query['example_id']}")


def run_fault_localization(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results = []
    by_label: dict[str, list[int]] = defaultdict(list)
    data_loss_errors = 0
    for case in cases:
        predicted = localize_fault(case["probes"])
        predicted_data_loss = predicted == "F1" and not case["probes"]["canonical_bytes_recoverable"]
        correct = predicted == case["expected_label"]
        by_label[case["expected_label"]].append(int(correct))
        if predicted_data_loss != case["expected_data_loss"]:
            data_loss_errors += 1
        results.append(
            {
                "case_id": case["case_id"],
                "expected_label": case["expected_label"],
                "predicted_label": predicted,
                "correct": correct,
                "expected_data_loss": case["expected_data_loss"],
                "predicted_data_loss": predicted_data_loss,
            }
        )
    summary = {
        "status": "instrument-development-only",
        "cases": len(cases),
        "macro_accuracy": statistics.mean(statistics.mean(values) for values in by_label.values()),
        "accuracy_by_label": {label: statistics.mean(values) for label, values in sorted(by_label.items())},
        "data_loss_diagnosis_errors": data_loss_errors,
        "interpretation": "Validates authored trace logic only; independent adversarial cases are required.",
    }
    return results, summary


def run_interference(
    corpus: list[dict[str, Any]], queries: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="pmlab-forgetting-") as temporary:
        work_root = Path(temporary)
        for update_count in UPDATE_COUNTS:
            snapshot = [row for row in corpus if row["version"] <= update_count]
            snapshot_queries = [row for row in queries if row["update_count"] == update_count]
            backends: list[Any] = [
                TextBackend(NoMemory()),
                TextBackend(RipgrepRetriever(snapshot, work_root / f"n{update_count}" / "rg")),
                TextBackend(FTS5Retriever(snapshot, work_root / f"n{update_count}" / "fts5.sqlite")),
                RuleEntityTimeRetriever(snapshot),
                OracleRetriever(),
            ]
            try:
                for backend in backends:
                    for query in snapshot_queries:
                        retrieved = backend.retrieve(query, TOP_K)
                        results.append(
                            {
                                "backend": backend.name,
                                "example_id": query["example_id"],
                                "query_type": query["query_type"],
                                "language": query["language"],
                                "update_count": update_count,
                                "retrieved": retrieved,
                                **score_retrieval(query, retrieved),
                            }
                        )
            finally:
                for backend in backends:
                    close = getattr(backend, "close", None)
                    if close:
                        close()

    backend_names = sorted({row["backend"] for row in results})
    summaries = []
    for backend in backend_names:
        backend_rows = [row for row in results if row["backend"] == backend]
        current_curve = {
            count: statistics.mean(
                row["recall_at_5"]
                for row in backend_rows
                if row["query_type"] == "current" and row["update_count"] == count
            )
            for count in UPDATE_COUNTS
        }
        historical = [row for row in backend_rows if row["query_type"] == "historical-as-of"]
        current = [row for row in backend_rows if row["query_type"] == "current"]
        summaries.append(
            {
                "backend": backend,
                "current_recall_curve": {str(key): value for key, value in current_curve.items()},
                "current_recall_log2_auc": normalized_auc(current_curve),
                "current_forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in current),
                "historical_recall_at_5": statistics.mean(row["recall_at_5"] for row in historical),
                "historical_forbidden_intrusion_rate": statistics.mean(row["forbidden_intrusion"] for row in historical),
            }
        )
    return results, {
        "status": "instrument-development-only",
        "records": len(corpus),
        "queries": len(queries),
        "top_k": TOP_K,
        "update_counts": list(UPDATE_COUNTS),
        "results": summaries,
        "critical_boundary": "B3 uses exact entity-name and ISO-date rules on templated queries; it is not an oracle arm, but its resolver is authored for this synthetic vocabulary and is not held out.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic F1/F2 memory diagnostics")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()

    cases = make_fault_cases()
    corpus = make_interference_corpus()
    queries = make_interference_queries()
    validate_interference(corpus, queries)

    args.dataset.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.dataset / "f1-fault-cases.jsonl", cases)
    write_jsonl(args.dataset / "f2-corpus.jsonl", corpus)
    write_jsonl(args.dataset / "f2-queries.jsonl", queries)

    f1_results, f1_summary = run_fault_localization(cases)
    f2_results, f2_summary = run_interference(corpus, queries)
    artifacts = args.dataset / "artifacts"
    write_jsonl(artifacts / "f1-results.jsonl", f1_results)
    write_json(artifacts / "f1-summary.json", f1_summary)
    write_jsonl(artifacts / "f2-results.jsonl", f2_results)
    write_json(artifacts / "f2-summary.json", f2_summary)
    manifest = {
        "status": "instrument-development-only",
        "generator": "scripts/run_forgetting_benchmark.py",
        "f1_cases": len(cases),
        "f2_records": len(corpus),
        "f2_queries": len(queries),
        "f1_cases_sha256": content_hash(cases),
        "f2_corpus_sha256": content_hash(corpus),
        "f2_queries_sha256": content_hash(queries),
        "backends": ["B0-no-memory", "B1-ripgrep", "B2-sqlite-fts5", "B3-rule-entity-time", "O-gold-evidence"],
        "authority": "authored development instrument; not held out; no architecture promotion",
    }
    write_json(artifacts / "manifest.json", manifest)
    print(json.dumps({"f1": f1_summary, "f2": f2_summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
