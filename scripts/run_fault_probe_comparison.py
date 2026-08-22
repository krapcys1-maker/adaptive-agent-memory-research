#!/usr/bin/env python3
"""Compare cascading passive telemetry with isolated active memory probes.

This is a deterministic observability instrument. It measures what can be
identified from each observation regime; it does not estimate real component
failure rates or prove that an implementation's probes are trustworthy.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-fault-probes-v0"
STAGES = ("F0", "F1", "F2", "F3", "F4", "F5")
TELEMETRY_PATTERNS = ("complete", "operational-sparse", "fault-silent")
F1_MODES = ("physical-loss", "recoverable-schema")


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


def fault_specs() -> list[dict[str, Any]]:
    """Create balanced no-fault, single, pair, and triple stage-fault specs."""
    specs: list[dict[str, Any]] = [{"fault_stages": [], "f1_mode": None}]
    for stage in STAGES:
        modes = F1_MODES if stage == "F1" else (None,)
        specs.extend({"fault_stages": [stage], "f1_mode": mode} for mode in modes)
    for width in (2, 3):
        for stages in itertools.combinations(STAGES, width):
            modes = F1_MODES if "F1" in stages else (None,)
            specs.extend({"fault_stages": list(stages), "f1_mode": mode} for mode in modes)
    return specs


def passive_trace(fault_stages: list[str], pattern: str) -> dict[str, bool | None]:
    """Emit one production trace; upstream failure cascades through the pipeline."""
    first_fault = min((STAGES.index(stage) for stage in fault_stages), default=None)
    trace: dict[str, bool | None] = {}
    for index, stage in enumerate(STAGES):
        trace[stage] = first_fault is None or index < first_fault
    if pattern == "operational-sparse":
        for stage in ("F1", "F3", "F4"):
            trace[stage] = None
    elif pattern == "fault-silent":
        silent_index = first_fault if first_fault is not None else STAGES.index("F3")
        trace[STAGES[silent_index]] = None
    return trace


def active_probes(fault_stages: list[str], f1_mode: str | None) -> dict[str, Any]:
    """Probe every stage using a controlled known-good upstream input."""
    stage_ok = {stage: stage not in fault_stages for stage in STAGES}
    return {
        "stage_ok": stage_ok,
        "capture_receipt_probe": stage_ok["F0"],
        "controlled_write_probe": stage_ok["F1"],
        "direct_id_found": f1_mode != "physical-loss",
        "full_scan_found": f1_mode != "physical-loss",
        "raw_bytes_recoverable": f1_mode != "physical-loss",
        "schema_reparse_possible": f1_mode == "recoverable-schema" or stage_ok["F1"],
        "oracle_query_retrieval_probe": stage_ok["F2"],
        "oracle_record_context_probe": stage_ok["F3"],
        "oracle_context_reader_probe": stage_ok["F4"],
        "fixed_answer_action_probe": stage_ok["F5"],
    }


def make_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for spec_index, spec in enumerate(fault_specs(), start=1):
        faults = spec["fault_stages"]
        for pattern in TELEMETRY_PATTERNS:
            case_key = f"{spec_index}|{','.join(faults)}|{spec['f1_mode']}|{pattern}"
            cases.append(
                {
                    "case_id": "F1PROBE-" + hashlib.sha256(case_key.encode()).hexdigest()[:12],
                    "fault_contract": "isolatable synthetic component faults",
                    "fault_stages": faults,
                    "root_fault": faults[0] if faults else None,
                    "f1_mode": spec["f1_mode"],
                    "physical_data_loss": spec["f1_mode"] == "physical-loss",
                    "telemetry_pattern": pattern,
                    "passive_trace": passive_trace(faults, pattern),
                    "active_probes": active_probes(faults, spec["f1_mode"]),
                }
            )
    return cases


def diagnose_passive(trace: dict[str, bool | None]) -> dict[str, Any]:
    """Locate the first observed failure without treating cascade as new faults."""
    first_false = next((index for index, stage in enumerate(STAGES) if trace[stage] is False), None)
    if first_false is None:
        unknown = [stage for stage in STAGES if trace[stage] is None]
        storage_observed_healthy = trace["F0"] is True and trace["F1"] is True
        return {"fault_stages": [], "root_fault": None, "unknown_stages": unknown, "physical_data_loss": False if storage_observed_healthy else None}
    root = STAGES[first_false]
    unknown = [stage for stage in STAGES if trace[stage] is None]
    unknown.extend(stage for stage in STAGES[first_false + 1 :] if stage not in unknown)
    if root == "F0":
        physical_data_loss: bool | None = False
    elif STAGES.index(root) > STAGES.index("F1") and trace["F1"] is True:
        physical_data_loss = False
    else:
        physical_data_loss = None
    return {
        "fault_stages": [root],
        "root_fault": root,
        "unknown_stages": unknown,
        "physical_data_loss": physical_data_loss,
    }


def diagnose_active(probes: dict[str, Any]) -> dict[str, Any]:
    faults = [stage for stage in STAGES if not probes["stage_ok"][stage]]
    physical_loss = (
        not probes["direct_id_found"]
        and not probes["full_scan_found"]
        and not probes["raw_bytes_recoverable"]
    )
    return {
        "fault_stages": faults,
        "root_fault": faults[0] if faults else None,
        "unknown_stages": [],
        "physical_data_loss": physical_loss,
    }


def binary_f1(truth: list[bool], prediction: list[bool]) -> float:
    tp = sum(t and p for t, p in zip(truth, prediction))
    fp = sum(not t and p for t, p in zip(truth, prediction))
    fn = sum(t and not p for t, p in zip(truth, prediction))
    return 1.0 if tp == fp == fn == 0 else (2 * tp) / (2 * tp + fp + fn)


def summarize(results: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    predicted_key = f"{arm}_diagnosis"
    exact = []
    roots = []
    loss_exact = []
    loss_decided = []
    masked_truth: list[bool] = []
    masked_predicted: list[bool] = []
    per_stage: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    unknown_counts = []
    for row in results:
        prediction = row[predicted_key]
        truth_set = set(row["fault_stages"])
        predicted_set = set(prediction["fault_stages"])
        exact.append(truth_set == predicted_set)
        roots.append(row["root_fault"] == prediction["root_fault"])
        decided = prediction["physical_data_loss"] is not None
        loss_decided.append(decided)
        loss_exact.append(decided and prediction["physical_data_loss"] == row["physical_data_loss"])
        unknown_counts.append(len(prediction["unknown_stages"]))
        for stage in STAGES:
            per_stage[stage].append((stage in truth_set, stage in predicted_set))
        if row["root_fault"] is not None:
            root_index = STAGES.index(row["root_fault"])
            for stage in STAGES[root_index + 1 :]:
                if stage in truth_set:
                    masked_truth.append(True)
                    masked_predicted.append(stage in predicted_set)
    stage_f1 = {
        stage: binary_f1([x[0] for x in pairs], [x[1] for x in pairs])
        for stage, pairs in per_stage.items()
    }
    return {
        "cases": len(results),
        "exact_fault_set_accuracy": statistics.mean(exact),
        "root_fault_accuracy": statistics.mean(roots),
        "macro_stage_f1": statistics.mean(stage_f1.values()),
        "per_stage_f1": stage_f1,
        "masked_downstream_fault_recall": statistics.mean(masked_predicted) if masked_truth else None,
        "data_loss_decision_coverage": statistics.mean(loss_decided),
        "data_loss_accuracy_when_decided": (
            sum(loss_exact) / sum(loss_decided) if any(loss_decided) else None
        ),
        "data_loss_overall_accuracy": statistics.mean(loss_exact),
        "mean_unknown_stages": statistics.mean(unknown_counts),
        "incremental_probe_units": 0 if arm == "passive" else 10,
    }


def run(output: Path) -> dict[str, Any]:
    cases = make_cases()
    results = []
    for case in cases:
        results.append(
            {
                **case,
                "passive_diagnosis": diagnose_passive(case["passive_trace"]),
                "active_diagnosis": diagnose_active(case["active_probes"]),
            }
        )
    passive_by_pattern = {
        pattern: summarize(
            [row for row in results if row["telemetry_pattern"] == pattern], "passive"
        )
        for pattern in TELEMETRY_PATTERNS
    }
    passive_by_fault_width = {
        str(width): summarize(
            [row for row in results if len(row["fault_stages"]) == width], "passive"
        )
        for width in range(4)
    }
    summary = {
        "status": "completed-deterministic-instrument-test",
        "cases": len(cases),
        "base_fault_specs": len(fault_specs()),
        "telemetry_patterns": list(TELEMETRY_PATTERNS),
        "arms": {
            "passive": summarize(results, "passive"),
            "active": summarize(results, "active"),
        },
        "passive_by_telemetry_pattern": passive_by_pattern,
        "passive_by_fault_width": passive_by_fault_width,
        "boundary": "Ideal active probes use controlled inputs and are assumed truthful. Results establish observability requirements, not real-world diagnostic accuracy.",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "cases.jsonl", cases)
    write_jsonl(output / "results.jsonl", results)
    write_json(output / "summary.json", summary)
    manifest = {
        "status": "frozen-deterministic-run",
        "generator": "scripts/run_fault_probe_comparison.py",
        "cases": len(cases),
        "stages": list(STAGES),
        "cases_sha256": hashlib.sha256((output / "cases.jsonl").read_bytes()).hexdigest(),
        "results_sha256": hashlib.sha256((output / "results.jsonl").read_bytes()).hexdigest(),
        "authority": "authored observability instrument; not held out",
        "model_api_required": False,
    }
    write_json(output / "manifest.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
