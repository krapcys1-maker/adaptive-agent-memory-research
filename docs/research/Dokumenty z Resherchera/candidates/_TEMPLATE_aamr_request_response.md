---
id: rmc-YYYY-MM-DD-NNN
type: mechanism_candidate # or experiment_proposal | precondition_note | duplicate_flag
researchos_label: # one of: INTERESTING | EXTERNAL_SIGNAL | STRONG_EXTERNAL_SIGNAL | CANDIDATE_FOR_TEST | NEEDS_PRECONDITION_CHECK
external_evidence_status: # one of: PAPER_CLAIM | EXTERNAL_MEASURED | REPO_CLAIM | CODE_VERIFIED | REPO_ARTIFACT_VERIFIED | INFERENCE | HYPOTHESIS
status: PENDING_AAMR_REVIEW # set once at creation, never edited afterward — see README.md's immutability rule
created: YYYY-MM-DD
source_request_id: # required for this template — the id from Dokumenty dla Resherchera/RESEARCH_REQUESTS/*.md this responds to
source_gap_id: # the OPEN_TESTABLE_GAPS.md id this request targets, if known
researchos_run_id: # ResearchOS runId(s) that produced this response
source_refs: [] # DOIs / URLs / "internal ResearchOS finding"
confidence: # ResearchOS's own confidence, e.g. low | medium | high — not a validation signal
---

<!--
Use this template specifically when responding to a named, OPEN AAMR
research request. Every section below is required by HANDOFF_PROTOCOL_V1
§11 — do not omit one because it's inconvenient (e.g. "what we did not
find" and "uncertainties" are as required as "what we found"). This is
never a substitute for AAMR's own validation: nothing here may be labeled
AAMR_MEASURED / AAMR_VALIDATED / AAMR_REPLICATED /
REPLICATED_VALIDATED_TRANSPLANT — those statuses belong to AAMR alone.
-->

## What we found

## What we did not find

## External evidence

<!-- what was actually measured, not just claimed — cite specific sources -->

## Negative evidence

<!-- stated plainly even when it weakens the candidate -->

## Testability check

<!-- explicit: does this require any capability outside AAMR's testability envelope (e.g. model fine-tuning, model-internal activation access)? -->

## Duplicate check

<!-- explicit: checked against DO_NOT_REDISCOVER (canonicalName + aliases) — matched or not, and why -->

## Preconditions

## Cheapest meaningful test

## What would falsify it

## Uncertainties

<!-- what remains genuinely unresolved — do not paper over this to make the candidate look stronger -->
