# PMLAB-UTILITY-001 T0.1 blind audit manual

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
