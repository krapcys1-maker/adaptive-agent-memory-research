# Catalog entity/time parser v0

Status: completed development baseline; challenge templates were observed before implementation

## Runtime contract

`parse_query(text, catalog)` receives only the query string and a catalog derived from stored corpus metadata: entity, topic, version, and `valid_from`. It does not receive the query's `history_id`, category, gold evidence IDs, or expected answer. Scoring uses those labels only after retrieval.

The parser performs deterministic entity/topic matching and recognizes ISO dates, English month dates, current intent, and one English/Polish relative-version template. It abstains on unknown entities, unresolved time, and unresolved entity ambiguity.

## Development result

Across the existing 24-query challenge:

- answerable history resolution: 1.000;
- answerable target-date resolution: 1.000;
- unanswerable parser abstention: 1.000;
- FTS5 Recall@5 after parser normalization: 1.000 versus 0.400 for raw text;
- MRR: 1.000 versus 0.289;
- oracle-normalized Recall@5: 1.000;
- parser history scoping added no gain over parser normalization alone.

Forbidden stale-version intrusion remained 1.000 for both parser arms. The parser therefore closes target discovery on this fixture but does not solve validity filtering or safe context construction.

## Interpretation boundary

This is not held-out evidence. The rules were written after the challenge's wording and corpus schema were visible, so the perfect parser score is vulnerable to template overfitting. It authorizes a frozen paraphrase, typo, alias, multilingual, date-format, and temporal-expression challenge without modifying parser v0. It does not authorize parser or architecture promotion.
