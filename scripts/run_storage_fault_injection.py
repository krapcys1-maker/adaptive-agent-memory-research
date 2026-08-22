#!/usr/bin/env python3
"""Disposable same-device filesystem fault-injection harness.

The harness exercises real files only below a freshly created system temporary
directory. Primary and replica paths are logical replicas on Disk 0 in the
current environment; it never emits PHYSICAL_LOSS_CONFIRMED.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from scripts.run_fault_probe_comparison import write_json, write_jsonl
except ModuleNotFoundError:
    from run_fault_probe_comparison import write_json, write_jsonl


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "lab" / "pmlab-storage-injection-v0"
TRIALS_PER_INJECTION = 25
INJECTIONS = (
    "clean",
    "capture-omission",
    "primary-missing",
    "replica-missing",
    "both-missing",
    "primary-truncated",
    "both-truncated",
    "schema-unsupported",
    "index-omission",
    "primary-structured-reader-fault",
    "both-raw-reader-timeout",
    "structured-parser-fault",
)
EXPECTED = {
    "clean": "NO_FAULT_OBSERVED",
    "capture-omission": "CAPTURE_FAILURE",
    "primary-missing": "ACCESS_FAILURE",
    "replica-missing": "DEGRADED_REDUNDANCY",
    "both-missing": "LOGICAL_REPLICA_LOSS",
    "primary-truncated": "ACCESS_FAILURE",
    "both-truncated": "LOGICAL_REPLICA_LOSS",
    "schema-unsupported": "RECOVERABLE_CORRUPTION",
    "index-omission": "ACCESS_FAILURE",
    "primary-structured-reader-fault": "ACCESS_FAILURE",
    "both-raw-reader-timeout": "INCONCLUSIVE",
    "structured-parser-fault": "ACCESS_FAILURE",
}


def encoded_event(event_id: str, schema_version: int = 1) -> bytes:
    return (
        json.dumps(
            {"schema_version": schema_version, "id": event_id, "value": f"value-{event_id}"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def checksum(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_temp_root(path: Path) -> Path:
    resolved = path.resolve()
    system_temp = Path(tempfile.gettempdir()).resolve()
    if resolved.parent != system_temp or not resolved.name.startswith("pmlab-storage-"):
        raise ValueError(f"unsafe temporary root: {resolved}")
    return resolved


def durable_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def raw_probe(path: Path, expected_checksum: str, forced: str | None = None) -> dict[str, Any]:
    started = time.perf_counter_ns()
    if forced == "timeout":
        return {"status": "timeout", "checksum_match": None, "latency_us": (time.perf_counter_ns() - started) / 1000}
    try:
        value = path.read_bytes()
    except OSError as exc:
        return {"status": "fail", "checksum_match": False, "error_type": type(exc).__name__, "latency_us": (time.perf_counter_ns() - started) / 1000}
    matches = checksum(value) == expected_checksum
    return {"status": "ok" if matches else "fail", "checksum_match": matches, "latency_us": (time.perf_counter_ns() - started) / 1000}


def structured_probe(
    path: Path,
    expected_checksum: str,
    forced: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter_ns()
    if forced == "timeout":
        return {"status": "timeout", "reason": "forced-reader-timeout", "latency_us": (time.perf_counter_ns() - started) / 1000}
    if forced == "parser-fault":
        return {"status": "fail", "reason": "forced-parser-fault", "latency_us": (time.perf_counter_ns() - started) / 1000}
    try:
        value = path.read_bytes()
        if checksum(value) != expected_checksum:
            raise ValueError("checksum-mismatch")
        parsed = json.loads(value)
        if parsed.get("schema_version") != 1:
            return {"status": "unsupported-schema", "reason": "schema-version", "latency_us": (time.perf_counter_ns() - started) / 1000}
        return {"status": "ok", "reason": None, "latency_us": (time.perf_counter_ns() - started) / 1000}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "fail", "reason": str(exc), "error_type": type(exc).__name__, "latency_us": (time.perf_counter_ns() - started) / 1000}


def diagnose(probes: dict[str, Any]) -> str:
    if not probes["write_receipt"]:
        if probes["primary_raw"]["status"] == "fail" and probes["replica_raw"]["status"] == "fail":
            return "CAPTURE_FAILURE"
        return "INCONCLUSIVE"
    raw_results = [probes["primary_raw"], probes["replica_raw"]]
    if all(result["status"] == "timeout" for result in raw_results):
        return "INCONCLUSIVE"
    valid_primary = probes["primary_raw"]["status"] == "ok"
    valid_replica = probes["replica_raw"]["status"] == "ok"
    if not valid_primary and not valid_replica:
        if any(result["status"] == "timeout" for result in raw_results):
            return "INCONCLUSIVE"
        return "LOGICAL_REPLICA_LOSS"
    if probes["primary_structured"]["status"] == "unsupported-schema":
        return "RECOVERABLE_CORRUPTION"
    if probes["primary_structured"]["status"] != "ok" or not probes["index_contains_id"]:
        return "ACCESS_FAILURE"
    if not valid_replica:
        return "DEGRADED_REDUNDANCY"
    return "NO_FAULT_OBSERVED"


def execute_trial(root: Path, injection: str, trial: int) -> dict[str, Any]:
    event_id = f"{injection}-{trial:03d}"
    schema_version = 99 if injection == "schema-unsupported" else 1
    value = encoded_event(event_id, schema_version)
    expected_checksum = checksum(value)
    primary = root / "primary" / f"{event_id}.json"
    replica = root / "replica" / f"{event_id}.json"
    index_ids = {event_id}
    write_receipt = injection != "capture-omission"
    if write_receipt:
        durable_write(primary, value)
        durable_write(replica, value)
    if injection in {"primary-missing", "both-missing"}:
        primary.unlink()
    if injection in {"replica-missing", "both-missing"}:
        replica.unlink()
    if injection in {"primary-truncated", "both-truncated"}:
        durable_write(primary, value[: max(1, len(value) // 2)])
    if injection == "both-truncated":
        durable_write(replica, value[: max(1, len(value) // 3)])
    if injection == "index-omission":
        index_ids.clear()
    primary_raw_forced = "timeout" if injection == "both-raw-reader-timeout" else None
    replica_raw_forced = "timeout" if injection == "both-raw-reader-timeout" else None
    structured_forced = None
    if injection == "primary-structured-reader-fault":
        structured_forced = "timeout"
    elif injection == "structured-parser-fault":
        structured_forced = "parser-fault"
    probes = {
        "write_receipt": write_receipt,
        "primary_raw": raw_probe(primary, expected_checksum, primary_raw_forced),
        "replica_raw": raw_probe(replica, expected_checksum, replica_raw_forced),
        "primary_structured": structured_probe(primary, expected_checksum, structured_forced),
        "index_contains_id": event_id in index_ids,
    }
    predicted = diagnose(probes)
    return {
        "case_id": "FSI-" + hashlib.sha256(event_id.encode()).hexdigest()[:12],
        "injection": injection,
        "trial": trial,
        "expected_outcome": EXPECTED[injection],
        "predicted_outcome": predicted,
        "correct": predicted == EXPECTED[injection],
        "replica_domain": "same-physical-disk-0-logical-only",
        "physical_loss_confirmed": False,
        "probes": probes,
    }


def run(output: Path) -> dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory(prefix="pmlab-storage-") as temporary:
        root = safe_temp_root(Path(temporary))
        for injection in INJECTIONS:
            for trial in range(TRIALS_PER_INJECTION):
                results.append(execute_trial(root, injection, trial))
    by_injection = {
        injection: {
            "trials": sum(row["injection"] == injection for row in results),
            "accuracy": sum(row["correct"] for row in results if row["injection"] == injection) / TRIALS_PER_INJECTION,
        }
        for injection in INJECTIONS
    }
    latency = {}
    for probe in ("primary_raw", "replica_raw", "primary_structured"):
        values = sorted(
            row["probes"][probe]["latency_us"]
            for row in results
            if row["probes"][probe]["status"] != "timeout"
        )
        latency[probe] = {
            "observations": len(values),
            "p50": statistics.median(values),
            "p95_nearest_rank": values[max(0, int(0.95 * len(values) + 0.999999) - 1)],
        }
    summary = {
        "status": "completed-disposable-same-device-harness",
        "cases": len(results),
        "trials_per_injection": TRIALS_PER_INJECTION,
        "outcome_accuracy": sum(row["correct"] for row in results) / len(results),
        "physical_loss_confirmed_count": sum(row["physical_loss_confirmed"] for row in results),
        "by_injection": by_injection,
        "probe_latency_us_descriptive": latency,
        "environment": {"platform": platform.platform(), "python": platform.python_version(), "volume_topology": "C and D observed on Disk 0"},
        "boundary": "Real fsync/read/checksum/file-loss operations in disposable temp files; primary and replica share Disk 0; repeated trials are deterministic exercises, not independent reliability samples.",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "results.jsonl", results)
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "status": summary["status"],
            "script": "scripts/run_storage_fault_injection.py",
            "injections": list(INJECTIONS),
            "results_sha256": hashlib.sha256((output / "results.jsonl").read_bytes()).hexdigest(),
            "temporary_root_guard": "resolved parent equals system temp and basename starts pmlab-storage-",
            "model_api_required": False,
            "authority": "state-machine and probe-execution test only; no P10 independence",
        },
    )
    return summary


def main() -> int:
    print(json.dumps(run(OUTPUT), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
