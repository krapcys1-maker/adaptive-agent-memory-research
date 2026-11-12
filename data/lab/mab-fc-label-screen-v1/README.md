# FactConsolidation label screen (MemoryAgentBench), 2026-11-12

A model-free screen of the released answers of MemoryAgentBench FactConsolidation against the benchmark's own update
rule. No model was called.

**Status: a screen with one reader, not confirmed benchmark errors.** The screen flags 68 of 800 released answers.
Every flagged item was then read against its question by one AI auditor. No human and no second reviewer has checked
the flags, the benchmark's maintainers have not been asked, and the project owner decided on 2026-11-12 to keep this as
a separate result and not to treat the flagged labels as established defects. Nothing was reported upstream.

## What was asked

MemoryAgentBench (arXiv:2507.05257v3, App. B.4.2) numbers every sentence of the context; in an edit pair the outdated
sentence has the smaller number. A (subject, relation) key therefore has one current value, the one with the largest
serial number. The screen asks, for each question, whether the released answer can be produced by a reasoner that
applies this rule at every hop.

## Counts

| Variant | Questions | Obtainable under the rule | Flagged | Outdated final hop | Outdated intermediate hop |
|---|---:|---:|---:|---:|---:|
| MH 6K | 100 | 96 | 4 | 2 | 2 |
| MH 32K | 100 | 87 | 13 | 3 | 10 |
| MH 64K | 100 | 90 | 10 | 6 | 4 |
| MH 262K | 100 | 66 | 34 | 16 | 18 |
| SH 6K | 100 | 100 | 0 | 0 | |
| SH 32K | 100 | 98 | 2 | 2 | |
| SH 64K | 100 | 98 | 2 | 2 | |
| SH 262K | 100 | 97 | 3 | 3 | |

Multi-hop over the four lengths: 339 of 400. Single-hop: 393 of 400. Of the 68 flagged items the reader marked 63
`CONFIRMED` and 5 `PROBABLE` (the question wording does not name every relation of the only path to the released answer).

"Obtainable" is an upper bound for a rule-following reasoner: some path that uses the current value at every hop
reaches the released answer. It does not require that the path matches the wording of the question.

## Why an answer gets flagged

The context joins many MQuAKE cases. A released answer follows the edits of its own case, while another case in the same
context overwrites a fact on its chain with a larger serial number. Two examples from MH 262K, quoting the benchmark:

- Question 9 asks for the creator of the official language of the headquarters city of a football club. The chain
  reaches Esperanto. Sentence 1514 says Esperanto was created by L. L. Zamenhof; sentence 8023 says it was created by
  Frank Miller. The released answer is L. L. Zamenhof.
- Question 8 asks for the school of the author of "Measure for Measure". Sentence 13949 gives William Shakespeare as the
  author; sentence 14943 gives Terrance Dicks. The released answer is Shakespeare's school; no school is stated for
  Terrance Dicks.

## A check that does not depend on reading questions

Inside one context, the released answers of different questions need different values for the same key, so no single
state of the facts satisfies all of them.

| Context | Keys used with two values | Questions involved |
|---|---:|---:|
| 6K | 4 | 10 |
| 32K | 6 | 13 |
| 64K | 3 | 7 |
| 262K | 5 | 17 |

For example, in the 6K context one released answer needs "Henri Grégoire is a citizen of India" and another needs "of
France". The examples are in [`results.json`](results.json).

## Method

1. Grammar: the 36 MQuAKE cloze templates that occur in the contexts, plus the generic template "The <office> is
   <person>.". It parses all 25,677 numbered sentences of the four contexts; none is left unparsed.
2. Anchors: subjects that occur literally in the question, longest match first.
3. Multi-hop: all simple paths of at most 4 hops from an anchor to a released answer over any historical value. An item
   is `CONSISTENT` if some path uses the current value at every hop, otherwise `SUPERSEDED_FINAL_HOP` (only the last
   value is outdated) or `SUPERSEDED_INTERMEDIATE_HOP`.
