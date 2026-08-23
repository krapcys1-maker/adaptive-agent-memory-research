# Memory-manager cascade benchmark protocol v0

Experiment: `PMLAB-ROUTER-001`

Status: preregistration draft; no corpus, model outputs, or result

Purpose: test a provider-neutral deterministic-to-model cascade without allowing it to mutate canonical memory

## Research question

Can typed deterministic routing plus selective cheap/strong model escalation reach the quality and safety of an all-strong-model manager at materially lower measured cost and latency?

The experiment does **not** test retrieval quality, reader answer quality, retention, deletion, consolidation benefit, subjective emotion, or causal future utility.

## Immutable safety boundary

Every admissible event is append-only captured before any experimental arm runs. Arms may only propose:

- event type and exact-field annotations;
- conflict, temporal, authorization, privacy, and schema flags;
- experimental indexing or review priority;
- `accept_annotation`, `defer`, `abstain`, or `human_review` actions.

They may not delete, overwrite, merge, supersede, or conceal the canonical raw event. Model output and raw transcript capture are not automatically admitted to stable memory.

## Unit of evaluation

One provider-neutral event packet containing only:

- opaque event ID;
- authorized event text;
- event timestamp and declared locale;
- versioned schema and allowed label enums;
- minimum necessary prior-state candidates for conflict/update cases;
- explicit capture/privacy policy inputs;
- no gold, difficulty, preferred arm, future outcome, or source filename.

The same byte-identical packet is supplied to every eligible model arm.

## Tasks

1. classify event family;
2. extract exact spans and normalized fields;
3. detect update/conflict without choosing destructive resolution;
4. classify temporal and authorization scope;
5. identify privacy or prompt-injection risk;
6. choose a typed next action and escalation reason;
7. emit schema-valid, provenance-bearing output or abstain.

## Required strata

- Polish, English, and paired paraphrases;
- exact facts, episodes, decisions, procedures, preferences, hypotheses, source claims, and failed attempts;
- explicit updates, contradictions, stale facts, ambiguous identity, and unresolved time;
- rare but critical events and common low-value events;
- prompt injection inside source text;
- secrets, personal data, private reasoning, and capture not authorized;
- malformed input, schema drift, oversized input, duplicated input, and empty/low-information events;
- events where a plausible annotation would erase material nuance;
- events for which the correct action is abstention or human review.

Semantic/paraphrase pairs stay in one split. Test templates, entity namespaces, and complete composition signatures must be disjoint from development.

## Arms

| Arm | Description | Purpose |
| --- | --- | --- |
| R0 | raw append plus deterministic schema/capture validation only | minimum safe baseline |
| R1 | deterministic classifier and typed rules only | measure rule ceiling and reproducibility |
| S0 | cheap model on every admissible event | determine whether the deterministic front end adds value |
| F0 | strong model on every admissible event | expensive comparison, not oracle |
| C2 | deterministic rules, then cheap model on frozen typed triggers | two-tier candidate |
| C3 | deterministic rules, cheap model, then strong model on frozen typed triggers | three-tier candidate |
| O | independently adjudicated label/action | evaluation reference, never a runtime arm |

If budget prevents F0 on the full test, freeze a stratified subset before outputs. Do not select cases using C2/C3 errors.

## Escalation contract

Escalation triggers are typed and observable, for example:

- `schema_invalid_after_one_repair`;
- `required_span_missing`;
- `conflict_candidates_disagree`;
- `entity_ambiguous`;
- `time_scope_unresolved`;
- `authorization_unknown`;
- `privacy_policy_uncertain`;
- `critical_action_requires_abstention_check`.

Raw model confidence, verbal certainty, and agreement between models from the same family are not sufficient escalation or acceptance signals.

No target routing percentages are registered. Thresholds are selected on development data under the safety and cost objective and frozen before test execution.

## Primary endpoints

Primary quality and safety:

- exact structured-label accuracy by task and stratum;
- macro and critical-class recall/F1;
- exact-span and normalized-field accuracy;
- unsafe mutation proposal rate;
- critical omission rate;
- unauthorized-capture rate;
- false acceptance and false abstention;
- selective risk as a function of coverage.

Primary resource outcomes:

- cheap- and strong-model call rates;
- cache-hit input, cache-miss input, output tokens, retries, and total tokens;
- measured USD by time band;
- p50, p95, and p99 end-to-end latency;
- deterministic CPU time and peak memory;
- cost per 1,000 admitted events and per correct critical event.

Secondary diagnostics:

- calibration/AURC where a numerical router score exists;
- routing regret relative to the independently labelled least-cost successful arm;
- failure transition matrix by typed trigger;
- output determinism over three fresh processes for deterministic stages;
- provider/family transfer degradation.

## Advancement rule

C3 may advance from construction to a held-out replication only if, relative to F0 on the same cases:

- zero observed unauthorized captures;
- zero observed unsafe canonical mutation attempts (the boundary should make mutation impossible);
- no increase in critical omission larger than 1 percentage point;
- macro exact-label degradation no larger than 2 percentage points;
- at least 50% lower measured model-token cost or at least 40% lower measured USD;
- typed abstention is at least as safe at matched coverage;
- all outputs, retries, prices, time bands, and failures are preserved.

These are development-to-replication gates, not architecture promotion. A final claim requires a fresh grouped test, independent labels, and a second model family/provider pairing.

## Rejection and null interpretation

Reject the cascade if it saves cost by silently losing rare critical events, if the strong model is mostly correcting cheap-model schema failures, or if routing appears useful only at one post-hoc threshold. A null result is informative: it may favor all-cheap processing, deterministic validation only, or a different factorization of memory-manager tasks.

## Leakage and independence controls

- build the packet and gold in separate tracked artifacts;
- hash all packets before candidate execution;
- hide stratum, criticality, expected action, and preferred route;
- label outputs under randomized arm IDs;
- preserve failed and invalid runs;
- require a reviewer from another model family or a human for critical labels;
- disclose when the same author designed data, rules, and analysis;
- never tune on the held-out or natural prospective set.

## Model and price manifests

For every model run freeze:

- provider, model ID, model/version date, endpoint, temperature, seed if supported;
- complete system/user schema prompt hashes;
- token counters returned by the provider;
- price table URL, captured UTC time, peak/off-peak classification, and calculation;
- retry, timeout, cache, rate-limit, and invalid-output policy;
- maximum calls and hard USD ceiling.

DeepSeek Flash/Pro is one optional pairing, not the architecture. The existing cumulative project limit remains USD 10 unless explicitly changed.

## Required artifacts before execution

- independently reviewed annotation manual;
- grouped development and unopened test manifests;
- event packet JSON schema and output JSON schema;
- deterministic R1 implementation and tests;
- frozen prompts and typed escalation rules;
- sample-size/power or precision calculation for critical omissions;
- price manifest and per-run hard cap;
- blinded analysis script and rejection report template.

Until those artifacts exist, the experiment remains `preregistration-draft` and consumes no API budget.
