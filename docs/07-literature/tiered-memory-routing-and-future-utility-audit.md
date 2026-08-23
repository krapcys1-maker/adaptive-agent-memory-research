# Tiered memory routing and future-utility audit

Status: primary-source audit, design implications only

Audited: 2026-08-23

Input: user-supplied synthesis about Mem0, LangMem, AgentMemory, Amygdala, model cascades, and longitudinal memory utility

## Bottom line

The synthesis is worth pursuing, but it contains two experiments that must remain separate:

1. **memory-manager routing** — when deterministic code, a cheap model, or a stronger model should process an event;
2. **future-utility learning** — whether a stored memory later improves an outcome and whether that improvement was caused by the memory.

The strongest original project opportunity is the closed loop

```text
store -> become eligible -> retrieve -> expose or withhold -> observe outcome
      -> estimate attributable utility -> revise experimental policy
```

No reviewed source establishes that a fixed `80-95% deterministic / 5-20% small / 0.5-2% frontier` allocation is optimal. Those percentages are an intuition, not a prior to enforce. Routing rates must emerge from frozen quality, risk, latency, and cost thresholds.

## Claim audit

| Claim in the synthesis | Audit status | What the evidence supports | Correction or project consequence |
| --- | --- | --- | --- |
| Mem0 V3 uses extraction plus semantic, lexical, entity, and temporal retrieval | Verified as vendor-documented architecture | Mem0 documents a six-stage extraction flow, single-pass ADD-only extraction, and multi-signal retrieval | Useful comparison for stage separation and hybrid signals; it does not establish our proposed model cascade |
| Mem0 V3 reaches roughly 90+ on LongMemEval | Verified only as vendor-reported system results | Mem0 publishes different V3 figures across its migration documentation and current benchmark repository | Record the exact run, retrieval depth, embedder, reader, judge, and date; do not mix tables or attribute a system score to ADD-only extraction alone |
| LangMem can run memory management in the background with its own model | Verified | Its background manager is separate from the foreground agent and accepts a model configuration | Supports replaceable background workers; it does not supply evidence for fixed escalation rates or causal utility |
| AgentMemory reports 95.2 Recall@5 and 98.6 Recall@10 | Verified as repository self-report | The test retrieves session blobs on LongMemEval-S with `recall_any@K`; no answer reader or judge is used | It is a coarse retrieval diagnostic: finding any gold session is weaker than retrieving all evidence or answering correctly |
| Amygdala uses a cheap model, hooks, SQLite, consolidation, feedback, and proactive recall | Largely verified in the pinned repository | The repository implements broad transcript hooks, local persistence, recall and heuristic feedback updates | Its `used`, `ignored`, and keyword significance signals are not causal utility and may be confounded by exposure and ranking |
| A deterministic-small-frontier cascade should be very cheap | Plausible but not established | Generic model-routing literature supports selective deferral after calibration | Cost estimates in the synthesis are outdated and cache assumptions were too optimistic; measure actual input/output/cache tokens and time band |
| Later retrieval, citation, or use can label future utility | Rejected as stated | These events are valuable telemetry | Exposure, citation, behavior, success association, and causal benefit are different levels; only a counterfactual design supports an attributable-utility claim |
| This research repository can become the first client and longitudinal dataset | Supported as an experiment design | It offers real delayed tasks, revisions, failures, and reuse opportunities | Begin with immutable shadow logging. Do not let the learned score change stable memory or ranking until the causal and safety gates pass |

## What the named projects actually contribute

### Mem0 V3

