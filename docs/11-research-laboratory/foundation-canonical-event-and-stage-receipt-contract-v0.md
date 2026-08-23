# Foundation v0 canonical event and stage receipt contract

Status: construction contract candidate; model-free; no product implementation claim

Contract ID: `PMLAB-FOUNDATION-CONTRACT-001`

Parent experiment: `PMLAB-FOUNDATION-001`

## Purpose

This contract turns the Foundation v0 diagram into auditable records before any
compactor, retriever, reader, or API model is evaluated. It defines two different
objects:

1. an immutable canonical event describing authorized evidence on the user's disk;
2. an append-only stage receipt describing what was actually observed at one
   diagnostic boundary.

The two objects are deliberately separate. A receipt is evidence about processing;
it is not the evidence payload and cannot silently revise the canonical event.

## Canonical event boundary

Every accepted event has:

- a stable event and idempotency key;
- an event type and exact content hash, byte length, media type, and storage reference;
- a source locator and, when available, a source-object hash and exact span;
- occurrence, observation, valid, and transaction time as distinct fields;
- actor, workspace/session/task scope, authorization, sensitivity, access, and retention metadata;
- producer identity and causal parents;
- an explicit original/corrects/supersedes relation.

The canonical record contains a reference to exact bytes, not an unreviewed semantic
summary. A correction or supersession is a new event. The earlier line is never
rewritten. Derived current-state projections may mark the earlier event stale only
by following the revision relation.

An event with `capture_allowed=false` is not a valid canonical event. Denied capture
belongs in a governance receipt that contains no prohibited payload.

## Required temporal semantics

- `occurred_at`: when the represented event happened; it may be unknown.
- `observed_at`: when the producer observed it.
- `valid_from` / `valid_to`: half-open domain-validity interval; either bound may be unknown.
- `transaction_at`: when this immutable record entered the archive.
- `precision`: declared granularity of the occurrence/valid-time claim.
- `timezone`: an IANA zone or `UTC`; it is not inferred from a bare clock value.

The validator rejects a reversed validity interval and a transaction time earlier
than observation time. It does not infer causality from wall-clock order.

## Diagnostic stages

| Stage | Boundary | Mandatory checks |
|---|---|---|
| `F0_CAPTURE` | source observation to accepted append | `source_seen`, `capture_authorized`, `canonical_append_acknowledged` |
| `F1_DURABLE_RECORD` | accepted append to recoverable valid record | `direct_id_read`, `full_scan_read`, `raw_bytes_recoverable`, `content_hash_match`, `schema_valid`, `provenance_valid` |
| `F2_INDEX_ADDRESS` | valid record to retrieval candidates | `index_membership`, `oracle_query_retrieval` |
| `F3_SELECT_PACK` | candidates to delivered context | `retrieved_set_contains_required`, `delivered_context_contains_required`, `validity_filter_passed`, `authorization_filter_passed`, `omission_report_present` |
| `F4_READER_USE` | delivered evidence to supported answer | `exact_evidence_exposed`, `answer_supported`, `citations_resolve` |
| `F5_ACTION_EVAL` | supported answer to authorized effect and score | `action_authorized`, `action_idempotent`, `external_effect_observed`, `evaluator_correct` |

A stage receipt records `pass`, `fail`, `unknown`, or `skipped` independently for
every required check. A stage cannot pass with a failed, unknown, or skipped
mandatory check. Missing telemetry is `unknown`, never an inferred pass.

## Physical-loss rule

End-to-end failure is not data loss. Only `F1_DURABLE_RECORD` may set
`data_loss_state=confirmed`, and only when all of the following controlled probes
fail:

- direct-ID read;
- full-scan read;
- raw-byte recovery;
- content-hash match.

If any raw recovery route succeeds, physical loss is ruled out even when schema or
provenance validation fails. Other stages use `not_applicable`; insufficient F1
evidence uses `unknown`.

This is a conservative laboratory diagnosis, not a storage-device warranty.

## Trace and receipt rules

- receipts use a shared `trace_id` and strictly increasing `sequence`;
- each receipt after the first names `previous_receipt_id`;
- every input/output reference has a typed ID and optional SHA-256;
- component name and version are mandatory;
- failures use registered machine-readable codes plus optional bounded notes;
- an authorization state is recorded at every exposure/action-capable stage;
- receipts are append-only observations and never overwrite earlier receipts.

## Frozen construction fixture

The construction fixture contains:

- one original synthetic file observation;
- one later correction event that points to the original;
- a complete six-stage passing trace;
- registered invalid mutations covering authorization, time, revision, content hash,
  missing stage evidence, false physical-loss claims, impossible pass states, and
  broken receipt chains.

It contains no user data, future query, answer key, model output, or external API
call. Passing the construction audit proves only that the contract and validator
agree on this frozen authored fixture.

## Non-claims and promotion gate

This contract does not prove durability, recovery, retrieval quality, reader
quality, or human-like memory. It is not permission to execute
`PMLAB-FOUNDATION-001`.

Before promotion beyond construction, an independent reviewer must attack the
field semantics, privacy boundary, revision rules, time semantics, and physical-loss
rule using a frozen blind packet. A second fixture author must then create unseen
valid and invalid traces. No threshold may be changed after those traces are opened.

## Artifacts

- `data/lab/pmlab-foundation-v0/contracts/canonical-event-v0.1.schema.json`
- `data/lab/pmlab-foundation-v0/contracts/stage-receipt-v0.1.schema.json`
- `data/lab/pmlab-foundation-v0/construction-v0/canonical-events.jsonl`
- `data/lab/pmlab-foundation-v0/construction-v0/stage-receipts.jsonl`
- `data/lab/pmlab-foundation-v0/construction-v0/invalid-mutations.json`

## Evidence basis

- `docs/04-systems/foundation-v0-architecture-decision.md`
- `docs/12-interdisciplinary-memory/interference-active-forgetting-synthesis.md`
- `docs/12-interdisciplinary-memory/temporal-provenance-versioning-and-correction-audit-v0.md`
- `docs/11-research-laboratory/interference-forgetting-benchmark-extension.md`
- `data/lab/pmlab-future-utility-v0/telemetry-event-v0.1.schema.json`
- `scripts/run_fault_probe_comparison.py`
- `scripts/run_fault_probe_robustness.py`

