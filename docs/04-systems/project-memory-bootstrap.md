# Provider-neutral project-memory bootstrap

## Purpose

This is a continuity tool for the research repository, not the proposed final agent-memory system. Its job is to let different subscription-based coding agents share durable project context without a model API key.

## Architecture

```text
Codex (subscription) ---- AGENTS.md ----\
                                      MCP stdio ---- local Python core
Claude Code ----------- CLAUDE.md -----/                  |
Other agents ---------------- CLI ------------------------+
                                                         |
                                      Git-tracked JSONL + Markdown
                                                         |
                                      disposable SQLite FTS5 index
```

The context window remains transient working memory. The tool retrieves a small task-specific bundle; it never injects the entire history.

## Reused ideas, not runtime dependencies

| Source project | Idea retained | Deferred or rejected for bootstrap |
| --- | --- | --- |
| AgentMemory | MCP tools, explicit save/recall, timeline, diagnostics, gold-query retrieval evaluation | Large tool surface, service runtime, automatic capture, unverified benchmark generalization |
| Graphiti | raw evidence provenance, temporal change, history-preserving supersession | graph database, automatic LLM extraction, entity resolution |
| LangMem | hot-path write tools versus background consolidation | LangGraph coupling and LLM-managed consolidation |
| Mem0 | append-only direction, lexical/semantic/entity retrieval as separable signals | managed service, API accounts, proprietary benchmark results, immediate vector dependency |
| Letta/MemGPT | explicit state and bounded memory blocks | agent runtime coupling and provider-specific orchestration |

## Why this first

Plain text and lexical search provide an auditable lower bound. If later embeddings, a temporal graph, emotional salience, learned consolidation, or forgetting cannot beat this baseline under controlled evaluation, their complexity is not justified.

## Deliberate limitations

- FTS5 is lexical and cannot reliably solve paraphrase or latent semantic matches.
- Memory writes are model-proposed, so write quality still requires review and benchmarks.
- `CURRENT_STATE.md` is manually curated and may drift; the append-only event log remains the audit trail.
- Cross-client configuration is present, but each client applies its own trust and tool-approval policy.
- No claim is made that the current store models human memory.

## Next evaluation

Create a small project-specific benchmark with real sessions, dated events, superseded decisions, paraphrases, distractors, and intentionally irrelevant memories. Compare `rg`, SQLite FTS5, and later hybrid retrieval using Recall@k, MRR/nDCG, supported-answer accuracy, temporal accuracy, provenance precision, harmful intrusion rate, latency, and token cost.
