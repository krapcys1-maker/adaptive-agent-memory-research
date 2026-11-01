# Temporal Anchor Fresh Replication v1 (Stage 2)

Full structured data: [`data/lab/arena/stage2-fresh-replication/stage2-analysis.json`](../../data/lab/arena/stage2-fresh-replication/stage2-analysis.json).
Predictions pre-registered before ingest: `PM-20260824-eb86fcf3`. Prior E1 result (still valid, not superseded): `PM-20260824-2d603195`.

## Epistemic key

**MEASURED** / **CODE_VERIFIED** / **INFERENCE** / **HYPOTHESIS** / **UNRESOLVED**, never mixed.

## Question

Does `TEMPORAL_ANCHOR_AT_CONTEXT` — rendering each retrieved Mem0 fact as `[YYYY-MM-DD] {fact}`, date from the item's own positionally-aligned session timestamp, nothing else changed — replicate on 10 fresh units never used anywhere in this arena before?

## Selection — MEASURED, gold-blind

10 units, excluding all 10 previously-used question_ids and every `_abs` variant. Fixed keyword/question_type classifier applied to all 490 fresh candidates before any individual inspection (`data/lab/arena/stage2-fresh-replication/stage2-selection.json`, `selection_sha256=79427d30d5c5a1787ca4a78916c0b6731f8cc26d8422deeaac54ac653eb55fe3`). Mix: 5 `TEMPORAL_POSITIVE`, 2 `TEMPORAL_BOUNDARY`, 3 `NON_TEMPORAL_CONTROL` (70/30). Three documented imperfect fits recorded at freeze time, not discovered post-hoc.

## A bug caught before it cost anything further

The first contamination-audit run flagged `0977f2af` and `0bb5a684` as FAIL. Investigation (before any reader/judge call) found this was a false positive in the new audit script: both units' own `haystack_dates` are non-unique, so `session_map()` correctly returns `None` and `gold_state()` takes the `UNOBSERVABLE` branch — which carries no `foreign_from_other_units` key. The check compared that missing key against `== 0`, reading `None == 0` as a failure. Fixed per the bug-discipline protocol: regression tests added (`tests/test_stage2_contamination_audit.py`, 4 tests, confirmed passing against the fix), `contamination_status()` extracted as a named function distinguishing `PASS`/`FAIL`/`UNOBSERVABLE`. Re-run: **RESET: PASS. CONTAMINATION: PASS** (2 units correctly reported `UNOBSERVABLE`, not counted as failures — the same condition documented throughout this project for `69fee5aa` in the original 10-unit set).

## Ingest and contamination audit — MEASURED

