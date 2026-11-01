# AAM-E2-FU: does memory help when there is something to remember, and do no harm when there is not?

**Status: exploratory, tier E, not entered in the experiment registry; preregistered before the first record.** Everything is synthetic: a fictional learner, items and prompts authored by an agent, one provider's model as the writer. It says nothing about any real account.

## Why this experiment

AAM-E1-SIM and AAM-E1-DS gave the writer notes about its own earlier entries in a stream where memory had nothing to add (every item was self-contained). The results were small and depended on the writer: with a 7B model raw notes increased repetition and lowered judged quality, with the strong model they changed little, and in both short traces produced the most explicit references back. The first real baseline of a live account (`docs/11-research-laboratory/published-notes-baseline-2026-11-01.md`) says that about one note in five has a clearly related earlier note, mostly from the previous week, and that the account never refers back to its own writing. So the question that matters for a live agent is not whether memory helps on average but whether it helps **where an earlier note carries information the writer does not otherwise have, without hurting where it does not**. This experiment builds that situation on purpose.

## Design

- **Writer.** `deepseek-flash`, the provider's flash model, in non-thinking mode through the local metering proxy (`scripts/metered_proxy.py`; hard cap 12 USD for the phase, ledger without message content). Temperature 0.8, top-p 0.95, at most 260 tokens. A short persona card is in every arm.
- **Stream.** 60 simulated days, one item a day. On 12 days (a fifth, mostly 1 to 3 days after the story, none later than 7 days, none before day 8) the item is a **follow-up**: it restates a story the learner wrote about earlier and adds a development ("Follow-up on the story that ...: ..."). The other 48 days bring fresh stories. 60 stories x (fresh item, development) are authored in `scripts/followup_memory_sim.py`; they refer to no real company, person or product. Stream seeds 11 to 16: six streams, so 72 follow-ups and 288 fresh days per arm.
- **Arms.** They differ only in what the writer is shown about its own earlier notes; the accompanying instruction is the same text in every arm that has notes.

| Arm | What the writer is shown |
|---|---|
| A0 | nothing |
| A1 | the three earlier notes whose task input is most similar to today's, always, in full (raw retrieval with no relevance bar) |
| A2 | the same, but only notes whose similarity reaches the threshold (possibly nothing), in full |
| A0i | (control) the same header and instruction as the arms with notes, with "(none)" as the notes |
| A3 | the same threshold, but a short trace (gist, angle, left open) of each matching note instead of the note, written by the same model at temperature 0 |

- **Retrieval.** The embedding (`sentence-transformers/all-MiniLM-L6-v2`, offline, CPU) of today's item against the embedding of each earlier item, as a live pipeline that stores task inputs would do. **Threshold calibrated beforehand from the items alone**, on streams that are not used in the experiment (seeds 100 to 102, no model text): the highest threshold in steps of 0.05 that keeps 90% of the true follow-up -> story pairs. Result: **0.70** (follow-up cosines: minimum 0.57, median 0.88; 0 of 141 fresh days have any earlier item at 0.70 or above). This retrieval is close to ideal by construction; a real one is worse (the live account's notes are in a narrow field), which the experiment does not test.

## Measures

Deterministic, per note, on days 8 to 60: `overlap4` (largest share of the note's 4-grams that one earlier note of the same arm contains), explicit references back (`callback_ext` of the harness patterns of AAM-E1-SIM), **grounded callbacks** (an explicit reference in a follow-up note whose embedding is within cosine 0.5 of the arm's own note on the original story), **spurious callbacks** (an explicit reference in a note on a fresh story), length.

