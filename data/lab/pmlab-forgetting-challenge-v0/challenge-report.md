# F1/F2 adversarial challenge v0 report

Status: completed authored challenge; not independently annotated

## Why this run exists

The first development fixture made exact entity plus ISO-date validity look perfect. This run changes entities and templates, duplicates surface names across histories, replaces some ISO dates with relative and natural-language time, varies history length, and adds unanswerable ambiguity.

## F1 result

Sixteen isolated-probe traces include nine multi-fault cases and seven missing-telemetry cases. The deterministic diagnostic contract recovered every authored known-fault set, unknown-stage set, and data-loss label.

This remains a contract test. Isolation means that each stage must be replayed under a verified upstream control. It does not show that root causes can be inferred from one cascading trace. The next F1 instrument must compare:

- passive end-to-end telemetry only;
- active isolated probes;
- incomplete or contradictory instrumentation;
- independently authored root-cause labels.

## F2 result

| Backend | Answerable Recall@5 | MRR | Forbidden-version intrusion | Unanswerable abstention |
| --- | ---: | ---: | ---: | ---: |
| no memory | 0.000 | 0.000 | 0.000 | 1.000 |
| ripgrep | 0.400 | 0.289 | 1.000 | 0.250 |
| SQLite FTS5 | 0.400 | 0.289 | 1.000 | 0.250 |
| rule entity-time | 0.500 | 0.500 | 0.300 | 0.250 |
| gold evidence oracle | 1.000 | 1.000 | 0.000 | 1.000 |

The rule resolver retained perfect recall for unseen exact-current and ISO-date queries. It scored zero on natural-language and relative time, only 0.5 on duplicated-name current queries, and failed three of four unanswerable cases. This falsifies the broad interpretation of the development score: exact-name plus ISO parsing is useful but insufficient.

`Forbidden-version intrusion` means that at least one record explicitly labeled non-gold for the query appears anywhere in the top-five set. The measure is intentionally strict because every stale version consumes context and can influence a reader. It should be supplemented in v1 with count, rank, token share, and reader-effect measures rather than discarded.

## Mechanism decomposition required next

The present comparison changes both query understanding and candidate scoping. The next experiment must cross them rather than award one bundled score:

| Query interpretation | Candidate scope | Question isolated |
| --- | --- | --- |
| raw | all records | lexical baseline |
| normalized entity/time | all records | query-understanding contribution |
| raw | validity-filtered | metadata/filter contribution under a weak query |
| normalized entity/time | validity-filtered | combined mechanism |

Entity resolution must include an explicit ambiguous outcome. Time normalization must return an interval or version constraint with confidence and abstain when several interpretations remain.

## Decision

Reject the present B3 resolver as a sufficient memory-access layer. Retain three small components as candidates for separate testing: entity resolution with ambiguity, temporal normalization, and validity filtering. Dense retrieval remains locked because it cannot by itself determine which version is valid.

Reader-level value confusion remains untested. It is the next linked experiment after the 2x2 retrieval decomposition is frozen.
