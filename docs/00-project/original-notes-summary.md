# Summary of the Original Project Notes

Status: reviewed

The original Polish notes propose a model-agnostic long-term memory layer for agents. Their strongest idea is a memory policy trained from the later usefulness of earlier experiences.

## Original conceptual components

- Working, episodic, semantic, procedural, decision, failure, and archive layers.
- A stable project memory separated from experimental memory.
- Append-only raw logs and hot/warm/cold/archive tiers.
- Hybrid retrieval using semantic similarity, BM25, recency, and importance.
- Synthetic or operational affect derived from failures, cost, surprise, rollback, novelty, and reward.
- Learned retention, priority, consolidation, and decay.
- Delayed supervision in which future reuse supplies labels.
- Weak supervision using deterministic rules and LLM classification.
- Public datasets including LongMemEval, LoCoMo, LongMemEval-V2, coding-agent traces, and BEAM.
- A staged comparison from manual rules through classical ML, small neural networks, and online learning.

## Research corrections required

- A context window is not biologically equivalent to working memory.
- Benchmark evidence labels do not make all unlabelled events useless.
- Retrieval frequency is not causal future utility.
- Human emotional memory findings do not imply machine emotion.
- Decision and failure memory are useful engineering record types, not standard biological memory systems.
- Consolidation must preserve raw evidence and transformation provenance.
- Benchmark claims require strict control of data versions, reader models, prompts, and judges.

The original files remain outside this English research repository as historical source material.
