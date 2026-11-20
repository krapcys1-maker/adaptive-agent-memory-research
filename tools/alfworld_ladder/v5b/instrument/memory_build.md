# ALFWorld ladder V5B: arms, bank and separation from the test games

Experiment name: `alfworld-ladder-r4-v5b`. V5B is V5 with the `mismatched_type` arm corrected after the V5 instrument review (see "Change from V5"). Data, bank, placebo and the other arms are unchanged.
- Code: `src/agent.py` (episode) and `src/run_episode.sh` (lab command). This is the same code as the public
  `tools/alfworld_ladder` after the V5 runner changes.
- Data: `src/build_pool_v5.py` (bank subset, units, families).
- Model under test: Qwen/Qwen3-4B-Instruct-2507-FP8 on local vLLM. No paid API is used.

## Arms

All four arms get the same base prompt: AdaMEM's ALFWorld prompt. They differ only in the block inserted after it.
Every arm then ends with the same one-line format reminder (new in V5): `Reminder: end your answer with exactly
one admissible action inside <action> </action> tags.`

| Arm | Block after the base prompt (fixed for the episode) |
|---|---|
| `none` | no block: AdaMEM's action instruction only |
| `placebo` | AdaMEM's retrieval wrapper ("Here are some task solving trajectories on similar tasks: … Retrieved Item 0 / Retrieved Item 1") with neutral filler lines (`placebo.txt`), token-matched (vLLM `/tokenize`) to the `retrieved_task` block of the same (task, seed) |
| `retrieved_task` | the same wrapper with the k = 2 bank walkthroughs whose goal text is most similar to this game's goal (content-word Jaccard over the whole bank, ties broken by a sha256 hash of (task, seed)). Ladder rung 4 |
| `mismatched_type` (new) | the same wrapper with 2 real bank walkthroughs of OTHER task types that are NOT among the `retrieved_task` picks of the same (task, seed). Candidates are ordered by goal similarity, lowest first. Every pair of the least similar quarter (at least 20 entries) is scored by block length against the `retrieved_task` block, and the closest pair is shown. If no pair is within 3%, the least similar HALF is searched. **The pool never goes beyond the least similar half**: the closest pair found there is used even if it is more than 3% off, and the real length difference is reported. Ties are broken by a sha256 hash. Real walkthrough content, unrelated task |

`memory_tokens` = tokens of the whole wrapper with its items (0 for `none`). `memory_sources` = the shown bank
tasks for `retrieved_task` and `mismatched_type`, and empty for `none` and `placebo`.

**Primary contrasts (family of 2):** `retrieved_task − placebo` and `mismatched_type − placebo`.
- If the right walkthrough helps more than any walkthrough, `retrieved_task − mismatched_type` > 0. That
  contrast is secondary.

## What changed from V4, and why

**V4 result** (300 held-out train games × 3 arms, min_tokens 8):
- solved: none 0.470, placebo 0.447, retrieved_task 0.687;
- memory − placebo: +0.240 [+0.177, +0.303] (91 gains, 19 losses);
- placebo − none: −0.023, so the placebo is neutral, as V4 intended;
- empty answers: 0 in every arm;
- verdict `measurement_problem`: untagged answers per step were memory 0.133 against placebo 0.099
  (+0.034 [+0.014, +0.053]), above the pre-registered 0.03.

Sampled untagged answers (process fields only, at most 3 per episode) were of two kinds:
- answers truncated at max_tokens during long deliberation, often about a retrieved walkthrough that does not fit
  the room;
- malformed tags such as `</action> take plate 1 </action>`.

None copied the bank's history format. The imbalance works against the memory arm, so it cannot explain the gain.
It only blocks a formal separation of content from format.

Changes for V5. Each one is the same in every arm:
1. **Bank:** a seeded (seed 5), type-stratified SUBSET of the V3/V4 bank, 60 items per type, 360 in total. Every
   item is a V4 bank item (verified), so the only change is the size of the retrieval candidate pool.
   - Freeing the other families gives a fresh test pool in all six types.
   - A smaller bank lowers the best available similarity. `metrics.top1_similarity` and
     `metrics.memory_similarity` record it per episode.
2. **New arm `mismatched_type`** (see Arms).
3. **Format reminder** at the end of every arm's prompt, including `none`.
4. **Counters that separate truncation from format:**
   - `metrics.truncated`: answers with finish_reason "length";
   - `metrics.untagged_not_truncated`: answers with no complete `<action>…</action>` pair among answers that
     were not truncated;
   - `invalid_no_action_tag` is kept for comparison with V3/V4.
