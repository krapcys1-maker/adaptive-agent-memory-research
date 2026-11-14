# Consolidation map: one project, one repository, one working root

**Status:** proposal, 2026-11-14. Written by an AI agent for the maintainer. Only the items marked "done" have happened;
everything else waits for the maintainer's confirmation and, where noted, separate consent. Nothing in this document
changes a frozen experiment.

## 1. Principle

Research, code, experiments, methodology, tests and publishable results live in **this repository** and nowhere else.
Local folders are working copies, scratch space or private storage. Work that exists only on one disk is unfinished work
and must be visible in the daily synchronisation report ([rules](work-placement-and-sync-rules.md)).

The coordinator (the local orchestration tool that schedules and supervises experiments) becomes a **component of this
repository**. It keeps its runtime state outside Git, but its code, tests and documentation are versioned here, and it
stores no research of its own.

## 2. One working root on the machine

```
<AAMR_ROOT>/
  repo/        the canonical clone of this repository (fast-forward only, never edited directly)
  work/        one Git worktree per branch, named after the branch; removed after the pull request is merged
  private/     material that must never reach the public repository: raw runs, sealed splits, blinding keys,
               secrets, backups; each item with a SHA-256 manifest that IS committed here (hashes only)
  sync/        the synchronisation configuration, folder manifests and dated reports (all ignored by Git)
```

No other directory may hold a clone. A second clone of the same repository is a copy of the same project, but it drifts;
use a worktree of `repo/` instead. Creating a repository with a different history needs the owner's consent.

**Done:** `repo/` (a fresh clone at `main`) and `work/consolidation-foundation` exist on the maintainer's machine.
Legacy folders are listed in section 6; none was moved or deleted.

## 3. Target layout inside the repository

The existing layout stays. New destinations are marked **new**.

| Path | Holds |
|---|---|
| `docs/00-project/` | scope, rules, decision log, this map |
| `docs/11-research-laboratory/` | protocols, audits, methodology; **new** `t39-temporal-layer/`, `audits/` |
| `data/lab/<experiment-id>/` | protocol, configuration, results, report, `raw-freeze.json` of one experiment; the README opens with its status |
| `scripts/` | experiment code and checks (`scripts/<family>/` for a family such as `wmb`); **new** `scripts/aamr_k1/` |
| `tools/` | reusable engines (`tools/project_memory`, structured memory); **new** `tools/coordinator/` |
| `tests/` | tests of the code above |
| `memory/` | append-only project memory |
| `.github/` | CI, issue and pull-request templates |

## 4. Where each existing component goes

| Component | Canonical location | State and route |
|---|---|---|
| Structured-memory runtime, source windows, retrieval metadata | `tools/structured_memory_*`, `data/lab/structured-memory-v1` and related | **done**: merged as slices of the former large pull request; its branch stays as history |
| EXP-PILOT-0 | `data/lab/experience-pilot-v0` | **done** |
| EXP-XFER-1 (stage S1) | `data/lab/experience-xfer-v1`, `tests/test_experience_xfer_v1.py` | 5 local commits; needs one test repaired (the frozen pilot README gained an amendment) and 3 memory events migrated; then a pull request that keeps the commits and authorship |
| AAMR-NIGHT-1 | `data/lab/aamr-night1` | 7 local commits stacked on XFER-1; needs a test that reads a document outside the repository replaced by an in-repository fixture, and 2 memory events migrated |
| AAMR-NIGHT-2 | `data/lab/aamr-night2` | 5 local commits stacked on NIGHT-1; **publication of the results is the owner's decision** and the raw-freeze manifest names a local drive that needs a ruling |
| K1: specification, decision log, results summary | `data/lab/aamr-k1/` | not in any repository today; import as one commit with provenance; **results are not published without the owner's decision** |
| K1: executor code and its tests | `scripts/aamr_k1/`, `tests/` | not in any repository today; import unchanged, add a pytest entry point that calls the existing offline checks |
| K1: raw runs | outside Git (`private/`), manifest in `data/lab/aamr-k1/raw-freeze.json` | see section 5 |
| Independent audits of AAMR and K1 (Fable) | `docs/11-research-laboratory/audits/` | the repository audit and the K1 specifications v0.1 to v0.3 after review; the K1 scientific audit waits until its author finishes; blinding keys never |
| Decision-rule characteristics (`rulecheck`) | `scripts/rule_characteristics.py` | open pull request, history and authorship preserved |
| Hypothesis-ledger methodology and statistics (Holm, discordant pairs) | `docs/11-research-laboratory/hypothesis-ledger-methodology.md`, `scripts/hypothesis_statistics.py` | next package; pure functions extracted from the ledger class (a new commit that names the original author) |
| T39 temporal-layer plan, reviews, reproductions | `docs/11-research-laboratory/t39-temporal-layer/` | package designed, not published: needs the owner's ruling on isolating the author of the held-out set |
| Verification-level specification | `docs/11-research-laboratory/` | document only; the code is tied to the coordinator layout |
| Coordinator | `tools/coordinator/` | see section 7; the running installation is untouched |
| Synchronisation tools | `scripts/aamr_sync_report.py` (this change) | **done** in this pull request |
| Test of the runner under the scheduler | `tools/coordinator/tests/` (as evidence) | with the coordinator import |
| Anything under `private/` | stays private | hashes only in this repository |

