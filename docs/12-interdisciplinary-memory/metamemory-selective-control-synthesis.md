# Metamemory, selective prediction, and retrieval control

Status: targeted primary-source pass complete; full systematic and independent review incomplete

## Central conclusion

A useful long-term memory system needs a meta-controller, but it should not imitate a human “feeling” with one scalar confidence. It should monitor typed evidence about capture, storage, query interpretation, retrieval, validity, context sufficiency, reader use, and action, then choose whether to answer, change search strategy, probe storage directly, ask for clarification, or abstain.

Human metamemory supplies the monitoring/control distinction and evidence that failed recall can still carry information about future retrievability. It also supplies the warning: feeling-of-knowing can be constructed from cue familiarity, partial information, and even incorrect accessible information rather than privileged access to the target trace.

Selective-prediction work supplies risk–coverage evaluation. LLM uncertainty work adds semantic rather than merely string-level disagreement. Neither establishes whether a record exists on disk; the local memory layer can and should use direct storage/provenance probes unavailable to biological subjects or opaque models.

## Evidence map

### Monitoring and control are different functions

Nelson and Narens organize metamemory across acquisition, retention, and retrieval. Monitoring includes judgments of learning, feeling of knowing, and confidence; control includes process selection, study/search allocation, and termination. The transferable abstraction is not introspection but a feedback loop: measurements change what operation runs next.

Callaway, Griffiths, Norman, and Zhang model recall as object-level evidence accumulation supervised by a meta-level policy that decides whether to continue, stop, or switch targets. Their human experiments and model comparison support a cost-sensitive search-control interpretation in their tasks. This does not identify one neural module or guarantee that a digital controller's confidence is calibrated.

### A sense of retrievability is informative but heuristic

Hart's 1965 study established the feeling-of-knowing paradigm. Koriat's three-experiment accessibility account argues that FOK is computed from accessible information during attempted retrieval, including correct and incorrect partial information, rather than direct privileged access to memory strength. Reder and Ritter's two experiments further show that familiarity with question components can drive a rapid initial FOK even when it does not track answer knowledge.

The engineering analogy is a warning: high lexical overlap, a familiar entity name, many retrieved fragments, or a fluent partial answer may make a query feel retrievable without supplying the right version or evidence. Parser v0's 1.0 observed-template score followed by 0.238 frozen-challenge recall is a project-local example of this cue-familiarity trap, not evidence that the human mechanism caused it.

### Search termination is a control decision, not proof of erasure

Miller, Weidemann, and Kahana reanalyzed 14 studies (1,079 participants and 28,015 lists) and ran a new 80-participant experiment with 9,122 lists. Recall termination became more likely over time and after errors, with patterns related to the type of intrusion. They interpret the result in terms of loss of appropriate retrieval cues. The direct implication is that a stopped search must be logged as a policy outcome with its cue history and budget, never converted into `not stored`.

### Abstention must be evaluated as risk versus coverage

SelectiveNet and earlier selective-classification work formalize a reject option and risk–coverage trade-off. This changes the target from maximum raw answer rate to minimum error at declared coverage, with abstentions measured rather than hidden.

Farquhar and colleagues group sampled generations by semantic equivalence before estimating uncertainty; their discrete variant can work without model token probabilities. Cole and colleagues report that repetition across sampled answers calibrated ambiguous-question answering better than likelihood or self-verification in their tested settings.

These methods remain reader-level signals. Repeated samples can agree on the same stale or poisoned record, and semantic entropy does not establish evidence sufficiency or disk availability. Our noisy-probe experiment independently demonstrates the general systems principle that repeated measurements sharing a failure domain are not independent confirmation.

The project-local post-hoc backend analysis supplies a direct retrieval example. Ripgrep and SQLite FTS5 jointly failed the safe-retrieval criterion on 13 of 24 existing development cases; 11 of 19 cases with the same top-ranked ID were still unsafe. Requiring top-1 agreement plus set Jaccard of at least 0.8 reduced answer coverage to 0.542 while selective retrieval risk remained 0.538. Agreement between implementations sharing lexical cues is therefore rejected as independent metamemory evidence on this corpus.

A subsequent protocol was committed before execution and replaced backend duplication with valid-time filtering, explicit trust filtering, and an authored bilingual glossary. On the same inspected development corpus, the combined arm raised safe-action accuracy from 0.458 to 0.833, lowered selective retrieval risk from 0.522 to 0.167, removed forbidden-record intrusion, and raised cross-language recall from 0 to 1.0. It nevertheless failed the frozen bundle gate because unanswerable abstention remained 0/2. Diverse cues can repair known access and selection failures, but they do not by themselves estimate evidence sufficiency.

## Typed metamemory state for this project

The meta-controller should expose a vector, not one feeling:

| Signal | Example evidence | Primary failure it addresses |
|---|---|---|
| capture status | source ID and accepted write receipt | F0 omission |
| durable availability | checksum-valid direct/raw/replica reads | F1 loss versus access |
| query resolution | entity candidates, temporal parse, ambiguity reason | parser failure |
| retrieval stability | target IDs under lexical, temporal, bilingual, and direct cues | F2 access |
| validity sufficiency | unique authorized current record or explicit conflict | F3 selection |
| evidence sufficiency | answer claims covered by source records | unsupported answer |
| reader stability | semantically clustered answers under frozen resampling | F4 use |
| action verification | fixed expected effect and judge agreement | F5 execution |
| search progress | new evidence per probe, elapsed cost, repeated intrusions | stop/switch decision |

Allowed controls are `ANSWER`, `REFORMULATE`, `CHANGE_CUE_TYPE`, `DIRECT_PROBE`, `EXPAND_SCOPE`, `ASK_CLARIFICATION`, `ABSTAIN`, and `STOP_BUDGET`. A monitor output never mutates canonical memory by itself.

## Benchmark proposal: PMLAB metamemory-control v0

### Cases

Cross stored/not-stored status with:

- default lexical success;
- alternate-cue-only recovery;
- direct-ID-only recovery;
- entity or temporal ambiguity;
- familiar poisoned distractor;
- stale version with high lexical similarity;
- semantically consistent but unsupported reader samples;
- high semantic disagreement with gold evidence present;
- missing or conflicting telemetry;
- bilingual and paraphrased cues.

### Arms

1. single-shot retrieval with no monitor;
2. model self-reported confidence;
3. cue-familiarity proxy;
4. sampled semantic-consistency score;
5. typed evidence monitor without control changes;
6. typed monitor plus fixed cue-escalation policy;
7. storage/query/reader oracle ceilings reported separately.

Monitoring and control must be ablated separately. A good score that never changes behavior is not a control improvement; a useful control based on miscalibrated monitoring may fail under distribution shift.

### Metrics

- risk–coverage curve and area under the risk–coverage curve;
- selective risk at frozen coverage points;
- Brier score and expected calibration error for recoverability and answerability;
- false-known rate: unsupported answer or wrong version accepted;
- false-unknown rate: abstention when a checksum-valid target is recoverable within budget;
- recovery yield after each cue escalation step;
- distortion and poisoned-record recovery;
- provenance-complete answer rate;
- probe, token, latency, and I/O cost;
- common-mode agreement error: consistent samples backed by the same wrong evidence;
- search-regret against an oracle action sequence.

### Candidate success gates to preregister independently

- zero unsupported answers in poisoned, conflicting-current, and missing-evidence critical strata;
- at least 15 percentage points more recovery of stored targets than single-shot retrieval with each distortion metric increasing by at most 1 point;
- risk–coverage dominance over scalar self-confidence and cue-familiarity baselines at matched coverage, with paired uncertainty intervals excluding zero;
- 100% immutable source IDs for accepted recovered answers;
- no `not stored` diagnosis unless the storage-probe contract supports it;
- no confidence benefit credited to repeated samples that share the same evidence and failure domain.

Thresholds for ECE, latency, search regret, and minimum coverage must be frozen by a reviewer before confirmatory data are examined.

## Rejected mappings

- Human FOK as proof that a memory trace exists.
- LLM verbal confidence as a privileged internal monitor.
- Familiarity or retrieval count as sufficient confidence.
- Low semantic entropy as proof of evidence correctness.
- Search timeout as evidence of deletion.
- A single arousal/emotion score as metamemory.
- Automatic rewrite or deletion triggered by uncertainty.

## Sources examined

- Hart (1965), identity/seed only: https://doi.org/10.1037/h0022263
- Nelson & Narens (1990), targeted full-text sections and framework figure: https://doi.org/10.1016/S0079-7421(08)60053-5
- Reder & Ritter (1992), abstract/method-result summary: https://doi.org/10.1037/0278-7393.18.3.435
- Koriat (1993), abstract plus author full text: https://doi.org/10.1037/0033-295X.100.4.609
- Miller, Weidemann, and Kahana (2012), full article: https://doi.org/10.3758/s13421-011-0178-9
- Callaway et al. (2024), targeted full-text model and experiment sections: https://doi.org/10.1037/rev0000441
- Geifman & El-Yaniv (2019): https://proceedings.mlr.press/v97/geifman19a.html
- Farquhar et al. (2024): https://doi.org/10.1038/s41586-024-07421-0
- Cole et al. (2023): https://doi.org/10.18653/v1/2023.emnlp-main.35

## Remaining evidence work

- fully read Hart and Reder/Ritter rather than relying on identity/abstract-level extraction;
- find direct and conceptual replications plus calibration failures for FOK and cue familiarity;
- compare gamma correlation, signal-detection, calibration, and control-utility measures in metamemory;
- reproduce semantic-consistency and selective-prediction baselines on the frozen project corpus;
- obtain an independent reviewer for case labels, action utilities, and risk–coverage gates.
