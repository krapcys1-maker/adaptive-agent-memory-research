# Recall per 1,000 retrieved words — issue 38

This is content-cost normalization, not a change to retrieval-quality or safety conclusions. Shared definitions and the disclosed query-policy amendment are in [the implementation note](../../../docs/00-project/retrieval-cost-2026-11-04.md).

## Historical costs that survive

Original measurement files are unchanged. The new backfill uses complete per-query observations and ratio-of-means aggregation, without rounding intermediate means.

| Source | Arm/depth | Queries | Recall | Mean retrieved words | Recall / 1,000 words |
| --- | --- | --- | --- | --- | --- |
| PMLAB-H1-BASE-E1 | recall@1 | 84 | 0.785714 | 22.809524 | 34.446764 |
| PMLAB-H1-BASE-E1 | recall@10 | 84 | 0.880952 | 245.928571 | 3.582147 |
| PMLAB-H1-BASE-E1 | recall@5 | 84 | 0.857143 | 117.321429 | 7.305936 |
| PMLAB-H1-ADDR-E1 | addressed | 84 | 1.000000 | 68.761905 | 14.542936 |
| PMLAB-H1-ADDR-E1 | lexical | 84 | 0.880952 | 245.488095 | 3.588575 |

The three old XLANG/association result sets omit both full rankings and token costs. They remain explicitly unavailable; none was reconstructed from current search. Addressed H1 recall is oracle-dependent by construction, so its apparent efficiency is an oracle bound, not evidence for a learned address resolver.

## Fresh fixed-snapshot measurements

Public snapshot: `617e084d1dac62cbd82e30a2a26af1797053e6d6`; 333 source events. These are new measurements, not historical backfill. Source memory bytes stayed unchanged. Dense retrieval used an already cached local model offline; cache-file digests are recorded and unchanged. FastEmbed 0.8.0 has changed pooling for the legacy model alias, so this is not a replication of old dense scores.

The first E1 snapshot inherited automatic query expansion and is retained in `fresh-snapshot/xlang-e1.json`; use `xlang-e1-explicit-baseline.json` for its corrected, explicitly unexpanded baseline. The amendment changes no historical result. E2 and association already used explicit unexpanded lexical search.

### E1, corrected explicit baseline

| Group | Arm | Queries | R@10 | Mean retrieved words@10 | Recall / 1,000 words@10 |
| --- | --- | --- | --- | --- | --- |
| english | b1 | 45 | 1.000000 | 2479.244444 | 0.403349 |
| english | b2 | 45 | 1.000000 | 1842.000000 | 0.542888 |
| english | b3 | 45 | 1.000000 | 2479.244444 | 0.403349 |
| polish | b1 | 45 | 0.155556 | 1301.111111 | 0.119556 |
| polish | b2 | 45 | 0.155556 | 1820.333333 | 0.085454 |
| polish | b3 | 45 | 0.777778 | 1910.266667 | 0.407157 |

### E2, cached dense retrieval

| Group | Arm | Queries | R@10 | Mean retrieved words@10 | Recall / 1,000 words@10 |
| --- | --- | --- | --- | --- | --- |
| english | b1 | 45 | 1.000000 | 2479.244444 | 0.403349 |
| english | b3 | 45 | 1.000000 | 2464.555556 | 0.405753 |
| english | b4 | 45 | 1.000000 | 1254.422222 | 0.797180 |
| english | b5 | 45 | 1.000000 | 1781.044444 | 0.561468 |
| polish | b1 | 45 | 0.155556 | 1301.111111 | 0.119556 |
| polish | b3 | 45 | 0.777778 | 1910.266667 | 0.407157 |
| polish | b4 | 45 | 0.955556 | 1559.600000 | 0.612693 |
| polish | b5 | 45 | 0.933333 | 1878.022222 | 0.496977 |

### Association E3, separate strata

| Group | Arm | Queries | R@10 | Mean retrieved words@10 | Recall / 1,000 words@10 |
| --- | --- | --- | --- | --- | --- |
| primary_mechanical | b1 | 500 | 0.470000 | 4251.068000 | 0.110560 |
| primary_mechanical | b2 | 500 | 0.436000 | 3601.906000 | 0.121047 |
| secondary_tag_only_authored_gold | b1 | 338 | 0.357988 | 3890.662722 | 0.092012 |
| secondary_tag_only_authored_gold | b2 | 338 | 0.375740 | 3311.245562 | 0.113474 |

## Interpretation and reproduction

Cost and recall need to be read together: a cheaper arm can have a higher normalized score while losing answers. Association mechanical and authored-tag gold are never pooled. Dense forbidden/stale intrusion and downstream answer usefulness are not re-measured here. No architecture or retriever is adopted from these tables.

```text
python scripts/backfill_retrieval_cost.py --output NEW_BACKFILL.json
python scripts/run_retrieval_cost_snapshot.py --root SNAPSHOT_ROOT --output NEW_DIRECTORY
python -m pytest -q tests/test_retrieval_metrics.py
```

Dense is optional: add `--dense-cache EXISTING_CACHE`; the driver forces local-only CPU loading and never downloads weights. Reproduce the source snapshot explicitly. Existing outputs cannot be overwritten. The helper counts only item text at the scored depth and retains shown IDs for future audit; it excludes prompt/query wrappers and is not a model-tokenizer count.
