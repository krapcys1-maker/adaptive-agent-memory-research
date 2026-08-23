# Foundation v0: lossless local archive plus compaction

Status: accepted as the research floor; not accepted as a final product architecture

Date: 2026-08-23

## Decision

The project will start from a hybrid, not from a choice between compaction and an external memory product.

1. The model or host context window remains working memory.
2. Native or open compaction may reduce the active conversation state.
3. A local append-only archive preserves the observations that compaction may omit.
4. Rebuildable retrieval creates a small, cited context pack for the current decision.
5. Summaries, semantic memories, procedures, salience scores, graphs, and learned policies are derived hypotheses. None may replace the only copy of raw evidence.

This is a minimum comparison substrate. It is deliberately weaker than the hoped-for adaptive memory and must remain easy to beat, inspect, repair, and remove.

## Why this is the floor

Compaction and long-term memory solve different constraints.

| Mechanism | Primary job | Fundamental limitation |
|---|---|---|
| Active context | make information directly available to the current model call | bounded and expensive |
| Compaction | preserve task-relevant continuation state in fewer active tokens | must decide now what later work will need |
| External archive | preserve recoverability across sessions and reinterpretation | preservation alone does not make an item findable or useful |
| Retrieval/context builder | choose evidence for the present query under a budget | can miss, intrude, or mis-rank preserved evidence |
| Consolidation | form reusable semantic or procedural abstractions | can introduce plausible errors and erase exceptions if treated as canonical |

The architecture therefore protects two different rights:

- **continuation:** compaction keeps the current task moving;
- **reconsideration:** the archive permits a future query to recover something that looked unimportant when it was first observed.

Neither mechanism is declared superior in general. The benchmark must price both.

## The frozen conceptual boundary

```text
provider or host session
        |
        +---- recent turns + native/open compaction ----+
        |                                               |
observed events                                        |
        |                                               |
append before lossy processing                         |
        v                                               v
canonical local archive --> rebuildable indexes --> cited context pack
        |                    FTS5 first            current/supporting/stale
        |                                               |
        +--------------- exact evidence ----------------+
                                                        |
                                                  next model call
```

### Canonical on the user's disk

- immutable event ID and payload hash;
- exact source locator or captured evidence span;
- occurrence/observation, valid, and transaction time kept distinct where applicable;
- actor, scope, authorization, sensitivity, and retention metadata;
- correction and supersession as new events;
- write receipt and recovery status;
- raw messages, tool results, file observations, decisions, and outcomes only when capture is authorized.

Git-tracked JSONL and reviewed Markdown are sufficient for the research floor. A future implementation may use another store only if it preserves the same observable contract and passes recovery tests.

### Rebuildable and disposable

- SQLite FTS5 index;
- current-state projections;
- citation aliases and compact source handles;
- optional embeddings and vector indexes;
- summaries, semantic facts, procedures, graphs, salience, utility estimates, and context packs.

Deleting these artifacts must never delete the canonical evidence from which they can be rebuilt.

### Provider-specific adapters

- OpenAI response compaction;
- Claude Code `/compact` or later host compaction;
- a frozen open summarizer/compactor;
- model tokenizers, SDKs, lifecycle hooks, and subscription-client integrations.

Provider adapters may improve continuation but may not define the canonical schema. An OpenAI or Anthropic product change must not require a memory migration.

## What is mandatory in v0

| Component | Initial choice | Reason |
|---|---|---|
| Canonical archive | append-only JSONL/Markdown on local disk | inspectable, portable, versionable |
| Exact retrieval | `rg` diagnostic plus SQLite FTS5 baseline | dependency-light lower bound |
| Evidence | exact source locators and cited snapshots at delivery | later audit must survive index or memory mutation |
| Context allocation | explicit byte/token budget and omission report | prevents silent context growth |
| Temporal output | `current`, `supporting`, `stale/conflicting` | correction history must not look current |
| Compaction control | one frozen open compactor; native products only as black-box arms | reproducibility plus realistic comparison |
| Integration | provider-neutral CLI/MCP boundary | OpenAI, Claude, local, and future hosts remain replaceable |
| Model worker | optional proposal-only batch worker | no API model owns or silently mutates canonical memory |
| Diagnostics | receipts for capture, retrieval, packing, delivery, and action | separates data loss from access and reader failure |

## What is explicitly not in the foundation

- embeddings as a mandatory dependency;
- a vector database, graph database, or bitemporal database;
- Mem0, Hindsight, AgentMem, or another complete memory runtime;
- model-owned deletion, overwrite, consolidation, or promotion;
- emotional salience as a truth or storage signal;
- learned retrieval fusion or intervention policy;
- autonomous external actions;
- cloud sync, CRDT replication, encryption product, or backup backend before their own contracts are frozen.

