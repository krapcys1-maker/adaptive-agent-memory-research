#!/usr/bin/env python3
"""Build a deterministic, gold-free audit packet for PMLAB-UTILITY-001 T0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab" / "pmlab-future-utility-v0"
PACKET = LAB / "independent-audit-v0"
BLIND = PACKET / "blind"
SOURCE_REVISION = "pmlab-utility-t0.1-audit-subject-v0.1"
BUILDER_VERSION = "future-utility-independent-audit-packet-v0.1"
COMPLETED_RECEIPT = PACKET / "completed-review-receipt.json"

SUBJECTS = {
    "subject-telemetry-schema-v0.1.json": LAB / "telemetry-event-v0.1.schema.json",
    "subject-experiment-manifest.json": LAB / "manifest.json",
    "subject-capture-policy.md": ROOT / "docs" / "11-research-laboratory" / "future-utility-telemetry-privacy-and-capture-policy-v0.md",
    "subject-telemetry-protocol.md": ROOT / "docs" / "11-research-laboratory" / "future-utility-telemetry-protocol-v0.md",
    "subject-validation-report.json": LAB / "t0" / "validation-report.json",
}

QUESTIONS = [
    ("A01", "claim-boundary", "Does every artifact limit T0.1 to synthetic instrument integrity and keep T1-T4, adaptive policy, and canonical mutation locked?"),
    ("A02", "unit-estimand", "Are task, memory, context bundle, assignment unit, analysis unit, and dependence cluster distinguished, with a primary estimand that is actually identified?"),
    ("A03", "interference-credit", "Does the design avoid assigning a shared task outcome to every co-exposed memory and define an exposure mapping or a bundle-level contrast?"),
    ("A04", "propensity-support", "Can the recorded assignment receipt reconstruct the probability of the realized action under the exact logging policy, action space, state, and safety overrides, with positivity diagnostics?"),
    ("A05", "censoring-missingness", "Are structural inapplicability, loss or missing outcome, and no event by deadline distinct, with a frozen defensible analysis for informative censoring?"),
    ("A06", "identifier-linkage", "Are content-derived hashes treated as linkable pseudonyms and protected against low-entropy dictionary attacks rather than called anonymous?"),
    ("A07", "lifecycle-erasure", "Can export, correction, tombstone, erasure, derived-index rebuild, backup propagation, and external-processor propagation be executed and verified without retaining erased content in audit records?"),
    ("A08", "security-access", "Are authentication, authorization, at-rest protection, key custody, access audit, retention, threat actors, and local/external processing boundaries explicit for natural data?"),
    ("A09", "digest-semantics", "Does each digest name its purpose and cover exact bytes or a named canonicalization profile, including Unicode, number, key-order, and whitespace behavior?"),
    ("A10", "audit-independence", "Are reviewer identity, conflicts, prior exposure, evidence inspected, limitations, and the difference between model challenge, human review, privacy review, and statistical reproduction disclosed?"),
]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_outputs() -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    for target, source in SUBJECTS.items():
        outputs[BLIND / target] = source.read_text(encoding="utf-8")

    questions = [
        {"question_id": question_id, "domain": domain, "question": question}
        for question_id, domain, question in QUESTIONS
    ]
    outputs[BLIND / "questions.json"] = pretty({"packet_version": "v0", "questions": questions})

    form = {
        "packet_id": "PMLAB-UTILITY-001-independent-audit-v0",
        "source_revision": SOURCE_REVISION,
        "reviewer": {
            "reviewer_id_or_pseudonym": None,
            "reviewer_kind": None,
            "family_or_affiliation": None,
            "review_started_at": None,
            "review_completed_at": None,
        },
        "findings": [
            {
                "question_id": question_id,
                "verdict": None,
                "severity": None,
                "evidence_locators": [],
                "rationale": None,
                "required_change": None,
            }
            for question_id, _, _ in QUESTIONS
        ],
        "gate_recommendations": {
            "T1": None,
            "T2": None,
            "T3": None,
            "T4": None,
        },
        "blocking_findings": [],
        "residual_risks": [],
        "overall_rationale": None,
        "attestation_id": None,
    }
    outputs[BLIND / "review-form.json"] = pretty(form)

    attestation = {
        "attestation_id": None,
        "reviewer_id_or_pseudonym": None,
        "reviewer_kind": None,
        "family_or_affiliation": None,
        "source_revision": SOURCE_REVISION,
        "packet_manifest_sha256": None,
        "statements": {
            "reviewed_only_listed_subject_artifacts": None,
            "did_not_receive_author_answer_key": None,
            "actively_sought_falsifying_evidence": None,
            "disclosed_conflicts_and_prior_exposure": None,
            "understands_review_does_not_authorize_T2_T4": None,
        },
        "conflicts_or_prior_exposure": None,
        "limitations": None,
        "signature_or_verifiable_acknowledgement": None,
    }
    outputs[BLIND / "attestation.json"] = pretty(attestation)

    manual = """# PMLAB-UTILITY-001 T0.1 blind audit manual

