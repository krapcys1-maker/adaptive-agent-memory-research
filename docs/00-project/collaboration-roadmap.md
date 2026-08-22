# Collaboration Roadmap

Status: reviewed

The research can proceed in parallel without prematurely coupling implementation decisions.

## Workstream HM-1 — Working memory and attention

Deliverable: reviewed synthesis of active maintenance, executive control, capacity, interference, chunking, and long-term-memory interaction.

Key output: precise statement of what a context window does and does not approximate.

## Workstream HM-2 — Episodic, semantic, and procedural systems

Deliverable: comparison of memory systems, event representation, schemas, semanticization, skills, habits, and Complementary Learning Systems.

Key output: candidate multi-store architecture and competing single-store baseline.

## Workstream HM-3 — Consolidation, replay, and reconsolidation

Deliverable: evidence map covering synaptic/systems consolidation, replay, interleaving, reactivation, updating, and controversies.

Key output: reversible consolidation requirements and unsafe transformations.

## Workstream HM-4 — Forgetting and retrieval

Deliverable: decay, interference, cue failure, inhibition, retrieval practice, spacing, source monitoring, and adaptive-forgetting synthesis.

Key output: operational distinction between deletion, archive, suppression, low confidence, and failed retrieval.

## Workstream HM-5 — Salience, emotion, reward, and prediction error

Deliverable: separate evidence for emotional arousal, stress, novelty, reward, motivation, and prediction-error effects.

Key output: a non-anthropomorphic operational-salience feature set with risks and ablations.

## Workstream AI-1 — Memory lifecycle survey

Deliverable: write/represent/organize/consolidate/retrieve/update/retain/delete taxonomy across papers and open-source systems.

Key output: a normalized architecture matrix.

## Workstream AI-2 — Local-first systems audit

Deliverable: code-level review of storage backends, offline operation, model/provider dependencies, encryption, access controls, portability, and deletion.

Key output: reusable components and missing local-first infrastructure.

## Workstream AI-3 — Temporal, graph, and hybrid retrieval

Deliverable: comparison of BM25, embeddings, reranking, graph traversal, temporal filtering, causal relations, and hierarchical retrieval.

Key output: minimal retrieval baselines and query-family routing hypotheses.

## Workstream AI-4 — Learned memory management

Deliverable: survey of learned write, compression, retrieval, retention, and context-management policies.

Key output: label definitions, model classes, feedback loops, and distribution-shift risks.

## Workstream EV-1 — Benchmark audit

Deliverable: versioned review of LongMemEval, LoCoMo, LongMemEval-V2, BEAM, MemoryAgentBench, LoCoMo-Plus, OmniMemEval, and MemBase.

Key output: what each benchmark measures, leakage risks, judge sensitivity, context-size dependence, and valid comparison protocol.

## Workstream EV-2 — Dataset and label audit

Deliverable: inspect evidence annotations, trajectory outcomes, licenses, splits, synthetic generation, and negative-label validity.

Key output: training/validation/final-test allocation and label confidence.

## Workstream EV-3 — Causal utility

Deliverable: methods for estimating whether a memory improved a later action, including paired rollouts, ablations, off-policy bias, and delayed/censored outcomes.

Key output: future-utility definition and feasible measurement protocols.

## Workstream SE-1 — Safety, privacy, and ownership

Deliverable: threat model for stored prompt injection, poisoned experience, secrets, cross-user leakage, model switching, correction, export, and deletion.

Key output: mandatory safety constraints for the eventual schema and APIs.

## Integration milestones

### Milestone 1 — Vocabulary freeze

All workstreams use the same operational definitions and evidence statuses.

### Milestone 2 — Evidence map v1

At least three strong sources for every high-priority human-memory mechanism and every major agent-memory lifecycle stage, including contrary findings where available.

### Milestone 3 — Architecture candidates

Three competing architectures described at mechanism level, without committing to a software stack.

### Milestone 4 — Evaluation protocol

Subsystem metrics, baselines, ablations, data splits, judge controls, and cost reporting fixed before implementation comparisons.

### Milestone 5 — Stable project-memory specification

Append-only research memory schema and retrieval protocol specified separately from experimental learned memory.

### Milestone 6 — Implementation authorization

Begin product code only when the baseline, data, and evaluation design can detect whether added complexity helps.
