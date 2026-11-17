# Embedding Model Benchmarks (FP16 on RTX 3060)

*Note: Peak GPU VRAM and GPU Latency were measured by me using a unified 10-iteration warm-up and 100-iteration average across all models in FP16. Top-1, Top-5, and Same Game overlap metrics are referenced from @krapcys1-maker's earlier comment to provide a consolidated view.*

| Model | Peak GPU VRAM | GPU Latency (ms/step) | Top-1 Exact Match | Top-5 Overlap | Top-1 Same Game | 
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen3-Embedding-4B** (Base) | 7.58 GB | 78.64 ms | Reference | Reference | Reference |
| **Qwen3-Embedding-0.6B** | 1.13 GB | 49.60 ms | 41.9% | 63.5% | 71.6% |
| **bge-small-en-v1.5** | 0.07 GB | 11.36 ms | 28.2% | 62.9% | 72.7% |
| **all-MiniLM-L6-v2** | 0.05 GB | 11.09 ms | 46.6% | 59.9% | 72.0% |

## Recommendation
Based on these trade-offs, I recommend moving forward with **all-MiniLM-L6-v2** as the embedder. It has the highest exact top-1 match with the 4B baseline (46.6%), uses virtually zero VRAM (0.05 GB), and processes at a highly efficient 11.09 ms/step, leaving the GPU completely free for the 4.4 GB agent model.
