# PMLAB evidence-sufficiency construction run v0

Status: exploratory construction test on corpus frozen before runner implementation; not held out

| Policy | Exact action | Coverage | Selective risk | False sufficient | False insufficient | Gap action | Obligation recall | Claim precision | False not-found | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| nonempty | 0.278 | 0.889 | 0.750 | 0.667 | 0.000 | 0.083 | 0.000 | 0.607 | 2 | 0.000 |
| similarity | 0.167 | 0.833 | 0.800 | 0.667 | 0.056 | 0.000 | 0.000 | 0.593 | 0 | 0.000 |
| context_relevance | 0.167 | 0.833 | 0.800 | 0.667 | 0.056 | 0.000 | 0.000 | 0.593 | 0 | 0.000 |
| self_report | 0.167 | 0.833 | 0.800 | 0.667 | 0.056 | 0.000 | 0.000 | 0.593 | 0 | 0.000 |
| semantic_consistency | 0.167 | 0.833 | 0.800 | 0.667 | 0.056 | 0.000 | 0.000 | 0.593 | 0 | 0.000 |
| claim_entailment | 0.222 | 0.278 | 0.200 | 0.056 | 0.056 | 0.000 | 0.000 | 1.000 | 0 | 1.000 |
| retrieved_obligation | 0.778 | 0.278 | 0.000 | 0.000 | 0.000 | 0.667 | 1.000 | 1.000 | 0 | 1.000 |
| collection_hybrid | 1.000 | 0.278 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0 | 3.000 |
| oracle | 1.000 | 0.278 | 0.000 | 0.000 | 0.000 | 1.000 | 1.000 | 1.000 | 0 | 0.000 |

## Candidate gate checks

- `zero_critical_false_sufficient`: PASS
- `gap_action_at_least_0.90`: PASS
- `obligation_recall_at_least_0.90`: PASS
- `claim_support_precision_at_least_0.95`: PASS
- `matched_coverage_point_available`: FAIL
- `matched_coverage_risk_gain_at_least_0.15`: FAIL
- `zero_false_not_found`: PASS

## Interpretation

The retrieved-obligation arm can recognize conflict, invalid evidence, missing facets, unsupported extra claims, and attribution gaps without converting a miss into storage loss. It cannot distinguish a recoverable collection miss from a truly absent facet without a collection-scope probe.
Its remaining exact-action errors are {"absent-empty-retrieval": 2, "absent-with-similar-distractor": 2, "missing-bridge-unavailable": 2, "missing-facet-unavailable": 2}.

The collection-aware hybrid consumes authored collection and obligation labels, so a pass validates only the typed decision contract. The next challenge must replace gold mappings with a frozen query decomposer, evidence mapper, real retrieval outputs, and independently reviewed labels.
The nearest self-report point differs from hybrid answer coverage by 0.444; the matched-coverage gate remains closed when this exceeds 0.06.
