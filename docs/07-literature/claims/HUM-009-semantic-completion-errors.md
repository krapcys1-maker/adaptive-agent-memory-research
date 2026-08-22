# HUM-009 — Semantic completion can trade exact episodic detail for plausible recall

- Domain: `human-memory-model`
- Claim type: `descriptive`
- Status: `challenged`
- Confidence: `low`
- Last reviewed: `2026-08-22`

## Scope and operational definition

- Population/species/system: VQ-VAE/PixelCNN computational model on MNIST-like images and synthetic contexts.
- Intervention or comparison: incomplete traces with strong, weak, or no semantic completion.
- Measured outcome: classification/capacity, noise robustness, and correct versus context-congruent wrong recall.
- Timescale: encode then reconstruct; no long sequential history.

## Supporting evidence

| Source ID and version | Exact section/page/figure/table/code locator | Result and uncertainty | Evidence type |
| --- | --- | --- | --- |
| Fayyaz et al., arXiv:2111.13537v1 | Figures 3–4 pp. 6–7 | semantic completion improves classification at fixed attention; up to about 2x additional efficiency | computational model |
| same | Figures 8–9 pp. 9–10; conclusion pp. 11–12 | incomplete traces tend toward plausible congruent but episode-incorrect contexts; authors note tuned attention and limited explanatory power | computational model fit |

## Contradictions, null results, and boundary conditions

Simple images are not language histories. The final journal version was not audited. The model does not implement hippocampal storage or sequential episodes, and classifier scores do not measure factual support.

## Alternative explanations

Category priors, tuning freedom, or classifier bias may produce the apparent efficiency and human-like error ratio.

## Computational translation

- Abstract problem: use a learned prior to fill missing memory details.
- Candidate mechanism: provenance-labeled semantic hypothesis used only after evidence retrieval.
- Simpler baseline: extractive summary or raw evidence.
- Predicted benefit: fewer tokens for common patterns.
- Predicted failure: confident plausible fabrication on rare or changed facts.
- Rejection criterion: unsupported-detail guardrail fails or efficiency vanishes at matched supported-answer accuracy.

## Independent review

- Reviewer/model/human: pending
- Context separated from extractor: `no`
- Source locator verified: `yes`
- Architecture preference hidden: `no`
- Confidence change and reason: not applicable; first extraction only
