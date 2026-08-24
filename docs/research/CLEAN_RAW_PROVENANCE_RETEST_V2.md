# Clean Raw-Provenance Retest v2 (E3: `arena-provenance-clean-v2`)

Full structured data: [`data/lab/arena/base-plus-x-v2/e3-analysis.json`](../../data/lab/arena/base-plus-x-v2/e3-analysis.json).

## Epistemic key

**MEASURED** / **CODE_VERIFIED** / **INFERENCE** / **HYPOTHESIS** / **UNRESOLVED**, never mixed.

## Why this retest exists

The prior `RAW_PROVENANCE_EXPANSION → DROP` decision (arena-mechanism-ablation-v1, Experiment B) was computed entirely against cross-unit-contaminated Mem0 data. It is **not** valid evidence and was not treated as such here.

## Method, exactly as it ran

- **No new Mem0 ingest. No Hindsight calls.** Reused the clean store's persisted contexts.
- BASE compact = the frozen `mem0_original` (native) arm, reused, not re-queried.
- `COMPACT + RAW` and `RAW ONLY` built via `arena.mechanism_ablation.build_arms()`, called fresh against the *current* `raw/arena-expansion-v1/mem0.json` — MEASURED and CODE_VERIFIED this session to now hold the clean run's data (0/18 mismatches against `mem0-breadth-arms.json`'s `mem0_original` context, checked before spending anything).
- Mapping: deterministic, session-date-only (`arena.retrieval_truth.session_map` / `mechanism_ablation.raw_session`), no semantic or gold-aware matching — the same code audited during the earlier Hindsight-ablation phase this session. Ambiguous units are `UNOBSERVABLE`, not guessed.
- Same frozen reader and judge protocol as E1 and every prior phase.

## Observability

**9 of 10 units observable.** `69fee5aa` is `UNOBSERVABLE`: *"this unit's haystack dates do not uniquely identify a session"* — the same unit that has been unobservable for retrieval diagnostics throughout this entire research thread.

## Scores — MEASURED (9 observable units)

| arm | score |
|---|---|
| compact | 5/9 |
| compact + raw | **6/9** |
| raw only | 4/9 |

`COMPACT_WRONG_RAW_FIXES`: **`['6a27ffc2']`** — 1 unit.
`RAW_CAUSES_REGRESSION`: **`[]`** — 0 units.

Raw-only underperforms compact (4/9 < 5/9), replicating the *direction* of the old (invalidated) finding on genuinely clean data — but note this is a directional replication of one sub-claim, not a validation of the old "zero repairs" headline, which this retest explicitly contradicts.

## The one repair, examined — not assumed

`6a27ffc2` ("how many videos of Corey Schafer's Python series have I completed?", gold `30`):

- **compact**: *"You have completed 20 videos so far."* — WRONG. Picks a stale count.
- **compact + raw**: *"...you have completed 30 videos of Corey Schafer's Python programming series so far."* — CORRECT.

This project's own earlier archaeology already established that Mem0's compact context for this unit holds **both** the stale (`20`) and updated (`30`) counts, and that the compact-only reader can go either way depending on which is more salient in a long list. The raw source session did not supply *missing* content — gold was already present, rank 1, in compact (MEASURED, all 4 compact failures below). What raw provenance did here was **disambiguate between two competing facts already in the compact context**, not fill a content gap.

## Absence vs. presence in the compact failures

**All 4 of the 9 observable units' compact failures had `gold_in_context=True, gold_rank=1` in compact.** `GOLD_OR_GOLD_ADJACENT_PRESENT_IN_COMPACT`: 4/4. `ABSENT_FROM_COMPACT`: 0/4.

| question_id | type | gold in compact | repaired |
|---|---|---|---|
| `6a27ffc2` | knowledge-update | yes, rank 1 | **yes** |
| `ba358f49` | multi-session | yes, rank 1 | no |
| `gpt4_59c863d7` | multi-session | yes, rank 1 | no |
| `gpt4_f420262c` | temporal-reasoning | yes, rank 1 | no |

This complicates the pre-registered H1 framing (repairs concentrated in the *absence* regime): on this sample, the failure set is **uniformly gold-present**, so there is no absence-subset to concentrate in. The one repair sits in what is better described as a **competing-facts / under-detail** regime (compact retained the fact but not enough to arbitrate between two contradictory mentions of it) rather than a pure absence regime. Recorded as the honest reading, not force-fit to the pre-registered label.

## Category breakdown of the 4 compact failures

- **temporal-reasoning**: 1 failure (`gpt4_f420262c`), 0 repaired.
- **multi-session**: 2 failures (`ba358f49`, `gpt4_59c863d7`), 0 repaired.
- **knowledge-update**: 1 failure (`6a27ffc2`), **1 repaired**.
- **single-session / other**: 0 failures in this set.

## The three specifically flagged units

- **`ba358f49`**: compact WRONG, compact+raw WRONG, raw-only WRONG. **Not repaired.** (Contrast with E1: this unit *does* flip correct under `+TIME` and `+BOTH` — its fix is temporal-anchoring, not raw provenance.)
- **`69fee5aa`**: `UNOBSERVABLE` — provenance mapping cannot resolve a unique session; untestable by this mechanism, consistent with every other diagnostic pass on this unit this session.
- **`gpt4_f420262c`**: compact WRONG, compact+raw WRONG, raw-only WRONG. **Not repaired** — as predicted going in (its needed dates are scattered across four separate sessions; top-1 provenance reaches only one of them). A non-repair here does not weigh against `+TIME`'s success on the same unit in E1; they test different mechanisms.

## Verdict

**RAW_PROVENANCE_CONDITIONAL_SIGNAL** — with an explicit correction to the mechanism it signals.

Criterion satisfied: ≥1 repair, no regressions, repair sits in a broadly under-detail (not pure-absence) regime. This is **not** a restoration of the old `DROP` conclusion (now confirmed unsupported, correctly) and **not** a strong revival either: 1 repair out of 9, via disambiguation of an already-present competing fact, not via supplying missing content. The two units where raw provenance was explicitly hypothesized to matter most for absence-type reasons (`ba358f49`, `gpt4_f420262c`) were **not** repaired. `H1` (absence-vs-under-detail) is not supported as originally framed — there was no absence-regime failure to test it against on this sample — while a narrower, previously-unstated variant ("raw helps arbitrate between competing extracted facts") has exactly one data point in its favor.

## Cost

Reader $0.016483 + judge $0.001907. **E3 subtotal: $0.018390.**
