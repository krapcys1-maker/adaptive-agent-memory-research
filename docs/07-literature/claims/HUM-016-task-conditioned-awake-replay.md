# HUM-016 — Awake replay content changes with task state and predicts near-term decisions

- Domain: `animal-memory`
- Claim type: `associational`
- Status: `challenged`
- Confidence: `medium`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: eight male rats, CA1 place cells and deep-MEC grid cells during a rewarded Z-track task.
- Intervention or comparison: task-engaged versus prolonged disengaged corner immobility; correct versus incorrect next turns.
- Measured outcome: local/congruent/forward replay, grid-place coherence, and cross-validated turn prediction.
- Timescale: roughly 10–15 seconds around task movement versus longer stops.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Ólafsdóttir et al. 2017 | Results, pp. 3–6, Figures 2–4 | engaged replay was more local/congruent/forward; disengaged replay was more remote and coherent with deep MEC | observational multi-site electrophysiology with shuffle controls |
| same | Results, pp. 7–8, Figure 5 | engaged-event classifier predicted next-turn correctness at 62.8% versus 49.6% shuffled; disengaged prediction was nonsignificant | cross-validated event-level classifier |

## Contradictions, null results, and boundary conditions

Engagement-by-accuracy interactions for congruence and locality were nonsignificant. Disengaged replay did not significantly predict choice. The task used a small number of male rats in one spatial paradigm.

## Alternative explanations

Task state, attention, arousal, reward timing, movement preparation, and network state may jointly cause both replay content and better choices. Disengaged grid coherence does not prove consolidation.

## Computational translation

- Abstract problem: decide what to rehearse online versus offline.
- Candidate mechanism: phase-conditioned replay with separate online task-local and offline diverse policies.
- Simpler baseline: one uniform, recency, or relevance sampler.
- Predicted benefit: immediate decision accuracy plus delayed transfer at the same replay budget.
- Predicted failure: excessive exploitation online or unproductive/random replay offline.
- Rejection criterion: the two-mode policy fails to beat matched single-policy baselines across two task families.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: medium for content/state association; low for proposed planning/consolidation functions

