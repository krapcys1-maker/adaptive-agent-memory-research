# WMB-R1: lexical versus hybrid retrieval on the account's own notes

Status: PREREGISTRATION, written before any model call of this slice. Nothing below has been run. Amendments are appended at the end, each with the reason and the commit.

## The question

The writing agent's session asked (board N-028, 2026-11-01) whether the shared memory module needs an embedding model at all. Their server has no numpy and no torch, so a MiniLM-class embedder in ONNX would be a separate, installed, versioned dependency; the lexical memory they run now gives a candidate on about 5% of tasks at its threshold, MiniLM at cosine 0.6 on about 20%. The two numbers are not comparable (different thresholds, no judgement of whether the candidate is the right note). This slice compares lexical and hybrid retrieval on equal terms, with relevance judged by a reader that does not know which method found the note.

Decision it informs: whether `memory_kernel` ships with an embedder profile on the writing agent's server for note-writing tasks (U1), and whether question-style recall such as the persona's facts (U2, U3) needs one later.

## What is not claimed

One account, 234 notes, tasks written by a model from the notes themselves, one relevance judge, one embedding model. A result here is an engineering input for this deployment, not a statement about lexical versus dense retrieval in general. Thresholds are fitted in-sample and say nothing about how they would generalise. Nothing here shows that injected memory improves a note (that is E5 and the live harm check); it only measures whether the right earlier note is found, and what a false injection costs in counts.

## Data (all local; only aggregates are published)

- `opublikowane.jsonl`, 234 published notes, sha256 `a775f381d08619a522b5699527a66e1ffd4b0747245bd71f8bd036dff75d71bb` (D:\Pamiec LLM\NIE_DANE).
- `replay/prep.json`, the E5 briefs (one neutral sentence per note, written by flash from the note), sha256 `f7cd207aacdc41b92ea64edd8a7c9ff78c292b54986be567ad3328cad706a565`.
- `data/lab/aam-e6-persona/persona.json` (synthetic persona; 26 biography items, 24 fact questions), sha256 `e30d8ef27d62e03e48cd201d9652947f4bf21eb585a761c2733390221d530a4a`.
- MiniLM: `sentence-transformers/all-MiniLM-L6-v2` from the local cache, CPU, as E5 used it.

Published: this README, `config.json`, `results.json`, `summary.json` (with the sha256 of the local record files), the scripts and tests. Not published: note texts, briefs, generated questions, pair texts.

## Part U1: the main part, tasks of the real kind

Tasks. Notes in the order of `parse_items` (date, then id), as in E5. Task `i` is the brief of note `i`, for `i = 20 .. 233` (E5's warm-up of 20): **214 eligible tasks**. The memory for task `i` is the notes `j < i` only. For the kernel, note `k` gets the synthetic time `day_k` 08:00 plus its rank within the day in minutes, so that earlier notes of the same day count as earlier (E5's rule) and the kernel's strict no-future rule agrees with it.

Methods. All use the kernel's tokenisation (lower-case stems, stop list) where they are lexical.

