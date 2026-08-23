# Exact citation and pack-order characterization v1

Experiment ID: `PMLAB-PACK-002`  
Status: frozen repair protocol; runner not implemented  
Authority: synthetic implementation characterization only

## Registered repair

This protocol inherits the question, fixture, pre-pack policy, order arms, budgets, metrics, interpretation limits, and reader-stage gate from frozen `PMLAB-PACK-001`. V0 produced no runner and no outcomes. V1 changes only the compact citation representation that failed the pre-run construct audit.

## Frozen fixture

Use byte-identical files from `data/lab/pmlab-pack-characterization-v0/`:

- `corpus.jsonl` SHA-256 `2270bffe8d76a760f216ad4ac85328b6de8970bdc1c12cf90188d21f2315a8c8`;
- `cases.jsonl` SHA-256 `da1f1a94d09cadcf0996ae102a6aa7e86ba1a72f95c2cb77ea28e66234dfc967`;
- the four source hashes in its manifest.

No case, candidate order, required label, evidence text, locator, budget, or order rule changes.

## Citation-format arms

| Arm | Definition |
|---|---|
| `T0_TEXT_ONLY` | bucket marker plus byte-identical evidence; capacity ceiling with no citation claim |
| `C0_FULL_INLINE` | `[path:line-line] <bucket> evidence` for every included record |
| `C1_SOURCE_FOOTER` | `[Snn:Lstart-Lend] <bucket> evidence`, with one complete footer entry `[Snn]=path` per included source path |

Source handles are assigned in first-included-source order. Multiple records from the same source reuse the same handle. A record is included only if its evidence line and the complete dictionary of the final pack fit. The dictionary must be in the same pack; an external sidecar is not allowed in the primary comparison.

## Order arms

- `O0_RETRIEVAL`: preserve supplied candidate rank after trust filtering.
- `O1_GOVERNED`: stable current, supporting, stale/conflicting order.
- `O2_REQUIRED_ORACLE`: privileged capacity ceiling with required current/supporting first, then other current/supporting, then stale.

## Budgets and fixed algorithm

Run `24 cases × 3 citation arms × 3 order arms × 4 budgets = 864` packs at 512, 768, 1024, and 1536 UTF-8 bytes.

Use greedy first-fit-with-continue. Never truncate evidence, locator text, or dictionary entries. Filter supplied `trust=untrusted` records before ordering, log them, and keep stale/conflicting records explicitly marked.

## Hypotheses

- `H-PACK2-01`: at 768 bytes, `C1_SOURCE_FOOTER - C0_FULL_INLINE` macro required retention is at least `+0.05`, with zero citation, evidence, trust, stale-marker, omission-ledger, or budget defects.
- `H-PACK2-02`: the compact-minus-full retention delta is positive in both the long-locator and required-source-reuse strata. Treat magnitude as descriptive on this authored sample.
- `H-PACK2-03`: at least one budget has an absolute `O1_GOVERNED - O0_RETRIEVAL` required-retention difference of `>=0.05` for a cited format. This supports order as a capacity mechanism only.

## Integrity gates

Every cited record must resolve from its serialized citation to the exact source path, line range, and byte-identical evidence. There must be zero orphan, ambiguous, missing, or duplicate-conflict handles; zero untrusted exposure; zero stale-marker loss; zero unreported omission; and zero budget violation. Any failure invalidates the implementation regardless of retention.

`T0_TEXT_ONLY` is a capacity ceiling and cannot satisfy provenance. `O2_REQUIRED_ORACLE` is non-deployable. No result can select a reader order, classifier, compression model, retriever, or architecture.

## Reader-stage gate

A reader experiment requires all integrity gates plus a `>=0.05` retention difference at 768 bytes or the same directional difference across at least two adjacent budgets. It must use fresh answer-bearing cases, blinded condition labels, equal evidence IDs and bytes where possible, explicit stale-use and citation metrics, provider-neutral structured outputs, and a separately frozen API cap.
