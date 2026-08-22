# HUM-014 — A time-bounded novelty signal can promote weak memory persistence

- Domain: `animal-memory`
- Claim type: `causal`
- Status: `challenged`
- Confidence: `medium`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: adult male Lister Hooded rats in an event-arena spatial task and parallel hippocampal slices.
- Intervention or comparison: weak/strong encoding, novel-box exploration before/after encoding, D1/D5 blockade, protein-synthesis blockade.
- Measured outcome: correct digging at 30 minutes/24 hours and LTP at 10 hours.
- Timescale: novelty one hour before or 30 minutes after encoding; immediate versus six-hour delayed blockade.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Wang et al. 2010 | Conditions 3–5, Figures 3–4, pp. 3–5 | novelty rescued weak 24-hour memory; rescue blocked by D1/D5 antagonist or immediate but not six-hour-delayed anisomycin | within-animal pharmacological experiment |
| same | Condition 6, Figure 5, p. 5 | 14/16 individual animals followed good-poor-rescued V pattern | within-subject summary |

## Contradictions, null results, and boundary conditions

Unrelated novelty did not make weak memory persistent without the correct timing/receptor/protein-synthesis conditions. STC is one interpretation and the authors discuss novelty-dopamine alternatives.

## Alternative explanations

Novelty may alter arousal, exploration, dopamine, attention, or state globally rather than provide a synapse-specific resource-capture mechanism.

## Computational translation

- Abstract problem: decide later which recent events merit durable derived state.
- Candidate mechanism: append-only event plus expiring eligibility tag and verified promotion signal.
- Simpler baseline: immediate write or fixed delayed batch.
- Predicted benefit: less premature consolidation while preserving outcome-linked episodes.
- Predicted failure: delayed signals promote unrelated events or miss urgent writes.
- Rejection criterion: no benefit over immediate append plus retrieval, or higher noise/poison promotion.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: first extraction only
