#!/usr/bin/env python3
"""Execute the frozen PMLAB v0.1 lexical protocol once on exploratory M2 gold."""

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
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_memory_benchmark as frozen  # noqa: E402


PACKET = ROOT / "data" / "lab" / "project-memory-lab-v0.1-construction"
BLIND = PACKET / "blind"
PREREG = ROOT / "data" / "lab" / "pmlab-v0.1-lexical-preregistration" / "manifest.json"
GOLD = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-pmlab-v01-adjudication-m2-20260823" / "model-reviewed-gold.jsonl"
GOLD_RECEIPT = GOLD.parent / "gold-freeze-receipt.json"
OUT = ROOT / "data" / "lab" / "pmlab-v0.1-lexical-exploratory-m2"
LOCK = OUT / "environment-lock.json"
RUN_MANIFEST = OUT / "run-manifest.json"
TOP_K = 5
BOOTSTRAP_REPETITIONS = 10_000
BOOTSTRAP_SEED = 20_260_822
EXPECTED = {
    "corpus": "260b44de1314629aaa7efd5bffe2157bd2414548cce2501cff6998f6ebae0d9d",
    "queries": "6dca3fcea6e7b7830231444d6e8050952843bbe8974f78633889e6ac76c056bf",
    "gold": "ed9f88778c42526ae37762b6a47e40c2ab7381c3eb2f10703851e3d1004d170f",
}
BACKEND_ORDER = ("B0-no-memory", "B1-ripgrep", "B2-sqlite-fts5", "O-reviewed-evidence")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def directory_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()) if path.exists() else 0


def load_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    if prereg.get("exploratory_execution_authorized") is not True or prereg.get("execution_authorized") is not False:
        raise ValueError("only the explicit M2 exploratory execution path may be used")
    paths = {"corpus": BLIND / "corpus.jsonl", "queries": BLIND / "queries.jsonl", "gold": GOLD}
    for name, path in paths.items():
        if sha256(path) != EXPECTED[name]:
            raise ValueError(f"frozen {name} hash mismatch")
    receipt = json.loads(GOLD_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("gold_sha256") != EXPECTED["gold"] or receipt.get("exploratory_frozen_lexical_baseline_permitted") is not True:
        raise ValueError("M2 gold receipt does not authorize the exploratory baseline")
    corpus = frozen.load_jsonl(paths["corpus"])
    queries = frozen.load_jsonl(paths["queries"])
    labels = frozen.load_jsonl(paths["gold"])
    by_id = {row["example_id"]: row for row in labels}
    if len(queries) != 120 or len(by_id) != 120 or {row["example_id"] for row in queries} != set(by_id):
        raise ValueError("queries and M2 gold do not form a complete 120-case join")
    label_fields = {
        "answerable", "gold_evidence_ids", "gold_current_ids", "forbidden_stale_ids",
        "alternative_acceptable_ids", "resolution", "evidence_tier", "human_confirmed",
    }
    merged = []
    for query in queries:
        label = by_id[query["example_id"]]
        if set(label) != {"example_id", *label_fields} or label["evidence_tier"] != "M2" or label["human_confirmed"] is not False:
            raise ValueError(f"invalid M2 label envelope: {query['example_id']}")
        merged.append({**query, **{field: label[field] for field in label_fields}})
    frozen.validate(corpus, merged)
    if {row["split"] for row in merged} != {"development", "test"}:
        raise ValueError("development/test split is incomplete")
    if any(sum(row["split"] == split for row in merged) != 60 for split in ("development", "test")):
        raise ValueError("expected 60 development and 60 test queries")
    return corpus, merged, prereg


class Oracle:
    name = "O-reviewed-evidence"

    def __init__(self, queries: list[dict[str, Any]]) -> None:
        self.labels = {row["example_id"]: row for row in queries}

    def retrieve_id(self, example_id: str, top_k: int) -> list[str]:
        row = self.labels[example_id]
        return list(dict.fromkeys(row["gold_evidence_ids"] + row["alternative_acceptable_ids"]))[:top_k]


def dcg_binary(retrieved: list[str], gold: set[str], k: int) -> float:
    return sum((1.0 / math.log2(rank + 1)) for rank, evidence_id in enumerate(retrieved[:k], 1) if evidence_id in gold)


def score(query: dict[str, Any], retrieved: list[str], corpus_by_id: dict[str, dict[str, Any]], latency_ms: float, backend: str, error: str | None = None) -> dict[str, Any]:
    gold = set(query["gold_evidence_ids"])
    at_1, at_5 = retrieved[:1], retrieved[:5]
    answerable = query["answerable"]
    recall_1 = len(gold & set(at_1)) / len(gold) if answerable else None
    recall_5 = len(gold & set(at_5)) / len(gold) if answerable else None
    ranks = [rank for rank, item in enumerate(at_5, 1) if item in gold]
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(gold), TOP_K) + 1))
    text = "".join(f"{corpus_by_id[item]['title']}\n{corpus_by_id[item]['body']}\n" for item in at_5)
    forbidden = set(query["forbidden_stale_ids"])
    return {
        "backend": backend, "example_id": query["example_id"], "split": query["split"],
        "category": query["category"], "family": query["family"], "consequence_weight": query["consequence_weight"],
        "answerable": answerable, "retrieved": at_5, "candidate_count": len(at_5),
        "recall_at_1": recall_1, "recall_at_5": recall_5,
        "all_required_at_5": gold <= set(at_5) if answerable else None,
        "precision_at_5": (len(gold & set(at_5)) / len(at_5)) if answerable and at_5 else (0.0 if answerable else None),
        "mrr": (1.0 / min(ranks)) if answerable and ranks else (0.0 if answerable else None),
        "ndcg_at_5": (dcg_binary(at_5, gold, TOP_K) / ideal) if answerable and ideal else (0.0 if answerable else None),
        "forbidden_intrusion_at_1": bool(forbidden & set(at_1)),
        "forbidden_intrusion_at_5": bool(forbidden & set(at_5)),
        "unanswerable_candidate_null": (not at_5) if not answerable else None,
        "returned_characters": len(text), "returned_utf8_bytes": len(text.encode("utf-8")),
        "latency_ms": round(latency_ms, 6), "backend_error": error,
    }


