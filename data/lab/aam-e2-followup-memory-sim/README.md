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

4. **A pairwise judge for the follow-up stratum.** The pointwise judge showed a ceiling effect in AAM-E1-DS, so a second judge compares notes in pairs. For each follow-up item and each pair of arms (A1-A0, A2-A0, A3-A0, A2-A1, A3-A2, A0i-A0, A2-A0i, A3-A0i) it sees the item, the arm's earlier note on the story and the two notes, in both orders, and answers which builds better on the earlier note (WINNER: 1, 2 or TIE; `deepseek-v4-pro` through the proxy). Control: the real A0 note against a copy of the earlier note (12 follow-ups, both orders); the real note must win in at least 75% of these or the judge is not used. Reading: an arm wins against a no-notes arm if its win rate is at least 0.60 with the interval above 0.5, against both A0 and A0i. The pairwise judge counts as one more judge in the rule for "memory helps where it is relevant": every informative judge must agree.

## Results (written on 2026-11-01 after the preregistered analyses had been run)

**The run.** 1,800 notes (6 streams x 60 days x 5 arms including the control A0i), `deepseek-flash` as the writer, in several processes; the proxy summaries are in `proxy-summary-*.json` and the run metadata in `run-meta-*.json` (the processes for streams 11, 13 to 16 ran with the first version of the script, stream 12 and the control arm with the amended one, whose changes cannot affect the other arms).

**A deviation, and its repair.** The preregistration named `deepseek-v4-pro` as the judge. The owner had authorised `deepseek-flash` only. The first judging pass used the pro model, which the owner objected to; the pro model was then **blocked at the proxy** (`scripts/flash_only_proxy.py`: any other model is answered with 403 and never forwarded), and every judge of this experiment was **run again with `deepseek-flash`, which is the judge of record** below. The pro results (`*-pro.*`) are kept, labelled, as an already-paid secondary check; they point the same way (pairwise win rates 0.81 and 0.79 for A2 and A3 over A0, and always-on memory lowering fresh quality by 0.21; the pro pointwise continuity sits at 5.0 for every arm).

**Deterministic measures (days 8 to 60; `report-measures.md`).**

| Arm | explicit reference back in follow-ups | grounded reference in follow-ups | explicit reference on fresh items ("spurious") | overlap4 |
|---|---|---|---|---|
| A0 none | 2.8% | 2.8% | 0.0% | 0.036 |
| A0i instruction only | 5.6% | 4.2% | 0.0% | 0.034 |
| A1 always-on raw | 66.7% | 55.6% | **30.1%** | 0.040 |
| A2 thresholded raw | 63.9% | 48.6% | 0.0% | 0.032 |
| A3 thresholded traces | 83.3% | **73.6%** | 0.0% | 0.035 |

The instruction without notes (A0i) does not make the writer refer back (A0i - A0 not distinguishable from zero), so the references come from the notes. Always-on raw retrieval makes the writer refer back to earlier notes on 30% of the fresh items, where they are irrelevant. Traces give 25 points more grounded references than raw notes in the same situation (A3 - A2 +0.250 [0.139, 0.375]). Lexical overlap and length do not differ between arms.

**Judge of record, `deepseek-flash`** (`report-judges.md`; it passed its planted controls: 100% of the copies and of the other-story replacements noticed, pairwise control 24 of 24).
- Pointwise continuity of follow-up notes (1 to 5): A0 4.72, A0i 4.44, A1 4.94, A2 4.93, A3 4.97. Against A0: A2 +0.21 [0.08, 0.33], A3 +0.25 [0.14, 0.38]; against A0i: A2 +0.49 [0.33, 0.64], A3 +0.53 [0.39, 0.68]. The instruction alone lowers continuity (A0i - A0 -0.28 [-0.46, -0.11]): told to refer back with nothing to refer to, the writer does worse.
- Pairwise (which note builds better on the earlier note, both orders; win rate of the first over the second): A2 over A0 0.847 [0.778, 0.910], A3 over A0 0.875 [0.806, 0.931], A2 over A0i 0.882, A3 over A0i 0.854, A2 over A1 0.722 [0.646, 0.799], **A3 over A2 0.694 [0.625, 0.764]**, A0i over A0 0.528 (no preference).
- On fresh items always-on memory is worse (A1 - A0: quality -0.17 [-0.26, -0.09], fit -0.22, freshness -0.48); the thresholded arms are not (quality -0.03 [-0.11, 0.04] for both).

