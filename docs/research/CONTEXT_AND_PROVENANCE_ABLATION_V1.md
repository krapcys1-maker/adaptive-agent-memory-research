# Context and provenance ablation, v1

`arena-context-ablation-v1` · frozen manifest
[`data/lab/arena/mechanism-ablation.json`](../../data/lab/arena/mechanism-ablation.json) ·
machine-readable result
[`data/lab/arena/context-ablation-report.json`](../../data/lab/arena/context-ablation-report.json)

**New spend: $0.0288 of a $0.50 cap.** No ingest, no retrieval, no new benchmark
units, no change to either system, no change to the reader.

---

## 1. The question

The fixed-reader run left one thing unexplained. Hindsight hands the reader about
thirty times more context than Mem0 and answers 7 of 10 against 4 — but Mem0 puts
the gold session at **rank 1** in eight of nine observable units. So the advantage
is not retrieval accuracy. Four candidates:

```
H1  volume: more context is simply worth more
H2  a different kind of information in what Hindsight returns
H3  raw provenance that Mem0's compaction discards
H4  some combination
```

Two ablations separate them, and each changes exactly one thing.

## 2. Frozen inputs

| | |
|---|---|
| selection | `arena-expansion-v1`, sha256 `a4d252f1…`, 10 units |
| Mem0 contexts | `raw/arena-expansion-v1/mem0.json`, sha256 recorded in the manifest |
| Hindsight contexts | `raw/arena-expansion-v1/hindsight.json`, likewise |
| reader | identical to `arena-fixed-reader-v1`: same model, prompt hash, `temperature=0`, `max_tokens=300` |
| judge | LongMemEval `evaluate_qa.py` @ `9e0b455f`, empty-response guard, two passes |
| token unit | whitespace-split words, the unit `context_tokens` already used |

**Truncation rule, fixed before any call:** whole evidence items, original order,
added while the next still fits. No re-ranking, no summarising, and **no item
chosen using the gold answer** — the only way a context-size curve can mean
anything.

**Provenance rule:** the raw source session whose *date* matches Mem0's top-1
retrieved memory, verbatim. Session date is the only key; a unit whose haystack
repeats a date is `UNOBSERVABLE`, not guessed. One unit is.

## 3. Experiment A — Hindsight context-size curve

| Variant | mean tokens | gold retained | correct | accuracy |
|---|---|---|---|---|
| Hindsight @ Mem0's budget | 102.0 | 7/9 | **4/10** | 0.40 |
| Hindsight @ 500 | 499.3 | 8/9 | **6/10** | 0.60 |
| Hindsight @ 1000 | 997.8 | 8/9 | **6/10** | 0.60 |
| Hindsight full | 3116.8 | 9/9 | **7/10** | 0.70 |
| *question only* | 0 | — | 0/10 | 0.00 |

**At Mem0's own per-probe token budget, Hindsight scores exactly 4/10 — the same
as Mem0.** The advantage disappears at equal context size and returns as the
budget grows.

Accuracy is monotone in the budget, and in this ablation the budget is the only
thing that varies. That is causal evidence for context breadth **on this frozen
sample** — not a general law, and not a claim that volume is what a memory
system should optimise.

Most of the gain arrives by 500 tokens. 500 and 1000 are identical at 6/10, so
there is a plateau in that region; the tenth unit only lands at full breadth.

## 4. Experiment B — Mem0 raw-provenance fallback

| Variant | mean tokens | correct | accuracy |
|---|---|---|---|
| Mem0 compact | 105.6 | 4/10 | 0.40 |
| Mem0 compact + top-1 raw provenance | 2265.7 | 4/9 | 0.44 |
| Mem0 top-1 raw provenance only | 2158.6 | 3/9 | 0.33 |

```
COMPACT_WRONG_RAW_FIXES   0
RAW_CAUSES_REGRESSION     0
```

**Zero.** Appending the entire raw source session behind Mem0's top-1 hit — about
2,150 words of verbatim conversation — repairs none of its failures and breaks
none of its successes. The same four probes are right in both arms.

**H3 is refuted on this sample.** Mem0's problem is not that compaction discarded
the passage its top hit came from.

