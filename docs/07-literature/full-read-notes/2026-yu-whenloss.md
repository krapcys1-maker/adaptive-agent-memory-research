# Yu, Lin & Wu — WhenLoss

- Status: full text read; extracted; recent preprint; code not located
- Version read: arXiv:2605.24579v1, 2026
- Source: https://arxiv.org/abs/2605.24579v1
- Local cache: `sources/papers/2026-WhenLoss-Diagnosing-Write-and-Retrieval-Bottlenecks.pdf` (ignored)

## Method and result

The paper evaluates a fixed reader under truncated full context, oracle evidence, complete stored memory, and retrieved memory. On 500 LongMemEval questions with three readers and a 5K write budget, four of six baselines were robustly write-dominant under the stated 0.02 margin. Controlled write and retrieval degradations selectively increased the corresponding gap. Reader-independent turn/span checks broadly matched the write ranking. Cross-benchmark LoCoMo and budget sweeps were also reported.

Exact locators: Section 3 and Figure 1 for the protocol; Table 3 and Figures 3–5 for diagnosis and perturbation; Section 6.8 and Table 6 for transfer/budget; Limitations.

## Limitations

- `OE -> CSM` is an upper bound on write degradation and may include format or missing-context mismatch.
- Indicators depend on reader, metric, budget, and gold-evidence annotations.
- LongMemEval and LoCoMo do not cover every memory workload.
- EPC adds a write-time LLM call and predicts future questions; misprediction may bias retention.
- No public code repository was found in the recorded exact searches.

## Project consequence

Adopt the condition ladder but add deterministic byte/checksum probes, explicit context-construction measurement, and action/evaluator stages. Use gaps to localize degradation, not to claim a single root cause.
