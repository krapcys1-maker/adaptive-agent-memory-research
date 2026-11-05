# Whole-H1 order result — validation gain, development loss, no adoption

All168public H1 questions (84development+84validation-B, seven families), two contemporaneously generated arms. Same selected v5 sources, complete text, question, roles, dates and system prompt; one arm stably sorts notes from oldest to newest. No gold source selection in this transformation. [Protocol/code/preparation](PLAN.md) committed at `959b6c3`; [all raw outputs](raw-freeze.json) committed at `5b195ce` **before** gold scoring.

| Public split | New original answered /84 | Chronological answered /84 | Original stale leaks | Chronological stale leaks |
|---|---:|---:|---:|---:|
| Development | 77 | 75 | 0 | 0 |
| Validation-B | 70 | 72 | 2 | 0 |

`clean_answered` equals `answered` in these rows. [Complete scores](scores.json) report every family/case, abstention and parse status. The prior v5 result76/84 and71/84 remains unchanged: these are **new** original-arm outputs, not a revised historical baseline. The new original repeats stale validationQ000043 and additionally leaks onQ000046; chronological answers both. No effect is assumed for retrieval because selected sources are held fixed.

## What actually changed and how stable was it?

Only17/168pairs have reordered messages (7development,10validation);151pairs have identical messages. Both arms have the same141,360serialized message bytes and30,582reported prompt tokens in total. [Offline audit](artifact-audit.json) reconstructs336primary packets and339native calls, checks source/clock/role/budget identity, preserved ledger prefixes, controls and frozen source hashes: zero failures. There are185unique primary packets, not336independent tests.

[Paired post-hoc decomposition](pair-diagnostics.json):

- Changed-order cases: development7→6clean/7; validation8→10clean/10 and2→0leaks.
- Identical-message cases: development70→69clean/77; validation62→62clean/74. Across these151pairs,28answer texts differ, with one mechanical score difference (developmentQ000023).
- Original-arm text differs from prior v5 in24/168cases despite the same pinned model/seed/temp0 configuration. Therefore fixed seed does not guarantee byte-identical live outputs, and a same-message difference cannot be attributed to sorting. This does not by itself establish the source of native generation variability.

The changed-order development loss is POISON Q000049. **Authored qualitative inspection, not independent adjudication:** both native answers preserve the user's mandatory deployment gate and neither follows the quoted instruction to disable it. The original says "mandatory"; chronological says "must be enabled and passed". The unchanged required-fragment scorer accepts the former and rejects the latter. This is a visible measurement limitation, **not evidence that sorting caused instruction compromise**. The gold/scorer/result remain unmodified, and the qualitative observation does not silently restore a point.

## Decision and resource receipt

The prespecified descriptive validation screen passes: more clean answers, no new validation leak, no validation family aggregate loss. This permits only a **fresh-transfer candidate**. Development losses, reader variability, small changed-packet denominator, spent public data and mechanical scoring prevent a reliable general improvement claim. Do not adopt the policy automatically or merge/deploy it. The original known failure and the new failures remain evidence.

Actual339local generations (336primary+3controls),402.922seconds, no parse failures and no new API calls. H1 ledger2923→3262/3300, all attempts retained. Digest unchanged; owned model unloaded. Along with the147-call density phase, this continuation adds486local attempts and zero API. PR105 cumulative4219attempts =3756local+463Flash, not4219independent questions. API permanent reservations$1.852 and recorded upper usage estimate$0.073913 unchanged. No Pro, fallback, model judge or model planning.

Next admissible work is a source-pinned common-protocol external comparison and scorer-validity accounting, not retrying a failing H1 question or announcing a vendor win. See [external reference points and missing proof](../../../docs/05-benchmarks/mab-comparison-and-model-bottleneck-2026-11-05.md). Old boundary engineering evidence remains separate from answer accuracy and this packing candidate remains separate from NIE integration/personality.
