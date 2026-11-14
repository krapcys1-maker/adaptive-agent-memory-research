# EXP-A (EXP-ABS-0): draft specification, audit and design-stage logs

**Status: DRAFT / PROPOSAL. NOT FROZEN. NOT RUN. NOT APPROVED. This is not a study and has no result.** Everything here was written by AI agents (Claude Fable 5.2 and Opus 5.5) on 2026-11-14 in the maintainer's local
laboratory. Nothing here was run on a model; the only executed things are design-stage simulations and unit tests of the draft code, whose logs are included. Whether the experiment is frozen, whether its executor is built and
whether it runs are three separate decisions of the maintainer, none of which has been made.

The documents are in Polish, as the agents wrote them; this README is the English entry point. Files were copied byte for byte except where a machine-local path was replaced by `[machine-local path omitted]`
(stated per file in [PUBLISHED_FILES.json](PUBLISHED_FILES.json)).

## The question

K1 ([data/lab/aamr-k1](../../../data/lab/aamr-k1/README.md)) found that no contrast detected a 10 percentage-point effect of the memory content. The NIGHT-1 review
([../coordinator-outputs-2026-11/reviews/](../coordinator-outputs-2026-11/README.md)) reports that in [NIGHT-1](../../../data/lab/aamr-night1/README.md) the success-trace memory lost 9 tasks, 8 of them by copying a value or a step from the shown example
(a mechanical classification the review itself calls possibly incomplete). EXP-A asks whether **removing the copied values** (abstraction) takes away
part of the harm, by comparing arms in which the same traces are shown in raw and in abstracted form, with matched controls. The exact estimand, arms, thresholds and decision states are in
[spec/SPEC_EXP_A_v0.2.md](spec/SPEC_EXP_A_v0.2.md) (section 8) and are not repeated here.

## Where it stands

1. v0.1 (Fable 5.2) was audited by Opus 5.5: **ACCEPT WITH FIXES**. The audit found, among six items K1 to K6, that the abstraction rule as written could not be executed (in the audit's own implementation it would stop preparation in 19% of the M blocks and 13% of the S blocks for the G and L tasks) and that the main
   contrast did not match the question. [audit/RAPORT_AUDYT_EXP_A_v0.1.md](audit/RAPORT_AUDYT_EXP_A_v0.1.md).
2. v0.2 takes in the fixes K1 to K6 and the remarks N1 to N3 of that audit ([spec/SPEC_EXP_A_v0.2.md](spec/SPEC_EXP_A_v0.2.md), section 0). **No audit of v0.2 itself is included here.**
3. The stimulus and analysis code for v0.2 exists and its tests pass (`logs/code-tests-v0.2.out`). **The executor that would run the episodes was not built.**

## What is withheld, and why

| Withheld | Reason |
|---|---|
| the stimulus and analysis code (`expA_*.py`), the audit scripts, the power-simulation scripts and the tests | they read the pre-consolidation private locations of the K1 stimuli and the BFCL function documents by absolute path, so they cannot run from this repository; the files were also not edited because the audit and the v0.2 text cite their exact bytes. A v0.3 that fixes the paths is the point at which they would be published, with a manifest |
| `stim_preview/` (5.8 MB: groups, plan, stimuli, decision and parameter tables) | derived from the K1 private material; its manifest keys hash files by old absolute path |

The withheld files are pinned by SHA-256 in the maintainer's private area and are not part of any claim made here.

## Files

| File (under this directory) | What it is | Status | Note | SHA-256 of the source (first 16) |
|---|---|---|---|---|
| `spec/SPEC_EXP_A_v0.2.md` | specification v0.2 (Claude Opus 5.5, from v0.1 and the audit): the CURRENT draft | DRAFT-SPEC-CURRENT | states itself as `projekt, NIE zamrozony, NIE uruchomiony`; freezing, building the executor and starting each need the owner's separate approval | `727d1ccfff837078` |
| `spec/SPEC_EXP_A_v0.1.md` | specification v0.1 (Claude Fable 5.2) | DRAFT-SPEC-SUPERSEDED | audited, then superseded by v0.2 | `83d9b8acba579404` |
| `spec/ANALIZA_SENSU.md` | analysis of whether the question makes sense and what each outcome would mean | DESIGN-NOTE | - | `9fc60a43fbed3897` |
| `audit/RAPORT_AUDYT_EXP_A_v0.1.md` | methodological audit of v0.1 (Claude Opus 5.5): verdict ACCEPT WITH FIXES, findings K1 to K6 | AI-AUDIT | an AI audit, not an independent human review; no model was called for it | `ceb7c31f82976969` |
| `audit/out/audit_abstraction.out` | output of the audit's check of the abstraction rule | AUDIT-LOG | - | `fbdd3fdda5e75aaf` |
| `audit/out/audit_calls_mc1.out` | output of the audit's call-count check | AUDIT-LOG | - | `ca5198256de27520` |
| `audit/out/audit_copy_k1.out` | output of the audit's check of copying in K1 data | AUDIT-LOG | - | `0eeee1ef093e0090` |
| `audit/out/audit_joint_match.out` | output of the audit's joint-matching check | AUDIT-LOG | - | `0b975b3799bae670` |
| `audit/out/audit_power.out` | output of the audit's independent power check | AUDIT-LOG | - | `27fe7ff20b554173` |
| `audit/out/diag_leak.out` | output of the audit's leakage diagnosis | AUDIT-LOG | - | `bfc1edeeec0a84c0` |
| `audit/out/block_lengths_GL.csv` | block lengths table used by the audit | AUDIT-TABLE | - | `3c3420430703397c` |
| `audit/out/decision_table_584.csv` | the 584-row decision table used by the audit | AUDIT-TABLE | - | `64354513e4e80bae` |
| `logs/power-simulation-v0.1.out` | power simulation of v0.1 (design stage; no experimental data) | DESIGN-STAGE-SIMULATION | - | `ec740d3524f899e4` |
| `logs/prior-evidence-v0.1.out` | prior evidence taken from K1 and NIGHT-2 results | DESIGN-STAGE-SIMULATION | - | `602336da85b4593b` |
| `logs/power-simulation-v0.2.out` | power simulation of v0.2 (design stage) | DESIGN-STAGE-SIMULATION | - | `ab51edd88e4695ac` |
| `logs/code-tests-v0.2.out` | result of the unit tests of the v0.2 stimulus and analysis code | TEST-LOG | the code itself is withheld (see README) | `6b34ee57b6a9ed85` |
