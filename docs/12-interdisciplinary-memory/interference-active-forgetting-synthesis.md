# Interference, active forgetting, and memory-failure localization

Status: reviewed; first primary-reading and adversarial pass complete

## Executive synthesis

An observed failure to answer is not evidence that a memory was erased. The same behavior can arise because an event was never captured, a stored representation lost decisive detail, an intact record was not retrieved, context construction selected the wrong version, or the reader failed despite receiving the gold evidence.

The engineering consequence is strict:

> No benchmark may label an end-to-end miss as `forgotten` until it has probed the stored bytes, indexes, retrieved set, constructed context, and reader separately.

Human and animal results support a functional distinction between availability and accessibility, but they do not license a literal mapping from a biological trace to a file. For a local-first agent, storage availability can be inspected directly. We should exploit that advantage instead of importing biological ambiguity into the system.

## What the evidence supports

### 1. Non-recall can coexist with preserved information

Tulving and Pearlstone held encoding constant and changed cues at test. Category cues recovered words that were unavailable to free recall, demonstrating that an output failure need not imply loss of the stored information. The study used categorized word lists and immediate tests, so it establishes a retrieval principle rather than permanence of all human memory.

The 2026 Drosophila work by Yang et al. provides a circuit-level example: behaviorally forgotten aversive information persisted in a silent trace and could be re-expressed when odor and training context were reinstated. Manipulated reminders could also distort recovery. This establishes both a recovery possibility and a recovery-integrity risk in that organism and task.

### 2. Similar or repeatedly selected memories can impair access to competitors

Anderson, Bjork, and Bjork reported that practicing retrieval of some category members improved those targets while reducing later recall of related, unpracticed members. The effect survived an output-order control and lasted at least 20 minutes in the reported paradigm. This is evidence for retrieval-induced forgetting as a behavioral effect.

It does not uniquely prove item-level inhibition. Jonker, Seli, and MacLeod produced three experiments and a context-based account in which study-to-practice context change plus practice-context reinstatement can produce the same behavioral pattern without an inhibition mechanism. Therefore `retrieval-induced forgetting` and `inhibition` must remain separate claims.

Bekinschtein et al. adapted the paradigm to rats. Across seven experiments, retrieval practice impaired competing object memories relative to time and interference controls; the effect depended on competition, generalized across test cues, lasted 24 hours, and was abolished by medial-prefrontal silencing. This strengthens the adaptive-control account but still does not identify the downstream molecular erasure mechanism.

### 3. Biological forgetting can be actively regulated

Shuai et al. reported that manipulating Rac activity in Drosophila mushroom-body neurons bidirectionally changed early olfactory-memory decay and interference-induced forgetting. Berry et al. separately reported that post-learning modulation of a small dopamine-neuron subset and the DAMB receptor altered forgetting of aversive and appetitive olfactory memories.

These are causal biological results in narrow fly conditioning paradigms. They do not imply that an agent should delete files, use one scalar decay score, or imitate dopamine. The transferable principle is that retention and accessibility can be controlled operations with distinct signals and timescales.

### 4. LLMs exhibit access interference even when the target remains present

Wang and Sun's PI-LLM benchmark repeatedly updated the same keys and asked models for the final values. Accuracy declined as competing older values accumulated even though the correct values remained in the prompt. Fixed-length controls and error-position analysis support interference rather than disk loss as the immediate failure class. Simple natural-language `forget` and focus prompts produced limited improvement; an ad hoc mock-QA reset helped but is not a general solution.

The task is synthetic, model calls were completed by May 2025, and the paper's claims about internal executive mechanisms exceed what behavioral outputs alone establish. Its public code is useful as a generator and scoring reference, not yet a trusted dependency.

### 5. Write loss and retrieval loss can be measured separately

Yu, Lin, and Wu's 2026 WhenLoss preprint evaluates one fixed reader under oracle evidence (`OE`), complete stored memory (`CSM`), and retrieved memory (`RM`). It defines:

```text
write indicator     = score(OE)  - score(CSM)
retrieval indicator = score(CSM) - score(RM)
```

On their fixed-budget LongMemEval setup, most tested baselines were write-dominant. Controlled write and retrieval degradation moved the corresponding indicator in the expected direction. The authors correctly qualify these as operational localization indicators: `OE -> CSM` can also include format or lost-context mismatch, and results depend on reader, metric, gold evidence, and budget.

