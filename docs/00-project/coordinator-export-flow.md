# From the coordinator to GitHub: the export flow

**Status:** operating procedure, introduced 2026-11-14 with the consolidation ([map](consolidation-map.md), [rules](work-placement-and-sync-rules.md)).
It adds an *export record* to the daily synchronisation report. It changes nothing in the running coordinator and needs no migration of its
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
    "hold": "owner decides whether to publish",
    "hold_since": "2026-11-14"
  }
}
```

`targets` supplies the result path for a task the coordinator does not describe (every closed mission, an experiment whose output is not under
`data/`). `hold` and `hold_since` are optional; `branch` and `pr` are written once they exist. The task id is the coordinator's: an experiment name,
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
- It does not export for you. The coordinator keeps running research; the export is a separate, reviewable pull request.
- Work that never ran as a declared experiment or mission is visible only through the Git findings (`LOCAL_ONLY_BRANCH`, `DIRTY`, ...).

## Tested on fictional tasks

`tests/test_aamr_sync_report.py` covers the record on invented tasks and a fictional coordinator home with fake secrets: a complete record is quiet and shown in
the table; a missing, open or incomplete check; a branch nobody pushed; a hold that is fresh, stale, undated or badly dated; finished tasks without a record
(and running ones, which are ignored); targets and holds taken from the record for a closed mission; and a spy on `open` showing that the report never opens a
database or `.env` file. The same report was also run on the maintainer's existing records on 2026-11-14 (experiments NIGHT-1, NIGHT-2, K1 and the two T39 missions).
