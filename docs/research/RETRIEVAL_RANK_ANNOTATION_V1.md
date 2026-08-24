# Retrieval Rank Annotation — Exploratory Test v1 ("Mechanism F")

Preregistration: `PM-20260824-d7372cde`. **Verdict: `MECHANISM_F_FAIL` — DROP.** Third consecutive failed mechanism family for this campaign (`D`, `E`, `F`) — triggers **STOP condition B**.

## Mechanism

Read-side, deterministic, zero LLM, unconditional: every retrieved item gets a `[rank N/M, relevance X.XX]` prefix, always — no threshold gate, direct response to `D`/`E`'s regime-mismatch lesson (Ledger Entries I, J).

## Results

8/8 fresh, gold-blind units, all 6 LongMemEval categories. The mechanism fired on every unit as designed (no regime-mismatch this time — confirms the "universal precondition" fix worked structurally). **Net repairs: 0. Regressions: 1** (`06f04340`).

| unit | type | BASE | +F |
|---|---|---|---|
| `19b5f2b3` | single-session-user | OK | OK |
| `129d1232` | multi-session | OK | OK |
| `06f04340` | single-session-preference | OK | **WRONG** |
| `157a136e` | multi-session | OK | OK |
| `2ebe6c90` | temporal-reasoning | WRONG | WRONG |
| `2ebe6c92` | temporal-reasoning | WRONG | WRONG |
| `0e4e4c46` | knowledge-update | OK | OK |
| `16c90bf4` | single-session-assistant | WRONG | WRONG |

## The regression, examined

`06f04340` — a preference-rubric question ("what should I serve for dinner... with my homegrown ingredients"). `BASE` answers decisively: identifies basil/mint/mixed-greens, proposes a specific dish, done. `+F`'s answer covers the *same* substantive content (basil, mint, quinoa salad, greens) but rambles into a tangent (a margarita mentioned in a lower-ranked, irrelevant item) and closes with an explicit hedge: *"the context doesn't specify exactly what other homegrown ingredients you have, so the answer cannot be fully determined."* The judge (preference-rubric template: correct as long as it recalls and uses the user's information) scored `BASE` correct and `+F` wrong — plausibly on that closing hedge reading as not actually committing to an answer.

**This matches a pattern already recorded multiple times elsewhere in this project** (E1's `+SRC` regressions, Stage 2's `031748ae`/`0977f2af`): adding structured meta-information to context can induce more hedging/cautious reader behavior, which a binary judge penalizes even when the underlying content is comparable. Not a new failure mode — a recurrence of "judge-penalized epistemic caution," now observed under a third, unrelated mechanism (rank/score annotation), which strengthens rather than narrows its status as a general risk of annotation-style interventions in this harness.

## Classification: `MECHANISM_FAILURE` (mild), not regime mismatch

Unlike `D` and `E`, this mechanism *did* fire everywhere — the universal-precondition fix worked exactly as intended. The failure here is a genuine (if narrow, n=1) negative interaction between the added annotation and reader/judge behavior, not an unexercised mechanism. Net effect at this sample size: strictly negative (0 repairs, 1 regression).

## Verdict and campaign consequence

**DROP.** No repair, one traceable regression. Per the circuit breaker and "don't force a second attempt," no retuning is attempted (the failure mode is qualitatively identical to previously-observed judge-caution regressions, not a fixable implementation bug).

This is the **third consecutive mechanism family** to close without a replicated positive signal in this autonomous campaign (`D`: regime mismatch/small-n; `E`: regime mismatch/never fired; `F`: fired everywhere, net negative). Per the campaign contract's **STOP condition B** ("3 consecutive mechanism families fail to produce a replicated positive signal"), the autonomous campaign stops here. Final report to follow.

## Cost

$0.581880 (ingest-dominated: 388 sessions across 8 units; reader+judge ~$0.003). One transient "Invalid JSON response" ingest warning, same benign pattern as prior runs — all 8 units show sane stored counts, no contamination FAIL.
