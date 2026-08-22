#!/usr/bin/env python3
"""Run PMLAB-SUFF-001 policy ablations on the frozen construction corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.build_evidence_sufficiency_corpus import content_hash
except ModuleNotFoundError:
    from build_evidence_sufficiency_corpus import content_hash


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "lab" / "pmlab-evidence-sufficiency-dev-v0"
THRESHOLD = 0.75
ANSWER_ACTIONS = {"ANSWER_FULL", "ANSWER_SUPPORTED_ONLY"}
GAP_ACTIONS = {
    "PARTIAL_WITH_GAP",
    "RETRIEVE_MISSING",
    "RETRIEVE_VALID",
    "ABSTAIN_NOT_FOUND",
    "ABSTAIN_INCONCLUSIVE",
    "ABSTAIN_INVALID_EVIDENCE",
    "ABSTAIN_CONFLICT",
    "ASK_CLARIFICATION",
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


def retrieved(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in case["evidence"] if row["retrieved"]]


def accepted_claims(case: dict[str, Any], action: str) -> list[dict[str, Any]]:
    claims = case["reader_signals"]["proposed_claims"]
    if action == "ANSWER_FULL":
        return claims
    if action == "ANSWER_SUPPORTED_ONLY":
        return [claim for claim in claims if claim["support_status"] == "supported"]
    return []


def result(
    case: dict[str, Any],
    policy: str,
    action: str,
    *,
    missing: list[str] | None = None,
    cost: float = 0.0,
    trace: list[str] | None = None,
) -> dict[str, Any]:
    expected = case["truth"]["expected_action"]
    claims = accepted_claims(case, action)
    answer_accepted = action in ANSWER_ACTIONS
    false_sufficient = answer_accepted and action != expected
    false_insufficient = expected in ANSWER_ACTIONS and not answer_accepted
    supported_claims = [claim for claim in claims if claim["support_status"] == "supported"]
    cited_claims = [claim for claim in supported_claims if claim["cited_source_ids"]]
    return {
        "case_id": case["case_id"],
        "stratum": case["stratum"],
        "critical": case["critical"],
        "policy": policy,
        "action": action,
        "expected_action": expected,
        "exact_action": action == expected,
        "answer_accepted": answer_accepted,
        "false_sufficient": false_sufficient,
        "false_insufficient": false_insufficient,
        "reported_missing_obligation_ids": sorted(missing or []),
        "gold_missing_obligation_ids": sorted(case["truth"]["missing_obligation_ids"]),
        "accepted_claims": len(claims),
        "supported_accepted_claims": len(supported_claims),
        "cited_supported_claims": len(cited_claims),
        "false_not_found": action == "ABSTAIN_NOT_FOUND" and case["truth"]["collection_answer_state"] != "none",
        "cost": cost,
        "trace": trace or [],
    }


def run_nonempty(case: dict[str, Any]) -> dict[str, Any]:
    action = "ANSWER_FULL" if retrieved(case) else "ABSTAIN_NOT_FOUND"
    return result(case, "nonempty", action)


def signal_value(case: dict[str, Any], signal: str) -> float:
    if signal == "similarity":
        return max((row["similarity"] for row in retrieved(case)), default=0.0)
    return case["reader_signals"][signal]


def run_scalar(case: dict[str, Any], policy: str, signal: str) -> dict[str, Any]:
    accepts = bool(retrieved(case)) and signal_value(case, signal) >= THRESHOLD
    return result(case, policy, "ANSWER_FULL" if accepts else "ABSTAIN_INSUFFICIENT")


def run_claim_entailment(case: dict[str, Any]) -> dict[str, Any]:
    claims = case["reader_signals"]["proposed_claims"]
    all_supported_and_cited = bool(claims) and all(
        claim["support_status"] == "supported" and claim["cited_source_ids"] for claim in claims
    )
    return result(
        case,
        "claim_entailment",
        "ANSWER_FULL" if all_supported_and_cited else "ABSTAIN_INSUFFICIENT",
        cost=1.0,
    )


def observed_obligation_state(case: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    rows = retrieved(case)
    missing: list[str] = []
    contradicted: list[str] = []
    invalid: list[str] = []
    for obligation in case["obligations"]:
        obligation_id = obligation["obligation_id"]
        support = [row for row in rows if obligation_id in row["supports"]]
        contradiction = [row for row in rows if obligation_id in row["contradicts"]]
        valid_support = [
            row
            for row in support
            if row["current"] and row["authorized"] and row["provenance_complete"]
        ]
        valid_contradiction = [
            row
            for row in contradiction
            if row["current"] and row["authorized"] and row["provenance_complete"]
        ]
        if valid_support and valid_contradiction:
            contradicted.append(obligation_id)
        elif not valid_support:
            missing.append(obligation_id)
            if support:
                invalid.append(obligation_id)
    return sorted(missing), sorted(contradicted), sorted(invalid)


def _supported_action(case: dict[str, Any]) -> str:
    claims = case["reader_signals"]["proposed_claims"]
    if any(claim["support_status"] == "unsupported" for claim in claims):
        return "ANSWER_SUPPORTED_ONLY"
    if any(
        claim["support_status"] == "supported-missing-attribution"
        or (claim["support_status"] == "supported" and not claim["cited_source_ids"])
        for claim in claims
    ):
        return "REPAIR_ATTRIBUTION"
    return "ANSWER_FULL"


def run_retrieved_obligation(case: dict[str, Any]) -> dict[str, Any]:
    missing, contradicted, invalid = observed_obligation_state(case)
    trace = ["DECOMPOSE", "CHECK_RETRIEVED_OBLIGATIONS"]
    if case["query_resolution"] == "ambiguous":
        action = "ASK_CLARIFICATION"
    elif contradicted:
        action = "ABSTAIN_CONFLICT"
    elif not missing:
        action = _supported_action(case)
    elif case["collection_scope"]["inventory_complete"] is False:
        action = "ABSTAIN_INCONCLUSIVE"
    elif invalid:
        stale = any(
            not row["current"] and set(row["supports"]) & set(invalid)
            for row in retrieved(case)
        )
        action = "RETRIEVE_VALID" if stale else "ABSTAIN_INVALID_EVIDENCE"
    else:
        action = "RETRIEVE_MISSING"
    return result(
        case,
        "retrieved_obligation",
        action,
        missing=missing,
        cost=1.0,
        trace=trace,
    )


def run_collection_hybrid(case: dict[str, Any]) -> dict[str, Any]:
    truth = case["truth"]
    state = truth["collection_answer_state"]
    trace = ["DECOMPOSE", "CHECK_RETRIEVED_OBLIGATIONS", "PROBE_COLLECTION", "CHECK_CLAIMS"]
    if case["query_resolution"] == "ambiguous":
        action = "ASK_CLARIFICATION"
    elif state == "conflict":
        action = "ABSTAIN_CONFLICT"
    elif state == "unknown" or case["collection_scope"]["inventory_complete"] is False:
        action = "ABSTAIN_INCONCLUSIVE"
    elif state == "none":
        action = "ABSTAIN_NOT_FOUND"
    elif state == "none-authorized":
        action = "ABSTAIN_INVALID_EVIDENCE"
    elif truth["current_evidence_sufficient"]:
        action = _supported_action(case)
    elif state == "partial":
        action = "PARTIAL_WITH_GAP"
    else:
        missing, _, invalid = observed_obligation_state(case)
        stale = any(
            not row["current"] and set(row["supports"]) & set(invalid)
            for row in retrieved(case)
        )
        action = "RETRIEVE_VALID" if stale else "RETRIEVE_MISSING"
    return result(
        case,
        "collection_hybrid",
        action,
        missing=truth["missing_obligation_ids"],
        cost=3.0,
        trace=trace,
    )


def run_oracle(case: dict[str, Any]) -> dict[str, Any]:
    return result(
        case,
        "oracle",
        case["truth"]["expected_action"],
        missing=case["truth"]["missing_obligation_ids"],
    )


def run_all(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        rows.append(run_nonempty(case))
        rows.append(run_scalar(case, "similarity", "similarity"))
        rows.append(run_scalar(case, "context_relevance", "context_relevance"))
        rows.append(run_scalar(case, "self_report", "self_report_sufficient"))
        rows.append(run_scalar(case, "semantic_consistency", "semantic_consistency"))
        rows.append(run_claim_entailment(case))
        rows.append(run_retrieved_obligation(case))
        rows.append(run_collection_hybrid(case))
        rows.append(run_oracle(case))
    return rows


def obligation_metrics(rows: list[dict[str, Any]]) -> tuple[float, float]:
    true_positive = false_positive = false_negative = 0
    for row in rows:
        predicted = set(row["reported_missing_obligation_ids"])
        gold = set(row["gold_missing_obligation_ids"])
        true_positive += len(predicted & gold)
        false_positive += len(predicted - gold)
        false_negative += len(gold - predicted)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    return precision, recall


def summarize_policy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    obligation_precision, obligation_recall = obligation_metrics(rows)
    accepted = [row for row in rows if row["answer_accepted"]]
    gap_rows = [row for row in rows if row["expected_action"] in GAP_ACTIONS]
    supported_claims = sum(row["supported_accepted_claims"] for row in rows)
    accepted_claims_total = sum(row["accepted_claims"] for row in rows)
    cited_supported = sum(row["cited_supported_claims"] for row in rows)
    return {
        "cases": len(rows),
        "exact_action_accuracy": sum(row["exact_action"] for row in rows) / len(rows),
        "answer_coverage": len(accepted) / len(rows),
        "selective_sufficiency_risk": sum(row["false_sufficient"] for row in accepted) / len(accepted) if accepted else 0.0,
        "false_sufficient_rate": sum(row["false_sufficient"] for row in rows) / len(rows),
        "false_insufficient_rate": sum(row["false_insufficient"] for row in rows) / len(rows),
        "critical_false_sufficient": sum(row["critical"] and row["false_sufficient"] for row in rows),
        "correct_gap_action_rate": sum(row["exact_action"] for row in gap_rows) / len(gap_rows),
        "obligation_gap_precision": obligation_precision,
        "obligation_gap_recall": obligation_recall,
        "accepted_claim_support_precision": supported_claims / accepted_claims_total if accepted_claims_total else 1.0,
        "supported_claim_attribution_rate": cited_supported / supported_claims if supported_claims else 1.0,
        "false_not_found": sum(row["false_not_found"] for row in rows),
        "mean_abstract_cost": sum(row["cost"] for row in rows) / len(rows),
        "action_distribution": dict(sorted(Counter(row["action"] for row in rows).items())),
        "exact_action_errors_by_stratum": dict(
            sorted(Counter(row["stratum"] for row in rows if not row["exact_action"]).items())
        ),
    }


def scalar_curve(cases: list[dict[str, Any]], signal: str) -> list[dict[str, Any]]:
    thresholds = sorted({signal_value(case, signal) for case in cases}, reverse=True)
    points = []
    for threshold in thresholds:
        accepted = [
            case
            for case in cases
            if retrieved(case) and signal_value(case, signal) >= threshold
        ]
        risk = sum(case["truth"]["expected_action"] != "ANSWER_FULL" for case in accepted)
        points.append(
            {
                "threshold": threshold,
                "coverage": len(accepted) / len(cases),
                "risk": risk / len(accepted) if accepted else 0.0,
                "accepted": len(accepted),
            }
        )
    return points


def closest_curve_point(points: list[dict[str, Any]], target_coverage: float) -> dict[str, Any]:
    return min(points, key=lambda point: (abs(point["coverage"] - target_coverage), point["risk"]))


def build_summary(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    policies = sorted({row["policy"] for row in results})
    metrics = {
        policy: summarize_policy([row for row in results if row["policy"] == policy])
        for policy in policies
    }
    curves = {
        "similarity": scalar_curve(cases, "similarity"),
        "context_relevance": scalar_curve(cases, "context_relevance"),
        "self_report": scalar_curve(cases, "self_report_sufficient"),
        "semantic_consistency": scalar_curve(cases, "semantic_consistency"),
    }
    hybrid = metrics["collection_hybrid"]
    matched = closest_curve_point(curves["self_report"], hybrid["answer_coverage"])
    coverage_gap = abs(matched["coverage"] - hybrid["answer_coverage"])
    matched_available = coverage_gap <= 0.06
    gates = {
        "zero_critical_false_sufficient": hybrid["critical_false_sufficient"] == 0,
        "gap_action_at_least_0.90": hybrid["correct_gap_action_rate"] >= 0.90,
        "obligation_recall_at_least_0.90": hybrid["obligation_gap_recall"] >= 0.90,
        "claim_support_precision_at_least_0.95": hybrid["accepted_claim_support_precision"] >= 0.95,
        "matched_coverage_point_available": matched_available,
        "matched_coverage_risk_gain_at_least_0.15": matched_available
        and matched["risk"] - hybrid["selective_sufficiency_risk"] >= 0.15,
        "zero_false_not_found": hybrid["false_not_found"] == 0,
    }
    return {
        "experiment_id": "PMLAB-SUFF-001",
        "status": "completed-exploratory-construction-test",
        "case_count": len(cases),
        "default_scalar_threshold": THRESHOLD,
        "policy_metrics": metrics,
        "risk_coverage": curves,
        "self_report_point_closest_to_hybrid_coverage": matched,
        "self_report_hybrid_coverage_gap": coverage_gap,
        "candidate_gate_checks": gates,
        "all_candidate_gates_pass": all(gates.values()),
        "interpretation_boundary": "authored labels and diagnostic-gold obligation mappings; state-machine construction only",
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# PMLAB evidence-sufficiency construction run v0",
        "",
        "Status: exploratory construction test on corpus frozen before runner implementation; not held out",
        "",
        "| Policy | Exact action | Coverage | Selective risk | False sufficient | False insufficient | Gap action | Obligation recall | Claim precision | False not-found | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    order = (
        "nonempty",
        "similarity",
        "context_relevance",
        "self_report",
        "semantic_consistency",
        "claim_entailment",
        "retrieved_obligation",
        "collection_hybrid",
        "oracle",
    )
    for policy in order:
        metric = summary["policy_metrics"][policy]
        lines.append(
            f"| {policy} | {metric['exact_action_accuracy']:.3f} | {metric['answer_coverage']:.3f} | "
            f"{metric['selective_sufficiency_risk']:.3f} | {metric['false_sufficient_rate']:.3f} | "
            f"{metric['false_insufficient_rate']:.3f} | {metric['correct_gap_action_rate']:.3f} | "
            f"{metric['obligation_gap_recall']:.3f} | {metric['accepted_claim_support_precision']:.3f} | "
            f"{metric['false_not_found']} | {metric['mean_abstract_cost']:.3f} |"
        )
    lines.extend(["", "## Candidate gate checks", ""])
    for gate, passed in summary["candidate_gate_checks"].items():
        lines.append(f"- `{gate}`: {'PASS' if passed else 'FAIL'}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The retrieved-obligation arm can recognize conflict, invalid evidence, missing facets, unsupported extra claims, and attribution gaps without converting a miss into storage loss. It cannot distinguish a recoverable collection miss from a truly absent facet without a collection-scope probe.",
            f"Its remaining exact-action errors are {json.dumps(summary['policy_metrics']['retrieved_obligation']['exact_action_errors_by_stratum'], sort_keys=True)}.",
            "",
            "The collection-aware hybrid consumes authored collection and obligation labels, so a pass validates only the typed decision contract. The next challenge must replace gold mappings with a frozen query decomposer, evidence mapper, real retrieval outputs, and independently reviewed labels.",
            f"The nearest self-report point differs from hybrid answer coverage by {summary['self_report_hybrid_coverage_gap']:.3f}; the matched-coverage gate remains closed when this exceeds 0.06.",
            "",
        ]
    )
    return "\n".join(lines)


def run(dataset: Path = DEFAULT_DATASET) -> dict[str, Any]:
    cases = read_jsonl(dataset / "cases.jsonl")
    manifest = read_json(dataset / "manifest.json")
    actual_hash = content_hash(cases)
    if actual_hash != manifest["case_sha256"]:
        raise ValueError(f"Frozen case hash mismatch: expected {manifest['case_sha256']}, got {actual_hash}")
    results = run_all(cases)
    summary = build_summary(cases, results)
    artifacts = dataset / "artifacts"
    write_jsonl(artifacts / "results.jsonl", results)
    write_json(artifacts / "summary.json", summary)
    write_json(
        artifacts / "manifest.json",
        {
            "experiment_id": "PMLAB-SUFF-001",
            "frozen_corpus_commit": "4ca0309",
            "case_sha256": actual_hash,
            "runner": "scripts/run_evidence_sufficiency_dev.py",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "policies": sorted(summary["policy_metrics"]),
            "network_or_model_calls": 0,
            "diagnostic_gold_arms": ["collection_hybrid", "oracle"],
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
