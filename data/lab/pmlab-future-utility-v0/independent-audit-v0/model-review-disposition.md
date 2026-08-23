# Disposition of the T0.1 DeepSeek blind challenge

Status: author disposition of an M2 cross-family, author-operated model challenge

Run: `deepseek-v4-flash-future-utility-t01-blind-audit-20260823`

Cost: USD 0.01060884 conservative peak-cache-miss estimate

Result: 1 pass, 7 conditional findings, 2 failures; T1-T4 all denied

## Authority boundary

The completed form passed the mechanical packet validator. That means the response covered every frozen question, obeyed the verdict/severity/gate rules, matched the packet hashes, and disclosed its model-operated status. It does not mean every substantive claim is correct.

This run is adversarial evidence tier M2: a different model family examined a gold-free packet under a frozen prompt. It is not human, legal, privacy-professional, DPIA, institutional, or statistical independence. `independent_audit.review_completed` therefore remains false.

## Disposition

| Finding | Model verdict | Project disposition | Consequence |
| --- | --- | --- | --- |
| A01 claim boundary | pass | accept | T0.1 is bounded to synthetic instrument integrity; all later gates remain locked |
| A02 unit and estimand | conditional major | accept | add an explicit bundle/assignment/analysis-unit contract; per-memory assignment events do not by themselves identify the declared bundle ITT |
| A03 interference and credit | conditional major | accept in principle, narrow the diagnosis | same-task per-memory events can help reconstruct exposures, but the current schema does not guarantee a complete frozen bundle membership record or exposure mapping; add one rather than infer completeness |
| A04 propensity and support | conditional major | accept | bind realized-arm probability to exact policy state, action space, candidate set, safety override, and assignment receipt; add overlap and ESS diagnostics |
| A05 censoring and missingness | conditional major | accept principle, reject prescribed enum as the only repair | structural inapplicability, lost/unobserved outcome, and no event by deadline must be distinct; this may be represented through outcome applicability plus closure state rather than one required enum |
| A06 identifier linkage | conditional major | accept | add a digest/pseudonym threat contract and use random opaque IDs for joins; never imply that SHA-256 of user content is anonymous |
| A07 lifecycle and erasure | fail blocking | accept blocker, reject hash-as-erasure shortcut | define and test export, rectification, tombstone, erasure propagation, derived-index rebuild, backups, processors, and receipts; retaining a content hash may itself preserve linkability and is not automatically erasure |
| A08 security and access | fail blocking | accept | create a threat model and Current/Target privacy profile covering authentication, authorization, encryption, key custody, access audit, retention, local processes, and external workers |
| A09 digest semantics | conditional major | accept | name exact-byte versus canonicalized representation for every digest and add cross-serialization fixtures |
| A10 audit independence | conditional major | partially reject factual rationale, retain missing-review gate | the blind manual already requires conflict/prior-exposure disclosure, family/affiliation, limitations, inspected artifacts, and attestation; however, no external human/privacy/statistical review has occurred, so the broader independence gate remains open |

## Corrections to model advice

The model proposed replacing erased content with a hash or null inside a tombstone. A null minimal receipt may be viable; retaining a content-derived hash is not accepted as a default because it can remain linkable, particularly for low-entropy content. The intended design separates a content-free integrity receipt from erasable content and linkage stores, then verifies propagation to indexes, derived datasets, packets, processors, and backups.

The model also said the manual does not require prior-exposure and organizational disclosure. That is incorrect. `review-manual.md` procedure step 7 and the attestation template explicitly require conflict/prior-exposure, reviewer kind, family/affiliation, and limitations. The completed DeepSeek attestation records the author-operated run and the prior DeepSeek-family review of schema v0.

## Locked repair order

1. Threat model and data-lifecycle inventory.
2. Export/rectification/tombstone/erasure contract plus synthetic propagation fixtures.
3. Digest and pseudonym contract plus dictionary/canonicalization challenge fixtures.
4. Bundle assignment, exposure mapping, interference boundary, and causal-unit contract.
5. Propensity receipt, support/ESS diagnostics, and informative-censoring plan.
6. Rebuild the blind packet against the repaired revision and seek a genuinely external review if available.
7. Only then reconsider a local, allowlisted, no-model, no-ranking-change T1 shadow sink.

No repair is authorized to ingest natural user data while this disposition is open.

