---
id: rmc-YYYY-MM-DD-NNN
type: mechanism_candidate # mechanism_candidate | experiment_proposal | precondition_note | duplicate_flag
researchos_label: # one of: INTERESTING | EXTERNAL_SIGNAL | STRONG_EXTERNAL_SIGNAL | CANDIDATE_FOR_TEST | NEEDS_PRECONDITION_CHECK
external_evidence_status: # one of: PAPER_CLAIM | EXTERNAL_MEASURED | REPO_CLAIM | CODE_VERIFIED | REPO_ARTIFACT_VERIFIED | INFERENCE | HYPOTHESIS
status: PENDING_AAMR_REVIEW # set once at creation, never edited afterward — see README.md's immutability rule
created: YYYY-MM-DD
source_run: # ResearchOS runId or postmortem file, if applicable
source_request_id: # if this responds to a specific OPEN request from Dokumenty dla Resherchera/RESEARCH_REQUESTS/ — leave blank otherwise. If set, consider using _TEMPLATE_aamr_request_response.md instead, which has the full required section set for request responses.
source_gap_id: # if this addresses a specific gap from Dokumenty dla Resherchera/OPEN_TESTABLE_GAPS.md — leave blank otherwise
source_refs: [] # DOIs / URLs / "internal ResearchOS finding"
target_failure: # what failure mode this mechanism is meant to address, if known
expected_positive_regime: # conditions under which this is expected to help
possible_negative_regime: # conditions under which this might hurt or not apply
preconditions: # what must be true for a test of this to be valid
duplicate_of: # id or description of an existing AAMR mechanism this may duplicate, if applicable
estimated_test_cost_usd: # rough estimate, if ResearchOS has one
confidence: # ResearchOS's own confidence, e.g. low | medium | high — not a validation signal
---

## Summary

<!-- 1-3 sentences: what this candidate is -->

## Why this might matter to AAMR

<!-- short rationale — the mechanism, the gap, the contradiction -->

## Evidence

<!-- concise — cite specific findings, not a full literature dump -->

## Suggested next step for AAMR

<!-- optional — what a test/check might look like, only if ResearchOS has a concrete idea -->
