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

## Results (written on 2026-11-01 after the preregistered analysis had been run; `results.json`)

**The run.** 202 notes with a 72 hour measurement (23 August to 28 October 2026), 142 of them evaluation notes (after the first 60), 2.63 notes a day over the last 30 days. Nothing was changed in the script after the first run; the digest in `config.json` is that of the run.

**1 Resolution.** Per note at 72 hours: median 14 views (quartiles 10 and 21) and 2 likes (1 and 3); 95% of notes have at least one like, 11% at least one reply, 7% at least one restack. Likes are usable per note by the reading, but they are small counts.

**2 Dispersion.** D = 0.72, below the 95% interval of the null (0.81 to 1.23): given its views, a note's likes vary *less* than binomial noise at the pooled rate (12.3% of views). Reading: the like rate does not differ between notes beyond chance.

**3 Skill** (reduction of squared error against the recency baseline; 95% moving-block interval):

| Outcome | all-history mean | type only | all features (ridge) |
|---|---|---|---|
| log(1 + views) | -0.51 [-1.43, -0.11] | 0.00 [-0.08, 0.07] | -0.14 [-0.33, -0.01] |
| log(1 + likes) | -0.14 [-0.53, 0.13] | -0.03 [-0.12, 0.03] | -0.24 [-0.42, -0.09] |

The recent past is far better than the whole history for views (the level moves), and no feature set beats it.

**4 Planted control** (+50% in the commonest evaluation type, SPROSTOWANIE): the type-only model sees it, views 0.18 [0.10, 0.29] and likes 0.14 [0.01, 0.26]. The ridge model on all features does not (0.02 [-0.13, 0.16] and 0.01 [-0.20, 0.19]): at about 140 evaluation notes it overfits, so **its null is uninformative**; the type-only null is informative.

**5 Early readings** (Spearman with the 72 hour value, views / likes): 6 h 0.59 / 0.70 (172 notes); 12 h 0.82 / 0.82 (132); **24 h 0.95 / 0.96 (199)**; 48 h 0.99 / 0.99 (201).

**6 Power** (share of simulated randomised comparisons that find the effect; per arm 20, 40, 80, 160). Views, +25%: 0.37, 0.64, 0.91, 1.00; +50%: 0.78, 0.98, 1.00, 1.00; +100%: 0.99, 1.00, 1.00, 1.00. Likes, +25%: 0.15, 0.30, 0.52, 0.83; +50%: 0.42, 0.69, 0.94, 1.00; +100%: 0.75, 0.97, 1.00, 1.00. False positive rate at no effect 0.04 to 0.06 in every cell (valid). Smallest per-arm sample with power of at least 0.8: views 80 / 40 / 20 and likes 160 / 80 / 40 for +25% / +50% / +100%.

**Replies (secondary).** Only 59 replies were measured at least 72 hours after posting; the median has no views and 22% have a like. Too sparse to serve as a per-reply outcome.

**Post hoc, descriptive, not preregistered** (an inline snippet over the same note table): Spearman between likes and views 0.59; the level is falling, with median views 24, 13, 10 and median likes 3, 2, 1 in the first, middle and last third of the notes; the median share of views from readers not connected to the account is 0.60.

**The readings applied mechanically.** Likes usable per note: yes. Like rate varies beyond chance: no. Features carry signal: no for views and for likes with the type-only model, whose instrument passed the planted control; the null of the full model is uninformative (its control failed). The 24 hour reading stands in for the 72 hour one: yes, for views and for likes. Power simulation valid: yes.

**Decisions recorded** (the ones stated in advance, applied):

1. **The learning loop (N4) is not built on per-note engagement at the current volume.** No feature known at publication predicts views or likes beyond the recent past, and a +50% difference in the commonest type would have been seen. Smaller differences, differences confined to rare types and combinations of features are not excluded; the multi-feature question needs a larger sample than this account has. Engagement is used as the recent level and in aggregate over weeks; feeling-like signals tied to engagement stay unvalidated on this account, and E4 (an environment with real outcomes) stays the test for signals.
2. **Feedback can be read at 24 hours instead of 72.**
3. **N3 cannot answer "does memory raise engagement" quickly at this volume.** Memory acts on the fifth of notes that have a related earlier note (about 0.53 a day), so the comparison has to be restricted to those notes; the other notes are identical in both arms and only add noise. Forty candidate notes per arm to see a +50% change in views take about 150 days, likes about 300 days, and a +100% change in views about 75 days; spread over all notes the same effect is diluted five times and is not detectable. So N3 is designed as a randomised concurrent harm check plus the judged and reply-based measures, with the offline pairwise judge (E5) as the main instrument for memory quality, or the candidate rate and volume are raised. A before and after comparison is out: the level fell by more than half over the period, so every live comparison must be concurrent and randomised.

## Limits

Counts are small and the platform's distribution is not under the account's control. Features are confounded with time (the writer model and the note type changed over the period); the recency baseline absorbs the level but not everything. The 72 hour window may be too short for slow notes. The power simulation resamples the account's own recent notes, so it carries its trend as noise (conservative). Descriptive tier E: a null here is a result, a positive is a hypothesis for E4 and N3.

## Files

`config.json`, `results.json` (aggregates), `scripts/engagement_signal.py` and its tests. Reproduce: `python scripts/engagement_signal.py --notes wyniki_notek.jsonl --replies odpowiedzi.jsonl --json results.json`.

## Log

Preregistered before the first run on the real data (commit 5ed1960).

- 2026-11-01 18:00: first and only run on the real exports (36 seconds); results written. The post hoc paragraph came from an inline snippet that reuses `note_table` of the script (Spearman of likes and views, medians by thirds of the notes, share of views by audience type) and is not part of `results.json`.