Not part of this project, and not to be consolidated: a cloned third-party research tool the maintainer used earlier
(its remote belongs to someone else; its local commits need a fork, which is the maintainer's decision), and a separate
unrelated project.

## 5. Large data, secrets and blinding keys

| Class | Examples | Where | Rule |
|---|---|---|---|
| Public and small | protocols, results, reports, metadata | this repository | commit; declare SHA-256 in the experiment's manifest |
| Public and large | raw model transcripts that make a result reproducible | **owner's decision** between Git LFS and a release asset; neither is private | check the current GitHub LFS quota before use; commit only a pointer and the SHA-256 |
| Private | secrets, tokens, sealed splits, blinding keys and labels, personal data, raw runs not cleared for publication | `private/` or another private store, never in a public repository | commit only the SHA-256 and a note that the item exists; a key is never in the same pull request as the proposals it blinds |

GitHub offers no private area inside a public repository. A private repository would be a new repository and needs the
owner's consent; a verified encrypted copy on a second physical location is the recommended minimum.

## 6. Legacy folders (nothing removed yet)

Removal happens only after the content is verified complete in its target and the maintainer agrees.

| Legacy location | Content | Removable when |
|---|---|---|
| the old main clone and its 36 worktrees | merged branches and 5 branches with unmerged work | the unmerged work is in pull requests and `repo/` holds every branch |
| the folder of earlier integration worktrees | trial branches, review worktrees | their pull requests are merged |
| the K1 executor folder | code, tests, specification, raw runs | code and specification are imported; raw runs are archived with a verified manifest |
| the 2026-11-13 audit and the K1 specifications folder | audits and drafts | imported to `docs/` or declared superseded |
| a preparation package for a next experiment | superseded plan | at once, after the maintainer agrees |
| a runner scheduling test folder | test evidence | stored with the coordinator tests |
| the audit backups | restored checkouts of earlier deliveries | a newer verified backup exists |

## 7. Coordinator migration (history preserved, production untouched)

1. **Inventory (done):** commits, branches, tests, secrets and database code were separated. Runtime state, secrets, local
   configuration, sandboxes and the live database are never imported.
2. **Import:** `git format-patch` limited to code, tests and documentation, paths rewritten under `tools/coordinator/`,
   applied with `git am` on a branch of this repository. Authors, dates and messages are kept. One commit per source
   branch that is worth keeping.
3. **Gate the database migration:** the schema-upgrade code stays out until the upgrade gate that is documented but not
   implemented is written and tested.
4. **CI:** a separate job runs the coordinator tests (standard library only).
5. **Cutover, only in a maintenance window the owner approves:** the scheduled task is pointed at
   `repo/tools/coordinator` and its runtime directory through one environment variable; the old folder stays as the
   rollback until a week of clean ticks.
6. **Retire** the old folder after a second approval.

## 8. Open decisions for the maintainer

1. A second physical location for private backups.
2. Replace the old main clone by `repo/` and point the coordinator's repository setting at it.
3. K1: publish code and specification (recommended), results later; raw runs private, LFS, or release asset.
4. The EXP-XFER-1 and NIGHT-1 pull requests may be opened as drafts once their tests are repaired; NIGHT-2 results wait.
5. A fork for the cloned third-party tool.
6. Whether to create the `status:` labels proposed in the work rules.
