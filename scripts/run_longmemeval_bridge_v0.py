#!/usr/bin/env python3
"""Run the frozen content-free LongMemEval bridge v0 lexical transfer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_memory_benchmark as lexical  # noqa: E402


BRIDGE = ROOT / "data" / "lab" / "longmemeval-bridge-v0"
OUT = BRIDGE / "execution"
SOURCE = ROOT / "external" / "datasets" / "longmemeval-cleaned-98d7416c24c7" / "longmemeval_s_cleaned.json"
SELECTION = BRIDGE / "selection.jsonl"
PROTOCOL = BRIDGE / "execution-protocol.json"
LOCK = OUT / "environment-lock.json"
SOURCE_BYTES = 277_383_467
SOURCE_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
SELECTION_SHA256 = "6eb629bc0f9d1938fa15247092f2f69e096dc92de59c92881d0478972aad6483"
PROTOCOL_SHA256 = "5d9bb7e99b9f41d6bf3fd80dd78e331b6ead5c4162fc0ebec6dd6d4af2b3f125"
PROTOCOL_FREEZE_COMMIT = "87b32e3"
QUESTION_TYPES = (
    "single-session-user",
    "single-session-assistant",
    "single-session-preference",
    "multi-session",
    "knowledge-update",
    "temporal-reasoning",
)
BACKENDS = ("B0-no-memory", "B1-ripgrep", "B2-sqlite-fts5", "O-answer-session-control")
TOP_K = 5
BOOTSTRAP_REPETITIONS = 10_000
BOOTSTRAP_SEED = 20_260_823


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def tool_versions() -> dict[str, Any]:
    rg = shutil.which("rg")
    if not rg:
        raise RuntimeError("ripgrep is required")
    rg_version = subprocess.check_output([rg, "--version"], text=True).splitlines()[0]
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "sqlite": sqlite3.sqlite_version,
        "ripgrep": rg_version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
    }


def validate_frozen_files() -> None:
    if not SOURCE.exists() or SOURCE.stat().st_size != SOURCE_BYTES or sha256_file(SOURCE) != SOURCE_SHA256:
        raise ValueError("LongMemEval source bytes differ from the frozen source")
    if sha256_file(SELECTION) != SELECTION_SHA256:
        raise ValueError("bridge selection differs from the frozen selection")
    if sha256_file(PROTOCOL) != PROTOCOL_SHA256:
        raise ValueError("bridge execution protocol differs from its pre-output freeze")
    subprocess.run(["git", "merge-base", "--is-ancestor", PROTOCOL_FREEZE_COMMIT, "HEAD"], cwd=ROOT, check=True)


def load_selected() -> list[dict[str, Any]]:
    validate_frozen_files()
    selected = lexical.load_jsonl(SELECTION)
    selected_by_id = {row["question_id"]: row for row in selected}
    if len(selected) != 36 or len(selected_by_id) != 36:
        raise ValueError("selection must contain 36 unique question IDs")
    with SOURCE.open(encoding="utf-8") as handle:
        source_rows = json.load(handle)
    rows = [row for row in source_rows if row["question_id"] in selected_by_id]
    if len(rows) != 36:
        raise ValueError("not all selected IDs exist in the source")
    rows.sort(key=lambda row: row["question_id"])
    for row in rows:
        selection = selected_by_id[row["question_id"]]
        answerable = not row["question_id"].endswith("_abs")
        if selection["answerable"] != answerable or selection["question_type"] != row["question_type"]:
            raise ValueError(f"selection/source mismatch: {row['question_id']}")
        if len(row["haystack_session_ids"]) != len(row["haystack_sessions"]):
            raise ValueError(f"session arrays differ: {row['question_id']}")
        known = set(row["haystack_session_ids"])
        if not set(row["answer_session_ids"]) <= known:
            raise ValueError(f"answer session missing from haystack: {row['question_id']}")
        if answerable and not row["answer_session_ids"]:
            raise ValueError(f"answerable case lacks retrieval gold: {row['question_id']}")
    return rows


def adapt(row: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, str], set[str], set[str]]:
    records: list[dict[str, str]] = []
    source_to_opaque: dict[str, str] = {}
    for index, (source_id, turns) in enumerate(zip(row["haystack_session_ids"], row["haystack_sessions"], strict=True)):
        opaque = f"S{index:03d}"
        source_to_opaque[source_id] = opaque
        body = "\n".join(f"{turn['role']}: {turn['content']}" for turn in turns)
        records.append({"evidence_id": opaque, "title": "", "body": body})
    mapped = {source_to_opaque[item] for item in row["answer_session_ids"]}
    gold = mapped if not row["question_id"].endswith("_abs") else set()
    near_miss = mapped if row["question_id"].endswith("_abs") else set()
    return records, source_to_opaque, gold, near_miss


class Oracle:
    name = "O-answer-session-control"

    def __init__(self, gold: set[str]) -> None:
        self.gold = sorted(gold)

    def retrieve(self, query: str, top_k: int) -> list[str]:
        del query
        return self.gold[:top_k]


def make_backend(name: str, records: list[dict[str, str]], gold: set[str], work: Path) -> tuple[Any, int]:
    if name == "B0-no-memory":
        return lexical.NoMemory(), 0
    if name == "B1-ripgrep":
        backend = lexical.RipgrepRetriever(records, work / "rg")
        size = sum(item.stat().st_size for item in (work / "rg").rglob("*") if item.is_file())
        return backend, size
    if name == "B2-sqlite-fts5":
        database = work / "fts.sqlite3"
        backend = lexical.FTS5Retriever(records, database)
        return backend, database.stat().st_size
    if name == "O-answer-session-control":
        return Oracle(gold), 0
    raise ValueError(name)


def close_backend(backend: Any) -> None:
    close = getattr(backend, "close", None)
    if close:
        close()


def dcg(retrieved: list[str], gold: set[str]) -> float:
    return sum(1.0 / math.log2(rank + 1) for rank, item in enumerate(retrieved[:TOP_K], 1) if item in gold)


def score_case(
    source: dict[str, Any],
    records: list[dict[str, str]],
    backend: str,
    retrieved: list[str],
    gold: set[str],
    near_miss: set[str],
    latency_ms: float,
    build_ms: float,
    index_bytes: int,
    error: str | None,
) -> dict[str, Any]:
    answerable = bool(gold)
    at_1, at_5 = retrieved[:1], retrieved[:TOP_K]
    positions = [rank for rank, item in enumerate(at_5, 1) if item in gold]
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(gold), TOP_K) + 1))
    by_id = {record["evidence_id"]: record for record in records}
    returned = "".join(by_id[item]["body"] for item in at_5)
    return {
        "question_id": source["question_id"],
        "question_type": source["question_type"],
        "answerable": answerable,
        "backend": backend,
        "required_session_count": len(gold) if answerable else None,
        "candidate_count": len(at_5),
        "ranking_sha256": sha256_json(at_5),
        "recall_at_1": len(set(at_1) & gold) / len(gold) if answerable else None,
        "recall_at_5": len(set(at_5) & gold) / len(gold) if answerable else None,
        "all_required_at_5": gold <= set(at_5) if answerable else None,
        "mrr": 1.0 / min(positions) if answerable and positions else (0.0 if answerable else None),
        "ndcg_at_5": dcg(at_5, gold) / ideal if answerable and ideal else (0.0 if answerable else None),
        "candidate_null": not at_5 if not answerable else None,
        "near_miss_intrusion_at_1": bool(set(at_1) & near_miss) if not answerable else None,
        "near_miss_intrusion_at_5": bool(set(at_5) & near_miss) if not answerable else None,
        "returned_characters": len(returned),
        "returned_utf8_bytes": len(returned.encode("utf-8")),
        "latency_ms": round(latency_ms, 6),
        "build_ms": round(build_ms, 6),
        "index_bytes": index_bytes,
        "backend_error": error,
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], fraction: float) -> float:
    return lexical.percentile(values, fraction)


def summarize_backend(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if row["answerable"]]
    abstention = [row for row in rows if not row["answerable"]]
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in answerable:
        by_type[row["question_type"]].append(row)
    per_type = {kind: mean([row["recall_at_5"] for row in by_type[kind]]) for kind in QUESTION_TYPES}
    total_gold = sum(row["required_session_count"] for row in answerable)
    total_found = sum(row["recall_at_5"] * row["required_session_count"] for row in answerable)
    return {
        "backend": rows[0]["backend"],
        "cases": len(rows),
        "answerable_cases": len(answerable),
        "abstention_cases": len(abstention),
        "macro_recall_at_1": mean([row["recall_at_1"] for row in answerable]),
        "macro_recall_at_5": mean(list(per_type.values())),
        "query_mean_recall_at_5": mean([row["recall_at_5"] for row in answerable]),
        "micro_recall_at_5": total_found / total_gold,
        "all_required_at_5_rate": mean([float(row["all_required_at_5"]) for row in answerable]),
        "mean_reciprocal_rank": mean([row["mrr"] for row in answerable]),
        "mean_ndcg_at_5": mean([row["ndcg_at_5"] for row in answerable]),
        "recall_at_5_by_question_type": per_type,
        "abstention_candidate_null_rate": mean([float(row["candidate_null"]) for row in abstention]),
        "abstention_near_miss_intrusion_at_1_rate": mean([float(row["near_miss_intrusion_at_1"]) for row in abstention]),
        "abstention_near_miss_intrusion_at_5_rate": mean([float(row["near_miss_intrusion_at_5"]) for row in abstention]),
        "mean_candidate_count": mean([row["candidate_count"] for row in rows]),
        "first_pass_latency_p50_ms": percentile([row["latency_ms"] for row in rows], 0.5),
        "first_pass_latency_p95_ms": percentile([row["latency_ms"] for row in rows], 0.95),
        "mean_build_ms_per_case": mean([row["build_ms"] for row in rows]),
        "mean_index_bytes_per_case": mean([row["index_bytes"] for row in rows]),
        "backend_errors": sum(row["backend_error"] is not None for row in rows),
    }


def bootstrap_difference(rows: list[dict[str, Any]]) -> dict[str, float]:
    b1 = {row["question_id"]: row for row in rows if row["backend"] == "B1-ripgrep" and row["answerable"]}
    b2 = {row["question_id"]: row for row in rows if row["backend"] == "B2-sqlite-fts5" and row["answerable"]}
    strata: dict[str, list[str]] = defaultdict(list)
    for question_id, row in b1.items():
        strata[row["question_type"]].append(question_id)
    observed = mean([mean([b2[q]["recall_at_5"] - b1[q]["recall_at_5"] for q in strata[kind]]) for kind in QUESTION_TYPES])
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPETITIONS):
        differences = []
        for kind in QUESTION_TYPES:
            ids = strata[kind]
            picked = [ids[rng.randrange(len(ids))] for _ in ids]
            differences.append(mean([b2[q]["recall_at_5"] - b1[q]["recall_at_5"] for q in picked]))
        samples.append(mean(differences))
    return {
        "b2_minus_b1": observed,
        "ci95_low": percentile(samples, 0.025),
        "ci95_high": percentile(samples, 0.975),
    }


def prepare() -> None:
    validate_frozen_files()
    dirty = git("status", "--porcelain")
    if dirty:
        raise ValueError("commit runner and tests before freezing the environment")
    lock = {
        "created_at": now(),
        "status": "environment-frozen-before-bridge-output",
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "runner_commit": git("rev-parse", "HEAD"),
        "runner_sha256": sha256_file(Path(__file__)),
        "protocol_sha256": sha256_file(PROTOCOL),
        "selection_sha256": sha256_file(SELECTION),
        "source_sha256": sha256_file(SOURCE),
        "tools": tool_versions(),
    }
    write_json(LOCK, lock)
    print(json.dumps(lock, indent=2))


def validate_lock() -> dict[str, Any]:
    if not LOCK.exists():
        raise ValueError("environment lock is missing; run --stage prepare after committing the runner")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if lock["runner_sha256"] != sha256_file(Path(__file__)):
        raise ValueError("runner changed after environment freeze")
    if lock["protocol_sha256"] != PROTOCOL_SHA256 or lock["selection_sha256"] != SELECTION_SHA256:
        raise ValueError("frozen protocol or selection mismatch")
    if lock["source_sha256"] != SOURCE_SHA256 or lock["tools"] != tool_versions():
        raise ValueError("source or execution environment changed after freeze")
    return lock


def primary() -> None:
    validate_lock()
    sources = load_selected()
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="longmemeval-bridge-") as temporary:
        base = Path(temporary)
        for source in sources:
            records, _, gold, near_miss = adapt(source)
            for backend_name in BACKENDS:
                work = base / source["question_id"] / backend_name
                started = time.perf_counter()
                backend, index_bytes = make_backend(backend_name, records, gold, work)
                build_ms = (time.perf_counter() - started) * 1000
                error = None
                started = time.perf_counter()
                try:
                    retrieved = backend.retrieve(source["question"], TOP_K)
                    known = {record["evidence_id"] for record in records}
                    if len(retrieved) > TOP_K or len(retrieved) != len(set(retrieved)) or not set(retrieved) <= known:
                        raise ValueError("backend returned too many, duplicate, or unknown IDs")
                except Exception as exc:
                    retrieved, error = [], f"{type(exc).__name__}: {exc}"
                latency_ms = (time.perf_counter() - started) * 1000
                close_backend(backend)
                rows.append(score_case(source, records, backend_name, retrieved, gold, near_miss, latency_ms, build_ms, index_bytes, error))
    rows.sort(key=lambda row: (row["backend"], row["question_id"]))
    results_path = OUT / "primary-results.jsonl"
    write_jsonl(results_path, rows)
    summaries = {backend: summarize_backend([row for row in rows if row["backend"] == backend]) for backend in BACKENDS}
    write_json(OUT / "primary-summary.json", {
        "created_at": now(),
        "status": "primary-complete-awaiting-fresh-process-determinism",
        "cases": 36,
        "content_free": True,
        "results_sha256": sha256_file(results_path),
        "backends": summaries,
        "paired_bootstrap": bootstrap_difference(rows),
    })
    print(json.dumps({"results": str(results_path), "sha256": sha256_file(results_path)}, indent=2))


def measurement(label: str) -> None:
    if label not in {"a", "b"}:
        raise ValueError("measurement label must be a or b")
    validate_lock()
    sources = load_selected()
    output: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"longmemeval-measurement-{label}-") as temporary:
        base = Path(temporary)
        for source in sources:
            records, _, gold, _ = adapt(source)
            for backend_name in ("B1-ripgrep", "B2-sqlite-fts5"):
                backend, _ = make_backend(backend_name, records, gold, base / source["question_id"] / backend_name)
                try:
                    backend.retrieve(source["question"], TOP_K)
                    rankings: list[list[str]] = []
                    latencies: list[float] = []
                    for _ in range(5):
                        started = time.perf_counter()
                        rankings.append(backend.retrieve(source["question"], TOP_K))
                        latencies.append((time.perf_counter() - started) * 1000)
                    if any(ranking != rankings[0] for ranking in rankings[1:]):
                        raise ValueError(f"within-process ranking drift: {backend_name}/{source['question_id']}")
                    output.append({
                        "backend": backend_name,
                        "question_id": source["question_id"],
                        "ranking_sha256": sha256_json(rankings[0]),
                        "candidate_count": len(rankings[0]),
                        "warm_latency_p50_ms": percentile(latencies, 0.5),
                        "warm_latency_p95_ms": percentile(latencies, 0.95),
                    })
                finally:
                    close_backend(backend)
    output.sort(key=lambda row: (row["backend"], row["question_id"]))
    path = OUT / f"measurement-{label}.jsonl"
    write_jsonl(path, output)
    print(json.dumps({"measurement": label, "rows": len(output), "sha256": sha256_file(path)}, indent=2))


def finalize() -> None:
    validate_lock()
    primary_path = OUT / "primary-results.jsonl"
    summary_path = OUT / "primary-summary.json"
    paths = [OUT / "measurement-a.jsonl", OUT / "measurement-b.jsonl"]
    if not primary_path.exists() or not summary_path.exists() or not all(path.exists() for path in paths):
        raise ValueError("primary and both fresh-process measurements are required")
    rows = lexical.load_jsonl(primary_path)
    measurements = [lexical.load_jsonl(path) for path in paths]
    comparable = lambda items: [(row["backend"], row["question_id"], row["ranking_sha256"], row["candidate_count"]) for row in items]
    deterministic = comparable(measurements[0]) == comparable(measurements[1])
    primary_rankings = sorted(
        (row["backend"], row["question_id"], row["ranking_sha256"], row["candidate_count"])
        for row in rows if row["backend"] in {"B1-ripgrep", "B2-sqlite-fts5"}
    )
    deterministic = deterministic and primary_rankings == comparable(measurements[0])
    summaries = {backend: summarize_backend([row for row in rows if row["backend"] == backend]) for backend in BACKENDS}
    difference = bootstrap_difference(rows)
    per_type_diff = {
        kind: summaries["B2-sqlite-fts5"]["recall_at_5_by_question_type"][kind]
        - summaries["B1-ripgrep"]["recall_at_5_by_question_type"][kind]
        for kind in QUESTION_TYPES
    }
    errors = summaries["B1-ripgrep"]["backend_errors"] + summaries["B2-sqlite-fts5"]["backend_errors"]
    controls = {
        "B0_zero_recall_and_empty": summaries["B0-no-memory"]["macro_recall_at_5"] == 0 and summaries["B0-no-memory"]["mean_candidate_count"] == 0,
        "oracle_perfect_answerable": summaries["O-answer-session-control"]["macro_recall_at_5"] == 1 and summaries["O-answer-session-control"]["all_required_at_5_rate"] == 1,
        "oracle_empty_abstention": summaries["O-answer-session-control"]["abstention_candidate_null_rate"] == 1,
        "fresh_process_determinism": deterministic,
        "no_backend_errors": errors == 0,
    }
    if not all(controls.values()):
        decision = "inconclusive-control-failure"
    elif difference["b2_minus_b1"] <= 0 or min(per_type_diff.values()) < -0.10:
        decision = "fails-sparse-transfer"
    elif difference["ci95_low"] >= 0:
        decision = "supports-sparse-transfer"
    else:
        decision = "inconclusive-uncertainty"
    warm = {}
    for backend in ("B1-ripgrep", "B2-sqlite-fts5"):
        selected = [row for row in measurements[0] if row["backend"] == backend]
        warm[backend] = {
            "query_p50_of_case_p50_ms": percentile([row["warm_latency_p50_ms"] for row in selected], 0.5),
            "query_p95_of_case_p95_ms": percentile([row["warm_latency_p95_ms"] for row in selected], 0.95),
        }
    final = {
        "created_at": now(),
        "status": "complete-public-transfer-diagnostic",
        "decision": decision,
        "architecture_effect": "none",
        "content_free": True,
        "primary_results_sha256": sha256_file(primary_path),
        "measurement_sha256": {path.stem: sha256_file(path) for path in paths},
        "controls": controls,
        "paired_bootstrap": difference,
        "b2_minus_b1_by_question_type": per_type_diff,
        "backends": summaries,
        "warm_latency": warm,
        "limitations": [
            "public, potentially contaminated transfer set",
            "30 answerable and six abstention cases provide low statistical power",
            "synthetic/compiled histories differ from natural project memory",
            "retrieval-only evaluation cannot establish answer correctness or abstention correctness",
            "session dates are deliberately excluded by the frozen metadata-blind adapter",
        ],
    }
    write_json(OUT / "final-summary.json", final)
    report = f"""# LongMemEval bridge v0 lexical transfer result