5. **Not changed: the rendering of bank items.** They stay in the agent's own history format,
   `[Observation i: '…', Action i: '…']`, without `<action>` tags.
   - Rendering them with tags was considered and rejected. No V4 sample copied the bank format.
   - Tagged walkthroughs invite the model to copy a sequence of tagged actions, and the parser takes the LAST tag,
     so a copied trajectory would send a wrong action. That would be a new artefact in the two walkthrough arms
     that the placebo cannot match.

## Change from V5 (after the V5 instrument review)

The V5 reviewer raised four objections, all accepted:
- the envelope's arm text was stale;
- widening the pool to ALL other-type entries could show walkthroughs very similar to the goal, which breaks
  "unrelated task";
- the pair could overlap the `retrieved_task` pair, because retrieval does not filter by type;
- the pool level was not recorded, and pilot 5 tested an older selection.

Fixes:
- the pool is capped at the least similar half;
- the retrieved picks are excluded;
- new per-episode metrics: `mismatched_pool` (quarter or half), `mismatched_length_diff` (relative block length
  against the memory block) and `overlap_with_retrieved` (expected 0);
- pilot 5B and the length check below were run on this code.

## Pilot and length check (V5B code, before the program)

- **Length check (all 350 units, seed 0, the model's own tokenizer, CPU only;** `length_check.json`,
  `src/check_lengths.py`):
  - mismatched pool used: quarter for 109 units, half for 241;
  - overlap with the retrieved pair: 0 in every unit;
  - goal Jaccard of the shown mismatched items: at most 0.0 (no shared content word with the goal in any unit).

  Block length relative to `retrieved_task` (mean 822 tokens):

  | arm | mean | min | max | within 3% | within 5% |
  |---|---|---|---|---|---|
  | placebo | +0.06% | −0.7% | +1.0% | 100% | 100% |
  | mismatched_type | −0.7% | −15.8% | +9.6% | 89.4% | 93.4% |

  Capping the pool at the half costs some length matching (V5: 93.7% within 3%) in exchange for unrelated
  content. The length-sensitivity analysis below covers the 6.6% of units that are more than 5% off.

## Earlier pilot (V5 code, older selection, kept for the record)

- **Pilot 5 (V5):** 3 pilot games × 4 arms, seed 4, full lab path, `pilot/pilot5_out.jsonl`. It ran with the first
  version of the pair search (400 random pairs); only the mismatched selection changed after it.
  - 12/12 results, 0 errors;
  - empty retries 0 and truncated answers 0 in every arm;
  - untagged_not_truncated: none 2, placebo 11, retrieved_task 3, mismatched_type 6, almost all in the four
    50-step failures;
  - format reminder present in every arm.
- V5 length check with the earlier exhaustive search, which could widen to all other-type entries: mismatched
  −0.4% mean, 93.7% within 3%. That rule was dropped after the review.

- **Pilot 5B (V5B code, this pinned agent.py):** 3 pilot games × 4 arms, seed 6, full lab path,
  `pilot/pilot5b_out.jsonl`.
  - 12/12 results, 0 errors, empty retries 0 in every arm;
  - truncated: one answer, in retrieved_task;
  - mismatched_type: pool quarter twice and half once, `overlap_with_retrieved` 0 each time, length difference
    −0.2%, −0.1% and 0.0%;
  - memory and placebo blocks token-matched (647/647, 932/935, 854/853);
  - untagged_not_truncated: none 0, placebo 10, retrieved_task 0, mismatched_type 15, almost all in the 50-step
    failures.

## Test games (`units.json`)

- 350 `train` games, one trial per family (seed 5). Per type: pick-and-place 60, clean 60, cool 60, heat 60,
  two-object 60, look-in-light 50. Look-in-light is capped by availability.
- Every family is in NONE of:
  - the V5 bank (360);
  - the V1–V3 valid_seen units (137 families);
  - the pilot games (25, `pilot_games.txt`);
  - the 300 games V4 measured.

  Overlap with each: 0 (`pool_manifest.json`).
- These are seen rooms: bank and units come from the same scenes, as in V3/V4.
- `valid_unseen` is never read by any script of this approach.

## Families (`families.json`)