[Mem0's evaluation documentation](https://docs.mem0.ai/core-concepts/memory-evaluation) describes its extraction and multi-signal retrieval pipeline. Its [V2-to-V3 migration page](https://docs.mem0.ai/migration/platform-v2-to-v3) and [memory-benchmarks repository](https://github.com/mem0ai/memory-benchmarks) report strong but not identical benchmark values. The benchmark repository also makes clear that embedder, answer model, judge, retrieval depth, and context budget affect the final score.

Project use:

- retain Mem0 as a system-level comparator;
- test ADD-only extraction separately from hybrid retrieval;
- never interpret one end-to-end score as evidence for every component;
- retain original raw events even if a model emits no extracted memory.

### LangMem

LangMem's [background memory guide](https://github.com/langchain-ai/langmem/blob/main/docs/docs/background_quickstart.md) and [manager API](https://langchain-ai.github.io/langmem/reference/memory/) support a clean foreground/background boundary and a separately configured model.

Project use:

- borrow the worker boundary and provider-neutral job packet;
- compare foreground latency with asynchronous processing;
- treat insert, update, and delete proposals as candidates, not canonical mutations;
- keep deterministic validation and append-only provenance outside the model.

### AgentMemory

The pinned [LongMemEval note](https://github.com/rohitg00/agentmemory/blob/main/benchmark/LONGMEMEVAL.md) uses a fresh index per question, stores session-level blobs, evaluates 500 LongMemEval-S questions, and calls success when any gold session appears in top K. The reported BM25+vector values are real within that instrument, but there is no answer-generation stage.

Project use:

- reproduce it only as a session-retrieval comparator;
- add all-required-evidence, forbidden-intrusion, unanswerable, reader, and cost metrics;
- do not use its headline percentages as an architecture gate.

### Amygdala

The pinned [Amygdala repository](https://github.com/NOBI327/amygdala) is valuable as a compact hook-driven local-memory comparator. Its automatic capture and implicit feedback are precisely why it is useful for falsification: a retrieved memory can be ignored for many reasons, and a successful task can expose several memories without identifying which one helped.

Project use:

- borrow hook and telemetry patterns only behind explicit capture scope and redaction;
- preserve `retrieved`, `shown`, `referenced`, and `outcome` as separate facts;
- reject `ignored = harmful` and `success = every exposed memory was useful`;
- retain it as a tier-C salience comparator, not a dependency.

## Routing evidence

Generic routing research supports the experiment, not the proposed quotas. [Language Model Cascades: Token-Level Uncertainty and Beyond](https://proceedings.iclr.cc/paper_files/paper/2024/hash/11f5520daf9132775e8604e89f53925a-Abstract-Conference.html) shows that learned deferral can outperform naive sequence-level uncertainty aggregation and warns about length bias. [FrugalGPT](https://arxiv.org/abs/2305.05176) studies learned cost-quality cascades. [RouteLLM](https://github.com/lm-sys/RouteLLM) provides reusable evaluation and threshold-calibration patterns, but its reported chat-benchmark savings cannot be transferred to memory management.

Consequences:

- route on typed failure or uncertainty (`schema_invalid`, `conflict`, `authorization_unknown`, `temporal_ambiguity`), not verbal confidence alone;
- include `always cheap`, `always strong`, deterministic-only, cascade, and oracle-label controls;
- calibrate thresholds on development data and freeze them before the test;
- report the complete selective risk/coverage/cost curve instead of selecting one favorable operating point;
- repeat any positive result with another model family before calling the routing rule provider-neutral.

## Three non-equivalent meanings of utility

### 1. Intrinsic write-time signal

[NEMORI](https://aclanthology.org/2026.acl-long.1607/) uses predictability or prediction error during semantic distillation: information already predictable from accumulated memory is treated as more redundant. This is a useful novelty/compressibility signal. It is not observed future benefit.

### 2. Observed post-exposure association

[MemRL](https://arxiv.org/abs/2601.03192) stores intent-experience-utility structures, first retrieves by similarity, then uses Q-values learned from environmental reward. This is much closer to a feedback loop, but a task reward distributed to retrieved memories still depends on the reward environment and credit-assignment rule.

Amygdala's positive/negative implicit feedback belongs to the same broad observational class, with a much more heuristic label.

### 3. Causal future utility

The project's target remains:

> improvement attributable to access to a memory on a later objective, net of retrieval, processing, and harm costs.

This requires comparable outcomes with and without access. Retrieval counts, clicks, citation, and task success can diagnose the path, but they cannot by themselves establish the counterfactual difference.

## Utility evidence ladder

| Level | Observable | Valid conclusion |
| --- | --- | --- |
| U0 | Stored | Capture occurred |
| U1 | Eligible/retrieved | The retrieval policy could access or ranked it |
| U2 | Exposed in context | The reader had an opportunity to use it |
| U3 | Behaviorally referenced | Output or action can be linked to it |
| U4 | Associated with task success or harm | Use and outcome co-occurred |
| U5 | Counterfactual benefit estimated | Access changed the outcome under an admissible comparison |

Only U5 can justify a causal retention or promotion claim. U0-U4 remain essential diagnostics and training candidates for explicitly non-causal surrogate models.

## Updated DeepSeek cost check

The synthesis used an older tariff. The official [DeepSeek pricing page](https://api-docs.deepseek.com/quick_start/pricing/) on 2026-08-23 lists time-dependent prices per million tokens:

| Model | Input cache miss off-peak / peak | Output off-peak / peak |
| --- | ---: | ---: |
| DeepSeek V4 Flash 0731 | $0.22 / $0.44 | $0.66 / $1.32 |
| DeepSeek V4 Pro 0813 | $0.66 / $1.32 | $1.98 / $3.96 |

For 100 daily decisions, 1,500 input and 200 output tokens per decision, 30 days, and **all cache misses**:

| Model | Off-peak monthly estimate | Peak monthly estimate |
| --- | ---: | ---: |
| Flash | $1.386 | $2.772 |
| Pro | $4.158 | $8.316 |

At 1,000 Flash decisions per day the same estimate becomes $13.86 to $27.72. Cache discounts apply only to prefixes that actually hit the provider cache. The benchmark must log actual cache-hit input, cache-miss input, output tokens, time band, retries, and total USD; it must not assume that event bodies are cached.

## Safe first architecture for the experiments

```text
canonical append-only raw event
        |
        +--> deterministic validator and exact metadata
        |
        +--> shadow candidate queue
                 |
                 +--> deterministic proposal
                 +--> cheap-model proposal when typed trigger fires
                 +--> strong-model proposal when a second typed trigger fires
                 |
                 +--> immutable comparison and cost log

canonical store is never deleted or rewritten by the experiment
```

The stable project memory and experimental memory are already separated in this repository. The new work should extend that boundary, not replace it.

## Decision

Advance two preregistration drafts:

- `PMLAB-ROUTER-001`: determine whether a calibrated tiered manager reduces cost without increasing critical omissions or unsafe mutation proposals;
- `PMLAB-UTILITY-001`: determine whether longitudinal telemetry can progress from exposure association to an admissible estimate of attributable future utility.

Do not yet implement automatic consolidation, deletion, learned ranking, emotional salience, or reward-updated retention. Those actions remain downstream of the two protocols and independent-label gates.
