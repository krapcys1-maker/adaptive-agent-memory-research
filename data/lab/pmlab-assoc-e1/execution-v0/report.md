# PMLAB-ASSOC-E1 — association graph over project memory

Experiment ID: `PMLAB-ASSOC-E1`
Tier: **E (exploratory)** — model-free, no network, no API cost
Authority: development measurement only. Not confirmatory, not independently reviewed, cannot select an architecture.

## Why this exists

The project's own memory was measured as 89.1% fully disconnected: 165 events, 10 edges. But 57 `source_refs` were shared by more than one event, so an association structure was already latent in the data and had simply never been materialized.

This is also the first experiment run under the Tier E rule: cheap, immediate, on real data, with no independence gate, explicitly labelled non-confirmatory. It exists to break a pattern where 21 preregistered protocols were never executed because each was designed to publication standard before running once.

## Materialization result

| | Before | After |
|---|---|---|
| Edges | 10 | **102** |
| Nodes with at least one edge | ~11% | **58.6%** |
| Mean degree | 0.02 | 2.1 |

169 active events, 57 shared source references, max degree 6.

## Question

Two events citing the same source are related by construction. Does one hop over that graph recover related memories that lexical search alone misses?

## Design

Gold is derived mechanically and never authored. Each `shares_source` edge is a known-related pair. Edges are split into five deterministic folds by SHA-256 of the pair, so every edge is held out exactly once and the split is reproducible without a stored seed.

For a held-out edge (A, B) the graph is rebuilt from the other four folds only. **The direct A–B link is therefore absent**, so the graph can only help through transitivity — A shares a source with C, C shares a different source with B. Each edge is evaluated in both directions, giving 204 queries from 102 edges.

- **B1** lexical only: FTS5 over active memory events, query is A's title plus summary, A excluded from its own results.
- **B2** lexical plus graph, fused by reciprocal rank fusion at k=60, matching the project's already-registered choice of equal-input RRF as the first hybrid.

Both arms return the same number of candidates, so B2 buys graph positions by surrendering lexical ones.

## Results

| Metric | B1 lexical | B2 lexical + graph | Paired difference | 95% CI |
|---|---|---|---|---|
| Recall@5 | 0.3824 | 0.4069 | **+0.0245** | **[−0.0343, +0.0833]** |
| Recall@10 | 0.5196 | 0.5588 | **+0.0392** | **[−0.0098, +0.0882]** |

- 2-hop reachability ceiling: **0.2206**. Only 22% of queries have their target reachable through the graph at all, which bounds any possible graph gain.
- Mean lexical positions displaced at depth 10: **1.76**.
- 10,000 paired bootstrap resamples.

## Interpretation

**The result is inconclusive, and that is the finding.** Both confidence intervals include zero. The direction is positive in both, and at depth 10 the interval only barely crosses zero, but nothing here supports a claim that the graph helps.

Three things are worth separating:

1. **The graph does convert some of its opportunities.** The ceiling is 0.221 and the observed gain is 0.039 at depth 10, so roughly one in five reachable targets became a recall gain. The mechanism is not inert.
2. **The sample is too small to resolve it.** 102 edges over 169 events. A difference of four percentage points on 204 paired queries is not separable from noise at this size.
3. **Displacement is real.** B2 gives up 1.76 lexical positions per query on average. On this data that cost was roughly repaid; on data where lexical search is stronger it might not be.

The honest summary is that materializing the graph was clearly worthwhile as *structure* — 10 edges to 102, isolation from 89% to 41% — while its *retrieval* benefit remains unproven.

## Reproducibility

Two fresh processes reproduced records digest `a5ea57f382aa6d5373fff1890c3a67702541956e1712d4f0105d7c26711b4d02` byte-identically.

One caveat is recorded rather than explained away. An earlier run of an earlier revision of the script produced a different digest, `4bc3525478e2fd4d`. The obvious hypothesis was that FTS5 BM25 uses global corpus statistics, so unrelated documents in the same index would perturb memory ranking. **That hypothesis was tested and refuted**: adding a large unrelated document to the indexed tree, rebuilding, and re-running produced an identical digest. The cause of the original difference was not established and is not asserted here.

## What this does not show

- No architecture claim. RRF at k=60 was chosen because it was already registered, not because it was compared against alternatives.
- No cross-language claim. That was the original motivation for a graph, since FTS5 showed zero cross-language recall, but this corpus is predominantly English and does not test it.
- No safety claim. Memory events carry no trust or forbidden labels, so the forbidden-intrusion metric used elsewhere in the project has no analogue here.
- Gold is `shares_source` co-citation, which is a proxy for relatedness, not relatedness itself. Two events can cite one file for unrelated reasons.

## Next steps that would resolve it

1. More edges. The graph grows with the memory; re-running at roughly 400 events would roughly double the sample.
2. A second deterministic edge type — same experiment identifier, or supersession chains — to test whether the effect is specific to co-citation.
3. A bilingual subset, which is where the mechanism was predicted to matter most and where it is currently untested.
