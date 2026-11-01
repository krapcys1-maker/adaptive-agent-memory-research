# Mechanism B: State / Supersession — Design + Preregistration v1

**Design and preregistration only. New API spend: $0.00. No experiment run.** No ingest, no reader, no judge, no web search, no arena code changes. Machine-readable preregistration: [`preregistration.json`](../../data/lab/arena/mechanism-b-state-supersession-v1/preregistration.json). Parent commit `4ec6b3c7e18a82bee6401e523c0f3c98438a75d2`. Predecessor decision: `PM-20260824-23cd74aa` (`TEMPORAL_BRANCH_PAUSE`).

## 1. Problem

The temporal branch (E1 → Stage 2 → archaeology → E2) closed without a mechanism clearing independent replication. Per the paused-branch decision, the next mechanism candidate should be a genuinely different family, not another temporal-rendering variant.

Canonical failure this design targets — `STALE_STATE_CONFUSION`:

> T1: user works at Microsoft. T2: user leaves Microsoft. T3: user works at Google. Question: *where does the user currently work?* Failure: retrieval contains all three facts; the system (or the reader) treats them symmetrically, or selects a stale one.

Broken into submodes (per the required decomposition — V1 does not attempt all of them, see §6):

| Submode | Definition | V1 coverage |
|---|---|---|
| A — Direct supersession | old value → new value, same key | 3 probes (R1) |
| B — Negation/revocation | fact → explicitly no longer true | 3 probes (R2) |
| C — Return/reactivation | A → B → A | 3 probes (R3) |
| D — Multi-attribute state | one entity, several independently-changing fields | adversarial negative control only (R4), no dedicated regime |
| E — Dependency cascade | one state change invalidates derived facts | out of scope, flagged as a forward risk |
| F — Ambiguous update | new statement may or may not supersede the old one | deferred to a v1.1 extension |

Internal grounding, not just external motivation: `data/lab/pmlab-stale-e1/execution-v0/report.md` (a different, already-existing research track in this same repo) measured, on this project's own memory store (n=9 supersession pairs), that **content/embedding similarity cannot separate a superseded fact from its replacement** — supersession pairs sit at the corpus's 99.5th similarity percentile, and the stale version becomes the nearest neighbor 6 of 9 times once the store's own metadata filter is removed. Two pairs are cosine-identical. Its conclusion: *"Supersession cannot be solved by better retrieval. It must be carried in the schema."* This directly motivates an explicit, structural mechanism over anything retrieval- or embedding-based, and is already cited in `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md` as F17.

A second internal precedent: this repo's own `project_memory` tool (`memory/SCHEMA.md`) already implements the target architectural principle operationally — bitemporal fields (`valid_from`/`valid_to`, `created_at`/`expired_at`), an append-only log, `succession` vs `correction` classification, and a current view *derived* by replay rather than mutation. It has been in active use throughout this session. It is not applied to the Mem0/arena baseline — that gap is what this design addresses.

## 2. External mechanism archaeology

From already-recorded frontier docs only (`GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`), no new search performed.

