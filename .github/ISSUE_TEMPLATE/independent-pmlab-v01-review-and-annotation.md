---
name: Independent PMLAB v0.1 review and annotation
about: Audit split leakage, then claim reviewer A or B for the blind 120-query packet
title: "[Independent review] Project Memory Lab v0.1 leakage audit or annotation A/B"
labels: research, independent-review
---

## Requested role

Choose exactly one initial role:

- independent query-form/leakage auditor; or
- annotation Reviewer A; or
- annotation Reviewer B.

Annotation must not begin until an independent leakage auditor accepts the development/test query forms. The two annotators must work independently and may not inspect one another's form before both hashes are frozen.

## Identity or stable pseudonym

## Family, affiliation, and relevant experience

## Prior exposure and assistance disclosure

- [ ] I have not inspected `internal/author-labels.jsonl`.
- [ ] I have not inspected `scripts/build_project_memory_lab_v0.py` or `scripts/build_project_memory_lab_v01.py`.
- [ ] I have not seen PMLAB v0/v0.1 backend outputs; none should exist for this corpus.
- [ ] If annotating, I have not inspected the other reviewer's completed form.
- [ ] I will disclose tools, collaborators, conflicts, and any earlier exposure.

Prior exposure may make a contribution useful for discussion while preventing it from satisfying the blind gate.

## Frozen packet

Candidate freeze: `cc904dd`

Review only:

`data/lab/project-memory-lab-v0.1-construction/blind/`

Blind query SHA-256:

`6dca3fcea6e7b7830231444d6e8050952843bbe8974f78633889e6ac76c056bf`

## Leakage-auditor workflow

- [ ] Copy and complete `blind/leakage-review-form.json`; do not overwrite the blank template.
- [ ] Compare development and test forms within all twelve categories without opening internal labels.
- [ ] Check semantic/task equivalence without accepting repeated lexical or syntactic frames.
- [ ] Check whether category cues, filenames, wording, or project exposure disclose target relations.
- [ ] Report every material issue and an accept/reject decision with rationale.
- [ ] Commit or otherwise freeze the signed report before annotation starts.

Validate the completed form with `python scripts/validate_pmlab_v01_leakage_review.py --review PATH`. A valid receipt records integrity and an accept/reject decision but never unlocks a backend by itself.

The existing automated and author audits are diagnostics, not independent acceptance.

## Annotator workflow

- [ ] Confirm that an independent leakage report accepted the packet.
- [ ] Fill every row in the assigned annotation form.
- [ ] Use corpus evidence rather than plausibility or external world knowledge.
- [ ] Complete the matching JSON attestation.
- [ ] Record the completed form SHA-256 in the attestation.
- [ ] Freeze/commit the form before requesting comparison or adjudication.
- [ ] Preserve ambiguity and disagreements in `notes`.

Do not run `rg`, FTS5, embeddings, or another retrieval backend to choose labels. Questions about the manual should not ask for the author's preferred evidence IDs.

## Expected completion date

## Contract questions
