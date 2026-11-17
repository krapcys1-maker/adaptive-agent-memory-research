**Status:** completed

# Lab program ALFWORLD-LADDER-R4-V4

**Question (owner):** Does showing the 4B agent two expert ALFWorld walkthroughs retrieved by goal similarity (ladder rung 4) raise the solve rate on held-out train games (families disjoint from the bank) above a token-matched placebo block and above no memory?

Domain: `command-run`
Cycles: 1; role calls: 9; units: 300.

## Results (cycle 1, n = 300 units, 3 arms)

| arm | solved |
|---|---|
| none | 0.47 |
| placebo | 0.45 |
| retrieved_task | 0.69 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| retrieved_task − placebo (primary) | +0.240 | [+0.177, +0.303] | 91 / 19 | practical |
| placebo-none | -0.023 | [-0.071, +0.024] | 23 / 30 | equivalent |
| retrieved_task-none | +0.217 | [+0.155, +0.278] | 84 / 19 | practical |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | practical | supported | developmental | +0.240 | [+0.177, +0.303] | `finding:00fa0192dfd13db2` |
| retrieved_task | H2 (predicted null) | 1 | practical | refuted | developmental | +0.240 | [+0.177, +0.303] | `finding:102266bf120db7a3` |
| retrieved_task | H3 (predicted positive) | 1 | practical | supported | developmental | +0.240 | [+0.177, +0.303] | `finding:e7402eac3345ea88` |

## Caveats

- Early check after the first chunk flagged: retrieved_task: invalid_no_action_tag per step, arm − placebo +0.038 [+0.012, +0.065]
- The measurement was interrupted by an infrastructure failure (a batch orphaned by a killed worker blocked the output file); the saved records were kept and only the missing tasks were run again.
- Measurement problem: process: invalid_no_action_tag per step, arm − placebo +0.034 [+0.014, +0.053] > 0.03 (pre-registered criterion) — content and format/process effects are not separated

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag | min_tokens |
|---|---|---|---|---|
| none | 0.000 | 0.176 | 0.090 | 0.221 |
| placebo | 0.000 | 0.195 | 0.099 | 0.217 |
| retrieved_task | 0.000 | 0.291 | 0.133 | 0.307 |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:83dcca42c4a4e619` (cycle 1): halted
- `decision:e72b3101363cdf00` (cycle 1): measurement resumed after an infrastructure failure
- `decision:0131f1264acf30d0` (cycle 1): rules applied to the results
- `decision:ead369c0349576ad` (cycle 1): program finished
- `decision:2c2134600713c5d7` (cycle 1): reexport_after_false_hold

## Status of each direction

- retrieved_task: measurement_problem — measurement problem, so neither established nor closed

## Scope of the conclusions

The conclusions apply only to the task population `command-run:alfworld-ladder-r4-v4-train`, the arms ['retrieved_task'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 300 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Reviewer and auditor notes that did not change the protocol: 24 (in `knowledge.jsonl`, kind `discussion`).

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
