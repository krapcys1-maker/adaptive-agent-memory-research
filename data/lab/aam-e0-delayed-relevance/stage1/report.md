# AAM-E0 Stage 1 report: retrieval-level run on the test seeds

Status: exploratory, tier E, synthetic worlds written by an agent, no independent review. Generator `goalshift-v0.2`. Seeds 100-119 (20 scenarios, 240 probes). Embedder `minilm`. Environment and wall-clock: `results.json` and `timing.json`.

## Verdict, exactly as the rules say

**NOT SUPPORTED: D minus the best of Del/Sum/Sum-raw is -0.050 (threshold 0.15); the 95% interval's lower bound is -0.125.**

- Also: a summary index with expansion is at least as good (Sum-raw 0.125 vs D 0.075; within 0.05 or better).

- Also: no better than conventional retrieval; at most a smaller index (F2 0.200 >= D 0.075).

## Primary comparison (strict gold, the pre-declared measure)

| quantity | value |
|---|---|
| cell / C / R | C3 / 250 words / 10% |
| D gold-in-context | 0.075 |
| best comparator chosen on dev seeds | Sum-raw (0.125) |
| D minus best, mean over scenarios | -0.05 |
| paired bootstrap 95%% interval | [-0.125, 0.0125] |
| F2 (dense over everything) | 0.2 |
| O (oracle concepts, cheaper traces) | 0.55 |
| Oc (oracle concepts, D's stored set and costs) | 0.2 |
| S (shuffled pointers, mean of 20 shuffles) | 0.0488 |

The comparator was chosen on 20 development probes, a noisy draw, not a finding. The interval is a percentile bootstrap over 20 scenarios: discrete and coarse, so lower bound above zero is a blunt criterion.

## Secondary: the same comparison by event id (a summary counts)

| quantity | value |
|---|---|
| D | 0.075 |
| best comparator chosen on dev (by id) | Sum (0.175) |
| D minus best, mean over scenarios | -0.1 |
| 95% interval | [-0.1875, -0.025] |

Reading: NOT SUPPORTED: D minus the best of Del/Sum/Sum-raw is -0.100 (threshold 0.15); the 95% interval's lower bound is -0.188.

## D against each comparator and control (same cell, C, R; strict gold)

| comparator or control | rate | D minus it | 95% interval |
|---|---|---|---|
| Del | 0.0625 | 0.0125 | [-0.05, 0.075] |
| Sum | 0.0 | 0.075 | [0.025, 0.1375] |
| Sum-raw | 0.125 | -0.05 | [-0.125, 0.0125] |
| F2 | 0.2 | -0.125 | [-0.2375, 0.0] |
| S | 0.0488 | 0.0263 | [-0.0162, 0.0719] |
| Oc | 0.2 | -0.125 | [-0.2125, -0.05] |

## Where D loses: stored or retrieved (C3, C=250)

| arm | R | gold stored | gold in context | stored but not retrieved |
|---|---|---|---|---|
| Del | 10% | 0.062 | 0.062 | 0.000 |
| Del | 25% | 0.188 | 0.100 | 0.087 |
| Sum-raw | 10% | 0.175 | 0.125 | 0.050 |
| Sum-raw | 25% | 0.287 | 0.075 | 0.212 |
| D | 10% | 0.200 | 0.075 | 0.125 |
| D | 25% | 0.500 | 0.087 | 0.412 |
| O | 10% | 0.550 | 0.550 | 0.000 |
| O | 25% | 1.000 | 1.000 | 0.000 |
| Oc | 10% | 0.200 | 0.200 | 0.000 |
| Oc | 25% | 0.500 | 0.500 | 0.000 |
| S | 10% | 0.200 | 0.049 | 0.151 |
| S | 25% | 0.500 | 0.105 | 0.395 |

## C3 by role (strict gold, C=250, R=10%, F2 without R)

| role | n | Del | Sum-raw | F2 | D | Oc | S |
|---|---|---|---|---|---|---|---|
| estimate_slip | 10 | 0.100 | 0.200 | 0.000 | 0.000 | 0.400 | 0.110 |
| failed_approach | 10 | 0.200 | 0.100 | 0.500 | 0.300 | 0.300 | 0.085 |
| hard_constraint | 10 | 0.000 | 0.100 | 0.800 | 0.000 | 0.100 | 0.020 |
| late_approval | 10 | 0.000 | 0.200 | 0.000 | 0.200 | 0.200 | 0.070 |
| scale_surprise | 10 | 0.100 | 0.100 | 0.000 | 0.000 | 0.100 | 0.010 |
| silent_dependency | 10 | 0.100 | 0.200 | 0.000 | 0.000 | 0.200 | 0.025 |
| single_owner | 10 | 0.000 | 0.100 | 0.200 | 0.100 | 0.200 | 0.065 |
| unreliable_party | 10 | 0.000 | 0.000 | 0.100 | 0.000 | 0.100 | 0.005 |

Cell C3 mixes roles that are paraphrases of the cue for a dense model with abstract ones; with 20 scenarios each role has only about 10 worlds x 1 probe.

## Gold-in-context, strict, every arm, cell, C and R

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 1.000 | 1.000 | 1.000 |
| F1 | C2 | 0.000 | 0.000 | 0.000 |
| F1 | C3 | 0.000 | 0.037 | 0.037 |
| F1 | ALL | 0.333 | 0.346 | 0.346 |
| F2 | C1 | 0.988 | 0.988 | 1.000 |
| F2 | C2 | 0.588 | 0.863 | 0.950 |
| F2 | C3 | 0.087 | 0.200 | 0.325 |
| F2 | ALL | 0.554 | 0.683 | 0.758 |
| B3 | C1 | 0.000 | 0.000 | 0.000 |
| B3 | C2 | 0.000 | 0.000 | 0.000 |
| B3 | C3 | 0.000 | 0.000 | 0.000 |
| B3 | ALL | 0.000 | 0.000 | 0.000 |
| Del | C1 | 0.087 / 0.175 | 0.087 / 0.175 | 0.087 / 0.175 |
| Del | C2 | 0.013 / 0.013 | 0.025 / 0.062 | 0.025 / 0.138 |
| Del | C3 | 0.025 / 0.037 | 0.062 / 0.100 | 0.062 / 0.188 |
| Del | ALL | 0.042 / 0.075 | 0.058 / 0.113 | 0.058 / 0.167 |
| Sum | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum-raw | C1 | 0.125 / 0.425 | 0.138 / 0.425 | 0.138 / 0.425 |
| Sum-raw | C2 | 0.125 / 0.188 | 0.138 / 0.263 | 0.138 / 0.275 |
| Sum-raw | C3 | 0.037 / 0.025 | 0.125 / 0.075 | 0.175 / 0.200 |
| Sum-raw | ALL | 0.096 / 0.212 | 0.133 / 0.254 | 0.150 / 0.300 |
| D | C1 | 0.125 / 0.275 | 0.200 / 0.412 | 0.200 / 0.500 |
| D | C2 | 0.075 / 0.025 | 0.087 / 0.163 | 0.087 / 0.338 |
| D | C3 | 0.050 / 0.037 | 0.075 / 0.087 | 0.075 / 0.250 |
| D | ALL | 0.083 / 0.113 | 0.121 / 0.221 | 0.121 / 0.362 |
| O | C1 | 0.562 / 1.000 | 0.562 / 1.000 | 0.562 / 1.000 |
| O | C2 | 0.575 / 1.000 | 0.575 / 1.000 | 0.575 / 1.000 |
| O | C3 | 0.550 / 1.000 | 0.550 / 1.000 | 0.550 / 1.000 |
| O | ALL | 0.562 / 1.000 | 0.562 / 1.000 | 0.562 / 1.000 |
| Oc | C1 | 0.250 / 0.575 | 0.250 / 0.575 | 0.250 / 0.575 |
| Oc | C2 | 0.175 / 0.575 | 0.175 / 0.575 | 0.175 / 0.575 |
| Oc | C3 | 0.200 / 0.500 | 0.200 / 0.500 | 0.200 / 0.500 |
| Oc | ALL | 0.208 / 0.550 | 0.208 / 0.550 | 0.208 / 0.550 |
| S | C1 | 0.043 / 0.036 | 0.101 / 0.097 | 0.113 / 0.209 |
| S | C2 | 0.023 / 0.039 | 0.043 / 0.104 | 0.043 / 0.209 |
| S | C3 | 0.027 / 0.033 | 0.049 / 0.105 | 0.054 / 0.183 |
| S | ALL | 0.031 / 0.036 | 0.064 / 0.102 | 0.070 / 0.200 |

## Gold stored

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| Del | C1 | 0.087 / 0.175 | 0.087 / 0.175 | 0.087 / 0.175 |
| Del | C2 | 0.025 / 0.138 | 0.025 / 0.138 | 0.025 / 0.138 |
| Del | C3 | 0.062 / 0.188 | 0.062 / 0.188 | 0.062 / 0.188 |
| Del | ALL | 0.058 / 0.167 | 0.058 / 0.167 | 0.058 / 0.167 |
| Sum | C1 | 0.138 / 0.438 | 0.138 / 0.438 | 0.138 / 0.438 |
| Sum | C2 | 0.138 / 0.300 | 0.138 / 0.300 | 0.138 / 0.300 |
| Sum | C3 | 0.175 / 0.287 | 0.175 / 0.287 | 0.175 / 0.287 |
| Sum | ALL | 0.150 / 0.342 | 0.150 / 0.342 | 0.150 / 0.342 |
| Sum-raw | C1 | 0.138 / 0.438 | 0.138 / 0.438 | 0.138 / 0.438 |
| Sum-raw | C2 | 0.138 / 0.300 | 0.138 / 0.300 | 0.138 / 0.300 |
| Sum-raw | C3 | 0.175 / 0.287 | 0.175 / 0.287 | 0.175 / 0.287 |
| Sum-raw | ALL | 0.150 / 0.342 | 0.150 / 0.342 | 0.150 / 0.342 |
| D | C1 | 0.250 / 0.575 | 0.250 / 0.575 | 0.250 / 0.575 |
| D | C2 | 0.175 / 0.575 | 0.175 / 0.575 | 0.175 / 0.575 |
| D | C3 | 0.200 / 0.500 | 0.200 / 0.500 | 0.200 / 0.500 |
| D | ALL | 0.208 / 0.550 | 0.208 / 0.550 | 0.208 / 0.550 |
| O | C1 | 0.562 / 1.000 | 0.562 / 1.000 | 0.562 / 1.000 |
| O | C2 | 0.575 / 1.000 | 0.575 / 1.000 | 0.575 / 1.000 |
| O | C3 | 0.550 / 1.000 | 0.550 / 1.000 | 0.550 / 1.000 |
| O | ALL | 0.562 / 1.000 | 0.562 / 1.000 | 0.562 / 1.000 |
| Oc | C1 | 0.250 / 0.575 | 0.250 / 0.575 | 0.250 / 0.575 |
| Oc | C2 | 0.175 / 0.575 | 0.175 / 0.575 | 0.175 / 0.575 |
| Oc | C3 | 0.200 / 0.500 | 0.200 / 0.500 | 0.200 / 0.500 |
| Oc | ALL | 0.208 / 0.550 | 0.208 / 0.550 | 0.208 / 0.550 |
| S | C1 | 0.250 / 0.575 | 0.250 / 0.575 | 0.250 / 0.575 |
| S | C2 | 0.175 / 0.575 | 0.175 / 0.575 | 0.175 / 0.575 |
| S | C3 | 0.200 / 0.500 | 0.200 / 0.500 | 0.200 / 0.500 |
| S | ALL | 0.208 / 0.550 | 0.208 / 0.550 | 0.208 / 0.550 |

## By event id

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 1.000 | 1.000 | 1.000 |
| F1 | C2 | 0.000 | 0.000 | 0.000 |
| F1 | C3 | 0.000 | 0.037 | 0.037 |
| F1 | ALL | 0.333 | 0.346 | 0.346 |
| F2 | C1 | 0.988 | 0.988 | 1.000 |
| F2 | C2 | 0.588 | 0.863 | 0.950 |
| F2 | C3 | 0.087 | 0.200 | 0.325 |
| F2 | ALL | 0.554 | 0.683 | 0.758 |
| B3 | C1 | 0.000 | 0.000 | 0.000 |
| B3 | C2 | 0.000 | 0.000 | 0.000 |
| B3 | C3 | 0.000 | 0.000 | 0.000 |
| B3 | ALL | 0.000 | 0.000 | 0.000 |
| Del | C1 | 0.087 / 0.175 | 0.087 / 0.175 | 0.087 / 0.175 |
| Del | C2 | 0.013 / 0.013 | 0.025 / 0.062 | 0.025 / 0.138 |
| Del | C3 | 0.025 / 0.037 | 0.062 / 0.100 | 0.062 / 0.188 |
| Del | ALL | 0.042 / 0.075 | 0.058 / 0.113 | 0.058 / 0.167 |
| Sum | C1 | 0.125 / 0.425 | 0.138 / 0.425 | 0.138 / 0.438 |
| Sum | C2 | 0.138 / 0.237 | 0.138 / 0.287 | 0.138 / 0.300 |
| Sum | C3 | 0.100 / 0.050 | 0.175 / 0.188 | 0.175 / 0.287 |
| Sum | ALL | 0.121 / 0.237 | 0.150 / 0.300 | 0.150 / 0.342 |
| Sum-raw | C1 | 0.125 / 0.425 | 0.138 / 0.425 | 0.138 / 0.425 |
| Sum-raw | C2 | 0.125 / 0.188 | 0.138 / 0.263 | 0.138 / 0.275 |
| Sum-raw | C3 | 0.037 / 0.025 | 0.125 / 0.075 | 0.175 / 0.200 |
| Sum-raw | ALL | 0.096 / 0.212 | 0.133 / 0.254 | 0.150 / 0.300 |
| D | C1 | 0.125 / 0.275 | 0.200 / 0.412 | 0.200 / 0.500 |
| D | C2 | 0.075 / 0.025 | 0.087 / 0.163 | 0.087 / 0.338 |
| D | C3 | 0.050 / 0.037 | 0.075 / 0.087 | 0.075 / 0.250 |
| D | ALL | 0.083 / 0.113 | 0.121 / 0.221 | 0.121 / 0.362 |
| O | C1 | 0.562 / 1.000 | 0.562 / 1.000 | 0.562 / 1.000 |
| O | C2 | 0.575 / 1.000 | 0.575 / 1.000 | 0.575 / 1.000 |
| O | C3 | 0.550 / 1.000 | 0.550 / 1.000 | 0.550 / 1.000 |
| O | ALL | 0.562 / 1.000 | 0.562 / 1.000 | 0.562 / 1.000 |
| Oc | C1 | 0.250 / 0.575 | 0.250 / 0.575 | 0.250 / 0.575 |
| Oc | C2 | 0.175 / 0.575 | 0.175 / 0.575 | 0.175 / 0.575 |
| Oc | C3 | 0.200 / 0.500 | 0.200 / 0.500 | 0.200 / 0.500 |
| Oc | ALL | 0.208 / 0.550 | 0.208 / 0.550 | 0.208 / 0.550 |
| S | C1 | 0.043 / 0.036 | 0.101 / 0.097 | 0.113 / 0.209 |
| S | C2 | 0.023 / 0.039 | 0.043 / 0.104 | 0.043 / 0.209 |
| S | C3 | 0.027 / 0.033 | 0.049 / 0.105 | 0.054 / 0.183 |
| S | ALL | 0.031 / 0.036 | 0.064 / 0.102 | 0.070 / 0.200 |

## Decoy intrusion (mean decoys in context)

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 2.013 | 2.087 | 2.275 |
| F1 | C2 | 2.000 | 2.112 | 2.138 |
| F1 | C3 | 1.062 | 1.262 | 1.387 |
| F1 | ALL | 1.692 | 1.821 | 1.933 |
| F2 | C1 | 0.562 | 1.150 | 1.738 |
| F2 | C2 | 0.700 | 1.225 | 1.837 |
| F2 | C3 | 0.537 | 0.863 | 1.275 |
| F2 | ALL | 0.600 | 1.079 | 1.617 |
| B3 | C1 | 0.050 | 0.275 | 0.725 |
| B3 | C2 | 0.087 | 0.338 | 0.713 |
| B3 | C3 | 0.062 | 0.375 | 0.675 |
| B3 | ALL | 0.067 | 0.329 | 0.704 |
| Del | C1 | 0.138 / 0.338 | 0.175 / 0.388 | 0.175 / 0.525 |
| Del | C2 | 0.212 / 0.525 | 0.275 / 0.613 | 0.275 / 0.725 |
| Del | C3 | 0.150 / 0.400 | 0.212 / 0.537 | 0.212 / 0.662 |
| Del | ALL | 0.167 / 0.421 | 0.221 / 0.512 | 0.221 / 0.637 |
| Sum | C1 | 0.250 / 0.525 | 0.375 / 0.762 | 0.375 / 1.075 |
| Sum | C2 | 0.388 / 0.675 | 0.500 / 0.863 | 0.500 / 1.113 |
| Sum | C3 | 0.250 / 0.425 | 0.412 / 0.800 | 0.412 / 1.150 |
| Sum | ALL | 0.296 / 0.542 | 0.429 / 0.808 | 0.429 / 1.113 |
| Sum-raw | C1 | 0.188 / 0.300 | 0.325 / 0.637 | 0.375 / 0.887 |
| Sum-raw | C2 | 0.350 / 0.575 | 0.463 / 0.750 | 0.500 / 0.900 |
| Sum-raw | C3 | 0.138 / 0.312 | 0.338 / 0.512 | 0.412 / 0.863 |
| Sum-raw | ALL | 0.225 / 0.396 | 0.375 / 0.633 | 0.429 / 0.883 |
| D | C1 | 0.300 / 0.438 | 0.350 / 0.938 | 0.362 / 1.175 |
| D | C2 | 0.287 / 0.412 | 0.425 / 0.713 | 0.463 / 1.075 |
| D | C3 | 0.138 / 0.175 | 0.263 / 0.425 | 0.287 / 0.725 |
| D | ALL | 0.242 / 0.342 | 0.346 / 0.692 | 0.371 / 0.992 |
| O | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| S | C1 | 0.141 / 0.182 | 0.256 / 0.378 | 0.269 / 0.677 |
| S | C2 | 0.143 / 0.169 | 0.281 / 0.380 | 0.302 / 0.717 |
| S | C3 | 0.089 / 0.125 | 0.174 / 0.345 | 0.189 / 0.639 |
| S | ALL | 0.124 / 0.159 | 0.237 / 0.367 | 0.253 / 0.677 |

## Negative transfer (decoy present and gold absent)

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 0.000 | 0.000 | 0.000 |
| F1 | C2 | 1.000 | 1.000 | 1.000 |
| F1 | C3 | 1.000 | 0.963 | 0.963 |
| F1 | ALL | 0.667 | 0.654 | 0.654 |
| F2 | C1 | 0.013 | 0.013 | 0.000 |
| F2 | C2 | 0.200 | 0.113 | 0.050 |
| F2 | C3 | 0.412 | 0.512 | 0.588 |
| F2 | ALL | 0.208 | 0.212 | 0.212 |
| B3 | C1 | 0.050 | 0.250 | 0.550 |
| B3 | C2 | 0.087 | 0.312 | 0.588 |
| B3 | C3 | 0.062 | 0.350 | 0.588 |
| B3 | ALL | 0.067 | 0.304 | 0.575 |
| Del | C1 | 0.125 / 0.250 | 0.163 / 0.275 | 0.163 / 0.362 |
| Del | C2 | 0.200 / 0.450 | 0.250 / 0.500 | 0.250 / 0.525 |
| Del | C3 | 0.150 / 0.350 | 0.200 / 0.438 | 0.200 / 0.438 |
| Del | ALL | 0.158 / 0.350 | 0.204 / 0.404 | 0.204 / 0.442 |
| Sum | C1 | 0.212 / 0.412 | 0.312 / 0.550 | 0.312 / 0.713 |
| Sum | C2 | 0.325 / 0.525 | 0.400 / 0.613 | 0.400 / 0.738 |
| Sum | C3 | 0.250 / 0.388 | 0.375 / 0.625 | 0.375 / 0.787 |
| Sum | ALL | 0.263 / 0.442 | 0.362 / 0.596 | 0.362 / 0.746 |
| Sum-raw | C1 | 0.138 / 0.200 | 0.225 / 0.300 | 0.263 / 0.362 |
| Sum-raw | C2 | 0.263 / 0.400 | 0.325 / 0.400 | 0.350 / 0.438 |
| Sum-raw | C3 | 0.125 / 0.287 | 0.275 / 0.412 | 0.300 / 0.500 |
| Sum-raw | ALL | 0.175 / 0.296 | 0.275 / 0.371 | 0.304 / 0.433 |
| D | C1 | 0.263 / 0.300 | 0.263 / 0.375 | 0.275 / 0.375 |
| D | C2 | 0.237 / 0.350 | 0.338 / 0.475 | 0.362 / 0.438 |
| D | C3 | 0.125 / 0.163 | 0.212 / 0.300 | 0.237 / 0.400 |
| D | ALL | 0.208 / 0.271 | 0.271 / 0.383 | 0.292 / 0.404 |
| O | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| S | C1 | 0.131 / 0.171 | 0.217 / 0.303 | 0.223 / 0.429 |
| S | C2 | 0.132 / 0.160 | 0.234 / 0.308 | 0.249 / 0.454 |
| S | C3 | 0.086 / 0.119 | 0.152 / 0.284 | 0.161 / 0.404 |
| S | ALL | 0.116 / 0.150 | 0.201 / 0.298 | 0.211 / 0.429 |

## False-association rate of the trace arms (fetched events that are not gold, all fetched through a concept link), C=250, R=10%

| arm | cell | false-association rate | events fetched |
|---|---|---|---|
| D | C1 | 0.9831 | 11.86 |
| D | C2 | 0.9917 | 10.53 |
| D | C3 | 0.9923 | 9.72 |
| D | ALL | 0.9887 | 10.7 |
| O | C1 | 0.0 | 0.56 |
| O | C2 | 0.0 | 0.57 |
| O | C3 | 0.0 | 0.55 |
| O | ALL | 0.0 | 0.56 |
| Oc | C1 | 0.0 | 0.25 |
| Oc | C2 | 0.0 | 0.17 |
| Oc | C3 | 0.0 | 0.2 |
| Oc | ALL | 0.0 | 0.21 |
| S | C1 | 0.9916 | 12.03 |
| S | C2 | 0.996 | 10.66 |
| S | C3 | 0.995 | 9.82 |
| S | ALL | 0.9941 | 10.84 |

## D under other concept rules and thresholds (secondary; C=250)

| variant | C1 R=10% | C2 R=10% | C3 R=10% | C1 R=25% | C2 R=25% | C3 R=25% |
|---|---|---|---|---|---|---|
| primary: concept df>=2, stem>=4 letters, cluster/query threshold 0.55 | 0.2 | 0.0875 | 0.075 | 0.4125 | 0.1625 | 0.0875 |
| v0.1 concept rule: any df, stem>=3 letters | 0.2125 | 0.0625 | 0.075 | 0.525 | 0.2 | 0.0875 |
| cluster/query threshold 0.45 | 0.15 | 0.075 | 0.0875 | 0.25 | 0.0625 | 0.05 |
| cluster/query threshold 0.65 | 0.1875 | 0.025 | 0.0375 | 0.475 | 0.125 | 0.075 |

## Limits

- Strict gold is primary: the reference code must be in the delivered text. By event id (secondary) a
  lead-truncated 8-word summary counts as the gold event although it does not hold the answer.
- Write-time importance is uninformative by construction (v0.2). This follows the specification's
  low-salience targets and removes a leak found in v0.1, at the cost that forgetting arms keep a
  random subset of the older events; their headroom is then set by their coverage, not by retrieval.
- O stores traces at about 2 words each, D at up to 6 (distinct clusters plus a pointer). At the same
  R, O therefore stores about three times as many events; O is an oracle with cheaper traces, not a
  same-footing upper bound on D. Oc (D's stored set and costs, oracle concepts) is the like-for-like
  oracle. 'Gold stored' separates a loss from not storing from a loss from not retrieving.
- The oracle gate tests the retrieval path (reach the gold when it is stored) and unconditional O at
  R=25%, where the budget is not binding. It does not claim that O is near 1 at R=10%.
- S is the mean of 20 independent pointer shuffles per probe (a spread, not one draw). Its gate is
  loose by nature; read the paired D minus S contrast instead.
- Summaries are lead-truncated extracts, a weaker stand-in for a model summary.
- Concept phrases for D are stemmed content words, not multiword phrases. D keeps a concept only if it
  occurs in at least 2 visible events and has at least 4 letters (fixed a priori, before the test
  seeds, after a dev diagnostic by a verifier showed one-off names and stemmer fragments dominated
  the concepts). D's sensitivity to that rule and to the cluster threshold is in the secondary table.
  Do not read 'not tuned' as 'robust'.
- Free resources are not charged to R: D's cluster vocabulary, seed vectors and co-occurrence table
  (built from all visible events, including dormant ones, so richer than a sequential ingest) and the
  dense index of Sum and Sum-raw. R measures only the stored trace or summary words.
- Cell C3 mixes roles of different difficulty (some are close paraphrases of the cue for a dense
  model, others are abstract). Roles are balanced across the test seeds (alternate worlds take
  alternate halves of the eight); tables per role are in the Stage 1 report.
- Overlap is measured in the arms' own token space (one stop-word list and crude stemmer shared by
  the generator, the overlap measure and D), so D's direct lexical route is blocked by construction.
- Every event carries a reference code, so the code tag says nothing about which event is a target.
  The reader question still says 'reference code'; a Stage 2 reader could pick any code in the context.
- The semantic gate thresholds were written before the first semantic measurement. The generator was
  revised after the first run (C2 cue wording) and again after the verifiers' review; both are tuning
  of the generator on development seeds, which the plan allows, and the C2/C3 separation is partly a
  product of that.
- Sentence templates are shared across worlds; names, numbers and codes are fresh. No arm is trained.
- Bit-equality of the dense results is claimed only for a fixed environment (see `environment` in
  `results.json`): the 0.55 cosine thresholds could move at the margin on another torch or hardware.

- Costs of the write-time work (concept extraction, clustering) are not charged to any arm in this model-free stage; wall-clock per retrieval is in `timing.json`.
- The audit of about 30 fetched associations for the false-association label has not been done; the rate above uses the generator's gold label only.
