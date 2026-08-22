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
