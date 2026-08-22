# Research Plan

## Mission

Build the evidence base required to design a local-first long-term memory layer for LLM agents without modifying the model's context window or parameters.

## Phase 0 — Research infrastructure

### Deliverables

- Shared terminology and scope.
- Source-quality and evidence-rating rules.
- Paper, project, dataset, and benchmark catalogs.
- Reproducible discovery scripts.
- Decision, exclusion, and open-question logs.

### Exit criteria

- Every core term has an operational definition.
- Each proposed mechanism has at least one measurable hypothesis.
- External projects have license and relevance metadata.
- Benchmark leakage and evaluation limitations are documented.

## Phase 1 — Human memory foundations

### 1. Working and short-term memory

Research capacity, attention, active maintenance, interference, chunking, the episodic buffer, and the relationship between short- and long-term memory.

Questions:

- Which properties are useful engineering abstractions?
- Which properties do not map to a text context window?
- Is the relevant analogue a buffer, an attention policy, or an active workspace?

### 2. Episodic memory

Research event binding, what-where-when structure, contextual reinstatement, source memory, temporal ordering, pattern separation, pattern completion, autobiographical memory, and reconstructive recall.

Questions:

- What metadata makes an event recoverable later?
- How should exact evidence coexist with reconstructed summaries?
- How do cues select a relevant episode when semantic similarity is weak?

### 3. Semantic memory and schemas

Research abstraction across episodes, schema formation, semanticization, concept learning, generalization, and the distinction between facts and beliefs.

Questions:

- When is evidence sufficient to promote an observation into a fact or rule?
- How should confidence, exceptions, and provenance survive consolidation?

### 4. Procedural and skill memory

Research habits, skill acquisition, sequence learning, action policies, automaticity, and transfer.

Questions:

- Should a procedure be stored as text, executable policy, examples, or all three?
- How should successful and failed attempts update a procedure?

### 5. Encoding and attention

Research depth of processing, novelty, distinctiveness, goals, curiosity, reward, prediction error, emotional arousal, and attentional selection.

Questions:

- Which signals predict later usefulness rather than mere memorability?
- Can outcome-conditioned salience improve write decisions?

### 6. Consolidation, replay, and sleep

Research synaptic versus systems consolidation, complementary learning systems, replay, interleaving, and offline reorganization.

Questions:

- When and how should an agent replay experiences?
- Can consolidation improve generalization without corrupting evidence?
- What schedule minimizes interference and compute cost?

### 7. Reconsolidation and updating

Research memory reactivation, updating, extinction, correction, and the controversy around trace modification.

Questions:

- Should retrieval modify memory strength or content?
- How do we preserve the original state while recording a revision?

### 8. Forgetting and interference

Research decay, retrieval failure, proactive and retroactive interference, cue overload, inhibition, adaptive forgetting, and retrieval-induced forgetting.

Questions:

- Does deleting data help, or is lowering retrieval priority enough?
- When is forgetting beneficial rather than destructive?
- How should the system distinguish stale, contradicted, irrelevant, and inaccessible memories?

### 9. Retrieval practice and spacing

Research testing effects, spacing, desirable difficulties, strength models, and reminder scheduling.

Questions:

- Does successful reuse strengthen agent memories?
- Can rarely used but critical memories be protected from frequency bias?

### 10. Metamemory and prospective memory

Research confidence, feeling-of-knowing, source monitoring, knowing when to search, remembering future intentions, and task interruption/resumption.

Questions:

- How can an agent know that relevant memory may exist?
- How should unresolved intentions and future triggers be stored?

## Phase 2 — LLM and agent memory landscape

Research each stage independently.

### Write

- Event segmentation and memory granularity.
- Extraction of facts, preferences, decisions, failures, and procedures.
- Write gating and duplicate detection.
- Privacy filtering and user control.

### Representation

- Raw text and trajectories.
- Atomic facts and structured records.
- Embeddings and sparse indexes.
- Temporal knowledge graphs.
- Hierarchical summaries.
- Latent and parameter-level memory as comparison classes.

### Organization

