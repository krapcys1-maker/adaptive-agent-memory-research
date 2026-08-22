# PMLAB obligation mapping development corpus v0

Status: authored construction source; not frozen, not held out, not independently reviewed

This corpus exercises the `pmlab-obligation-ir-v0` contract before any parser is implemented. It is a bilingual construction instrument, not evidence that the contract generalizes.

## Files

- `schema-v0.json` — versioned predicate/namespace catalog.
- `entities-v0.json` — versioned entity catalog with aliases, collisions, and a deliberately absent mention.
- `template-groups.jsonl` — semantic template groups. English and Polish variants remain inside one record so they cannot be split accidentally.
- `equivalence-fixtures.jsonl` — metric sanity checks for structure-versus-denotation disagreement.
- `cases.jsonl` — generated model-facing queries plus gold graphs; created only by the deterministic builder.
- `manifest.json` — hashes, group/case counts, and builder version; created after validation.

## Construction boundaries

- Every row is `construction`; there is no challenge set here.
- The query text and fixture catalogs may be inspected while building a parser, so every reported score is developmental.
- Future challenge groups must be authored after this source and builder are frozen.
- No paraphrase or translation from one semantic group may cross splits.
- No model output is accepted as gold. A model may later be an explicitly labeled comparator.

## Intended coverage

The groups cover all 13 computation operators, two- and three-facet decomposition, dependencies, predicate synonyms, aliases, collisions, NIL, relative/recurring/event-anchored time, authorization denial, explicit falsity, collection-bounded absence, and unsupported counterfactual/conditional structures.

## Freeze gates

1. The builder and validator pass from a clean checkout.
2. Each operator has at least one supported group.
3. Every English/Polish pair shares one template group and split.
4. Every scope-bearing leaf has entity, predicate, namespace, time, authorization, and certificate status.
5. Ambiguous, NIL, unauthorized, and unsupported cases never contain a silently resolved certificate query.
6. At least two different-structure/same-denotation fixtures and two same-structure/different-denotation fixtures are added.
7. A reviewer who did not author the corpus signs the atomicity and utility disposition.

Gates 1-6 can be completed autonomously in this branch. Gate 7 remains an explicit blocker to a confirmatory freeze.
