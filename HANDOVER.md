# Safe handover — 2026-11-04

## Current local upgrade: raw frozen, authored scoring next (2026-11-05)

All655calls each for Qwen14B and Qwen3.5 9B completed at sourcea71765f; complete native replay0failures. Gemma4 12B fixed Q4 package installed (digest6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b), but its V2phase stopped at251/655 on a foreign TCP client PID36812. Process had exited before identification; TCP alone does not establish inference. Preserve this safety abort, do not force ownership, resume, retry or score missing BEAM cases. [Raw receipt](data/lab/local-model-upgrade-v2/raw-freezes.json) replays every1564attempt including3failedV1controls and251partialGemma; [partial record](data/lab/local-model-upgrade-v2/gemma-incomplete.json) gives limits. Primary comparison is two complete models; no semantic labels joined yet. No model promotion/cleanup is complete.

Sourcea71765f CI12/12success,3577passed/21skipped per Linux3.11/3.12,run42013069495; post-generation auditor adds9focused checks (63total). Later source/result heads need their own CI. Task1564/2000,0API; PR105now6388=5925local+463historicalFlash. H1/API/oldBEAMledgers unchanged. NativePS memory undercounts Gemma versus driver/weight sizes; do not claim1.45GB true footprint. RSS sampling excludes separately named llama-server worker. Read generation-completion.json for desktop/timing caveats. Next: commit this raw/auditor freeze before opening original BEAM references; authored scoring, conservative cleanup, continuity/GH and verified recovery. No NIE/persona/shared-plan/original-dirty-file/frozen-runtime change.


## Active local upgrade amendment v2 (2026-11-05)

V1source9ad192d stopped after3controls and0primary calls because its exact control predicate rejected the valid refusal `I do not know.` with a terminal period. Failure/raw hashes committed atbbe7481; V1 stays failed and is not rewritten. [V2protocol](data/lab/local-model-upgrade-v2/PLAN.md) accepts exactly expected control text or that text plus one period, only for unrelated transport controls. Primary packet SHA d6fd978d6ac2cfe8a9c48054828698fbb34083e3958aaee91361cc56dd530faf is identical; no benchmark/gold/quality/decoding change.54focused checks pass. New private outputs are under the existing task root's `v2` subdirectory; shared root ledger/worker lock retain all3failed attempts, namespaced new keys, ceiling2000 (1968if3models complete). Do not start competing Ollama work. All other ownership/history safeguards from the dated registration below continue. Full raw commit must precede scoring; results/cleanup remain pending.


## Active continuation: controlled local-model upgrade (2026-11-05)

Owner's new attached task explicitly authorizes a read-only audit, official fixed-quant local candidate installation, paired memory-off/on benchmarks and conservative cleanup. [Protocol](data/lab/local-model-upgrade-v1/PLAN.md) and [audit](data/lab/local-model-upgrade-v1/audit.json): old worktrees and seventeen dirty files preserved; historical Qwen14B judge/default unchanged; protected strict alias verified identical 7B weights. Qwen3.5 9B Q4_K_M installed with full digest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90. No existing model removed or global configuration changed.

New isolated task prepares all84H1valid and200BEAM N/M pairs at8192context, plus all84H1 M repeats and3controls per model (655/model; new cap2000; zero paid). Existing H13262/3300, BEAM605/650, paid463 and PR1054824 are historical prefixes, not reset. Do not run a competing Ollama task, alter prepared inputs or old evaluators/ledgers, switch defaults, touch NIE/persona, or infer semantic improvement from engineering tests. The raw task directory is private at `D:\Pamiec LLM\GH_REVIVAL\local-llm-upgrade-2026-11-05`; its worker lock/reservation ledger identifies ownership. Full raw freeze must be committed before any new label join. Results, optional promotion, cleanup and verified delivery remain pending at this dated source registration; later continuation supersedes this pending status without erasing it. New models are subjects only, never judges/planners.23focused boundary/forgery checks pass; whole-suite preflight is still running and is reported separately when complete.


## Delivery confirmation: evidence-boundary diagnosis (2026-11-05)

Result/source281b7c2 passed all12CI jobs; full Linux Python3.11/3.12 each **3521passed/21skipped**, run42004606394. The later delivery/documentation head has separate CI.

