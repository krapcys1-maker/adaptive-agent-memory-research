# Minimal extensible architecture

Status: provisional

This is a research boundary, not a technology selection.

```text
                         immutable plane
sources + agent events ───────────────────→ raw evidence store
          │                                      │
          │                                      ↓
          │                              normalized source cards
          │                                      │
          ↓                                      ↓
append-only audit log                    atomic claim ledger
          │                                      │
          └───────────────┬──────────────────────┘
                          ↓
                  derived local views
             sparse | dense | temporal | graph
                          ↓
                 common retrieval contract
                          ↓
              budgeted context construction
                          ↓
         OpenAI | Claude | local model | other client

experiment manifests → frozen runner → run artifacts → review → decisions
```

## Stable core

- immutable source/event identity;
- append-only change history;
- provenance edges;
- typed claims, decisions, hypotheses, procedures, failures, and intentions;
- timestamps, valid-time, scope, confidence, and supersession;
- exportable text/JSON formats owned by the user;
- local access control and secret filtering.

## Replaceable adapters

- lexical index;
- embedding model and vector index;
- fusion/reranker;
- temporal index;
- graph representation;
- context builder;
- model provider;
- evaluator and judge.

All retrieval adapters receive the same frozen corpus and query object and return the same result shape:

```text
memory_id
source_id
score
rank
retrieval_signals
valid_time
token_count
provenance
backend_version
```

## Why this remains simple

- Text and JSON remain canonical; every index is derived.
- The model provider is outside the memory core.
- A new mechanism is an adapter, not a migration of user truth.
- Experiment artifacts and operational memory share identifiers but not authority.
- The system can begin with `rg` and FTS5, then add one measured capability at a time.

## Architectural unknowns deliberately left open

- final memory-object granularity;
- embedding model and vector database;
- graph database versus derived edge files;
- automatic write policy;
- consolidation model and schedule;
- emotional/operational-salience representation;
- learned retention and forgetting;
- encryption and multi-agent authorization implementation.

These remain open until their corresponding stage gates pass.
