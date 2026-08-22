#!/usr/bin/env python3
"""Historical validator for PMLAB v0 annotation submissions.

The validator checks packet integrity and annotation contracts.  It never reads
author labels, computes agreement with them, or unlocks a baseline run. The v0
packet is invalidated, so packet verification now rejects it by design.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "data" / "lab" / "project-memory-lab-v0-construction"
BLIND = PACKET / "blind"
MANIFEST = PACKET / "manifest.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_packet() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "independent-leakage-accepted-awaiting-dual-annotation":
        raise ValueError("packet is not independently leakage-accepted and awaiting dual annotation")
    if manifest["baseline_run_permitted"] is not False or manifest["author_labels_are_gold"] is not False:
        raise ValueError("construction safety flags changed")
    for relative, expected in manifest["hashes"].items():
        if relative.startswith("internal/") or relative == "corpus.jsonl":
            continue
        path = PACKET / relative
        if sha256(path) != expected:
            raise ValueError(f"blind packet hash mismatch: {relative}")
    return manifest


def validate_one(form_path: Path, attestation_path: Path, slot: str) -> dict[str, Any]:
    manifest = verify_packet()
    forms = read_jsonl(form_path)
    queries = read_jsonl(BLIND / "queries.jsonl")
    corpus = read_jsonl(BLIND / "corpus.jsonl")
    attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
    expected_ids = {row["example_id"] for row in queries}
    received_ids = [row.get("example_id") for row in forms]
    if len(forms) != manifest["queries"] or set(received_ids) != expected_ids or len(received_ids) != len(set(received_ids)):
        raise ValueError("completed form must contain every query exactly once")
    known_evidence = {row["evidence_id"] for row in corpus}
    reviewer_ids: set[str] = set()
    required = {
        "example_id", "reviewer_id", "answerable", "gold_evidence_ids", "gold_current_ids",
        "forbidden_stale_ids", "alternative_acceptable_ids", "confidence", "notes",
    }
    answerable_count = 0
    for row in forms:
        if set(row) != required:
            raise ValueError(f"{row.get('example_id')}: form fields differ from template")
        reviewer = row["reviewer_id"]
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError(f"{row['example_id']}: reviewer_id is blank")
        reviewer_ids.add(reviewer.strip())
        if row["answerable"] not in {True, False}:
            raise ValueError(f"{row['example_id']}: answerable must be boolean")
        lists = ["gold_evidence_ids", "gold_current_ids", "forbidden_stale_ids", "alternative_acceptable_ids"]
        for field in lists:
            value = row[field]
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value) or len(value) != len(set(value)):
                raise ValueError(f"{row['example_id']}: {field} must contain unique strings")
            if not set(value).issubset(known_evidence):
                raise ValueError(f"{row['example_id']}: {field} contains unknown evidence")
        gold = set(row["gold_evidence_ids"])
        current = set(row["gold_current_ids"])
        forbidden = set(row["forbidden_stale_ids"])
        alternatives = set(row["alternative_acceptable_ids"])
        if row["answerable"] != bool(gold):
            raise ValueError(f"{row['example_id']}: answerability/gold mismatch")
        if not current.issubset(gold):
            raise ValueError(f"{row['example_id']}: current gold must be a subset of required gold")
        if gold & forbidden or gold & alternatives or forbidden & alternatives:
            raise ValueError(f"{row['example_id']}: evidence roles overlap")
        confidence = row["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError(f"{row['example_id']}: confidence must be in [0,1]")
        if not isinstance(row["notes"], str):
            raise ValueError(f"{row['example_id']}: notes must be text")
        answerable_count += int(row["answerable"])
    if len(reviewer_ids) != 1:
        raise ValueError("one consistent reviewer_id is required per form")

    expected_attestation = {
        "reviewer_id", "reviewer_family_or_affiliation", "review_started_at", "review_completed_at",
        "assigned_slot", "completed_form_sha256", "blind_corpus_sha256", "blind_queries_sha256",
        "statements", "conflicts_prior_exposure_or_assistance", "signature_or_verifiable_acknowledgement",
    }
    if set(attestation) != expected_attestation:
        raise ValueError("attestation fields differ from template")
    reviewer = next(iter(reviewer_ids))
    if attestation["reviewer_id"] != reviewer or attestation["assigned_slot"] != slot:
        raise ValueError("attestation reviewer or slot does not match form")
    for field in ["reviewer_family_or_affiliation", "review_started_at", "review_completed_at", "signature_or_verifiable_acknowledgement"]:
        if not isinstance(attestation[field], str) or not attestation[field].strip():
            raise ValueError(f"attestation {field} is blank")
    if attestation["completed_form_sha256"] != sha256(form_path):
        raise ValueError("attestation form hash mismatch")
    if attestation["blind_corpus_sha256"] != sha256(BLIND / "corpus.jsonl") or attestation["blind_queries_sha256"] != sha256(BLIND / "queries.jsonl"):
        raise ValueError("attestation packet hashes mismatch")
    statements = attestation["statements"]
    required_statements = {
        "did_not_inspect_author_labels_or_builder_source", "did_not_inspect_backend_outputs",
        "did_not_inspect_other_reviewer_form", "used_only_corpus_evidence_for_labels",
        "disclosed_conflicts_prior_exposure_and_assistance",
    }
    if not isinstance(statements, dict) or set(statements) != required_statements or any(statements[key] is not True for key in required_statements):
        raise ValueError("all blind-review attestation statements must be true")
    if not isinstance(attestation["conflicts_prior_exposure_or_assistance"], str):
        raise ValueError("conflict/exposure disclosure must be text")
    return {
        "status": "complete-annotation-contract-valid-before-adjudication",
        "slot": slot, "reviewer_id": reviewer,
        "reviewer_family_or_affiliation": attestation["reviewer_family_or_affiliation"],
        "queries": len(forms), "answerable_labels": answerable_count,
        "form_sha256": sha256(form_path), "attestation_sha256": sha256(attestation_path),
        "blind_corpus_sha256": sha256(BLIND / "corpus.jsonl"), "blind_queries_sha256": sha256(BLIND / "queries.jsonl"),
        "author_labels_read": False, "backend_run_permitted": False,
        "authority": "integrity receipt only; agreement/adjudication still required",
    }


def validate_pair(form_a: Path, attestation_a: Path, form_b: Path, attestation_b: Path) -> dict[str, Any]:
    a = validate_one(form_a, attestation_a, "A")
    b = validate_one(form_b, attestation_b, "B")
    if a["reviewer_id"] == b["reviewer_id"]:
        raise ValueError("reviewer A and B must be different people")
    if a["form_sha256"] == b["form_sha256"]:
        raise ValueError("two byte-identical completed forms are not independent evidence")
    return {
        "status": "dual-annotation-contract-valid-before-adjudication",
        "reviewers": [a["reviewer_id"], b["reviewer_id"]], "receipts": {"A": a, "B": b},
        "agreement_computed": False, "author_labels_read": False, "backend_run_permitted": False,
        "next_gate": "receipt-freeze both forms, then produce a disagreement-only adjudication packet",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form-a", type=Path, required=True)
    parser.add_argument("--attestation-a", type=Path, required=True)
    parser.add_argument("--form-b", type=Path)
    parser.add_argument("--attestation-b", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if bool(args.form_b) != bool(args.attestation_b):
        raise SystemExit("--form-b and --attestation-b must be provided together")
    result = validate_pair(args.form_a, args.attestation_a, args.form_b, args.attestation_b) if args.form_b else validate_one(args.form_a, args.attestation_a, "A")
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
