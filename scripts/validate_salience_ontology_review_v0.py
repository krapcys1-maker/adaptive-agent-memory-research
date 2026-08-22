#!/usr/bin/env python3
"""Validate a completed independent operational-salience ontology review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BLIND = ROOT / "data" / "lab" / "pmlab-salience-ontology-review-v0" / "blind"
MANIFEST = BLIND / "manifest.json"
DEFAULT_REVIEW = BLIND.parent / "completed-review.json"
DEFAULT_ATTESTATION = BLIND.parent / "completed-attestation.json"
DEFAULT_RECEIPT = BLIND.parent / "completed-review-receipt.json"
DECISIONS = {"accept", "revise", "reject"}
OBSERVABILITY = {"clear", "partial", "not_observable"}
INDEPENDENCE = {"yes", "conditional", "no"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{name} must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains duplicates")
    return value


def verify_packet() -> dict[str, Any]:
    manifest = load(MANIFEST)
    if manifest["status"] != "blank-gold-free-packet-awaiting-independent-reviewer":
        raise ValueError("packet is not at the independent ontology-review gate")
    for name, expected in manifest["blind_hashes"].items():
        if sha256(BLIND / name) != expected:
            raise ValueError(f"blank packet hash mismatch: {name}")
    return manifest


def validate_completed(review_path: Path, attestation_path: Path) -> dict[str, Any]:
    manifest = verify_packet()
    contract = load(BLIND / "factor-contract.json")
    probes = [json.loads(line) for line in (BLIND / "probe-cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    review = load(review_path)
    attestation = load(attestation_path)
    expected_review_fields = {
        "review_id", "reviewer_id_or_pseudonym", "reviewer_family_or_affiliation", "reviewed_at",
        "source_evidence_commit", "factor_reviews", "probe_reviews", "missing_factors",
        "redundant_or_nonidentifiable_factors", "whole_packet_decision", "whole_packet_rationale", "attestation_id",
    }
    if set(review) != expected_review_fields:
        raise ValueError("completed review fields differ from blank contract")
    for field in ("review_id", "reviewer_id_or_pseudonym", "reviewer_family_or_affiliation", "reviewed_at", "whole_packet_rationale", "attestation_id"):
        nonempty(review[field], f"review.{field}")
    if review["source_evidence_commit"] != manifest["source_evidence_commit"]:
        raise ValueError("review source evidence commit mismatch")
    if review["whole_packet_decision"] not in DECISIONS:
        raise ValueError("invalid whole-packet decision")
    string_list(review["missing_factors"], "missing_factors")
    string_list(review["redundant_or_nonidentifiable_factors"], "redundant_or_nonidentifiable_factors")

    factor_ids = {row["factor_id"] for row in contract["factors"]}
    factor_reviews = review["factor_reviews"]
    if not isinstance(factor_reviews, list) or {row.get("factor_id") for row in factor_reviews} != factor_ids or len(factor_reviews) != len(factor_ids):
        raise ValueError("factor reviews do not exactly cover the contract")
    factor_decisions = {key: 0 for key in DECISIONS}
    for row in factor_reviews:
        required = {"factor_id", "decision", "operational_observability", "independent_from_other_factors", "overlaps_with", "leakage_or_safety_risks", "proposed_revision", "rationale"}
        if set(row) != required:
            raise ValueError(f"{row.get('factor_id')}: factor-review fields differ from contract")
        if row["decision"] not in DECISIONS:
            raise ValueError(f"{row['factor_id']}: invalid decision")
        factor_decisions[row["decision"]] += 1
        if row["operational_observability"] not in OBSERVABILITY or row["independent_from_other_factors"] not in INDEPENDENCE:
            raise ValueError(f"{row['factor_id']}: invalid observability or independence judgment")
        overlaps = string_list(row["overlaps_with"], f"{row['factor_id']}.overlaps_with")
        if any(item not in factor_ids - {row["factor_id"]} for item in overlaps):
            raise ValueError(f"{row['factor_id']}: overlap references an unknown/self factor")
        string_list(row["leakage_or_safety_risks"], f"{row['factor_id']}.leakage_or_safety_risks")
        nonempty(row["rationale"], f"{row['factor_id']}.rationale")
        if row["decision"] == "revise":
            nonempty(row["proposed_revision"], f"{row['factor_id']}.proposed_revision")
        elif row["proposed_revision"] is not None and not isinstance(row["proposed_revision"], str):
            raise ValueError(f"{row['factor_id']}: proposed revision must be null or string")

    probe_ids = {row["case_id"] for row in probes}
    probe_reviews = review["probe_reviews"]
    if not isinstance(probe_reviews, list) or {row.get("case_id") for row in probe_reviews} != probe_ids or len(probe_reviews) != len(probe_ids):
        raise ValueError("probe reviews do not exactly cover the packet")
    allowed_actions = set(contract["allowed_actions"])
    prohibited_actions = set(contract["always_prohibited_actions"])
    ambiguous = 0
    for row in probe_reviews:
        required = {"case_id", "supported_factor_ids", "unsupported_factor_ids", "unresolved_factor_ids", "permitted_actions", "prohibited_actions", "material_ambiguity", "rationale"}
        if set(row) != required:
            raise ValueError(f"{row.get('case_id')}: probe-review fields differ from contract")
        sets = [set(string_list(row[key], f"{row['case_id']}.{key}")) for key in ("supported_factor_ids", "unsupported_factor_ids", "unresolved_factor_ids")]
        if any(not values <= factor_ids for values in sets) or (sets[0] & sets[1]) or (sets[0] & sets[2]) or (sets[1] & sets[2]):
            raise ValueError(f"{row['case_id']}: invalid or overlapping factor judgments")
        if set.union(*sets) != factor_ids:
            raise ValueError(f"{row['case_id']}: every factor must be supported, unsupported, or unresolved")
        permitted = set(string_list(row["permitted_actions"], f"{row['case_id']}.permitted_actions"))
        prohibited = set(string_list(row["prohibited_actions"], f"{row['case_id']}.prohibited_actions"))
        if not permitted <= allowed_actions or not prohibited_actions <= prohibited or permitted & prohibited:
            raise ValueError(f"{row['case_id']}: invalid action judgment")
        if row["material_ambiguity"] not in {True, False}:
            raise ValueError(f"{row['case_id']}: material_ambiguity must be boolean")
        ambiguous += row["material_ambiguity"] is True
        nonempty(row["rationale"], f"{row['case_id']}.rationale")

    expected_attestation_fields = {
        "attestation_id", "reviewer_id_or_pseudonym", "reviewer_family_or_affiliation", "review_started_at",
        "review_completed_at", "source_evidence_commit", "packet_manifest_sha256", "completed_review_sha256",
        "statements", "tools_conflicts_or_prior_exposure_notes", "signature_or_verifiable_acknowledgement",
    }
    if set(attestation) != expected_attestation_fields:
        raise ValueError("completed attestation fields differ from blank contract")
    for left, right in (("attestation_id", "attestation_id"), ("reviewer_id_or_pseudonym", "reviewer_id_or_pseudonym"), ("reviewer_family_or_affiliation", "reviewer_family_or_affiliation")):
        if attestation[left] != review[right]:
            raise ValueError(f"attestation {left} does not match review")
    for field in ("review_started_at", "review_completed_at", "signature_or_verifiable_acknowledgement"):
        nonempty(attestation[field], f"attestation.{field}")
    if attestation["source_evidence_commit"] != manifest["source_evidence_commit"]:
        raise ValueError("attestation source evidence commit mismatch")
    if attestation["packet_manifest_sha256"] != sha256(MANIFEST) or attestation["completed_review_sha256"] != sha256(review_path):
        raise ValueError("attestation hashes do not bind the frozen packet and completed review")
    expected_statements = {
        "did_not_inspect_or_run_a_candidate_controller", "did_not_receive_author_preferred_probe_answers",
        "did_not_treat_salience_as_truth_or_validity", "reviewed_every_factor_and_probe_before_author_discussion",
        "disclosed_tools_conflicts_and_prior_exposure",
    }
    if not isinstance(attestation["statements"], dict) or set(attestation["statements"]) != expected_statements:
        raise ValueError("attestation statements differ from contract")
    if any(attestation["statements"][key] is not True for key in expected_statements):
        raise ValueError("every independent-review attestation statement must be true")
    nonempty(attestation["tools_conflicts_or_prior_exposure_notes"], "attestation.tools_conflicts_or_prior_exposure_notes")
    return {
        "status": "completed-independent-ontology-review-valid-before-author-discussion",
        "whole_packet_decision": review["whole_packet_decision"],
        "factor_decisions": dict(sorted(factor_decisions.items())),
        "materially_ambiguous_probes": ambiguous,
        "reviewer_id_or_pseudonym": review["reviewer_id_or_pseudonym"],
        "reviewer_family_or_affiliation": review["reviewer_family_or_affiliation"],
        "source_evidence_commit": manifest["source_evidence_commit"],
        "completed_review_sha256": sha256(review_path),
        "completed_attestation_sha256": sha256(attestation_path),
        "blank_packet_manifest_sha256": sha256(MANIFEST),
        "controller_unlocked": False,
        "authority": "integrity receipt only; author must disposition revisions before corpus construction",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--attestation", type=Path, default=DEFAULT_ATTESTATION)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    receipt = validate_completed(args.review, args.attestation)
    if args.write_receipt:
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
