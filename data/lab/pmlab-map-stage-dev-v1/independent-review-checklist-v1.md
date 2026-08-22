# Independent review checklist v1

The reviewer must not see candidate outputs, aggregate scores, or preferred architecture.

For every critical semantic group and a stratified 25% sample of ordinary groups, verify:

- [ ] PL and EN surfaces express the same intent.
- [ ] The case isolates the declared stage; other required inputs are supplied explicitly.
- [ ] Source spans are exact and do not leak the gold ID.
- [ ] Graph nodes are atomic and dependencies point backward.
- [ ] All plausible entity or predicate candidates are represented.
- [ ] NIL subtype or schema ambiguity is justified by visible catalog/schema state.
- [ ] Reference clock, timezone, principal, policy, and collection version are sufficient.
- [ ] Explicit falsity is not confused with not-retrieved or collection-bounded absence.
- [ ] Criticality and asymmetric error consequence are defensible.
- [ ] No surface, catalog ID, composition signature, or ambiguity pattern leaks across the future challenge boundary.

Review output must include reviewer identity/family, review date, source commit, per-field agreement, rationale for material disagreement, and signed freeze recommendation. A worker model may create an advisory queue, but a model under evaluation cannot be the sole reviewer of its own benchmark.
