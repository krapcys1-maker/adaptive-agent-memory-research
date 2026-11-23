# ALFWorld ladder V6: how the 4B agent USES a retrieved walkthrough

Experiment name: `alfworld-ladder-r4-v6` (lab family `alfworld-ladder-r4`, as V3–V5B).
- Code: `src/agent.py` (episode) and `src/run_episode.sh` (lab command). agent.py = the V5B agent with the
  positive-control arms (lab-alfworld-pc) plus the two V6 arms; every V5B code path is unchanged.
- Data: `src/build_pool_v6.py` (units, bank, families); checks: `src/check_lengths.py`, `tests/check_renderings.py`,
  `tests/dry_run_fake.sh` + `tests/check_dry_run.py`.
- Model under test: Qwen/Qwen3-4B-Instruct-2507-FP8 on local vLLM. No paid API is used.

## Why V6 (what V5B and the failure anatomy showed)

- V5B (300 fresh train games, 201 analysed at the second sequential look): `retrieved_task − placebo` +0.169
  [0.053, 0.285], state positive (below the 0.12 SESOI lower bound, so not practical); `mismatched_type − placebo`
  +0.015, equivalent. Two goal-similar expert walkthroughs help; walkthroughs of other task types do not.
- Positive control (ALFWORLD-PC-V5B-INSTRUMENT): own-game walkthrough (oracle_self) 0.867 vs placebo 0.533. The
  instrument sees large effects and there is headroom above the V5B effect.
- Failure anatomy (code, `scripts/failure_anatomy.py`, V4 and V5B partial): about 20–28% of the memory arm's losses
  are games the placebo solved (memory ignored or harmful), retrieval misses only 2–3%, the rest is the model limit.

V6 therefore keeps retrieval fixed (the same two picks in every treatment arm) and changes only HOW the two picked
walkthroughs are rendered. It also replicates the V5B arm on fresh games.

## Arms

All arms get the same base prompt: AdaMEM's ALFWorld prompt. They differ only in the block inserted after it. Every
arm ends with the same one-line format reminder: `Reminder: end your answer with exactly one admissible action
inside <action> </action> tags.`

All four block arms have the SAME block length: the `retrieved_task` block of the same (task, seed) is the target;
placebo, `retrieved_steps` and `retrieved_plan` are token-matched to it (vLLM `/tokenize`). The three treatment arms
show the SAME two bank walkthroughs (the `retrieved_task` picks: content-word Jaccard of the goal over the whole
bank, ties broken by a sha256 hash of (task, seed)).

| Arm | Block after the base prompt (fixed for the episode) |
|---|---|
| `none` | no block: AdaMEM's action instruction only |
| `placebo` | AdaMEM's retrieval wrapper with neutral filler lines (`placebo.txt`) split over two items, token-matched to the `retrieved_task` block. Identical to V5B |
| `retrieved_task` | the wrapper with the two picked walkthroughs in the agent's own history format (task line, `[Observation i: '…', Action i: '…']`, final observation; observations cut to 240 characters). Identical to V5B — the replication anchor |
| `retrieved_steps` (new) | the same two walkthroughs, ACTIONS ONLY: task line, then `[Action i: '<action>']` verbatim (numbers and locations kept), no observation text. Block = two filler items first, then the two content items (padding rule below), token-matched to the `retrieved_task` block |
| `retrieved_plan` (new) | the same two walkthroughs turned by DETERMINISTIC rules (no model) into an abstract subgoal plan: task line, `Plan (in order):`, one `- <subgoal>` per line. Verbs and object/receptacle classes kept; every number and every room-specific location removed. Padded as `retrieved_steps` |

**Padding rule (both new arms; changed after the V6 instrument review, finding F1):** the block is
`Retrieved Item 0` and `Retrieved Item 1` = filler, built exactly as the placebo's two items (the placebo's lines,
order and half/half split) with n lines, then `Retrieved Item 2` and `Retrieved Item 3` = the two content items,
unchanged. n is chosen so that the block is closest to the target length (as the placebo search). Why this layout:
- no filler line shares an item with content. The filler says its slot is empty ("No experience is stored at this
  position."), which is true of a filler item but would contradict a content item (the first draft appended filler
  inside the content items);