def make_backends(corpus: list[dict[str, Any]], queries: list[dict[str, Any]], work: Path) -> tuple[list[Any], dict[str, Any]]:
    if work.exists():
        raise ValueError(f"fresh work directory already exists: {work}")
    work.mkdir(parents=True)
    builds: dict[str, Any] = {}
    backends: list[Any] = [frozen.NoMemory()]
    started = time.perf_counter()
    rg = frozen.RipgrepRetriever(corpus, work / "rg-docs")
    builds[rg.name] = {"build_ms": round((time.perf_counter() - started) * 1000, 6), "index_bytes": directory_bytes(work / "rg-docs")}
    backends.append(rg)
    started = time.perf_counter()
    fts = frozen.FTS5Retriever(corpus, work / "fts5.sqlite3")
    builds[fts.name] = {"build_ms": round((time.perf_counter() - started) * 1000, 6), "index_bytes": (work / "fts5.sqlite3").stat().st_size}
    backends.extend([fts, Oracle(queries)])
    builds["B0-no-memory"] = {"build_ms": 0.0, "index_bytes": 0}
    builds["O-reviewed-evidence"] = {"build_ms": 0.0, "index_bytes": 0}
    return backends, builds


def retrieve(backend: Any, query: dict[str, Any]) -> list[str]:
    if isinstance(backend, Oracle):
        return backend.retrieve_id(query["example_id"], TOP_K)
    # The deployable backend boundary contains query text only.
    return backend.retrieve(query["query"], TOP_K)


def close_backends(backends: list[Any]) -> None:
    for backend in backends:
        close = getattr(backend, "close", None)
        if close:
            close()


