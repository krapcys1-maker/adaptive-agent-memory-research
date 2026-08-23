#!/usr/bin/env python3
"""Validate a completed PMLAB-UTILITY-001 audit without interpreting its verdicts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BLIND = ROOT / "data" / "lab" / "pmlab-future-utility-v0" / "independent-audit-v0" / "blind"
MANIFEST = BLIND / "manifest.json"
QUESTIONS = BLIND / "questions.json"
DEFAULT_FORM = BLIND.parent / "completed-review-form.json"
DEFAULT_ATTESTATION = BLIND.parent / "completed-attestation.json"
DEFAULT_RECEIPT = BLIND.parent / "completed-review-receipt.json"

VERDICTS = {"pass", "conditional", "fail", "not_assessable"}
SEVERITIES = {"none", "minor", "major", "blocking"}
REVIEWER_KINDS = {"human_external", "human_project", "model_external_author_operated", "model_project_operated"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def timestamp(value: Any) -> datetime:
    if not nonempty(value):
        raise ValueError("timestamp must be a nonempty string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def verify_blank_packet() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "blank-gold-free-packet-awaiting-review":
        raise ValueError("packet is not blank and awaiting review")
    if manifest["author_answer_key_present"] is not False:
        raise ValueError("packet claims an author answer key")
    for name, expected in manifest["hashes"].items():
        if sha256(BLIND / name) != expected:
            raise ValueError(f"audit packet hash mismatch: {name}")
    return manifest


def validate_completed(form_path: Path, attestation_path: Path) -> dict[str, Any]:
    manifest = verify_blank_packet()
    form = json.loads(form_path.read_text(encoding="utf-8"))
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    expected_top = {
        "packet_id", "source_revision", "reviewer", "findings", "gate_recommendations",
        "blocking_findings", "residual_risks", "overall_rationale", "attestation_id",
    }
    if set(form) != expected_top:
        raise ValueError("completed form fields differ from template")
    if form["packet_id"] != manifest["packet_id"] or form["source_revision"] != manifest["source_revision"]:
        raise ValueError("completed form targets the wrong packet or revision")

    reviewer = form["reviewer"]
    expected_reviewer = {
        "reviewer_id_or_pseudonym", "reviewer_kind", "family_or_affiliation",
        "review_started_at", "review_completed_at",
    }
    if not isinstance(reviewer, dict) or set(reviewer) != expected_reviewer:
        raise ValueError("reviewer fields differ from template")
    for field in ("reviewer_id_or_pseudonym", "family_or_affiliation"):
        if not nonempty(reviewer[field]):
            raise ValueError(f"reviewer {field} must be nonempty")
    if reviewer["reviewer_kind"] not in REVIEWER_KINDS:
        raise ValueError("invalid reviewer kind")
    started = timestamp(reviewer["review_started_at"])
    completed = timestamp(reviewer["review_completed_at"])
    if completed < started:
        raise ValueError("review completion precedes start")

    question_rows = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    expected_ids = [row["question_id"] for row in question_rows]
    findings = form["findings"]
    if not isinstance(findings, list) or [row.get("question_id") for row in findings] != expected_ids:
        raise ValueError("findings must cover every question exactly once in packet order")
    expected_finding = {"question_id", "verdict", "severity", "evidence_locators", "rationale", "required_change"}
    blocking: list[str] = []
    verdict_counts = {key: 0 for key in sorted(VERDICTS)}
    severity_counts = {key: 0 for key in sorted(SEVERITIES)}
    for row in findings:
        question_id = row["question_id"]
        if set(row) != expected_finding:
            raise ValueError(f"{question_id}: finding fields differ from template")
        if row["verdict"] not in VERDICTS or row["severity"] not in SEVERITIES:
            raise ValueError(f"{question_id}: invalid verdict or severity")
        if not isinstance(row["evidence_locators"], list) or not row["evidence_locators"] or any(not nonempty(item) for item in row["evidence_locators"]):
            raise ValueError(f"{question_id}: at least one evidence locator is required")
        if not nonempty(row["rationale"]):
            raise ValueError(f"{question_id}: rationale is required")
        if row["verdict"] == "pass":
            if row["severity"] != "none" or row["required_change"] is not None:
                raise ValueError(f"{question_id}: pass requires severity none and null required_change")
        else:
            if row["severity"] == "none" or not nonempty(row["required_change"]):
                raise ValueError(f"{question_id}: non-pass requires severity and concrete required_change")
        if row["severity"] == "blocking":
            blocking.append(question_id)
        verdict_counts[row["verdict"]] += 1
        severity_counts[row["severity"]] += 1

    if not isinstance(form["blocking_findings"], list) or form["blocking_findings"] != blocking:
        raise ValueError("blocking_findings must exactly list blocking question IDs in packet order")
    if not isinstance(form["residual_risks"], list) or any(not nonempty(item) for item in form["residual_risks"]):
        raise ValueError("residual risks must be a string list")
    if not nonempty(form["overall_rationale"]) or not nonempty(form["attestation_id"]):
        raise ValueError("overall rationale and attestation ID are required")

    gates = form["gate_recommendations"]
    if not isinstance(gates, dict) or set(gates) != {"T1", "T2", "T3", "T4"}:
        raise ValueError("gate recommendations differ from template")
    if gates["T1"] not in {"deny", "conditional", "allow_shadow_only"} or gates["T2"] not in {"deny", "conditional"}:
        raise ValueError("invalid T1 or T2 recommendation")
    if gates["T3"] != "deny" or gates["T4"] != "deny":
        raise ValueError("this packet cannot allow T3 or T4")
    if blocking and gates["T1"] != "deny":
        raise ValueError("blocking findings require T1 deny")
    if verdict_counts["fail"] and gates["T1"] == "allow_shadow_only":
        raise ValueError("unresolved failed findings prohibit T1 allow_shadow_only")

    expected_attestation = {
        "attestation_id", "reviewer_id_or_pseudonym", "reviewer_kind", "family_or_affiliation",
        "source_revision", "packet_manifest_sha256", "statements", "conflicts_or_prior_exposure",
        "limitations", "signature_or_verifiable_acknowledgement",
    }
    if set(attestation) != expected_attestation:
        raise ValueError("attestation fields differ from template")
    identity_fields = ("attestation_id", "reviewer_id_or_pseudonym", "reviewer_kind", "family_or_affiliation")
    expected_identity = {
        "attestation_id": form["attestation_id"],
        "reviewer_id_or_pseudonym": reviewer["reviewer_id_or_pseudonym"],
        "reviewer_kind": reviewer["reviewer_kind"],
        "family_or_affiliation": reviewer["family_or_affiliation"],
    }
    if any(attestation[field] != expected_identity[field] for field in identity_fields):
        raise ValueError("attestation identity does not match form")
    if attestation["source_revision"] != manifest["source_revision"] or attestation["packet_manifest_sha256"] != sha256(MANIFEST):
        raise ValueError("attestation packet revision or manifest hash mismatch")
    statements = attestation["statements"]
    expected_statements = {
        "reviewed_only_listed_subject_artifacts", "did_not_receive_author_answer_key",
        "actively_sought_falsifying_evidence", "disclosed_conflicts_and_prior_exposure",
        "understands_review_does_not_authorize_T2_T4",
    }
    if not isinstance(statements, dict) or set(statements) != expected_statements or any(value is not True for value in statements.values()):
        raise ValueError("all attestation statements must be exactly true")
    for field in ("conflicts_or_prior_exposure", "limitations", "signature_or_verifiable_acknowledgement"):
        if not nonempty(attestation[field]):
            raise ValueError(f"attestation {field} must be nonempty; use 'none known' when accurate")

    return {
        "status": "completed-audit-form-integrity-valid",
        "packet_id": manifest["packet_id"],
        "source_revision": manifest["source_revision"],
        "reviewer_id_or_pseudonym": reviewer["reviewer_id_or_pseudonym"],
        "reviewer_kind": reviewer["reviewer_kind"],
        "verdict_counts": verdict_counts,
        "severity_counts": severity_counts,
        "gate_recommendations": gates,
        "completed_review_form_sha256": sha256(form_path),
        "completed_attestation_sha256": sha256(attestation_path),
        "blank_packet_manifest_sha256": sha256(MANIFEST),
        "authority": "mechanical integrity receipt only; does not endorse findings or create legal, privacy, statistical, or institutional approval",
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

