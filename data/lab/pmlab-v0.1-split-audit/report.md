# PMLAB v0.1 development/test split audit

Status: automated descriptive screen passed; independent leakage audit still required

The label-free audit compared 300 within-category development/test query pairs. It flagged 0 pairs across 0 categories: none.

The numeric thresholds are descriptive and post-hoc. They are a construction diagnostic, not proof of semantic independence. The registered split policy separately requires different development/test query forms.

## Category maxima

| Category | Sequence | Token Jaccard | Character trigram Jaccard |
| --- | ---: | ---: | ---: |
| causal_multi_episode | 0.451 | 0.136 | 0.161 |
| contradiction | 0.454 | 0.222 | 0.209 |
| cross_language | 0.436 | 0.083 | 0.146 |
| exact_lexical | 0.413 | 0.077 | 0.084 |
| paraphrase | 0.438 | 0.105 | 0.125 |
| poison_resistance | 0.385 | 0.185 | 0.225 |
| procedure_failure | 0.496 | 0.273 | 0.367 |
| supersession | 0.477 | 0.167 | 0.226 |
| temporal_as_of | 0.440 | 0.294 | 0.256 |
| unanswerable | 0.400 | 0.111 | 0.098 |
| weak_overlap | 0.412 | 0.167 | 0.093 |
| what_where_when | 0.373 | 0.125 | 0.160 |

## Decision

The candidate may proceed to direct template inspection and independent leakage review. This screen does not unlock labels or backend execution.
