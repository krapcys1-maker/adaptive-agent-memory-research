# Benchmark Catalog

Status: in-progress

## High-priority suites

| Benchmark | Primary target | Strength | Limitation to investigate | Proposed role |
|---|---|---|---|---|
| LongMemEval | long-term assistant conversation | evidence sessions/turns, updates, temporal and multi-session questions | public labels/contamination; QA mixes retrieval and reader performance; abstention near-miss sessions are not positive retrieval gold | version-pinned 36-ID transfer bridge, never pooled with PMLAB |
| LoCoMo | multi-session dialogue | evidence IDs, summaries, temporal event structure | ten conversations; generated/edit pipeline; CC BY-NC 4.0; judge and annotation quality need audit | secondary noncommercial conversational audit, no bundled redistribution |
| LongMemEval-V2 | long-running agent experience | workflow knowledge, dynamic state, gotchas, trajectories | very large and operationally expensive; preprint/young benchmark | high-value held-out final test |
| BEAM | 100K–10M+ long memory | scale and multiple memory abilities | must verify exact task construction and contamination risk | held-out stress test |
| MemoryAgentBench | incremental agent memory | separates accurate retrieval, test-time learning, long-range understanding | requires inspection of environments and scoring | held-out agent evaluation |
| LoCoMo-Plus | implicit cognitive constraints | semantic cue/trigger disconnect | extension inherits some LoCoMo assumptions | adversarial generalization test |
| OmniMemEval | cross-system evaluation | unified user- and agent-memory adapters | comparability depends on adapter fidelity | harness reference |
| GoodAI LTM benchmark | continual and long-term capabilities | different task family and long-running focus | size, maintenance, licensing, and reproducibility need review | secondary test |

## Benchmark validity checklist

- Is the benchmark testing memory rather than only long-context reading?
- Is relevant evidence explicitly marked?
- Are negatives true negatives or merely never queried?
- Does the history contain answer leakage?
- Can the benchmark fit into current context windows?
- Are questions independent of generated filler artifacts?
- Are temporal metadata available to all systems equally?
- Is the answer evaluator deterministic or LLM-based?
- What judge model and prompt version were used?
- Are system-specific prompt exceptions or hardcoded answers present?
- Were retrieval `k`, token budgets, and reranking tuned on the test set?
- Is the memory index rebuilt using test questions?
- Are reported costs, latency, and memory-build calls included?
- Does the split prevent related users, templates, or environments from leaking?

## Required evaluation decomposition

```text
capture quality
  × representation integrity
  × retrieval quality
  × context construction
  × reader reasoning
  × action execution
  = end-to-end outcome
```

An end-to-end score alone cannot identify which factor improved.
