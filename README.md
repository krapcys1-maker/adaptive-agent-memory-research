# Adaptive Agent Memory Research

An open research workspace for designing **local-first, model-agnostic, long-term memory for LLM agents**.

The target system does not require changing a model's context-window implementation. The context window remains the agent's immediately available workspace; durable memory is stored on the user's disk and a memory controller decides what to write, preserve, consolidate, retrieve, revise, and archive.

This repository is currently a **research project, not a production memory implementation**.

## Research objective

We want to determine whether an external memory layer can help an agent accumulate useful experience over months or years while keeping inference context small, evidence-grounded, and relevant.

The central research hypothesis is:

> An agent needs complementary memory systems: a lossless or evidence-preserving episodic store for rapid learning from individual experiences, and a slower semantic/procedural store that consolidates recurring evidence. Memory transitions should eventually be governed by measured future utility, not semantic similarity alone.

## Non-negotiable constraints

- User data remains local by default.
- The system must be model-agnostic.
- Raw evidence is append-only during early research.
- Experimental forgetting must not destroy the only copy of a memory.
- Every derived memory must preserve provenance.
- Facts, hypotheses, decisions, preferences, and instructions must not be conflated.
- A retrieved memory is not automatically a useful memory.
- Every added mechanism must justify itself in controlled evaluation.

## Start here

1. Read [START_HERE.md](START_HERE.md).
2. Review the complete [research plan](RESEARCH_PLAN.md).
3. Use the [repository map](docs/00-project/REPOSITORY_MAP.md) to find materials.
4. Check [research questions](docs/00-project/research-questions.md) before adding a source.
5. Record claims in the [evidence ledger](docs/07-literature/evidence-ledger.csv).
6. Follow [CONTRIBUTING.md](CONTRIBUTING.md) when proposing changes.

## Repository layout

```text
docs/00-project/          Scope, definitions, methodology, decisions
docs/01-human-memory/     Cognitive psychology and neuroscience
docs/02-llm-memory/       LLM and agent memory mechanisms
docs/03-human-ai-bridge/  Testable mappings and invalid analogies
docs/04-systems/          Open-source systems and architecture comparisons
docs/05-benchmarks/       Benchmark coverage, flaws, and evaluation design
docs/06-datasets/         Training and evaluation data
docs/07-literature/       Reading queues, bibliography, evidence ledger
docs/08-experiments/      Experiment specifications (no implementation yet)
docs/09-synthesis/        Findings, open questions, exclusions
data/catalogs/            Machine-readable paper and repository catalogs
data/snapshots/           Reproducible discovery outputs (normally ignored)
external/repos/           Local shallow clones (ignored by Git)
sources/papers/           Local paper PDFs (ignored by Git)
scripts/                  Reproducible discovery and download helpers
```

## Current phase

The project is in **Phase 0: evidence collection and conceptual falsification**. We are deliberately postponing implementation until the memory lifecycle, evaluation targets, and baseline comparisons are sufficiently clear.

## Working language

Repository content is written in English so that contributors can collaborate internationally. Issues and discussions may use any language, but durable findings should be summarized in English.

## License

Original repository content is released under the [Creative Commons Attribution 4.0 International License](LICENSE). External repositories, datasets, and papers retain their own licenses and are not redistributed here.
