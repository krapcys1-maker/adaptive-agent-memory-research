# AAM-F1: is there learnable signal in the live account's real engagement numbers?

**Status: data-based feasibility test, tier E (model-free, existing data, no paid calls), not entered in the experiment registry; preregistered before the first run on the real data.** The blueprint (`docs/11-research-laboratory/persona-memory-blueprint-v0.md`) puts feeling-like importance signals and learning from outcomes (parts 6 to 8) behind two tests, E4 and this one. If the account's own engagement numbers carry no per-note signal that anything could learn from, the learning loop of the live agent (stage N4) cannot be built on them, and the randomised live comparison (N3) needs a known sample size. This test measures both.

**Privacy.** The exports are read-only copies made by the agent's own session into a local folder outside both repositories. Only aggregates are published here: no note text, no identifier.

**What was seen before this was written.** The field names of the two files, the number of populated fields in each, and one example row of each (an old note with a single like). No distribution, correlation or test statistic of any outcome had been computed.

## Data

`wyniki_notek.jsonl`: 234 notes, 16 August to 1 November 2026; 202 have a 72 hour measurement (views, likes, replies, restacks, interactions) and most have a time series of measurements. Features known at publication: type, format, form, ends with a question, length in words, writer model, hour and weekday. `odpowiedzi.jsonl`: 883 replies and comments, used only for the first two questions.

## Questions and the readings, stated in advance (`config.json` holds the parameters and the digests of the script and of both inputs)

| # | Question | Measure | Reading |
|---|---|---|---|
| 1 | Do the outcomes have per-note resolution? | share of notes with at least one like at 72 hours (also replies, restacks, interactions) | likes usable per note if the share is at least 0.5 (a convention fixed here) |
| 2 | Does the like rate differ between notes beyond chance? | Pearson dispersion D of likes given views against binomial noise at the pooled rate (1 means chance alone), Monte Carlo p over 10,000 draws | yes if D is at least 1.5 and p is below 0.01 |
| 3 | Do features known at publication predict an outcome better than the recent past? | rolling origin over the notes from the 61st on, using only outcomes known 72 hours after publication; outcome log(1 + views) and log(1 + likes); baseline: the median of the last 20 known notes, corrected by the mean of its earlier errors; models: baseline plus a shrunk effect of the type, baseline plus a ridge fit on all features; skill is the reduction of squared error against the baseline, with a moving-block bootstrap interval | signal if skill is at least 0.05 and the 95% interval lies above 0, per outcome |
| 4 | Can the instrument see an effect of that size at all? | the same evaluation after multiplying (1 + outcome) by 1.5 for the commonest type (planted) | the type-only model must meet the condition of question 3; otherwise a null in question 3 is uninformative for that outcome |
| 5 | Can an early reading stand in for the 72 hour one? | Spearman between the last reading taken between h/2 and h hours after publication (h = 6, 12, 24, 48) and the 72 hour value | the 24 hour reading stands in if the correlation is at least 0.9 for views and 0.8 for likes, on at least 30 notes |
| 6 | How many notes per arm does a randomised comparison need here? | simulated comparisons drawn from the last 100 notes, 20 to 160 per arm, a relative increase of 25%, 50%, 100% in the expected count (the control arm binomially thinned), Mann-Whitney at 5%, 1,000 simulations per cell | smallest per-arm sample with power of at least 0.8, per outcome and effect; valid only if the false positive rate at no effect lies between 0.02 and 0.09 |

**The decisions that follow, written before the numbers.** If question 3 is a null with a valid control (question 4) for both outcomes: the learning loop is not built on per-note engagement; engagement is used in aggregate over weeks, feeling-like signals tied to engagement stay unvalidated on this account, and N3 is sized from question 6. If an outcome shows signal: the features that carry it become hypotheses for E4 and N3, nothing is deployed on this evidence alone. If question 4 fails: the nulls say nothing and a larger sample is requested. Question 6 sizes N3 in every case.

## Results (written on 2026-11-01 after the preregistered analysis had been run; `results.json`; revised the same evening after an independent review, see the Erratum below)

**The run.** 202 notes with a 72 hour measurement (23 August to 28 October 2026), 142 of them evaluation notes (after the first 60), 2.63 notes a day over the last 30 days. Nothing was changed in the script after the first run; the digest in `config.json` is that of the run.

**1 Resolution.** Per note at 72 hours: median 14 views (quartiles 10 and 21) and 2 likes (1 and 3); 95% of notes have at least one like, 11% at least one reply, 7% at least one restack. Likes are usable per note by the reading, but they are small counts.

