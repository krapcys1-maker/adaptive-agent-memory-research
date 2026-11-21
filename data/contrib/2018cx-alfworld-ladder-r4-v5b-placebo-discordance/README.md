# V5B placebo comparison by three-arm solve outcome

The [published V5B report](../../lab/autolab-alfworld-ladder-r4-v5b/README.md)
compares placebo with no memory. We recompute that comparison and show how
the two baselines relate to the retrieved arm on the same tasks. This follows
the [suggestion on PR #239](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/239#issuecomment-7028240898).

## Reproduce

From the repository root, run:

```sh
python data/contrib/2018cx-alfworld-ladder-r4-v5b-placebo-discordance/placebo_discordance.py
```

The script uses only the standard library and the
[public V5B per-unit CSV](../../lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv).
It pairs outcomes by cycle, task and seed. All counts below are computed from
the CSV. The paired Wald intervals use the report's stopping-look critical
value of 2.7777.

## Paired contrasts

| Contrast | Difference in solve rate | Interval | Gains / losses |
|---|---:|---|---:|
| Placebo minus none | −0.060 | [−0.157, +0.037] | 19 / 31 |
| Retrieved minus placebo | +0.169 | [+0.053, +0.285] | 55 / 21 |
| Retrieved minus none | +0.109 | [−0.007, +0.226] | 48 / 26 |

All three rows reproduce the published contrasts at the report's precision.
Placebo and none disagree on 50 of 201 tasks, with 19 gains and 31 losses for
placebo. The placebo-minus-none interval spans zero and allows a decrease of
up to 15.7 percentage points. The report classifies the contrast as
inconclusive.

## Joint solve patterns

Each row reports the number of tasks with the listed outcome in each arm
(1 = solved).

| None | Placebo | Retrieved | Tasks |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 43 |
| 0 | 0 | 1 | 37 |
| 0 | 1 | 0 | 8 |
| 0 | 1 | 1 | 11 |
| 1 | 0 | 0 | 13 |
| 1 | 0 | 1 | 18 |
| 1 | 1 | 0 | 13 |
| 1 | 1 | 1 | 58 |

Of the 55 retrieved gains against placebo, **37 failed under both controls**
and **18 were already solved under none**. Of the 21 retrieved losses against
placebo, 13 also fail against none and 8 are specific to the placebo comparison.
Eleven tasks solved by both retrieved and placebo also fail under none, so
they contribute gains only to the retrieved-minus-none comparison. Thirteen
tasks solved only under none contribute losses only to that comparison.

These are descriptive counts from one outcome per task and arm in the stopped
V5B sample. The joint patterns do not estimate repeat-run stability or
identify which prompt component caused any particular outcome.

Prepared by @2018cx with Codex assistance.
