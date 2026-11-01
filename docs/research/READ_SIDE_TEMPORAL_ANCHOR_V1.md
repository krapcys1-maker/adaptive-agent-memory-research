# Read-Side Temporal Anchor v1 (E1: `arena-base-plus-x-v2`)

Full structured data: [`data/lab/arena/base-plus-x-v2/e1-analysis.json`](../../data/lab/arena/base-plus-x-v2/e1-analysis.json).
Predictions pre-registered, before any treatment context was built: `PM-20260824-d4155074`.

## Epistemic key

**MEASURED** (score/label read from a frozen judged artifact) / **CODE_VERIFIED** / **INFERENCE** / **HYPOTHESIS** / **UNRESOLVED**, never mixed.

## Question

Does rendering the already-persisted, positionally-aligned session timestamp (and/or a source-provenance tag) next to each already-retrieved Mem0 fact fix the specific units the archaeology attributed to missing temporal/attribution structure? No new ingest, no new retrieval — only the context-assembly string per item changed.

## Method, exactly as it ran

- BASE: frozen `mem0_original` (native) and `mem0_3000` (wide) arms, reused, not re-queried.
- `+TIME` (**TEMPORAL_ANCHOR_AT_CONTEXT**): each item → `[YYYY-MM-DD] {fact}`, date from the item's own positionally-aligned `evidence_times` entry, normalised through the project's existing `canonical_time()` — no text parsing of the fact, no LLM, no gold.
- `+SRC` (**SOURCE_TAG_AT_CONTEXT**): each item → `(source: user's message) {fact}` — uniform, because every stored fact in this selection genuinely originates from a user-role turn (`as_records` filters `role=="user"` — CODE_VERIFIED).
- `+BOTH`: gate — run only if `+TIME` or `+SRC` shows ≥1 predicted flip without unexplained regression. Satisfied by `+TIME`.
- `+PLACEBO`: gate — run only if `+TIME` shows a predicted flip. Satisfied. Each item → `[item-NNN] {fact}`, sequential by existing rank order, encoding no date/position-in-time/session-id/gold/semantics.
- Same frozen reader (`fixed_reader.py`, prompt hash unchanged), same frozen judge (`judge_pilot.py` protocol, imported not restated), 2 passes + 3rd on disagreement, blind to arm/hypothesis/gold.

## Results — MEASURED

| arm | score | flips→correct | regressions | predicted net | unexpected flips | avg tokens (Δ vs base) |
|---|---|---|---|---|---|---|
| native BASE | 5/10 | — | — | — | — | 111.0 |
| native `+TIME` | **7/10** | ba358f49, gpt4_f420262c | none | **+2** | none | 121.0 (+10) |
| native `+SRC` | 4/10 | none | gpt4_f49edff3 | −1 | none | 141.0 (+30) |
| native `+BOTH` | 6/10 | gpt4_f420262c | none | +1 | none | 151.0 (+40) |
| native `+PLACEBO` | 5/10 | none | none | 0 | none | 121.0 (+10) |
| wide BASE | 5/10 | — | — | — | — | 2385.7 |
| wide `+TIME` | **8/10** | ba358f49, gpt4_f420262c, gpt4_f49edff3 | none | **+3** | none | 2612.9 (+227) |
| wide `+SRC` | 4/10 | none | gpt4_98f46fc6 | −1 | none | 3067.3 (+682) |
| wide `+BOTH` | 7/10 | gpt4_f420262c, gpt4_f49edff3 | none | +2 | none | 3294.5 (+909) |
| wide `+PLACEBO` | 7/10 | ba358f49, gpt4_59c863d7 | none | +1 | **gpt4_59c863d7** | 2612.9 (+227) |

**Every single pre-registered flip target flipped** — PRIMARY `gpt4_f420262c` at both operating points; SECONDARY/boundary `ba358f49` at both; SECONDARY/boundary `gpt4_f49edff3` at wide (its only eligible operating point — already correct at native). **Zero unexplained regressions on `+TIME` itself, at either operating point.** Predicted non-effect units (`69fee5aa`, `gpt4_59c863d7`) stayed put on `+TIME` exactly as predicted; `gpt4_59c863d7` moved only under `+PLACEBO` (see below).

## `+SRC`'s two regressions — explained, not unexplained (transcript-level)

