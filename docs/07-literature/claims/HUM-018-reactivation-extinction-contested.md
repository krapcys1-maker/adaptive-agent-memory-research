# HUM-018 — Retrieval-timed behavioral updating does not reliably rewrite human memory

- Domain: `human-memory`
- Claim type: `causal`
- Status: `contested`
- Confidence: `medium`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: conditioned fear/SCR and procedural/declarative sequence memory in humans.
- Intervention or comparison: reminder plus new learning/extinction versus no reminder or delayed update.
- Measured outcome: spontaneous recovery, reinstatement, sequence accuracy/speed, and declarative sequence similarity.
- Timescale: 24 hours to 10–14 months.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Schiller et al. 2010 | Experiments 1–2, Figures 1–3 | reported time- and cue-specific absence of fear recovery after reminder-plus-extinction | small behavioral experiments |
| Chalkia et al. 2020 | Results, Figures 2–3 | preregistered `n=124` replication found recovery and reinstatement in both groups with no group advantage | high-powered direct replication of primary comparison |
| Hardwicke et al. 2016 | Experiments 1–7, Figures 2–4, Table 1 | four direct and three conceptual sequence replications found no retrieval-contingent destructive update | repeated replication battery with open artifacts |

## Contradictions, null results, and boundary conditions

The original fear result and some conceptual replications remain positive, while direct fear and sequence replication results are negative. Memory type, intervention, prediction error, strength, age, timing, and response measure may be genuine moderators, but they can also become post-hoc explanations.

## Alternative explanations

Observed amnesia or reduced expression may reflect extinction, response competition, context-dependent access, retrieval-induced strengthening, selection rules, or ordinary interference rather than physical trace rewriting.

## Computational translation

- Abstract problem: incorporate corrections without corrupting history.
- Candidate mechanism: explicit revision transaction creating a versioned, context-scoped successor.
- Simpler baseline: overwrite in place or retain both records with retrieval routing.
- Predicted benefit: correct current action plus audit/rollback and reduced stale return.
- Predicted failure: old belief resurfaces, update overgeneralizes, or raw evidence is destroyed.
- Rejection criterion: versioning fails to reduce stale intrusions/false rewrites at acceptable cost.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: contested effect; medium confidence that unconditional retrieval-triggered rewriting is unsafe

