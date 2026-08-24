# Related Work and Positioning — 2026-08-24

Status: first pass, external-request-triggered, primary-source verified for every arXiv ID cited below.
Author: Claude (Opus 5), acting as a research assistant on explicit instruction not to implement, not to tune, and not to try to confirm the project's own hypothesis.
Scope: the mechanism-transplant / operating-regimes research direction described to the assistant as the project's current possible trajectory (`docs/00-project/operating-plan-and-rules.md` Phases A–D, `docs/04-systems/comparative-memory-systems-lab.md`). This is **not** a review of the whole repository.

Labelling used throughout, per instruction:

- **MEASURED BY US** — read directly from this repository's own JSON/CSV artifacts.
- **PAPER CLAIM** — stated in an external paper's abstract or body, verified against the primary source, not reproduced by anyone here.
- **INFERENCE** — this document's own reasoning connecting two sourced facts.
- **UNVERIFIED** — reported to the assistant or found only in a secondary source, not confirmed against a primary source.

---

## Executive conclusion

The trajectory described — independent systems → common frozen arena → per-probe operating regimes → transplant a locally-winning mechanism → `BASE`/`+A`/`+B`/`+A+B` interaction ablation → controller — is **not invented for this document**. It is, almost word for word, `docs/00-project/operating-plan-and-rules.md`'s Phase A–D and `docs/04-systems/comparative-memory-systems-lab.md`'s "Transplant" section, both already committed to this repository (first committed 2026-08-23, per `git log`). That removes one risk (that the framing is post-hoc) and does not remove the harder one: **whether the specific combination is still open in the literature.**

All 11 papers named in the request were checked against primary sources (arXiv abstract pages/API, PDFs, and — where claimed — GitHub). **All 11 exist and are real papers**, which is not the usual outcome of this kind of check and is worth stating plainly. The list is not clean, though:

- **"D-MEM"** as described (dopamine-gated, reward-prediction-error, arXiv 2603.14597) is real and matches exactly — but it is a **different, unrelated paper** from the one this project's own literature queue already logged under a near-identical name (Zou et al., "Remember the Decision, Not the Description," arXiv 2605.10870, `docs/07-literature/full-read-notes/2026-zou-demem.md`). Two real papers, one name collision. The project's own notes currently only have the second one; this document is the first place both are distinguished.
- **"LongMINT"** was renamed to **"MINTEval"** between v1 and v2 (both 18–19 May 2026); the current version of record is MINTEval. Its headline failure driver is retrieval/construction (41.7%), not "interference and updates" as summarized — a real but secondary factor in the paper's own framing.
- **"FluxMem"** is a collided name: at least two other, unrelated 2026 papers also call themselves FluxMem. The claimed one (arXiv 2602.14038) is real; citations must carry the ID.
- Engram's "facts alone lose recall, facts+chunks restore it" is the paper's own **qualitative design observation**, explicitly not a quantified ablation — weaker evidence than its confident phrasing in the original brief suggested.
- MemCon's GitHub repo is real but has no LICENSE file despite an MIT README claim (already flagged internally, re-confirmed still true today). MemRouter's GitHub repo exists but contains only a README — no code.

The most consequential finding did not come from checking the 11 named papers — it came from the broad sweep run alongside them. **"Harness the Memory" (2608.15008) and "MemCon" (2607.13591) share four authors**, and MemCon shares a fifth author line with MemRouter (Weizhi Zhang). This is not three independent groups converging on the same idea; it looks like one overlapping research cluster (UCLA/UIC-adjacent) working the substrate-evaluation angle, the operation-controller angle, and the write-admission angle simultaneously. That is a materially bigger threat to any novelty claim resting on "a controller over memory decisions" than three unrelated single papers would be.

Against that, the broad sweep also surfaced the two most relevant pieces of prior art **not** in the original list: **A-TMA** turns out to already compare 9 pre-existing memory systems under one frozen harness (not disclosed in the original brief), and a paper called **"Exploring Cross-Scenario Generality of Agentic Memory Systems"** (arXiv 2606.04315) builds a composite system that **literally imports code-level components from two different named prior systems** (PlugMem's stores, LightMem's index). That is the closest thing found anywhere to this project's Phase C. Even so, neither paper — nor anything else found in ~20 searches across arXiv, GitHub, and two independent literature trackers — runs an explicit `BASE`/`+A`/`+B`/`+A+B` interaction grid **between mechanisms sourced from two different, independently-built systems**, and nothing found trains a router over mechanisms validated that way. That specific combination is the one part of the trajectory this document could not find anywhere, after a real search rather than an assumption.

**Bottom line: the direction is not invalidated, but its novelty has to be relocated.** "Memory systems have operating regimes and should be routed" is now a published, multi-team, well-resourced claim (see `docs/00-project/related-work-and-novelty.md` for the pre-existing APEX-MEM/Verbatim-Chunks/Tenure findings, and "Harness the Memory" below). What is not yet published anywhere found is the specific empirical discipline of cross-codebase mechanism transplant with a measured interaction grid, run before any controller is trained. That is narrower than the project's own five research questions taken together, and it is where this document recommends the project's remaining claim to originality be staked.

---

## Current AAMR evidence

Everything in this section was re-derived from the repository's own artifacts, not taken on the requester's word, and matched to the byte. Source files are named so the numbers can be re-checked without this document.

### Arena expansion (`data/lab/arena/expansion-report.json`) — MEASURED BY US

10 LongMemEval-S units (`arena-expansion-v1`), the pilot's 4 plus 6 more, explicitly **confirmatory and non-random**: the selection note in the artifact itself says temporal-reasoning is over-represented (3/10 vs a corpus proportion nearer 1/6) "to buy power on the question worth asking," and states the result "must never be presented as a random sample."

| | Mem0 | Hindsight |
|---|---|---|
| answered | 2/10 | 4/10 |
| knowledge-update | 2/3 | 2/3 |
| multi-session | 0/2 | 0/2 |
| single-session-user | 0/2 | 1/2 |
| temporal-reasoning | 0/3 | 1/3 |
| mean gold rank | 1.0 | 22.4 |
| mean precision@k | 0.54 | 0.12 |
| mean context tokens | 106.3 | 3157.8 |
| mean stored items | 280.8 | 554.4 |
| gold-in-context (observable subset) | 4/5 | 5/5 |
| total cost | $0.7592 | $4.4528 |

The pilot-only temporal signal (Hindsight 1/1, Mem0 0/1) weakened on expansion to Hindsight 1/3, Mem0 0/3. The project's own artifact does not claim replication, and this document agrees with that call — one unit out of three is not a mechanism, it is a coin flip that happened to land the same way twice.

### Question-only baseline (`data/lab/arena/fixed-reader-report.json`) — MEASURED BY US

`0/10`. Status is explicitly **"PARTIAL — memory arms BLOCKED"**: `runnable_arms` shows baseline=10, mem0=0, hindsight=0, and the recorded blocker is that delivered context text was not persisted before the per-unit store reset, so the memory arms of the fixed-reader comparison cannot be run against the same probes retroactively. This matches the reported measurement-integrity finding exactly. The plumbing fix (git log: *"Fixed-reader plumbing: decomposition, and a baseline that is not paid for twice"*) is recent and in the working tree, but **no run has yet been captured with it** — the existing `fixed-reader-report.json` predates the fix and is still blocked. Any experiment below that depends on delivered context text needs a fresh run first.

### Other pilots (`data/lab/arena/pilot-*.json`) — MEASURED BY US

- AAMR reference (`CANDIDATE-0`): abstained 4/4, $0.00, "stored nothing on 996 turns" — matches.
- CUPMem: 1/4, $1.5892 — matches. Note for context (see mechanism-candidate ranking below): CUPMem's own paper reports 68.0% overall on its own STALE benchmark's premise-resistance dimensions (`external/repos/icedreamc__STALE/README.md`), a different benchmark on a different construct. The 1/4 pilot number is not a contradiction of the paper's claim; it is a measurement of transfer to an out-of-domain benchmark, which is itself informative and worth stating that way rather than as "no demonstrated advantage."
- Graphiti: BLOCKED, not measured. The Kuzu embedded backend is deprecated upstream and fails on write-time index creation; FalkorDBLite does not build on win32. Correctly recorded as an operational block, not a mechanism failure.

**Conclusion this document draws from the above (INFERENCE, building on MEASURED BY US data):** gold evidence reaching the delivered context is close to necessary but nowhere near sufficient for a correct answer in this sample — both systems deliver gold most of the time and still answer correctly a minority of the time. The claim that retrieval is "not the bottleneck" should stay scoped to *this regime* (short LongMemEval-S sessions, n=10, English, two systems) — see the MINTEval discussion below for why generalizing it further is not supported.

---

## What the literature already establishes

Before the 11 papers checked for this document, the repository's own `docs/00-project/related-work-and-novelty.md` had already verified against primary sources that:

