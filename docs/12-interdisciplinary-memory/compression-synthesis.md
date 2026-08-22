# Compression synthesis: archive, semantic hypotheses, and active context

Status: extracted synthesis; not an architecture decision

## Convergent pattern

Five fully read sources point to a useful separation, although none validates our complete system:

```text
canonical episodic archive        derived semantic layer          query-conditioned working set
append-only, high fidelity   ->   summaries/models/hypotheses ->   evidence admitted to context
versioned + provenance            rebuildable + uncertain          strict token/risk budget
```

The first tier answers "what was observed?" The second answers "what pattern do we currently infer?" The third answers "what evidence is useful for this query/decision now?" A correction supersedes earlier state but does not erase the event history.

## What is supported versus inferred

| Statement | State |
| --- | --- |
| Active memory is capacity-limited and errors should be measured against task consequences | supported in constrained human/computational and agent tasks |
| Repeated irreversible summarization can compound loss | demonstrated in one small recent reference experiment; broader replication needed |
| Query-conditioned decision distinctions can beat descriptive similarity under matched runtime budget | reported in a recent agent-memory preprint; independent reproduction needed |
| Episodic detail can protect later model revision | normative Perspective plus reviewed prior simulations; direct project test needed |
| Semantic completion can improve efficiency while creating plausible wrong details | demonstrated in a narrow generative image model |
| Therefore our three-tier design is best | project hypothesis only |

## Candidate controller signals

Do not collapse them into one salience score before ablation:

- query relevance and evidence coverage;
- decision/consequence sensitivity;
- temporal validity and supersession;
- source trust and poisoning risk;
- model uncertainty and surprise;
- novelty versus reproducible model change;
- user-declared importance;
- emotional dimensions: valence, arousal/intensity, controllability, social significance, and predicted future need.

Emotion is metadata and a testable allocation signal at this stage, not proof of subjective experience and not permission to treat high arousal as truth.

## Safety boundary

- Lossy summaries are derived artifacts with source links, version, generator, and confidence.
- Unsupported semantic completion is explicitly labeled or blocked from factual answers.
- Raw evidence remains available for re-retrieval, audit, rollback, and future reinterpretation.
- Revocation and access control apply to every tier; an immutable-by-default research log is not an excuse to retain data against user policy.

## Decision gate

This synthesis may influence implementation only after the compression benchmark extension is run against frozen baselines. A three-tier design is rejected or simplified if raw retrieval alone matches its quality, cost, and latency, or if derived layers materially increase stale, poisoned, or unsupported answers.