Both `+SRC` regressions follow the identical pattern: BASE guessed a chronological/comparative order from a weak cue (list order, or "today"/"tonight" phrasing) and happened to land on gold; `+SRC` makes the reader explicitly decline to order the events at all ("cannot be determined... no dates provided" / "cannot be determined"). This project's own established convention treats an explicit non-answer to an answerable question as WRONG — so this is the reader becoming *more* epistemically cautious under the source annotation, which the binary judge penalizes. Full transcripts in the JSON artifact (`explained_regressions`). This satisfies the "analyze transcript before any further arm" rule: the regressions are understood, not anomalous, and do not implicate a harness defect.

## `gpt4_f420262c` transcript comparison — does the reader use the dates?

Gold: `JetBlue, Delta, United, American Airlines`.

**Native BASE** (wrong): *"1. American Airlines... 2. United Airlines... 3. JetBlue..."* — no dates cited, wrong order, Delta dropped.

**Native `+TIME`** (correct): *"1. JetBlue (..., **around November 17, 2022**) 2. United Airlines (..., **around January 28, 2023**) 3. American Airlines (..., **on February 10, 2023**)"* — the reader explicitly cites the rendered anchor dates and reorders by them, correctly.

**Wide BASE** (wrong): 4-item list, wrong order, invents "Spirit Airlines".

**Wide `+TIME`** (correct): *"1. JetBlue... 2. United Airlines... 3. American Airlines..."* — correct relative order for the three it lists.

This is direct, unambiguous transcript evidence that the reader used the anchor information, not a coincidental relabel.

## The placebo caveat — stated plainly, not minimized

At the **wide** operating point, `+PLACEBO` also produces a real, non-trivial gain (5/10 → 7/10 base-to-treatment reads as `+2` naively, but against the *native* BASE-per-arm accounting used throughout this table it is `+1` predicted net) with token overhead matched almost exactly to `+TIME` (2612.9 vs 2612.9 average tokens — the neutral `[item-NNN]` tag costs essentially the same tokens as a date tag). It flips `ba358f49` (a predicted target) **and** `gpt4_59c863d7` (explicitly predicted as a *non*-effect unit — an unexpected flip that does not fit the temporal mechanism at all). At **native**, `+PLACEBO` shows zero effect of any kind.

Read honestly: part of the wide-arm gain is a general "clearer per-item boundary" effect that a content-free tag also produces — this is not unique to temporal information. But `+TIME` at wide still nets 2 *more* predicted flips than `+PLACEBO` (`gpt4_f420262c`, the PRIMARY target with direct transcript confirmation of date usage, and `gpt4_f49edff3`), and at native the entire `+TIME` effect is placebo-free (placebo: 0/10 change). The mechanism-specific signal survives the placebo control; it does not fully explain the wide-arm magnitude on its own.

## Primary metric: PREDICTED_FLIPS_NET_OF_REGRESSIONS

| | native | wide |
|---|---|---|
| `+TIME` | **+2** | **+3** |
| `+SRC` | −1 | −1 |
| `+BOTH` | +1 | +2 |
| `+PLACEBO` | 0 | +1 (plus 1 unexpected, not counted) |

No unregistered flip is credited to the mechanism anywhere in this table (`gpt4_59c863d7`'s `+PLACEBO` flip is reported, not counted as a `+TIME`/`+SRC` success).

## Verdict

**TEMPORAL_ANCHOR_SUPPORTED.**

- ≥1 pre-registered predicted flip: far exceeded (5 flip-events across 2 operating points, all 3 registered target units hit at least once).
- No unexplained regression: `+TIME`/`+BOTH` show zero regressions anywhere; `+SRC`'s two regressions are transcript-explained (increased abstention under ambiguous evidence), not anomalous.
- Transcript behavior consistent with anchor use: directly confirmed for the PRIMARY target, both operating points.
- Caveat, carried forward rather than hidden: at the wide operating point specifically, a matched-token placebo also moves the score, so the wide-arm *magnitude* should be read as "`+TIME`'s effect exceeds a token/formatting placebo by 2 predicted units, not that the entire wide-arm gain is temporal-content-specific." The native operating point has no such confound.
- `SOURCE_TAG_AT_CONTEXT` alone: net negative on this sample (−1 at both points, 0 predicted flips) — its predicted role (helping `ba358f49` via attribution) did not materialize standalone; `ba358f49` flips under `+TIME` and `+BOTH`, not `+SRC` alone. Recorded as a real, transcript-explained negative result for this specific sub-mechanism, not folded into the overall verdict for `+TIME`.

## Cost

E1 total: reader $0.030781 + $0.03432 (gated) = $0.065101; judge $0.004089 + $0.00425 (gated) = $0.008339. **E1 subtotal: $0.073440.**
