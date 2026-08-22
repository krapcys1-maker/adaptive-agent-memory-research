# Research Automation

These scripts make discovery reproducible. Their outputs are candidate lists, not trusted evidence. Every important source must still be read and reviewed.

`build_metamemory_dev_corpus.py` deterministically authors the frozen construction corpus for PMLAB-META-001. `run_metamemory_control_dev.py` verifies its hash and compares scalar confidence, typed monitoring, typed control, and an oracle ceiling without network or model calls.

## Discover papers through OpenAlex

```powershell
python scripts/discover_openalex.py --per-query 40
```

Produces:

- `data/catalogs/papers-discovered.csv`
- a dated raw snapshot in `data/snapshots/`

## Budgeted literature screening

`screen_literature.py` prepares frozen public-metadata batches and can send them to DeepSeek V4 Flash as review candidates. It enforces a cumulative conservative USD budget, disables thinking, validates JSON, supports resume, and never stores the API key.

```powershell
python scripts/screen_literature.py prepare --run-id pilot-name --per-profile 5
python scripts/screen_literature.py run --run-id pilot-name --budget-usd 10
```

The default ignored key location is the parent workspace `.env` with `DEEPSEEK_API_KEY`. Outputs under `data/lab/api-screening/` are screening artifacts, not accepted evidence.

## PMLAB development comparison

Run the controlled 24-query instrument-development slice:

```powershell
python scripts/run_memory_benchmark.py
```

This compares no memory, actual `rg`, and SQLite FTS5. Its scores are diagnostic only; the slice is not the independently annotated 120-query PMLAB v0.

## F1/F2 forgetting diagnostics

Build and run the authored fault-localization and version-interference development slice:

```powershell
python scripts/run_forgetting_benchmark.py
```

To request a bounded adversarial methodology review after freezing a run:

```powershell
python scripts/review_forgetting_benchmark.py prepare --run-id review-name
python scripts/review_forgetting_benchmark.py run --run-id review-name --budget-usd 10
```

The review worker receives only synthetic metadata and aggregate results. Its output remains an unreviewed candidate queue until a local review records each disposition.

Run the adversarial entity/time and multi-fault challenge:

```powershell
python scripts/run_forgetting_challenge.py
```

This challenge is separated from development by entities and query templates, but it is still project-authored and must not be described as independently labeled.

Factor query normalization from history scope, then run the optional reader pilot:

```powershell
python scripts/run_query_scope_factorial.py
python scripts/run_reader_interference.py prepare
python scripts/run_reader_interference.py run --budget-usd 10
```

The stronger reader factorial is generated and run with `run_reader_stress.py`. Every model payload must pass gold-field, opaque-ID, per-case identity-isolation, and opaque-case-ID tests. V1–V4 are retained as leakage audits; v5 is the first fully interpretable stress run.

Compare passive cascading telemetry with controlled active probes for capture, storage, retrieval, selection, reader, and action stages:

```powershell
python scripts/run_fault_probe_comparison.py
```

Stress the active probes with transient, persistent, and correlated measurement failures:

```powershell
python scripts/run_fault_probe_robustness.py
```

Calculate the exact expected healthy-result audit curve:

```powershell
python scripts/run_probe_success_audit_curve.py
```

Exercise the storage diagnostic state machine against disposable real files. The script verifies its generated system-temp root before any unlink or truncation:

```powershell
python scripts/run_storage_fault_injection.py
```

Run the deterministic entity/time parser baseline against challenge v0:

```powershell
python scripts/run_query_parser_baseline.py
```

Run the post-freeze language/date challenge against unchanged parser v0:

```powershell
python scripts/run_query_parser_challenge.py
```

## Verify screening-source identity

Resolve `include` candidates through DOI content negotiation and the OpenAlex work endpoint:

```powershell
python scripts/audit_screening_sources.py
```

This verifies bibliographic identity only. It does not mark a paper read or validate a scientific claim.

## Refresh GitHub metadata

```powershell
powershell -ExecutionPolicy Bypass -File scripts/refresh-github-catalog.ps1
```

Produces `data/catalogs/repositories-current.csv` using the GitHub CLI.

## Download selected repositories

```powershell
powershell -ExecutionPolicy Bypass -File scripts/sync-repositories.ps1
```

Only rows with `download=yes` are shallow-cloned into the ignored `external/repos/` cache. Existing clones are fetched but not force-reset.

## Download open-access PDFs

```powershell
python scripts/download_papers.py
```

The script only uses nonempty `pdf_url` values from the curated catalog and verifies that the response is a PDF. Files are placed in the ignored `sources/papers/` cache.