The [delivery receipt](data/lab/beam-evidence-boundary-v2/delivery.json) records the exact tested result head281b7c2 and actual clean private restore (164files/78refs/fsck0), chained to beam-reader-delivery-final. GitHub#110/#51/#7/#84 and draftPR105 readbacks verified; general#110remains open. This later receipt/doc commit has separate CI. New engineering interface remains experimental; old N19/B39/Cdel32and all counters remain unchanged. Root Claude/Polish handoffs plus append-onlyC-016 identify this continuation. Private backup path: `D:\Pamiec LLM - audit backups\2026-11-05\beam-context-delivery`; a later beam-context-delivery-final supplement uses its own VERIFIED.json/head.

Post-hoc role composition:2403/3200candidate windows are assistant-origin, whereas1244/1325numeric target references are user-origin. These count different populations, not a causal effect or a user-only policy endorsement; both window and distinct-case/source counts are in the result supplement. Next evaluate source/instruction selection under a separate frozen protocol, preserving scope/role/uncertainty and the current negative controls. No reader rerun, API spend or integration remains pending for this completed phase. Memory373/0violations; registry85historical entries.


## Current continuation: source-context repair and full evidence diagnosis (2026-11-05)

[Complete model-free result](data/lab/beam-evidence-boundary-v2/README.md): all200cases,176with reference annotations/24without.1326declared slots include1325numeric IDs and1unresolved `--` marker; all numeric IDs map to the original archive.1216outside16candidates,34retrieved-but-budget-omitted,5shown-partial,70shown-full. All target sources shown in16/176cases,28/176at candidate stage. This is a source-ID coverage proxy, **not semantic sufficiency or a model/answer ceiling**. Old Bhas11authored passes even with no annotated source shown; annotations are not exhaustive evidence truth.

New frozen `tools/source_context_v1.py` retains complete first paragraph/active ATXheading ancestry as literal source-span dependencies under the same complete-message budget. Known example heading7-Q0000is structurally preserved; no new reader verifies semantic benefit.705old windows become390; all-target coverage16to15,197packets lose windows. Semantic status remains unresolved. Ordinary distant prose/intent/negation scope still fails in a retained negative fixture. Accept this inspectable engineering interface only; **keep packet experimental, no adoption or general#110closure**.

V1code5b70e0e failed on the explicit `--` marker in6-Q0004; started/failure receipt and code retained. V2amend50e12e4 frozen before full pass preserves that unresolved slot/valid siblings without guessed ID or denominator deletion. Runtime8.266seconds/1548160bytes; authored replay8.282seconds,200packets/1326slots/187734message mapping,zero failures. Three forged private copies rejected even after rebound hashes.117focused checks pass (71new/46existing). New head needs own CI; previous deliverye8c2523 has12successful jobs/3447passed21skipped per Linux3.11/3.12.

0newmodel/APIcalls; all H1/API/BEAMledgers/input/snapshot hashes unchanged. PR105cumulative4824=4361local+463Flash;H13262/3300,BEAM605/650,paid reservations$1.852/recorded upper$0.073913unchanged. Registry85historical rows preserves original84byte prefix; executed successor fulfils original pending registration. No NIE/persona/deployment/shared-plan/original-worktree/frozen predecessor edit.

Private new evidence: `D:\Pamiec LLM\GH_REVIVAL\beam-evidence-boundary-2026-11-05`, failed diagnostic-v1 and completed diagnostic-v2 kept. Full sources stay in prior immutable archives. Before this stage, final deliverye8c2523actually restored clean (121files/78refs/fsck0), chained to result50158dd. Later delivery receipts must identify their own heads. Next admissible work is label-free source/instruction/preference retrieval and sufficient-evidence measurement before a separately frozen reader protocol; do not spend spare ledger allowance on hidden retries. Latest result does not change old N19/B39/Cdel32or faulty reference annotations.


## Delivery confirmation for the completed BEAM study (2026-11-05)

Result/source commit50158ddb40e02e43ca9de8d929fe101ec6414052 passed all12CI jobs: **3447passed/21skipped on each Linux Python3.11/3.12**, run41996840238. The [delivery receipt](data/lab/beam-reader-evidence-v1/delivery.json) binds those exact results, GitHub readbacks and the verified private restoration. This later receipt/documentation commit has separate CI; never infer its status from an older head.

