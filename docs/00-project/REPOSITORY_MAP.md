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
| Compression code reproducibility status | `docs/04-systems/compression-code-reproducibility-audit.md` |
| PI-LLM interference code and reproducibility risks | `docs/04-systems/unable-to-forget-reproducibility-audit.md` |
| Benchmarks and evaluation risks | `docs/05-benchmarks/` |
| Public datasets and labels | `docs/06-datasets/catalog.md` |
| Papers to read | `docs/07-literature/reading-queue.md` |
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
| Neuroscience, information theory, storage, control, offloading, and cross-domain hypotheses | `docs/12-interdisciplinary-memory/` |
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
