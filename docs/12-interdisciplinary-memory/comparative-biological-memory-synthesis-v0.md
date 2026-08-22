# Comparative biological memory v0: representations, response states, savings, and transfer

Status: targeted primary-source pass; not a systematic review and not an architecture decision

## Research question

What survives if “memory” is defined by a measurable write–persistence–read relation rather than by resemblance to human recollection?

The cross-domain answer is not one universal mechanism. At least four different phenomena are routinely called memory:

1. **Representational memory:** a past episode or invader leaves content that can later be matched or reconstructed.
2. **Response-state memory:** exposure changes the probability or magnitude of a later response.
3. **Savings or priming:** baseline behavior may return, yet relearning or reactivation is faster.
4. **Transferred or inherited state:** an altered response crosses cell, lineage, or collective boundaries through a physical substrate.

These meanings must not share one benchmark. Persistence of bytes does not prove usable recall; faster response does not prove preservation of an episode; a transferred physiological state does not preserve semantic provenance.

## Primary-source audit

| System and source | Write / persistence / read observation | What is justified | Boundary or contradiction |
| --- | --- | --- | --- |
| Scrub-jay cache recovery, Clayton & Dickinson 1998, DOI `10.1038/26216` | caching supplies item, location, and time; recovery changes with food perishability and delay | integrated what–where–when behavior with type-specific validity horizons | “episodic-like” behavioral criterion, not evidence of autonoetic experience; narrow ecological task |
| *Physarum* habituation, Boisseau et al. 2016, DOI `10.1098/rspb.2016.0446` | repeated harmless quinine/caffeine exposure reduced avoidance; withholding restored it; response remained stimulus-specific | reversible suppression can save effort while preserving response to a different cue | same-group replication and molecular mechanism were initially absent; adaptation/fatigue must be excluded experimentally |
| *Stentor* single-cell habituation, Rajan et al. 2023, DOI `10.1016/j.cub.2022.11.010` | calibrated mechanical stimulation changed individual cells with a step-like switch; population curves appeared gradual because switch times differed | population averages can hide discrete heterogeneous state changes; inter-stimulus timing matters | two-state stochastic behavioral model does not identify the molecular storage substrate |
| *Physarum* dormancy, Boussard et al. 2019, DOI `10.1098/rstb.2018.0368` | sodium exposure altered later avoidance, sodium was retained through sclerotium dormancy, and the response remained after one month | a retained material can implement a durable response state across inactivity | same Toulouse group as the earlier habituation work; “circulating memory” is chemical load, not symbolic content |
| *Physarum* fusion transfer, Vogel & Dussutour 2016, DOI `10.1098/rspb.2016.2382` | a habituated plasmodium fused with a naïve one and the merged entity showed the altered response | state transfer can occur through substrate merger and mixing | not communication of an independently addressable fact; recipient identity and provenance are physically entangled |
| CRISPR priming, Datsenko et al. 2012, DOI `10.1038/ncomms1937` | a partial prior spacer–target match guided acquisition of additional nearby phage spacers; escape variants could restore resistance after new acquisition | an old exact-ish signature can seed bounded neighborhood expansion against a changed threat | engineered *E. coli* system; acquisition can include host DNA; near-match expansion has self/false-positive risk |
| Yeast GAL transcriptional memory, Sanz et al. 2023, DOI `10.1038/s41467-023-36586-x` | primed cells reacted faster after a glucose interval; a genome-wide deletion screen and RNA labeling implicated gene-specific and global mRNA turnover, not only chromatin | multiple retained/decay processes can jointly change reactivation speed while resting expression looks similar | short laboratory timescale; three biological experiments; faster transcription is not episodic recall |
| Human muscle loading, Seaborne et al. 2018, DOI `10.1038/s41598-018-20287-3` | loading–unloading–reloading in eight men left selected CpG hypomethylation patterns and altered reloading response | prior exposure can leave molecular state after gross phenotype returns toward baseline | small male cohort; association does not show that retained CpGs caused faster regrowth; not motor-skill memory |
| Mouse nucleus-specific muscle methylomics, Wen et al. 2021, DOI `10.1093/function/zqab038` | 8 weeks training, 12 weeks detraining, and 4 weeks retraining left cell-type-specific methylation; resting mRNA changes did not persist; previously trained muscle grew more without a myonuclear-number difference | latent preparedness may persist without persistent output; tissue mixtures can hide opposing cell-type signals | mouse model; methylation-to-regrowth causality remains a hypothesis |
| Myonuclear reversal, Dungan et al. 2019, DOI `10.1152/ajpcell.00050.2019` | elevated myonuclear density during hypertrophy reversed during detraining in the reported mouse protocol | permanent myonuclear count is not a universal muscle-memory substrate | does not refute every retained nuclear, epigenetic, protein, neural, or behavioral mechanism |
| Human muscle proteomics, Hulmi et al. 2025, DOI `10.1113/JP288104` | after 10-week training, 10-week detraining, and retraining, many proteins reversed while a smaller set remained elevated | memory candidates can be sparse residuals inside mostly reversible state | retained protein abundance is a potential mechanism, not proof of causal savings |
| Human BCG progenitor training, Cirovic et al. 2020, DOI `10.1016/j.chom.2020.05.014` | BCG vaccination induced a persistent transcriptional program in bone-marrow hematopoietic progenitors and altered later myeloid responses | durable upstream state can influence later short-lived workers | innate training is broader and shorter-lived than antigen-specific adaptive memory; inflammation can be harmful |
| Plasma cells versus memory B cells, Hammarlund et al. 2017, DOI `10.1038/s41467-017-01901-w` | rhesus macaque antibody responses persisted for years, up to a decade in the study, despite sustained memory-B-cell depletion | persistent output producers and recall-capable cells are separable memory roles | species/intervention-specific; serum output is not the same function as adaptive recall |
| Cross-reactive immune imprinting, Fish et al. 1989, PMID `2477487` | a previously selected mouse memory-B-cell population dominated response to a related analogue and remained clonally stable | fast reuse of a near match can bias response away from a new optimum | classic narrow antigen system; magnitude and harm vary by antigen/task, so imprinting is a test condition, not a universal outcome |