Raw-only scores lower (3/9) than compact or compact+raw (4/9 each), so the
compact memory is contributing something the raw session does not. Compaction is
not merely lossy here; it is doing work.

## 5. Per-probe

| Probe | Type | H@Mem0 | H@500 | H@1000 | H full | M compact | M +raw | M raw only |
|---|---|---|---|---|---|---|---|---|
| short | multi-session | no | no | no | no | no | no | no |
| medium | temporal | **yes** | **yes** | no | **yes** | no | no | no |
| long | single-session-user | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** |
| update | knowledge-update | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** |
| temporal-reasoning-1 | temporal | no | **yes** | **yes** | **yes** | no | no | no |
| temporal-reasoning-2 | temporal | no | no | no | no | **yes** | **yes** | no |
| knowledge-update-1 | knowledge-update | no | **yes** | **yes** | **yes** | **yes** | **yes** | **yes** |
| knowledge-update-2 | knowledge-update | no | no | no | no | no | ? | ? |
| multi-session-1 | multi-session | no | no | **yes** | **yes** | no | no | no |
| single-session-user-1 | single-session-user | **yes** | **yes** | **yes** | **yes** | no | no | no |

`?` = provenance unobservable for that unit.

One non-monotonicity is visible and is not smoothed over: `medium` is answered at
102 and 500 tokens, missed at 1000, and answered again at full. With one
generation per context that single cell is **noise until replicated**, and it is
marked as such rather than explained.

## 6. Failure decomposition

```
GOLD_DROPPED_BY_BUDGET       4    truncation cut the gold evidence out
GOLD_PRESENT_READER_WRONG   10    it survived and the answer still fell
```

The second number is more than twice the first. Even inside the truncation curve,
losing the gold is the *minority* failure — having it is not sufficient, which is
the same conclusion the ten-unit run reached and this experiment does not
overturn.

## 7. What changed against the previous interpretation

The earlier reading was *retrieval is not the bottleneck, and volume appears to
matter*. The first half stands. The second half now has controlled support and a
sharp boundary:

- **Breadth is causal here.** Hindsight at Mem0's budget is Mem0's score.
- **Provenance is not the mechanism.** The single most obvious explanation for
  Mem0's rank-1-and-still-wrong failures — that compaction threw away the
  supporting passage — is refuted at zero repairs out of nine.
- **Compaction is not simply lossy.** Raw-only is worse than compact.

So H1 has evidence, H3 is out, and H2 remains untested: 500 tokens of Hindsight
already beats 106 tokens of Mem0, which *could* be breadth alone or could be that
Hindsight's items differ in kind. This ablation cannot separate those, because it
never varied Mem0's breadth.

## 8. Promotion

**`BROAD_CONTEXT_EXPANSION` — PROMOTE to an isolated test.**

PROMOTE means *the most justified next mechanism to test in isolation*, not
proven. It is chosen over the alternatives because it is the only one with
controlled evidence: a monotone curve where the budget was the sole variable.

- `RAW_PROVENANCE_EXPANSION` — **DROP** as the next candidate. Zero repairs.
- `COMPACT_CONTEXT_EXPANSION_AT_SATURATION_POINT` — **HOLD.** The 500/1000
  plateau suggests a cheap operating point but rests on two arms of ten probes.
- Temporal/state mechanisms — **HOLD**, untouched by this experiment.

## 9. Cheapest next falsifying experiment

**Expand Mem0's own breadth and see whether it climbs the same curve.** Mem0
returns `limit=10`; its persisted stores hold 221–387 items per unit. Re-querying
Mem0 at k=50 and k=150 with no other change, then the same reader and judge,
costs roughly **$0.05** — query is free for Mem0 and only the reader and judge
are paid.

It falsifies cleanly. If Mem0 at 3,000 tokens reaches ~7/10, the mechanism is
breadth and H2 is dead. If it stays at 4/10 with the same budget Hindsight
succeeds at, then breadth is not sufficient and the difference is in the *kind*
of item each system stores — which would make H2 the live hypothesis and point at
what to read in the code.

This requires re-running Mem0's retrieval, which the current instruction
forbids, so it is proposed and not started.
