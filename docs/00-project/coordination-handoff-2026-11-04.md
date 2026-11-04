# Coordination audit and handoff — 2026-11-04

Status: sourced status snapshot and proposed work order, not an experiment result or deployment authorization. Prepared by Codex at the owner's request to inspect the project and GitHub and preserve Claude Code's work.

## Verified baseline

- GitHub `main`: `e894de291580f50b28ecdb5968da8284f47c4338` ([commit](https://github.com/krapcys1-maker/adaptive-agent-memory-research/commit/e894de291580f50b28ecdb5968da8284f47c4338)); latest main CI succeeded ([run](https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/runs/41496624599)).
- 44 open issues, including the status issue, and one open pull request: [#90](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/90), head `c7f0321e76b87af20eec70b70d4a1f4df5816840`. Its six checks succeeded ([run](https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/runs/41495424039)); GitHub reported it mergeable. This is CI evidence, not a new independent scientific review.
- [#92](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/92) already merged the scratch-directory exclusion. Issue #17 is no longer open. The task list in [#84](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/84) predates this and the persona amendments.
- The project investigates local-first, model-agnostic memory. It has instruments and bounded findings, not a validated final memory architecture or demonstrated improvement to live writing quality.

## Work already present

Recent commit trailers explicitly credit Claude Code. The following work is present; test counts below are reported by the corresponding artifacts, not rerun in this audit.

| Work | Evidence and limit |
|---|---|
| November offline/replay experiments and corrections | PRs #52–#63: writer memory, engagement, persona, botness probes, benchmark statistics and judge controls. Read the errata, especially #56 and #61, with the original reports. |
| Memory kernel | [#64](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/64) introduced 0.1.0; [#70](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/70) introduced the separate live 0.2.0 line. 0.1.0 remains a frozen R1 instrument. |
| Retrieval comparison R1 | [#67](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/67): judge control 54/60 against 55 required; no confirmatory verdict. Exploratory rankings do not establish a universal BM25 or embedding choice. |
| LifeSim D1 | [#68](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/68): deterministic life generator, exact gold, systems and gates; reported 859 tests. X0/X1 remain unexecuted as result experiments. Development gate checks are not confirmation. |
| Documentation and literature | [#69](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/69), [#71](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/71), [#89](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/89): synthesis, public-document hygiene, README and contributor refresh. |
| Persona battery, still on a feature branch | [#90](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/90): P1/P2/P3/P7, frozen run, three explicit amendments and exploratory reruns. P4/P5/P6 are not delivered by this PR. |

### The latest persona result must not be lost

Source: [README at the audited head](https://github.com/krapcys1-maker/adaptive-agent-memory-research/blob/c7f0321e76b87af20eec70b70d4a1f4df5816840/data/lab/aam-p-persona-v0/README.md), especially “Amendment runs”.

- The original instruction to add an “honour the record” sentence has **already been tested**. Agreement when the stored line was shown was 0.76 (frozen), 0.61 (0.1.0 + sentence), 0.67 (0.2.0), and 0.70 (0.2.0 + sentence). All are below the preregistered 0.90 reading. The sentence is not shown to fix consistency.
- The 0.2.0 P1 rerun retained 10/10 event-only facts. These reruns used `min_evidence=1.0`; the default 1.4 failed one of fourteen retrieval controls. This is a study-specific setting, not a recommendation to change defaults everywhere.
- The runner now loads the kernel explicitly. Preserve the frozen run at `35eddb64604a2da34324a9dc8d412974e01d0bfc`, its recorded digests, and the separation of amended runs. Do not “repair” history by replacing the original results.
- The PR description still describes the original run and says the results change nothing frozen. The current README explains subsequent amendments, including a changed runner digest. Update the description to describe the final branch before merging; do not erase the amendment history.
- A deterministic consistency check or promotion of stored details into hard facts are **untested alternatives**, not established remedies.

## Separate collaborator: the NIE integration agent

The owner clarified that a second agent, NIE, has been implementing the persona. Its work is a separate repository and must not be treated as an unstarted task in this research repository.

- Repository: [nothing-is-accidental-agent](https://github.com/krapcys1-maker/nothing-is-accidental-agent). GitHub `main` was `4b2fdb8`; branch `persona-v0` was `5cb731e65844cc6e9c3f8bcdc0a8220a1a6eb2dd`. There were no open PRs there. The local checkout had the latter head under a different branch name; never assume identical branch names identify the same work across local and remote inventories.
- [Commit 802148b](https://github.com/krapcys1-maker/nothing-is-accidental-agent/commit/802148ba32c3ca7eefe89c35ba9c147196a26290) already adds the persona module, canonical card, seeds, life-note prompt, bio gate, input/output filters, publication hooks and tests. `5cb731e` adds generated documentation. These are two commits beyond that repository's main.
- [The implementation note](https://github.com/krapcys1-maker/nothing-is-accidental-agent/blob/5cb731e65844cc6e9c3f8bcdc0a8220a1a6eb2dd/agent-v2/docs/ZMIANY_2026-11-02_PERSONA.md) reports 54 checks and 29 killed mutants. Its filter scores used the tuning items, so they are not a held-out evaluation. A separate private evaluation also already exists; Codex reproduced its deterministic totals during this audit. Its provenance, hashes and aggregate findings are in the local handoff, without publishing its inputs. Reconcile this result before commissioning another identical evaluation.
- The inspected local configuration has `PERSONA=False`, `PERSONA_ZYCIE=False`, and no enabled persona prompts. The implementation note leaves kernel 0.2.0 integration and expansion beyond life notes for later stages. Server deployment/live state was **not inspected**; local flags do not establish server state.
- The implementation still uses the honour-the-record sentence. Send its owner the later negative result in research PR #90; do not remove or alter their prompt from this workspace. Their input-filter evaluation and the research reference-output-filter experiment are separate tasks.

Suggested boundary: Claude on the research track owns experiments and their provenance; NIE owns its canonical persona, prompts, filters, integration and deployment; Codex owns the audit/handoff and any subsequently selected isolated engineering or documentation task. No assignment is considered accepted merely because this plan proposes it.

## Documentation lag that can misdirect the next session

At the audited baseline:

1. `memory/events.jsonl` contains 323 events; the latest is dated 2026-08-25. `memory/CURRENT_STATE.md` was last changed on 2026-08-23. Neither provides the November handoff by itself.
2. `data/lab/experiment-registry.csv` has 74 rows, was last changed on 2026-08-23, and has no `AAM-` or `WMB-` experiment IDs. The experiment READMEs are currently necessary to reconstruct November work.
3. [The benchmark specification](../11-research-laboratory/memory-benchmark-spec-v0.md) still describes R1 as under review, D1 as started and kernel 0.1.0 as the current module. Preserve its design and adoption rules, but update its status statements from later evidence.
4. The local integration board and persona report still offer the P2 sentence and kernel 0.2.0 reruns as next actions. Those reruns are already in #90. The integration team's later decisions must be read alongside that older report.

This handoff adds a sourced memory event on its own branch. It does not rewrite the older events, the state file or the registry, and it does not close [#79](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/79).

## Proposed work order

These are proposed responsibility boundaries, not claims that another session has accepted an assignment.

| Priority | Work and suggested owner | Completion evidence / dependency |
|---|---|---|
| 1 | Claude / integration owner: finish #90 review and update its description; reconcile the post-run findings with the integration board | Review the exact final head and latest main; retain original failures and amendments. Merge only through the normal integration workflow. No additional paid run just to repeat the same sentence. |
| 1 | Codex: #79 and the November continuity repair | A tested lab map, corrected status summaries, registry rows derived from actual artifacts, append-only memory updates. Check links and claims; keep results and hypotheses distinct. Coordinate ownership of shared summary files. |
| 2 | NIE integration owner + research evaluator: reconcile the existing filter evaluation and current integration | The filter, dark-launch code and a separate local evaluation already exist. Read the local handoff, inspect the misses, version any repair, and reserve genuinely unseen probes for its evaluation. Record actual deployment state. The reference output filter in #90 is a different component. This audit did not inspect production. |
| 2 | One LifeSim owner: [#80](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/80), then [#81](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/81); [#82](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/82) supports portability | Repair G-TELL/G-POS and G-BLIND/G-FEAS on development seeds; check G-DEPTH at adequate sample size. Preserve thresholds and explain amendments. Then freeze a candidate and follow the registered one-use confirmation procedure; only then X1. |
| 3 | Codex, in a separate change: [#73](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/73) | Reproducible mutation runner operating on temporary copies of both kernel lines, additional tests in separate files, explained equivalent survivors. Neither kernel needs to be edited for this task. |
| 3 | Retrieval evaluation owner: [#72](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/72), then [#78](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/78) as capacity allows | Public-corpus ranking/gate evidence first; R1b needs a repaired judge protocol, fresh controls and sufficient new notes. #78 is design only. Respect the two-unexecuted-designs-per-track limit. |
| 4 | Persona research owner: P4/P5/P6; WMB owner: T1 onward | Stability without events, bounded/selective/persistent change, pressure versus evidence; memory-dependent question bank and sealed split, then arms/adapters and writing opportunities. These are not implied by P1 success. |
| Later | Literature/public benchmarks and older research backlog | #75–#77, #83; #1–#15, #19, #24, #27, #31, #37–#42, #46–#51. Pick a concrete dependency rather than starting all tracks. #74 is a public reference-guard dataset, distinct from the production input filter. |

LifeSim's four failing gates on twenty development worlds are reported in #80/#81. The “11 of 16 pass” headline in #68 used four worlds, where G-DEPTH also failed. Keep the sample sizes attached to these statements.

## Working together without overwriting work

1. **One task, branch and worktree per writer.** Inspect `git status`, HEAD and worktree inventory before editing. Existing dirty files belong to their current author until explicitly transferred. Do not switch, reset, stash, clean, rebase or remove another session's worktree.
2. **Reserve file sets before overlapping work.** Record owner/session, issue, branch, base SHA, files, status and handoff link in the local coordination log. Check the issue's latest discussion too. No ownership was inferred from an empty assignee list.
3. **Freeze boundaries are explicit.** `scripts/wmb/memory_kernel.py` is 0.1.0 and frozen; `scripts/wmb/kernel/memory_kernel.py` is 0.2.0. Read each study's manifest before editing any dependency. Post-freeze changes require a separately recorded amendment/version, not a rewritten original.
4. **Shared files have a single editor at a time.** Re-read immediately before a narrow patch or append. Never replace a shared plan from an old copy. Keep earlier log entries. Use the project-memory API/CLI for events, and preserve both append-only tails if branches diverge; never resolve a log conflict with whole-file “ours/theirs”.
5. **Isolation is incomplete.** Worktrees share Git refs/config, but have separate working files and memory logs. Runtime caches can be rebuilt; private model proxies, budgets and integration services must not be restarted by an unrelated task. Record which checkout the memory CLI is using.
6. **Evidence follows the final head.** Review and run the checks relevant to the final diff. Before integration refresh main and rerun checks if the base or code changed. A green run on an earlier SHA is not a check of later changes.
7. **Leave a complete handoff.** Exact SHA, changed files, commands and results, unresolved defects, no-rerun list, next action, and whether anything was pushed/merged/deployed. Publishing and deployment are separate from preparing a local artifact.
8. **Keep private inputs outside the public repository.** Public handoffs carry aggregates, repository-relative paths and public links. Never copy local machine paths, persona text, raw replies, credentials or private ledgers into public documentation.

## Scope of this Codex session

- Read project instructions, selected source documents and results, local Git history/worktree state, and current GitHub issues, PR metadata, changed-file list and CI.
- Prepared this handoff and a sourced memory append on `codex/audit-handoff-2026-11-04`, based on `e894de2`; local coordination notes live outside the repository.
- No application, experiment, test, kernel or workflow code was edited. No new experiment or model call was run; the existing frozen filter's saved totals were recounted locally without changing its files. No branch was pushed, no PR or issue was changed, and no deployment was performed.
- Local `python scripts/verify_memory_integrity.py`: 325 events, zero violations after the two sourced appends; the previous 323 events are preserved byte for byte.
- Local `python scripts/audit_repository_claims.py --format json`: exit 0, zero critical findings, 13 low and 45 medium findings. This is not a claim that the older documentation/registry debt is gone.
- Full application/experiment tests were not rerun for this documentation-only change; the exact GitHub CI runs above were inspected. File-preservation verification is recorded in the local handoff.