4. Single-hop: the released answer must be the current value of some key of the anchor (`SUPERSEDED_VALUE` otherwise).
5. For each flagged item the rule-consistent answer is computed by following the same relations with current values. For
   18 of the 61 multi-hop items the chain ends early, because the current intermediate entity has no such fact.

All 800 questions had an anchor and at least one path.

## Relation to published reports

The Contract Memory Compiler paper (arXiv:2609.32658, App. B.3) reports an automated screen that flags 7 single-hop and
26 multi-hop references as possibly superseded and leaves them for manual adjudication. This screen finds the same
single-hop count and 27 multi-hop items of that kind (outdated final hop), and adds 34 multi-hop items with an outdated
intermediate hop. Whether the items are the same as theirs was not checked. The current version of arXiv:2606.01435
reports 41% multi-hop accuracy at 262K with gpt-4o, and the Contract Memory Compiler paper 61.0%; both are below the
66 obtainable answers counted here.

## Effect on the project's own 262K runs

The structured-memory runs of draft pull request #105 scored 55 and 59 of 100 on the released multi-hop labels at 262K
(local `qwen2.5:14b-instruct` and DeepSeek Flash). All of those correct answers are among the 66 unflagged questions.
On the 34 flagged questions both runs score 0 by construction. Where a rule-consistent answer exists (23 items) the
runs return it in 17 and 21 cases. This is a re-scoring against the screen's own adjudication. It is not an official
score and it does not change the result recorded in that pull request.

## Files

- [`summary.json`](summary.json): per-variant class counts and grammar coverage.
- [`results.json`](results.json): flag counts, the contradiction table with examples, the re-scoring above.
- [`flagged-items.jsonl`](flagged-items.jsonl): the 68 flagged items as variant, question index, class, verdict,
  relation path and the serial numbers of the outdated and the current sentence. It carries no question or answer
  text; with the benchmark file the sentences can be looked up by serial number.
- Code: [`../../../scripts/mab_fc_label_screen_v1.py`](../../../scripts/mab_fc_label_screen_v1.py),
  [`../../../scripts/mab_fc_label_adjudicate_v1.py`](../../../scripts/mab_fc_label_adjudicate_v1.py), tests in
  [`../../../tests/test_mab_fc_label_screen_v1.py`](../../../tests/test_mab_fc_label_screen_v1.py).

Kept outside the repository, because they quote benchmark questions and answers in bulk or belong to a decision not
taken: the per-item file with full text and paths (SHA-256 `94f49db82f659b9faf5bd1a13d2a0ec32d22bec265ea9be2a79c5d213c4637ce`),
the adjudication file with text (`9f62940884e2528cf705cae021e2a9584f57d406af45b138fb0610b540abe6f1`), the two review
listings, and an unposted draft of a report to the benchmark's maintainers.

## Reproduce

Download the `Conflict_Resolution` parquet of `ai-hyz/MemoryAgentBench` (MIT licence; the file used here has SHA-256
prefix `24d5c3f0` and suffix `a5ff45`). Python 3.12 and `pyarrow` are needed.

```text
python scripts/mab_fc_label_screen_v1.py --parquet PATH --out DIR
python scripts/mab_fc_label_adjudicate_v1.py --parquet PATH --dir DIR
```

`DIR` should be outside the repository. On 2026-11-12 the two commands reproduced the six original output files byte for
byte, including the hashes above. The re-scoring of the project runs needs `--prepared` and `--runs`, which point at
private artifacts of pull request #105.

## Limits

- One AI reader adjudicated the flags. Treat the 68 as candidates.
- Only the released parquet was examined. The MQuAKE source cases and MQuAKE-Remastered were not consulted.
- If the intended semantics is that each answer follows only the edits of its own case, the released labels are correct
  by construction. They then cannot be derived from the context, and the contradictions above remain.
- The verdicts for five items were entered by hand in the adjudication script after reading the review listings.
