# Side studies, November 2026: DS-HARD-1, DS-HARD-2 and NEMO-FLOOR

Status: exploratory side studies; summary numbers only. Added 2026-11-23.

These three studies ran **outside the lab pipeline**. They are not lab programs: no envelope, no instrument review, no
positive control and no lab code audit, and they produce no lab verdict, state or direction status. Each had a written
plan with its contrasts, statistics and decision words before any of its data; those plans are the pre-registration, and
the results below are read only against them. They are exploratory evidence about other models in a harder prompt mode,
not confirmatory results of the project.

All three reuse V6 material (see the [V6 package](../../data/lab/autolab-alfworld-ladder-r4-v6/README.md)): the V6 agent
and bank, V6 games, the walkthroughs V6's retrieval picks at seed 0, and the same kind of length-matched placebo block.
The models and the prompt mode differ from V6:

- **HARD mode.** The prompt shows no list of admissible actions; it gives the ALFWorld command grammar with a worked
  example, and the agent must type a valid command itself (an invalid one gets "Nothing happens."). The text is identical
  in every arm, so each memory comparison changes one factor. HARD mode was chosen because DeepSeek V4.1 Flash solved
  17 of 20 pilot games without memory in the lab's normal mode, too close to the ceiling to show a gain; in a 20-game HARD
  pilot it solved 13 of 20. The HARD-mode prompt patch is not in this repository yet.
- **Placebo.** Neutral filler in the same wrapper, matched in length to the `retrieved_task` block of the same game with
  the Qwen tokenizer the lab used for V6.

**Statistics, as fixed in the plans.** The game is the unit; a game enters a contrast only if both arms finished.
Paired difference of solve rates, exact two-sided McNemar test on the discordant pairs, 95% Newcombe interval (method 10,
paired). Verdict words: POSITIVE (p < 0.05 after the stated correction, difference > 0), NEGATIVE (the same, difference
< 0), NULL-INFORMATIVE (interval inside ±0.10), otherwise INCONCLUSIVE. These are the plans' own words, not the lab's
interval states.

**Checks done on the numbers.** Every number below was recomputed for this note from the per-episode outputs by a
script that does not import the studies' analyzers; all agree with the studies' result files, except that the bootstrap
intervals were reproduced only approximately (they depend on the random stream; the point estimates agree exactly).
Earlier, a recomputation by a reviewer model other than the authoring session matched every number of the first versions
of the DS-HARD-1 and DS-HARD-2 result files. The lab's science reviews then checked plan adherence, integrity and the
wording of each claim: a GPT model via Codex for DS-HARD-1 and DS-HARD-2, a Claude model (Fable) for NEMO-FLOOR. The GPT
reviews found the plans followed and the data complete, but **marked both DS-HARD claims as not supported as originally
worded**, because they put exploratory subgroup readings and a mechanism into the main claim; they also led to a
correction of the interval code to the plan's Newcombe method 10 (revision r2 of both result files, which this note
uses). The claims below are the corrected ones. The NEMO-FLOOR review found the claim supported, with minor notes only.

## DS-HARD-1: memory on a stronger API model, HARD mode

- **Model and run:** DeepSeek V4.1 Flash (API model id `deepseek-flash`), official API, thinking disabled, temperature
  0.7, no seed (sampling not reproducible), 50 steps. 200 V6 games (100 transform, 100 other), 4 arms, one sample per
  cell, 2026-11-22.
- **Plan:** written before data on 2026-11-22; two primaries with Holm correction.
- **Completeness:** 775 of 800 episodes recorded (none 194, placebo 193, `retrieved_task` 195, `mismatched_type` 193; the
  missing ones ended in errors, whose individual causes were not recorded), above the plan's 95% per arm. Four
  `mismatched_type` games were excluded from Q2 and Q3 by the plan's length rule (|length difference| > 10%).
- **Cost:** conservative ledger (all input at the cache-miss peak price × 1.25) 15.008 USD over 16,762 calls; the cap was
  15.0 USD, passed by the calls in flight.

| question | contrast | n | difference | 95% interval | gains / losses | p (Holm) | plan verdict |
|---|---|---:|---:|---|---:|---:|---|
| Q1, primary | `retrieved_task` − `placebo` | 193 | +0.218 | [+0.158, +0.282] | 43 / 1 | 1.0e-11 | POSITIVE |
| Q2, primary | `retrieved_task` − `mismatched_type` | 189 | +0.159 | [+0.103, +0.220] | 32 / 2 | 6.9e-08 | POSITIVE |
| Q3, secondary | `mismatched_type` − `none` | 189 | +0.063 | [+0.006, +0.121] | 21 / 9 | 0.043 (uncorrected) | — |
| descriptive | `placebo` − `none` | 193 | +0.005 | [−0.047, +0.057] | 13 / 12 | — | — |

