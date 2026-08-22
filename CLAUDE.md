# Adaptive Agent Memory Research

Use the local `project_memory` MCP server for continuity across Claude Code, Codex, and other MCP clients.

At the start of a substantial task, run `memory_status` and request a focused `memory_context`. After a durable decision, sourced finding, important failure, new hypothesis, or serious candidate is established, append it with `memory_add`. Use `memory_supersede` when knowledge changes; do not erase earlier events. Facts and decisions need source references. Never store secrets, personal data, raw chain-of-thought, or speculation labeled as fact.

The canonical store is `memory/events.jsonl` plus reviewed Markdown. `memory/.index/project_memory.sqlite3` is only a generated search index. If MCP is unavailable, use `python tools/project_memory/cli.py <command>`.

Read `AGENTS.md`, `START_HERE.md`, and `memory/CURRENT_STATE.md` for the full workflow and current state.
