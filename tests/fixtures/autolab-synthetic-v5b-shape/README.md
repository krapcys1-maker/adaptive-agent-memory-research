**Status:** completed

# Lab program SYNTHETIC-V5B-SHAPE

**Question (owner):** Synthetic V5B-shaped package: does a retrieved walkthrough beat a token-matched placebo and a mismatched walkthrough?

Domain: `command-run`
Cycles: 1; role calls: 0; units: 120.

## Results (cycle 1, n = 120 units, 4 arms)

| arm | solved |
|---|---|
| mismatched_type | 0.46 |
| none | 0.44 |
| placebo | 0.43 |
| retrieved_task | 0.83 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| mismatched_type − placebo (primary) | +0.025 | [-0.120, +0.170] | 31 / 28 | inconclusive |
| retrieved_task − placebo (primary) | +0.400 | [+0.268, +0.532] | 58 / 10 | practical |
| mismatched_type-none | +0.017 | [-0.120, +0.153] | 27 / 25 | inconclusive |
| placebo-none | -0.008 | [-0.154, +0.137] | 29 / 30 | inconclusive |
| retrieved_task-none | +0.392 | [+0.262, +0.521] | 56 / 9 | practical |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | practical | supported | developmental | +0.400 | [+0.268, +0.532] | `finding:de80c241f8c2275d` |
| mismatched_type | H2 (predicted null) | 1 | inconclusive | inconclusive | developmental | +0.025 | [-0.120, +0.170] | `finding:7faec13a258c7b28` |

## Caveats

- Measurement problem: process: untagged_not_truncated per step, arm − placebo +0.101 [+0.085, +0.118] > 0.03 (pre-registered criterion) — content and format/process effects are not separated
- Format criteria used the pre-registered rule `imbalance_only`: a counter fails only if the arm − placebo difference exceeds its tolerance AND the 95% interval excludes 0. Under this rule an `unresolved` state means placebo neutrality was not shown, only not refuted.
- Counters pre-registered as behaviour, not as format failures (their imbalance does not flag a measurement problem): `invalid_no_action_tag`; see the process criteria table below.

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag | mismatched_length_diff | truncated | untagged_not_truncated |
|---|---|---|---|---|---|---|
| mismatched_type | 0.000 | 0.123 | 0.056 | -0.203 | 0.040 | 0.138 |
| none | 0.000 | 0.127 | 0.058 | 0.000 | 0.038 | 0.037 |
| placebo | 0.000 | 0.124 | 0.057 | 0.000 | 0.036 | 0.037 |
| retrieved_task | 0.000 | 0.116 | 0.123 | 0.000 | 0.038 | 0.034 |

### Process criteria (arm − placebo, per step)

| arm | counter | kind | tolerance | difference | 95% interval | state |
|---|---|---|---|---|---|---|
| mismatched_type | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| mismatched_type | `invalid_no_action_tag` | behaviour | 0.03 | -0.001 | [-0.013, +0.010] | balanced |
| mismatched_type | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | +0.101 | [+0.085, +0.118] | imbalanced |
| retrieved_task | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_task | `invalid_no_action_tag` | behaviour | 0.03 | +0.066 | [+0.050, +0.083] | imbalanced |
| retrieved_task | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.003 | [-0.011, +0.005] | balanced |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:eda00a5ddeb35754` (cycle 1): rules applied to the results
- `decision:f870eec20148f544` (cycle 1): program finished

## Status of each direction

- mismatched_type: measurement_problem — measurement problem, so neither established nor closed
- retrieved_task: open

## Scope of the conclusions

The conclusions apply only to the task population `command-run:synthetic-v5b-shape`, the arms ['retrieved_task', 'mismatched_type'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 120 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