Status: complete public transfer diagnostic

Decision: `{decision}`. This result has no architecture-promotion authority and is never pooled with PMLAB.

## Primary comparison

- B1 macro Recall@5: {summaries['B1-ripgrep']['macro_recall_at_5']:.6f}
- B2 macro Recall@5: {summaries['B2-sqlite-fts5']['macro_recall_at_5']:.6f}
- paired B2-B1: {difference['b2_minus_b1']:+.6f}
- stratified 95% bootstrap interval: [{difference['ci95_low']:.6f}, {difference['ci95_high']:.6f}]
- deterministic across primary and two fresh processes: {str(deterministic).lower()}

## Abstention boundary

B1 candidate-null was {summaries['B1-ripgrep']['abstention_candidate_null_rate']:.3f} and B2 candidate-null was {summaries['B2-sqlite-fts5']['abstention_candidate_null_rate']:.3f}. These are candidate-generation diagnostics, not correct-answer abstention. Near-miss intrusion at five was {summaries['B1-ripgrep']['abstention_near_miss_intrusion_at_5_rate']:.3f} for B1 and {summaries['B2-sqlite-fts5']['abstention_near_miss_intrusion_at_5_rate']:.3f} for B2.

## Interpretation boundary

The bridge is public, small, and potentially contaminated. It tests whether an unchanged sparse lexical adapter transfers to session retrieval. It does not test a reader, completeness controller, durable-memory lifecycle, or a final architecture. No source question, answer, conversation, raw session ID, or evidence label is present in tracked execution artifacts.
"""
    (OUT / "report.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({"decision": decision, "summary": str(OUT / "final-summary.json")}, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("prepare", "primary", "measurement", "finalize"))
    parser.add_argument("--label", choices=("a", "b"))
    args = parser.parse_args()
    if args.stage == "prepare":
        prepare()
    elif args.stage == "primary":
        primary()
    elif args.stage == "measurement":
        measurement(args.label or "")
    else:
        finalize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