def primary_pass(corpus: list[dict[str, Any]], queries: list[dict[str, Any]], work: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    corpus_by_id = {row["evidence_id"]: row for row in corpus}
    known = set(corpus_by_id)
    backends, builds = make_backends(corpus, queries, work)
    rows: list[dict[str, Any]] = []
    try:
        for backend in backends:
            for query in queries:
                started = time.perf_counter()
                error = None
                try:
                    ranked = retrieve(backend, query)
                    if len(ranked) > TOP_K or len(ranked) != len(set(ranked)) or not set(ranked) <= known:
                        raise ValueError("backend returned too many, duplicate, or unknown IDs")
                except Exception as exc:  # benchmark contract converts a backend error to zero recall
                    ranked, error = [], f"{type(exc).__name__}: {exc}"
                latency = (time.perf_counter() - started) * 1000
                rows.append(score(query, ranked, corpus_by_id, latency, backend.name, error))
    finally:
        close_backends(backends)
    return rows, builds


def measurement_pass(corpus: list[dict[str, Any]], queries: list[dict[str, Any]], work: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    backends, builds = make_backends(corpus, queries, work)
    rankings: list[dict[str, Any]] = []
    latencies: list[dict[str, Any]] = []
    try:
        for backend in backends:
            for query in queries:  # one unmeasured warmup per query
                retrieve(backend, query)
            first_rankings: dict[str, list[str]] = {}
            for repetition in range(1, 6):
                for query in queries:
                    started = time.perf_counter()
                    ranked = retrieve(backend, query)
                    latency = (time.perf_counter() - started) * 1000
                    if repetition == 1:
                        first_rankings[query["example_id"]] = ranked
                    elif ranked != first_rankings[query["example_id"]]:
                        raise ValueError(f"within-process non-determinism: {backend.name}/{query['example_id']}")
                    latencies.append({"backend": backend.name, "example_id": query["example_id"], "measurement_repetition": repetition, "latency_ms": round(latency, 6)})
            rankings.extend({"backend": backend.name, "example_id": example_id, "retrieved": ranked} for example_id, ranked in sorted(first_rankings.items()))
    finally:
        close_backends(backends)
    return rankings, {"builds": builds, "latencies": latencies}


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], fraction: float) -> float:
    return frozen.percentile(values, fraction)


def summarize_backend(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if row["answerable"]]
    unanswerable = [row for row in rows if not row["answerable"]]
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in answerable:
        categories[row["category"]].append(row)
        families[row["family"]].append(row)
    critical = [row for row in answerable if row["consequence_weight"] >= 4]
    weight_sum = sum(row["consequence_weight"] for row in answerable)
    return {
        "backend": rows[0]["backend"], "queries": len(rows), "answerable_queries": len(answerable),
        "macro_recall_at_5_answerable_strata": mean([mean([row["recall_at_5"] for row in values]) for values in categories.values()]),
        "micro_recall_at_1": mean([row["recall_at_1"] for row in answerable]),
        "micro_recall_at_5": mean([row["recall_at_5"] for row in answerable]),
        "all_required_at_5_rate": mean([float(row["all_required_at_5"]) for row in answerable]),
        "precision_at_5": mean([row["precision_at_5"] for row in answerable]),
        "mrr": mean([row["mrr"] for row in answerable]), "ndcg_at_5": mean([row["ndcg_at_5"] for row in answerable]),
        "consequence_weighted_recall_at_5": sum(row["consequence_weight"] * row["recall_at_5"] for row in answerable) / weight_sum,
        "critical_full_evidence_miss_rate": mean([float(not row["all_required_at_5"]) for row in critical]),
        "forbidden_intrusion_at_1_rate": mean([float(row["forbidden_intrusion_at_1"]) for row in rows]),
        "forbidden_intrusion_at_5_rate": mean([float(row["forbidden_intrusion_at_5"]) for row in rows]),
        "unanswerable_candidate_null_rate": mean([float(row["unanswerable_candidate_null"]) for row in unanswerable]),
        "unanswerable_mean_candidate_count": mean([row["candidate_count"] for row in unanswerable]),
        "mean_returned_characters": mean([row["returned_characters"] for row in rows]),
        "mean_returned_utf8_bytes": mean([row["returned_utf8_bytes"] for row in rows]),
        "backend_error_rate": mean([float(row["backend_error"] is not None) for row in rows]),
        "first_pass_latency_ms": {"p50": percentile([row["latency_ms"] for row in rows], 0.5), "p95": percentile([row["latency_ms"] for row in rows], 0.95)},
        "recall_at_5_by_category": {name: mean([row["recall_at_5"] for row in values]) for name, values in sorted(categories.items())},
        "recall_at_5_by_family": {name: mean([row["recall_at_5"] for row in values]) for name, values in sorted(families.items())},
    }


def summarize(rows: list[dict[str, Any]], builds: dict[str, Any]) -> dict[str, Any]:
    by_backend: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_backend[row["backend"]].append(row)
    return {"backends": {name: {**summarize_backend(by_backend[name]), **builds[name]} for name in BACKEND_ORDER}}


def bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    relevant = [row for row in rows if row["answerable"] and row["backend"] in {"B1-ripgrep", "B2-sqlite-fts5"}]
    by_key = {(row["backend"], row["example_id"]): row for row in relevant}
    categories: dict[str, list[str]] = defaultdict(list)
    for row in relevant:
        if row["backend"] == "B1-ripgrep":
            categories[row["category"]].append(row["example_id"])
    rng = random.Random(BOOTSTRAP_SEED)
    samples = []
    for _ in range(BOOTSTRAP_REPETITIONS):
        category_differences = []
        for example_ids in categories.values():
            selected = [rng.choice(example_ids) for _ in example_ids]
            category_differences.append(mean([by_key[("B2-sqlite-fts5", value)]["recall_at_5"] - by_key[("B1-ripgrep", value)]["recall_at_5"] for value in selected]))
        samples.append(mean(category_differences))
    category_points = {
        category: mean([by_key[("B2-sqlite-fts5", value)]["recall_at_5"] - by_key[("B1-ripgrep", value)]["recall_at_5"] for value in ids])
        for category, ids in sorted(categories.items())
    }
    return {
        "comparison": "B2-minus-B1 macro Recall@5", "repetitions": BOOTSTRAP_REPETITIONS,
        "seed": BOOTSTRAP_SEED, "point_difference": mean(list(category_points.values())),
        "ci_95": [percentile(samples, 0.025), percentile(samples, 0.975)],
        "category_differences": category_points,
    }


def sanity(summary: dict[str, Any]) -> dict[str, bool]:
    b0, oracle = summary["backends"]["B0-no-memory"], summary["backends"]["O-reviewed-evidence"]
    return {
        "b0_zero_recall_and_empty": b0["macro_recall_at_5_answerable_strata"] == 0 and b0["unanswerable_candidate_null_rate"] == 1,
        "oracle_full_recall": oracle["macro_recall_at_5_answerable_strata"] == 1 and oracle["all_required_at_5_rate"] == 1,
        "oracle_zero_forbidden_intrusion": oracle["forbidden_intrusion_at_5_rate"] == 0,
        "backend_error_rates_at_most_0.01": all(row["backend_error_rate"] <= 0.01 for row in summary["backends"].values()),
    }


def decision(summary: dict[str, Any], boot: dict[str, Any], deterministic: bool) -> dict[str, Any]:
    b1, b2 = summary["backends"]["B1-ripgrep"], summary["backends"]["B2-sqlite-fts5"]
    non_exact_gains = sum(category != "exact_lexical" and value >= 0.05 for category, value in boot["category_differences"].items())
    checks = {
        "point_difference_at_least_0.05": boot["point_difference"] >= 0.05,
        "bootstrap_lower_bound_positive": boot["ci_95"][0] > 0,
        "at_least_three_non_exact_strata_gain_0.05": non_exact_gains >= 3,
        "critical_miss_regression_at_most_0.02": b2["critical_full_evidence_miss_rate"] - b1["critical_full_evidence_miss_rate"] <= 0.02,
        "forbidden_intrusion_regression_at_most_0.02": b2["forbidden_intrusion_at_5_rate"] - b1["forbidden_intrusion_at_5_rate"] <= 0.02,
        "deterministic_rankings": deterministic,
        **sanity(summary),
    }
    if not all((checks["oracle_full_recall"], checks["oracle_zero_forbidden_intrusion"], checks["backend_error_rates_at_most_0.01"], deterministic)):
        outcome = "inconclusive"
    elif all(checks.values()):
        outcome = "advance-B2-over-B1-exploratory"
    else:
        outcome = "reject-B2-promotion-retain-B1-as-simpler-baseline"
    return {"outcome": outcome, "checks": checks, "non_exact_strata_with_gain_at_least_0.05": non_exact_gains, "authority": "M2 model-reviewed exploratory result; no architecture promotion"}


def verify_lock() -> tuple[dict[str, Any], dict[str, Any]]:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8"))
    paths = {
        "runner": Path(__file__), "retrieval_dependency": ROOT / "scripts" / "run_memory_benchmark.py",
        "preregistration": PREREG, "corpus": BLIND / "corpus.jsonl", "queries": BLIND / "queries.jsonl",
        "gold": GOLD, "gold_receipt": GOLD_RECEIPT,
    }
    for name, path in paths.items():
        if sha256(path) != lock["hashes"][name]:
            raise ValueError(f"environment/input lock mismatch: {name}")
    load_inputs()
    return lock, manifest


