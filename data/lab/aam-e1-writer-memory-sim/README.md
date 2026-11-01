# AAM-E1-SIM: does a writing agent's own history change what it writes? (offline pilot)

**Status: exploratory, tier E, not entered in the experiment registry.** The design below was written before the first registered record existed. Everything is synthetic: a fictional columnist, prompts and news hooks authored by an agent, one small local model. Nothing here says anything about a real agent, a real account or real readers.

## Question

The operating doctrine asks what the atomic unit of agent memory is (question 1) and how the future utility of a memory is measured causally (question 3). The live-memory evaluation draft would test, on a real agent, whether showing it its own earlier output reduces repetition and increases explicit references back. This pilot runs the same comparison offline, at no cost and no risk, before any real account is touched:

- Does showing a writer its own earlier entries make it repeat itself less, refer back more, and stay on the day's topic?
- Is a short trace of each entry (gist, angle, what was left open) a better unit than the entry itself?
- Do dynamic importance and association, the two ideas the research direction names, add anything on top of plain traces?

It can rule things out. If raw history raises repetition, it should not be injected into a live agent as it is. If no arm moves the measures, either the measures have no headroom on generated text or memory does not matter for this writer, and nothing may be inferred about any real agent. Either way it also tells us whether the repetition and callback measures of the shadow-audit specification behave on text that a model actually wrote.

## Design

**Writer.** `qwen2.5:7b-instruct` through a local Ollama server (digest and version are written to `run-meta.json`). Temperature 0.8, top-p 0.95, at most 320 tokens, context 4096. For a given stream seed and day, every arm uses the same sampling seed. A fixed persona card (a dry columnist with three recurring motifs) is in the system prompt of every arm.

**Stream.** 36 simulated days. Six themes (meetings, email and messages, remote and hybrid work, learning and skills, money and prices, habits and routines) each have six news hooks. Every 6-day round contains each theme once, in a seeded order, with a fresh hook, so each theme returns six times and there is always something earlier to repeat or to refer back to. Stream seeds: 1, 2, 3. A small deterministic generator is used for the order, so the stream does not depend on the Python version.

**Arms.** They differ only in the notes about the writer's own earlier entries that are placed in the prompt. The instruction that accompanies the notes is the same text in every arm that has notes.

| Arm | What the writer is shown |
|---|---|
| M0 | nothing (no notes, no instruction) |
| M1 | the last three entries in full (what a naive agent loop does) |
| M2 | the three earlier entries most similar to today's trigger, in full (raw own-history retrieval) |
| M3a | one short trace per earlier entry (gist, angle, left open, five keywords, written by the same model at temperature 0 right after the entry); the three most similar traces |
| M3b | M3a plus dynamic importance and association (below) |

**Retrieval (M2, M3a, M3b).** BM25 (k1 = 1.2, b = 0.75) over lower-cased content words; the query is the theme plus the hook; each document carries its theme as a tag; a tie goes to the more recent entry; nothing is shown when no document scores above zero.

**M3b dynamics.** Importance of a trace at day t is `1 + 0.5 * uses - 0.5 * (t - day_of_trace) / 30`, kept between 0.25 and 3; the retrieval score is the BM25 score times importance, and the top two are shown. A trace gains one use when a later entry that was shown it contains an explicit reference to earlier writing and shares at least two of its keywords. Traces are linked when their keyword sets overlap (Jaccard at least 0.2, weight = Jaccard) and when they were used together (+0.25, capped at 1). One more trace, the strongest neighbour of the two shown with link weight at least 0.15, is added. No parameter was tuned.

## Measures

All are computed by deterministic code on each arm's own entries, for the **analysis days 7 to 36** (from the second round on, so every theme has an earlier entry). Tokens are lower-cased `\w+` words; n-grams are word n-grams.

- **overlap4 (primary).** For an entry, the largest share of its 4-grams that one earlier entry of the same arm and stream already contains (`repetition_overlap` of `scripts/shadow_baseline_measures.py`, window long enough to cover the whole run). Lower means less repetition.
- Secondary: `union_novelty` (one minus the share of its 4-grams found in any earlier entry), `overlap8` (the same as overlap4 with 8-grams), `rep_rate` (share of entries with overlap4 of at least 0.25).
- **Callbacks.** `callback_strict` (the shadow-audit definition: an explicit phrase, or an earlier title quoted in full) and `callback_ext` (the harness patterns for explicit reference to earlier own writing, and a "day N" reference to an earlier day). Narrated life events ("last week I tried ...") deliberately do not count. In M0 the rate should be near zero; if it is not, the detector is reported as unreliable.
- **hook_coverage (guard).** Share of the distinct content words of the day's hook that appear in the entry. A drop of 0.10 or more against M0 voids a repetition win: repeating less by drifting off topic is not a win.
- `words` (length), and for the arms with notes `shown_copy8`, the share of the entry's 8-grams that occur verbatim in the notes it was shown.

## Analysis (fixed here, implemented before any outcome is read)

