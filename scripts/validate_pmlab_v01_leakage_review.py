#!/usr/bin/env python3
"""Validate a genuinely independent PMLAB v0.1 query-leakage review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "data" / "lab" / "project-memory-lab-v0.1-construction"
BLIND = PACKET / "blind"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate(review_path: Path) -> dict[str, Any]:
    manifest = json.loads((PACKET / "manifest.json").read_text(encoding="utf-8"))
    allowed_statuses = {
        "automated-screen-passed-awaiting-independent-leakage-review",
        "model-blind-leakage-accepted-awaiting-m2-annotation",
    }
    if manifest["status"] not in allowed_statuses:
        raise ValueError("packet is not at the independent leakage-review gate")
    if manifest["baseline_run_permitted"] is not False or manifest["author_labels_are_gold"] is not False:
        raise ValueError("construction safety flags changed")
    for relative, expected in manifest["hashes"].items():
        if relative.startswith("internal/") or relative == "corpus.jsonl":
            continue
        if sha256(PACKET / relative) != expected:
            raise ValueError(f"blind packet hash mismatch: {relative}")

    review = json.loads(review_path.read_text(encoding="utf-8"))
    expected_fields = {
        "reviewer_id", "reviewer_family_or_affiliation", "review_started_at", "review_completed_at",
        "candidate_query_freeze_commit", "blind_corpus_sha256", "blind_queries_sha256",
        "category_reviews", "whole_packet_decision", "statements",
        "conflicts_prior_exposure_or_assistance", "signature_or_verifiable_acknowledgement",
    }
    if set(review) != expected_fields:
        raise ValueError("review fields differ from template")
    for field in ["reviewer_id", "reviewer_family_or_affiliation", "review_started_at", "review_completed_at", "signature_or_verifiable_acknowledgement"]:
        if not isinstance(review[field], str) or not review[field].strip():
            raise ValueError(f"{field} is blank")
    if review["candidate_query_freeze_commit"] != manifest["candidate_freeze_commit"]:
        raise ValueError("candidate query freeze commit mismatch")
    if review["blind_corpus_sha256"] != sha256(BLIND / "corpus.jsonl") or review["blind_queries_sha256"] != sha256(BLIND / "queries.jsonl"):
        raise ValueError("review packet hashes mismatch")

    categories = sorted({row["category"] for row in read_jsonl(BLIND / "queries.jsonl")})
    if set(review["category_reviews"]) != set(categories):
        raise ValueError("every and only registered category must be reviewed")
    material_ids: set[str] = set()
    known_examples = {row["example_id"] for row in read_jsonl(BLIND / "queries.jsonl")}
    decisions = []
    for category in categories:
        item = review["category_reviews"][category]
        if set(item) != {"decision", "material_overlap_example_ids", "notes"}:
            raise ValueError(f"{category}: fields differ from template")
        if item["decision"] not in {"accept", "reject"}:
            raise ValueError(f"{category}: decision must be accept or reject")
        if not isinstance(item["material_overlap_example_ids"], list) or any(value not in known_examples for value in item["material_overlap_example_ids"]):
            raise ValueError(f"{category}: material overlap IDs are invalid")
        if len(item["material_overlap_example_ids"]) != len(set(item["material_overlap_example_ids"])):
            raise ValueError(f"{category}: duplicate material overlap IDs")
        if not isinstance(item["notes"], str):
            raise ValueError(f"{category}: notes must be text")
        if item["decision"] == "reject" and not item["notes"].strip():
            raise ValueError(f"{category}: rejection requires notes")
        decisions.append(item["decision"])
        material_ids.update(item["material_overlap_example_ids"])

    expected_whole = "accept" if all(value == "accept" for value in decisions) else "reject"
    if review["whole_packet_decision"] != expected_whole:
        raise ValueError("whole-packet decision is inconsistent with category decisions")
    required_statements = {
        "did_not_inspect_author_labels_or_builder_source",
        "did_not_inspect_backend_outputs",
        "compared_all_within_category_development_test_forms",
        "checked_category_filename_wording_and_project_exposure_cues",
        "disclosed_conflicts_prior_exposure_and_assistance",
    }
    statements = review["statements"]
    if not isinstance(statements, dict) or set(statements) != required_statements or any(statements[key] is not True for key in required_statements):
        raise ValueError("all independent-review statements must be true")
    if not isinstance(review["conflicts_prior_exposure_or_assistance"], str):
        raise ValueError("conflict/exposure disclosure must be text")
    return {
        "status": "independent-leakage-review-contract-valid",
        "decision": expected_whole,
        "reviewer_id": review["reviewer_id"],
        "reviewer_family_or_affiliation": review["reviewer_family_or_affiliation"],
        "review_sha256": sha256(review_path),
        "blind_corpus_sha256": review["blind_corpus_sha256"],
        "blind_queries_sha256": review["blind_queries_sha256"],
        "material_overlap_example_ids": sorted(material_ids),
        "author_labels_read": False,
        "backend_run_permitted": False,
        "next_gate": "if accepted, freeze this receipt and explicitly change packet status before dual annotation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    result = validate(args.review)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.receipt:
        args.receipt.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
