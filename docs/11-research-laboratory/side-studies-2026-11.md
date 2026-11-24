# Side studies, November 2026: DS-HARD-1, DS-HARD-2, NEMO-FLOOR, NEMO-1 and the DeepSeek and Mistral pilots

Status: exploratory side studies, outside the lab pipeline. Added 2026-11-23; NEMO-1 added 2026-11-24.

## How to read this note

**What these studies are.** They are not lab programs, and they produce no lab verdict, state or direction status. They
had none of the lab's safeguards:
- no envelope (the lab's frozen pre-measurement protocol package);
- no instrument review;
- no positive control;
- no lab code audit.

**Their plans.** Each study had a written plan, with its contrasts, statistics and decision words, before any of its
data. The results below are read only against those plans.
- The plans are not published and have no external registry record.
- The evidence that a plan preceded the data is its file time against the first paid call. Its SHA-256 (end of this
  note) fixes its content.
- So they are called "plans written before the data", not pre-registrations, and their decision words are
  "plan-defined".
- The prompt mode and the game sets were chosen after the pilots described below.

These are exploratory results about other models, mostly in a harder prompt mode (NEMO-1 uses the lab's normal mode),
not confirmatory results of the project.
The list of all runs since V6, including those not reported here, is in [what we know so far](evidence-summary-2026-11.md).

**Funding and process.** The DeepSeek and OpenRouter calls were paid by the maintainer, from budgets approved in
private. CONTRIBUTING.md asks for an issue and a decision before anything calls a hosted model API. No public issue or
decision record was made for these runs, and this note is the first public record of them. Costs are given per study
from the spend ledgers (conservative: all input booked at the peak cache-miss price × 1.25).

**Shared material.** All studies reuse V6 material (see the
[V6 package](../../data/lab/autolab-alfworld-ladder-r4-v6/README.md)):
- the V6 agent and bank;
- V6 games;
- the walkthroughs that V6's retrieval picks at seed 0;
- the same kind of length-matched placebo block.

The models differ from V6, and every study except NEMO-1 also changes the prompt mode:
- **HARD mode** (DS-HARD-1, DS-HARD-2, NEMO-FLOOR and the HARD-mode pilots). The prompt shows no list of admissible actions. It gives the ALFWorld command grammar with a worked
  example, and the agent must type a valid command itself (an invalid one gets "Nothing happens."). The text is
  identical in every arm, so each memory comparison changes one factor. The HARD-mode prompt patch is not in this
  repository.
- **Placebo.** Neutral filler in the same wrapper, matched in length to the `retrieved_task` block of the same game with
  the Qwen tokenizer the lab used for V6.

**Statistics, as fixed in the plans.**
- The game is the unit. A game enters a contrast only if both arms finished (NEMO-1: only games with all four arms
  recorded).
- Each contrast is a paired difference of solve rates, with an exact two-sided McNemar test on the discordant pairs and
  a 95% Newcombe interval (method 10, paired).
- Plan-defined verdict words:
  - POSITIVE: p < 0.05 after the stated correction, difference > 0;
  - NEGATIVE: the same, difference < 0;
  - NULL-INFORMATIVE: the interval lies inside ±0.10;
  - INCONCLUSIVE: anything else.

  These are the plans' words, not the lab's interval states.
- Steps are counted with failures set to 50. Step contrasts use a Wilcoxon signed-rank test in its normal approximation.

**What a reader can check.**
- The per-game outcomes (`unit`, `arm`, `seed`, `solved`) of every study and pilot here are published in
  [`data/lab/side-runs-2026-11/`](../../data/lab/side-runs-2026-11/README.md). Every solve-rate number below can be
  recomputed from them; `tests/test_v6_seed1_d8_addendum.py` recomputes the headline contrasts.
- Not checkable from the repository, because they need the private action logs:
  - step counts (the Wilcoxon step tests);
  - per-step format counters;
  - the shown walkthroughs (the exposure counts, the same-floor-plan count);
  - the syntax check of DS-HARD-2;
  - costs.

**Who checked what.**
- **The lab's science reviews of DS-HARD-1 and DS-HARD-2:** an OpenAI GPT model via the Codex CLI (`gpt-6.2-astra`, as
  recorded in the result files). This is a different model family from the studies' authors.
  - They checked plan adherence, data integrity and the wording of each claim, working from the lab's tables; they did
    not recompute the statistics.
  - They found the plans followed and the data complete, but marked both claims as not supported as originally worded,
    because those put exploratory subgroup readings and a mechanism into the main claim. The claims below are the
    corrected ones.
  - The reviews also led to a correction of the interval code to the plan's Newcombe method 10 (revision r2 of both
    result files, used here).
- **The science review of NEMO-FLOOR:** a Claude model (Fable). The studies were written and run by Claude sessions, so
  this review is internal (same model family), not independent. It found the claim supported, with minor notes.
