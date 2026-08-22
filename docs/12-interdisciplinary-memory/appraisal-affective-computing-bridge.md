# Appraisal and affective computing as a bridge to memory control

Status: conceptual bridge; no claim of machine feeling and no architecture decision

## Why this bridge matters

Discrete labels such as joy, anger, fear, or sadness are poor first-class control inputs for durable memory. Appraisal theories instead describe evaluations of an event relative to goals, predicted consequences, control/coping potential, novelty, urgency, agency, and norms. Computational appraisal models show that these variables can drive a process model without assuming that the implementation has human physiology or subjective experience.

This does not validate any specific appraisal theory as a complete account of emotion. It offers a better experimental factorization than an opaque emotion-vector cosine score.

## Transferable factor map

| Appraisal concept | Project operational variable | Allowed memory effect | Forbidden inference |
| --- | --- | --- | --- |
| novelty | mismatch with a frozen predictor | provisional eligibility or extra verification | novel means true or important |
| goal relevance | named task/user/policy obligation | candidate retrieval/replay priority | related means evidentially sufficient |
| goal conduciveness | verified benefit/harm to an explicit objective | consequence label after outcome | positive language means benefit |
| urgency | time until an outcome becomes irreversible | retrieve-more or reminder timing | urgency overrides authorization |
| control/coping potential | preventability and recoverability | choose retrieve/ask/act/abstain experiment arm | high control proves the proposed action works |
| agency | source and responsible actor | authorization/provenance routing | inferred actor is confirmed identity |
| outcome probability | calibrated predictive distribution plus evidence | uncertainty-aware search budget | probability is factual validity |
| norm compatibility | versioned policy and consent rules | block or require review | social convention silently rewrites user policy |

## Critical separation

```text
observation -> appraisal candidate -> verified outcome -> control proposal
       |              |                    |                |
   raw evidence    uncertain metadata   evidence-linked   reversible action
```

An LLM may propose an appraisal, but it cannot self-certify the outcome, authority, or memory action. Explicit user labels and observed outcomes carry different provenance and must remain distinguishable. Reappraisal is a new versioned interpretation, not silent mutation of the original event.

## Why discrete emotion similarity is insufficient

Two episodes can both be tagged `fear=0.8` while requiring opposite actions: one may contain a verified recurring hazard, the other a corrected false alarm. Conversely, a neutral audit checksum and a frightening incident may share the same retrieval obligation even though their affect vectors are far apart. Emotion-vector nearest neighbors therefore test affect similarity, not task relevance, evidence sufficiency, or correct action.

## Falsifiable comparisons

1. Discrete eight-emotion cosine versus appraisal factors versus relevance/recency.
2. Model-inferred appraisal versus explicit user label versus verified outcome.
3. Static appraisal versus versioned reappraisal after correction.
4. One global control action versus phase-specific append/replay/protect/retrieve-more proposals.
5. Appraisal controller versus raw archive retrieval at identical context and maintenance budgets.

Reject appraisal control if its added dimensions do not beat verified consequence alone, if they amplify dramatic poison, or if a correction fails to reduce obsolete alarm behavior without deleting historical evidence.

## Source boundary

- Moors, Ellsworth, Scherer, and Frijda 2013 survey common claims and open disputes in appraisal theories: https://doi.org/10.1177/1754073912468165
- Marsella and Gratch's EMA process model treats appraisals as dynamically recomputed from changing beliefs and goals: https://doi.org/10.1016/j.cogsys.2008.03.005
- Their use in virtual agents establishes computational implementability, not phenomenology, biological equivalence, or memory benefit.
