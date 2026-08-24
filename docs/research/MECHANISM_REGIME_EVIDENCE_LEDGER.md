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
- **SUPERSEDED_BY:** none.
- **NEXT_TRIGGER:** a future turn separately authorizing the actual `MECHANISM_B_STATE_SUPERSESSION_V1` run (12 probes, BASE vs +B, projected ≈$0.15–0.25, recommended cap $0.30). Not authorized by this entry.

---

## Backlog (not run, not authorized here)

### `ZERO_ANSWER_DISPERSION_DIAGNOSTIC` (frontier H2)

- **STATUS:** `CHEAP_FOLLOWUP, NOT_RUN`.
- **WHAT_IT_WOULD_TEST:** whether a stable failure mode (vs. reader/judge noise) can be distinguished by dispersion of answers across repeated reads on ambiguous units — relevant to `H0` (noise) in this archaeology's competing-explanations analysis.
- **TRIGGER_CONDITION:** only if a future $0 archaeology pass cannot distinguish stable failure from reader noise on a specific probe using existing frozen data alone.
- **ESTIMATED_COST:** ~$0.01–0.02.
- **SOURCE:** [`GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`](GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md) (external reference, arXiv:2606.22728).

---

*Full mechanistic detail and per-unit transcripts for this update: [`TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md`](TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md), [`analysis.json`](../../data/lab/arena/temporal-alignment-and-distraction-archaeology-v1/analysis.json).*