- **The lab's science review of NEMO-1:** also a Claude model (Fable), so internal as well.
  - It found the plan followed, the data complete and the claim supported by the numbers.
  - It asked for two corrections before use, both applied in the NEMO-1 section: no "replication" wording, and a
    statement that Q2 is borderline.
  - The committed result file and summary (SHA-256 at the end of this note) are unchanged, so they still carry three
    defects that the review noted or that this note corrects. They cite the plan as "r2", although the rules applied
    are r3's. The summary calls the study a "cross-model replication". The result file lacks the count of
    wrapper-mapped token-cache lookups that the plan lists among its validity checks. The corrected wording exists only
    in this note.
- **Numeric re-verification of DS-HARD-1 and DS-HARD-2:** a Claude model (Sonnet). Internal.
- **This note's recomputation:** scripts written by a Claude model that do not import the studies' analyzers.
  Internal.
  - All solve-rate numbers agree exactly with the result files. For NEMO-1 this includes the Newcombe intervals of Q1
    to Q3 and of `retrieved_task` − `none`.
  - For NEMO-1, the following are taken from the result file and were not recomputed: Q4, the Q5 bootstrap interval,
    the intervals of the sensitivity rows, the per-step counters, the length ratios and the costs.
  - The step statistics agree with them.
  - Bootstrap intervals agree only approximately, because they depend on the random stream; the note gives the result
    file's values.

No model outside the Claude family recomputed any number. With the published tables, anyone can.

## The pilots that chose the task (pilots, not tests)

**DeepSeek pilots.** Both ran on 2026-11-22 on the same 20 V6 games (10 transform, 10 other), with `none` and
`retrieved_task` (seed label 0) and DeepSeek V4.1 Flash as below. Each had a rule written before its data (evidence: file
times). Neither rule judged memory: with 20 games, a solve-rate difference is a direction hint, not a result.

| pilot | rule (decides only feasibility) | episodes without error | `none` solved | `retrieved_task` solved | gains / losses | Qwen V6 seed 0, same games (`none` / `retrieved_task`) | invalid commands per step (`none` / `retrieved_task`) | conservative cost | rule outcome |
|---|---|---:|---:|---:|---:|---|---|---:|---|
| normal mode | GO if ≥ 90% of episodes end without error, the format rates are at most twice Qwen V6's on the same games, and 200 games × 2 arms project to at most 10 USD | 40 / 40 | 17 / 20 | 20 / 20 | 3 / 0 | 10 / 20, 11 / 20 | 0.020 / 0.005 | 0.472 USD | GO |
| HARD mode | the mode qualifies if `none` solves 6 to 14 of 20 and ≥ 90% of episodes end without error | 40 / 40 | 13 / 20 | 18 / 20 | 6 / 1 | 10 / 20, 11 / 20 | 0.272 / 0.224 | 0.659 USD | QUALIFIES |

- The mode was selected on no-memory pilot performance. The normal-mode pilot passed its feasibility rule, but `none` at
  17 of 20 leaves almost no room for a gain, so the HARD mode was piloted.
- Applied to the HARD pilot, the normal-mode rule gives NO-GO on the invalid-command rate. That is expected: without the
  admissible-action list, a wrong command is the task's difficulty, not a format failure.
- The pilot records carry no mode flag. The HARD pilot's mode rests on its run files and on its invalid-command rate.
- None of the 20 pilot games is among the DS-HARD-1 games.

**Mistral Nemo qualification pilot** (NEMO-1, revision r2; HARD mode; 20 V6 games; 4 arms).
- 65 of 80 episodes were recorded, on 19 of the 20 games. The other 15 were lost to HTTP 429 rate limits.
- Solved: `none` 0 of 14 recorded episodes, `placebo` 0 of 17, `retrieved_task` 3 of 17, `mismatched_type` 1 of 17.
- Its rule, written before the data, gave NO-GO for the NEMO-1 study as planned:
  - the floor (`none` 0 of 14 recorded episodes);
  - too few episodes without error;
  - too few games with a usable length ratio.
- This pilot motivated NEMO-FLOOR. Its 20 games are excluded from NEMO-FLOOR, because their outcomes had been seen.

**Mistral Nemo qualification pilot, revision r3** (normal mode; the same 20 V6 games; 4 arms). NEMO-1 was then
re-planned for the normal mode (r3). Its qualification pilot used the same 20 games as the r2 pilot.
- Its rule, written before the data, gives GO only if all of these hold:
  - `none` solves 4 to 16 of 20;
  - at least 90% of the 80 episodes end without an error;
  - the mean Mistral-token length ratio of `placebo`, and that of `mismatched_type`, lies in [0.90, 1.10], with at least
    15 usable games.
