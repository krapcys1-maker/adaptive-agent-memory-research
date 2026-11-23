# Addendum: a seed-1 re-run of the primary contrast and the D8 instruction arm on the ALFWORLD-LADDER-R4-V6 games

Added 2026-11-23. Package: `data/lab/autolab-alfworld-ladder-r4-v6/` (published bytes unchanged; they are pinned by
`PUBLISHED_FILES.json` and recomputed by `scripts/verify_autolab_packages.py`). This is an addition, not a correction of a
number. Nothing here changes the package's results, findings, verdicts, direction status or caveats.

Two follow-up runs used the V6 games after V6 had finished. Both are **exploratory side runs outside the lab pipeline**:
they are not lab programs, have no envelope, instrument review, positive control or code audit, and do not produce lab
verdicts. Each had a rule written before its data. The rules are not published and have no external registry record; the
evidence that they preceded the data is their file times (and their SHA-256 below). Both were run and first analysed by a session of the
project's automated coordinator. Every number below was then recomputed for this addendum by a second script, written
without importing the first one, from the per-episode outputs and from the published `per_unit.csv`; all of them agree
with the runs' own result files. The second script was written by a model of the same family (Claude), so this is a
recomputation, not an independent-model review. No second-model check was done of the quantities that are new in this
addendum (the Newcombe intervals of the D8 contrasts and the two-seed t-intervals).

The per-episode outputs of both runs are not published (they hold the full action logs). Their SHA-256 sums are listed at
the end. The seed-0 numbers can be recomputed from the public `per_unit.csv`; the seed-1 and D8 numbers cannot be
recomputed from this repository.

## 1. The primary contrast at a second seed

### What was run

- **Arms:** `placebo` and `retrieved_task`, the two arms of V6's primary contrast for full walkthroughs. `none`,
  `retrieved_steps` and `retrieved_plan` were not re-run.
- **Games and instrument:** the same 300 V6 games, with a byte-identical copy of the V6 instrument. The SHA-256 of
  `agent.py`, `run_episode.sh`, `vllm_serve.sh`, `bank.jsonl`, `units.json` and `families.json` equal the pins in the
  package's `knowledge.jsonl`. Same model (`Qwen/Qwen3-4B-Instruct-2507-FP8`), temperature 0.7, `min_tokens` 8, 50 steps,
  format reminder on (checked in all 600 records).
- **Seed 1.** The seed changes the model's sampling and also the tie-break among equally similar bank entries. The shown
  walkthroughs therefore differ from seed 0 in many games. The public `per_unit.csv` does not list the sources, so the
  check uses a proxy: DS-HARD-1 (see [the side-studies note](../side-studies-2026-11.md)) ran the same agent and bank at
  seed 0, so its `retrieved_task` sources are the V6 seed-0 picks. On the 195 games both runs share, the seed-1 pair was
  the same set of two walkthroughs in 69 games, and at least one walkthrough was shared in 166.
- **When:** 2026-11-21 23:40 to 2026-11-22 14:58 UTC, on the lab's GPU, after V6 had finished. V6's objects in `knowledge.jsonl` are dated 2026-11-19
  to 2026-11-21 (its run record 2026-11-21 05:14 UTC). The seed-1 episodes were not interleaved with V6's and not
  randomised together with them. 600 episodes, 0 errors, 0 duplicates, no exclusions.
- **Rule written before data** (2026-11-21; evidence: file times): if seed 1 gives `retrieved_task − placebo` ≥ +0.05, the seed-0 result is
  described as stable across two seeds; ≤ 0, not stable; in between, weaker but same sign. The rule also fixed the
  transform / other split and the two-seed estimate below.

**What to call it.** This is a seed re-run of the same protocol on the same games, bank, model and machine: a consistency
check of the V6 primary contrast under new sampling and a partly new choice of walkthroughs. It is not an independent
replication (new games, a new bank, another model or another lab would each be needed for that).

### Results

Paired over games; gains / losses = games solved only with `retrieved_task` / only with `placebo`; exact two-sided McNemar
test on the discordant pairs. The seed-0 rows are recomputed from the published `per_unit.csv`.

