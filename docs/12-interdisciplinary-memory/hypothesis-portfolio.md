# Cross-disciplinary hypothesis portfolio

Status: outline

Every hypothesis is an engineering translation, not a claim of biological equivalence.

| ID | Mechanism hypothesis | Minimal comparison | Primary success signal | Critical failure / rejection |
| --- | --- | --- | --- | --- |
| XH-01 | A fast immutable episodic store plus slow evidence-linked semantic/procedural views improves specificity and generalization. | one flat store | downstream task success at equal context budget | no robust gain or more unsupported synthesis |
| XH-02 | Competitive write allocation using novelty, consequence, prediction error, and redundancy reduces harmful memory intrusion without losing critical events. | save-all and relevance-only | critical recall minus intrusion per stored/retrieved token | rare critical misses or uncalibrated salience domination |
| XH-03 | Phase-conditioned replay uses task-local contradiction-aware sampling near decisions and diverse sampling offline to improve immediate action and delayed transfer. | no replay, uniform, recency, and one-policy replay | immediate and delayed task success at equal maintenance budget | no gain over raw retrieval, rare-event loss, poison/error amplification, or procedural perseveration |
| XH-04 | Decision-conditioned rate-distortion preserves better summaries than generic summarization. | equal-length generic summary and extractive compression | counterfactual decision regret under a fixed token budget | hidden-task brittleness or loss of correction-critical detail |
| XH-05 | Prospective memories encoded as condition-action commitments outperform similarity-only retrieval for delayed intentions. | ordinary fact/episode retrieval | intention completion with low false triggering | excessive polling, missed conditions, or unsafe stale intentions |
| XH-06 | A calibrated metacognitive controller that chooses retrieve/ask/abstain lowers cost and unsupported answers. | retrieve always and never retrieve | risk-weighted utility and search-trigger calibration | critical skipped retrieval outweighs saved tokens/latency |
| XH-07 | Multidimensional operational salience improves retention beyond relevance and recency. | relevance+recency | consequence-weighted recall and recovery | retains noise, creates chronic threat bias, or collapses valence into magnitude |
| XH-08 | Pattern-separating scopes plus controlled pattern completion improve weak-cue recall without blending similar episodes. | flat dense retrieval | recall under paraphrase/distractors and false-merge rate | spurious completion or confident source confusion |
| XH-09 | Append-only atomic events, hashes, rebuildable indexes, and fault injection materially improve recoverability. | mutable database/index-only store | recovery point, integrity, and audit after induced crashes/corruption | complexity without measurable recovery benefit |
| XH-10 | Conditioned suppression is safer than irreversible deletion for adaptive forgetting. | deletion, no forgetting | retrieval efficiency plus recovery after utility shift | archive growth overwhelms maintenance or suppression leaks irrelevant items |
| XH-11 | User-visible external artifacts are sometimes superior to internal memory records. | memory-only representation | task completion, collaboration, and correction | duplicated/conflicting artifacts or lost ownership boundaries |
| XH-12 | A different-model batch worker reduces screening labor without weakening scientific integrity. | subscription/manual workflow | verified source cards per reviewer hour | locator errors, automation bias, privacy failure, or no net time saving |
| XH-13 | Explicit evidence-bearing revision with versioned supersession is safer than retrieval-triggered overwrite. | in-place overwrite, append-both, and no update | valid-time action plus delayed return and audit recovery | false supersession, stale return, scope leakage, or excessive routing cost |

## Operational emotion candidate

Do not teach the memory system a single `emotion` number. Test a vector whose components remain interpretable:

```text
outcome_valence       benefit versus harm
outcome_magnitude     size of consequence
urgency               time before consequence becomes irreversible
surprise              calibrated prediction error
controllability       whether action can prevent or reverse the outcome
uncertainty           epistemic confidence
social_or_user_weight explicit user importance and consent
recurrence            evidence that the situation repeats
```

These variables may change write priority, replay sampling, retention protection, or retrieval rank through separate ablations. They are operational control signals, not evidence that the system feels emotion.

Required emotional-salience failure tests:

- a dramatic but irrelevant event must not crowd out quiet critical evidence;
- repeated failures must not produce permanent overreaction after correction;
- negative and positive events of equal magnitude must remain distinguishable;
- user-declared importance must not override safety, provenance, or consent;
- an attacker must not gain persistence merely by using emotional language;
- the system must preserve neutral details needed to verify a salient summary.
