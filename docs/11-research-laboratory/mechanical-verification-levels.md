# Mechanical verification levels (specification, proposal)

**Status:** specification of a checker that exists in the maintainer's local coordinator (`aamr_coord/lab/verify.py`, coordinator
branch `lab/hypothesis-ledger`, blob `93fdd9a05e2b`; design text in the coordinator's `docs/RESEARCH_LAB.md` section 5). The checker
itself is **not** published here: it is tied to the coordinator's run-folder layout and state module. What is published is the
specification, so that its reports can be read and reimplemented, and its limits are stated. No result, frozen file or verdict is
changed by this document. It complements the [independence ladder](../00-project/independence-ladder.md) (I0 to I5, who checked
a result) and the [hypothesis-ledger methodology](hypothesis-ledger-methodology.md): the levels below say *what a machine
re-derived from the raw data of one experiment*, not whether anyone independent believes it.

**Principle.** Green code tests and a program that ran to the end are not evidence that a mechanism works. The levels are
deliberately kept apart so that a pass on one cannot be read as a pass on another. The checker never decides a hypothesis.

## Inputs

For one experiment the checker needs: a **run folder** (the program's output: `DONE.json`, optional `errors.log`, `restarts.json`,
`state.json`, `heartbeat.json`, `sessions/*.jsonl`, `artifacts/*.json`), an **output folder** (`raw-freeze.json`, `results.json`) and
the experiment's registration (SHA-256 of protocol, specification and configuration at registration, model names, the baseline arm,
which sessions are test sessions). Session files are JSON lines with `task`, `arm`, `model` and `evaluation.solved`. A check whose
input is missing reports `unchecked`, never `pass`.

## The nine levels

Statuses: `pass`, `warn`, `fail`, `unchecked` (input missing), and for the last three levels `computed`, `none` / `is_replication`,
`undecided`. A `fail` on a level marked "blocking" below is listed in `blocking`.

| Level | What it re-derives | `pass` | `warn` | `fail` (blocking) |
|---|---|---|---|---|
| `execution` | that the program finished its stages | `DONE.json` present, every stage `done` | a stage `partial` or `skipped`, or lines in `errors.log` | no `DONE.json`, or a stage in another state |
| `integrity` | that the frozen raw files are the ones that were hashed | every file of `raw-freeze.json` exists and has the recorded SHA-256; no raw file outside the manifest; none modified after the freeze time | files in the run folder that the manifest does not list (volatile files such as heartbeat and logs are ignored), or files modified after the freeze | a listed file is missing or its SHA-256 differs; no manifest |
| `provenance` | that protocol, specification and configuration are the registered ones | each file's current SHA-256 equals the one registered, one `config_id` throughout, the preflight confirmed the model digest | digest of the model not confirmed | a hash differs from registration, or more than one `config_id` |
| `statistics` | that the tables in `results.json` follow from the raw sessions | task and solved counts recomputed per session and arm agree with the report | n/a | any difference |
| `leakage` | that no memory source is a test task | the memory artefacts' `source_turns` and the test sessions' tasks are disjoint | n/a | any overlap |
| `comparability` | that arms are comparable | the same task set in every arm of a session, one model per session | different task sets or several models in a session | n/a (not blocking) |
| `mechanism` | the effect of each arm against the baseline arm | `computed`: pairs, gains, losses, delta, exact two-sided McNemar p | n/a | n/a |
| `replication` | only a status | `none`, or `is_replication` with the id it replicates | n/a | n/a |
| `hypothesis` | nothing | always `undecided`: the owner decides after an independent review | n/a | n/a |

`mechanism` is **mechanical evidence in development data, not confirmation of a hypothesis**: it is a paired comparison on the
same tasks and says nothing about generalisation. `replication` needs a separate experiment (another executor, model or data).
`leakage` checks exact identity of source and task identifiers only; it does not detect paraphrased or near-duplicate leakage.

## Reading a report

A report is `{experiment, at, levels, blocking, summary}`. `summary` maps each level to its status. An experiment is
**mechanically clean** when `blocking` is empty and no level the experiment depends on is `unchecked`. That sentence is the whole
claim: it says the numbers can be recomputed from the frozen raw files and that the configuration is the registered one.

## Known limits of the specification and of its implementation

- **The McNemar test of `mechanism` is two-sided.** Many registered decision rules use a one-sided test or a threshold; the report's
  p-value is therefore not the rule's p-value. Do not compare them.
- **`statistics` recomputes counts of solved tasks only.** It does not re-run the scorer, so a scorer defect is invisible to it.
- **`integrity` trusts the freeze manifest.** A manifest written after the results were seen would pass; the freeze time check
  only catches files modified after the recorded time, with one second of tolerance.
- **`provenance` is only as strong as the registration.** If protocol or configuration were registered after the fact, the level is
  decorative; whether registration preceded the first model call is a separate question (compare the commit order).
- **A session format is assumed.** Other experiment layouts report `unchecked` until an adapter exists.
- **The checker is code in one repository's coordinator.** Its own correctness is tested there (the coordinator's suite); this
  repository has not run it. Any claim of "all levels passed" in a report of this repository is the coordinator's output unless a
  reproduction command is given next to it.

## Using it

An experiment's `README.md` should state which levels were checked, by what, and with which result, in the same words as the table
above, and say `unchecked` where it is so. Reports that quote "mechanical levels: pass" without naming the levels overstate. A level
status can be reimplemented from this table; the status vocabulary is stable.

## Provenance

Written on 2026-11-14 from the coordinator's `aamr_coord/lab/verify.py` (read-only) and its `docs/RESEARCH_LAB.md` section 5. The
code was read, not run, for this document; the table was checked against the code paths for each level. The Polish source text is not
reproduced.
