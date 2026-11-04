# Public lexical-gate comparison — protocol for issue 72

Fixed before this evaluation's first result. This is a descriptive, model-free, post-publication investigation, not a blinded confirmatory study. The author has seen the issue's H1 starter numbers and R1 summary. The design is timestamped in Git before execution; no kernel/default is edited and no setting will be selected on these reported curves.

## Data and adapters

All inputs are already public authored fixtures in this Apache-2.0 repository (see `LICENSE`); no third-party dataset or private R1 notes are downloaded. Publish input digests, adapters, exclusions and query counts.

1. H1: `prefix-v0/history.jsonl`, `reveal-v0/queries.jsonl`, `gold.jsonl`. Gold is the declared event ID. Date is the end of `asked_on_day`, with day one 2026-01-01, as in the issue starter.
2. E6 persona: the 26 dated biography items and 24 fact questions in `aam-e6-persona/persona.json`. Gold uses R1 U2's published rule: biography items containing any authored answer key as a whole phrase, case-insensitively. Exclude questions with no biography match and list their IDs. This is an answer-key retrieval proxy, not proof that an item fully answers a multi-key question. Query date 2026-12-01; task type personal, names channel disabled.
3. H2 dev and valid, reported separately: events, queries and gold under `corpus-h2/`. Map `recorded_on` to a transaction date with day one 2026-01-01; query date is end of `asked_on`. Gold is the declared event ID. Do not oracle-filter by `valid_from` or add supersession metadata: this evaluation measures retrieval of recorded text, not a temporal answer resolver. Temporal traps are an explicit limitation. Both public splits are descriptive; neither is claimed sealed confirmation.

Indexes include all source items; both modules retain their normal no-future retrieval gate. No key matching or gold information enters retrieval prompts/scores. Tie-breaks are each kernel's deterministic item-ID order after its unrounded score; report scores/rank IDs for inspection.

## Fixed grid

Rank only: names/embeddings off, `k=10`, `lex_tau=1e-9`, `min_evidence=0`. Compare frozen coverage with live BM25 `b` in 0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0 at `k1=1.2`; additionally k1=0.5/2.0 at b=0.75. Cross every live row with max_terms=20 and 0, top_terms=10. Top_terms changes a query-wide reference, not ranking. No standalone old-tokenizer BM25 row is claimed; tokenizer/stop-list differences confound comparisons across versions, while the within-live-line b curve isolates that parameter.

Gate: live `min_evidence=1.4`, `k=3`, k1=1.2, b=0.75, max_terms=20; `lex_tau` in 0.05, 0.10, 0.15, 0.20, 0.30, 0.45 crossed with `top_terms` in 0, 3, 5, 10, 20. Coverage uses its shipped lexical profile with k=3 (names off to isolate lexical retrieval). Do not change either module's shipped profile.

Negatives: persona fact questions against H1/H2 operational histories, and H1 operational questions against the persona biography. These disjoint authored worlds have no intended cross-world answer; common vocabulary remains allowed. This is a constructed no-answer bank, not independent human relevance labelling. Report its size, provenance and unrelated firing rate separately from positive-query firing and gold shown.

## Metrics and interpretation

Per suite and rank row: recall@1/@3/@10 (any gold event ID shown), the coverage-only and live-only hits, paired mean differences and percentile 95% bootstrap intervals over queries. Use 2,000 resamples, fixed seed 1729; no model. For gate rows report any-positive firing, gold shown and unrelated firing shares with counts. Keep dev/valid and suites separate; no pooled headline or globally optimal default is selected.

Publish mixed/negative outcomes as complete evidence. A default recommendation would require choosing on one suite and evaluating elsewhere under a separate stated rule; this report deliberately makes none. It does not overturn R1's failed judge gate, establish downstream writing quality or validate LifeSim. Both kernel files and all 18 WMB-R1 script declarations must remain byte-identical.
