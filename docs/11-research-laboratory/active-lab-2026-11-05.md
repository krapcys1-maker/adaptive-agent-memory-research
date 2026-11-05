# Active laboratory: what we are building and what the next result must decide

2026-11-05. This is the live operating view of the existing laboratory, not a second experiment registry or a claim of a new finished product. Follow [operating doctrine](../00-project/operating-doctrine.md), [research questions](../00-project/research-questions.md), the [lab map](lab-map.md), [historical registry](../../data/lab/experiment-registry.csv) and [current handover](../../HANDOVER.md). The registry counts historical rows; the old pending density row is explicitly superseded by its executed successor, not silently erased.

Latest executed comparison: [full BEAM reader result](../../data/lab/beam-reader-evidence-v1/README.md),200probes/605local/0API. Authored conservative N19/B39/Craw31/Cdel32 of200,8uncertain reference cases,8gains/15losses versus raw retrieval. Reject adoption of the new citation contract; reduced assessed contradictions do not compensate for quality loss. It is not old-graph transfer, official accuracy, independent review or a vendor comparison. Complete source windows and605native replay pass engineering checks, while semantic frame loss remains reproduced. Next work is evidence modality/context plus sufficient-evidence measurement; no automatic additional inference or NIE integration. Registry83historical rows; prior registration is fulfilled by its result successor. Latest HANDOVER supplies cumulative counts and exact freezes; older prospective sections below are historical planning context.

## Current identity

**A research prototype for source-grounded, stateful agent memory, with local persistence and inspectable execution.** Preserve source episodes; represent derived assertions separately; retain time, scope and provenance; use model-assisted interpretation/selection and code for explicit state/path operations. The project's other instruments study writer memory, persona, retention and evaluation validity. They are not automatically integrated into this candidate.

Working pieces: append-only continuity tooling, persistent source/claim stores, query-time state/path execution, bounded source packets, versioned CLI/runners, mechanical integrity/mutation tests, and real local/Flash trials. Missing product evidence: reliable efficient general capture, fresh external transfer, matched competitors, adaptive consolidation/forgetting and downstream agent benefit. NIE personality/deployment remains a separate ownership boundary.

Do not describe us as the first graph memory, first temporal memory, first append-only memory or the system that beats large-model memory providers. [Existing novelty audit](../00-project/related-work-and-novelty.md) already identified APEX-MEM as a close architectural predecessor; the current structured-execution idea also overlaps CAR.

## What actually differs from other work?

Our **research emphasis** is an inspectable boundary: which decisions genuinely need a model, which can be executed over explicit state, and what is lost when raw evidence is transformed. Small-model adequacy, per-stage failure attribution, reproducible negative results and full cost accounting are testable research goals. They are not proven unique capabilities or competitive advantages.

