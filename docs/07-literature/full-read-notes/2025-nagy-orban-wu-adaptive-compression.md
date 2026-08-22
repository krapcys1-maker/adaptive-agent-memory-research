# Nagy, Orbán, and Wu — Interplay of episodic and semantic memory arises from adaptive compression

- Status: full text read; extracted; first challenge pass complete; Perspective, not primary validation
- Version read: PsyArXiv/OSF preprint, 41 pages
- Source: https://doi.org/10.31234/osf.io/emky9
- Cached file: `sources/papers/adaptive-compression-emky9.pdf` (2,945,443 bytes)
- SHA-256: `584AFDE4D2ACCB08605E294474523BB914FD18263224C6ADE1B1373C483F1794`

## Research question

How should rate-distortion accounts change when the semantic/generative model used to compress experience is itself incomplete and changing?

## Evidence class and proposal

This is a Perspective integrating rate-distortion theory, structure learning, curriculum effects, and replay. It reviews prior simulations and empirical literature and proposes that relatively raw episodic traces preserve surprising observations for later reinterpretation when the current semantic model changes.

## Extracted claims

- A fixed semantic model can discard as noise details that would become diagnostic under a later structural hypothesis. The paper calls this the joint problem of "learning to remember" and "remembering to learn" (Sections 2–3, pp. 5–10).
- The proposed "episodic life-raft" preserves surprising/novel experiences at higher fidelity so alternative structures can later be evaluated (Sections 3–4, pp. 10–17; Figures 3–5).
- The authors cite a prior simulated category learner in which a small episodic buffer improved structure discovery and high Bayesian-surprise prioritization outperformed limited nonselective storage (p. 18; Figure 5c). This is reviewed prior work, not a new experiment in this Perspective.
- They propose variable-rate encoding: well-predicted episodes receive more compression; uncertain, novel, or prediction-violating episodes receive higher fidelity (pp. 19–20; Figure 5d).
- The authors explicitly identify the effect of variable-rate compression on structure-learning failures as untested and discuss neglected temporal segmentation and additional agent learning systems (pp. 20–23).
- Emotional salience is absent from existing RDT accounts. The Perspective proposes two routes: alter the distortion function through reward-related importance, or raise encoding rate when salience predicts later retrieval (p. 22). This is a proposed extension, not evidence that emotion is one scalar or that it should control storage alone.

## Limitations and challenge pass

- The paper is a normative Perspective; it does not directly validate the full framework.
- Surprise is model-relative prediction error, not emotion. Conflating them would erase valence, arousal, controllability, stress timing, and consequence.
- Noisy outliers can be surprising. Even Bayesian surprise depends on model specification and cannot guarantee future utility.
- High-fidelity storage of every anomaly can exhaust capacity or preserve attacks. Reproducibility, trust, consequence, and later utility need separate signals.
- Human curriculum/structure-learning analogies do not directly specify an LLM disk schema or retrieval policy.

## Project relevance

Preserve raw episodes because today's model of relevance may be wrong. Treat semantic summaries as versioned hypotheses, and test surprise as one allocation feature rather than a deletion rule. Emotion should enter initially as explicit metadata dimensions and user/consequence labels, not anthropomorphic internal feeling.

## Falsifiable hypothesis

In histories with a hidden rule change or rare exception, a bounded buffer prioritized by calibrated model change plus delayed utility should outperform recency and raw surprise while rejecting random outliers. Reject the mechanism if surprise-aware retention improves immediate anomaly recall but not later structure recovery, or increases poisoning/noise retention enough to erase utility gains.
