# Hindsight Information-Composition Archaeology v1

Diagnosis only. No new paid provider call, no rerun, no BASE+X implementation.
Full structured data: [`data/lab/arena/hindsight-archaeology-v1/information-composition-v1.json`](../../data/lab/arena/hindsight-archaeology-v1/information-composition-v1.json).

> **Correction (see `data/lab/arena/base-plus-x-v1/`):** section 9's Mem0 code
> citations below described `external/repos/mem0ai__mem0`'s HEAD checkout, not
> the actually-running pinned `mem0ai==1.0.6` in `external/venvs/mem0`. The
> causal diagnosis (Mem0's extraction is not grounded on the real historical
> date) was reconfirmed against the correct source and is, if anything, more
> precise there. A narrow patch built on the corrected source
> (`PER_SESSION_REFERENCE_DATE_AT_EXTRACTION`) was calibrated with one
> `$0.02`-capped call and found **not** to change extraction behavior on its
> own — see `data/lab/arena/base-plus-x-v1/calibration-per-session-reference-date.json`.
> Project memory: `PM-20260824-b697ecc3` (citation correction),
> `PM-20260824-c76d8a96` (calibration result).

## Epistemic key

Every claim below is tagged. Don't read across tags as equally certain.

- **MEASURED** — a number read directly off a frozen artifact.
- **OBSERVED** — a property read directly off raw context/answer text by a human-equivalent close read.
- **CODE-VERIFIED** — traced to a specific file/function in locally-available source.
- **INFERENCE** — a conclusion drawn from MEASURED/OBSERVED/CODE-VERIFIED facts, stated as such.
- **HYPOTHESIS** — a candidate explanation not yet independently replicated.
- **UNRESOLVED** — looked at, no clean answer.

## 0. Scope discipline

New paid spend this phase: **$0.00**. No LLM reader call, no judge call, no ingest, no retrieval was made. All numbers below are re-read from artifacts already on disk; all code claims are traced in locally-checked-out source (`external/repos/vectorize-io__hindsight`, `external/repos/mem0ai__mem0`).

## 1. Source of truth — re-verified this session

**MEASURED**, re-tallied directly from `mem0-breadth-judged.json`, `hindsight-ablation-judged.json`, `fixed-reader-judged-all.json`:

| | native/matched | 500 | 1000 | 3000/full |
|---|---|---|---|---|
| Mem0 | 5/10 | 6/10 | 6/10 | 5/10 |
| Hindsight | 5/10 | 6/10 | 6/10 | 7/10 |

Matches the prompt's expected numbers exactly — confirmed from artifacts, not assumed.

## 2. Freeze interpretation

**No bug found this phase that invalidates the frozen data.** One **cosmetic** issue, recorded but not reopened: `gpt4_98f46fc6`'s Hindsight judgement (`fixed-reader-judged-all.json`) reads as an instance of this project's already-documented LongMemEval judge looseness — Hindsight's own answer explicitly says the comparison "cannot be determined," yet is scored correct. This touches judge behavior on one probe's label, not retrieval, not context assembly, not the frozen scores in aggregate. Per the phase-2 rule, this is cosmetic — logged, no rerun.

## 3. Per-probe comparison matrix and groups

**MEASURED.** All 10 units, Mem0-3000 vs Hindsight-full:

| probe | group | type | mem0 tok | hind tok | mem0 gold_rank | hind gold_rank |
|---|---|---|---|---|---|---|
| gpt4_f420262c | **A** | temporal-reasoning | 2212 | 3095 | 1 | 1 |
| gpt4_59c863d7 | **A** | multi-session | 2339 | 3054 | 1 | 5 |
| gpt4_98f46fc6 | B | temporal-reasoning | 2113 | 3237 | 1 | 3 |
| 58bf7951 | B | single-session-user | 2211 | 3117 | 1 | 1 |
| 6a27ffc2 | B | knowledge-update | 2016 | 3077 | 1 | 1 |
| eace081b | B | knowledge-update | 2842 | 3096 | 1 | 1 |
| 311778f1 | B | single-session-user | 2340 | 2994 | 1 | 69 |
| ba358f49 | C | multi-session | 2602 | 3220 | 1 | 5 |
| gpt4_f49edff3 | C | temporal-reasoning | 2666 | 3139 | 1 | 8 |
| 69fee5aa | C | knowledge-update | 2516 | 3139 | UNOBSERVABLE | UNOBSERVABLE |

**Groups: A=2, B=5, C=3, D=0.** D being empty (Hindsight never loses to Mem0 at these widest budgets, on this sample) is itself a **MEASURED** fact worth keeping in view.

**INFERENCE**, immediately visible and important: in both group-A probes, `mem0_gold_rank=1` and `hindsight_gold_rank` is 5 in both — Mem0's retrieval ranks the gold evidence *better*, not worse, than Hindsight's, in exactly the two cases where Mem0's reader still fails. Whatever explains group A, it is not "Hindsight retrieves gold more prominently." That hypothesis is refuted by this session's own data before any content reading began.

