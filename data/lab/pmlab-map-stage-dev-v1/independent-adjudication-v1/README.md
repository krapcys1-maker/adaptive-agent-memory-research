# Independent adjudication packet v1

Status: packet revision 1.1 ready; no independent labels yet

This packet is the phase gate between authored development labels and candidate implementation.

## Blinding boundary

Give an independent reviewer only the contents of `blind/`. Do not give them:

- `data/lab/pmlab-map-stage-dev-v1/cases.jsonl`;
- either DeepSeek review directory;
- aggregate agreement results;
- `internal-priority-index.jsonl`;
- author rationale, criticality, stratum, or candidate architecture material.

The repository is public, so procedural blindness requires the reviewer to attest that they did not inspect those artifacts before submitting labels. Hash and commit the completed review form before revealing comparisons.

## Selection

The packet includes every critical semantic group plus a deterministic ordinary-group sample of one group per stage. This is 67 semantic groups/134 paired PL-EN rows: all 61 critical groups and six of 16 ordinary groups (37.5%, exceeding the frozen 25% minimum).

## Sequence

1. Reviewer reads `blind/review-manual-v1.md` and the versioned catalogs/contracts.
2. Reviewer fills every field in `blind/review-form.jsonl` without inspecting author or advisory labels.
3. Reviewer signs the attestation and records identity/family, date, and source commit.
4. Completed form is committed and hashed.
5. Only then generate a reveal/adjudication comparison against author and advisory labels.
6. Every material critical disagreement is resolved or the group is excluded. Original labels are never deleted.

`scripts/validate_mapper_independent_review_v1.py` creates the pre-reveal receipt. `scripts/reveal_mapper_adjudication_v1.py` refuses to compare labels unless the stored receipt exactly matches a freshly validated form and attestation. Its output is a three-way author/independent/advisory comparison plus a pending adjudication queue; it never writes adjudicated labels or changes gold.

DeepSeek is an advisory worker already used on this corpus. It cannot satisfy this independent-review requirement.

Revision 1.1 was issued before any reviewer was assigned. It adds exact reviewer-label JSON shapes after validation found that the base schema's entity field names (`ranked_candidates`) differed from the authored label envelope (`candidate_ids` plus `selected_ids`). No cases, selection, gold labels, or advisory results changed.
