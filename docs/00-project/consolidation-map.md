# Consolidation map: one public repository, one working root, a laboratory that keeps running

**Status:** carried out on 2026-11-14 under the maintainer's written delegation; this document now describes the state reached, where the earlier text proposed it. Written by an AI agent for the maintainer. The running laboratory was not changed by the consolidation, and nothing in this document changes a frozen experiment.

## 1. Principle

AAMR is the **only public repository** of this research. Finished research code, protocols, results (negative results
included) and reports belong on branches and in pull requests of this repository, and nowhere else.

The **coordinator** (the maintainer's local autonomous laboratory: it schedules and supervises experiments and keeps its
own runtime state) **stays where it is and keeps running**. Research may be started and carried out there. Nothing in this
document retires it, moves it, stops its scheduler or changes its database. What changes is the exit: whatever the
laboratory finishes must also reach this repository, and the daily report shows every finished task whose result has not.

| Stays in the laboratory (never in the public repository) | Goes to this repository (branch and pull request) |
|---|---|
| operational state, the database, queues, locks, logs | completed research code and its tests |
| local configuration, secrets, tokens | protocols and frozen configurations |
| blinded material: sealed splits, keys, labels | results, **including negative and inconclusive ones**, with their limits |
| raw runs not cleared for publication (only a SHA-256 manifest is published) | reports, audits and decisions that a reader needs |

Local folders other than the laboratory are working copies, scratch space or private storage. Work that exists only on one
disk is unfinished and must be visible in the daily synchronisation report ([rules](work-placement-and-sync-rules.md)).

## 2. One working root for the public project

```
<AAMR_ROOT>/
  repo/        the canonical clone of this repository (fast-forward only, never edited directly)
  work/        one Git worktree per branch, named after the branch; removed after the pull request is merged
  private/     material that must never reach the public repository: raw runs not yet cleared for
               publication, backups, manifests of what exists; hashes of its content are committed, content is not
  sync/        the synchronisation configuration, folder manifests and dated reports (all ignored by Git)
```

The laboratory has its own home and is **not** part of this tree. No other directory may hold a clone: use a worktree of
`repo/` instead. Creating a repository with a different history needs the owner's consent.

**State on the maintainer's machine, 2026-11-14 (after the consolidation):**

| Item | State |
|---|---|
| `repo/` | the canonical clone at `main`; the git-ignored data that experiments expect (`external/`, `sources/papers`, `data/lab/arena/raw`) was moved into it from the old clone; every commit of the three legacy clones is kept as `refs/legacy/*` |
| `work/` | worktrees of the branches in progress only; those of merged branches were removed |
| `private/` | `raw` and `gh-revival` (raw runs and private reports of earlier experiments), `k1-executor` (the K1 executor folder with its 326 MB raw run), `legacy` (older audit and preparation folders, venv package lists, the old clone's scratch data), `backups` (the restored audit deliveries and a copy of the coordinator's configuration before the switch), `docs-local` (the local coordination documents) |
| `sync/` | `sync.local.json`, the folder manifests and the dated reports; the scheduled task `AAMR-SYNC-REPORT` runs the report every day at 07:30 |

**Compatibility stubs.** The coordinator's database stores some absolute paths of the old layout, and a migration of a running database needs its own safeguard (a copy and a restore test), so the
old names are kept as directory junctions that point into the working root (delete a junction and move the folder back to undo): the old clone's name -> `repo/`, the old
`GH_REVIVAL` folder -> `private/gh-revival`, the K1 executor folder -> `private/k1-executor`, the 2026-11-13 audit folder -> `private/legacy/aamr-audit-2026-11-13`. The coordinator's
read-only commands (`lab list`, `runner check`, `status`) gave identical output before and after the switch, and its next scheduled ticks ran without error.

## 3. Target layout inside the repository

The existing layout stays. New destinations are marked **new**.

| Path | Holds |
|---|---|
| `docs/00-project/` | scope, rules, decision log, this map |
| `docs/11-research-laboratory/` | protocols, audits, methodology; **new** `t39-temporal-layer/`, `audits/` |
| `data/lab/<experiment-id>/` | protocol, configuration, results, report, `raw-freeze.json` of one experiment; the README opens with its status |
| `scripts/` | experiment code and checks (`scripts/<family>/` for a family such as `wmb`); **new** `scripts/aamr_k1/` |
| `tools/` | reusable engines (`tools/project_memory`, structured memory) |
| `tests/` | tests of the code above |
| `memory/` | append-only project memory |
| `.github/` | CI, issue and pull-request templates |

The laboratory's own infrastructure (scheduler, database layer, adapters, isolation) is not part of this layout. Whether
and when any of it is published is the owner's decision, separate from the export of research results.

## 4. Where each existing component went

