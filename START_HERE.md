# Start Here

## What we are building toward

The desired future system has two boundaries:

```text
LLM context window
  = immediately available working set

User-owned disk
  = durable events, facts, decisions, skills, sources, and archives
```

A controller between them performs a lifecycle:

```text
observe -> encode -> write -> organize -> consolidate -> retrieve
        -> use -> evaluate utility -> revise/archive
```

This is not a claim that a context window is biologically identical to human working memory. It is an engineering analogy whose useful and misleading parts must be tested.

## The first five questions

1. What is the atomic unit of agent memory: message, event, fact, relation, episode, procedure, or decision?
2. How can the system distinguish storage failure from retrieval failure and reasoning failure?
3. How can future utility be measured causally rather than inferred from retrieval frequency?
4. When should exact episodes be consolidated into semantic or procedural knowledge?
5. How can memories be updated without losing provenance, uncertainty, or superseded historical states?

## How to contribute research

For every important claim:

1. Link the primary source.
2. State what the source actually demonstrates.
3. Record limitations and competing interpretations.
4. Separate biological findings from proposed AI analogues.
5. Convert the analogue into a falsifiable hypothesis.
6. Define what evidence would reject the hypothesis.

## Confidence vocabulary

- **Established:** supported by multiple strong sources or replicated evidence.
- **Supported:** credible evidence exists but scope or interpretation is limited.
- **Preliminary:** early result, preprint, or narrow experimental setting.
- **Hypothesis:** testable proposal without sufficient evidence yet.
- **Analogy:** conceptual mapping, not evidence of shared mechanism.
- **Speculation:** useful idea that is not yet operationalized.
- **Rejected:** contradicted, non-falsifiable, or empirically unhelpful.

## Immediate reading path

1. [Scope and boundaries](docs/00-project/scope.md)
2. [Definitions](docs/00-project/definitions.md)
3. [Human memory research map](docs/01-human-memory/README.md)
4. [LLM memory research map](docs/02-llm-memory/README.md)
5. [Human-to-AI mapping](docs/03-human-ai-bridge/mapping.md)
6. [Systems catalog](docs/04-systems/catalog.md)
7. [Benchmark catalog](docs/05-benchmarks/catalog.md)
8. [Research methodology](docs/00-project/methodology.md)
