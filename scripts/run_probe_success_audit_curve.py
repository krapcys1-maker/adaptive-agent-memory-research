#!/usr/bin/env python3
"""Exact expected cost/accuracy curve for auditing first-pass healthy probes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.run_fault_probe_comparison import STAGES, binary_f1, write_json, write_jsonl
    from scripts.run_fault_probe_robustness import (
        OUTPUT as ROBUSTNESS_OUTPUT,
        PRIMARY_PROBES,
        PROBES,
        STORAGE_DIVERSE_PROBES,
        diagnose,
        majority,
        make_cases,
    )
except ModuleNotFoundError:
    from run_fault_probe_comparison import STAGES, binary_f1, write_json, write_jsonl
    from run_fault_probe_robustness import (
        OUTPUT as ROBUSTNESS_OUTPUT,
        PRIMARY_PROBES,
        PROBES,
        STORAGE_DIVERSE_PROBES,
        diagnose,
        majority,
        make_cases,
    )


OUTPUT = ROBUSTNESS_OUTPUT.parent / "pmlab-probe-success-audit-v0"
RATES = (0.0, 0.05, 0.10, 0.25, 0.50, 0.75, 1.0)


def consolidate_with_target_audit(
    observations: dict[str, list[bool | None]], audit_target: str | None
) -> tuple[dict[str, bool | None], int, int]:
    values: dict[str, bool | None] = {}
    fixed_cost = 0
    eligible_healthy = 0
    for probe, repetitions in observations.items():
        always_repeat = probe in STORAGE_DIVERSE_PROBES or repetitions[0] in (False, None)
        if always_repeat or probe == audit_target:
            values[probe] = majority(repetitions)
            fixed_cost += 3
        else:
            values[probe] = repetitions[0]
            fixed_cost += 1
            if repetitions[0] is True:
                eligible_healthy += 1
    return values, fixed_cost, eligible_healthy


def contributions() -> list[dict[str, Any]]:
    rows = []
    for case in make_cases():
        if case["noise_class"] != "transient-flip":
            continue
        target = str(case["target_probe"])
        no_values, base_cost, eligible = consolidate_with_target_audit(case["observations"], None)
        target_values, _, _ = consolidate_with_target_audit(case["observations"], target)
        rows.append(
            {
                "case_id": case["case_id"],
                "target_probe": target,
                "fault_stages": case["fault_stages"],
                "root_fault": case["root_fault"],
                "physical_data_loss": case["physical_data_loss"],
                "no_success_audit": diagnose(no_values, diverse_loss_gate=True),
                "target_success_audited": diagnose(target_values, diverse_loss_gate=True),
                "base_probe_units": base_cost,
                "eligible_healthy_first_results": eligible,
            }
        )
    return rows


def expected_indicator(no_value: bool, audit_value: bool, rate: float) -> float:
    return (1.0 - rate) * float(no_value) + rate * float(audit_value)


def summarize(rows: list[dict[str, Any]], rate: float) -> dict[str, Any]:
    exact = []
    roots = []
    stage_confusion = {stage: {"tp": 0.0, "fp": 0.0, "fn": 0.0} for stage in STAGES}
    loss_recall = []
    false_loss = []
    false_no_loss = []
    loss_decided = []
    loss_correct_decided = []
    expected_costs = []
    for row in rows:
        no = row["no_success_audit"]
        audited = row["target_success_audited"]
        truth = set(row["fault_stages"])
        no_set = set(no["fault_stages"])
        audited_set = set(audited["fault_stages"])
        exact.append(expected_indicator(no_set == truth, audited_set == truth, rate))
        roots.append(expected_indicator(no["root_fault"] == row["root_fault"], audited["root_fault"] == row["root_fault"], rate))
        for stage in STAGES:
            truth_positive = stage in truth
            probability_positive = (1.0 - rate) * float(stage in no_set) + rate * float(stage in audited_set)
            if truth_positive:
                stage_confusion[stage]["tp"] += probability_positive
                stage_confusion[stage]["fn"] += 1.0 - probability_positive
            else:
                stage_confusion[stage]["fp"] += probability_positive
        if row["physical_data_loss"]:
            loss_recall.append(expected_indicator(no["physical_data_loss"] is True, audited["physical_data_loss"] is True, rate))
            false_no_loss.append(expected_indicator(no["physical_data_loss"] is False, audited["physical_data_loss"] is False, rate))
        else:
            false_loss.append(expected_indicator(no["physical_data_loss"] is True, audited["physical_data_loss"] is True, rate))
        no_decided = no["physical_data_loss"] is not None
        audited_decided = audited["physical_data_loss"] is not None
        loss_decided.append(expected_indicator(no_decided, audited_decided, rate))
        loss_correct_decided.append(
            expected_indicator(
                no_decided and no["physical_data_loss"] == row["physical_data_loss"],
                audited_decided and audited["physical_data_loss"] == row["physical_data_loss"],
                rate,
            )
        )
        expected_costs.append(
            row["base_probe_units"] + 2.0 * rate * row["eligible_healthy_first_results"]
        )
    stage_f1 = {}
    for stage, counts in stage_confusion.items():
        denominator = 2 * counts["tp"] + counts["fp"] + counts["fn"]
        stage_f1[stage] = 1.0 if denominator == 0 else 2 * counts["tp"] / denominator
    coverage = sum(loss_decided) / len(loss_decided)
    return {
        "healthy_audit_rate": rate,
        "cases": len(rows),
        "expected_probe_units": sum(expected_costs) / len(expected_costs),
        "expected_exact_fault_set_accuracy": sum(exact) / len(exact),
        "expected_root_fault_accuracy": sum(roots) / len(roots),
        "expected_macro_stage_f1": sum(stage_f1.values()) / len(stage_f1),
        "expected_data_loss_recall": sum(loss_recall) / len(loss_recall),
        "expected_false_data_loss_rate": sum(false_loss) / len(false_loss),
        "expected_false_no_loss_rate": sum(false_no_loss) / len(false_no_loss),
        "expected_data_loss_decision_coverage": coverage,
        "expected_data_loss_accuracy_when_decided": sum(loss_correct_decided) / sum(loss_decided),
    }


def run(output: Path) -> dict[str, Any]:
    rows = contributions()
    curve = [summarize(rows, rate) for rate in RATES]
    passing = [point for point in curve if point["expected_exact_fault_set_accuracy"] >= 0.95]
    baseline_exact = curve[0]["expected_exact_fault_set_accuracy"]
    full_exact = curve[-1]["expected_exact_fault_set_accuracy"]
    analytic_rate = (0.95 - baseline_exact) / (full_exact - baseline_exact)
    analytic_cost = curve[0]["expected_probe_units"] + analytic_rate * (
        curve[-1]["expected_probe_units"] - curve[0]["expected_probe_units"]
    )
    summary = {
        "status": "completed-exact-expected-audit-curve",
        "condition": "one uniformly enumerated transient flip per case; storage-diverse policy fixed",
        "cases": len(rows),
        "curve": curve,
        "lowest_tested_rate_meeting_0_95_exact": passing[0]["healthy_audit_rate"] if passing else None,
        "analytic_rate_meeting_0_95_exact_under_linear_mixture": analytic_rate,
        "analytic_probe_units_at_0_95_exact": analytic_cost,
        "boundary": "Rates are exact mixture weights over audit/no-audit outcomes, not observed random trials or calibrated production probabilities.",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "case-contributions.jsonl", rows)
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "status": summary["status"],
            "script": "scripts/run_probe_success_audit_curve.py",
            "base": "data/lab/pmlab-fault-probes-robustness-v1",
            "rates": list(RATES),
            "contributions_sha256": hashlib.sha256((output / "case-contributions.jsonl").read_bytes()).hexdigest(),
            "model_api_required": False,
            "authority": "authored exact expectation under a specified synthetic condition",
        },
    )
    return summary


def main() -> int:
    print(json.dumps(run(OUTPUT), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
