# AI-006 — Decision-conflict-aware routing can improve bounded agent memory

- Domain: `agent-memory`
- Claim type: `methodological`
- Status: `challenged`
- Confidence: `low`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: DeMem on synthetic diagnostics and long-horizon agent benchmarks.
- Intervention or comparison: query-conditioned decision-conflict routing versus descriptive/RAG/agent-memory baselines.
- Measured outcome: LLM-judged answer score and synthetic regret under matched runtime memory budgets.
- Timescale: multi-session histories; query-time state selection.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Zou et al., arXiv:2605.10870v1 | Table 1 p. 8 | DeMem overall `0.911±0.040` and `0.920±0.038`, higher than reported baselines; Mnemis higher on single-hop | recent preprint experiment |
| same | Section 5.4 p. 9; Appendices D.10/E.11 | splits on 4.6% of routing events with 85% precision; ablations lower; DeMem-Core 90.8 | mechanism audit/ablation |

## Contradictions, null results, and boundary conditions

Mnemis wins the single-hop column. Performance declines under corrupted feedback. The formal setting is finite and feedback-rich; raw disk storage is not the constrained resource. Independent reproduction is absent.

## Alternative explanations

Routing prompts, evidence formatting, model judges, or benchmark-specific answerability may drive part of the gain. Runtime latency and all LLM-call costs are not captured by a state-slot count alone.

## Computational translation

- Abstract problem: select evidence that changes the optimal answer/action.
- Candidate mechanism: query-conditioned conflict-aware routing over immutable episodes.
- Simpler baseline: FTS5/hybrid retrieval under the same evidence-token budget.
- Predicted benefit: fewer critical misses and lower consequence-weighted error.
- Predicted failure: noisy feedback fragments states and increases cost without better answers.
- Rejection criterion: no held-out benefit beyond frozen retrieval baselines, or benefit fails cost/safety gates.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: not applicable; first extraction only