- the content ends right before the action instruction, as the walkthrough does in `retrieved_task`, so the recency
  of the content is the same in the three treatment arms; the padded block is literally a shortened placebo block
  followed by the content.
- Consequence: the padded arms show four items (two of them empty), the others two. This difference is part of the
  rendering being tested and is reported, not hidden.

**Plan rules** (`agent.plan_steps`, tested on all 410 bank and pilot walkthroughs, `tests/check_renderings.py`: no
digit, no unparsed action, one plan step per object action, every receptacle of clean/heat/cool/move kept):
- `go to R` [`open R`] `take O from R` → `find a O and take it` (`find another O and take it` for the 2nd object of
  the same class) — where the object lay is room-specific, so R is dropped;
- `go to R` [`open R`] `use L` → `find a L and use it` — where the lamp stands is room-specific;
- `go to R` [`open R`] followed by clean/heat/cool/move with R → `go to the R` [`open the R`], then that action;
- `clean/heat/cool O with R` → `<verb> the O with the R`; `move O to R` → `move the O to the R`;
- any other `open`/`close` → `<verb> the R` (an `open R` right before `take … from R` is dropped); `use L` alone →
  `use the L`; a `go to R` followed by anything else → dropped; any other form → the action without numbers (none
  occurs in the bank).

`memory_tokens` = tokens of the whole wrapper with its items (0 for `none`). `memory_sources` = the two shown bank
tasks for the three treatment arms (identical), empty for `none` and `placebo`.

New per-record metrics (every record; `null` where they do not apply):
- `matched_block_tokens`: tokens of the wrapper with the block this arm is matched to (the `retrieved_task` block;
  the oracle block in positive-control jobs);
- `block_length_diff`: `memory_tokens / matched_block_tokens − 1` (0 for `retrieved_task`);
- `content_tokens`: tokens of the non-filler content (the wrapper of the content items only; 0 for placebo);
- `plan_digit_count`: digits in the plan items (`retrieved_plan` only; must be 0);
- `steps_observation_count`: occurrences of "Observation" in the steps items (`retrieved_steps` only; must be 0).

The envelope's `arm_contracts` check these per record (lab: after the first batch and in the audit).

## Hypotheses and predictions (written before the program)

Primary contrasts (lab, family of 3, Bonferroni): `retrieved_task − placebo`, `retrieved_steps − placebo`,
`retrieved_plan − placebo`.

**Primary (the lab's decision; one question per arm: does THIS rendering, in THIS layout, help vs a same-length
neutral block?)**

| Arm | Prediction vs placebo | What a positive state means | What an equivalent / negative state means |
|---|---|---|---|
| `retrieved_task` | positive (V5B +0.169) | V5B replicated on disjoint games | V5B not replicated on these games |
| `retrieved_steps` | positive | the actions alone, in the padded layout, help | this rendering in the padded layout does not help detectably. NOT "actions carry no effect" (see Known limits: less content, four items, two empty) |
| `retrieved_plan` | positive | the abstract plan, in the padded layout, helps | this rendering in the padded layout does not help detectably. NOT "the effect needs concrete details" |

**Lab goal milestones (docs/LAB_GOAL.json, tags model = Qwen3-4B-Instruct-2507, environment = alfworld).**
`retrieved_task − placebo` is the replication anchor: a valid positive result here is the second program with the
same contrast positive on fresh games (milestone **M2**), and **M3** if its lower bound reaches SESOI (0.12).
`retrieved_steps − placebo` and `retrieved_plan − placebo` target **M3** (practical effect: valid result with lower
bound ≥ SESOI); a positive result is also the first evidence (M1) for that contrast.

The primary predictions do not separate mechanisms (all three predict "positive"); mechanism is read only from the
secondary axes below. A padded arm with an equivalent or negative state closes THAT RENDERING for this instrument,
not a mechanism.

