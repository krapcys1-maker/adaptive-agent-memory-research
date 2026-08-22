# Assessment of the DeepSeek advisory review

Status: model review preserved, critically assessed, and not treated as independent acceptance

The three author-operated DeepSeek V4 Flash roles all returned `needs_revision`. The valid API calls cost USD 0.013849 conservatively; one truncated JSON response is retained as an error and was replaced only by a schema-valid retry. The model saw frozen, content-free protocols and aggregates—not raw questions, conversations, answers, evidence IDs, personal files, or an API key.

## Findings accepted

- The public bridge is small and potentially contaminated. It cannot support confirmation or architecture promotion.
- The registered v0.1 label `supports-sparse-transfer` must not be paraphrased as statistically demonstrated B2 superiority. The paired 95% interval is `[0.000000, 0.116667]`, so zero remains compatible with the data.
- The repaired v0.1 run occurred after the invalid v0 point estimate was visible. Its mechanical repair is auditable, but the result is a known-outcome replication rather than fresh confirmatory evidence.
- B1 and B2 generated candidates on all six incomplete-answer cases. Near-miss intrusion at five was `1.000` and `0.833`; retrieval alone does not solve completeness or answer abstention.
- The next comparison should include local dense and hybrid retrieval under matched retrieval/context budgets, while a separate controller/reader test measures completeness, stale/poison handling, and correct abstention.
- Natural project histories, stronger power, and human or cross-family review remain necessary.

## Findings qualified or rejected

- The review calls the PMLAB interval `[0.003030, 0.121212]` non-significant while also printing a strictly positive percentile interval. That statement is internally inconsistent. PMLAB remains exploratory because its labels are M2 and its test is authored—not because that interval contains zero.
- The bridge protocol deliberately reports candidate-null and near-miss retrieval as diagnostics and explicitly says neither is correct answer abstention. The model's claim that the project conflated the constructs is false; the observed zero candidate-null rate is still an important negative result.
- Tie-breaking is inherited and explicit in lexical-v0. Duplicate, unknown, and over-limit IDs are rejected by the frozen runner. Their omission from the shortened review payload is a review-packet documentation limitation, not evidence that the execution silently accepted them.
- A fixed bootstrap seed is a reproducibility control, not itself a statistical defect. Monte Carlo sensitivity may be reported later, but it was not a preregistered gate.
- The suggestion of at least 100 answerable questions per type is an unsupported round number. The next sample size must come from a declared minimum effect, variance/pilot data, and power or precision target.
- Unequal returned bytes matter for downstream reader comparisons, but cannot explain identifier-level retrieval Recall@5 because no reader consumed those bytes in this bridge.

## Final disposition

Keep the frozen registered decision unchanged as an audit fact: v0.1 passed its descriptive `supports_sparse_transfer` rule. Narrow the scientific interpretation: on this 30-question public answerable slice, B2 had a `+0.05` point estimate over B1, with an interval compatible with no difference and with improvements concentrated in two of six types. This is weak transfer compatibility evidence for retaining B2 as the current sparse baseline, not evidence of general superiority.

The review is useful adversarial pressure at evidence tier M1. It is not an independent audit, does not validate raw data, and cannot promote a claim into canonical evidence without deterministic checks, source access, and a genuinely independent or cross-family review.
