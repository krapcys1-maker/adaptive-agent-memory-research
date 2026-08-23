# Brain-to-AI Memory Transfer Atlas

Status: active research track; functional analogies and falsifiable transfers only

## Purpose

This track asks a disciplined question:

> Which computational problems solved by biological memory systems have already been addressed in machine learning or LLM agents, which apparent matches are only metaphors, and which unresolved functions deserve controlled experiments in a local-first agent memory?

The project had already studied complementary stores, replay, salience, reconsolidation, interference, active forgetting, metamemory, prospective memory, compression, and comparative biology. What was missing was a single mechanism-level atlas connecting all five evidence layers:

```text
biological observation
        -> computational function
        -> formal or ML implementation
        -> LLM-agent implementation
        -> benchmark and falsification status
```

`atlas-v0.csv` supplies that missing structure. It begins with 38 mechanisms. A row is a research object, not an architecture recommendation.

## Core rule

Transfer the **function and constraints**, not the anatomical name.

Bad transfer:

```text
dopamine -> dopamine_score
hippocampus -> vector database
sleep -> nightly summarization
```

Admissible transfer:

```text
biological result: unexpected consequential outcomes can alter later retention
computational problem: allocate limited consolidation/retrieval resources
candidate mechanism: typed prediction-error and consequence signals
falsification: compare against relevance, recency, random, and oracle controls
```

## Artifacts

- `atlas-v0.csv` — machine-readable mechanism transfer map.
- `research-protocol.md` — discovery, evidence, implementation, and rejection procedure.
- `gap-analysis-v0.md` — what is already common, partially implemented, missing, or misleading.
- `source-and-system-seeds.md` — primary biological anchors, AI papers, repositories, and benchmark leads.
- `benchmark-portfolio-v0.md` — cross-mechanism experimental matrix and success rules.
- `repository-initial-audit-v0.md` — pinned code/benchmark inspection, mismatches, licenses, and blockers.

## Evidence boundary

The atlas distinguishes:

- a biological effect;
- a computational model of that effect;
- an ML system inspired by the model;
- an LLM-agent component using similar language;
- evidence that the component solves the same problem.

Similarity of vocabulary never advances a row. An implementation only counts when its operations and evaluation can be inspected. Biological plausibility never substitutes for a simpler engineering baseline.

## Current high-value gaps

The initial audit identifies these as especially under-tested in LLM agents:

1. pattern separation measured against false merging, not only recall;
2. prospective memory with external condition-action triggers and stale-intention safety;
3. source/reality monitoring that separates observed, inferred, simulated, and model-generated memories;
4. bundle-aware selective replay with poison and negative-transfer controls;
5. reconsolidation as evidence-bearing versioned revision rather than overwrite;
6. schema formation that preserves exceptions and provenance;
7. implicit/procedural transfer measured by first action rather than factual recall;
8. multi-timescale retention without irreversible deletion;
9. preplay/prospective simulation kept separate from factual episodic memory;
10. a controller that learns `store/retrieve/replay/consolidate/archive/ask/abstain` without conflating reward association with causal utility.

## Non-goals

- claiming that LLMs have human memory or emotion;
- assigning brain regions one-to-one to software modules;
- modifying model weights in the first laboratory phase;
- treating a new metaphor as novelty;
- promoting a mechanism before it beats a simpler provider-neutral baseline;
- using natural private user histories before the separate privacy and lifecycle gates close.
