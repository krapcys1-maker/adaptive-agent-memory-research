# Open-Source Systems Catalog

Status: in-progress

The machine-readable selection is in `data/catalogs/repositories-seed.csv`. Repository metrics and licenses should be refreshed before any architecture or adoption decision.

## Tier A — Download and inspect first

### General memory systems

- **Mem0:** strong production baseline for extraction, update, storage, retrieval, and deletion.
- **Letta:** stateful-agent architecture derived from MemGPT ideas.
- **Graphiti:** temporal knowledge graphs, validity, provenance, and graph retrieval.
- **LangMem:** hot-path versus background memory workflows.
- **MemOS:** broad memory lifecycle and evaluation platform.
- **AgentMemory:** local persistent memory for coding agents and project integration.
- **A-MEM:** dynamic note construction, linking, and memory evolution.
- **LightMem/StructMem:** efficient pipelines, structured consolidation, and benchmark tooling.
- **TiMem:** explicit temporal hierarchy and multi-level consolidation.

### Retrieval components

- **HippoRAG:** graph construction plus personalized PageRank.
- **RAPTOR:** hierarchical abstraction and tree retrieval.
- **GraphRAG:** broader graph-RAG comparison, reviewed selectively because of size.

### Benchmarks and datasets

- LongMemEval.
- LoCoMo.
- LongMemEval-V2.
- BEAM.
- MemoryAgentBench.
- Mem0 memory-benchmarks.
- OmniMemEval.
- MiMo Claude Code Traces.

### Foundational agent designs

- Generative Agents.
- Reflexion.
- Voyager.
- ExpeL.
- MemoryBank.

## What to extract from every system

| Dimension | Questions |
|---|---|
| Capture | What events are visible and automatically recorded? |
| Unit | Message, fact, note, episode, document, graph edge, skill? |
| Source preservation | Is raw evidence retained and addressable? |
| Update | Append, merge, overwrite, supersede, or version? |
| Time | Are event time, observation time, and validity time distinct? |
| Retrieval | Sparse, dense, graph, temporal, reranked, iterative? |
| Trigger | Always search, model choice, rules, or learned policy? |
| Consolidation | How are summaries or rules created and corrected? |
| Forgetting | Deletion, decay, archive, access weight, or none? |
| Utility | What feedback determines whether memory helped? |
| Security | Local mode, tenancy, encryption, access control, injection defense? |
| Evaluation | Dataset version, reader, judge, token budget, latency, and cost? |
| License | Can code or data be reused in the intended project? |

## Adoption rule

A high star count is not evidence of memory quality. No dependency is selected before code inspection, license review, benchmark reproduction, and comparison with a minimal local baseline.

## Primary research-code artifacts

- **amvjakob/wm-rate-distortion:** primary Julia notebooks for Figures 2–8 of the working-memory paper. The [reproducibility audit](compression-code-reproducibility-audit.md) found missing pinned dependencies, data artifacts, and a license, so it is a research reference rather than an adoptable dependency.
- **NOBI327/amygdala:** audited at `344133c`; 331 tests pass with a dummy OpenAI key, but its central ranker is affect/scene/time based rather than content based and its schema lacks the project's evidence/version/provenance contract. The [repository audit](amygdala-repository-audit.md) retains it as a tier-C salience comparator, not a foundation.

## Reuse-before-inventing audit

The [component audit](reuse-before-inventing-audit-v0.md) and [machine-readable adoption register](reuse-component-adoption-register-v0.csv) inspect exact reusable boundaries from GoodMemory, mnemos, mcp-local-memory, and memo. The [minimal reuse architecture](minimal-reuse-architecture-v0.md) combines only their strongest separable ideas with established protocol, privacy, encryption, and scheduling components.

The current decision is deliberately composite: adapt typed evidence and traces, cited local retrieval and path safety, exposure-versus-feedback accounting, and current/supporting/stale context packs. Do not adopt any one full memory product as the project core.
