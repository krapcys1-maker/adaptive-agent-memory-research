# Temporal memory models: what to borrow before writing our own

Status: design input for `#29`, produced under `#34`
Method: read the implementing code, not the documentation. Claims are pinned to a revision.

Sources, pinned:

- **Graphiti** — `getzep/graphiti`, Apache-2.0, 30.2k stars, `main` at 2026-08-21. Files read: `graphiti_core/edges.py`, `graphiti_core/utils/maintenance/edge_operations.py`.
- **SQL:2011** — the temporal-table standard, for the vocabulary both this and Graphiti are instances of.

## Answer to the five registered questions

### 1. What are the exact temporal fields?

Graphiti's `EntityEdge` carries **four**, on **two axes**:

| Field | Description in the code | Axis |
|---|---|---|
| `created_at` | when the record was written | transaction |
| `expired_at` | "datetime of when the node was invalidated" | transaction |
| `valid_at` | "datetime of when the fact became true" | valid |
| `invalid_at` | "datetime of when the fact stopped being true" | valid |

Plus `reference_time`, the timestamp of the episode that produced the edge.

This is textbook bitemporal modelling. SQL:2011 calls the same two axes *system time* and *application time*. Graphiti is an instance of a standard, not an invention — which is the strongest possible reason to borrow rather than design.

### 2. How does it separate a fact that changed from a fact that was wrong?

**Better than the design `#29` proposed.** I suggested two operations, `correct` and `succeed`. Graphiti needs no such distinction because the two axes already carry it.

From `resolve_edge_contradictions`, when a new fact supersedes an older one:

```python
edge.invalid_at = resolved_edge.valid_at
edge.expired_at = edge.expired_at if edge.expired_at is not None else utc_now()
```

The world-change is written on the **valid** axis — the old fact stopped being true exactly when the new one started. The bookkeeping is written on the **transaction** axis — the record was invalidated now. **Both records survive; neither is deleted.**

A correction, by contrast, would stamp `expired_at` without moving `invalid_at`: the record was wrong, so nothing about the world changed.

Two operations collapse into one mechanism with two timestamps. That is the insight worth taking.

### 3. Does it handle an expected expiry with no observation?

**No.** This is the dye-fades case from `#29`: hair colour that will revert without anyone recording it.

`invalid_at` is only ever set from an LLM extraction of the source text, or from an explicit contradiction. There is no decay, no half-life, no expected-expiry marker. A fact stays valid until something *observed* ends it.

The gap is real and we would inherit it. It is also arguably correct: inventing an end date nobody observed is exactly the fabrication our own upcaster refuses to make.

### 4. What can be borrowed without the backend?

**Borrow:** the four-field two-axis schema, and the succession rule that sets the prior fact's `invalid_at` to the successor's `valid_at` while stamping `expired_at` at write time. Both are pure field semantics. Neither needs a graph database, an LLM extraction pipeline, or an embedding.

**Do not borrow:** the graph backend or the extraction pipeline. Already recorded as too heavy for this bootstrap, and nothing above depends on them.

### 5. What does it get wrong or leave open?

Three things, and the first matters to us most.

**Temporal values are LLM-extracted, and a parse failure is silent.** From `edge_operations.py`:

```python
logger.warning('Error parsing valid_at date, skipping')
```

If the model emits an unparseable date, the temporal claim is dropped and the edge is stored with `valid_at = None`. The record then looks like a fact with no known start rather than a fact whose start was lost. **We must not copy this.** A dropped provenance field is exactly what our mechanical gate exists to catch, and our `verify_memory_integrity.py` would reject it.

**Contradiction detection is model-dependent.** Which edges become "invalidation candidates" is decided by an LLM, so what counts as a contradiction is not mechanically checkable. Our `supersedes` field is explicit and author-declared, which is weaker in coverage and stronger in auditability.

**No decay**, as in question 3.

## What this means for `#29`

The schema proposed in `#29` should change:

- **Adopt four fields, not two.** My draft had `valid_from` and `valid_to` beside `created_at`. That is one and a half axes and cannot express "this record was withdrawn as an error" separately from "the world changed". Add the transaction-side end explicitly.
- **Drop the proposed `correct` / `succeed` operations.** They are unnecessary once both axes exist, and one mechanism with two timestamps is easier to verify than two operations with overlapping semantics.
- **Keep our extraction discipline.** Temporal values must be explicit and mechanically checkable, never silently dropped. Where Graphiti guesses with an LLM and skips on failure, we require a declared value or an explicit unknown.
- **Keep supersession explicit.** Graphiti infers contradiction; we declare it. Ours is narrower and auditable, which is the trade this project consistently makes.
- **Accept the decay gap for now.** Record it as a known limitation rather than inventing a mechanism nobody has validated.

## Why this was worth doing before writing code

The bitemporal answer has existed since SQL:2011 and is implemented in a 30k-star project. Writing our own would have produced a worse version of a standard, and the `correct`/`succeed` split I proposed was a real design error that reading the code caught in twenty minutes.

This is the operating doctrine's first selection rule paying for itself: *does the answer already exist?*