- **APEX-MEM** (arXiv 2604.14362, ACL 2026, Amazon) — entity-property-value triplets over an append-only store with query-time temporal resolution, 88.88% LoCoMo / 86.2% LongMemEval. The README already states plainly that structured temporal memory is not a novel claim here.
- **"Verbatim Chunks Beat Extracted Artifacts"** (arXiv 2601.00821) — extraction loses to raw chunks by 15.9–22.0 points across two benchmarks; converges with this project's own 85.7% deterministic-extractor abstention rate.
- **Tenure** (arXiv 2605.11325) — a typed belief store with the same "stale/superseded/contradictory facts silently influence responses" framing this project arrived at independently through `POISON`/`OBSOLETE`.
- Six more systems (A-TMA, Graphiti/Zep, STALE/CUPMem, VISTA, A-MAC, NEMORI) recorded as **reported but not verified** — this document verifies A-TMA below; the other five remain open per that file's own instruction.

Layered on top of that, this document's checks establish, all **PAPER CLAIM, primary-source verified**:

- No single memory substrate/structure dominates across benchmarks and backbones, and routing between them is motivated as future work — "Harness the Memory."
- A learned controller over one memory backend's operations (retrieve/consolidate/forget) beats fixed heuristics and reduces tokens — MemCon.
- A learned classifier choosing among several memory *structures* per query beats fixed thresholding — FluxMem.
- A state-aware overlay separating current/historical/transition memory, applied across nine pre-existing host systems, recovers accuracy that a plain retrieval baseline cannot — A-TMA (see below for the "nine hosts" detail, found only in the broad sweep).
- A write-side admission classifier, holding retrieval fixed, beats an LLM-based memory manager on both quality and latency — MemRouter.
- Automatic diagnosis-and-repair of a memory system's own retrieval configuration, with revert-on-regression, beats static configuration — EvolveMem, and it is not alone: SimpleMem, Omni-SimpleMem, AutoMem, MemEvolve, Evo-Memory and EvoArena form a small existing sub-field of this exact idea.
- Six specific brain-inspired mechanisms (sleep-phase consolidation, interference forgetting, engram maturation, reconsolidation, entity graph, hybrid multi-cue retrieval) have been implemented together in one system and evaluated on a real benchmark (LongMemEval) after calibration on synthetic data only — Microsoft Research.
- Bounded self-maintained memory is measurably worse than full context and gets *worse* with longer history; more capacity alone does not fix it — Supersede.
- A bi-temporal, provenance-preserving, hybrid-retrieval engine beats full-context on LongMemEval-S with far fewer tokens — Engram.

**Consequence:** most of the individual *ingredients* of the project's five research questions (multiple stores, adaptive selection, temporal state, write/read routing, consolidation, forgetting, auto-tuning) now have at least one 2026 paper claiming a working version. What has not been shown, by any of them, is the specific *transplant-then-ablate-then-route* discipline this project's Phase C already commits to. See "What may still be an open gap" below.

---

## Prior-art matrix

`YES` / `NO` / `PARTIAL` / `UNKNOWN` used per instruction rather than forcing a binary. `PARTIAL` means the primary source confirms a weaker or narrower version of the column; `UNKNOWN` means the primary-source check available to this document did not settle it either way.

| Work | Year | Open code? | Multi-system comparison? | Multiple structures? | Adaptive selection? | Temporal state? | Write routing? | Read routing? | Consolidation? | Forgetting? | Mechanism-level ablations? | Cross-system transplant? | Interaction/synergy tests? | Learned controller? | Common frozen harness? | Failure decomposition? | Closest overlap with AAMR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Harness the Memory (2608.15008) | 2026 | NO (promised on acceptance) | YES | YES | PARTIAL (motivated, not built) | UNKNOWN | NO | PARTIAL | UNKNOWN | UNKNOWN | PARTIAL (substrate-level, 26 metrics) | NO | UNKNOWN | NO (future work) | YES | PARTIAL | The premise itself: no dominant substrate, routing motivated |
| MemCon (2607.13591) | 2026 | YES, code (no LICENSE file) | NO | NO | YES | UNKNOWN | YES | YES | YES | YES | UNKNOWN | NO | UNKNOWN | YES (tabular bandit+UCB) | UNKNOWN | UNKNOWN | The controller end-state, over one backend's own operations |
| FluxMem (2602.14038) | 2026 | NO | NO | YES (own 3-level hierarchy) | YES (offline-supervised) | UNKNOWN | PARTIAL | NO | UNKNOWN | UNKNOWN | UNKNOWN | NO | UNKNOWN | YES (probabilistic gate) | PARTIAL (std. benchmarks) | UNKNOWN | Learned selection among memory structures — but structures are self-designed, not borrowed |
| A-TMA (2607.01935) | 2026 | NO | YES (9 hosts) | NO (an overlay) | NO | YES | PARTIAL | YES | NO | NO | PARTIAL (own sub-components) | PARTIAL (one overlay applied uniformly to 9 hosts, not code ported host-to-host) | NO | PARTIAL (trained Qwen3B QLoRA+GRPO component) | YES | YES (bank/retrieval/answer-time) | Temporal state-aware failure decomposition; closest single-mechanism candidate |
| D-MEM (2603.14597) | 2026 | YES (sparse, 2 stars) | NO | NO | YES (fast/slow) | NO | YES | UNKNOWN | PARTIAL | UNKNOWN | UNKNOWN | NO | NO | YES (Critic Router) | NO (own LoCoMo-Noise) | NO | Surprise/RPE-gated write path — relevant to future-utility retention |
| Microsoft Human-Inspired (2605.08538) | 2026 | NO | NO | YES | PARTIAL (blended, not selected) | PARTIAL | PARTIAL | YES | YES | YES | UNKNOWN | NO | UNKNOWN | PARTIAL | NO | UNKNOWN | Direct rival realization of AAMR's own Phase 1/3 human-memory bridge |
| MemRouter (2605.00356) | 2026 | Repo exists, README only, no code | NO | NO | PARTIAL (admission only) | NO | YES | NO (held fixed) | NO | NO (by omission only) | PARTIAL | NO | NO | YES (~12M-param classifier) | YES (matched harness) | NO | The write-admission half of AAMR's future-utility question |
| MINTEval / "LongMINT" (2605.18565, renamed v2) | 2026 | YES (renamed repo) | N/A — a benchmark | N/A | N/A | PARTIAL (revision domains) | N/A | N/A | N/A | N/A | N/A | NO | NO | NO | YES (as a benchmark) | YES (41.7% retrieval/construction) | Candidate second, never-inspected benchmark for AAMR's own Phase D |
| Supersede (2606.27472) | 2026 | YES (Apache-2.0) | NO | NO | NO | PARTIAL | NO | NO | NO | NO | YES (bounded vs full-context vs capacity) | NO | NO | PARTIAL (GRPO proof-of-concept) | PARTIAL (own env) | YES | Independent quantification of AAMR's own "more storage ≠ better memory" reading |
| Engram (2606.09900) | 2026 | YES (AGPL/commercial) | NO | YES | NO | YES (true bi-temporal) | NO | YES (fixed hybrid fusion) | PARTIAL | NO (invalidate, never delete) | PARTIAL (qualitative only) | NO | NO | NO | NO | NO | Facts-vs-raw-chunks tradeoff directly relevant to AAMR's Mem0 puzzle |
| EvolveMem (2605.13941) | 2026 | YES | NO | NO | PARTIAL (self config only) | NO | NO | PARTIAL | NO | NO | PARTIAL (revert-on-regression, not factorial) | NO | NO | PARTIAL (meta-controller over own knobs) | NO | YES | Autonomous self-improvement loop — parallels AAMR's *research process*, not its memory architecture |
| **Cross-Scenario Generality / AutoMEM** (2606.04315) — found via broad sweep, not in original list | 2026 | UNKNOWN | YES (8 hosts) | YES | PARTIAL | UNKNOWN | UNKNOWN | YES | UNKNOWN | UNKNOWN | PARTIAL (single-pass vs multi-step, LightMem-graph vs PlugMem-graph) | **YES — literal component import across two named prior systems** | PARTIAL (limited, not a full grid) | NO (named as future work) | YES | PARTIAL (regime predictors identified) | **Closest known precedent for Phase C found anywhere** |
| "Memory Transplants for LLM Agents" (OpenReview AIJsjIqfsp) — UNVERIFIED | 2026 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN — title suggests it, abstract summary suggests within-system domain transfer instead | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Unresolved — access blocked three times; needs a direct check by the project |
| APEX-MEM (2604.14362) — already known in-repo | 2026 | UNKNOWN | NO | NO | NO | YES | NO | YES | NO | NO | UNKNOWN | NO | NO | NO | NO | NO | Structured temporal addressing baseline, already conceded |
| Graphiti (getzep/graphiti) | ongoing OSS | YES | NO | NO | NO | YES (bitemporal) | NO | YES | NO | NO | N/A | NO | NO | NO | N/A | NO | Bitemporal field schema AAMR already borrows conceptually |
| **AAMR itself** | ongoing | YES | YES (Phase A arena, 5 systems) | Designed, not measured | NOT YET | PARTIAL (H2/PMLAB-REV-V0 measured) | NOT YET | NOT YET | NOT YET | YES (suppression-first, tested negative once) | YES (own E2-A/A2/A3 ladder; ASSOC E1-E3) | **NOT YET RUN — this is the gap** | **NOT YET RUN** | NOT YET | YES (ARENA-0/0.1) | YES (a stated house principle) | — |

