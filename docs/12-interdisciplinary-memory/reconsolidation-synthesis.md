# Reconsolidation synthesis: retrieval is not authorization to rewrite

Status: contested synthesis; not an architecture decision

## Evidence boundary

Animal pharmacological work supports retrieval-dependent lability under some conditions, and a prominent human fear study reported durable behavioral updating. However, large direct replication and multi-experiment sequence evidence show that reminder-plus-new-learning does not reliably rewrite human memory. Reduced expression cannot by itself distinguish erasure, durable update, inhibition, competition, or retrieval failure.

## Engineering consequences with the strongest safety case

1. **Reads are pure:** retrieval does not mutate canonical evidence or durable beliefs.
2. **Revision is explicit:** a correction is a separately authorized transaction with evidence, scope, actor, time, and reason.
3. **Raw observations persist:** corrected beliefs supersede but do not erase the event history.
4. **Competing representations may coexist:** factual belief, affective/salience response, cached procedure, and context policy can change independently.
5. **Return tests are mandatory:** probe delay, old context, old cue, stress/attack, and rollback rather than scoring only immediately after update.
6. **Eligibility is not proof:** contradiction or prediction error can open review, but cannot itself validate the new claim.

## Candidate revision state machine — hypothesis only

```text
retrieve(record) -> no mutation

observe(conflict)
  -> append conflict event
  -> verify identity, provenance, validity time, and scope
  -> propose successor belief/procedure
  -> evaluate old-context and new-context cases
  -> approve, reject, or quarantine
  -> if approved: supersede derived state; retain predecessor and evidence
```

## Storage loss versus access failure

A system that stops returning an old belief may have deleted it, suppressed it, lost its cue, reranked it, or learned a context-specific competitor. Benchmarks must include direct ID lookup, alternate cues, archive search, rollback, and provenance inspection so these failure modes are not mislabeled as successful forgetting or rewriting.

## Emotion-specific implication

An affect-like control signal and a factual proposition are separate records. A safety update may lower automatic threat priority while preserving the historical fact that a warning occurred; a factual correction may change the proposition without instantly resetting a learned caution policy. The system must not infer that altered behavior proves that factual memory was erased.

## Promotion rule

No automatic retrieval-triggered update enters the minimal architecture. Versioned explicit revision is admitted as a safety invariant; the exact trigger/router remains a benchmark candidate. Any learned updater must beat no-update, overwrite, and coexistence baselines under delayed return, false-correction, poisoning, scope, and rollback tests.

