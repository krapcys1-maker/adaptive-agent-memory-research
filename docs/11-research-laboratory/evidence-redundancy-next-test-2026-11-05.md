# Evidence repetition versus valid correction — next falsifiable test

Status: **one pending exploratory design, not executed or a claimed new architecture**. Derived from [the whole-family controls](../../data/lab/h1-obsolete-controls-v1/README.md), #108 and prior evidence-sufficiency/temporal-versioning work. Do not describe source provenance or field-level revision as novel to this project; earlier synthesis and prototypes already discuss them.

## Observation and hypothesis

The original validation Q000043 pack fails twice across the retained v5 and whole-family repeat, while oracle-only and both two-note orders pass in the latest diagnostic. Six other original three-note packs pass; pack length alone is not the established cause. Hypothesis: repeated stale content receives excessive influence relative to one authoritative correction. Alternative explanations include longer context, wording, instruction adherence and generation variability.

## Proposed contrast, fixed before new calls

Use all 24 spent/public OBSOLETE cases, not only Q000043. Each pack contains the correction, one obsolete source and a third note. Cross third-note type (neutral control, explicit repeat of obsolete source, explicit repeat of correction) with correction position (first/last): 6 conditions, 144 primary local generations plus 3 unrelated controls. Preserve real source text, dates, roles and repeated source identity; never fabricate independent corroboration. Neutral additions are explicitly synthetic controls, not real history. Report byte lengths/native token counters and the unequal-content limitation rather than claim exact matched context.

Primary measurements: per-case stale leakage, clean `answered`, discordant pairs and failures/abstentions by condition. If duplicate-obsolete packs do not worsen leakage relative to both neutral and duplicate-correction contrasts, retire this exact-repeat intervention as unsupported here. A null result does not rule out semantic redundancy across differently worded sources, and a floor effect has limited falsification value. No significance/universal cause claim from these authored correlated cases; a fresh replication is required for promotion.

## Candidate mechanism if supported

A provenance-aware evidence view could represent repeated claims as one version with multiple source pointers, preserve obsolete versions for historical questions, and expose unresolved contradictions explicitly. This is different from letting repetition vote for truth. Before implementation, reuse the existing temporal resolver/provenance work and define field-level updates so a correction to one field cannot erase another field from a multi-field source (audit A04).

The decisive downstream test is automatic extraction/routing and every H1 family at declared budget, followed by fresh data. An oracle evidence diagnostic cannot establish that automatic claim grouping or revision works. No prompt-only fix or general architecture is selected by this design.

## Execution boundary

**Not run.** The existing H1 cap has only 24 attempts left (2776/2800); this design needs 147 and therefore does not fit. A separate explicit phase/resource amendment and code/input freeze are required before execution; do not reset the old ledger or silently extend its cap. No paid API call, sealed data, NIE change or deployment is part of this proposed test. There is no reason to spend calls until its contrasts and neutral-control confounds are reviewed. This is one pending design, within the operating doctrine's two-design limit.


## Execution update — 2026-11-05

The proposal and its previous "not run/resource amendment required" state above are historical. Cap amendment `6a24f95`, code/preparation `0cac1cd`, and raw freeze `edeb178` preceded the separate score. [Density results](../../data/lab/h1-evidence-density-v1/README.md):147local calls, one stale leak on developmentQ000045 only in stale-repeat/correction-first, all other conditions24/24. This is different from the original validationQ000043 failure, which remains in the original records. The separately frozen [whole-H1 order study](../../data/lab/h1-chronological-pack-v1/README.md) also completed:339local calls, dev77to75/84, valid70to72/84 and2to0leaks. No adoption; preserve scorer caveats and native variability. No new paid calls. The execution registry records are retrospective links to prior protocol freezes, not retroactive preregistration.