| | StateMem (full method) | StateMemWrapper (SMW) | STALE | StateAuditor |
|---|---|---|---|---|
| **System** | arXiv:2608.19652 | arXiv:2608.19652 (same paper, distinct component) | arXiv:2605.06527 | inside arXiv:2608.01619 |
| **Target failure** | state drift (44.4% on original LongMemEval, one backbone, Wilson 95% CI [30%,60%]) | same | conflict detection, 400 expert-validated scenarios | memory updates but behavior doesn't follow |
| **Write-time logic** | TurnEncoder: 1 LLM call/turn; StateStore flags supersessions | none — pure read/inference-time | not detailed in the recorded frontier doc beyond "LLM adjudicator over a predefined schema" | not applicable (audits after generation) |
| **Read-time logic** | deterministic (LLM-free) Rechecker traverses a dependency graph; 1 further LLM call resolves state at answer time | one call replacing the answer-generation call: Trace (≤250-word chronological value-chain per slot) then Resolve (4 fixed precedence rules) | not detailed further in recorded sources | audits stored-state → draft, the *opposite* direction from pre-answer resolution |
| **State representation** | StateStore + dependency graph | implicit, inferred at read time via Trace | predefined schema (not detailed further) | not detailed further |
| **Supersession representation** | explicit flag in StateStore | implicit, resolved via the 4 precedence rules, not persisted | not detailed further | not detailed further |
| **Deterministic components** | Rechecker (graph traversal) | the 4 precedence rules are *statable* deterministically, but the paper's own instantiation runs Trace+Resolve as one LLM call — not hard-coded logic as published | none disclosed | not detailed further |
| **LLM components** | TurnEncoder (per turn), answer-time resolver | the entire Trace+Resolve call | the adjudicator itself | draft generation (unrelated to the audit step) |
| **Dependencies** | full write-path integration | raw transcript access as a fallback input alongside retrieved chunks (INFERENCE-flagged caveat in the frontier map: this may be a privileged ground-truth fallback, not pure backend-blind robustness) | not detailed further | stored state accessible for audit |
| **Known benefits** | wrapper's total gain (below) attributed partly to structure | +32–67pp across 6 backends; 15–32pp of that nested-attributable to structure specifically vs. a length/cost-matched control (both MEASURED, independently recomputed from the paper's Table 6) | best model 55.2% on its own 400-scenario set | +5.0pp on its own benchmark |
| **Known failures** | dependency-propagation over-propagates −12.5pp on one subset (removing it leaves one backbone *better* off); a weak backbone (Qwen-3.5-9B) neutralizes the whole memory layer, drift 61–66% across long-context/Mem0/BM25/StateMem alike; a naive question-blind 250-word summary actively hurts | shares the same paper's negative results | not detailed further in recorded sources | explicitly "no gain" on a second benchmark (HorizonBench), matched control +0.6, not significant — an honest self-reported generalization failure |
| **Portability** | LOW — requires write-path surgery | HIGH — explicitly host-agnostic, "no backend storage change required," applied across 6 backends (4 real memory systems + 2 classical IR baselines) | unknown, not detailed further | unknown, not detailed further |
| **Code availability** | not found (paper says it will release; 4 days old at time of the frontier pass) | same | not confirmed in recorded sources | not confirmed |
| **Evidence strength** | MEASURED (paper's own numbers, independently recomputed), single paper, submitted 4 days before the frontier pass, **not independently replicated** | same | one paper | one paper, with an honest non-replication already self-reported |

Honesty note: fields marked "not detailed further" reflect the limits of what the already-recorded frontier doc captured for STALE and StateAuditor specifically — it goes much deeper on StateMem/SMW (the triggering paper). This document does not fabricate mechanistic detail beyond what was already recorded, per §29's verification requirement and this project's standing evidentiary discipline.

## 3. Candidate board

| Name | Source | Core idea | Target failure | Side | Complexity | Contamination risk | Host dependence | Needs LLM | Token cost | Why transplantable | Why not |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **CURRENT_STATE_OVER_HISTORY** | SMW's Resolve rule 1 ("later supersedes earlier"), isolated | group retrieved items by detected state key; render latest as Current, rest as History with provenance | A, C; partial B | read | LOW | low — pure post-retrieval string transform | none — no host code touched | NO | small, fixed per-probe overhead | smallest atomic slice of SMW's rule set; fully deterministic; reuses metadata (`evidence_times`) already read by the temporal branch | narrow state-key coverage (fixed templates); doesn't address D/E/F |
| **EXPLICIT_SUPERSESSION_LINK** | StateMem's StateStore concept, adapted read-side | same grouping as above, plus an explicit per-item supersession chain object (not just a two-block split) | A, B, C | read | MEDIUM | low | none | NO | slightly higher (chain metadata) | closer to a full audit trail; strictly more informative than the selected candidate | more moving parts for a first screen; the extra structure isn't yet motivated by any V1 metric that the simpler candidate can't already supply |
| **DETERMINISTIC_LATEST_VALID_VALUE** | the "in-place overwrite" arm named in this repo's own (separate-track, unrun) `docs/11-research-laboratory/revision-benchmark-extension.md` | drop every non-latest item per matched key from the context entirely | A, C | read | LOW | **HIGH — destructive** | none | NO | lowest (fewer items) | cheapest possible implementation | **violates the mandatory append-only principle (§8)** — directly causes the historical-question negative regime by construction; included only as a contrast/ablation arm, not a serious candidate |
| **STATE_TRANSITION_TRACE** | SMW's Trace step, closer to as-published | render a chronological narrative per key ("Employer: Microsoft (Jan 2023) → Google (Jun 2023), current: Google") | A, B, C, partially D | read | MEDIUM–HIGH | low | none | OPTIONAL (LLM-mediated narrative) or LOW (templated join) | higher (narrative prose) | may preserve full history more legibly than a flat two-block split; closer fidelity to the source paper's actual mechanism | if LLM-mediated, adds a second confound into a mechanism test; if templated, mostly redundant with the selected candidate at higher token cost |
| **POST_HOC_STATE_AUDIT** | StateAuditor | let the reader answer normally, then check the answer against a deterministic latest-value lookup; flag/retry on mismatch | A, B, C (post-hoc) | both (read for lookup, control-flow change for retry) | MEDIUM | low | requires a retry/control-flow hook the current frozen reader harness doesn't have | NO for the check, OPTIONAL for a retry rewrite | extra call on flagged cases only | genuinely orthogonal architectural shape (post-hoc vs pre-answer) — a real alternative hypothesis worth keeping on the board | StateAuditor's own paper reports "no gain, not significant" on a second benchmark — real external evidence of fragility; also needs a harness change (retry loop) the other candidates don't |

## 4. Selected mechanism: `CURRENT_STATE_OVER_HISTORY`

Against the 8 required criteria: (1) mechanistically distinct from `TEMPORAL_ANCHOR_AT_CONTEXT` — annotation-of-everything vs. structural regrouping-and-precedence, a categorically different intervention shape; (2) small enough for isolated transplant — pure post-retrieval string transform, no host code touched; (3) clear failure mode — `STALE_STATE_CONFUSION`; (4) minimal host assumptions — needs only `evidence_ids`/`evidence_times`, already read by the temporal branch; (5) deterministic — no LLM anywhere in the V1 mechanism; (6) cheap — read-side only, same cost shape as E1; (7) clear falsification — see §11; (8) externally motivated (SMW rule 1), AAMR-untested. `EXPLICIT_SUPERSESSION_LINK` was the closest runner-up and is not rejected on principle — it is the natural v1.1 elaboration once the simpler candidate's provenance rendering is measured to be insufficient.

## 5. Exact transplant spec

Full machine-readable version in `preregistration.json`. Summary:

- **Input:** the same retrieved item list (text + `evidence_id` + `evidence_times`) BASE already receives — no retrieval change.
- **State-key strategy:** deterministic normalized pattern matching (Option A of §10), 9 fixed keyword/regex templates covering exactly the 12 probes' attributes (employer, residence city, relationship status, diet, gym membership, medication, pet name, language learning, address type — full list in `preregistration.json`'s `state_key_definition.templates_v1`). Options B (construction-time metadata keys), C (LLM-assisted), and D (hybrid) were considered and explicitly not selected for V1 — B doesn't test the real mechanism, C/D add cost/confound before Option A's own coverage is even measured.
- **Update rule:** later `evidence_times` timestamp wins as current, per matched key.
- **Supersession rule:** ≥2 items sharing a key → latest renders as `Current state:`, the rest render in a `History (superseded):` block, each tagged with its own date.
- **Retrieval rule:** unchanged.
- **Context rendering:** items with no detected key render exactly as BASE, interleaved in original order; matched items are pulled into the two labeled blocks appended after them.
- **Ambiguity handling:** timestamp ties or low-confidence partial matches fall back to BASE-equivalent rendering for that key (no guessing), logged as a mechanistic event.
- **Failure fallback:** zero key matches in a probe → `+B` is byte-identical to `BASE`. The mechanism must be inert, never harmful, when it finds nothing to act on.
- **What it does not do:** touch Mem0 storage/extraction/ranking; delete or hide any item (every item stays in the rendered context); attempt dependency propagation (mode E); resolve ambiguous updates (mode F); use an LLM.

