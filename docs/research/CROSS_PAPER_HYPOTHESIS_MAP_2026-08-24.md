> **Publication note, 2026-11-12.** Written on 2026-08-24 and kept in one local working tree until this date; other
> documents and project-memory records cited it while it was unpublished. Everything below this note is the unedited
> original (SHA-256 of the original file: `033bc4345824fe9ee7f169f1a7a21a1687ebd80a8e8cecd2de2b8a6823087592`). It is a planning record, not a result. Where it and
> [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) disagree, the ledger wins. All arena numbers
> are on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1, with 4 to 10 questions per test.
>
> What happened next: H5 (harmful-sibling check) is ledger Entry C, an observed case on one example; H3 (authority
> collapse) is Entry D, not testable yet; H2 (zero-answer-dispersion diagnostic) is in the ledger backlog and was not
> run; H1 and H4 were wording and analysis refinements for experiments recorded in Entries A, B and H.

# Cross-Paper Hypothesis Map — 2026-08-24

Source of truth for AAMR's current state: `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md` and `HINDSIGHT_INFORMATION_COMPOSITION_ARCHAEOLOGY_V1.md`, both read *after* `GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md` was finished, per the requested ordering. **The roadmap is current and has already superseded a great deal of what earlier research documents in this repository said** — most importantly, cross-unit contamination invalidated the old `RAW_PROVENANCE_EXPANSION → DROP` and `BROAD_CONTEXT_EXPANSION → PROMOTE` decisions, and clean data now shows Mem0's own breadth curve is flat-then-down (5/10 → 6/10 → 6/10 → 5/10), not climbing. This document does not repeat that invalidation work; it takes the roadmap's Section 2 ledger and Section 6–8 candidate board as ground truth and asks what the external frontier adds to it.

**Direct consequence for a document I wrote earlier today:** `MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md`'s "$1 pick" (Mem0 breadth expansion) was exactly the experiment that has since been run cleanly and come back null. That is the system working as intended — a cheap, well-specified, falsifiable recommendation was tested and killed quickly — not a failure of that analysis. Its TierMem-reconciliation framework is explicitly kept by the roadmap ("remain the right analysis frame, but the empirical anchor must be re-bought") — the *method* survives, the *specific numbers* it was anchored to do not.

Labels follow the roadmap's own convention: **AAMR_MEASURED / AAMR_INVALIDATED / EXTERNAL_MEASURED / CODE_VERIFIED / PAPER_CLAIM / INFERENCE / HYPOTHESIS / UNRESOLVED.**

---

## External frontier vs. AAMR's current roadmap

