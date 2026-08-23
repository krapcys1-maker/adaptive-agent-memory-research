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

That last one currently reports 34 findings. None of them is a broken freeze — 243 of the 246 resolvable declared hashes match their working copy, and the remaining three are derived digests declared under a name that reads like a file digest. What it does report is 17 registry rows pointing at artifacts for experiments that have not run, and 12 experiment identifiers described in documentation but absent from the registry. Both are tracked in the issue list rather than hidden.

## What we are trying to find out

> Does an agent need complementary memory systems — an evidence-preserving episodic store for rapid learning from single experiences, and a slower semantic or procedural store that consolidates recurring evidence? And should transitions between them be governed by **measured future utility** rather than by semantic similarity?

Five questions organise the work:

1. What is the atomic unit of agent memory: message, event, fact, relation, episode, procedure, or decision?
2. How can storage failure be distinguished from retrieval failure and from reasoning failure?
3. How can future utility be measured causally rather than inferred from retrieval frequency?
4. When should exact episodes be consolidated into semantic or procedural knowledge?
5. How can memories be updated without losing provenance, uncertainty, or superseded historical states?

## What we have found so far

Of 71 registered experiments, 37 have run and 20 are blocked on corpora that need a reader model. All are exploratory and none is independently reviewed, so read what follows as measurements rather than settled science — but they are measurements, and the data is in the repository.

**A superseded fact is maximally similar to its replacement.** Across nine supersession pairs the mean cosine between an old fact and the fact that replaced it was 0.816 against a corpus baseline of 0.372, with one pair at 1.000. With the metadata filter removed, the stale version was the nearest neighbour in 6 of 9 cases and its median rank was 1. Content cannot separate a retired fact from its successor — only bookkeeping can. `PMLAB-STALE-E1`

**Two time axes are needed, and each single-axis design fails exactly the question the other answers.** A resolver with one timestamp scored 0.00 on *what did we believe at time T*, leaking future information on 6 of 18 queries. A bitemporal one scored 0.944 overall with zero leaks. The caveat matters as much as the result: every arm scored 1.00 on *what is true now*, so the second axis buys nothing unless historical questions get asked. `PMLAB-REV-V0`

**A local 220 MB multilingual embedder lifted Polish-query recall@10 from 0.156 to 0.978** — and pulled in four times as much superseded material doing it (0.200 forbidden intrusion against 0.050 for lexical search). Recall was solved; safety was not measured. `PMLAB-XLANG-E2`

**An association graph over memory made retrieval worse once the leak was closed.** The first version of this measurement was retracted by us: its leakage control removed only the direct edge between a held-out pair, so the gold-generating group reassembled over two hops. The corrected control removes 4.5 edges per pair instead of 1, and with it the graph harms the lexical baseline it was meant to help. `PMLAB-ASSOC-E2` retracted, `PMLAB-ASSOC-E3`

**Tier I3 of our own independence ladder cannot currently be instantiated.** Two roles of one model over 120 queries fabricated an evidence identifier exactly zero times, so both error vectors are constant and their correlation is undefined rather than zero. The harness reports it as undefined, because 0.0 would claim an independence nobody measured. `PMLAB-DECORR-E1`

Negative and retracted results are kept here on the same footing as positive ones. Three of the five above are negatives, one is a retraction of our own work, and that ratio is the honest one for this stage.

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

Issues labelled [`good first issue`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/good%20first%20issue) and [`no-expertise-needed`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/no-expertise-needed) are ordinary software work: a scoped bug, a missing exclusion rule, a CLI subcommand, reading one unfamiliar repository carefully. Each states what "done" means before you start.

If the setup instructions above fail on your machine, saying so in an issue is itself a useful contribution — this is developed on Windows and tested on Linux, and that gap has already produced one real defect.

**A negative result closes an issue here.** If you inspect something and find it is not what we assumed, write that down and the issue is done. Several of the findings above are exactly that.

### A few sessions, engineering

Issues labelled [`track:engine`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/track%3Aengine) build the machinery the research needs: sealed held-out splits, error-decorrelation measurement, the association layer, the bitemporal schema. These need care but not domain expertise.

### Research review

Issues labelled [`independent-review`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/independent-review) need someone who can judge evidence. Read [the independence ladder](docs/00-project/independence-ladder.md) first — it explains why a large share of what once required an expert reviewer is now a mechanical check, and what genuinely still needs human judgement.

Everything goes through [CONTRIBUTING.md](CONTRIBUTING.md). Disagreement with a recorded conclusion is welcome; that is what the evidence ledger is for.

## Reading path

New contributors do not need all of this. Read the first three, then follow whatever your issue touches.

1. [Start here](START_HERE.md) — the shape of the problem
2. [Operating doctrine](docs/00-project/operating-doctrine.md) — what we test next, and why that one
3. [Bootstrapping strategy](docs/00-project/bootstrapping-strategy.md) — why the tool is also the corpus, and what that costs
4. [Independence ladder](docs/00-project/independence-ladder.md) — how a claim earns promotion
5. [Repository map](docs/00-project/REPOSITORY_MAP.md) — where everything lives
6. [Scope](docs/00-project/scope.md) and [definitions](docs/00-project/definitions.md)
7. [Research plan](RESEARCH_PLAN.md) and [research questions](docs/00-project/research-questions.md)
8. [Human memory](docs/01-human-memory/README.md) · [LLM memory](docs/02-llm-memory/README.md) · [mapping between them](docs/03-human-ai-bridge/mapping.md)
9. [Systems catalog](docs/04-systems/catalog.md) · [benchmark catalog](docs/05-benchmarks/catalog.md)
10. [Research laboratory](docs/11-research-laboratory/README.md) and the [experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md)

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

Both defects this section used to list as open are now closed, and how they closed is more interesting than that they did. Frozen hashes were reproducible only on a Windows checkout because Git's end-of-line conversion made 843 of 1348 files under `data/` differ byte for byte across platforms; `.gitattributes` now disables conversion repository-wide. Six frozen artifacts had been modified after freezing, by two distinct causes rather than one. CI verifies freezes on Linux with full history, so the check cannot pass vacuously.

## Working language

Repository content is written in English so contributors can collaborate internationally. Issues and discussions may use any language; durable findings are summarised in English.

## License

Original content is released under [CC BY 4.0](LICENSE). External repositories, datasets, and papers keep their own licenses and are not redistributed here.
