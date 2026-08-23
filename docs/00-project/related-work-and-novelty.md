# Related work, and what this project can honestly claim

Status: **first pass, partially verified.** Written after an external prompt
pointed out that several 2026 systems occupy ground this project had been
treating as open. Two entries were verified against primary sources; the rest are
recorded as reported and are marked so.

The habit `CONTRIBUTING.md` requires applies to prior art as much as to code:
**claimed and verified are separate columns and never merged.**

---

## Verified against primary sources

### APEX-MEM — ACL 2026, Amazon

[arXiv 2604.14362](https://arxiv.org/abs/2604.14362) ·
[ACL anthology](https://aclanthology.org/2026.acl-long.749.pdf)

Structures conversation into **entity-property-value triplets** over a
domain-agnostic ontology, stores **append-only** so the full temporal evolution
survives, and resolves conflicting or evolving information **at query time**
through a multi-tool retrieval agent. 88.88% on LoCoMo QA, 86.2% on LongMemEval.

**This is the same architecture this project arrived at independently:**

```
raw text → entity → property → scope → canonical address → state chain → temporal resolution
```

The consequence is direct and unwelcome. *Entity-property addressing over an
append-only store with temporal resolution* **is not a novel contribution**, and
nothing in this repository may present it as one. It was published, with numbers,
before `PMLAB-H1-ADDR-E1` ran.

### Verbatim Chunks Beat Extracted Artifacts — 2026

[arXiv 2601.00821](https://arxiv.org/html/2601.00821)

A controlled ablation of memory representations. Extraction into structured
artifacts **loses** to verbatim chunks by 15.9 points on LoCoMo (43.9% vs 28.0%)
and 22.0 points on LongMemEval-S (67.4% vs 45.4%). The extracted-artifact
pipeline never beats naive RAG on overall accuracy. Across 3,121 missing
keywords the failure modes are **extraction gaps 78.8%**, temporal blindness
14.9%, reasoning-chain breaks 6.4%.

This is the most serious threat to the direction `PMLAB-H1-ADDR-E2` is taking,
and it should be read before that experiment continues rather than after.

**It also converges with what E2-A measured here.** The deterministic extractor
abstained on **85.7%** of probes — an extraction gap, arrived at independently,
in the same range as the 78.8% that paper reports as its dominant failure mode.
That convergence strengthens the finding and removes any claim to having
discovered it.

---

## Reported, not yet verified

Raised externally and recorded because a gap in prior-art coverage is worth
registering before it is closed. **None of the figures below has been checked
against a primary source**, and none may be cited in an evidence-ledger claim
until it is.

| Work | Reported overlap |
|---|---|
| A-TMA (2026) | "ghost memory": stale fact, current fact and the change notice coexisting. Records marked `current` / `historical` / `transition`; failures split across bank maintenance, retrieval, answer-time resolution. Reported +0.240 absolute conflict accuracy over Graphiti. |
| Graphiti / Zep | Raw episodes as provenance, entities and relations with validity windows, superseded facts retained rather than deleted, retrieval fusing semantic + BM25 + graph traversal. Already compared in `docs/04-systems/temporal-memory-model-comparison-v0.md`. |
| STALE / CUPMem | Later events invalidating earlier knowledge without an explicit correction; structured state consolidation and propagation-aware search. Reported best model 55.2% overall — the problem is not solved. |
| VISTA | Explicitly addressable memory blocks, archiving, token budgeting. |
| A-MAC | Future utility, factual confidence, semantic novelty, temporal recency; rules plus LLM judgement plus a learned admission policy. |
| NEMORI (ACL 2026) | "What deserves memory?" — future utility via predictability and prediction error. |

The last two matter for a different part of this project. **"Memory learns what
is worth remembering" and "future utility governs retention" are no longer
available as novelty claims**, and the research questions in `README.md` state
them as though they were open.

---

## What this project can still claim

Not *structured temporal memory works* — APEX-MEM demonstrated that with better
numbers than anything here.

What appears unoccupied is the **diagnostic programme**: not a system, a chain of
measurements answering *when and why similarity stops being the right access
mechanism*.

```
lexical vs dense                       0.881 vs 0.821
per-failure attribution                10 of 13 failures are F2, zero F3
opposite error profiles                RARE-EXC lexical-only 9, OBSOLETE dense-only 4
oracle router ceiling                  0.929 — bounds any router over those channels
near-clone analysis                    48 records matching one query shape
similarity saturation                  gold ranked 22–99, budget admits 17–22
oracle addressing                      245.5 → 68.8 tokens, stale 0.548 → 0.143
collision and fragmentation as metrics
preregistered automatic addressing     thresholds frozen before an extractor existed
DEV / VALID / commit-and-reveal SEALED
deterministic → small model → hybrid   extraction gap isolated to property, not entity
```

The falsifiable form:

> Similarity retrieval degrades when semantically homogeneous memories differ
> primarily by identity. Explicit addressable state can recover useful evidence
> more efficiently under a fixed context budget, and the failure of cheap
> extraction is localisable to a specific resolution step rather than to
> structure itself.

That last clause is where this diverges from *Verbatim Chunks*. That paper
concludes structure loses to raw text. This project has a measurement suggesting
**the structure was never the problem** — `E2-A` recovers entity on 0.571 of
questions and property on only 0.286, so the gap sits in one resolution step
rather than in the representation. If a narrow fix to property resolution
recovers most of the oracle advantage, that is a genuine refinement of a
published negative result. If it does not, *Verbatim Chunks* is right and this
project should say so.

---

## What follows

1. **APEX-MEM is the baseline**, not a neighbour. Any claim about addressing is
   measured against it or is not made.
2. The `README.md` research questions on future utility need a prior-art note.
   A-MAC and NEMORI occupy that ground.
3. The unverified table above needs primary-source checking before any of it
   enters the evidence ledger. Filed as an issue.
4. `PMLAB-H1-ADDR-E2` continues, with *Verbatim Chunks* registered as a stated
   risk to its premise rather than discovered halfway through.

## On finding this late

Selection rule 1 of the operating doctrine is *does the answer already exist?*
It was not applied to the architecture, only to individual mechanisms, and this
document exists because someone outside the project asked the question that the
doctrine already required. That is a process failure worth recording, and it is
recorded here rather than quietly fixed.