| External mechanism family | Classification | Reasoning |
|---|---|---|
| State/supersession tracking (StateMemBench, STALE, TOKI) | **COMPLEMENTARY** | AAMR's C1 (temporal anchor at context) is a narrower, already-in-flight instance of this broader family. StateMemBench's Trace→Resolve wrapper pattern is a more general template C1 could grow toward *after* E1 validates the basic idea — not a reason to change E1 now. |
| Consolidation failure / episodic-vs-abstraction (Useful Memories Become Faulty, SUMER) | **VALIDATES AAMR'S ARCHITECTURE, FUTURE-SCALE FOR THE ARENA** | Independently confirms AAMR's own README bet (separate episodic/semantic stores) via Complementary Learning Systems theory. Not actionable in the current 3 experiments — AAMR's stores are 200–600 items, explicitly below the regime where Tree/SP-style consolidation is judged likely to pay (roadmap §14), and no consolidation mechanism exists in the arena yet. |
| Authority/provenance collapse at consolidation (When Memory Becomes Authority) | **NEW CANDIDATE, FUTURE-SCALE** | Directly relevant the day AAMR builds any consolidation step — and AAMR's typed schema (`claim_class`, `source_refs`, bitemporal fields) is a plausible defense worth testing against this paper's own protocol. Does not apply to E1/E2/E3, which are read/write-side representation fixes, not consolidation. See H3 below. |
| Execution-state/dependency-structure memory (MAGE, ContextWeaver, GRADE) | **ONLY FUTURE-SCALE RELEVANT** | Targets state fragmentation across *actions* in agentic/tool-use tasks. AAMR's current arena is conversational QA (LongMemEval-S); there is no execution trace to fragment. Relevant only if AAMR's Phase D expands to an agentic benchmark. |
| Retrieval-utilization gap / confident-but-wrong (zero answer dispersion, HippoRAG scale decay) | **COMPLEMENTARY — new diagnostic lens, no roadmap change** | Adds a checkable property (does a failure look "coherent"/locked-in vs. noisy) to AAMR's existing gold-rank/gold-in-context vocabulary, without contradicting it. See H2. |
| Multi-agent shared-memory concurrency | **ONLY FUTURE-SCALE RELEVANT** | AAMR's arena is single-agent throughout. Worth knowing the literature exists (thinner than expected, real code+numbers) for when/if this becomes relevant, not before. |
| Memory poisoning / provenance-defense failure | **ONLY FUTURE-SCALE RELEVANT for the arena; worth a standing note for AAMR's own tooling** | Not applicable to a 10-unit frozen LongMemEval-S sample with no adversarial content. Tangentially relevant to AAMR's own append-only project-memory system, which does accept `memory_add` input — a governance question, not an arena experiment. |
| Skill/procedural memory transfer risk (Right Family Wrong Skill, AFTER) | **NEW CANDIDATE for AAMR's untested "procedural" store; diagnostic idea usable now at $0** | AAMR's README names a procedural store as an untested hypothesis with zero current coverage (confirmed by an earlier frontier-map grep). The *harmful-sibling-rate* metric this literature uses, though, can be repurposed as a free diagnostic on AAMR's existing **fact** retrieval today — see H5. |
| Graph-memory structural vulnerabilities (ShadowMerge, GraphRAG underperformance) | **ONLY FUTURE-SCALE RELEVANT** | AAMR's current candidate board has no graph-structured mechanism in play (Tree/SP and entity resolution are both explicitly off the board, per roadmap §14). Worth remembering before any future graph-memory transplant, not actionable now. |
| Learned admission/deletion policies (A-MAC, Control-Plane Placement) | **COMPLEMENTARY to AAMR's own future-utility research question, FUTURE-SCALE for the arena** | AAMR's README research question 3 (future utility) and F (retention) already point this direction; the arena's current 3 experiments are read/write-side representation, not admission/deletion. No change to E1–E3. |
| GRAVITY (already known) | **ALREADY COVERED, roadmap's reading is more precise than the original frontier-map pass** | The roadmap independently reached the same retargeting conclusion an earlier synthesis did (Event/Temporal anchors > Entity anchors for Mem0 specifically, since Mem0 already has its own entity store but no temporal structure) — convergent, not new. |
| TierMem (already known) | **ALREADY COVERED, directly informs E3** | The roadmap's own H1–H4 (§4) already extract the relevant differentiating variables. No new angle added here beyond H4 below. |
| Active reconstruction at retrieval time (Memory-is-Reconstructed, MemHarness, NapMem) | **COMPLEMENTARY, conceptual only** | Bears on how to *frame* C1 (is rendering a timestamp "reconstruction" or plain representation?) without changing its design or cost. Not a roadmap action. |
| MemIR — typed evidence/cue/claim memory, "provenance-role collapse" | **NEW CANDIDATE, sharpens an already-planned experiment at $0 marginal cost** | See H1. |

**Bottom line of this comparison: nothing found clears the bar for jumping ahead of E1.** E1 is cheap ($0.02–0.05), has registered predictions, targets AAMR's own best-supported mechanism (temporal representation), and nothing in the external frontier offers stronger evidence, better fit, lower cost, or a more concrete decision than what E1 already delivers. What the frontier *does* offer: two free-to-cheap enhancements that fold into the currently-planned stages (H1, H2), one free analytical refinement to E3 (H4), one free new diagnostic lens usable today (H5), and one well-justified future candidate explicitly flagged as not-yet-actionable (H3).

---

## Missing-cells matrix

Mechanism (rows) × AAMR's own data-driven failure taxonomy (columns: TEMPORAL_COMPOSITION, SUBJECT_ATTRIBUTION, SCATTERED_AGGREGATION, UPSTREAM_CAPTURE_GAP, GOLD_PRESENT_READER_WRONG-generic). `✓ tested` / `— not applicable` / `**MISSING**` = genuinely open cell.

