# What we know so far: experience memory in ALFWorld, November 2026

Status: graded summary; no new measurements. Added 2026-11-23; NEMO-1 added 2026-11-24.

This page grades the claims that the published lab programs and the exploratory side runs support so far. It adds no
measurement of its own. Every number is taken from the document it cites, where it is recomputed:
- **lab numbers** come from the package READMEs, which `scripts/verify_autolab_packages.py` recomputes;
- **side-run numbers** come from the addenda and the side-studies note, whose solve-rate numbers can be recomputed from
  the per-game tables in [`data/lab/side-runs-2026-11/`](../../data/lab/side-runs-2026-11/README.md).

Where the lab has published a state (`positive`, `inconclusive`, ...), that state rules. Numbers from side runs never
override it.

## Scope

- ALFWorld text games only, all of them `train` games. Their rooms were seen when the bank was built; `valid_unseen` is
  not used.
- A bank of **expert walkthroughs**, not the agent's own earlier episodes.
- Three models. Qwen3-4B in the normal mode (lab programs); DeepSeek V4.1 Flash in HARD mode; Mistral Nemo 12B in HARD
  mode (NEMO-FLOOR) and in the normal mode (NEMO-1). The last two are side studies. Model and mode are therefore
  confounded in every comparison between models, except Qwen against NEMO-1, which share the normal mode. That
  comparison still differs in game set and provider, and is descriptive.

## Terms

- **Normal mode:** the prompt lists the admissible actions.
- **HARD mode:** the prompt gives only the command grammar.
- **placebo:** a neutral filler block with the same length as the memory block.
- **SESOI:** the smallest effect of interest, 0.12.
- **`practical`:** the lab's state for an interval whose lower bound reaches the SESOI.
- **D8:** the lab's label for the hypothesis that the walkthroughs mainly teach the clean / cool / heat convention.
- **Plan written before the data:** for side runs, a plan whose timing rests on file times, not on a registry.

## Sources

Short names used below:
- **Lab packages:** [V4](../../data/lab/autolab-alfworld-ladder-r4-v4/README.md),
  [V5B](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md) and
  [V6](../../data/lab/autolab-alfworld-ladder-r4-v6/README.md).
- **Addenda:** [V5B secondary contrast](errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md),
  [V5B seed 1](errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md) and
  [V6 seed 1 and D8](errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md).
- **The [side-studies note](side-studies-2026-11.md):** DS-HARD-1, DS-HARD-2, NEMO-FLOOR, NEMO-1 and the pilots.

## Runs since V6 was published

Every run since V6 was published, including the ones not reported here:

| run | what | where | status |
|---|---|---|---|
| First D8 pilot | `d8_instruction` on the 114 V5B transform games, Qwen | V6 addendum, section 2 | reported (recomputed; no result file was written) |
| D8 on V6 games | `d8_instruction` on the 300 V6 games, Qwen | V6 addendum, section 2 | reported |
| V5B seed 1 | `none`, `retrieved_task` at seed 1, 201 games, Qwen | V5B seed-1 addendum | reported |
| V6 seed 1 | `placebo`, `retrieved_task` at seed 1, 300 games, Qwen | V6 addendum, section 1 | reported |
| DeepSeek pilots | 20 games, normal and HARD mode | side-studies note | reported as pilots |
| DS-HARD-1, DS-HARD-2 | DeepSeek V4.1 Flash, HARD mode | side-studies note | reported |
| Mistral probe and NEMO-1 smoke test | 1 and 5 API calls, one unfinished episode | — | not a result (no episode finished) |
| NEMO-1 pilot, revision r2 | Mistral Nemo 12B, HARD mode, 20 games | side-studies note | reported as a pilot (NO-GO) |
| NEMO-FLOOR | Mistral Nemo 12B, HARD mode, 100 games | side-studies note | reported |
| NEMO-1 pilot, revision r3 | Mistral Nemo 12B, normal mode, the same 20 games | side-studies note | reported as a pilot (GO) |
| NEMO-1 | Mistral Nemo 12B, normal mode, the 200 DS-HARD-1 games | side-studies note | reported (added 2026-11-24) |
| Faster-serving benchmark | vLLM serving flags on recorded V6 prompts | — | engineering measurement, no memory contrast; not reported here |

## Grades

- **strong:** seen with at least two models or two seeds, on a contrast fixed before the data, where at least one leg is
  a lab program. For side runs, "before the data" rests on file times, not on a registry.
- **moderate:** consistent, but exploratory, resting on one valid measurement, or with one leg only from a side run.
- **weak:** a single result, a result across runs, or a subgroup chosen after the data.
- **contradictory or model-dependent:** the results disagree between models, modes or seeds.

## Strong

**Claim.** Two goal-similar expert walkthroughs raise the solve rate above a length-matched neutral filler block.