| id | what it is |
|---|---|
| LEX_BM25 | BM25, k1 = 1.2, b = 0.75, idf over the causal memory of the task |
| LEX_KERNEL | the kernel's lexical channel as shipped (`memory_kernel.retrieve`, profile `lexical`, `min_evidence` 0, `names` off): idf-weighted coverage of the brief by the note |
| LEX_TFIDF | cosine of sublinear tf-idf vectors |
| EMB_MINILM | cosine of MiniLM vectors of brief and note (E5's score) |
| HYB_KERNEL | the kernel's hybrid (`retrieve`, profile `kernel` with ready vectors): strength = max(coverage / tau_lex, cosine / tau_emb) |
| REF_E5 | reference only: fire when the MiniLM top-1 cosine is at least 0.5722 (E5's threshold) |

`tau_emb` = the 80th-percentile rule applied to the top-1 MiniLM cosines of the eligible tasks (E5's own rule, which gave 0.5722; the script recomputes it and records both). `tau_lex` = the same rule applied to the top-1 coverage of LEX_KERNEL. So each channel alone fires on 20% of tasks and HYB_KERNEL is their union at that calibration. All strengths are then swept (below), so the absolute values matter only for how HYB_KERNEL weighs its two channels.

Each method gives per task a ranked candidate list (best first; ties broken towards the more recent note, as E5) and the score of its first candidate (`s`).

Pool and labels. For every eligible task the pool is the union of the top 5 candidates of LEX_BM25, LEX_KERNEL, LEX_TFIDF, EMB_MINILM and HYB_KERNEL. Each pooled pair (task, earlier note) is judged once by deepseek-flash through the judge proxy (temperature 0, fixed seed), blind to method and score, in an order that is a fixed shuffle of the pairs. The judge sees the brief and the earlier note and answers one word:

- `SAME`: the earlier note is about the same specific story, event, announcement or claim as the task, so the author could sensibly build on it or refer back to it;
- `RELATED`: the same broad subject or theme, a different specific story or claim;
- `UNRELATED`: otherwise.

The prompt text is in `config.json` (its sha256 is recorded). A reply that is not one of the three words is retried once with another seed; a second failure is a format failure. Pairs not in the pool are never judged and never counted as relevant (the usual pooling assumption; every method's own top-1 is in the pool by construction).

Strict relevance = `SAME`; lenient = `SAME` or `RELATED`. The prevalence rule: if at least 25 eligible tasks have at least one `SAME` note in their pool, the primary relevance is strict; otherwise lenient, and the strict one is reported beside it.

Judge gate (all must hold before any label is used for a reading):
1. positive control: 60 pairs (brief `k`, note `k`) for `k` drawn from the eligible tasks (seeded): at least 57 `SAME`;
2. negative control: 60 pairs (brief `i`, note `j`, `j < i`) with no shared content stem and MiniLM cosine below 0.15 (seeded): at least 57 `UNRELATED`;
3. repeat: a seeded 10% of the pooled pairs judged a second time with another seed: at least 85% identical labels;
4. hand sample: 40 pooled pairs stratified by judge label (14 SAME, 13 RELATED, 13 UNRELATED, or as many as exist), labelled by the assistant in a separate pass that has not seen the judge's labels: at least 85% agreement on SAME versus not-SAME. These are not a human ground truth (the reader is a language model too); they are a second, independent reading, and the owner may audit the sample file;
5. format failures at most 2% of calls.

If the gate fails, the labels are not used for the U1 readings and the report says so; U2, U3 and the implementation controls still stand.

Readings, for method `m` and sweep fraction `q` in {0.10, 0.20, 0.30}:
- Fire set `F_m(q)`: the `ceil(q * T)` tasks with the highest score `s` (ties by task index), `T` = number of eligible tasks. A task with no candidate is never fired; if fewer than `ceil(q * T)` tasks have a candidate, the method fires on all of them and the shortfall is reported.
- `hits_m(q)`: tasks in `F_m(q)` whose first candidate is relevant. `false_m(q)` = `|F_m(q)| - hits_m(q)`, the false injections. Equal exposure makes hits and false injections directly comparable between methods.
- **P1 (primary)**: `D = hits_HYB_KERNEL(0.20) - hits_LEX_KERNEL(0.20)` under the primary relevance. 95% interval by paired bootstrap over tasks (10,000 resamples, seed 20261102; the fire sets are recomputed inside every resample). Margin `delta = 6` tasks (about 3 percentage points of eligible tasks).
  - `EMBEDDER_HELPS_GATE`: lower bound of the interval above 0 and `D >= delta`;
  - `LEXICAL_SUFFICIENT_FOR_GATE`: upper bound below `delta`;
  - `UNRESOLVED` otherwise.
- Secondary, descriptive, no correction for multiplicity: the same `D` at q = 0.10 and 0.30 and under the other relevance; hits and false injections of all methods at every q; `LEX_BM25` and `LEX_TFIDF` against `LEX_KERNEL` (is the shipped lexical channel a poor choice of lexical?); `hits@3` (fired tasks with a relevant note among the method's first three); `REF_E5` (fire rate, hits, false injections).
- Exploratory, never used for the decision: the effect of the kernel's evidence floor (`min_evidence` 0, 0.4, 0.8, 1.2) on precision at 20% firing, and the channel weights; these produce the proposed default thresholds, flagged as in-sample.

## Part U3: questions with little word overlap

120 notes drawn by seed, 40 from each length tercile of all 234 notes. For each, flash (writer proxy) writes one question whose answer is a specific detail in the note and which must not reuse the note's distinctive words (paraphrase). Prompt in `config.json`. Gate: an answerability check by flash on the judge proxy ("does this note contain the answer?"): at least 95% yes; questions failing it are dropped and counted. Overlap of a question = share of its content stems found in the source note; terciles by overlap over the retained questions.

Memory = all 234 notes (no time restriction; this is question answering about the past, not task-time recall). Gold = the source note. For each method: recall@1, @3, @10 and MRR, overall and by overlap tercile.

- **P2**: in the lowest-overlap tercile, `D3 = recall@3(HYB_KERNEL) - recall@3(LEX_KERNEL)`, paired bootstrap over questions (10,000 resamples, seed 20261102).
  - `EMBEDDER_RESCUES`: lower bound above 0 and `D3 >= 0.15`;
  - `NO_RESCUE`: upper bound below 0.10;
  - `UNRESOLVED` otherwise.
- Limitation stated in advance: another note may also answer a question; such cases count against the method that returns it. No audit of this is planned beyond reporting how many of the first-ranked wrong notes share at least half of the question's content stems.

## Part U2: the persona's facts (smoke test, descriptive)

Index = the 26 biography items (origin `fiction_autobio`, dates as in the persona file) plus the 234 notes as distractors. Query = each of the 24 fact questions, task type `personal`. Gold = the biography items that contain any of the question's key strings (case-insensitive, whole word). recall@1 and @3 for each method, overall and by question style (`direct`, `indirect`). With 24 questions nothing here can decide anything; it is a check that the pipeline works on the persona and a first look at the name problem the kernel's name channel exists for.

## Implementation controls (free, run before any model call)

- C1 self-retrieval: for every eligible task `k`, the brief of note `k` against all 234 notes, non-causally: the note `k` must be the first candidate for at least 90% of tasks for every method. A method below that is a bug, and no reading is reported until it is fixed (amendment).
- C2 causality: for every method and task, no candidate has an index at or above the task's.
- C3 the kernel path agrees with an independent reference implementation of its coverage and cosine on a seeded 30 tasks (rank 1 identical, scores within 1e-6).
- C4 label shuffle (analysis check, synthetic and real): permuting relevance labels within each task must move `D` to about 0 and make the verdict not `EMBEDDER_HELPS_GATE` in at least 95% of 200 shuffles.

## Decision table

| P1 | P2 | what is recommended to the writing agent |
|---|---|---|
| EMBEDDER_HELPS_GATE | any | Add the embedder profile for note-writing memory. |
| LEXICAL_SUFFICIENT_FOR_GATE | not EMBEDDER_RESCUES | Stay lexical; no new dependency. |
| LEXICAL_SUFFICIENT_FOR_GATE | EMBEDDER_RESCUES | Lexical for note-writing; an embedder is needed only for question-style recall (the persona and identity phase), to be decided then. |
| UNRESOLVED | any | Run the kernel lexically in shadow; revisit with the shadow N1 aggregates (more tasks) before adding a dependency. |

If the judge gate or a control fails, the table is not applied and the report says which part is missing.

## Power, stated before the result

About 40 tasks fire at q = 0.20. If the two methods hit about 25 of them, with 10 to 15 tasks where they disagree, the bootstrap interval for `D` is roughly plus or minus 8 tasks. So only a gain of about 9 tasks or more (4 percentage points) can come out as `EMBEDDER_HELPS_GATE`, and `LEXICAL_SUFFICIENT_FOR_GATE` requires an upper bound under 6, which needs the two methods to be close on this sample. `UNRESOLVED` is a likely and honest outcome. P2 has 40 questions per tercile and larger expected effects.

## Cost and safety

Only deepseek-flash, through the flash-only metering proxies (judge 8798, writer 8799; ledger scope `e1`, cap 12 USD for the scope). Planned calls: about 2,800 pairs, 120 controls, 280 repeats, 120 generated questions, 120 answerability checks, roughly 3,400 calls of about 700 tokens, under 1 USD at list price. Stop at 2 USD of this slice. No key is printed or stored.

## Order of operations

1. This README and `config.json` reviewed by independent adversarial readers (before any code is final); amendments logged.
2. Scripts and tests written; digests recorded in `config.json`; the whole committed. This is the freeze.
3. `prepare` (free) and the implementation controls C1 to C4.
4. Judge gate collection (controls, repeat sample), then the pooled labels, then the hand sample.
5. `analyse`; verification by an independent re-implementation of the analysis from the record files; PR; result to the writing agent's session.

## Amendments

(none yet)
