# Emotion and salience synthesis: control signals, not a truth score

Status: extracted synthesis; not an architecture decision

## What the second full-reading batch changes

The phrase "emotion improves memory" is too coarse to engineer or test. The sources separate at least six mechanisms:

| Mechanism | Candidate computational translation | Main risk |
| --- | --- | --- |
| arousal/stress | change controller state and subsystem selection | habit/perseveration and loss of context sensitivity |
| reward/consequence | prioritize task-relevant predictive features | session-wide promotion of irrelevant co-occurrences |
| novelty | provide a time-bounded persistence/modification signal | retaining random anomalies or attacks |
| surprise/prediction error | open a model-update window | confusing noise with structural change |
| encoding duration/coverage | retain enough discriminating detail | coarse memories applied too broadly |
| neuromodulatory timing | gate encode/retrieve/consolidate operations | same signal can help or harm at another phase |

Valence and subjective feeling are not reducible to these mechanisms. An engineered controller may use explicit user-declared affective metadata without claiming an LLM experiences emotion.

## Strongest design implications to test

1. **Feature-contingent importance:** attach consequence to the evidence feature that predicts the outcome, not every item in the same session.
2. **Eligibility before permanence:** first append an episode and mark it provisionally eligible; promote derived semantic/procedural state only after a verified later signal and within a recorded time window.
3. **Precision guardrail:** high recall with context overgeneralization is failure. Test safe/near-neighbor contexts.
4. **Subsystem-shift guardrail:** high arousal/consequence must not suppress evidence retrieval in favor of a familiar cached procedure.
5. **Phase-aware control:** encode, retrieve, consolidate, revise, and abstain are separate actions. One scalar cannot safely select all of them.

## Candidate record fields — research hypothesis only

```text
event_time, observation_time, validity_time
valence, arousal, user_importance
consequence_weight, reward_contingent_feature
novelty, prediction_error, model_change_probability
encoding_coverage, specificity_scope
eligibility_created_at, eligibility_expires_at
promotion_reason, promotion_evidence_ids
controller_action, controller_confidence
```

These fields must remain optional, provenance-bearing, and independently ablated. Model-inferred emotion is lower trust than explicit user labels and cannot establish factual truth.

## Falsification criteria

Do not admit an emotion/salience controller if it:

- improves weighted recall only by storing/retrieving much more;
- increases false generalization to similar contexts;
- promotes emotionally worded poison or misinformation;
- increases habitual/procedural responses when evidence contradicts them;
- cannot beat consequence-only and uncertainty-only baselines;
- depends on hidden test answers or one model's self-judgment.