**2 Dispersion.** D = 0.72, below the 95% interval of the null (0.81 to 1.23): given its views, a note's likes vary *less* than binomial noise at the pooled rate (12.3% of views). Reading: the like rate does not differ between notes beyond chance. D below 1 is produced by the floor of about one like per note (95% of notes have one), which a binomial null at the pooled rate does not model; it is not a finding about unusual regularity (the reviewer's recomputation without the floor gives D = 0.97).

**3 Skill** (reduction of squared error against the recency baseline; 95% moving-block interval):

| Outcome | all-history mean | type only | all features (ridge) |
|---|---|---|---|
| log(1 + views) | -0.51 [-1.43, -0.11] | 0.00 [-0.08, 0.07] | -0.14 [-0.33, -0.01] |
| log(1 + likes) | -0.14 [-0.53, 0.13] | -0.03 [-0.12, 0.03] | -0.24 [-0.42, -0.09] |

The recent past is far better than the whole history for views (the level moves), and the note type adds nothing to it.

**4 Planted control.** The factor 1.5 multiplies (1 + outcome) for the commonest evaluation type (SPROSTOWANIE, 47 notes). That is **+52% in view counts but +69% in like counts** (means 20.2 to 30.8 and 2.68 to 4.52), not "+50%" for both. The type-only model sees it: views 0.18 [0.10, 0.29] and likes 0.14 [0.01, 0.26]. Re-run after the review with the effect planted on the count scale, same rule (post hoc, an inline snippet over the same table): views +25% 0.07 [-0.01, 0.17] fail, +50% 0.16 [0.08, 0.28] pass, +100% 0.30 [0.22, 0.44] pass; likes +25% 0.01 [-0.10, 0.10] fail, **+50% 0.06 [-0.06, 0.16] fail**, +75% 0.12 [-0.02, 0.23] fail, +100% 0.17 [0.03, 0.29] pass. So the instrument sees a +50% effect in view counts and only about +100% in like counts, in the commonest type; for likes the condition of question 4 is not met at +50%, which by the text written in advance means that the likes null says nothing below about +100%. The ridge model on all features does not see even the larger planted effect (0.02 [-0.13, 0.16] and 0.01 [-0.20, 0.19]): it overfits at about 140 evaluation notes, so **its null is uninformative**.

**5 Early readings** (Spearman with the 72 hour value, views / likes): 6 h 0.59 / 0.70 (172 notes); 12 h 0.82 / 0.82 (132); **24 h 0.95 / 0.96 (199)**; 48 h 0.99 / 0.99 (201).

**6 Power** (share of simulated randomised comparisons that find the effect; per arm 20, 40, 80, 160). Views, +25%: 0.37, 0.64, 0.91, 1.00; +50%: 0.78, 0.98, 1.00, 1.00; +100%: 0.99, 1.00, 1.00, 1.00. Likes, +25%: 0.15, 0.30, 0.52, 0.83; +50%: 0.42, 0.69, 0.94, 1.00; +100%: 0.75, 0.97, 1.00, 1.00. False positive rate at no effect 0.04 to 0.06 (valid). **The sizes 80 / 40 / 20 (views) and 160 / 80 / 40 (likes) in the first version were the next point of a doubling grid above the crossing, and overstate the need by up to about two times.** A finer grid with 3,000 simulations per cell (post hoc, same method, false positive rate 0.025 to 0.059) puts the 0.8 crossing at about **59 / 20 / 9 notes per arm** for +25% / +50% / +100% in views and **150 / 51 / 22** in likes. The thinning of the control arm and the floor of one like per note make the likes figures less certain than the views figures.

**Days.** A comparison restricted to notes that have a related earlier note needs 2m notes in all. The share of notes with an earlier note at cosine at least 0.5 / 0.6 / 0.7 is 42% / 21% / 10% (`published-notes-baseline-2026-11-01.md`), i.e. about 1.1 / 0.54 / 0.26 such notes a day at 2.63 notes a day. +50% in views then takes about 36 / 74 / 154 days and +50% in likes 92 / 188 / 392; +25% in views 107 / 218 / 453 and +25% in likes 271 / 553 / 1,150; +100% in views 16 / 33 / 69. The 20% is the share with a related predecessor at cosine 0.6, not a measured share of notes on which memory acts, and the harm direction was not simulated (a two-sided test is symmetric, so the sizes should hold for a drop).

