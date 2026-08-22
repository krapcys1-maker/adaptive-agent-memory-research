# F1/F2 development checkpoint

Status: completed exploratory instrument run; not held out

## Outcome

The run validates that the laboratory can preserve and score stage-level telemetry. It does not estimate real-world diagnostic accuracy or select a final retrieval architecture.

### F1 — authored fault localization

- 28 single-fault cases: four each for `OK` and `F0` through `F5`;
- authored stage-label agreement: 28/28;
- data-loss diagnosis errors: 0/28;
- raw-byte recoverability is distinct from the failed pipeline stage.

The perfect result is expected because the same author defined the traces and deterministic rules. It is a unit test of the fault vocabulary. It is not evidence of 100% localization on ambiguous, noisy, missing-telemetry, multi-fault, or independently authored traces.

### F2 — retrieval interference fixture

The corpus contains four entity histories with 64 updates each and 56 queries across update counts `1, 2, 4, 8, 16, 32, 64`.

| Backend | Current log2 AUC | Current stale intrusion | Historical Recall@5 | Historical future-version intrusion |
| --- | ---: | ---: | ---: | ---: |
| no memory | 0.000 | 0.000 | 0.000 | 0.000 |
| ripgrep | 0.417 | 0.857 | 1.000 | 0.393 |
| SQLite FTS5 | 0.417 | 0.857 | 1.000 | 0.393 |
| rule-based entity-time | 1.000 | 0.000 | 1.000 | 0.000 |
| gold oracle | 1.000 | 0.000 | 1.000 | 0.000 |

The lexical curves remain perfect through four versions and fall to zero at eight versions because the matching history exceeds `top_k=5` and neither backend understands validity. The exact breakpoint is a constructed ranking artifact, not a general performance estimate. Historical target recall remains high because the ISO date is a strong lexical cue, but future versions still intrude into the returned set.

The rule-based arm no longer reads gold `history_id` or `as_of_version`. It extracts one exact entity name and an optional ISO date from the query, then applies record validity. Its perfect score shows that explicit temporal scoping solves this fixture. Because the resolver and vocabulary were authored together, the result does not establish general entity resolution or natural-language temporal understanding.

## Adversarial review

A frozen five-job DeepSeek V4 Flash review correctly challenged the authored F1 score, initial oracle advantage, templated curve, missing multi-fault cases, and lack of a held-out gate. Its outputs remain model candidates. The oracle-input issue was repaired before this report; the other limitations remain blockers.

## Decision

Keep F1 and F2 at `completed-exploratory`. Advance the explicit entity-plus-valid-time mechanism to a held-out candidate comparison, but do not unlock dense retrieval or architecture promotion from these results.

The next gate requires:

1. independently authored and blindly labeled F1 cases, including multi-fault and missing telemetry;
2. unseen entities, paraphrased time expressions, ambiguous entity mentions, distractors, and unequal history lengths for F2;
3. equal token and `top_k` budgets;
4. a reader-level value-confusion condition separated from retrieval-only scoring;
5. bootstrap intervals over histories rather than treating templated queries as independent evidence.
