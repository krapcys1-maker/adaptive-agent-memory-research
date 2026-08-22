#!/usr/bin/env python3
"""Stress active memory diagnostics with noisy, silent, and correlated probes."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.run_fault_probe_comparison import (
        DEFAULT_OUTPUT as V0_OUTPUT,
        STAGES,
        active_probes,
        binary_f1,
        fault_specs,
        write_json,
        write_jsonl,
    )
except ModuleNotFoundError:
    from run_fault_probe_comparison import (
        DEFAULT_OUTPUT as V0_OUTPUT,
        STAGES,
        active_probes,
        binary_f1,
        fault_specs,
        write_json,
        write_jsonl,
    )


OUTPUT = V0_OUTPUT.parent / "pmlab-fault-probes-robustness-v1"
PRIMARY_PROBES = {
    "F0": "capture_receipt_probe",
    "F1": "controlled_write_probe",
    "F2": "oracle_query_retrieval_probe",
    "F3": "oracle_record_context_probe",
    "F4": "oracle_context_reader_probe",
    "F5": "fixed_answer_action_probe",
}
RECOVERY_PROBES = ("direct_id_found", "full_scan_found", "raw_bytes_recoverable")
SCHEMA_PROBE = "schema_reparse_possible"
PROBES = tuple(PRIMARY_PROBES.values()) + RECOVERY_PROBES + (SCHEMA_PROBE,)
STORAGE_DIVERSE_PROBES = (
    "controlled_write_probe",
    *RECOVERY_PROBES,
    SCHEMA_PROBE,
)


def truth_probes(fault_stages: list[str], f1_mode: str | None) -> dict[str, bool]:
    raw = active_probes(fault_stages, f1_mode)
    return {probe: bool(raw[probe]) for probe in PROBES}


def noise_scenarios() -> list[dict[str, str | None]]:
    scenarios: list[dict[str, str | None]] = [
        {"scenario": "clean", "noise_class": "clean", "target_probe": None}
    ]
    for noise_class in ("transient-flip", "transient-timeout", "persistent-flip"):
        for probe in PROBES:
            scenarios.append(
                {
                    "scenario": f"{noise_class}:{probe}",
                    "noise_class": noise_class,
                    "target_probe": probe,
                }
            )
    scenarios.extend(
        [
            {"scenario": "correlated-storage-false", "noise_class": "correlated", "target_probe": "recovery-triad"},
            {"scenario": "correlated-storage-healthy", "noise_class": "correlated", "target_probe": "recovery-triad"},
            {"scenario": "correlated-primary-false", "noise_class": "correlated", "target_probe": "all-primary"},
        ]
    )
    return scenarios


def observations(
    truth: dict[str, bool], scenario: dict[str, str | None]
) -> dict[str, list[bool | None]]:
    rows = {probe: [value, value, value] for probe, value in truth.items()}
    noise_class = scenario["noise_class"]
    target = scenario["target_probe"]
    if noise_class == "transient-flip":
        rows[str(target)][0] = not truth[str(target)]
    elif noise_class == "transient-timeout":
        rows[str(target)][0] = None
    elif noise_class == "persistent-flip":
        rows[str(target)] = [not truth[str(target)]] * 3
    elif scenario["scenario"] == "correlated-storage-false":
        for probe in RECOVERY_PROBES:
            rows[probe] = [False, False, False]
    elif scenario["scenario"] == "correlated-storage-healthy":
        for probe in RECOVERY_PROBES:
            rows[probe] = [True, True, True]
    elif scenario["scenario"] == "correlated-primary-false":
        for probe in PRIMARY_PROBES.values():
            rows[probe] = [False, False, False]
    return rows


def majority(values: list[bool | None]) -> bool | None:
    true_count = sum(value is True for value in values)
    false_count = sum(value is False for value in values)
    if true_count >= 2:
        return True
    if false_count >= 2:
        return False
    return None


def consolidate(
    observations_by_probe: dict[str, list[bool | None]], policy: str
) -> tuple[dict[str, bool | None], int]:
    if policy == "single":
        return {probe: values[0] for probe, values in observations_by_probe.items()}, len(PROBES)
    if policy == "repeat-all":
        return {probe: majority(values) for probe, values in observations_by_probe.items()}, 3 * len(PROBES)
    values: dict[str, bool | None] = {}
    cost = 0
    for probe, repetitions in observations_by_probe.items():
        repeat = (
            policy == "storage-diverse" and probe in STORAGE_DIVERSE_PROBES
        ) or repetitions[0] in (False, None)
        values[probe] = majority(repetitions) if repeat else repetitions[0]
        cost += 3 if repeat else 1
    return values, cost


def diagnose(
    values: dict[str, bool | None], diverse_loss_gate: bool
) -> dict[str, Any]:
    fault_stages = [
        stage for stage, probe in PRIMARY_PROBES.items() if values[probe] is False
    ]
    unknown_stages = [
        stage for stage, probe in PRIMARY_PROBES.items() if values[probe] is None
    ]
    if diverse_loss_gate:
        write_value = values["controlled_write_probe"]
        recovery = [values[probe] for probe in RECOVERY_PROBES]
        schema_value = values[SCHEMA_PROBE]
        loss_evidence = [write_value, *recovery, schema_value]
        if all(value is False for value in loss_evidence):
            physical_loss: bool | None = True
        elif schema_value is True and any(value is True for value in recovery):
            physical_loss = False
        else:
            physical_loss = None
    else:
        recovery = [values[probe] for probe in RECOVERY_PROBES]
        if all(value is False for value in recovery):
            physical_loss = True
        elif any(value is True for value in recovery):
            physical_loss = False
        else:
            physical_loss = None
    return {
        "fault_stages": fault_stages,
        "root_fault": fault_stages[0] if fault_stages else None,
        "unknown_stages": unknown_stages,
        "physical_data_loss": physical_loss,
    }


def run_arm(
    observation_set: dict[str, list[bool | None]], arm: str
) -> tuple[dict[str, Any], int]:
    policy = {
        "single-naive": "single",
        "repeat-all-naive": "repeat-all",
        "adaptive-abnormal-naive": "adaptive-abnormal",
        "adaptive-storage-diverse": "storage-diverse",
    }[arm]
    values, cost = consolidate(observation_set, policy)
    return diagnose(values, diverse_loss_gate=arm == "adaptive-storage-diverse"), cost


def make_cases() -> list[dict[str, Any]]:
    cases = []
    for spec_index, spec in enumerate(fault_specs(), start=1):
        truth = truth_probes(spec["fault_stages"], spec["f1_mode"])
        for scenario in noise_scenarios():
            key = f"{spec_index}|{scenario['scenario']}"
            cases.append(
                {
                    "case_id": "F1NOISE-" + hashlib.sha256(key.encode()).hexdigest()[:12],
                    "fault_stages": spec["fault_stages"],
                    "root_fault": spec["fault_stages"][0] if spec["fault_stages"] else None,
                    "f1_mode": spec["f1_mode"],
                    "physical_data_loss": spec["f1_mode"] == "physical-loss",
                    **scenario,
                    "truth_probes": truth,
                    "observations": observations(truth, scenario),
                }
            )
    return cases


def summarize(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    diagnoses = [row["arms"][arm]["diagnosis"] for row in rows]
    truth_sets = [set(row["fault_stages"]) for row in rows]
    predicted_sets = [set(diagnosis["fault_stages"]) for diagnosis in diagnoses]
    stage_f1 = {}
    for stage in STAGES:
        stage_f1[stage] = binary_f1(
            [stage in truth for truth in truth_sets],
            [stage in prediction for prediction in predicted_sets],
        )
    loss_positive = [row for row in rows if row["physical_data_loss"]]
    loss_negative = [row for row in rows if not row["physical_data_loss"]]
    decided = [diagnosis["physical_data_loss"] is not None for diagnosis in diagnoses]
    correct_decisions = [
        diagnosis["physical_data_loss"] == row["physical_data_loss"]
        for row, diagnosis in zip(rows, diagnoses)
        if diagnosis["physical_data_loss"] is not None
    ]
    return {
        "cases": len(rows),
        "exact_fault_set_accuracy": statistics.mean(t == p for t, p in zip(truth_sets, predicted_sets)),
        "root_fault_accuracy": statistics.mean(row["root_fault"] == diagnosis["root_fault"] for row, diagnosis in zip(rows, diagnoses)),
        "macro_stage_f1": statistics.mean(stage_f1.values()),
        "data_loss_recall": statistics.mean(
            row["arms"][arm]["diagnosis"]["physical_data_loss"] is True for row in loss_positive
        ),
        "false_data_loss_rate": statistics.mean(
            row["arms"][arm]["diagnosis"]["physical_data_loss"] is True for row in loss_negative
        ),
        "false_no_loss_rate": statistics.mean(
            row["arms"][arm]["diagnosis"]["physical_data_loss"] is False for row in loss_positive
        ),
        "data_loss_decision_coverage": statistics.mean(decided),
        "data_loss_accuracy_when_decided": statistics.mean(correct_decisions) if correct_decisions else None,
        "mean_probe_units": statistics.mean(row["arms"][arm]["probe_units"] for row in rows),
    }


def run(output: Path) -> dict[str, Any]:
    cases = make_cases()
    arms = (
        "single-naive",
        "repeat-all-naive",
        "adaptive-abnormal-naive",
        "adaptive-storage-diverse",
    )
    results = []
    for case in cases:
        arm_outputs = {}
        for arm in arms:
            diagnosis, cost = run_arm(case["observations"], arm)
            arm_outputs[arm] = {"diagnosis": diagnosis, "probe_units": cost}
        results.append({**case, "arms": arm_outputs})
    summary = {
        "status": "completed-deterministic-probe-robustness",
        "fault_specs": len(fault_specs()),
        "noise_scenarios": len(noise_scenarios()),
        "cases": len(results),
        "arms": {arm: summarize(results, arm) for arm in arms},
        "by_noise_class": {
            noise_class: {
                arm: summarize(
                    [row for row in results if row["noise_class"] == noise_class], arm
                )
                for arm in arms
            }
            for noise_class in sorted({row["noise_class"] for row in results})
        },
        "boundary": "Authored deterministic noise schedules; repetitions are independent only in transient scenarios; correlated and persistent faults intentionally defeat repetition.",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "cases.jsonl", cases)
    write_jsonl(output / "results.jsonl", results)
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "status": summary["status"],
            "script": "scripts/run_fault_probe_robustness.py",
            "base_instrument": "data/lab/pmlab-fault-probes-v0",
            "cases_sha256": hashlib.sha256((output / "cases.jsonl").read_bytes()).hexdigest(),
            "results_sha256": hashlib.sha256((output / "results.jsonl").read_bytes()).hexdigest(),
            "model_api_required": False,
            "authority": "authored robustness instrument; not empirical failure rates",
        },
    )
    return summary


def main() -> int:
    print(json.dumps(run(OUTPUT), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
