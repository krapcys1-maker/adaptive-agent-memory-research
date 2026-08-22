# F1/F2 adversarial challenge v0

Status: authored challenge-development-only

This set is held out by entity and query template from `pmlab-forgetting-dev`, but it is not independently annotated. Its purpose is to break assumptions exposed by the first development slice.

## F1

Sixteen cases combine isolated multi-stage failures and missing telemetry. Each probe is run under an explicit upstream control, so the instrument may identify several failed stages without confusing downstream cascading effects with independent faults.

This does not solve causal diagnosis from one end-to-end trace. A real pipeline must actually implement the isolated replays: canonical direct read, retrieval over verified storage, context construction from verified retrieval, reader with gold context, and action with a known-correct answer.

## F2

The corpus contains eight unequal histories and 154 records. Challenge entities are absent from development. `Mercury` and `Jordan` each name two different histories. Queries include exact current state, ISO dates, relative revisions, natural-language dates, Polish wording, ambiguous names, unknown entities, and underspecified time.

The same frozen `top_k=5` is used for no memory, ripgrep, FTS5, the development rule-based entity-time resolver, and the gold oracle. Reader-level value confusion is intentionally still excluded and remains a separate next experiment.

## Reproduction

```powershell
python scripts/run_forgetting_challenge.py
```

The frozen methodology review can be prepared with:

```powershell
python scripts/review_forgetting_benchmark.py prepare --run-id challenge-review-name --dataset data/lab/pmlab-forgetting-challenge-v0
```
