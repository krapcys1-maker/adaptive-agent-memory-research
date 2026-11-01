# Corpus H1 lexical baseline, re-run on the current corpus (2026-11-01)

`baseline-v0/results.json` was written by commit `a145004` (2026-08-23T17:39:13+03:00; the same commit also
holds `baseline-v0-pre-length-fix/`, the run before a length confound was repaired, so `baseline-v0` is itself a
second run). The corpus inputs were changed afterwards, and exactly one of those changes alters the script's
output: `cd5c3f4` (18:13:06+03:00, "Fix three corpus defects the first paid probes exposed") rewrote
`prefix-v0/history.jsonl` and `reveal-v0/queries.jsonl`. `reveal-v0/gold.jsonl` also changed in `3bcc899`
(before `cd5c3f4`), `cd5c3f4`, `07ece00` and `6e0fe2f`. The baseline was not re-run after `cd5c3f4`, so
`baseline-v0/results.json` describes the corpus as it stood before that repair. It is left exactly as it was.

This directory holds the same, unchanged script run on the current corpus:

```bash
python scripts/run_corpus_h1_baseline.py --out data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01
```

**Always pass `--out`.** Without it the script writes to `data/lab/corpus-h1/baseline-v0/` and would overwrite the
original that this directory exists to protect; the corpus README still documents the command without `--out`.

The output is byte-identical across runs (two runs compared) and contains no timestamps or absolute paths.

## What changed

Of the 1,142 values in each `results.json`, 334 differ. Recall at k = 1, 5 and 10 per family (earlier corpus → this
re-run), and the mean number of whitespace tokens that enter the prompt at k = 1:

| family | recall@1 | recall@5 | recall@10 | mean tokens at k = 1 |
|---|---|---|---|---|
| BILINGUAL | 0.083 → 1.000 | 0.417 → 1.000 | 0.833 → 1.000 | 15.0 → 17.0 |
| DELAYED | 0.083 → 1.000 | 0.417 → 1.000 | 0.833 → 1.000 | 37.0 → 39.0 |
| FAILFIX | 0.083 → 0.583 | 0.417 → 1.000 | 0.833 → 1.000 | 27.0 → 27.3 |
| OBSOLETE | 0.000 → 0.000 | 0.000 → 0.000 | 0.167 → 0.167 | 12.7 → 13.3 |
| POISON | 0.167 → 1.000 | 1.000 → 1.000 | 1.000 → 1.000 | 23.8 → 32.4 |
| RARE-EXC | 0.583 → 0.917 | 1.000 → 1.000 | 1.000 → 1.000 | 20.2 → 20.2 |
| REDERIVE | 0.167 → 1.000 | 0.833 → 1.000 | 1.000 → 1.000 | 7.5 → 10.4 |
| all 84 probes | 0.167 → 0.786 | 0.583 → 0.857 | 0.810 → 0.881 | 20.4 → 22.8 |

How often a forbidden event outranks the gold event (48 of the 84 probes have a forbidden event; BILINGUAL, DELAYED and
REDERIVE have none): overall 0.0833 → 0.0000; OBSOLETE 0.0833 → 0.0000; POISON 0.2500 → 0.0000 (3 of 12 → 0 of 12);
FAILFIX and RARE-EXC 0.0000 in both.

## Why (tested, not assumed)

The script has one commit in its history (`a145004`) and did not change. We ran it on `git archive` snapshots of
`data/lab/corpus-h1` at five commits:

| snapshot | output |
|---|---|
| `a145004` (17:39) | identical to `baseline-v0/results.json`, byte for byte |
| `3bcc899` (18:00) | identical to `baseline-v0/results.json` |
| `cd5c3f4` (18:13) | identical to this re-run, byte for byte |
| `07ece00` (18:17) | identical to this re-run |
| `6e0fe2f` (18:34) | identical to this re-run |

So the difference comes from the corpus repair in `cd5c3f4`, not from the script or the platform; the three
gold-only changes do not alter the output. Before `cd5c3f4` the 84 probes asked only 24 distinct question texts
(BILINGUAL, DELAYED and FAILFIX 1 of 12; REDERIVE 2 of 12; POISON 4 of 12; RARE 7 of 12; OBSOLETE 8 of 12); afterwards
all 84 are distinct. The commit message gives the same reason: "A probe that does not identify its own case is
unanswerable by construction". To repeat the test:

```bash
git archive a145004 data/lab/corpus-h1 | tar -x -C <empty directory>
python scripts/run_corpus_h1_baseline.py --corpus <empty directory>/data/lab/corpus-h1 --out <a new directory inside this repository>
cmp <that directory>/results.json data/lab/corpus-h1/baseline-v0/results.json
```

(The script reports an error after writing its output when `--out` is outside the repository; keep `--out` inside it.
Delete the directory afterwards; do not commit it.)

## Reading

The README's former headline, that recall@10 is perfect for the poisoned-instruction family while the poisoned line
outranks the genuine rule in 25% of probes, does not hold on the repaired corpus: it is 0 of 12. The 25% was measured
on a probe set in which the 12 poisoned-instruction probes asked 4 distinct questions, so it describes that probe set,
not retrieval. Every `baseline-v0` figure was measured on the earlier probe set, including the low recall@1 and
recall@5 of DELAYED and REDERIVE (0.083 and 0.417 for DELAYED; both are 1.000 on the repaired corpus).

Do not cite the 25% as a result about retrieval. Authority is unchanged from `baseline-v0`: a development
measurement of one lexical arm on one synthetic corpus, with no independent review.
