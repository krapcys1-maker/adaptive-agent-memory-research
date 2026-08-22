# PMLAB-MAP challenge stage-failure localization

Status: post-hoc diagnostic on a spent post-freeze challenge; not a new benchmark result

Stages are ordered as contract, query status, graph, entity, predicate, namespace, time, authorization, certificate, and false closure. `first_failure` is descriptive, not causal: most failed cases contain multiple errors.

| Arm | First contract | First status | First graph | First entity | Pass | Multi-stage | Critical failures | False closure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `qdmr_rules_pipeline` | 0 | 10 | 16 | 2 | 0 | 24 | 24 | 10 |
| `deepseek_v4_flash` | 15 | 2 | 7 | 0 | 3 | 21 | 21 | 2 |

A single end-to-end score cannot identify the repair. Contract, unresolved-status, graph, and grounding errors co-occur. The next experiment must use stage-specific inputs and oracle isolation rather than tune an integrated parser on these 28 cases.
