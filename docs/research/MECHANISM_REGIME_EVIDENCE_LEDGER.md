# Mechanism × Regime Evidence Ledger

Cumulative, append-oriented. Entries are added or superseded (with a `superseded_by` pointer), never deleted or silently rewritten. Each entry records what is currently believed about one mechanism under one regime, on what evidence, and what would change it.

---

## Entry A — `TEMPORAL_ANCHOR_AT_CONTEXT` × `SESSION_EVENT_ALIGNED`

- **MECHANISM:** `TEMPORAL_ANCHOR_AT_CONTEXT` — render each retrieved fact as `[YYYY-MM-DD] {fact}` using its session timestamp, read-side only.
- **REGIME:** questions where the session-recording timestamp is a good proxy for the true event time (no competing in-text date, or the in-text date and session date agree) — `SESSION_EVENT_ALIGNED`.
- **FAILURE_TARGETED:** reader cannot order or date-arithmetic facts that are temporally implicit (no in-text date, order matters).
- **OBSERVED_EFFECT:** POSITIVE, mechanistically confirmed via direct transcript evidence in both E1 (`gpt4_f420262c`-style multi-fact ordering) and Stage 2 (`0bc8ad92`: reader cites the rendered date + a context-stated current date, correctly computes duration, judged correct under the frozen judge's own off-by-one tolerance).
- **SOURCE_EXPERIMENTS:** E1 (`PM-20260824-2d603195`, [`READ_SIDE_TEMPORAL_ANCHOR_V1.md`](READ_SIDE_TEMPORAL_ANCHOR_V1.md)); Stage 2 (`PM-20260824-8dc62d48`, [`TEMPORAL_ANCHOR_FRESH_REPLICATION_V1.md`](TEMPORAL_ANCHOR_FRESH_REPLICATION_V1.md)); this archaeology ([`TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md`](TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md)).
- **EXTERNAL_SUPPORT:** none directly cited; consistent with the general intuition in temporal-grounding literature that explicit timestamps aid duration/ordering reasoning.
- **CONFIDENCE:** MEDIUM — real, transcript-confirmed effect, but only two clean independent positive instances across two experiments; regime boundary (alignment) is itself only partially validated (see Entry B for where it breaks).
- **KNOWN_COUNTEREXAMPLES:** `08f4fc43` repairs despite `SESSION_EVENT_DIVERGENT` alignment — because the fact carries its own explicit in-text date, making the divergence harmless. This means "alignment" alone is not the full boundary condition; presence of a usable date (session anchor OR in-text) for a *bounded lookup* task appears closer to the real condition.
- **STATUS:** `TEMPORAL_ANCHOR_SUPPORTED` (exploratory, E1) `QUALIFIED_BY` Stage 2 fresh replication — narrowed from "ordering questions in general" to "bounded lookups/arithmetic over explicitly-or-well-anchored named events." **UPDATE (Mechanism I, Entry N):** the further-narrowed `TEMPORAL_BOUNDARY`-only replication this note called for has now been run (8 fresh units) — 0 net repairs, but also 0 regressions, a third consecutive clean-null-or-positive sample. Status remains `SUPPORTED, qualified` — not elevated to `REPLICATED_VALIDATED_TRANSPLANT`, not weakened either. See Entry N for full detail.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a further replication specifically targeting `TEMPORAL_BOUNDARY`-shaped (bounded lookup/arithmetic) questions, gold-blind selected, would sharpen this regime boundary further. Now run — see Entry N.

---

## Entry B — `TEMPORAL_ANCHOR_AT_CONTEXT` × `SESSION_EVENT_DIVERGENT`

- **MECHANISM:** `TEMPORAL_ANCHOR_AT_CONTEXT` (same as Entry A).
- **REGIME:** many-item filter/count questions where several facts share one (later, recap-session) timestamp while each fact's own text carries a different, specific event date — `SESSION_EVENT_DIVERGENT`.
- **FAILURE_TARGETED:** N/A — this is a *negative-transfer* regime, not one the mechanism was designed to address.
- **OBSERVED_EFFECT:** NEGATIVE. `00ca467f` (doctor's appointments in March): BASE correctly lists both appointments using their in-text dates (March 3, March 20); `+TIME` renders only the shared later session-recording date on both, and the reader undercounts to 1, dropping the March 3rd item.
- **SOURCE_EXPERIMENTS:** Stage 2 (`PM-20260824-8dc62d48`); this archaeology.
- **EXTERNAL_SUPPORT:** none directly cited.
- **CONFIDENCE:** MEDIUM-LOW — one clean, well-evidenced instance; not yet replicated, and a structurally similar-looking case (`08f4fc43`) did NOT show this failure, so the true boundary (task type: many-item filter/count vs. two-item lookup) is inferred, not confirmed independently.
- **KNOWN_COUNTEREXAMPLES:** `08f4fc43` — same shared-anchor-plus-differing-in-text-dates structure, opposite (positive) outcome; the working distinction offered is task type (bounded lookup vs. many-item filter/count over a repeated tag), but this has an n of 1 vs 1 and is not independently confirmed.
- **STATUS:** `OBSERVED_CASE` — a real, specific negative-transfer mode worth carrying into any future design, not yet a general law.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** motivates hypothesis `EVENT_TIME_OVER_SESSION_TIME_PRECEDENCE` (see archaeology report) and strengthens the rationale for E2 (write-side resolved-event-date grounding). Not authorized to test by this document.

---

## Entry C — `HARMFUL_SIBLING_DISTRACTION`

- **MECHANISM:** none proposed yet — this is a *failure-mode candidate*, not a fix. Definition: correct evidence is present in the delivered context, but a semantically related, competing (wrong) item at close rank causes the reader to select, blend with, or default to the wrong variant instead of doing the harder correct resolution.
- **REGIME:** enumeration/identification tasks (e.g., "name the Nth item of category X") where a genuinely present but factually distinct sibling entity sits near the correct evidence cluster.
- **FAILURE_TARGETED:** wrong-entity substitution where the correct answer requires a harder multi-hop resolution than a nearby, directly-named wrong alternative.
- **OBSERVED_EFFECT:** one primary case. `gpt4_f420262c` (E1, BASE arm): wrong answer names "Spirit Airlines" as the 4th airline; the frozen `mem0_3000` context contains two real, present Spirit Airlines items at close rank (5 and 12) to the actually-relevant flight cluster (ranks 0,2,3,7,9); the correct airline (Delta) requires linking an unnamed flight to a separate SkyMiles mention. Classified `TRACEABLE_DISTRACTOR`.
- **SOURCE_EXPERIMENTS:** E1 (`PM-20260824-2d603195`, [`mem0-breadth-arms.json`](../../data/lab/arena/mem0-breadth-arms.json)); systematically checked against all 5 Stage 2 repair/regression cases in this archaeology — **0 of 5 show this pattern** (Stage 2's changes are hedges, omissions, or same-entity date conflicts, not sibling substitution); one Stage 2 case (`0bc8ad92`) shows a real near-miss distractor (a museum visit "with dad" vs. gold's "with a friend") being *correctly avoided*, a useful negative control.
- **EXTERNAL_SUPPORT:** none directly cited; consistent in spirit with general RAG "lexical near-miss" distractor literature, not specifically verified against it in this pass (no web research performed, per scope).
- **CONFIDENCE:** LOW — single confirmed instance, systematically absent from a second, independently-generated 5-case sample.
- **KNOWN_COUNTEREXAMPLES:** none for the phenomenon itself (it did occur where observed); Stage 2 is a null result for its *prevalence*, not a counterexample to its *existence*.
- **STATUS:** `OBSERVED_CASE` — explicitly NOT promoted to a measured general failure mode on one example, per required interpretation discipline.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a dedicated, gold-blind sample of enumeration/identification questions with known close-rank sibling entities would be needed to move this past `OBSERVED_CASE`. Not authorized or scheduled by this document. Motivates hypothesis `DISTRACTOR_AWARE_CONTEXT_ASSEMBLY` (untested).

---

## Entry D — `AUTHORITY_COLLAPSE_SAFE_CONSOLIDATION` (future trigger, not testable yet)

- **MECHANISM:** not yet designed in AAMR. External frontier concept (arXiv:2608.01679, "When Memory Becomes Authority") describing consolidation/summarization designs that avoid a stored summary silently overriding or discarding the raw evidence it was derived from.
- **REGIME:** any future AAMR mechanism that performs memory consolidation, summarization, or fact-merging at write time or at context-assembly time.
- **FAILURE_TARGETED:** "authority collapse" — a consolidated/summarized memory item being trusted over, or replacing access to, the raw source facts it summarizes, in a way that silently drops information (the external paper reports this in 48/49 tested authority-collapse configurations).
- **OBSERVED_EFFECT:** N/A — AAMR has no consolidation mechanism today; nothing to observe.
- **SOURCE_EXPERIMENTS:** none in AAMR. External: [`GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`](GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md) (parallel-session document, read-only reference here).
- **EXTERNAL_SUPPORT:** STRONG per the frontier map's summary of the source paper (48/49 configs affected) — not independently re-verified by this session (no web research performed).
- **CONFIDENCE:** N/A (design constraint, not an empirical AAMR finding).
- **KNOWN_COUNTEREXAMPLES:** N/A.
- **STATUS:** `EXTERNAL_STRONG_SIGNAL, AAMR_UNTESTED, NOT_ACTIONABLE_YET`.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** revisit before the first AAMR consolidation/summarization mechanism is designed, trusted, or adopted — this entry should gate that design, not be tested standalone before one exists.

---

## Entry E — `EVENT_TIME_RESOLUTION_AT_EXTRACTION`

- **MECHANISM:** `EVENT_TIME_RESOLUTION_AT_EXTRACTION` — write-side, distinct from `TEMPORAL_ANCHOR_AT_CONTEXT` (Entries A/B, which are read-side only, do not touch extraction). Adds one instruction bullet to Mem0's fact-extraction prompt, immediately after the (already correct, per `PER_SESSION_REFERENCE_DATE_AT_EXTRACTION`) `"Today's date is ..."` line, telling the model to resolve relative time expressions ("today", "yesterday", "last month", "next year", etc.) against that date and store the resolved absolute date, while never fabricating one when the text gives insufficient information.
- **REGIME:** `RELATIVE_EVENT_TIME_WITH_VALID_REFERENCE_DATE` — extraction of a fact containing a relative time expression, under a correct, correctly-threaded per-session reference date.
- **FAILURE_TARGETED:** the `00ca467f`-style session-vs-event-time negative-transfer mode (Entry B) at its root, by storing the resolved event date directly instead of requiring read-side reconciliation between a rendered session anchor and an in-text date.
- **OBSERVED_EFFECT:** NEGATIVE / NULL. Calibration ([`EVENT_TIME_RESOLUTION_CALIBRATION_V1.md`](EVENT_TIME_RESOLUTION_CALIBRATION_V1.md)) found the instruction changed extraction behavior in **0 of 5** cases — CONTROL and TREATMENT produced byte-identical extracted fact text in every case, including the four relative-time-bearing ones. `TREATMENT_RESOLVED = 0/4`. The instruction, as minimally phrased, is inert on `deepseek-chat` for this prompt structure.
- **SOURCE_EXPERIMENTS:** this calibration only (`PM-20260824-e9f15438` preregistration; verdict recorded in a companion project-memory event). No benchmark run — capability calibration only, 10 calls, $0.002811 spend against a $0.03 cap.
- **EXTERNAL_SUPPORT:** none cited; not researched this pass (no web research performed, per scope).
- **CONFIDENCE:** MEDIUM that the specific minimal-instruction design is inert (clean, unambiguous, zero-effect-in-5/5-cases result) — LOW on whether ANY instruction-based approach could work, since only one wording was tried and the pre-registered discipline explicitly forbids iterating wording after a FAIL without separate approval.
- **KNOWN_COUNTEREXAMPLES:** none — the null result was uniform across all 5 cases, no case showed partial or inconsistent behavior.
- **STATUS:** `CALIBRATION_FAILED`. Full E2 (a benchmark-scale run of this mechanism) is **`NOT_ELIGIBLE`** on this evidence.
- **RISK / COUNTEREXAMPLE TO GUARD AGAINST IN ANY FUTURE DESIGN:** `SESSION_TIME MUST NOT OVERRIDE EXPLICIT EVENT_TIME` — untested here (this calibration used only bare relative expressions, no case had a competing in-text explicit date for the model to potentially override), but any future write-side design that resolves event dates must preserve an explicitly-stated in-text date rather than silently substituting the session reference date, per the negative-transfer mechanism already documented in Entry B.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a separately-approved few-shot or structurally-different treatment (e.g., a dedicated `resolved_date` output field instead of in-line text resolution) would need its own pre-registration and calibration before any further consideration. Not authorized or scheduled by this document.

---

## Entry F — `CURRENT_STATE_OVER_HISTORY` (candidate, design-preregistered only)

- **MECHANISM:** read-side, post-retrieval, pre-render. Groups retrieved items sharing a deterministically-detected state key; renders the latest-timestamped item as `Current state:`, the rest as a provenance-preserving `History (superseded):` block. Isolated from StateMemWrapper's Resolve step, precedence rule 1 of 4 ("later supersedes earlier") only — rules 2–4 and the LLM-mediated Trace step are explicitly not transplanted.
- **REGIME:** `RELATIVE_EVENT_TIME` is not the axis here — regime is `STATE_KEY_MATCHED_WITH_TIMESTAMP_ORDERING`: ≥2 retrieved items share a state key detected by one of 9 fixed deterministic templates, and their session timestamps differ.
- **FAILURE_TARGETED:** `STALE_STATE_CONFUSION`, submodes A (direct supersession) and C (return/reactivation) directly; B (revocation) partially — see design doc for the full breakdown. D (multi-attribute), E (dependency cascade), F (ambiguous update) explicitly out of scope for V1.
- **OBSERVED_EFFECT:** N/A — no experiment has run. This is a design + preregistration only.
- **SOURCE_EXPERIMENTS:** none run. Design: [`MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md`](MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md), preregistration `data/lab/arena/mechanism-b-state-supersession-v1/preregistration.json`. Internal supporting evidence (not this mechanism, but the failure mode it targets): `data/lab/pmlab-stale-e1/execution-v0/report.md` (n=9, content similarity cannot separate a stale fact from its replacement; already cited as F17 in `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md`).
- **EXTERNAL_SUPPORT:** StateMemBench/StateMemWrapper (arXiv:2608.19652, MEASURED by the source paper, independently recomputed by the frontier-map pass, not yet independently replicated by anyone outside that paper); STALE (arXiv:2605.06527); StateAuditor (arXiv:2608.01619, honest self-reported non-replication on a second benchmark).
- **CONFIDENCE:** N/A — untested in AAMR. External support for the general family is real but single-paper/days-old for the specific source (StateMemBench).
- **KNOWN_COUNTEREXAMPLES:** N/A — nothing measured yet.
- **STATUS:** `EXTERNAL_SIGNAL, AAMR_UNTESTED, DESIGN_PREREGISTERED`.
- **RISK / COUNTEREXAMPLE TO GUARD AGAINST:** state-key over-matching could collapse two genuinely distinct, co-existing facts (different entities sharing surface vocabulary) into a false supersession — this is the same shape of error as `HARMFUL_SIBLING_DISTRACTION` (Entry C) but on the temporal-validity axis rather than the entity-identity axis. V1's R4 adversarial control probes are specifically designed to catch this before any positive result could be trusted.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** Entry G (Stage 1 exploratory test run and closed).
- **NEXT_TRIGGER:** superseded — see Entry G.

---

## Entry G — `CURRENT_STATE_OVER_HISTORY` (Stage 1 result: harness precondition never met, DROP)

- **MECHANISM:** same as Entry F, which this supersedes with a measured (not merely designed) status.
- **REGIME:** `STATE_KEY_MATCHED_WITH_TIMESTAMP_ORDERING` — but empirically, this regime **never arose** in either the original or repaired Stage 1 run: `current_history_split` (the mechanism's core action) fired **zero times across 24 probe-executions**.
- **FAILURE_TARGETED:** `STALE_STATE_CONFUSION` — untested, not refuted (see below).
- **OBSERVED_EFFECT:** `UNEXERCISED, NOT NEGATIVE`. Original run: BASE 12/12, `+B` 12/12, net repairs 0 — explained entirely by Mem0 1.0.6's own write-time ADD/UPDATE/DELETE reconciliation fully consolidating 8 of 9 R1/R2/R3 probes' sequential same-key statements into a single surviving memory before the mechanism ever saw competing items (verified at $0 via `memory.get_all()` reads on the persisted store). One repair retest (filler-spaced turns, the one permitted repair per the campaign's repair-budget rule) tested the hypothesis that turn-adjacency caused this — **the hypothesis was wrong**: state-carrying facts still fully consolidated to one item regardless of spacing, because Mem0's "existing memories" comparison is semantic/embedding-based, not proximity-based. One nominal flip (`RET3_DIET`, BASE wrong → `+B` correct) traced to a context-reordering side effect of the passthrough implementation, not the intended Current/History logic — not counted as a real repair.
- **SOURCE_EXPERIMENTS:** [`MECHANISM_B_STAGE1_RESULTS_V1.md`](MECHANISM_B_STAGE1_RESULTS_V1.md); `data/lab/arena/mechanism-b-state-supersession-v1/{stage1-raw.json, stage1-archaeology.json, stage1-repair-raw.json}`. Spend: $0.022315 (original) + $0.041754 (repair) = $0.064069.
- **EXTERNAL_SUPPORT:** unchanged from Entry F.
- **CONFIDENCE:** HIGH that this specific V1 harness on this host (Mem0 1.0.6) cannot exercise the mechanism as designed. LOW/UNKNOWN on the mechanism's own merit — it was never falsified, only untested (its logic behaved correctly in every case it had material to act on: 0/3 false supersession on R4 controls across both runs, correct tie-safe no-guess fallback on `SUP3`).
- **KNOWN_COUNTEREXAMPLES:** N/A for the mechanism itself. For the *host*: `RET1_JOB` shows Mem0's own write-time consolidation is not even reliably recency-correct (kept the middle of three sequential facts, not the latest).
- **NEW_INFRASTRUCTURE_FINDING (not previously recorded):** Mem0 1.0.6's UPDATE path can silently overwrite `metadata.timestamp` on an *existing* memory to match a later, textually-unrelated `add()` call's date, even when that memory's own text is left unchanged (`SUP3`: "Got engaged to my partner" kept its wording, lost its true date). This weakens `evidence_times` as a trustworthy recency signal for *any* mechanism that depends on it, including `TEMPORAL_ANCHOR_AT_CONTEXT` (Entries A/B).
- **STATUS:** `DROP (V1 harness, this host) — MECHANISM_LOGIC_UNEXERCISED, NOT REFUTED`.
- **RISK / COUNTEREXAMPLE TO GUARD AGAINST:** unchanged from Entry F (state-key over-matching), still untested since the mechanism never ran its core path.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** Entry F.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a future harness that either bypasses/observes Mem0's own update-decision step directly, or builds probes from real, far-separated multi-session LongMemEval conversations (genuinely untested whether that changes Mem0's consolidation behavior), would be required before this mechanism could be meaningfully tested on Mem0 again. Not scheduled by this entry. The infrastructure finding (metadata-timestamp overwrite) should be checked before trusting `evidence_times` in any future experiment.

---

## Backlog (not run, not authorized here)

### `ZERO_ANSWER_DISPERSION_DIAGNOSTIC` (frontier H2)

- **STATUS:** `CHEAP_FOLLOWUP, NOT_RUN`.
- **WHAT_IT_WOULD_TEST:** whether a stable failure mode (vs. reader/judge noise) can be distinguished by dispersion of answers across repeated reads on ambiguous units — relevant to `H0` (noise) in this archaeology's competing-explanations analysis.
- **TRIGGER_CONDITION:** only if a future $0 archaeology pass cannot distinguish stable failure from reader noise on a specific probe using existing frozen data alone.
- **ESTIMATED_COST:** ~$0.01–0.02.
- **SOURCE:** [`GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`](GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md) (external reference, arXiv:2606.22728).

---

## Entry H — `RAW_PROVENANCE` (C4) × `COMPACT_ABSENCE_OR_UNDERDETAIL` — first `REPLICATED_VALIDATED_TRANSPLANT`

- **MECHANISM:** read-side only. Appends the raw source session behind Mem0's top-1 retrieval hit to its compact context, verbatim (`mem0_compact_plus_raw`). Deterministic session-date mapping (`arena.mechanism_ablation.raw_session`, `arena.retrieval_truth.session_map`) — no gold-aware matching, no semantic guessing.
- **REGIME:** `COMPACT_ABSENCE_OR_UNDERDETAIL` — Mem0's compact extraction either drops a specific detail entirely (absence) or retains a fact without enough surrounding information to arbitrate between competing mentions (under-detail), AND the needed content is reachable via the top-1 hit's single source session (single-hop; this mechanism does not search beyond that one session).
- **FAILURE_TARGETED:** compact-context information loss at Mem0's own extraction/compression step.
- **OBSERVED_EFFECT:** POSITIVE, mechanistically confirmed twice, independently. E3 (original 10-unit-derived sample, 9 observable): compact 5/9, compact+raw **6/9**, raw-only 4/9; 1 repair (`6a27ffc2`, competing-facts disambiguation between a stale count and an updated one both already present in compact). This replication (8 fresh, gold-blind, never-used units): compact 5/8, compact+raw **6/8**, raw-only 4/8; 1 repair (`0e5e2d1a`, a genuine absence-type repair — compact dropped a specific number, "38 subjects," that the raw session states directly; `gold_in_context=True, gold_rank=1` in the raw-augmented arm). Zero regressions in both runs. `raw_only` underperforms `compact` in both runs, replicating that direction too.
- **SOURCE_EXPERIMENTS:** E3 (`docs/research/CLEAN_RAW_PROVENANCE_RETEST_V2.md`); fresh replication `PM-20260824-0a6fc616` / [`RAW_PROVENANCE_FRESH_REPLICATION_V1.md`](RAW_PROVENANCE_FRESH_REPLICATION_V1.md), `data/lab/arena/raw-provenance-fresh-replication-v1/{selection.json, results.json}`. Combined spend: E3 $0.018390 + replication $0.575419 = $0.593809.
- **EXTERNAL_SUPPORT:** TierMem (raw 0.873 > routed 0.851 > summary 0.755 on LoCoMo, EXTERNAL_MEASURED, though its router regresses on LongMemEval Knowledge-Update); Verbatim Chunks (verbatim 43.9% vs extracted 28.0%, hybrid preserves the gap, EXTERNAL_MEASURED) — both cited in `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md` §4 as raw-vs-compact evidence, real but regime-dependent.
- **CONFIDENCE:** MEDIUM. Effect is real and replicated (2 independent samples, 2 different repair mechanisms — competing-facts and absence — both traceable in transcript, 0 regressions across 17 combined observable units) but small in magnitude (1 repair per ~8-9 units each time) and single-hop-limited.
- **KNOWN_COUNTEREXAMPLES:** `078150f1` (multi-session) — needed detail exists in a *different* session than the top-1 hit's; single-hop provenance cannot reach it, a known, named limitation (not a failure of the mechanism's own logic). `0bc8ad93` (temporal-reasoning) — raw text made zero difference; both arms confidently give the same wrong answer, suggesting an entity/visit-matching confusion (H5-adjacent) that raw content alone does not resolve. `ba358f49` and `gpt4_f420262c` (E3) — both hypothesized a priori to benefit, neither repaired.
- **STATUS:** **`RAW_PROVENANCE_REPLICATED_SUPPORTED` → `REPLICATED_VALIDATED_TRANSPLANT`** (campaign status ladder: external motivation + isolated transplant + exploratory positive [E3] + fresh gold-blind replication + confirmed mechanistic trace, all satisfied). The first mechanism in this project to reach this status. Not claimed as large-effect or general-purpose — see confidence note.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** the original contaminated-data `RAW_PROVENANCE_EXPANSION → DROP` conclusion (already superseded by E3 itself; this entry is the ledger's first formal record of the mechanism's validated status).
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** this is the campaign's first `REPLICATED_VALIDATED_TRANSPLANT` — per the interaction-test gate (only unlocked when 2 mechanisms are both at this status), a second independently-validated mechanism is needed before any `BASE/+A/+B/+A+B` interaction test may run. A multi-hop extension (reaching beyond the top-1 session) would directly address the `078150f1`-class counterexample but is untested and not scheduled here.

---

## Entry I — `RETRIEVAL_CONFIDENCE_SIGNAL` — DROP (regime mismatch, small n)

- **MECHANISM:** read-side, deterministic. Appends one fixed, content-free note when the top-1 vs top-2 Mem0 retrieval score margin is below 0.10; inert otherwise. Uses Mem0's own already-returned scores, zero LLM.
- **REGIME (target, untested):** gold answer retrieved but not top-ranked, under genuine score ambiguity (near-tied top candidates).
- **FAILURE_TARGETED:** reader over-trusting the most prominent retrieved item when retrieval itself is ambiguous — distinct axis from `RAW_PROVENANCE` (Entry H, content absence) and the dropped state mechanism (Entry G, temporal validity).
- **OBSERVED_EFFECT:** NULL. 4 fresh, gold-blind units (n reduced from preregistered 5 after a provider-cap interruption on the 5th unit, mid-run — disclosed, see `RETRIEVAL_CONFIDENCE_SIGNAL_V1.md`). 3/4 flagged (margin < 0.10). Net repairs 0, regressions 0. Answer *text* visibly changes on all 3 flagged units (reader reacts to the note) but correctness never does.
- **SOURCE_EXPERIMENTS:** `PM-20260824-3885f6ac` (preregistration); [`RETRIEVAL_CONFIDENCE_SIGNAL_V1.md`](RETRIEVAL_CONFIDENCE_SIGNAL_V1.md); `data/lab/arena/retrieval-confidence-signal-v1/{selection.json, results.json}`. Spend $0.347161 (mostly ingest, before the interruption).
- **EXTERNAL_SUPPORT:** "When Confidence Takes the Wrong Path" (arXiv:2606.22728, frontier map family #5); this project's own prior roadmap flagged the score-margin gap as worth a free check.
- **CONFIDENCE:** LOW on the mechanism itself (untested precondition) — HIGH that this specific n=4 sample did not contain the target regime: the 2 flagged-and-wrong units are both absence failures (needed fact missing from the top-10 retrieved set entirely, not present-but-buried), which no prominence-flagging note can fix by construction.
- **KNOWN_COUNTEREXAMPLES:** none observed — no case showed the mechanism causing harm; it simply never had the chance to help.
- **STATUS:** `DROP (small-n, regime mismatch) — MECHANISM_UNTESTED_AT_TARGET_PRECONDITION`. Transform itself verified correct (8/8 unit tests, no LLM) and confirmed to reach the reader (answer text changes) — not an implementation failure.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a future sample specifically screened (still gold-blindly, e.g. by retrieval-score-margin computed from an already-persisted store at $0, without reference to gold) for near-tied-top-score cases where gold is present-but-not-top-1 would be a fairer test of this mechanism's actual precondition. Not scheduled here — per the campaign's "don't tune the same failed action" discipline, no second attempt was made this pass.

---

## Entry J — `SAME_CATEGORY_ENTITY_ENUMERATION` — DROP (regime mismatch, mechanism never fired)

- **MECHANISM:** read-side, deterministic. 22-category-suffix entity template (Airlines, Museum, Hotel, ...); enumerates distinct entities when ≥2 share a category. Zero LLM. Bug found+fixed pre-spend (sentence-initial verb over-capture), reverified against the real historical `gpt4_f420262c` case.
- **REGIME (target, untested at scale):** ≥2 distinct same-category entities co-retrieved. Correlates, on the one known real instance, with wide-breadth retrieval (208 items) — not exercised by this test's `native`/`compact` (~10-item) operating point.
- **FAILURE_TARGETED:** `HARMFUL_SIBLING_DISTRACTION` (Entry C).
- **OBSERVED_EFFECT:** NULL — mechanism fired 0/8 times; inert (byte-identical to BASE) on every unit. Not a false positive, not a false negative, not exercised at all.
- **SOURCE_EXPERIMENTS:** `PM-20260824-fd63ec2d`; [`SAME_CATEGORY_ENTITY_ENUMERATION_V1.md`](SAME_CATEGORY_ENTITY_ENUMERATION_V1.md); `data/lab/arena/sibling-entity-enumeration-v1/{selection.json, results.json}`. Spend $0.574796.
- **EXTERNAL_SUPPORT:** arXiv:2606.10388 ("Right Family, Wrong Skill").
- **CONFIDENCE:** LOW on the mechanism (never exercised) — MEDIUM that its precondition is rare at this project's standard `compact` retrieval breadth specifically (as opposed to rare in general — the one real case occurred at a much wider breadth).
- **KNOWN_COUNTEREXAMPLES:** none observed (nothing fired to be right or wrong about).
- **STATUS:** `DROP (regime mismatch, mechanism never exercised)`.
- **CAMPAIGN-LEVEL LESSON:** two consecutive mechanisms (Entry I, Entry J) now closed as regime-mismatch nulls, both narrow/templated preconditions vs. `RAW_PROVENANCE`'s (Entry H) universal one (Mem0 always compresses). Future candidates should weight precondition commonality heavily, or explicitly test at varied retrieval breadth.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a breadth-varied test (e.g. at the `_3000`/wide operating point, matching the one known real case's actual conditions) would be a fairer test of this mechanism's precondition. Not scheduled here.

---

## Entry K — `RETRIEVAL_RANK_ANNOTATION` — DROP (fired everywhere, net negative)

- **MECHANISM:** read-side, deterministic, unconditional. Every retrieved item annotated `[rank N/M, relevance X.XX]`, always — no threshold gate (direct fix for Entries I/J's regime-mismatch problem).
- **REGIME:** universal — fires on every non-empty retrieval by construction. Confirmed: 8/8 units fired in this test (contrast with Entry J's 0/8).
- **FAILURE_TARGETED:** reader mis-weighting evidence without explicit confidence signal.
- **OBSERVED_EFFECT:** NET NEGATIVE. 8 fresh units: 0 repairs, 1 regression (`06f04340`, a preference-rubric question — `+F`'s answer covers the same substantive content as `BASE` but adds a tangent and a closing hedge ("cannot be fully determined"), judged wrong where `BASE`'s decisive answer was judged correct).
- **SOURCE_EXPERIMENTS:** `PM-20260824-d7372cde`; [`RETRIEVAL_RANK_ANNOTATION_V1.md`](RETRIEVAL_RANK_ANNOTATION_V1.md); `data/lab/arena/retrieval-rank-annotation-v1/{selection.json, results.json}`. Spend $0.581880.
- **EXTERNAL_SUPPORT:** none specific; general motivation from the "confident-but-wrong" family (frontier map #5).
- **CONFIDENCE:** MEDIUM that unconditional rank/score annotation, as minimally rendered here, does not help and carries a mild regression risk — LOW that this generalizes beyond n=8.
- **KNOWN_COUNTEREXAMPLES:** none positive; the one changed case is the regression itself.
- **CROSS-CUTTING PATTERN CONFIRMED:** the regression matches "judge-penalized epistemic caution," already recorded independently in E1's `+SRC` regressions and Stage 2's `031748ae`/`0977f2af` — now observed a third time under an unrelated mechanism. This is now a recurring, cross-mechanism risk of context-annotation interventions in this harness, worth flagging for any future annotation-style mechanism design.
- **STATUS:** `DROP (fired universally, net negative on n=8)`.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** not scheduled — this closes the campaign's mechanism search per STOP condition B (3 consecutive failed families: Entries I, J, K). See `AUTONOMOUS_MEMORY_MECHANISM_CAMPAIGN_V1.md` for the full campaign closure.

---

## Entry Q — `SEMANTIC_ENTROPY_SUFFICIENCY_GATE` — DROP (trigger unreliable + remedy inherits RAW_PROVENANCE's own known limitations)

- **MECHANISM:** read/query-side. Sample the frozen reader M=4 times (temperature=0.7) on the standard compact context; embed locally, greedy-cluster (cosine, threshold 0.85), compute Shannon entropy over cluster proportions. If entropy > 0.5 (round threshold, not tuned to the calibration sample): escalate by appending the raw source session behind Mem0's top-1 hit (`mechanism_ablation.raw_session()`, the same frozen code Entry H uses) to the context. First candidate this campaign sourced from a ResearchOS handoff (`rmc-2026-08-24-001`) rather than AAMR's own discovery-rebuild pool.
- **REGIME (target):** queries where compact retrieval genuinely lacks needed information (absence-type failures) — the regime the underlying black-box semantic-entropy signal (SUGAR, Kuhn et al.) most directly supports.
- **FAILURE_TARGETED:** undetected compact-context insufficiency before answering, as a cost-efficiency gate on `RAW_PROVENANCE`'s unconditional ~21.4x token overhead (Entry H).
- **OBSERVED_EFFECT:** NULL/NEGATIVE-for-the-mechanism. 6 fresh, gold-blind units. BASE 3/6 correct, GATE 3/6 correct — byte-identical judgment on every unit, 0 regressions. Escalation fired selectively (2/6, 33%) but produced 0 traceable repairs. Preregistered success gate required all of: (a) GATE ≥ BASE with 0 unexplained regressions [met], (b) selective firing [met], (c) ≥1 traceable repair among escalated units [NOT met] — `MECHANISM_SEG_FAIL`.
- **SOURCE_EXPERIMENTS:** calibration `PM-20260825-41d5d71e` ($0-cost, reused already-persisted/already-labeled `raw-provenance-fresh-replication-v1` data, separation +0.804 sufficient=0.300 vs insufficient=1.104, 8 units); causal test `PM-20260825-e88248ff`; [`SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md`](SEMANTIC_ENTROPY_SUFFICIENCY_GATE_V1.md); `data/lab/arena/semantic-entropy-sufficiency-calibration-v1/calibration.json`, `data/lab/arena/semantic-entropy-gate-v1/{selection.json,results.json}`. Spend $0.003309 (calibration) + $0.435904 (causal test) = $0.439213. Independently verified via an 8-agent verify→adversarial-refute workflow (`wf_4c4d2a6e-40f`) that checked every interpretive claim against raw JSON, pipeline code, and (2 units) the primary LongMemEval corpus — caught and corrected one misclassification in this test's own first-draft analysis (see below).
- **EXTERNAL_SUPPORT:** Kuhn et al. (Nature 2024, black-box semantic entropy); SUGAR (arXiv 2501.04899, same signal validated for single-turn retrieve-or-not, not persistent-memory compact-vs-raw escalation — the untested transfer this test was designed to check). The ResearchOS candidate itself (`rmc-2026-08-24-001`) explicitly flagged, before any AAMR spend, that AAMR's own failures are dominated by presence-type (gold retrieved, reader still wrong) rather than absence-type failures, and that this signal is not obviously suited to the former — this test measured exactly that risk materializing.
- **CONFIDENCE:** MEDIUM-HIGH that this specific design (entropy trigger + top-1-anchored raw remedy) does not help on this project's actual failure mix — LOW on black-box semantic entropy as a general signal (the calibration's own separation was real and correctly directioned; the trigger produced 1 genuine true positive and 1 clustering-artifact false positive out of 2 firings on n=6, not "no signal at all").
- **KNOWN_COUNTEREXAMPLES:** none positive. Both escalated units remained wrong: `0edc2aef` (clustering artifact trigger on semantically-identical refusals, split by superficial phrasing; separately, a reader reasoning/application failure — an even more explicit combined preference statement was present in the injected raw text and still not applied) and `1de5cff2` (genuine true-positive trigger, but `raw_session()` deterministically pulled Mem0's own wrong rank-1 hit; code/corpus-verified as a compound of retrieval-ranking-miss, absence subtype 2, and assistant-turn-scoping-loss, absence subtype 4 — the Veja fact exists only on an assistant turn that `as_records()` unconditionally drops). One non-escalated wrong unit, `6e984301`, was independently traced to the primary LongMemEval corpus and confirmed as temporal-representation-loss (absence subtype 3, gold requires cross-session date arithmetic neither compact context nor this mechanism's own raw-injection format ever carries) — **not** a "confident hallucination," the characterization this report's own first draft used before adversarial verification corrected it.
- **STATUS:** `DROP (entropy trigger unreliable at n=6 — 1 true positive, 1 clustering artifact — and its remedy inherits RAW_PROVENANCE's own single-hop, top-1-anchored, no-date-stamp limitations; 0/2 traceable repairs, 0 regressions)`. Not `FAIL_ON_REPLICATION_GATE` — this mechanism never cleared an exploratory bar to begin with, unlike Entries N/P.
- **CROSS-CUTTING FINDING:** this is the campaign's 2nd consecutive mechanism-family failure since the post-Entry-P strategy checkpoint (after Entry P/`EXTRACTION_COMPLETENESS_VERIFICATION_PASS`'s own failed replication) — both `consecutive_failed_families_count` increments, still below the 3-consecutive strategy-pivot threshold. Also the first time this campaign's per-unit archaeology was itself independently, adversarially verified end-to-end before being written up, and that process caught a real misclassification (`6e984301`) — a methodological point worth carrying forward: single-pass archaeology, however careful, is not immune to plausible-sounding-but-wrong causal stories, especially for absence-type failures that require primary-source corpus tracing to fully resolve.
- **LAST_UPDATED:** 2026-08-25.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** not scheduled — no second attempt at this exact trigger+remedy design per "don't retune the same failed action." A future attempt would need either a more robust clustering method (e.g. bidirectional NLI entailment rather than embedding-cosine, to avoid the `0edc2aef`-class artifact) or a multi-hop/ranking-aware remedy (rather than top-1-anchored `raw_session()`) to have a materially different chance — neither is scheduled here.

---

*Full mechanistic detail and per-unit transcripts for this update: [`TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md`](TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md), [`analysis.json`](../../data/lab/arena/temporal-alignment-and-distraction-archaeology-v1/analysis.json).*

---

## Entry L — `SECOND_HOP_ASSOCIATIVE_EXPANSION` — DROP (regime confirmed, mechanism doesn't help: semantic drift)

- **MECHANISM:** read-side, one extra free Mem0 `search()` call seeded by the top-1 retrieved item's own text (A-MEM-inspired pseudo-relevance-feedback, adapted to Mem0's flat `search()` — no link graph). Appends the first genuinely-new (not in top-10 by id) hit as `[associated] <text>`, capped at 1. Inert when nothing new is returned. Campaign V2's first candidate: selected via external-discovery-first strategy after a 28-entry candidate pool and top-3 archaeology (see `EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md`); the two higher-ranked candidates were both disqualified pre-spend (one on a false CODE_VERIFIED claim about this project's Mem0 version, one on prior contradicting evidence, one already tested to ceiling).
- **REGIME (target):** cross-session synthesis gaps beyond `RAW_PROVENANCE`'s single-hop reach (`078150f1`-class misses, Entry H).
- **FAILURE_TARGETED:** `RAW_PROVENANCE`'s own documented limitation — it only ever reaches the one session behind Mem0's top-1 hit.
- **OBSERVED_EFFECT:** NULL. 6 fresh, gold-blind units. Mechanism fired (genuinely new item) on 2/6 (33%) — consistent with the $0 precondition check (~25% on a different, already-examined 8-unit set), i.e. **not** a regime-mismatch null like Entries I/J. Net repairs 0, regressions 0. In both fired cases the associated item was topically irrelevant to the query (pulled in for similarity to the top-1 item, not to the question) — on one unit (`1a8a66a6`) this irrelevant addition still visibly perturbed a `temperature=0` reader's answer content/confidence without changing correctness, a new instability data point distinct from the "judge-penalized epistemic caution" pattern (Entries I/J/K).
- **SOURCE_EXPERIMENTS:** `PM-20260824-9dcd4352` (preregistration); [`SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md`](SECOND_HOP_ASSOCIATIVE_EXPANSION_V1.md); `data/lab/arena/second-hop-expansion-v1/{selection.json, results.json}`. Spend $0.414206.
- **EXTERNAL_SUPPORT:** A-MEM (agiresearch/A-mem, NeurIPS 2025) link-expansion pattern; CODE_VERIFIED via repo inspection during Campaign V2 discovery, REPO_ARTIFACT not directly transplanted (this project has no link graph, so the query itself was adapted to seed via Mem0's existing `search()`).
- **CONFIDENCE:** MEDIUM that seeding hop-2 by top-1's text (rather than by the original query) is a structural mismatch for this task — HIGH that this specific n=6 sample showed no benefit.
- **KNOWN_COUNTEREXAMPLES:** none positive; both fired cases returned irrelevant associated content.
- **STATUS:** `DROP (regime confirmed, mechanism doesn't help — semantic drift from seeding by top-1 text instead of by query)`.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a query-seeded (rather than top-1-seeded) second hop would directly test whether the drift is the actual cause — not scheduled here per "don't retune the same failed action" discipline. **CAMPAIGN V2 LESSON:** external-discovery-first correctly avoided a near-zero-fire-rate regime mismatch (this candidate's precondition really does fire at a moderate, non-trivial rate) but did not avoid mechanism-level failure — external evidence de-risks precondition existence, not causal efficacy in this harness. This is failure 1 of 3 toward Campaign V2's strategy-pivot STOP threshold (not a global stop).

---

## Entry M — `HYDE_QUERY_REFORMULATION` — DROP (precondition confirmed real, this sample drew the wrong absence subtype)

- **MECHANISM:** read/query-side, one extra small `temperature=0` LLM call generates a short hypothetical memory-note; Mem0 `search()` uses that hypothetical text in place of the literal question (pure HyDE, Gao et al. ACL 2023, no blend). Selected via a fresh $0 diagnostic (not the next-ranked pool entry): a tally of all 11 project-wide `BASE`-wrong units found 9/11 (82%) were retrieval-absence failures, meaning the whole verification/repair-against-same-context tier (`CHAIN_OF_VERIFICATION_FACTORED`, `PARAPHRASE_SELF_CONSISTENCY`, `VERBALIZED_CONFIDENCE_GATED_REPAIR`, `TARGETED_EVIDENCE_REPAIR`, `EVIDENCE_TAGGED_CITATION`) has almost no precondition to fire against in this project's actual failure mix. A $0 full-store dump + hand-written-hypothetical re-query on 2 already-known absence units confirmed a large, real precondition effect (absent → rank 1, 2/2).
- **REGIME (confirmed real, but undersampled here):** a fact present somewhere in Mem0's full store but outside the top-10 the literal question's embedding surfaces, recoverable by a better-phrased query.
- **FAILURE_TARGETED:** query/fact phrasing mismatch — LongMemEval's own construction methodology (arXiv:2410.10813, A.1) deliberately builds evidence sessions to convey facts indirectly, not in the question's own words.
- **OBSERVED_EFFECT:** NULL on 6 fresh, gold-blind units (1/category). The mechanism fired (top-10 changed) on 6/6, but the 2 `BASE`-wrong units in this draw were both a *different* absence subtype (write-time extraction loss — the fact was never separately stored, in either query variant) than the subtype this candidate's own $0 check confirmed it could fix. 0 repairs, 0 regressions. No sign of the flagged hallucination-guided-retrieval-drift risk (reformed queries stayed topically on-target and never destabilized an already-correct answer).
- **SOURCE_EXPERIMENTS:** `PM-20260824-294f9581` (preregistration); [`HYDE_QUERY_REFORMULATION_V1.md`](HYDE_QUERY_REFORMULATION_V1.md); `data/lab/arena/hyde-query-reformulation-v1/{selection.json, results.json}`. Spend $0.437383.
- **EXTERNAL_SUPPORT:** HyDE (Gao et al., ACL 2023, arXiv:2212.10496); LongMemEval's own primary-source construction methodology (arXiv:2410.10813).
- **CONFIDENCE:** MEDIUM-HIGH that the confirmed precondition (present-in-store, ranking-miss) is real in this project — LOW that a typical 6-unit exploratory draw will happen to contain it, since project-wide tallying puts it at roughly 2 of 13 (~15%) of all observed failures, smaller than the write-time-extraction-loss and temporal-representation-loss subtypes.
- **KNOWN_COUNTEREXAMPLES:** none positive within this sample; both fired-and-still-wrong cases were the wrong absence subtype for this mechanism to fix.
- **STATUS:** `DROP (precondition confirmed real elsewhere, this sample's 2 failures were a different, un-fixable-by-this-mechanism absence subtype)`.
- **CROSS-CUTTING FINDING:** this test's own selection diagnostic and archaeology jointly establish a first taxonomy of this project's retrieval-absence failures — (1) write-time extraction loss, (2) retrieval-ranking miss (this candidate's target), (3) temporal-representation loss (a session-relative expression never resolved to an absolute date). Subtype (3) is now the single largest identified cluster project-wide (4/13 `BASE`-wrong units: `0db4c65d`, `2ebe6c90`, `2ebe6c92`, `4dfccbf7`), and is the exact target of the already-twice-attempted `TEMPORAL_ANCHOR_AT_CONTEXT` (Entries A/B).
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a larger sample, or one specifically pre-screened at $0 (via `memory.get_all()` full-store dumps, gold-blind) for units where the missing fact is confirmed present-but-unranked, would give this candidate a fairer test of its actual confirmed precondition. Not scheduled here per "don't retune the same failed action" discipline — Campaign V2 instead pivots to the higher-priority subtype (3) finding below.

---

## Entry N — `TEMPORAL_ANCHOR_AT_CONTEXT` × `TEMPORAL_BOUNDARY` (narrow confirmatory replication) — `FAIL` on gate, third consecutive clean/non-negative sample

- **MECHANISM:** `TEMPORAL_ANCHOR_AT_CONTEXT` (Entry A), tested via a dedicated, gold-blind selection restricted to the `TEMPORAL_BOUNDARY` sub-regime only — a fixed regex classifier (`is_temporal_boundary()`, question text only) matching duration/arithmetic-between-two-events questions, structurally excluding the many-item filter/count shape behind Entry B's one regression.
- **REGIME:** `TEMPORAL_BOUNDARY` as classified by question shape — the narrower regime Stage 2's own report (Entry A/B) flagged as the natural next confirmatory target.
- **FAILURE_TARGETED:** same as Entry A — reader unable to date-arithmetic facts whose only anchor is an unrendered session timestamp.
- **OBSERVED_EFFECT:** NULL. 8 fresh, gold-blind units, all `TEMPORAL_BOUNDARY`-classified. `+TIME` byte-for-byte judgment-identical to `BASE` on 8/8 — 0 repairs, 0 regressions. Both `BASE`-wrong units were retrieval-absence failures (the needed dated pair, or the needed session entirely, was never retrieved into the top-10) rather than "dates present but unrendered" — the specific gap `+TIME` targets. One unit (`bbf86515`) structurally exhibited the exact `SESSION_EVENT_DIVERGENT` pattern behind Entry B's regression (all 10 retrieved items shared one recap-session's date, diverging from at least one item's own in-text date) but caused **no new harm**, since the unit was already unanswerable from a total retrieval miss regardless of date rendering.
- **SOURCE_EXPERIMENTS:** `PM-20260824-717e8277` (preregistration); [`TEMPORAL_ANCHOR_BOUNDARY_V3.md`](TEMPORAL_ANCHOR_BOUNDARY_V3.md); `data/lab/arena/temporal-anchor-boundary-v3/{selection.json, results.json}`. Spend $0.559315.
- **EXTERNAL_SUPPORT:** none new; this is AAMR-internal evidence, ranked above external literature per this project's own evidence hierarchy.
- **CONFIDENCE:** MEDIUM-HIGH that this mechanism is *safe* within its stated regime — three independent AAMR samples now (E1, Stage 2's `TEMPORAL_BOUNDARY` bucket, this test) show zero regressions when the regime classifier correctly applies. LOW-MEDIUM on *efficacy at typical exploratory sample sizes* — genuine "dates present but unrendered" repair opportunities have so far only appeared in Stage 2's original 2-unit bucket, not in this fresh 8-unit draw.
- **KNOWN_COUNTEREXAMPLES:** none negative; `bbf86515`'s structural divergent-anchor recurrence caused no measurable harm this time, which is reassuring but an n of 1 (swamped by an unrelated total retrieval miss, so not a clean test of whether the trap itself is now harmless or just didn't get the chance to bite).
- **STATUS:** `FAIL_ON_REPLICATION_GATE (0 repairs, required ≥2) — mechanism remains SUPPORTED/qualified (Entry A), not elevated to REPLICATED_VALIDATED_TRANSPLANT, not weakened`.
- **CROSS-CUTTING FINDING:** both `BASE`-wrong units in this sample were retrieval-absence, the same subtype-mismatch pattern seen in Entry M (`HYDE_QUERY_REFORMULATION`) — a third consecutive Campaign V2 mechanism whose designed target (a real, project-confirmed failure subtype) simply didn't co-occur often enough with `BASE`-wrong outcomes in an 6-8-unit gold-blind draw to produce a repair. This suggests exploratory-test sample sizes in the 6-8 range may be systematically underpowered for any mechanism whose target failure subtype is a *minority* share of this project's overall failure mix, even when that subtype is real and confirmed.
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none (updates, does not replace, Entry A's `NEXT_TRIGGER`). **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a larger-n or pre-screened (at $0, gold-blind, e.g. selecting only fresh units where a $0 precondition check confirms a genuine unrendered-but-needed date pair exists) test would give this mechanism a fairer shot at clearing the replication bar. Not scheduled here — Campaign V2's 3rd consecutive mechanism-family failure (G, H, I) triggers the contract's strategy-pivot condition: return to external discovery to rebuild the candidate pool, rather than a fourth ad hoc pick.

---

## Entry O — `EXTRACTION_COMPLETENESS_VERIFICATION_PASS` — `EXPLORATORY_SUPPORTED`, first write-side mechanism, first Campaign V2 success

- **MECHANISM:** write-side vendor patch (`external/venvs/mem0/Lib/site-packages/mem0/memory/{utils.py,main.py}`). One additional LLM call after Mem0's normal extraction re-reads the session against already-extracted facts, returning `facts_to_add` (missing entirely) and `facts_to_replace` (a bundled fact split into individual items). Selected from the discovery-rebuild pool (v3, `EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md`) after Campaign V2's 3-consecutive-failure strategy pivot (G, H, I); the first candidate this campaign to target write-time extraction loss (absence subtype 1) directly rather than operating read-side on already-retrieved compact content.
- **REGIME:** sessions containing an enumerable list (numbered, comma/and-separated) that Mem0's own extraction prompt bundles into one fact string, when the individual items matter to the question.
- **FAILURE_TARGETED:** write-time extraction loss — CODE_VERIFIED that `USER_MEMORY_EXTRACTION_PROMPT`'s own shipped few-shot example teaches merging (two favorite movies → one fact string).
- **OBSERVED_EFFECT:** POSITIVE (exploratory). 6 fresh, gold-blind units (n reduced from preregistered 8 after the arena's own cost cap stopped mid-ingest — disclosed, see `EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1.md`). 1 genuine, transcript-traceable repair (`09d032c9`: a power-bank fact bundled inside an unrelated travel-organizing frame is split out and the reader correctly grounds a battery-tip answer in it) — 1 apparent second "repair" (`4dfccbf8`) is judge-noise, not a mechanism effect (both arms' answers are substantively identical, correctly citing the same unchanged fact). 0 regressions across all 6 units, including 3 already-correct units where the mechanism still fired (added/split content) without destabilizing anything.
- **SOURCE_EXPERIMENTS:** calibration `PM-20260824-f8d5e89c` → `PM-20260824-9d020373` (passed, 4/4 list cases split after one mid-calibration prompt revision, 0 fabrication); full test `PM-20260824-195a1656`; [`EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1.md`](EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1.md); `data/lab/arena/extraction-completeness-verification-v1/{selection.json, results.json, vendor-patch/manifest.json}`. Spend $1.198483 (ingest-dominated: dual BASE/+J banks per unit, plus one completeness-check call per session for +J).
- **EXTERNAL_SUPPORT:** ProMem, measured directly on LongMemEval with an ablation isolating this exact completeness-check stage (removing it drops HaluMem integrity 73.80%→60.33%).
- **CONFIDENCE:** MEDIUM — one clean, transcript-traceable repair with 0 regressions is a real positive signal, but n=1 genuine repair on a reduced n=6 sample is not yet replication-grade evidence.
- **KNOWN_COUNTEREXAMPLES:** none negative (0 regressions); one nominal "repair" reclassified as judge noise on close reading, not glossed over.
- **STATUS:** `EXPLORATORY_SUPPORTED` — first Campaign V2 mechanism to clear its exploratory gate. NOT yet `REPLICATED_VALIDATED_TRANSPLANT`. **UPDATE (Entry P):** the fresh replication this note called for has now been run (8 fresh units) — 0/0 net repairs/regressions, `MECHANISM_J_REPLICATION_FAILED` on the replication gate. Status remains `EXPLORATORY_SUPPORTED`, not elevated, not dropped (0 regressions across both samples, 14 units total). See Entry P for full detail.
- **ADDITIONAL FINDING (harness bug, fixed):** a stray system-wide `brotli.py` shadows the pinned Mem0 venv's own brotli decoder, crashing `httpx2` response decoding whenever DeepSeek's server brotli-encodes a response (`TypeError: process() takes no keyword arguments`) — ambient, pre-existing, unrelated to this mechanism, only now triggered by chance. Fixed by forcing `Accept-Encoding: gzip, deflate` via `default_headers` on the `OpenAI` client construction. Worth carrying into any future script using this same client pattern.
- **LAST_UPDATED:** 2026-08-25.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a fresh, gold-blind 8-unit replication on new units, specifically checking whether the genuine-repair rate (currently 1/6) replicates and whether the judge-noise pattern recurs. Now run — see Entry P.

---

## Entry P — `EXTRACTION_COMPLETENESS_VERIFICATION_PASS` — fresh replication `FAILED` on gate, regime-rarity result

- **MECHANISM:** `EXTRACTION_COMPLETENESS_VERIFICATION_PASS` (Entry O), tested via a second, fresh, gold-blind 8-unit sample, identical vendor patch and methodology, both operational fixes learned from v1 (cost-cap sizing, brotli decoder fix) applied proactively.
- **REGIME:** same as Entry O — sessions with an enumerable list Mem0's own extraction bundles into one fact, where the individual items matter to the question.
- **FAILURE_TARGETED:** same as Entry O.
- **OBSERVED_EFFECT:** NULL. 8 fresh, gold-blind units, ran cleanly to completion (no cap interruption, no decoder errors — both v1 operational issues did not recur). 0 net repairs, 0 regressions — `+J` judgment-identical to `BASE` on all 8 units, despite the mechanism visibly firing (context differs) on every one. The 4 `BASE`-wrong units spread across three *different* absence subtypes this mechanism was never designed to fix: temporal-representation-loss (`5e1b23de`), knowledge-update/supersession — the already-`DROP`ped `CURRENT_STATE_OVER_HISTORY` domain (`2133c1b5`), and assistant-turn-scoping-loss (`1d4da289`, the 5th independently-observed case of this root cause project-wide) — plus one case of pure irrelevant context churn with zero effect (`0a34ad58`).
- **SOURCE_EXPERIMENTS:** `PM-20260824-df787f9d` (preregistration); [`EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V2.md`](EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V2.md); `data/lab/arena/extraction-completeness-verification-v2/{selection.json, results.json}`. Spend $1.338754.
- **EXTERNAL_SUPPORT:** none new — same ProMem support as Entry O.
- **CONFIDENCE:** MEDIUM-HIGH that the mechanism's underlying split-detection logic is safe (0 regressions across 14 units, two independent samples) — LOW-MEDIUM on its practical repair rate, now estimated at roughly 1/14 (~7%) fresh gold-blind units showing the actual target precondition (bundled content the question needs) across both samples combined.
- **KNOWN_COUNTEREXAMPLES:** none negative; all 4 non-repairs are well-explained by a different, already-documented absence subtype apiece, not by any flaw in this mechanism's own logic.
- **STATUS:** `FAIL_ON_REPLICATION_GATE (0 repairs, required ≥1) — mechanism remains EXPLORATORY_SUPPORTED (Entry O), not elevated to REPLICATED_VALIDATED_TRANSPLANT, not dropped`.
- **CROSS-CUTTING FINDING:** this is now the *fourth* time this campaign (after Entries M, N) that a mechanism with a real, confirmed-real target precondition failed to replicate simply because a fresh gold-blind draw's failures landed on a *different* absence subtype than the one being tested. AAMR's failure mix appears to be a genuine patchwork of several distinct, individually-rare subtypes (write-time bundling, retrieval-ranking-miss, temporal-representation-loss, knowledge-update/supersession, assistant-turn-scoping-loss) rather than one dominant pattern any single 6-8-unit mechanism test can reliably land on — a structural reason to expect narrow single-mechanism campaigns at this sample size to show null replications more often than not, independent of mechanism quality.
- **LAST_UPDATED:** 2026-08-25.
- **SUPERSEDES:** none (updates, does not replace, Entry O's `NEXT_TRIGGER`). **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a larger-n or subtype-pre-screened (gold-blind, structural — not content/gold-based) sample specifically enriched for bundled-enumeration questions would give this mechanism a fairer shot at a clean replication. Not scheduled here per "don't retune the same failed action" discipline.

---

## Entry R — version scope, wording and counts (addendum to Entries A–Q, recorded 2026-11-01)

Added after the entries above; nothing above has been edited. This entry corrects what a reader could infer from them and records one open risk.

- **VERSIONS_MEASURED:** every measurement in Entries A–Q was taken with `mem0ai` 1.0.6 (`external/venvs/mem0`) and Hindsight packaged as `hindsight_api_slim` 0.9.1 (`external/venvs/hindsight`). On 2026-11-01 upstream is Mem0 2.2.1 and Hindsight 1.1.0. No entry has been re-run on either.
- **WHY_THAT_MATTERS (UNTESTED):** Mem0 v2.0.0 (2026-04-16) replaced the add/update/delete extraction with a single-pass, ADD-only extraction, introduced multi-signal hybrid retrieval (semantic + BM25 + entity matching), and, in its own release notes, captures agent-generated facts "for the first time". Entry G's DROP is explicitly about Mem0 1.0.6's write-time reconciliation, which no longer exists in that form. The three failure modes named in request `arr-2026-08-25-001` (assistant-turn representation loss, retrieval-anchor failure, temporal representation loss) may therefore be partly artefacts of the legacy versions. This has not been checked, and no entry should be read as a statement about current Mem0 or Hindsight.
- **ENTRY_H_WORDING:** the evidence behind `REPLICATED_VALIDATED_TRANSPLANT` is 2 repairs and 0 regressions in 17 observable units, on Mem0 1.0.6. That label is this campaign's own procedural ladder term, not a statistical claim; an exact two-sided sign test on 2 repairs against 0 regressions gives p = 0.5. Two qualifications. (1) The replication's repair (`0e5e2d1a`) is a `single-session-assistant` question whose evidence sits in an assistant turn that `as_records()` deliberately discards from the compact context, so it shows a harness design effect more than anything about extraction (the root cause counted in Entries P and Q as assistant-turn-scoping-loss). The E3 repair (`6a27ffc2`) is a competing-facts case whose dependence on the legacy version is untested. (2) In the replication the raw arm carries roughly 16–32 times the context of the compact arm (89–128 tokens against 2,045–3,339; the one exception, `0e5e2d1a`, is 109 against 609), and `raw_only` is not a length-matched control. Recommended public wording: *a small positive signal (2 repairs in 17 units, 0 regressions, Mem0 1.0.6)*.
- **COUNT_CORRECTION:** this ledger has 17 entries, A–Q (Q sits physically before L). The request text and the V3 budget ledger's gating condition say "16 entries"; they are frozen, so this note is the correction.
- **UPSTREAM_DATA_DEFECTS:** public LongMemEval issues report gold-label defects for several question ids. One of them, `370a8ff4`, was a unit in Entry L's sample (both arms wrong, mechanism did not fire, verdict unchanged). See [`LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md`](LONGMEMEVAL_KNOWN_GOLD_DEFECTS.md), and recompute any temporal-accuracy claim with and without the listed ids.
- **NEXT_TRIGGER:** a re-baseline of the frozen units on current Mem0 (and Hindsight), before any candidate for `arr-2026-08-25-001` is tested and before any new spend. It needs a preregistration first; this entry authorises no spend.
- **LAST_UPDATED:** 2026-11-01.
- **SUPERSEDES:** none. **SUPERSEDED_BY:** none.
