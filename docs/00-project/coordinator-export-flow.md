# From the coordinator to GitHub: the export flow

**Status:** operating procedure, introduced 2026-11-14 with the consolidation ([map](consolidation-map.md), [rules](work-placement-and-sync-rules.md)).
It adds an *export record* to the daily synchronisation report and a tool, `scripts/aamr_export.py`, that does the route below
([the tool](#the-tool)). It changes nothing in the running coordinator and needs no migration of its
database: the record lives in the synchronisation configuration, on the maintainer's machine, next to the report.

## The rule

A research task that ends in the laboratory (an experiment with a `DONE.json`, or a closed mission) is **not finished** until it has an export
record, and the record names one of two exits:

1. **Exported:** a target path in this repository, the result of a protected-data check, and a branch or pull request (later: merged);
2. **Held:** the same target and check, and an explicit hold with a reason and the date it started.

Work that has neither shows up in the daily report as a warning, and as an alert if its result is on no remote branch.

## The steps, in order

1. **Before the task starts**, name its target in this repository (`data/lab/<id>/`, `docs/11-research-laboratory/<topic>/` or
   `scripts/<family>/`) and its branch (`claude/<topic>-<date>`). For an experiment the coordinator's `out_dir` should already end in
   `data/lab/<id>`; for a mission, give the target in the export record.
2. **When it ends**, work in a worktree of the canonical clone (never in a second clone, never in the laboratory). Copy the product; never
   move or change the laboratory's original.
3. **Protected-data check.** Before anything is committed, check the product for what must not leave:
   - secrets: keys, tokens, `.env` files, credentials; machine-local absolute paths and addresses (replace in non-frozen documents, or explain in an erratum for frozen bytes);
   - blinded material: sealed splits, blinding keys and labels, held-out answers; a key is never in the same pull request as the proposals it blinds;
   - raw runs and transcripts not cleared for publication (only a SHA-256 manifest goes in);
   - the laboratory's own state: database, queues, locks, local configuration.

   Record the outcome: `clean` (nothing to withhold) or `withheld` (with the list of what is withheld and how it is pinned, usually by SHA-256).
4. **Branch and pull request.** One branch, one pull request, one topic; the first commit within a day. Put the HANDOFF block in the description
   (see the rules). Status of the work goes at the top of the README of `data/lab/<id>/`: planned, running, completed, negative, inconclusive or invalidated.
5. **Merge** only when the owner has authorised that merge or the task, the content was checked and the required checks on the exact head are green.
6. **Update the export record** with the branch, the pull request number and the check; after the merge the report shows the task as `on main`.
7. **A hold** (the owner decides publication, a protected-data question is open) is written into the record with `hold` and `hold_since`. A hold
   older than 14 days is a warning until it is decided or renewed with a new date.

## The tool

`scripts/aamr_export.py` does steps 2 to 6 for one finished task. It takes an *export plan* (a JSON file, [example](aamr-export-plan.example.json)):
which files are the publishable result and where they go in the repository, and which files are raw or protected and belong to the private area.

```text
python <AAMR_ROOT>/repo/scripts/aamr_export.py check  PLAN.json
python <AAMR_ROOT>/repo/scripts/aamr_export.py export PLAN.json --config <AAMR_ROOT>/sync/sync.local.json [--merge] [--move-private] [--sanitize-paths]
```

| Step | What the tool does |
|---|---|
| protected-data check | refuses a file whose name or folder looks like a secret, a blinding key, sealed data, a database or a transcript; a file inside the raw run folder; a file over 5 MB (50 MB in total); content with a token, key block, bearer credential, assigned secret or a personal e-mail address; a machine-local absolute path (unless the plan replaces it in a file that is not frozen, or a frozen file is published byte for byte together with an erratum); a manifest that records an absolute path; a target that already exists on `main` (unless the plan says `update`); a target outside `data/lab/`, `docs/`, `scripts/`, `tests/`; a result without a README that opens with its status |
| hold | **uncertain means held.** Nothing is pushed. The reasons (never the secret values: a match is masked) go into the export record with `hold` and `hold_since`, and the daily report shows the task as held. One held export never stops another; the exit code is 3 |
| private area | files named under `private` are copied (or, with `--move-private`, moved and replaced by a `<name>.MOVED.json` pointer) into `<AAMR_ROOT>/private`, with `MANIFEST.sha256.json` (relative paths, SHA-256, size) verified after the copy. The laboratory keeps its state and the pointer |
| branch and pull request | a worktree of the canonical clone, one commit with a `PUBLISHED_FILES.json` manifest (relative paths, SHA-256 of what was published and of the source, a note of any edit), a push, a pull request with a HANDOFF block, then the record is updated (`branch`, `pr`, `protected_check`, `private_location`) |
| checks and merge | only with `--merge`: wait for the required checks on the pull request; merge only when all pass. Failed or still pending checks: not merged, record gets a hold, exit code 4 |
| confirmation | after the merge the tool fetches and compares, for every published path, the blob on `origin/main` with the blob it committed; only then the record gets `merged` and `confirmed_on_main` and loses its hold |

**New manifests use relative paths.** A manifest of a raw run (`raw-freeze.json` or any file the plan marks `manifest`) lists the files relative to the run folder and
does not record an absolute `raw_root`; the check holds the export otherwise. Where the raw run lives is stated in the README and the private area's own manifest, so moving
the folder breaks nothing and nothing machine-local enters the public history (the frozen NIGHT-1, NIGHT-2 and K1 manifests are the reason: see their errata).

The tool writes only to the worktree it creates, the private area and the synchronisation configuration. It reads no database, `.env` or sealed material, calls no model and
no paid API, and never force-pushes or rewrites history. The worktree and the local branch are removed at the end, whatever the outcome.

## The export record

In `sync.local.json` (ignored by Git, see [the example](aamr-sync-config.example.json)):

```json
"require_export_record": true,
"hold_max_days": 14,
"exports": {
  "<task id>": {
    "targets": ["data/lab/<id>/README.md"],
    "protected_check": {"checked_on": "2026-11-14", "result": "withheld",
                        "withheld": ["raw run (326 MB), pinned by SHA-256"], "by": "<who>"},
    "branch": "claude/<topic>-<date>",
    "pr": 142,
    "private_location": ["private/raw/<id>/run"],
    "merged": true,
    "confirmed_on_main": "<12 characters of the commit on main>",
    "hold": "owner decides whether to publish",
    "hold_since": "2026-11-14"
  }
}
```

`targets` supplies the result path for a task the coordinator does not describe (every closed mission, an experiment whose output is not under
`data/`). `hold` and `hold_since` are optional; `branch` and `pr` are written once they exist. `aamr_export.py` writes all of these itself
(`merged` and `confirmed_on_main` only after it has compared the files on `main`). The task id is the coordinator's: an experiment name,
or `mission <name>` for a closed mission.

## What the daily report says

| Finding | Meaning | Severity |
|---|---|---|
| `EXPORT_NO_RECORD` | a finished task has no export record (only when `require_export_record` is on) | warning, or note if the result is already on `main` |
| `EXPORT_NO_PROTECTED_CHECK` | the record has no protected-data check | warning, or note on `main` |
| `EXPORT_PROTECTED_CHECK_OPEN` / `_INCOMPLETE` | the check has no valid result, or says "withheld" without listing what | warning |
| `EXPORT_BRANCH_MISSING` | the record names a branch but the result is on no remote branch | **alert** |
| `EXPORT_HOLD_STALE` | a hold without a valid date, or older than `hold_max_days` | warning |
| `EXPORT_RECORD_UNKNOWN_TASK` | a record names a task nobody knows (stale record) | note |

The existing findings still apply: `FINISHED_NOT_PUBLISHED` (alert when the result is on no remote), `FINISHED_NO_EXPORT_TARGET`, `FINISHED_IN_PR`,
`LOCAL_ONLY_BRANCH` and the rest ([rules, section 7](work-placement-and-sync-rules.md#7-the-daily-synchronisation-report)). The task table gains a column with the record.
Exit code: 0 nothing, 1 warnings, 2 alerts.

## Running it every day

The report is read-only and calls no model or paid API. It is meant to run once a day from the Windows Task Scheduler as its own task, separate from
the coordinator's scheduler and independent of it, writing to the ignored `sync/reports` folder:

```text
python <AAMR_ROOT>/repo/scripts/aamr_sync_report.py local --config <AAMR_ROOT>/sync/sync.local.json --out <AAMR_ROOT>/sync/reports --fetch-canonical
```

`--fetch-canonical` refreshes only the remote-tracking refs of the canonical clone (the one write the report makes). A run that ends with exit code 2 is
the signal to look at the report; the report names local paths, so it is not published.

## What this flow does not do

- It does **not** read or change the coordinator's database, state folder, `.env`, sealed or blinded material, and it needs no schema change.
  Do not merge the coordinator's `lab/hypothesis-ledger` branch as a whole: it would migrate the live database, and its schema-upgrade gate
  (`allow_schema_upgrade`) is not implemented. Any such migration needs its own safeguard (a copy, a restore test) first.
- It does not decide *whether* something may be published; the protected-data check is a human or agent judgement recorded in the file, not an
  automatic proof. A `clean` result that is wrong is a failure of the check, not of the report.
- The coordinator never exports by itself. It keeps running research; the export is a separate, reviewable pull request that an agent or the maintainer starts with
  `aamr_export.py`, and the tool stops at any uncertainty instead of guessing.
- Work that never ran as a declared experiment or mission is visible only through the Git findings (`LOCAL_ONLY_BRANCH`, `DIRTY`, ...).

## Tested on fictional tasks

`tests/test_aamr_export.py` runs the whole route on invented tasks against a local bare repository standing in for GitHub, with a fake pull-request client that really merges:
finished task to confirmed on `main` (relative manifest, private copy with a verified SHA-256 manifest, pointer, record, worktree removed); a pull request left open with `main` untouched;
failed and pending checks (no merge, a hold in the record); held exports for a token, an assigned secret, a personal address, a local path, a key file, `.env`, a blinding key, a blind
label file, a transcript and a database (nothing pushed, no secret value in the record or in the check file); a raw run file; a large file; an absolute manifest path; a missing README status;
an overwrite; a target outside the allowed folders; path replacement in a file that is not frozen, with the edit stated in the manifest; a frozen file with paths that needs its erratum;
one held export not stopping the next; the daily report reading what the tool wrote; and a content scan that stays linear on a 5 MB single line.

**End to end on the real repository, 2026-11-14.** A fictional finished task was built outside the laboratory (a run folder with a `DONE.json`, an output folder, a relative-path `raw-freeze.json`, invented numbers, a README that
opens with "FICTIONAL self-test"). Run with `--merge --move-private`: the check passed with the raw run withheld, the branch and pull request #152 were opened, all 12 required checks passed on the exact head, the pull request was merged,
and the tool confirmed on `origin/main` that every published file has the blob it had committed. Checked afterwards by hand: the files and a relative-path `PUBLISHED_FILES.json` were on `main`; the raw run
was in `private/raw/export-flow-selftest/run` with a manifest whose hashes all matched and which holds no absolute path; the task's folder in the laboratory kept only the pointer file `run.MOVED.json`; the export record
held `pr`, `protected_check`, `private_location`, `merged` and `confirmed_on_main`; the daily report showed the task as *on main*; the worktree and local branch were gone. A second fictional task with a token-shaped
string in a note was **held**: exit code 3, nothing pushed, the reason and the date in the record (the string appears neither in the record nor in the check file), and the report showed it as *held*. The fictional result
was removed from `data/lab/` in the pull request that closes the consolidation, so that `data/lab/` holds only real results; its trace stays in the history of pull request #152. The remote branch of a merged export is not deleted by the
tool: it is removed by the routine branch clean-up after it is checked against the live remote.

`tests/test_aamr_sync_report.py` covers the record on invented tasks and a fictional coordinator home with fake secrets: a complete record is quiet and shown in
the table; a missing, open or incomplete check; a branch nobody pushed; a hold that is fresh, stale, undated or badly dated; finished tasks without a record
(and running ones, which are ignored); targets and holds taken from the record for a closed mission; and a spy on `open` showing that the report never opens a
database or `.env` file. The same report was also run on the maintainer's existing records on 2026-11-14 (experiments NIGHT-1, NIGHT-2, K1 and the two T39 missions).
