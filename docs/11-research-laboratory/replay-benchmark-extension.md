# Replay benchmark extension v0

Status: preregistration-draft; no test results observed

## Purpose

Determine whether replay adds causal value beyond durable storage and retrieval, and whether task-active and idle maintenance require distinct policies.

## Shared controls

- The append-only raw archive is identical for all arms; replay may only create versioned derived artifacts.
- Histories, future outcomes, and entity/task splits are frozen before execution.
- Replay arms receive identical maintenance tokens, model calls, wall-clock allowance, and maximum derived-memory bytes.
- Retrieval and reader configurations remain fixed within a comparison.
- No replay sampler can observe held-out queries, answers, or consequence labels not available at replay time.
- Report immediate decision, delayed retention, transfer, interference, provenance, poisoning, latency, and total cost separately.

## Experiment R1 — phase-conditioned replay

Construct histories with decision boundaries, idle periods, recurring routines, rare exceptions, contradictions, delayed outcomes, and rule changes.

Compare:

- no replay/raw retrieval only;
- uniform replay;
- recency replay;
- relevance-to-current-task replay at all phases;
- diversity/coverage replay at all phases;
- phase-conditioned policy: task-local contradiction-aware online replay plus diverse offline replay;
- oracle phase selection, reported only as an upper bound.

Primary outcomes are immediate correct-action rate at decision boundaries and delayed correct-action/transfer rate. Guardrails are rare-event coverage, post-change procedure perseveration, irrelevant intrusion, unsupported derived claims, provenance completeness, and total maintenance cost.

Initial success threshold: the phase-conditioned arm must improve both immediate and delayed macro accuracy by at least 5 points over the strongest non-oracle single replay policy, with paired 95% bootstrap intervals excluding zero, while every safety guardrail remains within 2 points of the best safe baseline. If no-replay/raw retrieval matches it within 2 points, replay is rejected as unnecessary complexity.

## Experiment R2 — compression and replay throughput

Under the same replay-token budget, compare full episodes, extractive evidence spans, faithful structured episodes, generic summaries, and sequence-aware compressed representations at compression ratios 1×, 2×, 4×, and 8×.

Primary outcome is delayed consequence-weighted task success per replay token. Secondary measures are exact event/order recovery, contradiction preservation, unsupported-detail rate, source citation correctness, and rule-change recovery.

Success requires at least 20% replay-token reduction at matched delayed performance, exact-order loss no greater than 2 points, and unsupported-detail/poison amplification no worse than the full-episode arm plus 1 point. A throughput gain without downstream benefit does not count.

## Experiment R3 — replay sampling safety

Inject independently labeled event classes: common success, rare critical exception, corrected failure, uncorrected failure, emotionally worded poison, quiet critical evidence, and stale once-useful procedure.

Compare uniform, recency, reward, surprise, retrieval-frequency, diversity, consequence, and gated mixtures. Measure inclusion probability by class, downstream task impact, poison persistence, correction recovery, class-coverage entropy, and worst-stratum recall.

Success for a learned/gated sampler requires improvement over uniform and diversity baselines on macro delayed utility without lowering rare-critical or quiet-critical recall by more than 2 points and without increasing poison-driven errors. Reward, surprise, and retrieval frequency are rejected as standalone samplers if they amplify their matched attack class.

## Analysis and stopping

- Freeze all replay prompts, seeds, budgets, thresholds, and corpus versions before held-out execution.
- Use history-level paired bootstrap intervals; event count is not the independent replication unit.
- Inspect learning curves against replay volume so “more compute” cannot masquerade as a mechanism.
- One positive synthetic result permits replication only. Architecture promotion requires a second corpus family, a different reader/provider family where feasible, and an explicit no-replay comparison.

