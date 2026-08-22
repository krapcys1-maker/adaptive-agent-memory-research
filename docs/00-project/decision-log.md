# Decision Log

## 2026-08-22 — Research before product implementation

Decision: Focus first on evidence collection, taxonomy, benchmark validity, and falsifiable hypotheses.

Reason: Existing project notes contain promising mechanisms but insufficient separation between established human-memory findings, engineering analogies, and untested claims.

## 2026-08-22 — Local-first durable storage

Decision: Treat user-owned disk as the default location for durable memory.

Reason: Portability, privacy, auditability, and independence from a single model provider are central project goals.

## 2026-08-22 — Context window remains unchanged

Decision: Do not require modifications to transformer context-window internals.

Reason: The research target is an external memory/controller layer compatible with existing models.

## 2026-08-22 — Raw evidence remains recoverable

Decision: During early research, experimental forgetting affects indexes and active tiers, not the only raw copy.

Reason: Learned retention will make mistakes, and consolidation may corrupt detail.

## 2026-08-22 — External sources are cached, not vendored

Decision: Clone useful repositories and download accessible papers locally, but keep them out of this public repository.

Reason: Respect licenses, avoid stale forks, reduce repository size, and preserve clear ownership.

## 2026-08-22 — Laboratory gates before architecture complexity

Decision: Compare `rg`, FTS5/BM25, local dense retrieval, hybrid retrieval, temporal ranking, graph retrieval, and operational salience in that order under one frozen contract.

Reason: Changing multiple components at once prevents causal attribution. Biological plausibility and benchmark popularity are not substitutes for incremental evidence.

## 2026-08-22 — Expand beyond human memory without collapsing meanings

Decision: Add comparative animal, motor, muscle, immune, cellular, epigenetic, prokaryotic, and collective memory as distinct research tracks.

Reason: Different biological systems expose useful strategies for persistence, priming, interference, specificity, and reactivation, but using one word for them must not imply shared mechanisms or cognition.

## 2026-08-22 — Coverage is a protocol state, not a completeness percentage

Decision: Report search rounds, databases, screened denominators, novelty yield, contradictions, and saturation status instead of unsupported estimates such as "95% complete."

Reason: The total relevant literature is unknowable and changes over time. A reproducible stopping rule is defensible; an absolute completeness claim is not.

## 2026-08-22 — External model APIs are optional batch workers

Decision: Keep the research memory, retrieval indexes, and accepted evidence independent of model APIs. Admit a cloud model only through a provider-neutral, review-gated batch experiment.

Reason: Subscription agents already support interactive research, while local tools cover canonical storage and initial retrieval. Premature API integration adds cost, privacy, provider-drift, and automation-bias risks without proving that scientific review becomes faster or better.

## 2026-08-22 — Begin reversible synthesis while continuing targeted discovery

Decision: Stop expanding the topic list without direction. Process Priority-A mechanisms in repeated screening, primary-reading, synthesis, and benchmark cycles while targeted adversarial and snowball searches continue.

Reason: The catalog now has enough disciplinary breadth to define falsifiable mechanism candidates, but most new leads remain unscreened and the lexical baselines are not reproduced. Raw source volume cannot substitute for exact evidence, independent challenge, or task-level evaluation.

## 2026-08-22 — Treat emotion as decomposed operational signals first

Decision: Test outcome valence, magnitude, urgency, surprise, controllability, uncertainty, explicit user weight, and recurrence as separate memory-control variables. Do not claim that a scalar salience score creates subjective emotion.

Reason: Arousal, valence, reward, prediction error, stress, and importance have different effects and failure modes. Keeping them separate permits ablation, calibration, poisoning tests, and rejection.

## 2026-08-22 — Transition from research to testing per hypothesis

Decision: Do not wait for global literature completeness. Admit a falsifiable hypothesis to an exploratory test when its mechanism, strongest alternative, baseline, characteristic failure, metrics, costs, safety guardrails, and rejection rule are explicit. Freeze a confirmatory test only after its corpus, split, thresholds, analysis, and review contract are recorded. New evidence may start a new protocol version but may not rewrite a frozen one.

Reason: Literature saturation and empirical test readiness answer different questions. More reading cannot resolve an uncertainty that depends on system behavior, while testing too early without a challenge search or rejection rule produces persuasive but uninterpretable scores.
