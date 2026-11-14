> **Publication note, 2026-11-12.** Written on 2026-08-24 and kept in one local working tree until this date; other
> documents and project-memory records cited it while it was unpublished. Everything below this note is the unedited
> original (SHA-256 of the original file: `c283bd77f68d4aea7d6f4419bb0c017602f95901d2ba7615c32a1d778acc3e46`). It is a planning record, not a result. Where it and
> [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) disagree, the ledger wins. All arena numbers
> are on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1, with 4 to 10 questions per test.
>
> What happened next: superseded the same day by [`RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md`](RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md).
> The project's own numbers quoted here (Mem0 4/10, zero of nine provenance repairs, a monotone Hindsight breadth curve)
> were measured on cross-unit-contaminated Mem0 stores or with a truncation bug and are invalid; the roadmap's section 3
> lists each one. The first experiment recommended in section 8 (Mem0 breadth expansion) was run on clean stores and
> showed no gain. The external-paper readings were not re-checked at publication.

# Mechanism Dependency Synthesis — 2026-08-24

Source of truth: `RELATED_WORK_RED_TEAM_2026-08-24.md`, deepened this pass with four targeted primary-source re-reads (GRAVITY, Memory-in-the-LLM-Era, TierMem, router-feature specifics) — not a new novelty sweep. Cross-referenced throughout against AAMR's own arena data (`data/lab/arena/expansion-report.json`, `docs/research/CONTEXT_AND_PROVENANCE_ABLATION_V1.md`).