**Corrected claim.** In this side study, on DeepSeek V4.1 Flash in ALFWorld V6 HARD mode, two expert walkthroughs of the
same task type raised the solve rate by +0.218 over the length-matched neutral filler (193 pairs) and by +0.159 over
length-matched walkthroughs of another task type (189 pairs). Both meet the pre-registered POSITIVE rule after Holm
correction. This supports choosing walkthroughs by task type in this setup.

**What it does not show.**

- Q2 does not separate procedural content from matched vocabulary, object names or concrete commands: the matched
  walkthroughs carry all of them.
- Where the gain sits is exploratory (Q5) and not part of the claim. In the plan's split, the Q1 difference is +0.368
  on transform games (n = 95) and +0.071 on the others (n = 98). Most of it comes from heat games, where the model
  without memory almost always failed (`none` 4 of 31, `placebo` 3 of 31, `retrieved_task` 29 of 31). In the other types,
  `placebo` already solved most games, which limits the possible gain there.
- Q3 (+0.063, uncorrected, lower bound near zero) suggests that even walkthroughs of another task type help a little in
  HARD mode; showing the command grammar in use is one possible route, not tested. It says nothing about the normal mode.
- One model, one environment, one sample per cell, no reproducible sampling.

## DS-HARD-2: which form of the walkthroughs carries the gain

- **Model and run:** as DS-HARD-1, 2026-11-22, one run with 4 arms: `retrieved_task` (the walkthroughs in full),
  `retrieved_steps` (their actions only), `retrieved_plan` (a rule-based subgoal plan without numbers and room-specific
  locations; it keeps the verbs and the object and appliance classes) and `placebo`. The two reduced forms are padded with
  filler to the length of the `retrieved_task` block, as in V6.
- **Games:** 100 of the 200 DS-HARD-1 games (50 transform, 50 other), chosen by a hash rule and frozen before any DS-HARD-2
  data. After the freeze, DS-HARD-1's aggregate outcomes on these games were seen while the analyzer was tested; they
  enter no DS-HARD-2 test. All 3 treatment arms of a game showed the same two walkthroughs, the same as DS-HARD-1's
  `retrieved_task` on the 99 games both recorded.
- **Plan:** revision r2, written before data after an independent pre-run review; two primaries with Holm correction.
- **Completeness:** 400 of 400 episodes, 0 errors, 0 exclusions. Block lengths within −0.6% and +0.9% of the target.
- **Cost:** conservative ledger 6.317 USD over 6,997 calls (cap 10.0 USD).

| question | contrast | n | difference | 95% interval | gains / losses | p | plan verdict |
|---|---|---:|---:|---|---:|---:|---|
| P1, primary | `retrieved_plan` − `placebo` | 100 | +0.130 | [+0.051, +0.213] | 15 / 2 | 0.0030 (Holm) | POSITIVE |
| P2, primary | `retrieved_steps` − `placebo` | 100 | +0.150 | [+0.062, +0.240] | 18 / 3 | 0.0030 (Holm) | POSITIVE |
| S0, in-run anchor | `retrieved_task` − `placebo` | 100 | +0.190 | [+0.101, +0.283] | 21 / 2 | 6.6e-05 | — |
| S1, abstraction | `retrieved_plan` − `retrieved_steps` | 100 | −0.020 | [−0.086, +0.043] | 3 / 5 | 0.73 | NULL-INFORMATIVE |
| S3 | `retrieved_plan` − `retrieved_task` | 100 | −0.060 | [−0.129, −0.001] | 1 / 7 | 0.070 | — |
| S3 | `retrieved_steps` − `retrieved_task` | 100 | −0.040 | [−0.098, +0.007] | 0 / 4 | 0.13 | — |

Share of the in-run gain kept, (form − `placebo`) / (`retrieved_task` − `placebo`), paired bootstrap: `retrieved_plan`
0.68 [0.42, 0.94], `retrieved_steps` 0.79 [0.54, 0.95].

