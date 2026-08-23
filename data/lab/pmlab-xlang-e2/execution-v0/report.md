# PMLAB-XLANG-E2 — local dense retrieval removes language as a variable

Experiment ID: `PMLAB-XLANG-E2`
Tier: **E (exploratory)** — local model, no network at query time, no API cost
Authority: development measurement only. **Recall only. No safety metric was measured.**
Follows: `PMLAB-XLANG-E1`, which measured the collapse and tested only model-free remedies.

Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 0.22 GB — the model this project already pinned and used in `PMLAB-REUSE-CHAR-001`. Weights cached locally.

## Results

Same 45 paired queries as E1. English query is the memory's title verbatim; Polish is a translation of the same title. Target is the memory's own id, known by construction.

| Arm | EN R@5 | EN R@10 | PL R@5 | PL R@10 |
|---|---|---|---|---|
| **B1** FTS5 only | 1.000 | 1.000 | 0.156 | 0.156 |
| **B3** FTS5 + glossary | 1.000 | 1.000 | 0.800 | 0.867 |
| **B4** dense | 1.000 | 1.000 | **0.911** | **0.978** |
| **B5** hybrid, RRF k=60 | 1.000 | 1.000 | 0.889 | 0.933 |

```
dense vs FTS5      +0.8222   95% CI [+0.7111, +0.9333]
dense vs glossary  +0.1111   95% CI [+0.0000, +0.2222]
hybrid vs FTS5     +0.7778   95% CI [+0.6444, +0.8889]

mean rank when dense finds the target: 1.956
```

## Three findings

### 1. Language stops being a variable

Polish Recall@10 goes from 0.156 to 0.978. Not translated around — dissolved. The embedding places a Polish question and its English answer in the same region, so there is nothing left to bridge.

When dense finds the target it puts it at mean rank **1.96**, so this is not a matter of digging it out of a long list.

Direct evidence of the mechanism, measured before the run:

```
cos("pamiec projektu",  "project memory")            +0.675
cos("czy graf ... w wyszukiwaniu", "does the graph ... retrieval")  +0.701
cos("pamiec projektu",  "zupa pomidorowa z makaronem")  +0.177
```

### 2. The hybrid is worse than dense alone

B5 scores 0.933 against B4's 0.978. Fusing a working arm with a failing one **costs** recall, because reciprocal rank fusion gives weight to a ranking that is mostly noise here.

This is the third time today that fusion has been measured to hurt: E1 showed graph fusion dropping English Recall@5 from 1.000 to 0.711, and the association graph contributed exactly zero when its lexical seed was empty. The pattern is consistent — **fusion helps only when both arms are informative, and silently taxes the good arm when one is not.**

### 3. Dense beats the hand-built glossary, but not by much

+0.111 with an interval whose lower bound sits exactly at zero. The glossary already recovers most of the gap for a hundred lines of JSON and no dependency.

The honest comparison is not recall but coverage: the glossary handles exactly the terms someone thought of and cannot handle paraphrase, an unfamiliar word, or a language nobody anticipated. Dense needs no vocabulary maintenance at all. The margin on *this* corpus understates the difference on any query the glossary's author did not foresee.

## What this does not show, and it matters more than what it does

**No safety metric was measured.** `PMLAB-REUSE-CHAR-001` measured dense forbidden intrusion at **0.200 against FTS5's 0.050** — four times worse.

The worst case is structural rather than incidental: **a superseded fact is maximally similar to its replacement.** "Ala has brown hair" and "Ala has green hair" are close neighbours by construction. So the mechanism that fixes cross-language recall is the same mechanism that makes stale-fact intrusion worse, and this project has already measured stale intrusion at 0.857.

A recall result of 0.978 is therefore **not a licence to adopt dense retrieval**. It is a licence to test it against the safety metric, which requires records labelled current and superseded — which `#29` has to define first.

Other limits:

- 45 queries, one corpus, one language pair, `n = 1` project.
- Polish queries are authored; the gold is mechanical but the translations are the author's.
- Title-verbatim English queries are a control, not a performance estimate.
- One model. No comparison against `multilingual-e5-large` or BGE-M3.
- `fastembed` is deliberately **not** in `requirements-dev.txt`. Adding it would make CI download an inference runtime and weights on every run; the script skips with a clear message when it is absent.

## What follows

1. **Do not swap the index yet.** Measure forbidden and stale intrusion first. The recall case is settled; the safety case is untouched.
2. **Keep the glossary.** It works today, costs nothing, and needs no dependency. Dense is the better long-term answer, not a reason to remove the cheap one.
3. **Stop fusing by default.** Three independent measurements now show fusion taxing the stronger arm. Fusion needs a condition, not a habit.
4. **`#29` becomes a prerequisite rather than a parallel track.** Without current-versus-superseded labels, dense retrieval's central risk cannot be measured at all.