## Mechanism classes that matter for the project

### A. Structured record plus validity horizon

The scrub-jay result is useful only at the functional level: item, place, time, and item-specific decay jointly determine a later action. The translation is a typed episode with `what`, `where/source`, event time, observation time, and a validity function. It does not support one generic recency score.

### B. Reversible suppression, not deletion

Habituation reduces response to a repeated low-value cue and later recovers. The safest software analogue is a reversible, cue-specific suppression policy over an intact raw archive. It must pass dishabituation, stimulus-specificity, spontaneous-recovery, and rare-critical protection tests. Deleting repeated records is not the analogue.

### C. Latent state and reacquisition savings

Muscle and transcriptional studies warn that the baseline readout can return while altered readiness remains. A memory benchmark must therefore distinguish:

- retained content at rest;
- response latency after a cue;
- fewer examples/calls needed to relearn;
- peak recovered performance;
- causal necessity of the retained state.

Calling any one of these “retention” hides the mechanism.

### D. Exact signature plus bounded near-neighbor expansion

CRISPR priming suggests a precise computational hypothesis: a verified old threat signature may open a tightly bounded acquisition/search neighborhood when a mutated near match appears. It also supplies the essential adversary: self-derived or irrelevant neighbors can be acquired. This resembles query expansion with provenance and a strict scope, not free semantic association.

### E. Persistent producer versus recall reserve

Long-lived plasma cells and memory B cells separate continuous output from a reserve that responds to renewed challenge. For an external-memory system these correspond more closely to a materialized active cache and a durable retrievable archive/index. Neither should be treated as the sole memory. Their independent failure and rebuild paths must be measured.

### F. Imprinting and competitive capture

Biological memory can make a system faster and worse: a familiar near match can monopolize response to a changed target. The direct LLM-memory analogue is stale or overgeneralized evidence dominating a newer exact record. This is a primary failure class, not an edge case.

### G. Transfer without semantic provenance

The *Physarum* fusion result shows that state can transfer when substrates merge. It does not show a portable, inspectable message. Collaborative agent memory therefore needs explicit record identity, source lineage, authorization, and conflict handling; copying a hidden controller state is not equivalent to sharing evidence.

