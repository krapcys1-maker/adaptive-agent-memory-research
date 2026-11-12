---
id: rmc-2026-08-25-001
type: research_gap
status: PENDING_AAMR_REVIEW
created: 2026-08-25
source_request_id: arr-2026-08-25-001
source_gap_id: GAP-002
researchos_run_id: cmt88rag60001p6crgu9coq5p
source_refs:
  - "internal ResearchOS finding — see Uncertainties for why external sources are not cited as qualifying evidence"
confidence: medium
---

<!--
This responds to a specific, OPEN AAMR request (arr-2026-08-25-001) whose own
stop_condition explicitly names this exact outcome — zero qualifying
candidates — as correct and expected, not a failure:
"jeśli po tym poszukiwaniu żaden kandydat nie spełnia WSZYSTKICH czterech
kryteriów filtra AAMR, ten request zamyka się jako WAITING_FOR_RESEARCH."
Filed under notes/ (type: research_gap) rather than candidates/ because
researchos_label and external_evidence_status both describe a positive
claim being made about something worth testing — there is no such claim
here. All ten sections the request-response protocol requires are still
included below in full, per instruction, even though this uses the
research_gap frontmatter shape rather than the candidate one.
-->

## Summary

ResearchOS ran one bounded research pass (run `cmt88rag60001p6crgu9coq5p`, $0.2521 of $0.30, `completed_with_limit` on `max_iterations`) targeting exactly the three failure modes named in `arr-2026-08-25-001`: `ASSISTANT_TURN_REPRESENTATION_LOSS` (GAP-004), `RETRIEVAL_ANCHOR_FAILURE` (GAP-002b), `TEMPORAL_REPRESENTATION_LOSS` (GAP-003). **Zero candidates met the request's four-criterion filter.** This is the request's own pre-declared correct outcome (`WAITING_FOR_RESEARCH`), not a shortfall being reported as if it were a finding.

## What we found

Eight hypotheses were generated and ranked; the two strongest, both purely engineering proposals with no external measured prior art behind the specific application:

- **Deterministic Calendar-Arithmetic Temporal Resolver** (targets failure mode 3, score 0.76): a non-LLM, regex + `datetime`/`dateutil` post-processing module that would resolve relative date expressions to absolute ISO timestamps before storage. Structurally sound, `CAN_TEST_NOW`, and genuinely distinct from the already-failed Entry E design (see Duplicate check) — but its own mechanism description contains no citation of prior art demonstrating this exact approach measured in an agent-memory extraction pipeline. It is a plausible thing to *build*, not a *found, measured* solution.
- **BM25-Pinned Deterministic Re-Ranking for post-escalation anchor selection** (targets failure mode 2, score 0.75): apply classical BM25 + POS-gated phrase normalization to select among multiple raw-retrieval candidates instead of anchoring to the single top-1 hit. BM25 itself is decades-old, well-understood IR technique — but no source found demonstrates it specifically applied to *this* problem (anchor selection after an escalation decision, in persistent agent memory, as opposed to general document ranking).
- A "Learned Importance Scoring" hypothesis for failure mode 1 (selective assistant-turn inclusion) scored highest overall (0.62) but requires training a small classifier — plausible, but again not something any retrieved source actually measured for this task.

## What we did not find

No source directly measuring any of the three failure modes as AAMR defines them. Several retrieved sources turned out topically mismatched on closer reading despite being cited by the generation step as support — e.g. a GIS/location-semantics paper and a chemistry-domain LLM-agent review were cited as if they supported "deterministic rules" and generic agent-review claims respectively; neither is about memory extraction, retrieval anchoring, or temporal resolution at all. This was caught in ResearchOS's own review before this note was written, not left for AAMR to discover.

## External evidence

