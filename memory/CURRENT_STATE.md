# Current project state

## Objective

Research a local-first, model-agnostic long-term memory layer for LLM agents. The model context window remains working memory; durable evidence, experiences, conclusions, and procedures live on the user's disk.

## Current phase

Evidence collection, source auditing, candidate preservation, benchmark design, and falsifiable hypothesis formation. We are not yet claiming a validated final architecture.

## Project-memory bootstrap

A dependency-free local memory now supports continuity of this research:

- Git-tracked append-only JSONL and reviewed Markdown are canonical;
- SQLite FTS5 is a disposable local index;
- MCP stdio serves Codex, Claude Code, and other clients;
- CLI remains available to clients without MCP;
- no model API key, vector database, graph database, or cloud account is required.

## Immediate priorities

1. Build a gold query set from real research sessions and measure lexical retrieval before adding embeddings.
2. Audit candidate repositories at pinned revisions and separate reusable mechanisms from marketing claims.
3. Define success metrics for write quality, retrieval, temporal revision, provenance, latency, token cost, and harmful-memory intrusion.
4. Study emotional salience as a testable prioritization signal, separated from simulated affect or claims of subjective emotion.
5. Preserve rejected and strange ideas as labeled hypotheses unless evidence rules them out.
