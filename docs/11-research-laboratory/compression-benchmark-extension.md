# Compression benchmark extension v0

Status: preregistration-draft; no test results observed

## Purpose

Test four claims suggested by the first compression reading batch without changing the frozen `pmlab-v0` development baseline.

## Shared controls

- Append-only canonical histories with event IDs, valid time, transaction time, and provenance.
- Frozen development/test split by complete history and entity.
- Identical active-context token/character budget, reader prompt, model, temperature, hardware, and cache condition.
- Retrieval-only and end-to-end reader results reported separately.
- All maintenance calls, tokens, latency, disk bytes, and failures counted.
- Results shown by task family and consequence weight; no single aggregate may hide critical misses.

## Experiment C1 — repeated compaction curve

Apply 0, 1, 2, 5, 10, and 20 maintenance cycles before the same held-out questions.

Backends:

- lossless archive + lexical/FTS retrieval;
- lossless archive + hybrid retrieval when unlocked;
- rolling summary overwrite;
- versioned summary plus raw archive fallback;
- oracle evidence selection.

Primary: critical-evidence recall at matched active-context budget. Secondary: supported answer accuracy, stale intrusion, unsupported detail, provenance completeness, p95 latency, total model calls, and disk growth.

Success for reversibility: the archive-backed curve loses no more than 2 percentage points from cycle 1 to 20 and exceeds rolling overwrite by at least 10 points on critical-evidence recall with a bootstrap 95% interval excluding zero. These are initial engineering thresholds, not universal scientific constants.

## Experiment C2 — model change, rare exception, and noise

Histories contain three separately labeled anomaly types:

1. a genuine latent rule change;
2. a stable rare exception needed only after delay;
3. a random or poisoned outlier that should not alter the model.

Compare recency, uniform reservoir, raw surprise, Bayesian/model-change proxy, delayed-utility labels, and a gated combination. Measure later structure recovery, exception recall, false promotion of noise, poisoning success, storage, and calls.

Success for adaptive retention: improve macro structure/exception recovery by at least 8 points over recency without increasing false noise promotion by more than 3 points. Reject raw surprise as a standalone policy if it retains poison/noise disproportionately.

## Experiment C3 — plausible semantic completion

Create answer pairs where a common/semantically congruent value conflicts with the actual episode. Compare raw evidence, summary, and generative semantic completion with and without provenance verification.

Primary: unsupported-plausible-detail rate. Secondary: answerability per retrieved token, exact episode fidelity, calibration/abstention, and source citation correctness.

Success for a semantic layer: at least 15% evidence-token reduction at matched supported-answer accuracy, with unsupported-plausible-detail rate no worse than the raw-retrieval baseline plus 1 point. Otherwise it remains a search aid, not an answer source.

## Experiment C4 — consequence-weighted allocation and emotion metadata

Use a factorial synthetic design rather than inferring emotion from prose:

- valence: negative, neutral, positive;
- arousal/intensity: low, high;
- consequence weight: 1, 3, 10;
- surprise: expected, unexpected;
- factual reliability: corroborated, single-source, contradicted;
- future query probability: low, high.

Compare uniform allocation, consequence-only, surprise-only, emotion-only, and factor-separated policies. Never use the emotional label as evidence truth.

Primary: consequence-weighted answer loss. Guardrails: unweighted critical recall, contradiction detection, calibration, demographic/topic bias, and adversarial emotional-language promotion.

Success: a factor-separated policy improves weighted loss over uniform allocation and all single-signal policies on held-out combinations, while no protected guardrail worsens beyond a preregistered 2-point non-inferiority margin. Failure means emotion metadata is not admitted to automatic allocation.

## Analysis and stopping

- Freeze seeds, examples, thresholds, and code commit before test execution.
- Report paired bootstrap intervals and per-history differences; choose another test only if its assumptions are documented.
- A statistically positive result is insufficient if cost or a safety guardrail fails.
- One successful task family permits replication, not architecture promotion. Promotion requires a second corpus family and a different reader/provider family where feasible.
