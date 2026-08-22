# Current project state

## Objective

Research a local-first, model-agnostic long-term memory layer for LLM agents. The model context window remains working memory; durable evidence, experiences, conclusions, and procedures live on the user's disk.

## Current phase

Evidence collection, comparative biological-memory expansion, source auditing, candidate preservation, and formal laboratory design. We are not yet claiming a validated final architecture. Mechanisms advance through registered stage gates rather than plausibility alone.

## Project-memory bootstrap

A dependency-free local memory now supports continuity of this research:

- Git-tracked append-only JSONL and reviewed Markdown are canonical;
- SQLite FTS5 is a disposable local index;
- MCP stdio serves Codex, Claude Code, and other clients;
- CLI remains available to clients without MCP;
- no model API key, vector database, graph database, or cloud account is required.
- external API models are optional, replaceable batch workers; they may write review candidates but never accepted evidence directly.

## Immediate priorities

1. Run the six-round coverage protocol and repair the distinction between discovered, screened, read, and independently reviewed sources.
2. Build and independently review `project-memory-lab-v0`, including dated evidence, supersession, paraphrase, causal, abstention, bilingual, poisoned-memory, and distractor cases.
3. Reproduce `rg` and FTS5/BM25 baselines under a frozen retrieved-token budget before selecting local embeddings.
4. Fully read and snowball the comparative source seeds for animal, motor, skeletal-muscle, immune, transcriptional, non-neural, CRISPR, and collective memory.
5. Audit candidate repositories at pinned revisions and separate reusable mechanisms from marketing claims.
6. Test emotional salience only after utility labels and consequence-weighted retention metrics exist; never equate operational signals with subjective emotion.
7. Preserve rejected ideas, null results, and failed runs as labeled evidence.
8. Before adding an API worker, preregister a frozen admission pilot measuring locator accuracy, unsupported claims, abstention, reviewer time, cost, privacy, and provider failure.