---

## Detailed comparison with closest works

### Harness the Memory vs AAMR

Verified: 15 authors (UIC/UW/McGill/MBZUAI/UCLA), submitted 15 Aug 2026, cs.CL, preprint only, no venue disclosed, code withheld "upon acceptance." Every headline number in the original brief checked out verbatim against the primary source: 3 backbones, 4 benchmark suites, 26 metrics, "no single substrate consistently dominates," "broad retrieval benefits factual QA, excessive retrieval harms sequential decision-making," scalability as "a further routing axis."

Answering the eight questions posed:

1. **How close to "operating regimes"?** As close as it gets at the *substrate* level. This is the strongest single piece of prior art against the premise, not a mechanism candidate.
2. **Which AAMR claims lose novelty because of it?** "Different memory representations win in different situations" and "this motivates routing" are both now published, dated 15 Aug 2026, by an active multi-institution group.
3. **Substrate, mechanism, or component-transplant level?** Substrate level. It reimplements 11 methods from prior systems inside its own harness rather than porting mechanisms between two *other* pre-existing systems' own codebases.
4. **Do they transplant mechanisms between independent systems?** No evidence found of this in the abstract or in the broad sweep's full-text read.
5. **BASE/+A/+B/+A+B, interaction/synergy?** Not found. The paper's 26 metrics profile substrates individually; no interaction grid.
6. **Do they learn a router from the discovered regimes?** No — explicitly named as future work / a design goal, not built in this paper.
7. **If code isn't public, what does an earlier open implementation buy?** Reproducibility and falsifiability the paper itself does not yet offer to anyone. It does not buy priority on the *idea* — that is already public and dated via the abstract text regardless of code status.
8. **Scientific priority vs implementation priority vs reproducibility priority — kept separate:** see the dedicated First-mover section below; the short version is that this paper already has (1) and nobody yet has (2) or (3) for the *full* transplant pipeline.

### MemCon / FluxMem vs future controller

MemCon (verified: 14 authors, submitted 15 Jul 2026, `+15.2 task-success points`, `5–20% token reduction`, both confirmed verbatim; tabular contextual bandit with UCB exploration, not a generic "bandit-like" policy) routes **operations** — when to retrieve, what, how much, when to consolidate, when to forget — over **one memory backend's own lifecycle**. FluxMem (verified: 11 authors, submitted 15 Feb 2026, three-level hierarchy, Beta-Mixture-Model probabilistic gate, PERSONAMEM +9.18%/LoCoMo +6.14%, both new figures not in the original brief) routes among **structures it designed itself**.

The distinction the request asked about — "mechanism routing rather than operation routing" — is real, not marketing: neither paper's router ever selects between a mechanism literally sourced from a *different, independently-built* system's codebase. Both routers operate entirely inside one paper's own architecture. That said, this is a narrower differentiator than it might first appear, because **the authorship overlap** (Eric Hanchen Jiang, Kai-Wei Chang, Aylin Caliskan, Ying Nian Wu shared between MemCon and Harness the Memory; Weizhi Zhang shared between Harness the Memory and MemRouter) means the group most likely to notice and close this exact gap next is the one that already published two of the three closest papers. If AAMR's differentiator is "we route between independently-sourced mechanisms, not just decisions," that claim needs the transplant step actually demonstrated soon, not asserted.

### Temporal mechanisms: A-TMA / Supersede / Engram

**A-TMA** (verified exactly: title, arXiv 2607.01935, v1 2 Jul / v2 8 Jul 2026, authors Shi/Tang/Tung, NUS-affiliated — inferred from author identity, not read off the PDF header; ghost memory, current/historical/transition, three-way failure split, **+0.240 absolute conflict-accuracy over Graphiti confirmed exactly**, temporal F1 0.0295→0.1705 on LoCoMo). The broad sweep additionally found, reading the full text, that **A-TMA already compares 9 pre-existing host systems** (Mem0, A-Mem, Graphiti/Zep, MemoryLLM, M+, InsideOut, others) under one frozen harness and reports host-dependent gains (e.g. InsideOut+A-TMA: 0.117→0.662) — this was not in the original brief and materially raises A-TMA's relevance: it is doing something close to this project's own Phase A/B already, plus deploying one new mechanism as an overlay across many hosts. What it does *not* do is literally lift a mechanism out of one host's code and insert it into a different host's baseline, and its ablation table (Table 5, per the sweep) ablates its own sub-components, not cross-system pairs. Its overlay includes a **trained Qwen3B QLoRA+GRPO component** — this is not a free deterministic transplant, and any reproduction should say so plainly. No code found.

**Supersede** (verified exactly: arXiv 2606.27472, single author Vedant Patel, "preprint, under review," not peer-reviewed; every quantitative claim checked against the PDF: bounded-vs-full-context degradation with p-values, 24× longer history dropping accuracy 68%→28%, 24× more capacity alone leaving accuracy unchanged at 28%, GRPO fine-tune raising held-out accuracy 9.0%→16.7%). Its own coined term is "supersession gap"; "knowledge-update memory gap" as phrased in the original brief is an imprecise blend with LongMemEval's pre-existing category name of the same words, not a fabrication. This is not a mechanism to transplant — it is an independent, rigorous confirmation of the shape of AAMR's own H2 finding ("more storage does not fix a temporal-currency problem"), and its released Apache-2.0 environment is a candidate additional stress test if the project ever wants a harder, trainable version of its own H2 corpus.

**Engram** (verified exactly: arXiv 2606.09900, single independent-researcher author Liuyin Wang; append-only lossless episodes, atomic SPO facts, true bi-temporal fields, non-destructive supersession chain, hybrid dense+BM25+graph+recency+salience scoring, as-of filtering, provenance, all confirmed; LongMemEval-S 83.6% vs 73.2% full-context, +10.4pts, ~8× fewer tokens, McNemar p<10⁻⁶, confirmed exactly). Its bi-temporal schema converges with what this project already measured independently in `PMLAB-REV-V0` (0.944 exact match, both-axes-needed) — a second confirmation of a finding AAMR already owns, not new ground. Its "facts alone lose recall, facts+chunks restore detail" claim, however, is **explicitly labelled by the paper itself as a qualitative design observation**, not a quantified ablation — the paper states a full facts-only ablation is future work, and no specific percentage exists for this claim anywhere in the text. (One automated verification pass run during this check briefly hallucinated a "68.4%" figure for exactly this claim before being caught and corrected against the actual PDF — a small, self-contained demonstration of the exact failure mode this whole document exists to guard against, recorded here rather than quietly discarded.) This weakens, but does not remove, its relevance to AAMR's own Mem0 gold-rank-1-still-fails puzzle — see Experiment 3 below.

### Brain-inspired / consolidation mechanisms (Microsoft Human-Inspired Memory Architecture)

Verified exactly, including the approximate ID given (2605.08538, no correction needed): Microsoft Research (Kerestecioglu, Robsky, Vasters, Sharma, Kesselman), submitted 8 May 2026, confirmed independently via the MSR publication page and a co-author's own public writing.

