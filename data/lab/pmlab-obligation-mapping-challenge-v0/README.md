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

The unchanged deterministic QDMR arm has now been scored. It fell from construction F1 0.922 to 0.409, produced 18 critical omissions and ten false closures, and reached zero end-to-end exact cases. Even gold obligations plus its frozen linker reached only 0.071 end-to-end exact. Full artifacts are in `deterministic-artifacts/`; no rule was repaired before scoring.

The unchanged optional-model prompt also failed: 13/28 schema-valid predictions, F1 0.325, 17 critical omissions, two false closures, and 0.107 end-to-end exact. Both candidate arms are rejected; their different error profiles motivate factorized stage tests rather than choosing either implementation.
