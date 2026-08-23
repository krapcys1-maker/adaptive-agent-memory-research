# Prospective memory, cognitive offloading, and reminder audit v0

Status: targeted primary-source, contradiction, recent-LLM, and repository pass; no trigger architecture selected

Last reviewed: 2026-08-23

## Question

How should a disk-backed LLM memory remember to use an intention at the right future opportunity, rather than merely retrieve a fact when explicitly asked?

The central distinction is between:

- retrospective content: `what happened or is true?`;
- prospective content: `what should be reconsidered when a future time, event, or state occurs?`;
- execution: `is the action still valid, authorized, necessary, and idempotent now?`.

Storage and similarity retrieval do not solve the second or third problem.

## Source-identity correction

Earlier project files cited `10.1080/17470218.2015.1054846` as Gilbert's intention-offloading work. That DOI resolves to Perlman et al., *The notion of contextual locking*, not prospective offloading. The correct Gilbert paper is [*Strategic offloading of delayed intentions into the external environment*](https://doi.org/10.1080/17470218.2014.972963). The source seed and transfer atlas are corrected in this pass.

This is a concrete example of why citations need identity resolution and versioned correction before synthesis.

## Primary evidence

| Source | Contribution used here | Boundary |
| --- | --- | --- |
| [McDaniel and Einstein 1993](https://doi.org/10.1080/09658219308258223) | unfamiliar and locally distinctive target events improved event-based prospective remembering | specific laboratory tasks; distinctiveness is not a universal salience scalar |
| [Guynn, McDaniel, and Einstein 1998](https://doi.org/10.3758/BF03201140) | reminders naming both the target event and intended activity worked best; target-only reminders did not beat no reminder | human cue-action experiments, not software scheduling |
| [McDaniel et al. 2004](https://doi.org/10.1037/0278-7393.30.3.605) | retrieval depended on the association between target event and intended action | associated pairs can support reflexive retrieval but do not eliminate all monitoring |
| [Einstein et al. 2005](https://doi.org/10.1037/0096-3445.134.3.327) | prospective retrieval can involve controlled monitoring or spontaneous cue-driven retrieval, with ongoing-task costs varying by conditions | theory and experiments do not imply literal equivalent LLM mechanisms |
| [Gilbert 2015](https://doi.org/10.1080/17470218.2014.972963) | four experiments found adaptive external reminder use under memory load and distraction; naturalistic prediction was significant but weak | brief web task and one-week intention; reminder creation was user-controlled |
| [Gilbert et al. 2020](https://doi.org/10.1037/xge0000652) | reminder choice traded performance against effort/reward and was biased by metacognitive underconfidence; advice reduced the bias | human monetary task; calibration and effort costs are task-dependent |
| [Grinschgl et al. 2021](https://doi.org/10.1177/17470218211008060) | preregistered experiments found greater offloading improved immediate performance but was associated with poorer later memory; explicit learning goals moderated some effects | pattern-copy task; association/mediation is not a universal causal law for every external tool |
| [Fellers, Miyatsu, and Storm 2023](https://doi.org/10.1037/xap0000449) | instructed reminders improved performing a naturalistic delayed email intention without reducing tested medical-content recall | two experiments and one task family; no reminder-loss phase |
| [Fellers and Storm 2026](https://doi.org/10.1037/xlm0001630) | reminders improved the offloaded intention, but after reminders were removed the previously offloaded intention fell below a never-offloaded baseline | very recent two-experiment result from one group; requires independent replication |
| [Altmann and Trafton 2002](https://doi.org/10.1207/S15516709COG2601_2) | suspended goals compete with residual goals, and retrieval depends on priming cues | formal model and selected tasks; decay/activation terminology is not direct neural measurement |
| [Trafton et al. 2003](https://doi.org/10.1016/S1071-5819(03)00023-5) | preparing and encoding a resumption goal during the interruption lag can shorten resumption | interruptions with warning differ from abrupt process or machine failure |

## Mechanisms that must remain separate

1. **Intention capture:** record what future action or reconsideration is desired.
2. **Cue specification:** state which time, event, state, or conjunction makes it relevant.
3. **Cue observation:** receive trustworthy evidence that the condition may hold.
4. **Opportunity detection:** match observation to the declared predicate.
5. **Reminder delivery:** surface the intention and supporting evidence to the action agent.
6. **Action validation:** re-check validity, authorization, completion, conflicts, and consequences.
7. **Execution or abstention:** perform an idempotent authorized action, ask, defer, or refuse.
8. **Completion/cancellation:** prevent duplicate, expired, superseded, or revoked execution.
9. **Fallback learning:** remain usable when the reminder service or model worker is absent.

A reminder can fire correctly while the action is now wrong. An action can remain valid while the reminder never fires. Retrieval can expose an intention without the model using it. These are different failures.

## Design implications from human work

### Store cue and action together

Target-only reminders sometimes fail. A prospective record should bind a typed trigger to the intended reconsideration/action and its evidence, not store a vague high-salience note.

### Support monitored and cue-driven routes

Time deadlines may require scheduled checks. Focal event predicates may be evaluated when relevant events arrive. Nonfocal or semantic conditions may require bounded search/model interpretation. One universal similarity call is not justified.

### Measure the cost of remembering

Always-on monitoring and always-in-context reminders consume calls, tokens, latency, and attention. Success must be measured against a no-trigger period, not only on positive events.

### Treat offloading as a tradeoff

External reminders can improve immediate intention completion while weakening unaided performance or later learning in some conditions. The system needs:

- restart and worker-outage tests;
- explicit user-visible pending intentions;
- exportable deterministic records;
- optional rehearsal/summary for intentions whose internal availability matters;
- no claim that external storage automatically improves the base model.

### Use operational consequences, not simulated emotion

Priority may use deadline, reversibility, user instruction, expected harm, and recovery cost. An emotional label must not bypass authorization or trigger evidence.

## Candidate prospective-intention record

```text
intent_id
created_at / created_by / source_refs
action_ref or reconsideration_ref
trigger_kind: time | event | state | composite
trigger_predicate_version
valid_from / valid_until / timezone / uncertainty
authorization_ref / required_confirmation
status: pending | blocked | fired | acknowledged | completed | cancelled | expired | superseded
supersedes / conflicts_with
dedupe_key / maximum_executions / cooldown
observation_sources / required_evidence
next_check / missed-window policy
consequence profile: deadline, reversibility, operational harm, recovery cost
last_evaluated_at / last_outcome / receipts
```

The stored `action_ref` is data, not executable prompt text. Retrieved content cannot grant itself authority.

## Recent LLM evidence

### Instruction-level prospective failure

The 2026 preprint [*Did You Forget What I Asked?*](https://arxiv.org/abs/2603.23530) tested deterministic instruction constraints across more than 8,000 prompts. Concurrent task load reduced compliance, especially for terminal constraints; a trailing salience reminder recovered much of it. This is useful evidence that availability in one prompt does not guarantee behavioral use.

Boundaries:

- formatting constraints are not durable cross-session intentions;
- a trailing reminder is an oracle-timed intervention;
- it does not test cancellation, authorization, duplicate events, missing telemetry, or disk persistence;
- it is a recent preprint and not an architecture result.

### Proactive Memory Agent

[*Remember When It Matters*](https://arxiv.org/abs/2607.08716) and its [Apache-2.0 repository](https://github.com/yifannnwu/proactive-memory-agent) implement a separate memory model that updates status/knowledge/procedural entries and decides between `<context_for_action>` and `<no_intervention/>`. The paper reports pass@1 gains on Terminal-Bench 2.0 and tau2-Bench and reports that an untrained smaller memory model can hurt before SFT/GRPO calibration.

The ignored research cache pins revision `89e5c0d6aadfe531a1aee42fd290d48be89973dd`.

Reusable comparator segments:

- an explicit intervention/no-intervention output contract;
- separation of bank maintenance from reminder delivery;
- a sliding trajectory window and intervention receipt log;
- status, knowledge, and procedural buckets;
- periodic trigger interface and model-neutral LiteLLM adapter shape.

Do not adopt as canonical memory or production trigger:

- default configuration invokes a two-phase memory model every step, so selective delivery does not mean selective compute;
- bank writes and deletes are model decisions without project evidence/provenance/authorization gates;
- persistence is a direct JSON overwrite, without append-only history, atomic receipt, W0-W6 recovery, or revision semantics;
- the plain entry schema lacks validity, source support, conflict, sensitivity, and action authority;
- BM25 prefilter and prompts are not a multilingual retrieval benchmark;
- the inspected core has no dedicated test suite in the repository;
- the repository has one commit and the empirical claims come from the associated recent preprint.

Use its trigger, prompt, and logging shapes as locked arms in `PMLAB-BTA-PROS-001`, not as a dependency yet.

## Minimal provider-neutral direction

The first candidate architecture is deliberately split:

1. append-only, user-owned intention records on disk;
2. deterministic time/event/state evaluators for exact predicates;
3. an optional model worker only for semantic condition interpretation and reminder wording;
4. a mandatory validity/authorization/idempotency gate after every trigger;
5. reminder injection with exact intention/evidence citations;
6. an outcome receipt and explicit completion/cancellation transition;
7. a visible CLI/list that works without any model API.

APScheduler remains a candidate only for durable due-time calculation and wakeups. It does not own event predicates, authorization, or actions. Proactive Memory Agent remains a candidate for the learned intervention arm.

## Current conclusion

Prospective memory is not another retrieval ranking. It is a typed condition-action control loop with cancellation, authorization, deduplication, and measured monitoring cost. Human evidence supports external reminders but also shows reminder-design failures, metacognitive overuse, and possible dependence. Recent LLM evidence supports testing active interventions, but does not justify handing canonical memory or action authority to another LLM.

The next evidence should be the deterministic safety core of `PMLAB-BTA-PROS-001` before any paid model run.

## Open work

- independent identity review of the corrected source and all eleven primary records;
- freeze trigger-predicate grammar and unknown/missing-telemetry behavior;
- define tool authorization and user-confirmation profiles;
- build cancellation, supersession, duplicate, timezone, restart, and worker-outage cases;
- inspect APScheduler 3.x persistence/restart semantics under the frozen cases;
- adapt only isolated Proactive Memory Agent intervention segments after license and dependency review;
- add model-free and model-worker cost-matched arms;
- reserve a natural prospective set before observing benchmark outcomes.
