#!/usr/bin/env python3
"""Validate M2 model annotation forms for the frozen PMLAB v0.1 packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "data" / "lab" / "project-memory-lab-v0.1-construction"
BLIND = PACKET / "blind"
sys.path.insert(0, str(ROOT / "scripts"))
import validate_pmlab_v0_annotation as base  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_packet() -> dict[str, Any]:
    manifest = json.loads((PACKET / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {
        "model-blind-leakage-accepted-awaiting-m2-annotation",
        "m2-model-reviewed-gold-frozen-exploratory-baseline-permitted",
    }:
        raise ValueError("packet is not M1-accepted and awaiting M2 annotation")
    if manifest["baseline_run_permitted"] is not False or manifest["author_labels_are_gold"] is not False:
        raise ValueError("construction safety flags changed")
    gate = manifest.get("model_review_gate") or {}
    receipt_path = ROOT / gate.get("receipt_path", "")
    if gate.get("evidence_tier") != "M1" or gate.get("decision") != "accept":
        raise ValueError("M1 gate did not accept the packet")
    if not receipt_path.is_file() or sha256(receipt_path) != gate.get("receipt_sha256"):
        raise ValueError("M1 receipt is missing or hash-mismatched")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("decision") != "accept" or receipt.get("experimental_annotation_permitted") is not True:
        raise ValueError("M1 receipt does not permit experimental annotation")
    for relative, expected in manifest["hashes"].items():
        if relative.startswith("internal/") or relative == "corpus.jsonl":
            continue
        if sha256(PACKET / relative) != expected:
            raise ValueError(f"blind packet hash mismatch: {relative}")
    return manifest


# Reuse the mature field/attestation checks while binding them to v0.1.
base.PACKET = PACKET
base.BLIND = BLIND
base.MANIFEST = PACKET / "manifest.json"
base.verify_packet = verify_packet


def validate_one(form: Path, attestation: Path, slot: str) -> dict[str, Any]:
    result = base.validate_one(form, attestation, slot)
    result.update({
        "status": "m2-model-annotation-contract-valid-before-adjudication",
        "evidence_tier": "M2",
        "human_independence_satisfied": False,
        "cross_family_independence_satisfied": False,
        "model_review_common_mode_risk": True,
        "authority": "role-separated blind model annotation; not human or cross-family independence",
    })
    return result


def validate_pair(form_a: Path, attestation_a: Path, form_b: Path, attestation_b: Path) -> dict[str, Any]:
    a = validate_one(form_a, attestation_a, "A")
    b = validate_one(form_b, attestation_b, "B")
    if a["reviewer_id"] == b["reviewer_id"]:
        raise ValueError("model roles A and B must have distinct role identifiers")
    if a["form_sha256"] == b["form_sha256"]:
        raise ValueError("completed forms are byte-identical")
    return {
        "status": "m2-dual-model-annotation-contract-valid-before-adjudication",
        "evidence_tier": "M2",
        "reviewers": [a["reviewer_id"], b["reviewer_id"]],
        "receipts": {"A": a, "B": b},
        "agreement_computed": False,
        "author_labels_read": False,
        "backend_run_permitted": False,
        "human_independence_satisfied": False,
        "cross_family_independence_satisfied": False,
        "model_review_common_mode_risk": True,
        "next_gate": "freeze forms, compute agreement, and adjudicate every disagreement",
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
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