- The pilot (2026-11-23, 80 of 80 episodes without error) passed it: GO.
- Solved, of 20: `none` 4, at the lower edge of the window; `placebo` 4; `retrieved_task` 7; `mismatched_type` 6.
- Mean length ratios on 20 games: `placebo` 0.984, `mismatched_type` 0.995.
- The main run is reported in the NEMO-1 section below.

## DS-HARD-1: memory on a stronger API model, HARD mode

**Setup.**
- **Model:** DeepSeek V4.1 Flash through the official API, as the alias `deepseek-flash`. The API exposes no seed, and
  the records and ledgers store only the alias, no served-model fingerprint.
- **Settings:** thinking disabled, temperature 0.7, 50 steps.
- **Calls:** 2026-11-22, 08:02–09:51 UTC.
- **Design:** 200 V6 games (100 transform, 100 other), 4 arms, one sample per cell.
- **Plan:** written before the data on 2026-11-22 (evidence: file times). Two primaries, with Holm correction.
- **Power** (from the plan, before the data): at about 200 pairs, discordance about 0.30 and the Holm first-step alpha
  0.025, about 63% for a true difference of 0.10 and about 95% for 0.15. The plan expected Q2 to be smaller than Q1.

**Completeness.**
- 775 of 800 episodes were recorded: `none` 194, `placebo` 193, `retrieved_task` 195, `mismatched_type` 193.
- The missing ones ended in errors whose individual causes were not recorded. Every arm is above the plan's 95%.
- Four `mismatched_type` games were excluded from Q2 and Q3 by the plan's length rule (|length difference| > 10%).

**Cost:** 15.008 USD over 16,762 calls. The cap was 15.0 USD; the calls in flight passed it.

Every question of the plan:

| question | contrast | n | difference | 95% interval | gains / losses | p | plan verdict |
|---|---|---:|---:|---|---:|---:|---|
| Q1, primary | `retrieved_task` − `placebo` | 193 | +0.218 | [+0.158, +0.282] | 43 / 1 | 1.0e-11 (Holm) | POSITIVE |
| Q2, primary | `retrieved_task` − `mismatched_type` | 189 | +0.159 | [+0.103, +0.220] | 32 / 2 | 6.9e-08 (Holm) | POSITIVE |
| Q3, secondary | `mismatched_type` − `none` | 189 | +0.063 | [+0.006, +0.121] | 21 / 9 | 0.043 (uncorrected) | — |
| Q4, secondary | steps, `retrieved_task` − `none` | 194 | median −7 steps | — | — | Wilcoxon z = −9.04, p ≈ 1.6e-19 | — |
| Q5, exploratory | Q1 within transform / other | 95 / 98 | +0.368 / +0.071; difference +0.297 | bootstrap [+0.183, +0.402] | — | — | — |
| descriptive | `retrieved_task` − `none` | 194 | +0.222 | [+0.162, +0.286] | 44 / 1 | — | — |
| descriptive | `placebo` − `none` | 193 | +0.005 | [−0.047, +0.057] | 13 / 12 | — | — |

The plan's format check, which flags a placebo-versus-memory gap above 0.03 per step on untagged or no-tag answers, was
not triggered. The no-tag rate was at most 0.007 per step in any arm.

**Corrected claim.** In this side study, on DeepSeek V4.1 Flash in ALFWorld V6 HARD mode, two expert walkthroughs of the
same task type raised the solve rate:
- by +0.218 over the length-matched neutral filler (193 pairs);
- by +0.159 over length-matched walkthroughs of another task type (189 pairs).

Both meet the plan-defined POSITIVE rule after Holm correction.

**What it does not show.**
- **Q2 does not separate procedural content from matched vocabulary, object names or concrete commands.** The matched
  walkthroughs carry all of them.
- **Exposure is not balanced between the Q2 arms.** This is the same issue the
  [V5B secondary-contrast addendum](errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md) found for this
  control. Counted from the private logs over the 189 Q2 games (378 uses per arm):

  | arm | distinct walkthroughs | uses by the ten most used | most uses of one walkthrough |
  |---|---:|---:|---:|
  | `retrieved_task` | 222 | 44 of 378 | 6 |
  | `mismatched_type` | 144 | 105 of 378 | 20 |

  The control repeats a few walkthroughs across many games. As a descriptive check, dropping the 85 games that were shown
  any of the control's ten most used walkthroughs leaves 104 games with +0.183 (20 / 1). This is a chosen subgroup, not
  an estimate.
- **Where the gain sits is exploratory (Q5).**
  - Most of it comes from heat games, where the model without memory almost always failed: `none` 4 of 31, `placebo`
    3 of 31, `retrieved_task` 29 of 31. In net games gained over `placebo`, heat accounts for 26 of 42.
  - In the other types, `placebo` already solved most games, which limits the possible gain.