GitHub#51/#7/#84 and draftPR105 contain the complete rejected result and limits. New [#110](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/110) has a synthetic hypothetical-frame counterexample and falsifiable acceptance criteria; #109engineering is completed. No independent reviewer or another agent's ACK is implied.

Private recovery `D:\Pamiec LLM - audit backups\2026-11-05\beam-reader-delivery` actually restores50158dd,78refs,220copied files,fsck0 and a clean tree,0source writes. It chains to the verified beam-format delivery for original sources/labels. A small later `beam-reader-delivery-final` supplement may cover the later delivery head: use its own VERIFIED.json/head, not an assumption. Root CLAUDE.md and Polish handoff are updated; WSPOLPRACA_NIE has append-onlyC-015. Original shared plan/NIE/persona/frozen code remain unchanged. Memory371events/0violations; registry83historical rows. No remaining model call or semantic scoring task is pending for this phase; next research is#110/evidence completeness, with BEAM now development.

## Current continuation: full BEAM reader comparison completed and rejected (2026-11-05)

[Complete result](data/lab/beam-reader-evidence-v1/README.md): all200probes/10histories/10abilities,605actual local calls,0API, five controls passed. Code439f9c7/matrixb8e3f83 before inference; complete raw64f7f0b before first reference join. Zero native replay failures across605requests/responses/200matched B/C evidence pairs; all600primary outputs valid JSON and normal stops. Model digest unchanged, owned worker unloaded. Do not rerun/overwrite this phase or spend the spare task allowance on retries.

Codex authored all382within-question distinct answer verdicts, with arm names masked but design known and some common/full sources inspected. **Not independent, fully blind or official BEAM accuracy.** Conservative full-rubric counts N19/B39/Craw31/Cdelivered32 out of200; allNpasses are abstention. Non-abstention N0/B29/Cdel14 of180. Eight reference cases remain uncertain (3defective/5ambiguous), with full-denominator bounds in score.json. B→Cdel8gains/15losses; material contradictions39→14 but one newly assessed case; two correct rawCanswers lost to quote guard. C/Bmedian latency1.1474. Prespecified quality/no-new-contradiction gates fail: **reject adoption**. No graph-transfer/current-company/general-memory claim. Subsequent BEAM tuning is development.

Important failure: a suffix can retain role/hash/offsets yet omit a hypothetical-example heading. BEAM10M-7-M007239 demonstrates a hypothetical quote being treated as actual advice. New synthetic test reproduces literal acceptance; passing it means the defect exists, not a repair. Source-frame/modality preservation and evidence completeness are the next engineering boundary. General efficient semantic capture and a matched competitor remain open. Source-window engineering#109 is completed; semantic capture#106 remains unresolved.

Source preparation74.812seconds/2,616,798,059bytes plus reader1176.156seconds/5,918,045rawarchivebytes. Native605prompt/generated counts613469/18390. New BEAMledger605/650; oldH13262/3300 and463paid attempts unchanged. PR105cumulative4824=4361local+463Flash; reservations$1.852/usage upper estimate$0.073913 unchanged.57focused tests pass including the reproduced qualifier defect. Execution headb8e3f83 CI12/12success with3434passed/21skipped on both Linux3.11/3.12; later evaluator/result/docs need their own CI. Registry83historical rows, previous82byte prefix retained; E1-002 fulfils E1-001's pending registration. No NIE/persona/deployment/shared-plan/original-worktree edit. Read operations guide for immutable stage boundaries.

Private reader and authored-review archives are under `D:\Pamiec LLM\GH_REVIVAL\beam-window-2026-11-05`; original source/labels remain in the earlier external-transfer archive. Raw inputs/requests/answers/review reasons/backups stay private. GitHub/verified recovery delivery receipts are subsequent to the result commit; verify them rather than borrowing an older green or restoration claim.

## Current continuation: complete source windows; full reader comparison next (2026-11-05)

[Source-window result](data/lab/beam-source-windows-v1/README.md): frozen code53fe7d5 processed187,734sources into405,070traceable windows and400packets. Full offline reconstruction has zero failures. Preparation74.812seconds/2,616,798,059outputbytes; indexes contain only the visible scope/cutoff.33window tests and13new reader-contract checks pass. This is engineering readiness, not answer quality. All200retrieval packets omit candidates;187show partial sources.