| Component | Canonical location | State and route |
|---|---|---|
| Structured-memory runtime, source windows, retrieval metadata | `tools/structured_memory_*`, `data/lab/structured-memory-v1` and related | merged as slices of the former large pull request (#121 to #125); its branch stays as history |
| EXP-PILOT-0 | `data/lab/experience-pilot-v0` | merged (#111, #120) |
| EXP-XFER-1 (stage S1) | `data/lab/experience-xfer-v1` | merged (#136); one test repaired for the pilot README amendments; events migrated |
| AAMR-NIGHT-1 | `data/lab/aamr-night1` | merged (#137), with a README, a registry row and the raw freeze published byte for byte with an erratum (the maintainer's ruling) |
| AAMR-NIGHT-2 | `data/lab/aamr-night2` | merged (#141); results published, negative on the frozen main test |
| K1: mechanical record (specification, executor code and tests, stimuli, outcomes, generated report) | `data/lab/aamr-k1/` | merged (#142); the raw run stays private with its SHA-256; machine-local paths in frozen files are explained in an erratum |
| K1: scientific audit by an AI auditor | `docs/11-research-laboratory/audits/aamr-k1-scientific-audit-2026-11-14/` | merged (#146) as a separate, labelled interpretation; the blinded material is withheld |
| Decision-rule characteristics | `scripts/rule_characteristics.py` | merged (#134), history and authorship preserved |
| Hypothesis-ledger methodology and statistics | `docs/11-research-laboratory/hypothesis-ledger-methodology.md`, `scripts/hypothesis_*.py` | merged (#138) as a proposal with tests; the ledger class and its database stay in the coordinator |
| T39 temporal-layer plan, reviews, reproductions | `docs/11-research-laboratory/t39-temporal-layer/` | merged (#139) as a proposal, nothing approved; the blinding risk for the held-out set is stated in its README |
| Mechanical verification levels | `docs/11-research-laboratory/mechanical-verification-levels.md` | merged (#140), document only |
| FactConsolidation label screen | `data/lab/mab-fc-label-screen-v1/` | merged (#143) as a preliminary screening by one AI reader |
| August planning documents, spend ledger, integration record | `docs/research/`, `data/lab/aam-deepseek-2026-11/`, `docs/00-project/` | merged (#132, #133, #145) |
| Coordinator (the running laboratory) | **stays in place** (its own home folder, outside this tree) | unchanged; it exports research products here through the export flow ([coordinator-export-flow.md](coordinator-export-flow.md)); its migration-bearing branch `lab/hypothesis-ledger` must not be merged as a whole |
| Synchronisation tools | `scripts/aamr_sync_report.py` | merged (#135, #144, #147): the report, the coordinator adapter, the export records |
| Anything under `private/` | stays private | hashes only in this repository |

Not part of this project, and not consolidated: a cloned third-party research tool the maintainer used earlier (its remote belongs to someone else; its local commits need a fork, which is the
maintainer's decision), and a separate unrelated project.

## 5. Large data, secrets and blinding keys

| Class | Examples | Where | Rule |
|---|---|---|---|
| Public and small | protocols, results, reports, metadata | this repository | commit; declare SHA-256 in the experiment's manifest |
| Public and large | raw model transcripts that make a result reproducible | **owner's decision** between Git LFS and a release asset; neither is private | check the current GitHub LFS quota before use; commit only a pointer and the SHA-256 |
| Private | secrets, tokens, sealed splits, blinding keys and labels, personal data, raw runs not cleared for publication, the laboratory's state and database | the laboratory's home, `private/`, or another private store; never a public repository | commit only the SHA-256 and a note that the item exists; a key is never in the same pull request as the proposals it blinds |

GitHub offers no private area inside a public repository. A private repository would be a new repository and needs the
owner's consent; a verified encrypted copy on a second physical location is the recommended minimum.

## 6. Legacy folders: what was verified, moved and removed (2026-11-14)

Before anything was removed, every ref of the three legacy clones was imported into the canonical clone (`refs/legacy/*`) and every commit not reachable from GitHub (23) was compared with `main`
by Git blob; the uncommitted files of the legacy worktrees were compared byte for byte (or as contained in a published file). All content was on `main`, or was an intended repair of a test, or
an append to the registry and event log. Then:

| Legacy location | Result |
|---|---|
| the old main clone and its 36 worktrees, the standalone lab-map clone | **removed**; their git-ignored data moved into `repo/` and `private/legacy`, their venvs removed after recording the package lists (`private/legacy/venv-freeze`); the old clone's name is a junction to `repo/` |
| the folder of earlier integration worktrees (`... - community-cleanup`, a second clone and 6 worktrees) | **removed** |
| `GH_REVIVAL` | its 36 worktrees were **removed**; its 27 data folders and loose notes moved to `private/gh-revival` (junction at the old name) |
| the K1 executor folder | moved to `private/k1-executor` (junction at the old name, because the coordinator's database names it); its code and results are in `data/lab/aamr-k1/` |
| the 2026-11-13 audit and the K1 specifications folder | moved to `private/legacy/aamr-audit-2026-11-13` (junction at the old name: the registry pins the K1 specification there); the specification itself is in `data/lab/aamr-k1/spec/` |
| the preparation package for a next experiment, the runner scheduling test folder | moved to `private/legacy` |
| the audit backups | moved to `private/backups/audit-backups` (they are the only backups of earlier deliveries; no newer verified backup exists) |
| local coordination documents of the old root | copied to `private/docs-local` and verified by hash, originals removed; the old root's `CLAUDE.md` is a pointer to the new one at the working root |

**Exceptions that remain, with the reason:** the coordinator's home folder (the running laboratory); the old root folder as a thin compatibility shell (the two secret files whose location the held-out isolation
design names, the data of the separate NIE persona project, a project settings folder, and two junctions); the four junctions named above; the maintainer's notes folder on the pattern-research ("pajęczyna") topic
(an unidentified process holds the folder itself, although no file in it is locked, so it was not moved); and the unfinished EXP-A (EXP-ABS-0) draft folders (specification v0.1 and v0.2, the methodological audit, code and
tests: unfrozen drafts awaiting the owner's approval; the code still reads the K1 executor and audit folders through the junctions, and the daily report lists them as held, with a warning until a protected-data check and
a publication decision exist). No session was running on 2026-11-14 at the end of the day. The K1 audit folder (its audit is published; it holds the blinded cases and their key) and the laboratory review report
were moved to `private/legacy`; the review is held in the daily report until the owner decides whether to publish it. A third-party research tool and an unrelated project that live on the same disk are not part of this project.

The 63 remote branches that were already contained in `main` were deleted on GitHub after each was re-checked against the live remote (same SHA as listed, still an ancestor of `main`, no open pull request); the list with
their last SHAs is kept in `private/backups/remote-branches-2026-11-14`. Only `main` and `codex/structured-memory-runtime-2026-11-04` (88 patches of unique history, the former large pull request) remain on the remote; there are no tags.

## 7. The laboratory and the repository

1. **The laboratory keeps running.** Its scheduler, database and configuration are not touched by anything in this
   repository. This proposal contains no cutover, no retirement date and no stop.
2. **What leaves the laboratory** is a finished research product: code that was run, its protocol, results (negative ones
   too), reports. The route is always a branch and a pull request here, named in advance (target directory and branch).
3. **What stays** is listed in section 1: state, database, local configuration, secrets, blinded material.
4. **How the gap is watched.** The daily report reads the laboratory's declared experiments (a run folder with
   `DONE.json` means finished) and its closed missions, and shows each task as one of: *on main*, *in PR*, *held by owner*,
   *finished only locally*. Tasks that ended without a declared target path are listed separately, so nothing is hidden.
5. **A limited export step** is needed for tasks whose products have no declared path (closed missions, the K1 executor):
   each such task gets a target path in this repository, either in the synchronisation configuration or, if the owner
   decides to change the laboratory, as a field of the task definition. Until then the report names the gap.
6. **Infrastructure code** of the laboratory is not required to be public. If the owner later wants it published, it would
   be imported with history under a path of the owner's choice, in a separate pull request, and the running installation
   would still not be switched over by that import.

## 8. Open decisions for the maintainer

1. A second physical location for private backups (the audit backups and the raw runs are on the same disk as everything else).
2. The coordinator's absolute paths: migrate its database and configuration to the new layout and then remove the four junctions. It needs a copy of the database and a restore test first; the coordinator's own
   fix for the K1 registry entry (branch `fix/lab-sync-keep-protocol`) is not merged there.
3. K1: the large raw run (326 MB) stays private; if it should be public, Git LFS or a release asset is the choice. K1b (about 1 000 tasks) is not designed or approved.
4. The held-out set of the T39 plan: who writes it, given that the plan is now public (decision G of that plan).
5. A fork for the cloned third-party tool.
6. Whether to create the `status:` labels proposed in the work rules.
7. Whether, and where, the laboratory's infrastructure code is ever published.
8. The `raw_root` field of the two published `raw-freeze.json` files (NIGHT-1, NIGHT-2) records a Windows drive path of the old layout (a drive letter, the old root folder, the old `GH_REVIVAL` folder and the run folder). It was published
   byte for byte with an erratum, on the owner's ruling for NIGHT-1. A later commit or revert does not remove it from Git history, nor from the pull-request refs and any clone or fork; only a history rewrite with a force push would, and that
   would break the recorded commit hashes and links. The folder names were already in earlier public commits; the user name and any secret are not in these files. Decision: leave as is, or replace the value in the current tree with an erratum
   (the frozen bytes then change; no manifest pins these two files), or rewrite history.
9. Whether to publish the EXP-A draft and the laboratory review report (held in the daily report).
10. The EXP-A (EXP-ABS-0) specification itself: approval to freeze, to build its executor and to run.

