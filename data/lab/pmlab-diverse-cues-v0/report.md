# Diverse-cue retrieval development run v0

Status: protocol and runner frozen before execution; source corpus was previously inspected and is not held out

| Arm | Safe action | Selective risk | Recall@5 | Forbidden | Abstention | Cross-language recall | Depth |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw | 0.458 | 0.522 | 0.841 | 0.292 | 0.000 | 0.000 | 5 |
| time | 0.667 | 0.304 | 0.841 | 0.083 | 0.000 | 0.000 | 10 |
| trust | 0.542 | 0.435 | 0.841 | 0.208 | 0.000 | 0.000 | 10 |
| bilingual | 0.542 | 0.458 | 0.932 | 0.292 | 0.000 | 1.000 | 5 |
| time_trust | 0.750 | 0.217 | 0.841 | 0.000 | 0.000 | 0.000 | 10 |
| time_trust_bilingual | 0.833 | 0.167 | 0.932 | 0.000 | 0.000 | 1.000 | 10 |

## Frozen candidate gates

- `safe_action_gain_at_least_15_points`: PASS
- `forbidden_intrusion_at_most_0.05`: PASS
- `cross_language_gain_at_least_0.50`: PASS
- `unanswerable_abstention_at_least_0.50`: FAIL

## Interpretation boundary

authored inspected development corpus and tailored glossary; not confirmatory
A failed abstention gate means the bundle is not a complete metamemory controller even if validity, trust, and bilingual retrieval improve.
