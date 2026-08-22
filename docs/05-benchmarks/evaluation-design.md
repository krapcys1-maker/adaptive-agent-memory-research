# Evaluation Design Requirements

Status: outline

## Four evaluation layers

### Layer 1 — Storage integrity

- Can exact original evidence be recovered?
- Are timestamps, entities, sources, and validity preserved?
- Did consolidation introduce unsupported statements?

### Layer 2 — Retrieval

- Evidence Recall@k and Precision@k.
- Recall per retrieved token.
- Recall under paraphrase, temporal cue, causal cue, and weak semantic overlap.
- Distractor sensitivity as history grows.

### Layer 3 — Use and reasoning

- Does the model cite and correctly interpret evidence?
- Can it resolve updates and contradictions?
- Does it abstain when evidence is missing?

### Layer 4 — Task utility

- Paired outcomes with and without a memory.
- Repeated-task efficiency and failure avoidance.
- Cost, latency, and token reduction.
- Human evaluation of whether memory changed the decision appropriately.

## Retention evaluation

Every retention decision belongs to one of four outcomes:

| Decision | Later needed | Result |
|---|---:|---|
| keep | yes | true keep |
| keep | no | storage/retrieval-cost overhead |
| suppress/archive | no | true suppress |
| suppress/archive | yes | critical retention error |

Weight errors by downstream consequence, not only frequency.

## Counterfactual protocol

Where feasible, replay the same later task using:

1. no durable memory;
2. full relevant source episode;
3. retrieved memory candidate;
4. consolidated memory only;
5. retrieved memory plus provenance evidence.

This separates memory availability from memory transformation and reader performance.
