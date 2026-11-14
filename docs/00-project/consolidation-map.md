# Consolidation map: one public repository, one working root, a laboratory that keeps running

**Status:** proposal, revised 2026-11-14 after the owner's decision on the coordinator. Written by an AI agent for the
maintainer. Only the items marked "done" have happened; everything else waits for the maintainer's confirmation and,
where noted, separate consent. Nothing in this document changes a frozen experiment or the running laboratory.

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

**State on the maintainer's machine, checked 2026-11-14:**

| Item | State |
|---|---|
| `repo/` (fresh clone at `main`) | exists |
| `work/consolidation-foundation` (worktree of the pull request that introduced this map) | exists |
| `sync/` | exists, **empty** except for the first dated reports; no configuration is kept there yet |
| `private/` | exists, **empty**; nothing has been moved into it |

Legacy folders are listed in section 6; none was moved or deleted.

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

## 4. Where each existing component goes

| Component | Canonical location | State and route |
|---|---|---|
| Structured-memory runtime, source windows, retrieval metadata | `tools/structured_memory_*`, `data/lab/structured-memory-v1` and related | **done**: merged as slices of the former large pull request; its branch stays as history |
| EXP-PILOT-0 | `data/lab/experience-pilot-v0` | **done** |
| EXP-XFER-1 (stage S1) | `data/lab/experience-xfer-v1`, `tests/test_experience_xfer_v1.py` | 5 local commits; one test repaired (the frozen pilot README gained an amendment) and 3 memory events migrated; own pull request |
| AAMR-NIGHT-1 | `data/lab/aamr-night1` | 7 local commits stacked on EXP-XFER-1; a test that reads a document outside the repository needs an in-repository fixture; 2 memory events to migrate |
| AAMR-NIGHT-2 | `data/lab/aamr-night2` | 5 local commits stacked on NIGHT-1; **publication of the results is the owner's decision**, and the raw-freeze manifest names a local drive that needs a ruling |
| K1: specification, decision log, results summary | `data/lab/aamr-k1/` | not in any repository today; **results are not published without the owner's decision**. The executor writes outside any `data/` folder, so the report cannot name a target path yet (see the gap in the [rules](work-placement-and-sync-rules.md#8-coverage-and-its-limits)) |
| K1: executor code and its tests | `scripts/aamr_k1/`, `tests/` | not in any repository today; import unchanged, add a pytest entry point for the existing offline checks |
| K1: raw runs | outside Git (`private/`), manifest in `data/lab/aamr-k1/raw-freeze.json` | see section 5 |
| Independent audits of AAMR and K1 (Fable) | `docs/11-research-laboratory/audits/` | the repository audit and the K1 specifications v0.1 to v0.3 after review; the K1 scientific audit waits until its author finishes; blinding keys never |
| Decision-rule characteristics (`rulecheck`) | `scripts/rule_characteristics.py` | open pull request, history and authorship preserved |
| Hypothesis-ledger methodology and statistics (Holm, discordant pairs) | `docs/11-research-laboratory/hypothesis-ledger-methodology.md`, `scripts/hypothesis_statistics.py` | next package; pure functions extracted from the ledger class (a new commit that names the original author) |
| T39 temporal-layer plan, reviews, reproductions | `docs/11-research-laboratory/t39-temporal-layer/` | package designed, not published: needs the owner's ruling on isolating the author of the held-out set |
| Verification-level specification | `docs/11-research-laboratory/` | document only |
| Coordinator (the running laboratory) | **stays in place** | unchanged by this proposal; it exports research products to this repository; see section 7 |
| Synchronisation tools | `scripts/aamr_sync_report.py` | **done** in the pull request that introduced this map; reads the laboratory's declared experiments and closed missions without modifying anything |
| Anything under `private/` | stays private | hashes only in this repository |

Not part of this project, and not to be consolidated: a cloned third-party research tool the maintainer used earlier (its
remote belongs to someone else; its local commits need a fork, which is the maintainer's decision), and a separate unrelated
project.

## 5. Large data, secrets and blinding keys

| Class | Examples | Where | Rule |
|---|---|---|---|
| Public and small | protocols, results, reports, metadata | this repository | commit; declare SHA-256 in the experiment's manifest |
| Public and large | raw model transcripts that make a result reproducible | **owner's decision** between Git LFS and a release asset; neither is private | check the current GitHub LFS quota before use; commit only a pointer and the SHA-256 |
| Private | secrets, tokens, sealed splits, blinding keys and labels, personal data, raw runs not cleared for publication, the laboratory's state and database | the laboratory's home, `private/`, or another private store; never a public repository | commit only the SHA-256 and a note that the item exists; a key is never in the same pull request as the proposals it blinds |

GitHub offers no private area inside a public repository. A private repository would be a new repository and needs the
owner's consent; a verified encrypted copy on a second physical location is the recommended minimum.

## 6. Legacy folders (nothing removed)

Removal happens only after the content is verified complete in its target and the maintainer agrees. **The laboratory's
home is not a legacy folder and is not on this list.**

| Legacy location | Content | Removable when |
|---|---|---|
| the old main clone and its 36 worktrees | merged branches and 5 branches with unmerged work | the unmerged work is in pull requests and `repo/` holds every branch |
| the folder of earlier integration worktrees | trial branches, review worktrees | their pull requests are merged |
| the K1 executor folder | code, tests, specification, raw runs | code and specification are imported; raw runs are archived with a verified manifest |
| the 2026-11-13 audit and the K1 specifications folder | audits and drafts | imported to `docs/` or declared superseded |
| a preparation package for a next experiment | superseded plan | at once, after the maintainer agrees |
| a runner scheduling test folder | test evidence | stored where the maintainer wants the laboratory's test evidence kept |
| the audit backups | restored checkouts of earlier deliveries | a newer verified backup exists |

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

1. A second physical location for private backups.
2. Replace the old main clone by `repo/` and point the laboratory's repository setting at it (a change of the running
   installation, so only when the maintainer wants it).
3. K1: publish code and specification (recommended), results later; raw runs private, LFS, or release asset; and a target
   path for its results.
4. The EXP-XFER-1 and NIGHT-1 pull requests may be opened as drafts once their tests are repaired; NIGHT-2 results wait.
5. A fork for the cloned third-party tool.
6. Whether to create the `status:` labels proposed in the work rules.
7. Whether, and where, the laboratory's infrastructure code is ever published.
