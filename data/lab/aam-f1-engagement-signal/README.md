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

## Limits

Counts are small and the platform's distribution is not under the account's control. Features are confounded with time (the writer model and the note type changed over the period); the recency baseline absorbs the level but not everything. The 72 hour window may be too short for slow notes. The power simulation resamples the account's own recent notes, so it carries its trend as noise (conservative). Descriptive tier E: a null here is a result, a positive is a hypothesis for E4 and N3.

## Files

`config.json`, `results.json` (aggregates), `scripts/engagement_signal.py` and its tests. Reproduce: `python scripts/engagement_signal.py --notes wyniki_notek.jsonl --replies odpowiedzi.jsonl --json results.json`.

## Log

Preregistered before the first run on the real data.