## 4. Group A close read

### gpt4_f420262c — "order of airlines flown, earliest to latest"

Gold: `JetBlue, Delta, United, American Airlines`. Mem0 answers `American, United, JetBlue, Spirit` (wrong order, drops Delta, invents Spirit). Hindsight answers `JetBlue, United, Delta, American`, judged correct.

**OBSERVED**, reading both raw contexts:
- Mem0's relevant memories: *"...on a flight from New York to Los Angeles on February 10th"* (has a date) / *"1-hour delay on a United Airlines flight from Boston to Chicago..."* (no date) / *"red-eye flight on JetBlue from San Francisco to Boston..."* (no date) / *"Took a round-trip flight from Boston to Atlanta today"* (no airline name at all — this is the Delta flight, but "Delta" never appears in this sentence).
- Hindsight's matching memories each carry an explicit `| When: <date>` field — `before November 17, 2022`, `January 28, 2023`, `January 15, 2023`, `February 10, 2023` — covering all four flights, plus an `Involving:` field.

Only 1 of 4 needed flights carries a date in Mem0's text; the Delta flight isn't named at all. Hindsight recovers dates for all 4.

### gpt4_59c863d7 — "how many model kits have I worked on or bought" (gold: 5)

Mem0 answers 4 (misses the German Tiger I tank diorama). Hindsight answers 5.

**OBSERVED:** the Tiger I fact is **not absent** from Mem0's context — it appears once, at position 60 of 223 items. Hindsight's context restates the identical underlying fact **three times**, at positions 32, 39 and 68 of 131 items, each with its own `When:`/`Involving:` metadata. Content presence rules out a content-absence story here; the difference is in how many independent chances the reader has to notice the fact while scanning a long list.

## 5. Beyond gold presence — full checklist, all 10 probes

Full per-probe answers to the 17-item checklist are in the JSON artifact (`comparison_matrix[*].qualitative.checklist`). Summary of what actually differentiated outcomes, not what was merely present:

- **Temporal ordering needed + date stripped in Mem0’s text**: differentiates gpt4_f420262c (A) and partially gpt4_f49edff3 (C, boundary case — Hindsight recovers 2 of 3 needed dates, fails on the 3rd, and the overall answer is still wrong).
- **Distributed-fact aggregation/counting**: differentiates gpt4_59c863d7 (A). Also present in `6a27ffc2` and `311778f1` (B) but there the needed fact was a single already-computed number (not scattered across many items), so aggregation wasn't actually being tested — both trivially succeed.
- **Correction/supersession ("used to be A, now B")**: present in `6a27ffc2` (B, succeeds — a single buried correct mention was enough) and `69fee5aa` (C, fails — the "corrected" value was never captured by either system in the first place; both are stuck on the stale number).
- **Content genuinely absent from both**: `ba358f49` and `69fee5aa`. Neither is informative for ranking a Mem0-vs-Hindsight mechanism — the gap is upstream of either system's compaction.

## 6. Data-driven taxonomy

Built from what actually differed, not from the suggested preset list.

| class | definition | Mem0 | Hindsight | correlates with correctness? |
|---|---|---|---|---|
| **structured_temporal_anchor** | explicit, separately-labelled date attached to a fact | inconsistent — present only if stated in the source message text | structural — required extraction field, `\| When: X` | **yes**, on temporal-composition questions (A: full; C: partial boundary) |
| **redundant_episodic_accumulation** | same event stored as multiple independent near-duplicate rows | rare (dedup by design) | frequent (no dedup on raw facts) | probabilistic — helps findability in long scattered lists, doesn't manufacture correctness (69fee5aa) or become necessary when one clean mention suffices (6a27ffc2) |
| **entity_qualifier_retention** | whether a compacted fact keeps naming the specific entity | at least one confirmed loss | retained via the same write-time field | single-probe evidence only — not independently replicated |

**Considered and explicitly not supported by this sample:** atomic-fact-vs-summary compression (both systems return atomic facts here — not differentiating); raw provenance (already refuted in a prior experiment, Experiment B of arena-mechanism-ablation-v1: appending raw source text repaired 0 of 4 failures); an explicit correction/supersession marker (neither system has one — both just present old and new facts and rely on the reader).

## 7. Content vs representation vs selection vs composition

Per probe, in `comparison_matrix[*].qualitative.classification` and the JSON's `content_representation_selection_composition` block. Headline: **6 of 10 probes are not diagnostic** (3 trivial single-fact B cases, 2 equal content-absence C cases, 1 judge-noise B case). Of the 4 that are diagnostic, **all 4 land on REPRESENTATION_DIFFERENCE**, none on pure CONTENT_ABSENCE or pure SELECTION/DISTRACTOR. No probe in this sample supports a distractor/conflict story (category C in the brief) — a wider Mem0 context was never observed to introduce a competing wrong answer that beat a present, correct one.

