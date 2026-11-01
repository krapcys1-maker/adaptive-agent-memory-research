# Agent integration contract, proposal v0.1

**Status: proposal, revised on 2026-11-01 (v0.1).** The file keeps its v0 name so that existing links hold. The revision follows an independent audit of a real publishing agent (NIE) by that agent's own session and an independent check of that audit; the changes are listed in section 8. The owner has not reviewed this draft, and it is not the canonical format: that is the owner's decision. Nothing here is implemented, the names are provisional, and no existing agent has been touched. It answers item 8 of the [research vision](research-vision-2026-11.md): an interface through which an external autonomous agent can feed experiences to the memory engine and receive retrievals, without the engine knowing anything about that agent. The facts about today's engine it builds on are in section 7 of the [direction review](research-direction-review-2026-11.md).

## 1. Principles

1. **Independence.** The engine knows nothing about any particular agent; an agent knows nothing about the engine's internals. Both sides see only this contract.
2. **Research mode first.** The first integration is a replay: the agent (or a wrapper) writes an append-only export of its experiences, and the research harness consumes it offline. The production agent is never changed, and no retrieval result is injected into it.
3. **Budget is explicit and in tokens.** Every retrieval has a hard budget; the engine cannot exceed it.
4. **Cost is reported by the engine**, per call, in the same shape for every strategy.
5. **Provenance is never lost.** Any returned item says whether it is original evidence or a later interpretation, and which raw experiences it rests on.
6. **Forgetting is operational first.** A dormant experience is no longer supplied, but stays recoverable. Physical erasure exists for privacy and is a different, logged operation.
7. **Determinism of the engine, reproducibility of the environment.** Given a stream, a strategy configuration and a seed, the engine's state and context digests are identical on two runs (checked by running twice), and the configuration has a digest. A hosted reader without seed or temperature control, or whose model alias can drift, is not reproducible: a replay with such a reader is a re-evaluation, not a reproduction. Report the number of draws, a drift canary and the list of unrecorded inputs. "A pinned model and a seed" is not a sufficient condition.

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