- Family = the ALFWorld task directory (same task type, objects, receptacle and scene). Two trials of one
  directory share a family.
- The map covers the 350 units and the 360 bank tasks.

## Bank (`data/bank.jsonl`)

- Source: ALFWorld `train` planner walkthroughs, replayed in the installed text environment (current action
  syntax). Every item replayed to a win with every action admissible.
- V5 subset as described above. The 134 train families that also occur in valid_seen were already excluded from
  the original bank.
- The planner knows where objects are, so walkthroughs never search.
- Rendering of one item:
  - `Task: <goal>.`;
  - then one line per step, `[Observation i: '<obs>', Action i: '<action>']`;
  - then `Final observation: '<obs>'`;
  - observations have whitespace collapsed and are cut to 240 characters.

## Sampling parameters

- temperature 0.7, max_tokens 2048, min_tokens 8, max 50 steps, history of the last 50 (observation, action)
  pairs in AdaMEM's format, k = 2, format reminder on.
- vLLM: `--max-model-len 16384 --gpu-memory-utilization 0.80 --enforce-eager --seed 0`. The request seed is a
  sha256 hash of (unit, arm, seed, step).
- One strict parser for every arm:
  - the last `<action>…</action>` of the answer, matched case-insensitively to the admissible commands;
  - anything else goes to the game as written and counts in `invalid_actions`.
- Reported per result:
  - `solved`, `memory_sources` and `actions` (the full sequence);
  - `metrics`: `memory_tokens`, `tokens`, `steps`, `invalid_actions`, `invalid_no_action_tag`, `truncated`,
    `untagged_not_truncated`, `empty_retries`, `top1_similarity`, `memory_similarity`, `mismatched_pool`,
    `mismatched_length_diff`, `overlap_with_retrieved`, and the sampling settings;
  - `evidence`.

## Format criteria (pre-registered; the lab checks them)

- `untagged_not_truncated` per step: walkthrough arm − placebo ≤ 0.03, or the 95% unit-bootstrap interval
  includes 0. This applies to each of `retrieved_task` and `mismatched_type`.
- `empty_retries` per step: same rule.
- `truncated` is reported per arm as behaviour, not as a format failure.
- If a criterion fails, the conclusion must say that content and format are not separated for that arm. The
  primary result is still reported.

## Definitions and edge cases

- **solved:** the environment reports a win within 50 agent steps. Every step counts, including steps whose answer
  was unparsed or not admissible.
- **Unparsed answers in the history:** stored as the tag text, or "None" if there is no tag. This is the same in
  every arm.
- **Server failure or context overflow:** after 4 failed attempts `chat()` raises `ServerError`. The episode is
  then an error (no `solved`), and the lab retries it. It is never recorded as unsolved.
- **Hash stability:** tie-breaks, pair sampling and request seeds come from sha256 of the joined values, not
  Python's `hash()`.

## Scope of the conclusion

- `retrieved_task − placebo`: showing two goal-similar expert walkthroughs, against a same-length neutral block.
- `mismatched_type − placebo`: showing two real walkthroughs of unrelated tasks, against the same block.
  Together they separate "any walkthrough" from "the right walkthrough". They do NOT separate retrieval by
  similarity from random same-type walkthroughs (`random_same_type`, rung 3, implemented but not in this program).
- A positive result means "retrieved expert demonstrations help this 4B agent on held-out train games in seen
  rooms". It does not mean "the agent's own experience helps", and it does not transfer to unseen rooms.
- The bank is half the V4 bank, so effect sizes are not directly comparable with V4. The similarity metrics
  quantify the difference.

## Planned secondary analyses (written before the program starts)

- **Same-room sensitivity:** the primary contrasts repeated without the units whose shown items share the room
  number with the unit. In V4, dropping 29 such units changed memory − placebo from +0.240 to +0.247.
- **Similarity and gain (input for a relevance gate):** the gain of `retrieved_task` over placebo per unit,
  against `top1_similarity`.
- **Truncation:** `truncated` per step, by arm.
- **Per type:** the primary contrasts by task type (descriptive).
- **Length sensitivity:** `mismatched_type − placebo` repeated without the units whose `mismatched_length_diff` is
  above 5% in absolute value (6.6% of units in the length check).

## Known limits

- The bank holds expert walkthroughs, not the agent's own successes.
- The similarity key is lexical (content-word Jaccard), not an embedding.
- Seen rooms only. valid_unseen stays sealed for a single confirmation.