| games | n | seed | `placebo` | `retrieved_task` | difference | gains / losses | McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 300 | 0 | 0.477 | 0.607 | +0.130 | 72 / 33 | 0.0002 |
| all | 300 | 1 | 0.457 | 0.613 | +0.157 | 78 / 31 | 7.7e-06 |
| transform (clean / cool / heat) | 151 | 0 | 0.404 | 0.649 | +0.245 | 50 / 13 | 3.0e-06 |
| transform (clean / cool / heat) | 151 | 1 | 0.371 | 0.642 | +0.272 | 53 / 12 | 2.8e-07 |
| other | 149 | 0 | 0.550 | 0.564 | +0.013 | 22 / 20 | 0.88 |
| other | 149 | 1 | 0.544 | 0.584 | +0.040 | 25 / 19 | 0.45 |

**Reading under the rule written before data:** seed 1 gives +0.157 ≥ +0.05, so the seed-0 result (+0.130) is described as
**stable across two seeds**.

**Two-seed estimate.** Per game, the mean of seeds 0 and 1 for each arm; then the paired difference and a 95% t-interval
over the games (the game is the unit, so the two seeds are not counted as independent games):

| games | n | `placebo` | `retrieved_task` | difference | 95% interval (t, over games) |
|---|---:|---:|---:|---:|---|
| all | 300 | 0.467 | 0.610 | +0.143 | [+0.090, +0.196] |
| transform | 151 | 0.387 | 0.646 | +0.258 | [+0.180, +0.337] |
| other | 149 | 0.547 | 0.574 | +0.027 | [−0.040, +0.094] |

**Net games gained by task type** (games solved only with `retrieved_task` minus games solved only with `placebo`;
descriptive, a split chosen after the data):

| task type | games | net, seed 0 | net, seed 1 |
|---|---:|---:|---:|
| `pick_clean` | 53 | 12 | 12 |
| `pick_cool` | 49 | 15 | 24 |
| `pick_heat` | 49 | 10 | 5 |
| `look_at` | 50 | 7 | 4 |
| `pick_and_place` | 46 | 0 | 2 |
| `pick_two` | 53 | −5 | 0 |
| all | 300 | 39 | 47 |

**Agreement between seeds, game by game** (planning inputs for multi-seed programs): phi of `solved` between seed 0 and
seed 1 is 0.585 for `placebo` and 0.468 for `retrieved_task`; the correlation of the per-game difference
(`retrieved_task` − `placebo`) between the seeds is 0.297.

### How to read it

- **The interval of record stays the package's.** V6's published interval for this contrast, +0.130 [+0.049, +0.211],
  is a paired sequential interval at the final look (z = 2.4166) and carries the lab's state and direction status. The
  two-seed interval above is a fixed-sample t-interval computed outside the lab's rules. It is not a lab verdict and is
  not directly comparable with the sequential interval. Its lower bound (+0.090) is below the lab's SESOI of 0.12, so even
  on this reading the estimate would not be `practical`.
- **What the two seeds can and cannot show.** With 300 games the two-seed interval is about ±0.053 wide, so a true gain
  of a few points cannot be told apart from a larger one within it. Because seed 1 also changed many of the shown
  walkthroughs, the re-run does not separate sampling noise from the choice of walkthroughs.
- **Transform versus other games is exploratory.** The split was fixed in the seed-1 rule, but it was chosen after V5B
  and V6 had shown where the gain sits, and it is not one of V6's registered contrasts. On the 149 other games the
  two-seed interval [−0.040, +0.094] excludes neither no effect nor a gain of about 0.09: it does not show that memory
  fails to help there.
- **Single games and single types.** The per-game difference agrees between seeds with a correlation of only 0.297, so
  which particular games gain or lose under one seed is mostly sampling noise. Per-game or per-type claims from one seed
  are weak.
- **Not shown.** Nothing about `none` at seed 1 (not run), about `retrieved_steps` or `retrieved_plan`, about other models,
  other environments or unseen rooms.

## 2. The D8 instruction arm on the V6 games

### What was run

