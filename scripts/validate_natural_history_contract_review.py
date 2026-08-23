#!/usr/bin/env python3
"""Validate an independently frozen natural-history contract review form."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "data" / "lab" / "pmlab-natural-history-v0" / "independent-contract-review-v0"
MANIFEST = PACKET / "packet-manifest.json"
DIMENSIONS = {
    "historical_git_reconstruction", "stable_unit_identity", "markdown_unitization",
    "structured_row_canonicalization", "duplicates_aliases_and_exclusions",
    "backend_projection_and_byte_equality", "query_privacy_and_capture_order",
    "development_test_isolation",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(path: Path) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    form = json.loads(path.read_text(encoding="utf-8"))
    require(form["packet_id"] == manifest["packet_id"], "packet ID mismatch")
    require(form["source_commit"] == manifest["source_commit"], "source commit mismatch")
    require(form["packet_manifest_sha256"] == sha256(MANIFEST), "packet manifest hash mismatch")
    for relative, expected in manifest["artifacts"].items():
        require(sha256(ROOT / relative) == expected, f"source artifact hash mismatch: {relative}")
    reviewer = form["reviewer"]
    require(set(reviewer) == {"reviewer_id", "reviewer_class", "model_family", "provider"}, "reviewer schema mismatch")
    require(isinstance(reviewer["reviewer_id"], str) and reviewer["reviewer_id"].strip(), "reviewer ID required")
    require(reviewer["reviewer_class"] in {"human_independent", "cross_family_model_independent", "advisory_only"}, "invalid reviewer class")
    if reviewer["reviewer_class"] == "cross_family_model_independent":
        require(all(isinstance(reviewer[key], str) and reviewer[key].strip() for key in ("model_family", "provider")), "model family/provider required")
    attest = form["blindness_attestation"]
    require(set(attest) == {"not_an_author_of_reviewed_contract", "did_not_view_forbidden_advisory_paths", "did_not_view_builder_or_backend_output", "used_one_stateless_review_context"}, "attestation schema mismatch")
    require(all(value is True for value in attest.values()), "all blindness attestations must be true")
    rows = form["dimensions"]
    require(len(rows) == 8 and {row["dimension"] for row in rows} == DIMENSIONS, "dimension coverage mismatch")
    for row in rows:
        require(set(row) == {"dimension", "decision", "evidence", "required_change"}, "dimension schema mismatch")
        require(row["decision"] in {"accept", "revise", "reject"}, "invalid dimension decision")
        require(isinstance(row["evidence"], str) and row["evidence"].strip(), "dimension evidence required")
        if row["decision"] != "accept":
            require(isinstance(row["required_change"], str) and row["required_change"].strip(), "required change missing")
    require(form["overall_verdict"] in {"accept_for_development_builder_review", "needs_revision", "reject"}, "invalid overall verdict")
    require(isinstance(form["blockers"], list) and isinstance(form["required_adversarial_tests"], list), "blocker/test lists required")
    require(all(isinstance(item, dict) and set(item) == {"severity", "issue", "required_change"} and item["severity"] in {"critical", "major", "minor"} for item in form["blockers"]), "invalid blocker")
    if form["overall_verdict"] == "accept_for_development_builder_review":
        require(all(row["decision"] == "accept" for row in rows), "accept verdict requires all dimensions accepted")
        require(not any(item["severity"] in {"critical", "major"} for item in form["blockers"]), "accept verdict cannot retain critical/major blockers")
        require(form["builder_unlock_recommendation"] is True, "accepted review must explicitly recommend development-builder review")
    else:
        require(form["builder_unlock_recommendation"] is False, "non-accept verdict cannot recommend builder unlock")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", form["signed_at"] or "") is not None, "signed_at must be UTC seconds")
    independent = reviewer["reviewer_class"] in {"human_independent", "cross_family_model_independent"}
    return {
        "valid": True, "independent_class": independent, "overall_verdict": form["overall_verdict"],
        "form_sha256": sha256(path), "source_commit": manifest["source_commit"],
        "boundary": "A valid form still requires author disposition and cannot authorize backend execution or prospective testing.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("form", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.form), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
