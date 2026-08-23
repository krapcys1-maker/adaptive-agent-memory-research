# Motor consolidation, savings, and context audit v0

Status: targeted primary-source and contradiction pass; design hypotheses only, no biological mechanism is selected for the LLM memory architecture.

## Research question

What does human motor-memory evidence actually justify about offline consolidation, interference, faster relearning, context-dependent recall, and parallel learning systems?

The engineering temptation is to translate `sleep -> consolidate procedures` or `savings -> durable stored procedure`. The literature does not support either shortcut. Motor sequence skill, force-field adaptation, and visuomotor rotation are different tasks; resistance to interference, post-delay retention, post-sleep performance, aftereffects, and relearning speed are different endpoints.

## Endpoint decomposition

| Endpoint | Operational question | Confound that must be separated |
| --- | --- | --- |
| End-of-practice performance | What can the participant do now? | fatigue, reactive inhibition, strategy, speed/accuracy tradeoff |
| Delayed retention | What performance remains after a fixed delay? | time of day, warm-up, test-induced relearning, changed context |
| Interference resistance | Does task B degrade later expression of task A? | retrograde versus anterograde interference and retrieval blocking |
| Offline enhancement | Is delayed performance above the best pre-delay level? | averaging artifacts and restoration from fatigue |
| Savings | Is relearning faster than initial learning? | residual state, explicit strategy, changed learning rate, volatile process |
| Transfer/generalization | Does learning help in a changed effector, target, or context? | task similarity and cue-dependent selection |
| Aftereffect | Does adapted output persist when the perturbation is removed? | implicit recalibration versus intentional strategy |

These measures must not be collapsed into one `memory strength` score.

## Primary evidence and contradictions

### Time-dependent protection is task- and protocol-dependent

