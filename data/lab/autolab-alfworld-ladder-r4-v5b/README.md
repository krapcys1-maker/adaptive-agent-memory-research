**Status:** completed

# Lab program ALFWORLD-LADDER-R4-V5B

**Question (owner):** Does showing the 4B agent two goal-similar expert ALFWorld walkthroughs (rung 4), or two length-matched walkthroughs of unrelated task types, raise the solve rate on fresh held-out train games above a token-matched placebo block?

Domain: `command-run`
Cycles: 1; role calls: 12; units: 300.

## Results (cycle 1, n = 201 units, 4 arms)

| arm | solved |
|---|---|
| mismatched_type | 0.46 |
| none | 0.51 |
| placebo | 0.45 |
| retrieved_task | 0.62 |

| comparison | difference | 95% interval | gains / losses | state |
|---|---|---|---|---|
| mismatched_type − placebo (primary) | +0.015 | [-0.067, +0.097] | 19 / 16 | equivalent |
| retrieved_task − placebo (primary) | +0.169 | [+0.053, +0.285] | 55 / 21 | positive |
| mismatched_type-none | -0.045 | [-0.135, +0.045] | 17 / 26 | inconclusive |
| placebo-none | -0.060 | [-0.157, +0.037] | 19 / 31 | inconclusive |
| retrieved_task-none | +0.109 | [-0.007, +0.226] | 48 / 26 | inconclusive |

## Findings (negative ones included)

| arm | hypothesis | cycle | state | verdict | level | difference | interval | id |
|---|---|---|---|---|---|---|---|---|
| retrieved_task | H1 (predicted positive) | 1 | positive | supported | developmental | +0.169 | [+0.053, +0.285] | `finding:8650d1bf0b553d97` |
| retrieved_task | H2 (predicted null) | 1 | positive | refuted | developmental | +0.169 | [+0.053, +0.285] | `finding:6e0dffcd862d0e98` |
| mismatched_type | H3 (predicted null) | 1 | equivalent | supported | developmental | +0.015 | [-0.067, +0.097] | `finding:825927fef33cb839` |
| mismatched_type | H4 (predicted positive) | 1 | equivalent | refuted | developmental | +0.015 | [-0.067, +0.097] | `finding:1acdf20f0a871e4b` |

## Caveats

- Measured although the reviewers' only remaining objection was statistical power (risk of an inconclusive result).
- Early check after the first chunk flagged: retrieved_task: untagged_not_truncated per step, arm − placebo -0.048 [-0.089, -0.006]
- The registered calibration (power at SESOI 0.857) describes a single-look rule with threshold z = 2.2414; the executed rule had interim looks at [0.34, 0.67] with thresholds [3.8992, 2.7777, 2.2736] and could stop early once every primary comparison was decided. The power of the executed sequential rule was not calibrated before the measurement.
- Format criteria used the pre-registered rule `imbalance_only`: a counter fails only if the arm − placebo difference exceeds its tolerance AND the 95% interval excludes 0. Under this rule an `unresolved` state means placebo neutrality was not shown, only not refuted.
- Counters pre-registered as behaviour, not as format failures (their imbalance does not flag a measurement problem): `invalid_no_action_tag`; see the process criteria table below.

## Measurement checks (per step, by arm)

| arm | empty_retries | invalid_actions | invalid_no_action_tag | min_tokens | overlap_with_retrieved | truncated | untagged_not_truncated |
|---|---|---|---|---|---|---|---|
| mismatched_type | 0.000 | 0.218 | 0.095 | 0.218 | 0.000 | 0.046 | 0.050 |
| none | 0.000 | 0.135 | 0.048 | 0.216 | 0.000 | 0.035 | 0.013 |
| placebo | 0.000 | 0.194 | 0.097 | 0.209 | 0.000 | 0.036 | 0.062 |
| retrieved_task | 0.000 | 0.266 | 0.112 | 0.283 | 0.000 | 0.063 | 0.049 |

### Process criteria (arm − placebo, per step)

| arm | counter | kind | tolerance | difference | 95% interval | state |
|---|---|---|---|---|---|---|
| mismatched_type | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| mismatched_type | `invalid_no_action_tag` | behaviour | 0.03 | -0.002 | [-0.018, +0.014] | balanced |
| mismatched_type | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.012 | [-0.024, -0.001] | balanced |
| retrieved_task | `empty_retries` | criterion (imbalance_only) | 0.03 | +0.000 | [+0.000, +0.000] | balanced |
| retrieved_task | `invalid_no_action_tag` | behaviour | 0.03 | +0.015 | [-0.004, +0.033] | unresolved |
| retrieved_task | `untagged_not_truncated` | criterion (imbalance_only) | 0.03 | -0.013 | [-0.025, -0.001] | balanced |

Code audit verdict: **valid** (completeness, recomputation, leakage, raw-data integrity).

## Decisions

- `decision:3bfeb411f5f5871f` (cycle 1): measured despite a power-only objection
- `decision:adbc92ccde39102d` (cycle 1): interim_look
- `decision:a8c8fc34aa967426` (cycle 1): interim_look
- `decision:f4717ebfa4a5b874` (cycle 1): rules applied to the results
- `decision:bf0ee421f9766340` (cycle 1): program finished

## Status of each direction

- mismatched_type: closed
- retrieved_task: open

## Scope of the conclusions

The conclusions apply only to the task population `command-run:alfworld-ladder-r4-v5b`, the arms ['mismatched_type', 'retrieved_task'] against the placebo `placebo`, the measurement conditions of the envelope and the scale of 201 units in 1 run(s). Do not generalise to other tasks, models, prompts or scales.

Reviewer and auditor notes that did not change the protocol: 30 (in `knowledge.jsonl`, kind `discussion`).

Per-task records (one row per task × arm × seed: solved, steps, empty and untagged answers, memory tokens, the counters required by the protocol; an empty cell = not reported, not zero): `per_unit.csv`. The raw episode logs stay private.

All numbers were computed by the lab's code from the raw data; model roles only proposed and criticised.
Provenance: `knowledge.jsonl` + `PROVENANCE.json`; check with `python verify_provenance.py knowledge.jsonl`.
