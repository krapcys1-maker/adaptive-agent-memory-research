# Comparative Memory Systems Lab

A track, not a survey. The question is never *which system is best* — it is
**which mechanism resolves which failure mode, and why.**

Five systems solving overlapping problems by different routes are five
experiments already run by other people. Reading them as systems produces a
feature table. Reading them as mechanisms produces a map of the design space,
and the map is the part nobody has drawn.

## Why this is a research track and not homework

`CANDIDATE-0` reached 1.000 internally and its entity resolution does not fire
on external questions. Hindsight describes that exact capability as a solved
feature. Reading their mechanism is not a detour from the research; the research
question *is* where deterministic structure stops sufficing, and someone else's
model/heuristic boundary is a measured answer to it arrived at independently.

## The sheet, one per system

Filled from code, never from a README. Claimed and verified stay separate, as in
[`memeval-repository-audit-v0.md`](memeval-repository-audit-v0.md).

| Field | What it must answer |
|---|---|
| mechanism | what it actually does, in one sentence |
| assumption | what must be true about the data for it to work |
| what it solves | which failure mode, named |
| what it costs | calls, tokens, latency, storage |
| where it fails | stated by them, or found by us |
| dependence on a model | which decisions call one, which do not |
| dependence on an ontology | must a schema be supplied, learned, or neither |
| temporal model | validity, supersession, invalidation, or none |
| provenance | is the raw record kept, and can an answer be traced |
| context cost | tokens delivered per query |
| failure profile | the vector, never a single accuracy |

## Three comparisons worth more than a ranking

### 1. Analogy — different names, one principle

```
Graphiti          edge invalidation
A-TMA / CUPMem    current / historical / transition
AAMR              succession / correction chain
```

If those are the same mechanism wearing three vocabularies, the shared principle
— *not every stored fact is simultaneously true* — is a finding about memory
rather than about any system. If they differ in a case that matters, the
difference is the finding.

### 2. Difference — same output, different question

```
dense retrieval   find a record similar to this text
addressing        find the state of this object
```

Both return records. `PMLAB-H1-DENSE-E1` measured what separates them: 48
near-identical records buried the gold for both retrievers, and the two failed
on *opposite* families — all nine lexical-only wins were RARE-EXC, all four
dense-only wins were OBSOLETE.

### 3. Transplant — is a gain additive?

```
BASE + temporal            +6
BASE + addressing          +8
BASE + both               +14   complementary
                           +8   redundant, two routes to one problem
                          +17   synergistic, and the interesting case
```

**A transplant is void unless every arm runs on one harness.** If Graphiti runs
under its own and AAMR under ours, the two deltas are not on the same scale and
adding them means nothing. `ProsusAI/MemEval` holds model, embedder, scoring and
decoding constant across systems and is the candidate — audited in
[`memeval-repository-audit-v0.md`](memeval-repository-audit-v0.md), with the
caveat recorded there that its constants are repeated per adapter rather than
enforced by the registry.

`scripts/compare_corpus_h1_arms.py` already refuses to tabulate arms that did not
share a budget, reader and probe count. The same guard applies here and is the
reason a transplant table can be trusted at all.

## The measurement this project is unusually equipped for

Per question, per system:

```
Graphiti   ✓     Hindsight  ✗     CUPMem  ✓     AAMR  ✗
failure type: entity | property | retrieval | stale | conflict |
              future validity | reasoning | abstention
```

`scripts/measure_reviewer_decorrelation.py` already computes phi over binary
error vectors and **correctly returns undefined rather than 0.0 when a vector is
constant**. It was built for `PMLAB-DECORR-E1`, which could not run: two roles of
one model family fabricated zero times across 120 queries, so both error vectors
were constant and the correlation did not exist.

Four or five architecturally distinct systems will not produce constant error
vectors. **The harness that had nothing to measure finally has something**, and
tier I3 — a genuinely cross-family panel with measured error correlation —
becomes instantiable for the first time.

That connection was not planned. It is worth stating plainly because it means
this track unblocks a tier the independence ladder has carried as a label since
it was written.

## What a result could look like

Not a new framework. A principle, if the correlations support one:

> No single mechanism is optimal. The *kind* of information determines the
> representation and the access method.

```
exact operational detail    lexical
current structured state    address
conceptual experience       semantic
state history               temporal chain
conflict                    resolver or abstention
repeated experience         consolidation
long-term usefulness        adaptive retention
```

If that holds, the contribution is a controller that classifies a query's
requirement and routes it — and the evidence for it is the failure-correlation
map, not an accuracy table.

**And it may not hold.** The correlations may show the mechanisms are largely
redundant, in which case the honest finding is that the design space is smaller
than it looks and most of these systems are one system. That would be worth
publishing too.

## Order

1. **Hindsight** — entity resolution first, because that is the component
   `CANDIDATE-0` measurably fails at. Issue #50.
2. **Graphiti** — the temporal model, narrowly: `valid_from`, `valid_to`,
   `invalidated_at`, provenance.
3. **CUPMem** — already in the STALE repository, so it is the cheapest baseline
   available and needs no reimplementation.
4. **APEX-MEM** — ontology and property resolution; what is agentic and what is
   deterministic.
5. **Mem0** — lexical, semantic and entity fusion, and the cost of extraction.

Licence and attribution recorded before anything is borrowed. A negative reading
closes an entry: *their resolver is one large model call per event and costs more
than the problem is worth* is a complete answer.