## 8. Anti-storytelling checks

Full tabulation in the JSON (`anti_storytelling_checks`). Headline:

- **Candidate 1 (temporal grounding)** passes all five checks: predictable without gold, deterministically definable, its absence tracks the one clean C-group failure it should track, and it does not require gold to transplant.
- **Candidate 2 (redundant accumulation)** passes the deterministic-definition check but **fails the sharp-correlation check** (present in a BOTH_WRONG control without helping, absent in a BOTH_CORRECT probe without hurting) and has no gold-free way to decide *which* facts deserve redundant retention before transplanting.
- **Candidate 3 (entity retention)** has only one supporting probe — flagged as under-replicated, not asserted as a validated mechanism.

## 9. Code inspection (performed *after* the data read, not before)

Three independent local-code investigations, `external/repos/vectorize-io__hindsight` and `external/repos/mem0ai__mem0`. Full citations in the JSON's `code_mechanisms` block; headline:

**CODE-VERIFIED — Hindsight's temporal/entity field** (`hindsight_api/engine/retain/fact_extraction.py`, `extract_facts_from_text`): `when`/`who` are *required* LLM-extraction schema fields; when non-`"N/A"`, they're joined into the stored fact text as `\| When: X \| Involving: Y`. This happens at **WRITE time** only — confirmed absent from retrieval/search code by grep.

**CODE-VERIFIED — Mem0's date loss is a plumbing gap, not a missing instruction** (`mem0/memory/main.py::_add_to_vector_store`, `mem0/configs/prompts.py`): the live extraction prompt *already* instructs "preserve exact dates... convert relative to absolute using Observation Date." But `main.py` never threads a real timestamp into that call; `_resolve_dates()` silently defaults `current_date`/`observation_date` to `datetime.now(timezone.utc)` (ingestion wall-clock time, not the conversation's real date), and OSS `add()` explicitly rejects an external `timestamp` argument ("Platform-only... Not supported in OSS"). The prompt asks for something it structurally cannot receive.

**CODE-VERIFIED — the redundancy asymmetry**: Hindsight has no similarity check on the raw-fact write path, and its consolidation-layer dedup only touches a later "observation" layer without removing the original raw duplicates from what retrieval returns (`prefer_observations` defaults `False`). Mem0's live pipeline is ADD-only (the old ADD/UPDATE/DELETE decision prompt exists in the codebase but is dead code, never invoked) and suppresses near-duplicates at extraction time via an LLM instruction plus exact-hash matching.

## 10. Candidate mechanisms (ranked)

Full detail (OBSERVED_BEHAVIOR / CODE_MECHANISM / SUPPORTED_PROBES / CONTROL_PROBES / ALTERNATIVE_EXPLANATION / TRANSPLANTABILITY / MINIMAL_TRANSPLANT / PREDICTION / FAILURE_PREDICTION) is in the JSON's `candidates` array. Summary:

1. **TEMPORAL_GROUNDING_AT_EXTRACTION** — TRANSPLANTABILITY: **HIGH**. Not "more tokens": Mem0's 3000-token context already contains the relevant facts: the missing ingredient is a date attached to facts already present, not more content.
2. **REDUNDANT_RAW_FACT_ACCUMULATION** — TRANSPLANTABILITY: **LOW-MEDIUM**. Real, code-verified, but the minimal transplant is a blunt system-wide relaxation of Mem0's existing dedup, with no way to target only the facts that would benefit, and a direct conflict with this project's multi-session cross-unit-contamination concerns.
3. **ENTITY_QUALIFIER_RETENTION** — single-probe support, not independently replicated. Kept separate from candidate 1 only because the brief asks not to force-fit probes into one bucket; may turn out to be the same mechanism observed twice.

## 11. Gate to Frankenstein

Checklist (full detail in JSON `first_transplant_candidate_gate`):

| | data diff | code coverage | no gold needed | isolable | falsifiable | small enough | not just tokens |
|---|---|---|---|---|---|---|---|
| Candidate 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Candidate 2 | ✓ | ✓ | ✓ | partial | ✓ | ✗ | ✗ |
| Candidate 3 | single-probe | shares C1's path | ✓ | shares C1's path | untested | — | ✓ |

**FIRST_TRANSPLANT_CANDIDATE: TEMPORAL_GROUNDING_AT_EXTRACTION.**

Candidate 1 is the only one clearing all seven gates. Candidates 2 and 3 are recorded, not discarded — 2 fails specifically on "small enough" and "not just tokens"; 3 needs replication this phase did not attempt.

## 12. Not implemented

No BASE+X. No code change to either system. No new harness, router, controller, or benchmark. This document is a diagnosis, not a patch.

## 13-14. Artifacts and memory

JSON artifact: `data/lab/arena/hindsight-archaeology-v1/{comparison-matrix.json, information-composition-v1.json}`. Project memory: append-only finding recorded, no history rewritten (see commit / memory ID in the final response).