A blind judge scores each note from 1 to 5: FIT to the item, FRESH against the earlier notes it is shown, QUALITY overall, and, for follow-ups only, **CONTINUITY** (builds on the learner's earlier note on that story accurately and specifically). The judge sees the item, the new note, and for a follow-up the arm's own earlier note on the story, for a fresh item up to two earlier notes of the same theme; it is not told the arm. Judges: `deepseek-v4-pro` through the proxy on all notes (the same provider as the writer; the self-preference risk is the same for every arm) and `qwen2.5:14b-instruct` locally (a different family) on all follow-ups and a random quarter of the fresh notes. Planted controls as in AAM-E1-SIM: 12 notes replaced by the learner's earlier note on the story, 12 replaced by a note on another story; a dimension is informative only if at least 75% of its controls score 2 or lower on it (FRESH and, for follow-ups, CONTINUITY for the copies; FIT for the replacements).

## Analysis, practical thresholds and readings stated in advance

Paired contrasts over (stream, day), percentile bootstrap (10,000 draws, seed 20261101, 95%), by stratum; the intervals are approximate and probably too narrow because notes in a stream depend on each other. The primary measure is the **judged CONTINUITY of follow-up notes** (1 to 5); the practical threshold is 0.5 points. Guards: the **judged QUALITY of fresh notes** (a drop of 0.15 or more with an interval below zero is harm) and spurious callbacks.

| Reading | Condition |
|---|---|
| Memory helps where it is relevant | A2 or A3 exceeds A0 on follow-up CONTINUITY by 0.5 or more with the interval above zero, with both judges agreeing in sign, and the fresh-stratum guards hold |
| Always-on memory harms | A1 is below A0 on fresh-stratum QUALITY by 0.15 or more with the interval below zero |
| Traces against notes | A3 - A2 on follow-up CONTINUITY: 0.3 or more means traces are better, -0.3 or less means notes are better, otherwise they are equivalent here |
| Nothing moves | none of the above holds |

A judge dimension that fails its controls is reported as uninformative and not used for a reading. A disagreement in sign between the two judges is reported as unresolved. Thresholds are not retuned after the run, and a null is reported as one.

## Amendments made before any record was read

Written on 2026-11-01 while the writer processes were still running. No record had been read: only row counts and the exit state of the processes.

1. **A stream could not be built.** The process for stream seeds 11 and 12 stopped at seed 12 with "no free base for a follow-up on day 26": the first draw of follow-up days left one follow-up without a free earlier story. (Seeds 5 and 23 fail the same way.) `make_stream` now redraws in that case. The streams that built on the first draw are unchanged, and a test pins their fingerprints (seeds 11, 13, 14, 15, 16 and the calibration seeds 100 to 102); stream 12 is run now with the amended script.
2. **A control arm for the instruction.** Arm **A0i** gets the same header and instruction as the arms with notes, with "(none)" in place of the notes. Without it every contrast against A0 is notes plus instruction, which an independent review of AAM-E1-SIM pointed out and which applies here too. A0i is run on all six streams after the other arms, with the amended script (its prompts and the arms A0 to A3 are untouched by the amendment). The rule for "memory helps where it is relevant" now requires the gain on follow-up CONTINUITY against **both** A0 and A0i, and A0i - A0 is reported.
3. **No change to the primary measure, the threshold of 0.70, or the readings.** The deterministic overlap is secondary here for a reason the same review gave for AAM-E1-SIM: a repetition measure that is already near its floor cannot show a reduction, so the primary is judge-based.

## Limits

One provider's model as the writer, one persona, sixty authored stories, six streams. Items restate the story they develop, which makes retrieval easy; a live follow-up may not. The judge is a model. Continuity is judged against the arm's own earlier note, so an arm whose earlier notes are poor is judged against a poor reference. The experiment does not test learning from outcomes, the persona, or any real reader.

## Files

`config.json` (parameters and the SHA-256 of the scripts), `records.jsonl`, `run-meta.json`, `proxy-summary.json`, `balance-*.json`, judgments, `results.json` and `report.md` (added as they exist).

## Log

Preregistered before the first record.

- 2026-11-01 16:35: the analysis and judge script (measures, planted controls, readings applied mechanically) and its nine tests were committed, with its digest in config.json, while the three writer processes were running (seed 11 day 52/60  +4 notes  elapsed 156s) and before any record had been read.

- 2026-11-01 16:38: amendments above committed with refreshed digests while the writer processes were running (seed 14 day 47/60  +4 notes  elapsed 345s); no record had been read.
