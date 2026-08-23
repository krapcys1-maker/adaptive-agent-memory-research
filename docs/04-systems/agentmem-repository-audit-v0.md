# AgentMem repository audit v0

Status: static audit complete; local test execution unavailable; no architecture adoption

Audited repository: [AgentMem/agentmem](https://github.com/AgentMem/agentmem)

Revision: `c96ff3ce7a5286d33a7c280d53cafa1bfcb13693`

License: Apache-2.0 with `NOTICE`

Audit date: 2026-08-23

## Disposition

AgentMem is a serious donor for **verified action receipts, cited intervention snapshots, host adapters, and null-result methodology**. It is not a suitable canonical store for this project and is not evidence that proactive memory universally improves agent performance.

Keep it locally pinned and characterize selected modules. Do not import the full runtime or copy its memory-bank lifecycle into Foundation v0.

## Repository identity and independence

- The complete public history contains 105 commits from 2026-07-13 through 2026-07-19; the initial local observation of one commit was a shallow-clone artifact and is explicitly corrected here.
- The repository credits a clean-room reimplementation of the two-phase architecture in *Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents* and states that the authors' reference code was not copied.
- Clean-room implementation independence is not the same as independent evaluation. AgentMem authors wrote the implementation, harnesses, fixtures, and reports. Its results are self-reported until another party reproduces them from frozen artifacts.
- Public GitHub metadata at audit time showed 2 stars, 0 forks, and 0 open issues. Adoption is too early to infer maintenance or external validation from community activity.

## What the code implements

### Two-phase proactive controller

`agent/memory_agent.py` performs a Phase-1 maintenance call followed by a Phase-2 speak-or-stay-silent call at every triggered memory step. Triggering reduces the number of steps, but a triggered step still pays both model calls. A learned advantage layer may gate an intervention back to silence; it never creates an intervention by itself.

This is useful as an intervention comparator. It is not a cheap retrieval baseline.

### Mutable memory bank

`schemas.py` stores status, knowledge entries, procedural entries, causal edges, an archive, lifecycle state, salience, and counters in a `MemoryBank` snapshot. `bank.py` permits the model to update an entry in place and exposes `memory_delete`; deletion removes an active or archived entry and all incident edges. Capacity pressure demotes entries when continual memory is enabled, but the explicit delete tool remains destructive. The store tests explicitly expect later saves to overwrite the earlier serialized bank.

This violates the project's canonical-evidence contract. A derived AgentMem-style bank could be rebuilt beside the archive, but it cannot own the only copy of an observation.

### Storage

- JSON storage writes a complete bank to a temporary file and uses `os.replace`.
- SQLite stores one JSON bank blob per session and overwrites it through an upsert under WAL mode.
- The event schema has a free-form `source` string but no content hash, exact span, valid/transaction-time split, derivation chain, authorization record, or raw append-only event log.
- JSON atomic replacement improves visibility of one snapshot but does not establish `fsync`, accepted-record completeness, power-loss recovery, or backup restore.

These stores are acceptable for the project's comparator state, not for canonical long-term evidence.

### Intervention auditability

The injector rejects unresolved citation IDs, records use/cooldown state, and includes `cited_snapshot`: the exact text of each cited entry at delivery time. This repairs a real failure found by the authors: after consolidation and eviction, only 11 of 31 old intervention IDs still resolved. The post-fix snapshot makes the delivered evidence auditable even if the bank later changes.

This is directly reusable as a contract: every delivered memory bundle should preserve a content-addressed exposure receipt or immutable cited snapshot. The implementation should be adapted to canonical source spans, not only bank prose.

### Verified action receipts

`verify/receipt.py` captures before/after file snapshots, hashes effects, records checks, forms an append-only hash chain, and can restore captured bytes. Recorders extend the same shape to Git and listable APIs. Ed25519 attestation and optional notary code are present.

The useful boundary is the receipt schema and deterministic before/after verification. It does not prove the truth of claims beyond the captured surfaces, prevent a compromised local writer from replacing the whole ledger, or provide independent timestamp truth without separately trusted custody.

## Evaluation evidence

### Results worth preserving

- **tau2 airline:** 37/50 without memory versus 38/50 with memory; five tasks changed fail-to-pass and four pass-to-fail. The report correctly describes this as a null-sized net result, not a replication of the paper's larger gain.
- **Terminal-Bench:** 23 paired, budget-capped trials reported no genuine pass-rate flip. The memory layer consumed money or action turns while accurate advice often failed to repay its cost on short tasks.
- **Claude Code compaction:** two one-seed Haiku scenarios compared Claude's compact summary with and without AgentMem. One case was worse with memory (25 versus 37 calls to green); the other tied 4 versus 4. Both probes were already grounded without memory. The report calls this a null on acceleration.
- **cross-session account probes:** on three external Python libraries, the memory arm cited real artifacts while an open 27B model without memory invented unrelated web-backend work. A stronger Sonnet model abstained rather than confabulating, so the observed failure mode is model-dependent.
- **repeat-fix trials:** four reminder-active Qwen seeds favored memory, but a no-intervention control differed by ten turns and exposed a noise floor larger than most observed gaps. Three Sonnet seeds were flat at 14 total turns per arm.
- **citation audit:** 31/31 intervention IDs were valid when injected, but only 11/31 still resolved later before cited snapshots were added.

### What these results do not establish

- Most live experiments have very small sample sizes, authored scenarios, or one model family.
- Several arms change both memory and token/turn allocation, so pass rate, cost, and opportunity to explore must be read together.
- Grounded file names are weaker than a fully accurate account; the authors found a grounded memory answer that was still contradicted by `git status`.
- The reported cross-session advantage is not a comparison with Foundation v0 FTS5, exact raw retrieval, a frozen open compactor, Mem0, Hindsight, or an oracle at matched budgets.
- Self-authored reports and committed JSON are auditable artifacts but not independent reproduction.

## Reuse decision

| Segment | Decision | Required before use |
|---|---|---|
| `Intervention.cited_snapshot` and delivery telemetry | adapt contract with attribution | bind to immutable source hash/span; retention and privacy tests |
| file/Git action receipt model | characterize, then adapt selected schema ideas | path confinement, TOCTOU, large-file, symlink/junction, concurrent-writer, and recovery tests |
| report/grounding scorers | comparator and negative-test donor | distinguish existence, modification, semantic accuracy, and unverifiable claims |
| provider and host adapters | reference only | separate subscription/API support matrix and hook-failure tests |
| two-phase speak/silence loop | comparator only | matched call/token budget against deterministic trigger and retrieval-only arms |
| salience, reinforcement, promotion, and consolidation | experimental comparator | future-utility, false-transfer, correction, poison, and causal-credit benchmarks |
| JSON/SQLite bank store | reject as canonical store | may hold rebuildable comparator state only |
| explicit model-owned update/delete tools | reject for canonical evidence | proposal-only output plus governed deterministic application |
| notary and hosted hub | defer | threat model, key custody, authorization, erasure, independent time source, and restore contract |

## Test execution status

The repository contains 83 test files and 437 functions matching `test_*` across the scanned package/evaluation test paths. Its CI declares Python 3.11/3.13 lint, formatting, strict core type checking, tests, and build. Local execution was attempted with the repository's frozen `uv` workflow but `uv` is not installed in the current environment. No local pass claim is made.

Before adapting code, run the pinned revision in a disposable environment and preserve:

- dependency lock and interpreter identity;
- unit, lint, format, and type-check outputs;
- selected receipt and injection fault tests;
- license/NOTICE attribution;
- a clean-room comparison against our own contract, not only its public API.

## Bottom line

AgentMem strengthens the case for the hybrid foundation in two ways. Its positive cross-session probes show why compaction alone may be insufficient, while its short-task and compaction nulls show why an always-active memory controller should not be assumed to help. The best parts to borrow are measurement and audit boundaries, not the mutable memory bank.
