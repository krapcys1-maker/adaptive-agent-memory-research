# Temporal Alignment and Distraction Archaeology v1

Zero-cost forensic re-analysis of Stage 2's `TEMPORAL_ANCHOR_FRESH_REPLICATION_V1` failure, plus the H5 harmful-sibling/distraction diagnostic. New API spend: **$0.00** — every claim below is read from already-frozen artifacts.

Full structured data: [`data/lab/arena/temporal-alignment-and-distraction-archaeology-v1/analysis.json`](../../data/lab/arena/temporal-alignment-and-distraction-archaeology-v1/analysis.json).
Prior results, unchanged: E1 `PM-20260824-2d603195`, Stage 2 `PM-20260824-8dc62d48`, commit `b45402a1984f236329279b54bd0b05c2f9612581`.

## Epistemic key

**MEASURED** (read directly from a frozen transcript/label) / **INFERENCE** (this document's reasoning connecting measured facts) / **HYPOTHESIS** (untested) / **UNRESOLVED**. A mechanistic story is INFERENCE unless a transcript explicitly demonstrates it.

## Main research question

Can Stage 2's failed replication be explained by (A) SESSION_TIME vs EVENT_TIME divergence, (B) harmful-sibling/distraction, (C) reader/judge noise, or (D) a combination? No answer was assumed going in; each hypothesis was tried against counter-examples, not just confirming cases.

**Answer: (D), and not uniformly — different Stage 2 units fail or succeed for different, individually-identifiable reasons.** No single hypothesis explains all five repair/regression cases.

## Per-unit archaeology

All 10 units, full detail in the JSON artifact. Summary:

| unit | regime | outcome | temporal_alignment | timestamp used | distractor | effect |
|---|---|---|---|---|---|---|
| `01493427` | POSITIVE | unchanged correct | NON_TEMPORAL | no | none | neutral |
| `031748ae` | POSITIVE | **regression** | DIVERGENT | **yes** | none | hurt (judge-penalized caution) |
| `07741c45` | POSITIVE | unchanged wrong | AMBIGUOUS | unclear | none | neutral |
| `0977f2af` | POSITIVE | **regression** | AMBIGUOUS | no | none | unclear (judge noise) |
| `0bb5a684` | POSITIVE | unchanged correct | NON_TEMPORAL | no (in-text dates sufficed) | none | neutral |
| `08f4fc43` | BOUNDARY | **repair** | DIVERGENT (harmless) | **yes** | none | **helped** |
| `0bc8ad92` | BOUNDARY | **repair** | ALIGNED | **yes** | avoided | **helped** |
| `001be529` | CONTROL | unchanged correct | NON_TEMPORAL | no | none | neutral |
| `00ca467f` | CONTROL | **regression** | DIVERGENT (harmful) | yes | none (same-entity conflict) | **hurt** |
| `0100672e` | CONTROL | unchanged correct | NON_TEMPORAL | no | none | neutral (borderline hedge) |

## Critical transcript cases

### Repair 1 — `08f4fc43` (days between two church services)

Gold: 30 days. BASE: *"cannot be determined."* `+TIME`: *"the Sunday mass at St. Mary's Church was on January 2nd, and the Ash Wednesday service was on February 1st. That is 30 days apart."*

**Evidence chain:** context → two facts, both anchored `[2023-02-20]` (a single later recap session) → each fact's own text states its own date explicitly (*"...on January 2nd"*, *"...on February 1st"*) → reader cites those exact in-text dates, not the shared anchor → correct arithmetic → judge: correct.

**A. Session timestamps:** both `2023-02-20`. **B. In-text event dates:** January 2 and February 1, both explicit. **C. How the reader used both:** it used the in-text dates, ignored the (irrelevant here) shared anchor. **D. Did session anchor dominate event date?** No — the opposite; in-text date won cleanly. **E. Did BASE avoid the conflict?** There was no conflict to avoid — BASE had the identical in-text dates available and still failed to use them. The `+TIME` treatment's only change was a uniform per-item date prefix; **INFERENCE**: this plausibly shifted the reader's general reading strategy toward actively parsing and comparing dates across a long list, rather than supplying information that was otherwise missing.

### Repair 2 — `0bc8ad92` (months since a museum visit)

Gold: 5. `+TIME` computes ~4 (Oct 22, 2022 → Feb 18, 2023), citing the anchor date directly and a "current date" reference. **Judged correct** — the frozen judge's own TEMPORAL template explicitly forgives off-by-one duration errors; this is a legitimate pass under the standing protocol, not a scoring bug.

**Distractor check:** a near-miss candidate exists — item 2, *"Attended a guided tour at the Natural History Museum yesterday **with dad**"*, anchored `2023-02-18`, structurally similar (a museum visit) but with the wrong companion (dad, not a friend). The reader correctly excludes it. Recorded as a useful **negative control** for H5: a real, present, close sibling that did *not* cause distraction here.

### Regression 1 — `031748ae` (team size when started vs now)

Gold requires two numbers (4 then, 5 now). Only one team-size fact is retrievable anywhere in context: *"Leads a team of 4 engineers,"* anchored `[2023-10-24]`, five months after *"New role as Senior Software Engineer,"* anchored `[2023-05-11]`. BASE silently assumed 4 was the starting count (matching half of gold, apparently enough for the judge). `+TIME` notices the five-month gap between the two anchors and refuses to assume 4 was the starting number: *"The context does not specify how many engineers you led when you first started."*

**This is the reader correctly reasoning about session-time divergence** — and being judge-penalized for the resulting honesty. Not a reasoning failure; a scoring-protocol interaction.

### Regression 2 — `0977f2af` (kitchen gadget ordering)

Both facts (Air Fryer, Instant Pot) share one session anchor `2023-05-21`; the Air Fryer fact has a relative cue ("yesterday") with no fixed reference, the Instant Pot fact has no date cue of any kind. **The true order is not derivable from the delivered evidence in either arm.** BASE and `+TIME` produce near-identical abstentions, both naming the gold entity ("Instant Pot") while explaining they cannot establish an order. `TEMPORAL_INFORMATION_USED: NO` for both. The flip reads as judge sensitivity to `+TIME`'s more explicit *"does not specify which one came first"* phrasing — not a mechanism effect.

### Regression 3 — `00ca467f` (doctor's appointments in March) — the clean negative-transfer case

**A. Session timestamps:** both target facts, and several unrelated facts in the same recap session, share the identical anchor `[2023-03-27]`. **B. In-text event dates:** each target fact states its own date explicitly — *"...by Dr. Smith on March 3rd"*, *"...with... Dr. Thompson on March 20th"*. **C. How the reader used both:** BASE (no anchors at all) correctly lists both from their in-text dates. `+TIME` drops the bronchitis (March 3) visit and undercounts to 1. **D. Did the session anchor dominate?** The observable behavior is consistent with this — content is byte-identical between arms except for the added tags, and the shared, repeated anchor sits alongside several *other* same-session, non-appointment facts (a gastroenterology consideration, a hand-numbness scheduling plan), which may have made the "which of these March-27-tagged items are actually appointments" filter harder, not easier. **E. Did BASE avoid this?** Yes, entirely — by never being given a competing date signal to reconcile against the in-text ones.

**Why this differs from `08f4fc43` despite an structurally similar setup** (shared session anchor + explicit differing in-text dates on both facts): **INFERENCE**, not proven from a single pair — `08f4fc43` is a two-item, explicitly-named-event lookup; `00ca467f` is a many-item filter-and-count task where a *uniformly repeated* tag sits among several superficially similar same-tagged distractor items. Task type, not divergence alone, appears to be the operative variable.

## H5 — harmful-sibling / distraction archaeology

### Primary case: `gpt4_f420262c`'s "Spirit" (E1, not Stage 2)

Searched the frozen `mem0_3000` delivered context (208 items) for any source of "Spirit" in the wrong BASE answer (*"...4. Spirit Airlines"*).

**Found:** item 5, *"Curious about Spirit Airlines' baggage policies"* (rank 5, immediately adjacent to the relevant flight cluster at ranks 0, 2, 3, 7, 9), and item 12, *"Planning a spring break trip to Fort Lauderdale in March and flying Spirit Airlines"* (a real but *future*, not-yet-taken trip).

**Classification: `TRACEABLE_DISTRACTOR`.** Spirit Airlines is a genuine, present, semantically-adjacent item at close rank proximity to the actually-relevant flight facts. The correct 4th airline (Delta) requires a multi-hop link the reader apparently didn't make (an unnamed Boston–Atlanta flight + a separate Delta SkyMiles mention); Spirit, directly named and nearby, is the path of least resistance. Textbook harmful-sibling pattern: correct evidence present + a plausible wrong-sibling entity also present + reader selects the wrong variant instead of doing the harder correct resolution.

### Same check applied to all 5 Stage 2 repair/regression cases

**Result: 0 of 5 show H5-style entity-level sibling distraction newly caused or removed by `+TIME`.** `031748ae` and `0977f2af`'s changes are hedges/omissions, not fabricated content — nothing to trace to a sibling. `00ca467f`'s regression is a same-entity date-signal conflict (see above), mechanistically distinct from sibling substitution: the dropped item is *itself correct*, not confused with a different wrong entity. `08f4fc43` and `0bc8ad92` are repairs (nothing wrong to trace); `0bc8ad92` additionally shows a real near-miss distractor that the reader *correctly avoided*, a useful negative control.

## Distraction taxonomy status

**`HARMFUL_SIBLING_DISTRACTION`** — defined as: *correct evidence is present, but semantically related competing evidence inside the same delivered context causes the reader to select, blend, or reason from the wrong variant.*

**Status: `OBSERVED_CASE`** (one clean, well-evidenced instance — `gpt4_f420262c`'s "Spirit"). **Not promoted to a measured general failure mode** on the strength of one example. Within Stage 2 specifically, this mechanism has **no supporting evidence** (`NOT_OBSERVED` for the `+TIME` treatment's specific effect) — the mechanism is real somewhere in this arena's data, but it is not what explains Stage 2's regressions.

## Temporal alignment × effect table

| alignment | repairs | regressions | neutral |
|---|---|---|---|
| ALIGNED | 1 | 0 | 0 |
| DIVERGENT | 1 | 2 | 0 |
| AMBIGUOUS | 0 | 1 | 1 |
| NON_TEMPORAL | 0 | 0 | 4 |

**DIVERGENT alone does not predict direction** — it contains both a repair (`08f4fc43`, harmless divergence because the fact carries its own explicit date) and two regressions of different character (`00ca467f`, genuine negative transfer; `031748ae`, judge-penalized honesty). What matters is not divergence per se but whether an explicit in-text date exists as a fallback, and whether the task is a bounded lookup vs. a many-item filter/count.

## Distraction status × effect table

| distractor_status | repairs | regressions | unchanged |
|---|---|---|---|
| TRACEABLE_DISTRACTOR (E1, pre-existing) | 0 | 0 | 1 (wrong) |
| TRACEABLE_DISTRACTOR_AVOIDED | 1 | 0 | 0 |
| NO_DISTRACTOR | 1 | 3 | 4 |

`+TIME` did not measurably shift attention/selection toward wrong entities anywhere in Stage 2 — the one avoided near-miss (`0bc8ad92`) if anything suggests rendered dates can help *reject* a superficially similar distractor, not just fail to prevent one.

## Competing explanations

**H0 — Stage 2 is reader/judge noise.** EVIDENCE_FOR: `0977f2af` is clean judge-phrasing noise; `0100672e` shows the same sensitivity sitting right at a knife's edge without flipping; `0bc8ad92`'s pass leans on the judge's own stated tolerance. EVIDENCE_AGAINST: `08f4fc43` and `00ca467f` are *content* changes, not phrasing artifacts — one adds a real, correct computation BASE never attempted; the other drops a real, correct fact. **STATUS: WEAK** — explains 1–2 of 5 events, not the two content-level cases.

**H1 — SESSION_TIME helps only when it is a good EVENT_TIME proxy.** EVIDENCE_FOR: `0bc8ad92` (ALIGNED → repair, anchor directly used). EVIDENCE_AGAINST: `08f4fc43` is DIVERGENT yet still repairs, because an in-text date makes the anchor moot. **STATUS: SUPPORTED but incomplete** — true where it applies, doesn't cover the case where in-text dates make alignment irrelevant.

**H2 — SESSION_TIME hurts when explicit in-text EVENT_TIME differs from the anchor.** EVIDENCE_FOR: `00ca467f` (clean positive case). EVIDENCE_AGAINST: `08f4fc43` has the identical structural profile (shared anchor, explicit differing in-text dates on both facts) and *repairs* instead. **STATUS: SUPPORTED for one instance, directly contradicted in its simple form by a structurally near-identical case — WEAK as a general rule, real as a specific mechanism under a further, unconfirmed condition (task type; see H4).**

**H3_LOCAL — the added prefix changes attention and exposes a harmful sibling.** (Not to be confused with frontier H3, `AUTHORITY_COLLAPSE_SAFE_CONSOLIDATION`.) EVIDENCE_FOR: none within Stage 2. EVIDENCE_AGAINST: 0 of 5 cases show new sibling distraction; `0bc8ad92` shows a distractor being *avoided* under `+TIME`, if anything the opposite direction. **STATUS: DISFAVORED** for this sample.

**H4 — sample selection / category composition explains E1 vs Stage 2.** EVIDENCE_FOR: E1's win pattern (multi-fact ordering across several scattered sessions, where session anchors are the *only* available temporal signal and are well-aligned) does not structurally recur in Stage 2's `TEMPORAL_POSITIVE` bucket — none of `01493427`/`031748ae`/`07741c45`/`0977f2af`/`0bb5a684` share that shape; Stage 2's actual wins landed in the structurally different `TEMPORAL_BOUNDARY` bucket instead. A gold-blind, keyword-based classifier cannot guarantee sampling the deeper structural property that drove E1. EVIDENCE_AGAINST: the classifier did correctly surface some genuinely temporal-composition-shaped questions. **STATUS: SUPPORTED.**

**H5_LOCAL — E1 was a small-n success without a stable mechanism effect.** EVIDENCE_FOR: E1's flip counts were small (1–3 per arm), inherently sampling-fragile. EVIDENCE_AGAINST: E1's primary case has a direct, unambiguous mechanistic transcript (dates cited, order corrected); Stage 2 independently reproduces an equally clean mechanistic transcript twice (`08f4fc43`, `0bc8ad92`) on *different* units. The underlying "rendering a usable date helps a reader do date arithmetic it needs to do" effect is not illusory — it fires cleanly and repeatedly. What is unstable is whether E1's *specific* regime composition recurs by chance. **STATUS: PARTIALLY SUPPORTED, substantially overlapping with H4** — not "no effect," but "small-n regime-selection was not representative."

## E1 vs Stage 2 reconciliation

E1's `+TIME` wins concentrated on multi-fact ordering across several sessions where the rendered anchor was the *only* temporal signal available and happened to align well with event time (`gpt4_f420262c`: 4 flights, months apart, no in-text dates on most). Stage 2's `TEMPORAL_POSITIVE` bucket — selected gold-blind by category/keyword, not by this deeper structural property — turned out low in that specific pattern; its actual mechanistic wins fell in the adjacent `TEMPORAL_BOUNDARY` bucket instead (two-item duration lookups), and its one clean loss is a *different* structural case entirely (many-item filter/count with a shared, repeated session tag competing against in-text dates).

**Verdict: `REGIME_DEPENDENCE`, not `SMALL_N_NOISE`.** The mechanism (rendering usable dates helps date-arithmetic reasoning) is real and repeatedly, directly demonstrated in transcripts across both experiments. What does not hold up is the *specific regime prediction* (`TEMPORAL_POSITIVE`-labeled ordering questions, as a category) as the reliable target — the reliable target looks narrower and more structural: **bounded lookups over explicitly-or-well-anchored named events**, not the `question_type`/keyword category Stage 2's selection rule used as a proxy for it. `NOT SMALL_N_NOISE` because the effect is mechanistically reproducible, not statistically marginal, when the right structural conditions hold.

## New mechanism hypotheses (max 3, none endorsed, none run)

**1. `EVENT_TIME_OVER_SESSION_TIME_PRECEDENCE`**
TARGET_FAILURE: `00ca467f`-style negative transfer (session anchor competing with a valid in-text event date on a filter/count task).
EXPECTED_REGIME: many-item filter/count tasks where several items share one session tag but each carries its own distinct in-text date.
EXPECTED_BENEFIT: avoids dropping valid items when in-text dates already resolve the question.
EXPECTED_NEGATIVE_REGIME: items with no in-text date at all — no information gained, back to session-anchor-only behavior.
MINIMAL_CALIBRATION: a handful of synthetic filter/count cases with deliberately conflicting session/event dates, checked for reader behavior only (no benchmark scoring).
FALSIFICATION: reader still drops valid items even when in-text dates are given rendering precedence.
ESTIMATED_COST: ~$0.05–0.10 (calibration + a tiny paired arm).

**2. `DISTRACTOR_AWARE_CONTEXT_ASSEMBLY`**
TARGET_FAILURE: H5-style harmful-sibling substitution (the `gpt4_f420262c`/"Spirit" pattern).
EXPECTED_REGIME: enumeration/identification tasks with several same-category-different-instance items ranked near the genuinely relevant cluster.
EXPECTED_BENEFIT: fewer wrong-sibling substitutions where the correct answer needs a harder multi-hop resolution than a nearby wrong-but-named alternative.
EXPECTED_NEGATIVE_REGIME: tasks that legitimately need to distinguish two genuinely-relevant similar items — over-flagging could suppress a needed item.
MINIMAL_CALIBRATION: replay `gpt4_f420262c` with the two Spirit items explicitly flagged as "candidate distractor: verify relevance before use" and check whether the flip resolves.
FALSIFICATION: flagging does not change the wrong answer, or degrades other cases.
ESTIMATED_COST: ~$0.05.

**3. `TASK-TYPE-CONDITIONAL TEMPORAL ANCHOR`**
TARGET_FAILURE: fixing `00ca467f`-style regressions without losing `08f4fc43`/`0bc8ad92`-style gains, by rendering (or weighting) session anchors differently for lookup vs. filter/count tasks.
EXPECTED_REGIME: mixed corpora containing both task shapes.
EXPECTED_BENEFIT: keeps the demonstrated lookup/arithmetic gains while removing the filter/count negative-transfer mode.
EXPECTED_NEGATIVE_REGIME: requires a reliable task-type signal at inference or assembly time — itself a new, untested failure surface if the classifier is wrong.
MINIMAL_CALIBRATION: replay `00ca467f` and `08f4fc43` under a task-type-gated rendering rule; check whether it fixes the former without breaking the latter.
FALSIFICATION: task-type detection is unreliable, or gating doesn't change behavior on either probe.
ESTIMATED_COST: ~$0.05–0.10.

None of these three is asserted to survive further testing. All three remain untested.

## E2 decision

`E2` = write-side temporal resolution (reference date + explicit resolve-relative-time instruction at extraction, previously calibrated inert on its own in `PM-20260824-c76d8a96`).

This archaeology identifies a *specific*, mechanistically-clear failure mode (`00ca467f`: session-recording time competing with an explicit in-text event time on a filter/count task) that write-side resolved-event-date grounding would address by construction — storing the resolved event date directly, rather than only the recording-session date, removes the divergence at its source rather than requiring the reader to arbitrate between two rendered timestamps at read time. Combined with two independently clean repair transcripts confirming the underlying "give the reader a usable date" idea works when the structural conditions are right, this sharpens E2's motivation beyond where it stood after Stage 2 alone.

**`E2_CALIBRATION_JUSTIFIED`** — as a recommendation for a future decision, not as approval to proceed. This document does not authorize or initiate E2 or its calibration.

## Backlog items recorded, not run

- **`ZERO_ANSWER_DISPERSION_DIAGNOSTIC` (frontier H2):** requires new reader calls. Not run. `STATUS: CHEAP_FOLLOWUP, NOT_RUN`. Trigger: only if a future $0 archaeology pass cannot distinguish stable failure from reader noise on a specific probe. Estimated cost ~$0.01–0.02.
- **`AUTHORITY_COLLAPSE_SAFE_CONSOLIDATION` (frontier H3):** future-only design constraint, not testable today (no consolidation mechanism exists in AAMR yet). `STATUS: EXTERNAL_STRONG_SIGNAL, AAMR_UNTESTED, NOT_ACTIONABLE_YET`. Trigger: revisit before the first AAMR consolidation/summarization mechanism is trusted or adopted.

## E3 H4 annotation (only if free and quick — kept short)

E3's raw-provenance repair (`6a27ffc2`) was, per the E3 report itself, a *disambiguation of a competing already-extracted fact* rather than a content-absence fix or a pattern-generalization case — it does not cleanly map onto the external RAW_PROVENANCE × DETAIL_REPRODUCTION-vs-GENERALIZATION axis (frontier H4) without further probes that don't currently exist in the frozen E3 set. **No separate analysis branch opened** — not a priority, and not answerable deterministically from existing data alone.

## Supersession discipline

**E1** (`PM-20260824-2d603195`, `TEMPORAL_ANCHOR_SUPPORTED`, exploratory) is **not retracted**. **Stage 2** (`PM-20260824-8dc62d48`, `TEMPORAL_ANCHOR_FAILED_REPLICATION`) stands alongside it. **Current synthesis**, per this document: `TEMPORAL_ANCHOR_AT_CONTEXT` is **`QUALIFIED_BY Stage2 fresh replication`** — `REGIME_DEPENDENT`, specifically: positive and mechanistically-confirmed for bounded lookups over explicitly-or-well-anchored named events; negative for many-item filter/count tasks with a repeated session tag competing against in-text dates; neutral-to-judge-noise on genuinely underspecified questions. Neither prior verdict is deleted; this is the reconciling layer.
