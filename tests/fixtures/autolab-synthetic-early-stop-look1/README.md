**Status:** completed

# Lab program SYNTHETIC-EARLY-STOP-LOOK1

**Question (owner):** Synthetic sequential package that stopped early at look 1

Domain: `command-run`
Cycles: 1; role calls: 0; units: 300.

## Results (cycle 1, n = 103 units, 4 arms)

| arm | solved |
|---|---|
| mismatched_type | 0.88 |
| none | 0.38 |
| placebo | 0.42 |
| retrieved_task | 0.86 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| mismatched_type − placebo (primary) | +0.466 | [+0.228, +0.704] | 55 / 7 | practical |
| retrieved_task − placebo (primary) | +0.447 | [+0.228, +0.666] | 50 / 4 | practical |
| mismatched_type-none | +0.505 | [+0.279, +0.731] | 57 / 5 | practical |
| placebo-none | +0.039 | [-0.228, +0.306] | 27 / 23 | inconclusive |
| retrieved_task-none | +0.485 | [+0.279, +0.692] | 52 / 2 | practical |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | practical | supported | developmental | +0.447 | [+0.228, +0.666] | `finding:3bc813b84285e09a` |
| mismatched_type | H2 (predicted null) | 1 | practical | refuted | developmental | +0.466 | [+0.228, +0.704] | `finding:9b1f6dbd939f9f74` |

## Caveats

- Format criteria used the pre-registered rule `imbalance_only`: a counter fails only if the arm − placebo difference exceeds its tolerance AND the 95% interval excludes 0. Under this rule an `unresolved` state means placebo neutrality was not shown, only not refuted.
- Counters pre-registered as behaviour, not as format failures (their imbalance does not flag a measurement problem): `invalid_no_action_tag`; see the process criteria table below.

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag | truncated | untagged_not_truncated |
|---|---|---|---|---|---|
| mismatched_type | 0.000 | 0.115 | 0.053 | 0.040 | 0.042 |
| none | 0.000 | 0.119 | 0.052 | 0.039 | 0.037 |
| placebo | 0.000 | 0.109 | 0.053 | 0.038 | 0.041 |
| retrieved_task | 0.000 | 0.137 | 0.056 | 0.031 | 0.032 |

### Process criteria (arm − placebo, per step)

| arm | counter | kind | tolerance | difference | 95% interval | state |
|---|---|---|---|---|---|---|
| mismatched_type | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| mismatched_type | `invalid_no_action_tag` | behaviour | 0.03 | -0.000 | [-0.014, +0.013] | balanced |
| mismatched_type | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | +0.001 | [-0.008, +0.011] | balanced |
| retrieved_task | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_task | `invalid_no_action_tag` | behaviour | 0.03 | +0.003 | [-0.009, +0.017] | balanced |
| retrieved_task | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.009 | [-0.018, +0.000] | balanced |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:8537c5ffbc9c45d3` (cycle 1): interim_look
- `decision:12d138052fd07410` (cycle 1): rules applied to the results
- `decision:3583e45fe83da950` (cycle 1): program finished

## Status of each direction

- mismatched_type: open
- retrieved_task: open

## Scope of the conclusions

The conclusions apply only to the task population `command-run:synthetic-early-stop-look1`, the arms ['retrieved_task', 'mismatched_type'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 103 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
