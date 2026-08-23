# Reuse component characterization benchmark v0

Experiment ID: `PMLAB-REUSE-CHAR-001`  
Status: frozen-development protocol; synthetic characterization only

## Purpose

Test whether the narrow components selected by the reuse-before-inventing audit can share one provider-neutral contract before any product integration:

- SQLite FTS5/BM25 sparse retrieval;
- exact source citations;
- optional local FastEmbed dense retrieval;
- equal-input reciprocal-rank fusion with `k=60`;
- context construction with `current`, `supporting`, and `stale/conflicting` sections.

This is an implementation-characterization experiment. Its authored synthetic cases are visible to the implementer, small, and not independently labelled. It can reveal bugs, incompatibilities, missing metadata, and qualitative complementarity. It cannot select a production architecture, satisfy `PMLAB-NATURAL-RET-001`, or support a superiority claim.

## Frozen sample

- 36 line-addressable evidence records in Polish and English;
- 20 queries covering exact terms, paraphrases, cross-language cues, terminology shift, multi-evidence questions, stale/current competition, poison, and missing information;
- one byte-identical `search_text` field shared by every retrieval arm;
- exact source path and line range for every record;
- authored record metadata supplies pack buckets. Bucket inference is explicitly **not** tested here.

Record IDs are readable because this is a characterization fixture. Backends receive IDs only as return identifiers and receive no query labels, buckets, trust, paths, or gold.

## Retrieval arms

| Arm | Definition |
|---|---|
| `B2_FTS5` | SQLite FTS5 `unicode61`, OR query over deterministic Unicode tokens, BM25 order, ID tie break |
| `C0_FASTEMBED` | FastEmbed 0.8.0, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, exact normalized float32 inner product, ID tie break |
| `C2_RRF` | Equal-input fusion of B2 and C0 rankings at depth 10 using `sum(1/(60+rank))` |

FastEmbed source artifact: `qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q` at observed Hugging Face revision `faf4aa4225822f3bc6376869cb1164e8e3feedd0`. It is a restricted diagnostic, not the E5 candidate registered for the future natural benchmark. If FastEmbed or the model is unavailable, the run must report the dense and RRF arms as unavailable; it may not silently substitute a model.

## Packaging arms

Each available retrieval arm produces the same top five IDs, then packages them three ways under a frozen 768-byte UTF-8 budget:

- `raw`: text in retrieval order;
- `cited`: text plus `path:line-line` for every included item;
- `bucketed`: current first, then supporting, then stale/conflicting, preserving retrieval order within a bucket and reporting omissions.

Untrusted records are omitted from `bucketed` packs and counted. Stale/conflicting records remain visible in their own section; they must never appear under current or supporting. Packaging never changes retrieval metrics.

## Metrics

Retrieval:

- macro required-evidence Recall@5;
- all-required-evidence@5;
- MRR@5;
- forbidden/stale intrusion@5;
- candidate-null behavior for unanswerable queries;
- per-category recall;
- p50/p95 query latency, build time, embedding time, and vector bytes.

Citations and packing:

- exact citation span validity;
- citation coverage among packed items;
- required evidence retained under the byte budget;
- stale-to-current/supporting leakage;
- untrusted omission;
- actual UTF-8 bytes and omission counts.

## Characterization gates

These gates validate the instrument, not the architecture:

1. every corpus citation resolves to byte-identical source text;
2. every cited packed item has a valid locator;
3. bucketed packs have zero stale-to-current/supporting leakage;
4. bucketed packs never expose an untrusted record;
5. every pack respects 768 UTF-8 bytes and reports omissions;
6. RRF matches the frozen formula and deterministic tie break;
7. two fresh-process runs produce byte-identical rankings for all available arms;
8. the exact corpus and query hashes are recorded.

Retrieval gains, losses, and failures are observations only. No minimum retrieval score is an architecture gate.

## Interpretation boundaries

- Dense success on authored paraphrases does not demonstrate natural project-history benefit.
- Dense failure does not reject embeddings; it can reflect this diagnostic model, language mix, or small sample.
- RRF can improve one stratum while harming another. Only the future independently reviewed natural benchmark may decide whether it advances.
- Perfect citation or bucket metrics validate deterministic plumbing, not evidence truth, bucket inference, completeness, or reader behavior.
- Candidate-null is not semantic abstention: dense retrieval always has nearest neighbors unless a separate controller declines to answer.

