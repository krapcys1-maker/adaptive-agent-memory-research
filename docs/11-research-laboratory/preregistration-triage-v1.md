# Preregistration triage v1

Applies the selection rule from [`operating-doctrine.md`](../00-project/operating-doctrine.md) to all 21 registry rows sitting at `preregistration-draft`.

Nothing is deleted. A retired or reclassified preregistration stays in the registry as a labelled record.

## The finding that reframes the backlog

The blocker was never independent review.

```
development_set built        :  0 / 21
requires a reader model      : 18 / 21
requires an independent judge:  4 / 21
```

Every one of the 21 lacks a corpus. Eighteen additionally need a frozen reader model, which means API budget. Independent review blocks only four, and for those it is the *second* blocker behind the missing corpus.

This matters because the project has spent months treating reviewer scarcity as the constraint. It is not. **The constraint is that no corpus exists**, and corpora are authored work that needs no reviewer to begin.

## The unit of work is the corpus, not the experiment

The 21 drafts are not 21 independent pieces of work. They cluster into four families that would each share one corpus, plus four standalone items.

| Family | Experiments | Count | Shared need |
|---|---|---|---|
| **REV** revision and time | V0, V1, V2, V3 | 4 | temporal corpus with supersessions and corrections |
| **COMP** compaction | C1, C2, C3, C5, C6, C7 | 6 | multi-cycle compaction corpus plus reader |
| **REPLAY** | R1, R2, R3, R4 | 4 | episode corpus with outcomes plus reader |
| **FORG** forgetting | F3, F4, F5 | 3 | interference corpus plus reader |
| standalone | BIO-SAVINGS, NATURAL-COMP, ROUTER, BTA-PROS | 4 | each its own |

Building four corpora would unblock sixteen experiments. Treating them as twenty-one separate items is why none moved.

## Classification

### Execute now — 1

**`PMLAB-REV-V0-001` Deterministic temporal basis and historical reconstruction.**

The only draft requiring neither a reader model nor an independent judge. Its arms are `one-time`, `append-only`, `valid-only`, `transaction-only`, `bitemporal`, `bitemporal-causal`, `oracle`, and its threshold is zero critical future leakage, no silent concurrent winner, and exact pre-correction reconstruction.

Three things make it the right pick under the doctrine:

1. **It can run today.** Deterministic arms, mechanical gold, no model, no budget.
2. **A corpus already exists in usable form.** `memory/events.jsonl` carries 182 events with 8 real supersessions, genuine corrections, and transaction timestamps produced by actual use rather than authored for a benchmark.
3. **It answers a question already in the issue tracker.** #29 records that the memory schema has no valid time, so recording that a fact changed necessarily hides the fact that was true before it. V0 is the registered experiment for exactly that.

It also sequences three others: V1, V2 and V3 all assume a temporal basis that V0 establishes.

### Blocked on corpus and budget — 16

`COMP-C1, C2, C3, C5, C6, C7` · `REPLAY-R1, R2, R3, R4` · `FORG-F3, F4, F5` · `REV-V1, V2, V3`

Named dependency: an authored corpus, and for all but REV-V1–V3 a frozen reader model with a registered API cap.

Independence tier genuinely required: **I1 sealed split** for the corpus, not I5. None of these needs an expert reviewer to start; they need someone to build the fixture.

Status changed from `preregistration-draft` to `blocked-corpus-not-built` so the registry stops implying they are merely waiting their turn.

### Blocked on independent review — 4

`BIO-SAVINGS-001` (independent action-label review) · `NATURAL-COMP-001` (independent obligation and scope adjudication) · `ROUTER-001` (independent critical labels) · `BTA-PROS-001` (independent intention and opportunity validity)

These are the only four where a human judgement gate is real. Even here the corpus is missing first, so the reviewer is not yet the binding constraint.

Under the independence ladder, three of the four may be decomposable into I4 micro-tasks rather than needing I5. That is worth checking before recruiting anyone.

### Retired — 0

No draft was retired. Each still addresses one of the five research questions, and none is superseded by a completed result. Retirement stays available and would be recorded, not deleted.

## Effect on the work-in-progress limit

The doctrine sets a limit of two experiments per track in "designed, not executed". The backlog was 21 against a limit of 2.

After triage, "designed and ready" is **1** — `REV-V0-001`. The other 20 carry an explicit named blocker and no longer count as work in progress, because nobody can start them.

That is the honest reading: the queue was never 21 items of pending work. It was one executable item and twenty missing fixtures.

## Next actions

1. Build the `REV-V0` corpus from `memory/events.jsonl` and execute it as Tier E.
2. Check whether `NATURAL-COMP`, `ROUTER` and `BTA-PROS` decompose into I4 micro-tasks.
3. Pick **one** corpus family and build its fixture. REV is already half-built by V0; COMP and REPLAY both need a reader and therefore budget.
4. Do not add a new preregistration until at least one family has an executed result.
