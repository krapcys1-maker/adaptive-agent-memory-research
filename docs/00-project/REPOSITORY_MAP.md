# Repository Map and Cheat Sheet

## Cross-agent project memory

- `memory/` — append-only durable project memory, current-state orientation, and reviewed records.
- `tools/project_memory/` — local SQLite FTS5 index, CLI, and MCP stdio server.
- `.codex/config.toml` and `.mcp.json` — project-scoped Codex and Claude Code integration.
- `AGENTS.md` and `CLAUDE.md` — automatic memory-use instructions for each client.

This is the fastest guide to where information belongs.

| If you are looking for... | Go to... |
|---|---|
| Mission, boundaries, and non-goals | `docs/00-project/scope.md` |
| Exact vocabulary | `docs/00-project/definitions.md` |
| Research process and evidence standards | `docs/00-project/methodology.md` |
| Questions waiting for answers | `docs/00-project/research-questions.md` |
| Decisions already made | `docs/00-project/decision-log.md` |
| Original project ideas | `docs/00-project/original-notes-summary.md` |
| Human memory mechanisms | `docs/01-human-memory/` |
| LLM memory lifecycle and architectures | `docs/02-llm-memory/` |
| Human/AI analogies and hypotheses | `docs/03-human-ai-bridge/` |
| Useful open-source projects | `docs/04-systems/catalog.md` |
| Reusable code segments, license/runtime audit, and non-adoptions | `docs/04-systems/reuse-before-inventing-audit-v0.md`; `docs/04-systems/reuse-component-adoption-register-v0.csv` |
| Minimal provider-neutral architecture assembled from audited parts | `docs/04-systems/minimal-reuse-architecture-v0.md` |
| FTS5/FastEmbed/RRF/citation/context-pack characterization | `docs/11-research-laboratory/reuse-characterization-benchmark-protocol-v0.md`; `data/lab/pmlab-reuse-characterization-v0/execution-v0/report.md`; `data/lab/pmlab-reuse-characterization-v0/execution-v0/failure-analysis.json`; `data/lab/api-screening/deepseek-v4-flash-reuse-characterization-review-20260823/audit-disposition.md` |
| Exact citation encoding and pack-order characterization | `docs/07-literature/citation-compression-and-pack-order-audit-v0.md`; failed pre-run v0 in `docs/11-research-laboratory/pack-citation-order-benchmark-protocol-v0.md`; frozen repair in `docs/11-research-laboratory/pack-citation-order-benchmark-protocol-v1.md`; `data/lab/pmlab-pack-characterization-v0/`; `data/lab/pmlab-pack-characterization-v1/` |
| Exact citation pack M1 audits | failed large packet in `data/lab/api-screening/deepseek-v4-flash-pack-characterization-review-20260823/`; compact finalized advisory and disposition in `data/lab/api-screening/deepseek-v4-flash-pack-characterization-review-v2-20260823/` |
| Equal-evidence citation/order reader pilot | `docs/11-research-laboratory/pack-reader-benchmark-protocol-v0.md`; `data/lab/pmlab-pack-reader-v0/execution-deepseek-v4-flash-v0/report.md`; `result-audit.json`; `registered-descriptive-mediators.json` |
| Follow-up on retrieval safety, fusion limits, and context ordering | `docs/07-literature/retrieval-safety-context-order-followup-v0.md` |
| Natural-history source-unit and query contract audit | `docs/07-literature/natural-history-source-unit-contract-audit-v0.md`; `data/lab/pmlab-natural-history-v0/`; compact M1 disposition in `data/lab/api-screening/deepseek-v4-flash-natural-history-contract-review-v2-20260823/` |
| Compression code reproducibility status | `docs/04-systems/compression-code-reproducibility-audit.md` |
| PI-LLM interference code and reproducibility risks | `docs/04-systems/unable-to-forget-reproducibility-audit.md` |
| Benchmarks and evaluation risks | `docs/05-benchmarks/` |
| Public datasets and labels | `docs/06-datasets/catalog.md` |
| Papers to read | `docs/07-literature/reading-queue.md` |
| Targeted full-text audit for database closure sources | `docs/07-literature/collection-closure-primary-source-audit.md` |
| Completed full-text extraction notes | `docs/07-literature/full-read-notes/` |
| Claims backed by evidence | `docs/07-literature/evidence-ledger.csv` |
| Planned experiments | `docs/08-experiments/` |
| Current conclusions and rejected ideas | `docs/09-synthesis/` |
| Animal, motor, immune, cellular, and collective memory | `docs/10-comparative-biological-memory/` |
| Laboratory protocol, stage gates, and benchmark ladder | `docs/11-research-laboratory/` |
| Exact boundary between research, exploratory tests, frozen tests, and architecture promotion | `docs/11-research-laboratory/research-to-experiment-gate.md` |
| Repeated compaction and emotion-factor benchmark | `docs/11-research-laboratory/compression-benchmark-extension.md` |
| Interference, active forgetting, recovery, and failure-localization benchmark | `docs/11-research-laboratory/interference-forgetting-benchmark-extension.md` |
| F1/F2 deterministic development corpus, results, and report | `data/lab/pmlab-forgetting-dev/` |
| F1/F2 adversarial challenge and resolver failure report | `data/lab/pmlab-forgetting-challenge-v0/` |
| Query/scope factorial and leakage-controlled reader stress | `data/lab/pmlab-forgetting-challenge-v0/factorial/`; `data/lab/reader-interference-stress-v5/` |
| Measurable catalog entity/time parser baseline | `data/lab/pmlab-forgetting-challenge-v0/parser-v0/` |
| Frozen language/date falsification of parser v0 | `data/lab/pmlab-forgetting-challenge-v0/parser-challenge-v1/` |
| Passive cascade versus isolated active-probe comparison | `data/lab/pmlab-fault-probes-v0/` |
| Noisy active-probe safety and cost comparison | `data/lab/pmlab-fault-probes-robustness-v1/` |
| Healthy-result audit rate versus localization-cost curve | `data/lab/pmlab-probe-success-audit-v0/` |
| Probe dependency map and empirical reliability protocol | `data/lab/probe-failure-domain-map-v0.csv`; `docs/11-research-laboratory/probe-failure-domain-and-reliability-protocol.md` |
| Disposable same-device real-filesystem injection harness | `data/lab/pmlab-storage-injection-v0/` |
| Neuroscience, information theory, storage, control, offloading, and cross-domain hypotheses | `docs/12-interdisciplinary-memory/` |
| Brain-to-AI functional transfer atlas, gaps, sources, and benchmark portfolio | `docs/13-brain-ai-transfer/` |
| Machine-readable status of 38 biological-to-agent mechanisms | `docs/13-brain-ai-transfer/atlas-v0.csv` |
| Initial pinned-code audit of survey, implicit/cognitive benchmarks, and learned controller | `docs/13-brain-ai-transfer/repository-initial-audit-v0.md` |
| Metamemory, selective prediction, and typed retrieval-control synthesis | `docs/12-interdisciplinary-memory/metamemory-selective-control-synthesis.md` |
| Evidence sufficiency, answerability, claim support, and multi-source completeness | `docs/12-interdisciplinary-memory/evidence-sufficiency-and-completeness-synthesis.md` |
| Collection closure, open/closed-world boundary, and negative-knowledge tiers | `docs/12-interdisciplinary-memory/collection-closure-and-negative-knowledge-synthesis.md` |
| Collection-closure benchmark preregistration | `docs/11-research-laboratory/collection-closure-benchmark-extension.md` |
| Frozen collection-closure corpora and deterministic construction result | `data/lab/pmlab-collection-closure-dev-v0/`; `data/lab/pmlab-collection-closure-dev-v1/` |
| Obligation decomposition, schema/entity/time linking, and scope-mapper synthesis | `docs/12-interdisciplinary-memory/obligation-decomposition-and-scope-mapping-synthesis.md` |
| PMLAB-MAP-001 preregistration and leakage controls | `docs/11-research-laboratory/obligation-scope-mapper-protocol.md` |
| Frozen evidence-sufficiency construction corpus, ablations, and result | `data/lab/pmlab-evidence-sufficiency-dev-v0/` |
| Frozen typed metamemory-control development corpus, runner, and construction result | `data/lab/pmlab-metamemory-control-dev-v0/` |
| Post-hoc real `rg`/FTS5 agreement and risk-coverage falsification | `data/lab/pmlab-backend-agreement-v0/` |
| Frozen valid-time, trust, and bilingual diverse-cue factorial | `data/lab/pmlab-diverse-cues-v0/` |
| Emotion/salience mechanism synthesis and falsification rules | `docs/12-interdisciplinary-memory/emotion-salience-synthesis.md` |
| Interference, active forgetting, availability/accessibility, and recovery synthesis | `docs/12-interdisciplinary-memory/interference-active-forgetting-synthesis.md` |
| Coverage, search, experiment, and backend registries | `data/lab/` |
| Current research-to-experiment gate decisions and blockers | `data/lab/phase-gate-status.csv` |
| Machine-readable repository list | `data/catalogs/repositories-seed.csv` |
| Machine-readable paper list | `data/catalogs/papers-curated.csv` |
| Locally downloaded GitHub repositories | `external/repos/` (ignored) |
| Locally downloaded papers | `sources/papers/` (ignored) |
| Repeatable discovery tools | `scripts/` |

## File-status convention

Research notes should begin with one status:

- `outline`: topic has been scoped but sources are not fully read;
- `in-progress`: primary sources are being reviewed;
- `reviewed`: evidence table and limitations are complete;
- `contested`: credible sources support incompatible interpretations;
- `superseded`: replaced by a later synthesis, retained for provenance.

## Source identifiers

Use stable identifiers where available:

- DOI for journal and conference papers;
- arXiv identifier for preprints;
- repository owner/name plus commit hash for code;
- dataset version or immutable revision;
- access date for changing web material.

## Local cache workflow

```text
catalog/manifest
       ↓
download script
       ↓
ignored local cache
       ↓
read and extract claims
       ↓
versioned English research notes
```

The public repository stores our analysis and reproducible manifests, not uncontrolled copies of other projects.