[Reader protocol](data/lab/beam-reader-evidence-v1/PLAN.md) is registered before inference: all200probes, N no memory/B raw lexical/C identical evidence plus literal-citation contract. New read-time candidate, **not the earlier55/59graph mechanism**.605planned local calls including5controls; new BEAM cumulative ledger cap650, not a reset of H13262/3300 or prior463paid attempts. Existing local3756/total4219 remain the base. No new API/judge/planner or NIE/persona change. If complete, local4361/total4824. Freeze code/config and prepared packets before calls; freeze all raw outputs before joining references. Codex authored rubric assessment must remain separate from literal quote validity and official BEAM accuracy. Never silently retry a failed control or incomplete phase. Registry82rows, with original80rows preserved; reader result pending.

Private access outputs: `D:\Pamiec LLM\GH_REVIVAL\beam-window-2026-11-05\access-v1`; planned reader outputs `reader-evidence-v1` and new task ledger `beam-local-ledger-v1.jsonl` under the same parent. Full source/labels remain in the earlier external-transfer private archive. Preserve all historical versions and failed attempts.

## Current continuation: external BEAM data boundary completed (2026-11-05)

[BEAM format result](data/lab/beam-transfer-format-v2/README.md) is the latest stage under#51/#7. Prepared the complete pinned repository10M-tier source selection:10conversations,187,734messages,200probes across10abilities.20Git-blob/size-verified JSON files total471,872,306bytes. Upstream prefers `chat_trunecated.json`; no pickle/external code/default model client executed. Raw text/questions/annotations stay private. Reader question keys are only opaqueID/conversationID/question; construction metadata and all evaluator annotations are separate.

Frozen v1codefc5429b succeeded on the original one-conversation cache, then rejected full data on an explicit null time anchor in conversation7. Failure/output directory retained. Frozen v2code24432f2 preserves null as unknown, separately from absence, without inferred calendar/fact validity. All187,734messages and200question/annotation pairs reconstruct exactly.6focused tests include forged hash plus reader-label-leak rejection. This is authored engineering evidence, **not memory accuracy or an official BEAM reproduction**.

Scale diagnostics:30,177message texts exceed the prior H14500byte cap even without headers;187,054distinct scoped role/text keys and680duplicate opportunities. These are not token counts, guaranteed cache reuse or a universal model-call lower bound. Next: bounded source windows with provenance and affordable capture policy, then freeze the complete candidate/baseline/evaluation/resource protocol. Do not hide capture cost or call ordinary retrieval the same graph candidate. Official scoring has model dependencies; no model judge is authorized.

0newlocal/0paid calls in this stage. H1ledger3262/3300 and API463/$1.852reserved unchanged, retained prefixes verified. Prior totalPR105inference4219unchanged. Registry80rows with old79byte prefix preserved, retrospective format-entry linked to prior code freezes. Memory366events/0violations. Prior documentation head51d4e27 CI completed successfully; new format code requires its own checks. No NIE/persona/frozen predecessor/original dirty worktree changes.


## Laboratory identity and next active work (2026-11-05)

Owner explicitly requests a working concept-testing laboratory. [Active operating view](docs/11-research-laboratory/active-lab-2026-11-05.md) reuses the existing doctrine, instruments, registry, comparative contract and adapters. Current identity: source-grounded state-memory research prototype; model-assisted interpretation/selection, local persistence and inspectable code execution. No generic final-product or unique-architecture claim. APEX-MEM/Graphiti/CAR overlap the core ideas; Mem0/Hindsight current descriptions are author claims, not new reproductions.

One next item under existing#51/#7: pin a common-protocol external adapter/baselines, then separately freeze a complete eligible run. No-memory, ordinary retrieval, our candidate and a compatible pinned competitor are distinct arms. All prior fitting, cost and scoring limits apply. Three mechanism ideas stay a ranked backlog, not new preregistrations. No new model call/cap extension/NIE change.

Code/results head58bdcfc has12/12successful CI jobs, full3377pass/21skip on each Linux Python3.11/3.12, plus the recorded10pinned focused checks; [receipt](data/lab/h1-chronological-pack-v1/delivery.json). Later documentation hashes require their own CI status. A verified private restoration exists for58bdcfc,91copied files/78refs/fsck0 and clean actual checkout; original baseline/previous delivery remain preserved. Current canonical memory365events/0violations; older counts are dated snapshots.