## Project failure taxonomy

| Code | Failure class | Direct probe | A miss means |
| --- | --- | --- | --- |
| `F0` | capture/encoding | compare source event with write receipt and immutable event ID | required evidence never entered canonical memory |
| `F1` | storage integrity | direct ID/path read, checksum, schema and provenance validation | record is absent, corrupt, truncated, or transformed beyond recovery |
| `F2` | indexing/addressing | full scan or direct-ID oracle succeeds while registered retrieval misses | evidence is stored but not accessible through the tested index/query policy |
| `F3` | validity/selection | retrieved set contains gold but current-context set omits it or prefers stale/poisoned evidence | ranking, temporal scope, authorization, or context construction failed |
| `F4` | reader utilization | exact gold evidence is in the prompt but the fixed reader fails | reasoning, instruction following, extraction, or answer formatting failed |
| `F5` | action/evaluation | correct answer is produced but not used or is scored incorrectly | executor or evaluator failed rather than memory |

The diagnosis is the earliest failed probe in the controlled pipeline. Multiple failures may coexist and must be reported rather than collapsed into one label.

## Operational definition of active forgetting

For this project, active forgetting is a **policy-controlled reduction in default accessibility or influence**, not automatic physical deletion. Candidate operations, from most reversible to least reversible, are:

1. lower default rank while retaining direct-ID access;
2. exclude from the active index while preserving the archive;
3. require a context, role, time, or explicit recovery cue;
4. replace current use with a versioned successor while retaining history;
5. compact a derived representation with raw-evidence fallback;
6. cryptographic or physical deletion only under a separate user, privacy, or legal policy.

Retrieval frequency alone cannot authorize suppression. A frequently retrieved memory may be a recurring mistake, and a rarely retrieved memory may be safety-critical.

## Mechanism candidates retained

### Typed cue bundles

Store lexical, semantic, temporal, entity, source, task, and context cues separately. Prediction: alternate or reinstated cues recover intact records missed by one index without increasing false recovery beyond the preregistered guardrail.

### Reversible competition control

Use current-validity filters, diversity constraints, per-entity version scopes, and bounded negative rank weights instead of deletion. Prediction: stale intrusion falls while explicitly historical queries remain answerable.

### Retrieval-neighbor audit

Track which candidates repeatedly lose to retrieved records sharing a cue. Prediction: high overlap and repeated selection identify access competition that can be repaired through query diversification or scoped retrieval.

### Recovery with provenance

A recovered claim must point to the unchanged source event and identify the cue or context that made it accessible. Prediction: recovery without source identity produces more unsupported or cross-version completions than provenance-gated recovery.

## Rejected shortcuts

- End-to-end answer failure as proof of deletion or storage loss.
- A `forget this` prompt as a reliable memory-control primitive.
- Retrieval-induced forgetting as automatic proof of neural inhibition.
- Biological Rac or dopamine findings as direct parameter choices for an LLM system.
- Destructive deletion as the first response to interference.
- A single average recall score that hides current-state, historical, rare-critical, poisoned, and recovery strata.

## Architecture implications

The minimal architecture needs observable checkpoints and stable evidence IDs:

```text
source event -> write receipt -> canonical record -> index candidates
             -> retrieved set -> constructed context -> reader output -> action
```

Every experiment must save artifacts at each arrow. This diagnostic instrumentation should be built before dense retrieval, graph ranking, learned salience, or active-forgetting policies are evaluated.

## Sources examined in this checkpoint

- Tulving & Pearlstone (1966), https://doi.org/10.1016/S0022-5371(66)80048-8
- Anderson, Bjork & Bjork (1994), https://doi.org/10.1037/0278-7393.20.5.1063
- Shuai et al. (2010), abstract and bibliographic record only, https://doi.org/10.1016/j.cell.2009.12.044
- Berry et al. (2012), https://doi.org/10.1016/j.neuron.2012.04.007
- Jonker, Seli & MacLeod (2013), https://doi.org/10.1037/a0034246
- Bekinschtein et al. (2018), https://doi.org/10.1038/s41467-018-07128-7
- Wang & Sun (2025), https://arxiv.org/abs/2506.08184
- Yu, Lin & Wu (2026), https://arxiv.org/abs/2605.24579v1
- Yang et al. (2026), https://doi.org/10.1038/s41593-026-02381-2
