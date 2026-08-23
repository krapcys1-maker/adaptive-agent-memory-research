# Delayed-reveal auditor v0 failure

Status: failed instrument run; no leakage result

Frozen auditor commit: `5a08f8a`

The first execution stopped while checking registered invalid mutations. Two
mutations were rejected, but an earlier generic consistency check masked the
registered reason class:

- removing the third reveal produced `reveal gold join mismatch` before the
  registered `counterfactual fork requires at least three reveals` check;
- collapsing all answer states produced `state catalog join` before the registered
  `counterfactual answers not incompatible` check.

The fixture was not changed and no threshold or expected reason was changed. The
repair may only reorder the already frozen checks so counterfactual-fork invariants
run before downstream gold/catalog joins. This failed run makes no L0-L4 claim.

Targeted test result at failure: 2 passed, 2 failed. No API call was made and cost
was USD 0.