**Secondary mechanism axes (pre-registered; from the raw data, not the lab's decision).** Paired difference on the
same units, Wald interval with Bonferroni over the 3 arm-vs-arm contrasts (z = 2.394). State of a contrast X − Y:
`above` = lower bound > 0; `below` = upper bound < 0; `undecided` = the interval includes 0. Each axis has exactly
one of three outcomes:

| Axis | Contrast | `above` | `below` | `undecided` |
|---|---|---|---|---|
| A. observation text | `retrieved_steps − retrieved_task` | the observation text hinders use of the walkthrough ("memory ignored": salience) | the observations carry part of the effect (room layout / what is where) | not separable at this n |
| B. abstraction bundle | `retrieved_plan − retrieved_steps` | the plan bundle helps beyond the concrete actions | the concrete actions (numbers, find-locations, history format) help beyond the plan | not separable at this n |
| (descriptive) | `retrieved_plan − retrieved_task` | — | — | — |

- The plan vs steps contrast changes a BUNDLE, not one factor: numbers removed, find-locations removed, bullet
  subgoals instead of the agent's history format, an explicit "find … and take it" step, merged go/open steps, and
  less content (112 vs 197 tokens). Axis B can say "the bundle helps / hurts", not "stale numbers harm".
- Detectable difference (half-width of the interval at the SESOI-free null): about ±0.069 at n = 360 with
  arm-vs-arm discordance 0.30, ±0.084 if the lab stops at the second look (242 units), ±0.12 at the first look
  (123 units). Differences below these are `undecided`, which is reported as such.
- The padded layout differs from `retrieved_task` in content share (25% / 14% vs 100%) and item count (4 vs 2), so
  axis A also carries the layout. The pilot check `oracle_steps` (below) only shows whether the padded actions-only
  layout can carry a large effect; it does not separate the cost of the layout from the cost of dropping the
  observations.

The lab's code computes only the arm − placebo contrasts and arm − none (descriptive).

## Change from V5B, and why

1. **Bank and test games swap roles.** After V5B and the positive-control pilot, no heat, cool or look-in-light
   family is left outside the V5B bank: keeping the V5B bank would leave 206 fresh test games in three types only
   (pick-two 122, pick-and-place 54, clean 30), and 206 games give power 0.68 at the SESOI for three treatment arms
   (lab calibration, discordance 0.37). So:
   - **test units** = one trial (seed 6) of each of the 360 V5B BANK families: 60 per type, all six types. These
     families were never a test unit in any program (V1–V5B, the pilots, the PC runs; asserted by family);
   - **bank** = the planner walkthroughs of exactly the 350 games V5B listed as test units (already measured, so no
     longer usable as test), replayed in the installed text environment: 350/350 won with every action admissible.
     60 per type, 50 look-in-light (all V5B had). Same source, same replay code and same rendering as every earlier
     bank; 350 instead of 360 items.
   - The bank is therefore a ROLE-SWAPPED bank from the same 710-family pool (the V3/V4 bank pool), not an
     independent draw: the goal-similarity pairing mirrors V5B's (mean top-1 goal Jaccard 0.764 vs V5B 0.770, mean
     shown 0.689 vs 0.699). The test GAMES are disjoint from V5B's and never measured, so this is a second test of
     the V5B claim on disjoint games; it is not a test over an independent bank.
   - 134 of the 360 unit trials are the exact trials whose walkthroughs V5B showed as memory. The model is
     stateless (no weights change between programs), so this exposes nothing to the agent.
2. **`mismatched_type` dropped** (closed in V5B: equivalent); its code stays, it is not in the catalogue.
3. **Two new arms** (above), both equal-length by padding (layout fixed after review F1).
4. Nothing else changes: prompts, sampling, parser, format reminder, counters, placebo, `retrieved_task`.

## Positive control

