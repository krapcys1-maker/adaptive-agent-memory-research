# Declared-label coverage audit v1

Status: base audit completed; five-group coverage amendment authored; independent review still required

The base allocation has exactly 72 semantic groups and 144 paired PL/EN rows across all six stages. Structural validation and quota compliance are necessary but not sufficient: the builder now compares every declared enum in `case-schema-v1.json` with observed gold labels.

## Uncovered labels

| Declared label | Classification | Disposition before candidates |
| --- | --- | --- |
| `contract_span.reject_reason=unsafe_unresolved_state` | true negative-control gap | add a schema-valid ambiguous/unauthorized payload carrying an unsafe conclusive certificate |
| `entity_linking.action=mention_not_detected` | upstream-boundary control absent | add an explicitly invalid/missing mention-span control and label it as a boundary case, not ordinary entity retrieval |
| `time_authorization.time_status=unsupported` | true temporal-control gap | add an unresolvable event/future-condition temporal control distinct from vague ambiguity |
| `certificate_routing.action=partial_with_gap` | true routing-action gap | add mixed supported/incomplete facets with an explicit gap |
| `certificate_routing.action=abstain` | true routing-action gap | add a case where neither clarification nor further local search can safely resolve the query |
| `obligation_graph.query_status=unauthorized` | stage-contract inconsistency | do not inject policy into a raw-query-only graph stage; supersede or narrow this enum in a versioned schema amendment and keep authorization tests in `time_authorization` |

## Decision

Do not call the 72-group base corpus complete for implementation. Author a versioned supplemental coverage tranche before any candidate exists. Supplemental rows must remain development data, use new semantic-group IDs, preserve PL/EN pairing, and be counted separately from the frozen base allocation. The graph status inconsistency must be documented rather than filled with a cross-stage leakage case.

The manifest's `uncovered_declared_labels` object is the machine-readable source of this audit. Independent label review remains a separate blocker after coverage repair.

## Resolution

`case-schema-amendment-v1.json` and `supplemental-coverage-groups-v1.jsonl` implement the five exercisable controls as new development groups without changing the 72-group base allocation. The accumulated corpus is 77 groups/154 rows. `manifest.json` now reports an empty `unresolved_coverage_gaps` object.

`obligation_graph.query_status=unauthorized` remains visible in `uncovered_declared_labels`, but its full disposition is recorded under `non_exercisable_declared_labels`: the isolated graph stage has no principal or policy input, so authorization belongs to `time_authorization` and to the later integrated contract. This is a schema-scope clarification, not a fabricated graph example.
