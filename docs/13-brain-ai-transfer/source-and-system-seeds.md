# Brain-to-AI source and system seeds

Status: screened seed map; individual claims still require full-text extraction

## Use rule

This file is a routing map, not a bibliography that confers evidence by citation count. Prefer primary experiments, official proceedings, and inspectable repositories. Record exact claims and limitations in the evidence ledger after full reading.

## Biological and computational anchors

| Mechanism family | Starting source | What to extract |
| --- | --- | --- |
| Working memory | Baddeley, 2003, `10.1038/nrn1201` | components, capacity claims, and boundaries; avoid equating the model with a token window |
| Episodic/semantic systems | McClelland, McNaughton, O'Reilly, 1995, `10.1037/0033-295X.102.3.419` | fast/slow learning, interleaving, catastrophic interference |
| Systems consolidation | Frankland and Bontempi, 2005, `10.1038/nrn1607` | time, transformation, and dependence claims |
| Replay | prioritized and generative replay literature plus primary neural replay studies | selection rule, representation replayed, causal manipulation, negative transfer |
| Pattern separation/completion | Yassa and Stark, 2011, `10.1016/j.tins.2011.06.006` | discrimination/completion tradeoff and task definitions |
| Encoding specificity | Tulving and Thomson, 1973, `10.1037/h0020071` | cue/trace compatibility; distinguish from semantic similarity |
| Source monitoring | Johnson, Hashtroudi, Lindsay, 1993, `10.1037/0033-2909.114.1.3` | origin judgments, characteristic errors, confidence limits |
| Reality monitoring | Johnson and Raye, 1981, `10.1037/0033-295X.88.1.67` | external versus internally generated discrimination |
| Reconsolidation | Nader, Schafe, LeDoux, 2000, `10.1038/35021052` | reactivation boundary conditions; do not universalize destabilization |
| Retrieval-induced forgetting | Anderson, Bjork, Bjork, 1994, `10.1037/0278-7393.20.5.1063` | practiced, related-unpracticed, and unrelated contrasts |
| Prospective memory | event- and time-based prospective-memory literature | trigger recognition, intention execution, cancellation, monitoring cost |
| Metamemory | Nelson and Narens, 1990 and selective-prediction literature | monitoring versus control; calibration and abstention |
| Emotional modulation | McGaugh, 2004, `10.1146/annurev.neuro.27.070203.144157` | phase, arousal, timing, selectivity, and collateral effects |
| Synaptic tagging/novelty | Moncada and Viola, 2007, `10.1523/JNEUROSCI.1083-07.2007` | eligibility window and later promotion; no literal molecular transfer |
| Goal/habit control | outcome-devaluation and model-based/model-free literature | arbitration, stress interactions, null and contradictory results |
| Multiple timescales | Fusi, Drew, Abbott, 2005, `10.1016/j.neuron.2005.02.001` | retention/capacity tradeoff and cascade assumptions |

## Current AI maps and surveys