## 6. Target failure

See §1's table. V1 covers submodes A, B, C with 3 dedicated probes each. D is exercised only adversarially (as a negative control an over-eager mechanism must NOT trigger on), not as its own regime. E and F are out of scope by design, per the explicit instruction not to assume the first test must cover everything.

## 7. Negative regimes (mandatory, preregistered)

| Risk | How V1 is meant to catch it |
|---|---|
| Related facts mistaken for same state | R4 controls (CTL1 two cats, CTL2 two languages, CTL3 home vs. work address) are adversarially constructed to share surface vocabulary while requiring separate keys |
| Parallel attributes collapsed | same R4 controls, specifically CTL3 (both facts contain the literal word "address") |
| Historical question asks old value | **not measured by V1's 12 probes** — no dedicated historical-question probe exists yet; recorded as an open gap in `unresolved_questions`, not papered over |
| Ambiguous update treated as supersession | out of scope for V1 (mode F deferred); flagged as a known unaddressed risk, not claimed solved |
| Return-to-old-value mishandled | R3 probes (RET1/2/3) directly test A→B→A; correct behavior requires the *third*, most-recent occurrence to win, not merely "first key match" |
| Context clutter from state trace | tracked via the `token_delta` metric; the roadmap's own §10 Pair-1 caveat ("prefix clutter... push the reader to skim structure instead of content") is a known, general risk for this class of intervention, not unique to this mechanism |
| Over-propagation of invalidation | no dependency graph exists in V1 (mode E out of scope), but the *base* current/history split could still mis-group unrelated same-keyed items — this is exactly what the R4 adversarial controls test |