| Mechanism | Failure mode targeted | Dependencies | Transplantability | Likely interaction with a Mem0-like baseline | Measurable outcome | Cost | Interference risk | Priority |
|---|---|---|---|---|---|---|---|---|
| Sleep-phase consolidation | Unbounded raw-episode growth | A background batch scheduler (default every 6h) | Low — architecturally heavy, touches the storage lifecycle, not a drop-in retrieval addition | Would change what Mem0 has *stored* by the time of query, not just how it's retrieved — confounds any transplant test unless isolated | Store size reduction, retention precision (paper reports 97.2%/58%) | High engineering time | Medium — changes the object under test, not additive to it | 2 |
| Interference-based forgetting | Retrieval noise from accumulated near-duplicates | An interference-scoring pass over the store | Medium | AAMR already tested a conceptually adjacent idea (association-graph retrieval fusion, `PMLAB-ASSOC-E1/E2/E3`) and found it **negative** (E3: −0.114 Recall@5) — real risk of repeating a known failure mode under a new name | Recall@k before/after | Medium | High — overlaps a track already found harmful once | 2 |
| Engram maturation | Premature promotion of one-off events to long-term status | A dual-trace store with a maturation curve (~1wk/~2wk) | Low — a new storage primitive, not a retrieval-side add-on | Orthogonal to Mem0's current design; would require a schema change | Precision of "mature" vs "fresh" classification | High engineering time | Low, but high blast radius if wrong | 2 |
| Reconsolidation on retrieval | Stale facts surviving because nothing revisits them | A labile/modifiable post-retrieval window (60 min default) | Low-medium — needs a state machine on top of storage | Directly touches AAMR's open research question G (updating without losing provenance) | Correction rate after re-exposure | Medium | Medium — AAMR's own doctrine already flags reconsolidation as an open, contested question even in the source literature it read in Phase 1 | 2 |
| Entity knowledge graph | Multi-hop questions | An entity-relation extraction and graph store | Medium | Mem0 already does some entity/fact fusion; a graph layer is additive in principle | Multi-hop accuracy | Medium-high | Medium | 3 |
| Hybrid multi-cue retrieval | Single-signal retrieval missing relevant items | Requires the other five mechanisms' outputs as cues | Low standalone — this is an integration mechanism, not isolable | N/A until the cues it fuses exist | N/A standalone | N/A standalone | N/A standalone | not isolable |

Its "synthetic calibration without benchmark exposure" claim is accurately characterized in the original brief for *threshold calibration specifically* (8/50 synthetic sessions, locked before touching real data) — but the paper does then report real benchmark numbers (a VSCode issue-tracking dataset and a first LongMemEval streaming run), so this is not a "no benchmark contact at all" methodology, only a "no benchmark contact for tuning" one. Worth citing precisely for AAMR's own future calibration work, since benchmark leakage is a repeatedly-stated concern here too.

### Learned routing: D-MEM / MemRouter

**D-MEM** (verified exactly, and disambiguated — see the executive conclusion — from the unrelated Zou et al. paper of a near-identical short name: arXiv 2603.14597, Song/Xin, UCSD/CMU, submitted 15 Mar 2026; Fast/Slow Reward-Prediction-Error routing, a "Critic Router" scoring Surprise/Utility, O(1) bypass vs O(N) restructuring, LoCoMo-Noise benchmark, >80% token reduction, all confirmed against the live abstract). This is a **write-time** gate: routine events take a cheap path, high-surprise/contradiction events trigger expensive restructuring. It is the closest match in the whole batch to AAMR's own dormant research bridge hypothesis 3 ("prediction error and outcome severity improve retention decisions beyond relevance and recency") — but AAMR currently has **no write-time signal infrastructure at all** to hang this on; adopting it is a bigger lift than a retrieval-side transplant. Code exists (`github.com/london-and-tequila/dmem`) but is sparse (2 stars, no description) — treat as unaudited if reused.

**MemRouter** (verified exactly: arXiv 2605.00356, Hu/Lin/Zhang/Ma/Wang, submitted 1 May 2026; ~12M trainable parameters — 0.17% of the 7B backbone — F1 52.0 vs 45.6, p50 latency 58ms vs 970ms, matched-harness with retrieval held fixed, all confirmed directly from the full text). This answers "what should enter durable memory?" on the **write/admission** side only, cleanly separated from retrieval — a genuinely well-controlled comparison AAMR should benchmark any future retention policy against. Its repo (`github.com/SongW-SW/MemRouter`) is real but is a one-commit README stub with no working code — the paper's numbers are legitimate, but nothing here is currently reusable off the shelf.

Compared against AAMR's own future-utility retention ideas (research question F): both D-MEM and MemRouter are evidence that "a small learned signal, cheaper than a full LLM call, improves the write/admission decision" is an active, validated direction elsewhere — supporting AAMR's premise that this is worth pursuing, while also meaning a future AAMR write-gate experiment has real published baselines to beat, not just intuition to test against.

### AutoResearch overlap: EvolveMem

Verified exactly (trivial title-spacing difference only): arXiv 2605.13941, Liu/Ye/Xia/Zheng/Xie/Ding/Yao, UNC-Chapel Hill/Berkeley/UCSC, submitted 13 May 2026; failure-log diagnosis, config-change proposals, revert-on-regression, explore-on-stagnation, all confirmed verbatim; real, working code (`github.com/aiming-lab/SimpleMem`, +25.7% LoCoMo / +18.9% MemBench over strongest baseline). It is not an isolated idea — SimpleMem, Omni-SimpleMem, AutoMem, MemEvolve, Evo-Memory and EvoArena form a small existing cluster doing versions of the same thing.

The distinction the request asked about is real: **EvolveMem's action space is its own retrieval configuration** — it never imports a different, independently-built system's mechanism. It optimizes one architecture against itself over time. AAMR's Phase A–D, by contrast, is about comparing *architecturally distinct, pre-existing, independently-designed* systems and porting code between them. That is a substantial methodological difference, not wording — but it is worth noting that EvolveMem's autonomous diagnose-propose-revert loop is a closer analogy to **AAMR's own research *process*** (`docs/00-project/bootstrapping-strategy.md`'s "using our own memory as a corpus," the mechanical claim-audit gates) than to AAMR's proposed memory *architecture*. If AAMR ever automates its own experiment-selection loop, EvolveMem is the closest published prior art for that meta-level activity, separate from the memory-mechanism question entirely.

### The closest precedent found: "Exploring Cross-Scenario Generality of Agentic Memory Systems" (2606.04315)

Not in the original list; found and read in full during the broad sweep. Chen/Gu/Yin/Long/Zeng/Liu/Guo/Zhou/Tang (MSU/GMU/Purdue), ~June 2026. Compares 8 pre-existing systems (SimpleMem, LightMem, PlugMem, HippoRAG, Mem-T, MemRL, others) under one fixed harness across 5 scenarios, and identifies concrete regime predictors — e.g. a benchmark's "structural rate" predicts whether graph/indexed methods beat note-based ones by margins from +13pp to −15pp, which is itself a sharper, quantified version of the "operating regimes" premise than anything else found. Its composite system, AutoMEM, **literally integrates retrieval code from two different named prior systems** — a PlugMem-graph variant using PlugMem's tag/semantic/episodic stores, and a graph built from LightMem's write-time summary index. This is the only primary-source-confirmed instance found anywhere of genuine cross-codebase component reuse between independently-designed agent memory systems.

It stops short of AAMR's full design in two specific, checkable ways: its ablation compares whole variants (single-pass vs multi-step; LightMem-graph vs PlugMem-graph) rather than a `BASE`/`+A`/`+B`/`+A+B` grid quantifying interaction; and it explicitly names a "tiered router" as unimplemented future work. This paper is the single most important piece of related work this document found, and it is recommended the project read it in full before finalizing any transplant-harness design, both to avoid duplicating its engineering choices and to correctly cite it as the closest known precedent rather than presenting Phase C as unprecedented.

One more candidate surfaced but **could not be verified**: "Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift" (OpenReview id `AIJsjIqfsp`, ~March 2026). OpenReview blocked direct fetch on three attempts; everything known about it comes from consistent secondary search summaries only: a 2×2 factorial design, 5 memory systems, "architecture transfer is system-dependent." The "code-to-math shift" framing in every summary found suggests it tests one system's *own* architecture generalizing across a task-domain shift, not cross-system mechanism transplant into a *different* system's baseline — but this is UNVERIFIED and the title is close enough to this project's own language that it should be checked directly by someone with OpenReview access before this document's reading of it is trusted.

---

## What is clearly not novel

Verified against the primary sources above, not assumed:

