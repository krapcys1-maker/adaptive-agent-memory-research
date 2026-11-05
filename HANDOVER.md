# Safe handover — 2026-11-04

Read [AUDIT_REPORT.md](AUDIT_REPORT.md) first. **The repository and prior work are preserved; the new memory candidate is not ready for general use.** This is a local uncommitted audit delivery on top of `cb6d72dc1610d8c9308f2cb5a73f2e452803fa1f`, not an independent Claude approval or a merged feature release.

## Where to resume

- Owned worktree: `GH_REVIVAL/codex-structured-memory-runtime-2026-11-04`, branch `codex/structured-memory-runtime-2026-11-04`.
- Main/base `1b673d3`; draft [PR105](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/105) published at `a58cd87`. Local `cb6d72d` adds the final raw-output freeze. At audit entry, v5 dev/valid score files were untracked; the safety snapshot includes them. Audit files and subsequent continuity updates are also local. No audit commit/push/merge was made.
- Private raw artifacts/requests/final outputs/failed attempts: sibling `GH_REVIVAL/structured-memory-2026-11-04`. Audit receipts/logs: `GH_REVIVAL/integrity-audit-2026-11-04`. These paths are relative to the local workspace, not repository contents. Do not upload private raw logs or the backup.
- Verified private recovery snapshot: `D:\Pamiec LLM - audit backups\2026-11-04\20261104T181004Z`; read `VERIFIED_RESTORE.json`, `manifest.json`, `workspace-root-files.json` and the private marker. All CAS bytes and both Git ref graphs verified; active filesystem/index/status actually restored. Other worktree inventories were saved but not all rehydrated. Credentials/caches/weights and `NIE_DANE` are excluded. Earlier `20261104T180224Z` is incomplete.
- Full work history through PR104: [delivery audit](docs/00-project/project-delivery-audit-2026-11-04.md), [coordination handoff](docs/00-project/coordination-handoff-2026-11-04.md), [laboratory map](docs/11-research-laboratory/lab-map.md), dated root Polish journals. Current audit supersedes their status snapshots where explicitly stated; it does not rewrite their experiments.

## Completed during the session

PR90's Claude persona implementation was reviewed and merged alongside versioned PR93 integrity corrections. PR94–104 delivered mutation checks, CLI verification, LifeSim platform checks and development diagnosis, laboratory navigation, retrieval costs/ranking, an offline journal bridge, typed-fact local reading, matched Flash/local pilots, and a full failed hard benchmark with an evidence audit. See the audit chronology for exact commits and limits. Original frozen kernels, original persona runner, prior results and integration code remain retained.

PR105 supplies a runnable candidate with these separate layers:

1. `tools/structured_memory_v1.py` and `structured_memory_v2.py`: hashed append-only raw sources/extractions; literal claims; separate recorded/effective time; conservative conflicts or explicitly declared ordered-single state; bounded graph execution with source paths. V2 refines cache informativeness/specificity; it inherits the confirmed conditional/coordination bug.
2. `tools/structured_memory_cli_v1.py`: offline source/extract/resolve/query/status. Caller supplies scope, clock and proposals; it is not automatic agent integration.
3. `tools/retrieval_metadata_v1.py`, `retrieval_metadata_v2.py`, `evidence_memory_v1.py`: retrieval addresses/kinds are separate from asserted truth; exact source spelling, revision IDs and caller-provided roles/provenance are preserved. `attach` and `recall` are persistent CLI/library entry points.
4. `tools/evidence_candidates_v1.py`: bounded source-first candidates including sources rejected by metadata extraction. Generic entity pools and lexical/recency ranking, not service-name templates.
5. Versioned benchmark controllers and integrity replay scripts: structured pipeline v1–v5 and H1 v1–v5. Their hooks/identity composition are research instrumentation. See [runtime contracts](docs/04-systems/source-grounded-runtime-v1.md).

## Results that must not be broadened

| Test | Recorded observation | Limit |
| --- | --- | --- |
| MAB spent FC-MH262k100 | Free paths local 25/100, Flash 19/100; executable options local 55/100, Flash 59/100 normalized exact | Same 100 development questions, self-set target 80 unmet; no matched vendor ranking. Flash secondary SubEM60 is not a replacement metric. |
| Capture | 18,333 raw sources, 18,328 accepted claims, four quarantines and one header; 110 extractor calls plus 18,223 cached sources | Span acceptance is not semantic truth. Three failed/capped capture attempts remain preserved. |
| H1 v1 | OBSOLETE leaks stay dev12/12, valid9/12 | Negative fact-chain transfer result; never erase it. |
| H1 v3/v4 | Metadata alone leaves most leakage; automatic routing reaches dev69/84 and valid70/84 `answered`, leaks7/12 and2/12 | Public development evidence, automatic routing adds inference; unchanged old bounds use a different reader. |
| H1 v5 | Dev base62 →76/84, OBS leaks12→0/12; valid base66→71/84, OBS leaks9→1/12. Supporting source found84/84 in both treatments | Flash reranking adds candidate context/cost; not a pure-chain/equal-total-input result. Valid has11 gains and6 losses; stale caseQ000043 remains. |

