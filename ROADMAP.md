# Roadmap: experience memory, ladder v1

Status (updated 22 November 2026; plan written 15 November 2026). Measured so far (rung 4, retrieved expert walkthroughs, Qwen3-4B-Instruct-2507-FP8; one RTX 3060 and vLLM 0.33.0 according to the lab's unpublished server logs (see [VOLUNTEER_COMPUTE.md](docs/research-map/VOLUNTEER_COMPUTE.md))). Completed and published, see [the results table](docs/challenges/RESULTS.md):
- [V3](data/lab/autolab-alfworld-ladder-r4-v3/README.md): 100 `valid_seen` games, `measurement_problem`.
- [V4](data/lab/autolab-alfworld-ladder-r4-v4/README.md): 300 `train` games, `measurement_problem`, [H3 erratum](docs/11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v4-h3-verdict.md).
- [V5B](data/lab/autolab-alfworld-ladder-r4-v5b/README.md): 201 `train` games, all 6 task types, unified format reminder on, [secondary contrast addendum](docs/11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md).
- [V6](data/lab/autolab-alfworld-ladder-r4-v6/README.md): 300 `train` games not measured before, five arms, one seed. V6 swapped bank and test relative to V5B: its 300 test games come from the 360 families of V5B's bank, and its bank holds the replayed walkthroughs of V5B's 350 test games. It is a new bank and new games, not a same-bank re-run of V5B.
- In V5B, `retrieved_task − placebo` is +0.169 [+0.053, +0.285] (`positive`, direction `open`), `mismatched_type − placebo` is +0.015 [-0.067, +0.097] (`equivalent` at the declared ±0.12 margin, direction `closed`), `untagged_not_truncated` is balanced, and the code audit verdict is valid. The intervals are the paired sequential intervals at look 2 (`n = 201`, `z = 2.7777`).
- In V6 the three memory arms show the same two retrieved walkthroughs, but not the same amount of their content: about 720 tokens for full walkthroughs, 197 for actions and 112 for plans. The actions and plan blocks are padded with placebo filler to the same length of about 800 tokens. Against placebo (paired sequential intervals at the final look, look 3, `n = 300`, `z = 2.4166`), full walkthroughs gave +0.130 [+0.049, +0.211], actions only +0.137 [+0.055, +0.219] and abstract plans +0.130 [+0.060, +0.200]; all three are `positive` and none is `practical`. The full-walkthrough and actions directions are `open`. The plan direction has a format measurement problem (`untagged_not_truncated` exceeded its pre-registered criterion), so its positive contrast does not separate content from format. Against no memory (secondary): full walkthroughs +0.073 [−0.009, +0.156] (64/42, `inconclusive`), actions +0.080 [+0.000, +0.160] (62/38, `positive`), plans +0.073 [+0.002, +0.145] (51/29, `positive`), and `placebo − none` −0.057 [−0.122, +0.009] (`inconclusive`). The three point estimates are close (+0.073, +0.080, +0.073) with lower bounds at or near zero, so the different labels reflect the decision threshold, not a difference between renderings; no contrast between renderings was tested. Inconclusive is not the same as no effect.
- Built and published since 15 November: [`tools/experience_memory/`](tools/experience_memory/README.md) (0.1.0, parity-certified against V5B), the pinned V5B replication instrument ([`tools/alfworld_ladder/v5b/SETUP_SAME.md`](tools/alfworld_ladder/v5b/SETUP_SAME.md), #229), and the first volunteer sensitivity cell ([`data/contrib/placebo-v4-B03-r1-mt0-fr0/`](data/contrib/placebo-v4-B03-r1-mt0-fr0/README.md), PR #243, CPU replay passed, lab spot-check pending). Rungs 0–3 and 5 are not measured yet as full ladder rungs (`none` is included in V3–V6 and `random_same_type` is implemented in `tools/alfworld_ladder/agent.py`).

## Stage 0: setup (no study results)

1. Package skeleton `experience_memory/` with tests on a fake model (runs in CI without a GPU) — done: `tools/experience_memory/` (0.1.0, parity-certified against V5B).
2. ALFWorld adapter and the ladder arms: no memory, fixed examples, random bank, random bank of the same type, retrieval once by task, retrieval by state every step. Every arm logs which bank entries were shown at each decision — partial: `tools/alfworld_ladder/agent.py` implements `none`, `placebo`, `random_same_type`, `retrieved_task` and `mismatched_type`; fixed examples, general random bank and per-step state retrieval remain open.
3. Bank built from ALFWorld expert demonstrations of the train split (no model calls) — done (`tools/alfworld_ladder/data/bank.jsonl`, 710 items; `tools/alfworld_ladder/v5b/data/bank.jsonl`, 360 items); building it from the agent's own runs is a later rung.
4. An embedding model that fits next to the agent model on a 12 GB GPU, or embeddings on CPU — measured, not assumed.
5. A task-exposure ledger, a frozen 60-task development list from `valid_seen` (stratified by the six task types and by goal phrasing, since adjective-form goals such as "put a cool egg in microwave" are 28% of `valid_seen`), and a block on `valid_unseen`.
   - Check the action syntax of any bank first: 90–92% of trajectories in three public ALFWorld banks contain an action that does not match the current syntax templates.
   - CPU tools for both checks are in `tools/alfworld_cpu/`.
   - Possible directions, with their trade-offs, are in [docs/research-map/DIRECTIONS.md](docs/research-map/DIRECTIONS.md).
6. Diagnostic overlays: polluted bank, stale entry, cold start, growing bank.

## Stage 1: the ladder (development data)

Rungs 0–5 as in the [README](README.md), then improvements one at a time. After each rung:

- per-task gain/loss table against the noise floor;
- every gain and loss read and classified (memory pointed to the object, shortened the search, copied an action from a mismatched situation, distracted, overflowed the context, or unrelated noise);
- written lesson and the choice of the next rung, recorded before the next run.

Stop and report if rung 5 does not beat rung 2 beyond noise (the match does not matter), or if three improvements in a row do not help.

## Stage 2: one confirmation

The best version against no memory, the random banks (rungs 2 and 3) and rung 5, on ALFWorld `valid_unseen`, 3 seeds. The decision rule and its power are simulated and written down before the first call.

## Stage 3: wider

A second model, ScienceWorld, then a tool-use benchmark (the real target).

## Not now

Graph memory and spreading activation, an RL-trained memory manager, continuous memory rewriting, and stacking many modules at once. The evidence for agents that act is weak or negative; see the [research map](docs/research-map/README.md).
