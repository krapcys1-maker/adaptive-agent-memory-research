# LifeSim development diagnosis — issues 80 and 81

Tier E descriptive diagnosis on L1 seeds **5..24**, C0 unless stated. No generator, renderer, system, gate, threshold, registration, frozen artifact or golden digest was changed. No models, confirmation seeds or sealed epochs were used. **The benchmark is not repaired. Both issues remain open for fixes.**

The [protocol](../../../docs/00-project/lifesim-development-diagnosis-protocol-2026-11-04.md) was committed before execution (`2a2eb8b`). Complete numerical records accompany this README. `manifest.json` contains the source digest block, platform and 489-second execution time. `execution-receipt.json` distinguishes the execution-start source from the completion HEAD; the measured source stayed byte-identical while tests/integration commits were added. The separate layout/frequency follow-up is explicitly post-diagnosis, not preregistered.

## Canonical reproduction

| Gate | Passed | n | Detail |
| --- | --- | --- | --- |
| G-DET | True | 2 |  |
| G-INV | True | 1 |  |
| G-SOLVE | True | 3183 |  |
| G-SCORE | True | 3183 |  |
| G-HOST | True | 6529 |  |
| G-SUPPORT | True | 2420 |  |
| G-ARO | True | 2923 |  |
| G-LEN | True | 22331 |  |
| G-AFF | True | 22331 |  |
| G-POS | False | 22331 | position tells |
| G-TELL | False | 22331 | surface features predict |
| G-BLIND | False | 2923 | blind arms beat chance |
| G-ORACLE | True | 3183 |  |
| G-DEPTH | True | 3183 |  |
| G-FEAS | False | 20 | cell void: no headroom |
| G-LEAK | True | 20 |  |

Four failures reproduce the issue reports: G-TELL, G-POS, G-BLIND and G-FEAS. A diagnostic ablation below cannot turn any of those failures into a canonical pass.

## G-TELL: several surface channels predict later evidence

Canonical evidence AUC is 0.945458 (one-sided upper95 0.947499; 3,223 positive / 19,108 other lines); top-arousal AUC is 0.619200 (upper95 0.624862). Each ablation reuses the existing world-grouped CV, regularization and 200 world-bootstrap draws. Only the in-memory feature callback is temporarily restricted; the gate file is unchanged.

| Evidence feature block | AUC | Upper95 |
| --- | --- | --- |
| all_minus_ngrams | 0.908281 | 0.911661 |
| all_minus_rare | 0.943626 | 0.945838 |
| capitals | 0.866881 | 0.871528 |
| channel | 0.631125 | 0.638750 |
| day_offset | 0.569640 | 0.581611 |
| day_position | 0.510389 | 0.517238 |
| digits | 0.525530 | 0.531108 |
| length | 0.500053 | 0.508388 |
| ngrams | 0.941082 | 0.943307 |
| numeric | 0.889944 | 0.894537 |
| rare_share | 0.705380 | 0.714467 |
| skeleton | 0.548703 | 0.558490 |
| text-prefix-proxy | 0.945165 | 0.947130 |

Length alone is uninformative, but capitalized internal words alone reach AUC 0.866881, n-grams 0.941082 and rare-token share 0.705380. Removing rarity leaves AUC 0.943626; replacing the latent skeleton with a text-prefix proxy leaves 0.945165. Thus a rare-token-only repair or deleting the template feature is insufficient. These are predictive ablations, not estimates of independent causal contributions.

## G-POS: uniform padding-slot insertion does not imply uniform word position

Canonical clause p rounds to 0.000000; answer-token p is 0.213405. Clause tables (quartiles 0..3) are evidence `[1323, 911, 755, 234]` versus other `[6935, 4957, 5390, 1826]`. The first-fact-slot test conditions on having a fact slot, whereas the clause test includes every line.

Post-diagnosis layout counts show **15,842 other lines with zero slots, and no evidence lines with zero slots**. Evidence has 1.90 slots per ordinary line against 0.33 for ordinary other lines. Article text is 659/3,223 evidence lines but 836/19,108 other lines; its cores average about 24 words and never start in quartile 3 in this run. Single-slot cores average about 9 words, while three-slot cores average 22–23.

`verbalise.render_line_parts` computes padding from `target - core - affect - tag` and samples `k_pre` uniformly over padding-sentence insertion slots. Longer, slot-bearing cores permit fewer padding sentences and less prefix word mass. The mixture of channels, core sizes and slots differs between evidence and other lines. The measured tables and this construction explain why a uniform sentence-slot choice does not satisfy word-quartile independence; they do not isolate every causal contribution. See `surface-diagnosis.json` and the `layout` rows in `followup-layout-and-counts.json`.

## G-BLIND: stream-conditioned guessing is not bounded by the current cap

Passing families cover **0.760520**, below 0.90. Canonical failing B0h accuracies are IN4 0.159292 vs chance 0.041667 (n=226), SE4 0.099476 vs 0.028774 (n=382), and SE5 0.347826 vs 0.025112 (n=92, underpowered).

| Family / asked slot | n | B0h accuracy | Chance |
| --- | --- | --- | --- |
| IN4 / closing_time | 226 | 0.159292 | 0.041667 |
| SE4 / lives_in | 31 | 0.387097 | 0.033333 |
| SE4 / relation | 321 | 0.068536 | 0.029412 |
| SE4 / works_as | 30 | 0.133333 | 0.017241 |
| SE5 / lives_in | 45 | 0.488889 | 0.033333 |
| SE5 / works_as | 47 | 0.212766 | 0.017241 |