**Corrected claim.** On 100 ALFWorld games in HARD mode on DeepSeek V4.1 Flash, the plan without numbers and
room-specific locations raised the solve rate over the length-matched placebo by +0.130, and the actions alone by +0.150.
In the same padded layout, plan minus actions was −0.020, inside the pre-registered ±0.10 margin. The plan kept an
estimated 0.68 of the full walkthroughs' gain over placebo (95% interval 0.42 to 0.94), the actions 0.79 (0.54 to 0.95).
A form without numbers and concrete locations can raise success in these conditions. How much the action names, the
appliance classes and the order of subgoals each contribute is not resolved.

**What it does not show.**

- Not "an abstract strategy carries the gain": the plan keeps the verbs and the object and appliance classes (for
  example "heat the X with the microwave").
- Not "the plan keeps most of the gain": the interval of its share reaches below one half.
- Neither reduced form is shown to be worse than the full walkthroughs: the S3 McNemar tests give p = 0.070 and p = 0.13.
  Only the actions met the ±0.10 criterion against the full walkthroughs. S3 also changes the layout (padded against
  unpadded), not only the form.
- No `none` arm was run, so which games the model fails without help is known only from DS-HARD-1 on another day. The
  per-type counts are descriptive; the largest net gain of both forms was in heat games (`placebo` 4 of 15; plan and
  actions 10 of 15 each, full walkthroughs 14 of 15). Not every other type was at the ceiling (clean: `placebo` 15 of 18).
- **Same population, not an independent replication.** S0 (+0.190) repeats DS-HARD-1 Q1 (+0.218) on a subset of the same
  games with the same walkthroughs, model and mode. Same-unit check between the two days on the 99 shared games:
  `retrieved_task` moved by −0.030 (1 / 4) and `placebo` by −0.010 (7 / 8).
- **Power** (from the plan's simulations): a form that keeps half of the gain is detected about 60% of the time; a
  NULL-INFORMATIVE S1 means no loss of 0.10 or more was detected, not that there is no loss.

## NEMO-FLOOR: can walkthroughs lift a weak 12B model off the HARD-mode floor?

- **Model and run:** Mistral Nemo 12B (`mistralai/mistral-nemo`) through OpenRouter, pinned to one provider (DeepInfra,
  FP8, no fallbacks; all 14,005 served calls came from it), temperature 0.7, no seed, 50 steps, HARD mode, 3 arms
  (`none`, `placebo`, `retrieved_task`), one sample per cell, 2026-11-22 to 2026-11-23.
- **Games:** 100 of the DS-HARD-1 games, with the 20 games of the earlier NEMO pilot excluded (their outcomes had been
  seen); the same walkthroughs and placebo blocks as DS-HARD-1.
- **Plan:** written before data on 2026-11-22, revised before data after a design review; one primary, no multiplicity
  correction; a futility stop after 40 games (not triggered: 8 gains, 0 losses).
- **Completeness:** 300 of 300 episodes, 100 complete games, 0 errors in the recorded episodes. As the plan prescribes,
  errored episodes were re-run once with fresh samples: 5 in stage 1 by the run log, none listed for stage 2. The
  discarded attempts are not kept, so their content cannot be checked.
- **Cost:** conservative ledger 0.933 USD over 14,518 ledger rows (provider-reported 0.724 USD), cap 2.0 USD.

| contrast | n | difference | 95% interval | gains / losses | p | plan verdict |
|---|---:|---:|---|---:|---:|---|
| `retrieved_task` − `placebo` (primary) | 100 | +0.200 | [+0.122, +0.289] | 20 / 0 | 1.9e-06 | POSITIVE |
| `retrieved_task` − `none` (secondary, uncorrected) | 100 | +0.210 | [+0.130, +0.301] | 21 / 0 | 9.5e-07 | — |
| `placebo` − `none` (descriptive) | 100 | +0.010 | [−0.037, +0.061] | 2 / 1 | — | — |

Solved games: `none` 1 of 100, `placebo` 2 of 100, `retrieved_task` 22 of 100. The plan's floor premise (`none` and
`placebo` each ≤ 0.10) holds.

**The pre-registered reading: a floor lift, not a general memory gain.** Task-memory walkthroughs lift Mistral Nemo 12B
off the HARD-mode floor, from 2 of 100 (`placebo`) to 22 of 100 (`retrieved_task`). This is all the study claims.

- 78 of 100 games stay unsolved. The lift is uneven across types (descriptive; solved with memory): `pick_and_place`
  10 of 16, heat 4 of 17, clean 3 of 18, `look_at` 3 of 15, `pick_two` 2 of 20, `pick_cool` 0 of 14. `placebo` solved
  one `pick_and_place` and one `look_at` game and nothing else.
