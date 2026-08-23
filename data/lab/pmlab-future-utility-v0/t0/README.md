# PMLAB-UTILITY-001 T0 synthetic validation

Status: completed construction validation; T1 remains locked

## Purpose

Test whether the append-only telemetry contract can represent and deterministically validate memory registration, task registration, candidate eligibility, retrieval, assignment, exposure, behavioral reference, outcomes, cost, corrections, retry delivery, and delayed-outcome censoring.

This is not a memory-quality, future-utility, or causal-effect result.

## Frozen inputs

- `../telemetry-event-v0.schema.json` — frozen schema reviewed by the M1 advisory worker;
- `../telemetry-event-v0.1.schema.json` — post-advisory Draft 2020-12 repair contract;
- `valid-deliveries.jsonl` — one complete and one censored synthetic task;
- `invalid-cases.json` — eleven registered mutations that must fail;
- `../../../../scripts/validate_future_utility_telemetry_t0.py` — dependency-free structural and cross-event validator.

Hashes are recorded in `../manifest.json` and the deterministic report.

## Result

| Check | Result |
| --- | ---: |
| Deliveries | 24 |
| Logical events | 23 |
| Exact retries collapsed | 1 |
| Corrections preserving original target | 1 |
| Tasks / closed windows | 2 / 2 |
| Explicitly censored tasks | 1 |
| Premature causal-effect events | 0 |
| Registered invalid cases rejected | 18 / 18 |
| Raw-content fields accepted | 0 |
| External-processing events | 0 |

The maximum observed pair levels were one U1-only pair, one U2 pair, and one U4 association. U3 is zero in the maximum-level table because the behaviorally referenced pair later reached U4. No U5 label was emitted. The two tasks share one dependence cluster because both retrieve the same memory.

## What passed

- byte-equivalent duplicate delivery becomes one logical outcome;
- conflicting identity reuse is rejected;
- retrieval must refer to a frozen candidate set;
- assignment must follow retrieval and synthetic/randomized assignment needs a nonzero propensity;
- shown/withheld observation must agree with the assignment arm;
- behavioral reference requires a prior shown exposure;
- outcomes must be registered before observation;
- correction points backward to an existing scalar payload field and leaves the target bytes unchanged;
- every missing registered outcome appears explicitly in a censored closure;
- logical recorded time cannot move backward and a correction must still satisfy the target event's contract;
- observation windows are frozen at task registration, outcomes cannot arrive after them, and closure cannot move the deadline;
- tasks that retrieve the same memory must share an opaque dependence cluster for later spillover-aware analysis;
- non-synthetic capture requires a governance receipt, while T0 remains local and disposable;
- sensitive external processing, raw content, and T0 causal-effect claims are rejected.

## Authority and next gate

T0 validates construction semantics only. Before T1 natural shadow capture, the project still needs:

1. an independent privacy/capture review;
2. an authentic task-family outcome dictionary;
3. an allowlist and redaction implementation for project artifacts;
4. a local append-only sink with export/correction handling;
5. a short no-model pilot proving completeness and missingness denominators.

T2-T4 remain locked. No memory may be hidden, promoted, deleted, reranked, or assigned a causal utility score from this result.

The DeepSeek M1 advisory accepted prior T0 with limits. Its disposition and post-review changes are recorded in `advisory-disposition.md`; the repaired v0.1 contract has not received independent review.
