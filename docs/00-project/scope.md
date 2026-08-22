# Scope and Boundaries

Status: reviewed

## In scope

- Persistent, user-owned memory stored on local disk.
- Memory usable across sessions and across compatible LLMs.
- Event capture, representation, indexing, retrieval, consolidation, updating, retention, and archiving.
- Episodic, semantic, procedural, decision, failure, preference, and prospective memory functions.
- Memory quality, privacy, security, provenance, contradiction, and deletion controls.
- Learning which memories help future tasks.
- Human-memory research when it yields a testable computational principle.
- Evaluation on dialogue, knowledge work, coding agents, and long-running projects.

## Out of scope during research phase

- Changing transformer attention or expanding the native context window.
- Claiming biological equivalence between human and LLM memory.
- Claiming machine emotion or consciousness.
- Irreversible automatic deletion.
- Training a large model before establishing deterministic and classical-ML baselines.
- Cloud-first storage of personal memory.

## System boundary

The future system may inspect agent-visible events and tool results, store approved information locally, and inject selected evidence into later prompts. It must not assume access to hidden model activations or provider-side training.

## Privacy boundary

Local-first does not automatically mean safe. Research must include:

- encryption at rest;
- access control between users, agents, projects, and tools;
- secret and credential filtering;
- prompt-injection resistance in stored content;
- explicit export, correction, and deletion;
- auditability of every retrieval and derived memory;
- prevention of cross-user or cross-project leakage.
