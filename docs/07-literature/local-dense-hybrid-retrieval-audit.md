# Local multilingual dense and hybrid retrieval audit

Status: targeted primary-source wave complete; candidate identities frozen for development screening

## Question

Which reusable components should enter the next project-memory retrieval comparison without prematurely choosing a vector database or a product architecture?

## Decision

Admit two local multilingual representations to development screening, one low-cost semantic control, one exact search definition, and one untuned fusion rule:

- `intfloat/multilingual-e5-small` is the default resource-conscious dense candidate.
- `BAAI/bge-m3` is a resource-ceiling candidate, evaluated in dense-only mode.
- multilingual MiniLM is a diagnostic control, not the presumed winner.
- normalized float32 matrix multiplication is the reference exact search.
- equal-input Reciprocal Rank Fusion with `k=60` is the first hybrid.

Do not select Faiss, sqlite-vec, an approximate index, BGE-M3 sparse output, ColBERT, a reranker, or a learned fusion model in this comparison. Those are separate mechanisms and would destroy causal attribution.

Exact captured revisions and roles are in `data/catalogs/dense-retrieval-candidates.csv`.

## Evidence audit

### Multilingual E5 small

The pinned model card and configuration report 12 layers, 384-dimensional embeddings, a 512-position input limit, MIT licensing, and a required `query: ` / `passage: ` prefix even for non-English text. The model card explicitly warns that longer text is truncated to 512 tokens. The technical report describes a multilingual weakly supervised pretraining stage followed by supervised fine-tuning.

What this supports: a plausible low-resource multilingual retrieval candidate with a documented asymmetric retrieval interface.

What it does not support: superiority on this project's mixed Polish/English research history, calibrated completeness scores, or a choice of vector store.

Sources: [pinned model card](https://huggingface.co/intfloat/multilingual-e5-small/tree/614241f622f53c4eeff9890bdc4f31cfecc418b3), [E5 technical report](https://arxiv.org/abs/2402.05672).

### BGE-M3

The pinned model card reports 1024-dimensional output, input up to 8192 tokens, more than 100 working languages, and dense, learned sparse, and multi-vector modes. It also says query instructions are no longer required. The card acknowledges a corrected MIRACL evaluation error and states that BM25 remains competitive in long-document retrieval. This is useful evidence for careful replication, not a defect to hide.

What this supports: a high-resource multilingual ceiling and later hypotheses about long units or multi-function retrieval.

What it does not support: mixing its three outputs into the first dense test, giving it longer source units than E5, or adopting its recommended hybrid weights without a separate development procedure.

Sources: [pinned model card](https://huggingface.co/BAAI/bge-m3/tree/5617a9f61b028005a4858fdac845db406aefb181), [BGE-M3 report](https://arxiv.org/abs/2402.03216), [official implementation](https://github.com/FlagOpen/FlagEmbedding).

### Multilingual MiniLM control

The model card labels the model as a 50-language sentence-similarity representation with 384-dimensional output and Apache-2.0 licensing. Its sentence-transformers configuration limits inputs to 128 tokens.

What this supports: a cheap check of whether general semantic similarity already captures easy paraphrases.

What it does not support: treating the result as a fair long-memory ceiling. Truncation must be reported and this arm cannot decide the architecture.

Source: [pinned model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/tree/e8f8c211226b894fcb81acc59f3b34ba3efd5f42).

### Polish retrieval evidence

PIRB contains 41 Polish retrieval tasks across multiple domains and evaluates more than 20 dense and sparse systems. It reports strong multilingual E5 results and further gains from sparse-dense hybrid retrieval. The paper's qualitative analysis associates hybrid gains especially with named entities and specialized terminology.

The transfer limit is decisive: PIRB's final fusion uses a learned ranking model trained on Polish retrieval data. Our first hybrid is therefore the simpler unsupervised RRF control, not a reproduction of PIRB's learned fusion. PIRB is external transfer evidence and cannot replace a natural project-history test. Its paper is CC BY-NC 4.0 and the repository/datasets require a component-level license audit before redistribution.

Sources: [PIRB paper](https://aclanthology.org/2024.lrec-main.1117/), [official code](https://github.com/sdadas/pirb).

### Fusion and exact search

Cormack, Clarke, and Buettcher define RRF as the sum of `1 / (k + rank)` over input rankings. They fixed `k=60` during a pilot and did not alter it during validation. RRF combines ranks rather than incompatible raw scores, making it an appropriate first untuned sparse-dense baseline.

Faiss documentation identifies Flat indexes as the exact option and `IndexFlatIP` as inner-product search. With L2-normalized vectors this implements cosine ranking. For our present corpus, direct NumPy exact search is even easier to audit. Faiss must reproduce those ranks exactly before it may replace the reference implementation.

Sources: [RRF paper](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf), [Faiss index guidance](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index).

## Frozen representation controls

All dense arms must share:

- one corpus snapshot and one model-independent source-unit manifest;
- identical source text, without hidden metadata or backend-specific summaries;
- a common maximum source-unit length no greater than the selected E5 limit;
- documented truncation counts and tokenizers;
- model revision, tokenizer revision, pooling, prefix policy, normalization, dtype, device, library lock, and batch size;
- exhaustive search and an opaque document-ID tie break;
- top-k retrieval output plus returned bytes/tokens, latency, peak RAM, index bytes, and embedding time.

The primary comparison concerns representation. Storage, ANN, reranking, long-document encoding, learned sparse output, and learned fusion each require a later one-difference-at-a-time test.

## Rejection rules

- Reject a model manifest if its pinned revision cannot be fetched and hash-verified offline.
- Reject an arm if tokenization or truncation differs from its manifest.
- Invalidate a comparison if source units differ between backends.
- Park BGE-M3 if the available machine cannot run the frozen dtype without swapping or silently changing precision.
- Do not promote dense retrieval if gains occur only on authored paraphrases and do not transfer to prospective natural queries.
- Do not promote hybrid retrieval unless it beats the stronger component under the registered effect and cost thresholds.

## Repository checkpoint

Five new source repositories were shallow-cloned under the ignored `external/repos/` tree and recorded by commit in `data/catalogs/repository-revisions.csv`: sentence-transformers, FlagEmbedding, Faiss, sqlite-vec, and PIRB. No model weights or PIRB constituent datasets have been downloaded yet.
