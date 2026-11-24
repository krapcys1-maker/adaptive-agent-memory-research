# Lab spot-check of `placebo-v4-B03-r1-mt0-fr0`

Step 2 of the validation rule in [VOLUNTEER_COMPUTE.md](../../../../docs/research-map/VOLUNTEER_COMPUTE.md#how-results-are-checked).
Run by the lab on 2026-11-24. **Result: passed.** All must-match fields are equal in all 15 episodes. The solved
counts are within the declared limits.

## The draw

- Salt `eed078c55e4947986b11b60950c80626`, committed in [`SPOT_CHECK_SALT.md`](../../../../docs/challenges/SPOT_CHECK_SALT.md)
  (commit `0646fce`, merged in PR #266) before the draw.
- The 5 games with the lowest `sha256(salt + cell id + game path)` ([`draw.json`](draw.json)):
  1. `train/pick_cool_then_place_in_recep-Pan-None-DiningTable-11/trial_T20190908_204347_530034`
  2. `train/pick_and_place_simple-Pen-None-Shelf-310/trial_T20190909_113609_142533`
  3. `train/pick_and_place_simple-Box-None-Sofa-205/trial_T20190907_214830_497445`
  4. `train/pick_cool_then_place_in_recep-Potato-None-Microwave-20/trial_T20190909_035658_081195`
  5. `train/pick_two_obj_and_place-Candle-None-Cabinet-412/trial_T20190908_222902_113581`
- All 3 arms, replicate seed 1 and the card's settings (`min_tokens = 0`, `format_reminder = 0`, temperature 0.7,
  `max_tokens` 2048, 50 steps): 15 episodes ([`batch.jsonl`](batch.jsonl), unit ids as in the cell).

## The lab's configuration

This is a sensitivity cell, so the re-run used the reference configuration, not the cell's:
RTX 3060, vLLM 0.33.0 with `MarlinFP8ScaledMMLinearKernel` for `Fp8LinearMethod` (the flags of
[`vllm_serve.sh`](../../../../tools/alfworld_ladder/vllm_serve.sh)), the reference game archive (each game's
`game.tw-pddl` checked against the pinned manifest before the run), ALFWorld 0.4.2, TextWorld 1.7.0,
fast-downward-textworld 20.6.4. The placebo, bank and prompt-template files had the card's digests. `agent.py`
was the current runner; it differs from the cell's pin only by the positive-control arms (commit `945e0dc`), which
these jobs do not use. The lab's records are in [`records.jsonl`](records.jsonl).

## Result

| Arm | solved, volunteer (5 games) | solved, lab re-run (5 games) | difference | limit |
|---|---|---|---|---|
| none | 2 | 3 | +1 | 4 |
| placebo | 2 | 2 | 0 | 4 |
| retrieved_task | 4 | 3 | −1 | 4 |
| total | 8 | 8 | 0 | 8 |

- **Must-match fields: 15 of 15 equal.** Retrieved entry ids (`memory_sources`), `memory_tokens`,
  `top1_similarity` and `memory_similarity` (4 decimals) are identical in every episode.
- **Solved counts:** two episodes changed outcome in opposite directions (Pan-DiningTable-11 `retrieved_task`
  1 → 0, Candle-Cabinet-412 `none` 0 → 1). For a sensitivity cell a deviation would be reported and attributed to the
  configuration, not failed; here none exceeds the limits anyway.
- **Descriptive only (not a criterion):** on these 15 episodes the empty-answer pattern of the cell also appears on
  the reference stack. Empty answers per step, none / placebo / retrieved_task: volunteer 0.712 / 0.000 / 0.552, lab
  0.925 / 0.000 / 0.750. Five games cannot show that the two configurations are equivalent, and this check does not
  claim it.
