# Baseline profile of the live account's own published notes (snapshot of 2026-11-01)

**Status: descriptive measurement, not an experiment.** The source is a read-only export of the account's published notes, made by the agent's own session and kept outside this repository; only aggregates are recorded here (no text, no id, no excerpt). Produced with `scripts/published_notes_baseline.py --embed`; the semantic part uses `sentence-transformers/all-MiniLM-L6-v2`, offline, on CPU. Facts about the account's prompts and cadence come from its own session and are not verified by this project.

## The snapshot

234 notes from 16 August to 1 November 2026, on 69 days with at least one note: 3.39 per day (median 3, from 1 to 10), 91 words on average (33 to 245), no exact duplicate. The export holds notes only: no comments, replies or longer articles, and no reader data.

## What the numbers say

| Measure | Value |
|---|---|
| Lexical overlap with one earlier note (share of a note's 4-grams already contained), mean | 0.018 |
| ... 99th percentile | 0.19 |
| ... notes with overlap of at least 0.2 / at least 0.5 | 0.85% (2 notes) / none |
| Provisional repetition rule (5-grams, overlap of at least 0.5, within 30 days) | 0 of 234 |
| Explicit references to the account's own earlier writing (phrase, or an earlier title quoted in full) | 0 of 234 |
| Semantic: top-1 cosine to an earlier note (earlier same-day notes included), mean (SD) | 0.478 (0.159) |
| ... median / 90th / 99th percentile | 0.464 / 0.696 / 0.856 |
| Notes with an earlier note at cosine of at least 0.5 / 0.6 / 0.7 / 0.8 | 42.1% / 20.6% / 9.9% / 3.0% |
| ... of which the earlier note is from the previous 7 days (cosine at least 0.6 / 0.7) | 81% / 96% (median gap 2 days) |
| Day-level intraclass correlation: binary at 0.6 / 0.7, continuous top-1 cosine | 0.003 / 0.013 / 0.144 |
| Detectable shift of the mean top-1 cosine, 200 tasks, memory in 25% / 50% of them | 0.073 / 0.063 (0.46 / 0.40 SD) |
| ... with 400 tasks | 0.051 / 0.045 (0.32 / 0.28 SD) |

A one-off check with the extended callback patterns of the offline writer simulation (`scripts/writer_memory_sim.py` on its own branch) also found 0 of 234; that check is not reproduced by the script above.

## What follows

1. **Lexical repetition has no headroom.** The account does not copy its own phrases; a memory designed to reduce repetition cannot show a gain on a measure that sits at its floor. A repetition rate cannot be the primary measure of a live comparison.
2. **The account never refers back to its own writing, although about one note in five has a clearly related earlier note.** Callbacks therefore start at zero, so a callback rate shows whether the memory is used at all; it cannot show that using it is good.
3. **Re-covering old ground is real but semantic, and recent.** About one note in ten has a very close earlier note (cosine of at least 0.7), almost always from the previous week. A mean top-1 cosine to the account's own history is a continuous measure with room to move, and a memory window of about a week covers most of the candidates.
4. **Binary near-duplicate rates are too small to resolve.** At a base rate near 10% a comparison of 200 tasks with half in the memory arm resolves roughly 12 percentage points, more than the rate itself. The continuous measure resolves 0.063 (0.40 SD) in the same comparison.
5. **Memory can change only the tasks that have something to retrieve.** For about 80% of the notes the nearest earlier note is below cosine 0.6, so an arm that injects nothing for them is identical to the control by construction. Randomising only the tasks for which retrieval finds a candidate removes that dilution; randomising everything dilutes any effect to about a fifth.

The shared plan of the two sessions was changed accordingly: the primary measure of the live comparison is the mean top-1 cosine to the account's own earlier items, with grounded callbacks as the secondary that shows the memory is used and a blind quality judge as the guard against "less similar because worse".

## Limits

Notes only; the agent reports 5 to 17 comments a day on top of its notes, and those are the bulk of its tasks, so comments and replies need their own baseline before a design is fixed. The cosine thresholds are conventional, not calibrated against human judgements of "the same ground". The embedding model is small; the corpus is English. The account's own prompts already carry about 14 ad hoc memory blocks (reported), which may explain the lexical floor. Nothing here is causal.

Reproduce on any JSONL of `{id, date, text, title}`: `python scripts/published_notes_baseline.py items.jsonl --embed --json aggregates.json`.
