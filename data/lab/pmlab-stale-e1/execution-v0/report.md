# PMLAB-STALE-E1 — content cannot separate a superseded fact from its replacement

Experiment ID: `PMLAB-STALE-E1`
Tier: **E (exploratory)** — local model, no network at query time, no API cost
Authority: development measurement only. **n = 9 supersession pairs**; qualitative result and effect direction, not a confidence interval.

## Why this question, and not the obvious one

The obvious test — "does dense retrieval surface stale facts?" — is malformed against this store. `search()` already excludes superseded records by metadata: **0 of 9 appear in results**. Measuring that measures the filter, not the risk.

The question that matters is what that filter is doing for us, and whether anything else could do it.

## Results

```
supersession pair cosine     mean 0.816   min 0.593   max 1.000
corpus baseline cosine       mean 0.372   p95 0.556   p99 0.638

mean corpus percentile of a supersession pair   0.9948
pairs above the corpus 99th percentile          7 / 9
```

With the metadata filter removed and the current memory used as the query:

```
stale version is the nearest neighbour   6 / 9
stale version in the top 5               8 / 9
median rank of the stale version         1
```

| cosine | percentile | stale rank | current memory |
|---|---|---|---|
| 0.619 | 0.984 | 5 | Reader pilot v0 invalidated by gold-label leakage |
| 0.885 | 0.9998 | **1** | Reader stress required five iterations to close known leakage |
| 0.801 | 0.9993 | **1** | Validity ambiguity and weak abstention policy drive failures |
| 0.593 | 0.973 | 7 | LongMemEval public bridge completed |
| **1.000** | 0.9999 | **1** | LongMemEval public bridge completed |
| 0.911 | 0.9998 | **1** | Future-utility telemetry T0.1 validates amended instrumentation |
| 0.714 | 0.998 | 2 | Independent natural-history contract review packet v0.1 is ready |
| **1.000** | 0.9999 | **1** | Multiple agent sessions may write to this repository concurrently |
| 0.823 | 0.9996 | **1** | The association-graph benefit was an artifact of leakage control |

## The finding

A superseded memory and the memory that replaced it sit at the **99.5th percentile** of all pairwise similarity in this corpus. That is not a coincidence of wording — it is what a revision *is*. The two records state the same claim about the same subject at different times.

**Two pairs have cosine exactly 1.000.** For those, content-based retrieval cannot distinguish the stale record from the current one at all. Not poorly — *not at all*, because the representations are identical.

Remove the metadata filter and the stale version becomes the top result more often than not: 6 of 9 nearest neighbours, 8 of 9 in the top five, median rank 1.

## What this establishes

> **Supersession cannot be solved by better retrieval. It must be carried in the schema.**

A better embedding makes this *worse*, not better, because a better embedding places two statements of the same claim closer together. The mechanism that fixed cross-language retrieval in `PMLAB-XLANG-E2` — semantic proximity — is the same mechanism that makes a stale fact indistinguishable from its replacement.

This is a claim about the field rather than about this repository. This project's audit of `NOBI327/amygdala` recorded that its "schema lacks evidence provenance, valid time, supersession, and trust". Under this measurement that stops being a missing feature and becomes a **correctness defect**: such a system returns stale facts as top results by construction, not by accident.

It also bounds `PMLAB-XLANG-E2`. Dense retrieval's Recall@10 of 0.978 is safe **only because the supersession filter exists**. Swapping the index from lexical to dense is admissible; swapping it while dropping the metadata filter is not.

## And it answers the hair-colour question

The recurring example in `#29` — memory holds "Ala has brown hair", then Ala dyes it green — has an answer now. "Brown" and "green" are the same claim about the same subject at different times, so they are semantic near-neighbours by construction. **No retrieval method can order them correctly from content.** Only valid time can, which is exactly what `#29` proposes and what this store currently lacks.

## Limits

- **n = 9.** Qualitative, directional. Enough to separate "content can do it" from "content cannot", which was the decision at hand, and not enough for an interval.
- One model, one corpus, `n = 1` project.
- The pairs are this project's own supersessions, which skew towards revisions of experimental findings rather than the full variety of real-world fact change.
- Cosine 1.000 arises partly because two pairs share a title verbatim. That is a real pattern in revision, not an artifact — a revision often keeps the subject line and changes the claim — but a corpus with more rewriting would show fewer exact ties.
- This measures separability and ranking. It does not measure how often a user would actually be harmed, which needs a reader.

## What follows

1. **The supersession filter is load-bearing and must never be dropped**, including in any future dense or hybrid index. It should be a tested invariant, not a convention.
2. **`#29` is promoted from a schema improvement to a prerequisite.** Without valid time, a fact that becomes stale *without* a formal supersession is indistinguishable from a current one, and this experiment shows content will not save us.
3. Any external memory system considered for reuse should be checked for supersession in its schema **first**, before its retrieval quality is evaluated at all.
