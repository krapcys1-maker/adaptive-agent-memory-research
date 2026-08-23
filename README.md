<h1 align="center">Can an agent learn what is worth remembering?</h1>

<p align="center">
A local-first, model-agnostic memory system that decides what to keep from<br>
<b>the measured future usefulness of past experience</b> — not from what looks similar to your query.
</p>

<p align="center">
<a href="https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/workflows/ci.yml"><img src="https://github.com/krapcys1-maker/adaptive-agent-memory-research/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg" alt="License: CC BY 4.0"></a>
<img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No dependencies">
<img src="https://img.shields.io/badge/API%20key-not%20required-blue" alt="No API key">
<a href="https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/good%20first%20issue"><img src="https://img.shields.io/github/issues/krapcys1-maker/adaptive-agent-memory-research/good%20first%20issue?label=good%20first%20issues&color=7057ff" alt="Good first issues"></a>
</p>

---

## Give Claude Code persistent project memory in two minutes

The memory engine this research is built on is dependency-free, offline, and works today on **your** project. Point any MCP client at it:

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research ~/aamr
claude mcp add project-memory -- python ~/aamr/tools/project_memory/server.py --root .
```

Your agent now has eight tools — `memory_status`, `memory_search`, `memory_context`, `memory_get`, `memory_timeline`, `memory_add`, `memory_supersede`, `memory_rebuild_index` — writing to a single append-only `memory/events.jsonl` in your repository. No API key, no vector database, no daemon, no cloud account, no `pip install`.

Prefer no MCP client? Everything works from the CLI:

```bash
python tools/project_memory/cli.py add --kind decision \
  --title "Use SQLite for the cache" \
  --summary "Chose SQLite over Redis because the deployment target has no daemon." \
  --source docs/adr/0003.md
python tools/project_memory/cli.py search "why sqlite"
```

> **This is the research engine, not a finished product.** It is used daily by this project on itself, which is the strongest thing we can honestly say about it. Bugs, rough edges, and honest reports of both are welcome — see [#36](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/36) if setup fights you.

---

## The problem

An agent's context window is a workspace, not a memory. Once a conversation is compacted, whatever was dropped is gone — including the thing that turns out to matter three weeks later.

The usual answer is to embed everything and retrieve by similarity. That answers *what looks like this query*, which is not the same question as *what will this agent need*. Those two come apart badly, and this project exists to measure exactly where.

## The idea

Two stores, not one. A fast, evidence-preserving episodic log that learns from single experiences, and a slower semantic or procedural store that consolidates what recurs. What moves between them is governed by **measured future utility** rather than by semantic similarity or retrieval frequency.

```text
                 experience
                     │
                     ▼
        ┌────────────────────────┐
        │   append-only log      │   immutable evidence, never rewritten
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │   memory controller    │   write · preserve · consolidate · revise · archive
        └────────────┬───────────┘
                     ▼
    ┌──────────┬───────────┬────────────┬──────────┐
    │ episodic │ semantic  │ procedural │ failure  │
    └──────────┴─────┬─────┴────────────┴──────────┘
                     ▼
        ┌────────────────────────┐
        │  measured future use   │   ◄── the part that is actually research
        └────────────┬───────────┘
                     ▼
                 retrieval ──────────► agent