- **Q3 is only suggestive.** It is uncorrected, with a lower bound near zero. It suggests that even walkthroughs of
  another task type help a little in HARD mode; showing the command grammar in use is one possible route, not tested. It
  says nothing about the normal mode.
- **Q4 mostly mirrors success**, because failures count as 50 steps.
- **Limits:** one model, one environment, one sample per cell, no reproducible sampling.

## DS-HARD-2: which form of the walkthroughs carries the gain

**Setup.**
- **Model and run:** as DS-HARD-1, in one run on 2026-11-22, 11:46–12:16 UTC, after DS-HARD-1 and not interleaved with
  it.
- **Arms:** 4.
  - `retrieved_task`: the walkthroughs in full;
  - `retrieved_steps`: their actions only;
  - `retrieved_plan`: a rule-based subgoal plan without numbers and room-specific locations, which keeps the verbs and
    the object and appliance classes;
  - `placebo`.

  The two reduced forms are padded with filler to the length of the `retrieved_task` block, as in V6.
- **Games:** 100 of the 200 DS-HARD-1 games (50 transform, 50 other), chosen by a hash rule and frozen before any
  DS-HARD-2 data.
  - After the freeze, DS-HARD-1's aggregate outcomes on these games were seen while the analyzer was tested. They enter
    no DS-HARD-2 test.
  - All 3 treatment arms of a game showed the same two walkthroughs, the same as DS-HARD-1's `retrieved_task` on the 99
    games both recorded.
- **Plan:** revision r2, written before the data after an internal pre-run review of r1 by a Claude model (Sonnet; same family as the
  authors).
  The evidence is file times; that review also found no DS-HARD-2 output or spend ledger in the study folder. Two
  primaries, with Holm correction.
- **Completeness:** 400 of 400 episodes, 0 errors, 0 exclusions. Block lengths were within −0.6% and +0.9% of the target.
  The contracts held: no digit in any plan, no observation text in any actions block.
- **Cost:** 6.317 USD over 6,997 calls (cap 10.0 USD).

Every question of the plan:

| question | contrast | n | difference | 95% interval | gains / losses | p | plan verdict |
|---|---|---:|---:|---|---:|---:|---|
| P1, primary | `retrieved_plan` − `placebo` | 100 | +0.130 | [+0.051, +0.213] | 15 / 2 | 0.0030 (Holm) | POSITIVE |
| P2, primary | `retrieved_steps` − `placebo` | 100 | +0.150 | [+0.062, +0.240] | 18 / 3 | 0.0030 (Holm) | POSITIVE |
| S0, in-run anchor | `retrieved_task` − `placebo` | 100 | +0.190 | [+0.101, +0.283] | 21 / 2 | 6.6e-05 | — |
| S1, abstraction | `retrieved_plan` − `retrieved_steps` | 100 | −0.020 | [−0.086, +0.043] | 3 / 5 | 0.73 | NULL-INFORMATIVE |
| S2, share of the gain kept | (form − `placebo`) / (`retrieved_task` − `placebo`) | 100 | plan 0.68, actions 0.79 | paired bootstrap: plan [0.42, 0.94], actions [0.54, 0.95] | — | — | — |
| S3 | `retrieved_plan` − `retrieved_task` | 100 | −0.060 | [−0.129, −0.001] | 1 / 7 | 0.070 | — |
| S3 | `retrieved_steps` − `retrieved_task` | 100 | −0.040 | [−0.098, +0.007] | 0 / 4 | 0.13 | — |
| S4, steps | mean steps: plan 17.5, actions 15.5, full 13.1, `placebo` 23.9 | 100 | plan − placebo, actions − placebo, full − placebo, plan − actions | — | — | Wilcoxon z = −4.65, −4.88, −5.86, +1.47; p ≈ 3e-06, 1e-06, 5e-09, 0.14 | — |
| S5, exploratory | P1, P2, S1 within transform / other | 50 / 50 | P1 +0.20 / +0.06; P2 +0.24 / +0.06; S1 −0.04 / 0.00 | bootstrap of the difference: P1 [−0.02, +0.28], P2 [+0.02, +0.34], S1 [−0.16, +0.06] | — | — | — |
| S6, descriptive across runs | DS-HARD-1 on these games: `none` 0.737, `placebo` 0.768, `retrieved_task` 0.980, `mismatched_type` 0.818 (n = 99) | — | — | — | — | — | — |
| rule G, syntax | grammar-malformed commands per step, every arm | — | 0.0000 | — | — | — | not flagged (taken from the result file; not recomputed here) |

**Corrected claim.** On 100 ALFWorld games in HARD mode on DeepSeek V4.1 Flash:
- the plan without numbers and room-specific locations raised the solve rate over the length-matched placebo by +0.130;
- the actions alone raised it by +0.150;
- in the same padded layout, plan minus actions was −0.020, inside the plan-defined ±0.10 margin;
- the plan kept an estimated 0.68 of the full walkthroughs' gain over placebo (95% interval 0.42 to 0.94), and the
  actions 0.79 (0.54 to 0.95).

