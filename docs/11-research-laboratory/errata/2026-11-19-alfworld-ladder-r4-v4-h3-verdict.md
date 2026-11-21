# Erratum: verdict of hypothesis H3 in ALFWORLD-LADDER-R4-V4

Added 2026-11-19. Package: `data/lab/autolab-alfworld-ladder-r4-v4/` (published bytes unchanged; they are pinned by
`PUBLISHED_FILES.json` and recomputed by `scripts/verify_autolab_packages.py`).

## What the package says

The findings table lists H3 (`finding:e7402eac3345ea88`) as **supported**, with state `practical`
(retrieved_task − placebo +0.240, 95% interval [+0.177, +0.303], SESOI 0.12).

## What it should say

H3 pre-registered `expected_state: positive_below_SESOI`: a positive effect whose interval lies between 0 and the SESOI.
Its own falsification text says it is refuted by a `practical` state (lower bound ≥ SESOI), which "speaks for H1".
The measured lower bound +0.177 is above the SESOI 0.12, so **H3 is refuted**. H1 (expected `practical`) stays supported
and H2 (expected `equivalent`) stays refuted.

## Why it happened

The laboratory's verdict rule (`program._s_conclude`) read only the predicted direction (`predicted: positive`), not the
pre-registered `expected_state`. A positive or practical state therefore "supported" every hypothesis that predicted a gain,
including one that predicted the gain would be small. The package verifier already flagged it as a warning
("verdict supported with state practical, hypothesis expected_state positive_below_SESOI").

## What changed

From 2026-11-19 the laboratory judges a hypothesis with `expected_state` against that state (`program.hypothesis_verdict`)
and records the rule it used in the finding (`verdict_rule`). A hypothesis whose `expected_state` contradicts its predicted
direction is rejected before the test. `scripts/verify_autolab_packages.py` recomputes verdicts with the new rule for findings
that carry `verdict_rule` and with the old rule for older packages, where it keeps the warning.

## What does not change

The measurement, the numbers, the code audit verdict (valid) and the direction status of V4 (`measurement_problem`: content
and format/process effects are not separated) are unchanged. The erratum affects one hypothesis label, not the result.
V3 and V5B have no hypothesis with an `expected_state` that disagrees with its verdict.