- **Multiple memory types in one system** — not novel (FluxMem, Microsoft, Engram, MemCon's multi-operation backend all do this; AAMR's own README already conceded APEX-MEM precedence on the structured/temporal combination specifically).
- **Brain-inspired memory architecture** — not novel, and not novel *comprehensively*: Microsoft's paper covers six mechanisms together, from a well-resourced lab, evaluated on a real benchmark.
- **Adaptive/learned structure selection** — not novel (FluxMem, explicitly, with a trained gate).
- **A controller deciding when/what/how much to retrieve** — not novel (MemCon, explicitly, as the paper's entire contribution).
- **Operating-regime dependence at the substrate level** ("no single substrate dominates") — not novel; this is "Harness the Memory"'s own headline finding, dated 15 Aug 2026.
- **Current/historical/transition temporal-state distinction** — not novel; A-TMA uses this exact vocabulary, Graphiti's bitemporal fields are functionally equivalent, and AAMR's README already conceded the structured-temporal combination to APEX-MEM.
- **Learned write/admission gating** — not novel (MemRouter, explicitly; D-MEM's fast/slow gate is a variant of the same idea on the write side).
- **Autoresearch / self-tuning of retrieval configuration** — not novel; not even a single paper, but a small existing cluster (EvolveMem plus at least five adjacent 2026 papers).

## What may still be an open gap

The one part of the described trajectory not found anywhere in either the targeted 11-paper check or the ~20-query broad sweep, corroborated by an independent literature tracker consulted during that sweep, is:

> **An explicit `BASE`/`BASE+A`/`BASE+B`/`BASE+A+B` interaction/synergy measurement, run on mechanisms extracted from two or more independently-designed, pre-existing systems' own codebases (not reimplemented from scratch, not both designed by one paper's authors), completed *before* any router is trained over the result.**

This is narrower than "operating regimes exist" (taken, "Harness the Memory") and narrower than "a controller helps" (taken, several times over). It is close to, but stops short of being taken by, A-TMA (multi-system harness + one overlay, no cross-host code porting) and by AutoMEM/Cross-Scenario-Generality (genuine cross-system code import, but a whole-variant comparison rather than a factorial interaction grid, and no router). This document could not find literal disproof that no one is attempting this — a negative search result is never proof of absence — but the search was real, primary sources were read in full for the two closest candidates, and an independent tracker agreed. That is the strongest form of "open, as far as anyone here can currently tell" available without deeper access (the blocked OpenReview paper is the one loose thread left).

Two smaller, more defensible gaps sit alongside it:
- A **failure-mode instrumentation layer** distinguishing storage/retrieval/reasoning failure at the granularity A-TMA proposes (bank-maintenance/retrieval/answer-time), applied to AAMR's *own* arena data — AAMR currently measures gold-in-context, gold-rank and end accuracy, with nothing in between. Nobody else's instrumentation is directly reusable here without adaptation, so building this for AAMR's own harness is legitimate, un-duplicated work regardless of the transplant question.
- A **published, reproducible account of what actually happens when you try** the transplant-and-ablate discipline, win or lose. Even a negative result here (mechanisms turn out mostly redundant, or transplants mostly fail to survive porting) would be a documented finding nobody else currently has in this form.

---

## First-mover / priority analysis

This needs to be precise, because it is easy to get comforting and wrong.

**What "Harness the Memory" already publicly removed, as of its 15 Aug 2026 submission date:** the specific sentence "no single memory substrate/system wins everywhere, therefore routing is motivated," stated as a general empirical claim across substrates, backbones and benchmarks. Any AAMR paper or writeup that states this as its own finding, without citing this paper, would be independently re-discovering something already dated and public. This is true regardless of whether Harness the Memory's code is ever released — an idea's priority timestamp is set by the moment it is stated in a way others can read and act on (submission to a public preprint server), not by the moment its implementation becomes available.

**What code publication does and does not establish:** code establishes reproducibility and lets others verify or extend the specific numbers reported. It does not retroactively create or remove priority on the *idea* — that was already set by the text. Conversely, its absence here does not weaken Harness the Memory's claim on the idea; it only means nobody, including this project, can yet check its 26-metric results independently.

**What this repository's own git history establishes, checked directly:** `docs/00-project/operating-plan-and-rules.md` (Phase A–D, including the `BASE`/`+A`/`+B`/`+A+B` interaction formula) and `docs/04-systems/comparative-memory-systems-lab.md` were both first committed **2026-08-23** — eight days *after* Harness the Memory's 15 Aug submission. AAMR cannot claim to have arrived at "operating regimes motivate routing" before that paper did; the timestamps do not support it, and this document will not soften that. What AAMR's 23 Aug commit *does* establish, on the same public, checkable basis, is the specific `BASE`/`+A`/`+B`/`+A+B` interaction-quantification formalism, applied to mechanisms sourced from independently-built systems — and as of this check (24 Aug), that specific formalism still has no confirmed public prior instance anywhere this document could find, including in the two closest papers (A-TMA, AutoMEM/Cross-Scenario-Generality).

**What would have to be completed publicly to make a credible claim on that narrower point:** the transplant would have to actually run (not just be designed), on a harness good enough that a skeptical reader could not attribute a result to a harness artifact rather than the mechanism, with the interaction term computed and reported whichever way it comes out — including the boring or negative case — and it would need to be public before anyone else's version of the same specific test. Right now AAMR has the harness (Phase A, running) and the formalism (Phase C, written) but zero completed transplant runs. Priority on a method that has not yet produced a single result is not yet earned; it is, at best, a registered intent with a timestamp, which is worth something procedurally (see the independence ladder's own I1 sealed-split logic — informational and temporal separation enforced cryptographically, not by good intentions) but is not a scientific claim yet.

---

## Interpretation of current Mem0 vs Hindsight results

Answering the six questions directly:

1. **Does "Harness the Memory" predict the narrow-vs-broad tradeoff?** Yes, directly — its own headline ("broad retrieval helps factual QA, excessive retrieval hurts sequential decision-making," "no substrate dominates") describes exactly the shape of Mem0 (narrow, precision@k 0.54, 106 tokens) vs Hindsight (broad, precision@k 0.12, 3158 tokens) found here. AAMR's n=10 sample is a consistent local anecdote for a published general pattern, not new evidence for it.
2. **Does Engram suggest why hybrid facts+chunks could matter?** As INFERENCE, plausibly — but weakly, since Engram's own version of this claim is qualitative, not ablated. It is a hypothesis worth testing on AAMR's own data (Experiment 3 below), not a result to cite as already established.
3. **Does A-TMA suggest retrieved facts may still need answer-time state resolution?** Yes, and this is the sharpest actionable point in this whole document: A-TMA's three-way failure split (bank-maintenance / retrieval / answer-time resolution) names an instrumentation gap AAMR's current arena data genuinely has. AAMR measures gold-in-context, gold-rank, and end accuracy, with no stage in between recording *why* a reader with gold in context still answered wrong.
4. **Does MINTEval contradict "retrieval is not the bottleneck"?** Not directly — but it is a real caution against generalizing the claim. MINTEval's own dominant failure driver is retrieval/construction (41.7% of failures), at a much larger scale (15.6k QA, up to 1.8M context tokens) than AAMR's n=10 LongMemEval-S sample. AAMR's finding is specifically "gold already reached the context and the answer was still wrong" — a narrower, different claim than "retrieval fails to surface gold at all," which is what dominates MINTEval's regime. Both can be true simultaneously in their own regimes; neither generalizes to the other's without more data.
5. **Is Mem0-like retrieval actually a good BASE, or premature from too few observations?** Premature to call validated, reasonable to use as a *Tier-E working baseline*. `retrieval_unobservable_units: 5` out of 10 means the retrieval-quality numbers above rest on an effective n of 5 per system. That is enough for an exploratory transplant test (see Experiment 1) under this project's own doctrine, and nowhere near enough to defend as "the" baseline in anything written for outside readers.
6. **What additional evidence is needed before calling it the baseline?** Exactly what the project's own promotion path already specifies: repeat at larger n or with a second mechanism (still Tier E), then a sealed I1 held-out test — plus, ideally, a second, never-inspected benchmark (Phase D). MINTEval is now a concrete, verified, real candidate for that role, released under its current name with code and data (`github.com/amy-hyunji/MINTEval`, `dinobby/MINTEval` on HuggingFace) — worth registering as a Phase D candidate. This document is not recommending it be run now; the cost/benefit of a second full benchmark pass belongs to a later decision.

---

## Ranked transplant candidates

Priority scale: 1 (lowest) – 5 (highest).

