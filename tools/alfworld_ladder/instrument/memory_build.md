# ALFWorld ladder: arms, bank and separation from the test games

Experiment name: `alfworld-ladder-r4-v1`. Code: `src/agent.py` (episode), `src/run_episode.sh` (lab command),
`src/build_data.py` (units, families, bank). Model under test: Qwen/Qwen3-4B-Instruct-2507-FP8 on local vLLM.
No paid API is used.

## Arms

| Arm | What the agent sees in addition to the no-memory prompt |
|---|---|
| `none` | nothing. The prompt is exactly AdaMEM's no-memory ALFWorld prompt (baseline). |
| `placebo` | AdaMEM's retrieval wrapper ("Here are some task solving trajectories on similar tasks: … Retrieved Item 0 / Retrieved Item 1"), with neutral filler lines from `placebo.txt` in place of the trajectories. The filler is token-matched (vLLM `/tokenize`) to the `retrieved_task` block of the same (task, seed). Same position, same wrapper, same two-item layout. |
| `retrieved_task` | the same wrapper with k = 2 expert walkthroughs from the bank whose goal text is most similar to this game's goal (content-word Jaccard over the WHOLE bank, ties broken by a hash of (task, seed)). Ladder rung 4: whole trajectories retrieved by task. Measured on the 137 units (independent audit, seed 0): 21% of units get at least one walkthrough of another task type (13% of items, mostly pick-and-place ↔ pick-two); in 114 of 137 units the second item is decided by the tie-break. This is the arm as described, not a defect. |

The block is chosen once per episode and shown at every step. `memory_tokens` = tokens of the whole wrapper with
its items (0 for `none`). `memory_sources` = the two bank task ids for `retrieved_task`, empty for `none` and `placebo`.

Not in this program's catalogue but implemented in the code: `random_same_type` (ladder rung 3, two random bank
walkthroughs of the same task type; the TRAD "Random" control). It is the natural second treatment.

## Test games (`units.json`)

- The 140 games of ALFWorld `valid_seen` (`json_2.1.1/valid_seen/<task dir>/<trial>`), sorted. They form
  137 families; with `one_per_family` the lab keeps 137.
- Types: pick-and-place 35, clean 27, cool 25, two-object 24, heat 16, look-in-light 13.
- Stratification for analysis (not families): goal phrasing. About 28% of valid_seen goals use the adjective form
  ("put a clean X in Y", "put a hot X…"), which is the most common systematic failure of the no-memory agent.
- `valid_unseen` is never read by any script of this approach.

## Families (`families.json`)

- Family = the ALFWorld task directory, e.g. `pick_cool_then_place_in_recep-Egg-None-Microwave-12`:
  same task type, same objects and receptacle, same scene (room). Two trials of one directory are "almost the
  same game" and share a family. Goal phrasing is NOT a family.
- The map covers every unit and every bank entry.

## Bank (`data/bank.jsonl`) and separation from the test

- Source: ALFWorld `train`, planner walkthroughs replayed in the installed text environment (current action
  syntax; every bank entry replayed to a win with every action admissible; 0 failures).
- Sampling: per task type, a seeded (seed 0) shuffle of train games, at most one trial per family, up to 120 per
  type: 710 entries (look-in-light has only 110 eligible families).
- **Disjoint by family from the test:** 134 train families that also occur in valid_seen (same task in the same
  room) were removed before sampling. Overlap of bank families with unit families: 0.
- The planner knows where objects are, so walkthroughs never search. They show the correct action order and
  syntax, not exploration.
- Rendering of one item (changed 2026-11-15 after pilot 1, before any program): `Task: <goal>.`, then one line
  per step in exactly the format the agent sees its own history in (AdaMEM's
  `[Observation i: '<obs>', Action i: '<action>']`), then `Final observation: '<obs>'`. Observations have
  whitespace collapsed and are cut to 240 characters. Pilot 1 used a `> <action>` line format instead; the model
  then often answered in that format without `<action>` tags (8.0 unparsed actions per episode against 1.7 for
  placebo), a format artefact, not a content effect. Pilot 2 checks the new format.

## Sampling parameters

- temperature 0.7 (as in AdaMEM), max_tokens 2048, max 50 steps per episode, history of the last 50
  (observation, action) pairs in AdaMEM's format, k = 2.
- vLLM: `--max-model-len 16384 --gpu-memory-utilization 0.80 --enforce-eager --seed 0`; request seed =
  hash(unit, arm, seed, step). vLLM batching makes results only approximately deterministic.
- Action parsing, ONE strict parser for every arm, unchanged since the first pilot: the last `<action>…</action>`
  of the answer, matched case-insensitively to the admissible commands. Anything else (no tags, or a command that is
  not admissible) goes to the game as written and counts in `metrics.invalid_actions`; the game answers
  "Nothing happens." Empty answers are retried up to 3 times with a new seed.
- Reported per result: `solved`, `memory_sources`, `metrics.memory_tokens`, `tokens`, `steps`,
  `invalid_actions`, `seconds`, `temperature`, `max_tokens`, `max_steps`, `model`, and `evidence` (goal, outcome,
  last four actions with the game's replies).

## Planned secondary analyses (written before the program starts)

- **Same-room sensitivity.** valid_seen rooms also occur in train. No test family is in the bank, but bank
  entries of other tasks in the same room remain. An independent audit found that the retrieved items come from
  the test game's room in 7–10 of 137 units, and show the true location of the goal object in 2–6 of them
  (upper bound on the advantage 2.9–4.4 points, expected about 1 point). The primary result (memory − placebo)
  is repeated without the units whose `memory_sources` share the room number (the last number of the task
  directory) with the unit.
- **Format versus behaviour.** `metrics.invalid_no_action_tag` per step, by arm. A memory-arm excess of untagged
  answers over placebo is a format trace; an excess of tagged but inadmissible answers is behaviour.
- **Empty answers.** `metrics.empty_retries` per step, by arm.
- **Server failures.** If the model server fails on every attempt for a step, the episode ends as an error
  (no `solved`), so the lab retries it. It is never recorded as unsolved.

## Known limits

- The bank is expert walkthroughs, not the agent's own successes (AdaMEM uses ~1,600 own successes). A positive
  result answers "does retrieved expert demonstration help", not "does own experience help".
- The goal-similarity key is lexical, not AdaMEM's Qwen3-Embedding-4B. Our GPU check (issue #173) found cheap
  keys pick the same game as the 4B embedder about 72% of the time.
- Same-room (`valid_seen`) test games: scenes appear in train, though no test family is in the bank.
