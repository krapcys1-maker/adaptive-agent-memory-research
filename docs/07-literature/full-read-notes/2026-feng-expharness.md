# Feng et al. — ExpHarness

- Status: full main text and implementation appendix read; extracted; independent reproduction not run
- Version read: arXiv:2605.30712v2, 2026
- Source: https://arxiv.org/abs/2605.30712
- Code: https://github.com/ulab-uiuc/ExpHarness at `9dd6b3f42ede70b85196a9041d295e61ee5af9b2`; Apache-2.0 read from `LICENSE`, no code execution
- Read artifact: 66 pages, 976615 bytes, SHA-256 `756e45fabfc4625ddf57b9b5fd734f4b131be0bafd822c2cb77dc0aa48a3adf6`

## Authors' claim and method

ExpHarness places learning in a replaceable harness rather than the frozen executor. An experience graph stores skills from successes and lessons from failures, and a lightweight retrieval copilot chooses graph diffusion depth and the semantic-versus-utility trade-off. Retrieval starts with semantic seeds, expands through personalized PageRank, then ranks candidates using historical utility and an upper-confidence term (Sections 3.1–3.4, pp. 3–6).

The reward is `(with-experience score - no-experience score) + η * with-experience score`. It updates both the copilot and graph utilities. Node utility is a historical shared-reward estimate for retrieval sets containing that node, not an isolated causal contribution of that node (Section 3.4, p. 6).

## Reported results

- Static, Table 2 (p. 6): with Llama-3.2-3B-Instruct, ExpHarness scored 69.57 weighted average versus 62.06 for MemRL, a 12.1% relative improvement reported by the authors. With Llama-3.1-8B-Instruct, it scored 78.76 versus 75.34 for MemRL, a 4.5% relative improvement.
- Agentic, Table 3 (p. 7): ExpHarness scored 53.4 versus 44.0 for S3 with Qwen3-32B and 62.3 versus 55.3 for S3 with Gemini-3.1-Flash-Lite, corresponding to the reported relative gains of 21.4% and 12.7%. The step-count comparison excludes some retrieval, inference and training costs; it is not total compute.
- Transfer, Figure 2 (p. 8): joint graph+copilot transfer was closest to target-specific training among the compared variants. However, the large-to-small comparison has no no-memory reference, so transfer alone does not establish improvement over the unaugmented target executor.
- Ablations, Figure 3 (p. 9): all four variants performed below the full method. Flat experience caused the largest drop but changed both candidate generation and ranking, so that drop cannot be assigned to graph structure alone.

## Limitations and competing interpretations

- Node utilities are set-level historical rewards, not per-experience causal values. Semantic relevance, historical utility and copilot adaptation are not independently isolated in the main ablations.
- The experiments use fixed graph hyperparameters and embedding-based similarity. The authors call for adaptive graph construction, pruning and richer process-level feedback (Appendix A, p. 14).
- Training is not free: Appendix B (p. 16) reports about 40 hours for ExpSuite-Agentic and 20 hours for ExpSuite-Static on 4 NVIDIA A6000 GPUs. Environment step counts do not include retrieval, LLM inference or training costs.
- There is a no-memory baseline but no random-bank control. The benchmarks cover static QA, math, code, ALFWorld and AppWorld, not small-local-model results across every task family or long-horizon real-world deployment.
- Retrieved experience does not guarantee safe behavior. The authors recommend human-in-the-loop checkpoints and auditable retrieval logs (Appendix A, p. 15).

## Project consequence and falsifiable test

Treat graph structure and utility-aware retrieval as separate factors to test, not as guaranteed improvements. Compare raw trajectories, a flat experience pool, graph diffusion and utility ranking under matched model, task, token and compute budgets, including a same-type random bank and explicit compute accounting. Joint graph+copilot transfer is a hypothesis to test against target-specific training, not a result to generalize to every model pair.

**Hypothesis:** graph diffusion plus utility-aware retrieval will outperform flat or random memories only for some task families and utility distributions. If matched comparisons show no advantage, reject the added graph and retrieval complexity for that setting rather than assuming it is always useful.