```

The append-only log, the controller and retrieval are built and running — that is what the two-minute setup above gives you. The box marked *the part that is actually research* is the open question, and the four stores below the controller are a design rather than a measured decomposition. This diagram is the hypothesis, not a claim about what works.

## What we have measured

Of 71 registered experiments, **37 have run** and 20 are blocked on a corpus that does not exist yet. All are exploratory and none is independently reviewed, so read these as measurements rather than settled science — but they are measurements, and the data is in the repository.

**A superseded fact is maximally similar to the fact that replaced it.** Mean cosine 0.816 between an old fact and its replacement, against a corpus baseline of 0.372 — one pair at 1.000. With the metadata filter removed, the stale version was the nearest neighbour in 6 of 9 cases and its median rank was 1. *Content cannot separate a retired fact from its successor. Only bookkeeping can.* → `PMLAB-STALE-E1`

**One timestamp cannot answer "what did we believe at time T".** It scored 0.00 on that question and leaked future information into 6 of 18 queries. Separating valid time from transaction time scored 0.944 with zero leaks. The caveat matters as much as the result: every design scored 1.00 on *what is true now*, so the second axis buys nothing unless historical questions get asked. → `PMLAB-REV-V0`

**A 220 MB local multilingual embedder lifted Polish-query recall@10 from 0.156 to 0.978** — and pulled in four times as much superseded material doing it (0.200 forbidden intrusion against 0.050 for lexical search). Recall solved; safety unmeasured. → `PMLAB-XLANG-E2`

**An association graph over memory made retrieval worse.** The earlier, favourable version of this result was **retracted by us**: its leakage control removed one edge where it needed to remove 4.5, so the gold-generating group reassembled over two hops. → `PMLAB-ASSOC-E2` retracted, `PMLAB-ASSOC-E3`

**A benchmark can score perfect recall and still hand the agent the wrong answer.** On the new corpus, the poisoned-instruction family scores **1.000 recall@10** — and retrieves the poisoned line *above* the genuine rule in **25%** of probes. A system retrieving both records looks flawless on recall and would act on the wrong one. This is one lexical arm on one synthetic corpus, so it is evidence about what recall hides rather than a claim about memory systems in general. → `PMLAB-H1-BASE-E1`

**We cannot currently instantiate tier I3 of our own independence ladder.** Two roles of one model fabricated an evidence identifier zero times across 120 queries, so the error correlation is *undefined* rather than zero — and the harness reports undefined, because 0.0 would claim an independence nobody measured. → `PMLAB-DECORR-E1`

Four of those six are negatives and one is a retraction of our own work. **That ratio is the honest one at this stage**, and it is the thing this project is most willing to defend.

### The number that is not here yet

There is no headline benchmark table on this page, and there will not be one until it is earned. The comparison that matters — adaptive memory against native compaction and against vector retrieval, at a fixed context budget, on a long history — needs a corpus and a reader model.

The corpus now exists: [corpus H1](data/lab/corpus-h1/README.md), 538 events over 30 simulated days, 84 delayed probes across seven failure families, generated deterministically with no model and no API key. Its first run found a defect *in the corpus* — document length predicted the answer in 12 of 12 instances of three families — which is exactly what the construction-test tier is for. Both the broken and the repaired measurement are published.

What is still missing is the reader model that scores whether an arm could answer from what it retained, and the compaction arms themselves. That is [#41](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/41), still open, still the highest-leverage task.

We have pre-committed to publishing that result whichever way it falls. Given that three separate runs here have already measured our own mechanisms *harming* retrieval, a negative headline is a live possibility — and it would be published in the same font as a positive one.

## Try the research, not just the tool

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research
cd adaptive-agent-memory-research
python -m pip install -r requirements-dev.txt
```

Inspect the memory this project keeps about its own research, and watch it assemble a context bundle under a hard character budget:

```bash
python tools/project_memory/cli.py status
python tools/project_memory/cli.py context "what is blocking independent review" --char-budget 4000
```

Check that the append-only log satisfies every invariant decidable from its bytes — no model, no network, no reviewer:

```bash
python scripts/verify_memory_integrity.py
```

Audit the whole repository for claims that no longer hold:

```bash
python scripts/audit_repository_claims.py
```

That last one reports 34 findings. None is a broken freeze — 243 of the 246 resolvable declared hashes match their working copy, and the other three are derived digests declared under a name that reads like a file digest. What it does report is 17 registry rows pointing at artifacts for experiments that have not run, and 12 experiment identifiers described in documentation but absent from the registry. Tracked in the issue list, not hidden.

## How to help

Contributions run at three depths, and **you do not need a background in memory research for the first one.**

### About an hour, no research background

Issues labelled [`good first issue`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/good%20first%20issue) and [`no-expertise-needed`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/no-expertise-needed) are ordinary software work: a scoped bug, a missing exclusion rule, a CLI subcommand, reading one unfamiliar repository carefully. Each states what "done" means before you start.

If the setup instructions above fail on your machine, saying so in an issue is itself a useful contribution — this is developed on Windows and tested on Linux, and that gap has already produced one real defect.

**A negative result closes an issue here.** If you inspect something and find it is not what we assumed, write that down and you are done. Several of the findings above are exactly that.

### A few sessions, engineering

Issues labelled [`track:engine`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/track%3Aengine) build the machinery the research needs: sealed held-out splits, error-decorrelation measurement, the bitemporal query layer, cost-normalised retrieval metrics. These need care but not domain expertise.

