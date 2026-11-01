# Corpus H1 lexical baseline, re-run on the current corpus (2026-11-01)

`baseline-v0/results.json` was written by commit `a145004` (2026-08-23T17:39:13+03:00). The corpus inputs it
reads were changed afterwards: `prefix-v0/history.jsonl` and `reveal-v0/queries.jsonl` by `cd5c3f4`
(18:13:06+03:00, "Fix three corpus defects the first paid probes exposed"), and `reveal-v0/gold.jsonl` several
times after that. The baseline was never re-run, so `baseline-v0/results.json` describes an earlier corpus.
It is left exactly as it was.

This directory holds the same script run on the current corpus:

```bash
python scripts/run_corpus_h1_baseline.py --out data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01
```

The output is byte-identical across runs (two runs compared) and contains no timestamps or absolute paths.

| measure | `baseline-v0` (earlier corpus) | this re-run (current corpus) |
|---|---|---|
| overall recall@10 | 0.8095 | 0.8810 |
| overall: forbidden outranks gold | 0.0833 | 0.0000 |
| BILINGUAL recall@10 | 0.8333 | 1.0000 |
| DELAYED recall@10 | 0.8333 | 1.0000 |
| FAILFIX recall@10 | 0.8333 | 1.0000 |
| FAILFIX forbidden outranks gold | 0.0000 | 0.0000 |
| OBSOLETE recall@10 | 0.1667 | 0.1667 |
| OBSOLETE forbidden outranks gold | 0.0833 | 0.0000 |
| POISON recall@10 | 1.0000 | 1.0000 |
| POISON forbidden outranks gold | 0.2500 | 0.0000 |
| RARE-EXC recall@10 | 1.0000 | 1.0000 |
| RARE-EXC forbidden outranks gold | 0.0000 | 0.0000 |
| REDERIVE recall@10 | 1.0000 | 1.0000 |

## Reading

The README's former headline, that recall@10 is perfect for the poisoned-instruction family while the poisoned
line outranks the genuine rule in 25% of probes, does not hold on the current corpus: it is 0 of 12. The likely
cause is the corpus repair in `cd5c3f4`, which changed the probes after the baseline was written. That is an
explanation, not a finding; it has not been tested by re-running the script on the earlier corpus.

Do not cite the 25% as a result about retrieval. Authority is unchanged from `baseline-v0`: a development
measurement of one lexical arm on one synthetic corpus, with no independent review.