**The readings stated in advance, applied mechanically.** *Memory helps where it is relevant:* the pointwise judge says no and the pairwise judge says yes, so by the rule (all informative judges must agree) the result is **unresolved**. The disagreement has a plain cause: the pointwise scale has a ceiling (A0 already scores 4.72, so the largest possible gain is 0.28 and the practical threshold of 0.5 could not be met by any arm), which is the same kind of defect as the threshold of AAM-E1-SIM; the pairwise judge has no ceiling and prefers the memory arms in 85 to 88% of the comparisons, with the instruction-only control at chance. *Always-on memory harms fresh notes:* **yes**. *Traces against notes:* equivalent by the pointwise judge, traces better by the pairwise judge (0.694) and by grounded references (+25 points).

**Reading.** Where an earlier note carries information the writer does not otherwise have, giving the writer that note (or a short trace of it) makes the follow-up note refer back to it accurately far more often than chance and, by the pairwise judge, makes it a better continuation; the benefit is not the instruction and not length. Injecting memory regardless of relevance does damage: spurious references on 30% of fresh items and lower judged fit, freshness and quality. A relevance threshold removes the damage, and a short trace is at least as good as the full note and better on grounded references and in the pairwise comparison. This is the first result of this series in which memory helps a writer, and it holds only where retrieval is close to ideal: the threshold of 0.70 was calibrated on item texts that restate their story and let through no spurious match on fresh days. It is one provider's model judged by the same provider's model, on authored stories.

**Decision recorded for the live-memory plan.** (1) The first live arm is **thresholded traces**; no always-on injection. (2) The threshold has to be calibrated on the live retrieval (AAM-E3A did not certify one; 0.6 on note-to-note cosine is a post-hoc starting value), and the live comparison should use a pairwise judge, because pointwise scores saturate. (3) The next test is the one this design avoids: imperfect retrieval, with follow-ups that do not restate their story and fresh items of the same theme as distractors.

## Limits

One provider's model as the writer, one persona, sixty authored stories, six streams. Items restate the story they develop, which makes retrieval easy; a live follow-up may not. The judge is a model. Continuity is judged against the arm's own earlier note, so an arm whose earlier notes are poor is judged against a poor reference. The experiment does not test learning from outcomes, the persona, or any real reader.

## Files

`config.json` (parameters and the SHA-256 of the scripts), `records.jsonl`, `run-meta.json`, `proxy-summary.json`, `balance-*.json`, judgments, `results.json` and `report.md` (added as they exist).

## Log

Preregistered before the first record.

- 2026-11-01 16:35: the analysis and judge script (measures, planted controls, readings applied mechanically) and its nine tests were committed, with its digest in config.json, while the three writer processes were running (seed 11 day 52/60  +4 notes  elapsed 156s) and before any record had been read.

- 2026-11-01 16:38: amendments above committed with refreshed digests while the writer processes were running (seed 14 day 47/60  +4 notes  elapsed 345s); no record had been read.

- 2026-11-01 16:45: the pairwise judge (amendment 4) and its tests were committed with the refreshed digest of the analysis script while the control-arm runs were finishing; no E2 record had been read.

- 2026-11-01 16:57: results written. Two things changed after records were read, both disclosed above: the judge model (pro replaced by flash on the owner's instruction, every judge re-run) and the judge-analysis command line (it rejected NAME=PATH pairs; fixed and tested, no effect on any number). Digests refreshed.
