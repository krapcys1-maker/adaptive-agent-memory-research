# What we know so far: experience memory in ALFWorld, November 2026

Status: summary, graded; no new measurements. Added 2026-11-23.

This page grades the claims that the published lab programs and the exploratory side runs support so far. It adds no
number of its own. Every number is taken from the document it cites, where it is recomputed:
- lab numbers come from the package READMEs, which `scripts/verify_autolab_packages.py` recomputes;
- side-run numbers come from the addenda and the side-studies note, which were recomputed from the per-episode outputs.

Where the lab has published a state (`positive`, `inconclusive`, ...), that state rules. Numbers from side runs never
override it.

**Scope of everything below:**
- ALFWorld text games only, all of them `train` games (their rooms were seen when the bank was built; `valid_unseen` is
  not used);
- a bank of **expert walkthroughs**, not the agent's own earlier episodes;
- three models, each in one prompt mode: Qwen3-4B in the normal mode (lab programs) and DeepSeek V4.1 Flash and Mistral
  Nemo 12B in HARD mode (side studies). Model and mode are therefore confounded in every comparison between models.

**Sources** (short names used below):
- lab packages: [V4](../../data/lab/autolab-alfworld-ladder-r4-v4/README.md),
  [V5B](../../data/lab/autolab-alfworld-ladder-r4-v5b/README.md) and
  [V6](../../data/lab/autolab-alfworld-ladder-r4-v6/README.md);
- addenda: [V5B secondary contrast](errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md),
  [V5B seed 1](errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md) and
  [V6 seed 1 and D8](errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md);
- the [side-studies note](side-studies-2026-11.md), which covers DS-HARD-1, DS-HARD-2, NEMO-FLOOR and the DeepSeek pilots.

**Grades:**
- **strong:** seen with at least two models or two seeds, on a contrast fixed before the data;
- **moderate:** consistent, but exploratory or resting on one valid measurement;
- **weak:** a single result, a result across runs, or a subgroup chosen after the data;
- **contradictory or model-dependent:** the results disagree between models, modes or seeds.

## Strong

| claim | rests on | limits |
|---|---|---|
| Two goal-similar expert walkthroughs raise the solve rate above a length-matched neutral filler block. | V5B `retrieved_task − placebo` +0.169 [+0.053, +0.285], `positive`; V6 +0.130 [+0.049, +0.211], `positive` (results tables); V6 seed 1 +0.157, two-seed estimate +0.143 [+0.090, +0.196] (V6 addendum, section 1); DS-HARD-1 Q1 +0.218 [+0.158, +0.282]; DS-HARD-2 S0 +0.190 (same population); NEMO-FLOOR +0.200, a floor lift (side-studies note) | No lab interval is `practical`: every lower bound is below the SESOI of 0.12. The seed-1 runs are consistency checks, not independent replications. DS-HARD-2 repeats DS-HARD-1 on a subset of the same games. V4 is left out because of its measurement problem. |
| Walkthroughs of the right task type beat length-matched walkthroughs of another type. | V5B `retrieved_task − mismatched_type` +0.154 [+0.035, +0.273], `positive` (secondary, named before the measurement, reported later; V5B secondary-contrast addendum); DS-HARD-1 Q2 +0.159 [+0.103, +0.220], plan-defined POSITIVE (side-studies note) | It does not separate knowing the procedure of the type from matched vocabulary, object names or concrete commands. In V5B the control repeated a few walkthroughs across many games (exposure not balanced). |
| The actions alone, without the observation text, already beat the placebo. | V6 `retrieved_steps − placebo` +0.137 [+0.055, +0.219], `positive`, `open`; DS-HARD-2 P2 +0.150 [+0.062, +0.240], plan-defined POSITIVE | The actions keep the verbs, objects and appliances. Both arms are padded to the full block length, so layout is held fixed, but form and content are not separated further. |

## Moderate

| claim | rests on | limits |
|---|---|---|
| For Qwen and DeepSeek, the gain sits mostly in the transform games (clean / cool / heat). | Qwen V6 against placebo: transform +0.245 and +0.272 at seeds 0 and 1, other +0.013 and +0.040; two seeds +0.258 against +0.027 (V6 addendum, section 1). Qwen V5B against none: +0.202 and +0.211 against −0.011 and +0.126 (V5B seed-1 addendum). DeepSeek DS-HARD-1 Q5: +0.368 against +0.071 (side-studies note) | The split was chosen after V5B had shown where the gain sits, so it is exploratory. It does **not** hold for Mistral Nemo: 7 of its net 20 games gained are transform games, and 9 are `pick_and_place` (side-studies note). On the other games, Qwen's interval does not exclude a gain of about 0.09. |
| A rule-based plan without numbers and room-specific locations beats the placebo and is not detectably worse than the actions alone. | DS-HARD-2 P1 +0.130 [+0.051, +0.213], plan-defined POSITIVE; S1 plan − actions −0.020 [−0.086, +0.043], inside ±0.10; share of the gain kept 0.68 [0.42, 0.94] (side-studies note) | Only one valid measurement: in V6 the plan arm has a format measurement problem, so its +0.130 does not separate content from format. The plan keeps verbs and appliance classes, so this is not evidence that an "abstract strategy" carries the gain. The share's interval reaches below one half. Against the full walkthroughs the plan is borderline (McNemar p = 0.070; the interval just excludes zero). |

