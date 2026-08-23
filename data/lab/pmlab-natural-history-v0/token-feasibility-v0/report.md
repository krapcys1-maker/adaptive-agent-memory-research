# Natural-history logical-unit byte and tokenizer feasibility v0

Status: deterministic, label-free feasibility result; no byte ceiling, source-unit builder, retrieval backend, dense model, or architecture selected.

## Question

Before building a historical corpus, how large are the policy-eligible logical units in an exact Git snapshot, and which pinned tokenizer limits would be exposed if those units were passed without splitting?

This is deliberately not a retrieval experiment. It reads no queries, gold evidence, labels, backend scores, embeddings, or vectors.

## Frozen inputs

- source snapshot: `44b2b9beeb4339fa3b758baba80bb3514c4b9ba1`;
- multilingual E5-small tokenizer revision: `614241f622f53c4eeff9890bdc4f31cfecc418b3`, including the registered `passage: ` prefix and 512-token limit;
- BGE-M3 tokenizer revision: `5617a9f61b028005a4858fdac845db406aefb181`, with the registered 8,192-token limit;
- paraphrase-multilingual-MiniLM-L12-v2 tokenizer revision: `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, used only as a 128-token diagnostic.

Only tokenizer/configuration files were downloaded. Model weights were not downloaded or executed. Exact local tokenizer-file hashes are recorded in `tokenizer-files.json` and the aggregate result is in `summary.json`.

## Result

The audit extracted 1,673 pre-split logical units: 1,290 Markdown sections, 241 catalog rows, and 142 project-memory events. The median unit was 531 UTF-8 bytes; p90 was 1,041, p95 was 1,345, p99 was 2,698, and the maximum was 35,639 bytes.

Unsplit token exposure was materially model-dependent:

| Tokenizer | Registered limit | Units over limit | Median | p95 | Maximum |
|---|---:|---:|---:|---:|---:|
| MiniLM diagnostic | 128 | 942 | 139 | 374 | 9,659 |
| multilingual E5-small plus passage prefix | 512 | 37 | 141 | 376 | 9,661 |
| BGE-M3 | 8,192 | 1 | 139 | 374 | 9,659 |

The aggregate candidate-byte scan does not select a ceiling. It shows why bytes alone are insufficient:

- 1,536 bytes retains 96.53% of logical units without splitting, but two units at or below that byte size already exceed E5's token limit;
- 2,048 bytes retains 98.15%, while eight such units exceed E5's limit;
- 3,072 bytes retains 99.22%, while 24 exceed E5's limit;
- 4,096 bytes retains 99.46%, while 28 exceed E5's limit;
- no listed byte threshold makes the 128-token MiniLM diagnostic truncation-safe.

The maximum unsplit unit also exceeds BGE-M3's registered limit. Therefore every admissible implementation needs an executable oversize path; a large-context encoder does not remove that requirement.

## Interpretation

The result rejects three shortcuts:

1. do not choose the global byte ceiling from a percentile alone;
2. do not allow provider/model-specific silent truncation;
3. do not treat MiniLM as interchangeable with the E5/BGE development candidates on common source units.

The next label-free step is to validate the revised deterministic split contract, including repeated heading context, zero overlap, and byte-identical body reconstruction. Only its post-split byte/token distribution can support a ceiling proposal. Independent contract review must still precede a builder authorization.

## Reproducibility and limits

Two consecutive runs produced identical `summary.json` SHA-256 `63139780bf4050b713e46536114eceddf1c6b21f112c839f1df1dcb2ac37312b`. The result describes one historical project snapshot and pinned tokenizer revisions. It does not measure embedding quality, retrieval quality, reader utility, latency, memory use, or generalization. The secondary `CURRENT_STATE.md` factor is counted for feasibility but remains excluded from the primary corpus.
