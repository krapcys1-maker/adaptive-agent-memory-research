# PMLAB-MAP construction baseline report

Status: deterministic development result; corpus was inspectable and is not held out

Corpus freeze commit: `4b6c47e`. Runner: `pmlab-map-construction-runner-v1`.

| Arm | Obligation F1 | Critical full recall | Structure exact | E2E exact | False closure |
| --- | ---: | ---: | ---: | ---: | ---: |
| `whole_query_single_scope` | 0.563 | 0.750 | 0.536 | 0.482 | 0 |
| `conjunction_splitter` | 0.756 | 0.821 | 0.536 | 0.482 | 0 |
| `qdmr_rules_pipeline` | 0.922 | 1.000 | 1.000 | 0.679 | 0 |
| `gold_obligations_predicted_links` | 1.000 | 1.000 | 1.000 | 0.750 | 0 |
| `gold_oracle` | 1.000 | 1.000 | 1.000 | 1.000 | 0 |

## Link-stage diagnostic

| Arm | Entity | Predicate | Namespace | Time | Authorization | Certificate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `gold_obligations_predicted_links` | 0.933 | 0.956 | 0.978 | 0.911 | 1.000 | 0.978 |
| `qdmr_rules_pipeline` | 0.940 | 0.916 | 0.940 | 0.916 | 1.000 | 0.976 |

## Construction-gate disposition

- critical full recall: 1.000 — pass;
- obligation F1: 0.922 — pass;
- false closure: 0 — pass;
- entity top-1 proxy: 0.940 — fail;
- predicate top-1 proxy: 0.916 — fail;
- exact supported temporal mapping proxy: 0.916 — pass;
- critical unresolved safe handling: 1.000 — pass.

The construction arm is rejected for promotion because entity and predicate linking miss the preregistered 0.95 thresholds. The apparent temporal pass is only a coarse exact-label proxy on authored cases, not the registered supported-expression interval metric.

## Interpretation boundary

The rules were written after the construction corpus was inspectable. Scores measure instrument behavior and expose stage failures; they are not estimates of generalization. No arm may be promoted until its implementation is frozen and evaluated on a new grouped challenge with unseen compound signatures and schemas.

`gold_obligations_predicted_links` isolates the linker ceiling after perfect decomposition. `gold_oracle` is a scorer contract check. Any false closure or critical omission blocks promotion regardless of average F1.
