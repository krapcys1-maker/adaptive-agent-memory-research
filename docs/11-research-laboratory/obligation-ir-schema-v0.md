# Obligation IR schema v0

Status: design freeze candidate; no corpus or parser result

This document freezes the construction contract for `PMLAB-MAP-001`. It is deliberately an intermediate representation, not a product API and not an architecture endorsement.

## Design decision

Computation and scope are different axes.

- An **obligation graph** says which answer facets and computations the question requires.
- A **scope mapping** says which entity, predicate, namespace, valid time, authorization domain, and completeness certificate may answer each leaf obligation.
- A **decision layer** consumes mapped obligations and evidence states; it may answer, continue searching, return a typed gap, clarify, or abstain.

Temporal, authorization, provenance, and closure annotations are not QDMR operators. Keeping them separate prevents a good decomposition score from concealing a dangerous scope selection.

## Operator inventory v0

The graph uses a small typed inventory adapted from QDMR. Operator names describe computation, not surface words.

| Operator | Contract | Typical memory question | Scope-bearing? |
| --- | --- | --- | --- |
| `SELECT` | retrieve atomic values satisfying one grounded relation | “Who approved Umber?” | yes |
| `FILTER` | restrict a referenced set by a grounded condition | “decisions after the audit” | condition leaf does |
| `PROJECT` | follow a relation from a referenced entity/set | “their owners” | yes |
| `AGGREGATE` | count/sum/min/max over a referenced set | “How many were rejected?” | child obligations do |
| `GROUP` | aggregate per grouping key | “How many failures per backend?” | child leaves do |
| `SUPERLATIVE` | choose extremum under a measure | “Which run cost most?” | measure and candidate leaves do |
| `COMPARATIVE` | compare values or filter by comparison | “Was FTS5 better than rg?” | compared leaves do |
| `UNION` | combine alternative result sets | “decisions or findings” | child leaves do |
| `INTERSECTION` | retain values shared by sets/conditions | “reviewed and current records” | child leaves do |
| `DIFFERENCE` | subtract an explicit set from another | “planned but not completed experiments” | both child leaves do |
| `SORT` | order a referenced set by a grounded key | “latest three failures” | key leaf does |
| `BOOLEAN` | evaluate existence, relation, conjunction, or explicit negation | “Was the run approved?” | yes |
| `ARITHMETIC` | calculate from referenced numeric values | “difference in recall” | child leaves do |

`TEMPORAL_SCOPE`, `CURRENT_VALID`, `AUTHORIZATION_SCOPE`, `EXPLICIT_NEGATION`, `ABSENCE`, and `CERTIFICATE` are intentionally **not** operators. They are typed annotations or evidence/decision states.

Unsupported computation is represented as `unsupported_structure`, never coerced to the closest operator.

## Canonical record

```yaml
schema_version: pmlab-obligation-ir-v0
query_id: opaque-id
language: pl
raw_query: "..."
reference_clock:
  instant: 2026-08-22T12:00:00+03:00
  timezone: Europe/Bucharest
  source: case-fixture
graph:
  nodes:
    - obligation_id: O1
      operator: SELECT
      natural_spans: [{start: 0, end: 18, text: "..."}]
      arguments: []
      output_type: entity | scalar | boolean | set | record | unknown
      criticality: critical | ordinary
      scope:
        entity:
          mention: "Umber"
          candidates:
            - {id: "project:umber", type: project, basis: exact_alias}
          status: resolved | ambiguous | nil | unsupported
        predicate:
          mention: "zatwierdził"
          candidates:
            - {id: "approval.approver", basis: glossary}
          status: resolved | ambiguous | nil | unsupported
        namespaces:
          candidates: ["canonical-events", "approvals"]
          status: resolved | ambiguous | unauthorized | unsupported
        valid_time:
          raw_span: null
          interval: {start: null, end: "2026-08-22T12:00:00+03:00", bounds: "(]"}
          anchor: query_reference_clock
          granularity: second
          recurrence: null
          status: resolved | ambiguous | unbounded | unsupported
        authorization:
          principal: fixture-user
          required_capability: read
          status: allowed | denied | unknown
      certificate_query:
        predicate: "approval.approver"
        entity_ids: ["project:umber"]
        interval: {start: null, end: "2026-08-22T12:00:00+03:00"}
        namespaces: ["canonical-events", "approvals"]
        authorization_principal: fixture-user
        status: applicable | ambiguous | inapplicable | unsupported
  edges: []
query_status: resolved | ambiguous | unauthorized | unsupported_structure
provenance:
  parser_version: gold-v0
  schema_version: fixture-schema-v0
  glossary_version: fixture-glossary-v0
  entity_catalog_version: fixture-entities-v0
```

