# Dataset Catalog and Label Strategy

Status: in-progress

## Public datasets

### LongMemEval

Useful labels:

- answer sessions and evidence turns;
- knowledge updates;
- temporal relations;
- questions requiring abstention.

Do not interpret all non-evidence turns as globally useless.

### LoCoMo

Useful material:

- long conversations;
- event summaries;
- evidence dialogue IDs;
- temporal event graphs;
- human verification/editing.

Use event summaries as perceived importance and QA evidence as later task relevance, not as a complete utility ground truth.

### LongMemEval-V2

Useful material:

- agent trajectories;
- workflow knowledge;
- dynamic state;
- environment-specific recurring failures;
- premise awareness;
- long temporal gaps and multimodal observations.

Reserve a held-out portion for final evaluation.

### MiMo Claude Code Traces

Potential weak signals:

- tool errors;
- repeated failed actions;
- strategy changes;
- recovery sequences;
- duration, cost, and token usage;
- final task success.

Manual inspection is required before treating these as frustration, causal importance, or utility labels.

### BEAM and MemoryAgentBench

Use primarily for held-out stress and transfer evaluation. Avoid optimizing all policies directly on final test data.

## Label taxonomy

Keep these targets separate:

| Label | Meaning |
|---|---|
| query relevance | needed to answer a particular query |
| retrieval success | selected by the memory system |
| reader use | cited or reflected in the model output |
| decision influence | changed the selected action |
| outcome utility | improved the objective outcome |
| causal utility | estimated difference with versus without memory |
| retention horizon | latest time at which availability was required |
| compression safety | whether transformed memory preserves task-critical content |
| consolidation eligibility | evidence sufficiency for a generalized memory |
| stale/superseded | no longer valid for current-state use |

## Data risks

- Censored futures: an event may become useful after observation ends.
- Exposure bias: frequently retrieved memories receive more chances to appear useful.
- Policy bias: current retrieval determines which utility labels can be observed.
- Template leakage between synthetic histories.
- Judge-model bias and prompt sensitivity.
- User and environment leakage across splits.
- Outcome confounding by reader model capability.
- Positive-outcome bias that forgets useful warnings and avoided failures.
