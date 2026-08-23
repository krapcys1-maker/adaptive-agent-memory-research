# Brain-to-AI transfer gap analysis v0

Status: in-progress synthesis; architecture-neutral

## Result

The useful research question is not whether an agent has a hippocampus, cortex, amygdala, or sleep. It is whether a bounded operation from biological memory solves a measurable agent failure better than simpler software controls at the same cost.

The initial 38-row atlas finds no empty field called "memory" waiting for one biological solution. It finds a set of separable control problems: admission, binding, discrimination, completion, temporal order, retrieval, source judgment, revision, replay, consolidation, suppression, prospective triggering, confidence, and action transfer.

## Already common enough to be baselines

| Function | Common machine realization | What remains unproven |
| --- | --- | --- |
| Limited active workspace | context window, scratchpad, token budgeting | active executive control rather than passive truncation |
| One-shot event storage | event logs, experience buffers, episodic records | correct capture, identity/time binding, and later access |
| Semantic abstraction | summaries, profiles, knowledge graphs | exception preservation and provenance-complete consolidation |
| Associative retrieval | lexical, dense, graph, and hybrid search | reliable completion without false merge or unsupported inference |
| Tiered retention | recent/archive tiers, caches, MemGPT-style paging | principled transitions and reversible retention across timescales |
| Importance scoring | recency, frequency, relevance, salience scores | future utility, collateral harm, calibration, and causal credit |
| Offline maintenance | compaction, summarization, background jobs | whether the selected data and transformation cause later benefit |

These operations do not become brain-equivalent because they resemble a biological function.

## Partially transferred mechanisms

1. **Complementary learning systems.** Fast event stores and slower summaries are common, but consolidation schedules, replay selection, exception handling, and interference are rarely evaluated as one causal chain.
2. **Selective replay.** Experience replay is mature in reinforcement and continual learning; agent systems still lack bundle-aware assignment, poison controls, and delayed-utility evaluation.
3. **Pattern separation and completion.** Embeddings, entity resolution, graphs, and associative retrieval offer adjacent operations, but benchmarks usually reward recall without charging for false merging.
4. **Reconsolidation.** Memory updates exist, yet many overwrite the record rather than create an evidence-bearing revision that can be challenged or rolled back.
5. **Prospective memory.** Schedulers and reminders exist, while condition-action intentions, stale-trigger cancellation, temporal validity, and provenance are under-tested in LLM agents.
6. **Metamemory.** Confidence and routing are common, but knowing whether a fact is absent, inaccessible, contradicted, or outside collection scope remains unresolved.
7. **Schema formation.** Summarization produces regularities but often erases exceptions, source diversity, and uncertainty.
8. **Implicit and procedural memory.** Skills and demonstrations exist, but most memory benchmarks test verbal recall rather than the first relevant action.
9. **Multiple timescales and active forgetting.** Decay is common; reversible accessibility changes, recovery probes, and retention-policy safety are not.
10. **Reality monitoring.** Provenance fields exist, but observed, inferred, simulated, retrieved, and generated content are seldom challenged under recursive re-ingestion.

## Highest-value unresolved tests

| Rank | Gap | Why it may matter more than adding another retriever |
| --- | --- | --- |
| 1 | Source and reality monitoring | a fluent memory that loses origin can convert inference or simulation into false personal history |
| 2 | Pattern separation x completion | similarity search must retrieve related evidence without merging distinct people, times, or episodes |
| 3 | Prospective condition-action memory | remembering what to do later is not equivalent to answering a question about the past |
| 4 | Schema plus exception preservation | long-term compression is useful only if recurring structure and consequential exceptions survive |
| 5 | Replay with negative-transfer controls | replay can consolidate poison, bias, stale policy, and accidental correlations |
| 6 | Procedural first-action transfer | useful experience should change behavior when relevant, not merely improve factual recall |
| 7 | Multi-timescale reversible retention | one decay curve cannot express legal retention, user value, access frequency, and evidential importance |
| 8 | Learned lifecycle control | a controller is worthwhile only after its actions can receive credible delayed utility and harm signals |

## Literal transfers to reject

Reject these equations as architecture claims:

```text
hippocampus = vector database
cortex = summary database
amygdala = scalar importance score
dopamine = reward or surprise field
sleep = scheduled summarization
forgetting = deletion
emotion = positive/negative sentiment
recollection = nearest-neighbor retrieval
```

They may be search metaphors, but each collapses multiple mechanisms and hides boundary conditions. The project instead records the target failure, abstract operation, matched controls, and rejection test.

## Evidence limitations

- Cross-disciplinary surveys organize terminology; they do not validate a transfer.
- A neuroscience primary result establishes a bounded biological observation, not an agent design.
- An agent benchmark gain establishes performance under that benchmark, not mechanistic equivalence.
- Current long-memory benchmarks overrepresent explicit question answering and underrepresent prospective, procedural, source-monitoring, suppression, and first-action outcomes.
- Exact disk storage prevents physical loss but does not solve encoding, indexing, accessibility, interference, trust, or context allocation.
- External memory does not eliminate stability-plasticity. It relocates the tradeoff into representations, retrieval, consolidation, policy updates, and maintenance.

## Decision

Do not select a brain-shaped architecture. Maintain a mechanism/failure atlas and promote only operations that survive provider-neutral, cost-matched, adversarial tests. The first test portfolio should cover source monitoring, separation/completion, prospective memory, schema exceptions, and procedural first action before a learned global controller is attempted.
