# Local-backend agreement as a metamemory signal

Status: post-hoc exploratory analysis on the existing PMLAB development corpus; not held out

## Main result

Ripgrep and FTS5 both failed the same safe-retrieval criterion on 13 of 24 cases. Among the 19 cases where their top result agreed, 11 were still unsafe. Backend agreement is therefore not independent evidence when both systems share lexical features and the same corpus.

| Strategy | Answer coverage | Selective retrieval risk | Safe action accuracy | Recall@5 | Forbidden intrusion | Abstention |
|---|---:|---:|---:|---:|---:|---:|
| ripgrep | 0.958 | 0.522 | 0.458 | 0.841 | 0.292 | 0.000 |
| fts5 | 0.958 | 0.522 | 0.458 | 0.841 | 0.292 | 0.000 |
| intersection | 0.958 | 0.522 | 0.458 | 0.841 | 0.292 | 0.000 |
| union | 0.958 | 0.522 | 0.458 | 0.841 | 0.292 | 0.000 |
| agreement_gate_0.8 | 0.542 | 0.538 | 0.250 | 0.409 | 0.125 | 0.000 |

The agreement gate accepts FTS5 only when top-1 IDs match and set Jaccard similarity is at least 0.8. It is a frozen descriptive rule, not an optimized policy.

## Valid interpretation

This analysis uses real local backend outputs, but the corpus is authored development data, labels were visible, and the analysis was designed after earlier benchmark results existed. It can falsify the idea that lexical-backend agreement is independent confirmation on this corpus; it cannot estimate deployment calibration or validate typed control.

Next: add a genuinely different cue family (temporal/entity normalization or bilingual retrieval), freeze its outputs before labels are used for policy fitting, and obtain independent review of the acceptance criterion.
