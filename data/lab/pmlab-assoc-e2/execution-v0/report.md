# PMLAB-ASSOC-E2 — a second edge type for the memory association graph

Experiment ID: `PMLAB-ASSOC-E2`
Tier: **E (exploratory)** — model-free, no network, no API cost
Authority: development measurement only. Not confirmatory, not independently reviewed, cannot select an architecture.
Follows: `PMLAB-ASSOC-E1`, which found the retrieval benefit inconclusive over 102 co-citation edges and registered "a second deterministic edge type" as the resolving step.

## Edge types

| Type | Edges | Mechanical? |
|---|---|---|
| `shares_source` | 105 | yes — two events cite the same file |
| `shared_rare_tag` | 147 | **no — tags were authored by the agent running this experiment** |
| `same_experiment` | 18 | yes — same `PMLAB-*` / `API-*` identifier in text |
| `supersession` | 8 | yes — explicit `supersedes` field |
| **union** | **240** | — |

Connected nodes: 151 of 174 active events. E1 had 102 edges over 169 events.

## Gold stratification

Tag edges are allowed **into the graph** but their pairs are reported separately as gold. Using authored tags to *route* a search is legitimate; using them to define *what counts as a correct answer* would measure the author's own judgement of relatedness — the authored-fixture trap E1 deliberately avoided.

## Leakage control

When a pair is held out, **every** direct edge between those two events is removed from the fold graph regardless of type. Without this a pair linked by both a source and a tag would stay directly connected and the graph would recover it trivially. Any gain therefore still requires transitivity.

## Results

| Stratum | n | ceiling | B1@5 | B2@5 | diff@5 | 95% CI@5 | diff@10 | 95% CI@10 |
|---|---|---|---|---|---|---|---|---|
| **overall** | 480 | 0.323 | 0.3375 | 0.3917 | **+0.0542** | **[+0.0104, +0.0979]** | **+0.0458** | **[+0.0063, +0.0854]** |
| mechanical | 240 | 0.367 | 0.3958 | 0.4417 | +0.0458 | [−0.0167, +0.1083] | +0.0417 | [−0.0125, +0.0958] |
| tag_only | 240 | 0.279 | 0.2792 | 0.3417 | **+0.0625** | **[+0.0042, +0.1208]** | +0.0500 | [−0.0042, +0.1042] |

10,000 paired bootstrap resamples. Both directions of every edge are queried.

## Interpretation

**The direction and magnitude are consistent across every stratum**, roughly +0.04 to +0.06, and the pooled interval excludes zero at both depths. E1's inconclusive result at 102 edges becomes separable from zero at 240.

The most important reading is what the stratification rules *out*. The obvious worry was that authored tag gold would inflate the estimate. It did not: the mechanical stratum, whose gold is not authored, gives a point estimate of +0.0458 at depth 5 against the tag stratum's +0.0625 and the pooled +0.0542. The mechanical stratum fails to exclude zero because n = 240, not because the effect is absent there.

So the honest summary is: **a small, consistent benefit of roughly five points, visible only when strata are pooled, and not driven by the authored gold.**

## What this does not show

- **Pooling to gain power was decided after seeing the strata.** No threshold was preregistered — this is Tier E. The pooled interval should be read as a description of this sample, not as a test that was set up in advance to be passed.
- No architecture claim. RRF at k=60 was inherited from an existing project decision, not compared against alternatives.
- No safety claim. Memory events carry no trust or forbidden labels, so the forbidden-intrusion metric used elsewhere has no analogue here.
- Gold remains a proxy. Two events can cite one file, or share one rare tag, for unrelated reasons.
- E1 and E2 ran against different memory sizes, 169 and 174 active events, so they are related measurements rather than a clean before-and-after.

## Registered label

`supports-association-benefit-exploratory`. Direction consistent across strata, magnitude around five points, pooled interval excluding zero, underpowered per stratum, no preregistered threshold.

## The step this unlocks

The effect is now large enough and stable enough to justify a **sealed held-out test** under independence tier I1, using `scripts/sealed_split.py`. That would fix the two weaknesses this run cannot fix on its own: the threshold would be registered before the challenge half exists, and the split would be verifiable by a third party rather than chosen by the author.

That is the natural promotion path — from Tier E exploration to a commit-and-reveal evaluation — and it needs no reviewer, no model, and no budget.
