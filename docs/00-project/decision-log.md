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
