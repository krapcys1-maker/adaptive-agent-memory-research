# Minimal Reuse Architecture v0

Status: research blueprint; implementation remains gated by benchmark evidence

This document instantiates reusable component candidates inside the technology-neutral boundary in `docs/11-research-laboratory/minimal-architecture.md`; it does not replace that boundary or authorize implementation.

## Design target

Give any compatible LLM a local, inspectable long-term memory without changing its context window. The context window remains working memory. Disk stores canonical observations and derived records. A small adapter retrieves an evidence-bounded context pack for the current model call.

Compaction is complementary and sits outside the canonical store. Native host compaction and a frozen open compactor may reduce active conversation state, but their outputs are versioned derived artifacts. They cannot overwrite the local raw archive. The formal boundary and comparison tracks are frozen in `foundation-v0-architecture-decision.md`.

```text
LLM host (OpenAI / Claude / local / future provider)
          recent state + optional compaction
                    |
          MCP or direct local adapter
                    |
             Memory service API
    remember | recall | context | feedback | forget
          /            |             \
canonical event log  derived index   audit ledgers
raw messages/files   SQLite + FTS5   evidence/retrieval/action
          \            |             /
            deterministic context pack
       current | supporting | stale/conflicting
```

## Smallest useful kernel

### 1. Canonical layer

- append-only raw observation/message records;
- stable source URI and content hash;
- observation time, validity time, ingestion/transaction time, and optional expiry kept distinct;
- derived facts point to evidence spans; summaries never replace their sources;
- supersession and quarantine are reversible; physical deletion is a separate governed operation.

Reference donors: GoodMemory evidence/temporal contracts and memo's authoritative-text principle.

### 2. Derived retrieval layer

- SQLite metadata plus FTS5 is the mandatory baseline;
- indexes are disposable and rebuildable from canonical records;
- optional local embedding adapter writes model ID, revision, dimension, normalization, and creation time beside every vector generation;
- dense results cannot bypass scope, lifecycle, time, or access filters;
- deterministic RRF is the first hybrid comparator; learned fusion comes later.

Reference donors: mnemos RRF and citations, existing `sqlite-vec`, optional FastEmbed.

### 3. Evidence-bounded context builder

- returns current, supporting, and stale/conflicting sections;
- reports omitted items and why they were omitted;
- preserves citations and uncertainty;
- budgets with the real target tokenizer when available, with a declared fallback estimator;
- never reinforces a memory merely because it was retrieved.

Reference donors: memo context packs, GoodMemory retrieval traces, mcp-local-memory exposure/feedback separation.

### 4. Provider-neutral boundary

- domain and storage ports contain no OpenAI, Anthropic, or model-specific types;
- local `stdio` MCP is the first interoperability adapter;
- direct Python/TypeScript calls are optional adapters over the same operations;
- API workers perform bounded classification or extraction jobs and return typed proposals; they never own canonical storage or silently mutate memory.

Reference donor: official MCP SDK after a pinned-major compatibility test.

Protocol support does not guarantee automatic capture from every subscription client. Each host needs a separately audited connector or hook. Until one exists, explicit `remember`, local file import, and export are the safe common denominator; no client-specific hook may become part of the canonical domain model.

### 5. Background and prospective work

- durable job records contain trigger, scope, earliest/latest execution, idempotency key, status, and evidence;
- a scheduler calculates due time only;
- a separate policy authorizes reads, writes, notifications, or external actions;
- time, event, and state triggers have separate tests;
- every job is replayable and duplicate-safe.

Reference donor: APScheduler 3.x for time scheduling only.

### 6. Safety boundary

- path confinement before filesystem reads or writes;
- secret scan before ingestion and before commit/export;
- optional PII classification/redaction with explicit false-negative warnings;
- optional database encryption with independently managed keys and tested recovery;
- retrieved text is untrusted data, not executable instruction;
- all maintenance actions have dry-run, trace, and rollback paths.

Reference donors: mnemos path confinement, Gitleaks core/CLI, Presidio, SQLCipher.

## Interfaces worth freezing early

| Interface | Minimum contract |
|---|---|
| `ObservationStore` | append, get-by-id/hash, stream by scope/time; immutable payload |
| `MemoryRepository` | propose, activate, supersede, quarantine, archive; version checked |
| `EvidenceRepository` | link record to exact source span and preserve derivation metadata |
| `SearchChannel` | query plus filters returns candidate IDs, raw scores, ranks, and trace |
| `FusionPolicy` | channel ranks to deterministic ordered candidates |
| `ContextBuilder` | candidates plus token budget to cited categorized pack and omissions |
| `FeedbackLedger` | explicit outcome, exposure map, delay window, actor, and reason |
| `JobStore` | idempotent prospective/background jobs and action log |
| `MemoryAdapter` | provider/host-neutral remember, recall, context, feedback, and forget |

Freeze meanings, not implementations. SQLite, embeddings, model providers, and MCP versions must remain replaceable.

## Build and benchmark order

1. Current local JSONL/FTS5 memory versus a stricter canonical/evidence schema.
2. Freeze an open compaction baseline while preserving raw evidence outside it.
3. FTS5 retrieval with citations and real token budgeting, both with and without compaction.
4. Optional exact dense retrieval under the same candidates and filters.
5. Deterministic RRF hybrid retrieval.
6. Context buckets and omission reporting.
7. Explicit outcome feedback ledger without automatic reinforcement.
8. Prospective time jobs and restart/idempotency tests.
9. Only then test graph expansion, learned controllers, emotional salience, consolidation, decay, or destructive forgetting.

## Success gate

A component earns inclusion only if it improves at least one preregistered memory outcome without unacceptable regression in evidence correctness, stale-memory harm, privacy, latency, cost, portability, or recoverability. “More memories retrieved” and “larger context produced” are not success metrics.

## Remaining reuse searches triggered by implementation choices

- host-specific capture/export adapters after the first target clients are frozen;
- cross-platform atomic locking after the implementation language is chosen;
- backup/restore and operating-system key custody after the storage/encryption profile is frozen;
- schema migration tooling after the first versioned canonical schema exists;
- observability export after the retrieval/action trace contract is stable.

These are deliberately deferred: selecting them now would couple the research kernel to a language, host, or deployment mode before its benchmark boundary is validated.
