# PMLAB-MAP stage annotation manual v1

Status: candidate labeling manual; no case labels yet

## Unit of annotation

The unit is a semantic group, not a translated row. Annotate the language-neutral intent and stage gold first, then create PL/EN surfaces. Both languages inherit one semantic-group ID and may never cross splits.

## General rules

- Annotate only the stage named by the case. Upstream inputs supplied as gold are experimental controls, not claims that a deployable system knows them.
- Keep natural-language source spans exact and contiguous. If a concept has no exact span, mark it implicit rather than inventing text.
- Record every plausible catalog/schema candidate before choosing linked, ambiguous, or unresolved.
- Do not use model output, confidence, or prior benchmark failures to decide gold.
- Critical means that omission or false resolution could expose unauthorized information, create false closure/negation, bind the wrong entity, or silently drop a required answer facet.
- Exclude a case when a fluent reader cannot distinguish competing gold labels from the supplied input. Do not adjudicate underspecification by adding hidden assumptions.

## Entity labels

- `linked`: one catalog entry is supported by mention plus supplied context.
- `ambiguous_in_catalog`: at least two catalog entries remain plausible.
- `missing_entity`: the text refers to an entity, but the correct referent is absent from the versioned catalog.
- `non_entity_phrase`: the surface is not an entity mention in context despite resembling an alias.
- `mention_not_detected`: the stage receives no valid mention span; this is different from NIL after mention detection.

## Predicate labels

Link only when the requested relation is represented by the schema version. A topically related column is not sufficient. Use `ambiguous_schema` when multiple candidates remain semantically plausible and `unsupported_predicate` when none represents the requested facet.

## Time and authorization

Normalize against the recorded clock and timezone. Preserve unresolved boundaries for expressions such as “early next week.” Authorization is evaluated for the recorded principal and policy version; it cannot be inferred from data existence.

## Certificates

- `explicit_negative` requires evidence or a domain rule establishing proposition-level falsity.
- `requires_complete_scope` represents collection-bounded absence and requires exact current authorized completeness metadata.
- `applicable` cannot be used for ambiguous, NIL, unauthorized, stale, incomplete, or mismatched scope.
- An insertion counterexample must invalidate any certificate that claimed absence in the inserted scope.

## Disagreement coding

Reviewers independently return label, confidence (`high|medium|low`), rationale, exact disputed field, and disposition (`agree|minor|material|exclude`). Adjudication never deletes original annotations. Material disagreement on a critical label blocks corpus freeze until resolved or excluded.