| Mechanism | Source | Target failure | Why it may help | How isolated | Dependencies | Impl. complexity | Expected API cost | Expected eng. time | Benchmark-tuning risk | Best falsifying test | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Deterministic entity resolution (trigram + union-find) | Hindsight, `entity_resolver.py` — **code-verified in-repo, I0 tier**, not paper-claimed | Entity-name-variation failures inside Mem0's narrow retrieval | Already read from the shipping code, zero training, zero model calls, directly testable against Mem0's own 8 failures | Very high — a single pure function, no coupling to Hindsight's extraction pipeline | None beyond porting ~1400 lines of deterministic Python | Low | ~$0 (deterministic) | Hours | Low — it's an existing, unrelated system's shipped code, not tuned to AAMR's sample | Transplant onto Mem0, replay the frozen 10-unit sample; zero units flip and precision@k unchanged = fail | **5** |
| Raw source-chunk fallback alongside extracted context | Engram's *design observation* (qualitative) + AAMR's own related-work note on "Verbatim Chunks Beat Extracted Artifacts" | Mem0 failures where gold was in context but the answer was still wrong | Directly tests AAMR's own unexplained puzzle; cheap since it changes only what's included in the prompt, not retrieval | High — no new component, a context-assembly change only | Needs the just-shipped context-text persistence fix to actually be exercised on a fresh run first | Low | ~$1 (reader calls only) | Hours, once the persistence prerequisite is confirmed | Low | No gold-in-context failure flips with raw chunk added = fail | **4** |
| Cheap deterministic approximation of A-TMA's current/historical/transition tagging | A-TMA (2607.01935) — reimplemented from the paper's description, not from code (none public), and explicitly *not* the paper's trained Qwen3B overlay | The 3 temporal-reasoning units where Mem0 scored 0/3 and Hindsight's signal weakened to 1/3 | Names an instrumentation and reasoning gap this project's own data plausibly has; cheapest possible test of the concept before committing to the full trained version | Medium — a heuristic reimplementation, not a reproduction of A-TMA itself; must be labelled as such in any writeup | A timestamp/order heuristic over already-stored items; no training | Low-medium | ~$1–2 | Half a day | Medium — hand-tuning a 3-unit heuristic risks fitting the sample; report as directional only | 0/3 unchanged and reader transcripts show no behavioral difference = fail | **4** |
| Write-admission classifier | MemRouter (2605.00356) | Over-storage / low-value writes | Cleanly separated, well-controlled published baseline to benchmark against | Medium — paper is precise, but repo is an empty stub, needs reimplementation from scratch | Needs labelled admission-quality data AAMR does not yet have | Medium-high | Low (small classifier) | Days–weeks | Low if trained on AAMR's own data | No improvement over random admission on held-out data = fail | 3 |
| CUP-Mem premise/state adjudication | CUPMem (`external/repos/icedreamc__STALE`) — already vendored, no reimplementation needed | Premise-resistance / implicit-conflict questions | Code already local; the paper's own 68.0% STALE result vs this project's 1/4 LongMemEval pilot is an unexplained transfer gap worth understanding on its own | Medium — needs disentangling from the rest of the CUPMem pipeline first | None beyond the code already present | Medium | ~$1–2 for a diagnostic pass | A day | Low | Diagnostic pass finds the 1/4-vs-68% gap is a benchmark-construct mismatch, not a mechanism failure = informative regardless of direction | 3 |
| AutoMEM's cross-system component-wiring approach | Cross-Scenario-Generality (2606.04315) — read as **methodology**, not as a mechanism to import | Engineering risk in AAMR's own future transplant harness | The only found precedent for physically wiring two independent systems' code together; cheap to learn from before designing AAMR's own plumbing | High (reading only) | None | Low (reading) | $0 | Hours | N/A | N/A — this is a reading recommendation, not an experiment | 3 |
| Fast/slow Reward-Prediction-Error write gate | D-MEM (2603.14597) | Expensive restructuring on every write regardless of novelty | Matches AAMR's own dormant "prediction error and outcome severity" bridge hypothesis | Low — AAMR has no write-time signal infrastructure to attach this to yet | A write-time "surprise" scorer, none of which exists in AAMR today | High | Low per-call, high build cost | Weeks | Medium | No cost/accuracy improvement over uniform write cost = fail | 2 |
| Microsoft reconsolidation-on-retrieval | Microsoft Human-Inspired (2605.08538) | Stale facts nothing ever revisits | Directly touches AAMR's open research question G | A labile-state machine on top of storage | Storage-model change, not a retrieval add-on | High | Low | Weeks | Medium — the source paper itself treats this as calibrated on synthetic data only | No correction-rate improvement after re-exposure = fail | 2 |
| Microsoft interference-based forgetting | Microsoft Human-Inspired (2605.08538) | Near-duplicate accumulation degrading recall | Conceptually adjacent to a mechanism class AAMR cares about | An interference-scoring pass | Overlaps `PMLAB-ASSOC-E1/E2/E3`, already found **negative** for a related idea (association-graph fusion, −0.114 Recall@5) | Medium-high | Low | Days–weeks | High — real risk of re-discovering the same negative result under a new name | Recall@k does not improve, or degrades, replicating the ASSOC finding = fail (and informative) | 2 |
| Sleep-phase consolidation / engram maturation | Microsoft Human-Inspired (2605.08538) | Unbounded raw growth, premature promotion | High conceptual fit with AAMR's own four-store design diagram | A background scheduler and a maturation curve | Touches the storage lifecycle itself, not additive to retrieval | High | Low | Weeks+ | Medium | N/A until a later phase — not a cheap isolable test today | 2 |
| Bi-temporal filtering | Engram (2606.09900) | Stale-vs-current confusion | AAMR already has this validated independently (`PMLAB-REV-V0`, 0.944 exact) | High | None — confirmatory only | Low (citation/validation, not a build) | $0 | Hours | Low | N/A — this is a "cite as converging evidence" item, not a transplant target | 2 (as validation, not as new work) |

---

## Exactly three next experiments

All three are Tier E in this project's own doctrine terms (`docs/00-project/operating-doctrine.md`): hours, model-free or near-free, existing frozen data, no sealed-split gate required. All three use the existing 10-unit `arena-expansion-v1` sample and the existing fixed-reader plumbing; none requires a new corpus, a new system adapter, or a controller.

### Experiment 1 — Transplant Hindsight's deterministic entity resolver onto Mem0

- **HYPOTHESIS:** Some of Mem0's 8 failures on `arena-expansion-v1` are attributable to entity-name variation that Hindsight's code-verified deterministic resolver (trigram similarity + union-find, `entity_resolver.py`) would fix without importing Hindsight's context-token cost.
- **BASELINE:** Mem0 alone (2/10, precision@k 0.54, 106 mean context tokens).
- **INTERVENTION:** Mem0's retrieval pipeline with Hindsight's entity-resolver applied as a canonicalization pass over stored items and queries; reader, judge, and unit set unchanged.
- **CONTROLLED VARIABLES:** same 10 frozen units, same fixed reader, same judge, report the token-budget delta explicitly (should be ~0 since the transplant is deterministic and pre-retrieval).
- **METRICS:** units flipped, precision@k delta, context-token delta, marginal cost (should be ~$0).
- **FAIL CONDITION:** zero units flip and precision@k is unchanged.
- **SUCCESS CONDITION:** at least one of the 8 current Mem0 failures becomes correct, or precision@k improves without a token-budget increase.
- **COST:** effectively $0 beyond a handful of reader calls already budgeted elsewhere.
- **WHAT IT WOULD PROVE:** whether a specific, code-verified mechanism from one independently-built system transplants additively onto a different system's baseline *at all* — the first real data point for Phase C, which has not produced one yet.
- **WHAT IT WOULD NOT PROVE:** general transplantability of mechanisms; n=10 (effectively n≤8 failures) is not powered for an effect-size claim; this is a single-mechanism test, so it says nothing yet about interference or synergy, which needs a second validated mechanism first.

### Experiment 2 — Cheap deterministic approximation of A-TMA's temporal tagging, on the weakened temporal-reasoning subset

