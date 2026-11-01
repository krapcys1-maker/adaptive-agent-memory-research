# Temporal Anchor, Restricted to TEMPORAL_BOUNDARY — Confirmatory Test v3 ("Mechanism I")

Preregistration: `PM-20260824-717e8277`. **Verdict: `MECHANISM_I_FAIL` on the replication gate — mechanism NOT elevated to `REPLICATED_VALIDATED_TRANSPLANT`.** Third consecutive Campaign V2 mechanism-family failure (G, H, I) — triggers the contract's **3-consecutive-failure strategy-pivot condition**: STOP the current candidate-selection strategy, return to external discovery to rebuild the candidate pool. Not a global stop.

## Mechanism and why this test

`TEMPORAL_ANCHOR_AT_CONTEXT` (render each retrieved fact as `[YYYY-MM-DD] {fact}`) is not dropped — Ledger Entry A's status is `SUPPORTED, qualified`. E1 showed a real positive effect; Stage 2's fresh 10-unit replication failed its own overall gate (net −1) but showed a clean, unbroken 2/2 positive signal specifically within the `TEMPORAL_BOUNDARY` (duration/arithmetic between two named events) sub-regime, with 0 regressions in that bucket — all 3 of Stage 2's regressions occurred outside it. This test gives that narrower regime its own dedicated, gold-blind confirmatory replication, using a fixed regex classifier (`is_temporal_boundary()`) applied to question text only, structurally excluding the many-item filter/count shape responsible for Stage 2's one clear negative-transfer case.

## Results

8/8 fresh, gold-blind units, all classified `TEMPORAL_BOUNDARY` (`data/lab/arena/temporal-anchor-boundary-v3/selection.json`). **Net repairs: 0. Regressions: 0. Effect: NULL** — `+TIME` is byte-for-byte judgment-identical to `BASE` on all 8 units.

| unit | BASE | +TIME |
|---|---|---|
| `b3c15d39` | OK | OK |
| `60bf93ed` | OK | OK |
| `b46e15ed` | WRONG | WRONG |
| `bbf86515` | WRONG | WRONG |
| `c8090214` | OK | OK |
| `a3045048` | OK | OK |
| `6613b389` | OK | OK |
| `8c18457d` | OK | OK |

## The two BASE-wrong units, examined — retrieval absence, not a date-rendering failure

**`b46e15ed`** — "how many months since two charity events on consecutive days" (gold: 2 months). `+TIME`'s dates are real and were **used, correctly**: the reader identifies two same-day events (`2023-02-15`) and correctly reasons they were on the *same* day, not consecutive ones — a traceable, sound use of the rendered anchors that `BASE` couldn't attempt at all. Neither arm's top-10 contains the actual consecutive-day pair the gold answer needs — that pair was never retrieved into context at all. `+TIME` gives a strictly *more precise* non-answer than `BASE`'s vague one (ruling out a real near-miss candidate rather than just declining), though both are scored `WRONG`. This is a retrieval-absence failure the mechanism structurally cannot fix, not a defect in the mechanism itself.

**`bbf86515`** — "days before Rack Fest did I attend Turbocharged Tuesdays" (gold: 4 days). Neither arm's context mentions "Turbocharged Tuesdays" anywhere — a clean total retrieval miss, unrelated to date rendering. Separately notable: all 10 `+TIME` items in this unit render the *same* date, `[2023-06-28]` — a single later recap session recalling several distinct earlier events (one fact's own in-text date, "Attended Rack Fest... on June 18th," diverges from its rendered `2023-06-28` session anchor) — structurally the exact `SESSION_EVENT_DIVERGENT` pattern behind Stage 2's one regression (`00ca467f`, Ledger Entry B). It occurred here too, on a question shape the classifier could not have excluded (the divergence is a retrieval-time property, not detectable from question text alone) — but caused **no new harm**, because the underlying retrieval miss ("Turbocharged Tuesdays" absent entirely) already made this unit unanswerable regardless of date rendering.

## Classification

Both failures are retrieval-absence, not temporal-representation problems — the same subtype-mismatch pattern already documented for Mechanism H. The known `SESSION_EVENT_DIVERGENT` trap (Entry B) recurred structurally in `bbf86515` but produced no measurable harm this time, because it was swamped by a total retrieval miss. Across three independent AAMR samples now (E1, Stage 2's `TEMPORAL_BOUNDARY` bucket, this v3 test), the mechanism has **never caused a regression on a unit within its stated positive regime** — its safety is more strongly confirmed than ever, even though replication-scale efficacy (≥2 net repairs) remains unconfirmed, because none of the 10 wrong units seen across these regime-scoped tests (2 here + the earlier 2 in Stage 2's own bucket, which *did* flip) has yet supplied a clean "dates present, simply not rendered" opportunity outside Stage 2's original 2 cases.

## Verdict and campaign consequence

**`MECHANISM_I_FAIL`** on the preregistered gate (0 net repairs, required ≥2). Not a negative result — 0 regressions, and the one structural recurrence of the known divergent-anchor trap caused no harm — but the gate is honored literally rather than re-litigated, per this project's standing discipline.

`TEMPORAL_ANCHOR_AT_CONTEXT` remains `SUPPORTED, qualified` (Ledger Entry A) — this test neither strengthens nor weakens that status; it adds a third clean-null data point and reconfirms the regime is narrower even than "duration/arithmetic by question shape" — it also needs the specific dated pair or event to have actually been retrieved, a precondition orthogonal to date rendering.

This is Campaign V2's **3rd consecutive mechanism-family failure** (G: `SECOND_HOP_ASSOCIATIVE_EXPANSION`; H: `HYDE_QUERY_REFORMULATION`; I: this test) — regardless of selection strategy (G/H came from external discovery, I came from AAMR-internal evidence). Per the contract's explicit STOP semantics: **3 consecutive mechanism failures → STOP the current candidate-selection strategy → return to external discovery to rebuild the candidate pool.** This is *not* a global stop (no 2 validated mechanisms + interaction test done, budget far from exhausted at $1.410904/$5.00, no validity/contamination failure, testable candidates still exist, cost accounting reliable, no destructive/security blocker) — the campaign continues, but the next step is a fresh discovery pass rather than another ad hoc pick.

## Cost

$0.559315 (8 units ingested, 372 sessions; reader+judge on 2 arms negligible on top of ingest). One benign transient "Invalid JSON response" ingest warning, same pattern as every prior run. 2 units `UNOBSERVABLE` contamination (consistent prior rate), 0 `FAIL`.
