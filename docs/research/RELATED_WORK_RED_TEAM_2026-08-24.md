> **Publication note, 2026-11-12.** Written on 2026-08-24 and kept in one local working tree until this date; other
> documents and project-memory records cited it while it was unpublished. Everything below this note is the unedited
> original (SHA-256 of the original file: `3cf47b1c444354edeb4506edf796762ddd7f37e8e7e032e9f6251a21f772dea8`). It is a planning record, not a result. Where it and
> [`MECHANISM_REGIME_EVIDENCE_LEDGER.md`](MECHANISM_REGIME_EVIDENCE_LEDGER.md) disagree, the ledger wins. All arena numbers
> are on `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1, with 4 to 10 questions per test.
>
> What changed since: the note "added after this search completed" and the Claim 4 row rely on
> `arena-context-ablation-v1`, whose Mem0 arms were later invalidated (contaminated stores). On clean stores raw
> provenance produced 2 repairs in 17 units with 0 regressions (ledger Entry H), so "zero repairs, drop" no longer holds.
> The prior-art findings themselves were not re-checked at publication.

# Related Work Red-Team — 2026-08-24

Status: adversarial follow-up to `RELATED_WORK_AND_POSITIONING_2026-08-24.md`, same day. Goal was explicitly to attack, not confirm, that report's remaining novelty claim. Research only — no code touched, no experiments run, `arena-context-ablation-v1` untouched throughout.

Labelling: **PRIMARY VERIFIED** (actual abstract/PDF/repo read), **PRIMARY-EQUIVALENT** (first-party conference/venue metadata, not the paper site itself, cross-corroborated), **SECONDARY LEAD** (search-snippet or citing-paper mention only), **UNVERIFIED** (could not confirm by any method).

## Search objective

Attack the positioning report's most defensible claim: *"Take mechanisms originating in independently-built memory systems, transplant them into a common baseline, measure `BASE`/`+A`/`+B`/`+A+B` interactions under a frozen harness, and only then train a router over mechanisms with demonstrated positive operating regimes."* Also cover a second, newer target that the positioning report predates: AAMR's `arena-context-ablation-v1` experiment, which asks whether Hindsight's advantage over Mem0 is context *volume* or preserved *provenance/detail* — a retrieve-then-conditionally-expand-to-raw-source question.

## Search protocol

Five parallel agents, one per track cluster (A: cross-system transplant + AutoMEM deep-dive; B: the blocked OpenReview "Memory Transplants" paper; C+D: factorial interaction and router-after-validation; E+F: retrieve-then-expand and context sufficiency; G+H: temporal overlays on multiple hosts and a July–August 2026 recency sweep). All five were interrupted once by a host-process restart mid-run and resumed from their saved transcripts rather than restarted from zero. Final tally: **≥113 distinct search queries** across the five tracks (31 + 13 + 29 + 20 + a further ~20 in Track B's multi-engine attempt on the OpenReview paper), well past the 20-query floor, plus upward of 50 individual primary-source fetches. No track needed three-consecutive-empty-queries to stop; each was cut off by a completion decision once its assigned questions were answered.

## Newly found works

Not previously known to AAMR, found and at least PRIMARY-VERIFIED or PRIMARY-EQUIVALENT unless marked otherwise:

- **"Memory in the LLM Era: Modular Architectures and Strategies in a Unified Framework"** — arXiv:2604.01707 (Apr 2, rev. Aug 6, 2026). The most important find of this pass — see below.
- **"Exploring Cross-Scenario Generality of Agentic Memory Systems" / AutoMEM** — arXiv:2606.04315. Already known, but re-verified in far more depth (all 12 requested questions answered against full text); the correction matters more than the paper being "new."
- **GRAVITY** — arXiv:2605.01688 (May 3, 2026). Structural-anchoring overlay wrapped around 5 independent hosts (Zep, Mem0, A-Mem, LiCoMemory, LightMem) with a real per-host before/after table.
- **TierMem** — arXiv:2602.17913 (Feb 20, 2026, ICLR 2026/OpenReview). Two-tier summary→raw-log architecture built directly on top of Mem0, with a learned RL-trained escalation router.
- **Eywa** — arXiv:2605.30771 (May 29, 2026). Compact-retrieval → fixed-rule raw-episode-rescue architecture.
- **"Diagnosing Retrieval vs. Utilization Bottlenecks in LLM Agent Memory"** — arXiv:2603.02473 (Mar 2, 2026, MemAgents Workshop @ ICLR 2026). Names Mem0 explicitly; 3×3 write-strategy × retrieval-method design.
- **"Mem0 vs. long-context LLM inference"** — arXiv:2603.04814 (Mar 5, 2026).
- **"Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift"** — OpenReview `AIJsjIqfsp`, ICLR 2026 MemAgents Workshop poster (Feng, Yao, Lewis). Resolved this session — see below.
- **"The Power of Noise"** — arXiv:2401.14887 (SIGIR 2024, well-established) and **"Sufficient Context"** — arXiv:2411.06037 (Google Research, Nov 2024). General-RAG prior art for context-breadth-vs-accuracy.
- A cluster of July–August 2026 temporal/state papers checked and *ruled out* as multi-host overlays: TOKI (2606.06240), MemTxn (2607.27834), TGMS (2607.10265), MemTX (2607.23929), Governed Persistent Memory (2608.12476), "From Faulty Memories to Corrected Actions" (2608.10502), StateAuditor (2608.01619) — all standalone, single-architecture evaluations, not overlays applied across independent pre-existing hosts.
- A debunked vendor claim: vectorize.io's public "Hindsight 94.6% vs. Mem0 49.0%" LongMemEval comparison cites arXiv:2603.04814 as independent support — that paper **does not mention Hindsight at all**. The comparison appears to blend a self-reported vendor number with an unrelated paper's Mem0 number. Treat as unreliable; do not cite as external corroboration of AAMR's own Mem0-vs-Hindsight gap.

## Cross-system transplant prior art

### AutoMEM, corrected

The positioning report's original characterization — "its ablation is limited (single-pass vs multi-step; LightMem-graph vs PlugMem-graph)" — undersold it. Direct full-text verification (including in-page search for `router`, `synerg`, `interaction`, `isolat`, `BASE`, `transplant`) establishes:

- BASE is explicit and named: **DCI-Lite** (raw trajectory + grep/read agent), LoCoMo = 45.0.
- BASE+A (LightMem-derived graph index) = 67.3 — isolated, PRIMARY VERIFIED.
- BASE+B (PlugMem-derived graph index) = 66.0 — isolated, PRIMARY VERIFIED.
- BASE+A+B is **never run** — the two are tested as mutually exclusive configuration choices, never combined.
- No interaction/synergy term is computed anywhere in the text (couldn't be, since the +A+B cell doesn't exist).
- The transplant itself is a genuine ambiguity, not confirmed either way: Appendix C states official baseline implementations are integrated as **git submodules** "so results can be reproduced against upstream code without modification" — confirmed for PlugMem/LightMem run as standalone baseline rows in their comparison table — but whether AutoMEM's *own* graph-index-building code calls into those same submodules, versus reimplementing the schema itself, is not explicitly stated in the text obtained.
- Routing: fixed at configuration time, not a per-query decision. The one router discussed is future work and is a **cost-tier** router (route steps to a cheap vs. strong backbone), not a mechanism-selection router.
- No public code repository found anywhere in the paper (checked every link on the page).

**Consequence: AutoMEM does more of the "isolated Δ per independently-sourced mechanism" step than AAMR previously credited it for, but still stops before `+A+B` and before any interaction computation, and its transplant provenance (submodule reuse vs. reimplementation) is itself unresolved.**

### Memory in the LLM Era — the most important finding of this search

arXiv:2604.01707. Decomposes 12 named prior systems (A-MEM, MemoryBank, MemGPT, Mem0, Mem0g, MemoChat, Zep, MemTree, MemoryOS, MemOS, MemGAS, LightMem) into a shared 4-stage framework, then builds a method combining the "multi-granularity tree organization of MemTree and MemOS" with the "hierarchical memory storage of MemoryOS" plus a novel segment-level-processing (SP) step. Its own Table 8 ablation, as extracted:

| Configuration | Score |
|---|---|
| Full method (Tree + SP) | 43.40 |
| w/o Tree (SP only) | 39.01 |
| w/o SP (Tree only) | 41.15 |
| w/o Tree & SP (≈ MemoryOS baseline) | 37.36 |

Read as a factorial grid — `BASE` = 37.36, `BASE+Tree` = 41.15, `BASE+SP` = 39.01, `BASE+Tree+SP` = 43.40 — a naive additive prediction (37.36 + 3.79 + 1.65 = 42.80) undershoots the actual combined score (43.40) by 0.60, i.e. **latent mild positive synergy**. The paper never frames, names, or computes this — it reports four numbers in an ablation table for a different purpose, and the interaction reading is only visible if a reader does the arithmetic. Public code is confirmed: `github.com/Yanchen398/Memory-in-the-LLM-Era` (a PVLDB Artifact Availability statement points to it), so the raw runs behind this table are, in principle, independently checkable.

Two things keep this from being a direct hit on AAMR's claim rather than a weakening of it: `BASE` here is **one of the donor systems itself** (MemoryOS), not a neutral common harness unaffiliated with either transplanted component — which is a real difference from AAMR's "common baseline" framing — and there is no router anywhere in this paper. But the raw material for exactly the interaction computation AAMR describes as unpublished already exists, publicly, with code. **AAMR should read this paper's Section 8.2 and repository directly before finalizing any claim that no one has published data sufficient to compute a cross-system interaction term.**

### GRAVITY — a second precedent for "one mechanism, many hosts, per-host comparison"

arXiv:2605.01688 (May 3, 2026, predates A-TMA). Injects structured entity/topic anchoring into the prompts of **five independent, pre-existing host memory systems** — Zep, Mem0, A-Mem, LiCoMemory, LightMem — "without requiring any architectural modifications to the host model," and reports a genuine per-host without→with table (verified verbatim, e.g. Mem0: 52.6→64.0 / 51.7→64.0 / 51.0→59.1 across three metrics; LightMem: 68.8→72.6 / 67.1→70.9 / 70.1→75.8). The mechanism itself is structural, not temporal/state-aware, so it doesn't answer the A-TMA-specific question this search also ran (see below) — but it is real, verified, independent confirmation that the "wrap a mechanism around several independent hosts, measure each host's own before/after" methodology shape has precedent beyond A-TMA alone.

One incidental caution surfaced while re-reading A-TMA's own table during this pass: automated extraction of its Table 2 showed explicit `+A-TMA` rows for only 3 of its 9 listed hosts (A-Mem, Graphiti/Zep, InsideOut), with the other 6 appearing as base-only rows. This may be an artifact of automated HTML extraction rather than a real gap in the paper — it is **not** asserted as a finding, only flagged for the AAMR team to eyeball directly given how much weight the earlier positioning report placed on A-TMA's "9 hosts" framing.

### The OpenReview paper — resolved

Track B reached, via ICLR's own first-party conference infrastructure (`iclr.cc` paper-detail page, cross-corroborated by the workshop's own Google Sites schedule and by Google Scholar's index — three independent fetches, consistent overlapping text, OpenReview.net itself never directly reachable across eight total attempts in two sessions), a real abstract: **PRIMARY-EQUIVALENT**.

- Title: "Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift."
- Authors: Zhaoxiang Feng, Mingyang Yao, David (Scott) Lewis.
- Venue: ICLR 2026 Workshop on Memory for LLM-Based Agentic Systems ("MemAgents"), Poster Session 1, April 27, 2026 — a workshop poster, not a peer-reviewed main-track paper.
- Content, quoted: "a memory transplant protocol that disentangles architecture from content by independently varying each across a code-to-math domain shift (LiveCodeBench to MATH)," a 2×2 factorial design, five memory systems, "architecture transfer is system-dependent with no universal direction."

**Resolution of the interpretation question: this is Interpretation A — domain transfer of one memory system's own architecture and content across a task-domain shift — not Interpretation B, cross-system mechanism grafting.** "Architecture" and "content" both belong to a single system in this paper's own definitions; the five memory systems are tested independently of each other to check whether the domain-transfer finding generalizes, not combined or ported into one another. This is **not a direct threat** to AAMR's cross-system-transplant claim, despite sharing the word "transplant." It should be cited in AAMR's own writing specifically to preempt the obvious reviewer confusion between the two meanings of "memory transplant," not as competing prior art.

## Factorial interaction prior art

Beyond Memory-in-the-LLM-Era and AutoMEM above, no other paper found runs a genuine multi-condition factorial grid on independently-sourced memory mechanisms. Confirmed near-misses, all checked against primary source and found to fall short on the "factorial" axis specifically:

- **"Human-Inspired Memory Architecture"** (2605.08538) — 9 configurations on LongMemEval, but **nested/stacked** (progressive addition: dedup-only → dedup+reconsolidation → ...), not factorial; all six mechanisms are self-designed by one author group, not transplanted from named external systems.
- **"Dissecting Agentic RAG"** (2606.21553, Jun 19 2026) — 8 conditions, **one-factor-at-a-time**, not a combination grid; components are individually sourced from distinct published techniques (closer on the sourcing axis) but never combined pairwise. Contains an untrained heuristic router that the paper itself reports **underperformed** a fixed strategy — a useful negative data point.
- **"Harness the Memory"** (2608.15008) — confirmed by direct quote: **"No factorial ablation is conducted."** Ablations are univariate (top-k sweep, context-length stress test) across 11 substrates reimplemented as "canonical versions," not literal transplants of named-system code.

## Router-after-validation prior art

No Type-D router (selecting between independently-sourced mechanisms, each separately validated before the router existed) was found anywhere across all five tracks. Every router-bearing paper found classifies as Type B (structures within one designed architecture) or Type C (operations within one backend):

| Paper | arXiv ID | Type | Trained how |
|---|---|---|---|
| **FluxMem** | 2602.14038 | **B** | **Exact methodological match to AAMR's sequencing**: each of 3 self-designed structures independently scored per training interaction, highest-reward one becomes the label, selector trained offline by supervised classification on those labels — "validate independently, then train router on regime labels," just not cross-system. |
| MemRouter | 2605.00356 | C | Supervised classification on ground-truth admission labels. |
| MemPrism | 2608.06745 (Aug 7, 2026) | B/C | KL-distillation + GRPO, end-to-end. |
| ShardMemo | 2601.21545 | C | Direct evidence-to-shard supervision. |
| MemCon | 2607.13591 | C | Online bandit, trained task-by-task. |
| RIZZ | 2606.20638 | B/C | Continuous/integrated, not sequentially validated. |

**FluxMem is the closest methodology match found for "validate independently, then train a router on the resulting regime labels" — but it routes between structures one paper's authors designed themselves, never between mechanisms extracted from separate, independently-built systems.** This is the sharpest available distinction for AAMR to lean on: the *sequencing* (validate, then route) has precedent; the *sourcing* (mechanisms taken from different pre-existing, independently-authored systems) does not, anywhere found.

## Retrieve→expand / provenance prior art

Directly relevant to `arena-context-ablation-v1`, which this search predates by only hours and which the original positioning report did not cover at all.

- **TierMem** (2602.17913) — **the closest architectural neighbor found to AAMR's provenance-expansion arm.** Built on Mem0 as its underlying store. Tier-1 fast summary (default) → Tier-2 immutable raw-log (escalation target), with an explicit, non-guessed provenance pointer (`raw_log_id ← page_id`, conceptually identical to AAMR's session-ID/timestamp mapping). Its escalation trigger is a **learned, RL-trained ("runtime sufficiency router," SFT-from-GPT-5-teacher then GRPO) sufficiency classifier** — a materially heavier mechanism than AAMR's current top-1/supplementary design. Confirmed cost/accuracy figures on LoCoMo: summary-only 0.755 acc/260 tok; raw-only 0.873 acc/7398 tok; TierMem-routed 0.851 acc/3981 tok (54.1% token reduction, 60.7% latency reduction vs. always-raw); Mem0 itself scores 0.684 (LoCoMo)/0.596 (LongMemEval) as a separate baseline row. **Critically, the paper never asks why raw-only (0.873) still beats its own smart router (0.851), and never disentangles volume from detail as competing explanations — that specific diagnostic question is the one thing AAMR's `arena-context-ablation-v1` asks that TierMem does not.**
- **Eywa** (2605.30771) — compact retrieval → conditional raw-episode rescue, trigger is an explicit **fixed rule table keyed on question type**, not learned — closer in spirit to a simple heuristic AAMR might use. Explicit provenance pointer, though the fetched text left some ambiguity about whether the "rescue" step purely dereferences a pointer or blends in an independent full-text search. The paper's own Limitations section admits it runs no cost/accuracy ablation and makes no controlled Mem0 comparison.
- **Zep** (2501.13956) — a useful negative case: maintains bidirectional fact↔episode provenance but **never feeds raw episode text back to the answering model**, and the authors state outright that this connection "is not directly examined in this paper's experiments." A major, well-cited production system has the ingredient and has explicitly not run AAMR's experiment.
- Parent-Document/"small-to-big" retrieval and Auto-Merging Retriever (LangChain/LlamaIndex) — the right architectural *shape*, but these are industry documentation patterns, not peer-reviewed papers, and their expansion is typically unconditional once a match threshold is hit rather than adaptively triggered.

**AAMR's design differs from both close neighbors in a specific, statable way: explicit provenance pointer (like both), applied to the top-1 hit specifically (like neither exactly), and — most importantly — used as a diagnostic instrument to separate volume from detail rather than as a production escalation mechanism (unlike both). That framing, not the mechanism's bare existence, is where the remaining claim to distinctiveness has to sit.**

**Note added after this search completed:** `arena-context-ablation-v1` finished (a separate process, not this search) while this report was being written; its result is now on disk at `docs/research/CONTEXT_AND_PROVENANCE_ABLATION_V1.md`. It found exactly the diagnostic answer this section says was still open: raw-provenance fallback repairs zero of Mem0's nine observable failures (`COMPACT_WRONG_RAW_FIXES: 0`, `RAW_CAUSES_REGRESSION: 0`) — H3 refuted — while a pure context-breadth curve on Hindsight is monotone and causal (4/10 at Mem0's own budget, up to 7/10 at full breadth). This does not change the prior-art picture above (TierMem/Eywa/Zep remain the right citations for the *mechanism shape*), but it does mean the open diagnostic question this section flagged has already been answered on AAMR's own data, and the write-up at `CONTEXT_AND_PROVENANCE_ABLATION_V1.md` does not currently cite TierMem, Eywa, or Zep at all. One more thing worth flagging for AAMR's own attention: TierMem's raw-only condition (0.873) *beats* its own learned router (0.851) — raw wins there — while AAMR's Mem0-raw-only (3/9) is *worse* than Mem0-compact (4/9) — compaction wins here. That is a real tension with the general "raw beats extraction" pattern this search found elsewhere (Verbatim Chunks, Diagnosing Retrieval vs. Utilization Bottlenecks) and is worth AAMR investigating directly rather than assuming the literature's general finding transfers to its own pipeline — it may be genuinely boundary-dependent (what "compact" throws away differs by system), not a contradiction to explain away.

## Context sufficiency prior art

- **"Verbatim Chunks Beat Extracted Artifacts"** (2601.00821, already known to AAMR) — a new detail found this pass matters directly to `arena-context-ablation-v1`: the paper explicitly tests a hybrid condition and reports, quoted, that **"adding artifacts alongside chunks preserves accuracy; substituting them forfeits the gap."** That is close to identical in spirit to AAMR's own `mem0_compact_plus_raw` arm. AAMR's experiment is not the first test of "compact + raw beats compact alone" — it is closer to an independent replication of an already-published result, in a different but adjacent setting (this project's own retrieval pipeline and probe set, rather than 2601.00821's storage-representation ablation).
- **"Diagnosing Retrieval vs. Utilization Bottlenecks"** (2603.02473) — 3×3 design naming Mem0 explicitly; confirms accuracy varies far more with retrieval method (20 points) than with write strategy (3–8 points), and that raw chunked storage matches or beats Mem0-style extraction.
- **"Mem0 vs. long-context LLM inference"** (2603.04814) — an independent, Mem0-specific, LongMemEval/LoCoMo-based finding that long-context inference beats a Mem0-based memory system on two of three benchmarks — the same flavor of finding as AAMR's own Mem0-vs-Hindsight result, with a different "broad" arm (long-context LLM rather than Hindsight).
- **"The Power of Noise"** (2401.14887, SIGIR 2024) — general RAG: irrelevant documents added to context can improve accuracy up to 35%; the retriever's own top-ranked-but-irrelevant hits actively hurt. Strongest general (non-agent-memory) precedent for "broad/noisy beats narrow/precise."
- **"Sufficient Context"** (2411.06037, Google Research) — large models answer confidently instead of abstaining when context is insufficient; directly relevant background for why Mem0 having gold at rank 1 does not guarantee a correct answer.
- The vendor "94.6 vs. 49.0" Hindsight-vs-Mem0 claim, investigated and found unsupported (see above) — **the practical upshot is that no rigorous, independent, peer-reviewed head-to-head Mem0-vs-Hindsight study exists anywhere found in this search. AAMR's own internal comparison is more novel than the original positioning report assumed, not less, on this specific pairing — even though the general "narrow-precise-loses-to-broad-imprecise" pattern is now well precedented elsewhere.**

## Top 10 threats

| # | Paper | Exact overlap | What it already takes from us | What it does NOT do | Threat level |
|---|---|---|---|---|---|
| 1 | Memory in the LLM Era (2604.01707) | Cross-system component combination with an ablation table containing full-grid-equivalent data, public code | The raw numerical material for exactly the interaction computation AAMR says is unpublished | Frame/compute the interaction term itself; use a neutral (non-donor) BASE; build a router | **HIGH** |
| 2 | AutoMEM / Cross-Scenario Generality (2606.04315) | Isolated BASE+A and BASE+B on independently-sourced graph-index mechanisms under one harness | Clean single-mechanism deltas against a real, named, non-donor BASE (DCI-Lite) | Run BASE+A+B; compute interaction; build a mechanism router; release code | **HIGH** |
| 3 | TierMem (2602.17913) | Provenance-pointer-based conditional expansion to raw source, built directly on Mem0 | The core architecture AAMR's `arena-context-ablation-v1` provenance arm resembles, plus real cost/accuracy figures | Ask whether its own raw-beats-routed gap is volume or detail; use AAMR's simpler top-1/diagnostic framing | **HIGH** (for the context-ablation experiment specifically) |
| 4 | Harness the Memory (2608.15008) | "No substrate dominates, routing motivated," from an active multi-paper author cluster | The regime-characterization premise, publicly and confirmedly (quote: "No factorial ablation is conducted") | Transplant named mechanisms across systems; run any interaction grid; build any router | **MEDIUM** |
| 5 | Verbatim Chunks Beat Extracted Artifacts (2601.00821) | Hybrid compact+raw arm explicitly shown to preserve accuracy vs. compact alone | Prior, independent confirmation of AAMR's own `mem0_compact_plus_raw` hypothesis, in an adjacent setting | Run it as a conditional/triggered retrieval-time mechanism, or on Mem0/Hindsight specifically | **MEDIUM** |
| 6 | GRAVITY (2605.01688) | Mechanism transplanted across 5 independent hosts with verified per-host before/after numbers | A second, verified precedent (beyond A-TMA) for the "transplant + per-host comparison" methodology shape | Use a temporal/state-aware mechanism; run any factorial or interaction analysis | **MEDIUM** |
| 7 | Eywa (2605.30771) | Fixed-rule conditional raw-episode rescue with explicit provenance pointer | A simpler, rule-based alternative design point to TierMem's learned router | Run any cost/accuracy ablation (the paper's own admitted gap); compare against Mem0/Hindsight | **MEDIUM** |
| 8 | FluxMem (2602.14038) | Exact "validate independently, then train router on regime labels" sequencing | The training *methodology* AAMR's eventual controller would need, already demonstrated | Source what it routes between from independently-built external systems (Type D) | **MEDIUM** |
| 9 | Diagnosing Retrieval vs. Utilization Bottlenecks (2603.02473) | Mem0-named 3×3 write-strategy × retrieval-method design confirming raw ≥ extraction | An independent, controlled generalization of "Mem0-style extraction underperforms raw" | Test Mem0 against a broad system like Hindsight; test conditional expansion | **LOW–MEDIUM** |
| 10 | Mem0 vs. long-context LLM inference (2603.04814) | Independent Mem0-vs-broad-context finding on LongMemEval/LoCoMo | A second data point for "Mem0 loses to a broader alternative," with a different broad arm | Use Hindsight or any memory system as the broad arm; examine rank-1-yet-wrong cases | **LOW–MEDIUM** |

## Claim falsification table

| Claim | Verdict | Best counterexample / basis |
|---|---|---|
| **1.** No published work runs a full `BASE`/`+A`/`+B`/`+A+B` interaction grid with A and B from independently-built systems. | **WEAKENED** | Memory-in-the-LLM-Era's Table 8 contains the full four-cell data (arithmetically), with public code — but never frames or computes it as an interaction, and its BASE is itself one of the two donor systems (MemoryOS), not a neutral harness. AutoMEM independently weakens this further (clean isolated BASE+A, BASE+B) without fully falsifying it, since neither paper reaches BASE+A+B with a genuinely neutral baseline. |
| **2.** No published work learns a router only after transplanted mechanisms have independently demonstrated positive Δ. | **SURVIVES** (narrow but real margin) | FluxMem runs the exact validate-then-train-router sequence, but only over self-designed structures (Type B), never over mechanisms sourced from independently-built external systems (Type D). No Type-D router-after-validation paper found anywhere across ~113 queries. |
| **3.** No published work combines cross-system transplant + interaction/synergy measurement + router-after-validation, all three together. | **SURVIVES** | Direct consequence of Claim 2 surviving: since no paper does the router-after-validation-of-transplanted-mechanisms step at all, the full conjunction cannot be satisfied by anything found, regardless of how far individual pieces (1) have been weakened elsewhere. |
| **4.** A selective retrieve→provenance-expand mechanism may still be a useful, distinct mechanism candidate. | **WEAKENED, then separately settled by AAMR's own data** | On the prior-art axis: TierMem is architecturally very close (Mem0-based, provenance-pointer-linked, conditional escalation) and Eywa is a second, simpler-design neighbor, so the claim cannot rest on the mechanism's bare novelty — only on the diagnostic *framing*. On the empirical axis, independent of any of this search's findings: `arena-context-ablation-v1` (completed by a separate process while this search ran) already tested it directly and found `RAW_PROVENANCE_EXPANSION` repairs zero of nine observable failures — the project's own data now says drop this specific candidate regardless of what the literature does or doesn't already contain. |

## What remains plausibly open

- The specific **diagnostic framing** — disentangling context volume from provenance/detail preservation as competing explanations for a broad-imprecise system beating a narrow-precise one that already has gold ranked first — was not found addressed by TierMem, Eywa, or any other retrieve-then-expand paper surfaced.
- The **conjunctive** transplant → interaction-grid → router-after-validation pipeline, taken as a whole with mechanisms sourced from independently-built systems, remains unmatched everywhere searched (Claims 2 and 3 above).
- A genuinely neutral-baseline (non-donor-system) `BASE+A+B` interaction measurement between two independently-built systems' mechanisms — Memory-in-the-LLM-Era comes close but uses a donor system as its own baseline; no better candidate found.
- No rigorous independent Mem0-vs-Hindsight comparison exists in the literature; AAMR's own internal one is more novel on that specific pairing than previously assumed.

## What is definitely no longer claimable

- That AutoMEM's transplant evidence is "limited" in the way the original positioning report described — it is more complete (isolated BASE+A, BASE+B) than previously credited, even though it still lacks BASE+A+B and any interaction computation.
- That the OpenReview "Memory Transplants" paper is an unresolved threat — it is now confirmed (PRIMARY-EQUIVALENT) to be a within-system domain-transfer study, not cross-system mechanism grafting, and is low threat.
- That "no one has published data sufficient to compute a memory-mechanism interaction term" in any absolute sense — Memory-in-the-LLM-Era's own ablation table already contains that data, uncomputed and unframed, but present and reproducible from public code.
- That AAMR's provenance-expansion mechanism (for `arena-context-ablation-v1`) is architecturally unprecedented — TierMem is a close, published, Mem0-based neighbor and must be cited.
- That the public "Hindsight 94.6% vs. Mem0 49.0%" figure is safe to cite as external corroboration of anything — it is vendor content resting on a miscited source.

## Recommended wording changes

1. In the AutoMEM discussion, replace "limited ablation (single-pass vs multi-step...)" with an accurate description: isolated `BASE+A`/`BASE+B` are cleanly measured; `BASE+A+B` and any interaction term are absent; transplant provenance (submodule reuse vs. reimplementation) is itself unconfirmed from the paper's text.
2. Add "Memory in the LLM Era" (2604.01707) to the prior-art matrix and detailed comparisons as the top threat to Claim 1, with the explicit caveat about its donor-system BASE.
3. Update the OpenReview paper's status from "UNVERIFIED, flagged as the biggest unresolved risk" to "PRIMARY-EQUIVALENT verified, low threat, cite defensively to preempt reviewer confusion about the two meanings of 'memory transplant.'"
4. `arena-context-ablation-v1` finished and was written up (`CONTEXT_AND_PROVENANCE_ABLATION_V1.md`) while this search was running, and its own text does not yet cite TierMem, Eywa, or Zep. Add them there directly — the experiment's own real result (raw-provenance fallback: zero repairs, refuted) is now the stronger reason to drop that mechanism, but the write-up still owes readers the prior-art context for why the mechanism was worth testing in the first place, and TierMem's opposite-direction finding (its raw-only condition *beats* its own learned router) deserves an explicit note given how directly it seems to conflict with AAMR's own raw-only-underperforms-compact result.
5. Strengthen, rather than weaken, the citation of "Verbatim Chunks Beat Extracted Artifacts" for the provenance-expansion experiment specifically — its hybrid-arm finding is close to a prior, independent replication of AAMR's own hypothesis for that experiment.
6. Do not cite the vendor "94.6 vs 49.0" Hindsight number anywhere, including informally; note instead that no independent Mem0-vs-Hindsight study exists, which is itself a small positive point for AAMR's own comparison's novelty.
7. Sharpen the controller-side differentiator from "we route between mechanisms, they route between operations/structures" (already stated) to the more specific and now better-evidenced claim: "the *validate-then-route* training sequence is precedented (FluxMem); what is not precedented anywhere found is applying that sequence to mechanisms *sourced from independently-built, separately-authored systems* rather than structures designed by one paper's own authors."

## Sources

All accessed 2026-08-24 unless noted.

- "Memory in the LLM Era: Modular Architectures and Strategies in a Unified Framework" — arXiv:2604.01707 (Apr 2, rev. Aug 6, 2026). Code: `github.com/Yanchen398/Memory-in-the-LLM-Era`. PRIMARY VERIFIED (abstract + Table 8 extraction).
- "Exploring Cross-Scenario Generality of Agentic Memory Systems" — arXiv:2606.04315. PRIMARY VERIFIED, full text including Appendix C and Limitations, in-page keyword search performed.
- "GRAVITY: Architecture-Agnostic Structured Anchoring for Long-Horizon Conversational Memory" — arXiv:2605.01688 (May 3, 2026). PRIMARY VERIFIED (full HTML, Table 1).
- "TierMem: From Lossy to Verified: A Provenance-Aware Tiered Memory for Agents" — arXiv:2602.17913 (Feb 20, 2026). PRIMARY VERIFIED.
- "Eywa: Provenance-Grounded Long-Term Memory for AI Agents" — arXiv:2605.30771 (May 29, 2026). PRIMARY VERIFIED.
- "Diagnosing Retrieval vs. Utilization Bottlenecks in LLM Agent Memory" — arXiv:2603.02473 (Mar 2, 2026). PRIMARY VERIFIED.
- "Mem0 vs. long-context LLM inference" — arXiv:2603.04814 (Mar 5, 2026). PRIMARY VERIFIED (abstract).
- "Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift" — OpenReview `AIJsjIqfsp`, ICLR 2026 MemAgents Workshop. PRIMARY-EQUIVALENT (iclr.cc first-party page, cross-corroborated by workshop site and Google Scholar; OpenReview.net itself unreachable, 8 attempts across 2 sessions).
- "Harness the Memory" — arXiv:2608.15008. PRIMARY VERIFIED, re-confirmed with direct quote "No factorial ablation is conducted."
- "Human-Inspired Memory Architecture for LLM Agents" — arXiv:2605.08538. PRIMARY VERIFIED (ablation structure re-checked: nested, not factorial).
- "Dissecting Agentic RAG: A Component Ablation for Multi-Hop QA with a Local 7B Model" — arXiv:2606.21553 (Jun 19, 2026). PRIMARY VERIFIED.
- "FluxMem" ("Choosing How to Remember...") — arXiv:2602.14038. PRIMARY VERIFIED (training methodology re-confirmed).
- "Verbatim Chunks Beat Extracted Artifacts" — arXiv:2601.00821 (v4 Jul 22, 2026). PRIMARY VERIFIED, hybrid-arm detail newly extracted.
- "The Power of Noise: Redefining Retrieval for RAG Systems" — arXiv:2401.14887 (SIGIR 2024). PRIMARY VERIFIED.
- "Sufficient Context: A New Lens on Retrieval Augmented Generation Systems" — arXiv:2411.06037 (Nov 2024, Google Research). PRIMARY VERIFIED.
- Zep — "A Temporal Knowledge Graph Architecture for Agent Memory" — arXiv:2501.13956 (Jan 2025). PRIMARY VERIFIED.
- vectorize.io Hindsight-vs-Mem0 marketing comparison — investigated and found to miscite arXiv:2603.04814, which does not mention Hindsight. UNVERIFIED as a valid comparison; not to be cited by AAMR.
- Ruled-out temporal/multi-host candidates (all PRIMARY VERIFIED as not matching the multi-host-overlay shape): TOKI (2606.06240), MemTxn (2607.27834), TGMS (2607.10265), MemTX (2607.23929), Governed Persistent Memory (2608.12476), "From Faulty Memories to Corrected Actions" (2608.10502), StateAuditor (2608.01619).
- Secondary leads not independently deep-verified, flagged for possible AAMR follow-up only: "Does Memory Credit Travel? Paired Factorial Audits of LLM-Agent Memory" (Rocchi, SSRN, ~Jul 2026 — blocked, UNVERIFIED), MemFactory (2603.29493), M★ (2604.11811/2605), HyperMem (2604.08256), WhenLoss (2605.24579), StateMemBench (2608.19652), TEPA (2608.07429), AgentMemBench (2608.00009), "When Memory Becomes Authority" (2608.01679), "Survey of Agent Memory in the Second Half" (2602.06052, updated Aug 4, 2026).

---

## Red-team update — 2026-08-24

Appended to `RELATED_WORK_AND_POSITIONING_2026-08-24.md` without altering its original text; full detail in this document.

- **SUPERSEDED BY NEW PRIOR ART / CORRECTED VERIFICATION**: the original report's characterization of AutoMEM's ablation as "limited" undersold it — isolated `BASE+A` and `BASE+B` are cleanly measured there. It still lacks `BASE+A+B` and any interaction term, so the core gap claim is not overturned, only the supporting description of AutoMEM.
- **SUPERSEDED BY NEW PRIOR ART**: "Memory in the LLM Era" (arXiv:2604.01707), not in the original report at all, now the top threat to the interaction-grid piece of AAMR's novelty claim — its ablation table contains data arithmetically equivalent to a full four-cell grid, uncomputed as an interaction by its own authors, with public code.
- **RESOLVED, NOT SUPERSEDED**: the OpenReview "Memory Transplants" paper, previously flagged UNVERIFIED and treated as the single biggest open risk, is now PRIMARY-EQUIVALENT confirmed as a within-system domain-transfer study (Interpretation A) — low threat.
- **NEW SCOPE, NOT COVERED BEFORE**: `arena-context-ablation-v1`'s provenance-expansion mechanism has close published neighbors (TierMem, Eywa, Zep) that the original report — written before that experiment existed — could not have addressed.
- **NET EFFECT ON THE GO/PIVOT/STOP CALL**: unchanged at GO. Claims 2 and 3 (router-after-validation of cross-system-sourced mechanisms; the full three-part conjunction) survive this adversarial pass intact. Claim 1 (the bare interaction-grid step) and Claim 4 (the provenance-expansion mechanism's novelty) are both weakened and now require explicit differentiation from named prior art in any future writeup, not just a background citation.
