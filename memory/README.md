# Project memory

This directory is the durable, provider-neutral memory of the research project. It works without an LLM API key.

## What is canonical

- `events.jsonl` is the append-only structured event stream.
- `CURRENT_STATE.md` is a small, human-reviewed orientation page.
- `records/` contains longer reviewed notes that should remain easy to read and diff.
- `templates/` defines recommended note shapes.

`memory/.index/project_memory.sqlite3` is generated and ignored by Git. Delete it at any time; `memory_rebuild_index` or the CLI rebuilds it from canonical files.

## Interfaces

The same Python core is exposed in two ways:

- MCP over local stdio for Codex, Claude Code, and other MCP clients;
- CLI for any agent that can run a shell command.

Examples:

```sh
python tools/project_memory/cli.py status
python tools/project_memory/cli.py search "emotional salience consolidation"
python tools/project_memory/cli.py context "compare memory candidates" --char-budget 8000
python tools/project_memory/cli.py add --kind finding --title "Short title" --summary "Durable claim" --source "paper DOI or repository path" --confidence medium
python tools/project_memory/cli.py supersede PM-YYYYMMDD-xxxxxxxx --reason "New evidence" --summary "Revised conclusion"
```

## Design boundaries

- This tool remembers the project; it is not the final experimental memory architecture.
- It performs lexical FTS5 retrieval, not embedding search. This is an intentional baseline.
- It does not summarize conversations automatically or call a model in the background.
- A model decides what to propose for storage, while the append-only record preserves reviewability.
- Sensitive data and raw private reasoning must never be stored.
