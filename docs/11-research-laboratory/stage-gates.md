# Stage gates before product implementation

Status: reviewed

The operational handoff from evidence gathering to exploratory and frozen experiments is defined in `research-to-experiment-gate.md`. These R0-R5 gates govern the broader path from research integrity to a candidate product architecture.

## Gate R0 — Inventory integrity

Required:

- deduplicated source and repository manifests;
- explicit distinction between discovered, screened, read, and reviewed;
- stable identifiers and pinned repository revisions;
- search log and coverage matrix.

Failure condition: the project cannot reconstruct where a claim or artifact came from.

## Gate R1 — Evidence map

Required:

- atomic claims with exact source locators;
- conflicts, null results, and boundary conditions;
- comparative biological mechanisms kept in distinct categories;
- each architecture idea tied to a falsifiable hypothesis and simpler baseline.

Failure condition: a design proposal is supported only by analogy, a survey abstract, popularity, or repository stars.

## Gate R2 — Benchmark validity

Required:

- frozen development and held-out sets;
- retrieval and reader effects separable;
- leakage, contamination, judge, context-size, and version audit;
- `rg`, FTS5/BM25, no-memory, and oracle controls;
- registered metrics, budgets, practical threshold, and rejection rule.

Failure condition: a score cannot identify which memory subsystem improved.

## Gate R3 — Baseline laboratory

Required:

- reproducible B1/B2 runs;
- complete run artifacts, environment, latency, token, and error reports;
- independent reproduction of at least one result;
- negative results retained.

Failure condition: rerunning from the manifest changes the conclusion materially.

## Gate R4 — Controlled complexity

Add one mechanism at a time:

1. local dense retrieval;
2. fixed hybrid fusion;
3. temporal validity;
4. graph relations;
5. operational salience or learned retention.

Each mechanism needs an ablation and must beat the immediately simpler registered baseline. A mechanism that only shifts cost or errors to another subsystem does not pass.

## Gate R5 — Pre-implementation architecture

Required:

- evidence-supported component list;
- accepted data and threat models;
- provider-neutral interfaces;
- migration, export, correction, and deletion plan;
- explicit unknowns and rejected alternatives;
- two independent reader/provider evaluations where subscriptions permit.

Only after R5 should the project call an architecture a candidate implementation rather than a research sketch.
