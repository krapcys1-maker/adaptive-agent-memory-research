# Comparative biological memory

Status: outline

## Purpose

Study how past events alter future behavior across organisms and substrates. The goal is to expand the design space, not to claim that an LLM, a muscle fiber, an immune lineage, a bird, and a bacterium remember in the same sense.

## Mandatory decomposition

| Family | Example storage substrate | Observable readout | What must not be inferred |
| --- | --- | --- | --- |
| Neural episodic-like memory | distributed neural circuits | flexible what-where-when behavior | human-like conscious recollection |
| Neural associative memory | altered circuit/synaptic state | changed response to a cue | explicit symbolic facts |
| Motor/skill memory | motor, cortical, cerebellar, striatal, and spinal systems | retained or faster skill performance | that the memory resides only in muscle |
| Skeletal-muscle history effect | methylation, myonuclei, transcriptional/metabolic state | altered response to reloading | event recall or procedural representation |
| Adaptive immune memory | persistent clones and receptors | faster or stronger antigen-specific response | general-purpose cognition |
| Trained innate immunity | epigenetic/metabolic state in cells or progenitors | changed nonspecific secondary response | antigen-specific recall |
| Transcriptional memory | chromatin marks, nuclear localization, poised machinery | faster gene reactivation | an autobiographical memory |
| Prokaryotic CRISPR memory | ordered spacer sequences | sequence-specific defense | flexible semantic generalization |
| Non-neural habituation | persistent cellular/network state | declining response to repeated harmless input | mechanism equivalence with neural habituation |
| Stigmergic/collective memory | environment, artifacts, group structure | later behavior guided by traces | memory inside one individual |

## Research tracks

### CBM-1 — Convergent animal capabilities

Compare episodic-like, spatial, associative, social, and prospective-like behavior across corvids, rodents, primates, insects, fish, and cephalopods. Focus on task structure, ecological demand, error patterns, and whether similar capabilities arise from different architectures.

Engineering questions:

- Is a typed what-where-when episode more reliable than an unstructured chunk?
- Should validity and decay depend on memory content, as food perishability depends on type?
- Can reconstructive errors inspire source-monitoring and false-memory tests?

### CBM-2 — Habituation, sensitization, and threat learning

Study how repeated harmless inputs are suppressed while rare consequential inputs are strengthened. Include reversal, dishabituation, generalization, extinction, and reconsolidation.

Engineering questions:

- Can repeated low-value events lose retrieval priority without deletion?
- How do we prevent threat-like salience from producing permanent overreaction?
- What evidence should reopen a suppressed pattern?

### CBM-3 — Motor and procedural learning

Separate neural skill acquisition from peripheral muscle adaptation. Study fast and slow learning, interference, consolidation, practice scheduling, transfer, automaticity, and savings during relearning.

Engineering questions:

- Should procedures have an executable form, examples, failure boundaries, and provenance?
- Does offline stabilization reduce interference between procedures?
- Can reacquisition speed be a metric distinct from immediate recall?

### CBM-4 — Cellular priming and hysteresis

Study transcriptional memory, epigenetic state, metabolic priming, and other cases where identical current input produces a different response because of prior exposure.

Engineering questions:

- Can a compact primed state speed later processing without storing a full episode in the hot path?
- Which state must remain reversible and versioned?
- When does priming become stale bias?

### CBM-5 — Immune and sequence-encoded memory

Separate adaptive immune specificity, trained innate immunity, and CRISPR spacer acquisition. Compare their write triggers, diversity limits, persistence, false positives, and removal dynamics.

Engineering questions:

- Can high-risk failure signatures receive protected retention?
- How should a threat memory expire or be corrected?
- What prevents immune-style memory from overfitting to benign inputs?

### CBM-6 — Externalized and collective memory

Study stigmergy, caches, landmarks, trails, nests, artifacts, and socially transmitted information. This track may be especially relevant to agents because files, Git history, tickets, and tools already act as external memory.

Engineering questions:

- When is writing a durable artifact better than creating an internal memory object?
- How should multiple agents coordinate through shared traces without cross-contamination?

## Translation filter

No biological idea enters an architecture proposal until its note states:

1. empirical behavior and assay;
2. physical substrate and timescale;
3. alternative explanation;
4. abstract computational problem;
5. simplest non-biological baseline;
6. predicted benefit;
7. predicted failure mode;
8. preregistered rejection criterion.

See [source seeds](source-seeds.md) for the initial primary-study map. These seeds establish plausibility and vocabulary; they do not establish coverage.

The first targeted contradiction pass is [motor consolidation, savings, and context audit v0](motor-consolidation-savings-and-context-audit-v0.md). It rejects a single motor-memory-strength construct and derives separate retention, access, context, execution, and relearning endpoints for a future procedural-memory benchmark.
