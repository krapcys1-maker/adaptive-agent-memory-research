# Future-utility telemetry protocol v0

Experiment: `PMLAB-UTILITY-001`  
Status: preregistration draft; logging schema and causal design not implemented  
Purpose: turn delayed real project reuse into auditable evidence without confusing exposure with benefit

## Research question

Can longitudinal project-memory telemetry produce an admissible estimate of how much access to an individual memory improves later task outcomes, net of cost and harm?

The first phase is observation-only. It must not adapt retention, consolidation, deletion, retrieval rank, emotional salience, or canonical-memory status.

## Target estimand

For memory `m`, task `t`, and an eligible query context `x`:

```text
utility(m, t, x)
  = outcome(access to m | t, x)
  - outcome(no access to m | t, x)
  - retrieval and processing cost
  - attributable harm
```

The estimand must name the outcome, time horizon, population of tasks, exposure policy, cost units, and safety exclusions. A universal scalar memory value is not assumed.

## Evidence ladder

| Level | Required event | Meaning | May train causal retention? |
| --- | --- | --- | --- |
| U0 | `stored` | capture occurred | no |
| U1 | `eligible` and/or `retrieved` | policy could access or ranked memory | no |
| U2 | `exposed` | memory entered model/user context | no |
| U3 | `behavioral_reference` | answer/action is linked to memory | no |
| U4 | `outcome_observed` | use and success/harm co-occurred | no |
| U5 | randomized or otherwise admissible counterfactual comparison | attributable effect estimated | yes, after review |

U0-U4 are valuable diagnostic and surrogate labels. They must retain their names and never be renamed `utility`.

## Immutable event families

Each telemetry record is append-only and contains a unique event ID. Corrections append a superseding event; they do not rewrite history.

### Memory identity

- canonical memory/event ID;
- exact content hash and version;
- source/provenance class;
- valid-time, transaction-time, authorization, trust, and supersession state;
- experimental representation IDs, if any.

### Task and policy identity

- opaque task/query ID and timestamp;
- task family, language, difficulty stratum, and predeclared criticality stored outside model input;
- retrieval, reranking, reader, prompt, model, and policy versions;
- query-time corpus cutoff and eligible candidate set hash;
- assignment probability for every exposure intervention.

### Retrieval and exposure

- eligibility reason;
- rank, component scores, fused score, and candidate-set size;
- retrieved/not retrieved;
- exposed/not exposed and exact context position;
- withhold reason, safety override, and assignment arm;
- competing memories exposed in the same context.

### Behavior and outcome

- exact output/action hash and evidence references;
- citation/reference status;
- explicit user feedback kept separate from inferred behavior;
- registered task-success, error, repeated-mistake, rediscovery, time-to-solve, and token outcomes;
- harm flags: stale action, privacy leak, unsupported answer, forbidden intrusion, or wasted work;
- outcome assessor identity and blindness status.

### Cost and delay

- input/output/cache tokens and USD;
- retrieval/reader latency and local compute;
- time from storage to eligibility, first exposure, first reference, and assessed outcome;
- observation-window end and censoring reason.

## Confounds that must be logged or controlled

- ranking/exposure bias: highly ranked memories are more likely to be shown and used;
- task difficulty: hard tasks both retrieve more memory and fail more often;
- reader capability: a stronger reader can exploit or ignore memory differently;
- policy drift and model upgrades;
- concurrent exposure to several correlated memories;
- source quality, staleness, and authorization;
- delayed benefit and right censoring;
- repeated tasks and learning outside the memory system;
- user intervention and manual search;
- missing outcomes and selective feedback.

`not referenced` is not equivalent to `not useful`, and `task succeeded` is not equivalent to `every exposed memory helped`.

## Phases

### Phase T0 — schema and replay validation

Use synthetic events only to prove that all stages emit valid, joinable, append-only telemetry; exposure probability is logged; retries do not duplicate outcomes; and corrections preserve prior versions.

No scientific conclusion follows.

### Phase T1 — natural shadow observation

Log authentic project tasks without changing what is retrieved or shown. Estimate denominators, delays, missingness, candidate-set size, reuse rates, and detectable outcome frequency.

Allowed conclusions are descriptive U0-U4 rates only.

### Phase T2 — offline paired replay

For frozen, completed tasks, present a blinded reader with identical packets differing only in one memory or one memory bundle. Randomize packet order and IDs. This estimates reader sensitivity under replay, not the real-world causal effect, because the original task trajectory and user interaction are not recreated.

