# Emotion and salience synthesis: control signals, not a truth score

Status: extracted synthesis; not an architecture decision

## Adversarial primary-source update

The strongest transferable result is selectivity, not strength. Human oddball and pharmacological experiments report paired benefits and costs: an arousing item or prioritized representation can be retained better while nearby or lower-priority material is retained worse. A 90-participant phase manipulation also reported opposite effects when acute stress targeted consolidation versus retrieval. Therefore `arousal -> importance` and `emotion -> retain more` are rejected translations.

The proposed stress-driven shift from goal-directed control to habit is also not a stable general law. A 2009 food-outcome devaluation study reported such a shift, while two 2025 habit-goal competition experiments totaling 129 participants found no acute-stress effect on habit strength for reward or punishment avoidance. Task, timing, outcome, and individual response are moderators to test, not nuisance variables to average away.

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
6. **Collateral-memory accounting:** every gain for a salient target must be paired with loss measurements for quiet, adjacent, peripheral, and competing evidence.
7. **No hard-coded subsystem shift:** arousal or negative valence cannot automatically select a cached procedure; current evidence and outcome validity must remain decisive.

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

## Current conclusion

Do not attempt to teach an LLM subjective emotion as the memory mechanism. The testable candidate is an external, provenance-bearing control vector that may affect provisional eligibility, replay scheduling, retention protection, or a request to retrieve more evidence. Factual validity and canonical storage authority remain separate. Each control edge must win its own ablation; a single successful aggregate does not license all four.
