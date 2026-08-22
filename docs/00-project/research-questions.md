# Research Questions

Status: in-progress

## A. Problem definition

- What failures attributed to “memory” are actually failures of attention, retrieval, temporal reasoning, or context construction?
- What must persist verbatim, and what may be safely transformed?
- What is the correct unit of retention and retrieval?

## B. Write policy

- Can a system predict later utility at encoding time?
- Which labels distinguish importance, novelty, utility, and risk?
- How should repeated low-value events affect write decisions?
- How can secrets, malicious instructions, and irrelevant tool output be excluded safely?

## C. Representation

- Which tasks need raw episodes, facts, graphs, procedures, or hierarchical summaries?
- Can one memory have multiple representations sharing one provenance identity?
- How should time, uncertainty, scope, and validity be represented?

## D. Consolidation

- When does consolidation help generalization?
- When does it produce factual drift or premature generalization?
- How many independent episodes justify a semantic or procedural rule?
- Can consolidation be reversible and evidence-preserving?

## E. Retrieval

- When should memory search be triggered?
- Which cues require lexical, semantic, temporal, graph, or causal search?
- How should contradictory evidence be bundled?
- What ranking objective best predicts downstream task benefit?

## F. Utility and credit assignment

- How can influence on an action be measured?
- Can paired rollouts estimate counterfactual utility economically?
- How should delayed, rare, or catastrophic utility be valued?
- How do selection bias and censored future observations affect labels?

## G. Forgetting and retention

- Is adaptive retrieval suppression sufficient without deletion?
- What should decay: content, index weight, confidence, or retrieval priority?
- How should retention differ by memory type?
- How can the system recover from a mistaken retention decision?

## H. Evaluation

- Which benchmarks test storage, retrieval, updating, temporal validity, and experienced-agent behavior separately?
- How can benchmark questions avoid turning “not queried” into “not useful”?
- How can we measure whether memory helps a weaker model?
- What evaluation remains valid as native context windows grow?

## I. Safety and ownership

- How can user-local memory remain portable across models?
- How should multiple agents share or isolate memory?
- How can stored prompt injection and poisoned experience be detected?
- How are correction, deletion, consent, and audit implemented?

## J. Comparative biological memory

- Which memory functions evolved convergently in animals with substantially different neural architectures?
- Which behavioral assays establish retained information without making claims about subjective recollection?
- What is stored in motor memory versus in skeletal-muscle adaptation, and what are their distinct timescales?
- Which cellular systems implement priming, hysteresis, sequence-encoded history, or faster reacquisition?
- Which immune-memory mechanisms suggest useful threat-specific retention, and which would create dangerous overreaction in an agent?
- When is environmental or collective persistence a better analogy than internal memory?
- For every biological mechanism, what simpler non-biological baseline could explain the same proposed engineering benefit?
