# Adaptive Agent Memory Research

Use the local `project_memory` MCP server for continuity across Claude Code, Codex, and other MCP clients.

At the start of a substantial task, run `memory_status` and request a focused `memory_context`. After a durable decision, sourced finding, important failure, new hypothesis, or serious candidate is established, append it with `memory_add`. Use `memory_supersede` when knowledge changes; do not erase earlier events. Facts and decisions need source references. Never store secrets, personal data, raw chain-of-thought, or speculation labeled as fact.

The canonical store is `memory/events.jsonl` plus reviewed Markdown. `memory/CURRENT_STATE.md` is the short current state; the full diagnostic history is in `memory/DIAGNOSTICS_ARCHIVE.md`, which is searchable but not forced into every bundle. `memory/.index/project_memory.sqlite3` is only a generated search index. If MCP is unavailable, use `python tools/project_memory/cli.py <command>`.

Read `AGENTS.md`, `START_HERE.md`, and `memory/CURRENT_STATE.md` for the full workflow and current state.

Before choosing what to work on, read `docs/00-project/operating-doctrine.md`. It carries the selection rule, the work-in-progress limit, and what counts as success.

Latest continuation (2026-11-05): the local-model audit is complete. Start with [HANDOVER](HANDOVER.md) and the [report](data/lab/local-model-upgrade-v2/README.md); the [delivery receipt](data/lab/local-model-upgrade-v2/delivery.json) binds result CI and restoration. [Intermediate stages](data/lab/local-model-upgrade-v2/stage-history.md) have no pending instructions. Keep the historical default/judge; 9B failed promotion and Gemma is incomplete. Documentation finalization adds zero model calls.
