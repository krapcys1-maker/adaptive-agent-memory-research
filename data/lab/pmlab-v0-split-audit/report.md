# PMLAB v0 development/test split audit

Status: v0 rejected for held-out confirmation before labels or backend execution

The label-free audit compared 300 within-category development/test query pairs. It flagged 22 pairs across 3 categories: causal_multi_episode, contradiction, procedure_failure.

The numeric thresholds are descriptive and post-hoc. The rejection does not depend on treating them as preregistered: the registered split policy already required different query templates, while direct paired inspection shows repeated frames with mostly entity/failure substitutions.

## Category maxima

| Category | Sequence | Token Jaccard | Character trigram Jaccard |
| --- | ---: | ---: | ---: |
| causal_multi_episode | 0.881 | 0.706 | 0.705 |
| contradiction | 0.893 | 0.769 | 0.724 |
| cross_language | 0.551 | 0.222 | 0.148 |
| exact_lexical | 0.706 | 0.400 | 0.295 |
| paraphrase | 0.536 | 0.188 | 0.137 |
| poison_resistance | 0.780 | 0.522 | 0.520 |
| procedure_failure | 0.892 | 0.625 | 0.657 |
| supersession | 0.771 | 0.500 | 0.444 |
| temporal_as_of | 0.818 | 0.538 | 0.414 |
| unanswerable | 0.603 | 0.556 | 0.327 |
| weak_overlap | 0.466 | 0.167 | 0.110 |
| what_where_when | 0.792 | 0.600 | 0.492 |

## Decision

Do not request independent labels and do not execute B0/B1/B2 on this split. Preserve the corpus, protocol, and audit as a pre-run instrument failure. V0.1 must change test query forms without changing evidence records or reading backend results, rerun this audit, and issue new packet hashes.
