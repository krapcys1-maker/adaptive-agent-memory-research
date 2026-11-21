**Status:** completed

# Lab program ALFWORLD-LADDER-R4-V6

**Question (owner):** With retrieval held fixed (the same two goal-similar expert walkthroughs), does the 4B agent's solve rate on fresh held-out train games rise above a token-matched placebo block when the walkthroughs are shown in full (V5B replication), as their actions only, or as an abstract subgoal plan without numbers and room-specific locations?

Domain: `command-run`
Cycles: 1; role calls: 12; units: 300.

## Results (cycle 1, n = 300 units, 5 arms)

| arm | solved |
|---|---|
| none | 0.53 |
| placebo | 0.48 |
| retrieved_plan | 0.61 |
| retrieved_steps | 0.61 |
| retrieved_task | 0.61 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| retrieved_plan − placebo (primary) | +0.130 | [+0.060, +0.200] | 60 / 21 | positive |
| retrieved_steps − placebo (primary) | +0.137 | [+0.055, +0.219] | 75 / 34 | positive |
| retrieved_task − placebo (primary) | +0.130 | [+0.049, +0.211] | 72 / 33 | positive |
| placebo-none | -0.057 | [-0.122, +0.009] | 25 / 42 | inconclusive |
| retrieved_plan-none | +0.073 | [+0.002, +0.145] | 51 / 29 | positive |
| retrieved_steps-none | +0.080 | [+0.000, +0.160] | 62 / 38 | positive |
| retrieved_task-none | +0.073 | [-0.009, +0.156] | 64 / 42 | inconclusive |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | positive | supported | developmental | +0.130 | [+0.049, +0.211] | `finding:74f6b5bd1be13ffe` |
| retrieved_steps | H2 (predicted positive) | 1 | positive | supported | developmental | +0.137 | [+0.055, +0.219] | `finding:a0e419ca1cccd13d` |
| retrieved_plan | H3 (predicted null) | 1 | positive | refuted | developmental | +0.130 | [+0.060, +0.200] | `finding:d6883ff01a9b6a61` |

## Caveats

- Measured although the reviewers' only remaining objection was statistical power (risk of an inconclusive result).
- Early check after the first chunk flagged: retrieved_plan: untagged_not_truncated per step, arm − placebo +0.041 [+0.021, +0.058]
- Measurement problem: process: untagged_not_truncated per step, arm − placebo +0.042 [+0.032, +0.052] > 0.03 (pre-registered criterion) — content and format/process effects are not separated
- Format criteria used the pre-registered rule `imbalance_only`: a counter fails only if the arm − placebo difference exceeds its tolerance AND the 95% interval excludes 0. Under this rule an `unresolved` state means placebo neutrality was not shown, only not refuted.
- Counters pre-registered as behaviour, not as format failures (their imbalance does not flag a measurement problem): `invalid_no_action_tag`; see the process criteria table below.

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag | truncated | untagged_not_truncated |
|---|---|---|---|---|---|
| none | 0.000 | 0.133 | 0.053 | 0.040 | 0.013 |
| placebo | 0.000 | 0.197 | 0.091 | 0.039 | 0.053 |
| retrieved_plan | 0.000 | 0.214 | 0.138 | 0.043 | 0.095 |
| retrieved_steps | 0.000 | 0.271 | 0.122 | 0.075 | 0.049 |
| retrieved_task | 0.000 | 0.322 | 0.116 | 0.067 | 0.050 |

### Process criteria (arm − placebo, per step)

| arm | counter | kind | tolerance | difference | 95% interval | state |
|---|---|---|---|---|---|---|
| retrieved_plan | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_plan | `invalid_no_action_tag` | behaviour | 0.03 | +0.047 | [+0.033, +0.061] | imbalanced |
| retrieved_plan | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | +0.042 | [+0.032, +0.052] | imbalanced |
| retrieved_steps | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_steps | `invalid_no_action_tag` | behaviour | 0.03 | +0.032 | [+0.015, +0.047] | imbalanced |
| retrieved_steps | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.003 | [-0.013, +0.006] | balanced |
| retrieved_task | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_task | `invalid_no_action_tag` | behaviour | 0.03 | +0.025 | [+0.011, +0.039] | unresolved |
| retrieved_task | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.003 | [-0.014, +0.007] | balanced |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

Instrument sensitivity: oracle − placebo = +0.283, n = 60 (passed) — a positive control of the instrument, not a finding (details: `sensitivity.json`).

## Per-episode metrics (mean by arm)

| arm | block_length_diff | content_tokens | matched_block_tokens | memory_similarity | memory_tokens | plan_digit_count | steps | steps_observation_count | tokens | top1_similarity |
|---|---|---|---|---|---|---|---|---|---|---|
| none | — | — | — | — | 0.000 | — | 35.270 | — | 69789.127 | 0.771 |
| placebo | 0.000 | 0.000 | 799.860 | — | 800.083 | — | 36.613 | — | 100065.093 | 0.771 |
| retrieved_plan | 0.002 | 112.290 | 799.860 | 0.693 | 801.237 | 0.000 | 31.757 | — | 82882.963 | 0.771 |
| retrieved_steps | 0.001 | 197.050 | 799.860 | 0.693 | 800.347 | — | 28.933 | 0.000 | 80327.137 | 0.771 |
| retrieved_task | 0.000 | 719.860 | 799.860 | 0.693 | 799.860 | — | 28.530 | — | 78265.987 | 0.771 |

## Decisions

- `decision:c777467816789756` (cycle 1): measured despite a power-only objection
- `decision:4171c4f997e6331e` (cycle 1): interim_look
- `decision:4d44a4210db6bee5` (cycle 1): interim_look
- `decision:f58f426a2450b7c9` (cycle 1): rules applied to the results
- `decision:7daadd7e97dfc8e4` (cycle 1): program finished
- `decision:2c1251b0dce7fe18` (cycle 1): halted
- `decision:fcff62eeea52bccf` (cycle 1): export retried
- `decision:c28631d459998692` (cycle 1): export retried
- `decision:7f46de322dd62498` (cycle 1): export retried
- `decision:718c3015fd156293` (cycle 1): resume_export

## Status of each direction

- retrieved_plan: measurement_problem — measurement problem, so neither established nor closed
- retrieved_steps: open
- retrieved_task: open

## Scope of the conclusions

The conclusions apply only to the task population `command-run:alfworld-ladder-r4-v6`, the arms ['retrieved_plan', 'retrieved_steps', 'retrieved_task'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 300 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Reviewer and auditor notes that did not change the protocol: 22 (in `knowledge.jsonl`, kind `discussion`).

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens, the counters required by the protocol; an empty cell = not reported, not zero): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