| Mechanism | TEMPORAL_COMPOSITION | SUBJECT_ATTRIBUTION | SCATTERED_AGGREGATION | UPSTREAM_CAPTURE_GAP | Generic confident-wrong |
|---|---|---|---|---|---|
| Temporal anchor at context (C1) | ✓ E1 planned | — | — | — | — |
| Source/subject tag (C2) | — | ✓ E1 planned (single-probe evidence so far) | — | — | — |
| C1+C2 combined | **gated cell inside E1**, registered prediction on `ba358f49` | (same cell) | — | — | — |
| Raw provenance / verbatim supplement (C4) | — | — | — | ✓ E3 planned (H1 in roadmap) — but only single-hop | — |
| Multi-hop provenance extension | — | — | — | **MISSING** — roadmap's own H3, explicitly deferred | — |
| Zero-answer-dispersion diagnostic | — | — | — | — | **MISSING** — H2 below, $0.01–0.02, no roadmap entry yet |
| Harmful-sibling / distraction check | — | — | — | — | **MISSING** — H5 below, $0, no roadmap entry yet |
| MemIR-style role typing | — | **MISSING but folds into C2** — H1 below | — | — | — |
| Authority-collapse-safe consolidation | — | — | — | — | **MISSING, but no consolidation mechanism exists to test it against yet** |
| Query-conditioned reranking (C5) | — | — | ✓ deliberately off-board (F7: gold rank already 1, no truncation at 3000) | — | — |
| Redundancy preservation (C7) | — | — | ✓ deliberately off-board (failed anti-storytelling check) | — | — |

Two genuinely new, cheap, currently-open cells fall out of this table: the **zero-answer-dispersion diagnostic** and the **harmful-sibling/distraction check**, neither previously in AAMR's own candidate board, both runnable at near-zero cost on data AAMR already has.

---

## Cross-paper connection hypotheses

### H1 — MemIR's "provenance-role collapse" sharpens C2's tag wording

**SOURCE A (external, PAPER_CLAIM):** MemIR (arXiv:2605.25869) separates memory into typed atoms — raw evidence, retrieval cues, truth-bearing claims — specifically to prevent "provenance-role collapse": source-monitoring errors where an agent confuses *who said something* or *what evidence backs a claim*, because unstructured flat text conflates evidence/cue/claim into one blob.

**SOURCE B (AAMR, from the roadmap's own §10 Pair 1 risk analysis, AAMR_MEASURED/INFERENCE mix):** the roadmap already anticipated, independently of knowing MemIR exists, that C2's naive tag design has a specific failure mode: *"'Friend Rachel is getting married' is about Rachel, sourced from user — tag wording must say 'from user's message,' not 'about user.'"*

**UNOBSERVED CONNECTION:** AAMR's C2 and MemIR's typed-atom design are solving the identical problem (provenance-role collapse) at different granularities — one tag per item vs. a full evidence/cue/claim type system. Nobody has checked whether AAMR's planned single-tag version is sufficient, or whether it needs MemIR's sharper about-vs-from distinction to actually avoid the collapse the roadmap itself worried about.

**PROPOSED MECHANISM:** within E1's already-planned `+SRC` arm, use MemIR's explicit about-vs-from distinction as the tag vocabulary, rather than an ad hoc scheme — directly closes the gap the roadmap flagged as a risk, before it becomes an observed failure.

**EXPECTED REGIME:** third-party-attribution probes specifically (`ba358f49`-shaped).

**EXPECTED FAILURE:** no benefit if `ba358f49`'s actual reader error doesn't involve about-vs-from confusion at all — worth a transcript check before spending the tag-wording effort.

**MINIMAL TEST:** a wording choice inside E1's existing `+SRC` arm — no new experiment, no new spend.

**FALSIFICATION:** E1's `+SRC` arm fails to flip `ba358f49` even with the sharper wording — would suggest the tag *mechanism* itself, not its wording, is the limiting factor.

**COST: $0 marginal.**

---

### H2 — Zero-answer-dispersion diagnostic on AAMR's own known failures

**SOURCE A (external, MEASURED by the source paper):** "When Confidence Takes the Wrong Path" (arXiv:2606.22728) — across six QA snapshots, 42–59% of RAG errors show *zero answer dispersion* across five resampled attempts: self-consistency-based confidence estimation is structurally blind to these, because retrieval failed "coherently" (all samples agree on the same wrong answer), not noisily.

**SOURCE B (AAMR, AAMR_MEASURED):** group A's two clean failures (`gpt4_f420262c`, `gpt4_59c863d7`) were each judged from a single generation at temperature 0 — the roadmap's own uncertainty #2 already flags that "every arm × unit is one generation... a random flip elsewhere does not count as success" without having tested whether these *specific* failures are stable or noisy.

**UNOBSERVED CONNECTION:** nobody has checked whether AAMR's own group-A failures show the "coherent lock-in" signature (2606.22728's pattern) or genuine reasoning noise. This is a free, orthogonal diagnostic AAMR's own instrumentation already supports (the frozen contexts exist; only new reader calls are needed).

