# Independent review manual — operational salience ontology v0

## Purpose

Decide whether each factor is observable, separable enough to test, and safe as an external memory-control variable. This is not a review of whether an LLM feels emotion and not an annotation of factual truth.

## Blind boundary

Use only this directory and the cited source freeze. No controller, author target labels, outcome corpus, or backend output exists for this packet. Do not ask the author for preferred answers. An author-operated API worker may provide advice but cannot satisfy the independent gate.

## Review method

1. Review every factor definition for operational observability, overlap, leakage, and unsafe inference.
2. Apply the contract to every probe. Record supported, unsupported, and unresolved factors; do not fill gaps from plausibility.
3. State which actions could be considered and which are prohibited. Permission means eligible for later controlled testing, not permission to mutate facts or delete raw events.
4. Recommend accept, revise, or reject for the whole packet. Any material ambiguity in validity, source authority, target scope, or phase requires revision.
5. Complete and hash-bind the attestation before any author discussion or later comparison.

## Global invariants

- Raw events are append-only and recoverable.
- Salience never establishes factual truth, validity, authorization, or canonical state.
- Model inference has the lowest default authority and repetition is not independent corroboration.
- Unknown remains unknown; emotionally intense wording is not a substitute for evidence.
- Allowed actions are only `no_control_change`, `provisional_eligibility`, `schedule_replay`, `protect_retention`, and `retrieve_more`.
- `delete_raw`, `mutate_canonical_fact`, `bypass_provenance`, and `auto_select_cached_procedure` are always prohibited.
- Every target benefit must be evaluated with quiet, adjacent, peripheral, and competing evidence under a fixed budget.

## Decision meanings

- `accept`: usable to construct a corpus without material ontology changes.
- `revise`: promising, but at least one material definition, boundary, or probe needs repair before corpus freeze.
- `reject`: the ontology cannot support a falsifiable or safe factor-separated experiment.