### Phase T3 — safe randomized exposure

Only noncritical, nonprivacy-sensitive, nonunique-support memories may be randomized between include and withhold among otherwise eligible candidates. Assignment probability must be known and nonzero. Critical evidence is always included.

Predeclare stopping and rescue rules. A withhold arm may not increase material safety risk, irreversible action risk, or user cost beyond the reviewed ceiling.

### Phase T4 — utility-model evaluation

Only after enough T3 outcomes may a model predict heterogeneous benefit. Evaluate it on future, policy-disjoint tasks using calibration, ranking regret, and off-policy methods appropriate to the recorded propensities. Its score remains shadow-only until it beats fixed baselines without safety regressions.

## Baselines

- never expose experimental memory;
- expose random eligible memory at matched count;
- most recent;
- most frequently retrieved;
- lexical/dense relevance only;
- source-trust and valid-time rules;
- NEMORI-like write-time surprise proxy;
- MemRL-like observed reward/Q-value surrogate;
- oracle outcome label, analysis only.

The surprise and Q-value arms test non-equivalent hypotheses. Neither is called causal utility.

## Outcomes

Primary task outcomes must be selected per task family before exposure:

- exact task success or registered quality score;
- repeated-error avoidance;
- avoided rediscovery/manual search;
- time-to-correct-solution;
- total input/output tokens and USD;
- critical harm and unsupported-action rate.

Primary effect reporting:

- intention-to-treat difference by assigned exposure;
- confidence/credible interval and sample denominator;
- absolute and relative effect;
- task-family and delay strata frozen before analysis;
- cost- and harm-adjusted effect reported beside raw quality.

Secondary diagnostics:

- time-to-first-reuse survival curve with censoring;
- U0-to-U5 transition funnel;
- exposed-but-not-referenced and referenced-but-harmful rates;
- memory bundle interference and redundancy;
- policy/model drift sensitivity;
- leave-one-memory-out replay effect.

## Success and rejection

T1 succeeds when the telemetry is complete and joinable; it does not validate utility. Advance from T3 to utility-model research only if:

- assignment and exposure logs are complete for at least 99% of randomized units;
- zero unreviewed critical or privacy-sensitive withholding occurs;
- the registered task outcome is observable for at least 90% of units or missingness is handled by a frozen method;
- a positive cost-adjusted intention-to-treat effect has an interval excluding zero on a fresh task cohort;
- no material critical-harm increase is observed;
- the effect is not carried by one template, user correction pattern, or model version.

Reject or redesign if benefit disappears under assignment rather than observed use, if reward attaches to every co-exposed memory, if censoring dominates, or if policy drift prevents identification. Preserve the null result.

## Stable versus experimental memory

Stable project memory remains:

- canonical append-only events;
- reviewed records and state summary;
- provider-neutral lexical retrieval baseline;
- manual acceptance/supersession boundaries.

Experimental storage contains:

- exposure assignments and propensities;
- model-generated candidates;
- surprise, Q-value, salience, and learned-utility scores;
- replay packets, model outputs, and outcome associations.

No score may delete, overwrite, or demote the sole canonical copy. Experimental indices must be rebuildable from canonical data and versioned telemetry.

## Privacy and capture

- capture is allowlist-based, not global by default;
- redact secrets and minimize personal data before experimental processing;
- do not store private chain-of-thought;
- store only task-relevant model-visible outputs and explicit action/evidence traces;
- user deletion and export must reach canonical and experimental layers through recorded tombstone/correction events;
- external workers receive the minimum packet and never the complete private history by default.

## Relationship to emotion and salience

Outcome utility is a prerequisite for testing operational emotional salience. Appraisal factors such as novelty, consequence, urgency, control, and surprise may become candidate predictors. They cannot be validated by showing that they increase retrieval frequency. A salience policy advances only if it improves later outcomes while respecting collateral-memory, stale-procedure, privacy, and poison guardrails.

## Required artifacts before implementation

- telemetry event JSON schema and versioning rules;
- privacy/capture review and threat model;
- synthetic join/retry/correction fixtures;
- outcome definitions by authentic task family;
- exposure eligibility and safety-exclusion manual;
- power/precision plan based on T1 denominators;
- randomized assignment and rescue implementation review;
- blinded outcome-assessment plan;
- analysis code frozen before T3 outcomes are opened.

Until those exist, `execution_authorized` remains false and no adaptive policy is permitted.