**PROPOSED MECHANISM:** not a mechanism — a diagnostic. If AAMR's group-A failures show near-zero dispersion, that is independent, convergent support for the representation-fix framing E1 is built on (a stable answer determined by a stable, incomplete representation is exactly what adding a missing anchor should be able to move). If dispersion is high, that would argue for prioritizing the roadmap's own already-flagged second-reader replication (uncertainty #4) sooner, since reader variance would then be a larger factor than currently assumed.

**MINIMAL TEST:** resample the reader 3–5× at temperature > 0 on the frozen contexts for `gpt4_f420262c` and `gpt4_59c863d7` (and, for contrast, one or two group-C probes) — zero new ingest, zero new retrieval, uses artifacts already on disk.

**FALSIFICATION:** high answer variance across resamples would weaken (not disprove) the "coherent representation gap" framing.

**COST: ~10–25 extra reader calls, roughly $0.01–0.02 — fits inside or alongside E1's own $0.10 cap.**

---

### H3 — Authority-collapse-safe design principle for AAMR's eventual consolidation step (future-scale, explicitly not jumping ahead)

**SOURCE A (external, MEASURED by the source paper):** "When Memory Becomes Authority" (arXiv:2608.01679) — across 7 consolidators × 7 LLM backbones (49 configurations), authority collapse — content survives consolidation while the source-scope constraints governing its authorized use are silently stripped — occurred in 48 of 49. A fix that predicts and persists authority labels at consolidation time drops the unauthorized-action rate from 16.9% to 0.0% with unchanged benign task success.

**SOURCE B (AAMR, CODE_VERIFIED via `memory/CURRENT_STATE.md`, `PMLAB-REV-V0`):** AAMR's own project-memory schema already carries `claim_class`, `supersession_kind`, and `source_refs` as first-class, structurally-present fields — not a retrofit, a design decision from the start — and AAMR's own PMLAB-REV-V0 independently found bitemporal modeling (separating valid time from transaction time) reaches 0.944 exact match on "what did we believe at time T" questions, vs. 0.00 for a single timestamp.

**UNOBSERVED CONNECTION:** nobody has tested whether a consolidation step operating over records that already carry this kind of typed, bitemporal metadata shows a lower authority-collapse rate than the paper's untyped baselines. AAMR's own tooling might already be structurally defended against a failure mode the field has just identified as near-universal — or the schema might not matter if the consolidation *process* itself (an LLM doing the summarizing) simply drops the fields regardless of whether they exist, which is exactly the kind of thing the 48/49 result suggests happens by default.

**PROPOSED MECHANISM:** whenever AAMR builds any consolidation/summarization step — in the arena or in its own project-memory tooling — run the authority-collapse paper's own audit protocol against it before trusting it.

**EXPECTED REGIME:** any future consolidation work, arena or tooling.

**EXPECTED FAILURE:** typed schema alone doesn't help if the consolidation prompt doesn't explicitly instruct the model to carry the fields forward — a real possibility given the 48/49 base rate was presumably measured on systems that also had *some* provenance concept before losing it.

**MINIMAL TEST: not runnable today.** AAMR has no consolidation mechanism in its current arena (Tree/SP are explicitly off the board; store sizes are below the regime judged likely to need one). This is a design principle to carry into whatever consolidation work AAMR eventually does, not a competitor to E1–E3.

**COST:** $0 now; cheap later (reuse the source paper's own audit protocol rather than designing one from scratch).

**Explicitly: this does not qualify to jump ahead of E1** on the roadmap's own bar — it fails "concrete decision unlocked" today, since there is nothing yet built for it to test.

---

### H4 — Hard-case concentration as an added axis for E3's already-planned category split

**SOURCE A (external, MEASURED):** "When Continual Learning Moves to Memory" (arXiv:2604.27003) found that raw/verbatim experience reuse gives negative forward transfer overall (−9.5%, −7.5%), but the harm is *concentrated on hard cases specifically* (−26.1, −12.7 on hard subsets vs. roughly neutral on easy subsets) — a pooled number would have hidden this.

**SOURCE B (AAMR):** the roadmap's own E3 design already plans a per-category split (its H4, "category alignment... testable inside E3's per-category split for free") to test whether provenance repairs concentrate in specific LongMemEval categories.

**UNOBSERVED CONNECTION:** the external finding suggests category alone may not be the right cut — the *hard/easy* axis (or, more specifically, whether a question needs exact-detail reproduction vs. pattern generalization) might matter more than which LongMemEval category a probe happens to fall into, and it cuts across categories rather than aligning with them.

**PROPOSED MECHANISM:** when E3 runs, tag each probe not only by its existing category but also by whether it requires reproducing a specific detail (date, quantity, name — favors raw, per Verbatim Chunks) vs. pattern generalization across many items (favors compact/abstracted, per 2604.27003) — a finer, externally-motivated cut than category alone.

**MINIMAL TEST:** no new spend — an additional tag applied when analyzing E3's already-planned output.

**FALSIFICATION:** N/A — this is a free analytical enhancement regardless of which way E3's raw counts land.

**COST: $0, folds into E3's existing $0.10 cap.**

---

### H5 — Harmful-sibling / distraction diagnostic applied to AAMR's own fact retrieval (most promising: genuinely new, $0, cheapest immediate test)

**SOURCE A (external, MEASURED by the source paper):** "Right Family, Wrong Skill" (arXiv:2606.10388, updated 4 days before this report) found that standard retrieval metrics can look excellent (Recall@3 0.848–0.888) while a large fraction of "correct-looking" retrievals (harmful-sibling rate 0.346–0.372) are actually same-family-wrong-variant items that would misfire if acted on — a failure invisible to recall/precision alone.

**SOURCE B (AAMR, OBSERVED in the archaeology's own transcript, `HINDSIGHT_INFORMATION_COMPOSITION_ARCHAEOLOGY_V1.md` §4):** on `gpt4_f420262c` (the airline-ordering probe), Mem0's wrong answer includes **"Spirit"** — an airline that does not appear in the gold set at all. Gold is present at rank 1 in Mem0's context (AAMR_MEASURED), yet the reader's wrong answer names something not obviously drawn from the correct evidence — a pattern that has never been checked against AAMR's current failure taxonomy, which only distinguishes gold-present vs. gold-absent, not "a plausible-but-wrong competing item was in the mix."

**UNOBSERVED CONNECTION:** AAMR's current diagnostic vocabulary (`GOLD_IN_CONTEXT`, `GOLD_RANK`, `GOLD_DROPPED_BY_BUDGET`, `GOLD_PRESENT_READER_WRONG`) has no category for "the reader was distracted by a similar-but-wrong item," which is mechanistically different from "the reader had insufficient information" — the failure mode C1 (temporal anchoring) is built to fix. If some of AAMR's failures are actually distraction rather than under-specification, temporal anchoring alone would not fix them, and a different mechanism (reranking, or explicit contradiction/distractor flagging) would be needed instead.

**PROPOSED MECHANISM:** not a new mechanism to transplant — a diagnostic re-read of the delivered context for `gpt4_f420262c` and any other group-A/C probe, checking specifically for a stored item that could plausibly explain the wrong answer's specific wording (where did "Spirit" come from — a genuine confabulation, or a real stored item about a different trip/person that the reader conflated with the target?).

**EXPECTED REGIME:** any probe where the wrong answer contains specific, checkable content not present in the gold set.

**EXPECTED FAILURE:** if "Spirit" is a pure model confabulation with no traceable source in the delivered context, this diagnostic returns a clean negative — which is itself informative (rules out distraction, strengthens the pure under-specification story C1 targets).

**MINIMAL TEST:** re-read the already-collected, already-frozen context for `gpt4_f420262c` (and the other group-A/C probes) for a plausible source of "Spirit" — a pure re-analysis of data already on disk, identical in spirit to the archaeology's own method.

**FALSIFICATION:** no traceable source found for the specific wrong content — narrows to a pure confabulation/reasoning failure, not a retrieval-composition one.

**COST: $0 — no new spend, no new calls, applies the archaeology's own already-successful method (close-read before code-read) to one more question it didn't ask.**

---

## Top 5, ranked by promise

1. **H5** (harmful-sibling/distraction check) — most promising: genuinely new diagnostic axis, literally free, uses data already on disk, has a concrete, specific lead to chase (the unexplained "Spirit" answer) rather than a generic recommendation to "check for distraction."
2. **H2** (zero-dispersion diagnostic) — cheapest paid option (~$0.01–0.02), directly informs whether E1's representation-fix framing is well-targeted before spending the rest of Stage 1's budget.
3. **H1** (MemIR-informed C2 wording) — free, low-effort, closes a risk the roadmap itself already flagged.
4. **H4** (hard/easy split for E3) — free analytical enhancement, sharpens interpretation regardless of E3's outcome.
5. **H3** (authority-collapse-safe consolidation) — highest long-run strategic value, explicitly not actionable yet; the right item to revisit once any consolidation mechanism is on the board.

None of the five compete with E1, E2, or E3 for the next dollar — H1, H2, H4, and H5 fold into or run alongside the currently-budgeted stages at $0–0.02 combined marginal cost; H3 is correctly deferred.

---

## Sources

All external papers cited above were verified in `GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md` earlier the same day; not re-verified here. AAMR-internal facts are cited to `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md` and `HINDSIGHT_INFORMATION_COMPOSITION_ARCHAEOLOGY_V1.md`, both read in full for this document.
