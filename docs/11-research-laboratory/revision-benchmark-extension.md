# Revision and reconsolidation benchmark extension v0

Status: preregistration-draft; no test results observed

## Shared controls

- Raw source events are append-only in every arm.
- All revision evidence, actor, event time, validity time, scope, and transaction time are visible to scoring.
- Split complete entities/histories so a correction template cannot leak to test.
- Hold reader, retrieval budget, model calls, prompts, and maintenance cost constant.
- Score current correctness and historical audit separately.

## Experiment V1 — overwrite, supersession, and coexistence

Histories contain true corrections, temporary exceptions, misinformation, ambiguous scope changes, and reversions. Compare in-place overwrite, append-both without status, versioned supersession, context-scoped coexistence, and no derived update/raw retrieval.

Primary: valid-time correct-action rate. Guardrails: stale-belief intrusion, false supersession, exact historical reconstruction, provenance completeness, rollback success, and context overgeneralization.

Versioned revision succeeds if it improves valid-time action by at least 8 points over append-both and no-update, reduces stale intrusion by at least 8 points versus overwrite, and preserves at least 99% exact historical/audit recovery. If raw retrieval matches current correctness within 2 points, derived revision is not justified for that stratum.

## Experiment V2 — retrieval is not a write trigger

Cross four events: pure retrieval, retrieval plus verified contradiction, retrieval plus unverified/adversarial conflict, and verified correction without prior retrieval. Compare read-modify-write, prediction-error-triggered update, explicit verified transaction, and no update.

Primary: authorized correct-update rate minus unauthorized mutation rate. Guardrails: poison persistence, unchanged-record checksum, missed urgent correction, and maintenance cost.

Success requires zero canonical mutation after pure retrieval, at least 95% preservation under unverified conflicts, and at least 90% correct scoped revision for verified contradictions. A prediction-error gate is rejected if it promotes surprise/attack more often than the explicit transaction baseline.

## Experiment V3 — return and representation dissociation

For each correction, independently manipulate factual proposition, affect/salience metadata, cached procedure, and context rule. Test immediately, after long delay, in the update context, in the old context, after an old cue, and after adversarial reinstatement.

Primary: per-representation correct control under each probe. Guardrails: factual erasure, salience persistence after safety evidence, unsafe procedural relapse, calibration, and explicit uncertainty.

Success requires at least 90% correct representation-specific behavior in every probe stratum and no more than 2-point degradation from immediate to delayed/renewal tests. A single fused memory field is rejected if changing one dimension corrupts another.

## Analysis and promotion

- Freeze correction validity, ambiguity, and attack labels before running systems.
- Report history-level paired intervals and worst-stratum results.
- Repeat after paraphrasing both old and new cues.
- Promotion requires a second corpus family and a different reader/provider family where feasible.
- Immediate post-update accuracy alone can never promote a revision policy.