Status: blank, gold-free falsification packet

## Authority

This packet asks whether the listed artifacts justify progression to a narrowly scoped T1 shadow observation. It cannot authorize randomized exposure, adaptive ranking, retention, deletion, consolidation, emotional salience, or a causal claim. A model review is adversarial advice, not legal advice, a DPIA, a human privacy approval, or an independent statistical reproduction.

## Procedure

1. Verify all hashes in `manifest.json` before review.
2. Inspect only the five `subject-*` artifacts, `questions.json`, and this manual.
3. Answer every question independently of the project author's later synthesis or disposition.
4. Cite an artifact plus JSON path, heading, field, or report key for every finding.
5. Prefer `fail` or `not_assessable` when evidence is absent; do not infer an unimplemented control.
6. List every `fail` with severity `blocking` in `blocking_findings`.
7. Complete and sign the attestation. Disclose prior exposure, model family, organizational relation, and limitations.

## Finding contract

- `verdict`: `pass`, `conditional`, `fail`, or `not_assessable`.
- `severity`: `none`, `minor`, `major`, or `blocking`.
- `evidence_locators`: one or more exact locations for any non-empty assessment.
- `required_change`: null only for an unconditional pass; otherwise a concrete repair or evidence request.

## Gate contract

- T1: `deny`, `conditional`, or `allow_shadow_only`.
- T2: `deny` or `conditional`; this packet cannot allow replay.
- T3 and T4: `deny`; this packet cannot authorize them.

T1 `allow_shadow_only` requires no blocking finding, no unresolved `fail`, and explicit evidence for data inventory, minimisation, access control, retention, export/erasure propagation, missingness denominators, and outcome definitions. Synthetic structural tests alone are insufficient.

## Independence labels

Choose exactly one reviewer kind: `human_external`, `human_project`, `model_external_author_operated`, or `model_project_operated`. Only `human_external` may be described as external human review, and even that label does not imply legal, privacy, or statistical credentials unless separately documented.
"""
    outputs[BLIND / "review-manual.md"] = manual

    subject_names = sorted(SUBJECTS)
    pre_manifest_hashes = {
        path.name: sha_bytes(content.encode("utf-8"))
        for path, content in outputs.items()
    }
    manifest = {
        "packet_id": "PMLAB-UTILITY-001-independent-audit-v0",
        "packet_revision": "v0.1",
        "status": "blank-gold-free-packet-awaiting-review",
        "builder_version": BUILDER_VERSION,
        "source_revision": SOURCE_REVISION,
        "subject_artifacts": subject_names,
        "question_count": len(QUESTIONS),
        "author_answer_key_present": False,
        "reviewer": None,
        "review_status": "not_started",
        "hashes": dict(sorted(pre_manifest_hashes.items())),
        "authority": "packet preparation and integrity only; no review, privacy approval, T1 authorization, or causal validation",
    }
    outputs[BLIND / "manifest.json"] = pretty(manifest)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if COMPLETED_RECEIPT.exists():
        if not args.check:
            raise SystemExit("audit packet is frozen by a completed review receipt; create a new packet revision")
        manifest_path = BLIND / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mismatches = [name for name, expected in manifest["hashes"].items() if sha_bytes((BLIND / name).read_bytes()) != expected]
        if mismatches:
            raise SystemExit("frozen audit packet hash mismatch: " + ", ".join(mismatches))
        print(canonical({"status": "frozen-reviewed-packet-current", "files": len(manifest["hashes"]) + 1, "questions": manifest["question_count"]}))
        return 0
    outputs = build_outputs()
    stale = [
        str(path.relative_to(ROOT))
        for path, content in outputs.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    ]
    if args.check and stale:
        raise SystemExit("stale or missing audit packet artifacts: " + ", ".join(stale))
    if not args.check:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print(canonical({"status": "current" if not stale else "written", "files": len(outputs), "questions": len(QUESTIONS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
