# Register of the autonomous laboratory's work, 2026-11-14

**Status: a one-time reconciliation of the maintainer's local laboratory (the "coordinator": a private repository, code only) against `main`, made on 2026-11-14 by the consolidation agent (Claude Sonnet 5.5). Every state below was read that day from the laboratory's database and folders or from GitHub. It is a point-in-time record, not a live view; the daily synchronisation report ([export flow](../00-project/coordinator-export-flow.md)) is the live view.**

## How it was made

1. The coordinator's database (cycles, tasks, runs, decisions, experiments), its folders (missions, reports, workspace, outbox, inbox, sandboxes, docs) and the state reported by the session that builds the laboratory's code were read, read-only.
2. For every item the result was looked for on `main` by path and, for copies, by SHA-256.
3. NIGHT-1, NIGHT-2 and K1 were checked rather than assumed complete (section 1).
4. Everything finished and safe to publish that was missing went through [`scripts/aamr_export.py`](../../scripts/aamr_export.py): protected-data check, branch, pull request, the 12 required checks, merge, confirmation on `main`.
   What could not be published is listed in section 7 with the reason.

## 1. The three experiments

| Experiment | State | On `main` | Pull requests | Checked on 2026-11-14 |
|---|---|---|---|---|
| AAMR-NIGHT-1 | completed 2026-11-13; development result, transfer not confirmed | [data/lab/aamr-night1](../../data/lab/aamr-night1/README.md) | #137; AI review, mechanical verification: #154 | raw run re-hashed against the published manifest: 17 of 17 match. `results.json` recomputed from the raw run with the script on `main`: 15 of 18 top-level keys identical; the three that differ are `done` and `state` (bookkeeping written after the analysis) and `open_problems`, a descriptive list whose last entry is chosen among equal counts in an order that depends on the interpreter's hash seed. No decision rule depends on it |
| AAMR-NIGHT-2 | completed 2026-11-13; development result, negative on the frozen main test | [data/lab/aamr-night2](../../data/lab/aamr-night2/README.md) | #141; AI review, mechanical verification: #154 | raw run re-hashed: 19 of 19 match. `results.json` recomputed: every analysis key identical; only `done` and `state` (bookkeeping) differ |
| AAMR-K1 (EXP-PLACEBO-0) | completed 2026-11-14; nothing decided at the registered 10 pp | [data/lab/aamr-k1](../../data/lab/aamr-k1/README.md) | #142 (mechanical record), #146 (AI audit, separate); run record, mechanical verification, review: #154 | raw run re-hashed: 21 of 21 match. Not recomputed in this reconciliation. The AI audit in #146 states that it re-derived the three contrasts from the raw data to the digit (its own statement; its scripts need the private raw run). The coordinator's own review of K1 (task 18) is **invalid as a review**: its context package carried no K1 result |