**Experience** (JSON, UTF-8). Required: `experience_id`, `occurred_at`, `agent_id`, `kind`, `content`, `privacy`, `capture`. Optional: `task_id`, `goal_ids`, `payload`, and the rest.
- `experience_id`: stable; `id_basis` says whether the agent supplied it (`native`) or the exporter derived it (`derived_content_hash_plus_occurrence`).
- `occurred_at`: ISO-8601 UTC, supplied by the agent or the replayer; the engine adds its own `recorded_at`. `available_at`: the earliest moment the agent could have used the information (default `occurred_at`); `as_of` filters on it, because outcomes are recorded after they happen.
- `run_id` (optional) with `run_id_basis`: `native`, `time_window` (the entry was matched to a run by time) or `absent`.
- `kind`: `observation`, `action`, `decision`, `outcome`, `feedback`, `note` or `source_document`.
- `content`: the raw text; for a `decision` or an `outcome` of an agent that does not record its inputs, the recorded result, never an invented input.
- `capture`: `native` or `reconstructed`. For a `decision`, `inputs` says what is known about what the agent saw: `captured`, `derived`, `hashed_only`, `truncated` or `absent`. `refs` (other experience ids) may list only recorded experiences, and is `reconstructed` when matched by time window.
- `payload` (optional structured data), `source` (uri or path, retrieved-at, reliability hint), `tags`.
- Outcomes that arrive late also carry `age_at_measurement` and `censored` (a measurement taken before the outcome could have matured).
- `privacy`: the class `public_own` (the agent's own published text), `third_party_pseudonymized` or `excluded`, plus a retention class. Hashes and keyed pseudonyms of third-party content count as personal data.

An export as a whole carries `fidelity`: `exact`, `re_evaluation`, `reconstructed` or `synthetic`.

**Goal**: `goal_id`, `text`, `status` (`active`, `paused`, `done`), `valid_from`, `parent_goal_id`, optional `concept_hints`, and `basis`: `stated`, or `derived` when an exporter infers goals for an agent that has none (series, topics or experiment arms); a derived goal has provenance `interpretation`.

**Retrieved item**: `item_id`, `experience_ids`, `representation` (`episodic_raw`, `summary`, or `trace_resolved` for a trace that was followed back to its raw event; `trace_resolved` and the `association:<concept>` reason code are provisional, see section 7), `text`, `tokens`, `score`, `reason` (codes such as `cue_match`, `goal_match`, `association:<concept>`, `recency`), `provenance` (`original` or `interpretation`, with the source ids). `reason` is what makes false associations auditable.

**Cost** (integer micro-units, as in `scripts/arena/adapter.py`, which has model calls, input tokens, output tokens and wall-clock microseconds, each marked `native`, `instrumented` or `unobservable`). Embedding tokens and an estimated price would be additions to that type; it does not hold them today.

## 4. Replay and isolation

- The agent side produces an `export`: one JSONL line per experience, in time order, plus its goal changes and, if available, the outcomes of its tasks. Two exporter classes exist. **E1, a passive importer outside the agent**: a read-only snapshot of the agent's logs; it yields actions and outcomes but never inputs, so its fidelity is at most `re_evaluation`. **E2, an in-agent capture hook**: it changes the production agent, lives outside this repository, needs the owner's separate explicit authorisation, and this project neither recommends nor builds it. For an agent that does not record its cues and tasks (the Substack agent NIE is the first case), the cues and tasks of an experiment are generated in the laboratory, not recorded, and every result must say so. This repository does not contain and must not change that agent.
- `replay` advances a simulated clock; `as_of` makes every query time-correct and prevents future leakage.
- A later `shadow` mode lets the engine receive live experiences and answer `retrieve` while the agent ignores the answers; results are compared offline. Only after that could any injection into a real agent be considered, and that is a separate decision.
- Interventions from the vision map onto replay: remove or replace one experience, restore an earlier state, or add a goal that makes an old experience relevant are all operations on the stream plus a seed.
- Secrets and personal data: the exporter must not include credentials or subscriber data. Exporters are allowlist-only (copy named fields, fail closed on anything else), free text is scanned for handles and e-mail addresses, and `ingest` rejects records of class `excluded`. `erase` supports deletion on request. Nothing derived from third parties is committed to a public repository, including this one: only aggregate numbers, synthetic fixtures and manifest hashes may leave the laboratory. Key custody, rotation and destruction for pseudonyms must be written down before any real export.

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
| goals from a real agent | none | an agent such as NIE has no goal events; derive them from series and experiment arms with `basis: derived` |
| delayed outcomes | none | outcomes are recorded after they occur and may be censored: `available_at`, `age_at_measurement`, `censored` |
| block budgets | `char_budget` (characters) | NIE's memory blocks are in characters, at most about 1,250 tokens, against the 4,000-token starting figure of the vision |

## 6. Suggested path (not started)

1. Define the strategy interface as a small Python protocol that extends the arena adapter contract with a goal argument, a token budget and `maintain`. Wrap `MemoryStore` as one strategy. Change nothing in `tools/project_memory` yet.
2. Run the first experiment ([proposal v0](../11-research-laboratory/delayed-relevance-first-experiment-proposal-v0.md)) through that interface on synthetic streams.
3. Only then decide which operations deserve an MCP tool, and fix the gaps above in the store itself (caller-supplied time, token budgets, argument validation, a default root that is the working directory).
4. Write the exporter for a real agent as a separate wrapper, or against an isolated copy of that agent, read-only, after the owner approves. Adding anything to the production agent's own repository is a change to that agent and needs its own explicit authorisation.

## 7. Open questions

Who owns the exporter format when two agents differ; whether `feedback` labels from the agent itself (`self_report`) may be used for learning at all, given the vision's own warning about reinforcing familiar but wrong memories; whether the contract should carry a trace-and-association concept explicitly or leave it to strategies; and the retention and privacy policy for a real publishing agent, which the owner must set. Added in v0.1: which data from a real agent may be published, and in what form; custody and rotation of pseudonym keys; and who may authorise an in-agent capture hook (the owner, outside this project).

## 8. Changes from v0 (2026-11-01)

Facts about the real agent below are reported by its own session and by an independent check of that report; this project has not verified them against the agent's server.

- The agent records no prompts or model responses, only metadata, and its main journal has no run identifier (0 of about 5,400 entries). Hence `capture`, `inputs`, `run_id_basis` and `fidelity`, and the E1 and E2 exporter classes.
- Outcomes arrive up to days after the event, and some fields (a status that is overwritten in place, a field that may be filled in afterwards) leak the future if read from a snapshot. Hence `available_at`, `age_at_measurement`, `censored`, and the rule that `as_of` filters on `available_at`.
- The agent's environment is not deterministic (no seed or temperature control, model aliases that change, unseeded random draws). Hence the split in principle 7.
- The agent's repository on GitHub is public, as is this one. Hence the privacy classes, the allowlist rule and the publication boundary in section 4.
- The in-agent hook is a decision about the production agent, so it moved out of the suggested path (section 6, step 4).