| Reference | Current author-stated capabilities inspected on2026-11-05 | Consequence for our claims |
|---|---|---|
| [Mem0](https://github.com/mem0ai/mem0) | Personalization, user/session/agent state, hybrid retrieval and time-aware retrieval. Its April2026 algorithm note distinguishes managed-platform results from the open SDK. | Neither personalization nor temporal retrieval is our novelty. Old GPT-4o-mini benchmark rows do not describe today's managed service. |
| [Graphiti](https://github.com/getzep/graphiti) | Temporal context graph, source episodes/provenance, historical queries and hybrid retrieval. | Time, graphs and retained source history are shared ground, not our moat. |
| [Hindsight](https://github.com/vectorize-io/hindsight) | Retain/recall/reflect, observations/mental models and multiple local/hosted provider options. | Local operation, learning language and model portability are not unique to us. No current same-protocol run was made here. |
| [APEX-MEM, ACL2026](https://aclanthology.org/2026.acl-long.749/) | Entity-centric property graph, append-only evolution and query-time conflict handling. | Direct prior art for the broad architecture; our study must isolate a narrower mechanism. |
| [CAR/post-retrieval assembly](https://arxiv.org/html/2606.01435v2) | Separate evidence extraction from policy execution, including multi-hop freshness handling. | Deterministic execution after extraction is prior art. Its task results are reference points, not our matched baseline. |

These are checked **primary-source descriptions**, not new code-level mechanism audits or reproductions. Earlier mechanism sheets and pinned adapters retain their own dates/limits. No vendor accuracy, latency or cost ranking follows from this table.

## The instruments already available

| Research layer | Existing instrument/evidence | What it can decide / cannot decide |
|---|---|---|
| Integrity and boundary behavior | `tools/structured_memory_v3.py`, `tools/structured_paths_v1.py`; [boundary fixtures](../../data/lab/structured-boundaries-v1/README.md) | Scope/time/source invariants and specified counterexamples; not semantic extraction accuracy. |
| State/path reasoning | [Complete spent MAB100](../../data/lab/structured-memory-v1/README.md) and [paired replay](../../data/lab/structured-memory-v1/reader-comparison-posthoc-v1.json) | Model+graph development behavior; not held-out small-model superiority. |
| Evidence use and interference | [Density](../../data/lab/h1-evidence-density-v1/README.md), [all-family order study](../../data/lab/h1-chronological-pack-v1/README.md) | Causal packet contrasts plus same-message stability controls; both retain failures and scorer limits. |
| Genuine memory-off controls | [Coverage map](../05-benchmarks/memory-baselines-and-benchmark-age-2026-11-05.md), original N/K hard scores and N/V typed trials | Information dependence in their own protocols; not a missing N arm for the latest graph result. |
| Fair comparisons | Frozen [comparative contract](../../data/lab/comparative/contract-v0.json), `scripts/comparative_lab.py`, existing [arena adapters](../../scripts/arena/) | Refuses mismatched conditions; requires new comparable run data, not borrowed vendor headline scores. |
| Future agent utility | WMB and [LifeSim instruments](lab-map.md), [MemoryArena sources](https://memoryarena.github.io/) | Existing WMB judge/LifeSim validity failures must be resolved; source inspection or passing software tests is not agent benefit. |
| External transfer | Cached [LongMemEval bridge audit](../06-datasets/longmemeval-public-bridge-audit.md), [LongMemEval-V2](https://github.com/xiaowu0162/LongMemEval-V2), STALE and BEAM sources | Data/setup provenance exists; do not call unexecuted end-to-end benchmarks passed. The old36-case LongMemEval bridge was retrieval-only. |

## The next active work item

**One common-protocol external comparison**, owned by existing GitHub[#51](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/51), with benchmark construction/metric work in[#7](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/7). First pin/adapt inputs and run interfaces without model calls. Inventory whether questions were previously inspected and whether image/environment dependencies can be honored. Select the task by transfer/falsification value and executable fit, never by preliminary accuracy. Our old MAB and H1 are development/regression, not confirmation.

Required comparison conditions: memory absent; ordinary retrieval; our frozen candidate; at least one pinned compatible competitor before a superiority claim. Keep the same allowed reader/decoding/question roster/time cutoff and declared budget. Record unavailable/incompatible arms as such. If a full-history reference exceeds a model's context, mark that limitation rather than secretly truncate it. Equal reader settings do not imply equal ingestion cost: report both.

Before inference, freeze capture/cache/state rules, prompts, source selection, source/packet identities, scoring, complete roster, resource ledger, stop rules and decision thresholds. No label-directed subset or retry. Use only installed declared local workers and DeepSeek V4.1 Flash for API. No Pro, judge or project-planning model. Current ledgers/caps remain in force; a later executable experiment needs a prior explicit amendment if it cannot fit, not a new hidden ledger. No new run or budget extension is created by this operating note.

After inference, freeze complete final responses before scoring, reconstruct native requests, and report every selected case. Measure supported answers, harmful stale/conflicting answers, abstention, capture/representation availability, retrieved/shown evidence, reader use, and ingestion/query cost separately. Use original benchmark scoring where feasible; label adaptations and authored qualitative checks. If labels are subjective and no accepted evaluation is available under the no-model-judge constraint, report that limitation instead of inventing official accuracy. A negative or tradeoff result closes the item with a decision. Any repair makes that set development for later runs.

## Concept queue — hypotheses, not claimed discoveries or new preregistrations

1. **State execution versus evidence presentation.** Does an explicit state/policy operation help beyond the same raw evidence given to the same reader? Falsifier: no fresh gain, or gains disappear after controlling evidence/context/cost. CAR/APEX are relevant prior art; current MAB pipeline differences do not isolate the mechanism.
2. **Safe capture versus economical reuse.** Can a successor recover useful reuse without changing polarity, scope, time or partial-property meaning? Falsifier: a boundary regression or no end-to-end cost benefit. Exact-only currently sacrifices all18,223old template reuse opportunities; do not hide this baseline.
3. **Completeness/authority versus recency.** Can the system retain rare exceptions and abstain on a missing hop while respecting user/tool roles? Falsifier: added harmful answers, lost historical answers or no advantage over ordinary retrieval. H1 sorting alone remains unadopted.

These remain a ranked backlog. Execute/retire existing registered work before adding designs, with at most two unexecuted designs per track. No concept is accepted because of biological terminology, an attractive architecture or a saturated easy control.

## Entry commands and completion record

Windows-safe offline entry points (no inference):

```text
python -X utf8 tools/project_memory/cli.py status
python -X utf8 tools/project_memory/cli.py context "current active experiment and failure mechanism"
python -X utf8 scripts/registry_summary.py --format json
python -X utf8 scripts/comparative_lab.py --help
python -X utf8 tasks.py fast
```

The registry command counts **historical rows**, not deduplicated live tasks. `-X utf8` avoids the observed Windows help-output encoding failure without modifying a frozen module or shared environment. Model runners are separate explicit commands under their own frozen protocols; these entry commands never launch them.

Every finished item leaves: result+decision in the registry, immutable raw/source identities, complete costs/failures, current handover and a sourced canonical-memory event, a verified GitHub update and private recovery receipt. EngineeringCI at `58bdcfc` passed12/12jobs, including full3377pass/21skip on each Linux Python3.11/3.12; see [receipt](../../data/lab/h1-chronological-pack-v1/delivery.json). This supports the recorded software head, **not** semantic generalization, competitive superiority or later documentation hashes.


## Execution update: first external-comparison stage completed (2026-11-05)

The data/interface stage under#51/#7 now has [full BEAM10M format evidence](../../data/lab/beam-transfer-format-v2/README.md): all10pinned conversations,187,734messages and200probes, with reader/evaluator separation and exact reconstruction. Initial v1 partial success and full-data null-time rejection are retained; v2 preserves explicit unknown time. No memory/reader run or benchmark score.6focused tests,0model calls; prior caps/ledgers unchanged.

New scale evidence changes implementation priority:30,177messages exceed the old4500byte limit even before headers;187,054scoped role/text keys are distinct. Before inference, implement auditable bounded source windows and decide affordable capture versus query-time interpretation, without discarding history or silently swapping the current graph candidate for raw retrieval. The active comparison item remains open for the full mechanism/baseline/evaluation freeze; no additional unexecuted model experiment was registered.
