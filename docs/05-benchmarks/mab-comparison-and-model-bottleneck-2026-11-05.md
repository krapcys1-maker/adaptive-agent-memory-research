# What our MAB result does and does not beat

Checked 2026-11-05 against primary sources. Published-result comparison only; no competitor was rerun in this phase. Read the [machine-replayed paired summary](../../data/lab/structured-memory-v1/reader-comparison-posthoc-v1.json) and the [original implementation record](../../data/lab/structured-memory-v1/README.md).

## Published external reference points

The benchmark authors' [v4 paper, Table3](https://arxiv.org/html/2507.05257v4#S4.T3), reports the following FC-MH accuracy percentages. Unspecified memory/RAG backbones use GPT-4o-mini. These are the authors' historical configurations, not measurements of current commercial releases.

| Published configuration | FC-MH (%) |
|---|---:|
| Mem0 | 2 |
| Zep | 3 |
| Cognee | 3 |
| MemGPT | 3 |
| HippoRAG-v2 | 5 |
| GPT-5-mini long context | 28 |

Two further primary sources prevent cherry-picking only the weakest baselines:

- [ActionRAG, authors' research page](https://www.actioneer.com/research/) reports FC-MH15.5. Do not substitute its overall55.1 for this task score.
- [Reddy and Challaram, v2, Tables2–4](https://arxiv.org/html/2606.01435v2#S5.SS2) reports Chain-Aware Resolution **27 with GPT-4o-mini and41 with GPT-4o at262K**. Its pooled51.5 GPT-4o score averages four lengths and must not replace the262K cell. This is a task-specialized extraction/policy-execution pipeline, a particularly relevant comparator to our idea.

This is a verified set of reference points, **not an exhaustive current leaderboard or state-of-the-art claim**. Search hits advertising99.9% retrieval or BEAM scores concern different tasks and are not FC-MH262k results.

## Our separately reported development result

One public `factconsolidation_mh_262k` history, all100 supplied questions, dataset revision `7ea066982b140a19337e17e60d45d4076e042faf`, 18,333 raw source lines. Both question planners use one locally derived graph. Models choose executable relation paths; code computes terminal values from that graph.

| Our planner on frozen graph | Original primary exact /100 | Secondary upstream SubEM /100 |
|---|---:|---:|
| Qwen2.5 14B Q4_K_M | 55 | 55 |
| DeepSeek V4.1 Flash | 59 | 60 |

SubEM is the metric declared for conflict resolution in the [official repository](https://github.com/HUST-AI-HYZ/MemoryAgentBench#-clarification-on-evaluation-metrics). It is reported secondarily, without replacing our declared exact metric or its failed80/100 aspiration. Both rows are development evidence on already inspected questions. Different ingestion granularity, prompts, context, answer execution, model versions and preprocessing prevent a matched ranking against the published numbers above. Conversion to the same metric alone does not equalize a protocol.

The graph was produced with the old learned-template cache, before the boundary repair. It is **not** a fresh end-to-end execution of the repaired exact-only extractor. The new safer cache has zero exact reuse opportunities on18,223 previously template-served sources, so earlier cheap capture cannot be attributed to it. This cost/semantic gap must remain visible in competitive claims.

## Why local and API scores are close

Native frozen primary outputs have55 questions correct on both,41 wrong on both,4 correct only on Flash, and none correct only locally. An exploratory paired exact McNemar calculation gives p=.125; the shared history, public development and post-hoc analysis further limit inference. This is neither proof of equality nor a significant advantage claim.

The same representation can bottleneck both planners. A prior post-hoc diagnostic finds a gold substring in at least one of the bounded enumerated paths for64/100 questions. That uses SubEM and bounded enumeration; it is not a universal64% ceiling and cannot be substituted as an exact-score denominator. It supports investigating capture, predicate distinctions and option availability before assuming a larger reader alone will fix missing evidence. Parameter count is not measured by these system scores; the API alias does not itself establish a comparable parameter count or compute budget.

## Concrete assets, hypotheses and missing proof

Implemented assets include persistent local source logs, provenance, explicit update/time/scope handling, and multi-hop execution with source IDs. Narrow counterfactual boundary tests and reproducible failure records make these inspectable. These are our capabilities, **not claims that competitors lack them**; ActionRAG also describes provenance, and CAR also separates extraction from execution. The generic idea is not claimed as novel.

Potential competitive value is accurate update-aware execution with a small local model and little answer-time context. Superiority in accuracy, cost, latency, capture efficiency or operational reliability is **unproven**. Full cost includes ingestion, reranking, failed attempts and repair costs; query tokens alone would conceal the expensive part.

The next competitive decision needs (1) a pinned upstream incremental adapter and at least one baseline under identical allowed backbones/inputs/metric, (2) all FC lengths/SH and MH reported separately rather than selecting262K, (3) an additional external task with no answer-directed development, and (4) complete ingestion/query resource accounting. Do not run upstream scripts with their default OpenAI/Pro/judge models: only the authorized Flash and installed local worker are allowed. Preserve prior kernels, scores and raw failures. The old development result remains useful and promising without calling it a vendor win.
