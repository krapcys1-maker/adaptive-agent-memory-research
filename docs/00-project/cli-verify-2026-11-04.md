# Project-memory CLI verify — issue 19

`python tools/project_memory/cli.py verify` now delegates to the existing integrity verifier. `--format text` and `--format json` are supported, and the global `--root` selects that root's `memory/events.jsonl`. Clean logs exit 0; violations and missing logs exit 1. Verification occurs before constructing a `MemoryStore`, so it cannot initialize a missing store or rebuild an index.

The bridge loads this repository's verifier explicitly by file, not executable code from a foreign root. No invariant-checking logic is duplicated. The verifier's JSON mode now emits a single valid JSON object on stdout: the old human success footer is confined to text mode. The alias and direct script have identical output and exit status.

Seven new cases cover both output formats for clean/broken logs, the default root, a missing log with no created files, and a foreign root containing hostile Python code. The focused CLI/verifier/memory suite passed 57 tests. Full project validation and exact-head CI are recorded in the PR. `memory/README.md` documents the commands and exit codes.

This change builds on the separately reviewed issue 73 branch. Its memory tail is preserved; original research worktrees and NIE code are not modified. No model calls or deployment are involved.