The strongest concentration is state questions: SE4 lives_in is 12/31 correct, SE5 lives_in 22/45, and SE5 works_as 10/47. The follow-up records all 700 predictions, stream counts and inferred slots. There are no slot-inference mismatches. Average observed distinct vocabulary values are 11.23 / 16.28 / 15.60 in IN4 / SE4 / SE5; almost every gold value has already appeared. A full-vocabulary uniform chance does not remove the information available to a world-specific stream-frequency guess. This is an explanation of the shortcut, not a replacement chance rule.

Two construction details matter. First, `_cap_select` counts each `(family, ask, gold)` key, but its cap is `floor(share * n_ref)` where `n_ref` is the **total number of selected units across groups**, not that family/ask group size. EP4 pairs are units. Small state groups can therefore retain high gold concentration: mean per-world/group modal shares are about 0.50 for SE4 and 0.45 for SE5. Second, even a true 0.15 group cap would exceed the nominal chance+0.05 bound (about 0.075–0.092 for these families), and a static cap does not bound adaptive, query-time stream guessing.

Proposed repair to test separately: populate state/closing-time answer pools with enough plausible alternatives and changed states, normalize any concentration filter to its actual family/ask target, and audit the unchanged B0h bound on chronological queries. A matching cap alone is not a proof of blind safety. Low-count groups need more development worlds or explicit unsupported status, not relaxed thresholds.

## G-FEAS: surprise exploits an available lexical shortcut; null rehearsal control is duplicated

| Cell | R | GO complete@C | GS complete@C | Headroom | Passed |
| --- | --- | --- | --- | --- | --- |
| C+ | 0.1 | 0.606269 | 0.366661 | 0.239609 | True |
| C+ | 0.25 | 0.709738 | 0.516196 | 0.193542 | False |
| C- | 0.1 | 0.636752 | 0.368293 | 0.268459 | True |
| C- | 0.25 | 0.713160 | 0.510309 | 0.202851 | True |
| C0 | 0.1 | 0.473745 | 0.357500 | 0.116245 | False |
| C0 | 0.25 | 0.678523 | 0.514019 | 0.164504 | False |
| C0r | 0.1 | 0.473745 | 0.357500 | 0.116245 | False |
| C0r | 0.25 | 0.678523 | 0.514019 | 0.164504 | False |

GS is the strongest competitor in all eight cells. On C0, its online surprisal score separates evidence with pooled AUC **0.814057**; final-stream rare-token share gives **0.711526**, and mean within-world Spearman correlation between GS and rarity is **0.452577**. This supports a shared lexical-rarity component of the shortcut, but does not prove that it is the only tell or that a text repair will restore headroom. The feature ablations above rule out that simple inference. No post-repair result is claimed.

For **all 20 seeds**, C0 and C0r have identical world serialization, observations and queries. `Cell.rehearsal` is validated in the schema but not consumed by the query builder or world construction; `make_bundle` constructs the world from `cfg` before selecting the cell. Actual retelling reads `cfg.rehearsal`, which is off in this L1 configuration. A registration that calls C0r a rehearsal-off intervention therefore needs an explicit cell-to-world configuration path and a versioned recheck before it is a distinct control.

Under the unchanged design, null cells are void and cannot support NC1; C+ at R=.10 is live, but that alone does not make X1 valid. After text/answer-pool repairs, remeasure the full sixteen-gate table and feasibility for every control cell. If a null cell still has no headroom, the design/registration needs a different backbone or cell, not an easier H threshold.

## G-DEPTH: sample size, with a narrow empirical minimum

The four-world prefix seeds 5..8 has 17 SE5 items and fails. Eight worlds have fewer than 40; the first passing prefix is **nine worlds, seeds 5..13, with 43 SE5 items**. Twenty worlds have 92 SE5 items and every family passes. All prefixes are retained in `depth-prefixes.json`. Nine is only the empirical minimum for this fixed L1 order, not a power guarantee, an L2 estimate or a reason to shrink the registered 100-seed confirmation range. Keep the twenty-world development reproduction; count family support on the actual tier/configuration before any permitted confirmation execution. None was run here.

## Decision and remaining work

The diagnosis deliverable is complete; the proposed repairs remain unexecuted and issues 80/81 stay open. Do not run confirmation or X1 on this version. Prioritize: (1) balance observable fact/name/content and core-position distributions without breaking slot/invariance contracts, (2) repair answer-pool/concentration construction and route rehearsal settings explicitly, (3) repeat all sixteen development gates and report every moved digest in a new version. Keep the old results and thresholds. A successful engineering suite cannot substitute for those validity checks.

## Reproduce

From the repository root, with the existing development dependencies installed (numpy/scipy are used by the instrument):

```powershell
python scripts/lifesim/development_diagnosis.py --output NEW_DIRECTORY
python scripts/reviews/lifesim_development_followup.py --output NEW_DIRECTORY/followup-layout-and-counts.json
python -m pytest -q tests/test_lifesim_development_diagnosis.py
python tasks.py check
```

The first command rejects non-development seeds and an existing directory; the second refuses to overwrite its output. Seven focused epoch/output/concentration tests pass. The final integrated full-gate and CI receipts are recorded in the PR and delivery handoff.
