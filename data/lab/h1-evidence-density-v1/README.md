# H1 density result — one position-dependent stale failure

All24 public OBSOLETE cases, six three-note conditions, one pinned local Qwen14B seed. [Protocol](PLAN.md) and code/preparation were committed at `0cac1cd`, complete [raw freeze](raw-freeze.json) at `edeb178` before separate gold scoring. This is an oracle-source-ID diagnostic on spent data, not automatic retrieval, difficult external-benchmark performance or confirmation.

| Condition | Answered /24 | Stale leaks /24 |
|---|---:|---:|
| neutral_first | 24 | 0 |
| neutral_last | 24 | 0 |
| stale_repeat_first | 23 | 1 |
| stale_repeat_last | 24 | 0 |
| correction_repeat_first | 24 | 0 |
| correction_repeat_last | 24 | 0 |

The failure is **developmentQ000045**, a different case from the known validationQ000043. The latter passes all six conditions here; its original three-note-pack failure remains preserved. Repeating the same obsolete source ID with the correction first introduces one failure; neutral volume and repeated correction do not in this fixed experiment. This supports a **narrow interaction between repetition and position**, not a proof that order alone caused the original differently worded three-note failure, nor a universal fix. The additional failure is on spent development data, not a held-out discovery. Each arm has24cases; 144generations are not144independent histories. Native prompt counts differ by note content (5922neutral,6543stale-repeat,6295correction-repeat total per arm), despite the same three-note count. A fixed-seed floor on the other arms has low power for broader conclusions.

[Scores](scores.json) retain every case/arm. [Offline integrity replay](artifact-audit.json) reconstructs144native packets, roles, clocks, same-ID repetitions and the explicit synthetic neutral source. No parse errors, raw/source/ledger drift or transport-control failures. It is authored mechanical replay, not independent semantic review.

Actual147new local calls (144primary+3controls), 154.922seconds, zero API calls. H1 cumulative ledger2776→2923 under the **prior** cap3300 amendment `6a24f95`; old byte prefix retained. Model digest unchanged and owned model unloaded. API463attempts/$1.852reserved remains unchanged.

Decision: do not alter production packing based on one case. Execute the separately frozen [whole-H1 paired chronological comparison](../h1-chronological-pack-v1/PLAN.md), including all seven families and losses, with no new oracle source selection. Its result is separate; no success is presumed here.
