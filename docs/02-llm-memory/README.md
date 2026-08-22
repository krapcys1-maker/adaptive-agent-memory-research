# LLM and Agent Memory Research Map

Status: outline

## Memory substrates to compare

- Model parameters.
- Context tokens and recurrent summaries.
- Local files and append-only logs.
- Relational databases and document stores.
- Sparse indexes and vector stores.
- Temporal or causal knowledge graphs.
- Hierarchical summaries and trees.
- Learned latent states.
- Executable skills and procedures.

The target project centers on local external storage, but other substrates remain useful comparison classes.

## Lifecycle dimensions

| Stage | Questions |
|---|---|
| Observe | Which messages, actions, tool results, environment changes, and outcomes are visible? |
| Encode | What unit and representation should be created? |
| Write | Which candidate memories are admitted, rejected, or quarantined? |
| Organize | How are entity, time, task, causal, and source relations represented? |
| Consolidate | When are episodes transformed into facts, beliefs, or procedures? |
| Retrieve | When does search occur, using which index and cue? |
| Construct | Which evidence fits within the current token budget? |
| Use | Did memory influence a decision or merely appear in the prompt? |
| Evaluate | Did it improve the outcome, and at what cost? |
| Retain | Should accessibility increase, decay, or move to archive? |
| Correct | How are contradictions, new states, and user corrections represented? |
| Delete | How is user-requested erasure performed across derived representations? |

## Primary architecture families

- Flat fact stores.
- Raw episodic stores.
- Summarization and reflection memory.
- Hierarchical memory.
- Temporal knowledge graphs.
- Hybrid symbolic/vector retrieval.
- File-system memory for coding agents.
- Learned write, retrieval, or retention policies.
- Skill libraries and procedural experience.
- Multi-agent shared memory with governance.

## Failure taxonomy

- Observation was never captured.
- Encoding lost essential detail.
- Memory was written under the wrong entity or time.
- Consolidation introduced an unsupported claim.
- Correct memory existed but was not retrieved.
- Distractors displaced relevant evidence.
- Correct evidence exceeded the context budget.
- The model ignored or misread retrieved evidence.
- The memory was stale, poisoned, or contradicted.
- The final action failed despite correct use of memory.
