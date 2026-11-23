# Addendum: a seed-1 re-run of `none` and `retrieved_task` on the ALFWORLD-LADDER-R4-V5B games

Added 2026-11-23. Package: `data/lab/autolab-alfworld-ladder-r4-v5b/` (published bytes unchanged; they are pinned by
`PUBLISHED_FILES.json` and recomputed by `scripts/verify_autolab_packages.py`). This is an addition, not a correction of a
number. It does not overlap with the [earlier V5B addendum](2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md),
which concerns `retrieved_task − mismatched_type` at seed 0. Nothing here changes the package's results, findings,
verdicts or direction status.

This is an **exploratory side run outside the lab pipeline**: not a lab program, no envelope, instrument review,
positive control or code audit, and no lab verdict. Like the V6 seed-1 re-run (see the
[V6 addendum](2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md)), it was run and first analysed by a session of
the project's automated coordinator. Every number below was recomputed for this addendum by a second script, written
without importing the first, from the per-episode outputs and the published `per_unit.csv`; all agree with the run's
own result file. That script was written by a model of the same family (Claude), so it is a recomputation, not an
independent-model review. The per-episode outputs are not published (they hold the full action logs); their SHA-256 is
at the end. The seed-0 rows can be recomputed from the public `per_unit.csv`; the seed-1 rows cannot be recomputed from
this repository.

## What was run

- **Arms:** `none` and `retrieved_task` at seed 1, on the 201 games V5B measured. `placebo` and `mismatched_type` were not
  re-run, so this re-run says nothing about V5B's two primary contrasts, which are against `placebo`.
- **Instrument:** the V5B agent with one added arm that this run does not use (the D8 instruction arm). Checked by diff
  against the published `tools/alfworld_ladder/v5b/src/agent.py` (same SHA-256 as the V5B agent copy the run started
  from): the only changes are the sentence constant, the arm name in `ARMS`, `d8_instruction` returning no memory like
  `none`, and its prompt suffix; the code paths of `none` and `retrieved_task` are unchanged.
- **Bank, model and settings:** the V5B bank (its SHA-256 equals the published `tools/alfworld_ladder/v5b/data/bank.jsonl`)
  and the V5B model and settings: `Qwen/Qwen3-4B-Instruct-2507-FP8`, temperature 0.7, `min_tokens` 8, 50 steps, format
  reminder on (checked in all 402 records).
- **Seed 1** changes the model's sampling and also the tie-break among equally similar bank entries, so the shown
  walkthrough pair can differ from seed 0. The run's rule cites an earlier audit estimate that about 66% of games get a
  different pair; that figure could not be checked here, because the public package does not list the sources.
- **When:** 2026-11-21, about 15:58 to 23:35 UTC, on the lab's GPU, after V5B had finished; not
  interleaved or randomised together with V5B's arms. 402 episodes, 0 errors, 0 duplicates, no exclusions.
- **Rule written before data** (2026-11-21; evidence: file times; not published, no external registry record): report
  the solve rates and `retrieved_task − none` (paired gains and losses, exact McNemar p) at seed 1 next to seed 0, the
  transform / other split descriptively, and the between-seed agreement. **Results are reported, not judged**: the rule
  defines no verdict and no pooled two-seed estimate, so none is given here.

## Results

`retrieved_task − none`, paired over games; exact two-sided McNemar test. The seed-0 rows are recomputed from the
published `per_unit.csv`.

| games | n | seed | `none` | `retrieved_task` | difference | gains / losses | McNemar p |
|---|---:|---:|---:|---:|---:|---:|---:|
| all | 201 | 0 | 0.507 | 0.617 | +0.109 | 48 / 26 | 0.014 |
| all | 201 | 1 | 0.512 | 0.687 | +0.174 | 55 / 20 | 6.5e-05 |
| transform (clean / cool / heat) | 114 | 0 | 0.386 | 0.588 | +0.202 | 36 / 13 | 0.0014 |
| transform (clean / cool / heat) | 114 | 1 | 0.447 | 0.658 | +0.211 | 36 / 12 | 0.0007 |
| other | 87 | 0 | 0.667 | 0.655 | −0.011 | 12 / 13 | 1.0 |
| other | 87 | 1 | 0.598 | 0.724 | +0.126 | 19 / 8 | 0.052 |

**Agreement between seeds, game by game:** phi of `solved` between seed 0 and seed 1 is 0.512 for `none` and 0.460 for
`retrieved_task`; the correlation of the per-game difference (`retrieved_task − none`) between the seeds is 0.316. On
V6 the same quantities were 0.585 / 0.468 / 0.297 (for `placebo` and `retrieved_task`).

## How to read it

- **The interval of record stays the package's.** V5B publishes `retrieved_task − none` as a secondary contrast,
  +0.109 [−0.007, +0.226], `inconclusive`, on the sequential interval of its second look (z = 2.7777). The McNemar p of
  the seed-0 row above is a fixed-sample test of the same counts and does not replace that state.
- **Seed 1 points the same way and is larger** (+0.174). This is a consistency check on the same games, bank, model and
  machine, not an independent replication, and it is a secondary contrast (against `none`, not against `placebo`).
- **The other games show how noisy one seed is.** Their difference moves from −0.011 at seed 0 to +0.126 at seed 1, with
  the same games and instrument. Neither "memory does not help on these types" (seed 0) nor "it does" (seed 1, p = 0.052)
  is supported by one seed. The transform / other split was chosen after V5B had shown where the gain sits: exploratory.
- **Power.** With 87 other games and the discordance seen here (25 and 27 discordant pairs), the exact McNemar test
  reaches p < 0.05 only from a split of 18 / 7 or 20 / 7 onwards, a net difference of about +0.13 to +0.15. Smaller true
  effects on these games would usually be missed; no pooled estimate was planned, so the question stays open.
- **Not shown.** Nothing about `placebo` or `mismatched_type` at seed 1, the primary contrasts, other models or
  environments.

## Source files (not in this repository)

| file | SHA-256 |
|---|---|
| rule `SEED1_RULE.md` | `5975d0de326f34e540ae79e61a90ef1f76fea7b9c075fdbef5c3f68a49b3610c` |
| result `RESULT_SEED1.md` | `60428d2acd89313bfabaf328e583daef1f90396401bc1447d1a03c6ebf6a7c02` |
| outputs `out_v5b_seed1.jsonl` | `0708689243cb5771a4e161723bcc775e54147b55a33929c5b686417614ebf02a` |
| jobs `batch_v5b_seed1.jsonl` | `e3571ea032387bae97c42529af580405ce331e3968b6c7093f92784fc07c757d` |

`tests/test_v6_seed1_d8_addendum.py` recomputes the seed-0 rows of this addendum from the published `per_unit.csv`.

## What does not change

The V5B package, its two primary contrasts (`retrieved_task − placebo` +0.169, positive; `mismatched_type − placebo`
+0.015, equivalent), its secondary contrasts and their states, the findings and the direction status.