**Rests on:**
- V5B `retrieved_task − placebo` +0.169 [+0.053, +0.285], `positive` (results table);
- V6 +0.130 [+0.049, +0.211], `positive` (results table);
- V6 at seed 1: +0.157; two-seed estimate +0.143 [+0.090, +0.196] (V6 addendum, section 1);
- DS-HARD-1 Q1 +0.218 [+0.158, +0.282];
- DS-HARD-2 S0 +0.190, on the same population as DS-HARD-1;
- NEMO-FLOOR +0.200, a floor lift (side-studies note);
- NEMO-1 Q1 +0.130 [+0.054, +0.205], Mistral Nemo in the normal mode, on the DS-HARD-1 games (side-studies note).

**Limits:**
- Among V5B and V6, no lab interval is `practical`: every lower bound is below the SESOI. The lab's level for these
  findings is `developmental`.
- This is a gain over the filler, not over no memory. Against `none`, see the weak table: the filler itself runs about
  0.06 below `none` in V5B and V6.
- The seed-1 runs are consistency checks, not independent replications. DS-HARD-2 repeats DS-HARD-1 on a subset of the
  same games.
- V4 is left out because of its measurement problem.

## Moderate

### Walkthroughs of the right task type beat length-matched walkthroughs of another type

**Rests on:**
- V5B `retrieved_task − mismatched_type` +0.154 [+0.035, +0.273], `positive`. This is a secondary contrast, named
  before the measurement and reported later (V5B secondary-contrast addendum).
- DS-HARD-1 Q2 +0.159 [+0.103, +0.220], plan-defined POSITIVE (side-studies note).
- NEMO-1 Q2 +0.082 [+0.005, +0.157], plan-defined POSITIVE but borderline (Holm p = 0.048), on the same games and
  walkthroughs as DS-HARD-1 (side-studies note).

**Limits:**
- In V5B and DS-HARD-1, the control repeats a few walkthroughs across many games (NEMO-1 shows the same control
  walkthroughs as DS-HARD-1; not counted separately):
  - in V5B, its ten most used walkthroughs account for 131 of 402 uses;
  - in DS-HARD-1, for 105 of 378 uses (the matched arm: 44 of 378).
- None of the three separates knowing the procedure of the type from matched vocabulary, object names or concrete
  commands.
- The side-study legs are one sample per cell. DS-HARD-1 and NEMO-1 share the games and the walkthroughs, so they are
  not independent samples.

### The actions alone, without the observation text, already beat the placebo

**Rests on:**
- V6 `retrieved_steps − placebo` +0.137 [+0.055, +0.219], `positive`, `open`;
- DS-HARD-2 P2 +0.150 [+0.062, +0.240], plan-defined POSITIVE.

**Limits:**
- Graded moderate because the second leg is a 100-game side run on another model and in another mode.
- The V6 interval is not `practical`.
- The actions keep the verbs, objects and appliances. Both arms are padded to the full block length.

### For Qwen, DeepSeek (HARD mode) and Mistral Nemo (normal mode only), more of the gain over the filler falls in transform games (clean / cool / heat) than in the others

**Rests on** transform − other, the difference of the two stratum differences:
- Qwen V6 against `placebo`: +0.232 [+0.103, +0.360] at seed 0 and +0.231 [+0.102, +0.361] at seed 1; two-seed means
  +0.231 [+0.129, +0.334] (V6 addendum, section 1).
- DeepSeek DS-HARD-1 Q5: +0.297, bootstrap [+0.183, +0.402] (side-studies note).
- Mistral Nemo NEMO-1 Q5: +0.160, bootstrap [+0.010, +0.310], lower bound near zero (side-studies note).

**Limits:**
- The split was chosen after V5B had shown where the gain sits, so it is exploratory.
- The strata differ in baseline as well as in type: in V6, `placebo` solves 0.40 of the transform games and 0.55 of the
  others.
- **V5B does not support the pattern at seed 1.** Against `none`, V5B's difference of differences is +0.213
  [+0.052, +0.375] at seed 0, but only +0.084 [−0.077, +0.245] at seed 1 (V5B seed-1 addendum).
- **It does not hold for Mistral Nemo in HARD mode** (NEMO-FLOOR): 7 of its net 20 games gained are transform games, and
  9 are `pick_and_place`.
- In NEMO-1 the transform types start near the floor without memory (3 of 32 to 34 solved by `none` in each), so the
  split confounds task type with headroom there as well.

### A rule-based plan without numbers and room-specific locations beats the placebo, and is not detectably worse than the actions alone

**Rests on:**
- DS-HARD-2 P1 +0.130 [+0.051, +0.213], plan-defined POSITIVE;
- DS-HARD-2 S1, plan − actions: −0.020 [−0.086, +0.043], inside ±0.10;
- the plan's share of the gain kept: 0.68 [0.42, 0.94] (side-studies note).

**Limits:**
- There is only one valid measurement. In V6 the plan arm has a format measurement problem.
- The plan keeps the verbs and appliance classes.
- The share's interval reaches below one half.
- Against the full walkthroughs the plan is borderline (McNemar p = 0.070; the interval just excludes zero).

## Weak

### For Qwen, the full walkthroughs (`retrieved_task`) raise the solve rate above no memory

**Rests on:**
- V5B `retrieved_task − none` +0.109 [−0.007, +0.226], `inconclusive` (results table);
- V6 +0.073 [−0.009, +0.156], `inconclusive` (results table);
- V5B at seed 1: +0.174, McNemar p 6.5e-05 (V5B seed-1 addendum).

