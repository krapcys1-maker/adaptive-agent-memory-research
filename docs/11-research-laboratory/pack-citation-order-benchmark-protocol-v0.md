# Exact citation and pack-order characterization v0

Experiment ID: `PMLAB-PACK-001`  
Status: frozen at `7913791`, then invalidated pre-run by a citation-treatment construct audit
Authority: synthetic implementation characterization only

## Question

With retrieval held fixed, how do citation encoding, source-path length, source reuse, context order, and byte budget affect exact citation resolution and retention of required evidence?

This experiment isolates serialization. It does not test retrieval, automatic bucket classification, evidence truth, answerability, prompt-injection detection, or reader behavior.

## Fresh fixture

- 36 authored records stored in four real local Markdown sources with short, medium, long, and reused locators;
- 24 fixed candidate lists, each containing seven ranked records;
- required evidence at early, middle, and late positions;
- one to three required records per case;
- current, supporting, stale/conflicting, and untrusted records;
- deterministic text-length variation;
- no record, case, or result from the spent `PMLAB-REUSE-CHAR-001` fixture.

The fixture is visible and author-labelled. It may validate mechanics and reveal tradeoffs, but it cannot support an architecture or human-memory claim.

## Fixed pre-pack policy

Untrusted records are filtered before ordering or serialization. This validates only enforcement of supplied trust metadata. Stale/conflicting records remain eligible and must retain an explicit `stale_conflicting` marker. Required evidence is never untrusted or stale in this fixture.

The packer uses greedy first-fit-with-continue: consider records in arm order, include a record only if the complete resulting pack fits, and otherwise log its omission before considering later records. It may not truncate evidence text or a locator.

## Citation-format arms

| Arm | Definition |
|---|---|
| `T0_TEXT_ONLY` | bucket marker plus byte-identical evidence; capacity ceiling with no citation claim |
| `C0_FULL_INLINE` | repeat `path:line-line` beside every included evidence record |
| `C1_COMPACT_FOOTER` | use deterministic `[Snn]` handles beside evidence and include one complete in-pack handle-to-locator dictionary |

For `C1`, a record is included only if both its evidence line and all dictionary entries required by the final pack fit. Handle assignment follows first included source locator order. No external sidecar is allowed for the primary comparison.

## Order arms

| Arm | Definition |
|---|---|
| `O0_RETRIEVAL` | preserve supplied candidate rank after trust filtering |
| `O1_GOVERNED` | stable `current -> supporting -> stale_conflicting` order |
| `O2_REQUIRED_ORACLE` | required current/supporting first, then other current/supporting, then stale; non-deployable capacity ceiling |

`O2` is explicitly privileged and cannot be promoted. The deterministic run may measure retention differences but cannot select an order for a reader.

## Budgets and factorial design

Run every citation-format × order × budget combination for every case at 512, 768, 1024, and 1536 UTF-8 bytes: `24 × 3 × 3 × 4 = 864` packs.

## Metrics

- macro required-evidence retention;
- all-required retention rate;
- critical-required retention;
- mean included records and UTF-8 utilization;
- exact locator resolution for every cited record;
- orphan, ambiguous, duplicate, or missing handle count;
- untrusted exposure;
- stale marker loss;
- explicit omitted IDs and reasons;
- paired per-case deltas between `C1` and `C0`;
- strata by budget, locator length, required position, required count, and required-source reuse.

## Frozen hypotheses and decisions

- `H-PACK-01` passes only if `C1-C0` macro required retention at 768 bytes is at least `+0.05`, all C1 handles resolve exactly, and no C1 pack exceeds budget.
- `H-PACK-02` is descriptive unless the direction of the C1-C0 delta is positive both for long-locator and source-reuse strata. No significance claim is allowed on 24 authored cases.
- `H-PACK-03` is supported as a capacity mechanism if at least one non-oracle order changes required retention by `>=0.05` at any budget. It cannot select reader order.
- If any cited arm has an invalid locator, orphan handle, evidence mutation, unreported omission, untrusted exposure, stale-marker loss, or budget violation, the implementation fails regardless of retention.
- `T0` is a capacity ceiling and cannot satisfy citation requirements.

No parameter, case, record, ordering rule, or budget may change after freeze. Post-hoc analyses must be labelled and may not retune this fixture.

## Reader-stage gate

A new reader experiment is justified only if:

1. all deterministic integrity gates pass;
2. at least one compact/full or non-oracle order comparison changes required retention by `>=0.05` at 768 bytes or across at least two adjacent budgets;
3. the reader protocol uses fresh answer-bearing cases, equal evidence IDs and bytes where possible, blinded condition labels, provider-neutral structured outputs, explicit stale-use and citation measures, and a separately frozen API cap.

The reader test must include full-inline and compact-handle arms. Learned compression remains excluded until those reversible baselines are measured.

## Pre-run invalidation

No pack was executed. After freeze and before runner implementation, an audit found that `C1_COMPACT_FOOTER` assigned a handle to each complete `path:line-line` locator. Because every record has a distinct line range, the dictionary would repeat the full path once per record and add footer overhead. The treatment therefore could not operationalize `H-PACK-02` source-path reuse and had no credible compression mechanism relative to inline locators.

The protocol and fixture are preserved unchanged. `PMLAB-PACK-002` repairs only this construct by mapping one handle to each source path while retaining the line range inline.
