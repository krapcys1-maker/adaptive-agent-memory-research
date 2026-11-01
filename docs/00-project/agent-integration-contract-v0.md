# Agent integration contract, proposal v0

**Status: proposal.** Nothing here is implemented, the names are provisional, and no existing agent has been touched. It answers item 8 of the [research vision](research-vision-2026-11.md): an interface through which an external autonomous agent can feed experiences to the memory engine and receive retrievals, without the engine knowing anything about that agent. The facts about today's engine it builds on are in section 7 of the [direction review](research-direction-review-2026-11.md).

## 1. Principles

1. **Independence.** The engine knows nothing about any particular agent; an agent knows nothing about the engine's internals. Both sides see only this contract.
2. **Research mode first.** The first integration is a replay: the agent (or a wrapper) writes an append-only export of its experiences, and the research harness consumes it offline. The production agent is never changed, and no retrieval result is injected into it.
3. **Budget is explicit and in tokens.** Every retrieval has a hard budget; the engine cannot exceed it.
4. **Cost is reported by the engine**, per call, in the same shape for every strategy.
5. **Provenance is never lost.** Any returned item says whether it is original evidence or a later interpretation, and which raw experiences it rests on.
6. **Forgetting is operational first.** A dormant experience is no longer supplied, but stays recoverable. Physical erasure exists for privacy and is a different, logged operation.
7. **Determinism.** Given a stream, a strategy configuration, a pinned model and a seed, a replay is reproducible, and the configuration has a digest.

## 2. Operations

| Operation | Purpose | Key inputs | Key outputs |
|---|---|---|---|
| `ingest` | Record one experience in the archive. | `experience` (section 3) | `experience_id`, write cost |
| `set_goal` | Create or change a goal, with a valid-from time. | `goal` (section 3) | `goal_id` |
| `retrieve` | Build the context for a task. | `cue` text, `goal_ids`, `budget_tokens` (hard), `tokenizer`, `as_of`, `mode` | items with representation, tokens, reason, provenance; `retrieval_id`; cost |
| `feedback` | Tell the engine what happened with a retrieval. | `retrieval_id`, used and ignored item ids, outcome with its label source | acknowledgement |
| `maintain` | Run consolidation or re-evaluation outside retrieval. | `as_of`, optional budget | what changed; cost |
| `forget` | Make experiences dormant, reactivate them, or erase them. | experience ids, mode `dormant`, `reactivate` or `erase`, reason | tombstones |
| `export` / `replay` | Move a stream out of an agent and run it through a strategy deterministically. | time range; stream, strategy config, seed | stream file; retrieval log, cost totals |
| `describe` | State version, configuration digest, counts and cost totals. | none | description |

`retrieve` never mutates state unless the strategy declares `query_mutates_state` (the arena adapter already uses this declaration). `maintain` is the only operation that may consolidate or re-score, so its cost is visible and separate from retrieval.

## 3. Records

**Experience** (JSON, UTF-8): `experience_id` (stable, supplied by the agent), `occurred_at` (ISO-8601 UTC, supplied by the agent or the replayer; the engine adds its own `recorded_at`), `agent_id`, `task_id` (optional), `goal_ids` (optional), `kind` (`observation`, `action`, `decision`, `outcome`, `feedback`, `note` or `source_document`), `content` (the raw text), `payload` (optional structured data), `source` (uri or path, retrieved-at, reliability hint), `refs` (other experience ids), `tags`, and `privacy` (retention class; `pii` as `none`, `present` or `unknown`).

**Goal**: `goal_id`, `text`, `status` (`active`, `paused`, `done`), `valid_from`, `parent_goal_id`, optional `concept_hints`.

**Retrieved item**: `item_id`, `experience_ids`, `representation` (`episodic_raw`, `summary`, or `trace_resolved` for a trace that was followed back to its raw event; `trace_resolved` and the `association:<concept>` reason code are provisional, see section 7), `text`, `tokens`, `score`, `reason` (codes such as `cue_match`, `goal_match`, `association:<concept>`, `recency`), `provenance` (`original` or `interpretation`, with the source ids). `reason` is what makes false associations auditable.

**Cost** (integer micro-units, as in `scripts/arena/adapter.py`, which has model calls, input tokens, output tokens and wall-clock microseconds, each marked `native`, `instrumented` or `unobservable`). Embedding tokens and an estimated price would be additions to that type; it does not hold them today.

## 4. Replay and isolation

- The agent side produces an `export`: one JSONL line per experience, in time order, plus its goal changes and, if available, the outcomes of its tasks. The Substack agent would need a read-only exporter in a separate wrapper; this repository does not contain and must not change that agent.
- `replay` advances a simulated clock; `as_of` makes every query time-correct and prevents future leakage.
- A later `shadow` mode lets the engine receive live experiences and answer `retrieve` while the agent ignores the answers; results are compared offline. Only after that could any injection into a real agent be considered, and that is a separate decision.
- Interventions from the vision map onto replay: remove or replace one experience, restore an earlier state, or add a goal that makes an old experience relevant are all operations on the stream plus a seed.
- Secrets and personal data: the exporter must not include credentials or subscriber data; `ingest` rejects records flagged `pii: present` unless the strategy is configured to accept them; `erase` supports deletion on request.

## 5. How it maps onto what exists

| Contract | Today | Gap |
|---|---|---|
| `ingest` | `memory_add` | cannot supply `created_at`/`occurred_at`; nine research-only kinds, none for raw experiences; no payload or stable external id; no batch write |
| `retrieve` | `memory_context` | budget in characters; no goals; no `as_of`; no cost; lexical FTS5 only; the index also covers repository documents, so an experimental root must hold nothing else |
| revise | `memory_supersede` | fine as is; valid time already exists |
| inspect | `memory_get`, `memory_search`, `memory_timeline` | keep |
| `feedback` | none | usage telemetry schemas exist in `data/lab/pmlab-future-utility-v0/` but the server emits nothing |
| `maintain`, `forget` | none | supersession is the only state change; no dormant, reactivate or erase |
| `export`, `replay`, `describe` | none | `scripts/arena/adapter.py` and `scripts/corpus/arms.py` already contain the cost types and the budget-fair fill to build on, and `scripts/arena/adapter_v0_1.py` defines the contract digest |

## 6. Suggested path (not started)

1. Define the strategy interface as a small Python protocol that extends the arena adapter contract with a goal argument, a token budget and `maintain`. Wrap `MemoryStore` as one strategy. Change nothing in `tools/project_memory` yet.
2. Run the first experiment ([proposal v0](../11-research-laboratory/delayed-relevance-first-experiment-proposal-v0.md)) through that interface on synthetic streams.
3. Only then decide which operations deserve an MCP tool, and fix the gaps above in the store itself (caller-supplied time, token budgets, argument validation, a default root that is the working directory).
4. Write the exporter for a real agent as a separate wrapper, or against an isolated copy of that agent, read-only, after the owner approves. Adding anything to the production agent's own repository is a change to that agent and needs its own explicit authorisation.

## 7. Open questions

Who owns the exporter format when two agents differ; whether `feedback` labels from the agent itself (`self_report`) may be used for learning at all, given the vision's own warning about reinforcing familiar but wrong memories; whether the contract should carry a trace-and-association concept explicitly or leave it to strategies; and the retention and privacy policy for a real publishing agent, which the owner must set.
