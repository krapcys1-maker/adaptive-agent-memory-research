# AAM-E3A: calibrating a relevance threshold for own-history memory on the live account's real notes

**Status: calibration, tier E, not entered in the experiment registry; preregistered before the first judgment.** Only aggregates are recorded in this repository. The notes themselves (a local, read-only export made by the agent's own session) and the pair-level judgments stay outside it; the judgments hold note indices, cosines and ratings, never text.

## Question

The live comparison would inject earlier notes into the writer. There are two ways to get that wrong: injecting notes that are not relevant (drift, forced references back), and injecting so rarely that the arm cannot differ from the control. The first real baseline (`docs/11-research-laboratory/published-notes-baseline-2026-11-01.md`) showed that about one note in five has a clearly related earlier note, so a relevance threshold is needed, and so far the only candidate (cosine 0.55 to 0.6) is a convention. Which threshold keeps the injected notes relevant while still serving a meaningful share of the notes?

## Design

- **Data.** The 234 published notes (16 August to 1 November 2026), in publication order; for each note, every earlier note is a candidate memory, same-day earlier notes included (they are in memory by then).
- **Retrieval.** Unit-length embeddings from `sentence-transformers/all-MiniLM-L6-v2`, offline, on CPU. For every note but the first, its three most similar earlier notes by cosine (a tie goes to the more recent), 3 x 233 candidate pairs. The note being written is represented by its own text, a stand-in for the task input that the live agent would have.
- **Negative controls.** One random earlier note per note (from the fourth note on), never one of its three candidates, 230 pairs, fixed seed.
- **Judge.** `deepseek-v4-pro` in non-thinking mode at temperature 0, through the local metering proxy (hard cap 12 USD for the phase). It sees the full text of both notes and answers one line: 0 = unrelated or only a very loose connection, 1 = the same general area but a different point, 2 = the same specific story, claim or question, or a direct follow-up. The question is whether being reminded of the earlier note would help the author who is writing the new one.
- **Second judge.** `qwen2.5:14b-instruct` locally on 200 pairs drawn at random from the judged ones, to measure agreement (weighted Cohen's kappa); run when the GPU is free and reported either way. If kappa is below 0.4 the calibration is reported as judge-dependent.

## Analysis and the rule stated in advance

Relevance by cosine bin. For each threshold tau in {0.5, 0.55, 0.6, 0.65, 0.7}, injecting up to the three most similar earlier notes with cosine of at least tau: the number of injected notes, the share of notes that receive at least one (coverage), the precision (share rated 1 or 2) with a Wilson interval, the share rated 2, and the noise (share rated 0).

A threshold is **usable** if its precision is at least 0.80 and its coverage at least 0.10. The recommended retrieval threshold for the shadow log and the first live arm is the **lowest usable** one. If no threshold is usable, the finding is that this retrieval cannot serve this account well enough, and the next step is a different retrieval (for example one that also uses the note's own metadata), not a lower bar. **The judge is declared unreliable** if fewer than 90% of the random negative controls are rated 0; in that case nothing is concluded from the ratings.

## Result of the first scale (v1) and an amendment made after it was read

**v1 failed its own control.** Only 52.6% of the 230 random negative controls were rated 0 (the rule requires 90%), so by the rule stated above nothing is concluded from the v1 ratings. The judge rated about half of the random pairs 1, "the same general area", because every note of this account is about AI. For the record, the v1 table (`report-v1.md`) shows the share rated 2 rising from 0.6% below cosine 0.3 to 31.8% at 0.5 to 0.6, 77.4% at 0.6 to 0.7 and 100% from 0.7, but that is an observation made after the control failed, not a conclusion.

**Amendment, written after v1 was read and before anything was run again.** Scale v2 adds the sentence that being about AI, or about the same broad field, is not a connection, and sharpens levels 0 and 1 (`SCALES` in `scripts/retrieval_calibration.py`; the v1 text is unchanged and was checked to be identical to the one used). The pairs, the judge and its settings, the thresholds, the rule for a usable threshold and the control rule are unchanged. v2 is run once, on the same pairs, and reported together with the failure of v1. If v2's controls also fail the rule, the finding is that an LLM rating of relevance cannot be calibrated this way on this account's notes.

## Limits

The account's own texts stand in for its task inputs. A cosine from a small embedding model is a coarse proxy for relevance, and an LLM's rating of relevance is a proxy for the benefit to a writer; neither is a human judgement. The judge is a model, its prompt is one of many, and its ratings of 1 versus 2 are the least certain. Notes only: replies and articles have their own distributions. The rule above sets the bar for precision and coverage by judgement, not by a loss function.

## Files

`config.json` (parameters and the SHA-256 of the scripts), `results-v1.json` and `report-v1.md` (aggregates of the first scale), `results.json` and `report.md` (aggregates of the final run), `scripts/retrieval_calibration.py` and its tests.

Reproduce on any JSONL of `{id, date, text}`: `python scripts/retrieval_calibration.py run items.jsonl --out judgments.jsonl --base-url http://127.0.0.1:8798/v1 --model deepseek-v4-pro`, then `python scripts/retrieval_calibration.py analyse judgments.jsonl`.

## Log

Preregistered before the first judgment.

- 2026-11-01 16:19: v1 judgments analysed (control failure, see above); amendment and the digest of the script with scale v2 committed before the v2 run.
