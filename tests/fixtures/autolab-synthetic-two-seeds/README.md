**Status:** completed

# Lab program SYNTHETIC-TWO-SEEDS

**Question (owner):** Synthetic package with two seeds, a placebo identical to no memory and a disputed result

Domain: `command-run`
Cycles: 1; role calls: 0; units: 80.

## Results (cycle 1, n = 80 units, 3 arms)

| arm | solved |
|---|---|
| none | 0.55 |
| placebo | 0.55 |
| retrieved_task | 0.78 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| retrieved_task − placebo (primary) | +0.225 | [+0.082, +0.368] | 28 / 10 | positive |
| placebo-none | +0.000 | [-0.025, +0.025] | 0 / 0 | equivalent |
| retrieved_task-none | +0.225 | [+0.082, +0.368] | 28 / 10 | positive |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | positive | disputed | developmental | +0.225 | [+0.082, +0.368] | `finding:7c58d73f16f22795` |

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag |
|---|---|---|---|
| none | 0.000 | 0.088 | 0.059 |
| placebo | 0.000 | 0.082 | 0.049 |
| retrieved_task | 0.000 | 0.094 | 0.059 |

### Process criteria (arm − placebo, per step)

| arm | counter | kind | tolerance | difference | 95% interval | state |
|---|---|---|---|---|---|---|
| retrieved_task | `empty_retries` | criterion (equivalence) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_task | `invalid_no_action_tag` | criterion (equivalence) | 0.03 | +0.010 | [-0.006, +0.026] | balanced |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:587e6f286d70e866` (cycle 1): rules applied to the results
- `decision:e83333fba83d4c45` (cycle 1): program finished

## Status of each direction

- retrieved_task: open

## Scope of the conclusions

The conclusions apply only to the task population `command-run:synthetic-two-seeds`, the arms ['retrieved_task'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 80 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