- It **does not separate three routes**: (a) learning the HARD-mode command format and the object names from the
  walkthroughs' exact command strings (there is no `mismatched_type` arm to control it); (b) following a similar
  walkthrough's command sequence; (c) understanding the task. Route (a) is visibly active: invalid commands per step fall
  from 0.786 (`none`) and 0.759 (`placebo`) to 0.549 (`retrieved_task`). Route (b) is plausible in some games: in 10 games
  a shown walkthrough comes from the same ALFWorld floor plan as the test game, and 4 of those were solved.
- It says nothing about models that can already play, and it must not be cited as evidence of task understanding.
- **Power** (from the plan): a lift of 0.10 or more was well powered (about 0.85 to 0.9 with the futility stop); below
  about 0.08 an INCONCLUSIVE result would have been the likeliest outcome.

## Across the three studies

- **Models and modes are confounded.** The lab's V6 measures Qwen3-4B in normal mode; these studies measure DeepSeek V4.1
  Flash and Mistral Nemo 12B in HARD mode. Any comparison of gain sizes or of which task types gain is descriptive. For
  example, the DeepSeek gain sits mostly in heat games (DS-HARD-1: 26 of the 43 gains over `placebo`), while in the V6
  `per_unit.csv` 27 of Qwen's net 39 games over `placebo` come from clean and cool games and 10 from heat games. Whether
  the admissible-action list of the normal mode already supplies the heat command is an untested hypothesis.
- **Same games, correlated results.** All three studies use V6 games, and NEMO-FLOOR and DS-HARD-2 use subsets of the
  DS-HARD-1 games. Outcomes are correlated through game difficulty; the studies are not independent samples of games.
- **Expert walkthroughs only.** All memory here is a bank of expert walkthroughs, not the agent's own earlier episodes.

## Source files (not in this repository)

The per-episode outputs and spend ledgers are kept in the maintainer's working copy and are not published (they hold the
full action logs). SHA-256:

| file | SHA-256 |
|---|---|
| DS-HARD-1 plan `DS_HARD_1_PLAN.md` | `b5e4a37363da610c51bd1c3b2ab3f1db8b6083fd4b7cb67d64fa1cd68f2529d9` |
| DS-HARD-1 result `RESULT_DS_HARD_1.md` (r2) | `38d8d0df61402b2f1aa23cc47b5cfdafce93fa0972a300da9d99e6da8595c239` |
| DS-HARD-1 outputs `out_ds_hard_1.jsonl` | `f8422bf6ca3c26d2075c0391aba2e95ac7630c3341b98769602bc6bcd348acbb` |
| DS-HARD-1 jobs `batch_ds_hard_1.jsonl` | `d2e42fa532391c7ea1c2d76d9ceb57314043cb26a48cf352663dc5e141a63d12` |
| DS-HARD-2 plan `DS_HARD_2_PLAN.md` (r2) | `0c1276922d9e0a287193e722a2e7074a5529b5d9e570c3a5bf0f8595f24c69be` |
| DS-HARD-2 result `RESULT_DS_HARD_2.md` (r2) | `8ae0335904787a3d61f32cc61fb7a4e76aa3098cb5ad95547e243e1796bfa66a` |
| DS-HARD-2 outputs `out_ds_hard_2.jsonl` | `61f39d7608f3d4dfeecaf6d5763c17136c07ecea513c07bc36ee59e751807388` |
| DS-HARD-2 jobs `batch_ds_hard_2.jsonl` | `16919b23e9202f21ec2fbe68f4a7c3e51de0167f92668938269b78fa06e2d8ff` |
| NEMO-FLOOR plan `NEMO_FLOOR_PLAN.md` | `a836bacdca0eae69b45c3d02e3eb984173c98c9eb2f234163430f995951e7979` |
| NEMO-FLOOR result `RESULT_NEMO_FLOOR.md` | `1fedaddd1f0b1112fe7b3a142f2d8c44ee5bca558ca97b8fb1a2dca41b650bef` |
| NEMO-FLOOR outputs `out_nemo_floor.jsonl` | `7cb69cd0ea815cb239fbd3f80e49f0c19f732f8590065f3f4ecdf22655fa9836` |
| NEMO-FLOOR jobs `batch_nemo_floor.jsonl` | `f2afee508a86542f2df752cd8ac2202732846057dd6fe51c81790e723b145a7b` |

Related: [V6 addendum: seed-1 re-run and the D8 instruction arm](errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md).
