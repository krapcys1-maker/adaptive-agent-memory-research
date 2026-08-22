#!/usr/bin/env python3
"""Run PMLAB-CLOSURE-001 policy ablations on frozen construction v1."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.build_collection_closure_corpus import canonical_json, content_hash
except ModuleNotFoundError:
    from build_collection_closure_corpus import canonical_json, content_hash


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "lab" / "pmlab-collection-closure-dev-v1"
FROZEN_CORPUS_SHA256 = "3450ebbed450904216c75366c9aac374bdafb5e9add3a13d44e59e74d69ee43c"
EVALUATION_TIME = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
ACCEPT_ACTIONS = {"ANSWER_SUPPORTED", "ANSWER_EXPLICIT_NEGATIVE", "REPORT_BOUNDED_ABSENCE"}
STRONG_NEGATIVE_TIERS = {
    "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
    "N3_PROPOSITION_FALSE",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def public_case(case: dict[str, Any]) -> dict[str, Any]:
    """Remove evaluation-only fields before every deployable policy call."""
    return {key: value for key, value in case.items() if key != "gold"}


def artifact_maps(dataset: Path) -> dict[str, dict[str, dict[str, Any]]]:
    specs = {
        "inventories": ("inventories.jsonl", "inventory_id"),
        "probes": ("probes.jsonl", "probe_set_id"),
        "certificates": ("certificates.jsonl", "certificate_id"),
        "insertions": ("insertions.jsonl", "insertion_set_id"),
    }
    return {
        name: {row[id_key]: row for row in read_jsonl(dataset / filename)}
        for name, (filename, id_key) in specs.items()
    }


def linked(case: dict[str, Any], artifacts: dict[str, dict[str, dict[str, Any]]]) -> tuple[dict[str, Any], ...]:
    observed = case["observed"]
    return (
        artifacts["inventories"][observed["inventory_id"]],
        artifacts["probes"][observed["probe_set_id"]],
        artifacts["certificates"][observed["certificate_id"]],
        artifacts["insertions"][observed["insertion_set_id"]],
    )


def matching_records(case: dict[str, Any], inventory: dict[str, Any]) -> list[dict[str, Any]]:
    scope = case["observed"]["mapped_query_shape"]
    predicates = set(scope["predicates"])
    entities = set(scope["entity_constraints"])
    return [
        row
        for row in inventory["records"]
        if row["predicate"] in predicates and row["entity"] in entities
    ]


def retrieved_matching_records(case: dict[str, Any], inventory: dict[str, Any]) -> list[dict[str, Any]]:
    retrieved_ids = set(case["observed"]["retrieved_record_ids"])
    return [row for row in matching_records(case, inventory) if row["record_id"] in retrieved_ids]


def record_state(case: dict[str, Any], inventory: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    rows = retrieved_matching_records(case, inventory)
    positives = [row for row in rows if row["polarity"] == "positive" and row["current"] and row["authorized"]]
    negatives = [row for row in rows if row["polarity"] == "negative" and row["current"] and row["authorized"]]
    conflict = len({canonical_json(row["value"]) for row in positives}) > 1
    return positives, negatives, conflict


def decision(tier: str, action: str, *, trace: list[str], evidence_ids: list[str] | None = None, certificate_id: str | None = None, probe_ids: list[str] | None = None, cost: float = 0.0) -> dict[str, Any]:
    return {
        "negative_tier": tier,
        "action": action,
        "trace": trace,
        "evidence_ids": evidence_ids or [],
        "certificate_id": certificate_id,
        "probe_ids": probe_ids or [],
        "cost": cost,
    }


def direct_record_decision(case: dict[str, Any], inventory: dict[str, Any], *, allow_negative_without_closure: bool, cost: float) -> dict[str, Any] | None:
    positives, negatives, conflict = record_state(case, inventory)
    if conflict:
        return decision("NONE", "ABSTAIN_CONFLICT", trace=["RETRIEVAL", "CONFLICT"], evidence_ids=[row["record_id"] for row in positives], cost=cost)
    if positives:
        return decision("NONE", "ANSWER_SUPPORTED", trace=["RETRIEVAL", "POSITIVE_EVIDENCE"], evidence_ids=[row["record_id"] for row in positives], cost=cost)
    if negatives and allow_negative_without_closure:
        return decision("N3_PROPOSITION_FALSE", "ANSWER_EXPLICIT_NEGATIVE", trace=["RETRIEVAL", "EXPLICIT_NEGATIVE"], evidence_ids=[row["record_id"] for row in negatives], cost=cost)
    return None


def run_global_cwa(case: dict[str, Any], artifacts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    inventory, _, _, _ = linked(case, artifacts)
    direct = direct_record_decision(case, inventory, allow_negative_without_closure=True, cost=0.1)
    if direct:
        return direct
    return decision("N3_PROPOSITION_FALSE", "ANSWER_EXPLICIT_NEGATIVE", trace=["NEGATION_BY_FAILURE"], cost=0.1)


def run_global_owa(case: dict[str, Any], artifacts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    inventory, _, _, _ = linked(case, artifacts)
    if not case["observed"]["retrieval_attempted"]:
        return decision("N0_NOT_RETRIEVED", "RETRIEVE", trace=["OWA", "NO_RETRIEVAL"], cost=0.2)
    direct = direct_record_decision(case, inventory, allow_negative_without_closure=False, cost=0.2)
    if direct:
        return direct
    return decision("N1_NOT_FOUND_IN_SEARCHED_SCOPE", "ABSTAIN_INCONCLUSIVE", trace=["OWA", "NO_CLOSURE"], cost=0.2)


def run_retrieval_saturation(case: dict[str, Any], artifacts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    inventory, _, _, _ = linked(case, artifacts)
    direct = direct_record_decision(case, inventory, allow_negative_without_closure=True, cost=1.0)
    if direct:
        return direct
    return decision("N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE", "REPORT_BOUNDED_ABSENCE", trace=["RETRIEVAL", "SATURATION_ASSUMED"], cost=1.0)


def run_coarse_completeness(case: dict[str, Any], artifacts: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    inventory, _, certificate, _ = linked(case, artifacts)
    if not case["observed"]["retrieval_attempted"]:
        return decision("N0_NOT_RETRIEVED", "RETRIEVE", trace=["COARSE", "NO_RETRIEVAL"], cost=1.2)
    direct = direct_record_decision(case, inventory, allow_negative_without_closure=True, cost=1.2)
    if direct:
        return direct
    if certificate["status"] == "complete":
        return decision("N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE", "REPORT_BOUNDED_ABSENCE", trace=["COARSE_COMPLETE_FLAG"], certificate_id=certificate["certificate_id"], cost=1.2)
    return decision("N1_NOT_FOUND_IN_SEARCHED_SCOPE", "ABSTAIN_INCONCLUSIVE", trace=["COARSE_NOT_COMPLETE"], cost=1.2)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def certificate_failure(case: dict[str, Any], inventory: dict[str, Any], probes: dict[str, Any], certificate: dict[str, Any]) -> tuple[str | None, str | None]:
    mapped = case["observed"]["mapped_query_shape"]
    scope = certificate["query_shape"]
    if len(mapped["entity_constraints"]) > 1:
        return "ambiguous-query", "ASK_CLARIFICATION"
    if mapped != scope:
        if mapped["entity_constraints"] != scope["entity_constraints"]:
            return "scope-map-mismatch", "REMAP_SCOPE"
        return "certificate-shape-mismatch", "ABSTAIN_INCONCLUSIVE"
    freshness = certificate["freshness"]
    if certificate["status"] == "expired" or parse_time(freshness["expires_at"]) <= EVALUATION_TIME:
        return "expired", "PROBE_SCOPE"
    if freshness["certified_mutation_sequence"] != inventory["mutation_sequence"]:
        return "mutation-sequence-mismatch", "PROBE_SCOPE"
    exceptions = certificate["exceptions"]
    if exceptions["unauthorized"]:
        return "unauthorized-domain", "ABSTAIN_INCONCLUSIVE"
    if exceptions["unavailable"] or exceptions["unsearched"]:
        return "domain-not-covered", "PROBE_SCOPE"
    if set(inventory["registered_domains"]) != set(inventory["available_domains"]):
        return "registered-domain-unavailable", "PROBE_SCOPE"
    if inventory["expected_member_count"] != inventory["observed_member_count"]:
        return "enumeration-count-mismatch", "PROBE_SCOPE"
    if any(row["status"] != "success" for row in probes["results"]):
        return "probe-failure", "PROBE_SCOPE"
    if certificate["status"] != "complete":
        return "certificate-not-complete", "ABSTAIN_INCONCLUSIVE"
    return None, None


def run_query_certificate(case: dict[str, Any], artifacts: dict[str, dict[str, dict[str, Any]]], *, check_insertions: bool) -> dict[str, Any]:
    inventory, probes, certificate, insertions = linked(case, artifacts)
    cost = 3.0 if check_insertions else 2.0
    if not case["observed"]["retrieval_attempted"]:
        return decision("N0_NOT_RETRIEVED", "RETRIEVE", trace=["NO_RETRIEVAL"], cost=cost)

    direct = direct_record_decision(case, inventory, allow_negative_without_closure=False, cost=cost)
    if direct:
        return direct

    failure, action = certificate_failure(case, inventory, probes, certificate)
    if failure:
        return decision("NONE" if action == "ASK_CLARIFICATION" else "N1_NOT_FOUND_IN_SEARCHED_SCOPE", action or "ABSTAIN_INCONCLUSIVE", trace=["CERTIFICATE_REJECTED", failure], certificate_id=certificate["certificate_id"], probe_ids=[row["probe_id"] for row in probes["results"]], cost=cost)

    if check_insertions and any(row["admissible"] and row["changes_query_answer"] for row in insertions["allowed_insertions"]):
        return decision("N1_NOT_FOUND_IN_SEARCHED_SCOPE", "ABSTAIN_INCONCLUSIVE", trace=["CERTIFICATE_VALIDATED", "COUNTEREXAMPLE_INSERTION"], certificate_id=certificate["certificate_id"], probe_ids=[row["probe_id"] for row in probes["results"]], cost=cost)

    _, negatives, _ = record_state(case, inventory)
    if negatives:
        return decision("N3_PROPOSITION_FALSE", "ANSWER_EXPLICIT_NEGATIVE", trace=["CERTIFICATE_VALIDATED", "EXPLICIT_NEGATIVE"], evidence_ids=[row["record_id"] for row in negatives], certificate_id=certificate["certificate_id"], probe_ids=[row["probe_id"] for row in probes["results"]], cost=cost)
    return decision("N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE", "REPORT_BOUNDED_ABSENCE", trace=["CERTIFICATE_VALIDATED", "NO_AUTHORIZED_CURRENT_RECORD"], certificate_id=certificate["certificate_id"], probe_ids=[row["probe_id"] for row in probes["results"]], cost=cost)


def run_oracle(case: dict[str, Any], _: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    gold = case["gold"]
    return decision(gold["expected_negative_tier"], gold["expected_action"], trace=["DIAGNOSTIC_GOLD"], cost=0.0)


DEPLOYABLE_ARMS: dict[str, Callable[[dict[str, Any], dict[str, dict[str, dict[str, Any]]]], dict[str, Any]]] = {
    "global_cwa": run_global_cwa,
    "global_owa": run_global_owa,
    "retrieval_saturation": run_retrieval_saturation,
    "coarse_completeness": run_coarse_completeness,
    "query_certificate": lambda case, artifacts: run_query_certificate(case, artifacts, check_insertions=False),
    "certificate_plus_insertion": lambda case, artifacts: run_query_certificate(case, artifacts, check_insertions=True),
}


def is_unsafe_strong_negative(predicted: str, gold: str) -> bool:
    if predicted == "N3_PROPOSITION_FALSE":
        return gold != "N3_PROPOSITION_FALSE"
    if predicted == "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE":
        return gold not in {"N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE", "N3_PROPOSITION_FALSE"}
    return False


def score(case: dict[str, Any], arm: str, output: dict[str, Any]) -> dict[str, Any]:
    gold = case["gold"]
    accepted = output["action"] in ACCEPT_ACTIONS
    unsafe = is_unsafe_strong_negative(output["negative_tier"], gold["expected_negative_tier"])
    return {
        "case_id": case["case_id"],
        "pair_group": case["pair_group"],
        "language": case["language"],
        "stratum": gold["stratum"],
        "critical": gold["critical"],
        "arm": arm,
        **output,
        "expected_negative_tier": gold["expected_negative_tier"],
        "expected_action": gold["expected_action"],
        "exact_tier": output["negative_tier"] == gold["expected_negative_tier"],
        "exact_action": output["action"] == gold["expected_action"],
        "accepted": accepted,
        "unsafe_strong_negative": unsafe,
        "adversarial_certificate_claim": gold["adversarial_certificate_claim"],
    }


def run_all(cases: list[dict[str, Any]], artifacts: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        visible = public_case(case)
        for arm, policy in DEPLOYABLE_ARMS.items():
            rows.append(score(case, arm, policy(visible, artifacts)))
        rows.append(score(case, "oracle", run_oracle(case, artifacts)))
    return rows


def summarize_arm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted = [row for row in rows if row["accepted"]]
    critical = [row for row in rows if row["critical"]]
    strong = [row for row in rows if row["negative_tier"] in STRONG_NEGATIVE_TIERS]
    positives = [row for row in rows if row["expected_action"] == "ANSWER_SUPPORTED"]
    adversarial = [row for row in rows if row["adversarial_certificate_claim"]]
    invalidation = [row for row in rows if row["stratum"] in {"expired-exact-certificate", "scope-mutated-after-certificate"}]
    unsafe = [row for row in rows if row["unsafe_strong_negative"]]
    return {
        "cases": len(rows),
        "exact_tier_accuracy": sum(row["exact_tier"] for row in rows) / len(rows),
        "exact_action_accuracy": sum(row["exact_action"] for row in rows) / len(rows),
        "critical_tier_accuracy": sum(row["exact_tier"] for row in critical) / len(critical),
        "action_coverage": len(accepted) / len(rows),
        "selective_decision_risk": sum(not (row["exact_tier"] and row["exact_action"]) for row in accepted) / len(accepted) if accepted else 0.0,
        "unsafe_strong_negative_rate": len(unsafe) / len(rows),
        "unsafe_strong_negative_risk": len(unsafe) / len(strong) if strong else 0.0,
        "critical_unsafe_strong_negatives": sum(row["critical"] for row in unsafe),
        "unsupported_n3": sum(row["negative_tier"] == "N3_PROPOSITION_FALSE" and row["expected_negative_tier"] != "N3_PROPOSITION_FALSE" for row in rows),
        "unsupported_n2": sum(row["negative_tier"] == "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE" and row["expected_negative_tier"] not in {"N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE", "N3_PROPOSITION_FALSE"} for row in rows),
        "positive_safe_coverage": sum(row["action"] == "ANSWER_SUPPORTED" for row in positives) / len(positives),
        "counterexample_insertion_detection": sum(row["negative_tier"] not in STRONG_NEGATIVE_TIERS for row in adversarial) / len(adversarial),
        "expiry_mutation_invalidation_accuracy": sum(row["negative_tier"] not in STRONG_NEGATIVE_TIERS for row in invalidation) / len(invalidation),
        "accepted_strong_with_certificate": sum(bool(row["certificate_id"]) for row in strong) / len(strong) if strong else 1.0,
        "accepted_strong_with_probe_ids": sum(bool(row["probe_ids"]) for row in strong) / len(strong) if strong else 1.0,
        "mean_abstract_cost": sum(row["cost"] for row in rows) / len(rows),
        "action_distribution": dict(sorted(Counter(row["action"] for row in rows).items())),
        "tier_errors_by_stratum": dict(sorted(Counter(row["stratum"] for row in rows if not row["exact_tier"]).items())),
        "action_errors_by_stratum": dict(sorted(Counter(row["stratum"] for row in rows if not row["exact_action"]).items())),
    }


def build_summary(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        arm: summarize_arm([row for row in results if row["arm"] == arm])
        for arm in (*DEPLOYABLE_ARMS, "oracle")
    }
    candidate = metrics["certificate_plus_insertion"]
    baseline = metrics["retrieval_saturation"]
    coverage_gap = abs(candidate["action_coverage"] - baseline["action_coverage"])
    matched_available = coverage_gap <= 0.06
    gates = {
        "zero_unsupported_n3": candidate["unsupported_n3"] == 0,
        "zero_unsupported_n2": candidate["unsupported_n2"] == 0,
        "zero_critical_unsafe_strong_negatives": candidate["critical_unsafe_strong_negatives"] == 0,
        "mutation_and_expiry_invalidation_1.0": candidate["expiry_mutation_invalidation_accuracy"] == 1.0,
        "critical_tier_accuracy_at_least_0.95": candidate["critical_tier_accuracy"] >= 0.95,
        "positive_safe_coverage_at_least_0.90": candidate["positive_safe_coverage"] >= 0.90,
        "counterexample_insertion_detection_1.0": candidate["counterexample_insertion_detection"] == 1.0,
        "strong_negative_provenance_1.0": candidate["accepted_strong_with_certificate"] == 1.0 and candidate["accepted_strong_with_probe_ids"] == 1.0,
        "matched_coverage_point_available": matched_available,
        "matched_coverage_unsafe_risk_gain_at_least_0.15": matched_available and baseline["unsafe_strong_negative_risk"] - candidate["unsafe_strong_negative_risk"] >= 0.15,
    }
    return {
        "experiment_id": "PMLAB-CLOSURE-001",
        "dataset": "pmlab-collection-closure-dev-v1",
        "status": "completed-exploratory-construction-test",
        "case_count": len(cases),
        "policy_metrics": metrics,
        "candidate_gate_checks": gates,
        "all_candidate_gates_pass": all(gates.values()),
        "retrieval_candidate_coverage_gap": coverage_gap,
        "interpretation_boundary": "authored synthetic inventories certificates probes insertions and visible gold; state-machine construction only",
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# PMLAB collection-closure construction run v1",
        "",
        "Status: exploratory construction test on corpus frozen before runner implementation; not held out",
        "",
        "| Arm | Tier accuracy | Action accuracy | Critical tier | Coverage | Selective risk | Unsafe negative | N3 errors | N2 errors | Insert detection | Invalidations | Positive coverage | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in (*DEPLOYABLE_ARMS, "oracle"):
        metric = summary["policy_metrics"][arm]
        lines.append(
            f"| {arm} | {metric['exact_tier_accuracy']:.3f} | {metric['exact_action_accuracy']:.3f} | "
            f"{metric['critical_tier_accuracy']:.3f} | {metric['action_coverage']:.3f} | {metric['selective_decision_risk']:.3f} | "
            f"{metric['unsafe_strong_negative_risk']:.3f} | {metric['unsupported_n3']} | {metric['unsupported_n2']} | "
            f"{metric['counterexample_insertion_detection']:.3f} | {metric['expiry_mutation_invalidation_accuracy']:.3f} | "
            f"{metric['positive_safe_coverage']:.3f} | {metric['mean_abstract_cost']:.2f} |"
        )
    lines.extend(["", "## Candidate gate checks", ""])
    for gate, passed in summary["candidate_gate_checks"].items():
        lines.append(f"- `{gate}`: {'PASS' if passed else 'FAIL'}")
    candidate = summary["policy_metrics"]["certificate_plus_insertion"]
    certificate = summary["policy_metrics"]["query_certificate"]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Global CWA and retrieval saturation turn missing evidence into unsupported strong negatives. A coarse completeness flag still trusts wrong scope, stale version, missing domains, and unsound certificate claims.",
            "",
            f"The query-specific certificate arm leaves {certificate['unsupported_n2']} unsupported N2 decisions; the insertion check leaves {candidate['unsupported_n2']}. This isolates whether an admissible missing insertion can change the answer.",
            f"The candidate's remaining tier errors are {json.dumps(candidate['tier_errors_by_stratum'], sort_keys=True)}.",
            "",
            "The construction does not validate natural-language obligation decomposition. The multi-facet case intentionally remains a boundary: one facet can be supported while another has only N1 closure. A later decomposer/mapper arm and unseen split are required.",
            f"Candidate and retrieval-saturation action coverage differ by {summary['retrieval_candidate_coverage_gap']:.3f}; matched-coverage claims remain blocked when the gap exceeds 0.06.",
            "",
        ]
    )
    return "\n".join(lines)


def verify_frozen(dataset: Path, bundle: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]) -> None:
    actual = content_hash(bundle)
    if actual != manifest["corpus_sha256"] or actual != FROZEN_CORPUS_SHA256:
        raise ValueError(f"Frozen corpus hash mismatch: manifest={manifest['corpus_sha256']} expected={FROZEN_CORPUS_SHA256} actual={actual}")
    for key, rows in bundle.items():
        if content_hash(rows) != manifest["artifact_sha256"][key]:
            raise ValueError(f"Frozen artifact hash mismatch: {key}")


def run(dataset: Path = DEFAULT_DATASET) -> dict[str, Any]:
    manifest = read_json(dataset / "manifest.json")
    bundle = {key: read_jsonl(dataset / f"{key}.jsonl") for key in ("cases", "inventories", "probes", "certificates", "insertions")}
    verify_frozen(dataset, bundle, manifest)
    artifacts = artifact_maps(dataset)
    results = run_all(bundle["cases"], artifacts)
    summary = build_summary(bundle["cases"], results)
    output = dataset / "artifacts"
    write_jsonl(output / "results.jsonl", results)
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "experiment_id": "PMLAB-CLOSURE-001",
            "frozen_corpus_commit": "e9649ac",
            "corpus_sha256": manifest["corpus_sha256"],
            "runner": "scripts/run_collection_closure_dev.py",
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "network_or_model_calls": 0,
            "deployable_arms_receive_gold": False,
            "diagnostic_gold_arms": ["oracle"],
        },
    )
    (dataset / "report.md").write_text(render_report(summary), encoding="utf-8", newline="\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    print(json.dumps(run(args.dataset), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