## Cross-domain invariants admitted to testing

1. **Raw trace and adaptive state must remain separate.** Suppression, priming, cached output, and learned policy should be rebuildable or reversible without destroying evidence.
2. **Readout defines the memory claim.** Exact content, action bias, response latency, relearning speed, and persistent output are different endpoints.
3. **Specificity has a cost curve.** Exact matching misses drift; broad matching risks self/near-neighbor capture. Report both miss and false-expansion rates.
4. **Competition is unavoidable.** A retained or rapidly recalled old response can block a better new response.
5. **Population averages are insufficient.** Per-history and per-user state transitions may be discrete and heterogeneous even when the aggregate curve is smooth.
6. **Persistence does not identify substrate.** Molecular marks, retained proteins, chemical loads, cell populations, and environmental traces may correlate with the same behavioral readout.
7. **Causal ablation is required before architectural promotion.** A persistent correlate is not the mechanism until removing or isolating it changes savings or recall.

## Benchmark candidates

| ID | Question | Minimal arms | Primary outcome | Required guardrail |
| --- | --- | --- | --- | --- |
| BIO-M1 | Can repeated harmless cues be suppressed without deleting their evidence? | no suppression; frequency decay; cue-specific reversible suppression | maintenance/context saved at equal downstream utility | spontaneous recovery, dishabituation, novel and rare-critical recall |
| BIO-M2 | Do aggregate gains hide failing histories? | global scalar; per-history state; oracle state | macro and worst-decile utility, transition-time distribution | no subgroup/history may be hidden by pooled mean |
| BIO-M3 | Is “memory” retained content or faster reacquisition? | archive only; latent priming metadata; retained summary; oracle | calls/tokens/time to regain a frozen performance threshold | baseline output and final recovered accuracy reported separately |
| BIO-M4 | Does a verified old signature safely guide near-neighbor acquisition? | exact only; unrestricted semantic expansion; bounded provenance expansion | recovery of drifted targets at fixed acquisition budget | self/irrelevant acquisition, poisoning, scope escape |
| BIO-M5 | Does the old near match competitively capture a changed query? | latest-only; similarity-only; validity-aware competition; oracle | current exact-action accuracy under controlled similarity | stale intrusion and false confident completion |
| BIO-M6 | Can active cache and durable reserve fail independently? | active cache only; archive only; both; rebuild-after-loss | answer/action recovery after removal of either layer | provenance completeness and rebuild determinism |
| BIO-M7 | Can state be shared without losing provenance? | opaque state copy; record merge; namespace/capability merge | correct cross-agent reuse and conflict localization | no authority escalation, source laundering, or silent overwrite |
| BIO-M8 | Do typed item-specific validity horizons beat recency? | recency; type decay; explicit valid time; oracle | correct recovery/action across perishable and stable records | no false expiration of quiet stable evidence |

These are preregistration candidates, not permission to implement them all. BIO-M1 and BIO-M5 overlap the existing forgetting/interference program and should reuse its corpus contracts. BIO-M3 should be a small deterministic instrument before any biological-inspired architecture is proposed.

## Rejected translations

- DNA methylation is not a vector database and CRISPR is not semantic RAG.
- Muscle “memory” does not justify saving model weights or calling procedural skill an episode.
- Immune memory does not justify permanent threat scores, automatic deletion, or indiscriminate alert amplification.
- Habituation does not justify ignoring frequent events; innocuousness, specificity, recovery, and protected exceptions are required.
- A chemical or epigenetic trace is not better merely because it is physically deeper than a file.
- Non-neural learning does not show consciousness, human-like recollection, or one substrate-independent algorithm.

## Current conclusion

Comparative biology strengthens a conservative architecture: append exact observations; keep derived response states separate and reversible; make retrieval and relearning measurable; preserve specific provenance; and test old-memory competition explicitly. The most useful new experiment is not a simulated neuron or emotion field. It is a factor-isolated **savings-versus-retained-content** benchmark, followed by cue-specific reversible suppression and near-match imprinting tests.

No product component is admitted by this audit. Independent replication review, fuller animal-learning coverage, and causal mechanism audits remain open.
