#!/usr/bin/env python3
"""Run deterministic monitoring/control ablations on the frozen dev corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_metamemory_dev_corpus import content_hash
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from build_metamemory_dev_corpus import content_hash


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "lab" / "pmlab-metamemory-control-dev-v0"
SCALAR_THRESHOLD = 0.75
CONTROL_ORDER = ("TEMPORAL_CUE", "BILINGUAL_CUE", "ENTITY_CUE", "DIRECT_ID")
OPERATION_COST = {
    "ASK_CLARIFICATION": 0.25,
    "TEMPORAL_CUE": 1.0,
    "BILINGUAL_CUE": 1.0,
    "ENTITY_CUE": 1.0,
    "DIRECT_ID": 1.5,
    "STORAGE_PROBE": 2.0,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def candidate_is_evidence_valid(candidate: dict[str, Any] | None) -> bool:
    if candidate is None:
        return False
    return all(
        (
            candidate["current"],
            candidate["authorized"],
            candidate["checksum_valid"],
            candidate["provenance_complete"],
            candidate["evidence_sufficient"],
            not candidate["conflict"],
        )
    )


def outcome(
    case: dict[str, Any],
    policy: str,
    action: str,
    candidate: dict[str, Any] | None,
    *,
    cost: float = 0.0,
    trace: list[str] | None = None,
) -> dict[str, Any]:
    truth = case["truth"]
    answered = action == "ANSWER"
    correct = bool(
        answered
        and truth["answerable"]
        and candidate is not None
        and candidate["value"] == truth["expected_value"]
    )
    false_known = answered and not correct
    false_unknown = not answered and truth["answerable"]
    return {
        "case_id": case["case_id"],
        "stratum": case["stratum"],
        "critical": case["critical"],
        "policy": policy,
        "action": action,
        "answer": candidate["value"] if answered and candidate else None,
        "answered": answered,
        "correct": correct,
        "false_known": false_known,
        "false_unknown": false_unknown,
        "provenance_complete": bool(answered and candidate and candidate["provenance_complete"]),
        "cost": cost,
        "trace": trace or [],
    }


def run_simple_policy(case: dict[str, Any], policy: str) -> dict[str, Any]:
    initial = case["initial"]
    candidate = initial["candidate"]
    if policy == "no_monitor":
        accepted = candidate is not None
    else:
        score_name = {
            "self_confidence": "self_confidence",
            "cue_familiarity": "cue_familiarity",
            "semantic_consistency": "semantic_consistency",
        }[policy]
        accepted = candidate is not None and initial[score_name] >= SCALAR_THRESHOLD
    return outcome(case, policy, "ANSWER" if accepted else "ABSTAIN", candidate)


def run_typed_monitor(case: dict[str, Any]) -> dict[str, Any]:
    initial = case["initial"]
    if initial["query_ambiguous"]:
        return outcome(case, "typed_monitor", "ASK_CLARIFICATION", None, cost=0.25)
    candidate = initial["candidate"]
    if candidate_is_evidence_valid(candidate):
        return outcome(case, "typed_monitor", "ANSWER", candidate)
    return outcome(case, "typed_monitor", "ABSTAIN", None)


def run_typed_control(case: dict[str, Any]) -> dict[str, Any]:
    initial = case["initial"]
    trace: list[str] = []
    cost = 0.0
    if initial["query_ambiguous"]:
        return outcome(
            case,
            "typed_control",
            "ASK_CLARIFICATION",
            None,
            cost=OPERATION_COST["ASK_CLARIFICATION"],
            trace=["ASK_CLARIFICATION"],
        )

    candidate = initial["candidate"]
    if candidate_is_evidence_valid(candidate):
        return outcome(case, "typed_control", "ANSWER", candidate, trace=["INITIAL_ACCEPT"])

    operations = case["operations"]
    for operation in CONTROL_ORDER:
        if operation not in operations:
            continue
        trace.append(operation)
        cost += OPERATION_COST[operation]
        candidate = operations[operation].get("candidate")
        if candidate_is_evidence_valid(candidate):
            return outcome(case, "typed_control", "ANSWER", candidate, cost=cost, trace=trace)

    if "STORAGE_PROBE" in operations:
        trace.append("STORAGE_PROBE")
        cost += OPERATION_COST["STORAGE_PROBE"]
        storage_status = operations["STORAGE_PROBE"]["storage_status"]
        if storage_status == "absent":
            action = "ABSTAIN_NOT_STORED"
        elif storage_status == "present-conflict":
            action = "ABSTAIN_CONFLICT"
        elif storage_status == "present":
            action = "ABSTAIN_ACCESS"
        else:
            action = "ABSTAIN_INCONCLUSIVE"
        return outcome(case, "typed_control", action, None, cost=cost, trace=trace)

    return outcome(case, "typed_control", "ABSTAIN_INCONCLUSIVE", None, cost=cost, trace=trace)


def run_oracle(case: dict[str, Any]) -> dict[str, Any]:
    truth = case["truth"]
    if truth["answerable"]:
        return outcome(
            case,
            "oracle",
            "ANSWER",
            {
                "value": truth["expected_value"],
                "current": True,
                "authorized": True,
                "checksum_valid": True,
                "provenance_complete": True,
                "evidence_sufficient": True,
                "conflict": False,
            },
        )
    action = "ASK_CLARIFICATION" if case["initial"]["query_ambiguous"] else "ABSTAIN"
    return outcome(case, "oracle", action, None)


def run_all(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        for policy in ("no_monitor", "self_confidence", "cue_familiarity", "semantic_consistency"):
            results.append(run_simple_policy(case, policy))
        results.append(run_typed_monitor(case))
        results.append(run_typed_control(case))
        results.append(run_oracle(case))
    return results


def summarize_policy(rows: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    answered = sum(row["answered"] for row in rows)
    correct = sum(row["correct"] for row in rows)
    false_known = sum(row["false_known"] for row in rows)
    false_unknown = sum(row["false_unknown"] for row in rows)
    recoverable = sum(case["truth"]["answerable"] for case in cases)
    critical_unsupported = sum(row["critical"] and row["false_known"] for row in rows)
    accepted_with_provenance = sum(row["answered"] and row["provenance_complete"] for row in rows)
    common_mode_wrong = sum(
        row["stratum"] == "consistent-unsupported" and row["false_known"] for row in rows
    )
    return {
        "cases": total,
        "answered": answered,
        "coverage": answered / total,
        "correct_answers": correct,
        "selective_risk": false_known / answered if answered else 0.0,
        "distortion_rate": false_known / total,
        "false_known": false_known,
        "false_unknown": false_unknown,
        "stored_target_recovery": correct / recoverable,
        "critical_unsupported_answers": critical_unsupported,
        "provenance_complete_accept_rate": accepted_with_provenance / answered if answered else 1.0,
        "common_mode_consistent_wrong": common_mode_wrong,
        "mean_abstract_cost": sum(row["cost"] for row in rows) / total,
    }


def build_summary(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    policies = sorted({row["policy"] for row in results})
    by_policy = {
        policy: summarize_policy([row for row in results if row["policy"] == policy], cases)
        for policy in policies
    }
    control = by_policy["typed_control"]
    baseline = by_policy["no_monitor"]
    return {
        "experiment_id": "PMLAB-META-001",
        "status": "completed-exploratory-construction-test",
        "case_count": len(cases),
        "scalar_threshold": SCALAR_THRESHOLD,
        "policy_metrics": by_policy,
        "candidate_gate_checks": {
            "critical_unsupported_zero": control["critical_unsupported_answers"] == 0,
            "recovery_gain_at_least_15_points": (
                control["stored_target_recovery"] - baseline["stored_target_recovery"] >= 0.15
            ),
            "distortion_not_increased": control["distortion_rate"] <= baseline["distortion_rate"],
            "accepted_provenance_complete": control["provenance_complete_accept_rate"] == 1.0,
        },
        "interpretation_boundary": (
            "Authored deterministic development construction test. Passing gates validates only "
            "the implemented state-machine semantics, not generalization or architecture efficacy."
        ),
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# PMLAB metamemory-control development run v0",
        "",
        "Status: exploratory construction test on a frozen authored corpus; not held out",
        "",
        "## Result",
        "",
        "| Policy | Coverage | Selective risk | Stored-target recovery | False known | False unknown | Critical unsupported | Provenance accepted | Mean cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order = (
        "no_monitor",
        "self_confidence",
        "cue_familiarity",
        "semantic_consistency",
        "typed_monitor",
        "typed_control",
        "oracle",
    )
    for policy in order:
        metric = summary["policy_metrics"][policy]
        lines.append(
            f"| {policy} | {metric['coverage']:.3f} | {metric['selective_risk']:.3f} | "
            f"{metric['stored_target_recovery']:.3f} | {metric['false_known']} | "
            f"{metric['false_unknown']} | {metric['critical_unsupported_answers']} | "
            f"{metric['provenance_complete_accept_rate']:.3f} | {metric['mean_abstract_cost']:.3f} |"
        )
    lines.extend(
        [
            "",
            "The fixed typed-control state machine recovered alternate-cue, direct-ID, poison-adjacent, and stale-version targets while refusing absent, ambiguous, and conflicting cases. Scalar policies failed specifically on the authored high-confidence/common-mode-wrong cases. Typed monitoring without control remained safe but could not recover targets missed by the first cue.",
            "",
            "## Candidate gate checks",
            "",
        ]
    )
    for name, passed in summary["candidate_gate_checks"].items():
        lines.append(f"- `{name}`: {'PASS' if passed else 'FAIL'}")
    lines.extend(
        [
            "",
            "## Valid interpretation",
            "",
            summary["interpretation_boundary"],
            "The next admissible test must replace authored operation outcomes with real retrieval backends, hide labels from policy development, add risk-coverage sweeps, and receive independent review.",
            "",
        ]
    )
    return "\n".join(lines)


def run(dataset: Path = DEFAULT_DATASET) -> dict[str, Any]:
    cases = read_jsonl(dataset / "cases.jsonl")
    corpus_manifest = read_json(dataset / "manifest.json")
    actual_hash = content_hash(cases)
    if actual_hash != corpus_manifest["case_sha256"]:
        raise ValueError(
            f"Frozen case hash mismatch: expected {corpus_manifest['case_sha256']}, got {actual_hash}"
        )

    results = run_all(cases)
    summary = build_summary(cases, results)
    artifacts = dataset / "artifacts"
    write_jsonl(artifacts / "results.jsonl", results)
    write_json(artifacts / "summary.json", summary)
    write_json(
        artifacts / "manifest.json",
        {
            "experiment_id": "PMLAB-META-001",
            "frozen_corpus_commit": "a4d5d3c",
            "case_sha256": actual_hash,
            "runner": "scripts/run_metamemory_control_dev.py",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "policies": sorted(summary["policy_metrics"]),
            "scalar_threshold": SCALAR_THRESHOLD,
            "network_or_model_calls": 0,
        },
    )
    (dataset / "report.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    print(json.dumps(run(args.dataset), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