## Owner clarification: baselines, publication age and overfitting (2026-11-05)

Read [the coverage/relevance note](docs/05-benchmarks/memory-baselines-and-benchmark-age-2026-11-05.md). We do have authored N/V controls (local0→48/48raw, Flash0→46/48raw/48delivered), and an original hard local N/K comparison (both0/100). These are not a contemporaneous no-memory arm for the later structured55/59 experiment. H1 base/original is another memory condition, not no memory. Reanalysis reconstructs the old400requests/384primary contexts and report identically, without new calls. The48turns repeat eight fields; absence-of-information abstention is appropriate despite zero target recall.

The GPT-4-era competitor table is historical published configurations, not a present-day ranking. MAB remains a targeted regression task, not the sole modern evaluation. LongMemEval-V2/MemoryArena were source-inspected, not executed/passed. No new GPT/Pro/judge model was authorized or called; Flash/local policy and ledgers unchanged.

Material unresolved fitting risk: public MAB100 and H1 were reused after error inspection and mechanism changes. Protocol/raw freezes and absent gold in planner packets do not establish held-out transfer. The55/59 result measures model+old graph+code, not standalone14B intelligence. Freeze the entire pipeline before unused external cases; report memory-off and ordinary retrieval; retain all outcomes. Any set used for repairs becomes development. No generalization gap is measured yet. Durable events PM-20261105-23572dcb and PM-20261105-92325fb8; memory now364events/0violations. No inference was added by this clarification.


## Latest continuation — density, whole-H1 ordering and competitive calibration (2026-11-05)

Read this block before older snapshots. Density protocol/code `0cac1cd`, raw freeze `edeb178`: all24public OBSOLETE cases, six arms,147actual local calls. Stale-repeat with correction first loses developmentQ000045 (23/24, one leak); the other five arms24/24. ValidationQ000043 passes these controls but its original pack failure remains. [Result](data/lab/h1-evidence-density-v1/README.md).

Whole-H1 paired order protocol/code `959b6c3`, raw freeze `5b195ce`: all168questions/seven families,339new local calls. New original→chronological: dev77→75/84; valid70→72/84 with2→0leaks. Only17pairs reorder;151identical-message controls contain28text differences and one mechanical score difference. Prior v5 counts76/71 remain unchanged. A POISON mechanical loss retains the safe policy in both answers: authored qualitative inspection is separate from unchanged scorer/gold. Validation screen passes for fresh transfer candidacy **only**; no adoption. [All evidence/limits](data/lab/h1-chronological-pack-v1/README.md).

Both offline audits reconstruct480primary native packets with zero failures/parse errors; six transport controls passed. This is authored integrity replay, not independent semantic review. The pinned focused suite passes10tests; prior complete gates3372pass/20skip are from the earlier boundary delivery, not this new head. Check latest-head CI separately. Current claim audit retains45medium/22low findings.

Cumulative H1 local cap explicitly amended before calls at `6a24f95`:3262/3300 attempts now; old prefix retained. This continuation adds486local,0API. PR105 total4219 =3756local+463Flash; paid reservations$1.852, recorded usage upper estimate$0.073913 unchanged. No Pro/fallback/judge/project-planning calls. Owned local model unloaded. The earlier "147 not run/2776 of2800" notes remain dated history.

[External comparison](docs/05-benchmarks/mab-comparison-and-model-bottleneck-2026-11-05.md): published FC-MH reference points include Mem0 2, Zep3, HippoRAG-v2 5, GPT-5-mini28, and CAR/GPT-4o41 at262K. Ours: local55/100 and Flash59/100 exact; secondary SubEM55/60. Different models/ingestion/policy/budgets and spent development prohibit a vendor ranking. The old graph predates safer exact-only capture; do not ascribe its capture efficiency to the repair. Separation of extraction from execution is prior art, not our novelty claim. Paired old outputs:55both correct,41both wrong,4Flash-only,0local-only; posthoc p=.125 is not equality/superiority proof.

