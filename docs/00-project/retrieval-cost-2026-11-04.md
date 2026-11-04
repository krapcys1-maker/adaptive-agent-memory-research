# Retrieval cost normalization — issue 38

## Decisions fixed before new measurements

- Shared helper: `scripts/retrieval_metrics.py`, standard library only. The numerator is the runner's per-query gold-event recall (binary ID hit, or a declared fractional recall); it is not a new measure of downstream usefulness.
- Denominator: whitespace-separated words in item text within the scored depth, not all candidates. H1 uses history-event text. Project-memory runners count title, summary and body, including repeated fields as they would be shown; embedding inputs and ranking are unchanged. Metadata and query/prompt wrappers are excluded. These are content-cost estimates, not tokenizer IDs or the frozen kernel's characters/4 estimate.
- Aggregation: ratio of means, equivalently `1000 * sum(query recall) / sum(query token cost)`. Do not average individual query ratios. Calculate from unrounded observations; round the final statistic to six decimals. Empty samples or zero total tokens produce null, never infinity.
- Apply the helper to H1 baseline/addressing and cross-language E1/E2/association E3 runners. Future records retain the IDs actually shown and token costs at each depth. Plain recall, retrieval ranking and original output artifacts are preserved.
- Historical backfill reads the five named existing result sets. Compute a metric only when every query in that group has its cost. Keep language and mechanical/authored-gold strata separate. Missing historical costs/rankings are unavailable, never inferred by rerunning current retrieval. Old superseded baseline versions are not silently promoted over the corrected H1 reference.
- Fresh model-free demonstrations may run on the fixed public snapshot `617e084d1dac62cbd82e30a2a26af1797053e6d6`; label them as new snapshot measurements, never historical cost reconstruction. No paid model calls or weights downloads are part of this correction.

These are descriptive engineering measurements, not a confirmatory experiment or a new adoption decision. Addressed H1 recall remains oracle-dependent, dense safety remains unmeasured, and association strata retain their leakage-control limitations. Cost normalization does not repair any of those limitations.

## Implementation

Both H1 runners replace duplicated arithmetic with the helper. Cross-language E1/E2 and association E3 append per-arm/depth cost fields and aggregate them next to recall. A separate read-only `scripts/backfill_retrieval_cost.py` emits new analysis files and refuses to overwrite old artifacts. Its output carries source digests and original interpretation caveats.

The existing scripts are mutable experiment runners, not among the script declarations frozen by WMB-R1; that declared import closure and both kernel files are unchanged. Existing measurement JSON and their conclusions remain preserved. New results below will distinguish reproducible historical costs from fresh snapshot measurements and unavailable history.

## Explicit E1 query-policy amendment after the first snapshot run

The fresh E1 baseline unexpectedly matched its glossary arm. Inspection identified an integration defect: `MemoryStore.search` now defaults to `expand=True`, while the legacy E1 runner omitted the argument despite defining B1 as lexical-only. E2 and association E3 already pass `expand=False` explicitly. The initial fresh E1 JSON remains preserved with its actual inherited policy; it is not labelled a pure lexical baseline.

E1 now explicitly disables automatic expansion in every arm, so only labelled B3 receives the authored glossary. A regression assertion pins that policy for all three project-memory runners. This changes E1's new execution to restore its documented arm definition; it does not change published historical results or embedding inputs. A separate corrected-E1 file and source receipt record the rerun on the same snapshot. This is a disclosed post-first-run integration amendment, not an undeclared favorable parameter choice.
