# PMLAB-PACK-READER-001 result

Status: completed single-family synthetic compatibility pilot; all frozen gates passed

## Result

The reader returned the exact answer set in all 128 conditions, used no stale atom, abstained in no answerable case, and emitted no unresolved citation. All four arms reached 16/16 bilingual groups exact-answer correct.

| Citation format | Order | Exact answer | Exact required citations | Required citation recall | Stale use |
|---|---|---:|---:|---:|---:|
| full path | retrieval | 32/32 | 32/32 | 1.000000 | 0/32 |
| full path | governed | 32/32 | 32/32 | 1.000000 | 0/32 |
| compact source alias | retrieval | 32/32 | 32/32 | 1.000000 | 0/32 |
| compact source alias | governed | 32/32 | 31/32 | 0.984375 | 0/32 |

The sole exception was `PRG-14-PL` in compact-governed order. The model returned both correct answer atoms but cited `R01,R03` instead of `R01,R02`. `R03` was a resolvable current record, so this was not an orphan citation, but it did not support the requested second atom. The other three conditions for the same semantic case cited `R01,R02` exactly. This isolated observation cannot establish a format, language, or order effect.

## Descriptive cost mediators

Compact aliases reduced the mean serialized user message from 1,430.625 to 1,084.125 UTF-8 bytes (`-24.22%`) and the mean provider prompt count from 653.094 to 548.594 tokens (`-16.00%`). These are registered descriptive mediators. Latency varied from approximately 1.08 to 1.14 seconds per arm mean and is not interpreted causally because calls were sequential and not latency-randomized.

The run made 128 stateless HTTP calls with zero retry or error. Conservative cost was USD 0.04026000 against the USD 0.50 experiment cap; the global project ledger became USD 0.97255180.

## Integrity and interpretation

- Fixture freeze: `365c0b6c0ae159b1517fbc87941aa33a8e369da2`.
- Prompt, runner, and scorer freeze: `d870741e8bba6257d12288b23d1e8f367571ae6e`.
- Raw-response freeze before gold join: `1df509b7b71f144fb924ba3737ec6c919de5857e`.
- The construction audit passed 11 checks; the prompt audit resolved 1,024/1,024 locators; the post-run deterministic audit independently reproduced the primary arm metrics and cost.
- Bilingual pairs count as 16 semantic groups, not 32 independent replications.

This supports compatibility of both locator representations and both orders for this authored fixture and this reader. It does not show that compact is superior, that governed order improves reading, that automatic current/stale labels are correct, that retrieval works, or that either choice transfers to natural project history. A second model family is required before a format or order recommendation. The synthetic fixture is now spent and must not be tuned into a new held-out claim.

## Next admissible tests

1. Repeat the unchanged frozen 128 prompts with a genuinely different model family and a separately frozen model/cost manifest.
2. Build natural-history development cases with real path reuse, longer evidence sets, automatic-label errors, mixed relevance, and independently reviewed answer/citation obligations.
3. Retain full paths as the baseline and compact aliases as a candidate. Do not promote governed order: this pilot showed compatibility, not benefit.
