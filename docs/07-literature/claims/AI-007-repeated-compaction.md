# AI-007 — Irreversible repeated compaction can compound evidence loss

- Domain: `agent-memory`
- Claim type: `methodological`
- Status: `challenged`
- Confidence: `low`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: small-model twelve-fact needle experiment in a 2026 survey.
- Intervention or comparison: rolling LLM-summary overwrite versus archive-and-retrieve at matched average active budget.
- Measured outcome: final fact recall after repeated compaction.
- Timescale: 5–25 compaction events in the plotted reference experiment.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Colaco and Lahjouji, arXiv:2607.08032v1 | Section 14.2 pp. 17–18; Figure 6 | reversible recall near 0.95; irreversible 0.33–0.56 | small reference experiment |

## Contradictions, null results, and boundary conditions

The authors call the numbers illustrative and report a single commodity GPU/small-model setup. It compares one summarization discipline and one task family, so it cannot establish universal dominance.

## Alternative explanations

The selected summarizer, prompt, fact density, retrieval oracle quality, or unequal maintenance compute may explain the size of the gap.

## Computational translation

- Abstract problem: information loss under repeated lossy state rewrites.
- Candidate mechanism: canonical archive plus versioned rebuildable summaries.
- Simpler baseline: canonical archive plus FTS5 only.
- Predicted benefit: flat critical-recall curve with audit/rollback.
- Predicted failure: retrieval misses despite preserved storage or prohibitive query latency.
- Rejection criterion: preregistered rolling summarization matches archive-backed systems on recall, provenance, cost, and safety across two corpora.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: not applicable; first extraction only
