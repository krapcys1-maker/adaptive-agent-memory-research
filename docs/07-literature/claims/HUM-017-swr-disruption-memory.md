# HUM-017 — Disrupting ripple-associated hippocampal activity can impair specific spatial-memory performance

- Domain: `animal-memory`
- Claim type: `causal`
- Status: `challenged`
- Confidence: `medium`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: small samples of male rats in two spatial-navigation paradigms.
- Intervention or comparison: online ripple-triggered hippocampal-afferent stimulation during post-training rest or awake task pauses, with within-animal/no/delayed stimulation controls.
- Measured outcome: multi-day navigation learning, outbound alternation, inbound return, place-field stability, and post-experience reactivation.
- Timescale: hundreds of milliseconds of neural suppression; one-hour rest or awake pauses over 8–10 training days.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Ego-Stengel and Wilson 2010 | Results, Figures 1–4 | ripple-triggered post-training disruption slowed one maze's learning while measured sleep architecture remained similar | within-animal causal perturbation, five analyzed rats |
| Jadhav et al. 2012 | main text, Figures 1–4 | awake SWR disruption selectively impaired outbound but not inbound W-track performance versus delayed/no-stimulation controls | between-group causal perturbation, 6/4/4 rats |

## Contradictions, null results, and boundary conditions

The rest-disruption deficit was moderate and disappeared with additional training. Awake disruption spared inbound performance, place-field stability, and later rest reactivation. Neither study selectively perturbed decoded replay content.

## Alternative explanations

Ripple-associated population activity may support retrieval, planning, coordination, excitability control, or downstream communication without replayed sequence content being the causal variable. Electrical stimulation may have broader effects than the measured local/sleep controls capture.

## Computational translation

- Abstract problem: use limited maintenance compute to connect recent/remote evidence to future decisions.
- Candidate mechanism: content-targeted online/offline replay.
- Simpler baseline: ordinary retrieval, no maintenance, or matched random/sham maintenance.
- Predicted benefit: selective gain on history-dependent immediate and delayed tasks.
- Predicted failure: extra compute rather than content explains gains, or simple retrieval matches replay.
- Rejection criterion: no content-specific advantage under equal compute across two task families.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: medium for ripple-associated processing; low for replay content as the causal mechanism

