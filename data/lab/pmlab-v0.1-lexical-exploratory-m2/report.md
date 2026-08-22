# PMLAB v0.1 lexical exploratory M2 result

Status: completed once; model-reviewed exploratory evidence; not confirmatory

## Primary result

| Backend | Macro Recall@5 | All required@5 | Critical miss | Forbidden@5 | Unanswerable null |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0-no-memory | 0.000 | 0.000 | 1.000 | 0.000 | 1.000 |
| B1-ripgrep | 0.697 | 0.618 | 0.714 | 0.133 | 0.000 |
| B2-sqlite-fts5 | 0.755 | 0.673 | 0.714 | 0.150 | 0.000 |
| O-reviewed-evidence | 1.000 | 1.000 | 0.000 | 0.000 | 1.000 |

## Frozen comparison

B2-B1 macro Recall@5 difference: `0.057576`; stratified 95% bootstrap CI: `[0.003030, 0.121212]`.

Decision: `advance-B2-over-B1-exploratory`.

All checks and per-category differences are retained in `final-summary.json`. Rankings matched the sealed primary output across two fresh measurement processes.

## Authority boundary

Gold was produced by blind, role-separated calls to one author-operated model family. This result can falsify or retain a lexical baseline for further exploratory work, but it cannot establish confirmatory validity or promote embeddings, graphs, salience, or a product architecture. H-tier or cross-family replication remains required.

Warm-latency measurements contain 2400 query observations after one unmeasured warmup per query in each fresh process.