The topically closest sources (`Does Memory Credit Travel? Paired Factorial Audits of LLM-Agent Memory`, `Learned Importance Scoring for Adaptive Memory Compaction in LLM-Based Agent Systems`, `Retrieval Beats Cheap Structured Memory: A Cost–Retention Study of LLM Agent Memory on Real Long-Conversation Benchmarks`) are all very recent (2026), non-peer-reviewed preprints (SSRN / Preprints.org / TechRxiv). They were retrieved via OpenAlex/Crossref (genuine index entries, not fabricated), but this run's own iteration budget ran out (`budget_limit:max_iterations`) before its VerificationAgent step could read past the abstract level and assign a real `evidence_class`. Treat their relevance as **unconfirmed, not disconfirmed** — see Uncertainties.

## Negative evidence

Not the primary finding here (the gap is an absence of positive evidence, not a specific failure mode), but AAMR's own absence-taxonomy (Ledger Entries M, O) already shows this project's dominant failure pattern is retrieval-absence, not evidence-present-but-misread — worth keeping in mind if any of the above candidates are later picked up, since the same caveat applied to the earlier semantic-entropy candidate (Entry Q, FAILED) may apply again.

## Testability check

All three hypotheses above are `CAN_TEST_NOW` per `TESTABILITY_ENVELOPE.md` — "deterministic post-processing" and classical IR re-ranking require no model fine-tuning, no hidden-activation access, no provider-side training. Testability was never the blocker; evidentiary rigor was.

## Duplicate check

Checked against all 16 `DO_NOT_REDISCOVER.md` entries (A–Q), explicit reasoning for the two closest:
- **Entry E** (`EVENT_TIME_RESOLUTION_AT_EXTRACTION`, FAILED — inline relative-time instruction in the extraction prompt, model ignored it): the temporal-resolver hypothesis above is a **separate, deterministic, non-LLM field**, not an inline instruction — matches the exact distinction `arr-2026-08-25-001` itself pre-authorized as non-duplicate. Not flagged.
- **Entry Q** (`SEMANTIC_ENTROPY_SUFFICIENCY_GATE`, FAILED — embedding-cosine sample-and-cluster *trigger* with top-1-anchored *remedy*): the BM25 hypothesis above addresses *remedy selection after* an escalation decision, not the *trigger* for escalation — same distinction the request itself drew. Not flagged.

No exact or aliased match found for any of the eight hypotheses.

## Preconditions

None outstanding — all three top hypotheses are precondition-free per the current testability envelope.

## Cheapest meaningful test

Not proposed — per the request's own filter, a test is only warranted once a candidate clears evidence-class rigor, which none currently do. If AAMR wants to treat the temporal-resolver or BM25 hypotheses as engineering proposals *without* requiring prior external measurement (a different bar than what this request asked for), the cheapest starting point would be a $0 precondition check against already-collected AAMR data — same discipline as every prior mechanism this campaign — before any paid test.

## What would falsify it

This note itself makes no falsifiable claim — it reports an absence. What would change it: a genuine `EXTERNAL_MEASURED`, `CODE_VERIFIED`, or `REPO_ARTIFACT_VERIFIED` source found later, specifically for one of the three named failure modes (not a generic agent-memory survey, not a different-context application of the same generic technique).

## Uncertainties

- The three 2026 preprints under External evidence were never read past abstract level by this run — they might turn out relevant, or might not; this is a real gap in this run's own completeness, caused by hitting `max_iterations` before full verification, not a considered rejection.
- ResearchOS's own literature search here is limited to pubmed/openalex/crossref; a GitHub-code-first search (matching what AAMR's request explicitly asked for — "sprawdzić GitHub, kod, nie tylko README") was not meaningfully completed within budget. This is a real, acknowledged shortfall in following the request's own §"Co ResearchOS MA zrobić" item 1, not something to paper over.
- Given both gaps above, a second, better-scoped pass (narrower goal text — this run's own goal prompt was long enough to exceed Hindsight's recall query limit and lost memory context for its first step — plus explicit GitHub source coverage) could plausibly surface a real candidate where this one did not. Not proposed here as a request for more budget; noted for AAMR's own prioritization.
