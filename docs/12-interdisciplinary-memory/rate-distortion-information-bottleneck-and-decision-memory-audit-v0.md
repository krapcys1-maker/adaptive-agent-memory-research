# Rate-distortion, information bottleneck, and decision-memory audit v0

Status: targeted foundational, primary-model, contradiction, and recent-agent pass; no compression policy selected

Last reviewed: 2026-08-23

## Question

What should a disk-backed LLM memory preserve when the archive can be large but retrieval, active context, latency, and maintenance compute are bounded?

The answer cannot be `summarize more`. Lossy compression is defined only relative to a source distribution, a resource budget, a reconstruction/use operation, and a distortion measure. If future tasks are unknown or the distortion measure is wrong, an apparently optimal summary can destroy the one exception needed to revise the model later.

## Source-identity correction

The project seed previously linked *Optimal forgetting: Semantic compression of episodic memories* to `10.1371/journal.pcbi.1008363`. The official PLOS record and the discovered catalog identify the article as [`10.1371/journal.pcbi.1008367`](https://doi.org/10.1371/journal.pcbi.1008367). The seed is corrected in this pass.

Together with the prospective-memory DOI correction in the previous pass, this establishes a project-wide need for automated title-author-year-DOI identity checks before a source can become accepted evidence.

## Evidence classes

| Source | Contribution used here | Boundary |
| --- | --- | --- |
| [Shannon 1959](https://ieeexplore.ieee.org/document/5311476) | rate-distortion theory characterizes achievable rate for a declared source and fidelity/distortion criterion | does not supply a distortion function for truth, safety, or future agent decisions |
| [Tishby, Pereira, and Bialek 1999/2000](https://arxiv.org/abs/physics/0004057) | a short code for `X` can be optimized to preserve information about a relevant variable `Y` | the future-relevant `Y` and its distribution are unknown and nonstationary for open-ended agents |
| [Nagy, Török, and Orbán 2020](https://doi.org/10.1371/journal.pcbi.1008367) | generative semantic compression produced structured, human-like distortions across chess, natural text, and sketches | explanatory normative/computational account; plausible distortion is not factual correctness |
| [Jakob and Gershman 2023](https://doi.org/10.7554/eLife.79450) | a rate-distortion population-code model fit several visual working-memory error structures better in seven of eight reported comparisons | restricted visual tasks, reused datasets, and two-monkey neural reanalysis; public reproduction is artifact-blocked |
| [Nagy, Orbán, and Wu 2025](https://doi.org/10.31234/osf.io/emky9) | perspective argues that model-incongruent episodes may need higher fidelity so later structure learning can reinterpret them | proposal/synthesis; variable-rate protection of later structure revision remains untested |
| [Zou et al. 2026 / DeMem](https://arxiv.org/abs/2605.10870) | decision-conflict-aware state partitioning reportedly improved several long-horizon memory results at a matched runtime budget | recent preprint, reader/judge dependence, no public code found, finite contextual-bandit assumptions, single-hop exceptions |
| [Colaco and Lahjouji 2026](https://arxiv.org/abs/2607.08032) | cross-layer survey and small reference experiment distinguish reversible archive retrieval from rolling irreversible compaction | small illustrative experiment and heterogeneous survey, not a broadly reproduced systems result |
| [RECOMP](https://openreview.net/forum?id=mlJLVigNHp), [LongLLMLingua](https://aclanthology.org/2024.acl-long.91/), and [LLMLingua-2](https://aclanthology.org/2024.findings-acl.57/) | establish learned selective augmentation, query-aware compression, and budget/reordering comparators | task-, reader-, model-, language-, and ratio-dependent derived views without byte-exact evidence guarantees |

## Four operations that must not share one label

1. **Lossless encoding:** reversible representation of the same bytes or symbols.
2. **Extractive selection:** retain exact spans while omitting other evidence from the current pack.
3. **Generative summarization:** produce new lossy text that may merge, infer, or omit content.
4. **Decision-state abstraction:** map histories to the same runtime state when they are predicted to support the same action/value decision.

The project's compact citation handles are lossless pack encoding. FTS5 top-k is extractive selection. A rolling narrative summary is generative compression. DeMem-style partitioning is decision abstraction. Their rates, errors, and reversal paths are different.

## Three budgets that must be reported separately

- canonical disk bytes and growth;
- active context bytes/tokens presented to the reader;
- maintenance/retrieval model calls, latency, energy proxy, and monetary cost.

A method can reduce context tokens while increasing disk, calls, latency, or privacy exposure. Calling that simply `compression` hides the tradeoff.

## Formal translation and its limits

Let:

- `H` be an evidence-bearing history;
- `Z = C(H, q)` be a compressed or selected representation under query/task `q`;
- `B` be the declared budget;
- `A` be the downstream answer/action policy;
- `L(A(H,q), A(Z,q))` be decision distortion or regret;
- `G` be safety/provenance constraints that cannot be traded away by average utility.

The engineering problem is not only:

```text
minimize expected L subject to size(Z) <= B
```

It is closer to:

```text
minimize expected decision loss + measured compute/latency cost
subject to active-context budget B
and hard provenance, authorization, stale-state, privacy, and critical-exception gates G.
```

This still does not authorize deleting `H`. The objective is conditional on the observed task distribution, decision labels, utility model, and threat model. Unknown future queries and later corrections make reversible archive retention a distinct governance decision.

## Failure modes

### Wrong relevance variable

Information bottleneck preserves information about `Y`; it does not tell us what `Y` should be. Training only on current questions may erase evidence for future tasks, audits, disputes, or model revision.

### Average loss hides critical exceptions

A common rule can dominate mean accuracy while a rare contraindication, authorization exception, or correction carries much larger harm. Report critical-case recall and worst/grouped loss, not only an average score.

### Semantic completion creates convincing errors

Generative models can reconstruct likely details that were never observed. Plausibility may improve conventional similarity or reconstruction metrics while reducing evidential truth.

### Surprise preserves poison

Unexpected events can reveal a new rule, be random noise, or be adversarial. Surprise alone is not importance, truth, emotion, or future utility.

### Repeated compaction compounds omission

A summary-of-summary pipeline removes access to discarded distinctions and can convert earlier uncertainty into later certainty. Maintenance-cycle curves must include 0, 1, 2, 5, 10, and 20 transformations.

### Decision equivalence is model-relative

Two histories are safe to merge only relative to a task/action/value model. A later action space, new evidence, or corrected reward can split them again. Store partition evidence and keep reconstruction links.

### Compression can increase prompt-injection risk

A generative compressor may remove distrust markers or summarize malicious instructions as legitimate procedure. Derived text never inherits authority from source text.

## Current project evidence

- `PMLAB-PACK-002` shows compact source handles can preserve exact evidence while reducing repeated locator overhead; this is reversible encoding, not learned semantic compression.
- `PMLAB-PACK-READER-001` found one single-family compatibility result, including a compact-governed citation miss; it does not select compact format as default.
- `PMLAB-REUSE-CHAR-001` found retrieval-arm safety differences on a synthetic fixture; high recall did not imply low forbidden intrusion.
- The repeated-compaction, model-change/exception/noise, semantic-completion, consequence allocation, delayed-promotion, and specificity tests remain preregistration drafts without results.

## Revised benchmark direction

Add `C7` to the compression protocol:

### C7 — decision-conditioned distortion under task shift

Freeze histories with pairs that are:

- descriptively similar but action-incompatible;
- descriptively different but action-equivalent;
- equivalent for the current task but different for a hidden future task;
- common-rule versus rare critical exception;
- correct anomaly versus noise/poison;
- current versus corrected reward/authorization model.

Compare:

- raw archive plus exact retrieval;
- equal-token extractive evidence selection;
- generic equal-length summary;
- query-aware learned compression;
- descriptive similarity partition;
- decision-conflict partition;
- versioned decision partition with raw fallback;
- oracle task-specific partition.

Primary endpoints:

- counterfactual decision regret at fixed context bytes/tokens;
- critical-exception miss and wrong-action rate;
- transfer loss under future-task reveal;
- correction/repartition recovery;
- exact source/provenance resolution;
- poisoned-state merge rate;
- total maintenance/retrieval cost.

Promotion requires gains over extractive and raw-retrieval baselines on at least two task families without critical, provenance, or task-shift regression. One current-task average gain cannot select an architecture.

## Minimal architecture implication

The evidence currently supports a conservative separation:

```text
lossless canonical archive
  -> rebuildable exact indexes and source locators
  -> optional versioned summaries/partitions as hypotheses
  -> query-conditioned active pack under measured decision and safety loss
```

Do not recursively overwrite the sole summary. Do not treat a semantic layer as observation. Do not delete raw evidence because a learned compressor predicts low present utility.

## Current conclusion

Rate-distortion and information bottleneck give a precise language for tradeoffs, not a universal memory algorithm. Their decisive missing input is the distortion/relevance variable. For this project, compression succeeds only when it preserves downstream decisions, rare consequential exceptions, corrections, provenance, and safe abstention under a fixed active-context and compute budget. Reversibility remains mandatory until governance and prospective evidence justify otherwise.

## Open work

- automate title/author/year/DOI identity validation for accepted sources;
- independently review the eight-source evidence boundary;
- freeze C7 tasks, action/value labels, task-shift reveal, and hard safety gates;
- replicate repeated compaction with two task families and at least two summarizers;
- find or request DeMem code; no repository was found in repeated exact-title/method searches through 2026-08-23;
- add a fixed non-LLM scorer wherever possible before any learned reader/judge;
- measure disk, context, model calls, latency, and monetary cost separately;
- keep model-based compression locked until reversible/extractive controls are frozen.
