# Shared-memory provenance and conflict benchmark protocol v0

Status: preregistration draft; no corpus, runner, result, or execution authority

Experiment ID: `PMLAB-SHARED-001`

## Purpose

Measure whether sharing long-term memory across agents or offline replicas saves useful work without turning convergence, majority adoption, or repeated copying into evidence. This protocol isolates transport convergence, semantic validity, provenance, authorization, confidentiality, and correction.

## Unit of analysis

One case is a frozen ordered set of operations over two or more principals and replicas. It includes:

- immutable source/event IDs and bytes;
- replica identity and initial knowledge;
- operation ID, author, causal parents, creation time, receipt time, scope, and payload hash;
- policy and capability state visible at each operation;
- declared application invariants;
- partitions, retries, duplication, reordering, crashes, exports, and revocations;
- oracle converged state, allowed exposures, unresolved conflicts, and required action.

LLM answers are a later reader layer. The first execution must be deterministic and model-free.

## Arms

| Arm | Description |
| --- | --- |
| S0 | isolated private stores; no sharing |
| S1 | naive last-arrival or last-writer shared file |
| S2 | append-only operation log with deterministic replay |
| S3A | Automerge-backed replicated view over the same accepted operations |
| S3Y | Yjs-backed replicated view over the same accepted operations |
| S4 | S2/S3 plus explicit provenance, valid-time, and invariant checks |
| S5L | S4 plus simple local namespace/capability authorization |
| S5U | S4 plus UCAN-like signed attenuated capability validation |
| O | oracle delivery, invariant, authorization, and conflict control |

Every non-oracle arm receives identical operation semantics and budgets. An adapter-specific representation may not change the gold operation set.

## Required strata

1. concurrent compatible additions;
2. concurrent correction and stale edit;
3. delete/update and supersede/update conflicts;
4. duplicate, reordered, delayed, and lost delivery;
5. partition followed by merge;
6. crash during append, compaction, or index rebuild;
7. semantically conflicting procedures whose bytes merge cleanly;
8. accepted-claim promotion without supporting evidence;
9. poisoned claim copied by several authorized agents;
10. unauthorized writer, reader, promoter, and exporter;
11. capability attenuation, expiry, delegation, and concurrent revocation;
12. revocation learned before and after an offline action;
13. restricted data already exported, backed up, or exposed to a model;
14. correction that must propagate while preserving history;
15. deletion request with complete, incomplete, and unknown replica inventory;
16. agent turnover with independent and contaminated reviewers;
17. bilingual equivalent updates and cross-language retrieval views;
18. high- and low-cost independent verification.

## Endpoints

### Replication

- operation delivery recall and duplicate application rate;
- byte/state convergence after quiescence;
- lost-update rate;
- convergence latency, bytes transferred, disk growth, and compaction cost.

### Semantics

- invariant violation recall and false-positive rate;
- exact supported current state;
- unresolved-conflict preservation;
- stale or poisoned adoption and propagation depth;
- time to detection and correction.

### Provenance and authorization

- exact resolvable derivation-chain completeness;
- unauthorized write acceptance;
- unauthorized retrieval or export exposure;
- promotion without required reviewer/source authority;
- revocation enforcement by causal scenario.

### User outcome

- useful duplicated work avoided at matched exact supported action;
- critical false-action rate;
- correction recovery time;
- bounded abstention when inventory or authority is unknown.

`state convergence` is never reported as `truth convergence` or `task success`.

## Critical gates

Reject an arm if any of the following occurs in the registered critical strata:

- an unauthorized principal receives restricted plaintext;
- an unsupported claim becomes accepted solely through merge, recency, or majority;
- a semantic conflict is silently replaced by one winner;
- a deletion or revocation receipt claims bytes are gone when an inventoried copy remains;
- provenance needed to resolve a derived claim is lost during merge or compaction;
- correction deletes the earlier evidentiary state instead of versioning it;
- the arm cannot recover its derived view from canonical evidence;
- a supposedly independent reviewer receives prior verdicts or hidden shared context.

## Freeze order

1. threat model, invariants, and operation schema;
2. independent protocol review;
3. case allocation and power/precision rule;
4. blind oracle labels and replica inventory;
5. adapter versions and deterministic serialization rules;
6. runner, fault injector, and scorer hashes;
7. development execution;
8. one untouched prospective test;
9. only then a reader-model extension across at least two model families.

## Execution locks

- no architecture promotion from authored development cases;
- no networked production data;
- no secrets, personal data, or real private conversations;
- no external model API in the deterministic replication phase;
- no CRDT or capability implementation becomes canonical storage before independent review and prospective safety gates;
- every failed and null run is retained.

## Evidence basis

See [distributed shared-memory audit v0](../12-interdisciplinary-memory/distributed-shared-memory-crdt-provenance-audit-v0.md) and [collective-memory audit v0](../10-comparative-biological-memory/collective-externalized-and-social-memory-audit-v0.md).
