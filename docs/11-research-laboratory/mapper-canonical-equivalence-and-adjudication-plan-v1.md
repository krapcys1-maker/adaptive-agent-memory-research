# Mapper canonical equivalence and adjudication plan v1

Status: post-advisory protocol draft; gold unchanged; candidate implementation prohibited

## Why exact agreement is not enough

The remaining-corpus blind advisory pass produced only 18/110 exact object matches, yet several safety-relevant fields agreed much more often. Exact equality currently mixes three different questions:

1. **semantic label validity** — does the graph, scope, or certificate mean the right thing?
2. **canonical representation** — did two annotators choose the same operator decomposition, span boundary, interval spelling, and status vocabulary?
3. **serialization compliance** — did the worker follow the required JSON types?

These must be adjudicated and scored separately. Six schema-invalid advisory outputs remain serialization failures. Free-form `basis` text and equivalent-but-differently-rendered time expressions must not decide semantic agreement.

## Disagreement classes

### Mechanical disputes

These can be checked without interpretive judgment:

- exact substring membership;
- unique sequential node IDs and backward dependencies;
- catalog/schema ID membership;
- reference clock, timezone, principal, and policy copied from input;
- collection freshness/completeness/scope flags;
- insertion matching the certified scope;
- JSON field and type validity.

Mechanical checks should remain deterministic and may override neither semantic gold nor reviewer rationale. They only identify impossible annotations.

### Conventional disputes

These require a canonical manual and independent adjudication:

- whether a query facet is `SELECT`, `PROJECT`, `FILTER`, `BOOLEAN`, or a multi-node composition;
- whether pronoun reference to a query entity creates a graph dependency or only entity-stage coreference;
- minimal versus clause-level source-span boundaries;
- when an exact alias defeats a semantically plausible near-neighbor (`ST-P07`, `ST-P08`, `ST-P09`);
- the canonical rendering of recurrence, unbounded time, event anchors, inherited scope, and interval endpoints;
- whether collection-bounded absence is itself a certificate status or a satisfied prerequisite;
- which route distinguishes `continue_search`, `partial_with_gap`, and `abstain`.

## Proposed canonical graph rules

- A node represents one denotationally necessary retrieval or computation, not every noun phrase.
- `SELECT` retrieves a base relation or set from the fixed query scope.
- `PROJECT` retrieves an attribute or relation whose subject is the result of exactly one parent.
- `FILTER` retains members of a parent set using a condition stated in the query.
- `AGGREGATE` maps a set to a scalar; `GROUP` creates grouping partitions; `ARITHMETIC`, `COMPARATIVE`, set operators, and `SUPERLATIVE` are derived nodes with all operands as parents.
- A pronoun that refers to a query-stated entity is resolved by the entity stage and does not create a graph edge. A pronoun that refers to a prior answer does create a dependency.
- A direct yes/no relation may be one `BOOLEAN` node. Do not add hidden entity-selection nodes unless their results are independently requested or consumed.
- Gold should store a preferred graph plus explicitly enumerated equivalent graphs when two decompositions preserve atomic facets, dependency semantics, and downstream scope. Report strict graph exact and equivalence-class exact separately.
- Source spans use the smallest contiguous clause that expresses a leaf facet; derived nodes use the smallest explicit operator trigger. Where two boundaries are linguistically defensible, store accepted spans rather than relying on fuzzy matching.

## Proposed temporal normalization grammar

Future review prompts must include the grammar rather than assume it:

- absolute intervals: ISO-8601 half-open `[start,end)` with explicit UTC offset;
- point/event-to-now intervals: `[event,reference_clock]`;
- recurrence: `recurrence:<frequency>:<weekday>@<local-time>:<IANA-zone>`;
- unbounded past: `unbounded:(-infinity,<reference_clock>]`;
- vague but bounded: `ambiguous:<candidate-boundary>:<reason>`;
- unsupported: `unsupported:<reason>`;
- inherited: `inherit:<parent IDs>` or `intersection:<parent IDs>:<interval>`.

Temporal support and authorization are orthogonal. `time_status=unsupported` must not imply `authorization_status=denied`. Policy output must cite the supplied policy version and preserve allowed and denied namespace partitions.

## Proposed certificate contract v2

The v1 `certificate_status` overloads evidence type, closure requirement, and validity. Before candidates, test a v2 structured contract:

```json
{
  "evidence_class": "positive|derived|explicit_negative|no_hit|mixed",
  "closure_check": "not_required|satisfied|failed|ambiguous",
  "certificate_status": "applicable|inapplicable|ambiguous",
  "action": "answer|continue_search|clarify|partial_with_gap|abstain",
  "evidence_refs": [],
  "gap_reasons": []
}
```

`basis` becomes human-readable rationale and is not exact-scored. `evidence_refs`, `gap_reasons`, and structured scope fields carry the auditable decision. A no-hit can answer absence only when closure is satisfied for the exact authorized entity/predicate/time/namespace scope. A matching insertion changes closure to failed and forces recomputation.

## Predicate adjudication queue

At minimum, independently review `ST-P05`, `ST-P07`, `ST-P08`, `ST-P09`, and `ST-P11` in both languages. The reviewer must see the full schema catalog and answer two separate questions:

1. candidate set: every semantically plausible schema ID;
2. selection: unique supported top-1, ambiguity, or unsupported.

An exact alias is evidence, not automatic truth. Conversely, an unlisted paraphrase may still match a description. Any catalog design that intentionally makes two labels ambiguous must not give only one of them an exact alias without explaining why selection remains unsafe.

## Independent adjudication gate

Before corpus labels can be frozen:

1. publish the v2 canonical manual without candidate outputs or aggregate candidate scores;
2. have at least one genuinely independent human or different model family annotate all critical groups and a stratified 25% of ordinary groups;
3. preserve original author, DeepSeek advisory, independent, and adjudicated labels as separate fields;
4. require 100% resolution or exclusion of material critical disagreements;
5. report per-field agreement and grouped PL/EN parity, not only row-average exact;
6. freeze gold, equivalence classes, scorer version, and exclusions in Git;
7. only then permit candidate implementation on stage-dev-v1.

The current 77-group corpus remains development material. No advisory agreement rate is an architecture result.
