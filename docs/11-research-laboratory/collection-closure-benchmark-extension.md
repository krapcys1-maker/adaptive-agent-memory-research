# Collection closure and negative-knowledge benchmark extension

Status: v0 and repaired v1 construction corpora frozen; exploratory construction run complete; held-out and architecture claims blocked

## Purpose

`PMLAB-CLOSURE-001` tests whether a memory controller can distinguish a retrieval miss from collection-bounded absence and from proposition-level falsity. It follows `PMLAB-SUFF-001`, whose retrieved-obligation arm could safely detect missing evidence but could not decide whether to continue searching or issue a stable negative/partial result without diagnostic gold collection state.

The benchmark is specified before any case builder or runner is implemented. Its theory and contract are in `docs/12-interdisciplinary-memory/collection-closure-and-negative-knowledge-synthesis.md`.

## Primary hypothesis

An exact query-specific completeness certificate plus a counterexample-insertion check will reduce unsafe negative decisions relative to retrieval saturation and coarse namespace completeness, without forcing global open-world abstention on scopes that are demonstrably complete.

## Factor separation

The frozen corpus must independently vary:

- retrieval success;
- canonical-store enumeration success;
- replica/media availability;
- query-to-scope mapping correctness;
- certificate granularity and freshness;
- authorization boundaries;
- explicit negative evidence;
- whether an admissible insertion changes the answer;
- validity, supersession, and conflict state.

The runner must not receive hidden inventory or gold scope labels. Oracle arms must be visibly separate from deployable arms.

## Minimum artifacts before freeze

- `cases.jsonl` with opaque IDs and model-invisible gold fields;
- `inventories.jsonl` with versioned namespace, replica, and media membership;
- `probes.jsonl` with observable success/failure and failure-domain labels;
- `certificates.jsonl` with scopes, basis, version, expiry, and exceptions;
- `insertions.jsonl` with allowed counterexample updates;
- immutable manifest, file hashes, generation seed, and freeze commit;
- label audit that checks all N0-N3 decisions against the formal contract;
- bilingual and paraphrase variants split by semantic template, not random rows.

## Development and held-out order

1. Freeze the schema and 32-48 construction cases.
2. Commit corpus and manifest before implementing the runner.
3. Run deterministic arms only to validate the state-machine semantics.
4. Freeze scope mapper v0 and certificate evaluator v0.
5. Create an unseen challenge using new entities, time expressions, namespaces, certificate bases, and fault combinations.
6. Obtain independent label and threat-model review.
7. Only then run a confirmatory comparison.

## Promotion boundary

A construction pass can admit the state machine and artifact contract. It cannot establish that real disks, replicas, access controls, natural-language scope mapping, or completeness metadata are reliable. Architecture promotion remains blocked until the held-out and independent-review gates pass.

## Frozen construction outcome

- v0 freeze: `b99b20a`, corpus SHA-256 `3599635e6e66cd1f98a2d7bcae98f97369aa5e4c412590f697a126f124253e58`;
- v0 defect: insertion-counterexample certificates declared `partial`, so insertion checking was not isolated;
- v1 repair/freeze before runner: `e9649ac`, corpus SHA-256 `3450ebbed450904216c75366c9aac374bdafb5e9add3a13d44e59e74d69ee43c`;
- candidate certificate-plus-insertion arm: exact tier/action 0.958, critical tier 0.941, zero unsupported N2/N3, positive safe coverage 1.0;
- failed gates: critical tier below 0.95 because multi-facet decomposition is absent; matched-coverage comparison unavailable because coverage gap versus retrieval saturation is 0.583.

The next protocol version must freeze the decomposer and per-obligation scope mapper separately. V1 labels and cases remain unchanged.
