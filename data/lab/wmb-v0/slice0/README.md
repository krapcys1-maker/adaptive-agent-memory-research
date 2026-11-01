# WMB slice 0: does the pairwise judge see what it must see? (T0 core)

**Status: instrument-validity test, tier E apart from a few hundred cheap judge calls (`deepseek-flash` through the flash-only proxy); preregistered before the first scored run.** The WriterMemBench specification (`docs/11-research-laboratory/memory-benchmark-research-digest-2026-11-01.md`, track T0) puts measurement validity first: nothing is read from a pairwise win rate unless the judge passes planted pairs. The E5 replay (AAM-E5-REPLAY) rests on that judge; this tests it with the replay's own data. Every earlier correction in this lab (E6, E6E) was a scorer that had not been checked against reading.

## Design

Planted pairs built from the local replay data (214 tasks, the model's notes of every arm, the author's earlier notes), each judged in both orders by the E5 prompt and settings (temperature 0, one line `WINNER: 1|2|TIE`):

| Family | Pair | Expected |
|---|---|---|
| aa | a note against an identical copy of itself | tie |
| copy | the model's note against a verbatim copy of the author's earlier note | the model's note wins |
| callback | a note with a grounded callback against the same note with the callback sentences removed | the callback note wins |
| spurious | a clean note against the same note with a fabricated callback prepended, on a task with no relevant earlier note | the clean note wins |
| null | a real note against a one-line non-answer | the real note wins |

Up to 40 tasks per family (fewer where the data do not hold 40, as for grounded callbacks). Also computed without new calls: the share of real arm pairs of the E5 judgments on which both orders agree; and, with `--retest`, the agreement of the verdicts of the copy family at two seeds.

## Rules, fixed before the first scored run (ours; the literature gives ranges, not cutoffs)

| Rule | Condition |
|---|---|
| aa ties | at least 0.90 of the verdicts are ties |
| copy, callback, spurious, null seen | at least 37/40 = 0.925 of the tasks are won by the expected note (mean score over the two orders above one half) |
| orders agree | at least 0.70 of the real arm pairs give the same verdict in both orders |
| format | at most 2% of the verdicts cannot be parsed |

**Decision, stated in advance.** If every rule holds, the pairwise lane may be used as a secondary measure in the benchmark. If any fails, it is descriptive only: its win rates (including those of AAM-E5-REPLAY) are reported as descriptive, the deterministic reference accounting carries the writing track, and the failing family says what the judge cannot see.

## Results (written on 2026-11-01 after the preregistered run; `results.json`, `summary.json`)

**The run.** 448 judgments by `deepseek-flash` through the flash-only proxy in 55 seconds (no parse failure); 40 tasks in each family except callback, for which the replay data hold 24 notes with a grounded callback. The judgment file stays local; `summary.json` carries its SHA-256 and the offline verifier recomputes every aggregate from it.

| Family | Tasks | Expected note wins | Wilson 95% | Tie rate | Rule |
|---|---|---|---|---|---|
| aa (identical pair) | 40 | all verdicts are ties: 1.00 | | 1.00 | met (0.90) |
| copy (model note against a copy of the earlier note) | 40 | 40 | [0.91, 1.00] | 0.00 | met |
| spurious (clean against a fabricated callback) | 40 | 40 | [0.91, 1.00] | 0.00 | met |
| null (real note against a one-line non-answer) | 40 | 39 (0.975) | [0.87, 1.00] | 0.00 | met |
| **callback (grounded callback against the callback removed)** | 24 | **3 (0.125)** | [0.04, 0.31] | 0.02 | **not met** |

Order consistency on the real arm pairs of AAM-E5-REPLAY: 469 of 664 (0.706), just over the rule of 0.70. Test-retest agreement of the copy verdicts at two seeds: 80 of 80. The planted families show no position bias (the first position wins half of the non-tie verdicts); in the callback family the first position wins 0.72 of the non-tie verdicts.

**The readings applied mechanically.** The judge sees an identical pair, a copy, a fabricated callback and a non-answer; it does not see, or does not reward, a grounded callback. `judge_usable_as_secondary`: **no**.

**What the callback failure is** (post hoc, an inline snippet over the same 24 tasks, same judge): the judge does not merely prefer shorter notes. With an equally long non-callback sentence removed instead, the note with the callback wins 14, loses 1 and ties on 9 tasks; with the callback sentences removed, the note with the callback wins 3, loses 11 and ties on 10. So the E5 judge prompt ("does not repeat it or force a reference") penalises the explicit callback itself; the sentences it removes typically restate what the earlier note said ("I wrote before that resin codes identify plastic type, not recyclability ..."). A callback in this account's notes is, to this judge, mostly repetition.

**Decisions recorded** (stated in advance, applied, with what follows from them):

1. **The pairwise lane is descriptive only.** Its win rates, including the preference for thresholded memory in AAM-E5-REPLAY (0.64 to 0.73 against the instruction-only control), are not evidence that explicit callbacks help, and cannot be read as a measure of grounded memory use. The preference stands as an observed fact about this judge; its mechanism is not the callback.
2. **A writing track cannot take "more grounded callbacks" as success.** The deterministic reference accounting (grounded, spurious, missing) still measures what a design does, but whether a callback is good is a question about readers or the owner, not about this judge. The calibration step of the specification (the owner reads about 60 blind pairs, among them callback against no callback) is therefore not optional for the writing track: it decides what "good memory use" means for this account.
3. **Cheap checks that came out well:** the judge is stable (retest 80 of 80), sees copies, fabricated callbacks and non-answers, and has no position bias on planted pairs; the marginal order consistency on real pairs (0.706) says that real differences are subtle, and the minimum detectable win rate for the 43 natural opportunity tasks of E5 is 0.72.

## Limits

Planted pairs are easier than real differences; passing shows that the judge can see these defects, not that it ranks designs well. The notes are the model's, so the judge and the writer are of the same provider. Fewer than 40 callback tasks are available, so that family is less certain. Only aggregates are published; judgments stay local.

## Files

`config.json`, `results.json` and `summary.json` (aggregates and the digest of the local judgment file), `scripts/wmb/t0_battery.py`, `scripts/wmb/contract.py`, `scripts/wmb/stats.py` and their tests. Reproduce: `python scripts/wmb/t0_battery.py run --items opublikowane.jsonl --replay DIR --workdir DIR --retest`, then `analyse --json results.json`.

## Log

Preregistered before the first scored run (commit 23f786c).

- 2026-11-01 21:05: first and only scored run (55 seconds); results written. The length control in the Results is a post hoc inline snippet and is labelled as such; it is not part of `results.json`.
