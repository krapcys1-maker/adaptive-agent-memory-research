> **Publication note, 2026-11-12.** Written on 2026-08-24 and kept in one local working tree until this date; other
> documents and project-memory records cited it while it was unpublished. Everything below this note is the unedited
> original (SHA-256 of the original file: `b9496570d02efe5d6b0a45f9a47f33c4e2aef4b56fd6886cf649ba684ae16233`). It is a planning record, not a result. Where it and
> [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) disagree, the ledger wins. All arena numbers
> are on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1, with 4 to 10 questions per test.
>
> What happened next: its three experiments were run. E1 (read-side temporal anchor) is ledger Entries A, B and N; E2
> (write-side temporal resolution) stopped at calibration, Entry E; E3 (clean raw-provenance retest) is Entry H. The
> `BASE`/`+A`/`+B`/`+A+B` interaction grid of sections 9 to 11 was never reached, because only one mechanism was validated.

# Research Roadmap, Evidence-Driven, V1 — 2026-08-24

Synthesis and planning only. No code changed, no benchmark run, no ingest, no reader/judge call, no paid API call was made for this document. Every number below was re-read from frozen artifacts or primary-source notes already in the repository, not from memory of earlier prose.

Labels used throughout, never mixed:

- **AAMR_MEASURED** — read directly from this repository's own frozen artifacts, valid (not invalidated) as of this document.
- **AAMR_INVALIDATED** — measured by us, formally invalidated (contamination or superseded run); listed so it is never silently re-used.
- **EXTERNAL_MEASURED** — a number read from an external paper's own tables during the primary-source-verified passes (`RELATED_WORK_*_2026-08-24.md`).
- **CODE_VERIFIED** — confirmed by direct inspection of locally checked-out or vendored source, at the pinned version actually running.
- **PAPER_CLAIM** — an external paper's own stated conclusion, not reproduced here.
- **INFERENCE** — this document's reasoning connecting tagged facts.
- **HYPOTHESIS** — a proposed, testable, not-yet-tested claim.
- **UNRESOLVED** — examined, no clean answer.

---

## 1. Executive conclusion

**The Frankenstein hypothesis — that a better memory system can be built by identifying, isolating, and combining mechanisms from different systems — is currently supported PARTIALLY, and the support is asymmetric: external evidence that single transplanted mechanisms work across hosts is real and multi-sourced; AAMR's own evidence is so far diagnostic, not causal — zero completed transplant runs exist, because the first attempt was correctly stopped at calibration when the minimal patch proved inert.**

The single most consequential update since the last synthesis pass (`MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md`) is that its recommended first experiment — Mem0 breadth expansion — **has since been run, clean, and answered**: Mem0's accuracy does not climb with breadth (5/10 native → 6/10 @500 → 6/10 @1000 → 5/10 @3000, where the 3000-token arm delivers the *entire* memory bank of every unit — AAMR_MEASURED). Volume is now saturated and eliminated as the explanation of the Mem0–Hindsight gap on this sample. What remains is the *kind* of item each system stores — and the information-composition archaeology localized the best-gated candidate difference to **structured temporal anchoring of facts in the delivered representation** (Hindsight's `| When: X | Involving: Y`, CODE_VERIFIED at write time; Mem0's bare undated fact strings, AAMR_MEASURED in the delivered contexts).

The cheapest strong next test is **not** the write-side date patch (already built, already calibrated, measured inert on its own — the model ignores a reference date it is never instructed to use). It is a **read-side transplant**: render each retrieved Mem0 memory with the per-memory session timestamp that the clean run already persisted but never delivered (`evidence_times` in `clean-mem0.json` — AAMR_MEASURED that these exist and are real session dates, and AAMR_MEASURED that the delivered contexts contain no dates at all). This is a deterministic context-assembly change, needs **zero new ingest**, costs ~$0.03–0.05 including a token-matched placebo arm, and directly tests the representation hypothesis the archaeology actually produced.

Recommended next three paid experiments, stage-gated, total hard cap **$2.20**, expected actual spend ~$0.95:

1. **E1 — Read-side temporal anchoring micro-grid** (BASE / +TIME / +SOURCE-TAG, with the +BOTH cell gated on either arm showing a predicted flip): cap $0.10.
2. **E2 — Write-side temporal resolution at extraction** (reference date + explicit resolve-instruction; calibration-gated before any 10-unit spend): cap $1.00, entered only on an E1 signal or an E1-null that implicates extraction rather than the reader.
3. **E3 — Clean re-test of raw-provenance expansion with per-category split** (the old zero-repairs DROP rests entirely on contamination-invalidated data): cap $0.10, unconditional.

---

## 2. What AAMR actually knows (valid findings ledger)

Every Mem0 number that predates the reset fix is invalidated (§3). The table below is the post-invalidation, post-truncation-fix state of knowledge.