The envelope's `positive_control` block runs the lab's sensitivity step on THIS command before the measurement:
rung 0 replay (scripted expert / null on 10 pilot games), rung 1 smoke (every catalogue arm on 3 pilot games, all
contracts), rung 2 `oracle_self` vs placebo (30, at most 60 pilot games). Pilot = the 60 games of
lab-alfworld-pc (`data/pilot_units.json`, walkthroughs `data/pilot_walkthroughs.jsonl`, unchanged sha256).
Pilot families are disjoint from the V6 test games and the V6 bank (0 and 0, `data/pool_manifest.json`).
The oracle block is Item 0 = this game's walkthrough, Item 1 = the top retrieved item of the V6 bank.

The lab's step tests `oracle_self` (full format) only. To show that the PADDED layout can also carry a large
effect (review F1), agent.py has one more control-only arm, `oracle_steps`: the oracle block's two walkthroughs
rendered as `retrieved_steps` and padded in the same layout, token-matched to the oracle block. It is never in the
catalogue and the lab never sends it; it was run once in pilot 6 (below) against the control placebo.

**Rule for the `oracle_steps` check (written before pilot 6 was read; review R2-1).** 30 pilot games, paired
`oracle_steps − placebo` (control jobs, seed 0), the lab's rung-2 thresholds:
- PASS ("the padded actions-only layout carries a large effect"): difference ≥ 0.24 AND one-sided exact sign test
  over the discordant pairs p ≤ 0.005;
- UNVERIFIED: difference ≥ 0.12 without PASS. The program starts; every conclusion about a padded arm says that the
  padded layout was not shown to carry a large effect;
- FAIL: difference < 0.12. The padded layout cannot show even a large effect, so the two padded arms are REMOVED from
  the V6 catalogue before `autolab add` (V6 runs `retrieved_task` only, with the envelope changed accordingly), and
  the padding is redesigned in a new program.

## Pilot and length check (V6 code, before the program)

- **Renderings** (`tests/check_renderings.py`, CPU): 410 walkthroughs (bank + pilot), 0 problems; plan lengths 2–7
  subgoals.
