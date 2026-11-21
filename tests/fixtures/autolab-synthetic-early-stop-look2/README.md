**Status:** completed

# Lab program SYNTHETIC-EARLY-STOP-LOOK2

**Question (owner):** Synthetic sequential package that stopped early at look 2

Domain: `command-run`
Cycles: 1; role calls: 0; units: 300.

## Results (cycle 1, n = 201 units, 4 arms)

| arm | solved |
|---|---|
| mismatched_type | 0.63 |
| none | 0.38 |
| placebo | 0.38 |
| retrieved_task | 0.80 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| mismatched_type − placebo (primary) | +0.249 | [+0.114, +0.384] | 79 / 29 | positive |
| retrieved_task − placebo (primary) | +0.423 | [+0.300, +0.546] | 100 / 15 | practical |
| mismatched_type-none | +0.249 | [+0.114, +0.384] | 79 / 29 | positive |
| placebo-none | +0.000 | [-0.135, +0.135] | 48 / 48 | inconclusive |
| retrieved_task-none | +0.423 | [+0.311, +0.534] | 93 / 8 | practical |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | practical | supported | developmental | +0.423 | [+0.300, +0.546] | `finding:01d1d4dbb8d29d3c` |
| mismatched_type | H2 (predicted null) | 1 | positive | refuted | developmental | +0.249 | [+0.114, +0.384] | `finding:1003473e6233712d` |

## Caveats

- Format criteria used the pre-registered rule `imbalance_only`: a counter fails only if the arm − placebo difference exceeds its tolerance AND the 95% interval excludes 0. Under this rule an `unresolved` state means placebo neutrality was not shown, only not refuted.
- Counters pre-registered as behaviour, not as format failures (their imbalance does not flag a measurement problem): `invalid_no_action_tag`; see the process criteria table below.

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag | truncated | untagged_not_truncated |
|---|---|---|---|---|---|
| mismatched_type | 0.000 | 0.119 | 0.054 | 0.037 | 0.042 |
| none | 0.000 | 0.109 | 0.051 | 0.038 | 0.034 |
| placebo | 0.000 | 0.115 | 0.049 | 0.037 | 0.037 |
| retrieved_task | 0.000 | 0.127 | 0.055 | 0.035 | 0.033 |

### Process criteria (arm − placebo, per step)

| arm | counter | kind | tolerance | difference | 95% interval | state |
|---|---|---|---|---|---|---|
| mismatched_type | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| mismatched_type | `invalid_no_action_tag` | behaviour | 0.03 | +0.005 | [-0.004, +0.014] | balanced |
| mismatched_type | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | +0.005 | [-0.002, +0.011] | balanced |
| retrieved_task | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_task | `invalid_no_action_tag` | behaviour | 0.03 | +0.006 | [-0.004, +0.015] | balanced |
| retrieved_task | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.004 | [-0.010, +0.003] | balanced |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:4c2b1d3f68cb0242` (cycle 1): interim_look
- `decision:15a184327497f2e0` (cycle 1): interim_look
- `decision:029076d67d4ddbb6` (cycle 1): rules applied to the results
- `decision:68788d9b6986d69b` (cycle 1): program finished

## Status of each direction

- mismatched_type: open
- retrieved_task: open

## Scope of the conclusions

The conclusions apply only to the task population `command-run:synthetic-early-stop-look2`, the arms ['retrieved_task', 'mismatched_type'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 201 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