A form without numbers and concrete locations can raise success in these conditions. How much the action names, the
appliance classes and the order of subgoals each contribute is not resolved.

**What it does not show.**
- **Not "an abstract strategy carries the gain".** The plan keeps the verbs and the object and appliance classes (for
  example "heat the X with the microwave").
- **Not "the plan keeps most of the gain".** The interval of its share reaches below one half.
- **Plan against the full walkthroughs is borderline.** The exact McNemar test gives p = 0.070 (1 / 7), while the
  Newcombe interval [−0.129, −0.001] just excludes zero. The two methods disagree at the margin, so this contrast is
  neither shown equal nor clearly shown worse.
- **Actions against the full walkthroughs:** p = 0.13 (0 / 4), interval [−0.098, +0.007]. Only the actions met the ±0.10
  criterion. S3 also changes the layout (padded against unpadded), not only the form.
- **No `none` arm was run.** Which games the model fails without help is known only from DS-HARD-1, run earlier the same
  day and not interleaved with this run.
  - The per-type counts are descriptive. The largest net gain of both forms was in heat games: `placebo` 4 of 15; plan
    and actions 10 of 15 each; full walkthroughs 14 of 15.
  - Not every other type was at the ceiling (clean: `placebo` 15 of 18).
- **Same population, not an independent replication.** S0 (+0.190) repeats DS-HARD-1 Q1 (+0.218) on a subset of the same
  games, with the same walkthroughs, model and mode. A same-unit check between the two runs on the 99 shared games:
  `retrieved_task` moved by −0.030 (1 / 4) and `placebo` by −0.010 (7 / 8).