- **HYPOTHESIS:** A minimal, deterministic current/historical/transition tag (timestamp order plus lexical overlap over already-stored items — explicitly *not* A-TMA's trained Qwen3B overlay, since no code is public) recovers some of the temporal-reasoning failures where Mem0 scored 0/3 and Hindsight's own signal weakened from 1/1 to 1/3.
- **BASELINE:** Mem0 alone on the 3 temporal-reasoning units (0/3); Hindsight (1/3) as a reference point, not a target to beat.
- **INTERVENTION:** Mem0's retrieval plus the deterministic tag, same fixed reader.
- **CONTROLLED VARIABLES:** same 3 units, same reader/judge; the result must be reported as a labelled heuristic reimplementation, never as a reproduction of A-TMA itself.
- **METRICS:** accuracy on the 3-unit subset; a qualitative read of whether the reader's stated reasoning stopped citing a superseded fact as current.
- **FAIL CONDITION:** 0/3 unchanged and no visible change in the reader's failure transcripts.
- **SUCCESS CONDITION:** at least one unit flips, or the reader transcripts show it explicitly stopped treating a superseded fact as current even without flipping the final answer.
- **COST:** ~$1–2.
- **WHAT IT WOULD PROVE:** whether the *concept* A-TMA names is worth the much larger investment of a full, trained reproduction on this project's own data — a cheap go/no-go gate, not a test of A-TMA's own reported +0.240 number (which was measured on LTP against Graphiti, a different benchmark, different baseline, and the real trained mechanism).
- **WHAT IT WOULD NOT PROVE:** anything about A-TMA's actual reported effect size; n=3 is too small for more than a directional read — a single flip is a hint, not a finding.

### Experiment 3 — Raw source-chunk supplementation on Mem0's gold-in-context-but-wrong failures

- **HYPOTHESIS:** Some Mem0 failures happen even with gold in context because Mem0 delivers an extracted/summarized representation rather than the raw source turn; supplementing with the raw verbatim turn recovers some of them (testing AAMR's own version of Engram's qualitative claim, and of the already-verified "Verbatim Chunks Beat Extracted Artifacts" finding already in this project's related-work notes).
- **PREREQUISITE:** confirm the recent context-text persistence fix actually captures raw text on a fresh run — the existing `fixed-reader-report.json` predates the fix and is still recorded as blocked.
- **BASELINE:** Mem0 alone, restricted to the subset of its units where `gold_in_context: true` but the answer was still scored wrong.
- **INTERVENTION:** Mem0's delivered context plus the corresponding raw session turn(s) appended verbatim; same fixed reader.
- **CONTROLLED VARIABLES:** same restricted unit subset, same reader/judge; report the token-budget delta (this intervention is expected to increase it, unlike Experiments 1 and 2).
- **METRICS:** accuracy delta on the restricted subset; token delta.
- **FAIL CONDITION:** no unit flips.
- **SUCCESS CONDITION:** at least one gold-in-context failure flips to correct with the raw chunk added.
- **COST:** ~$1, once the prerequisite fresh run exists.
- **WHAT IT WOULD PROVE:** whether representation-completeness (facts vs. raw) is a real, present cause of some of this project's *own* observed failures — resolving the ambiguity this project's own arena report already names but does not explain.
- **WHAT IT WOULD NOT PROVE:** general superiority of raw chunks over structured facts at any scale beyond this sample; a fail result here would actually *strengthen* the "retrieval success ≠ answer success" reading by pointing at reader/reasoning capacity instead of representation as the remaining unexplained factor.

---

## Gates before building a controller

**Yes, clearly too early**, and not only by this document's outside judgement — by the project's own already-adopted doctrine. The WIP limit rule ("at most two experiments per track may sit in designed-not-executed") and the sequential Phase A→B→C→D structure both already forbid skipping to a controller before Phase C's ablation grid has run even once. Zero mechanisms currently have a single validated, isolated Δ on this project's own data; a controller trained today would be routing over things nobody has shown transplant at all.

Proposed gates, built from mechanisms already in this project's own promotion-path ladder rather than invented for this document:

1. **At least two independently-transplanted mechanisms**, each showing a positive isolated Δ on a frozen Tier-E sample (Experiments 1 and 2/3 above are the first attempts at exactly this).
2. **Each Δ repeated once** — either at a larger n or as a second, structurally different probe set — per the doctrine's own promotion path ("Tier E result → repeat at larger n or with a second mechanism, still Tier E"), before anyone treats a single-shot n≤10 flip as a real effect.
3. **At least one completed `BASE+A+B` interaction measurement**, not just two separate `BASE+A` and `BASE+B` results — because a controller that routes between two mechanisms whose *combination* has never been measured could be routing into a regime that is actually worse than either alone (`interaction < 0`), and nobody would know until the controller found out the hard way.
4. **At least one sealed I1 held-out check** on whichever mechanism looks most promising, before it is treated as validated rather than exploratory — matching the project's own independence-ladder logic (informational/temporal separation enforced cryptographically) rather than trusting a same-process re-check.

Only once all four are met does "which mechanism to activate, depending on regime" become a question with enough validated raw material to be worth training a policy over. Before that, a controller is a solution in search of confirmed mechanisms.

---

## Recommended project positioning

**A. Conservative academic**

> AAMR evaluates independently-designed LLM agent memory systems under one shared, frozen harness, and measures how a mechanism verified as differentiating inside one system's source code performs when isolated and inserted into a different system's baseline retrieval. No general claim is made about transplant success rates, mechanism interaction, or any learned controller; the current, demonstrated contribution is the harness, per-probe failure attribution across systems, and a small number of controlled single-mechanism transplant results, reported whichever way they land.

**B. Strong but defensible**

> Rather than proposing another monolithic memory architecture, AAMR studies memory as a set of mechanisms with potentially distinct operating regimes, evaluated under a shared harness rather than each system's own. Where prior work (notably "Harness the Memory") has established that no single memory substrate dominates and has argued for routing between them, and where at least one other group has begun combining named components from two prior systems, AAMR's distinguishing commitment — not yet demonstrated by anyone else this document could find — is an explicit `BASE`/`BASE+A`/`BASE+B`/`BASE+A+B` interaction measurement between mechanisms sourced from independently-built systems, completed before any routing decision is trained.

**C. Ambitious research vision**

> AAMR treats the current landscape of LLM agent memory systems not as a set of competing final architectures but as a set of partially redundant, partially complementary mechanisms whose value only becomes measurable once they are extracted from their source systems, tested for genuine additive or interfering interaction on common ground, and — if and only if that interaction turns out to be worth exploiting — recombined by a controller built on measured evidence rather than intuition. If the project's Phase C interaction measurements show real synergy, the durable contribution is a reusable methodology for mining, validating and composing memory mechanisms across an active and fast-moving field, rather than one more memory system on a leaderboard; if they mostly show redundancy, that is a publishable finding in its own right about how much smaller the real design space is than the paper count suggests.

None of the three claims priority on "operating regimes exist" (taken) or "a controller helps" (taken, repeatedly). All three stake their claim on the transplant-then-interaction-measurement discipline specifically, which is the one part of the trajectory this document's search did not find already done.

---

## GO / PIVOT / STOP decision

**GO — for the mechanism-transplant research direction specifically, with the novelty claim narrowed as above.** Not a verdict on the repository as a whole.

- **Evidence for continuing:** the harness (Phase A) is real and running with actual cost/accuracy data across five systems; the transplant formalism (Phase C) was written independently of this literature check and, on inspection, is not duplicated by anyone found; three cheap, falsifiable, doctrine-compliant experiments are ready to run today at near-zero marginal cost and would produce this project's first-ever transplant data point regardless of which way they land.
- **Strongest threat:** the Harness-the-Memory/MemCon/MemRouter author cluster — an active, multi-paper, apparently coordinated program already covering the controller side of this space from several angles. It has not yet published the specific cross-system transplant-and-ablate step, but it is exactly the kind of group positioned to notice and close that gap next.
- **Strongest prior-art overlap:** "no single substrate dominates, therefore route" — already public, dated, and multiply confirmed (Harness the Memory, plus the general shape of Mem0-vs-Hindsight's own narrow/broad tradeoff matching it).
- **Most promising remaining gap:** the `BASE`/`+A`/`+B`/`+A+B` interaction grid across mechanisms sourced from independently-built systems, feeding a router only after that grid exists — confirmed unoccupied by both the targeted check and the broad sweep, with one loose thread (the blocked OpenReview paper) still worth a direct look.
- **What single result over the next 2–3 experiments would most increase confidence:** any confirmed, once-replicated, non-zero Δ from Experiment 1 — the cheapest, most controlled possible test, using a mechanism this project has already verified at code-read tier rather than merely paper-claimed. A first successful transplant of *any* kind, however small, is the first evidence Phase C's premise is mechanically achievable here at all, not just plausible on paper.
- **What result would trigger abandoning or pivoting the mechanism-routing hypothesis:** if all three recommended experiments — including Experiment 1, the cheapest and most controlled of the three, using code this project has already read and trusts — show zero effect, that would suggest the bottleneck on this project's own data is not mechanism-level at all (more likely reader/reasoning capacity, judge strictness, or a small-sample ceiling), and continuing to chase mechanism transplant without addressing that would be building on an untested foundation. That is a sharp, cheap, three-experiment pivot trigger, not a vague "if it doesn't work out" one.

---

## Sources

Every entry below was checked against a primary source during this session (2026-08-24) unless marked otherwise.

**Already verified inside this repository before this document (`docs/00-project/related-work-and-novelty.md`):**
- APEX-MEM — arXiv:2604.14362, ACL 2026 (Amazon). PAPER CLAIM, previously verified in-repo.
- "Verbatim Chunks Beat Extracted Artifacts" — arXiv:2601.00821. PAPER CLAIM, previously verified in-repo.
- Tenure — arXiv:2605.11325. PAPER CLAIM, previously verified in-repo.

**Verified for this document, primary source read directly:**
- "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents" — Huang, Zhang, Wu, Chen, Jiang, Yang, Yang, Zou, Zhang, Wu, Wu, Chang, Yu, Liu, Caliskan. arXiv:2608.15008, submitted 15 Aug 2026. No code found; paper states code planned "upon acceptance." Accessed 2026-08-24.
- "Memory as a Controlled Process: Learned Adaptive Memory Management for LLM Agents" (MemCon) — Jiang et al. (14 authors incl. Chang, Caliskan, Wu). arXiv:2607.13591, submitted 15 Jul 2026. Code: `github.com/ericjiang18/MemCon` (public, no LICENSE file despite MIT README claim). Accessed 2026-08-24.
- "Choosing How to Remember: Adaptive Memory Structures for LLM Agents" (FluxMem) — Lu, Wu, Liu, Xu, Li, Wang, Hu, Ding, Sun, Lu, Zhang. arXiv:2602.14038, submitted 15 Feb 2026. No code found. Name collision noted with two unrelated papers also titled "FluxMem" (arXiv:2603.02096, arXiv:2605.28773). Accessed 2026-08-24.
- "A-TMA: Decoupling State-Aware Memory Failures in Long-Term Agent Memory" — Shi, Tang, Tung. arXiv:2607.01935 (v1 2 Jul, v2 8 Jul 2026). No code found. Accessed 2026-08-24.
- "D-MEM: Dopamine-Gated Agentic Memory via Reward Prediction Error Routing" — Song, Xin. arXiv:2603.14597, submitted 15 Mar 2026. Code: `github.com/london-and-tequila/dmem` (public, sparse). Accessed 2026-08-24. **Distinct from** "Remember the Decision, Not the Description" (DeMem) — Zou et al., arXiv:2605.10870, 11 May 2026, already logged in `docs/07-literature/full-read-notes/2026-zou-demem.md`; no code found for the Zou paper.
- "Human-Inspired Memory Architecture for LLM Agents" — Kerestecioglu, Robsky, Vasters, Sharma, Kesselman (Microsoft Research). arXiv:2605.08538, submitted 8 May 2026. No code found. Accessed 2026-08-24.
- "MemRouter: Memory-as-Embedding Routing for Long-Term Conversational Agents" — Hu, Lin, Zhang, Ma, Wang. arXiv:2605.00356, submitted 1 May 2026. Code: `github.com/SongW-SW/MemRouter` (README only, no working code). Accessed 2026-08-24.
- "LongMINT" / "MINTEval: Evaluating Memory under Multi-Target Interference in Long-Horizon Agent Systems" — Lee, Chen, Singh, Khan, Stengel-Eskin, Bansal. arXiv:2605.18565 (v1 18 May "LongMINT", v2 19 May 2026 renamed "MINTEval" — current version of record). Code/data: `github.com/amy-hyunji/MINTEval`, `huggingface.co/datasets/dinobby/MINTEval`. Accessed 2026-08-24.
- "Supersede: Diagnosing and Training the Memory-Update Gap in LLM Agents" — Patel. arXiv:2606.27472, submitted 25 Jun 2026, preprint under review. Code: `github.com/Vrin-cloud/supersede` (Apache-2.0). Accessed 2026-08-24.
- "Less Context, More Accuracy: A Bi-Temporal Memory Engine for LLM Agents..." (Engram) — Wang. arXiv:2606.09900, submitted 5 Jun 2026. Code: `github.com/ly-wang19/engram` (AGPL-3.0/commercial). Accessed 2026-08-24.
- "EvolveMem: Self-Evolving Memory Architecture via AutoResearch for LLM Agents" — Liu, Ye, Xia, Zheng, Xie, Ding, Yao. arXiv:2605.13941, submitted 13 May 2026. Code: `github.com/aiming-lab/SimpleMem` (EvolveMem subfolder). Accessed 2026-08-24.
- "Exploring Cross-Scenario Generality of Agentic Memory Systems: Diagnostics and a Strong Baseline" — Chen, Gu, Yin, Long, Zeng, Liu, Guo, Zhou, Tang. arXiv:2606.04315, ~Jun 2026. Code status not confirmed. Accessed 2026-08-24.

**Found but UNVERIFIED — flagged, not relied upon:**
- "Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift" — OpenReview id `AIJsjIqfsp`, ~Mar 2026. Access blocked three times; details from secondary search summaries only. Recommend a direct check by someone with OpenReview access.
- "Are We Ready For An Agent-Native Memory System?" — Zhou et al., arXiv:2606.24775, ~Jun 2026. Confirmed at abstract level only; steps 3–5 of the transplant pipeline unconfirmed either way.

**Survey papers, useful as field maps, confidence noted:**
- Zhang et al., "A Survey on the Memory Mechanism of LLM-based Agents," arXiv:2404.13501 / ACM TOIS. PRIMARY (repo checked: `github.com/nuster1128/LLM_Agent_Memory_Survey`).
- Liu et al., "Memory in the Age of AI Agents: A Survey," repo `github.com/Shichun-Liu/Agent-Memory-Paper-List`. PRIMARY (repo checked directly).
- "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers," arXiv:2603.07670. SECONDARY (search-confirmed only).
- "From Storage to Experience," arXiv:2605.06716, repo `github.com/FeishuLuo/Evolving-LLM-Agent-Memory-Survey` (already present in this repo's `external/repos/`). SECONDARY.
- "Externalization in LLM Agents," arXiv:2604.08224. SECONDARY.

**In-repository primary evidence cited above (MEASURED BY US):**
- `data/lab/arena/expansion-report.json`, `data/lab/arena/fixed-reader-report.json`, `data/lab/arena/pilot-*.json`, `data/lab/arena/pilot-graphiti-blocked.json`.
- `docs/00-project/operating-plan-and-rules.md`, `docs/00-project/operating-doctrine.md`, `docs/00-project/independence-ladder.md`, `docs/00-project/decision-log.md`, `docs/00-project/related-work-and-novelty.md`.
- `docs/04-systems/comparative-memory-systems-lab.md`, `docs/04-systems/hindsight-mechanism-sheet-v0.md`, `docs/04-systems/temporal-memory-model-comparison-v0.md`.
- `docs/07-literature/full-read-notes/2026-zou-demem.md`, `docs/07-literature/reading-queue.md`, `docs/07-literature/evidence-ledger.csv`, `data/catalogs/papers-curated.csv`.
- `external/repos/icedreamc__STALE/README.md`, `external/repos/ericjiang18__MemCon` (local clone).
- `memory/CURRENT_STATE.md`, `memory/README.md`.
- Git history: `git log --follow` on `docs/00-project/operating-plan-and-rules.md` and `docs/04-systems/comparative-memory-systems-lab.md` (both first committed 2026-08-23).

---

## Empirical update after fixed-reader rerun and context ablation

**Appended, not rewritten.** Everything above was written before the measurements
below existed and is left exactly as it was.

### The fixed-reader blocker is resolved

The earlier fixed-reader experiment could not run: the runner recorded
`context_tokens` and discarded the context, and both stores are reset per unit,
so nothing could be looked up. Contexts are now persisted (`context_texts`,
evidence order, per-evidence session times) with a regression test that fails
when they are not. Both systems were rerun on the same frozen
`arena-expansion-v1` for telemetry only — no setting changed — for $5.1732 of a
$6.00 cap.

Retrieval replicated across the six units Mem0 had run twice: gold-in-context
identical on all six, gold rank identical on all six, precision@k identical on
three and within 0.2 on two.

### Same reader over both contexts

| arm | correct | gold-in-context | mean gold rank | mean p@k | mean context |
|---|---|---|---|---|---|
| Hindsight | 7/10 | 9/9 | 10.44 | 0.088 | 3,117 tok |
| Mem0 | 4/10 | 8/9 | 1.00 | 0.578 | 106 tok |
| question only | 0/10 | — | — | — | 0 |

Memory helped on 8 of 10 probes and interfered on none. Both systems roughly
doubled once a reader composed the answer, so the earlier 2/10-vs-4/10 was
substantially an artefact of judging a stored memory against a gold answer.

### Context-size ablation (`arena-context-ablation-v1`, $0.0288)

| Hindsight budget | 102 tok | 500 | 1000 | 3117 |
|---|---|---|---|---|
| correct | 4/10 | 6/10 | 6/10 | 7/10 |

**At Mem0's own per-probe budget Hindsight scores 4/10 — exactly Mem0's score.**
The advantage vanishes at equal context size. In an ablation where only the
budget varies, accuracy is monotone in it.

### Provenance fallback (refuted)

| | correct |
|---|---|
| Mem0 compact | 4/10 |
| Mem0 compact + top-1 raw source session | 4/9 |
| raw source session only | 3/9 |

```
COMPACT_WRONG_RAW_FIXES  0
RAW_CAUSES_REGRESSION    0
```

Appending ~2,150 words of verbatim source behind Mem0's top-1 hit repairs none of
its failures. Raw-only is *worse* than compact, so compaction is doing work
rather than merely losing information.

### SUPERSEDES PRIOR EXPERIMENT PRIORITY

The ranking above put Hindsight's entity resolver at priority 5 as a transplant
candidate. That ordering is superseded as the *next* experiment, on two grounds
measured since:

1. Mem0 places the gold session at **rank 1 in 8 of 9** observable units and
   still answers 4 of 10. Whatever dominates these failures, it is not entity
   resolution — the right memory is being found and ranked first.
2. `BROAD_CONTEXT_EXPANSION` now has controlled evidence that no other candidate
   has: a monotone budget/accuracy curve with the budget as sole variable.

The entity resolver remains a candidate and is **not dropped**; it is no longer
the next thing to test. `RAW_PROVENANCE_EXPANSION` is **dropped** as a next
candidate at zero repairs out of nine. A-TMA and temporal mechanisms are
**held**, untouched by these experiments.

Detail: [`CONTEXT_AND_PROVENANCE_ABLATION_V1.md`](CONTEXT_AND_PROVENANCE_ABLATION_V1.md).