- Paired contrasts per measure, entry by entry over (stream seed, day): M1-M0, M2-M0, M3a-M0, M3b-M0, M3a-M2, M3b-M2, M3b-M3a.
- Percentile bootstrap, 10,000 draws over (seed, day) pairs, bootstrap seed 20261101, 95% interval. Entries of one arm depend on each other through the history, and there are only three streams, so the intervals are approximate and probably too narrow. Per-stream means are printed next to them so that sign agreement across streams can be judged.
- Practical threshold for the primary measure: an absolute difference of 0.05 in overlap4. The value is a guess at what 90 paired entries per arm could resolve if the standard deviation of a paired difference is near 0.1; the actual standard deviation is reported, not used to retune the threshold.
- No outcome is read before the analysis script is committed. Progress checks look at row counts and parse failures only.

## Readings stated in advance

| Reading | Condition on overlap4 (and the guard) | What it would mean for the live-memory plan |
|---|---|---|
| Raw history helps | M2-M0 at most -0.05, interval excludes 0, hook_coverage drop below 0.10 | raw own-history is a viable arm B in the live comparison; traces must beat it to be worth their cost |
| Raw history hurts | M2-M0 at least +0.05, interval excludes 0 | do not inject raw entries into the live agent; use traces or an avoid-list |
| Traces beat entries | M3a-M2 at most -0.05, interval excludes 0, guard holds | the unit of memory matters; carry traces into the live design |
| Dynamics add | M3b-M3a at most -0.05, interval excludes 0, guard holds | keep importance and association; if not, drop them |
| Nothing moves | every difference below 0.05 in size | no inference about a real agent; the measure or the writer has no headroom here |

Callback rates, copying and length are reported for every contrast and read as context for the table above, not as extra chances to win.

## Limits

One small quantised model; one synthetic persona; six themes; three streams of 36 days. Lexical overlap cannot judge quality, only copying and drift, so the guard and the printed examples carry that burden. No readers are simulated, so nothing about learning from outcomes is tested. The persona's invented past ("last week I tried ...") is fiction and is not a memory. The author read the entries of two eight-day smoke runs (stream seeds 98 and 99, not part of the data) to debug the harness; the prompt's reply format was changed after them, before any registered record existed. In the smoke run an M2 entry ignored the day's trigger and reused motifs from the entries it was shown, which is why the guard exists.

## Files

- `config.json`: the frozen parameters and the SHA-256 of the scripts.
- `run-meta.json`: model digest, Ollama version, options, harness digest (written by the first run).
- `records.jsonl`: one line per entry (text, notes shown, trace, token counts).
- `scripts/writer_memory_sim.py` (harness) and `tests/test_writer_memory_sim.py`.

Reproduce the run: `python scripts/writer_memory_sim.py --records PATH --seeds 1 2 3` with the model named in `config.json` served by a local Ollama. The entries themselves are not bit-reproducible across machines; the analysis of the stored records is.

## Addendum A: a blind LLM judge (written on 2026-11-01 while the registered run was still in progress, before any outcome was read)

The lexical measures cannot see quality. After the run, `scripts/judge_writer_memory_sim.py` scores every analysis-day entry (days 7 to 36 of the three streams and five arms) with `qwen2.5:14b-instruct` at temperature 0, blind to the arm. Four scores from 1 to 5: fit to the day's trigger, freshness against the same author's earlier entries on the theme (the latest two, taken from the same arm), voice against the persona card, and overall quality.

Planted controls show whether the judge can tell anything: 12 entries replaced by a copy of the author's previous entry on the theme and 12 replaced by an entry on another theme, drawn from arm M0 with a fixed seed. A dimension counts as informative only if at least 75% of its controls score 2 or lower on it (freshness for the copies, fit for the replacements); otherwise it is reported as uninformative and not used.

Guard: an arm whose mean quality is lower than M0 by 0.30 or more, with a bootstrap interval below zero, gets no credit for a repetition win. The judge is a 14B model of the same family as the 7B writer, which is a limit and not a remedy; an independent judge (another family, or a human sample) would be a further step. The judge's results are reported beside the registered analysis and never instead of it.

## Addendum B: how far this simulation can speak for the live account (written on the same occasion)

A read-only snapshot of the live account's published notes (see `docs/11-research-laboratory/published-notes-baseline-2026-11-01.md`) shows lexical repetition at the floor (mean 4-gram overlap with one earlier note 0.018) and no explicit callback, while about one note in five has a semantically related earlier note, mostly from the previous week. This simulation is a stress test: every entry has a same-theme predecessor six days earlier. Its effect sizes cannot be carried over to the live account without scaling them to the share of tasks that have something to retrieve, which is about a fifth there.

## Log

Preregistered before the first registered record.

- 2026-11-01 15:38: analysis script and its tests committed, digest added to config.json, while the run was in progress (seed 1 day  5/36  +5 entries  elapsed 114s) and before any outcome had been read. The harness digest is unchanged.
- 2026-11-01 16:02: addenda A (blind judge with planted controls) and B (external validity against the live account's baseline), the judge script and the backends module committed, digests added to config.json; the registered run was in progress (seed 2 day 34/36  +5 entries  elapsed 1609s) and no outcome had been read.
