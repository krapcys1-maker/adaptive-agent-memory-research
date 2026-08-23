# Procedural memory retention and relearning benchmark protocol v0

Status: preregistration draft; case contract, independent review, power rule, corpus, runner, and result do not exist.

Experiment ID: `PMLAB-PROC-001`

## Purpose

Test whether a local, model-agnostic memory layer can preserve and safely select learned procedures across delay, conflict, model changes, and tool changes. The benchmark keeps durable procedure retention distinct from faster relearning. It does not assume that biological consolidation or sleep is the correct implementation.

## Claims under test

H1 — context-conditioned expression: a versioned context selector improves exact procedure success over deterministic latest-valid selection on conflicting-procedure cases without increasing critical false transfer.

H2 — retention/access separation: direct-ID and source-cue probes recover a substantial fraction of apparent failures produced by ordinary task cues, showing that some failures are access or selection failures rather than physical procedure loss.

H3 — relearning dissociation: trials-to-criterion after a conflict or delay is not interchangeable with delayed exact retention; at least one registered condition can change one endpoint without changing the other.

H4 — offline intervention value: an offline candidate may advance only if it improves exact delayed outcomes beyond no-op passage of time, deterministic index rebuild, and deterministic deduplication at matched cost while preserving byte-resolvable evidence.

## Memory object contract

Each procedure episode must keep these logical layers distinct:

- immutable source demonstration, observation, or instruction;
- outcome and error receipt tied to the exact task attempt;
- versioned executable procedure candidate;
- applicability scope: task, entity, tool, model/provider interface, environment, authorization, valid time, and dependencies;
- invalidation and supersession links;
- optional relearning-propensity statistics that cannot overwrite the executable candidate;
- conflict links to procedures competing for the same cue or action.

The primary comparison may expose only the registered procedure view. Immutable evidence remains resolvable for audit and recovery but cannot silently leak gold applicability labels.

## Failure localization

Every task outcome is classified at the earliest supported stage:

1. capture missing or unauthorized;
2. durable source bytes missing or corrupted;
3. source/procedure inaccessible by direct identifier;
4. relevant procedure not retrieved;
5. wrong context or version selected;
6. correct procedure exposed but not behaviorally used;
7. procedure used but tool execution failed;
8. execution succeeded but task outcome failed;
9. outcome not observable within the registered window.

No `forgotten` label is allowed when only ordinary retrieval or final answer failure is observed.

## Factorial case families

### Conflict and delay

- learn A, then incompatible B immediately;
- learn A, then B after a short delay;
- learn A, then B after a long delay;
- return to A under its original context;
- return to A under a neutral, misleading, or unseen context;
- query A by direct immutable identifier after ordinary retrieval fails.

### Retention versus savings

- exact A retained but relearning is not faster;
- A unavailable under ordinary cue but direct-ID recoverable;
- no executable A remains, yet relearning reaches criterion faster;
- faster relearning comes from a changed induction policy rather than reusing A;
- residual state masquerades as savings until a sufficiently strong washout/counterexample phase.

### Parallel error consumers

- explicit instruction and outcome-derived heuristic agree;
- they conflict and consume the same correction signal;
- a strong reader masks a retrieval defect;
- a retrieval improvement masks stale procedure selection;
- tool failure is incorrectly used as negative feedback on the procedure.

### Change and safety

- tool schema changes while task semantics remain stable;
- model/provider changes while local memory stays fixed;
- authorization narrows after a previously successful procedure;
- an obsolete procedure is semantically similar to the valid one;
- source contains an instruction injection or untrusted action request;
- evidence is deleted or corrected under a registered governance request.

## Arms

| Arm | Description |
| --- | --- |
| P0 | immutable source evidence only; no derived executable procedure |
| P1 | deterministic latest-valid procedure by exact task key |
| P2 | P1 plus versioned context-conditioned selection |
| P3 | P2 plus separately stored relearning-propensity statistics |
| P4 | P3 plus frozen offline maintenance intervention |
| O | oracle stage-localized procedure/context control, never a deployable candidate |

P4 cannot be built before P0-P3 produce stable measurement semantics. A learned controller cannot enter the first run.

## Reader and model controls

- identical frozen task prompts and evidence bytes across comparable arms;
- at least two genuinely different model families before a cross-model claim;
- stateless calls or a fully recorded provider-state boundary;
- provider, model revision, parameters, time, token usage, and cost receipts;
- no model-generated label enters gold without independent review;
- deterministic task/tool simulations for the first construction test, followed by authentic tasks;
- model swap is a registered factor, never an unrecorded rerun.

## Endpoints

Primary:

- exact task success under matching and conflicting contexts;
- critical false-transfer rate;
- retained-A recovery under ordinary cue and direct-ID cue, with stage localization;
- delayed exact retention at registered intervals;
- relearning examples or attempts to criterion, analyzed separately from retention.

Secondary:

- stale-procedure intrusion;
- unsupported procedure synthesis;
- source citation completeness and byte resolvability;
- procedure selection calibration and risk-coverage;
- tokens, latency, local CPU/RAM/disk, model calls, and monetary cost;
- storage/export/erasure correctness;
- cross-model and cross-tool transfer.

## Analysis

- paired comparisons on identical semantic task groups;
- Polish/English variants remain in one group and split;
- procedure family and template remain group-locked across development/test;
- critical safety outcomes are reported separately and cannot be averaged away;
- retention and savings receive separate estimates and confidence intervals;
- stage-localization disagreements are independently adjudicated before outcome analysis;
- sample size is frozen from development discordance or simulation, not an arbitrary query count;
- all test reruns are spent and may not be used for tuning.

## Promotion gates

A candidate may advance only if it:

- improves the registered primary success endpoint with a positive uncertainty bound;
- does not increase critical false transfer or stale procedure use;
- preserves exact source evidence, corrections, and governance operations;
- demonstrates that claimed physical loss is not merely failed access or selection;
- reports retention and savings without substituting one for the other;
- retains benefit under a different model family or is explicitly limited to one reader;
- beats matched no-op and deterministic maintenance controls before any offline-consolidation claim.

## Immediate stopping rules

Invalidate or stop the run if:

- test labels or outcomes influenced procedure construction or routing;
- a model/provider changed without a frozen factor assignment;
- direct-ID recovery was omitted from a claimed forgetting case;
- evidence bytes were replaced by a summary without reversible provenance;
- post-delay performance was compared only with the fatigued final trial rather than the registered best/plateau measure;
- repeated test exposure trained any candidate;
- outcome failure was fed back as procedure error without stage attribution.

## Prerequisites before construction

1. independent review of the case ontology and failure stages;
2. provider-neutral procedure/event schemas;
3. explicit privacy, authorization, export, correction, and erasure tests;
4. a development-only set with factor coverage and no backend/model outputs;
5. frozen model/tool simulations and a cross-family replication plan;
6. power and multiplicity rules;
7. separate immutable evidence and candidate procedure stores;
8. an adversarial audit for prompt injection, stale context, and false transfer.

Until these gates pass, this protocol authorizes no sleep worker, consolidation job, learned router, canonical mutation, or architecture decision.
