# Context Window and Durable Memory Boundary

Status: reviewed

## Design stance

The context window is an interface constraint, not the durable memory store. The future memory system should work with existing APIs by selecting a bounded working set from local persistent storage.

```text
local durable memory
        ↓ retrieve
evidence candidates
        ↓ rank and budget
active working set
        ↓ format
LLM context window
```

## What must happen outside the model

- Durable storage and user ownership.
- Versioning and provenance.
- Temporal validity and supersession.
- Index construction.
- Candidate retrieval.
- Token budgeting.
- Access controls and deletion.
- Experiment logging and utility labels.

## What may involve an LLM

- Ambiguous event extraction.
- Query reformulation.
- Relation and causal-candidate extraction.
- Consolidation proposals.
- Procedure induction.
- Evidence-aware summarization.

The deterministic controller executes changes and preserves source links. An LLM proposal is not self-validating.

## Important comparison

Growing context windows can reduce the need for retrieval on small histories but do not solve:

- indefinite growth;
- privacy and portability;
- contradiction and validity management;
- cross-session structured state;
- reuse of experience across tasks;
- controlled forgetting;
- auditability and user correction;
- latency and inference cost.
