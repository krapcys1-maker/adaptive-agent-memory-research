# Benchmark ladder

Status: reviewed

## Fixed experimental unit

Each example contains:

- immutable source events and identifiers;
- query, query time, and optional target task;
- gold evidence IDs, including all acceptable alternatives;
- answerability and abstention label;
- temporal validity and supersession state;
- query category and difficulty;
- retrieved-token budget;
- downstream consequence weight where retention is tested.

The test corpus is frozen before backend tuning. Development and test histories must not share paraphrase templates, entities, or copied episodes when this could leak the answer.

## Retrieval ladder

| Level | Backend | Question answered | Unlock condition |
| --- | --- | --- | --- |
| O | full relevant evidence oracle | reader ceiling and prompt sensitivity | gold evidence reviewed |
| B0 | no memory | true incremental value of memory | always required |
| B1 | `rg`/tokenized lexical scan | lowest-complexity text baseline | always required |
| B2 | SQLite FTS5/BM25 | indexed sparse retrieval benefit | B1 reproducible |
| C1 | pinned local dense embeddings | paraphrase/semantic benefit | frozen corpus and embedding model |
| C2 | hybrid sparse+dense with fixed fusion | complementary retrieval benefit | C1 and fusion tuned only on development set |
| C3 | temporal/validity-aware ranking | update and as-of reasoning benefit | temporal gold labels reviewed |
| C4 | graph/causal traversal | relational multi-hop benefit | graph extraction accuracy measured separately |
| C5 | salience/learned retention | storage-budget and delayed-utility benefit | downstream utility labels and counterfactual protocol exist |

Graph and salience are not retrieval synonyms. Graph evaluation needs correct entity/edge extraction; salience evaluation needs write/retention decisions under a fixed storage or retrieval budget.

## Query strata

- exact lexical lookup;
- paraphrase and synonym substitution;
- weak lexical overlap;
- what-where-when episodic lookup;
- temporal `as of` and current-state questions;
- superseded or contradictory facts;
- causal and multi-episode chains;
- procedure and failure avoidance;
- prospective intention and trigger;
- cross-language Polish/English cues;
- unanswerable questions requiring abstention;
- adversarial distractors and stored prompt injection;
- scale at 1×, 10×, and 100× irrelevant history.

## Metrics by layer

### Storage and transformation

- exact event recovery;
- schema validity and corruption detection;
- provenance precision;
- unsupported-claim rate after consolidation;
- reversible supersession and recovery.

### Retrieval

- Recall@k, Precision@k, MRR, and nDCG;
- evidence recall per retrieved token;
- critical-memory miss rate;
- stale-memory intrusion rate;
- distractor and scale degradation;
- p50/p95 latency and disk growth.

### Reader use

- supported-answer accuracy using the same reader and prompt;
- citation/source attribution accuracy;
- temporal interpretation and contradiction resolution;
- abstention calibration;
- harm from irrelevant or poisoned retrieval.

### Downstream utility

- paired task-success delta with and without the memory;
- repeated-task efficiency and avoided failure cost;
- tokens, wall time, model calls, and monetary cost where applicable;
- retention regret under a fixed storage/retrieval budget;
- speed and accuracy of relearning after an archived memory is needed again.

## Repetition and analysis

- Deterministic retrieval runs are repeated only to detect infrastructure variance.
- Stochastic reader/judge conditions use multiple seeds or repeated calls declared in advance.
- Primary comparisons use paired examples and bootstrap confidence intervals or an appropriate paired test.
- Report effect size and confidence interval, not only a p-value.
- Inspect per-stratum errors before declaring a global win.
- A human-reviewed subset anchors any LLM judge; judge disagreement is a reported metric.

## What counts as success

A candidate advances only if its registered primary metric improves over the previous level with a positive 95% paired confidence interval and the practical minimum defined before the run. It must not exceed preregistered regressions in critical misses, stale intrusions, provenance, latency, tokens, disk, or privacy risk.

Suggested practical gates for the first laboratory version:

- storage integrity and provenance: 100% on the controlled corpus;
- retrieval: improvement in at least three nontrivial strata, not only aggregate score;
- end-to-end: at least 5 percentage points task-success improvement, or at least 15% token reduction while remaining within 2 points of baseline success;
- salience/retention: fewer consequence-weighted critical misses at the same storage and retrieved-token budget;
- graph: improvement on temporal/causal multi-hop cases after charging graph-extraction errors and build cost.

These thresholds are provisional and must be frozen in an experiment manifest before results are viewed.
