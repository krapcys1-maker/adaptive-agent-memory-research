# Probe failure-domain and empirical reliability protocol v0.1

Status: design freeze v0.1; versioned research contract, not implementation evidence

## Purpose

Define when two memory diagnostics count as independent, how their false-health and false-failure rates will be measured, and which evidence can justify `physical data loss`, `access failure`, or `inconclusive`.

This protocol follows the passive/active, noisy-probe, and healthy-audit instruments. It prevents repeated calls to the same broken dependency from being counted as independent confirmation.

## Fixed diagnostic outcomes

Every investigation returns one of these states rather than a forced Boolean:

- `CAPTURE_FAILURE`: no accepted durable write can be established; the source may still permit recapture.
- `ACCESS_FAILURE`: checksum-valid canonical bytes are recovered, but a later structured read, index, retrieval, context, reader, or action path fails.
- `PHYSICAL_LOSS_CONFIRMED`: an accepted durable write is established and the target is absent from every inventoried authorized replica through media-level checks.
- `RECOVERABLE_CORRUPTION`: bytes exist and match an accepted receipt or reconstructable checksum, but schema/provenance parsing fails.
- `INCONCLUSIVE`: probes conflict, time out, share an unresolved failure domain, or replica inventory is incomplete.
- `NO_FAULT_OBSERVED`: the frozen probe suite passes; this is not proof that no intermittent fault exists.

`PHYSICAL_LOSS_CONFIRMED` is prohibited when only the primary device has been checked or the authorized-replica inventory is incomplete.

## Independence rule

Two observations count as independent evidence only when both conditions hold:

1. the frozen dependency map contains no unmitigated single failure domain capable of producing both observations; and
2. fault injection shows that one path can fail while the other remains observable and correct.

Different commands, code paths, or retries are not sufficient. In map v0, direct-ID read, full scan, raw-byte recovery, and schema reparse all share the primary filesystem and storage device. Raw-byte recovery is parser-independent but not media-independent. Therefore P2–P5 can establish an access/parser distinction, but cannot alone confirm physical loss.

P10, a separately inventoried replica with an alternate runtime, filesystem, device, and checksum implementation, is planned because no current probe supplies media independence.

P11 is an isolated restore drill. It restores into a disposable target without overwriting the source, verifies exact byte hashes and accepted operation IDs, parses canonical schemas, rebuilds derived indexes, runs current/historical retrieval probes, and records achieved recovery point and recovery time. A backup copy, repository check, or SQLite structural integrity check does not substitute for P11.

## Write-receipt evidence levels

- `W0`: application accepted and assigned an operation ID;
- `W1`: runtime buffer flush completed;
- `W2`: atomic replace/database transaction returned;
- `W3`: required file, journal/WAL, and directory sync returned under the declared VFS/device assumptions;
- `W4`: a fresh process reopened and matched exact bytes/receipt after a restart;
- `W5`: a separately inventoried alternate failure domain verified the same accepted content;
- `W6`: P11 restored canonical content and rebuilt usable views while reconciling accepted IDs.

Reports state the highest observed tier and its assumptions. They may not translate W2/W3 into independent recovery or W5 into a tested restore.

## Reliability measurements

For each probe and each relevant failure injection, record:

- truth state and injection ID;
- first result and repeated results;
- false-healthy, false-failure, timeout, malformed-result, and stale-result indicators;
- process, host, filesystem, storage device, parser, index, model, and fixture versions;
- p50/p95/p99 latency, bytes read/written, and retry count;
- every shared dependency active during the observation.

Report marginal rates and joint contingency tables. Pairwise non-correlation is not proof of independence; conditional failure rates must be reported by injected domain. A zero-error sample is stated with its denominator. As a planning approximation, zero events in 300 trials only bounds the one-sided 95% rate near 1%; approximately 3,000 clean trials are needed for a near-0.1% bound. These are sample-planning rules, not guarantees.

## Required injection families

1. accepted write lost before fsync or durable commit;
2. torn/truncated append and checksum mismatch;
3. valid bytes with unknown or incompatible schema;
4. permissions, path, mount, and stale-handle failures;
5. primary index omission with intact canonical bytes;
6. stale index snapshot and clock/validity error;
7. primary process crash and clean restart;
8. primary storage-device unavailable while alternate replica remains readable;
9. shared fixture/oracle corruption;
10. reader/provider timeout and deterministic wrong answer with gold context;
11. action adapter failure after a fixed correct answer;
12. correlated failures that simultaneously affect nominally different probes.
13. successful structural restore with one or more accepted logical records omitted;
14. backup/repository manifest corruption and stale-but-valid snapshot;
15. encryption-key loss, wrong key, or revoked recovery authority;
16. primary and replica damaged by the same writer, account, controller, power, or deletion event.

Each family includes clean controls, sham injection, and a recovery check after fault removal.

## Audit policy to freeze before empirical runs

- Always repeat timeouts and failures on a fresh process when safe.
- Always audit storage-critical healthy signals through a different dependency class.
- Sample other healthy results at a preregistered rate based on measured false-health bounds and consequence tier.
- Never lower sampling because the current batch looks clean.
- Never use emotional language as a consequence label; use explicit operational harm, reversibility, and recovery cost.
- Never run a restore drill over the only remaining source or production target.
- Treat checksum verification as detection and identity evidence, not recovery or completeness.
- Reconcile restored canonical IDs with the independently retained accepted-write receipt manifest.

## Candidate gates for independent review

The safety invariants already fixed elsewhere remain binding: zero false `PHYSICAL_LOSS_CONFIRMED` decisions when recoverable bytes exist and zero false `NO_LOSS` decisions in confirmed-loss injections. The existing F1 localization threshold is at least 0.95 exact and at least 0.90 per class.

Before a confirmatory freeze, reviewers must set minimum decision coverage, real latency/I/O budgets, injection denominators, and acceptable confidence bounds without seeing the confirmatory results. Abstention is counted explicitly and may not be silently scored as correct.

## Versioning

`data/lab/probe-failure-domain-map-v0.csv` is immutable after the first empirical run. Any dependency discovery or implementation change creates v1 and records which results are no longer comparable. Deployment-specific maps replace this generic design; they do not inherit independence claims automatically.

Evidence basis: `../12-interdisciplinary-memory/storage-durability-crash-consistency-and-recovery-audit-v0.md`.
