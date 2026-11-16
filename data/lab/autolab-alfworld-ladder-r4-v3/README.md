**Status:** completed

# Lab program ALFWORLD-LADDER-R4-V3

**Question (owner):** Does showing the 4B agent two expert ALFWorld walkthroughs retrieved by goal similarity (ladder rung 4) raise the solve rate on valid_seen games above a token-matched placebo block and above no memory?

Domain: `command-run`
Cycles: 1; role calls: 10; units: 100.

## Results (cycle 1, n = 100 units, 3 arms)

| arm | solved |
|---|---|
| none | 0.44 |
| placebo | 0.57 |
| retrieved_task | 0.64 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| retrieved_task − placebo (primary) | +0.070 | [-0.042, +0.182] | 20 / 13 | inconclusive |
| placebo-none | +0.130 | [+0.040, +0.220] | 18 / 5 | positive |
| retrieved_task-none | +0.200 | [+0.082, +0.318] | 30 / 10 | positive |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | inconclusive | inconclusive | developmental | +0.070 | [-0.042, +0.182] | `finding:d1724ed63afb7231` |
| retrieved_task | H2 (predicted null) | 1 | inconclusive | inconclusive | developmental | +0.070 | [-0.042, +0.182] | `finding:f631c79c88cf79ff` |
| retrieved_task | H3 (predicted null) | 1 | inconclusive | inconclusive | developmental | +0.070 | [-0.042, +0.182] | `finding:29436466f00a5506` |

## Caveats

- Measured although the reviewers' only remaining objection was statistical power (risk of an inconclusive result).
- Post-hoc annotation (code check added after this run): the placebo was not a neutral control. It almost removed empty model answers (empty retries per step: placebo 0.001, memory 0.582, no memory 0.743). The format criterion fixed before the run (untagged answers per step, memory − placebo ≤ 0.03 or a 95% bootstrap interval that includes 0) FAILED: +0.115 [+0.081, +0.147]. Content and format are therefore not separated, and both placebo − none and memory − placebo are hard to read. Cause and fix (identical for all arms: vLLM min_tokens = 8) are tested in the follow-up program ALFWORLD-LADDER-R4-V4.

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag |
|---|---|---|---|
| none | 0.743 | 0.250 | 0.172 |
| placebo | 0.001 | 0.146 | 0.062 |
| retrieved_task | 0.582 | 0.290 | 0.177 |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:21269e9fdc2c624c` (cycle 1): measured despite a power-only objection
- `decision:0ab1da31abb3a265` (cycle 1): rules applied to the results
- `decision:b3c9f02a55ae9f22` (cycle 1): program finished
- `decision:f78b66f058f44505` (cycle 1): halted
- `decision:1f11ae095279f30c` (cycle 1): export retried
- `decision:8217e0d0b14f4f97` (cycle 1): annotation added after the result — Post-hoc annotation (code check added after this run): the placebo was not a neutral control. It almost removed empty model answers (empty retries per step: placebo 0.001, memory 0.582, no memory 0.743). The format criterion fixed before the run (untagged answers per step, memory − placebo ≤ 0.03 or a 95% bootstrap interval that includes 0) FAILED: +0.115 [+0.081, +0.147]. Content and format are therefore not separated, and both placebo − none and memory − placebo are hard to read. Cause and fix (identical for all arms: vLLM min_tokens = 8) are tested in the follow-up program ALFWORLD-LADDER-R4-V4.

## Status of each direction

- retrieved_task: measurement_problem — measurement problem, so neither established nor closed

## Scope of the conclusions

The conclusions apply only to the task population `command-run:alfworld-ladder-r4-v3`, the arms ['retrieved_task'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 100 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Reviewer and auditor notes that did not change the protocol: 17 (in `knowledge.jsonl`, kind `discussion`).

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