These remain plug-in comparators. A rejected mechanism remains documented and may return if a new benchmark exposes a gap.

## Relationship to GitHub systems

No single repository becomes the source of truth. Reuse is segmented.

- GoodMemory remains a donor for evidence, time, and storage-port contracts.
- mnemos remains a donor for cited retrieval, path confinement, and deterministic RRF.
- memo remains a donor for authoritative text, context packs, and atomic-write tests.
- AgentMem is a donor for intervention receipts, cited snapshots, action-grounding checks, and honest null-test design. Its model-maintained mutable bank is not the canonical archive.
- Proactive Memory Agent is a comparator for speak/silence decisions, not a storage foundation.
- Mem0 and Hindsight remain end-to-end benchmark arms after versions, readers, extraction models, budgets, and licenses are frozen.

Ideas may be adapted only under their licenses, with revision pinning, attribution, isolated contract tests, and an explicit statement of what was not copied.

## Two benchmark tracks

### Track R: reproducible and provider-neutral

All arms use the same history, event units, reader model, active-context budget, query, seed policy, and cost accounting.

| Arm | Description |
|---|---|
| R0 | recent window only; no compaction and no external memory |
| R1 | frozen open compactor only |
| R2 | R1 plus raw filesystem/`rg` retrieval |
| R3 | R1 plus SQLite FTS5 with exact citations |
| R4 | R1 plus optional dense retrieval |
| R5 | R1 plus deterministic RRF |
| R6 | R1 plus a pinned external memory system |
| R7 | R1 plus the project's adaptive candidate |
| O | oracle evidence selection at the same active-context budget |

### Track P: production black boxes

Run separately for each provider; never pool OpenAI and Claude scores.

- native compaction alone;
- the same native compaction plus Foundation v0 retrieval;
- the same native compaction plus a pinned external system;
- the same native compaction plus the adaptive candidate.

Official OpenAI documentation describes `/responses/compact` output as encrypted and opaque and says not to depend on its internals. Claude Code documentation says `/compact` replaces the conversation with a summary and that older tool outputs are cleared before summarization. Both therefore belong in black-box product tests, not in the reproducible definition of memory.

API billing and subscription access are separate experimental resources. A subscription client must not be assumed to include an automatable API compaction endpoint.

## The decisive task family

Ordinary recall is insufficient. Histories must contain items whose future importance is unknowable at write time.

Example shape:

1. At token 120,000 an apparently minor timestamp anomaly is recorded.
2. Several million tokens later a new task reveals that this anomaly explains a critical failure.
3. The earlier event competes with common facts, obsolete facts, contradictions, poison, repeated noise, and more recent but irrelevant events.

The test asks whether each arm can recover the exact old evidence, distinguish its time and reliability, make the correct new decision, cite its source, and do so within the same active-context and compute budget. It also includes cases where the anomaly is noise so that saving everything is not confused with promoting everything.

## Success and rejection

The adaptive system earns added complexity only if, on at least two corpus families and two reader/provider families where feasible, it improves delayed supported task success or counterfactual decision regret over:

- the frozen open compactor;
- FTS5 plus citations;
- the strongest unlocked retrieval comparator;
- at least one pinned external memory system; and
- a native-compaction black box in the provider-specific track.

It must not materially worsen critical wrong action, stale or poisoned intrusion, unsupported detail, provenance completeness, recovery, privacy, latency, disk growth, prompt tokens, maintenance calls, or total cost. A gain in Recall@k alone is not sufficient.

If FTS5 plus compaction matches the adaptive system, the adaptive layer is rejected or simplified. If compaction alone matches it on short tasks, that is an expected boundary condition, not a reason to hide the null.

## Consequence for current work

The existing provider-neutral project-memory bootstrap is the first executable reference for the storage/retrieval boundary, not evidence that the final system works. Research can now proceed against one stable floor while all higher mechanisms remain gated experiments.

## Sources

- [Official OpenAI model guidance: response compaction](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.2#compaction-extending-effective-context)
- [Claude Code context window and compaction](https://code.claude.com/docs/en/context-window)
- [Claude Code prompt caching and compaction request](https://code.claude.com/docs/en/prompt-caching)
- [AgentMem repository](https://github.com/AgentMem/agentmem), audited at `c96ff3ce7a5286d33a7c280d53cafa1bfcb13693`
- `../11-research-laboratory/compression-benchmark-extension.md`
- `../12-interdisciplinary-memory/compression-synthesis.md`
- `minimal-reuse-architecture-v0.md`
