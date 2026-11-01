# AAM-E5-REPLAY: the memory arms replayed on the live account's real published history

**Status: data-based feasibility test, tier E, not entered in the experiment registry; preregistered before the first call.** The owner's rule is that tests rest on data and not on guesses, and that the agent's implementer (the NIE session) builds only what passed. AAM-E2-FU showed a benefit of thresholded memory on authored stories with near-ideal retrieval. This replays the same arms on the account's own 234 published notes (16 August to 1 November 2026), so that the recurrence of topics is the real one and retrieval is imperfect.

**Privacy.** The notes are the account's public texts, exported read-only by the agent's own session into a local folder outside both repositories. The notes written by the model are synthetic but conditioned on that history, so they stay in the same local folder too. Only aggregates are published here.

## Design

- **Tasks.** Each real note i from the 21st on (214 tasks; the first 20 are history only). The task input is a **brief**: one neutral sentence, at most 25 words, written once by `deepseek-flash` at temperature 0 from the note, without quoting it or mentioning earlier notes.
- **Retrieval.** Embedding (`sentence-transformers/all-MiniLM-L6-v2`, offline) of the brief against the real earlier notes (same-day earlier notes included); the three nearest. **Threshold:** the value above which a fifth of the tasks have a candidate, matching the 20.6% of real notes that have a related earlier note at note-to-note cosine 0.6 (computed from briefs and notes only, before any new note is written). Retrieval from a one-sentence brief is deliberately worse than ideal.
- **Arms.** R0 nothing. R0i the same header and instruction as the arms with notes, with "(none)". R1 the three nearest earlier notes always, in full. R2 the same only above the threshold. R3 above the threshold, a short trace (gist, angle, left open; written once per real note by the same model at temperature 0) instead of the note. Same writer (`deepseek-flash`, non-thinking, temperature 0.8) and the generic persona card of AAM-E2-FU, so only the memory differs.
- **Judge.** `deepseek-flash` through the flash-only metering proxy (cap 12 USD for the phase), comparing two notes at a time in both orders: which is the better public note on the item, given what the author has already written (fits, adds something new, refers to the earlier note only where that helps, no repetition, no forced reference). On tasks with a candidate the judge sees the top earlier note; on the others it sees none, and a sample of 80 of them is judged. **Planted control:** the model's R0 note against a copy of the earlier note, on 12 candidate tasks; the judge is informative only if the note wins at least 75% of them.

## Measures, and the readings stated in advance

Pairwise win rate of the first arm over the second, per task (both orders averaged), with a percentile bootstrap over tasks (10,000 draws, seed 20261101). Also, by code: explicit references back, grounded ones (a reference whose note is within cosine 0.5 of the top earlier note), and length.

| Reading | Condition |
|---|---|
| Thresholded memory helps on real candidates | R2 or R3 beats both R0 and R0i with a win rate of at least 0.60 and an interval above 0.5, and the judge is informative |
| A thresholded arm harms the other tasks | its win rate over R0 on the sampled non-candidate tasks has an interval entirely below 0.5 |
| Always-on memory harms the other tasks | R1 over R0 on the same tasks, same condition |
| Traces against notes | R3 over R2 on candidates: traces better at 0.60 or more with the interval above 0.5, notes better at 0.40 or less with the interval below 0.5, otherwise equivalent here |

About 40 tasks have a candidate, so the intervals will be wide; a null is a result. Nothing here is a claim about readers: no reader sees these notes.

## Limits

The persona is generic and not the account's, so style is not the account's. The brief is written from the note and so carries its topic into the task. The judge is a model of the same provider as the writer. Notes only: replies and articles have their own distributions. The threshold is matched to a measured share and is not calibrated against human judgements of relevance (AAM-E3A could not certify one).

## Files

`config.json`, `results.json` (aggregates), `scripts/replay_memory_sim.py` and its tests. Reproduce: `python scripts/replay_memory_sim.py prepare|write|judge|analyse --items items.jsonl --workdir DIR`.

## Log

Preregistered before the first call.