- **Arm `d8_instruction`:** the `none` prompt plus one fixed sentence after the action instruction, stating the ALFWorld
  convention for transform goals:

  > Note: in these tasks a goal such as "put a clean mug in cabinet", "put a cool apple in fridge" or "put a hot potato in
  > countertop" means that you must first make the object clean (rinse it at a sinkbasin), cool (cool it with a fridge) or
  > hot (heat it with a microwave) yourself, and only then put it in the target place.

  The sentence also names the appliance for each transform, so the arm bundles the convention with appliance knowledge.
- **Question:** how much of the memory gain on transform games does a one-sentence statement of the convention reproduce?
- **Games:** all 300 V6 games, seed 0, run on 2026-11-21 between about 09:10 and 15:55 UTC, after V6 had finished (V6's
  run record: 2026-11-21 05:14 UTC): 151 transform games and 149 others.
  300 episodes, 0 errors, 0 duplicates, `memory_tokens` 0 in every episode; same model and settings as V6.
- **Agent:** the agent of the first D8 pilot, i.e. the V5B agent with this one sentence added. Its code path for a
  no-memory prompt is the same as the V6 agent's; the V6 agent's changes concern the memory arms and the positive-control
  arms only (checked by diff).
- **Comparison:** game by game with V6's measured `none` and `retrieved_task` at seed 0 (the published `per_unit.csv`).
  The D8 episodes ran later than those arms, were not interleaved with them and were not randomised together with them,
  so every comparison below is **across runs**, not within one run.
- **Rule written before data** (evidence: file times): on transform games, "the convention explains most of the gain" if d8 − none ≥ +0.10 and
  retrieved − d8 ≤ +0.05; "memory adds beyond the convention" if retrieved − d8 ≥ +0.10 with an exact McNemar p < 0.05;
  otherwise inconclusive. On other games, "harmless" if d8 − none > −0.05; "harmful" if d8 − none ≤ −0.05 with p < 0.05;
  otherwise inconclusive; d8 against `retrieved_task` there is descriptive only. The rule file is dated before the first
  episode, but only by seconds; that it preceded the data rests on file times, not on a registry record.

### Results

Exact two-sided McNemar test; the 95% intervals (Newcombe method 10, paired) were computed for this addendum and are not
in the run's own result file.

| games | n | d8 | `none` | `retrieved_task` | d8 − none (gains / losses, p) | 95% interval | retrieved − d8 (gains / losses, p) | 95% interval | rule |
|---|---:|---:|---:|---:|---|---|---|---|---|
| transform | 151 | 0.497 | 0.430 | 0.649 | +0.066 (29 / 19, p = 0.19) | [−0.024, +0.154] | +0.152 (40 / 17, p = 0.0032) | [+0.055, +0.245] | memory adds beyond the convention |
| other | 149 | 0.530 | 0.638 | 0.564 | −0.107 (13 / 29, p = 0.020) | [−0.190, −0.022] | +0.034 (20 / 15, p = 0.50; descriptive) | [−0.045, +0.111] | harmful |

### How to read it

