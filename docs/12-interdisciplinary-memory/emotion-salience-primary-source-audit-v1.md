# Emotion, arousal, reward, and memory — adversarial primary-source audit v1

Status: targeted primary-source audit; mechanism synthesis, not clinical guidance or architecture validation

## Question

Which findings survive after replacing the slogan “emotion strengthens memory” with phase-, target-, and task-specific comparisons?

## Evidence matrix

| Source | Intervention and task | Reported result | What it does not establish |
| --- | --- | --- | --- |
| Strange, Hurlemann, and Dolan 2003 | emotional/perceptual word oddballs; propranolol arm; selective bilateral amygdala lesions | emotional-item enhancement was coupled to impaired memory for preceding items; pharmacological blockade and lesions abolished the coupled pattern | general effect size across natural events, providers, or long histories |
| Clewett et al. 2017 | randomized propranolol/placebo emotional oddball task; final N=26 | under placebo, arousal favored prioritized preceding items at the cost of lower-priority subsequent items; propranolol changed parts of the trade-off | a global “NE score”; the salivary proxy is not privileged access to central NE |
| Smeets et al. 2008 | N=90; stress before encoding, during consolidation, before retrieval, or control; 24-hour DRM recall | consolidation stress improved true recall while retrieval stress impaired it, predominantly for emotional words | that stress always helps storage or always harms access; false recall was not changed in the same way |
| Wittmann, Dolan, and Düzel 2011 | two small human experiments crossing semantic identity versus color as reward-predictive feature | delayed recollection benefit appeared when semantic identity predicted reward, not when peripheral color did | a session-wide reward promotion rule or causal dopamine estimate |
| Schwabe and Wolf 2009 | acute stress before instrumental learning; food-outcome devaluation | stressed participants were less sensitive to outcome devaluation | a universal stress-to-habit controller |
| Zwosta et al. 2025 | two experiments, total N=129; stress/control; reward and loss-avoidance habit-goal competition | no evidence of increased habit strength or reduced goal-directed control under acute stress | that the 2009 result is impossible in its task; the two paradigms are not identical |
| Moncada and Viola 2007 | rat weak inhibitory avoidance plus nearby novel/familiar open-field exposure and pharmacological interventions | nearby novelty rescued long-term memory in a time-, D1/D5-, and protein-synthesis-dependent manner | that unrelated novelty should promote arbitrary software records or that dopamine is an implementation parameter |

## Claims retained

1. Modulation is phase-specific: encoding, post-encoding consolidation, retrieval, and reconsolidation cannot share one monotonic control rule.
2. Modulation is competitive: target gains can coexist with collateral losses.
3. Priority is feature- and task-contingent: the predictive feature matters more than generic co-occurrence in a salient session.
4. Eligibility windows are plausible abstractions, but promotion needs causal/event linkage and a raw, reversible archive.
5. Stress-driven subsystem selection is contested and must include a no-shift/null-compatible model.

## Claims rejected or withheld

- Emotion is not a truth, confidence, relevance, or retention score.
- Valence and arousal are not interchangeable.
- Model-generated dramatic language is not evidence of consequence.
- A memory system does not acquire subjective feeling by storing affect labels.
- Biological transmitters, receptors, or brain regions are not software modules or parameter values.
- Arousal must not automatically prefer procedures over evidence retrieval.

## Engineering translation boundary

The only candidate admitted to experiment design is an operational vector with provenance and uncertainty:

```text
source_of_signal: explicit_user | verified_outcome | policy | model_inference
target_feature_ids
valence
outcome_magnitude
urgency
surprise_or_prediction_error
controllability
future_need_probability
signal_confidence
eligible_actions: append | replay | protect | retrieve_more | revise_candidate
valid_from, valid_until
```

`model_inference` has the lowest default authority. None of these fields can change factual validity, delete raw events, or bypass poison/provenance checks.

## Decisive research gaps

- The source set is rich in narrow laboratory paradigms and poor in longitudinal naturalistic memory under changing goals.
- Individual, sex/hormonal, chronic-stress, developmental, and task differences can change effects; they cannot safely become demographic defaults.
- We lack independently reviewed outcome labels for project-memory events.
- We do not know whether any factor-separated controller beats raw archival retrieval at equal disk, maintenance, and context budgets.

## Sources

- https://doi.org/10.1073/pnas.1635116100
- https://doi.org/10.1016/j.nlm.2016.10.017
- https://doi.org/10.1016/j.psyneuen.2008.07.009
- https://doi.org/10.1101/lm.1996811
- https://doi.org/10.1523/JNEUROSCI.0979-09.2009
- https://doi.org/10.1371/journal.pone.0327807
- https://doi.org/10.1523/JNEUROSCI.1083-07.2007