Brashers-Krug, Shadmehr, and Bizzi reported that learning an opposing force field immediately after the first disrupted later expression, while a delay of roughly four hours reduced the disruption. The influential interpretation was a time-dependent transition from fragile to protected motor memory. The study established a behavioral interference pattern, not a universally protected procedure store. [Brashers-Krug et al. 1996](https://pubmed.ncbi.nlm.nih.gov/8717039/)

Caithness and colleagues then ran experiments across three laboratories. Opposing visuomotor rotations and position- or velocity-dependent force fields produced complete interference even when separated by 24 hours or one week, including washout conditions intended to control anterograde interference. This directly contradicts a universal time-only protection rule. [Caithness et al. 2004](https://pubmed.ncbi.nlm.nih.gov/15470131/)

Krakauer, Ghez, and Ghilardi found a conditional result in visuomotor rotation: without washout, interference persisted at 24 hours; with washout, 24-hour but not five-minute spacing yielded resistance; doubling initial training produced resistance even at five minutes. Their interpretation distinguishes retrograde disruption from anterograde retrieval interference. The result also shows that elapsed time, training amount, and test protocol can produce similar observed protection. [Krakauer et al. 2005](https://pubmed.ncbi.nlm.nih.gov/15647491/)

Conclusion: `A was not expressed after B` is not sufficient evidence that A was erased or never consolidated. Storage integrity, access, selection, current context, and behavioral expression must be localized separately—consistent with the project's existing availability-versus-accessibility branch.

### Sleep enhancement can be stabilization or fatigue recovery

Rickard and colleagues identified averaging, reactive inhibition, time-of-day, time-since-sleep, and massed-practice fatigue as alternate explanations for post-sleep finger-sequence gains. In two experiments, controlling or reducing these factors eliminated enhancement; they left open a possible protective role against forgetting. [Rickard et al. 2008](https://pubmed.ncbi.nlm.nih.gov/18605872/)

Sheth and colleagues reported early training gains followed by reduced learning efficacy or partial reversal, with sleep restoring performance toward an earlier attainable level. Their restorative interpretation is not evidence that sleep wrote additional skill content. [Sheth et al. 2008](https://doi.org/10.1371/journal.pone.0003190)

A later finger-tapping experiment measured an early post-training boost and concluded that sleep stabilized performance at or restored it to that level rather than enhancing it beyond the pre-sleep maximum. [Nettersheim et al. 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4412892/)

Landry and colleagues assigned 44 participants to uninterrupted NREM nap, fragmented NREM nap, quiet wake, or active wake. All groups improved after a short ten-minute rest, while no additional sleep- or wake-condition gain appeared across the longer interval. This makes the measurement time immediately around practice a first-class design variable. [Landry et al. 2016](https://pubmed.ncbi.nlm.nih.gov/26655281/)

Conclusion: an offline maintenance job must be compared with no-op passage of time, immediate rest, cache/fatigue recovery, and ordinary deterministic maintenance. A later performance increase does not by itself establish useful consolidation.

### Savings is not equivalent to durable retention

Hadjiosif, Morehead, and Smith separated visuomotor adaptation into components measured around 60-second delays. Across 118 participants in four main experiments plus a control, their temporally persistent component predicted 24-hour retention but not savings. The temporally volatile component produced savings but not long-term retention; persistent adaptation could even show anti-savings. They also used an 800-trial washout because shorter washout could leave persistent residuals masked by an opposing volatile component. Data and analysis code were released. [Hadjiosif et al. 2023](https://doi.org/10.1371/journal.pbio.3001799)

This is decisive for benchmark design: faster relearning can reflect an altered learning propensity rather than retrieval of a durable stored output. Conversely, durable retained state need not make reacquisition faster.

### A visible learning curve can mix competing systems

Albert and colleagues modeled and experimentally tested explicit strategy and implicit adaptation as parallel systems that can compete for a shared task-error signal. Increasing one contribution can reduce the other's observed learning without changing its intrinsic retention or sensitivity. Thus aggregate performance can change because the mixture changed, not because one memory trace was strengthened or weakened. [Albert et al. 2022](https://doi.org/10.7554/eLife.65361)

Heald, Lengyel, and Wolpert compared context-dependent inference with conventional multi-rate explanations across sensorimotor phenomena. Their COIN account dynamically expresses and updates multiple context-specific memories according to inferred context. The paper supports context-conditioned selection as a serious model of behavioral expression, but it does not establish that an LLM should copy the biological model or its parameters. [Heald et al. 2021](https://doi.org/10.1038/s41586-021-04129-3)

## What survives translation

The strongest computational abstractions are separations, not copied mechanisms:

1. **Stored procedure versus learning propensity.** Preserve a versioned executable procedure separately from statistics that alter how quickly a new procedure is induced.
2. **Retention versus accessibility.** Test a procedure under its original cue, a conflicting cue, a neutral cue, and an explicit source locator before declaring loss.
3. **Multiple timescales.** Permit fast volatile adaptation and slow persistent state as candidates, but identify them from interventions rather than fitting one aggregate curve.
4. **Context-conditioned expression.** Record task, tool, model, environment, authorization, version, and validity interval; never infer that the newest or strongest procedure is globally appropriate.
5. **Parallel error consumers.** Separate errors attributed to retrieval, reader reasoning, tool execution, and final outcome. Improvements in one stage can hide failure or reduce training signal in another.
6. **Offline maintenance as a controlled intervention.** Consolidation, deduplication, summarization, rehearsal, and index rebuilding need separate arms and immutable source evidence.

## Benchmark consequences for LLM procedural memory

`PMLAB-PROC-001` should be designed before any sleep-inspired worker is implemented.

### Required memory objects

- immutable source demonstrations and outcome receipts;
- versioned procedure candidate with applicable task/tool/model/environment scope;
- explicit dependencies, preconditions, invalidation conditions, and provenance;
- learning-propensity state stored separately from the current executable procedure;
- conflict links between procedures that compete for the same cue or action.

### Factorial cases

- A then conflicting B at immediate, short-delay, and long-delay intervals;
- same procedure under matching, neutral, misleading, and unseen contexts;
- a retained but suppressed A recoverable by direct identifier;
- apparent improvement caused only by removal of temporary noise or reader fatigue;
- faster relearning with no retained executable output;
- retained executable output with no savings;
- parallel explicit rule and implicit outcome-derived heuristic that consume the same error;
- changed tool or model version that makes a once-valid procedure stale.

### Arms

- immutable evidence only;
- deterministic latest-valid procedure selection;
- procedure plus context-conditioned selection;
- procedure plus separate relearning-propensity statistics;
- offline compaction/rehearsal candidate;
- oracle stage-localized control for storage, access, selection, execution, and outcome.

### Primary metrics

- exact procedure success and critical failure rate under matching and conflicting contexts;
- source-evidence preservation and citation completeness;
- retained-A recovery after B, with storage/access/selection/execution localization;
- savings as trials or examples to criterion, reported separately from delayed retention;
- false transfer to a superficially similar but incompatible context;
- stale-procedure intrusion and unsupported procedure synthesis;
- offline intervention benefit relative to no-op, index rebuild, and deterministic deduplication at matched cost.

### Rejection gates

Reject the candidate mechanism if any of the following holds:

- it improves aggregate relearning while worsening delayed exact retention or critical outcomes;
- a claimed forgotten procedure remains directly recoverable, showing access rather than storage loss;
- apparent offline gain disappears when compared with the best pre-delay performance or a short-rest control;
- context routing increases unsafe transfer or suppresses the correct procedure without a recoverable trace;
- compaction destroys immutable evidence or makes procedure provenance unresolvable;
- performance gains can be explained by model/provider change, repeated test exposure, or outcome leakage.

## Current conclusion

The evidence supports a benchmark family, not a sleep module. The project should treat procedure state, access, context selection, execution, delayed retention, and reacquisition speed as separate variables. The most promising near-term analogy is context-conditioned expression over preserved versioned procedures; the most important warning is that savings is not a proxy for durable memory.

## Open searches

- preregistered or high-powered direct replications of the 2023 volatile/persistent dissociation;
- applied motor skills outside finger tapping and laboratory cursor/robot perturbations;
- long-delay retention with direct context manipulation and explicit source-recovery tests;
- null results for context-conditioned multi-memory models;
- causal sleep or replay interventions that separate stabilization from rest and fatigue recovery;
- clinical and aging samples to test whether the endpoint separations generalize.