- Entity, topic, task, project, temporal, and causal indexes.
- Links between evidence and derived memories.
- Versioning, supersession, and validity intervals.

### Retrieval

- Lexical, dense, hybrid, graph, temporal, causal, and multi-stage retrieval.
- Query expansion and memory routing.
- Diversity, contradiction handling, and evidence bundles.
- Retrieval triggering and abstention.

### Context construction

- Token budgeting.
- Ordering and grouping.
- Raw evidence versus summaries.
- Instruction/data separation and prompt-injection resistance.

### Consolidation

- Episode clustering.
- Semantic and procedural induction.
- Confidence calibration.
- Reversible summaries and provenance.

### Retention

- Importance, recency, access frequency, novelty, cost, prediction error, and future utility.
- Archive versus suppression versus deletion.
- Per-type decay and retention horizons.

### Learning

- Weak supervision.
- Delayed labels.
- Counterfactual utility estimation.
- Contextual bandits and online learning.
- Distribution shift and catastrophic policy mistakes.

## Phase 3 — Human/AI bridge

For each biological idea, produce:

```text
finding -> computational principle -> proposed mechanism
        -> baseline -> experiment -> rejection criterion
```

High-priority bridge hypotheses:

1. Complementary episodic and semantic stores outperform a single homogeneous store.
2. Provenance-preserving consolidation outperforms destructive summarization.
3. Prediction error and outcome severity improve retention decisions beyond relevance and recency.
4. Per-memory-type retention policies outperform one global decay curve.
5. Retrieval-trigger policies reduce token cost without increasing critical misses.
6. Counterfactual utility labels outperform retrieval-frequency labels.
7. Temporal and causal indexes recover memories missed by semantic similarity.

## Phase 4 — Evaluation science

### Separate subsystems

- Write quality.
- Storage integrity.
- Retrieval recall and precision.
- Temporal and contradiction reasoning.
- Context-builder efficiency.
- Downstream task impact.
- Consolidation fidelity.
- Utility prediction.
- Retention mistakes.

### Required comparisons

- Full context when feasible.
- Raw chronological archive.
- BM25.
- Dense retrieval.
- Hybrid BM25+dense.
- Recency+importance+relevance.
- Hierarchical summaries.
- Temporal graph.
- Learned policy.

### Required ablations

- Without each memory type.
- Without provenance.
- Without consolidation.
- Without operational salience.
- Without recency.
- Without semantic similarity.
- With and without the retrieved memory in the final task.

### Core metrics

- Evidence Recall@k and Precision@k.
- Critical-memory miss rate.
- Stale-memory and contradiction error rates.
- Source attribution accuracy.
- Exact-detail preservation.
- Downstream task delta with versus without memory.
- Context tokens, latency, storage, and model-call cost.
- Utility prediction calibration.
- Retention regret and irreversible-loss rate.

## Phase 5 — Data strategy

### Public supervised evidence

- LongMemEval and LoCoMo for conversational evidence retrieval.
- LongMemEval-V2 and MemoryAgentBench for agent experience.
- BEAM and long-scale suites for stress testing.
- Coding-agent trajectories for failures, recovery, and strategy changes.

### Synthetic histories

Generate histories with controlled ground truth for:

- delayed usefulness;
- contradictions and supersession;
- recurring failures;
- weak semantic cue overlap;
- rare but catastrophic events;
- consolidation-safe and consolidation-unsafe details;
- causal versus merely correlated memories.

### Real project logs

Eventually record:

- what was stored;
- predicted importance and retention;
- what was retrieved;
- whether it influenced an action;
- whether the action improved;
- later corrections and human feedback.

## Phase 6 — Pre-implementation specification

Only after earlier phases, define:

- append-only event schema;
- memory object schema;
- provenance and versioning model;
- retrieval API;
- local security and encryption model;
- data export/deletion controls;
- baseline evaluation harness;
- experiment registry.

## Explicitly deferred

- Replacing or modifying transformer context-window internals.
- Training a large neural network before simple baselines.
- Irreversible forgetting.
- Claims of human-equivalent memory.
- Emotion or consciousness claims.
- Production deployment before privacy threat modeling.