Next admissible work: source-pinned common-protocol external adapter/baseline and measurement-validity accounting, without changing old scores or opening confirmation seeds. The pending density registry row is preserved and explicitly superseded by executed DENS-E1-002; ORDER-E1-001 is also completed. Cataloguing is retrospective with prior freeze evidence,79rows total.

No frozen predecessor, original dirty worktree, NIE personality/integration or deployment changed. Rechecked14original worktrees/32,035files,20frozen paths, NIE status/head/diff and shared plan: unchanged. PR105 remains draft; no community/Claude independent review is implied.


## Current continuation — 2026-11-05

The owner authorized implementation and ongoing GitHub updates/community problem reports. The audit below is a preserved historical snapshot, now committed at `5eeb8cc` and pushed; its old "local/uncommitted/no subsequent inference" statements describe the audit itself. PR105 remains draft. No frozen implementation, kernel, original worktree, NIE personality/prompt or deployment was changed.

- New code committed at `b353695`: `tools/structured_memory_v3.py` (exact interpretation replay and visible-predicate plans), `tools/structured_paths_v1.py` (source/time-scoped query packets), `tools/structured_memory_cli_v2.py` (offline interface). Read [boundary results](data/lab/structured-boundaries-v1/README.md). 347 focused checks include 288 counterfactual time/scope fixtures; 100 MAB packets and 200 saved executions are unchanged. Exact-only reuse loses all 18,223 previously template-served MAB opportunities: it is a conservative baseline, not efficient general capture or semantic verification of old claims.
- Community issues: [106](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/106), [107](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/107), [108](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/108). Keep open for the stated limits/review; publishing a counterexample does not mean community review has occurred. Connector writes returned empty results and did not persist issues; authenticated `gh` writes were verified by direct reads.
- Completed [whole-family reader controls](data/lab/h1-obsolete-controls-v1/README.md), with plan `8504591`, frozen preparation/code `b353695`, committed raw freeze `1097e23` before scoring. All 24 public OBSOLETE cases, four conditions, 99 local calls including 3 controls. Original packs: 23/24 answered, one stale leak again in validQ000043. Oracle-only and both two-note orders: 24/24 each, zero leaks. These are oracle-ID diagnostics, not automatic retrieval/general semantic confirmation. Larger-pack evidence composition remains unresolved.
- H1 ledger now 2776/2800 unique attempts; API ledger unchanged at 463 calls, $1.852 reserved and recorded usage upper estimate $0.073913. PR105 cumulative generations 3733 (3270 local/463 Flash), not independent questions. Model digest unchanged and the owned local model unloaded. No new API call, cap extension or ledger reset.
- Full gates pass in both environments: **3372 passed/20 skipped**, plus memory/claim checks. The separate environment uses all six exact requirements pins, pytest8.4.2 and a clean `pip check`, with no global package change. Runtime commit `b353695` has [12/12 successful CI jobs](https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/runs/41967742251), including macOS. See [delivery receipt](data/lab/structured-boundaries-v1/delivery.json). Later commits add data/documentation/replay evidence; do not call the earlier CI run a check of those later hashes.
- Next pending design: [evidence repetition versus neutral volume](docs/11-research-laboratory/evidence-redundancy-next-test-2026-11-05.md), **not executed**. It needs 147 calls and cannot fit the remaining 24 H1 attempts. Any execution requires an explicit resource/protocol amendment before calls, preserving the old ledger. Efficient safe extraction, claim-level correction granularity, automatic conflict handling and fresh transfer are still open.

New local raw evidence/logs/environment are outside Git at `GH_REVIVAL/boundary-repair-2026-11-05`; do not upload the environment or raw requests/answers. Project memory records the boundary cost tradeoff (`PM-20261105-7f46e820`) and reader diagnostic (`PM-20261105-62cf25c0`). Follow the newer status block before the historical audit handover below.

Registry continuity: appended `PMLAB-BOUNDARY-E1-001` and `PMLAB-H1-CTRL-E1-001` with completed results/decisions, plus one pending `PMLAB-H1-DENS-E1-001`. The previous 74 CSV rows are byte-preserved. These entries were catalogued **after execution**, with the earlier plan/code/raw freeze commits separately documented; the catalog append is not a claim of prospective registry entry. This does not backfill every older November study or execute the original unchanged H1-ADDR-E2 protocol.

## Historical audit handover

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
