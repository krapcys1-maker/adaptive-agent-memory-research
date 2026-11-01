---
id: rmc-2026-08-24-001_aamr-review
reviews_candidate: rmc-2026-08-24-001
type: aamr_review
status: AAMR_MEASURED
created: 2026-08-25
---

# AAMR review of `rmc-2026-08-24-001` (`semantic-entropy-escalation-gate`)

## Result

**`MECHANISM_SEG_FAIL` → `DROP`.** Full detail: [`SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md`](SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md); ledger record: `MECHANISM_REGIME_EVIDENCE_LEDGER.md` Entry Q.

## What AAMR did with this candidate

1. Re-derived its precondition status: the candidate's `duplicate_of`/`suggested_next_step` fields assumed `RAW_PROVENANCE`'s value was still undecided ("sequence after Experiment #3"). That premise was already resolved by the time of review — `RAW_PROVENANCE` is `REPLICATED_VALIDATED_TRANSPLANT` (Entry H) — so the test was reframed around Entry H's own measured ~21.4x token overhead (cost-efficiency), not correctness, per the candidate's own stated logic for what would make the test still worth running.
2. Ran a **$0 calibration** (`PM-20260825-41d5d71e`) by reusing already-persisted, already-labeled data from a prior experiment (`raw-provenance-fresh-replication-v1`) — no new ingest, no new gold-blind selection. Result: clean, correctly-directioned separation (sufficient=0.300, insufficient=1.104, +0.804), which justified proceeding to one bounded causal test.
3. Ran the causal test on 6 fresh, gold-blind, never-used units (`PM-20260825-e88248ff`, $0.435904): BASE 3/6 correct, GATE 3/6 correct, 0 regressions, escalation fired selectively (2/6) but produced 0 traceable repairs.
4. Independently, adversarially verified every interpretive claim in the resulting archaeology against the raw results, the pipeline code, and (for two units) the primary LongMemEval corpus — this caught and corrected a misclassification in AAMR's own first-draft analysis (one unit initially read as "confident hallucination" was, on primary-source tracing, actually the already-documented temporal-representation-loss subtype).

## Why it failed, in terms of this candidate's own stated risk

The candidate's own `possible_negative_regime` field named this risk before any AAMR spend: "AAMR's own observed Mem0 failures are dominated by exactly this presence-type pattern [gold present, reader still wrong], not absence... the effect on AAMR's actual workload could be smaller than on SUGAR's own benchmark, or null." That is exactly what was measured. Of the two units where entropy escalated: one (`0edc2aef`) was a reader reasoning/application failure — the needed preference statement was present in context (and stated even more explicitly in the injected raw text) but the reader would not generalize it; the other (`1de5cff2`) was a genuine absence, but of a kind (assistant-turn-scoping-loss, compounded by a retrieval-ranking miss) this project already had on record as structurally unreachable by `RAW_PROVENANCE`-style raw injection. The entropy trigger itself was also unreliable at this sample size: one of its two firings was a clustering artifact on near-duplicate refusal phrasing, not real model disagreement.

## What this closes

- **`arr-2026-08-24-001`** (AAMR's own research request, GAP-005): closed with `AAMR_MEASURED` evidence — AAMR tested the candidate directly rather than waiting on further ResearchOS literature search, which the request's own stop condition treated as an acceptable closure path.
- **`GAP-005`** (`OPEN_TESTABLE_GAPS.md`): closed. No cheap proxy signal for compact-vs-raw sufficiency was found to correlate usefully with this project's actual failure mix at n=6; `RAW_PROVENANCE` continues to run unconditionally.

## For ResearchOS

This is not a criticism of the candidate's sourcing or reasoning — the literature review was accurate (SUGAR's result is real, black-box semantic entropy's core validity is real, and the calibration confirmed the signal transfers directionally), and the candidate's own self-flagged risk is exactly what explains the negative result. The value ResearchOS added here was making that risk explicit *before* AAMR spent anything on the design, which is what let this close in one bounded, well-understood test rather than several. If a future candidate proposes a different remedy for the same gate (not top-1-anchored single-hop raw injection, and/or a more robust clustering method than embedding-cosine for the trigger), it would not be a duplicate of this entry — see `DO_NOT_REDISCOVER.md` Entry Q for the precise `do_not_retry` boundary.
