# Local model upgrade: historical stage snapshots

The three intermediate HANDOVER sections below are preserved verbatim from [result commit 0688e9b](https://github.com/krapcys1-maker/adaptive-agent-memory-research/blob/0688e9b668e097918ca86996bb61b6c5d32eea1a/HANDOVER.md). They describe registration, the transport amendment and the raw freeze before scoring and cleanup. Their pending instructions are superseded by the completed [report](README.md) and current [HANDOVER](../../../HANDOVER.md).

The fenced block is literal historical source. Its original repository-root-relative links are displayed as text; follow the original handover link above to view them in their original location. Do not resume or repeat these completed stages.

```markdown
## Current local upgrade: raw frozen, authored scoring next (2026-11-05)

All655calls each for Qwen14B and Qwen3.5 9B completed at sourcea71765f; complete native replay0failures. Gemma4 12B fixed Q4 package installed (digest6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b), but its V2phase stopped at251/655 on a foreign TCP client PID36812. Process had exited before identification; TCP alone does not establish inference. Preserve this safety abort, do not force ownership, resume, retry or score missing BEAM cases. [Raw receipt](data/lab/local-model-upgrade-v2/raw-freezes.json) replays every1564attempt including3failedV1controls and251partialGemma; [partial record](data/lab/local-model-upgrade-v2/gemma-incomplete.json) gives limits. Primary comparison is two complete models; no semantic labels joined yet. No model promotion/cleanup is complete.

Sourcea71765f CI12/12success,3577passed/21skipped per Linux3.11/3.12,run42013069495; post-generation auditor adds9focused checks (63total). Later source/result heads need their own CI. Task1564/2000,0API; PR105now6388=5925local+463historicalFlash. H1/API/oldBEAMledgers unchanged. NativePS memory undercounts Gemma versus driver/weight sizes; do not claim1.45GB true footprint. RSS sampling excludes separately named llama-server worker. Read generation-completion.json for desktop/timing caveats. Next: commit this raw/auditor freeze before opening original BEAM references; authored scoring, conservative cleanup, continuity/GH and verified recovery. No NIE/persona/shared-plan/original-dirty-file/frozen-runtime change.


## Active local upgrade amendment v2 (2026-11-05)

V1source9ad192d stopped after3controls and0primary calls because its exact control predicate rejected the valid refusal `I do not know.` with a terminal period. Failure/raw hashes committed atbbe7481; V1 stays failed and is not rewritten. [V2protocol](data/lab/local-model-upgrade-v2/PLAN.md) accepts exactly expected control text or that text plus one period, only for unrelated transport controls. Primary packet SHA d6fd978d6ac2cfe8a9c48054828698fbb34083e3958aaee91361cc56dd530faf is identical; no benchmark/gold/quality/decoding change.54focused checks pass. New private outputs are under the existing task root's `v2` subdirectory; shared root ledger/worker lock retain all3failed attempts, namespaced new keys, ceiling2000 (1968if3models complete). Do not start competing Ollama work. All other ownership/history safeguards from the dated registration below continue. Full raw commit must precede scoring; results/cleanup remain pending.


## Active continuation: controlled local-model upgrade (2026-11-05)

Owner's new attached task explicitly authorizes a read-only audit, official fixed-quant local candidate installation, paired memory-off/on benchmarks and conservative cleanup. [Protocol](data/lab/local-model-upgrade-v1/PLAN.md) and [audit](data/lab/local-model-upgrade-v1/audit.json): old worktrees and seventeen dirty files preserved; historical Qwen14B judge/default unchanged; protected strict alias verified identical 7B weights. Qwen3.5 9B Q4_K_M installed with full digest56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90. No existing model removed or global configuration changed.

New isolated task prepares all84H1valid and200BEAM N/M pairs at8192context, plus all84H1 M repeats and3controls per model (655/model; new cap2000; zero paid). Existing H13262/3300, BEAM605/650, paid463 and PR1054824 are historical prefixes, not reset. Do not run a competing Ollama task, alter prepared inputs or old evaluators/ledgers, switch defaults, touch NIE/persona, or infer semantic improvement from engineering tests. The raw task directory is private at `D:\Pamiec LLM\GH_REVIVAL\local-llm-upgrade-2026-11-05`; its worker lock/reservation ledger identifies ownership. Full raw freeze must be committed before any new label join. Results, optional promotion, cleanup and verified delivery remain pending at this dated source registration; later continuation supersedes this pending status without erasing it. New models are subjects only, never judges/planners.23focused boundary/forgery checks pass; whole-suite preflight is still running and is reported separately when complete.


```
