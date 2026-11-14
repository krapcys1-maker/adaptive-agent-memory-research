---
id: rmc-2026-08-24-001
type: mechanism_candidate
researchos_label: CANDIDATE_FOR_TEST
external_evidence_status: EXTERNAL_MEASURED
status: PENDING_AAMR_REVIEW
created: 2026-08-24
source_run: ResearchOS night-campaign-v1 runs cmt7jjox200017sk6tne9tdf5 (broad survey, precondition-blocked cluster) and cmt7lcdfd0001lfzjs2bl5j8d (reframed, bestHypothesis below) — see docs/postmortems/night-campaign-v1-state.md in the ResearchOS repo for the full audit trail
source_refs: [https://arxiv.org/abs/2501.04899, https://doi.org/10.1038/s41586-024-07421-0, "internal:AAMR docs/research/MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md §4", "internal:AAMR docs/07-literature/evidence-ledger.csv AI-011"]
target_failure: Compact/summarized memory representations can silently omit or under-represent information needed to answer a query, with no current mechanism to detect this and escalate to the full/raw representation before generating an answer. AAMR's own MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md §4 ("context-sufficiency gate before attempting any expansion") names this exact dependency as open and states that no candidate cheap-proxy signal was found in AAMR's own literature search.
expected_positive_regime: Queries where the compact representation genuinely lacks the needed information (absence-type failures) — the regime SUGAR's own results and semantic-entropy theory most directly support.
possible_negative_regime: Queries where information is present in the compact representation but under-used or misread by the reader (presence-type failures) — AAMR's own MECHANISM_DEPENDENCY_SYNTHESIS §3-4 reports its own observed Mem0 failures are dominated by exactly this presence-but-still-wrong pattern, not absence. A semantic-entropy-style signal is not obviously suited to detecting this failure mode, so the effect on AAMR's actual workload could be smaller than on SUGAR's own benchmark, or null. Stated here deliberately, not discovered after the fact.
preconditions: No fine-tuning and no model-internal access required — uses only (1) the ability to sample the existing generation model multiple times at nonzero temperature (standard API capability, already available), and (2) a frozen text-embedding model to cluster the sampled outputs semantically (AAMR's own stack already uses local FastEmbed MiniLM per evidence-ledger AI-060, so no new dependency). Explicitly does NOT need logprobs or token-level probabilities — this is the discrete/black-box semantic-entropy variant, not the token-level-entropy variant used by FLARE/DRAGIN (which does require model-internal signals and would hit the same precondition problem AAMR's scope.md rules out).
duplicate_of: Not a duplicate of AAMR's own RAW_PROVENANCE_EXPANSION mechanism (that question — does raw fallback help at all — is already AAMR's own, via the planned/pending Experiment #3 "arena-provenance-clean-v2", cap $0.10). This candidate is downstream of and sequenced after that one: it answers "what signal decides when to try the fallback," not "does the fallback work." Closest external prior art: SUGAR (Zubkova, Park, Lee — arXiv 2501.04899, Jan 2025), which validates the identical signal (semantic entropy, sample-and-cluster) for a related but different decision point (whether to retrieve from an external corpus at all, in single-turn RAG) — not for compact-vs-raw escalation inside a persistent agent memory. That transfer is the actual open question.
estimated_test_cost_usd: ~0.05-0.15 (M=10-20 cheap samples per query on an existing small fixture with already-known ground truth; comparable order of magnitude to AAMR's own reported small-fixture experiment costs, e.g. Experiment #3's own $0.10 cap)
confidence: Medium — the underlying signal is empirically validated in a closely related setting (SUGAR), which lowers implementation risk versus an unprecedented design; the genuine uncertainty is specifically whether it transfers to AAMR's own decision point and workload, which no source (AAMR's own docs or ResearchOS's search) has tested, and AAMR's own failure-mode data gives a concrete reason it might transfer only partially.
---

## Summary

Test embedding-clustered semantic entropy over multiple sampled generations (black-box, no model-internal access) as the cheap proxy signal for AAMR's own open compact-vs-raw memory escalation gate (`MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md` §4) — adapting SUGAR's already-validated retrieval-gating mechanism to AAMR's specific, narrower decision point.

## Why this might matter to AAMR

AAMR's own synthesis doc names this gate as an open dependency and explicitly states that no candidate signal was found in AAMR's own search. The signal proposed here is not a fresh, unprecedented idea — it is already empirically validated for a closely related decision (SUGAR, Jan 2025), which makes the implementation risk lower than proposing something with zero prior evidence. The open part is narrow and specific: does the same signal, computed the same way, transfer from "retrieve or not" to "compact summary or raw record."

## Evidence

**What was actually measured (not just claimed):**
- Semantic entropy over sampled, semantically-clustered generations reliably estimates black-box model uncertainty without needing token probabilities (Kuhn et al., Nature 2024 — already in AAMR's own evidence-ledger.csv as AI-011).
- SUGAR (arXiv 2501.04899, Jan 2025) measured that this same signal, used to decide *whether and how much* to retrieve, improves QA performance and retrieval efficiency across multiple benchmarks. This is the closest prior art found (two targeted WebSearches, both general web and arXiv-focused) — genuinely close, not a loose analogy.
- Checked FLARE and DRAGIN as alternative prior art: both use token-level predictive entropy computed from model-internal logprobs/attention distributions, not the black-box sample-and-cluster variant. Both would hit the same precondition problem as the ResearchOS run that originally surfaced the parametric-consolidation cluster this candidate replaced — AAMR's own scope.md excludes model-internal activation access during this research phase. Not viable prior art for AAMR's actual constraints; noted for completeness.

**What is not measured anywhere (the actual gap):**
- No source found — not AAMR's own docs, not the two WebSearches run for this candidate — tests this signal specifically for compact-summary-vs-raw-memory escalation inside a *persistent* agent memory system, as opposed to a single-turn "retrieve from an external corpus or not" decision.

**Negative-evidence caveat, from AAMR's own data (not glossed over):**
- `MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md` §3-4 reports AAMR's own observed Mem0 failure cases are dominated by "gold present at rank 1... but still wrong" — a presence-type failure, not an absence-type one. Semantic-entropy-style signals are theoretically best suited to detecting *absence* of information (the model genuinely doesn't know), not presence-but-misuse. This is a concrete, AAMR-internal reason the effect could be smaller on AAMR's actual workload than on SUGAR's own benchmark, possibly null. Any test of this candidate should report the absence/presence split explicitly, not just an aggregate number.

**Supporting background (secondary, not load-bearing):** ResearchOS's own literature run (25 sources via pubmed/openalex/crossref) surfaced additional general hallucination-detection literature consistent with semantic entropy's black-box viability, without exceeding the two primary sources above.

## Suggested next step for AAMR

Reuse an existing small fixture with already-known ground truth for compact-vs-raw sufficiency (e.g. the arena-context-ablation or pmlab-reuse-characterization fixtures already in AAMR's own `data/lab/`). For each query: sample M=10-20 generations from the existing generation model at nonzero temperature, embed with the already-used local FastEmbed MiniLM, cluster, compute entropy, and check whether entropy correlates with the already-known cases where the compact representation was actually insufficient — reporting the absence/presence split called out above, not just an aggregate correlation. Sequence this after AAMR's own Experiment #3 (`arena-provenance-clean-v2`) resolves whether raw fallback helps at all — if Experiment #3 finds zero repairs, this gate is moot regardless of signal quality, and testing it first would waste budget on a downstream question before the upstream one is settled.
