# HUM-015 — Experience-related hippocampal sequences can recur during sleep on a compressed timescale

- Domain: `animal-memory`
- Claim type: `descriptive`
- Status: `challenged`
- Confidence: `low`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: rat CA1 pyramidal-cell recordings during wheel running and slow-wave sleep.
- Intervention or comparison: original parallel spike trains versus four surrogate families; pre-run and post-run sleep; short versus long sequence field states.
- Measured outcome: recurring multi-cell sequences, shared triplets, and associated theta/ripple power.
- Timescale: sequence termination below 50 ms versus above 100 ms; sleep before and after one run session.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Nádasdy et al. 1999 | Results, pp. 4–5, Figures 5–7 | recurring sequences exceeded reported surrogate nulls; significance depended on bin and shuffle design | multi-unit electrophysiology and Monte Carlo null models |
| same | Results, pp. 5–7, Figures 8–9 | two-rat pre/post evidence and categorical ripple association supported experience-related compressed replay | observational within-animal comparison |

## Contradictions, null results, and boundary conditions

At a 5-ms JPM bin, two rats had more triplets in shuffled trains, though not significantly. Only two rats supported the Sleep1–Run–Sleep2 comparison. The null distribution changes with the shuffle's preserved statistics.

## Alternative explanations

Population rate/synchrony changes, state-dependent excitability, imperfect null models, or common input could contribute without sequence-specific consolidation.

## Computational translation

- Abstract problem: perform bounded maintenance over more stored episodes.
- Candidate mechanism: compressed offline replay of selected evidence.
- Simpler baseline: no replay, uniform sampling, or ordinary indexing maintenance.
- Predicted benefit: better delayed retention/transfer per maintenance token.
- Predicted failure: event blending, error reinforcement, or no gain over retrieval-only storage.
- Rejection criterion: no matched-budget advantage or any material safety-guardrail failure.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: low because causal consolidation and an exact compression ratio were not established