| Source | Contribution | Boundary |
| --- | --- | --- |
| [Memory in the Age of AI Agents](https://arxiv.org/abs/2512.13564) | broad agent-memory taxonomy and lifecycle map | survey; classifications are not comparative causal evidence |
| [AI Meets Brain](https://arxiv.org/abs/2512.23343) | explicit cognitive-neuroscience to autonomous-agent bridge | recent preprint; each claimed bridge needs primary verification |
| [From Storage to Experience](https://aclanthology.org/2026.findings-acl.2069/) | storage, reflection, and experience-oriented evolution map | qualitative survey; reports weak unified comparison infrastructure |
| [When Continual Learning Moves to Memory](https://arxiv.org/abs/2604.27003) | reframes external-memory stability/plasticity and negative transfer | recent preprint; reproduce task and representation effects before promotion |

## Systems and methods worth inspecting

| Candidate | Mechanism relevance | Local status | Audit question |
| --- | --- | --- | --- |
| [HippoRAG](https://github.com/osu-nlp-group/hipporag) | graph retrieval inspired by hippocampal indexing and consolidation language | already pinned locally | what gain comes from graph/PPR operations rather than the biological framing? |
| [MemGPT/Letta](https://github.com/letta-ai/letta) | bounded working context and tiered external memory | catalogued | which paging policies are model-neutral and benchmarked? |
| [Memory-R1](https://arxiv.org/abs/2508.19828) | learned add/update/delete/no-op and memory distillation | paper lead | does association-based reward predict causal future usefulness and harm? |
| [MIRIX](https://arxiv.org/abs/2507.07957) | multiple typed stores including episodic, semantic, procedural, and resource memory | paper lead | are types operationally distinct, ablated, and portable across providers? |
| [MemCon](https://github.com/ericjiang18/MemCon) | controlled retrieval, planning, consolidation, and forgetting actions | pinned locally; very recent; README says MIT but no root license file | can the controller beat frozen rules under distribution shift and equal budget? |
| [ICAL](https://proceedings.neurips.cc/paper_files/paper/2024/hash/8ac50fd0a4eeeb1f077b17bb7c5353c3-Abstract-Conference.html) | multimodal abstracted experience and continual learning | paper lead | does abstraction improve first action and transfer without erasing exceptions? |
| [Reflexion](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) | verbal experience/reflection store | paper lead | does retained reflection transfer, or merely add test-specific hints? |
| [MemRL](https://github.com/MemTensor/MemRL) | reward-updated utility of intent/experience memories | catalogued for audit | delayed credit, bundle interference, propensity logging, and negative transfer |
| [Nemori](https://github.com/nemori-ai/nemori) | prediction-error memory distillation | catalogued for audit | distinguish novelty, surprise, consequence, and causal downstream value |

## Benchmark leads

| Benchmark | Coverage added | Known gap |
| --- | --- | --- |
| [LoCoMo-Plus](https://aclanthology.org/2026.acl-long.1150/) | harder long-conversation memory evaluation | still primarily explicit answer production |
| [ImplicitMemBench](https://aclanthology.org/2026.acl-long.1301/) | procedural memory, priming, and conditioning | synthetic/controlled scope; transfer to durable local memory remains open |
| LoCoMo and LongMemEval | longitudinal facts, updates, abstention, and temporal queries | limited first-action, source-monitoring, and maintenance-policy causality |
| AgentPoison | memory/RAG poisoning and trigger attacks | attack coverage is not a general integrity benchmark |
| project PMLAB corpora | local evidence sufficiency, interference, validity, retrieval, probes | constructed development evidence; not independent external validation |

## Repository acquisition decisions

1. Keep HippoRAG as the pinned graph/indexing comparator; do not clone another fork merely for a brain label.
2. Add the official evolving-memory survey repository as a discovery index, not evidence.
3. Add the LoCoMo-Plus repository as a benchmark lead, but audit data/license/version before download.
4. Do not clone unverified implementations for Memory-R1 or MIRIX. MemCon now has an author-linked repository pinned locally, but its missing root license file and unreplicated claims block reuse.
5. Do not add a heavy neuroscience simulator yet. None of the first portfolio tests requires reproducing tissue dynamics.

The first pinned-code findings and license blockers are recorded in [`repository-initial-audit-v0.md`](repository-initial-audit-v0.md).

## Search queue

- prospective-memory agent benchmarks with event-trigger cancellation and stale intentions;
- reality/source-monitoring benchmarks involving recursively generated summaries;
- pattern-separation metrics for entity, time, and episode false merges;
- schema induction with rare but consequential exceptions;
- replay ablations reporting negative transfer and contaminated-memory amplification;
- implicit/procedural tests scored before verbal explanation;
- multiple-timescale memory with reversible suppression and recovery;
- null results for learned memory controllers under policy or domain shift.
