# Colaco and Lahjouji — What to Keep, What to Forget

- Status: full text read; extracted; first challenge pass complete; independent reproduction pending
- Version read: arXiv:2607.08032v1, 9 July 2026, 24 pages
- Source: https://arxiv.org/abs/2607.08032
- Cached file: `sources/papers/memory-compaction-2607.08032.pdf` (743,672 bytes)
- SHA-256: `6C19532535FBC3C748FAA1A67B0E047581A6FC56B99B54D43E47097BE8107EBD`

## Research question

Can KV-cache, prompt, architectural-state, and agent-memory compaction be compared as one task-utility-preserving rate-distortion problem?

## Method and evidence class

This is a cross-layer survey and formal synthesis, supplemented by two small reference experiments. It introduces reversibility, query conditioning, and multi-fidelity as design properties and proposes COMPACT-Bench. It is not a large comparative validation of production memory systems.

## Extracted results

- The paper defines compaction as `C(H) -> Z` under a budget, with a usage operator and expected task loss; it interprets useful retained bits through a task/query-conditioned information bottleneck (Section 2, p. 2).
- For agent memory, it distinguishes reversible raw archival paging/retrieval from irreversible summary overwrite, argues that temporal versioning can retire rather than delete superseded facts, and notes that reversibility does not prevent poisoning (Section 10, pp. 9–10).
- A unified needle experiment covered 1,395 generations. The full cache scored 1.00; below roughly a quarter of the full budget all tested methods were at or near zero (Section 14.1, pp. 16–17; Figure 5).
- In a twelve-fact repeated-compaction reference experiment, reversible archive retrieval stayed near 0.95 recall, while rolling irreversible summaries ranged from 0.33 to 0.56 and worsened with more compactions (Section 14.2, pp. 17–18; Figure 6).
- The research agenda explicitly calls for query-conditioned reversible multi-fidelity compaction, loss attribution/confidence, composition tests, episodic-to-semantic promotion and stopping rules, safe self-curation, and rollback (Section 15, pp. 18–19).

## Limitations and challenge pass

- The authors state that the reference experiment used a small open model on one commodity GPU; its absolute values are illustrative, not leaderboard evidence (Limitations, p. 19).
- The clean lower-bound form assumes a query-agnostic operator and treats task-conditioned information content as given; estimating it for real tasks is open (p. 19).
- The proposed cross-layer operator algebra is an empirical agenda, not a proven composition law.
- The survey includes many recent preprints and heterogeneous self-reported budgets. Cross-paper ratios are not controlled comparisons.
- Figure 6 motivates replication but does not establish that every summarizer or task exhibits the same degradation.

## Project relevance

The paper supplies a direct missing benchmark: measure the same memories after repeated lossy transformations, not only after one retrieval. It also supports keeping a lossless canonical tier and making summaries rebuildable derived artifacts.

## Falsifiable hypothesis

At matched active-context bytes/tokens, append-only archive plus retrieval will have a flatter error curve across 1, 2, 5, 10, and 20 maintenance cycles than rolling summary overwrite. Reject universality if a preregistered summarizer matches retrieval on critical fact recall, stale-state rate, provenance, and total cost across at least two task families.