- **Power** (from the plan's simulations): a form that keeps half of the gain is detected about 60% of the time. A
  NULL-INFORMATIVE S1 means no loss of 0.10 or more was detected, not that there is no loss.

## NEMO-FLOOR: can walkthroughs lift a weak 12B model off the HARD-mode floor?

**Setup.**
- **Model:** Mistral Nemo 12B (`mistralai/mistral-nemo`) through OpenRouter, pinned to one provider (DeepInfra, FP8, no
  fallbacks). All 14,005 served calls came from it.
- **Settings:** temperature 0.7, no seed, 50 steps, HARD mode, one sample per cell.
- **Arms:** `none`, `placebo`, `retrieved_task`.
- **Calls:** 2026-11-22 18:50 UTC to 2026-11-23 02:33 UTC.
- **Games:** 100 of the DS-HARD-1 games, with the 20 games of the NEMO-1 qualification pilot excluded. The same
  walkthroughs and placebo blocks as DS-HARD-1.
- **Plan:** written before the data on 2026-11-22 and revised, still before the data, after a design review by a Claude
  model (Sonnet). The evidence is file times. One primary, no multiplicity correction, and a futility stop after 40
  games (not triggered: 8 gains, 0 losses).

**Completeness:** 300 of 300 episodes, 100 complete games, 0 errors in the recorded episodes. As the plan prescribes,
errored episodes were re-run once with fresh samples: 5 in stage 1 by the run log, none listed for stage 2. The
discarded attempts are not kept.

**Cost:** 0.933 USD over 14,518 ledger rows (provider-reported 0.724 USD), cap 2.0 USD.

Every question of the plan:

| contrast | n | difference | 95% interval | gains / losses | p | plan verdict |
|---|---:|---:|---|---:|---:|---|
| `retrieved_task` − `placebo` (primary) | 100 | +0.200 | [+0.122, +0.289] | 20 / 0 | 1.9e-06 | POSITIVE |
| `retrieved_task` − `none` (secondary, uncorrected) | 100 | +0.210 | [+0.130, +0.301] | 21 / 0 | 9.5e-07 | — |
| `placebo` − `none` (descriptive) | 100 | +0.010 | [−0.037, +0.061] | 2 / 1 | — | — |
| steps, `retrieved_task` − `placebo` (descriptive) | 100 | — | — | — | Wilcoxon z = −4.11, p ≈ 3.9e-05 | — |

- Solved games: `none` 1 of 100, `placebo` 2 of 100, `retrieved_task` 22 of 100.
- The plan's floor premise (`none` and `placebo` each ≤ 0.10) holds.
- The plan also asks for per-type counts and for format counters; both are given below.

**The plan-defined reading: a floor lift, not a general memory gain.** Task-memory walkthroughs lift Mistral Nemo 12B off
the HARD-mode floor, from 2 of 100 (`placebo`) to 22 of 100 (`retrieved_task`). This is all the study claims.

- **Most games stay unsolved, and the lift is uneven.** 78 of 100 games stay unsolved. Solved with memory, by type
  (descriptive):

  | type | solved with memory |
  |---|---:|
  | `pick_and_place` | 10 of 16 |
  | heat | 4 of 17 |
  | clean | 3 of 18 |
  | `look_at` | 3 of 15 |
  | `pick_two` | 2 of 20 |
  | `pick_cool` | 0 of 14 |

  `placebo` solved one `pick_and_place` game and one `look_at` game and nothing else. In net games gained over
  `placebo`, 9 of 20 are `pick_and_place` and 7 are transform games.
- **It does not separate three routes:**
  - (a) learning the HARD-mode command format and the object names from the walkthroughs' exact command strings; there
    is no `mismatched_type` arm to control this;
  - (b) following a similar walkthrough's command sequence;
  - (c) understanding the task.
- **Route (a) is visibly active.** Invalid commands per step fall from 0.786 (`none`) and 0.759 (`placebo`) to 0.549
  (`retrieved_task`).
- **Route (b) is plausible in some games.** In 10 games a shown walkthrough comes from the same ALFWorld floor plan as
  the test game, and 4 of those were solved.
- **What it does not show.** It says nothing about models that can already play, and it must not be cited as evidence
  of task understanding.
- **Power** (from the plan): a lift of 0.10 or more was well powered, about 0.85 to 0.9 with the futility stop. Below
  about 0.08, INCONCLUSIVE would have been the likeliest outcome.

## NEMO-1: the DS-HARD-1 contrasts on Mistral Nemo 12B in the lab's normal mode

**Setup.**
- **Model:** as NEMO-FLOOR: Mistral Nemo 12B (`mistralai/mistral-nemo`) through OpenRouter, pinned to DeepInfra (FP8,
  no fallbacks). All 33,689 calls in the recorded episodes were served by it.
- **Settings:** temperature 0.7, kept from DS-HARD-1 although Mistral recommends 0.3 for this model; no seed, 50 steps,
  one sample per cell.
- **Mode: normal.** The prompt is the V6 instrument's own prompt, with the list of admissible actions, as in the lab's
  Qwen runs. DS-HARD-1 used HARD mode.
- **Design:** the DS-HARD-1 design on the same population.
  - The same 200 games and 800 jobs: the jobs file is a byte copy of DS-HARD-1's.
  - The same 4 arms and seed label 0; the placebo and control blocks matched in length with the Qwen tokenizer, through
    DS-HARD-1's token cache.
  - The same shown walkthroughs: in each of the 581 `placebo`, `retrieved_task` and `mismatched_type` episodes that
    both runs recorded, the recorded memory sources equal DS-HARD-1's (counted from the private logs).
- **Calls:** the main run on 2026-11-23, 05:26–21:41 UTC, after NEMO-FLOOR and after the r3 qualification pilot above.
  The 20 pilot games are among the 200; the main run re-ran them, and the pilot episodes are not analysed.
- **Plan:** revision r3, written before any r3 data on 2026-11-22 (evidence: file times).
  - Revisions: r1 in HARD mode (an internal design review by a Claude model, Sonnet, gave NO-GO); r2 in HARD mode with
    the qualification pilot above (NO-GO); r3 in the normal mode, revised after a second internal design review (Sonnet).
  - Two primaries, with Holm correction.
  - The unit set is the complete games, those with all four arms recorded without an error. DS-HARD-1 used all
    available pairs; the plan reports that as a sensitivity row.
  - The plan's expectation, before the data: if DS-HARD-1's HARD-mode gain came from producing commands, the
    admissible-action list removes that route and Q1 could be near zero.
  - **Power** (from the plan): about 0.4 to 0.6 for a true difference of 0.10, so the plan named INCONCLUSIVE as the
    likeliest outcome.

**Completeness.**
- 800 of 800 episodes, 200 complete games, 0 errors, one run with no resumes.
- One agent version in all 800 episodes; 0 misses of the strict Qwen token cache.
- Four `mismatched_type` games were excluded from Q2 and Q3 by the plan's length rule (|length difference| > 10%). All
  four were unsolved in both Q2 arms, so they do not change Q2's gains and losses.
- The blocks were matched in length with the Qwen tokenizer. Under Mistral's tokenizer, the mean length ratio to
  `retrieved_task` (step-0 prompt minus `none`) was 0.985 for `placebo` (0.947 to 1.004) and 0.996 for `mismatched_type`
  (0.858 to 1.046), on 200 games.

**Cost.**
- Main run: 2.632 USD over 33,775 calls (provider-reported 2.100 USD). Qualification pilot r3: 0.258 USD.
- The cap was 4.9 USD on the total of all Mistral ledgers, NEMO-FLOOR included. The NEMO-1 ledgers (probe, smoke test,
  both pilots, main run) total 3.215 USD; NEMO-FLOOR's 0.933 USD (above) is not in that total.

Every question of the plan:

| question | contrast | n | difference | 95% interval | gains / losses | p | plan verdict |
|---|---|---:|---:|---|---:|---:|---|
| Q1, primary | `retrieved_task` − `placebo` | 200 | +0.130 | [+0.054, +0.205] | 44 / 18 | 0.0026 (Holm) | POSITIVE |
| Q2, primary | `retrieved_task` − `mismatched_type` | 196 | +0.082 | [+0.005, +0.157] | 37 / 21 | 0.048 (Holm) | POSITIVE |
| Q3, secondary | `mismatched_type` − `none` | 196 | +0.041 | [−0.026, +0.108] | 26 / 18 | 0.29 (uncorrected) | — |
| Q4, secondary | steps, `retrieved_task` − `none` | 200 | median paired difference 0 steps | — | — | Wilcoxon z = −4.28, p ≈ 1.9e-05 | — |
| Q5, exploratory | Q1 within transform / other | 100 / 100 | +0.210 / +0.050; difference +0.160 | bootstrap [+0.010, +0.310] | — | — | — |
| descriptive | `retrieved_task` − `none` | 200 | +0.115 | [+0.043, +0.186] | 39 / 16 | 0.0027 | — |
| sensitivity | Q1 without the 20 pilot games | 180 | +0.139 | [+0.058, +0.218] | — | 0.0013 (uncorrected) | — |
| sensitivity | Q2 without the 20 pilot games | 176 | +0.091 | [+0.009, +0.171] | — | 0.040 (uncorrected) | — |

- Solved games: `none` 46, `placebo` 43, `retrieved_task` 69 and `mismatched_type` 53, of 200.
- No floor or ceiling flag of the plan fired. The all-pairs sensitivity rows equal the primary rows, because every game
  is complete.
- The plan's classification rule, fixed before the data, gives "SAME PATTERN AS DS-HARD-1 (cross-model and
  cross-mode)": both primaries POSITIVE, with no floor flag on Q2. The plan defines this as the same direction and
  significance pattern on the same contrasts; it compares effect sizes only descriptively.
