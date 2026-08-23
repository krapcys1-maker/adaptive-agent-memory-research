# Adaptive Agent Memory Research

[![CI](https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/workflows/ci.yml/badge.svg)](https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/workflows/ci.yml)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](LICENSE)

An open research workspace for **local-first, model-agnostic, long-term memory for LLM agents**.

The context window stays the agent's immediate workspace. Durable memory lives on the user's disk, and a controller decides what to write, preserve, consolidate, retrieve, revise, and archive. No model API key, vector database, or cloud account is required for anything in this repository.

This is a **research project, not a production memory library**. What it offers is not a product but a method: every claim carries provenance, negative results are preserved rather than deleted, and mechanisms advance through registered gates instead of plausibility.

## Try it in two minutes

The repository ships a dependency-free project memory that this research uses on itself. You can run all of it locally, offline:

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research
cd adaptive-agent-memory-research
python -m pip install -r requirements-dev.txt
```

Inspect the memory the project keeps about its own research:

```bash
python tools/project_memory/cli.py status
```

Ask it something and watch it assemble a context bundle under a character budget:

```bash
python tools/project_memory/cli.py context "what is blocking independent review" --char-budget 4000
```

Check that the append-only log satisfies every invariant that is decidable from its bytes — no model, no network, no reviewer:

```bash
python scripts/verify_memory_integrity.py
```

Audit the whole repository for claims that no longer hold:

```bash
python scripts/audit_repository_claims.py
```

That last one currently reports real problems. They are tracked in the issue list, not hidden.

## What we are trying to find out

> Does an agent need complementary memory systems — an evidence-preserving episodic store for rapid learning from single experiences, and a slower semantic or procedural store that consolidates recurring evidence? And should transitions between them be governed by **measured future utility** rather than by semantic similarity?

Five questions organise the work:

1. What is the atomic unit of agent memory: message, event, fact, relation, episode, procedure, or decision?
2. How can storage failure be distinguished from retrieval failure and from reasoning failure?
3. How can future utility be measured causally rather than inferred from retrieval frequency?
4. When should exact episodes be consolidated into semantic or procedural knowledge?
5. How can memories be updated without losing provenance, uncertainty, or superseded historical states?

## Non-negotiable constraints

- User data stays local by default.
- The system must be model-agnostic.
- Raw evidence is append-only during early research.
- Experimental forgetting must never destroy the only copy of a memory.
- Every derived memory preserves provenance.
- Facts, hypotheses, decisions, preferences, and instructions are never conflated.
- A retrieved memory is not automatically a useful memory.
- Every added mechanism justifies itself in controlled evaluation.

## How to help

Contributions run at three depths. **You do not need a background in memory research for the first one.**

### About an hour, no research background

Issues labelled [`good first issue`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/good%20first%20issue) and [`no-expertise-needed`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/no-expertise-needed) are ordinary software work: a scoped bug, a missing exclusion rule, a CLI subcommand. Each states what "done" means. If the setup instructions above fail on your machine, saying so in an issue is itself a useful contribution.

### A few sessions, engineering

Issues labelled [`track:engine`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/track%3Aengine) build the machinery the research needs: sealed held-out splits, error-decorrelation measurement, the association layer, the bitemporal schema. These need care but not domain expertise.

### Research review

Issues labelled [`independent-review`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/independent-review) need someone who can judge evidence. Read [the independence ladder](docs/00-project/independence-ladder.md) first — it explains why a large share of what once required an expert reviewer is now a mechanical check, and what genuinely still needs human judgement.

Everything goes through [CONTRIBUTING.md](CONTRIBUTING.md). Disagreement with a recorded conclusion is welcome; that is what the evidence ledger is for.

## Reading path

New contributors do not need all of this. Read the first three, then follow whatever your issue touches.

1. [Start here](START_HERE.md) — the shape of the problem
2. [Operating doctrine](docs/00-project/operating-doctrine.md) — what we test next, and why that one
3. [Independence ladder](docs/00-project/independence-ladder.md) — how a claim earns promotion
4. [Repository map](docs/00-project/REPOSITORY_MAP.md) — where everything lives
5. [Scope](docs/00-project/scope.md) and [definitions](docs/00-project/definitions.md)
6. [Research plan](RESEARCH_PLAN.md) and [research questions](docs/00-project/research-questions.md)
7. [Human memory](docs/01-human-memory/README.md) · [LLM memory](docs/02-llm-memory/README.md) · [mapping between them](docs/03-human-ai-bridge/mapping.md)
8. [Systems catalog](docs/04-systems/catalog.md) · [benchmark catalog](docs/05-benchmarks/catalog.md)
9. [Research laboratory](docs/11-research-laboratory/README.md) and the [experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md)

## Repository layout

```text
docs/00-project/          Scope, definitions, methodology, independence ladder, decisions
docs/01-human-memory/     Cognitive psychology and neuroscience
docs/02-llm-memory/       LLM and agent memory mechanisms
docs/03-human-ai-bridge/  Testable mappings and invalid analogies
docs/04-systems/          Open-source systems and architecture comparisons
docs/05-benchmarks/       Benchmark coverage, flaws, and evaluation design
docs/06-datasets/         Training and evaluation data
docs/07-literature/       Reading queues, bibliography, evidence ledger
docs/08-experiments/      Experiment specifications
docs/09-synthesis/        Findings, open questions, exclusions
docs/10-comparative-biological-memory/  Animal, motor, immune, cellular, collective memory
docs/11-research-laboratory/            Protocols, benchmark ladder, gates, architecture boundary
docs/12-interdisciplinary-memory/       Compression, storage, control, offloading synthesis
docs/13-brain-ai-transfer/              Brain-to-AI mechanism atlas and transfer gaps
data/catalogs/            Machine-readable paper and repository catalogs
data/lab/                 Experiment registry, corpora, frozen runs, results
scripts/                  Experiment runners, audits, discovery helpers
tests/                    Test suite; runs on every pull request
memory/                   Append-only project memory and its generated index
tools/project_memory/     Dependency-free CLI and MCP memory adapter
```

## Current phase

Evidence collection alongside gated laboratory testing. Each falsifiable hypothesis may enter an exploratory test under the [research-to-experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md); confirmatory claims, added architecture, and any product implementation remain blocked behind stricter benchmark, reproduction, safety, and review gates.

Work is organised in three parallel tracks — engine, experiment, and community — with milestones **M1 Engine**, **M2 Execute**, and **M3 Independence**. New preregistrations are paused until the existing unexecuted drafts are triaged, because the project was designing protocols faster than it could run them.

Two things are openly broken and tracked rather than quietly fixed: some frozen provenance hashes are reproducible only on a Windows checkout, and six frozen artifacts were modified after freezing. Both are in the issue list with the evidence attached.

## Working language

Repository content is written in English so contributors can collaborate internationally. Issues and discussions may use any language; durable findings are summarised in English.

## License

Original content is released under [CC BY 4.0](LICENSE). External repositories, datasets, and papers keep their own licenses and are not redistributed here.
