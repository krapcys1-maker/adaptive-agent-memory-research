# PMLAB-MAP construction baseline report

Status: deterministic development result; corpus was inspectable and is not held out

Corpus freeze commit: `4b6c47e`. Runner: `pmlab-map-construction-runner-v0`.

| Arm | Obligation F1 | Critical full recall | Structure exact | E2E exact | False closure |
| --- | ---: | ---: | ---: | ---: | ---: |
| `whole_query_single_scope` | 0.563 | 0.750 | 0.536 | 0.375 | 0 |
| `conjunction_splitter` | 0.756 | 0.821 | 0.536 | 0.375 | 0 |
| `qdmr_rules_pipeline` | 0.911 | 0.964 | 1.000 | 0.482 | 0 |
| `gold_obligations_predicted_links` | 1.000 | 1.000 | 1.000 | 0.357 | 0 |
| `gold_oracle` | 1.000 | 1.000 | 1.000 | 1.000 | 0 |

## Interpretation boundary

The rules were written after the construction corpus was inspectable. Scores measure instrument behavior and expose stage failures; they are not estimates of generalization. No arm may be promoted until its implementation is frozen and evaluated on a new grouped challenge with unseen compound signatures and schemas.

`gold_obligations_predicted_links` isolates the linker ceiling after perfect decomposition. `gold_oracle` is a scorer contract check. Any false closure or critical omission blocks promotion regardless of average F1.
