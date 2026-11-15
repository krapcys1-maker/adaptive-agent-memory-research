# Roadmap: experience memory, ladder v1

Status: plan, 15 November 2026. Nothing in this line has been measured yet.

## Stage 0: setup (no study results)

1. Package skeleton `experience_memory/` with tests on a fake model (runs in CI without a GPU).
2. ALFWorld adapter and the ladder arms: no memory, fixed examples, random bank, random bank of the same type, retrieval once by task, retrieval by state every step. Every arm logs which bank entries were shown at each decision.
3. Bank built from ALFWorld expert demonstrations of the train split (no model calls); building it from the agent's own runs is a later rung.
4. An embedding model that fits next to the agent model on a 12 GB GPU, or embeddings on CPU — measured, not assumed.
5. A task-exposure ledger, a frozen 60-task development list from `valid_seen` (stratified by the six task types and by goal phrasing, since adjective-form goals such as "put a cool egg in microwave" are 28% of `valid_seen`), and a block on `valid_unseen`.
   - Check the action syntax of any bank first: 90–92% of trajectories in three public ALFWorld banks contain an action that the current ALFWorld rejects.
   - CPU tools for both checks are in `tools/alfworld_cpu/`.
   - Possible directions, with their trade-offs, are in [docs/research-map/DIRECTIONS.md](docs/research-map/DIRECTIONS.md).
6. Diagnostic overlays: polluted bank, stale entry, cold start, growing bank.

## Stage 1: the ladder (development data)

Rungs 0–5 as in the README, then improvements one at a time. After each rung:

- per-task gain/loss table against the noise floor;
- every gain and loss read and classified (memory pointed to the object, shortened the search, copied an action from a mismatched situation, distracted, overflowed the context, or unrelated noise);
- written lesson and the choice of the next rung, recorded before the next run.

Stop and report if rung 5 does not beat rung 2 beyond noise (the match does not matter), or if three improvements in a row do not help.

## Stage 2: one confirmation

The best version against no memory, the random bank and rung 5, on ALFWorld `valid_unseen`, 3 seeds. The decision rule and its power are simulated and written down before the first call.

## Stage 3: wider

A second model, ScienceWorld, then a tool-use benchmark (the real target).

## Not now

Graph memory and spreading activation, an RL-trained memory manager, continuous memory rewriting, and stacking many modules at once. The evidence for agents that act is weak or negative; see the [research map](docs/research-map/README.md).
