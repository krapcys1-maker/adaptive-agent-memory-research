# PMLAB-DECORR-E1 — tier I3 cannot be instantiated on the data this project holds

Experiment ID: `PMLAB-DECORR-E1`
Tier: **E (exploratory)** — analysis is model-free and spends no API budget
Authority: development measurement only.

## What was attempted

The independence ladder asserts that a same-family model panel counts as **one** reviewer, and requires tier I3 to *measure* error correlation rather than assert it. That measurement had never been made, so I3 was a label rather than a tier.

Issue #24 stated the measurement was "buildable and testable entirely on existing recorded label files". **That assumption was wrong**, and this run establishes why.

## Why the obvious dataset cannot answer it

The project holds one two-reviewer dataset: roles A and B of the same model over 120 queries. Its gold is derived from those very labels.

```
resolution:      unanimous_roles_a_b       95
                 blind_model_adjudication  25
human_confirmed: False                    120
```

On 95 items both roles are correct **by construction**, because gold *is* their agreement. On 25 exactly one is wrong by construction, because a third same-family role picked the winner. An error correlation computed against that gold would measure the construction rather than the reviewers.

## What was measured instead

One property is decidable from the bytes with no gold at all: **did a role cite an evidence identifier absent from the material it was shown?** The job payload records exactly which records each query presented. A citation outside that set is a fabrication — wrong regardless of anyone's judgement, and detectable with no model and no adjudicator.

That is a genuine I0 ground truth, and it is the kind the ladder specifies.

## Result

```
queries compared          120
fabrications, role A        0
fabrications, role B        0
fabrications on the same query  0

error correlation phi     undefined
```

**Neither role fabricated once.** The error vectors are therefore constant, and the correlation of two constant vectors is **undefined, not zero**. The script reports it as undefined and says why, because reporting 0.0 here would claim independence that was never measured.

## The finding

> Tier I3 needs errors to measure. A dataset in which the reviewers do not err on the only mechanically decidable dimension yields no signal, however many items it contains.

This is not a defect in the reviewers or the harness. It is a property of the pairing: the mechanical dimension available here is easy enough that a competent model does not fail it, and the dimension where models *do* disagree — the semantic labels — has no gold that is independent of the labels themselves.

## What I3 actually requires, none of which exists today

1. **A harder mechanical task**, where models measurably fail often enough for a correlation to be estimated.
2. **Human-confirmed gold**, which is tier I4 or I5 and is precisely the scarce resource the ladder was built to route around.
3. **A genuinely cross-family panel**, which needs new API spend against a second provider.

Until one is built, **I3 remains a label**, and any claim resting on a model panel must be recorded as `asserted` rather than as measured. The ladder already specifies that fallback; this run shows the fallback is currently the only honest option.

## Limits

- One dataset, one model family, one task.
- The mechanical dimension is narrow: identifier fabrication only. Other decidable properties — schema validity, span exactness — were not extracted here and might show errors where this one does not.
- Absence of fabrication on 120 queries is not evidence that fabrication never occurs; it bounds the rate loosely at best.

## What follows

Issue #24 is corrected rather than closed as done. The harness exists and is reusable; what it lacks is a dataset with errors to correlate. The cheapest path to one is extracting a second mechanical dimension from the same recorded runs, which costs nothing and may yet produce a usable error vector.
