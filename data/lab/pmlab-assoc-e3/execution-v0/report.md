# PMLAB-ASSOC-E3 — with the leak closed, the association graph harms retrieval

Experiment ID: `PMLAB-ASSOC-E3`
Tier: **E (exploratory)** — model-free, no network, no API cost
Supersedes: `PMLAB-ASSOC-E2`, retracted for insufficient leakage control
Authority: development measurement only. **The mechanical stratum is the primary result. There is no pooled headline.**

## What was repaired

**The leakage control.** E2 removed only the direct edge between a held-out pair, leaving every other event citing the same source connected to both endpoints, so the gold-generating group reassembled over two hops. Here an edge is removed when **every** group generating it is one of the groups that defined the held-out pair; an edge that also arises from an independent group survives, because that group is a genuine alternative mechanism.

Removing all group-generated edges unconditionally would delete legitimate structure. Removing only the direct edge is far too weak. This is the control that actually tests transitivity. It removes a mean of 4.5 edges per held-out pair rather than 1.

**Displacement is measured again.** E1 reported the cost in lexical positions surrendered; E2 dropped it and published only the favourable half.

**No post-hoc pooling.** E2 decided to pool after seeing the strata. The mechanical stratum — the only one whose gold is not authored by the agent running the experiment — is primary here, and the tag stratum is reported beside it, labelled.

## Results

### Primary: mechanical gold, n = 280

| Metric | B1 lexical | B2 lexical + graph | Difference | 95% CI |
|---|---|---|---|---|
| Recall@5 | 0.400 | 0.286 | **−0.1143** | **[−0.1786, −0.0536]** |
| Recall@10 | 0.536 | 0.496 | −0.0393 | [−0.0857, +0.0071] |

```
queries helped @10   18
queries harmed @10   29
mean lexical positions displaced @10   4.2
reachability ceiling                   0.246
```

### Secondary: tag gold, authored by the experimenting agent, n = 270

| Metric | B1 | B2 | Difference | 95% CI |
|---|---|---|---|---|
| Recall@5 | 0.289 | 0.237 | −0.0519 | [−0.1037, 0.0000] |
| Recall@10 | 0.433 | 0.378 | **−0.0556** | **[−0.1037, −0.0074]** |

```
queries helped @10   14
queries harmed @10   29
```

## The finding

**With the leak closed, the graph does not help. It harms.**

At depth 5 on mechanical gold, the harm is −0.114 with an interval that excludes zero. Both strata point the same way at both depths, and in both the graph harms roughly twice as many queries as it helps.

E2's +0.0542 was entirely the leak.

## Why, and it is not subtle

The failure is in how the graph is *reached*, not in the graph itself. Expansion is seeded from the top three lexical hits, and that design helps in neither regime:

- **When lexical retrieval fails, there are no seeds**, so the graph contributes nothing. `PMLAB-XLANG-E1` measured this exactly: gain of 0.0000 with a confidence interval of [0, 0] on Polish queries, 26 of 45 of which returned no candidates at all.
- **When lexical retrieval succeeds, the graph displaces the correct answer.** `PMLAB-XLANG-E1` measured English Recall@5 falling from 1.000 to 0.711 under graph fusion. Here it costs 4.2 lexical positions per query.

Three independent measurements now agree that reciprocal rank fusion with this graph **taxes the stronger arm**. Fusion is not a free addition; it is a trade, and here the trade is bad.

## What is and is not concluded

**Concluded for this design.** A `shares_source` / `shared_rare_tag` graph, fused by RRF at k=60 and seeded from the top-3 lexical hits, does not improve retrieval over lexical alone on this corpus, and measurably degrades it at depth 5.

**Not concluded.** That graphs are useless for agent memory. The seeding is the identified flaw, and an entry point that does not depend on lexical success — an entity or identifier lookup, or a dense seed — was never tested. Nor does this touch the graph's value as *structure*: materialising it took the memory from 10 edges to 240 and connectivity from about 11% to 92%, which remains true and useful for navigation and consolidation regardless of retrieval.

**Not concluded.** That the retracted E2 result was dishonest. It was wrong, for a reason a single author checking his own work did not catch, which is what tier I2 exists for.

## Limits

- One corpus, `n = 1` project, no preregistered threshold.
- Gold remains a proxy: two events can cite one file for unrelated reasons.
- The corrected control may still be imperfect. It closes group reconstitution; it does not prove no other path leaks.
- `n = 280` and `n = 270` per stratum, so the depth-10 mechanical interval touching zero is genuinely uncertain rather than proof of no effect.

## Status

The association-graph-as-retrieval-fusion question is **closed with a negative result** across three experiments. E1 was inconclusive, E2 was a leakage artifact and is retracted, E3 measures harm. Any future attempt needs a different entry point, not a bigger graph.
