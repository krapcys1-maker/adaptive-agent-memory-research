#!/usr/bin/env python3
"""Validate a completed blind mapper review before any label reveal."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import review_pmlab_map_remaining_deepseek as contracts  # noqa: E402


PACKET_DIR = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1" / "independent-adjudication-v1"
BLIND_DIR = PACKET_DIR / "blind"
MANIFEST_PATH = BLIND_DIR / "manifest.json"
JOBS_PATH = BLIND_DIR / "jobs.jsonl"
ENTITY_PATH = BLIND_DIR / "entity-catalog-v1.json"
PREDICATE_PATH = BLIND_DIR / "predicate-catalog-v1.json"
DEFAULT_FORM = PACKET_DIR / "completed-review-form.jsonl"
DEFAULT_ATTESTATION = PACKET_DIR / "completed-attestation.json"
DEFAULT_RECEIPT = PACKET_DIR / "completed-review-receipt.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_blank_packet() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["status"] != "blank-blind-packet-awaiting-independent-reviewer":
        raise ValueError("packet is not in blank awaiting-review state")
    for name, expected in manifest["blind_hashes"].items():
        if sha256(BLIND_DIR / name) != expected:
            raise ValueError(f"blank packet hash mismatch: {name}")
    return manifest


def validate_completed(form_path: Path, attestation_path: Path) -> dict[str, Any]:
    manifest = verify_blank_packet()
    forms = read_jsonl(form_path)
    jobs = read_jsonl(JOBS_PATH)
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    expected_groups = {job["semantic_group_id"] for job in jobs}
    received_groups = {row.get("semantic_group_id") for row in forms}
    if len(forms) != len(expected_groups) or received_groups != expected_groups:
        raise ValueError("completed form group IDs do not exactly match packet")
    if len(received_groups) != len(forms):
        raise ValueError("duplicate form group")
    jobs_by_group = {job["semantic_group_id"]: job for job in jobs}
    entity_catalog = json.loads(ENTITY_PATH.read_text(encoding="utf-8"))
    predicate_catalog = json.loads(PREDICATE_PATH.read_text(encoding="utf-8"))
    entity_ids = {row["id"] for row in entity_catalog["entities"]}
    predicate_ids = {row["id"] for row in predicate_catalog["predicates"]}
    namespaces = set(predicate_catalog["namespaces"])
    reviewer_ids: set[str] = set()
    reviewer_families: set[str] = set()
    attestation_ids: set[str] = set()
    dispositions: dict[str, int] = {key: 0 for key in ("valid", "minor_issue", "material_issue", "exclude")}
    language_mismatch = 0
    for row in forms:
        group = row["semantic_group_id"]
        required = {
            "semantic_group_id", "source_commit", "reviewer_id_or_pseudonym",
            "reviewer_family_or_affiliation", "reviewed_at", "independent_labels",
            "language_equivalent", "stage_isolation", "disputed_or_underspecified_fields",
            "confidence", "exclude_recommendation", "rationale", "attestation_id",
        }
        if set(row) != required:
            raise ValueError(f"{group}: completed form fields differ from template")
        if row["source_commit"] != manifest["corpus_freeze_commit"]:
            raise ValueError(f"{group}: wrong source commit")
        for field in ("reviewer_id_or_pseudonym", "reviewer_family_or_affiliation", "reviewed_at", "rationale", "attestation_id"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise ValueError(f"{group}: {field} must be nonempty")
        if row["language_equivalent"] not in {True, False}:
            raise ValueError(f"{group}: language_equivalent must be boolean")
        language_mismatch += row["language_equivalent"] is False
        if row["stage_isolation"] not in dispositions:
            raise ValueError(f"{group}: invalid stage isolation disposition")
        dispositions[row["stage_isolation"]] += 1
        if row["confidence"] not in {"high", "medium", "low"}:
            raise ValueError(f"{group}: invalid confidence")
        if row["exclude_recommendation"] not in {True, False}:
            raise ValueError(f"{group}: exclude recommendation must be boolean")
        if row["stage_isolation"] == "exclude" and row["exclude_recommendation"] is not True:
            raise ValueError(f"{group}: excluded group must recommend exclusion")
        if not isinstance(row["disputed_or_underspecified_fields"], list) or any(not isinstance(item, str) or not item for item in row["disputed_or_underspecified_fields"]):
            raise ValueError(f"{group}: disputed fields must be strings")
        labels = row["independent_labels"]
        if not isinstance(labels, dict) or set(labels) != {"en", "pl"}:
            raise ValueError(f"{group}: both independent language labels required")
        case_by_language = {case["language"]: case for case in jobs_by_group[group]["cases"]}
        for language in ("en", "pl"):
            result = {
                "case_id": case_by_language[language]["case_id"],
                "independent_label": labels[language],
                "confidence": row["confidence"],
                "rationale": row["rationale"],
            }
            contracts.validate_label(result, case_by_language[language], entity_ids, predicate_ids, namespaces)
        reviewer_ids.add(row["reviewer_id_or_pseudonym"])
        reviewer_families.add(row["reviewer_family_or_affiliation"])
        attestation_ids.add(row["attestation_id"])
    if len(reviewer_ids) != 1 or len(reviewer_families) != 1 or len(attestation_ids) != 1:
        raise ValueError("reviewer identity/family/attestation must be consistent across form")
    required_attestation = {
        "attestation_id", "reviewer_id_or_pseudonym", "reviewer_family_or_affiliation",
        "review_started_at", "review_completed_at", "source_commit", "packet_manifest_sha256",
        "statements", "conflict_or_prior_exposure_notes", "signature_or_verifiable_acknowledgement",
    }
    if set(attestation) != required_attestation:
        raise ValueError("attestation fields differ from template")
    if attestation["attestation_id"] not in attestation_ids or attestation["reviewer_id_or_pseudonym"] not in reviewer_ids or attestation["reviewer_family_or_affiliation"] not in reviewer_families:
        raise ValueError("attestation identity does not match form")
    if attestation["source_commit"] != manifest["corpus_freeze_commit"] or attestation["packet_manifest_sha256"] != sha256(MANIFEST_PATH):
        raise ValueError("attestation source commit or packet manifest hash mismatch")
    for field in ("review_started_at", "review_completed_at", "signature_or_verifiable_acknowledgement"):
        if not isinstance(attestation[field], str) or not attestation[field].strip():
            raise ValueError(f"attestation {field} must be nonempty")
    statements = attestation.get("statements")
    expected_statements = {
        "did_not_inspect_author_gold", "did_not_inspect_advisory_predictions_or_scores",
        "did_not_inspect_candidate_implementations", "labeled_each_language_before_reveal",
        "disclosed_conflicts_or_prior_exposure",
    }
    if not isinstance(statements, dict) or set(statements) != expected_statements:
        raise ValueError("attestation statements differ from template")
    for field in expected_statements - {"disclosed_conflicts_or_prior_exposure"}:
        if statements[field] is not True:
            raise ValueError(f"required blind attestation is not true: {field}")
    if statements["disclosed_conflicts_or_prior_exposure"] not in {True, False}:
        raise ValueError("conflict disclosure statement must be boolean")
    if statements["disclosed_conflicts_or_prior_exposure"] is True and not str(attestation.get("conflict_or_prior_exposure_notes") or "").strip():
        raise ValueError("disclosed exposure requires notes")
    return {
        "status": "completed-independent-form-valid-before-reveal",
        "source_commit": manifest["corpus_freeze_commit"],
        "reviewer_id_or_pseudonym": next(iter(reviewer_ids)),
        "reviewer_family_or_affiliation": next(iter(reviewer_families)),
        "attestation_id": next(iter(attestation_ids)),
        "reviewed_groups": len(forms),
        "reviewed_rows": len(forms) * 2,
        "stage_isolation_dispositions": dispositions,
        "language_mismatch_groups": language_mismatch,
        "completed_review_form_sha256": sha256(form_path),
        "completed_attestation_sha256": sha256(attestation_path),
        "blank_packet_manifest_sha256": sha256(MANIFEST_PATH),
        "gold_revealed_by_validator": False,
        "authority": "integrity receipt only; adjudication not yet performed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form", type=Path, default=DEFAULT_FORM)
    parser.add_argument("--attestation", type=Path, default=DEFAULT_ATTESTATION)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    receipt = validate_completed(args.form, args.attestation)
    if args.write_receipt:
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
