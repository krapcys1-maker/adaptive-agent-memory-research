# Brain-to-AI transfer research protocol v0

Status: open discovery protocol; no architecture promotion

## Unit of research

One atlas row represents one proposed transfer and contains:

```text
biological mechanism or construct
biological function and boundary conditions
abstract computational problem
formal or algorithmic abstraction
ML implementation status
LLM-agent implementation status
benchmark evidence
literal-analogy risks
minimal falsifiable test
primary sources and inspectable systems
```

Mechanisms that share a name but solve different problems remain separate. Mechanisms with different names but the same abstract operation are linked as aliases, not counted as independent support.

## Five-stage evidence ladder

| Stage | Minimum evidence | Valid statement |
| --- | --- | --- |
| B0 vocabulary | review, textbook, or seed | the construct is worth screening |
| B1 biological mechanism | primary manipulation, lesion, recording, or reproducible behavioral contrast | a bounded biological effect was observed |
| C1 computational principle | formal model or explicit algorithm with failure conditions | a mechanism can be expressed computationally |
| M1 ML realization | inspectable method plus controlled benchmark | an artificial system implements a related operation |
| A1 agent-memory realization | external or parametric memory lifecycle plus agent-level ablation | an LLM agent uses and benefits from the operation under the tested conditions |

An A1 result does not prove biological equivalence. A biological B1 result does not prove engineering usefulness.

## Search procedure

For every mechanism, search in six passes:

1. exact neuroscience or psychology term;
2. computational-neuroscience model and aliases;
3. continual-learning, reinforcement-learning, information-retrieval, database, and operating-system analogues;
4. `LLM`, `agent`, `RAG`, `external memory`, and `long-term memory` implementations;
5. benchmark, ablation, replication, null result, negative transfer, poisoning, and failure terms;
6. citations backward and forward from the strongest primary source and strongest implementation.

Example alias expansion for pattern separation:

```text
pattern separation
sparse or orthogonal representation
contrastive indexing
entity/time scoping
deduplication versus disambiguation
similar-episode interference
false merge and source confusion
```

Search logs record date, query, database, result count when available, screened count, new unique mechanisms, new implementations, contradictions, and reason for stopping.

## Implementation classification

`ml_status` and `llm_agent_status` use only these states:

- `mature` / `common` — multiple established implementations, still not necessarily validated for our task;
- `demonstrated` — at least one inspectable controlled implementation;
- `partial` — adjacent implementation misses a defining operation or boundary;
- `sparse` — isolated or weakly evaluated examples;
- `none_found` — no qualifying implementation found after logged searches, never proof of nonexistence.

`transfer_status` means:

- `existing_baseline` — must be included as a comparison;
- `active_project_hypothesis` — already has a project protocol or strong synthesis;
- `gap_candidate` — promising but requires primary reading and a benchmark contract;
- `background_only` — useful context, not near-term engineering;
- `reject_literal_transfer` — the anatomical/metaphorical mapping is specifically unsafe or uninformative.

## Admission to an experiment

A transfer is test-ready only when all are explicit:

- target failure and computational function;
- strongest non-biological engineering alternative;
- minimum baseline and one mechanism-specific ablation;
- unit of assignment and analysis;
- data, model, prompt, retrieval, and maintenance budgets;
- primary outcome and harm outcomes;
- characteristic failure and rejection threshold;
- source/provenance preservation;
- privacy and mutation boundary;
- reason the experiment can distinguish mechanism from extra compute or context.

## Universal negative controls

Every brain-inspired mechanism is compared with:

- no mechanism;
- random action at matched frequency and cost;
- simple recency/relevance/frequency rules;
- equal extra tokens or model calls without mechanism-specific content;
- oracle using held-out labels, analysis only;
- corrupted, stale, or poisoned inputs where the mechanism could amplify memory.

If random or equal-compute controls match the candidate, attribute the gain to capacity or computation, not the proposed mechanism.

## Cross-mechanism interactions

The atlas is factorized because the full `Memory Policy` is not identifiable as one initial experiment:

```text
STORE -> RETRIEVE -> REPLAY -> CONSOLIDATE -> REVISE -> ARCHIVE
```

Only one transition rule changes per first-stage experiment. Pairwise interactions are tested later, starting with:

- pattern separation x completion;
- salience x collateral forgetting;
- replay x consolidation representation;
- reconsolidation x source monitoring;
- prospective memory x temporal validity;
- procedural memory x goal/habit arbitration;
- learned control x causal future-utility telemetry.

## Stopping rule

Discovery for one row pauses after two consecutive query/snowball rounds produce:

- no new qualifying primary mechanism paper;
- no new inspectable implementation class;
- no new benchmark or material contradiction;
- and the existing sources cover the principal claim, boundary, and failure mode.

The row then moves to synthesis or experiment. It never becomes “all literature collected.” New evidence creates a new atlas revision.
