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

## Backlog (not run, not authorized here)

### `ZERO_ANSWER_DISPERSION_DIAGNOSTIC` (frontier H2)

- **STATUS:** `CHEAP_FOLLOWUP, NOT_RUN`.
- **WHAT_IT_WOULD_TEST:** whether a stable failure mode (vs. reader/judge noise) can be distinguished by dispersion of answers across repeated reads on ambiguous units — relevant to `H0` (noise) in this archaeology's competing-explanations analysis.
- **TRIGGER_CONDITION:** only if a future $0 archaeology pass cannot distinguish stable failure from reader noise on a specific probe using existing frozen data alone.
- **ESTIMATED_COST:** ~$0.01–0.02.
- **SOURCE:** [`GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`](GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md) (external reference, arXiv:2606.22728).

---

*Full mechanistic detail and per-unit transcripts for this update: [`TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md`](TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md), [`analysis.json`](../../data/lab/arena/temporal-alignment-and-distraction-archaeology-v1/analysis.json).*
