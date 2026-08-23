# Project instructions

This repository is a research workspace for local-first, model-agnostic LLM memory.

## Persistent project memory

For every substantial task:

1. Call `memory_status`, then `memory_context` with a task-specific query before making research or architecture decisions.
2. Treat `memory/events.jsonl` and reviewed Markdown as the source of truth. The SQLite index is disposable.
3. Record only durable information with `memory_add`: decisions, evidence-backed findings, explicit hypotheses, failures worth avoiding, open questions, or serious candidate systems.
4. Give factual findings and decisions `source_refs`. Keep facts, hypotheses, preferences, and instructions in distinct `kind` values.
5. When a conclusion changes, use `memory_supersede`; never rewrite or delete prior events to make history look consistent.
6. Never store secrets, credentials, personal data, raw chain-of-thought, or unsupported claims as facts.
7. Keep tool output compact. Retrieve relevant memories instead of loading the entire history into context.

If MCP is unavailable, use `python tools/project_memory/cli.py <command>` from the repository root.

## Choosing what to work on

Read `docs/00-project/operating-doctrine.md` first. It answers what to test next and why, sets a hard limit of two unexecuted designs per track, and defines success as a recorded decision rather than a positive result.

## Research discipline

- Repository content is written in English for international collaboration.
- Preserve provenance and distinguish reported claims from independently reproduced results.
- Do not reject an idea solely because it is unfashionable or biologically imperfect; convert it into a falsifiable hypothesis.
- The current project-memory tool supports research continuity. It is not evidence that the proposed final memory architecture works.