| # | FINDING | STATUS | EVIDENCE | CONFIDENCE | WHAT IT DOES NOT PROVE |
|---|---|---|---|---|---|
| F1 | Clean Mem0 breadth curve is flat-then-down: **5/10 native (limit 10, ~106 tok), 6/10 @500, 6/10 @1000, 5/10 @3000** | AAMR_MEASURED | `mem0-breadth-judged.json` (recomputed from per-row labels this pass), arms from `mem0-breadth-arms.json`, provenance `mem0-breadth-refreeze-v2.json` | Medium-high (clean store verified `foreign_from_other_units: 0` on all arms; but n=10, one generation per cell) | That breadth *hurts* Mem0 in general — the 3000-arm drop is a single probe flip (`gpt4_f49edff3`) |
| F2 | The Mem0 3000-token arm contains each unit's **entire store** (201–272 items = all stored items; no truncation triggers) | AAMR_MEASURED | `mem0-breadth-arms.json` item counts vs `clean-mem0.json` `stored_items`; refreeze note "0 of 10 at 3000" | High | That nothing more could ever be delivered — raw source sessions are not in the store, only extracted facts |
| F3 | Corrected Hindsight curve: **5/10 @matched(~102 tok), 6/10 @500, 6/10 @1000, 7/10 @full(~3117 tok)** | AAMR_MEASURED | `hindsight-ablation-judged.json` (truncation-bug-corrected arms), full arm from `fixed-reader-judged-all.json`; `hindsight-ablation-refreeze-v2.json` | Medium (see F4/F5 caveats) | Monotone causal breadth benefit — the earlier "monotone curve" claim was computed with the skip-on-overflow truncation bug; the corrected matched arm moved 4/10→5/10 |
| F4 | **At equal (Mem0-matched) budget the two systems score identically: 5/10 = 5/10** | AAMR_MEASURED | F1 + F3 | Medium-high (held under both the buggy and the corrected truncation, and under contaminated and clean Mem0 — the equality itself replicated across four analysis variants) | That the systems are equivalent — the equality is at the *narrow* operating point only |
| F5 | Hindsight's full-breadth 7/10 includes **one judge-loose label** (`gpt4_98f46fc6`: answer says "cannot be determined", scored correct). Strictly read, full breadth may be 6/10 and the Hindsight curve flat above 500 | AAMR_MEASURED (the label and the answer text), INFERENCE (the strict re-reading) | Archaeology §2; `fixed-reader-judged-all.json` per-unit labels re-checked this pass | High that the loose label exists; the strict 6/10 reading is arithmetic, not a re-judgement | That Hindsight's wide-context advantage is an artifact — group A (below) survives the strict reading: 2 units where Hindsight is right and Mem0 wrong at widest breadth |
| F6 | At widest breadth: **A=2 units Hindsight-correct/Mem0-wrong; B=5 both-correct; C=3 both-wrong; D=0 Mem0-correct/Hindsight-wrong** | AAMR_MEASURED | `hindsight-archaeology-v1/comparison-matrix.json`, re-tallied | Medium-high (n=10) | That Hindsight dominates in general — D=0 is a 10-unit, non-random-sample fact |
| F7 | In both group-A failures Mem0's **gold rank is 1** (Hindsight's is 5); clean Mem0 places gold at rank 1 in 9/9 observable units and still scores ≤6/10 in every arm | AAMR_MEASURED | Archaeology matrix; `clean-mem0.json` retrieval blocks | High | That retrieval never matters — this is a regime fact (LongMemEval-S, 10 units, compact extraction); MINTEval shows retrieval dominates failures at much larger scale (EXTERNAL_MEASURED) |
| F8 | Mem0's delivered contexts are **bare fact strings with no dates and no subject attribution**; the same artifact stores real per-memory session timestamps (`evidence_times`, e.g. `2023/01/28 (Sat) 01:32`) that are never rendered into any delivered context | AAMR_MEASURED | `mem0-breadth-arms.json` context arrays; `clean-mem0.json` `deep_retrieval.evidence_times`; reader assembly `fixed_reader.py::user_message` (CODE_VERIFIED: items joined as `- {text}`) | High | That rendering them would help — that is exactly the untested E1 hypothesis |
| F9 | Hindsight's stored facts carry `\| When: <date> \| Involving: <who>` appended into fact text at **write time**, as required extraction-schema fields; frequently also absolute dates resolved into the fact text itself | CODE_VERIFIED (`hindsight-api-slim/.../retain/fact_extraction.py`, re-verified this pass: `combined_parts.append(f"When: {when}")`) + AAMR_MEASURED in delivered contexts | High | That When-fields are *the* cause of Hindsight's wins — supported on 1 full + 1 partial + 1 plausible probe, not proven |
| F10 | Mem0 1.0.6's extraction prompt hardcodes `Today's date is {datetime.now():%Y-%m-%d}` at module import; the arena adapter's correct per-session `metadata["timestamp"]` never reaches extraction; OSS `add()` rejects an external timestamp | CODE_VERIFIED (pinned 1.0.6 snapshot in `base-plus-x-v1/vendor-patch/`, empirically confirmed "2026-08-24" while ingesting a 2022/2023 corpus) | High | That fixing the date fixes anything by itself — see F11 |
| F11 | **The minimal date-only patch is inert at extraction level**: with a correct reference date substituted, extracted fact text is byte-identical to BASE ("…today" preserved unresolved). Root cause: the 1.0.6 prompt contains no instruction to resolve relative time, and its few-shots demonstrate *dropping* temporal words | AAMR_MEASURED (one calibration case, $0.0016, `calibration-per-session-reference-date.json`) + CODE_VERIFIED (prompt text) | High for the mechanism reading; the behavioral cell itself is n=1 synthetic input | That a date+instruction treatment would also be inert — that variant was deliberately not attempted (third-change rule) and is untested |
| F12 | The Mem0 vs Hindsight difference, where diagnostic, is a **representation difference**, not content-absence, not selection/distractor: 4 of 4 diagnostic probes classify as REPRESENTATION_DIFFERENCE; 0 probes show a wider context introducing a competing wrong answer | AAMR_MEASURED (archaeology classification; 6 of 10 probes non-diagnostic) | Medium (classification is a close-read, not blind) | That representation explains all failures — group C (3 both-wrong) includes upstream capture gaps neither representation fixes |
| F13 | Redundant restatement (same fact stored 3× with independent metadata) differentiates the counting probe `gpt4_59c863d7`; Hindsight has no raw-fact dedup (CODE_VERIFIED), Mem0 suppresses near-duplicates (CODE_VERIFIED) | AAMR_MEASURED + CODE_VERIFIED | Medium | That redundancy causes correctness — it failed the archaeology's sharp-correlation anti-storytelling check (present in a BOTH_WRONG control without helping) |
| F14 | Contamination mechanism: Mem0 1.0.6 `delete_all` removes ≤100 rows per call (vector-store `list` default limit); every unit stored 220–392 rows; every pre-fix reset left 120–292 residual rows; 8/100 delivered evidence items in the audited run came from other units; residue also suppressed writes (ADD→UPDATE/NOOP drift) | AAMR_MEASURED (`cross-unit-contamination-audit.json`, empirically proven 250→150→50) | High | Nothing about memory mechanisms — this is a harness/vendor-API finding, and a reusable methodological result in its own right |
| F15 | Question-only baseline: 0/10 | AAMR_MEASURED | `fixed-reader-report.json` / `fixed-reader-judged-all.json` | High | — |
| F16 | Judging is deterministic-protocol but loose in at least one known way (F5); reader is a single model (deepseek-chat, temp 0); every cell is one generation | AAMR_MEASURED | Judged artifacts; `judge_stability` 48/48 stable on the ablation set | High | That any 1-unit delta between arms is signal — the earlier `medium`-slot non-monotonicity was explicitly recorded as noise-until-replicated |
| F17 | Older PMLAB results (bitemporal resolver 0.944; association-graph fusion negative at −0.114 R@5; supersession indistinguishable by similarity at cosine 1.000; cross-language gap 0.156→0.978) | AAMR_MEASURED (separate track, unaffected by arena invalidation) | High | These are instrument/schema findings, not arena mechanism findings |

**The one-sentence compression: on this frozen 10-unit sample, both systems retrieve gold near-perfectly at their widest settings, deliver it, and still fail on 3–5 units each; the measured difference between them at wide breadth is 1–2 units, at least one of which is cleanly attributable to temporal anchoring of the delivered representation (AAMR_MEASURED for the correlation, HYPOTHESIS for the causation — no transplant has yet tested it).**

## 3. Invalidated / superseded conclusions

Listed so they cannot silently re-enter reasoning. All carry `INVALIDATED_BY_CROSS_UNIT_CONTAMINATION` stamps in their artifacts unless noted.

| Old conclusion | Where it lived | Why invalid | What replaces it |
|---|---|---|---|
| Mem0 2/10 (memory-as-answer), 4/10 (fixed reader); mean gold rank 1.0, p@k 0.54, 106 tok | `expansion-report.json`, `fixed-reader-report.json`, quoted throughout `RELATED_WORK_AND_POSITIONING` | Contaminated store (F14) | Clean Mem0: 5/10 native (F1); gold-rank-1 pattern *survived* the clean rerun (F7) |
| "Hindsight @ Mem0's budget = 4/10 = Mem0's 4/10; accuracy monotone in budget" | `CONTEXT_AND_PROVENANCE_ABLATION_V1.md` §3, §7 | Both sides superseded: Mem0 side contaminated; Hindsight side computed with the `continue`-on-overflow truncation bug (18/30 contexts wrong) | Corrected: 5/10 = 5/10 at matched budget (F4); corrected curve 5/6/6/7 with the full-arm rise resting partly on a judge-loose label (F3, F5) |
| **"H3 refuted: raw provenance repairs zero of nine Mem0 failures; raw-only worse than compact; `RAW_PROVENANCE_EXPANSION` → DROP"** | Same doc §4, §8; propagated into `MECHANISM_DEPENDENCY_SYNTHESIS` §3 | Every Mem0 arm in that experiment used contaminated compact contexts | **The DROP decision is currently unsupported.** No clean provenance test exists. E3 (§8) re-runs it for ~$0.05 |
| "Memory helped on 8 of 10 probes; both systems roughly doubled with a reader" | Positioning appendix | Mem0 half contaminated | Hindsight half stands (4/10 memory-as-answer → 7/10 with reader); Mem0 half unknown at the memory-as-answer protocol and not worth re-buying |
| "`BROAD_CONTEXT_EXPANSION` → PROMOTE (the only candidate with controlled evidence)" | Same doc §8; synthesis §8 picked its Mem0 arm as the first test | The promotion's evidentiary base (monotone Hindsight curve) weakened under the truncation fix, and the recommended experiment has since **run**: breadth does not lift clean Mem0 (F1, F2) | Volume is dead as the explanation of the gap for Mem0 (H1 falsified on this sample); the kind-of-information hypothesis (H2) is the live one, sharpened to representation (F12) |
| Archaeology's original minimal transplant ("thread timestamp into `_resolve_dates()` / `generate_additive_extraction_prompt`; the prompt's date-preservation instruction already exists") | `HINDSIGHT_INFORMATION_COMPOSITION_ARCHAEOLOGY_V1.md` §9 | Code-citation error: that text described the **unreleased HEAD checkout**, not the pinned running 1.0.6. The real 1.0.6 prompt has no such instruction (F10, F11) | The corrected mechanism reading in F10/F11; recorded in `PM-20260824-c76d8a96` |
| Pilot temporal signal "Hindsight 1/1 vs Mem0 0/1" | pilot artifacts | Never claimed as replication; expansion weakened it (1/3 vs 0/3), and the Mem0 side was contaminated anyway | Clean temporal-reasoning at widest: Mem0 1/3, Hindsight 1/3 — **the aggregate temporal gap between systems is currently zero**; what differs is *which* temporal units each fails, and `gpt4_f420262c` is the one clean Hindsight-only temporal win |

Note the compound status of the earlier headline "Mem0 4/10 vs Hindsight 7/10": the 7 stands (with the F5 caveat), the 4 was contaminated, and the clean gap at widest is 5-vs-7 (or 5-vs-6 strict) — half the size it was reported at.

## 4. External evidence synthesis

No new sweep was run; this consolidates the two primary-source-verified passes plus this document's own arithmetic on their tables.

**What external evidence establishes for the Frankenstein premise, by claim:**

1. **A mechanism lifted over many independent hosts can be uniformly positive.** GRAVITY: +Δ on all 5 independent hosts (Zep, Mem0, A-Mem, LiCoMemory, LightMem), e.g. Mem0 52.6→64.0 — EXTERNAL_MEASURED. A-TMA: overlay gains across 9 hosts (e.g. InsideOut 0.117→0.662) — EXTERNAL_MEASURED, with the caveat that its overlay includes a trained Qwen3B component. This is the strongest external pillar: single-mechanism transplant *onto* hosts works, at least for representation-side anchoring and temporal-state overlays.
2. **Isolated BASE+A / BASE+B deltas from independently-sourced components exist.** AutoMEM: BASE(DCI-Lite)=45.0, +LightMem-graph=67.3, +PlugMem-graph=66.0 — EXTERNAL_MEASURED. BASE+A+B never run; interaction never computed.
3. **A full four-cell grid across two donor systems exists arithmetically, uncomputed by its authors.** Memory-in-the-LLM-Era Table 8: BASE(≈MemoryOS)=37.36, +Tree=41.15, +SP=39.01, +both=43.40 → interaction **+0.60** — EXTERNAL_MEASURED (the cells), INFERENCE (the computation). §10 of the task asked whether +0.60 is stable: **it is not established as stable — see the per-category decomposition below**; it is an existence proof, one benchmark, one table, no variance estimate, and BASE is itself a donor system.
4. **Raw-vs-compact representation effects are real but regime-dependent.** TierMem: raw 0.873 > routed 0.851 > summary 0.755, monotonic on LoCoMo, but the router *regresses* below summary-only on LongMemEval Knowledge-Update — EXTERNAL_MEASURED. Verbatim Chunks: verbatim 43.9% vs extracted 28.0%; **hybrid preserves the gap, substitution forfeits it** — EXTERNAL_MEASURED. Diagnosing R-vs-U: retrieval-method choice swings 20pt, write-strategy 3–8pt with raw ≥ extracted — EXTERNAL_MEASURED.
5. **Reader-side failure with sufficient context is a known, general phenomenon.** Sufficient Context: frontier models answer confidently instead of abstaining — PAPER_CLAIM, directly explaining AAMR's gold-present-reader-wrong majority. Power of Noise: irrelevant additions can *help*; related-but-irrelevant hits hurt most — EXTERNAL_MEASURED (general RAG).
6. **Routers exist only within one system's own design space.** FluxMem (structures, validate→label→train — the sequencing precedent), MemCon (operations, bandit), MemRouter (admission), TierMem (escalation). **No Type-D router (over mechanisms from independently-built systems) found anywhere in ~113 red-team queries** — the surviving novelty claim.
7. **No dominant substrate; routing motivated.** Harness the Memory — PAPER_CLAIM ("no factorial ablation is conducted" — direct quote), from the author cluster most likely to close the gap next.

**Memory-in-the-LLM-Era per-category interaction, computed here (INFERENCE from EXTERNAL_MEASURED cells):**

| Category | BASE | +Tree | +SP | +Both | Interaction S(A+B)−S(A)−S(B)+S0 |
|---|---|---|---|---|---|
| Single-hop | 43.58 | 47.97 | 45.82 | 49.63 | **−0.58** |
| Multi-hop | 35.64 | 34.99 | 35.23 | 36.94 | **+2.36** |
| Temporal | 28.05 | 35.24 | 31.89 | 39.86 | **+0.78** |
| Open-domain | 18.98 | 19.20 | 14.25 | 19.69 | **+5.22** |
| Overall | 37.36 | 41.15 | 39.01 | 43.40 | **+0.60** |

The +0.60 headline decomposes into a sign-mixed set, and the largest positive term (OK, +5.22) is a *rescue* effect: SP alone is 4.73 **below** BASE on that category and the combination merely undoes the damage. **Do not cite this as "synergy exists"; cite it as "interaction terms are computable, non-zero, category-dependent, and sign-mixed — which is precisely why measuring them before routing is worth doing."** That reframing is more honest and, usefully, is a better argument for AAMR's own program than the synergy reading was.

**GRAVITY deep-read conclusions (per task §9).** The transplanted thing is representation-side prompt injection of three anchor families (entity profiles; 4W1O event traces chained heuristically; topic summaries), reranked by query similarity — retrieval is essentially untouched (oracle-retrieval ablation ~0/negative; removing query-expansion <0.5pt) — EXTERNAL_MEASURED. Per-component ablations exist **only on LightMem**: Entity anchors have the largest mean marginal gain there; the single largest drop in the whole paper comes from removing *reranking*. Is there a minimal GRAVITY-derived mechanism with better external evidence than the temporal-grounding candidate? **No — for AAMR specifically.** Reasoning: (a) GRAVITY's own text warns gains shrink where the host already covers the dimension, and Mem0 ships its own entity store while having *no* temporal structure at all (CODE_VERIFIED); (b) AAMR's only measured group-A mechanism trace is temporal (F6–F9), not entity; (c) the reranking lesson targets selection, and AAMR's measured bottleneck is not selection (F7: gold rank 1). The best externally-evidenced mechanism class (anchoring-as-representation) and AAMR's own measured gap *coincide* at temporal anchoring — that coincidence is the strongest justification available for E1, and it is exactly the kind of retargeting the dependency synthesis recommended. What GRAVITY does **not** provide: any per-component ablation on Mem0, or any evidence about *session-timestamp* anchors specifically (its When comes from extracted event tuples).

**TierMem vs AAMR (task §11) — reframed, because the AAMR side of the tension is gone.** The old tension ("TierMem: raw > routed; AAMR: raw provenance repaired nothing, raw-only worse than compact") compared TierMem's numbers against **invalidated** AAMR data (§3). The differentiating variables tabulated in the dependency synthesis (absence-dominant vs presence-dominant failures; 7,400 vs 2,800 raw tokens; multi-hop vs single-hop; trained trigger vs unconditional) remain the right analysis frame, but the empirical anchor must be re-bought. Falsifiable hypotheses, updated:

- **H1 (absence-vs-under-detail):** provenance/raw expansion repairs only failures where gold is absent from the compact representation. On clean data the observable Mem0 failure set at 3000 tokens is 5 units: `ba358f49`, `gpt4_f420262c`, `69fee5aa`, `gpt4_59c863d7`, `gpt4_f49edff3`. Of these, at least two (`69fee5aa` — the corrected value was never captured by either system; `ba358f49` — see below) have a genuine capture/absence component. HYPOTHESIS, testable inside E3 at no extra cost by splitting repairs by gold-adjacent-content presence.
- **H2 (raw-volume threshold):** untested; E3 keeps single-session volume first, and only escalates if H1 shows absence-subset repairs.
- **H3 (multi-hop access):** untested; explicitly deferred (§16).
- **H4 (category alignment):** testable inside E3's per-category split for free.

## 5. Mechanism × failure-mode × operating-regime matrix

Failure modes observed in AAMR's own clean data: **TEMPORAL_COMPOSITION** (facts present, dates stripped, ordering/arithmetic needed: `f420262c` full, `f49edff3` partial, `ba358f49` plausible), **SUBJECT_ATTRIBUTION** (bare fact misattributed: `ba358f49` reader answer "context does not include your age" while `Is 32 years old` sat in context — AAMR_MEASURED), **SCATTERED_AGGREGATION** (counting across many items: `59c863d7`), **UPSTREAM_CAPTURE_GAP** (corrected value never stored by either system: `69fee5aa`), **GOLD_PRESENT_READER_WRONG** residue (Sufficient-Context-style overconfidence).

| Mechanism | Class | Target failure mode | Operating regime where it helps | Regime where it hurts / is inert | External evidence | AAMR evidence | Isolable? | Testable without gold? |
|---|---|---|---|---|---|---|---|---|
| Temporal anchor in delivered representation (When-field / rendered timestamp) | REPRESENTATION (read-side variant) / WRITE (Hindsight's native variant) | TEMPORAL_COMPOSITION | Temporal-ordering, relative-date, age/duration arithmetic questions; wide contexts where dates disambiguate many similar items | Inert where no temporal composition needed; possible harm if a wrong anchor turns vague-harmless into confident-wrong (archaeology failure-prediction) | GRAVITY anchor family (EXTERNAL_MEASURED, 5 hosts, but event-tuple When, not session-date); APEX-MEM temporal addressing (PAPER_CLAIM) | F8/F9 correlation on 1 full + 1 partial + 1 plausible probe; calibration F11 proves the *write-side date alone* is not this mechanism | **Yes — cleanly** (read-side: one context-assembly function) | **Yes** (timestamps come from corpus metadata, not gold) |
| Temporal resolution at extraction (date + instruction; facts stored with absolute dates) | WRITE + REPRESENTATION | TEMPORAL_COMPOSITION + retrieval of temporal facts (embeddings now contain dates) | Same as above, plus queries that *search* by time | Changes stored text globally: dedup behavior, embedding neighborhoods; regression surface is wider | Hindsight does this natively (CODE_VERIFIED); Verbatim-Chunks-adjacent (specificity retention) | F11: date-only inert; date+instruction untested | Yes, but only via re-ingest (vendor patch, third change) | Yes |
| Source/subject attribution tag (Involving-field analogue) | REPRESENTATION (read-side) | SUBJECT_ATTRIBUTION | Contexts mixing user-facts with facts about third parties; possessive questions ("my age", "my friend's…") | Inert where attribution unambiguous; token cost trivial | Hindsight's `Involving:` field (CODE_VERIFIED); no isolated external ablation found | `ba358f49` reader transcript (single probe — under-replicated, archaeology candidate 3) | Yes (same assembly function) | Yes |
| Redundant fact accumulation | WRITE / STORE | SCATTERED_AGGREGATION (findability in long lists) | Counting/enumeration over long scattered histories | Dilutes precision everywhere else; directly conflicts with contamination-hygiene; token cost | Hindsight no-dedup (CODE_VERIFIED); no external isolated ablation | `59c863d7` correlation; **failed sharp-correlation anti-storytelling check** | Poorly (blunt system-wide dedup relaxation) | Partially |
| Raw provenance / verbatim chunk supplement | CONTEXT / RETRIEVAL | Under-detail: qualifiers/relations lost by extraction; UPSTREAM_CAPTURE_GAP is *not* fixable this way | TierMem regime: absence-dominant compact failures, large raw volume, multi-hop | AAMR's old data said inert-here — but that data is invalidated; TierMem says trigger (not content) is category-dependent | TierMem, Verbatim Chunks, Eywa, Diagnosing-R-vs-U (all EXTERNAL_MEASURED/PAPER_CLAIM) | **None valid** (§3) | Yes (context-assembly) | Yes |
| Query-conditioned reranking of retrieved items | RETRIEVAL (selection) | Wrong item order under budget truncation | Hosts/regimes with poor ranking; large candidate sets, tight budgets | Inert where ranking already good | GRAVITY's largest single ablation effect (EXTERNAL_MEASURED, LightMem) | **Wrong bottleneck here**: gold rank already 1 (F7); no budget truncation at 3000 (F2) | Yes | Yes |
| Event-chain anchors (4W1O tuples, heuristic chaining, rerank) | REPRESENTATION (heavier) | TEMPORAL_COMPOSITION over multi-event narratives | Long multi-session narratives | Build cost; overlaps simpler temporal anchor | GRAVITY event anchors (EXTERNAL_MEASURED, LightMem only) | None | Yes, moderate build | Yes |
| Sufficiency gate / escalation trigger | ROUTING | Wasted expansion; hidden category-specific effects | Only meaningful once ≥1 expansion mechanism has a measured positive regime | Premature now; TierMem shows triggers are the regime-dependent part | TierMem router (EXTERNAL_MEASURED), Eywa rule table (PAPER_CLAIM) | None | Needs a validated mechanism first | Partially |
| Tree / hierarchical organization; segment processing | STORE / CONSOLIDATION | Cross-segment retrieval at scale | Large memory banks, open-domain + temporal (per Memory-in-LLM-Era) | OK category: SP-alone *hurts* (−4.73) — sign-mixed | Memory-in-LLM-Era (EXTERNAL_MEASURED, non-factorable coupling) | None; AAMR stores are 200–600 items — likely below the regime where trees pay | Poorly (SP requires Tree) | Yes |
| Entity resolution (trigram+union-find) | RETRIEVAL | Entity-name-variation misses | Hosts with ranking failures from surface variants | Inert where gold rank already 1 | Hindsight shipping code (CODE_VERIFIED) | Superseded as next test by F7 | Yes | Yes |

**Dependency statements (task §8), each labeled:**

- Temporal grounding helps only temporal-composition questions — **SUPPORTED** (AAMR: all its support sits in temporal/arithmetic probes; GRAVITY's anchors are category-targeted by design). Not MEASURED: no BASE+X run yet.
- Raw detail helps only when compact representation lost qualifiers/relations — **SUPPORTED externally** (TierMem 28.8% over-generalization failures; Verbatim 78.8% extraction gaps), **UNRESOLVED at AAMR** (prior contrary evidence invalidated).
- Raw detail is useless when compact already retained gold and relations — formerly "MEASURED at AAMR", now **UNRESOLVED** (same invalidation).
- Redundancy helps findability under scattering but hurts via dilution/contamination — **PLAUSIBLE** (one supporting probe, one failed control; CODE_VERIFIED asymmetry exists).
- Tree organization pays only at large store size — **PLAUSIBLE** (Memory-in-LLM-Era regime; AAMR stores likely below threshold — INFERENCE).
- Structural anchors reduce utilization failure rather than retrieval failure — **SUPPORTED** (GRAVITY oracle ablation; AAMR F7+F12 point the same way).
- Retrieval precision and answer accuracy can conflict — **MEASURED, small-n** (Mem0: p@k high, gold rank 1, still loses at wide breadth; Power-of-Noise externally).
- Breadth helps only specific question types and can hurt others — **MEASURED, small-n** (Mem0 3000-arm loses `f49edff3` that 500/1000 had; Hindsight gains `multi-session-1` only at 1000+; Harness-the-Memory externally).
- Escalation triggers, not escalated content, are the regime-dependent part — **SUPPORTED external** (TierMem Knowledge-Update regression), untested at AAMR.

## 6. Candidate board

Eight candidates max; entity resolution, tree/SP, event-chains, sufficiency gate and redundancy are **deliberately off the board** (wrong bottleneck, wrong regime, too big, premature, failed control — respectively, per §5).

| # | Candidate | Origin | Target failure | AAMR support | External support | Mechanistic clarity | Minimal transplant | Cost to test | What would falsify it |
|---|---|---|---|---|---|---|---|---|---|
| C1 | **TEMPORAL_ANCHOR_AT_CONTEXT** — render each retrieved memory as `- [YYYY-MM-DD] {fact}` from already-persisted `evidence_times` | Hindsight `When:` (functional transplant, read-side); archaeology candidate 1; GRAVITY anchoring class | TEMPORAL_COMPOSITION | F8 (dates absent), F9 (donor mechanism), archaeology checklist: differentiates A-probe f420262c fully, C-probe f49edff3 partially; ba358f49 plausible | GRAVITY 5-host anchoring; APEX-MEM | **Total** — one deterministic string change at context assembly | Modify arm-builder only; no vendor code, no ingest | ~$0.02–0.05 | Zero predicted flips (f420262c, ba358f49, f49edff3) across both breadth points, no transcript behavior change |
| C2 | **SOURCE_TAG_AT_CONTEXT** — prefix each item with its provenance subject ("user fact") | Hindsight `Involving:`; ba358f49 misattribution transcript | SUBJECT_ATTRIBUTION | Single probe (under-replicated, flagged by archaeology's own gate) | Involving-field exists in donor; no isolated external ablation | High | Same assembly function | ~$0.01 marginal inside E1 | ba358f49 does not flip and no attribution language changes in transcripts |
| C3 | **TEMPORAL_RESOLUTION_AT_EXTRACTION** — reference date + explicit resolve-relative-dates instruction at write time | Hindsight write-time grounding; F10/F11 corrected mechanism reading | TEMPORAL_COMPOSITION + temporal retrieval | F11 (necessity of the instruction half); patch infrastructure already built and vendored | Hindsight native; Verbatim-Chunks specificity logic | High, but wider blast radius (stored text, embeddings, dedup) | The existing two-line patch + one prompt-instruction line (**requires the pending third-change approval**) + re-ingest | ~$0.80 (re-ingest dominated) | Calibration: resolved dates fail to appear; 10-unit: no temporal-probe flip that C1 didn't already achieve |
| C4 | **CLEAN_RAW_PROVENANCE_RETEST** — re-run compact+raw / raw-only arms on the clean store, split by category and by gold-adjacent-content presence | AAMR's own invalidated Experiment B; TierMem/Eywa/Verbatim externally | Under-detail + tests H1/H4 | None valid (that's the point) | Strong external (three papers) | High | Existing (already-written, frozen) provenance code path over clean contexts | ~$0.05 | 0 repairs again, now on clean data → DROP becomes valid and externally-tensioned finding worth writing up |
| C5 | Query-conditioned rerank | GRAVITY ablation | Selection under truncation | Negative fit: F7 | Strongest single-component external effect | Total | Cosine reorder before truncation | ~$0.01 | — (do not run now: no selection failure exists to fix; would be harness validation, not discovery) |
| C6 | Event-chain anchors (4W1O + chaining + rerank) | GRAVITY event anchors | Multi-event temporal narratives | None | LightMem-only ablation | Medium | LLM tuple pass + heuristic chain + rerank | ~$1+ | Deferred: strictly dominated by C1 for first contact with the failure mode |
| C7 | Redundancy preservation (dedup relaxation) | Hindsight no-dedup | SCATTERED_AGGREGATION | 1 probe + 1 failed control | None isolated | Low (blunt) | System-wide dedup off | ~$0.80 | Deferred: failed anti-storytelling gate; contamination-risk conflict |
| C8 | Sufficiency/escalation gate | TierMem/Eywa | Wasted expansion | None | Trigger-regime evidence | Medium | Needs a validated expansion mechanism first | — | Premature by definition until C3/C4 resolve |

## 7. Candidate ranking (decision scores, 0–5; not probabilities)

| Axis | C1 anchor@ctx | C2 source-tag | C3 resolve@extract | C4 provenance-retest | C5 rerank | C6 event-chains | C7 redundancy | C8 gate |
|---|---|---|---|---|---|---|---|---|
| EVIDENCE_STRENGTH | 4 | 2 | 3 | 2 (external only) | 3 | 2 | 1 | 2 |
| FIT_TO_AAMR_FAILURES | 4 | 3 | 4 | 2 | 0 | 3 | 2 | 1 |
| PORTABILITY | 5 | 5 | 3 | 4 | 5 | 3 | 2 | 2 |
| MECHANISTIC_CLARITY | 5 | 5 | 4 | 4 | 5 | 3 | 2 | 2 |
| CHEAP_FALSIFIABILITY | 5 | 5 | 3 | 5 | 5 | 2 | 2 | 1 |
| GENERALIZATION_POTENTIAL | 4 | 3 | 4 | 3 | 3 | 3 | 2 | 3 |
| INTERACTION_POTENTIAL | 4 | 4 | 4 | 3 | 2 | 3 | 2 | 4 |
| REGRESSION_RISK (5 = high) | 1 | 1 | 3 | 1 | 1 | 2 | 4 | 2 |
| **Decision sum (higher better, risk subtracted)** | **30** | **26** | **22** | **22** | **22** | **17** | **9** | **13** |

C5's sum is inflated by cheapness axes; its FIT of 0 is disqualifying — cheap tests of the wrong bottleneck are how budgets die of a thousand cuts. C1 leads on every axis that matters and carries the lowest regression risk.

## 8. Top 3 experiments

Constraint honored: each unlocks a named decision; none is run for novelty.

### EXPERIMENT #1 — `arena-base-plus-x-v2`: read-side temporal anchoring micro-grid

- **QUESTION:** Does rendering per-memory session dates (and/or a source-attribution tag) into Mem0's delivered context flip the specific units whose failures the archaeology attributed to missing temporal/attribution structure?
- **WHY NOW:** Volume is eliminated (F1/F2); representation is the live hypothesis (F12); the write-side minimal patch is calibrated-inert (F11); the required data (`evidence_times`) is already persisted, so the marginal cost is reader+judge only.
- **MECHANISM:** C1 (+C2 as the second axis of the same grid).
- **BASE:** frozen clean Mem0 arms at two operating points — `mem0_original` (native, 5/10) and `mem0_3000` (whole store, 5/10) — byte-identical to `mem0-breadth-arms.json`.
- **TREATMENT ARMS:** (A) `+TIME`: each item `- [YYYY-MM-DD] {fact}`, date = the item's own `evidence_times` entry, joined positionally via the verified prefix property; (B) `+SRC`: each item `- (user fact) {fact}`; (A+B): both — **gated: run only if A or B produces ≥1 predicted flip**; (P) `+PLACEBO`: `- [item-0NN] {fact}` at matched token cost, run only if A shows flips (separates content-of-anchor from tokens-of-anchor; note the breadth curve itself already shows added tokens alone do not help Mem0 — F1).
- **WHAT EXACTLY CHANGES:** the context-assembly string for each item. Nothing else.
- **WHAT MUST STAY FROZEN:** selection (`a4d252f1…`), stores (no ingest), item order, reader model/prompt/params (hash-pinned), judge protocol/commit, blinding procedure, budgets.
- **PREDICTED PROBES (register before running):** `gpt4_f420262c` flips (+TIME); `ba358f49` flips (+TIME, +SRC, or only +BOTH — the reader needs both the anchor for "next year"/"is 32" and the attribution of the age fact); `gpt4_f49edff3` may flip (+TIME, boundary — Hindsight recovered 2/3 dates and still failed, so a non-flip is uninformative against the mechanism).
- **PREDICTED NON-EFFECTS (equally binding):** `69fee5aa` must NOT flip (corrected value never stored — no date can conjure it); `gpt4_59c863d7` not expected to flip (counting/scatter, not temporal); the 5 currently-correct units must not regress (regression watch: `98f46fc6`, `58bf7951`, `6a27ffc2`, `eace081b`, `311778f1`).
- **PRIMARY METRIC:** count of *predicted* flips net of regressions, per arm, per operating point. **SECONDARY:** overall accuracy; transcript-level behavior (does the reader cite dates/attribution it previously lacked); token deltas per arm.
- **EXPECTED RESULT if mechanism real:** +1 to +3 on predicted units at one or both operating points, zero regressions, transcripts show date usage.
- **FALSIFICATION RESULT:** zero predicted flips at both operating points AND transcripts show the reader ignoring rendered dates → the *representation* variant of temporal grounding is dead on this sample; the archaeology's candidate 1 must be demoted or reinterpreted (e.g. Hindsight's advantage lives in resolved-event dates, not session dates — which is C3's separate hypothesis).
- **REGRESSION CONDITION:** any currently-correct unit lost in a treatment arm → stop, analyze transcript before any further arm.
- **ESTIMATED COST:** 2 base points already paid; 2–5 treatment arms × 10 reader calls × ~$0.0006 + judging ~$0.00005/call ≈ **$0.02–0.04**. **HARD CAP: $0.10.**
- **STOP CONDITION:** cap, or any harness anomaly (context hash mismatch vs frozen arms).
- **DECISION UNLOCKED:** whether representation-side temporal anchoring becomes AAMR's first validated transplant (→ E2 and Stage 2 replication), or dies cheaply (→ E3's provenance retest and C3's write-side variant become the only live temporal candidates).

### EXPERIMENT #2 — `arena-base-plus-x-v3`: write-side temporal resolution at extraction (calibration-gated)

- **QUESTION:** Does grounding extraction with the real session date *plus an explicit instruction to resolve relative time expressions* produce stored facts with absolute dates, and does that improve the same temporal probes end-to-end (including via retrieval, which E1 cannot touch)?
- **WHY NOW (conditional):** Only after E1. If E1 shows the reader *uses* anchors, C3 tests whether write-time grounding adds anything beyond read-time rendering (resolved event dates vs session dates; embedding effects). If E1 is null *because transcripts show the reader ignoring correct anchors*, C3 is pointless (same reader downstream) — skip to E3/pivot. If E1 is null because session dates were the *wrong* anchor (reader used them, still failed), C3's resolved-dates variant is precisely the next distinct hypothesis.
- **MECHANISM:** C3. BASE: unpatched 1.0.6 clean ingest (exists). TREATMENT: patched ingest — the two vendored changes + one added instruction line (+ a resolved-dates few-shot swap if calibration demands it).
- **PREREQUISITE GATE (calibration, ≤$0.02):** extend the existing 1-case calibration to ~5 synthetic cases ("today", "yesterday", "next year", "last month", none); gate = resolved absolute dates appear in extracted fact text on ≥3 of 4 date-bearing cases with zero fabricated dates on the none-case. Fail → STOP, $0.78 saved, finding recorded (the 1.0.6 extraction prompt resists cheap temporal grounding — itself a publishable footnote against casual "just fix the prompt" claims).
- **WHAT CHANGES / FROZEN:** changes: extraction prompt content (via the already-vendored patch mechanism), hence stored fact text. Frozen: selection, reader, judge, budgets, retrieval settings, embedder.
- **PREDICTED PROBES:** same temporal set as E1, plus: stored-fact audit — the four `f420262c` flights should now carry absolute dates in stored text; `ba358f49`'s "next year" should resolve.
- **PREDICTED NON-EFFECTS:** `69fee5aa` must not flip; knowledge-update category must not regress (dates attached to superseded facts could plausibly *help or hurt* staleness handling — watch, don't predict).
- **PRIMARY METRIC:** predicted temporal flips net of regressions vs BASE **and vs BASE+E1-winner** (the marginal value over the read-side fix is the decision-relevant number).
- **FALSIFICATION:** calibration gate fails; or 10-unit run shows no marginal gain over E1's winner.
- **ESTIMATED COST:** calibration $0.02 + patched re-ingest ~$0.76 + arms/judging ~$0.05 ≈ **$0.83**. **HARD CAP: $1.00.** STOP at calibration-fail or cap.
- **DECISION UNLOCKED:** whether AAMR's first *write-side* transplant is worth anything beyond its read-side shadow — i.e., whether Frankenstein work should modify donors' write paths at all, or live entirely at context assembly. Also unlocks C3-vs-C1 as the first candidate *pair* for a genuine cross-stage interaction grid (Stage 4).

### EXPERIMENT #3 — `arena-provenance-clean-v2`: clean raw-provenance retest with category split

- **QUESTION:** On the *clean* store, does appending the top-1 hit's raw source session repair any Mem0 failure — and if any, are repairs concentrated in absence-type failures (H1) and specific categories (H4)?
- **WHY NOW:** The DROP decision currently cited across two research documents rests entirely on invalidated data (§3). Three external papers (TierMem, Verbatim Chunks, Eywa) predict the opposite sign. $0.05 closes an open contradiction between AAMR's ledger and the external literature, whichever way it lands.
- **MECHANISM:** C4. BASE: clean `mem0_original` and `mem0_3000` arms. TREATMENT: compact+raw and raw-only arms rebuilt from the clean store using the frozen, already-corrected provenance code path (session-date mapping, UNOBSERVABLE rule unchanged).
- **WHAT CHANGES / FROZEN:** only the appended raw text; same reader/judge/selection; token deltas reported.
- **PREDICTED PROBES:** if TierMem's absence-hypothesis transfers: `ba358f49` (whose raw session contains the user's age statement verbatim with its date context) is the most likely repair; `69fee5aa` repairs only if the correction exists in *some* stored session's raw text despite never being extracted — informative either way for the capture-gap taxonomy.
- **PREDICTED NON-EFFECTS:** `f420262c` unlikely to repair via raw (the dates are scattered across four sessions; top-1 provenance reaches one) — a non-repair there does NOT falsify temporal anchoring.
- **PRIMARY METRIC:** `COMPACT_WRONG_RAW_FIXES` and `RAW_CAUSES_REGRESSION`, per category, split by gold-adjacent-content presence in the compact context.
- **EXPECTED / FALSIFICATION:** ≥1 repair in the absence subset → H1 alive, provenance re-enters the candidate list as a *conditional* mechanism (and C8's gate becomes relevant later). 0 repairs again → DROP becomes valid on clean evidence, and AAMR owns a genuinely interesting, externally-tensioned negative worth stating next to TierMem/Verbatim (boundary-dependence of "raw beats extraction").
- **ESTIMATED COST:** ~18 reader calls + judging ≈ **$0.02–0.05**. **HARD CAP: $0.10.** STOP: cap or provenance-mapping anomaly.
- **DECISION UNLOCKED:** whether the raw/verbatim axis stays dead at AAMR (freeing all future budget for representation mechanisms) or revives as the second mechanism family.

## 9. Stage-gated roadmap and budget ladder

Ledger context: total project API spend to date **$12.07** (AAMR_MEASURED, `spend-ledger.jsonl`); the arena's cost structure is ingest-dominated (Mem0 ~$0.074/unit; Hindsight ~$0.26–0.44/unit; reader ~$0.0006/call; judge ~$0.00005/call).

| Stage | Content | MAX SPEND | ENTRY condition | EXIT condition | STOP condition |
|---|---|---|---|---|---|
| **0 — free analysis** | This document; register E1 per-unit predictions in project memory *before* any call; strict-judge re-read of `98f46fc6` full-arm label (paper-only re-adjudication, no API); confirm E1 arm-builder determinism against frozen hashes | $0.00 | — | Predictions registered append-only | — |
| **1 — cheap causal test** | E1 (+ E3 may run in the same session; both are frozen-context reader/judge work) | $0.20 combined | Stage 0 exit | Per-unit flip table vs registered predictions, both experiments | Any cap; any frozen-input hash mismatch; any regression on a currently-correct unit pending transcript analysis |
| **2 — replication** | Whatever produced a predicted positive Δ in Stage 1, replicated on **fresh units**: +8–10 never-used LongMemEval-S units biased to temporal-reasoning/multi-session (new Mem0 ingest, no Hindsight needed), BASE vs winning treatment only | $1.00 | ≥1 predicted flip net of regressions in Stage 1 | Effect present on fresh units (≥2 net predicted flips there) → mechanism A **validated at Tier-E-replicated**; else demoted | Cap; contamination check fails on new ingest (store_after_reset must be 0) |
| **3 — second mechanism** | E2 (calibration-gated write-side), or — if E2's entry logic voids it — promotion of E3's surviving branch (conditional provenance) to its own BASE+B test on the Stage-2 unit set | $1.00 | Stage 1 complete; E2 entry logic (§8) satisfied | Isolated Δ_B measured on the same frozen sets as Δ_A | Calibration gate fail (STOP with finding); cap |
| **4 — interaction test** | `BASE / +A / +B / +A+B` on the pooled 18–20-unit set, interaction = S(A+B)−S(A)−S(B)+S0, per-category | $0.30 (read-side pair) / $1.00 (if B is write-side: one more patched ingest) | **Both** A and B independently validated (Stage 2-grade) with predicted regimes registered | Interaction term computed and recorded, whatever its sign | Cap |
| **5 — held-out confirmation** | Sealed I1 split: ~10 fresh, never-inspected units (LongMemEval-S remainder or LongMemEval-V2), key externally witnessed, one shot, BASE vs best validated configuration | $2.50 | Stage 4 exit with non-negative interaction, or a single Stage-2-validated mechanism if Stage 3/4 died | Held-out Δ reported, whichever way | One shot only — no reruns whatever the result |
| **6 — controller** | Only per §11 gates | TBD, separately approved | §11 | — | — |

Cumulative worst-case through Stage 5: **≈ $5.00**. Expected realistic path: **≈ $2.5–3.5**. Rule inherited from doctrine: every stage's spend requires the previous stage's recorded decision — no "$1 here, $1 there".

## 10. Interaction plan

Best-motivated pairs, in order:

**Pair 1: C1 (+TIME) × C2 (+SRC)** — same stage (context assembly), trivially co-installable, measured *inside E1* at near-zero marginal cost (the gated +BOTH cell). WHY COMPLEMENTARY: they repair different reader failures on the *same* unit (`ba358f49` plausibly needs both the anchor and the attribution). WHY THEY MAY INTERFERE: prefix clutter — two annotations per line could push the reader to skim structure instead of content (Power-of-Noise cuts both ways). A-failure-mode: wrong-anchor confident-dating. B-failure-mode: attribution tag wrong for third-party facts stored from user messages ("Friend Rachel is getting married" is *about* Rachel, sourced from user — tag wording must say "from user's message", not "about user"). EXPECTED A+B: ≥ max(A,B); INTERACTION TO MEASURE: flips(A+B) − flips(A) − flips(B) + 0 on the predicted-unit set. Honest caveat: at n=10 this is a direction-check, not an estimate — the real interaction measurement belongs to Stage 4's pooled set.

**Pair 2: C1/C2 winner (read-side representation) × C3 (write-side resolution)** — cross-stage pair, the scientifically interesting one: does write-time grounding add anything once read-time anchoring exists? Redundant (interaction ≈ −min(Δ)) is a perfectly good publishable answer: it would say the cheap, non-invasive transplant captures the whole effect — mechanism value lives at context assembly, not in donor code surgery.

**Pair 3: C1 × C4-conditional (temporal anchor × raw escalation)** — only if E3 revives provenance: anchors fix composition over present facts; raw fixes under-detail/absence. Predicted near-orthogonal (different failure units). This is the pair that would first justify a *routing* question (C8), because the raw arm has real token cost and a trigger would need to decide when it pays.

Per instruction: no A+B is recommended anywhere until A and B separately show signal — the E1 +BOTH cell is gated accordingly.

## 11. Frankenstein gate and controller gate

**FIRST STATIC FRANKENSTEIN** (a configuration adopted as a build, not an experiment arm) may be assembled when ALL hold:

1. Mechanism A has a positive Δ, replicated on fresh units (Stage 2 exit).
2. Mechanism B likewise, independently.
3. The BASE/+A/+B/+A+B grid has been run on ≥18 units with interaction ≥ −ε (ε = 1 unit; a mildly redundant pair may still be adopted if each is individually cheap and non-regressive — redundancy is a cost question, interference is a stop question).
4. Predicted operating regimes for A and B are written down and at least category-level consistent with the observed per-category deltas.
5. No unexplained regression on any previously-correct unit survives transcript analysis.

Assessment of whether this is the right gate: yes, with one deliberate deviation from the earlier positioning-document version — that version required interaction measurement only before a *controller*; this gate requires it before even a static combination is *adopted*, because Memory-in-the-LLM-Era's own table (§4) shows per-category sign-mixing that an aggregate would hide. The E1 +BOTH cell does not violate this gate: it is an experiment arm inside a grid, not an adopted build.

**CONTROLLER GATE** (Stage 6). Minimum conditions, FluxMem-sequenced (validate → regime labels → train selector), adapted to independently-sourced mechanisms:

1. ≥2 mechanisms validated per the Frankenstein gate, with **measured, category-resolved** regimes.
2. Demonstrated regime *variance*: at least one unit-class where A>B and one where B>A (or a mechanism-vs-off tradeoff). Current data has almost none — at widest breadth D=0 (F6): Hindsight never loses to Mem0, and Mem0's own breadth arms show only +1 unit of oracle-over-best-fixed headroom (7/10 oracle-across-arms vs 6/10 best fixed — AAMR_MEASURED, this pass). **A router with no measured regime variance has nothing to route.**
3. Gold-free features available at inference (query-type/shape à la Eywa; candidate-set statistics; the retrieval-confidence/score-margin gap flagged in the dependency synthesis — still unprecedented anywhere, still worth a free check on our own data first).
4. A cost model: the router must beat both fixed configurations on accuracy-per-dollar, not just accuracy — TierMem's router loses to raw-only on accuracy and wins on cost; that is the honest shape of the claim to aim for.
5. Training data scale: ≥50–100 labeled units (implies Phase-D-scale corpus, not the current 20).

## 12. Continue / Pivot / Stop criteria

- **CONTINUE** as long as each stage exits with a recorded decision and ≤ one mechanism family has died.
- **PIVOT triggers:**
  - E1, E2, E3 all null (three independent, well-motivated transplants at zero effect): the mechanism-transplant hypothesis is **not yet refuted in general, but is refuted at this arena's scale** — the honest reading would be that the 10-unit LongMemEval-S regime bottoms out at reader/judge behavior, not memory representation. Pivot options, in order of preference: (a) answer-time interventions (Sufficient-Context-style sufficiency prompting — cheap, same harness), (b) Phase D early: a bigger arena (LongMemEval-V2 / MINTEval) where representation effects have room to appear, (c) router-over-whole-systems — currently *unsupported* by our own data (D=0; routing needs variance), so it is a fallback only if a bigger arena surfaces variance.
  - Judge-strictness re-read (Stage 0) collapses the Hindsight full-arm advantage AND E1 is null → the entire Mem0-vs-Hindsight wide-context gap was 1 loose label + noise; pivot to Phase D immediately (the current arena would have nothing left to explain).
- **STOP (Frankenstein hypothesis, this arena):** three nulls above *plus* a Stage-2-scale replication failure of any Stage-1 positive (i.e., even apparent signals do not replicate). What remains valuable regardless: the contamination/reset methodology (F14), the equal-budget equivalence result (F4), the truncation-bug case study, the calibration-before-spend discipline (F11 — a $0.0016 measurement that saved a $0.80 experiment), and a documented, externally-tensioned negative on transplantability at small scale — publishable per the positioning document's own "if they mostly show redundancy, that is a finding" framing.

## 13. Major uncertainties

1. **Judge looseness** (F5): one known loose label sits exactly on the wide-context gap; unknown how many others. Stage 0 re-read is free and mandatory.
2. **Single-generation cells**: every arm × unit is one generation at temp 0; the recorded `medium`-slot non-monotonicity proves single-cell flips occur without cause. Mitigation: prediction-anchored scoring (a random flip elsewhere does not count as success), replication stage.
3. **n=10, confirmatory, non-random**: temporal-reasoning over-represented by design; nothing here generalizes without Phase D. All effect sizes are 1–3 units by construction.
4. **Single reader model** (deepseek-chat): all utilization findings could be reader-idiosyncratic. Cheap probe if E1 succeeds: one replication arm under a second reader before Stage 5.
5. **Hindsight-side unreplicated**: the corrected Hindsight arms were judged once; the matched-arm 4→5 move under the truncation fix shows these numbers move under harness corrections.
6. **Third-change approval pending** for C3's instruction line — E2 is blocked on an explicit user decision, by design.
7. **Session-date vs event-date**: C1 anchors with session dates; Hindsight's When is often a *resolved event date* ("before November 17, 2022"). If E1 fails where Hindsight succeeded, this distinction is the first suspect (and C3 tests exactly it).
8. **`raw/arena-expansion-v1/mem0.json` instability** (silently overwritten by newest run — recorded in refreeze v2): any future experiment touching it must pin per-unit values, not re-read the file.

## 14. What NOT to test yet

- **Controller/router** — gate §11 unmet on every condition; no regime variance measured (D=0).
- **Redundancy relaxation (C7)** — failed anti-storytelling control; direct conflict with contamination hygiene; blunt.
- **Entity resolver transplant** — retrieval-side fix for a non-retrieval bottleneck (F7); keep for a host/regime where ranking actually fails.
- **Query-conditioned rerank (C5)** — same reason; revisit only when a truncation-under-budget regime returns.
- **Event-chain anchors (C6)** — strictly dominated by C1 for first contact; build only if C1 validates and multi-event narratives remain broken.
- **Tree/SP organization** — store sizes here (200–600 items) are likely below the regime where hierarchy pays; Phase-D-scale question.
- **Second-hop provenance** — only if E3 revives single-hop provenance.
- **Second benchmark (MINTEval/LongMemEval-V2)** — Phase D entry is gated on the current arena being explained or exhausted (§12), not on curiosity.
- **Any new Hindsight ingest** — nothing in the next three experiments needs one dollar of the most expensive component in the ledger.

## 15. Shortest realistic path to "Frankenstein works" proof

Definition of the proof (narrow, honest): *two mechanisms, each sourced from an independently-built system, each with a replicated positive isolated Δ on a frozen common host, their combination measured with interaction ≥ 0, surviving one sealed held-out set.* Not a paper, not generality — the existence proof.

| Step | What | Units | Spend |
|---|---|---|---|
| 0 | Predictions + strict-judge re-read | 10 | $0.00 |
| 1 | E1 grid (+E3 alongside) | 10 | ~$0.06 |
| 2 | Replicate winner on fresh temporal-biased units | +8–10 | ~$0.85 |
| 3 | Second mechanism (E2 calibration-gated, or provenance branch) | same sets | ~$0.85 |
| 4 | BASE/+A/+B/+A+B pooled grid | 18–20 | ~$0.15–1.00 |
| 5 | Sealed held-out, one shot | +10 | ~$1.60–2.50 |

**Totals: 2 mechanisms, ~28–30 probes total (≥18 fresh beyond the current frozen 10), 1 replication round per mechanism, 5 paid stages, ≈ $3.5 expected / $5.5 worst-case.** Calendar time is dominated by decision latency, not compute; every step is hours.

If every step lands positive, the endpoint is exactly the thing the red-team pass confirmed nobody has published: a neutral-host, cross-system, factorial interaction measurement with validated mechanisms — with a sealed replication behind it.

## 16. Failure path (worst case, pre-committed reading)

If **temporal grounding fails** (E1 null with reader-ignores-anchors transcripts, E2 calibration-blocked or null): the representation family loses its flagship; C4/raw and answer-time interventions inherit the budget. The archaeology's method (close-read → anti-storytelling gates → code verification) remains sound — it produced a candidate that was *cheap to kill*, which is the method working, not failing.

If **the GRAVITY-derived family fails too** (C1 null and C6 never justified): representation-side injection as a class is dead on this arena; the Verbatim/TierMem raw axis (C4) is the only remaining externally-supported family; if it also fails —

If **all three fail**: the Frankenstein hypothesis is **not** globally refuted (external multi-host evidence stands; our arena is 10 units of one benchmark with one reader), but AAMR's cheapest honest sentence becomes: *"at small scale, on LongMemEval-S, with a frontier reader, memory-representation transplants do not move outcomes; the bottleneck is elsewhere (reader behavior / judge construct / probe design)."* That sentence, with the contamination and calibration case studies behind it, is a real methods contribution. The pivot then is arena-scale (Phase D) or answer-time mechanisms — not more transplants of the same size, and not a router (which would inherit all of the above problems plus training variance).

The project retains value in the worst case through: the harness itself (five systems, frozen, replicable), the invalidation discipline (F14, truncation, calibration-stop — three caught-and-documented instrument failures in one day), the equal-budget equivalence finding (F4 — genuinely not in the literature for this pairing), and the negative itself.

## 17. The main question, answered in parts

**"Czy składanie mechanizmów pamięci może działać?" — PARTIALLY, with the following decomposition:**

- **A. External evidence:** **YES for single-mechanism transplants** (GRAVITY ×5 hosts, A-TMA ×9 hosts — EXTERNAL_MEASURED); **PARTIAL for combination** (AutoMEM's isolated deltas without the +A+B cell; Memory-in-the-LLM-Era's computable but donor-based, sign-mixed grid).
- **B. AAMR evidence:** **diagnostic only.** A code-verified, probe-anchored candidate mechanism exists; a calibrated instrument exists; zero causal transplant results exist. The strongest AAMR contribution so far is negative-space: volume eliminated, retrieval eliminated, selection eliminated — representation left standing.
- **C. Single-mechanism transplant:** externally YES; at AAMR **UNRESOLVED, cheap to resolve** (E1 is the test).
- **D. Multiple mechanisms combined:** externally PARTIAL (no neutral-BASE +A+B anywhere); at AAMR untested.
- **E. Interaction-aware Frankenstein:** **nobody has done it** (red-team confirmed across ~113 queries); this is the open lane, and §15 prices reaching it at under $6.
- **F. Learned controller:** externally YES within-system (FluxMem/MemCon/TierMem); Type-D (cross-system) — nobody; at AAMR far behind gates, and currently *counter-indicated* by our own D=0 / no-variance data.

## 18. Immediate next actions (no spend)

1. Register E1's per-unit predictions (§8) in project memory, append-only, before any implementation.
2. Strict-judge paper re-read of `gpt4_98f46fc6` (Hindsight full arm) and annotation of F5's impact on the headline gap.
3. Obtain the pending decision: approval of the C3 "third change" (instruction line) *conditionally* on the E2 entry logic, so Stage 3 is not blocked mid-flight.
4. Then, and only then, the Stage 1 permission request: E1 + E3, combined cap $0.20.

*Stopping here per instruction: nothing below Stage 0 has been implemented, no arm built, no call made.*
