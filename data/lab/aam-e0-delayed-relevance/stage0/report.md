# AAM-E0 Stage 0 report: construct checks on the development seeds

Status: exploratory, tier E, synthetic worlds written by an agent, no spend, no model, no network. Development seeds [0, 1, 2, 3, 4]. Generator `goalshift-v0.2`. Embedder: `minilm`. Wall-clock is in `timing.json`, not here.

A passed gate says the generator behaves as designed. It says nothing about real agents or about arm D. A failed gate is a finding about the world, reported as such.

## Verdict

**Stage 0 PASSED.**

| gate | result | measured |
|---|---|---|
| headroom (strict gold): best of Del/Sum/Sum-raw in C3 at C=250, R=10% in [0.2, 0.8] | PASS | Sum-raw = 0.250 (Del 0.150, Sum 0.000, Sum-raw 0.250); by event id the best is Sum = 0.250 |
| overlap C1: mean in [0.30, 0.50], each in [0.20, 0.60] | PASS | mean 0.380, min 0.312, max 0.400 |
| overlap C2 and C3: zero (cue and goal vs target, stemmed content words, the arms' own token space) | PASS | max cue overlap 0.000, max goal overlap 0.000 |
| semantic: C1 and C2 cue-target cosine exceeds the archive baseline by >= 0.15; C3 by <= 0.10; C2 - C3 >= 0.10 (embedder: minilm) | PASS | gaps C1 0.366, C2 0.178, C3 0.045 |
| decoys: every probe has >= 2 decoys, all dated before its cue | PASS | min decoys per probe 3 |
| structure and leakage: determinism, cue file identical without history, 150 events of 12-35 words each with a code, 4/4/4 probes, target day 2-9, gap >= 14, no id or gold code in the cue | PASS | 0 problems |
| write-time importance is uninformative: target rank share in [0.30, 0.70] in every cell (0 = top, 0.5 = chance) | PASS | C1 0.552, C2 0.625, C3 0.403 |
| oracle retrieval path: O and Oc reach the gold >= 0.95 of the time when they stored it (C=250, R=10% and 25%), and O >= 0.95 unconditionally at R=25% | PASS | O R=10%: 1.000 given stored (gold stored 0.533, unconditional 0.533); O R=25%: 1.000 given stored (gold stored 1.000, unconditional 1.000); Oc R=10%: 1.000 given stored (gold stored 0.167, unconditional 0.167); Oc R=25%: 1.000 given stored (gold stored 0.517, unconditional 0.517) |
| shuffled S near chance at C=250 (S <= P(gold has a trace) x fetched/traces + 0.10) | PASS | R=10%: S 0.072 (mean of 20 shuffles) vs chance 0.069; D 0.083; R=25%: S 0.090 (mean of 20 shuffles) vs chance 0.126; D 0.250 |

Best comparator on the primary cell (C3, C=250, R=10%): **Sum-raw** by strict gold ({'Del': 0.15, 'Sum': 0.0, 'Sum-raw': 0.25}); **Sum** by event id ({'Del': 0.15, 'Sum': 0.25, 'Sum-raw': 0.25}). The decision rules use the strict measure. They differ because a lead-truncated 8-word summary is credited by id for an event whose reference code it does not contain.

## Old generator against new, side by side

| arm (C3, C=250, R=10%) | v0.1 by id | v0.1 strict | v0.2 by id | v0.2 strict (primary) |
|---|---|---|---|---|
| Del | 0.20 | 0.20 | 0.15 | 0.15 |
| Sum | 0.35 | 0.00 | 0.25 | 0.00 |
| Sum-raw | 0.05 | 0.05 | 0.25 | 0.25 |
| F2 | 0.25 | 0.25 | 0.15 | 0.15 |
| D | 0.10 | 0.10 | 0.20 | 0.20 |
| O | 0.95 | 0.95 | 0.70 | 0.70 |
| S | 0.15 | 0.15 | 0.14 | 0.14 |

v0.1 drew the authored consequence by event kind (targets about twice as consequential as filler) and computed novelty against earlier events only, which fell with time and favoured the day 2-9 targets. Its importance ranking therefore told every forgetting arm which events were targets (gold's mean rank share among dormant events 0.13-0.22 against 0.5 for an uninformative score). In v0.2 both write-time fields are drawn by position only. The v0.1 column is from the committed v0.1 Stage 0 (seeds 0-4, MiniLM); n is 20 probes per cell, so one probe is 0.05.

## Measured overlap (cue content words also in the target, stemmed, in the arms' own token space)

| cell | n | mean | min | max |
|---|---|---|---|---|
| C1 | 20 | 0.3795 | 0.3125 | 0.4 |
| C2 | 20 | 0.0 | 0.0 | 0.0 |
| C3 | 20 | 0.0 | 0.0 | 0.0 |

## Semantic similarity (cosine, cue vs target; baseline = cue vs every other visible event)

| cell | target | baseline | gap | decoys | target rank 1 | in top 11 | mean rank |
|---|---|---|---|---|---|---|---|
| C1 | 0.5134 | 0.1469 | 0.3665 | 0.2333 | 1.0 | 1.0 | 1.0 |
| C2 | 0.2739 | 0.0959 | 0.178 | 0.1826 | 0.2 | 0.85 | 6.0 |
| C3 | 0.1549 | 0.11 | 0.045 | 0.177 | 0.0 | 0.15 | 46.75 |

## Gold-in-context, strict (reference code present in the delivered text), C x R

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 1.000 | 1.000 | 1.000 |
| F1 | C2 | 0.000 | 0.100 | 0.150 |
| F1 | C3 | 0.050 | 0.050 | 0.050 |
| F1 | ALL | 0.350 | 0.383 | 0.400 |
| F2 | C1 | 1.000 | 1.000 | 1.000 |
| F2 | C2 | 0.400 | 0.700 | 1.000 |
| F2 | C3 | 0.100 | 0.150 | 0.300 |
| F2 | ALL | 0.500 | 0.617 | 0.767 |
| B3 | C1 | 0.000 | 0.000 | 0.000 |
| B3 | C2 | 0.000 | 0.000 | 0.000 |
| B3 | C3 | 0.000 | 0.000 | 0.000 |
| B3 | ALL | 0.000 | 0.000 | 0.000 |
| Del | C1 | 0.000 / 0.050 | 0.000 / 0.050 | 0.000 / 0.050 |
| Del | C2 | 0.000 / 0.000 | 0.050 / 0.050 | 0.050 / 0.050 |
| Del | C3 | 0.050 / 0.050 | 0.150 / 0.200 | 0.150 / 0.350 |
| Del | ALL | 0.017 / 0.033 | 0.067 / 0.100 | 0.067 / 0.150 |
| Sum | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Sum-raw | C1 | 0.050 / 0.300 | 0.050 / 0.300 | 0.050 / 0.300 |
| Sum-raw | C2 | 0.050 / 0.050 | 0.050 / 0.050 | 0.050 / 0.100 |
| Sum-raw | C3 | 0.150 / 0.050 | 0.250 / 0.250 | 0.250 / 0.450 |
| Sum-raw | ALL | 0.083 / 0.133 | 0.117 / 0.200 | 0.117 / 0.283 |
| D | C1 | 0.050 / 0.450 | 0.050 / 0.450 | 0.050 / 0.500 |
| D | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.100 |
| D | C3 | 0.100 / 0.050 | 0.200 / 0.300 | 0.200 / 0.350 |
| D | ALL | 0.050 / 0.167 | 0.083 / 0.250 | 0.083 / 0.317 |
| O | C1 | 0.500 / 1.000 | 0.500 / 1.000 | 0.500 / 1.000 |
| O | C2 | 0.400 / 1.000 | 0.400 / 1.000 | 0.400 / 1.000 |
| O | C3 | 0.700 / 1.000 | 0.700 / 1.000 | 0.700 / 1.000 |
| O | ALL | 0.533 / 1.000 | 0.533 / 1.000 | 0.533 / 1.000 |
| Oc | C1 | 0.050 / 0.500 | 0.050 / 0.500 | 0.050 / 0.500 |
| Oc | C2 | 0.100 / 0.400 | 0.100 / 0.400 | 0.100 / 0.400 |
| Oc | C3 | 0.350 / 0.650 | 0.350 / 0.650 | 0.350 / 0.650 |
| Oc | ALL | 0.167 / 0.517 | 0.167 / 0.517 | 0.167 / 0.517 |
| S | C1 | 0.015 / 0.028 | 0.025 / 0.092 | 0.043 / 0.195 |
| S | C2 | 0.018 / 0.035 | 0.050 / 0.070 | 0.050 / 0.138 |
| S | C3 | 0.075 / 0.022 | 0.140 / 0.107 | 0.147 / 0.205 |
| S | ALL | 0.036 / 0.028 | 0.072 / 0.090 | 0.080 / 0.179 |

## Gold stored (the arm kept something of the gold event: raw, summary or trace)

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| Del | C1 | 0.000 / 0.050 | 0.000 / 0.050 | 0.000 / 0.050 |
| Del | C2 | 0.050 / 0.050 | 0.050 / 0.050 | 0.050 / 0.050 |
| Del | C3 | 0.150 / 0.350 | 0.150 / 0.350 | 0.150 / 0.350 |
| Del | ALL | 0.067 / 0.150 | 0.067 / 0.150 | 0.067 / 0.150 |
| Sum | C1 | 0.050 / 0.300 | 0.050 / 0.300 | 0.050 / 0.300 |
| Sum | C2 | 0.050 / 0.100 | 0.050 / 0.100 | 0.050 / 0.100 |
| Sum | C3 | 0.250 / 0.450 | 0.250 / 0.450 | 0.250 / 0.450 |
| Sum | ALL | 0.117 / 0.283 | 0.117 / 0.283 | 0.117 / 0.283 |
| Sum-raw | C1 | 0.050 / 0.300 | 0.050 / 0.300 | 0.050 / 0.300 |
| Sum-raw | C2 | 0.050 / 0.100 | 0.050 / 0.100 | 0.050 / 0.100 |
| Sum-raw | C3 | 0.250 / 0.450 | 0.250 / 0.450 | 0.250 / 0.450 |
| Sum-raw | ALL | 0.117 / 0.283 | 0.117 / 0.283 | 0.117 / 0.283 |
| D | C1 | 0.050 / 0.500 | 0.050 / 0.500 | 0.050 / 0.500 |
| D | C2 | 0.100 / 0.400 | 0.100 / 0.400 | 0.100 / 0.400 |
| D | C3 | 0.350 / 0.650 | 0.350 / 0.650 | 0.350 / 0.650 |
| D | ALL | 0.167 / 0.517 | 0.167 / 0.517 | 0.167 / 0.517 |
| O | C1 | 0.500 / 1.000 | 0.500 / 1.000 | 0.500 / 1.000 |
| O | C2 | 0.400 / 1.000 | 0.400 / 1.000 | 0.400 / 1.000 |
| O | C3 | 0.700 / 1.000 | 0.700 / 1.000 | 0.700 / 1.000 |
| O | ALL | 0.533 / 1.000 | 0.533 / 1.000 | 0.533 / 1.000 |
| Oc | C1 | 0.050 / 0.500 | 0.050 / 0.500 | 0.050 / 0.500 |
| Oc | C2 | 0.100 / 0.400 | 0.100 / 0.400 | 0.100 / 0.400 |
| Oc | C3 | 0.350 / 0.650 | 0.350 / 0.650 | 0.350 / 0.650 |
| Oc | ALL | 0.167 / 0.517 | 0.167 / 0.517 | 0.167 / 0.517 |
| S | C1 | 0.050 / 0.500 | 0.050 / 0.500 | 0.050 / 0.500 |
| S | C2 | 0.100 / 0.400 | 0.100 / 0.400 | 0.100 / 0.400 |
| S | C3 | 0.350 / 0.650 | 0.350 / 0.650 | 0.350 / 0.650 |
| S | ALL | 0.167 / 0.517 | 0.167 / 0.517 | 0.167 / 0.517 |

Gold-in-context cannot exceed gold stored. The gap between the two is the loss 'stored but not retrieved'; the shortfall of gold stored below 1 is the loss 'not stored' (a budget effect, not a retrieval effect). O keeps cheaper traces than D (about 2 words each against up to 6), so at the same R it stores far more; Oc has D's stored set and D's costs and is the like-for-like oracle.

## By event id (a summary of the gold event counts even without the code)

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 1.000 | 1.000 | 1.000 |
| F1 | C2 | 0.000 | 0.100 | 0.150 |
| F1 | C3 | 0.050 | 0.050 | 0.050 |
| F1 | ALL | 0.350 | 0.383 | 0.400 |
| F2 | C1 | 1.000 | 1.000 | 1.000 |
| F2 | C2 | 0.400 | 0.700 | 1.000 |
| F2 | C3 | 0.100 | 0.150 | 0.300 |
| F2 | ALL | 0.500 | 0.617 | 0.767 |
| B3 | C1 | 0.000 | 0.000 | 0.000 |
| B3 | C2 | 0.000 | 0.000 | 0.000 |
| B3 | C3 | 0.000 | 0.000 | 0.000 |
| B3 | ALL | 0.000 | 0.000 | 0.000 |
| Del | C1 | 0.000 / 0.050 | 0.000 / 0.050 | 0.000 / 0.050 |
| Del | C2 | 0.000 / 0.000 | 0.050 / 0.050 | 0.050 / 0.050 |
| Del | C3 | 0.050 / 0.050 | 0.150 / 0.200 | 0.150 / 0.350 |
| Del | ALL | 0.017 / 0.033 | 0.067 / 0.100 | 0.067 / 0.150 |
| Sum | C1 | 0.050 / 0.300 | 0.050 / 0.300 | 0.050 / 0.300 |
| Sum | C2 | 0.050 / 0.050 | 0.050 / 0.100 | 0.050 / 0.100 |
| Sum | C3 | 0.250 / 0.050 | 0.250 / 0.400 | 0.250 / 0.450 |
| Sum | ALL | 0.117 / 0.133 | 0.117 / 0.267 | 0.117 / 0.283 |
| Sum-raw | C1 | 0.050 / 0.300 | 0.050 / 0.300 | 0.050 / 0.300 |
| Sum-raw | C2 | 0.050 / 0.050 | 0.050 / 0.050 | 0.050 / 0.100 |
| Sum-raw | C3 | 0.150 / 0.050 | 0.250 / 0.250 | 0.250 / 0.450 |
| Sum-raw | ALL | 0.083 / 0.133 | 0.117 / 0.200 | 0.117 / 0.283 |
| D | C1 | 0.050 / 0.450 | 0.050 / 0.450 | 0.050 / 0.500 |
| D | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.100 |
| D | C3 | 0.100 / 0.050 | 0.200 / 0.300 | 0.200 / 0.350 |
| D | ALL | 0.050 / 0.167 | 0.083 / 0.250 | 0.083 / 0.317 |
| O | C1 | 0.500 / 1.000 | 0.500 / 1.000 | 0.500 / 1.000 |
| O | C2 | 0.400 / 1.000 | 0.400 / 1.000 | 0.400 / 1.000 |
| O | C3 | 0.700 / 1.000 | 0.700 / 1.000 | 0.700 / 1.000 |
| O | ALL | 0.533 / 1.000 | 0.533 / 1.000 | 0.533 / 1.000 |
| Oc | C1 | 0.050 / 0.500 | 0.050 / 0.500 | 0.050 / 0.500 |
| Oc | C2 | 0.100 / 0.400 | 0.100 / 0.400 | 0.100 / 0.400 |
| Oc | C3 | 0.350 / 0.650 | 0.350 / 0.650 | 0.350 / 0.650 |
| Oc | ALL | 0.167 / 0.517 | 0.167 / 0.517 | 0.167 / 0.517 |
| S | C1 | 0.015 / 0.028 | 0.025 / 0.092 | 0.043 / 0.195 |
| S | C2 | 0.018 / 0.035 | 0.050 / 0.070 | 0.050 / 0.138 |
| S | C3 | 0.075 / 0.022 | 0.140 / 0.107 | 0.147 / 0.205 |
| S | ALL | 0.036 / 0.028 | 0.072 / 0.090 | 0.080 / 0.179 |

## Decoy intrusion (mean decoys in context)

| arm | cell | C=100 (R=10% / 25%) | C=250 (R=10% / 25%) | C=500 (R=10% / 25%) |
|---|---|---|---|---|
| A | C1 | 0.000 | 0.000 | 0.000 |
| A | C2 | 0.000 | 0.000 | 0.000 |
| A | C3 | 0.000 | 0.000 | 0.000 |
| A | ALL | 0.000 | 0.000 | 0.000 |
| F1 | C1 | 2.050 | 2.050 | 2.100 |
| F1 | C2 | 2.050 | 2.100 | 2.100 |
| F1 | C3 | 1.050 | 1.250 | 1.250 |
| F1 | ALL | 1.717 | 1.800 | 1.817 |
| F2 | C1 | 0.750 | 1.200 | 1.650 |
| F2 | C2 | 0.700 | 1.050 | 1.750 |
| F2 | C3 | 0.600 | 0.850 | 1.400 |
| F2 | ALL | 0.683 | 1.033 | 1.600 |
| B3 | C1 | 0.200 | 0.500 | 1.050 |
| B3 | C2 | 0.100 | 0.350 | 1.000 |
| B3 | C3 | 0.000 | 0.200 | 0.600 |
| B3 | ALL | 0.100 | 0.350 | 0.883 |
| Del | C1 | 0.200 / 0.500 | 0.450 / 0.650 | 0.450 / 0.750 |
| Del | C2 | 0.050 / 0.450 | 0.100 / 0.550 | 0.100 / 0.600 |
| Del | C3 | 0.050 / 0.150 | 0.050 / 0.200 | 0.050 / 0.350 |
| Del | ALL | 0.100 / 0.367 | 0.200 / 0.467 | 0.200 / 0.567 |
| Sum | C1 | 0.400 / 0.650 | 0.600 / 1.000 | 0.600 / 1.300 |
| Sum | C2 | 0.350 / 0.550 | 0.450 / 0.750 | 0.450 / 1.100 |
| Sum | C3 | 0.200 / 0.450 | 0.200 / 0.750 | 0.200 / 0.900 |
| Sum | ALL | 0.317 / 0.550 | 0.417 / 0.833 | 0.417 / 1.100 |
| Sum-raw | C1 | 0.400 / 0.600 | 0.500 / 0.950 | 0.600 / 1.150 |
| Sum-raw | C2 | 0.250 / 0.350 | 0.450 / 0.700 | 0.450 / 0.900 |
| Sum-raw | C3 | 0.100 / 0.400 | 0.200 / 0.550 | 0.200 / 0.800 |
| Sum-raw | ALL | 0.250 / 0.450 | 0.383 / 0.733 | 0.417 / 0.950 |
| D | C1 | 0.150 / 0.350 | 0.450 / 0.850 | 0.550 / 1.200 |
| D | C2 | 0.350 / 0.500 | 0.450 / 0.750 | 0.450 / 1.100 |
| D | C3 | 0.100 / 0.200 | 0.150 / 0.350 | 0.150 / 0.550 |
| D | ALL | 0.200 / 0.350 | 0.350 / 0.650 | 0.383 / 0.950 |
| O | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| O | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C1 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C2 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | C3 | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| Oc | ALL | 0.000 / 0.000 | 0.000 / 0.000 | 0.000 / 0.000 |
| S | C1 | 0.133 / 0.250 | 0.325 / 0.495 | 0.420 / 0.848 |
| S | C2 | 0.120 / 0.190 | 0.240 / 0.448 | 0.245 / 0.725 |
| S | C3 | 0.070 / 0.107 | 0.100 / 0.370 | 0.125 / 0.492 |
| S | ALL | 0.107 / 0.182 | 0.222 / 0.438 | 0.263 / 0.688 |

## D under other concept rules and thresholds (secondary; C=250)

| variant | C1 R=10% | C2 R=10% | C3 R=10% | C1 R=25% | C2 R=25% | C3 R=25% |
|---|---|---|---|---|---|---|
| primary: concept df>=2, stem>=4 letters, cluster/query threshold 0.55 | 0.05 | 0.0 | 0.2 | 0.45 | 0.0 | 0.3 |
| v0.1 concept rule: any df, stem>=3 letters | 0.05 | 0.0 | 0.0 | 0.35 | 0.1 | 0.15 |
| cluster/query threshold 0.45 | 0.05 | 0.0 | 0.2 | 0.4 | 0.05 | 0.1 |
| cluster/query threshold 0.65 | 0.05 | 0.0 | 0.05 | 0.45 | 0.05 | 0.15 |

## Write-time importance

| measure | value |
|---|---|
| target importance rank share, C1 | 0.5516 |
| target importance rank share, C2 | 0.6247 |
| target importance rank share, C3 | 0.4029 |
| mean novelty target / decoy / filler | 0.5074 / 0.4934 / 0.4941 |
| mean consequence target / decoy / filler | 0.5 / 0.5611 / 0.6667 |

Rank share is the target's position in the importance ordering of the archive visible at the cue (0 = most important, 0.5 = no information). Because importance is uninformative by construction, an arm that forgets by importance keeps a random subset of the older events, and its chance of holding the target is about its coverage.

## Notes and honest limits

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