Labels used throughout: **MEASURED** (a number or fact read directly from a primary source, or from AAMR's own artifacts), **PAPER CLAIM** (the source's own stated conclusion, not independently reproduced), **INFERENCE** (this document's reasoning connecting two measured facts), **HYPOTHESIS** (a proposed, not-yet-tested claim). No dependency below is stated as fact unless it was actually measured somewhere.

---

## 1. Mechanism × regime matrix

| Mechanism | Target failure mode | Stage | When it helps | When it hurts | Dependencies | Hosts tested | Evidence strength |
|---|---|---|---|---|---|---|---|
| **GRAVITY** structural anchoring (entity/event/topic) | Under-specified or unlinked entity/temporal/thematic context | Representation (prompt-injection), not retrieval | All 5 hosts, all conditions tested — MEASURED, uniformly positive | Oracle-retrieval condition: slightly negative (84.9→83.9) when retrieval is already perfect — MEASURED | A working host retrieval pipeline to supplement; own GPT-4o-mini extraction+embedding build ($$ at build time, not query time) | Zep, Mem0, A-Mem, LiCoMemory, LightMem (5, independent, pre-existing) | **High** — multi-host, ablated, oracle-controlled |
| **Memory-in-the-LLM-Era** Tree (multi-granularity organization) | Poor cross-segment retrieval, especially open-domain-knowledge and temporal questions | Write + retrieval (both) | Standalone Δ = −4.39pp if removed from full method; MEASURED | Non-monotonic on one category: MemTree-alone scores *highest* on OK (26.54), beating the full method (19.69) — MEASURED, unremarked by the paper's own authors | Structurally coupled to SP (SP only exists once Tree/HM exists) — MEASURED, not independently toggleable | Author-designed method vs. donor systems (MemTree, MemOS, MemoryOS) as ablation arms, one benchmark (LoCoMo) | **Medium-high** — real ablation, single benchmark, non-factorable from SP |
| **Memory-in-the-LLM-Era** SP (segment-level processing) | Token overhead / incoherent tree-leaf boundaries | Write only, at short-term→mid-term transition | Standalone Δ = −2.25pp if removed; hits temporal-reasoning hardest in absolute terms — MEASURED | Removing SP *raises* OK score in one row-comparison — MEASURED, unremarked | Requires Tree/HM to exist at all | Same as above | **Medium** — real numbers, single benchmark, mechanism narrower than Tree |
| **AutoMEM** (LightMem-graph / PlugMem-graph index) | Weak grep/read-only baseline retrieval | Retrieval (index construction) | BASE+A=67.3, BASE+B=66.0 vs BASE=45.0, both isolated — MEASURED | Never run together; no interaction measurable | Cypher graph substrate; ambiguous whether it reuses donor code or reimplements schema | DCI-Lite agent harness only (not multiple independent pre-existing memory *systems*) | **Medium-high** on isolated deltas, **none** on interaction (cell doesn't exist) |
| **TierMem** tiered summary→raw escalation | Missing or under-specified evidence at the compact tier | Retrieval + context construction | LoCoMo: monotonic Summary<Router<Raw on all 4 categories — MEASURED | LongMemEval "Knowledge Update": Router (0.744) *below* Summary-only (0.756) — MEASURED, unremarked; "SS-Pref": Router ties Summary, both far below Raw | A pre-built Mem0-like summary tier; a trained RL router (SFT+GRPO) OR a simpler fixed policy | Built on Mem0 only | **High** on its own benchmark; **directly informative, not directly transferable** — see §3 |
| **Eywa** fixed-rule raw-episode rescue | Under-specified compact answers for shape-sensitive questions (exact/list/count/interval/recommendation) | Retrieval + context construction | PAPER CLAIM only — no ablation reported | Not reported — paper's own Limitations section admits no cost/accuracy ablation exists | A hand-coded question-type classifier; explicit provenance pointer at write time | Own pipeline only, no Mem0/Hindsight comparison | **Low-medium** — real mechanism, unquantified |
| **FluxMem** structure-selection gate | Wrong memory structure (linear/graph/hierarchical) for the query | Retrieval (structure choice) | PAPER CLAIM: +9.18% PERSONAMEM, +6.14% LoCoMo | Not reported | 12-engineered-feature vector (§6), offline-labelled training data (regime labels from independently scoring each structure) | Own 3 structures, one paper's design | **Medium** — real numbers, single-architecture, structures self-designed |
| **Harness the Memory** substrate comparison (diagnostic only) | N/A — not a mechanism, a measurement instrument | N/A | Confirms breadth-helps-QA/hurts-sequential-decisions pattern generally — PAPER CLAIM | N/A | 3 backbones, 4 benchmarks | 11 substrates reimplemented "canonically" | **High as diagnosis, zero as a transplantable mechanism** — explicitly "no factorial ablation is conducted" |
| **Diagnosing Retrieval vs. Utilization Bottlenecks** (3×3 design) | Isolates whether retrieval method or write strategy drives accuracy | Retrieval AND write, factorially separated | Retrieval method: 20pt swing (57.1–77.2%); write strategy: only 3–8pt swing, raw ≥ Mem0-extraction always — MEASURED | Not reported as harmful anywhere | Requires controlling both axes at once | Mem0 named explicitly as one write-strategy arm | **High** — genuinely factorial, though within one paper's own pipeline |
| **Verbatim Chunks Beat Extracted Artifacts** (raw vs. extracted storage) | Lossy extraction discarding answer-critical detail | Write/storage representation | LoCoMo 43.9% vs 28.0% (verbatim vs. extracted); hybrid (chunks+artifacts) preserves the gap, substitution forfeits it — MEASURED | Not reported as harmful | None beyond storing both forms | Own pipeline, not host-wrapped | **High** — large controlled ablation, though not host-agnostic |
| **Mem0 vs. long-context LLM inference** | Compares Mem0-style compaction against full long-context inference | End-to-end system comparison, not a component | Long-context wins on LongMemEval/LoCoMo; Mem0 competitive only on PersonaMemv2 (stable persona facts) — PAPER CLAIM | Mem0 loses where facts evolve/accumulate rather than stay flat — INFERENCE from the PersonaMemv2 exception | Compute budget (long-context is markedly more expensive below ~10 turns) | Mem0 vs. GPT-5-mini long-context, three benchmarks | **Medium** — independent replication of the general pattern, different broad arm than Hindsight |
| **Sufficient Context** (abstention diagnostic) | Confident wrong answers when context is insufficient | Answer-time reasoning, not memory | N/A — a diagnostic finding, not a mechanism | Confirms models rarely abstain even when they should — PAPER CLAIM | None (behavioral finding about frontier LLMs generally) | Gemini 1.5 Pro, GPT-4o, Claude 3.5 | **High as diagnosis** — explains *why* gold-present-but-wrong happens at all |
| **Power of Noise** (irrelevant-document injection) | Over-narrow retrieval starving the reader of context | Context construction | Adding random/irrelevant docs improves accuracy up to 35%; retriever's own top-ranked-but-irrelevant hits are the *most* harmful kind — MEASURED, SIGIR 2024 | Related-but-irrelevant docs hurt more than random ones — MEASURED | None — a context-construction finding, not a build-time mechanism | General RAG, not agent-memory-specific | **High**, but general-RAG, not agent-memory native |

---

## 2. Dependencies, not just correlations

**A. Does structural anchoring help more where the host context is already wide/noisy?**
MEASURED, and the direction runs **opposite** to the question's premise: across GRAVITY's 5 hosts, the host with the smallest gain from anchoring (LightMem) had the *highest* baseline scores of the five (68.8/67.1/70.1 pre-anchoring), while the hosts with the largest absolute gains (Zep, Mem0) had lower, narrower baselines. INFERENCE: anchoring looks like it fills a gap that narrower/lower-performing hosts have and richer hosts have already partly closed on their own — not something that specifically compounds with breadth or noise. This is a real but correlational read across only 5 hosts, not a controlled sweep of "host richness" as an independent variable — treat as suggestive, not settled.

**B. Do entity/topic anchors reduce reader interference at large breadth?**
Not directly measured by anything found. The closest adjacent evidence is GRAVITY's own oracle-retrieval ablation: when retrieval is already perfect, anchoring adds ~0 or slightly negative value (84.9→83.9). INFERENCE: this suggests anchoring's value is specifically about *filling representational gaps left by imperfect retrieval*, not about *filtering interference from an already-large candidate set* — a different mechanism than "reduces interference at breadth" would imply. Genuinely open; nothing found tests interference reduction directly.

**C. Does raw detail help only when compact representation lost qualifiers, relations, or chronology?**
MEASURED, and this is one of the best-supported dependencies in the whole set. TierMem's own error taxonomy attributes 28.8% of its Tier-1 failures specifically to "over-generalization... retains topic relevance but loses answer-critical specificity (entities, modifiers, exact values)" — its own example: "severe peanut allergy" compressed to generic "dietary preferences." "Verbatim Chunks Beat Extracted Artifacts" independently found extraction gaps (lost specificity, essentially the same phenomenon) as 78.8% of its dominant failure category. Two independent papers converge on this exact mechanism.

**D. Is raw detail useless if compact memory already retained gold and the required relations?**
MEASURED — this is essentially AAMR's own finding, not inferred from the literature: Mem0 places gold at rank 1 in most observable cases, and adding the raw session behind that hit repaired zero of nine failures. TierMem's own error taxonomy makes the complementary point from the other side: 41.3% of *its* Tier-1 failures are outright **absence**, not under-detail — a different, harder starting condition than AAMR's. Put together (§3 below), these two facts aren't in tension; they describe two different regimes of the same underlying variable.

**E. Does tree/hierarchical organization only pay off combined with another mechanism?**
MEASURED, and the answer is more precise than a yes/no: Tree has real standalone value (removing it from the full method costs 4.39pp; it isn't inert alone). But the full Tree+SP combination (43.40) beats the naive additive prediction from each standalone contribution by +0.60 — a small, genuine complementary bonus on top of Tree's own independent value, not a precondition for it. One structural caveat undercuts how "clean" this reads as a factorial result: SP is architecturally impossible to test without Tree (it only exists at the point where dequeued short-term messages become tree leaves) — so this is a constrained, non-fully-factorable 3-component space, not a textbook 2×2 grid. AAMR's own planned transplants (independently-sourced mechanisms bolted onto an unrelated host) would not have this coupling problem, and should be genuinely cleaner to interpret than this precedent is.

**F. Which mechanisms show a positive effect across many independent hosts, and are therefore good transplant candidates?**
GRAVITY is the standout, and currently the *only* mechanism in this set with this property directly measured: positive across all 5 independent, architecturally distinct hosts, with an oracle-controlled ablation ruling out "it's just doing better retrieval." Nothing else in the reviewed set has been tested this way — AutoMEM's isolated deltas are both against one shared agent harness (DCI-Lite), not multiple independent memory *systems*.

**G. Which mechanisms are strongly host/regime-dependent, and therefore better suited to a router than to blanket inclusion?**
Two convergent pieces of evidence point the same way. "Diagnosing Retrieval vs. Utilization Bottlenecks" found retrieval-*method* choice swings accuracy by up to 20 points depending on setup, while write-strategy choice (raw vs. extracted) swings it by only 3–8 points and is directionally consistent (raw ≥ extracted, basically always) — i.e., *what* you keep is a near-global good default, *how* you search it is regime-dependent. TierMem's own per-category table reinforces this from a different angle: the *decision to escalate* helps almost everywhere but actually regresses on LongMemEval's "Knowledge Update" category specifically — meaning the escalation trigger itself, not the raw content, is the thing that's host/category-dependent. Together: **write-strategy-style choices (raw vs. compact) look closer to safe global defaults; retrieval-method and escalation-trigger choices look like the right things to route on.**

---

## 3. The TierMem vs. AAMR tension, resolved with specific differentiating variables

TierMem: raw-only (0.873) beats its own learned router (0.851) beats summary-only (0.755) — raw context clearly, uniformly helps. AAMR: raw-provenance-plus-compact repairs zero of nine Mem0 failures, and raw-only alone is *worse* than compact (3/9 vs. 4/9). These are not presented here as a contradiction requiring a narrative reconciliation — the primary-source re-read surfaced concrete, measured differences in experimental design that plausibly explain the divergence on their own:

| Variable | TierMem | AAMR (`arena-context-ablation-v1`) |
|---|---|---|
| Dominant Tier-1/compact failure cause | 41.3% **absence** (gold not in the summary at all) vs. 28.8% under-detail — MEASURED, TierMem's own error taxonomy | Gold present at rank 1 in most observable Mem0 cases — MEASURED, AAMR's own arena data |
| Amount of raw material added on escalation | ~7 pages × ~1000 tok ≈ 7,398 tok average — MEASURED | One session, ~2,150 words (~2,800 tok) — MEASURED |
| Provenance mechanism | Warm-start on the linked page(s), **then** limited multi-hop search (up to T_max steps) if still insufficient — MEASURED | Single fixed pointer-follow to the top-1 hit's session, no second-stage search — MEASURED |
| Retrieval trigger | A trained RL policy conditioned on (query, retrieved summaries) — MEASURED | Unconditional, applied to test the hypothesis directly, not a production trigger — MEASURED |
| Category pattern | Monotonic on LoCoMo; regresses specifically on LongMemEval "Knowledge Update" — MEASURED | The 10-unit sample's own strongest category is knowledge-update (2/3 for both Mem0 and Hindsight); weakest are multi-session and temporal-reasoning — MEASURED |

**Four falsifiable hypotheses follow directly:**

1. **Absence-vs-under-detail hypothesis.** Raw/provenance expansion only repairs failures where gold is genuinely *absent* from the compact representation, not where it is present but under-detailed or unused. *Falsify by*: partitioning AAMR's own failure set (once larger than n=9) by presence/absence of gold-adjacent content in Mem0's compact context, and checking whether repair rate is higher in the absence subset specifically.
2. **Raw-volume-threshold hypothesis.** Provenance expansion needs to cross a minimum token volume before it has any chance of helping; AAMR's single-session ~2,800 tokens may sit below whatever threshold TierMem's ~7,400-token, multi-hop-capable escalation clears. *Falsify by*: re-running the same provenance test with 2–3 sessions instead of 1, holding everything else fixed.
3. **Multi-hop-access hypothesis.** A single fixed pointer-follow is not equivalent to a search-capable escalation; some of AAMR's failures may need a *second* hop (e.g., the session the top-1 hit itself references) that a single-hop design cannot reach. *Falsify by*: adding one bounded multi-hop step (follow one additional cross-reference from the top-1 session, mechanically, no gold-aware selection) and checking for new repairs.
4. **Category-alignment hypothesis.** Provenance/raw expansion's value is concentrated in exactly the categories where AAMR is already weakest (multi-session, temporal-reasoning) and near-zero elsewhere (knowledge-update) — meaning a null result pooled across all 10 units could be masking a real, category-specific effect. *Falsify by*: re-examining the existing 9-probe result split by category rather than pooled (already partially visible in the per-probe table in `CONTEXT_AND_PROVENANCE_ABLATION_V1.md` §5 — worth a dedicated re-read before spending anything new here).

None of these four require abandoning AAMR's own `DROP` decision on the blanket `RAW_PROVENANCE_EXPANSION` candidate — they narrow *when* it might still matter, which is a different and cheaper question than *whether* it matters in general.

---

## 4. GRAVITY: is there a minimal Candidate A?

Structural anchoring computes three things from raw conversation and injects them as supplementary prompt blocks, reranked by query similarity: **entity profiles** (attributes, typed relations, timeline, co-occurrence), **event traces** (4W1O tuples chain-linked by heuristic, non-LLM overlap into causal/temporal sequences), and **topic summaries** (LLM-clustered cross-session narratives). MEASURED, and important: the mechanism is overwhelmingly representation-side, not retrieval-side — an oracle-retrieval ablation shows zero-to-negative benefit when retrieval is already perfect, and removing the one retrieval-touching component (query expansion) changes accuracy by under half a point. The single largest ablation drop in the whole paper is from removing *reranking*, not from removing any one anchor category — meaning selection of what to show matters more than which category it comes from.

Yes, a minimal candidate exists, with one important, paper-stated caveat. Entity Anchors alone has the largest mean marginal gain of the three sub-components on the one host tested (LightMem) and is structurally the simplest (no temporal-tuple schema, no cross-session clustering). But the paper's own ablation was run **only on LightMem, never on Mem0**, and its own text notes that gains shrink where a host already covers that structural dimension — and Mem0 is explicitly described as already maintaining its own graph-based entity-relationship store. This is a real, stated reason to expect *less* headroom for Entity anchors specifically on Mem0 than GRAVITY's own numbers would suggest.

**INFERENCE, connecting this to AAMR's own failure profile rather than to GRAVITY's own biggest average number:** AAMR's clearest, most repeatedly observed weakness is temporal reasoning (0/3 on the frozen sample, and the earlier pilot-to-expansion temporal signal weakened rather than replicated) — a dimension Mem0 has no explicit structure for at all, unlike entities. **Event/temporal anchors, not Entity anchors, are the better-motivated minimal candidate for AAMR specifically** — not because GRAVITY's own numbers rank them highest (they don't, on LightMem), but because they target the one failure mode AAMR has already, repeatedly, independently measured as real, on a host (Mem0) that has no competing native structure for it. This is a genuine departure from "pick whatever the source paper says worked best" toward "pick what the source paper's own decomposition says would target our specific, already-measured gap" — exactly the kind of dependency this synthesis was asked to surface rather than just report.

A cheap minimal version, in plain terms: extract 4W1O-style event tuples (who/what/when/where/outcome) per session via one LLM pass per session (or reuse Mem0's own extraction pass if it already segments turns), link them into simple chronological chains using the same kind of heuristic (non-LLM) overlap GRAVITY uses rather than a second model call, rerank by query similarity, and inject the top few as a small supplementary block alongside Mem0's existing retrieved context — never replacing it. Reranking should not be skipped; it is the single highest-leverage sub-component GRAVITY's own ablation identifies.

---

## 5. Memory-in-the-LLM-Era: what the interaction is actually made of

Re-verified directly (LoCoMo, token-level F1, per-category breakdown SH/MH/TR/OK exists and was not visible in the earlier pass):

| Configuration | SH | MH | TR | OK | Overall |
|---|---|---|---|---|---|
| Full (Tree+SP) | 49.63 | 36.94 | 39.86 | 19.69 | 43.40 |
| w/o Tree | 45.82 | 35.23 | 31.89 | 14.25 | 39.01 |
| w/o SP | 47.97 | 34.99 | 35.24 | 19.20 | 41.15 |
| w/o Tree & SP (≈MemoryOS) | 43.58 | 35.64 | 28.05 | 18.98 | 37.36 |

The paper's own quoted interpretation: removing Tree costs 4.39pp overall, removing SP costs 2.25pp, "with temporal reasoning being the most affected question category" — PAPER CLAIM. INFERENCE, this document's own arithmetic, not the authors': Tree's removal costs far more on OK (−5.44pp) than SP's removal does (−0.49pp, roughly 11× smaller), while *both* hit TR hardest in absolute terms (Tree: −7.97pp; SP: −4.62pp). So the two components are not solving the same problem uniformly — Tree looks like the OK-relevant piece, both matter for TR, and neither dominates SH. A full synergy search for "synerg/interact/additive" across the paper's text returned nothing — the authors never compute or discuss this, confirming the original finding.

Whether the +0.60 combined-vs-additive gap plausibly reflects "Tree improves organization, SP improves extraction, and better-organized retrieval makes better-extracted segments more useful" is **HYPOTHESIS only** — the paper offers no such explanation, and one unremarked data point argues against a clean story: the Tree-only row (no SP, no combination) scores *highest* of any configuration on the OK category (26.54, beating the full method's 19.69) — meaning SP actively costs something on that one category even though it helps overall. Treat the interaction as real in the numbers and genuinely useful as an existence proof that cross-mechanism synergy can be positive, but not yet as a settled causal story about *why*.

---

## 6. Router signals: what's actually usable without gold labels

Four systems' actual input features, read directly from source rather than assumed:

| System | Feature basis | Learned or fixed | Confirmed inputs |
|---|---|---|---|
| FluxMem | 12 hand-engineered features | Learned (offline, supervised on regime labels) | `page_count`, `avg_page_length`, `entity_density`, `relation_indicators`, `topic_diversity`, `topic_transitions`, `is_qna_pattern`, `is_decision_tree`, `is_entity_centric`, `time_span`, `temporal_density`, `semantic_complexity` — explicitly *not* embeddings |
| MemRouter | Dense embedding only | Learned (supervised classification head) | BGE-large sentence embedding → projected into a frozen backbone's hidden space; no engineered signal at all |
| Eywa | Question-shape classification | Fixed rule table | Exactly 5 of 8 shapes trigger rescue: exact, list, count, interval, recommendation — boolean and factoid do not |
| TierMem | Raw query + retrieved summaries | Learned (RL, GPT-5-distilled) | Sufficiency judged end-to-end from (query, top-k Tier-1 summaries); no separate confidence scalar is fed in |

Candidate feature list for a future AAMR router, each assessed on inference-time availability, cost, and leakage risk:

| Feature | Measurable at inference | Cheap | Leakage risk | Status |
|---|---|---|---|---|
| Query type/classification | Yes | Yes | Low | **Precedented** (Eywa's whole mechanism) |
| Entity density in retrieved candidates | Yes | Yes | Low | Precedented in spirit (FluxMem's `entity_density`, computed over context not post-retrieval candidates — a variant, not identical) |
| Recency spread of retrieved items | Yes | Yes | Very low | Precedented in spirit (FluxMole's `time_span`) |
| Context-sufficiency estimate | Yes, if computed by a model | Moderate | Moderate — safe only if it doesn't shortcut through gold-derived signal | Precedented in spirit (essentially what TierMem's router computes end-to-end) |
| Retrieval confidence score | Yes | Yes | Low, if untuned on eval gold | **Notably absent from every system checked** — Eywa explicitly excludes it |
| Score margin between top candidates | Yes | Yes | Low | Not found in any paper checked — open |
| Contradiction count among candidates | Yes (pairwise NLI) | Moderate | Low | Not found in any paper checked — motivated by Eywa's goal, not its mechanism |
| Number of candidate memories | Yes | Yes | Very low | Structurally analogous to FluxMem's `page_count`, different purpose |
| Evidence redundancy among candidates | Yes | Moderate | Low | Not found; MemRouter's admission gate implicitly relates but doesn't expose this as a feature |

**INFERENCE, most actionable for AAMR:** retrieval confidence and score-margin — arguably the two cheapest, most obvious router signals — are absent from every system actually checked. That is either a real gap AAMR could fill, or evidence that these signals turned out not to be useful and nobody published the negative result. No way to tell which from what was found; worth a cheap, direct check on AAMR's own data before building anything more elaborate.

---

## 7. Top 5 testable mechanism hypotheses

### 1. Event/temporal anchor injection on Mem0 (GRAVITY-derived, retargeted)

- **HYPOTHESIS:** injecting a lightweight, chronologically-chained event summary (4W1O-style) alongside Mem0's existing retrieved context repairs some of Mem0's temporal-reasoning failures.
- **SOURCE EVIDENCE:** GRAVITY's Event-anchor ablation (measured, LightMem host) plus the oracle-controlled finding that anchoring's benefit is representation-side, not retrieval-side.
- **WHY IT MAY GENERALIZE:** it targets a structural gap (temporal chaining) that Mem0 has no native equivalent for, unlike entity structure, which Mem0 already partially covers.
- **DEPENDENCIES:** an event-extraction pass (LLM or reuse of Mem0's own segmentation), a heuristic (non-LLM) chaining step, a reranking step — reranking should not be skipped, per GRAVITY's own largest ablation effect.
- **EXPECTED BENEFIT:** recovery of some fraction of the 0/3 temporal-reasoning failures on the frozen sample.
- **EXPECTED FAILURE MODE:** Mem0 may already implicitly encode enough temporal order in its stored items that this is redundant — GRAVITY's own caution about host-overlap applies here too, just less directly than for Entity anchors.
- **MINIMAL TRANSPLANT:** event tuples + heuristic chaining + rerank + inject as one supplementary block; no training required.
- **BASE vs. BASE+X DESIGN:** BASE = Mem0 alone on the frozen 10-unit sample; BASE+X = Mem0 + event-anchor block, same reader/judge/budget accounting.
- **WHAT WOULD FALSIFY IT:** zero of the 3 temporal-reasoning failures flip, and reader transcripts show no behavioral change.
- **ESTIMATED COST:** low — a handful of extraction calls (already-stored sessions) plus reader calls; no training.

### 2. Query-conditioned reranking of already-retrieved content

- **HYPOTHESIS:** reranking Mem0's own already-stored/retrieved items by query-similarity before truncating to budget improves accuracy, independent of any new extraction machinery.
- **SOURCE EVIDENCE:** GRAVITY's own largest single ablation effect is removing reranking, not removing any anchor category; "Diagnosing Retrieval vs. Utilization Bottlenecks" independently found retrieval-method choice swings accuracy far more than write-strategy choice.
- **WHY IT MAY GENERALIZE:** two unrelated papers converge on "how you select from what you have" mattering more than "what category of thing you have" — a mechanism-agnostic, host-agnostic claim.
- **DEPENDENCIES:** none beyond an embedding similarity function — no new data structures, no LLM calls if reusing existing embeddings.
- **EXPECTED BENEFIT:** general accuracy lift, not targeted at one category.
- **EXPECTED FAILURE MODE:** Mem0's stored items may already be pre-filtered/pre-ranked well enough that reranking a small set changes nothing.
- **MINIMAL TRANSPLANT:** compute cosine similarity between query and each already-retrieved item, reorder before budget truncation — genuinely trivial to implement.
- **BASE vs. BASE+X DESIGN:** BASE = Mem0's current ordering; BASE+X = Mem0's same retrieved set, reranked before truncation.
- **WHAT WOULD FALSIFY IT:** no change in which units are answered correctly.
- **ESTIMATED COST:** near-zero — no new model calls at all if existing embeddings are reused.

### 3. Mem0 breadth expansion (k=50 / k=150)

- **HYPOTHESIS:** Mem0's own accuracy climbs with context breadth the same way Hindsight's did, meaning the earlier volume-vs-provenance ambiguity (H1 vs. H2) resolves in favor of volume for Mem0 too.
- **SOURCE EVIDENCE:** AAMR's own Hindsight breadth curve is already monotone and causal (4/10 at Mem0's budget → 7/10 at full breadth) — MEASURED BY US; TierMem's own per-category numbers independently show the largest summary-to-raw gaps on exactly the categories (multi-session-adjacent, temporal-reasoning) where AAMR is already weakest — a convergent, if indirect, signal.
- **WHY IT MAY GENERALIZE:** this isn't cross-paper generalization at all — it's AAMR's own already-designed next step, cited in its own existing report as "the cheapest next falsifying experiment," now additionally supported by an independent paper's category-level pattern.
- **DEPENDENCIES:** none — re-query Mem0's own persisted store at higher k, no new mechanism.
- **EXPECTED BENEFIT:** if H1 holds, accuracy should rise toward Hindsight's range as budget grows.
- **EXPECTED FAILURE MODE:** flat accuracy despite more tokens would kill H1 for Mem0 specifically and point squarely at H2 (kind of information, not amount).
- **MINIMAL TRANSPLANT:** not a transplant — a parameter change (Mem0's own `limit`).
- **BASE vs. BASE+X DESIGN:** BASE = Mem0 at current k=10; +X = Mem0 at k=50 and k=150, same reader/judge.
- **WHAT WOULD FALSIFY IT:** accuracy stays at 4/10 (or near it) despite a large token increase.
- **ESTIMATED COST:** ~$0.05, per AAMR's own prior estimate — the cheapest item on this list by a wide margin.

### 4. Context-sufficiency gate before attempting any expansion

- **HYPOTHESIS:** a cheap signal estimating whether the compact representation is likely *missing* gold entirely (vs. merely under-detailed) can decide whether escalation (raw or breadth) is worth attempting at all, rather than applying it unconditionally.
- **SOURCE EVIDENCE:** the TierMem/AAMR reconciliation in §3 — TierMem's failures are dominated by absence (41.3%), AAMR's observable Mem0 failures are dominated by presence-but-still-wrong; TierMem's own router is exactly this kind of gate, formalized as (query, retrieved-summaries)→sufficiency.
- **WHY IT MAY GENERALIZE:** it reframes "does expansion help" from a blanket question (already answered no, for provenance, on AAMR's data) into a conditional one, which is consistent with what both papers' data actually show once split by regime.
- **DEPENDENCIES:** requires either a trained signal (heavier) or a cheap proxy (retrieval confidence, candidate count, score margin — none of which were found precedented anywhere in this search, so this piece is more exploratory than the others).
- **EXPECTED BENEFIT:** avoids wasting budget/tokens on expansion attempts that can't help, and could reveal a positive effect currently hidden inside a pooled null result.
- **EXPECTED FAILURE MODE:** if AAMR's failures are dominated by presence-but-wrong (as the pooled result suggests), this gate may correctly conclude "don't expand" almost every time — a valid but low-value outcome.
- **MINIMAL TRANSPLANT:** none available off the shelf; would need to be built from AAMR's own data.
- **BASE vs. BASE+X DESIGN:** BASE = current unconditional policy (already tested, null); +X = same mechanism gated by a cheap sufficiency proxy, tested only on the subset it triggers on.
- **WHAT WOULD FALSIFY IT:** the gate fires rarely or never on the existing 9-probe set, or fires but still shows no repairs where it does.
- **ESTIMATED COST:** low for a first proxy-based version; higher if a trained signal is pursued.

### 5. Bounded second-hop provenance search

- **HYPOTHESIS:** some of AAMR's failures need a second hop beyond the top-1 hit's own session (something that session itself references), which a single fixed pointer-follow cannot reach.
- **SOURCE EVIDENCE:** TierMem's escalation design explicitly includes "provenance-guided warm-start, then limited multi-hop search (up to T_max steps) if still insufficient" — AAMR's own test never went past the first hop.
- **WHY IT MAY GENERALIZE:** it isolates one specific, mechanical difference between the two experimental designs rather than assuming the whole mechanism failed to transfer.
- **DEPENDENCIES:** a mechanical (non-gold-aware) way to identify a second-hop candidate — e.g., a cross-reference or shared entity between the top-1 session and another stored session.
- **EXPECTED BENEFIT:** small — this is a narrow, corrective follow-up to an already-negative result, not a fresh mechanism.
- **EXPECTED FAILURE MODE:** no additional repairs, which would further strengthen the existing `DROP` decision rather than overturn it.
- **MINIMAL TRANSPLANT:** one bounded, mechanical hop added to the existing (already-built) provenance-following code.
- **BASE vs. BASE+X DESIGN:** BASE = the existing single-hop result (already measured: 0 repairs); +X = same mechanism with one additional mechanical hop.
- **WHAT WOULD FALSIFY IT:** zero additional repairs — expected, and still useful as confirmation the earlier `DROP` was not an artifact of hop-count.
- **ESTIMATED COST:** very low — extends existing, already-frozen code rather than building anything new.

---

## 8. Priority: the next dollar

**FIRST MECHANISM TO TEST: #3, Mem0 breadth expansion (k=50/150).**

Scored strictly on the requested criteria, not novelty:

- **Evidence strength:** the highest of anything on this list. It isn't drawn from someone else's paper at all — it's a direct extrapolation of AAMR's own already-measured, monotone, causal Hindsight breadth curve, independently reinforced by TierMem's category-level pattern.
- **Portability:** trivial — no new mechanism, no transplant, just a parameter already exposed by Mem0's own query interface.
- **Mechanistic clarity:** total — there is no ambiguity about what is being varied or why.
- **Cheap falsifiability:** the cheapest item on this list by a wide margin (~$0.05, already estimated by AAMR's own prior report), with a clean, pre-specified failure condition.
- **Relevance to AAMR's own observed failures:** it resolves the exact ambiguity AAMR's own existing report says is still open — "This ablation cannot separate [H1 from H2], because it never varied Mem0's breadth" — not a hypothesis borrowed from elsewhere, but the missing half of an experiment AAMR already ran the other half of.

Everything else on the list — the event-anchor transplant, the reranking test, the sufficiency gate, the second-hop check — is better motivated *after* this result is in, because it settles whether volume alone is doing the work for Mem0 too (in which case reranking and breadth-style fixes deserve the next round of investment) or whether Mem0 stays flat despite more tokens (in which case the kind-of-information hypothesis strengthens, and the event-anchor and sufficiency-gate candidates move up). Reranking (#2) is the natural second purchase regardless of which way #3 lands, since it is nearly as cheap and answers a mostly-orthogonal question.

---

## Sources

All papers as previously verified in `RELATED_WORK_RED_TEAM_2026-08-24.md`; this pass re-fetched primary-source full text for: GRAVITY (arXiv:2605.01688), Memory in the LLM Era (arXiv:2604.01707), TierMem (arXiv:2602.17913), FluxMem (arXiv:2602.14038), MemRouter (arXiv:2605.00356), Eywa (arXiv:2605.30771). AAMR-internal sources: `data/lab/arena/expansion-report.json`, `docs/research/CONTEXT_AND_PROVENANCE_ABLATION_V1.md`.
