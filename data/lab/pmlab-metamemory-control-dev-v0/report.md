# PMLAB metamemory-control development run v0

Status: exploratory construction test on a frozen authored corpus; not held out

## Result

| Policy | Coverage | Selective risk | Stored-target recovery | False known | False unknown | Critical unsupported | Provenance accepted | Mean cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no_monitor | 0.538 | 0.571 | 0.333 | 8 | 8 | 8 | 0.786 | 0.000 |
| self_confidence | 0.385 | 0.800 | 0.111 | 8 | 12 | 8 | 0.700 | 0.000 |
| cue_familiarity | 0.385 | 0.800 | 0.111 | 8 | 12 | 8 | 0.700 | 0.000 |
| semantic_consistency | 0.385 | 0.800 | 0.111 | 8 | 12 | 8 | 0.700 | 0.000 |
| typed_monitor | 0.231 | 0.000 | 0.333 | 0 | 12 | 0 | 1.000 | 0.019 |
| typed_control | 0.692 | 0.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0.981 |
| oracle | 0.692 | 0.000 | 1.000 | 0 | 0 | 0 | 1.000 | 0.000 |

The fixed typed-control state machine recovered alternate-cue, direct-ID, poison-adjacent, and stale-version targets while refusing absent, ambiguous, and conflicting cases. Scalar policies failed specifically on the authored high-confidence/common-mode-wrong cases. Typed monitoring without control remained safe but could not recover targets missed by the first cue.

## Candidate gate checks

- `critical_unsupported_zero`: PASS
- `recovery_gain_at_least_15_points`: PASS
- `distortion_not_increased`: PASS
- `accepted_provenance_complete`: PASS

## Valid interpretation

Authored deterministic development construction test. Passing gates validates only the implemented state-machine semantics, not generalization or architecture efficacy.
The next admissible test must replace authored operation outcomes with real retrieval backends, hide labels from policy development, add risk-coverage sweeps, and receive independent review.
