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
- **STATUS:** `TEMPORAL_ANCHOR_SUPPORTED` (exploratory, E1) `QUALIFIED_BY` Stage 2 fresh replication — narrowed from "ordering questions in general" to "bounded lookups/arithmetic over explicitly-or-well-anchored named events."
- **LAST_UPDATED:** 2026-08-24.
- **SUPERSEDES:** none.
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a further replication specifically targeting `TEMPORAL_BOUNDARY`-shaped (bounded lookup/arithmetic) questions, gold-blind selected, would sharpen this regime boundary further. Not authorized or scheduled by this document.

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
