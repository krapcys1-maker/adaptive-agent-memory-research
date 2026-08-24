# External Discovery Candidate Pool v2

Campaign V2 (external-discovery-first strategy) opening phase. Executed as a 12-agent Workflow (8 parallel discovery searches → synthesis/dedup → zero-cost archaeology on top 3). Zero AAMR experiment spend — this entire phase used only web/GitHub research and code reading, none of it against the project's $5 experiment budget.

Full pool, scores, and raw archaeology text: workflow journal `wf_d25fd577-a75`. 42 raw candidate mentions → 28 deduped pool entries after clustering.

## Critical catch: a false "CODE_VERIFIED" claim, caught twice independently

The top-ranked pool entry (`STATE_SUPERSESSION_BREADTH_REDIAGNOSIS`, composite score 12500 — far above everything else) claimed direct code-reading proof that this project's vendored Mem0 is "v2.0.18" with a "purely additive" write path (no UPDATE/DELETE ever emitted), which would have overturned Mechanism B's DROP verdict (`CURRENT_STATE_OVER_HISTORY`, Ledger Entry G) and reopened it as a live candidate.

**This is false for this project's actual harness.** Caught two ways:
1. **Independently, by me, before trusting the workflow's own archaeology phase**: `pip show mem0ai` on the actual installed environment (`external/venvs/mem0`) returns `1.0.6`, not `2.0.18`. Direct `grep` of the real `_add_to_vector_store` shows `get_update_memory_messages`, `event_type == "UPDATE"`, and `event_type == "DELETE"` are live code paths — exactly matching what Mechanism B's own empirical `memory.get_all()` reads already showed happening.
2. **By the workflow's own archaeology agent**, independently: it read the exact same file the discovery agent cited, confirmed no such version exists anywhere in this project (a targeted grep for "2.0.18" found zero mem0-related hits), and found `_update_memory`/`_delete_memory` are real, non-stub, live-default-path implementations.

Root cause: the discovery agent had cloned `external/repos/mem0ai__mem0` — the current upstream GitHub repository — and mistook that for this project's actual vendored/pinned copy in `external/venvs/mem0` (site-packages, `mem0ai==1.0.6`). Two structurally different codebases, conflated. This is precisely the failure mode the evidence-class discipline (`CODE_VERIFIED` requires reading the *right* code) exists to catch, and it was caught before a single dollar was spent re-testing a falsified premise.

**Consequence:** Mechanism B's DROP verdict is **not** reopened. `CURRENT_STATE_OVER_HISTORY`'s original rationale (Mem0's own write-time ADD/UPDATE/DELETE reconciliation absorbs the target precondition before any read-side mechanism sees it) stands, and is if anything reinforced by this closer read.

## Candidates #2 and #3: also disqualified, using real accumulated AAMR data

- **`SERIAL_POSITION_CONTEXT_REORDER`** ("lost in the middle" reordering, CODE_VERIFIED against LangChain's actual algorithm): archaeology reconstructed the full gold-rank position vector across **17 distinct observable AAMR retrieval runs to date** (superset of the already-recorded "9/9") — **gold_rank = 1 in 17/17 (100%)**. The precondition (gold ranked 2nd–9th, "buried in the middle") has never once occurred in this project's actual retrieval history. Worse, the archaeology found the specific alternating-reorder algorithm would *demote* items originally ranked 8–10, which remain gold-relevant 41–59% of the time in this corpus's multi-session/knowledge-update questions (many LongMemEval-S units label several sessions as gold). Not a harmless null — a plausible mild negative. **NOT_VIABLE.**
- **`RETRIEVAL_BREADTH_AND_THRESHOLD_EXPANSION`** (external evidence: Memanto, +26.2pp from breadth alone on LongMemEval): AAMR already ran exactly this sweep, to the literal ceiling (whole-store retrieval, 201–272 items/unit), months before this campaign — the corrected breadth-ablation curve is flat at the ceiling (5/10 native → 5/10 at whole-store), with a documented distractor-cost regression from widening (`gpt4_f49edff3`, a confirmed `TRACEABLE_DISTRACTOR` case) and an already-computed oracle-vs-best-fixed-arm ceiling of **+1/10 unit** for any breadth-tuning scheme — and that one unit is independently flagged as noise (single-generation judge cell, unreplicated). **NOT_VIABLE.**

## Remaining pool, notable entries not yet actioned

- **`SECOND_HOP_ASSOCIATIVE_EXPANSION`** (rank 5, CODE_VERIFIED against A-MEM's actual link-traversal code) — selected as Mechanism G, see [`SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md`](SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md).
- **`CONTEXT_WRITE_TIME_ONLY_LEVERAGE`** (rank 7, not a transplant candidate — a strategic finding): independent external evidence (`arXiv:2606.15903`, ForgetEval, 1,385 cases) that read-time-only conflict/supersession handling plateaus in a statistically indistinguishable band across three architecturally distinct systems (63–68%), while a write-time LLM hook lifts scores to 91–94%. **Recommendation adopted:** deprioritize any further read-side-only conflict/supersession mechanism (this affects pool entries `SCOPED_CONTRADICTION_FLAG`, `STANDING_RULE_VS_INSTANCE_TAGGING`, `INTENT_AWARE_REVOCATION_SUPPRESSION`, `DETERMINISTIC_FRESHNESS_AGGREGATION`, `EVIDENCE_EXTRACTION_POLICY_SEPARATION` — all in this same family) unless project scope is explicitly revisited to allow write-time hooks.
- **`EBBINGHAUS_DECAY_RERANK` (avoid)** — flagged explicitly as a documented negative: an independent head-to-head study (MemoryOS, EMNLP 2025) found pure decay-curve reranking the *worst*-performing method on both its benchmarks. Recorded so it is not independently rediscovered.
- **`EVIDENCE_EXTRACTION_POLICY_SEPARATION` (avoid)** — the source paper's *own* generalization check on LongMemEval itself (this project's actual benchmark) found no significant advantage (26/45 vs 29/45, p=0.45). Recorded as a documented near-miss, not worth prioritizing.
- Several LLM-mediated verification/self-consistency mechanisms (`CHAIN_OF_VERIFICATION_FACTORED`, `PARAPHRASE_SELF_CONSISTENCY`, `VERBALIZED_CONFIDENCE_GATED_REPAIR`, `TARGETED_EVIDENCE_REPAIR`) scored well on independence and evidence strength but carry materially higher per-unit cost (3–5x reader calls) — held in reserve as the next tier if Mechanism G does not validate.

## Evidence-discipline note

No claim in this pool was silently upgraded between evidence classes. Several PAPER_CLAIM-level numbers were explicitly left unverified rather than assumed (e.g. `EVIDENCE_TAGGED_CITATION`'s accuracy delta, `RARR`'s ">90% preservation" figure) because the underlying table couldn't be cleanly extracted from a compressed PDF pass — flagged rather than rounded up.
