# Work placement, pull requests, issues and the daily synchronisation report

**Status:** rules for every agent and contributor, proposed 2026-11-14 together with the
[consolidation map](consolidation-map.md). The maintainer confirms or amends them through the pull request that
introduces them.

## 1. The rule for agents

Every new research task names, **before work starts**, its target directory in this repository and its branch, in the
issue or the first message of the task:

```
Target: data/lab/<experiment-id>/   code: scripts/<family>/   docs: docs/11-research-laboratory/<topic>.md
Branch: claude/<topic>-<date>   (or codex/…, docs/…, data/…, fix/…)
```

- **No new independent repository** without the owner's explicit consent. A second clone is not allowed either: use a
  worktree of the canonical clone.
- One branch is one pull request is one topic. Work on a branch that is not on GitHub is "local"; local work older than a
  day appears as an alert in the synchronisation report.
- Every worktree lives under the working root named in the consolidation map and is removed only after the pull request
  is merged and the owner agrees.
- Frozen experiments (a manifest pins their bytes, or their README declares them frozen) are read-only. Corrections go in
  new files or new versions; check first with `python scripts/pinned_files.py --check PATH`.
- Large raw data, secrets, sealed data and blinding keys never enter a public pull request (section 5 of the map).

## 2. Reporting finished work

Finish every stage with this block in the pull request (and in the task's final message):

```
HANDOFF
Branch and head: …            Pull request: #… (or "none, because …")
In Git / only local: …
Tests run and result: …
Issues touched and the acceptance criterion each one meets: …
Frozen files touched: none | listed
Held for the owner: … (results, keys, raw data, spending)
```

A task is finished only when its result is on the main line, or its pull request is open and the HANDOFF block says what
is held and why. A task that ends with results that are neither is reported by the synchronisation report as
`FINISHED_NOT_PUBLISHED`.

## 3. When to open a pull request

After every stage that produced code, data or a document that later work uses. Open it as a draft within a day of the
first useful commit; mark it ready only after the required checks pass. Merging is the maintainer's action.

## 4. Issues

- An issue states a question or a deliverable and **at least one acceptance criterion** (a file, a test, a measured
  threshold).
- Close an issue with `Closes #N` only when the pull request quotes the criterion and points to the file or test that
  meets it. If the criterion is not met, comment instead of closing.
- Before starting, search open issues and pull requests, `git log -S"<symbol>"`, the lab map and the project memory, and
  write the result under "Does this already exist?" in the pull request.

## 5. What GitHub should show

Each experiment appears in four states, each visible without reading code:

| State | Where it is visible |
|---|---|
| Planned | an issue with acceptance criteria, label `status:planned` |
| Running or frozen | a draft pull request with the protocol; the README of `data/lab/<id>/` states "Status: frozen" |
| Completed | merged; the README opens with "Status: completed", the headline numbers, the limits, and the reproduction command |
| Negative, inconclusive or invalidated | merged like any result; the README opens with "Status: negative", "inconclusive" or "invalidated", and the reason. A negative result is never left out |

Proposed labels (to be created only with the maintainer's consent): `status:planned`, `status:running`,
`status:completed`, `status:negative-result`; `status:blocked` already exists.

A pull request that changes a result updates the README or roadmap line that mentions it in the same pull request.

## 6. When the owner's consent is required

Merging; pushing unpublished results; anything touching keys, sealed data or blinding; paid APIs (DeepSeek V4.1 Flash
only, with a ledger line per call); changes to branch protection, permissions or security settings; deleting branches,
worktrees or folders; changes to the running coordinator; new files inside a frozen experiment; publishing a new
interpretation of results; licensing; public comments in the owner's name.

## 7. The daily synchronisation report

`scripts/aamr_sync_report.py` (standard library; no network except the optional GitHub section; no model; no paid API).
It writes only to the report folder you name.

```
python scripts/aamr_sync_report.py local  --config <AAMR_ROOT>/sync/sync.local.json --out <AAMR_ROOT>/sync/reports
python scripts/aamr_sync_report.py github --repo krapcys1-maker/adaptive-agent-memory-research --tree <AAMR_ROOT>/repo
python scripts/aamr_sync_report.py all    --config … --repo …
```

Exit code 0: nothing to report; 1: warnings; 2: alerts. The configuration (see
[the example](aamr-sync-config.example.json)) lists the roots to search, folders outside Git, private repositories,
branches held on purpose, and the tasks to watch: a task is a marker file that shows it finished and the repository path
where its result must appear.

| Code | Meaning |
|---|---|
| `LOCAL_ONLY_BRANCH` | commits on a local branch that no remote has (alert after a day) |
| `FINISHED_NOT_PUBLISHED` | a task is done but its result is not on the main line; held tasks stay visible |
| `DETACHED_UNREACHABLE` | detached HEAD carrying commits no branch has |
| `NO_REMOTE` | a repository with no remote needs a verified backup |
| `DIRTY`, `UNTRACKED` | uncommitted work; untracked files are compared with the main line |
| `STALE_WORKTREE_MISSING`, `STALE_WORKTREE_MERGED` | broken or removable worktrees (removal needs consent) |
| `BEHIND_MAIN` | a checkout far behind the main line |
| `NON_GIT_CHANGED` | new or changed files in a folder outside Git, against its manifest |
| `PR_*`, `ISSUE_*`, `BRANCH_*`, `EXPERIMENT_*` | pull-request state and checks, issue freshness and resolution, merged or stale branches, missing experiment READMEs and index entries |

It never opens a file whose name looks like a secret, a blinding key or sealed data (`.env`, `*.key`, `*secret*`,
`KEY_*`, `blind_*`, a `sealed/` folder): they are listed by name only. It does not fetch, so run `git fetch` in the
canonical clone first; remote-tracking refs older than a week are flagged and the result then errs on the side of caution.
Reports name local paths: keep them in an ignored folder and do not publish them.

Scheduling it (for example with the Windows Task Scheduler, once a day) is a separate step that the owner approves.
