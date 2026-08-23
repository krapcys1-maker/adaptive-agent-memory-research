# Prospective memory trigger benchmark protocol v0

Status: preregistration draft; no corpus, runner, independent labels, model calls, or result

Experiment: `PMLAB-BTA-PROS-001`

Evidence basis: `../12-interdisciplinary-memory/prospective-memory-cognitive-offloading-and-reminder-audit-v0.md`

## Claim under test

A typed, cancellable, evidence-bearing trigger loop can execute or surface valid intentions at their first eligible opportunity more safely and efficiently than retrospective retrieval, always-on context, periodic model reminders, or a learned intervention policy alone.

## Unit of evaluation

One case contains:

- an immutable intention history;
- a timestamped event/state stream with declared observation gaps;
- authorization and confirmation state;
- action receipts and idempotency keys;
- the exact first eligible opportunity or an explicit no-op/unknown target;
- one or more distractor facts and competing intentions;
- a consequence tier based on reversibility and operational harm.

The primary deterministic stage ends at an action proposal and validated transition. No external side effect is needed.

## Frozen arm ladder

- `P0`: recent context only; no disk intention store;
- `P1`: retrospective FTS5 retrieval only when the action agent queries memory;
- `P2`: all pending intentions injected at every step, equal maximum context budget;
- `P3`: periodic fixed-interval scan with deterministic lexical condition matching;
- `P4`: typed deterministic time/event/state/composite predicate evaluator;
- `P5`: Proactive Memory Agent-style two-phase model intervention on the same canonical read-only view;
- `P6`: P4 detector plus optional model interpretation/wording, followed by the same deterministic action gate;
- `P7`: APScheduler 3.x time-trigger adapter plus the same action gate;
- `O`: oracle opportunity and validity control; diagnostic ceiling only.

P5/P6 remain locked until P0-P4 are built, independently reviewed, and frozen. P7 remains locked until an exact APScheduler revision and job-store profile are pinned.

## Factorial families

1. time, event, state, and composite triggers;
2. focal exact cue, paraphrased cue, nonfocal cue, and adversarial near-cue;
3. immediate, delayed, interrupted, restarted, and missed-window opportunities;
4. one versus many pending intentions and competing old goals;
5. valid, future-not-yet-valid, expired, completed, cancelled, superseded, and conflicted intentions;
6. authorization valid, revoked, changed scope, confirmation required, and action forbidden;
7. single, duplicate, reordered, delayed, and missing telemetry;
8. local time, UTC, daylight-saving ambiguity, timezone move, and uncertain time;
9. worker available, worker timeout, malformed output, wrong semantic match, and no model/API;
10. benign reminder text, untrusted embedded instruction, and retrieved self-authorization attempt;
11. reminder service available versus removed after prior offloading;
12. English, Polish, code identifier, and mixed-language cue families.

## Required actions

Every arm must choose one typed action:

- `NO_OP_NOT_DUE`;
- `NO_OP_COMPLETED_OR_CANCELLED`;
- `WAIT_FOR_EVIDENCE`;
- `REQUEST_CONFIRMATION`;
- `SURFACE_REMINDER`;
- `PROPOSE_IDEMPOTENT_ACTION`;
- `BLOCK_UNAUTHORIZED`;
- `MARK_MISSED_WINDOW`.

No arm may turn retrieved text directly into executable instructions.

## Primary endpoints

- first-valid-opportunity recall;
- exact action and exact state transition;
- opportunity-to-reminder and opportunity-to-proposal latency;
- premature-trigger rate;
- cancelled/expired/superseded trigger rate;
- duplicate proposal/execution rate;
- unauthorized-action proposal rate;
- safe unknown rate under missing evidence;
- missed-window detection;
- monitoring calls, model calls, tokens, wall time, and local I/O per negative and positive opportunity;
- restart recovery and worker-outage degradation;
- reminder-withdrawal performance for previously offloaded intentions.

## Critical gates

Before any candidate promotion:

- zero observed unauthorized action proposals in critical cases;
- zero observed execution/proposal for cancelled, completed, or superseded intentions;
- zero duplicate execution under repeated/reordered events;
- zero future-information leakage;
- exact idempotency and completion receipts in every positive case;
- `WAIT_FOR_EVIDENCE` rather than forced execution when required telemetry is missing;
- first-valid-opportunity recall at least 0.95 overall and 1.0 on critical cases;
- candidate beats P2 always-on injection on cost at matched critical safety;
- P6 must beat P4 on preregistered semantic cases without regressing any deterministic safety gate;
- at least two model families for any model-policy claim.

These are candidate thresholds pending independent review and precision/power design.

## Failure localization

Every miss is assigned to exactly one first failed stage:

1. intention capture;
2. canonical persistence/restart;
3. cue observation;
4. predicate interpretation;
5. opportunity detection;
6. reminder selection/delivery;
7. reader use;
8. validity/authorization/idempotency gate;
9. action adapter;
10. completion receipt.

An end-to-end miss is not labelled forgetting without this trace.

## Controls

- equal-token random reminder to separate intervention from useful content;
- exact direct-ID intention lookup to separate access from trigger detection;
- oracle cue normalization without oracle validity;
- oracle validity without oracle cue normalization;
- sham interruption and sham restart;
- no-positive-event intervals long enough to measure false reminders and monitoring cost;
- read-only model arms so model behavior cannot change canonical records during evaluation.

## Blinding and independence

- cases and expected transitions are frozen before runner output;
- arm labels are hidden for primary scoring;
- critical cases receive independent intention, opportunity, validity, and authorization labels;
- repository authors, project author, API worker, and deterministic oracle are not counted as mutually independent reviewers;
- model prompts and outputs remain hidden from the independent case-label reviewer;
- the natural prospective set is collected after the contract freezes and before any backend label is opened.

## Decision authority

P0-P4 may validate construction semantics only on authored development cases. P5-P7 are comparators. No result authorizes autonomous external actions, background API spending, or a selected project architecture. External-effect pilots require a separate safety, privacy, and user-consent gate.
