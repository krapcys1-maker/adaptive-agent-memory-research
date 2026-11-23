# Addendum: a seed-1 re-run of the primary contrast and the D8 instruction arm on the ALFWORLD-LADDER-R4-V6 games

Added 2026-11-23. Package: `data/lab/autolab-alfworld-ladder-r4-v6/`. Its published bytes are unchanged; they are pinned
by `PUBLISHED_FILES.json` and recomputed by `scripts/verify_autolab_packages.py`. This is an addition, not a correction
of a number. Nothing here changes the package's results, findings, verdicts, direction status or caveats.

Two follow-up runs used the V6 games after V6 had finished. Both are **exploratory side runs outside the lab pipeline**.
They are not lab programs and produce no lab verdict. They have none of the lab's safeguards:
- no envelope (the lab's frozen pre-measurement protocol package);
- no instrument review;
- no positive control;
- no code audit.

Each run had a rule written before its data. The rules are not published and have no external registry record. The
evidence that they preceded the data is their file times; their SHA-256 (end of this page) fixes their content.

**What a reader can check.**
- The per-game outcomes (`unit`, `arm`, `seed`, `solved`) are published in
  [`data/lab/side-runs-2026-11/`](../../../data/lab/side-runs-2026-11/README.md).
- Every number on this page that rests on solve rates can be recomputed from those tables and the package's
  `per_unit.csv`. `tests/test_v6_seed1_d8_addendum.py` does so.
- The action logs stay private, so the overlap counts of shown walkthroughs cannot be checked by a reader.

**Who computed the numbers.** Both runs were run and first analysed by a session of the project's automated coordinator,
a Claude model. The numbers were then recomputed by a second script, also written by a Claude model, that does not
import the first. These are internal checks within one model family, not independent reviews.

**"D8"** is the lab's label for one hypothesis about why the walkthroughs help: they teach the ALFWorld convention that a
goal such as "put a clean X in Y" requires cleaning X first.

## 1. The primary contrast at a second seed

### What was run

- **Arms:** `placebo` and `retrieved_task`, the two arms of V6's primary contrast for full walkthroughs. `none`,
  `retrieved_steps` and `retrieved_plan` were not re-run.
- **Games and instrument:** the same 300 V6 games, with a byte-identical copy of the V6 instrument.
  - The SHA-256 of `agent.py`, `run_episode.sh`, `vllm_serve.sh`, `bank.jsonl`, `units.json` and `families.json` equal
    the pins in the package's `knowledge.jsonl`.
  - Same model (`Qwen/Qwen3-4B-Instruct-2507-FP8`), temperature 0.7, `min_tokens` 8, 50 steps, format reminder on
    (checked in all 600 records).
- **Seed 1.** The seed changes the model's sampling and also the tie-break among equally similar bank entries, so the
  shown walkthroughs differ from seed 0 in many games.
  - The public `per_unit.csv` does not list the sources, so this was checked with a proxy. DS-HARD-1 (see
    [the side-studies note](../side-studies-2026-11.md)) ran the same agent and bank at seed 0, so its `retrieved_task`
    sources are the V6 seed-0 picks.
  - On the 195 games both runs share, the seed-1 pair was the same set of two walkthroughs in 69 games, and at least one
    walkthrough was shared in 166. These counts come from the private logs.
- **When:** 2026-11-21 23:40 to 2026-11-22 14:58 UTC, on the lab's GPU, after V6 had finished.
  - V6's objects in `knowledge.jsonl` are dated 2026-11-19 to 2026-11-21; its run record is dated 2026-11-21 05:14 UTC.
  - The seed-1 episodes were not interleaved with V6's and not randomised together with them.
  - 600 episodes, 0 errors, 0 duplicates, no exclusions.
- **Rule written before the data** (2026-11-21; evidence: file times). If seed 1 gives `retrieved_task − placebo`
  ≥ +0.05, the seed-0 result is described as stable across two seeds; ≤ 0, not stable; in between, weaker but same sign.
  The rule also fixed the transform / other split and the two-seed estimate below.

**What to call it.** This is a seed re-run of the same protocol on the same games, bank, model and machine: a consistency
check of the V6 primary contrast under new sampling and a partly new choice of walkthroughs. It is not an independent
replication; that would need new games, a new bank, another model or another lab.

### Results

The contrast is paired over games. Gains / losses are the games solved only with `retrieved_task` / only with
`placebo`. The p values come from an exact two-sided McNemar test on the discordant pairs.

| games | n | seed | `placebo` | `retrieved_task` | difference | gains / losses | McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 300 | 0 | 0.477 | 0.607 | +0.130 | 72 / 33 | 0.0002 |
| all | 300 | 1 | 0.457 | 0.613 | +0.157 | 78 / 31 | 7.7e-06 |
| transform (clean / cool / heat) | 151 | 0 | 0.404 | 0.649 | +0.245 | 50 / 13 | 3.0e-06 |
| transform (clean / cool / heat) | 151 | 1 | 0.371 | 0.642 | +0.272 | 53 / 12 | 2.8e-07 |
| other | 149 | 0 | 0.550 | 0.564 | +0.013 | 22 / 20 | 0.88 |
| other | 149 | 1 | 0.544 | 0.584 | +0.040 | 25 / 19 | 0.45 |

**Reading under the rule written before the data.** Seed 1 gives +0.157, above the rule's +0.05, so the rule's word is
"stable". The threshold is lenient:
- In a normal approximation with the seed-0 discordance (0.35) and 300 games, a true difference of 0, 0.05 and 0.13
  gives "stable" with probability of about 0.07, 0.50 and 0.99.
- A seed-1 value under half of the seed-0 value would also have been called stable.

Read the outcome as "same sign, similar size".

**Two-seed estimate.** For each game, take the mean of seeds 0 and 1 per arm. Then compute the paired difference with a
95% t-interval over the games. The game is the unit, so the two seeds are not counted as independent games.

| games | n | `placebo` | `retrieved_task` | difference | 95% interval (t, over games) |
|---|---:|---:|---:|---:|---|
| all | 300 | 0.467 | 0.610 | +0.143 | [+0.090, +0.196] |
| transform | 151 | 0.387 | 0.646 | +0.258 | [+0.180, +0.337] |
| other | 149 | 0.547 | 0.574 | +0.027 | [−0.040, +0.094] |

**Transform − other.** This is the difference of the two stratum differences, with a 95% normal interval over games:

| seeds | difference of differences | 95% interval |
|---|---:|---|
| seed 0 | +0.232 | [+0.103, +0.360] |
| seed 1 | +0.231 | [+0.102, +0.361] |
| two-seed means | +0.231 | [+0.129, +0.334] |

The two strata start from different levels: at seed 0, `placebo` solves 0.404 of the transform games and 0.550 of the
others, so the headroom differs.

**Net games gained by task type.** Net = games solved only with `retrieved_task` minus games solved only with `placebo`.
This is descriptive, a split chosen after the data.

| task type | games | net, seed 0 | net, seed 1 |
|---|---:|---:|---:|
| `pick_clean` | 53 | 12 | 12 |
| `pick_cool` | 49 | 15 | 24 |
| `pick_heat` | 49 | 10 | 5 |
| `look_at` | 50 | 7 | 4 |
| `pick_and_place` | 46 | 0 | 2 |
| `pick_two` | 53 | −5 | 0 |
| all | 300 | 39 | 47 |

**Agreement between seeds, game by game.** These are planning inputs for multi-seed programs:
- phi of `solved` between seed 0 and seed 1: 0.585 for `placebo`, 0.468 for `retrieved_task`;
- correlation of the per-game difference (`retrieved_task` − `placebo`) between the seeds: 0.297.

### How to read it

- **The interval of record stays the package's.** V6's published interval for this contrast is +0.130
  [+0.049, +0.211].
  - That is a paired sequential interval at the final look (z = 2.4166), and it carries the lab's state and direction
    status.
  - The two-seed interval above is a fixed-sample t-interval computed outside the lab's rules. It is not a lab verdict
    and is not directly comparable with the sequential interval.
  - Its lower bound (+0.090) is below the lab's SESOI of 0.12, so even on this reading the estimate would not be
    `practical`.
- **What the two seeds can and cannot show.**
  - With 300 games the two-seed interval is about ±0.053 wide, so a true gain of a few points cannot be told apart from
    a larger one within it.
  - Seed 1 also changed many of the shown walkthroughs, so the re-run does not separate sampling noise from the choice
    of walkthroughs.
- **Transform versus other games is exploratory.**
  - The split was fixed in the seed-1 rule, but it was chosen after V5B and V6 had shown where the gain sits, and it is
    not one of V6's registered contrasts.
  - The difference of differences is about +0.23 at both seeds. Its interval excludes zero, but the strata differ in
    baseline as well as in task type.
  - On V5B at seed 1 the same split (against `none`) gives only +0.084 [−0.077, +0.245]; see the
    [V5B addendum](2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md).
  - On the 149 other V6 games, the two-seed interval [−0.040, +0.094] excludes neither no effect nor a gain of about
    0.09. It does not show that memory fails to help there.
- **Single games and single types.** The per-game difference agrees between seeds with a correlation of only 0.297.
  Which particular games gain or lose under one seed is therefore mostly sampling noise, and per-type rows are weak
  evidence.
- **Not shown.**
  - Nothing about `none` at seed 1, which was not run.
  - Nothing about `retrieved_steps` or `retrieved_plan`.
  - Nothing about other models, other environments or unseen rooms.

## 2. The D8 instruction arm on the V6 games

### What was run

- **Arm `d8_instruction`:** the `none` prompt plus one fixed sentence after the action instruction, stating the ALFWorld
  convention for transform goals:

  > Note: in these tasks a goal such as "put a clean mug in cabinet", "put a cool apple in fridge" or "put a hot potato in
  > countertop" means that you must first make the object clean (rinse it at a sinkbasin), cool (cool it with a fridge) or
  > hot (heat it with a microwave) yourself, and only then put it in the target place.

  The sentence also names the appliance for each transform, so the arm bundles the convention with appliance knowledge.
- **Question:** how much of the memory gain on transform games does a one-sentence statement of the convention reproduce?
- **Games:** all 300 V6 games (151 transform, 149 other), seed 0.
  - Run on 2026-11-21 between about 09:10 and 15:55 UTC, after V6 had finished (V6's run record: 2026-11-21 05:14 UTC).
  - 300 episodes, 0 errors, 0 duplicates, `memory_tokens` 0 in every episode; same model and settings as V6.
- **Agent:** the agent of the first D8 pilot, i.e. the V5B agent with this one sentence added. Its code path for a
  no-memory prompt is the same as the V6 agent's. This was checked by diff: the V6 agent's changes concern only the
  memory arms and the positive-control arms.
- **Comparison:** game by game with V6's measured `none` and `retrieved_task` at seed 0, from the published
  `per_unit.csv`.
  - The D8 episodes ran later than those arms, were not interleaved with them and were not randomised together with
    them.
  - So every comparison below is **across runs**, not within one run.
- **Rule written before the data.** The evidence is file times: the rule file precedes the first episode by seconds.
  - Transform games:
    - "the convention explains most of the gain" if d8 − none ≥ +0.10 and retrieved − d8 ≤ +0.05;
    - "memory adds beyond the convention" if retrieved − d8 ≥ +0.10 with an exact McNemar p < 0.05;
    - otherwise inconclusive.
  - Other games:
    - "harmless" if d8 − none > −0.05;
    - "harmful" if d8 − none ≤ −0.05 with p < 0.05;
    - otherwise inconclusive;
    - d8 against `retrieved_task` there is descriptive only.

### Results

The p values come from an exact two-sided McNemar test. The 95% intervals (Newcombe method 10, paired) were computed for
this addendum; they are not in the run's own result file.

| games | n | d8 | `none` | `retrieved_task` | d8 − none (gains / losses, p) | 95% interval | retrieved − d8 (gains / losses, p) | 95% interval | the rule's word |
|---|---:|---:|---:|---:|---|---|---|---|---|
| transform | 151 | 0.497 | 0.430 | 0.649 | +0.066 (29 / 19, p = 0.19) | [−0.024, +0.154] | +0.152 (40 / 17, p = 0.0032) | [+0.055, +0.245] | memory adds beyond the convention |
| other | 149 | 0.530 | 0.638 | 0.564 | −0.107 (13 / 29, p = 0.020) | [−0.190, −0.022] | +0.034 (20 / 15, p = 0.50; descriptive) | [−0.045, +0.111] | harmful |

### How to read it

- **Transform games.** Across runs, the walkthroughs beat the sentence by +0.152 [+0.055, +0.245]. This is the rule's
  "memory adds beyond the convention".
  - The sentence against `none` is +0.066 [−0.024, +0.154].
  - The memory gain on the same games in V6 is `retrieved_task − none` +0.219 (44 / 11).
  - As point values, +0.066 is about 30% of +0.219. No interval was computed for this share; the only interval is the
    one for the sentence's own difference, [−0.024, +0.154], so the share is not pinned down.
- **What the transform test could detect.** With 48 discordant pairs, the exact McNemar test reaches p < 0.05 only from a
  split of 32 / 16 onwards, a net difference of about +0.106 on 151 games. A true effect of the observed size (+0.066)
  would usually not be detected, so the non-significant d8 − none says little.
- **Other games: the sentence did not help, and the drop against `none` is not attributable to it.**
  - The rule's word is "harmful": −0.107 against `none`, across runs.
  - But within V6 itself, on the same 149 games, the neutral filler block shows a similar drop: `placebo − none` −0.087
    (12 / 25, p = 0.047), interval [−0.165, −0.007].
  - Against the filler, the sentence is −0.020 (16 / 19, p = 0.74), interval [−0.098, +0.058]. This is descriptive and
    across runs.
  - On these games, `none` (0.638) is higher than the filler (0.550), the D8 arm (0.530), `retrieved_task` (0.564) and
    `retrieved_steps` (0.577). Only `retrieved_plan` is higher (0.671).
  - The drop against `none` is therefore shared with a content-free block. It may also reflect a high draw of `none`:
    on V5B's 87 non-transform games, `none` moved from 0.667 at seed 0 to 0.598 at seed 1.
  - The result shows no harm specific to the sentence.
- **Transform games against the filler** (descriptive, across runs): the sentence is +0.093 (31 / 17, p = 0.060),
  interval [+0.003, +0.180]. Within V6, the filler is −0.027 against `none` on these games (13 / 17).
- **The first D8 pilot does not recur in size.**
  - The first pilot ran the same arm on the 114 transform games of V5B, on 2026-11-21, compared with V5B's published
    arms (across runs). It gave d8 − none +0.140 (25 / 9, p = 0.009, interval [+0.041, +0.235]) and retrieved − d8
    +0.061 (24 / 17, p = 0.35, interval [−0.049, +0.169]).
  - No result file was written for that pilot. These numbers are recomputed from its outputs (now in
    `data/lab/side-runs-2026-11/d8-v5b-pilot.csv`) and V5B's public `per_unit.csv`.
  - On the V6 games the sentence's gain is smaller (+0.066) and the walkthroughs' margin over it larger (+0.152).
  - The two intervals for d8 − none overlap, and both pilots are single-seed and across runs, so "smaller on V6" is a
    description, not a test.
- **Not shown.**
  - Whether the convention or the appliance names do the work; the sentence states both.
  - Whether a sentence shown only on transform goals would help.
  - Anything at another seed.
- **Use for design.** A confirmatory test of this mechanism needs:
  - the instruction arm randomised within one run, together with `none`, `placebo` and the memory arm;
  - the sentence shown only on transform goals;
  - a version without the appliance names.

## Source files

The per-game tables are in `data/lab/side-runs-2026-11/`. The rules, result files and full outputs are not published:
- the outputs hold action logs;
- the rules and result files contain machine-local paths and internal coordination notes.

Their SHA-256 are commitments for a later release:

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
| seed-0 reference used by the runs, `v6_reference.json` (equal, cell by cell, to the published `per_unit.csv`: 1500 of 1500) | `462fdbe499d133c31232122137cb2ef5978e40d75c7702f1b83b5969773c2c07` |

## What does not change

- The V6 package and its three primary contrasts, with their sequential intervals.
- The findings: H1 and H2 supported, H3 refuted.
- The measurement problem of `retrieved_plan`.
- The code audit verdict (valid).
- The direction status: `retrieved_task` and `retrieved_steps` open, `retrieved_plan` measurement_problem.

Related: [V5B seed-1 addendum](2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md); [what we know so far](../evidence-summary-2026-11.md).
