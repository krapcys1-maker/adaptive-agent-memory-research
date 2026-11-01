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

## Limits

Planted pairs are easier than real differences; passing shows that the judge can see these defects, not that it ranks designs well. The notes are the model's, so the judge and the writer are of the same provider. Fewer than 40 callback tasks are available, so that family is less certain. Only aggregates are published; judgments stay local.

## Files

`config.json`, `results.json` and `summary.json` (aggregates and the digest of the local judgment file), `scripts/wmb/t0_battery.py`, `scripts/wmb/contract.py`, `scripts/wmb/stats.py` and their tests. Reproduce: `python scripts/wmb/t0_battery.py run --items opublikowane.jsonl --replay DIR --workdir DIR --retest`, then `analyse --json results.json`.

## Log

Preregistered before the first scored run.
