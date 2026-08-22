# PMLAB collection-closure construction run v1

Status: exploratory construction test on corpus frozen before runner implementation; not held out

| Arm | Tier accuracy | Action accuracy | Critical tier | Coverage | Selective risk | Unsafe negative | N3 errors | N2 errors | Insert detection | Invalidations | Positive coverage | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| global_cwa | 0.167 | 0.167 | 0.118 | 0.958 | 0.870 | 0.952 | 40 | 0 | 0.000 | 0.000 | 1.000 | 0.10 |
| global_owa | 0.625 | 0.333 | 0.706 | 0.083 | 0.000 | 0.000 | 0 | 0 | 1.000 | 1.000 | 1.000 | 0.20 |
| retrieval_saturation | 0.417 | 0.417 | 0.294 | 0.958 | 0.609 | 0.667 | 0 | 28 | 0.000 | 0.000 | 1.000 | 1.00 |
| coarse_completeness | 0.750 | 0.542 | 0.706 | 0.542 | 0.308 | 0.364 | 0 | 8 | 0.000 | 0.500 | 1.000 | 1.20 |
| query_certificate | 0.917 | 0.917 | 0.882 | 0.417 | 0.100 | 0.125 | 0 | 2 | 0.000 | 1.000 | 1.000 | 2.00 |
| certificate_plus_insertion | 0.958 | 0.958 | 0.941 | 0.375 | 0.000 | 0.000 | 0 | 0 | 1.000 | 1.000 | 1.000 | 3.00 |
| oracle | 1.000 | 1.000 | 1.000 | 0.375 | 0.000 | 0.000 | 0 | 0 | 1.000 | 1.000 | 1.000 | 0.00 |

## Candidate gate checks

- `zero_unsupported_n3`: PASS
- `zero_unsupported_n2`: PASS
- `zero_critical_unsafe_strong_negatives`: PASS
- `mutation_and_expiry_invalidation_1.0`: PASS
- `critical_tier_accuracy_at_least_0.95`: FAIL
- `positive_safe_coverage_at_least_0.90`: PASS
- `counterexample_insertion_detection_1.0`: PASS
- `strong_negative_provenance_1.0`: PASS
- `matched_coverage_point_available`: FAIL
- `matched_coverage_unsafe_risk_gain_at_least_0.15`: FAIL

## Interpretation

Global CWA and retrieval saturation turn missing evidence into unsupported strong negatives. A coarse completeness flag still trusts wrong scope, stale version, missing domains, and unsound certificate claims.

The query-specific certificate arm leaves 2 unsupported N2 decisions; the insertion check leaves 0. This isolates whether an admissible missing insertion can change the answer.
The candidate's remaining tier errors are {"multi-facet-with-different-closure-scopes": 2}.

The construction does not validate natural-language obligation decomposition. The multi-facet case intentionally remains a boundary: one facet can be supported while another has only N1 closure. A later decomposer/mapper arm and unseen split are required.
Candidate and retrieval-saturation action coverage differ by 0.583; matched-coverage claims remain blocked when the gap exceeds 0.06.
