# Public-data reanalysis of ALFWORLD-LADDER-R4-V5B

Contribution for issue #230 (`community_task:14a80dc5561ab183`).
The [public per-unit CSV](../../lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv)
is the input for all computed results. The [published V5B report](../../lab/autolab-alfworld-ladder-r4-v5b/README.md)
supplies the comparison values in the columns marked **Published report** in
section 1 and the stopping-look critical value used in the recomputation.
All numeric findings in sections 2–6 are computed from the CSV.
The script uses Python's standard library and runs without a GPU or inference calls.
Input SHA-256: `a7466cfd73fcfe0e64c157678d09903d7600d4fda45cccec12e3a0eb21c78471`.
An optional positional argument selects another path to the same CSV.

## How to rerun

```bash
python data/contrib/2018cx-alfworld-ladder-r4-v5b-reanalysis/reanalysis.py
```

## 1. Replication of the published numbers

The **Published report** columns transcribe the V5B results table. The
**Computed from CSV** columns are the script's independently recomputed values,
shown to four decimals for differences.

| Comparison | Difference (Published report) | Difference (Computed from CSV) | Gains/losses (Published report) | Gains/losses (Computed from CSV) |
|---|---|---|---|---|
| mismatched_type − placebo | +0.015 | +0.0149 | 19/16 | 19/16 |
| retrieved_task − placebo | +0.169 | +0.1692 | 55/21 | 55/21 |
| mismatched_type − none | −0.045 | −0.0448 | 17/26 | 17/26 |
| placebo − none | −0.060 | −0.0597 | 19/31 | 19/31 |
| retrieved_task − none | +0.109 | +0.1095 | 48/26 | 48/26 |

The script recomputes the two primary intervals using the lab's paired Wald
formula and the stopping-look critical value from the published report
(`z = 2.7777`). Both intervals agree at the report's precision.

| Primary comparison | Interval (Published report) | Interval (Computed from CSV) |
|---|---|---|
| mismatched_type − placebo | [-0.067, +0.097] | [-0.067, +0.097] |
| retrieved_task − placebo | [+0.053, +0.285] | [+0.053, +0.285] |

Data checks computed from the CSV found 804 rows, 201 unique units, each with exactly the four arms,
seed 0, cycle 1, and a binary solve outcome. All 804 error flags are zero.

## 2. Placebo token matching

Per unit, placebo and retrieved memory-token counts differ by a mean of 2.1
tokens (max 5), or 0.27% on average (max 0.97%, using the larger arm count as the
denominator). For placebo versus mismatched, the mean absolute gap is 9.6
tokens (max 186; mean relative 1.03%, max 15.97%). These are memory-block token
counts. The match leaves differences in example content and presentation open.

## 3. New finding: the effect is concentrated in a subset of task types

`retrieved_task − placebo` decomposed by task type (task type parsed from the unit id,
`~train/<type>-...`):

| task type | n | diff | 95% CI (unadjusted) | g/l |
|---|---|---|---|---|
| pick_clean_then_place_in_recep | 41 | +0.366 | [+0.202, +0.530] | 16/1 |
| pick_cool_then_place_in_recep | 35 | +0.257 | [+0.039, +0.475] | 13/4 |
| look_at_obj_in_light | 30 | +0.233 | [+0.053, +0.414] | 8/1 |
| pick_heat_then_place_in_recep | 38 | +0.132 | [−0.080, +0.343] | 11/6 |
| pick_and_place_simple | 28 | +0.036 | [−0.087, +0.158] | 2/1 |
| pick_two_obj_and_place | 29 | −0.103 | [−0.348, +0.142] | 5/8 |

Cleaning, cooling and light inspection account for 31 of the 34 net gains.
The two-object task has a negative point estimate. By goal object, among objects
with at least eight units, estimates range from +0.364 (Egg, n=11) to 0.000
(Apple, n=10 and Plate, n=9). The CSV lacks the original goal wording.
These unadjusted subgroup intervals are exploratory.

## 4. Episode length and action counters in gain/loss pairs

Means of the episode totals, with each cell showing placebo → retrieved:

| Measure | Gains (n=55) | Losses (n=21) |
|---|---|---|
| steps | 50.00 → 16.56 | 31.57 → 50.00 |
| invalid_actions | 12.62 → 2.87 (**−9.75**) | 3.76 → 17.33 (**+13.57**) |
| invalid_no_action_tag | 5.67 → 1.27 (−4.40) | 1.86 → 7.43 (+5.57) |
| untagged_not_truncated | 3.56 → 0.69 (−2.87) | 0.90 → 2.48 (+1.57) |
| truncated | 2.13 → 0.58 (−1.55) | 1.00 → 5.00 (+4.00) |
| empty_retries | 0.00 → 0.00 | 0.00 → 0.00 |

The unsuccessful arm used the full 50-step budget in both groups. The counter
totals mix episode duration with action quality, and the groups are selected on
the observed outcome. The CSV cannot establish an action-format mechanism.
A format-only exemplar arm, matched in length to a task-relevant exemplar,
would directly test that explanation on new games.

## 5. Sensitivity of process rates to task weighting

Across all 201 pairs, placebo contributes 7,700 steps and retrieved contributes
5,687. The lab's pooled rate divides each arm's total event count by its total
steps, giving more weight to longer episodes. An equal-task rate first divides
the event count by steps within each episode, then averages those episode rates
with each task weighted equally. All differences are retrieved minus placebo.

| Counter | Step-weighted difference (pp) | Equal-task difference (pp) | Equal-task 95% interval (pp) |
|---|---:|---:|---:|
| `invalid_no_action_tag` | +1.47 | -0.11 | [-1.71, +1.47] |
| `invalid_actions` | +7.14 | +1.82 | [-1.30, +5.00] |

Intervals are exploratory percentile intervals from 10,000 bootstrap samples
at seed 20261116, resampling whole paired tasks. The near-zero equal-task
estimate for `invalid_no_action_tag` shows that its direction depends on the
weighting. The step-weighted rate describes an observed step, and the
equal-task rate describes the average episode-level fraction. Episode length
can itself respond to the intervention, so both estimands describe observed
episode behaviour. This sensitivity analysis concerns the process counters.
The solve-rate contrast is already computed per paired task.

## 6. Scope of the leakage check

- `overlap_with_retrieved` is populated for the 201 mismatched rows and is zero throughout.
- `memory_similarity` is populated for retrieved and mismatched (201 rows each).
  Across those 402 rows, 201 values are nonzero.
- `top1_similarity` is populated and nonzero for all 804 rows.

The overlap field checks only the reported comparison. The raw trajectories
and source identities are unavailable in this table, so it cannot establish
absence of leakage or verify the original execution.

## Contribution

Prepared by @2018cx for #230 using WorkBuddy and Codex assistance. Suggested
CRediT roles are Formal analysis and Validation (recomputation of the published
per-unit table).