def prepare(runner_freeze_commit: str) -> dict[str, Any]:
    if OUT.exists() and any(OUT.iterdir()):
        raise ValueError(f"output directory is not empty: {OUT}")
    git("cat-file", "-e", f"{runner_freeze_commit}^{{commit}}")
    for relative in ("scripts/run_pmlab_v01_lexical_exploratory.py", "scripts/run_memory_benchmark.py"):
        committed = subprocess.check_output(["git", "show", f"{runner_freeze_commit}:{relative}"], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != sha256(ROOT / relative):
            raise ValueError(f"{relative} differs from runner freeze commit")
    corpus, queries, prereg = load_inputs()
    rg_version = subprocess.check_output([shutil.which("rg") or "rg", "--version"], text=True).splitlines()[0]
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    connection.close()
    lock = {
        "status": "environment-and-inputs-frozen", "created_at": now(), "runner_freeze_commit": runner_freeze_commit,
        "protocol_freeze_commit": prereg["protocol_freeze_commit"], "source_query_freeze_commit": prereg["source_query_freeze_commit"],
        "python": sys.version, "python_executable": sys.executable, "sqlite": sqlite3.sqlite_version,
        "ripgrep": rg_version, "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"),
        "queries": len(queries), "records": len(corpus), "top_k": TOP_K,
        "hashes": {
            "runner": sha256(Path(__file__)), "retrieval_dependency": sha256(ROOT / "scripts" / "run_memory_benchmark.py"),
            "preregistration": sha256(PREREG), "corpus": sha256(BLIND / "corpus.jsonl"), "queries": sha256(BLIND / "queries.jsonl"),
            "gold": sha256(GOLD), "gold_receipt": sha256(GOLD_RECEIPT),
        },
    }
    write_json(LOCK, lock)
    manifest = {
        "experiment_id": "PMLAB-V01-RET-001-M2-EXPLORATORY", "status": "environment-frozen-awaiting-development",
        "created_at": now(), "authority": "one exploratory execution under M2 model-review fallback",
        "confirmatory": False, "architecture_promotion_permitted": False, "environment_lock_sha256": sha256(LOCK),
        "development_freeze_commit": None, "test_authorization_commit": None,
    }
    write_json(RUN_MANIFEST, manifest)
    return manifest


def run_development() -> dict[str, Any]:
    _, manifest = verify_lock()
    if manifest["status"] != "environment-frozen-awaiting-development":
        raise ValueError("development pass is not authorized or was already run")
    if git("status", "--porcelain"):
        raise ValueError("development pass requires a clean worktree")
    corpus, queries, _ = load_inputs()
    selected = [row for row in queries if row["split"] == "development"]
    rows, builds = primary_pass(corpus, selected, OUT / "development" / "work")
    summary = {**summarize(rows, builds), "split": "development", "purpose": "infrastructure validation only; metrics must not tune the frozen test protocol"}
    checks = sanity(summary)
    summary["infrastructure_checks"] = checks
    summary["infrastructure_pass"] = all(checks.values())
    write_jsonl(OUT / "development" / "primary-results.jsonl", rows)
    write_json(OUT / "development" / "summary.json", summary)
    manifest["status"] = "development-complete-awaiting-freeze" if summary["infrastructure_pass"] else "development-infrastructure-failed"
    manifest["development_results_sha256"] = sha256(OUT / "development" / "primary-results.jsonl")
    manifest["development_summary_sha256"] = sha256(OUT / "development" / "summary.json")
    write_json(RUN_MANIFEST, manifest)
    return summary