H1 `answered` means the original required-fragment scorer passed without abstention; `leaked` is separate forbidden-marker matching. Neither is independent semantic adjudication. Full per-family records are in each score JSON. The same implementing agent re-ran computation from frozen files and got identical v5 scores with zero replay failures; this is **not** independently authored semantic review.

PR105 actual generation attempts: **3,634 = 3,171 local +463 paid Flash**. H1 local ledger `h1-local-ledger.jsonl` contains2,677 unique keys; preceding MAB local count494. Paid `api-ledger.jsonl` has463 reservations/$1.852, usage upper estimate$0.073913, zero unsettled calls. Final explicit caps500 paid/$2 and2,800 H1 local; older plans/ledger snapshots retain their earlier limits. Never reset a ledger, hide failures or count inherited baseline outputs as new calls. Model calls are not independent test cases. No model call was made during the integrity audit.

Local model is the installed `qwen2.5:14b-instruct`, Q4_K_M, digest `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6`. API permission is **DeepSeek V4.1 Flash only**, never Pro or provider/model fallback. Models exercise memory extraction/routing/reading; Codex handles project decisions, code and result assessment. No project-planning/model-judge requests are authorized by this handover.

## Confirmed blockers and order

1. **A01/A02 HIGH:** cache asserts conditional/compound spans; historical routing exposes future learned sentence shells. Reproduce using `python scripts/reviews/audit_structured_runtime_boundaries_2026_11_04.py`. The command's `observed:true` is a reproduced failure, not a passing capability check. Fix in successors; do not edit frozen v1/v2/v5 sources in place.
2. **A03 MEDIUM:** global predicate validation discloses private-scope existence through response status. **A04:** whole-source supersession removes unrelated properties if a partial correction supersedes a multi-property source; this is current granularity, not deletion of raw evidence. Agree the new contract before implementing it.
3. **A06 HIGH:** H1 validationQ000043 contains the later authoritative correction in the shown pack, yet the local reader emits the old value. Do not rerun just that question until green. Preregister a general conflict/packing intervention or bounded oracle control; measure retrieval, shown evidence and answer separately. Optional oracle controls registered earlier were **not executed**.
4. Verify a successor in an isolated pinned environment, obtain missing macOS/exact-head CI, then conduct independent review and fresh/sealed evaluation. No generic product, learned future utility, consolidation/forgetting loop, longitudinal NIE benefit or vendor superiority has been established.
5. Finish live documentation/registry/source navigation without rewriting historical declarations. The old registry omits November experiments; the lab map and result READMEs remain necessary. Claim gate currently reports45medium/22low despite exit0.

## Verification already performed

- Last full local suite:3041passed/20skipped/two existing warnings,377.99s; not redundantly repeated during an audit with unchanged tested runtime. All474tracked Python sources parsed. Counterexamples and both full v5 replay/rescore phases executed without inference.
- `git fsck --full`: actual research/NIE repositories and restored bundles exit0; dangling objects retained. No unresolved worktree operation/conflict found.
- Memory at audit entry:356events/333active/23superseded/zero violations. Read the later audit memory event as an appended update, not a changed old result.
- Published-head [CI](https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/runs/41881224236):10success, two macOS jobs cancelled for hosted-runner capacity; aggregate failure. Unpublished final raw freeze has no remote CI receipt. Never state12/12green for this head.
- Global `pip check`: nine conflicts; pytest9.1.1 installed versus pinned8.4.2. Other five direct pins match. Clean Linux CI used requirements successfully. Do not upgrade/downgrade shared packages to fix the audit.
- Heuristic all-ref/reflog research blob scan reviewed eight sentinel hits; no provider credential identified. It is not exhaustive security/license certification. All private backup/raw artifacts remain local.

## Boundaries for Claude and other agents

Keep the original dirty checkout `adaptive-agent-memory-research` and original Claude `GH_REVIVAL/docs-worktree` unchanged. The separate NIE repository is `C:\Users\user\Desktop\agent project`, branch `nie-jak-nia-wip`, head `5cb731e`; its code/personality/prompts/filters/deployment are not owned by this research task. Repeated checks matched the original 14worktrees/32,035files, NIE status/diff, shared plan and20frozen paths. `WSPOLNY_PLAN.md` is unchanged; coordination-board additions are append-only and do not imply another agent's ACK.

Before substantial work run project-memory `status` then task-specific `context` (CLI fallback documented in AGENTS), inspect current Git state, read freezes and create a new owned branch/worktree if needed. Preserve raw failures, versioned protocols, clocks/scopes/roles and exact denominators. Record durable sourced findings with `memory_add`; use supersession rather than editing old events.

The owner authorized autonomous work, but the latest task explicitly says **audit first, no refactoring/features and no automatic commit/push of potentially broken work**. That audit has now produced evidence and handover; it did not repair the candidate or merge PR105. A genuinely independent Claude/human review is recommended before promotion, and has not happened. Continue from the concrete blockers above instead of commissioning another identical narrow success test or rebuilding the existing persona from scratch.
