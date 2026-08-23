# Brain-to-AI benchmark portfolio v0

Status: candidate portfolio; protocols not yet frozen

## Shared contract

Every experiment uses a provider-neutral memory interface and a frozen corpus before model evaluation. The context, model-call, maintenance, latency, and storage budgets are reported separately. Raw observations remain recoverable; experimental forgetting changes accessibility unless a later governance-approved test explicitly studies deletion.

Shared baselines:

1. no durable memory;
2. recent-context window;
3. exact lexical retrieval;
4. FTS5 or equivalent local sparse retrieval;
5. local dense retrieval;
6. sparse+dense hybrid retrieval;
7. matched random action;
8. equal-token/equal-call non-mechanistic control;
9. held-out oracle for diagnostic ceiling only.

## Candidate experiments

| ID | Mechanism | Core factorial | Primary outcomes | Harm outcomes | Promotion condition |
| --- | --- | --- | --- | --- | --- |
| PMLAB-BTA-SEP-001 | pattern separation x completion | scoped identity/time binding x associative expansion | target recall, multi-hop completion | false merge, wrong-source completion, unsupported bridge | improves recall and reduces false merges across lexical and semantic cue families |
| PMLAB-BTA-SOURCE-001 | source/reality monitoring | provenance type x recursive ingestion x source conflict | correct origin and evidence selection | generated-as-observed, inference-as-fact, false confidence | material origin accuracy gain without answer-quality or token regression |
| PMLAB-BTA-PROS-001 | prospective memory | time/event trigger x cancellation x delayed condition | intention execution at first opportunity | premature, duplicate, stale, or unauthorized action | higher valid execution with bounded monitoring cost and near-zero stale action |
| PMLAB-BTA-SCHEMA-001 | schema formation | raw episodes x summary x schema+exceptions | transfer to new instance, compression | exception loss, provenance loss, overgeneralization | beats raw and summary controls on transfer while preserving consequential exceptions |
| PMLAB-BTA-IMPLICIT-001 | procedural/implicit memory | fact note x procedure x demonstration x abstracted lesson | first relevant action before explanation | verbal recall without behavior, negative transfer | improves held-out first action across surface changes, not only repeated tasks |
| PMLAB-BTA-REPLAY-001 | selective replay | none x random x recency x salience x utility candidate | delayed task utility and retention | poison amplification, collateral forgetting, compute cost | selected replay beats random and recency at equal frequency and survives poison tests |
| PMLAB-BTA-TIME-001 | multiple timescales | one decay x fixed tiers x typed reversible tiers | risk-weighted retention across delays | irreversible loss, stale retrieval, recovery failure | Pareto improvement in utility/cost with successful recovery and policy audit |
| PMLAB-BTA-RECON-001 | reconsolidation/revision | overwrite x append-only correction x evidence-bearing version graph | current-answer accuracy and correction uptake | history loss, resurrection of superseded claim, source laundering | versioned revision wins under conflict and rollback without accumulating misleading context |
| PMLAB-BTA-META-001 | metamemory/access diagnosis | no control x confidence x typed state+probe | correct retrieve/ask/abstain and fault localization | confident miss, needless search, false absence claim | improves risk-coverage and fault localization at matched retrieval budget |
| PMLAB-BTA-CONTROL-001 | learned lifecycle controller | frozen rules x bandit/policy x oracle | long-horizon net utility | distribution-shift loss, unlogged actions, privacy or deletion violations | only after component tests pass; must beat frozen rules prospectively on held-out families |

## Mechanism-specific controls

### Separation and completion

- near-duplicate people, objects, tasks, and timestamps;
- same entity across changed attributes versus distinct entities sharing attributes;
- related true episode versus tempting composite episode;
- retrieval-only completion versus generated bridge clearly marked as inference.

### Source and reality monitoring

- direct observation, quoted source, user claim, model inference, simulation, summary, and imported record;
- correct claim from an untrusted source and incorrect claim from a trusted source;
- recursively summarized material with preserved versus stripped lineage;
- adversarial instruction embedded inside a retrieved memory.

### Prospective memory

- time-based, event-based, and state-based triggers;
- changed condition, completed intention, explicit cancellation, missed window, and duplicate events;
- correct recognition with action disallowed by current authorization;
- monitoring-cost measurement when no trigger occurs.

### Schema and procedure

- common rule with rare high-cost exception;
- paraphrased and cross-domain transfer;
- observation before explanation to prevent answer leakage;
- negative demonstration and obsolete procedure.

## Metrics

Report at minimum:

- answer or action correctness;
- evidence precision/recall and source accuracy;
- false merge and contradiction rate;
- stale, premature, duplicate, and unauthorized action rate;
- first-action success before explanation;
- harm-weighted negative transfer;
- calibration, risk-coverage, and abstention utility;
- bytes, retrieved tokens, model calls, maintenance calls, latency, and energy proxy where available;
- recovery success after suppression, corruption, or index loss.

No single aggregate memory score replaces the failure-specific outcomes.

## Success and rejection

A mechanism is a project success only if it:

- improves the preregistered primary outcome on held-out data and more than one cue/task family;
- beats the strongest simpler baseline under a matched resource envelope;
- does not purchase average gains through unacceptable false memory, stale action, poisoning, privacy, or deletion harm;
- preserves evidence lineage and remains usable with at least two model providers or a model-independent deterministic evaluator;
- survives a blind audit or independent rerun before architecture promotion.

Reject or demote the mechanism when random action, extra tokens, more model calls, or a simple recency/relevance rule explains the gain; when benefit is confined to one prompt/model/dataset; or when the defining biological operation is absent and only its vocabulary remains.

## Execution order

```text
deterministic corpus and scorer
  -> lexical / FTS5 / dense / hybrid baselines
  -> source monitoring and separation/completion
  -> prospective and procedural first-action tests
  -> schema, replay, revision, and multi-timescale tests
  -> pairwise interactions
  -> learned lifecycle controller
```

The learned controller is deliberately last. Without validated actions, delayed outcomes, propensity logs, and harm measures, it would learn noise or benchmark shortcuts rather than memory policy.