## Weak

| claim | rests on | limits |
|---|---|---|
| For Qwen, walkthroughs raise the solve rate above **no memory**. | V5B `retrieved_task − none` +0.109 [−0.007, +0.226], `inconclusive`; V6 +0.073 [−0.009, +0.156], `inconclusive` (results tables); V5B seed 1 +0.174, McNemar p 6.5e-05 (V5B seed-1 addendum) | The lab's own intervals include zero in both programs. Only the exploratory seed-1 re-run is clearly positive. It is a secondary contrast in both programs. |
| For Qwen, the filler block alone lowers the solve rate a little. | `placebo − none`: V4 −0.023, `equivalent`; V5B −0.060 and V6 −0.057, both `inconclusive` (results tables). DeepSeek HARD: +0.005 [−0.047, +0.057] (DS-HARD-1) | The sign is consistent in three Qwen runs, but no lab interval excludes zero. |
| The D8 sentence (the clean / cool / heat convention, naming the appliances) lowers the solve rate on the non-transform games. | V6 games: −0.107 [−0.190, −0.022], 13 / 29, p = 0.020 (V6 addendum, section 2) | Across runs, one seed, one sentence. It is not evidence that retrieved memory harms these games: in V6, `retrieved_task − none` on them is −0.074, with an interval that includes zero. |
| Qwen gains nothing on `pick_two` games. | V6 net games over `placebo` on `pick_two`: −5 at seed 0, 0 at seed 1 (V6 `per_unit.csv` and the V6 seed-1 re-run) | A per-type stratum chosen after the data, one of six types. |

## Contradictory or model-dependent

| question | one side | other side | reading |
|---|---|---|---|
| Which task types gain? (net games over `placebo`) | DeepSeek HARD: 26 of its net 42 in heat games (side-studies note) | Qwen normal mode, V6 seed 0: 27 of its net 39 in clean and cool, 10 in heat. Mistral Nemo HARD: 9 of its net 20 in `pick_and_place`, 4 in heat (side-studies note) | "The gain is in heating" holds for DeepSeek in HARD mode only. Model and mode are confounded. One untested explanation: the normal mode's admissible-action list already offers the heat command. |
| Do walkthroughs of another type help? (against `none`) | DeepSeek HARD: `mismatched_type − none` +0.063 [+0.006, +0.121], uncorrected (DS-HARD-1 Q3) | Qwen normal mode: V5B `mismatched_type − none` −0.045 [−0.135, +0.045], `inconclusive` | Both model and mode differ. In HARD mode any walkthrough also shows the command grammar in use; that route is untested. |
| How much of the memory gain does the D8 sentence reproduce on transform games? | V5B games: d8 − none +0.140 [+0.041, +0.235]; retrieved − d8 +0.061 [−0.049, +0.169] (first D8 pilot, V6 addendum, section 2) | V6 games: d8 − none +0.066 [−0.024, +0.154]; retrieved − d8 +0.152 [+0.055, +0.245] | Both are across runs and single-seed, and the intervals overlap. The share the sentence reproduces is not pinned down: on V6 it lies anywhere from none to about 70% of the memory gain. |
| Does memory help Qwen on the non-transform games (against `none`)? | V5B seed 0: −0.011, 12 / 13 | V5B seed 1: +0.126, 19 / 8, p = 0.052 (V5B seed-1 addendum) | Seed noise on 87 games. Neither reading is supported by one seed. |

## What cannot be said yet

- That the agent learns from **its own** episodes: every result uses a bank of expert walkthroughs.
- That memory "works across models" as a general claim. Three models were measured, each in one mode, and the
  DeepSeek studies share games. NEMO-1 (Mistral Nemo in the normal mode) is still running and is not reported here.
- That an abstract strategy carries the gain. The plans keep the verbs and appliance classes, and "about two thirds" is
  not supported: the interval of the plan's share is 0.42 to 0.94.
- That memory harms where it is not needed. Harm was shown once, for the D8 sentence, across runs; it was not shown for
  retrieved walkthroughs.
- That the results hold for unseen rooms, other environments, or task types other than ALFWorld's six.
- That any side run is confirmatory. The side runs are exploratory, their plans are not published, and their
  pre-data status rests on file times.
- That per-type patterns are findings. Every split finer than transform / other was chosen after the data.

Not included here:
- the synthesis's cross-study regression of gain on the no-memory gap, which is unpublished and not in any result file;
- NEMO-1, which is running.
