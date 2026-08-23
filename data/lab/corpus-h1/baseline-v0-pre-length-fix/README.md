# The run that found the length confound

Kept because it is the evidence, not because it is a result.

This is `PMLAB-H1-BASE-E1` executed against the **first** version of corpus H1,
before the length confound was found and repaired. Its numbers are superseded.
It is preserved because the corpus was changed after this run, and a corpus
changed in response to a measurement must show the measurement that caused it.

## What it reported

```
recall@1   0.190   intrusion@1   0.000
recall@5   0.667   intrusion@5   0.167
recall@10  0.929   intrusion@10  0.250

forbidden outranks gold   0.000   over 48 probes
```

Two things in that are wrong, and only one of them looks wrong.

**`forbidden_above_gold` was a constant zero across all 48 probes.** The
forbidden record was retrieved a quarter of the time and never once outranked
the gold. A perfect score on the metric a benchmark is built around is the same
signal `PMLAB-DECORR-E1` ran into: a constant vector means the instrument is not
measuring, not that the system is perfect.

**`recall@10` of 0.929 for a plain OR-of-terms BM25 arm was too good.** A corpus
a lexical index answers nine times in ten cannot separate compaction arms.

## The cause

The gold event was systematically longer than the forbidden one:

```
OBSOLETE   gold longer in 12/12
RARE-EXC   gold longer in 12/12
FAILFIX    gold longer in 12/12
POISON     gold longer in  0/12
```

Every family with a forbidden event was perfectly predicted by length, in one
direction or the other. Under BM25 with an OR of query terms, a longer document
matches more terms, so an arm could score by preferring long events and never
read one. **The corpus was measuring document length wearing the costume of a
memory benchmark.**

## The repair, and the two attempts that failed

The first attempt hand-balanced the texts — lengthening the terse ones,
trimming the verbose. The confound inverted rather than disappearing: `12/12`
became `0/12`. A fixed template gives a fixed length relationship no matter how
the surface varies.

The second attempt appended a content-neutral elaboration on a coin flip drawn
from the seed, independently for gold and forbidden. That fixed `OBSOLETE` and
`FAILFIX` and left `POISON` and `RARE-EXC` still perfect, because their base
length gap was larger than any elaboration could bridge.

The third worked: close the base gap *and* elaborate independently, so length is
uncorrelated with which record is gold rather than merely equal on average.

```
OBSOLETE   gold longer in  5/12
RARE-EXC   gold longer in  8/12
FAILFIX    gold longer in  4/12
POISON     gold longer in  6/12
```

`tests/test_history_family_construction.py::test_gold_is_not_systematically_longer_than_its_forbidden_event`
now fails on any perfect split in either direction, so this defect class cannot
return silently.

## What changed in the numbers

| | pre-fix | post-fix |
|---|---:|---:|
| recall@10 | 0.929 | 0.810 |
| forbidden outranks gold | 0.000 | 0.083 |
| OBSOLETE recall@10 | 1.000 | 0.167 |
| POISON forbidden outranks gold | 0.000 | 0.250 |

The `OBSOLETE` collapse is the family working as specified: the obsolete host is
now stated three times over eleven days and the correction once, tersely, so
frequency, establishment and length all point the wrong way. That is what the
family claimed to measure and previously did not.

## The honesty problem, stated plainly

The corpus was modified after a baseline was run against it. That is tuning
unless the reason is independent of the score, so here is the reason: a
benchmark in which document length predicts the answer measures length. The
repair would have been correct had the baseline never run, and it was not
selected to make any arm look better or worse — no arm exists yet.

Both runs are kept. If a later reader thinks the change was self-serving, the
before, the after, and the diagnosis are all here to argue with.