- **Transform games.** Across runs, the walkthroughs beat the sentence by +0.152 (the rule's "memory adds beyond the
  convention"). How much of the memory gain the sentence reproduces is not pinned down: its point estimate against `none`
  (+0.066) is about 30% of the memory gain on these games (`retrieved_task − none` +0.219, 44 / 11, in V6), and its
  interval [−0.024, +0.154] reaches from no effect to about 70% of that gain.
- **What the transform test could detect.** With 48 discordant pairs the exact McNemar test reaches p < 0.05 only from a
  split of 32 / 16 onwards, a net difference of about +0.106 on 151 games. A true effect of the observed size (+0.066)
  would usually not be detected, so the non-significant d8 − none says little.
- **Other games.** Across runs, the sentence goes with −0.107 against `none`. For scale, the same 149 games give
  `placebo` 0.550 in V6 (2026-11-19 to 2026-11-21, seed 0) and 0.544 in the seed-1 re-run (2026-11-21/22). That is one arm,
  in one subset, with the seed changed as well, so it shows only that a later run of a whole arm did not move much in that
  one case; drift was not measured for `none`. Read this as a harm of this sentence, shown once, across runs. It
  is not evidence that retrieved memory harms these games: in V6 itself `retrieved_task − none` on them is −0.074, an
  exploratory subgroup whose interval includes zero.
- **The first D8 pilot does not replicate in size.** The first pilot ran the same arm on the 114 transform games of V5B
  (2026-11-21, compared with V5B's published arms): d8 − none +0.140 (25 / 9, p = 0.009, interval [+0.041, +0.235]) and
  retrieved − d8 +0.061 (24 / 17, p = 0.35, interval [−0.049, +0.169]); these are recomputed from its outputs and V5B's
  public `per_unit.csv`, as no result file was written for that pilot. On the V6 games the sentence's gain is smaller
  (+0.066) and the walkthroughs' margin over it larger (+0.152). The two intervals for d8 − none overlap, and both pilots
  are single-seed and across runs, so "smaller on V6" is a description, not a test.
- **Not shown.** Whether the convention or the appliance names do the work (the sentence states both); whether a sentence
  shown only on transform goals would help without the harm; anything at another seed.
- **Use for design.** A confirmatory test of this mechanism would need the instruction arm randomised within one run with
  `none` and the memory arm, shown only on transform goals, and a version without the appliance names.

## Source files (not in this repository)

SHA-256 of the files the numbers come from, kept in the maintainer's working copy:

| file | SHA-256 |
|---|---|
| seed-1 rule `V6_SEED1_RULE.md` | `b38db276b4f7e8a693cbbc15a6125af6525ac5b4672c5a883371591cad91eb94` |
| seed-1 result `RESULT_V6_SEED1.md` | `8172bafd2cac5a0431e2db056f63c21872748e9a3f071047848f7cdda6a5b840` |
| seed-1 outputs `out_v6_seed1_part1.jsonl` | `f1e845ff0616adf45aec48a3aaa5b7ab35ad65bea80355499961f3949825b252` |
| seed-1 outputs `out_v6_seed1_part2.jsonl` | `00094b51eb0d36964e1019c9f41b45665b90e18a9df41b304dae49906c73e16a` |
| seed-1 outputs `out_v6_seed1_part3.jsonl` | `682c5a80ec07486b5e56a5faca8d90fa0b619ea6e3db97291ff16764081710c1` |
| D8 rule `DECISION_RULE_V6.md` | `592f7124805aca0daf987dd4c50839d0c0af16544f095c1545d3348f73bbaf72` |
| D8 result `RESULT_V6.md` | `db462a7b0837cb10a5bb6f92a83df397357bd703495b2e077309b200755d7da3` |
| D8 outputs `out_v6_transform.jsonl` | `90ee9e5f056e416925f66ac8a31a02c8b6ebbc9f0c7c94281b8eef84794d64aa` |
| D8 outputs `out_v6_other.jsonl` | `36f45b4d40f417ae6749bc81506b69e4b53b344a0a378119e0e4ad46f4192144` |
| D8 agent `agent.py` | `42c45d142feef12b502ff31148fae9a934bb64553191bb3a258cf93212a112ad` |
| first D8 pilot outputs `out.jsonl` | `55f781e6f86ce87c1c52ace250513ea2582c0fb9b51e9643d8b5a9b0c1aaecdf` |
| seed-0 reference used by the runs `v6_reference.json` (equal, cell by cell, to the published `per_unit.csv`: 1500 of 1500) | `462fdbe499d133c31232122137cb2ef5978e40d75c7702f1b83b5969773c2c07` |

`tests/test_v6_seed1_d8_addendum.py` recomputes the seed-0 and V5B numbers of this addendum from the published
`per_unit.csv` files and checks that the addendum prints them.

## What does not change

The V6 package, its three primary contrasts and their sequential intervals, the findings (H1 and H2 supported, H3
refuted), the measurement problem of `retrieved_plan`, the code audit verdict (valid) and the direction status
(`retrieved_task` and `retrieved_steps` open, `retrieved_plan` measurement_problem).

Related: [V5B seed-1 addendum](2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md); [what we know so far](../evidence-summary-2026-11.md).
