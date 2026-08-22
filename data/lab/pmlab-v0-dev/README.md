# PMLAB v0 development slice

Status: instrument-development-only

This controlled corpus contains two queries for each of the 12 planned PMLAB v0 strata. It exists to debug retrieval, labels, metrics, and failure reporting before the 120-query pilot is independently annotated and frozen.

Files:

- `corpus.jsonl`: versioned synthetic memory records;
- `queries.jsonl`: answerable, stale/forbidden, and unanswerable labels;
- generated artifacts are written below `artifacts/` and may be reproduced with `python scripts/run_memory_benchmark.py`.

The slice is deliberately small and authored with knowledge of the baseline design. Its scores must not be used as architecture-selection evidence.
