# Start Here

Before substantial work, inspect [memory/CURRENT_STATE.md](memory/CURRENT_STATE.md) and retrieve a focused context bundle through the project-memory MCP server or CLI. See [memory/README.md](memory/README.md) for setup and usage.

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

The accepted research floor is [Foundation v0](docs/04-systems/foundation-v0-architecture-decision.md): native or open compaction manages continuation, while an append-only local archive preserves future recoverability. Compaction, summaries, embeddings, graphs, salience, and learned memory policies are derived and replaceable; none owns the only copy of evidence.

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
9. [Comparative biological memory](docs/10-comparative-biological-memory/README.md)
10. [Research laboratory](docs/11-research-laboratory/README.md)
11. [Research-to-experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md)
12. [Benchmark ladder](docs/11-research-laboratory/benchmark-ladder.md)
13. [Project Memory Lab v0](docs/11-research-laboratory/project-memory-lab-v0.md)
14. [Foundation v0 architecture decision](docs/04-systems/foundation-v0-architecture-decision.md)
15. [Foundation compaction plus memory benchmark](docs/11-research-laboratory/foundation-compaction-memory-benchmark-protocol-v0.md)
16. [Local dense and hybrid retrieval audit](docs/07-literature/local-dense-hybrid-retrieval-audit.md)
17. [Natural history retrieval benchmark v0](docs/11-research-laboratory/natural-history-retrieval-benchmark-protocol-v0.md)
18. [Natural completeness controller benchmark v0](docs/11-research-laboratory/natural-completeness-controller-benchmark-protocol-v0.md)
19. [Procedural memory retention and relearning benchmark v0](docs/11-research-laboratory/procedural-memory-retention-and-relearning-benchmark-protocol-v0.md)
20. [Tiered routing and future-utility audit](docs/07-literature/tiered-memory-routing-and-future-utility-audit.md)
21. [Memory-manager cascade benchmark v0](docs/11-research-laboratory/memory-manager-cascade-benchmark-protocol-v0.md)
22. [Future-utility telemetry protocol v0](docs/11-research-laboratory/future-utility-telemetry-protocol-v0.md)
23. [Interdisciplinary memory mechanisms](docs/12-interdisciplinary-memory/README.md)
24. [Cross-disciplinary hypothesis portfolio](docs/12-interdisciplinary-memory/hypothesis-portfolio.md)
