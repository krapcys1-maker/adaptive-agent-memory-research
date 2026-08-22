# PMLAB-MAP post-freeze challenge v0

Status: generated post-freeze challenge ready for commit freeze; do not score before the freeze commit

This challenge tests whether the unchanged PMLAB-MAP arms generalize beyond the inspectable construction fixture. It contains 14 semantic groups expanded into paired English and Polish cases.

The challenge introduces only post-freeze material:

- a distinct schema family, namespaces, predicates, entities, and aliases;
- compound graphs not present as complete signatures in construction;
- cross-type entity collision, NIL, authorization denial, temporal ambiguity, collection-bounded absence, and unsupported counterfactual cases;
- chains up to five obligations and set/numeric compositions.

The challenge is unseen to the frozen arms but its labels were authored by the same research process and are not independently reviewed. It must therefore be reported as a post-freeze challenge, not a definitive held-out benchmark.

No construction failure may be used to modify either parser before this challenge is scored. Any later repair creates a new version and requires another challenge.
