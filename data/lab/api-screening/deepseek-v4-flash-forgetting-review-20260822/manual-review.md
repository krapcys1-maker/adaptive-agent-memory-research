# Manual review of DeepSeek F1/F2 challenge candidates

Status: reviewed by benchmark author; not independent validation

Run cost: USD 0.00289828 conservative. Cumulative worker ledger after this run: USD 0.06426508 of the USD 10 hard cap.

| Candidate | Disposition | Review |
| --- | --- | --- |
| `tautological-probe` | accepted | 28/28 is a unit test of authored stage logic, not an empirical accuracy estimate. Independent blind traces remain required. |
| `missing-controls` | accepted | Multi-fault, missing-telemetry, noisy and ambiguous cases are absent. They remain the next F1 gate. |
| `oracle-advantage` | accepted and mitigated | The original B3 consumed gold `history_id` and `as_of_version`. It was replaced after this frozen review by a rule-based exact-entity/ISO-date resolver that consumes query text only. The replacement is still template-fitted and not held out. |
| `metric-artifact` | accepted with wording correction | The worker called update-count growth “higher k”; `top_k` was fixed at five. Its substantive point is correct: the sharp failure at eight updates is induced by templated ties and the fixed retrieval cutoff. |
| `label-leakage` | accepted | No architecture claim is allowed until independently authored, held-out data are frozen. |

The model did not assign or modify gold labels. Accepted changes were made through deterministic local review. The review manifest hashes the pre-mitigation benchmark state, preserving the order of events.
