# Research Automation

These scripts make discovery reproducible. Their outputs are candidate lists, not trusted evidence. Every important source must still be read and reviewed.

## Discover papers through OpenAlex

```powershell
python scripts/discover_openalex.py --per-query 40
```

Produces:

- `data/catalogs/papers-discovered.csv`
- a dated raw snapshot in `data/snapshots/`

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
