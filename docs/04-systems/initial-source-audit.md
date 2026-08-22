# Initial Source Audit

Status: in-progress

This note records findings from the downloaded repositories at the commits listed in `data/catalogs/repository-revisions.csv`. It is an initial documentation audit, not yet a full code or benchmark reproduction review.

## Mem0

Observed in the current README:

- the current open-source design advertises single-pass add-only extraction;
- the documented current path avoids automatic update/delete during extraction;
- retrieval combines semantic, BM25 keyword, and entity signals;
- temporal reasoning is explicitly advertised;
- managed-platform benchmark results include proprietary optimizations not present in the open-source SDK;
- APIs expose explicit update, delete, scoped deletion, and expiration operations.

Research value:

- strong production baseline and API reference;
- useful comparison for append-only extraction versus LLM-controlled mutation;
- must not equate managed-service benchmark claims with reproducible OSS behavior.

## Letta

Important discovery:

- `letta-ai/letta` is now a landing page;
- current source moved to `letta-ai/letta-code`;
- retired Letta V1 source remains on the `archive` branch and is unsupported.

Action: review `letta-code` as the current system and the archived V1 branch only for historical MemGPT lineage.

## Graphiti

Observed in the current README:

- episodes preserve the raw ingested ground-truth stream;
- derived entities and relationships trace back to episodes;
- facts have temporal validity windows and are invalidated rather than deleted when superseded;
- retrieval combines semantic, keyword, and graph traversal;
- incremental updates avoid complete graph recomputation;
- open-source Graphiti requires an external graph backend and application-level user/conversation management.

Research value: currently the closest examined component to our provenance, temporal validity, and immutable-evidence requirements. Its automatic invalidation and extraction accuracy still require code and benchmark audit.

## LangMem

Observed in the current README:

- separates in-conversation “hot path” memory tools from a background memory manager;
- the background manager extracts, consolidates, and updates knowledge;
- agents may decide when to store and search;
- storage primitives are separable from the agent workflow;
- the example in-memory store is nonpersistent; database-backed storage is required for durability.

Research value: useful workflow abstraction for capture timing and background consolidation. We must test whether agent-decided writes/searches miss critical events and whether updates preserve evidence.

## A-MEM

Observed in the paper-reproduction repository:

- new memories become structured notes;
- the system generates contextual descriptions and tags;
- it links new and historical memories;
- memory organization evolves through LLM-driven operations;
- the paper reproduction code and current system implementation are separate repositories.

Research value: central dynamic-organization comparison. Main risks to audit are write/update cost, unverified links, consolidation drift, and benchmark tuning.

## LightMem and StructMem

Observed in the current repository:

- the repository now hosts multiple memory methods, including LightMem and StructMem;
- it contains LoCoMo and LongMemEval reproduction scripts plus a separate MemBase benchmarking project;
- supported components include pre-compression, topic segmentation, LLM memory management, embeddings, Qdrant, FAISS, and BM25;
- local-model paths using Ollama, vLLM, and Transformers are documented;
- StructMem emphasizes event-level bindings and cross-event connections.

Research value: high-priority reproducible framework for comparing compression, structured consolidation, token use, and retrieval. Because many methods share one repository, evaluation configuration and dataset versions require careful isolation.

## TiMem

Observed in the current repository:

- a five-level Temporal Memory Tree transforms fine-grained fragments into increasingly stable abstractions/persona information;
- temporal ordering is first-class;
- consolidation is instruction-guided and does not require fine-tuning;
- recall scope is described as complexity-aware;
- the system supports self-hosting but requires multiple storage services in the documented full setup;
- parts of the project use different permissive licenses.

Research value: strong temporal-hierarchy comparison. Main questions are consolidation fidelity, low-frequency detail preservation, infrastructure cost, and whether persona-focused results transfer to coding/research agents.

## General lesson from the first audit

Current systems are converging on:

- structured extraction;
- hybrid retrieval;
- temporal metadata;
- background consolidation;
- graph or hierarchical organization;
- local/self-hosted options;
- common benchmark harnesses.

The most defensible research gap is therefore not “persistent vector memory.” It is reliable lifecycle control: evidence-preserving consolidation, causal utility, learned retention, type-conditioned forgetting, and subsystem-level evaluation.
