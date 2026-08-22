# Interdisciplinary memory mechanisms

Status: in-progress

## Mission

Identify mechanisms from adjacent disciplines that solve a measurable part of long-term agent memory. This track asks what a mechanism *does*, what substrate it needs, when it fails, and which simpler baseline could explain the same benefit.

The project aims at a functional memory substitute for continuity, learning, correction, future intentions, and appropriate recall. It does not assume that an external disk store creates human phenomenology, consciousness, or felt emotion.

## Common functional decomposition

```text
experience
   |
   v
event segmentation -> write allocation -> durable episode
                          |                    |
                          |                    v
                          |              replay/reactivation
                          |                    |
                          v                    v
                   priority control      consolidation
                          |                    |
                          +--------+-----------+
                                   v
                     multiple derived representations
                    lexical | dense | temporal | causal
                                   |
                                   v
                       metacognitive search trigger
                                   |
                                   v
                       budgeted context reconstruction
                                   |
                                   v
                      action, outcome, and correction
                                   |
                                   v
                     utility credit and future revision
```

## Priority map

| Priority | Discipline | Memory problem contributed | Candidate engineering mechanism | Main trap |
| --- | --- | --- | --- | --- |
| A | Cognitive psychology and cognitive neuroscience | encoding, source binding, interference, consolidation, retrieval, prospective memory | typed episodes, cue bundles, replay, intention triggers, metamemory | treating a behavioral construct as one brain module |
| A | Computational neuroscience | fast/slow learning, pattern separation/completion, allocation, attractor dynamics | episodic/semantic stores, sparse allocation, associative retrieval | attractor completion can confidently blend memories |
| A | Information theory and decision theory | what to preserve under finite attention and context | task-conditioned rate-distortion and counterfactual utility | compressing for description rather than future action |
| A | Information retrieval | finding evidence under lexical, semantic, temporal, and graph cues | sparse/dense hybrid retrieval with calibrated routing | measuring retrieval popularity instead of downstream benefit |
| A | Databases, file systems, and storage reliability | durability, ordering, correction, crash recovery, versioning | append-only log, checksums, atomic writes, snapshots, derived indexes | equating durable storage with successful remembering |
| A | Continual learning | stability-plasticity, interference, replay selection | episodic buffers, replay, protected knowledge, transfer metrics | changing model weights is not required for external memory |
| A | Affective neuroscience and control | consequence-sensitive consolidation and urgent recall | operational salience from outcome, surprise, urgency, controllability, and risk | calling scalar importance an emotion or retaining every failure forever |
| A | Metacognition and cognitive offloading | knowing when internal recall is insufficient; remembering future action | search/abstention policy, reminders, condition-based intentions | dependence on an external reminder can weaken unaided encoding |
| B | Distributed systems and security | shared memory, concurrent writes, trust, poisoning, deletion | provenance, namespaces, capabilities, review states, append/merge protocols | availability does not imply truth or authorization |
| B | Comparative biology and immunology | priming, savings, specificity, habituation, protected threat memory | typed retention policies and reversible suppression | collapsing distinct cellular and cognitive meanings of memory |
| B | Complex systems and dynamical systems | attractors, hysteresis, metastability, phase transitions | state-dependent retrieval and robust pattern completion | elegant dynamics without task-level advantage |
| B | Human-computer interaction | external artifacts, reminders, interruption recovery | task resumption records and user-visible memory controls | automation can create overreliance and poor calibration |
| C | Neuromorphic and storage hardware | energy, locality, endurance, physical associative search | future deployment optimization | prematurely designing around hardware that does not improve memory quality |
| C | Thermodynamics of information | cost of irreversible erasure and physical storage limits | conceptual constraint on deletion and computation | Landauer limits do not select a retrieval architecture at current scales |
| C | Evolution, ecology, and collective behavior | adaptation across lifetimes, artifacts, niches, stigmergy | population-level or workspace-level memory | confusing selection, environmental persistence, and individual learning |
| Watchlist | Quantum, atomic, and nuclear physics | possible future substrate-level effects | none currently justified for the software memory layer | unfalsifiable quantum-memory analogies and neuron/neutron confusion |

## Scale boundary

- **Neurons** and synapses matter because they are measured substrates of neural learning and memory.
- **Neutrons**, atomic states, and quantum effects matter to physical storage engineering only when they yield a distinct, testable system-level prediction.
- A mechanism at a smaller physical scale is not automatically a better explanation of cognition.
- The correct level of abstraction is the lowest level needed to predict a benchmark result or failure mode.

## Candidate invariant architecture

The cross-disciplinary evidence currently favors a stable separation, not a final component selection:

1. immutable or recoverable observations;
2. typed, versioned memory records with provenance and valid time;
3. derived representations that can be deleted and rebuilt;
4. an allocation policy deciding what enters active memory;
5. offline, reversible consolidation and replay;
6. multiple retrieval signals behind one contract;
7. prospective triggers for future intentions;
8. a metacognitive controller deciding when to retrieve, ask, or abstain;
9. outcome-based evaluation and credit assignment;
10. user ownership, correction, deletion, and audit.

Each item is a research candidate until its corresponding benchmark passes.

## Current conclusion about data volume

The project has enough breadth to stop adding undirected topics and begin structured processing. It does **not** yet have enough reviewed evidence for a final architecture:

- many records are discovery leads rather than screened sources;
- exact evidence locators and independent review remain sparse;
- cross-domain analogies have not been compared under one benchmark;
- `rg` and FTS5 baselines have not yet been frozen and reproduced.

Broad discovery and evidence processing should now run in parallel. A topic moves toward synthesis by coverage state, not raw paper count.

See:

- [source seeds](source-seeds.md);
- [hypothesis portfolio](hypothesis-portfolio.md);
- [compression synthesis](compression-synthesis.md);
- [emotion and salience synthesis](emotion-salience-synthesis.md);
- [replay synthesis](replay-synthesis.md);
- [reconsolidation and revision synthesis](reconsolidation-synthesis.md);
- [interference, active forgetting, and access-failure synthesis](interference-active-forgetting-synthesis.md);
- [synthesis protocol](synthesis-protocol.md).
