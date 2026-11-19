# Addendum: the secondary contrast `retrieved_task` − `mismatched_type` in ALFWORLD-LADDER-R4-V5B

Added 2026-11-19. Package: `data/lab/autolab-alfworld-ladder-r4-v5b/` (published bytes unchanged; they are pinned by
`PUBLISHED_FILES.json` and recomputed by `scripts/verify_autolab_packages.py`). This is an addition, not a correction of a number.

## What the package says

The README and the result's `secondary` field list three secondary contrasts, all against the no-memory baseline
(`retrieved_task−none`, `mismatched_type−none`, `placebo−none`). The two primary contrasts are against the placebo.

## What it omits

The private instrument note written before the measurement (`memory_build.md`, "Primary contrasts") states: "If the right
walkthrough helps more than any walkthrough, `retrieved_task − mismatched_type` > 0. That contrast is secondary." The package
leaves it out, although it is the direct test of "the right walkthrough vs any walkthrough".

## The contrast

Computed from `per_unit.csv` with the verifier's own functions (`paired_ci`, `interval_state` in
`scripts/verify_autolab_packages.py`), the same z as the published intervals of this result (`z` = 2.7777, the sequential
threshold of the second look), SESOI 0.12, first seed:

| contrast | n | gains / losses | difference | discordance | 95% interval | state |
|---|---:|---:|---:|---:|---|---|
| `retrieved_task` − `mismatched_type` | 201 | 55 / 24 | +0.154 | 0.393 | [+0.035, +0.273] | positive |

Sensitivity to the interval's z (same counts): fixed-sample family z 2.2414 gives [+0.058, +0.250]; z 1.96 gives
[+0.070, +0.238]. The state is `positive` in all three (lower bound above 0, below the 0.12 SESOI). It is not `practical`.

Reproduce (from the repository root):

```python
import csv, sys
from collections import defaultdict
sys.path.insert(0, "scripts")
import verify_autolab_packages as v
g = defaultdict(dict)
for r in csv.DictReader(open("data/lab/autolab-alfworld-ladder-r4-v5b/per_unit.csv", encoding="utf-8-sig")):
    g[r["unit"]][r["arm"]] = int(r["solved"])
gains = sum(a["retrieved_task"] == 1 and a["mismatched_type"] == 0 for a in g.values())
losses = sum(a["retrieved_task"] == 0 and a["mismatched_type"] == 1 for a in g.values())
print(len(g), gains, losses, v.paired_ci(gains, losses, len(g), 2.7777))
```

`tests/test_v5b_secondary_contrast.py` pins these numbers.

## How to read it

- **Secondary and post-hoc reported.** It was named as secondary before the measurement but was not computed or published with
  the result. It is not one of the two primary contrasts and it did not drive the stopping rule, which was based on the
  primary contrasts alone. The interval uses the primaries' z; it is not adjusted for a third contrast.
- **Same stopped dataset.** The 201 games are the ones the sequential rule had at its second look; the measurement stopped
  there. There are no new games and no new model runs. The interval inherits the caveat the package already carries: the
  executed sequential rule was not calibrated before the measurement.
- **Exposure is not balanced between the two arms.** Each arm shows two walkthroughs in each of 201 games, 402 uses. The
  `retrieved_task` arm used 227 distinct walkthroughs, and its ten most used account for 46 of 402 uses. The `mismatched_type`
  control used 141 distinct walkthroughs, and its ten most used account for 131 of 402 uses (two of them 24 uses each). Both
  counts are recomputed from the private raw file (`memory_sources`), which is pinned in `PROVENANCE.json` (`raw_sha256`); the
  public `per_unit.csv` only carries the number of sources. So the contrast compares goal-similar and varied content with
  unrelated and much more repeated content, and the control repeats a few walkthroughs across many games. A descriptive check:
  dropping the 97 games that were shown any of the control's ten most used walkthroughs leaves 104 games with 32 gains and 7
  losses (+0.240). This is a chosen subgroup, shown only to say the direction survives; it is not an estimate with an interval.
- **Not shown by this contrast.** It does not separate "choosing the right walkthrough" from "knowing the procedure of the
  task type" (that needs a same-type random control with balanced exposure), and it does not show an advantage over showing no
  memory (`retrieved_task−none` stays +0.109 [−0.007, +0.226], inconclusive).

## What does not change

The package, its two primary contrasts, the findings and their verdicts (H1 supported, H2 refuted, H3 supported, H4 refuted),
the code audit verdict (valid) and the direction status (`mismatched_type` closed, `retrieved_task` open).
