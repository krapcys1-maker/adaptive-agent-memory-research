# Disposable same-device storage fault injection v0

Status: completed state-machine and real-file probe execution test; not a reliability estimate and not P10

## Environment and safety

Windows reported both C: and D: as partitions of `Disk 0`. The harness therefore labels its two directories logical replicas on one physical failure domain. Every mutation occurred below a newly created system temporary directory whose resolved parent and `pmlab-storage-` prefix were checked before use. Temporary cleanup removed only that generated directory.

The run used real file creation, flush plus `fsync`, byte reads, SHA-256 verification, JSON/schema parsing, file unlink/truncation, and index-set mutation. Forced reader/parser timeout/failure cases did not wait in real time.

## Cases

Twelve injections were exercised 25 times each, for 300 trials:

- clean;
- capture omission;
- primary or replica missing;
- both logical replicas missing;
- primary or both replicas truncated;
- accepted bytes with unsupported schema;
- index omission;
- primary structured-reader fault;
- both raw readers timing out;
- structured-parser fault.

## Result

The authored state machine matched the authored expected outcome in 300/300 trials. Outcomes included `CAPTURE_FAILURE`, `ACCESS_FAILURE`, `DEGRADED_REDUNDANCY`, `LOGICAL_REPLICA_LOSS`, `RECOVERABLE_CORRUPTION`, `INCONCLUSIVE`, and `NO_FAULT_OBSERVED`.

`PHYSICAL_LOSS_CONFIRMED` was emitted 0 times, including when both logical replicas were deleted or truncated. This is the required behavior because the paths share Disk 0 and do not satisfy the independent-replica contract.

Non-timeout read timings were recorded as environment diagnostics only. Primary raw p50/p95 was approximately 609/4,769 microseconds, replica raw 519/802 microseconds, and primary structured 66/664 microseconds in the final run. Probe order, filesystem cache, antivirus, and tiny-file overhead are uncontrolled, so these values cannot compare probe performance.

## Interpretation

The result validates executable outcome semantics and the safety guard against falsely upgrading same-device loss to physical-loss confirmation. The 1.0 classification score is largely construction validity: the same author defined injections, classifier, and expected outcomes, and repeated trials are not independent samples.

P10 remains absent. A real physical-loss experiment requires a separately inventoried storage device or remote/offline replica, independently implemented checksum verification, failure injection that disables the primary domain, and external review of the expected classifications.
