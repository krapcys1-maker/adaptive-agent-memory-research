# T0 DeepSeek advisory disposition

Status: author disposition of an M1 advisory review

Review packet: `deepseek-v4-flash-future-utility-t0-review-20260823`

Frozen input commit: `af620525aa3e5ae46a14dab5479f6ff6bd95579f`

Reviewed schema: `pmlab-utility-telemetry-v0`, SHA-256 `1d28da644790e06b661e772c73b6ff779f91a8a52c95760d7877e48a53d8f04a`

Cost: USD 0.00540056; cumulative conservative project ledger: USD 0.84754164

Both model roles returned `accept_t0_with_limits`. This is author-operated model advice, not independent privacy, statistical, human, or institutional review. It cannot unlock T1-T4.

## Accepted and implemented in v0.1

| Advisory issue | Disposition |
| --- | --- |
| Outcomes and closure were not bound to a frozen deadline | Added task-level `observation_window_end`; outcomes after it and changed/early closures are rejected |
| Shared memories can create cross-task interference/spillover | Added opaque `dependence_cluster_id`; tasks retrieving the same memory must share a cluster |
| `internal` sensitivity was not included in the external-processing prohibition | All sensitivity other than `none` now forbids external processing |
| Natural capture lacked a machine-checkable approval reference | Added opaque governance receipt plus retention class and access scope; non-synthetic allowlisted/explicit capture requires a receipt |
| Allowed-field minimization and governance were underspecified | T0 requires local/disposable synthetic governance; natural retention/access remain blocked for independent review |

These repairs are author-implemented post-review and have not themselves received independent or M1 review.

## Already implemented before the review

The following advisory statements were checked against frozen code and were already covered:

- randomized/synthetic propensity must be in `(0,1]`; natural observation requires null propensity and `natural` arm;
- correction cannot target another correction or a causal-effect event;
- a corrected copy must satisfy the target event contract while the original stays immutable;
- the recursive privacy scan reaches correction reasons and assessor identifiers and rejects registered secret/email patterns;
- U0-U4 labels retain observational names and `causal_effect_estimated` is rejected before T4.

These are implementation facts, not evidence that the controls are sufficient against every privacy or causal failure.

## Accepted as unresolved T1 blockers

- independent privacy review and DPIA-equivalent threat assessment;
- access control, authentication, encryption-at-rest decision, and privacy audit trail for a local sink;
- minimization of assessor/governance identifiers and re-identification analysis for hashes;
- export, correction, tombstone, and erasure semantics, including conflict with append-only audit history;
- authentic per-task outcome definitions and missingness denominators;
- informative-censoring analysis and clustered/interference-aware analysis plan;
- secure handling policy for any raw artifact that cannot enter canonical telemetry.

## Rejected as a next action

The reviewer suggested moving to T1 after synthetic consent/privacy controls. The project does not accept this as authorization. First, the T0.1 delta requires review and the local governance/erasure/outcome contracts must exist. T1 will be a no-model, no-ranking-change shadow pilot only after those gates close.