**Limits:**
- For `retrieved_task`, the lab's own intervals include zero in both programs. Only the exploratory seed-1 re-run is
  clearly positive.
- In V6, the two other renderings are `positive` against `none`, with lower bounds at about zero: `retrieved_steps − none`
  +0.080 [+0.000, +0.160] and `retrieved_plan − none` +0.073 [+0.002, +0.145]. The plan arm has a format measurement
  problem.
- All of these are secondary contrasts.

### For Qwen, any added block (filler or instruction) lowers the solve rate a little against no memory (in V6 mostly on the non-transform games; V5B does not show that split)

**Rests on:**
- `placebo − none`: V4 −0.023, `equivalent`; V5B −0.060 and V6 −0.057, both `inconclusive` (results tables).
- On V6's 149 non-transform games: `placebo − none` −0.087 (12 / 25, p = 0.047), and the D8 sentence −0.107 against
  `none`, across runs (V6 addendum, section 2).
- DeepSeek in HARD mode: +0.005 [−0.047, +0.057] (DS-HARD-1).

**Limits:**
- No lab interval excludes zero.
- The D8 sentence is −0.020 against the filler on the non-transform games, so its drop against `none` is shared with
  the content-free block. It is not attributable to the sentence.
- `none` itself moves between seeds on such games (V5B: 0.667 to 0.598).

### Qwen gains no net games on `pick_two`

**Rests on:** V6 net games over `placebo` on the 53 `pick_two` games: −5 at seed 0 and 0 at seed 1 (V6 addendum,
section 1, per-type table).

**Limits:** a per-type stratum chosen after the data, one of six types; two seeds of the same games.

## Contradictory or model-dependent

### Which task types gain? (net games over `placebo`)

- **DeepSeek, HARD mode:** 26 of its net 42 in heat games (side-studies note).
- **Qwen, normal mode** (V6 seed 0): 27 of its net 39 in clean and cool, 10 in heat.
- **Mistral Nemo, HARD mode:** 9 of its net 20 in `pick_and_place`, 4 in heat (side-studies note).
- **Mistral Nemo, normal mode** (NEMO-1): 9 of its net 26 in heat, 12 in clean and cool, 2 in `pick_and_place`
  (side-studies note).

**Reading:** "the gain is in heating" holds for DeepSeek in HARD mode only. Model and mode are confounded, except between
Qwen and NEMO-1, whose comparison still differs in game set and provider. One untested explanation is that the normal mode's admissible-action list already offers the heat
command.

### Do walkthroughs of another type help? (against `none`)

- **DeepSeek, HARD mode:** `mismatched_type − none` +0.063 [+0.006, +0.121], uncorrected (DS-HARD-1 Q3).
- **Qwen, normal mode:** V5B `mismatched_type − none` −0.045 [−0.135, +0.045], `inconclusive`.
- **Mistral Nemo, normal mode:** `mismatched_type − none` +0.041 [−0.026, +0.108], uncorrected (NEMO-1 Q3).

**Reading:** between DeepSeek and the others, both model and mode differ. In the normal mode neither interval excludes
zero. In HARD mode any walkthrough also shows the command grammar in use; that route
is untested.

### What does the D8 sentence do on transform games? (against `none`, across runs)

- **V5B games:** d8 − none +0.140 [+0.041, +0.235]; retrieved − d8 +0.061 [−0.049, +0.169] (first D8 pilot; V6
  addendum, section 2).
- **V6 games:** d8 − none +0.066 [−0.024, +0.154]; retrieved − d8 +0.152 [+0.055, +0.245].

**Reading:** both results are across runs and single-seed, and the intervals for d8 − none overlap. On V6 the
walkthroughs clearly add beyond the sentence; on V5B they do not detectably add.

### Does memory help Qwen on the non-transform games? (against `none`)

- **V5B seed 0:** −0.011, 12 / 13.
- **V5B seed 1:** +0.126, 19 / 8, p = 0.052 (V5B seed-1 addendum).

**Reading:** seed noise on 87 games. Neither reading is supported by one seed.

## What cannot be said yet

- That the agent learns from **its own** episodes. Every result uses a bank of expert walkthroughs.
- That memory "works across models" as a general claim. Three models were measured, two of them in one mode only, and the
  side studies share games.
- That an abstract strategy carries the gain. The plans keep the verbs and appliance classes, and "about two thirds" is
  not supported: the interval of the plan's share is 0.42 to 0.94.
- That memory or the D8 sentence harms where it is not needed. No harm specific to added content was shown; the drop
  against `none` on non-transform games is shared with the neutral filler.
- That the results hold for unseen rooms, for other environments, or for task types other than ALFWorld's six.
- That any side run is confirmatory. They are exploratory, their plans are not published, and their pre-data status
  rests on file times.
- That per-type patterns are findings. Every split finer than transform / other was chosen after the data.

Not included here: an internal cross-study regression of gain on the no-memory gap. It is unpublished and is not in
any result file.