**Finding a hole in our method is worth more than completing a task.** The sealed-split tool carries three guards, each added after the corresponding attack was reproduced against it. A fourth would be the better contribution.

### Research review

Issues labelled [`independent-review`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/independent-review) need someone who can judge evidence. Read [the independence ladder](docs/00-project/independence-ladder.md) first — it explains why a large share of what once required an expert reviewer is now a mechanical check, and what genuinely still needs human judgement.

Everything goes through [CONTRIBUTING.md](CONTRIBUTING.md). Disagreement with a recorded conclusion is welcome; that is what the evidence ledger is for. Say hello in [Discussions](https://github.com/krapcys1-maker/adaptive-agent-memory-research/discussions).

## What we will not trade away

- User data stays local by default.
- The system must be model-agnostic.
- Raw evidence is append-only during early research.
- Experimental forgetting must never destroy the only copy of a memory.
- Every derived memory preserves provenance.
- Facts, hypotheses, decisions, preferences, and instructions are never conflated.
- A retrieved memory is not automatically a useful memory.
- Every added mechanism justifies itself in controlled evaluation.

## Prior art, and what is actually open

Two 2026 systems were verified in August 2026 and both occupy ground this page had been treating as open.

[APEX-MEM](https://arxiv.org/abs/2604.14362) (ACL 2026, Amazon) implements entity-property-value triplets over an append-only store with query-time temporal resolution — the architecture this project converged on independently — at 88.88% LoCoMo and 86.2% LongMemEval. **Structured temporal memory is not a novel claim here and is not made as one.**

[Verbatim Chunks Beat Extracted Artifacts](https://arxiv.org/html/2601.00821) finds extraction *losing* to raw chunks by 15.9 points on LoCoMo, with extraction gaps at 78.8% of failures. This project independently measured 85.7% abstention from a deterministic extractor — the same phenomenon, and a reason to take that paper's conclusion seriously rather than route around it.

A-MAC and NEMORI reportedly occupy *future utility as a retention criterion*, which question 3 below states as open. That is being verified in [#48](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/48); until it resolves, read question 3 as **possibly closed**.

What still looks unoccupied is not a system but a diagnostic programme: *when and why similarity stops being the right access mechanism*, measured through failure attribution, an oracle router ceiling, near-clone density and context cost. Full assessment in [related work and novelty](docs/00-project/related-work-and-novelty.md), including the process failure that let this be found late.

## The five research questions

> Does an agent need complementary memory systems — an evidence-preserving episodic store for rapid learning from single experiences, and a slower semantic or procedural store that consolidates recurring evidence? And should transitions between them be governed by **measured future utility** rather than by semantic similarity?

1. What is the atomic unit of agent memory: message, event, fact, relation, episode, procedure, or decision?
2. How can storage failure be distinguished from retrieval failure and from reasoning failure?
3. How can future utility be measured causally rather than inferred from retrieval frequency?
4. When should exact episodes be consolidated into semantic or procedural knowledge?
5. How can memories be updated without losing provenance, uncertainty, or superseded historical states?

## Current phase

Evidence collection alongside gated laboratory testing. Each falsifiable hypothesis may enter an exploratory test under the [research-to-experiment gate](docs/11-research-laboratory/research-to-experiment-gate.md); confirmatory claims, added architecture, and any product implementation remain blocked behind stricter benchmark, reproduction, safety, and review gates.

Work runs in three tracks — engine, experiment, community — with milestones **M1 Engine**, **M2 Execute**, **M3 Independence**. New preregistrations are paused until the existing unexecuted drafts are triaged, because the project was designing protocols faster than it could run them.

Both defects this section used to list as open are now closed, and how they closed is more interesting than that they did. Frozen hashes were reproducible only on a Windows checkout because Git's end-of-line conversion made 843 of 1348 files under `data/` differ byte for byte across platforms; `.gitattributes` now disables conversion repository-wide. Six frozen artifacts had been modified after freezing, by two distinct causes rather than one. CI verifies freezes on Linux with full history, so the check cannot pass vacuously.

---

<details>
<summary><b>Deep research — the full repository</b></summary>

### Reading path

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

### Repository layout

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

</details>

## Working language

Repository content is written in English so contributors can collaborate internationally. Issues and discussions may use any language; durable findings are summarised in English.

## License

Original content is released under [CC BY 4.0](LICENSE). External repositories, datasets, and papers keep their own licenses and are not redistributed here.
