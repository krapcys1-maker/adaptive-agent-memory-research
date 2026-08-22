# Manual review of challenge-v0 methodology candidates

Status: reviewed by benchmark author; not independent validation

Run cost: USD 0.00309408 conservative. Cumulative worker ledger after this run: USD 0.06735916 of the USD 10 hard cap.

| Candidate | Disposition | Review |
| --- | --- | --- |
| F1 tautological isolated probes | accepted | Perfect agreement is a contract/unit test. It cannot estimate causal localization from passive telemetry. |
| Add cascading end-to-end controls | accepted | The next F1 comparison must measure passive traces against active isolated probes. |
| Missing single/no-fault cases | partially rejected | This challenge includes an all-healthy control and complements the earlier 28-case single-fault suite. The review input summarized the challenge alone, so future manifests must expose linked control suites. |
| B3 conflates query understanding and retrieval | accepted | The next run will use a 2x2 query-normalization by validity-filtering design. |
| Gold oracle leaks labels | boundary accepted; wording rejected | The oracle intentionally returns registered gold evidence to define a ceiling; it is not a competing system. The real limitation is that gold was not independently annotated. |
| Forbidden intrusion may be a metric artifact | retained with clarification | Any forbidden version in top five is a strict binary risk flag. v1 must add intrusion count, rank, token share, and measured reader effect. |
| Update-count curve confounded | rejected as inapplicable | Challenge v0 has no update-count curve. The generic worker job used the wrong question. The preparation code was corrected after this frozen run. |
| No independent validation | accepted | Architecture promotion remains blocked. |

The worker neither created nor modified accepted labels. The prompt mismatch is preserved as a worker failure rather than silently removed.