The registry rows are in [data/lab/experiment-registry.csv](../../data/lab/experiment-registry.csv) (`AAMR-NIGHT-1`, `AAMR-NIGHT-2`, `AAMR-K1`). The raw runs stay private (K1's is 326 MB); the published manifests list them by SHA-256 with relative paths.

## 2. Missions and tasks of the coordinator (18 tasks, 4 cycles)

| Task | What | Outcome | Where |
|---|---|---|---|
| 1, 2, 3, 4, 5 | link tests of the three agents (tasks 1 and 2 failed and were repeated as 4 and 5) | operational; no research content | not exported |
| 6 | one synthetic connection test of deepseek-flash | succeeded; USD 0.00020625 settled, the only paid call the coordinator ever made | [spend/coordinator-deepseek-ledger.jsonl](coordinator-outputs-2026-11/spend/coordinator-deepseek-ledger.jsonl), #154 |
| 7, 11 | reproduction of the C3 trap; mutation check of the resolver | verified reproductions | [t39-temporal-layer/reproductions](t39-temporal-layer/reproductions/), #139 |
| 8, 9, 10 | first plan, first AI review, owner brief of mission T39-TEMPORAL | superseded by iteration 2 | [t39-temporal-layer/iteration-1-superseded](t39-temporal-layer/iteration-1-superseded/), #139 |
| 12, 13, 14 | revised plan, second AI review, decision table A to R of mission T39-REVISION | proposal, **not approved**; 18 decisions open | [t39-temporal-layer/iteration-2-proposal](t39-temporal-layer/iteration-2-proposal/), #139 |
| 15 | AI review of NIGHT-2 | completed | [coordinator-outputs-2026-11/reviews](coordinator-outputs-2026-11/reviews/), #154 |
| 16, 17 | drafted replies to pull requests #129 and #130 | never posted (dry-run mode); the maintainers handled both pull requests and merged them on 2026-11-14 | drafts stay private |
| 18 | AI review of K1 | completed, **invalid as a review of K1** (see above) | [coordinator-outputs-2026-11/reviews](coordinator-outputs-2026-11/reviews/), #154 |

Missions T39-TEMPORAL and T39-REVISION are closed; their run reports are in [coordinator-outputs-2026-11/missions](coordinator-outputs-2026-11/missions/) (#154), their plan, reviews and reproductions in the T39 directory above (#139).

## 3. Decisions waiting for the maintainer

The coordinator holds three open scientific or halt decisions: the next step after NIGHT-2 (cycle `waiting_owner`; the frozen rule's recommendation is "return to the components") and after K1 (cycle `halted`, no decisive result). Nothing has been decided; no experiment has been started for either. Two community decisions
in its database (about pull requests #129 and #130) are stale: both pull requests are merged.

## 4. Design and methodology work that left the laboratory

| Work | State | Where |
|---|---|---|
| decision-rule characteristics (C1) | proposal with code and tests | [decision-rule-characteristics.md](decision-rule-characteristics.md), #134 |
| hypothesis ledger: statistics and methodology (C2) | proposal, not adopted; the prototype ledger stays in the laboratory | [hypothesis-ledger-methodology.md](hypothesis-ledger-methodology.md), #138 |
| mechanical verification levels (C4) | proposal | [mechanical-verification-levels.md](mechanical-verification-levels.md), #140 |
| test of agent isolation (D7) | completed test; fix in the laboratory's code with a regression test | [coordinator-outputs-2026-11/tests](coordinator-outputs-2026-11/tests/), #154 |
| audit of the laboratory (Claude Opus 5.5, 2026-11-14) | completed AI audit | [coordinator-outputs-2026-11/analysis](coordinator-outputs-2026-11/analysis/), #154 |
| EXP-A (EXP-ABS-0) | **draft proposal; not frozen, not run, not approved**; code and stimuli withheld | [exp-abs-0](exp-abs-0/README.md), #155 |

## 5. The laboratory's own code

The session that builds the laboratory's code ("Autolab": a knowledge registry, a domain adapter, a program loop, an export module, a repository steward, a demo) merged its work in the private repository `kordynator` (pull requests 1, 2 and 4 to 8). That is laboratory code: it stays there, by the maintainer's rule. Its two demonstration runs (`SYN-DEMO-20261114-1523`, `-1535`) used fake roles, no model and no real data: **tests of the laboratory, not research results**; they were not published and will not be.

## 6. Work in progress at the time of writing

| Id | What | State |
|---|---|---|
| autolab K1-REPLAY-A | a mechanical replay of K1 block A from the frozen data (no model call), proposed as the first real task for the laboratory's automatic hand-off to the export tool | in progress; when finished it goes through `aamr_export.py` into `data/lab/autolab-k1-replay-a/` or is held with a reason. Not on `main` at the time of writing |

## 7. Held, with the reason

| Item | Reason |
|---|---|
| D11 blind back-test of the hypothesis ledger (a sheet of 15 cases, a key committed by hash, labels) | **unfinished and blinded**: the labels have not been returned; the sheet, the key and the labels stay private until they are |
| prototype of the hypothesis ledger and the laboratory's local-only branches (`lab/hypothesis-ledger`, `lab/experiment-runner`) | laboratory code; the first holds a blinding key and the T39 mission definitions in its history, the second the mission definitions; never pushed |
| task transcripts, prompts, context manifests, mission definitions, the database, usage readings, sandboxes (copies of this repository), the drafted community replies | operational state or raw material of the laboratory; not research results |
| raw runs of NIGHT-1, NIGHT-2 and K1 | raw data (K1: 326 MB); pinned by SHA-256 in the published manifests |
| `stim_preview/` and the code of EXP-A | see [exp-abs-0](exp-abs-0/README.md): paths of the old layout, material derived from private K1 stimuli |
| the two synthetic demonstration runs | not research results (section 5) |

## 8. Limits of this register

* The reviews and audits listed here were written by AI agents; none is an independent human review.
* All copies of the raw data and of the laboratory's code backup are on one physical disk. That protects against deletion and a bad migration, not against disk failure; a second location is the maintainer's decision.
* The register is as complete as the laboratory's own records: work that was never a coordinator task or a declared experiment is visible only through the Git findings of the daily report.
