# Zou et al. — Remember the Decision, Not the Description

- Status: full text read; extracted; first challenge pass complete; independent reproduction pending
- Version read: arXiv:2605.10870v1, 11 May 2026, 51 pages
- Source: https://arxiv.org/abs/2605.10870
- Cached file: `sources/papers/demem-2605.10870.pdf` (3,422,882 bytes)
- SHA-256: `BDC8D8AA326DDF6EB9E7F1D9EA109D4A20B00BA6E4307000D0D7518E53E86454`

## Research question

Under a fixed runtime memory budget, should an agent merge histories by descriptive similarity or preserve distinctions that change the best downstream decision?

## System, method, and comparisons

The paper formalizes query-conditioned routing of interaction histories into `K` runtime states as a contextual-bandit rate-distortion problem. DeMem splits a state when feedback certifies a decision conflict. It compares against full context, RAG, LangMem, Mem0, Zep, Nemori, EMem-G, Mnemis, ablations, and synthetic controls. Agent experiments use fixed answer backbones and two held-out LLM judges; the archive itself is not the constrained object.

## Extracted results

- LoCoMo descriptive similarity had weak correspondence to decision compatibility: Spearman `rho=0.103`, AUC `0.548`; under a matched answer-time budget, description retrieval exposed 66% of gold evidence and DeMem 83% (paper pp. 1–2).
- On LoCoMo, DeMem's overall score was `0.911±0.040` with GPT-4o-mini versus Mnemis `0.888±0.042`, and `0.920±0.038` with GPT-4.1-mini versus Mnemis `0.906±0.039` (Table 1, p. 8). Mnemis remained better on single-hop questions for both backbones (`0.938` vs `0.932`; `0.940` vs `0.935`).
- The evaluation used deterministic decoding and scores averaged across two LLM judges. A 150-instance human-agreement study reported `kappa=0.79` and 91.3% agreement (p. 8; Appendix E.14).
- Certified splitting fired on 4.6% of LoCoMo routing events with 85% precision against gold annotations; all reported ablations reduced performance. The theory-faithful DeMem-Core scored 90.8 overall (p. 9; Appendices D.10, E.6, E.11).
- With corrupted feedback probabilities 0, 0.1, and 0.2, overall scores were 91.1, 90.2, and 88.9; split precision declined from 85.0 to 80.8 and 77.6 (Table 18, p. 50).
- A Qwen2.5-14B experiment reported DeMem `0.490`, MemSkill `0.466`, and MemAct `0.450` overall, while MemSkill was higher on single-hop (`0.492` vs `0.487`; Table 19, p. 50).

## Limitations and challenge pass

- This is a very recent preprint with no independent reproduction found in this pass.
- The constrained resource is a runtime decision-state/answer context budget, not total disk storage. The results do not show that raw evidence should be deleted.
- LoCoMo and related answer scores depend substantially on LLM readers and judges; agreement checks reduce but do not remove judge bias.
- The formal guarantees assume a finite contextual-bandit setting and feedback structure unlike an open-ended personal agent.
- Pairwise conflict checks scale poorly; the authors identify candidate generation/approximation as future work (Appendix F, pp. 50–51).
- The "exact forgetting boundary" is conditional on the decision model and value distinctions being correct. Unknown future queries make irreversible forgetting unsafe.

## Project relevance

Treat decision-centric memory as a query-time routing hypothesis over a richer, reversible archive. The safe translation is not "forget descriptions" but "allocate scarce context to distinctions that alter an answer or action."

## Falsifiable hypothesis

Under the same retrieved-token budget, query-conditioned decision-conflict routing should reduce risk-weighted answer loss and critical misses versus lexical, embedding, and descriptive-salience retrieval. Reject promotion if it fails on frozen histories, if gains vanish with a fixed non-LLM scorer, or if latency/calls dominate the benefit.