- **Invalid commands.** In the normal mode an invalid command is one not on the admissible list. Per step: `none` 0.170,
  `placebo` 0.200, `retrieved_task` 0.281, `mismatched_type` 0.223. The analyzer applies the plan's format flags only to
  the untagged and no-tag counters (at most 0.002 per step in any arm). The plan does not say whether invalid commands
  are a format counter. So more invalid commands with memory were not flagged, although `retrieved_task` − `placebo` is +0.081 per
  step and every arm is above 0.10 per step.

**Corrected claim.** In this side study, on Mistral Nemo 12B in ALFWorld V6 normal mode, two expert walkthroughs of the
same task type raised the solve rate:
- by +0.130 over the length-matched neutral filler (200 games);
- by +0.082 over length-matched walkthroughs of another task type (196 games).

Both meet the plan-defined POSITIVE rule after Holm correction; Q2 only just.

**What it does not show.**
- **Not a replication of DS-HARD-1.** The games, walkthroughs, arms and statistics are the same, but the model and the
  prompt mode both differ. Effect sizes are compared only descriptively: DS-HARD-1 gave Q1 +0.218 and Q2 +0.159.
- **Q2 is borderline.** Its Holm p is 0.048 and its interval's lower bound is +0.005. The lab's review noted that one
  game's outcome changing could move p above 0.05 and the classification to the plan's "PARTIAL". With one sample per
  cell and no seed, Q2 is weak support.
- **Q2 does not separate procedural content from matched vocabulary, object names or concrete commands**, as in
  DS-HARD-1. The control arm shows the same walkthroughs as there, so the exposure imbalance described under DS-HARD-1
  applies here as well.
- **Normal mode, not command production.** With the admissible list shown, memory can help by choosing among listed
  commands. The result says nothing about producing commands. The plan had named a Q1 near zero as an outcome
  consistent with DS-HARD-1 in this mode; Q1 was positive.
- **Where the gain sits is exploratory (Q5).** Solved games by type (descriptive):

  | type | games | `none` | `placebo` | `retrieved_task` | `mismatched_type` |
  |---|---:|---:|---:|---:|---:|
  | `pick_and_place` | 30 | 18 | 21 | 23 | 21 |
  | `pick_two` | 38 | 7 | 8 | 7 | 5 |
  | `look_at` | 32 | 12 | 8 | 12 | 7 |
  | `pick_clean` | 34 | 3 | 1 | 5 | 7 |
  | `pick_cool` | 34 | 3 | 2 | 10 | 6 |
  | `pick_heat` | 32 | 3 | 3 | 12 | 7 |

  - Of the net 26 games gained over `placebo`, 21 are transform games: heat 9, cool 8, clean 4.
  - On `pick_two` and `look_at`, `retrieved_task` solved as many games as `none`.
  - The transform types start near the floor without memory, so the split confounds task type with headroom.
