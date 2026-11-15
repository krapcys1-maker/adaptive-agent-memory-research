# Research map: memory for agents that act

Compiled 13–15 November 2026 for the change of direction. The rule is the project's usual one: a claim that shaped a decision was checked in the full paper or in the code; anything read only as an abstract is a lead, not a basis.

Verification levels:
- **T**: full text read (method, setup, main tables, limitations);
- **K**: code read at a stated commit;
- **P**: counted or recomputed by us;
- **A**: abstract only.

Coverage is not complete; see the end of this page.

## A. Experience memory (the core of the new direction)

| Work | What it shows | Level | Caveats |
|---|---|---|---|
| AdaMEM, arXiv 2606.05684 (ICML 2026); code `yunx-z/AdaMEM`, Apache-2.0 | Retrieving successful steps **by the current state, every step**: ALFWorld seen 45.2 → 59.3% (Qwen3-4B, 3 runs); with strategy synthesis 65.5%; synthesis without memory 34.8% (worse than none) | T + K | one paper, one model; bank built from successes only; failures excluded |
| MemHarness, arXiv 2607.28272; code `KnowledgeXLab/MemHarness`, Apache-2.0 | Memory reconstructed before acting, trained with GRPO: ALFWorld 85.2% | T + K | without memory at test time 83.0%, so most of the gain is training; its per-memory "utility" is an observational success counter |
| Auto-Dreamer, arXiv 2605.20616 | Offline consolidation with provenance; with a pre-built fixed bank, ordinary methods jump about 40 points over their baseline, with a bank grown from empty they stay near it | T | point estimates without variance; no code found |
| ASSAY ("Not All Skills Help"), arXiv 2606.15390 | Per-skill effects measured by random masking; suppressing harmful skills per task; large AppWorld gains | T | frontier models; per-cell power 38.5% by the authors' own analysis |
| ACE, arXiv 2510.04618; code `ace-agent/ace` | Evolving playbook; in the code only ADD operations are applied | K | in ASSAY's table, ACE falls below the no-memory agent on AppWorld Test-C with GPT-5.1 |

## B. Harms and stability

| Work | What it shows | Level |
|---|---|---|
| "Useful Memories Become Faulty When Continuously Updated by LLMs", arXiv 2605.12978 | Repeated LLM consolidation degrades memory across seven frameworks; episodes carry the gain, abstractions alone fall to the no-memory level | T |
| TraceRetain, arXiv 2606.29178 | On clean ALFWorld with a strong model, memory policies are indistinguishable (ceiling); similar failed entries lower retrieval precision; memory shortens episodes by 37–55% | T |
| Causal Memory Policy, arXiv 2610.02070 | A memory's utility is identifiable only with randomised exposure; one score per memory does not transfer to new queries | T |
| arXiv 2604.27003 | Raw trajectories transfer negatively across different tasks; abstraction is safer | T (two runs per condition) |

## C. Simple baselines and critique

| Work | What it shows | Level |
|---|---|---|
| Raw-RAG, arXiv 2610.30755 | Plain dense retrieval over raw history ranks first in 6 of 7 settings against 12 memory systems (conversation QA) | T |
| Memory Tax, arXiv 2610.34073 | Many memory systems have negative net value against naive retrieval; the loss splits into faithfulness, accessibility and backbone dependence | T |
| Cross-component interference, arXiv 2605.05716 | Enabling every component is always worse than the best subset; effects are not additive | T |
| "Memory in the LLM Era", arXiv 2604.01707 | A method composed from 12 systems' modules ties Zep on LoCoMo; keeping raw messages is key | T |
| LoCoMo audit, `dial481/locomo-audit` | 99 of 1,540 gold answers wrong (6.4%) and a lenient judge | K + P (we recounted the error file and checked three cases against the conversations) |

**Why these simple baselines win, as far as is known.**
- *Raw retrieval:* the authors attribute it to higher evidence coverage, preserved relations, and irrecoverable losses when memory is transformed. These are the authors' analyses; we did not recompute them.
- *Interference:* that it exists is measured; *why* is mostly the authors' hypotheses (competition for context, conflicting instructions).

## D. Fact memory and graphs (side lines for this direction)

| System | What we checked | Level |
|---|---|---|
| Graphiti | deterministic invalidation of facts over time | K |
| Mem0 v3 | extraction is ADD-only | K |
| HippoRAG | personalised PageRank over a graph works | K |
| Synapse | the authors' own release reports that literal spreading activation does not rank better than vectors alone | K |

## Not yet read in full

ReMe, ExpGraph, the IBM trajectory-tips work, AWM, ExpeL, Memp, MemEvoBench, SeqMem-Eval, Evo-Memory, EvoMemBench (its repository has no licence), AMA-Bench, CMC. We did not find the full text of the NeurIPS 2026 paper "When Does Agent Memory Transfer?". Reading these is a good first contribution: one paper per pull request, with the level of verification stated.
