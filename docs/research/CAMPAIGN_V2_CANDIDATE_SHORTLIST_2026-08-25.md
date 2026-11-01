# Campaign V2 Candidate Shortlist — post-Mechanism-J (2026-08-25)

Per the standing autonomous contract's Phase A-D: after Mechanism J's replication failure (Entry P), read the ResearchOS bridge, identify max 3 actionable candidates, $0 archaeology on all 3, rank by expected-information-gain/cost, select max 1.

## Phase A — bridge state at time of selection

- `Dokumenty z Resherchera/` (ResearchOS → AAMR): 1 pending candidate, `rmc-2026-08-24-001` (semantic-entropy-escalation-gate), `status: PENDING_AAMR_REVIEW`. No new handoffs since the last check.
- `Dokumenty dla Resherchera/`: GAP-001 (Mechanism J replication) closed negatively; GAP-002, GAP-003, GAP-005 remain `OPEN`; `arr-2026-08-24-001` (compact-vs-raw sufficiency gate) remains the one open research request.

## Phase B — shortlist (max 3)

| # | Candidate | Source | Target | Testability |
|---|---|---|---|---|
| 1 | `SEMANTIC_ENTROPY_SUFFICIENCY_GATE` | ResearchOS `rmc-2026-08-24-001` / GAP-005 | compact-vs-raw cost-efficiency gate | `CAN_TEST_NOW` |
| 2 | `MULTI_QUERY_FUSION_RETRIEVAL` | AAMR discovery-v3 pool / GAP-002 | retrieval-ranking-miss (subtype 2) | `CAN_TEST_NOW` |
| 3 | `DETERMINISTIC_TEMPORAL_RESOLVER_POSTPROCESS` | AAMR discovery-v3 pool / GAP-003 | temporal-representation-loss (subtype 3) | `CAN_TEST_WITH_PRECONDITION` |

## Phase C — $0 archaeology

**#1 (semantic entropy gate):** full 8-step check already run (see `PM-20260825-41d5d71e`) — not a duplicate of Entry I; `RAW_PROVENANCE` dependency now resolved (Entry H); black-box, no logprobs, no fine-tuning; external evidence for the core signal is strong (Kuhn et al., Nature 2024), the specific transfer (single-turn retrieve-decision → persistent-memory escalation-decision) is honestly flagged as untested by the candidate itself. **A $0 calibration was additionally run** (reusing already-persisted, already-labeled `RAW_PROVENANCE` fresh-replication data, zero new ingest): mean entropy on known-sufficient units = 0.300, on known-insufficient units = 1.104, separation +0.804 in the theoretically expected direction, clean at n=8. Cost: $0.003309.

**#2 (multi-query fusion):** already archaeologized during the discovery-rebuild-v3 workflow (`EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md`, rank 5, composite 378) — external evidence real (SmartSearch 88.4% measured directly on LongMemEval-S; RAG-Fusion +19% NDCG@10 general domain), not a duplicate of Entry M (single-shot HyDE — this is multi-query consensus, mechanistically distinct). **Cost disqualification for this stage:** requires a full fresh gold-blind mechanism test (own ingest, no already-labeled data to reuse the way #1 could) — estimated $0.50–0.80, which would leave an uncomfortably thin safety reserve against the ~$1.04 remaining at selection time. Not selected this round; remains `OPEN` for a future stage with more headroom.

**#3 (structured temporal field):** already archaeologized (`EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md`, rank 2, `VIABLE_WITH_CAVEATS`) — requires a NEW vendor patch and its own calibration cycle before any exploratory spend, then a dual-bank exploratory test (same cost shape as Entry O/P, ~$1.2–1.35). **Cost disqualification:** a full exploratory test would not fit inside the remaining budget with any safety reserve at all. Not selected; remains `OPEN`, explicitly noted as budget-blocked rather than evidence-blocked.

## Phase D — ranking

By expected-information-gain ÷ cost: **#1 dominates** — it is the only candidate where a genuine calibration could be run at near-zero cost (reusing already-persisted, already-labeled data no other candidate has an equivalent for), it already produced a clean, correctly-directioned signal, and its full causal test (~$0.45–0.60, single-bank ingest, no new vendor patch) comfortably fits the remaining budget with real safety reserve. #2 and #3 are not rejected on evidence — both remain credible, `OPEN` gaps — they are deferred purely on cost fit at this specific point in the campaign.

## Phase E — selection

**Selected: #1, `SEMANTIC_ENTROPY_SUFFICIENCY_GATE`.** Full causal test preregistered (`PM-20260825-e88248ff`) and launched — see `docs/research/SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md` for the result.