- **Q4 mostly mirrors success**, because failures count as 50 steps; the median paired difference is 0 steps.
- **Limits:** one model at one pinned provider with FP8 weights, one environment (ALFWorld V6 `train` games), one sample
  per cell, no reproducible sampling, and a temperature above the model's recommended one.

## Across the studies

- **Models and modes are confounded.** The lab's V6 measures Qwen3-4B in normal mode. These studies measure DeepSeek
  V4.1 Flash in HARD mode, and Mistral Nemo 12B in HARD mode (NEMO-FLOOR) and in normal mode (NEMO-1). Any comparison of
  gain sizes, or of which task types gain, is descriptive. Net games gained over `placebo`:

  | model (run) | net games | heat | clean and cool | `pick_and_place` |
  |---|---:|---:|---:|---:|
  | DeepSeek (DS-HARD-1) | 42 | 26 (62%) | 9 | — |
  | Qwen (V6 `per_unit.csv`, seed 0) | 39 | 10 (26%) | 27 | — |
  | Mistral Nemo (NEMO-FLOOR, HARD mode) | 20 | 4 | — | 9 |
  | Mistral Nemo (NEMO-1, normal mode) | 26 | 9 (35%) | 12 | 2 |

  Whether the admissible-action list of the normal mode already supplies the heat command is an untested hypothesis.
- **Same games, correlated results.** All studies use V6 games. NEMO-1 uses the DS-HARD-1 games, and NEMO-FLOOR and
  DS-HARD-2 use subsets of them. Outcomes are correlated through game difficulty; the studies are not independent samples of games.
- **Expert walkthroughs only.** All memory here is a bank of expert walkthroughs, not the agent's own earlier episodes.

## Source files

The per-game tables are in `data/lab/side-runs-2026-11/`. The plans, result files, outputs and spend ledgers are not
published:
- the outputs hold the full action logs;
- the plans and result files contain machine-local paths and internal budget and coordination notes.

Their SHA-256 are commitments for a later release:

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
| NEMO-1 pilot outputs `out_nemo_1_pilot.jsonl` | `4d759d857a0d5cceee7877e23bc939005709780d01778aaab6250449307c87fb` |
| NEMO-1 plan `NEMO_1_PLAN.md` (r3) | `2b3f48e7cf488c45734c996466f5e8faf9319493e4028584394ea8a8baed53ff` |
| NEMO-1 pilot r3 outputs `out_nemo_1_pilot_r3.jsonl` | `c9fd67e019672e673051954cc1c09245dc54a7dd2d5d33e72fcb8c43239d62cf` |
| NEMO-1 pilot r3 result `PILOT_NEMO_1_r3.md` | `ac38608ccf04cf1fd024b8cf58bb34905988bf39227a38f127a7646a644dcb82` |
| NEMO-1 result `RESULT_NEMO_1.md` | `b3b499be350f41fbc6cfdb6de093b7c28f8a793892378d73a7df07af3e26d52b` |
| NEMO-1 summary `summary_nemo_1.json` | `d58f90c223fbb02020723e518caa2578afed1969a667a4c35fbf75692aee63ac` |
| NEMO-1 outputs `out_nemo_1.jsonl` | `3eda895f601494a0ebaf86e08ddc4331b9a5ee8f73f31f48ad20cf9752f2b59c` |
| NEMO-1 jobs `batch_nemo_1.jsonl` (equal to the DS-HARD-1 jobs) | `d2e42fa532391c7ea1c2d76d9ceb57314043cb26a48cf352663dc5e141a63d12` |
| DeepSeek pilot rule `PILOT_RULE.md` | `a5d9ebea4adf5a8b82528fa033a02aa722610538eec985a35649854f5d41cf3d` |
| DeepSeek pilot result `RESULT_PILOT.md` | `2e6895ec44d7cb251a550eaf8de163ab9e861b3669093fe3045b5acbc03bc767` |
| HARD pilot rule `PILOT_HARD_RULE.md` | `68993794a950e2cddece3874c89a1c6a950a48ecb70198ee770aa8d51864035f` |
| HARD pilot result `RESULT_PILOT_HARD.md` | `fb75285b9cb2c6551d6a83318d1f248be529b62fd302b80b0b721e4b44ed950a` |
| DeepSeek pilot outputs `out_pilot.jsonl` | `2d418fbbfe724f59956bfdc5fe3fa21a3db539d7c6b035df16cd5dd80cef1554` |
| HARD pilot outputs `out_pilot_hard.jsonl` | `28a1332f58f0b52d5d009aeb63b0450056a2e289c218023f33519aa27f07d033` |

Related:
- [V6 addendum: seed-1 re-run and the D8 instruction arm](errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md);
- [V5B addendum: seed-1 re-run](errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md);
- [what we know so far](evidence-summary-2026-11.md).