Candidate scores are permitted for ranking but cannot by themselves change `ambiguous`, `nil`, `unauthorized`, or `unsupported` into `resolved`.

## Atomicity policy

An obligation is atomic when one independently answerable proposition or value can receive its own evidence set, validity interval, authorization result, and completeness decision.

Split when any of the following differs:

- requested predicate or returned value;
- entity or entity binding;
- valid-time interval or temporal anchor;
- namespace or authorization boundary;
- certificate query shape;
- polarity or quantification;
- support/gap state that could differ while another facet is answerable.

Do not split merely because:

- a multiword mention or predicate contains a conjunction lexicalized as one schema item;
- a filter is inseparable from the identity of the requested set;
- a temporal phrase requires several SCATE-style components but denotes one scope annotation;
- alternative surface paraphrases denote the same leaf obligation.

If reviewers disagree whether a filter is independently certifiable, preserve both analyses, mark `atomicity_disputed`, and exclude the case from confirmatory primary metrics until adjudicated.

## Gold and comparison rules

1. Gold contains a set/DAG of obligations, not one privileged natural-language decomposition string.
2. Multiple gold graphs may be accepted when they are typed, executable, and denotationally equivalent.
3. Strict exact match compares canonical serialization only against the primary gold graph.
4. Structural scoring finds the maximum valid alignment to any accepted gold graph and reports node/operator, argument, and labeled-edge scores.
5. Denotational scoring executes supported graphs against frozen fixture schemas and clocks.
6. Scope scoring is per leaf obligation. A correct whole-query answer cannot repair a missed leaf.
7. A mapper-induced false N2/N3 is always reported as a critical unsafe error, regardless of aggregate F1.
8. Gold-obligation and gold-link oracle arms are diagnostic ceilings and must never be mixed with deployable results.

## Asymmetric utility v0

Primary counts remain unweighted and fully reported. The utility view is additional:

| Error | Loss |
| --- | ---: |
| critical obligation omitted | 100 |
| mapper causes unsupported N3 | 100 |
| mapper causes unsupported N2 | 80 |
| authorization boundary crossed | 100 |
| unresolved critical scope silently selected | 100 |
| ordinary obligation omitted | 20 |
| extra obligation causing abstention/search | 5 |
| harmless alternative but equivalent graph | 0 |
| canonical serialization mismatch only | 1 |

These numbers are preregistered engineering utilities, not empirical human costs. Confirmatory publication requires independent review and sensitivity analysis at loss ratios 2x and 0.5x for all nonzero noncritical losses.

## Grouping and split contract

Every row carries:

- `semantic_template_group` — same proposition/computation regardless of language or paraphrase;
- `schema_family` and `schema_version`;
- `composition_atoms` and `composition_signature`;
- `entity_alias_group`, `predicate_surface_group`, and `time_surface_group`;
- `bilingual_pair_group` and `paraphrase_group`;
- `criticality`, `ambiguity_class`, and `supportedness`.

All rows sharing a semantic template, bilingual pair, paraphrase, or direct translation stay in one split. The unseen-composition split may reuse atoms but not compound signatures. The unseen-schema split holds out both canonical namespace identifiers and surface labels. Construction/dev/challenge manifests must be frozen before any implementation sees challenge text.

## Required scorecard

- exact canonical graph rate;
- obligation precision/recall/F1 and critical recall;
- operator/node and labeled-edge F1;
- executable and denotationally equivalent graph rate;
- entity, predicate, namespace, time, and authorization scores separately;
- temporal structure exactness and interval-overlap/execution scores separately;
- ambiguity/NIL/unsupported calibration and clarification/abstention rate;
- per-obligation certificate applicability and exact scope;
- downstream exact N0-N3/action and mapper-caused false N2/N3;
- risk-coverage, latency, token/API cost, and local disk growth;
- every metric stratified by language, unseen template, unseen schema, unseen compound, synonym, temporal class, ambiguity, and criticality.

## Freeze acceptance checklist

- full-text source audit is committed and hashes match;
- an independent reviewer signs the operator and atomicity policy or disputes are recorded;
- at least two accepted-equivalent-graph cases and two same-structure/different-denotation cases exist;
- construction templates cover every operator used in primary metrics;
- critical multi-facet, authorization, NIL, ambiguous-time, and false-closure cases exist;
- validators reject cycles, forward references, missing scope fields, leaked gold fields, split-group overlap, and executable graphs with unresolved critical leaves;
- utility sensitivity script and evaluator tests exist before the first result.

Until this checklist and a frozen corpus manifest exist, the status remains a design freeze candidate rather than a frozen experiment.