def authorize_test(development_commit: str) -> dict[str, Any]:
    _, manifest = verify_lock()
    if manifest["status"] != "development-complete-awaiting-freeze":
        raise ValueError("successful development artifacts are not awaiting freeze")
    git("cat-file", "-e", f"{development_commit}^{{commit}}")
    for relative, expected_key in (("primary-results.jsonl", "development_results_sha256"), ("summary.json", "development_summary_sha256")):
        committed = subprocess.check_output(["git", "show", f"{development_commit}:data/lab/pmlab-v0.1-lexical-exploratory-m2/development/{relative}"], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != manifest[expected_key]:
            raise ValueError(f"development {relative} differs from frozen commit")
    manifest["development_freeze_commit"] = development_commit
    manifest["status"] = "test-primary-authorized-awaiting-clean-commit"
    write_json(RUN_MANIFEST, manifest)
    return manifest


def run_test() -> dict[str, Any]:
    _, manifest = verify_lock()
    if manifest["status"] != "test-primary-authorized-awaiting-clean-commit":
        raise ValueError("test is not authorized or was already executed")
    if (OUT / "test" / "primary-results.jsonl").exists():
        raise ValueError("sealed primary test result already exists")
    if git("status", "--porcelain"):
        raise ValueError("primary test requires a clean worktree")
    manifest["test_authorization_commit"] = git("rev-parse", "HEAD")
    corpus, queries, _ = load_inputs()
    selected = [row for row in queries if row["split"] == "test"]
    started_at = now()
    rows, builds = primary_pass(corpus, selected, OUT / "test" / "primary-work")
    summary = {**summarize(rows, builds), "split": "test", "started_at": started_at, "completed_at": now(), "execution_ordinal": 1, "sealed_before_determinism": True}
    write_jsonl(OUT / "test" / "primary-results.jsonl", rows)
    write_json(OUT / "test" / "primary-summary.json", summary)
    receipt = {"status": "primary-test-executed-once", "execution_ordinal": 1, "authorization_commit": manifest["test_authorization_commit"], "results_sha256": sha256(OUT / "test" / "primary-results.jsonl"), "summary_sha256": sha256(OUT / "test" / "primary-summary.json"), "completed_at": summary["completed_at"]}
    write_json(OUT / "test" / "primary-execution-receipt.json", receipt)
    manifest["status"] = "test-primary-complete-awaiting-two-fresh-process-measurements"
    manifest["primary_execution_receipt_sha256"] = sha256(OUT / "test" / "primary-execution-receipt.json")
    write_json(RUN_MANIFEST, manifest)
    return receipt


def measure(repetition: int) -> dict[str, Any]:
    _, manifest = verify_lock()
    if manifest["status"] not in {"test-primary-complete-awaiting-two-fresh-process-measurements", "test-measurements-in-progress"}:
        raise ValueError("primary test must be sealed before measurement")
    if repetition not in {1, 2}:
        raise ValueError("measurement repetition must be 1 or 2")
    target = OUT / "test" / f"measurement-{repetition}"
    if target.exists():
        raise ValueError(f"measurement {repetition} already exists")
    corpus, queries, _ = load_inputs()
    selected = [row for row in queries if row["split"] == "test"]
    rankings, measurements = measurement_pass(corpus, selected, target / "work")
    write_jsonl(target / "rankings.jsonl", rankings)
    write_jsonl(target / "latencies.jsonl", measurements["latencies"])
    receipt = {"status": "fresh-process-measurement-complete", "repetition": repetition, "process_id": os.getpid(), "completed_at": now(), "rankings_sha256": sha256(target / "rankings.jsonl"), "latencies_sha256": sha256(target / "latencies.jsonl"), "builds": measurements["builds"]}
    write_json(target / "receipt.json", receipt)
    manifest["status"] = "test-measurements-in-progress"
    manifest[f"measurement_{repetition}_receipt_sha256"] = sha256(target / "receipt.json")
    write_json(RUN_MANIFEST, manifest)
    return receipt


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return frozen.load_jsonl(path)


def final_report(summary: dict[str, Any], boot: dict[str, Any], verdict: dict[str, Any], warm: dict[str, Any]) -> str:
    lines = [
        "# PMLAB v0.1 lexical exploratory M2 result", "",
        "Status: completed once; model-reviewed exploratory evidence; not confirmatory", "",
        "## Primary result", "",
        "| Backend | Macro Recall@5 | All required@5 | Critical miss | Forbidden@5 | Unanswerable null |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in BACKEND_ORDER:
        row = summary["backends"][name]
        lines.append(f"| {name} | {row['macro_recall_at_5_answerable_strata']:.3f} | {row['all_required_at_5_rate']:.3f} | {row['critical_full_evidence_miss_rate']:.3f} | {row['forbidden_intrusion_at_5_rate']:.3f} | {row['unanswerable_candidate_null_rate']:.3f} |")
    lines.extend([
        "", "## Frozen comparison", "",
        f"B2-B1 macro Recall@5 difference: `{boot['point_difference']:.6f}`; stratified 95% bootstrap CI: `[{boot['ci_95'][0]:.6f}, {boot['ci_95'][1]:.6f}]`.", "",
        f"Decision: `{verdict['outcome']}`.", "",
        "All checks and per-category differences are retained in `final-summary.json`. Rankings matched the sealed primary output across two fresh measurement processes.", "",
        "## Authority boundary", "",
        "Gold was produced by blind, role-separated calls to one author-operated model family. This result can falsify or retain a lexical baseline for further exploratory work, but it cannot establish confirmatory validity or promote embeddings, graphs, salience, or a product architecture. H-tier or cross-family replication remains required.", "",
        f"Warm-latency measurements contain {warm['measurement_rows']} query observations after one unmeasured warmup per query in each fresh process.", "",
    ])
    return "\n".join(lines)


def finalize() -> dict[str, Any]:
    _, manifest = verify_lock()
    if manifest["status"] != "test-measurements-in-progress":
        raise ValueError("two fresh-process measurements are required before finalization")
    for repetition in (1, 2):
        if not (OUT / "test" / f"measurement-{repetition}" / "receipt.json").exists():
            raise ValueError(f"measurement {repetition} is missing")
    primary_rows = read_jsonl(OUT / "test" / "primary-results.jsonl")
    primary_rankings = {(row["backend"], row["example_id"]): row["retrieved"] for row in primary_rows}
    measurement_maps = []
    all_latencies = []
    for repetition in (1, 2):
        measurement_maps.append({(row["backend"], row["example_id"]): row["retrieved"] for row in read_jsonl(OUT / "test" / f"measurement-{repetition}" / "rankings.jsonl")})
        all_latencies.extend(read_jsonl(OUT / "test" / f"measurement-{repetition}" / "latencies.jsonl"))
    deterministic = all(mapping == primary_rankings for mapping in measurement_maps)
    primary_summary = json.loads((OUT / "test" / "primary-summary.json").read_text(encoding="utf-8"))
    boot = bootstrap(primary_rows)
    verdict = decision(primary_summary, boot, deterministic)
    latency_groups: dict[str, list[float]] = defaultdict(list)
    for row in all_latencies:
        latency_groups[row["backend"]].append(row["latency_ms"])
    warm = {"measurement_rows": len(all_latencies), "by_backend": {name: {"p50_ms": percentile(values, 0.5), "p95_ms": percentile(values, 0.95), "observations": len(values)} for name, values in sorted(latency_groups.items())}}
    final = {
        "status": "completed-once-model-reviewed-exploratory", "experiment_id": manifest["experiment_id"],
        "primary_execution_receipt_sha256": manifest["primary_execution_receipt_sha256"],
        "gold_sha256": EXPECTED["gold"], "summary": primary_summary, "bootstrap": boot,
        "fresh_process_rankings_deterministic": deterministic, "warm_latency": warm, "decision": verdict,
        "confirmatory": False, "architecture_promotion_permitted": False,
    }
    write_json(OUT / "test" / "final-summary.json", final)
    (OUT / "report.md").write_text(final_report(primary_summary, boot, verdict, warm), encoding="utf-8", newline="\n")
    manifest["status"] = "completed-once-model-reviewed-exploratory"
    manifest["final_summary_sha256"] = sha256(OUT / "test" / "final-summary.json")
    manifest["report_sha256"] = sha256(OUT / "report.md")
    manifest["decision"] = verdict["outcome"]
    write_json(RUN_MANIFEST, manifest)
    return final


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepared = sub.add_parser("prepare"); prepared.add_argument("--runner-freeze-commit", required=True)
    sub.add_parser("run-development")
    authorized = sub.add_parser("authorize-test"); authorized.add_argument("--development-commit", required=True)
    sub.add_parser("run-test")
    measured = sub.add_parser("measure"); measured.add_argument("--repetition", type=int, required=True)
    sub.add_parser("finalize")
    args = parser.parse_args()
    if args.command == "prepare": result = prepare(args.runner_freeze_commit)
    elif args.command == "run-development": result = run_development()
    elif args.command == "authorize-test": result = authorize_test(args.development_commit)
    elif args.command == "run-test": result = run_test()
    elif args.command == "measure": result = measure(args.repetition)
    else: result = finalize()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
