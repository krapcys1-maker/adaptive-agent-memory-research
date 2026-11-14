# Coordinator outputs imported from the maintainer's local laboratory (2026-11)

**Status: records, imported on 2026-11-14. Reviews and audits here were written by AI agents (Claude Fable 5.2 and Opus 5.5) inside the maintainer's local autonomous laboratory; none is an independent human review. Nothing here changes a frozen experiment, a verdict or a published result.**

The documents are in Polish, as the agents wrote them; this README is the English entry point. They were copied byte for byte except where a machine-local path was replaced by `[machine-local path omitted]`
(the edit is stated per file in [PUBLISHED_FILES.json](PUBLISHED_FILES.json), which also lists the SHA-256 of the published file and of the source as staged).

## Why this directory exists

The coordinator ("AAMR-COORDINATOR", a private repository, code only) produced work that had never reached this repository: three reviews of finished experiments, its mechanical verification of them, a run record of K1,
the run reports of the two T39 missions, a test of agent isolation, its ledger of paid calls and an audit of the laboratory itself. The experiments themselves were published earlier:
[NIGHT-1](../../../data/lab/aamr-night1/README.md), [NIGHT-2](../../../data/lab/aamr-night2/README.md), [K1](../../../data/lab/aamr-k1/README.md); the T39 plan, its reviews and reproductions
are in [../t39-temporal-layer/](../t39-temporal-layer/README.md).

## Read this before relying on any file

* **The K1 review is invalid as a review of K1.** The reviewer received a context package with no K1 result, so its verdict ("inconclusive") says nothing about the experiment. The coordinator's own
  verification of that review did not pass (`reviews/evidence-check-task-18.json`). The K1 interpretation that stands is the separate audit in
  [../audits/aamr-k1-scientific-audit-2026-11-14/](../audits/aamr-k1-scientific-audit-2026-11-14/README.md).
* **The review of NIGHT-2** saw the results and the report, not the raw sessions. **The review of NIGHT-1** is a direction decision as much as a review.
* **The mechanical verification** (`verification/`) was regenerated on 2026-11-14 after the laboratory's paths were switched; the verdicts are identical to the first run. For K1 three levels are `unchecked`
  because the laboratory has no analysis adapter for it.
* **The D7 test** found that, with the flags then in use, an agent could read a canary file outside its working directory. The fix is in the laboratory's code with a regression test. Any other harness that runs
  an agent with `--allowedTools` and relies on it to keep held-out material away from the agent should repeat the test.
* **The ledger** covers only the coordinator. The ledgers of the other paid work are in `data/lab/*/spend-ledger.jsonl`.

## Files

| File (under this directory) | What it is | Status | Note | SHA-256 of the source (first 16) |
|---|---|---|---|---|
| `reviews/night1-review-fable-2026-11-13.md` | independent review of NIGHT-1 and decision on the next direction (author: Claude Fable 5.2, at the owner's request, 2026-11-13) | AI-REVIEW | led to the specification of NIGHT-2; no model was run for it | `6fdeb93362c39a7c` |
| `reviews/night2-review-task-15.md` | coordinator task 15: independent review of NIGHT-2 (Fable) | AI-REVIEW | agrees with the frozen rule's recommendation; it saw results.json, REPORT.md, the specification, the protocol and the coordinator's verification, not the raw sessions | `16a7ba408deb9ca8` |
| `reviews/evidence-check-task-15.json` | the coordinator's mechanical check of the quotations in task 15 | MECHANICAL-CHECK | - | `bc208670aac8ca2c` |
| `reviews/k1-review-task-18-INVALID-AS-K1-REVIEW.md` | coordinator task 18: review of K1 (Fable) | AI-REVIEW-INVALID-AS-K1-REVIEW | the reviewer was given a context package without any K1 result (no results.json, REPORT.md or checker output), so its verdict INCONCLUSIVE says nothing about K1; the coordinator's own verification of it failed | `07bcf09b4dcc4609` |
| `reviews/evidence-check-task-18.json` | the coordinator's mechanical check of the quotations in task 18 | MECHANICAL-CHECK | it did not pass | `33a4fb18eae2b060` |
| `verification/NIGHT-1.md` | the coordinator's mechanical verification levels for NIGHT-1 | MECHANICAL-VERIFICATION | - | `0130a1095a69913f` |
| `verification/NIGHT-1.json` | same, machine-readable | MECHANICAL-VERIFICATION | - | `1c3d019fd64efd7a` |
| `verification/NIGHT-2.md` | the coordinator's mechanical verification levels for NIGHT-2 | MECHANICAL-VERIFICATION | - | `835697e603acba83` |
| `verification/NIGHT-2.json` | same, machine-readable | MECHANICAL-VERIFICATION | - | `761bf0affff07af9` |
| `verification/K1.md` | the coordinator's mechanical verification levels for K1 | MECHANICAL-VERIFICATION | provenance is `warn`; statistics, comparability and mechanism are `unchecked` because the coordinator has no analysis adapter for K1 | `ecce03b1667a99bf` |
| `verification/K1.json` | same, machine-readable | MECHANICAL-VERIFICATION | - | `8a74292de72d9fda` |
| `runs/K1-RUN_REPORT.md` | the coordinator's run record of K1 (one launch, no restarts, pinned files unchanged) | RUN-RECORD | - | `656593baf434ba8e` |
| `runs/K1-runner.log` | the runner's log of K1 | RUN-RECORD | - | `109719646580f0b3` |
| `missions/T39-TEMPORAL-mission-report.md` | run report of mission T39-TEMPORAL (iteration 1) | MISSION-RUN-REPORT | the plan, reviews and reproductions of this mission are in ../t39-temporal-layer/ | `4d86a0914092b4c1` |
| `missions/T39-REVISION-mission-report.md` | run report of mission T39-REVISION (iteration 2) | MISSION-RUN-REPORT | the final report of the same mission is ../t39-temporal-layer/iteration-2-proposal/final-report.md | `9841ea245da2fd93` |
| `tests/D7-agent-isolation-canary-test.md` | test of whether the coordinator's Claude CLI agents can read files outside their working directory (canary files, 20 calls), and the fix | TEST-REPORT | the fix (every tool rule confined to the working directory) is in the laboratory's code with a regression test; no real secret or key was touched | `3bacaec7b720915c` |
| `spend/coordinator-deepseek-ledger.jsonl` | the coordinator's own ledger of paid API calls | LEDGER | one synthetic connection test of deepseek-flash: 450 prompt and 25 completion tokens, USD 0.00020625 settled; hard cap USD 5.00; nothing else was ever spent through the coordinator | `56f35ca6ef5a83a9` |
| `analysis/autonomous-laboratory-review-2026-11-14.md` | audit of how the autonomous laboratory works, what it can do and what it lacks (author: Claude Opus 5.5, read-only review session, 2026-11-14) | AI-AUDIT | finding 2 of that audit (the K1 review package carried no result) explains why task 18 is invalid as a K1 review | `b2eecb4e4ed6667c` |

Sources: coordinator:docs/…, coordinator:reports/…, coordinator:state/…, coordinator:workspace/…, private:gh-revival/…, private:legacy/…. The full source path of each file is not published; the SHA-256 above identifies the original.

## What stays private

Task transcripts, prompts and context manifests, mission definitions, the coordinator's database and usage readings, the drafted community replies (never posted; superseded by the maintainer's actual handling of
pull requests #129 and #130), and the blinded material of the unfinished back-test of the hypothesis ledger (decision D11): the sheet, the key and the labels are withheld until the labels are returned.