**Replies (secondary).** Only 59 replies were measured at least 72 hours after posting; the median has no views and 22% have a like. Too sparse to serve as a per-reply outcome.

**Post hoc, descriptive, not preregistered** (an inline snippet over the same note table): Spearman between likes and views 0.59; the level is falling, with median views 23.5, 13, 10 and median likes 2.5, 2, 1 in the first, middle and last third of the notes (68, 67 and 67 notes); of the views the platform attributes to an audience type (a median half of all views) the median share from readers not connected to the account is 0.60, and of all views 0.26.

**The readings applied mechanically.** Likes usable per note: yes. Like rate varies beyond chance: no. Features carry signal: no for views and likes with the type-only model, whose instrument passed the planted control for views at +50% and for likes only at about +100%; the null of the full model is uninformative. The 24 hour reading stands in for the 72 hour one: yes. Power simulation valid: yes.

**Decisions recorded** (the ones stated in advance, applied; this replaces the first version):

1. **No large effect of the note type was found; per-note learning from engagement is not supported at this volume.** The instrument sees +50% in view counts and about +100% in like counts in the commonest type; other types (the same planted factor is not always seen in smaller types), other features and combinations were not testable with a valid instrument. The writer model is an in-sample candidate that is confounded with time (the reviewer reports p about 0.01 for views; not tested here) and is a hypothesis for E4 and N3, not a finding. Engagement is used as the recent level and in aggregate over weeks; feeling-like signals tied to engagement stay unvalidated on this account.
2. **Feedback can be read at 24 hours instead of 72.**
3. **A live comparison cannot establish a small benefit or a small harm quickly.** Restricted to notes with a related earlier note, a plausible effect of 25% needs about 110 to 450 days for views and 270 to 1,150 for likes over the range of thresholds, and 220 and 550 days at cosine 0.6; a 50% effect about 74 days for views and 190 for likes. The offline pairwise judge (E5) and the replies of readers carry the evidence of quality, and the live arm is a slow lane that can show a large harm. In terms of harm, a fall is the mirror of a rise (+50% is -33%, +25% is -20%): 20 notes per arm exclude a fall of about a third or more in views (about 74 days at cosine 0.6), 59 per arm a fall of a fifth (about 218 days). These sizes are for notes; if the live comparison runs on replies, replies are too sparse to carry an outcome (59 with a 72 hour reading, median no views). A before-and-after comparison is out: the level fell by more than half over the period, so every live comparison must be concurrent and randomised.

**Erratum (2026-11-01, evening).** An independent adversarial review reproduced the aggregates of F1 and found, in the conclusions: the planted effect is +52% in views but +69% in likes, so "a +50% effect would have been seen" holds for views only (corrected in 4 and in decision 1); "no feature predicts" was wider than what the one valid instrument tested (decision 1); the per-arm sizes and day counts were upper bounds from a doubling grid (6 and decision 3); the candidate share depends on a cosine threshold that was not stated (6); the 0.60 share of unconnected views is within the audience breakdown and the medians by thirds had been rounded up (post hoc); and the under-dispersion has a simple cause (2). The original wording stays in the git history (PR #59); the board entry P-026 and the plan were corrected in P-029.

## Limits

Counts are small and the platform's distribution is not under the account's control. Features are confounded with time (the writer model and the note type changed over the period); the recency baseline absorbs the level but not everything. The 72 hour window may be too short for slow notes. The power simulation resamples the account's own recent notes, so it carries its trend as noise (conservative). Descriptive tier E: a null here is a result, a positive is a hypothesis for E4 and N3.

## Files

`config.json`, `results.json` (aggregates), `scripts/engagement_signal.py` and its tests. Reproduce: `python scripts/engagement_signal.py --notes wyniki_notek.jsonl --replies odpowiedzi.jsonl --json results.json`.

## Log

Preregistered before the first run on the real data (commit 5ed1960).

- 2026-11-01 18:00: first and only run on the real exports (36 seconds); results written. The post hoc paragraph came from an inline snippet that reuses `note_table` of the script (Spearman of likes and views, medians by thirds of the notes, share of views by audience type) and is not part of `results.json`.
- 2026-11-01 evening: erratum after an independent adversarial review (see the Results). The digests of the run are unchanged; the corrections use inline post hoc snippets over the same note table (count-scale planted effects, a finer power grid), described in the text. The test suite is to be strengthened (causality of the rolling origin, the readings and the constants are not pinned by the current tests).