## 8. Baseline

Same memories, same retrieval, same reader, same prompt, same temperature/max_tokens, same judge, same retrieval budget as `BASE`. The only difference is whether the retrieved item list passes through the `+B` render transform before being joined into `Memory context:\n...` (the existing `fixed_reader.py::user_message` join point, unmodified). One confound is expected and explicitly not hidden: `+B`'s block headers add a small, fixed per-probe token count — tracked as `token_delta`, not silently absorbed into the accuracy number.

## 9. Experiment design (preregistered, not run)

`MECHANISM_B_STATE_SUPERSESSION_V1`, 12 probes (3 `CLEAN_SUPERSESSION` + 3 `REVOCATION` + 3 `RETURN` + 3 `NO_UPDATE_CONTROL`), matching the suggested distribution with no deviation. Full probe text, dates, expected values in `preregistration.json`'s `probe_plan`. Arms: `BASE`, `+B`. Both arms share one Mem0 ingest per probe (the mechanism is purely a post-retrieval render transform, so no second ingest is needed — same pattern as E1's `+TIME` arm). Probe distribution frozen before any probe was checked against expected behavior, matching this project's standing pre-registration discipline.

## 10. Metrics

**Primary:** accuracy, repairs, regressions, net repairs, current-state accuracy (R1+R2+R3), historical-question accuracy (no data in V1 — see §14 gap), false supersession rate (R4), state-key collision rate, token delta, latency delta.

