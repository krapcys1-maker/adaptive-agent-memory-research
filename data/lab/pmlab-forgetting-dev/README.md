# F1/F2 forgetting-development slice

Status: instrument-development-only

This deterministic synthetic slice tests whether the laboratory can distinguish data loss from access and downstream failures, then measures how repeated versions affect lexical retrieval. It is authored with knowledge of the tested baselines, has no independent gold annotation, and cannot justify architecture selection.

## F1 fault localization

`f1-fault-cases.jsonl` contains 28 single-fault traces: four variants each for `OK` and stages `F0` through `F5`. Every trace exposes write receipt, canonical integrity, raw-byte recoverability, full-scan, retrieval, context, reader, action, and judge probes. `expected_label` identifies the failed pipeline stage; `expected_data_loss` is a separate claim. A schema or provenance failure can therefore be `F1` without pretending that recoverable bytes were erased.

Passing F1 demonstrates only that the diagnostic rules recover faults intentionally encoded by the author. The next version needs independently authored multi-fault, ambiguous, missing-telemetry, and adversarial traces.

## F2 interference curves

`f2-corpus.jsonl` contains four independent entity histories with 64 versions each. `f2-queries.jsonl` probes current and historical-as-of retrieval after `1, 2, 4, 8, 16, 32, 64` updates, including one Polish query family.

The development comparison uses:

- `B0-no-memory`;
- `B1-ripgrep`;
- `B2-sqlite-fts5`;
- `B3-rule-entity-time`, resolving an exact entity name and optional ISO date from the query before applying temporal validity;
- `O-gold-evidence`.

`B3` does not consume gold query metadata, but its exact-name and ISO-date resolver was authored for this synthetic vocabulary. It does not establish general entity resolution, reader resistance to similar values, context-token behavior, or naturalistic conversation performance.

## Reproduction

```powershell
python scripts/run_forgetting_benchmark.py
```

Generated JSON/JSONL summaries live in `artifacts/`. Temporary ripgrep documents and the FTS5 database are created outside the repository and removed after the run.
