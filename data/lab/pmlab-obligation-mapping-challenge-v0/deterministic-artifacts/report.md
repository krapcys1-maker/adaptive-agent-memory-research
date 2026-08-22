# PMLAB-MAP post-freeze deterministic challenge

Status: post-arm challenge result; unseen to prediction code but labels are not independently reviewed

Challenge freeze: `adc540f`. Prediction implementation freeze: `6a82bd8`.

| Arm | Obligation F1 | Critical full recall | Structure exact | E2E exact | False closure | F1 drop vs construction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `whole_query_single_scope` | 0.409 | 0.250 | 0.429 | 0.000 | 10 | 0.154 |
| `conjunction_splitter` | 0.442 | 0.250 | 0.429 | 0.000 | 10 | 0.314 |
| `qdmr_rules_pipeline` | 0.409 | 0.250 | 0.429 | 0.000 | 10 | 0.514 |
| `gold_obligations_predicted_links` | 1.000 | 1.000 | 1.000 | 0.071 | 0 | 0.000 |
| `gold_oracle` | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 0.000 |

## Frozen-arm disposition

- QDMR rules: entity 0.000, predicate 0.053, time 0.895;
- gold obligations plus frozen linker: entity 0.333, predicate 0.300, time 0.833;
- QDMR critical safe unresolved handling: 0.000;
- QDMR status exact: 0.643.

The deployable deterministic arm is rejected if it has any critical omission or false closure, misses the 0.90 obligation-F1 or 0.95 entity/predicate gates, or drops more than 0.05 on unseen schema or 0.10 on unseen composition. Gold arms remain diagnostics, never deployable results.

No parser rule was changed after the challenge was authored. The harness only loads the frozen prediction functions and scorer. Because the same research process authored the labels, this is stronger than construction evidence but weaker than an independently reviewed benchmark.