**Mechanistic, per probe:** was correct state present in retrieved items; was stale state also present; did `+B` mark supersession correctly (R1/R2/R3); did the reader's answer traceably use the Current-state block; did `+B` hide information a historical sub-question would need (N/A for V1); did `+B` create a wrong supersession on an R4 control.

## 11. GO/FAIL gate

**`MECHANISM_B_EXPLORATORY_SUPPORTED`** requires ALL of: positive net repairs across the 9 R1+R2+R3 probes; zero false-supersession events across the 3 R4 controls; no systematic harm on R4; mechanism-level trace shows the intended causal path on every repair (not a coincidental match).

**`MECHANISM_B_FAIL`** if ANY of: no positive repair signal; false supersession common (≥1/3 R4 controls wrongly collapsed); a regression traceable to the mechanism suppressing information the reader had under BASE; the effect is attributable only to added token volume rather than the current/history structuring itself; the implementation needed a state-key rule that referenced a probe's own expected answer (a gold-specific oracle, not a general pattern).

## 12. Replication rule

Even a clean V1 pass caps at `MECHANISM_B_EXPLORATORY_SUPPORTED` — never `REPLICATED_VALIDATED_TRANSPLANT`. That status requires a fresh, independently-constructed or gold-blind-selected probe set under the same protocol, mirroring the E1→Stage-2 pattern already established in this project. A concrete real-corpus candidate for that future replication, verified this pass: LongMemEval-S's `knowledge-update` category holds 78 units in the full corpus, **0 used anywhere in this arena to date**.

## 13. Cost estimate

No API call made this turn. Projected, if a future turn separately authorizes the actual run: ingest ≈ $0.15–0.20 (12 short synthetic probes, each far smaller than a real 40+-session LongMemEval unit at the roadmap's own measured ~$0.074/unit), reader ≈ $0.014 (24 calls at ~$0.0006 each), judge ≈ $0.001 (24 calls at ~$0.00005 each). **Expected total ≈ $0.15–0.25.** Recommended hard cap: **$0.30**. Comfortably under the "$0.50 is too heavy for a first screen" ceiling.

## 14. Frankenstein relevance

- **vs. `TEMPORAL_ANCHOR_AT_CONTEXT`: `PARTIALLY_OVERLAPPING`**, not orthogonal. `CROSS_PAPER_HYPOTHESIS_MAP_2026-08-24.md` itself frames AAMR's temporal-anchor work as "a narrower, already-in-flight instance of this broader [state/supersession] family." Both consume the same `evidence_times` metadata; they differ in intervention shape (uniform annotation vs. structural regrouping-and-precedence). A future interaction grid is a genuinely open question, not an assumed redundancy.
- **vs. `RAW_PROVENANCE` family (E3/C4): `ORTHOGONAL`.** Different failure territory — missing-detail recovery vs. which-of-several-present-facts-is-current.
- **vs. `HARMFUL_SIBLING_DISTRACTION` (H5): `PARTIALLY_OVERLAPPING`.** Same observable shape (reader picks a wrong item among several plausible retrieved candidates), different underlying axis — entity-identity confusion (H5, e.g. Spirit vs. Delta) vs. temporal-validity confusion (this mechanism, Microsoft-then vs. Google-now). The R4 adversarial controls specifically test whether an over-loose key match could misfire in an H5-adjacent way.

## 15. Unresolved questions

Full list in `preregistration.json`'s `unresolved_questions`. Headline items: (1) V1 has zero dedicated historical-question probes, so the mechanism's stated risk of hiding needed history is *not yet measured*, only asserted as a design concern; (2) the 9-template state-key strategy is validated only against probes built to trigger it — its real-corpus miss rate is unknown; (3) the timestamp-tie fallback path is untested by any of the 12 probes as constructed; (4) whether Mem0's own near-duplicate suppression (roadmap F13) could merge two temporally-distinct same-key statements into one stored item *before this mechanism ever sees them* is unverified — a cheap, deterministic check worth running before any paid probe run.
