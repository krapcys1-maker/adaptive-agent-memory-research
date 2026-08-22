# Blind mapper-label review manual v1

You are reviewing a development benchmark, not a candidate system. Deliberately malformed, missing, ambiguous, denied, stale, incomplete, or unsupported inputs are valid negative controls when their typed label is justified.

Do not inspect author labels, model reviews, aggregate scores, architecture proposals, or files outside this `blind/` directory before submitting your form.

## Common rules

- Label PL and EN independently, then state whether they express the same semantic task.
- Use only visible input and the supplied versioned catalogs/contracts.
- Source spans must be exact contiguous substrings.
- Never invent an entity, predicate, policy, time anchor, or completeness fact.
- A stage may use only its supplied inputs. Do not repair missing upstream information by assumption.
- Mark `exclude` when two materially different labels remain equally defensible under this manual.

## Contract and span

Accept only valid serialization with required fields, exact source spans, sequential unique node IDs, backward-only dependencies, known catalog IDs, and safe unresolved states. An ambiguous or unauthorized payload carrying a conclusive applicable/negative certificate is `unsafe_unresolved_state`.

## Obligation graph

- A node is one denotationally necessary retrieval or computation.
- `SELECT` retrieves a base relation/set from query-stated scope.
- `PROJECT` retrieves an attribute/relation whose subject is a parent result.
- `FILTER` retains members of a parent set.
- `AGGREGATE` maps a set to a scalar; `GROUP` creates partitions.
- Set, arithmetic, comparative, and superlative operations are derived nodes with their operands as parents.
- Query-entity coreference belongs to entity linking and does not by itself create a graph edge. Reference to a prior answer does.
- Direct yes/no relation tests may be one `BOOLEAN` node.
- Use the smallest contiguous clause expressing a leaf facet; for a derived node use the smallest explicit operator trigger.
- Graph-only input contains no principal/policy, so it cannot output `unauthorized`.

## Entity and predicate linking

Entity actions are `linked`, `ambiguous_in_catalog`, `missing_entity`, `non_entity_phrase`, and `mention_not_detected`. Record every plausible ID before selecting. Null supplied mention is `mention_not_detected`.

Return the entity label with exactly four fields: `action`, `candidate_ids`, `selected_id`, and `selected_ids`. `candidate_ids` and `selected_ids` contain ID strings only. Always include `selected_ids`; use `[]` unless the result is a true multi-entity selection. Unresolved actions select neither a single nor multiple entities.

Predicate review has two decisions: candidate set and selection. An exact alias is strong evidence but not automatic truth; descriptions and entity context also matter. A topical near-neighbor is not enough. Use `ambiguous_schema` if multiple IDs remain defensible and `unsupported_predicate` if none represents the requested facet. Ranked predicates are arrays of ID strings only.

Return the predicate label with exactly `action`, `ranked_predicates`, `selected_predicate`, and `selected_namespaces`. Do not return scored objects inside `ranked_predicates`.

## Time and authorization

Copy reference clock, timezone, principal, and policy from input. Temporal support and authorization are orthogonal: unsupported or ambiguous time does not imply denial.

Canonical time grammar:

- `[start,end)` for ISO-8601 half-open intervals with offsets;
- `[event,reference_clock]` for resolved event-to-now intervals;
- `recurrence:<frequency>:<weekday>@<local-time>:<IANA-zone>`;
- `unbounded:(-infinity,<reference_clock>]`;
- `ambiguous:<candidate-boundary>:<reason>`;
- `unsupported:<reason>`;
- `inherit:<parents>` or `intersection:<parents>:<interval>`.

Authorization must preserve allowed and denied namespace partitions and cite the supplied policy version/basis.

## Certificate routing

For v1 labels, distinguish:

- `applicable`: direct positive evidence supports the requested proposition;
- `derived`: a deterministic computation over verified parents;
- `explicit_negative`: proposition-level evidence establishes falsity;
- `requires_complete_scope`: a no-hit supports collection-bounded absence only because fresh, complete, exact authorized scope is supplied;
- `ambiguous`: mapping/scope ambiguity prevents a unique certificate;
- `inapplicable`: required evidence, freshness, completeness, authorization, or scope match fails.

Actions are `answer`, `continue_search`, `clarify`, `partial_with_gap`, and `abstain`. A matching post-certificate insertion invalidates absence. An out-of-scope insertion is a negative control. Free-form rationale is not part of exact label identity; cite structured visible evidence in the review rationale.

## Review disposition

For each language row provide a complete independent label and confidence. For the semantic group also provide:

- language equivalence;
- stage isolation (`valid`, `minor_issue`, `material_issue`, `exclude`);
- disputed or underspecified field, if any;
- material-disagreement expectation before reveal;
- rationale based only on visible evidence.

The form must be complete and signed before any reveal comparison.