10/10 units complete. `store_before_reset == store_after_reset == 0` for every unit. Stored items 199–248 (consistent with the original 10 units' 201–272 range). Cost: **$0.715117** (813 provider calls), closely matching the pre-call projection of $0.7161.

## Reader and judge — MEASURED

Single operating point (wide, `deep_limit=400`, `truncate()` to a 3000-token budget — unmodified from the E1/original-10 construction). Same frozen reader (`fixed_reader.py`, unchanged hash), same frozen judge protocol (`judge_pilot.py`, unchanged hash), 2 passes + 3rd on disagreement — 20/20 stable, 0 disputed.

## Results

| | score |
|---|---|
| BASE | **7/10** |
| `+TIME` | **6/10** |
| DELTA | **−1** |

| regime | units | base correct | time correct | flips→correct | regressions |
|---|---|---|---|---|---|
| TEMPORAL_POSITIVE | 5 | 4 | 2 | 0 | 2 (`031748ae`, `0977f2af`) |
| TEMPORAL_BOUNDARY | 2 | 0 | 2 | 2 (`08f4fc43`, `0bc8ad92`) | 0 |
| NON_TEMPORAL_CONTROL | 3 | 3 | 2 | 0 | 1 (`00ca467f`) |

**Predicted repairs (wrong→correct within `TEMPORAL_POSITIVE`): 0.** **Unexpected repairs (outside the predicted bucket): 2.** **Regressions: 3.** **`NET_PREDICTED_REPAIRS = 0 − 3 = −3`.**

## Transcript analysis — mandatory for every flip and every regression

**`08f4fc43`** (flip, `TEMPORAL_BOUNDARY`) — `TEMPORAL_INFORMATION_USED: YES`. BASE: *"cannot be determined."* `+TIME`: *"the Sunday mass... was on January 2nd, and the Ash Wednesday service was on February 1st. That is 30 days apart."* Gold: 30 (31 also acceptable). Clean, direct anchor use.

**`0bc8ad92`** (flip, `TEMPORAL_BOUNDARY`) — `TEMPORAL_INFORMATION_USED: YES`. `+TIME` cites *"October 22, 2022"* as the visit and *"February 18, 2023"* as the current date, computes *"approximately 4 months."* Gold is 5 — but the frozen judge's own TEMPORAL template explicitly instructs *"do not penalize off-by-one errors"* for day/week/month counts, so this is a legitimate pass under the standing protocol, not noise.

**`031748ae`** (regression, `TEMPORAL_POSITIVE`) — `TEMPORAL_INFORMATION_USED: YES`, and well-founded. The "leads 4 engineers" fact is anchored `[2023-10-24]`, five months after the "new role" fact `[2023-05-11]`. BASE silently assumed "4" was the starting count; `+TIME` correctly notices the gap and hedges: *"The context does not specify how many engineers you led when you first started."* A more epistemically careful answer than BASE's lucky guess, judge-penalized for the hedge.

**`0977f2af`** (regression, `TEMPORAL_POSITIVE`) — `TEMPORAL_INFORMATION_USED: NO` for both arms. Both BASE and `+TIME` are near-identical honest abstentions that each happen to name the gold entity ("Instant Pot") while explaining they can't establish an order. The flip reads as judge phrasing-sensitivity to `+TIME`'s more explicit *"does not specify which one came first"* framing, not a mechanism effect.

**`00ca467f`** (regression, `NON_TEMPORAL_CONTROL`, predicted no effect) — `TEMPORAL_INFORMATION_USED: YES`, and this is the clearest negative-transfer case. Both relevant March facts (a bronchitis diagnosis dated "March 3rd" in-text, and a Dr. Thompson follow-up dated "March 20th" in-text) share the identical session anchor `[2023-03-27]` — a single later catch-up session recalling two distinct earlier events. `+TIME` renders only the session-recording date, not the in-text event dates. `+TIME`'s answer drops the March 3rd visit and undercounts to 1 (gold: 2). This is exactly the boundary condition the session-timestamp-vs-resolved-event-date distinction predicts: when a question needs the date *named inside* a fact rather than the date the fact was *recorded*, a diverging session anchor can compete with and crowd out correct in-text temporal reasoning.

## Interpretation, stated at the required precision

Not: *"temporal grounding does not work."*

**Session-timestamp anchoring at context assembly did not replicate under this Stage-2 regime.** Specifically: it produced zero repairs in the pre-registered `TEMPORAL_POSITIVE` bucket, two real, transcript-confirmed repairs in the adjacent `TEMPORAL_BOUNDARY` bucket (duration/arithmetic questions, where the mechanism's fit may actually be *better* than plain ordering), one clear negative-transfer regression on a control unit where the session anchor diverged from an in-text event date, one epistemically-defensible-but-judge-penalized hedge, and one judge-phrasing artifact unrelated to the mechanism. Resolved-event-date grounding (write-side, `C3`/`E2`) is a distinct, untested hypothesis and is not weakened or strengthened by this result.

## Verdict

**TEMPORAL_ANCHOR_FAILED_REPLICATION.**

Both trigger conditions independently hold: regressions (3) ≥ repairs (2, and 0 in the predicted regime); and the observed effect does not match the pre-registered regime (all movement landed outside `TEMPORAL_POSITIVE`, including a regression in the predicted-null `NON_TEMPORAL_CONTROL` bucket).

**`REPLICATED_VALIDATED_TRANSPLANT` status for Mechanism A: NO.** E1 remains a valid, single-sample exploratory signal (not retracted, not superseded — its own artifacts and transcripts stand on their own evidence). It does not clear the Stage 2 replication bar.

## What this sample newly teaches, worth carrying into any future design of this mechanism

1. The 08f4fc43/0bc8ad92 pattern suggests duration/arithmetic (`TEMPORAL_BOUNDARY`-shaped) questions may benefit *more* directly from explicit dates than simple ordering (`TEMPORAL_POSITIVE`-shaped) questions — the opposite of this sample's a priori difficulty ranking.
2. The 00ca467f pattern is a specific, falsifiable boundary condition: session-timestamp anchoring can actively mislead on questions requiring an event date named *inside* a fact when that date diverges from the fact's own recording session. Not investigated further here (out of scope — no second mechanism, no further experiments this phase).
3. Two of three regressions show the reader becoming *more* epistemically cautious under the treatment (hedging, more explicit abstention framing) in ways a binary judge penalizes — an echo of E1's `+SRC` regressions, now appearing under `+TIME` itself on a different sample.

## Cost

Ingest $0.715117 + reader $0.022894 + judge $0.001940 = **$0.739964** of the $1.00 hard cap.