- **Length check** (`instrument/length_check.json`, all 360 units, seed 0, the model's own tokenizer, CPU only):
  mean `retrieved_task` block 799 tokens (V5B: 822); relative to it (final layout):

  | arm | mean | min | max | within 1% | within 3% |
  |---|---|---|---|---|---|
  | placebo | +0.03% | −0.66% | +0.87% | 100% | 100% |
  | retrieved_steps | +0.07% | −0.60% | +0.69% | 100% | 100% |
  | retrieved_plan | +0.19% | −0.48% | +1.03% | 99.7% | 100% |

  Content share of the block: steps 24.7% (mean 197 tokens), plan 14.0% (112 tokens); the rest is filler.
  Shown items of the unit's own type: both 310, one 41, none 9 of 360. Same sources in the three treatment arms and
  no same-family source in every unit.
- **Fake-model dry run** (`tests/dry_run_fake.sh`, fake server with the model's tokenizer, random admissible action):
  5 pilot games (one per type available) × 5 catalogue arms + 2 games × 5 control arms (with `oracle_steps`):
  35/35 records, 0 errors; every contract metric present and kept; all blocks of this run within ±0.7% of the target (the length check
  above covers all 360 units); scripted
  expert 2/2, null 0/2; oracle sources include the game; 1550 prompts, all end with the reminder; no digit in a plan
  block, no observation in a steps block; in every block filler and content are separate items and the content
  items are last (`tests/dry_run_fake_report.json`, checked by `tests/check_dry_run.py`).
- **Pilot 6a (first draft layout, filler inside the content items; stopped after 11/25 when the layout was
  changed):** `pilot/pilot6a_oldlayout_out.jsonl`. Kept for the record only: vLLM's `/tokenize` gives the same
  block lengths as the CPU check (block_length_diff −0.14%…+0.55%).
- **Real-model pilot 6** (`pilot/pilot6_out.jsonl`, `pilot/pilot6_report.json`, full lab path `run_episode.sh`, final
  layout): see "Pilot 6 result" at the end of this file.

## Test games (`data/units.json`)

- 360 `train` games, one trial per family (seed 6), 60 per type. Families: the V5B bank families.
- Overlap 0 with: the V1–V3 valid_seen unit families, the V4 pool (354), the V5/V5B units (350), every pilot list
  (25), the PC pilot (60), every unit in the lab's job files, the V6 bank (`data/pool_manifest.json`).
- Seen rooms: bank and units come from the same scenes, as in V3–V5B. `valid_unseen` is never read.

## Families (`data/families.json`)

- Family = the ALFWorld task directory. The map covers the 360 units, the 350 bank tasks and the 60 pilot games.

## Sampling parameters (unchanged from V5B)

- temperature 0.7, max_tokens 2048, min_tokens 8, max 50 steps, history of the last 50 (observation, action) pairs
  in AdaMEM's format, k = 2, format reminder on.
- vLLM: `--max-model-len 16384 --gpu-memory-utilization 0.80 --enforce-eager --seed 0`. Request seed = sha256 of
  (unit, arm, seed, step).
- One strict parser for every arm: the last `<action>…</action>`, matched case-insensitively to the admissible
  commands; anything else goes to the game as written and counts in `invalid_actions`.
- Reported per result: `solved`, `memory_sources`, `actions` (full sequence), `metrics` (`memory_tokens`, `tokens`,
  `steps`, `invalid_actions`, `invalid_no_action_tag`, `truncated`, `untagged_not_truncated`, `empty_retries`,
  `top1_similarity`, `memory_similarity`, the V5B mismatched fields (null), the V6 block metrics above, sampling
  settings), `evidence`.

## Format criteria (pre-registered; the lab checks them)

- `untagged_not_truncated` per step: treatment arm − placebo ≤ 0.03, or the 95% unit-bootstrap interval includes 0;
  for each of the three treatment arms. `empty_retries` per step: same rule. Rule `imbalance_only`, as V5B.
- `truncated` and the combined `invalid_no_action_tag` are behaviour, reported per arm.
- If a criterion fails, the conclusion must say that content and format are not separated for that arm.

## Planned secondary analyses (written before the program starts; from the raw data, not by the lab)

1. **Arm vs arm (mechanism):** axes A and B and the descriptive plan − task contrast, with the states, thresholds
   and detectable differences defined in "Hypotheses and predictions". Reported on the units the lab measured
   (after an early stop: on those units, with the wider interval).
2. **Memory ignored / harmful:** `scripts/failure_anatomy.py` per treatment arm; the share of the arm's losses that
   the placebo solved. Prediction: lower for `retrieved_plan` and `retrieved_steps` than for `retrieved_task`.
3. **Copying:** per episode, the share of the agent's actions that equal, verbatim, an action of a shown walkthrough
   (task and steps arms; impossible in the plan arm by construction), and the share of `go to R n` actions whose
   `R n` is a location where a shown walkthrough found its object; their relation to `solved`. Walkthroughs with
   `go to A` then `take O from B` (A ≠ B, 26 of 350) are counted separately.
4. **Same-room sensitivity, similarity and gain, per type, truncation:** as V5B.
5. **Filler cost:** placebo − none (descriptive; V5B: −0.060 [−0.157, +0.037]) describes the cost of a whole block
   of filler. It does not bound the cost of filler NEXT TO content (the padded arms), which only the arm-vs-arm axes
   and the `oracle_steps` pilot check speak to.

## Definitions and edge cases (unchanged from V5B)

- **solved:** the environment reports a win within 50 agent steps; every step counts.
- **Server failure or context overflow:** after 4 failed attempts `chat()` raises `ServerError`; the episode is an
  error (no `solved`) and the lab retries it; never recorded as unsolved.
- **Hash stability:** tie-breaks and request seeds come from sha256 of the joined values.

## Scope of the conclusion

- Each primary contrast: showing the two goal-similar walkthroughs in that rendering, against a same-length neutral
  block in the same wrapper and position.
- A positive `retrieved_task` result on these games is the second test of the V5B claim on disjoint games (with a
  role-swapped bank from the same pool, see Change 1).
- Positive results mean "retrieved expert demonstrations, in this rendering, help this 4B agent on held-out train
  games in seen rooms". They do not mean "the agent's own experience helps" and do not transfer to unseen rooms.

## Known limits

- The bank holds expert walkthroughs, not the agent's own successes; the planner never searches.
- The padded arms carry 75–86% filler in two empty items before the content (review F1). Placebo has no content to
  be diluted, so the padding can bias the padded arms' PRIMARY contrasts toward null, relative to the rendering's
  effect without padding, and it biases axis A against `retrieved_steps`. Therefore: a positive padded arm is
  interpretable; an equivalent or negative one means "this rendering, padded, does not help detectably" and must
  not be closed as a mechanism ("actions alone / an abstract plan carry no effect"). The `oracle_steps` pilot check
  shows whether the padded layout can transmit a large effect at all.
- Bank oddities, equal across arms: 11 of 350 walkthroughs end without the put step (10 coffeemachine, 1
  stoveburner: the game is won early; V5B bank: 8), so their steps and plan items never show a put; 26 have
  `go to A` then `take O from B` with A ≠ B, shown verbatim in `retrieved_task` / `retrieved_steps` (the plan
  rules drop both locations).
- Report noise (lab code, not this instrument): the lab's process-balance table treats every integer metric as a
  per-step counter, so `content_tokens` and `matched_block_tokens` appear there as "imbalanced" and
  `plan_digit_count` / `steps_observation_count` as not computable. No format marker matches them, so nothing halts;
  ignore those rows.
- The plan keeps the classes of the walkthrough's own task, which may differ from the test goal (similar, not equal,
  tasks), as in `retrieved_task`.
- Lexical retrieval key (content-word Jaccard). Seen rooms only. valid_unseen stays sealed.

## Pilot 6 result (real model, final layout; read after the oracle_steps rule was written)

Run: `pilot/pilot6_batch.jsonl` (85 jobs), output `pilot/pilot6_out.jsonl`, report `pilot/pilot6_report.json`
(`tests/pilot6_report.py`). vLLM Qwen3-4B-Instruct-2507-FP8, sampling as the program.

**oracle_steps check (pre-registered rule, review R2-1):** 30 pilot games, paired control jobs at seed 0.
`oracle_steps` solved 26/30, control placebo 15/30; gains 12, losses 1;
difference **+0.367**, one-sided exact sign test **p = 0.0017**. Rule outcome: **PASS**
(≥ 0.24 and p ≤ 0.005). The padded actions-only layout (two filler items, then the content items last) can carry a
large effect, so the padded arms stay in the catalogue as designed. It does not measure how much the padding costs
relative to an unpadded block (see Known limits).

**Catalogue part (5 games × 5 arms, seed 7; a smoke test, not an estimate):**

| arm | n | solved | steps | truncated | untagged_not_truncated | empty_retries | block_length_diff |
|---|---|---|---|---|---|---|---|
| `retrieved_steps` | 4 | 3 | 84 | 1 | 3 | 0 | -0.0055..+0.0038 |
| `retrieved_task` | 5 | 2 | 162 | 26 | 6 | 0 | +0.0000..+0.0000 |
| `retrieved_plan` | 5 | 4 | 124 | 5 | 13 | 0 | -0.0045..+0.0060 |
| `placebo` | 5 | 2 | 215 | 7 | 12 | 0 | -0.0028..+0.0055 |
| `none` | 5 | 2 | 207 | 11 | 2 | 0 | — |

- Record checks (`pilot/pilot6_checks.json`): all contracts hold, blocks matched within ±0.6%, the three retrieval
  arms show the same two sources, plan blocks hold no digit, steps blocks no observation. The only problem: one
  `retrieved_steps` episode (`p4`, pick_two Book) hit the agent's 5400 s episode limit at step 48 and has no record.
  This is the known slow-episode case (the V4 and V5B measurements logged the same TimeoutError); the lab's runner
  retries a failed job once (`retries: 1`) and fails the measurement loudly if it fails again — no silent skip.
- A first version of the check script read `block_length_diff = 0.0` as missing (6 false flags on control jobs);
  fixed (`is not None`) before this report.

