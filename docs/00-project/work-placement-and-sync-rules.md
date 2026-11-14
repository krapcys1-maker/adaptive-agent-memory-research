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
- **The autonomous laboratory keeps running.** Research may be started and carried out in the maintainer's local
  coordinator. Agents must not stop it, move it, switch its scheduler or touch its database or configuration as part of
  this work. When a task there ends, its finished code, protocol, results (negative ones too) and report are exported to
  the target directory and branch named above, through a pull request. Its operational state, database, local
  configuration, secrets and blinded material stay out of the public repository.

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
branches held on purpose, the coordinator's configuration files, and the tasks to watch.

**Tasks are discovered, not typed in.** Give the report the coordinator's configuration files (and, if you want closed
missions, its missions report folder) and it lists every declared experiment by itself. An experiment is *finished* when
`DONE.json` exists in its run folder (the coordinator's own rule). Its result is expected at the repository path that
mirrors its output folder (from `data/` onwards), for the files its configuration requires. Entries in the configuration
are needed only for exceptions: a hold, a target path for a mission, a task the coordinator does not know. The adapter
parses only the paths and the experiments from those files and drops the rest at once; it does not open the
coordinator's database, state folder, `.env`, or any sealed or blinded material, and it changes nothing.

Every finished task is shown in one of these states:

| State | Meaning | Severity |
|---|---|---|
| `on main` | the result files are on the main line | none |
| `in PR #N` | the files are on a branch with an open pull request | note |
| `pushed, no open PR` | the files are on a remote branch that no open pull request carries | warning |
| `held by owner (reason)` | finished only locally, and publication is held by a decision of the owner | note (stays visible) |
| `finished only locally` | finished, and the files are on no remote | **alert** |
| `finished, no export target declared` | finished, but the report cannot say where its result belongs | warning |

| Code | Meaning |
|---|---|
| `LOCAL_ONLY_BRANCH` | commits on a local branch that no remote has (alert after a day) |
| `FINISHED_NOT_PUBLISHED`, `FINISHED_IN_PR`, `FINISHED_NO_EXPORT_TARGET` | a finished task whose result is not on the main line, waits in a pull request, or has no declared target (see the states above) |
| `DETACHED_UNREACHABLE` | detached HEAD carrying commits no branch has |
| `NO_REMOTE` | a repository with no remote needs a verified backup |
| `DIRTY`, `UNTRACKED` | uncommitted work; untracked files are compared with the main line |
| `STALE_WORKTREE_MISSING`, `STALE_WORKTREE_MERGED` | broken or removable worktrees (removal needs consent) |
| `BEHIND_MAIN` | a checkout far behind the main line |
| `NON_GIT_CHANGED` | new or changed files in a folder outside Git, against its manifest |
| `PR_*`, `ISSUE_*`, `BRANCH_*`, `EXPERIMENT_*` | pull-request state and checks, issue freshness and resolution, merged or stale branches, missing experiment READMEs and index entries |

It never opens a file whose name looks like a secret, a blinding key or sealed data (`.env`, `*.key`, `*secret*`,
`KEY_*`, `blind_*`, a `sealed/` folder): they are listed by name only. It does not fetch unless asked: pass
`--fetch-canonical` (it refreshes only the remote-tracking refs of the canonical clone) or run `git fetch` there first;
remote-tracking refs older than a week are flagged and the result then errs on the side of caution. With `--repo`
(or `repo` in the configuration) it reads the open pull requests through `gh` to tell *in PR* from *pushed, no open PR*.
Reports name local paths: keep them in an ignored folder and do not publish them.

Scheduling it (for example with the Windows Task Scheduler, once a day) is a separate step that the owner approves.

## 8. Coverage and its limits

What the report covers, checked on the maintainer's machine on 2026-11-14 without listing any task by hand:
the experiments declared in the coordinator's configuration (NIGHT-1, NIGHT-2 and K1) and its two closed missions.

What it does **not** cover, so that nobody reads it as complete:

- **K1 has no export target.** Its output folder is not under a `data/` folder, so the report can see that K1 finished
  but not where its result belongs; it is listed as `finished, no export target declared` until a target path is set.
- **Closed missions** (plans, reviews, reproductions) carry no target path in their definition. They are listed the same
  way until each gets a path in the configuration (`mission_targets`) or, if the owner changes the laboratory, in its task
  definition.
- **Work that never ran as a declared experiment**, for example a local branch of a stage run by hand, is visible only
  through the Git findings (`LOCAL_ONLY_BRANCH`, `DIRTY`, ...), not as a task.
- **A finished state is read from a marker**, not from the results: a run that wrote `DONE.json` but produced no
  required output is reported with the first required file as its expected path.
- **Tasks stored only in the coordinator's database** (its task queue) are not read, by design.

The limited export step that closes the first two gaps is a target path per task, set once; nothing in the laboratory has
to change for the report to use it.
