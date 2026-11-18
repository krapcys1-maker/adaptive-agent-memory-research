# Open problems you can own

These are research questions, not chores. Each one has:
- a hypothesis;
- the cheapest test that could refute it;
- what you need to run it.

They come from our first measurements (V3 and V4; V5B is running) and from a survey of related work, done on
17 November 2026. The sources are in [corpus.json](corpus.json), and the longer-term directions are in
[DIRECTIONS.md](DIRECTIONS.md).

Pick one and say so in its issue, or open a new issue with the
[mechanism proposal](../../.github/ISSUE_TEMPLATE/06-mechanism-proposal.md) template. You can use your own model, your own
setup and your own idea. A refuted hypothesis is a result. A written review, a replication or a validated cell
counts toward co-authorship of the next report ([AUTHORSHIP.md](../../AUTHORSHIP.md)).

**What we know so far.** On ALFWorld with Qwen3-4B:
- In V3 (100 `valid_seen` games, six task types, `min_tokens` not set) a token-matched placebo block raised the
  solve rate by 13 points over no memory (0.57 vs 0.44, [+0.04, +0.22]). In the same run the placebo almost removed
  empty answers (per step: none 0.743, memory 0.582, placebo 0.001), so V3's placebo was not a neutral control.
- In V4, with `min_tokens = 8` in every arm, there were no empty answers, and placebo and no memory were equivalent
  (0.45 vs 0.47, difference −0.02 [−0.07, +0.02]). V4 also changed the games (300 `train` games, five task types,
  no game shared with V3, a different family split), so the V3 → V4 change does **not** tell how much of the
  13 points came from the decoding artefact. That is a hypothesis. The direct test is the same games with
  `min_tokens` 0 and 8, all else fixed (P5).
- In V4 retrieved walkthroughs beat the placebo by 24 points (0.69 vs 0.45, interval [+0.18, +0.30]). Limits: one
  model, one seed, and five of the six task types (no `look_at_obj_in_light` games in V4's pool). The lab flags a
  measurement problem because the pre-registered format criterion was exceeded when untagged answers are counted
  per step, pooled over the 300 episodes of each arm (memory − placebo +3.4 pp, interval [+1.4, +5.3], criterion
  3 pp). Averaged per game instead (the mean of the 300 per-episode rates, a sensitivity analysis from the public
  `per_unit.csv`), the difference is +0.45 pp: the memory arm's episodes are shorter (26 vs 37 steps on average), so
  the per-step figure depends on how steps are weighted. The status is `measurement_problem`: neither established
  nor closed. V5B adds the sixth type and a format-matched control.
- In V4 the memory arm also makes more invalid actions per step (0.29 vs 0.20 for the placebo): walkthroughs may help
  planning while adding actions that do not fit the current room. Open question, see P1.
- In V4 the memory arm produces more answers without an action tag. A private sample of raw logs suggests that
  these are mostly answers cut off at max_tokens after long deliberation about a mismatch between the retrieved
  walkthrough and the current room. V3 and V4 did not record truncation, so the public tables cannot check this.
- None of the agent-memory papers we surveyed used a length-matched placebo: not AdaMEM, ExpeL, RAP, TRAD, Memp or
  ReasoningBank.

## P1. Does the memory gain depend on how well the walkthrough matches? (CPU only)

- **Hypothesis:** the gain grows with goal similarity, and truncated or untagged answers cluster in low-similarity
  games.
- **Test, part 1 (the public tables only):** re-analyse the published per-task tables, V3
  [`per_unit.csv`](../../data/lab/autolab-alfworld-ladder-r4-v3/per_unit.csv) and V4
  [`per_unit.csv`](../../data/lab/autolab-alfworld-ladder-r4-v4/per_unit.csv). They hold, per game and arm, the
  solve outcome, steps, empty retries, untagged answers (`invalid_no_action_tag`), invalid actions, memory tokens,
  `n_memory_sources` and `error`; the task type is part of the game name. From them you can run paired win/loss
  tests per task type and look at untagged answers and invalid actions by arm and type.
- **What they do not hold:** goal similarity and truncation were **not recorded** for V3 and V4. Truncation
  (`finish_reason`) was added to the agent after the V4 pin and cannot be recovered. Similarity can only be
  recomputed: the goal text comes from the ALFWorld game files, the walkthroughs from
  `tools/alfworld_ladder/data/bank.jsonl`, and the retrieved pair can be re-derived with the agent's deterministic
  Jaccard ranking and hash tie-break. That needs the ALFWorld data, not just the tables.
- **Test, part 2 (from V5B on):** the per-unit table also includes `truncated`, `untagged_not_truncated`,
  `top1_similarity` and `memory_similarity` (the lab exporter is being changed for that; placebo-check cells
  already write the similarity columns). Fit success and the untagged rate against similarity there.
- **Needs:** a laptop (part 1 and part 2); the ALFWorld data to recompute similarity for V3/V4.
- **Why it matters:** it is free, and it sets the threshold for the relevance gate (P3, D10).

## P2. Relevant content, or just the shape of an expert trajectory? (12 GB GPU)

- **Hypothesis:** the gain needs a *relevant* walkthrough. A length-matched walkthrough from a different task family
  does not help.
- **Test:** add a `mismatched` arm to the placebo-check cell (20 games: none, placebo, memory, mismatched).
- **Needs:** one cell on a 12 GB GPU, about 2.5 hours.
- **Why it matters:** this separates relevance from format. ExpeL's random examples gave only +2.5 points against +19
  for matched ones, but without a length control.

## P3. Show memory only when it fits (needs code, then cells)

- **Hypothesis:** showing memory only when similarity is at least τ, and the placebo otherwise, keeps the gain and
  removes the extra deliberation.
- **Test:** compare a gate, always-memory and the placebo on about 100 games, with τ taken from P1.
- **Why it matters:** this is direction D10. AdaMEM reports that more retrieved trajectories can lower success.

## P4. Is the memory "cost" a token-budget artefact? (12 GB GPU)

- **Hypothesis:** with a larger max_tokens budget, the memory arm's extra untagged answers disappear, and no-memory
  and the placebo do not change.
- **Test:** max_tokens 512 / 1024 / 2048 / 4096 × none / placebo / memory, with 20 games per cell. These are
  independent cells.
- **Why it matters:** it tells us whether memory hurts the agent, or only our budget.

## P5. Does the empty-answer artefact appear on your model? (12 GB GPU)

- **Hypothesis:** first-token end-of-sequence, and any part of the V3 placebo effect that came from it, depend on the
  model and the serving stack.
- **Test:** the placebo-check cell (#193) with `--min-tokens 0` and `8` on the same block, everything else fixed
  (this is also the direct test of the decoding hypothesis on those games), with Qwen3-4B or on another model
  (Qwen3-1.7B, Llama-3.2-3B, Gemma-3-4B) or another vLLM version. A different model makes the cell a conceptual
  replication; the card records it.
- **Why it matters:** if it generalises, every memory evaluation without such a control is suspect.

## P6. Does AdaMEM's raw-trajectory gain survive a placebo? (12 GB GPU)

- **Hypothesis:** the Synapse-style baseline in AdaMEM (+5 to 7 points with the same 4B model) shrinks once a
  length-matched placebo and `min_tokens` are added.
- **Test:** run the public AdaMEM code with these two additions on ALFWorld seen tasks.
- **Why it matters:** this is an external replication, with the same model, of the closest published work.

## P7. One instruction line against mismatch (12 GB GPU)

- **Hypothesis:** an instruction such as "if the example does not fit this room, ignore it", added to every arm,
  cuts deliberation and truncation in the memory arm.
- **Test:** 60 games, each arm with and without the line.
- **Why it matters:** it is the cheapest possible fix. Irrelevant context is a known distractor, and an instruction
  partly helps.

## P8. Shorter memory: actions only, or a summary (needs code, then cells)

- **Hypothesis:** an action-only walkthrough or a short script recovers the gain with less deliberation.
- **Test:** compare the full walkthrough, actions only and a summary, each with its own length-matched placebo.
- **Why it matters:** this is direction D11. Memp and AWM report that the format of memory matters.

Results go into the [results table](../challenges/RESULTS.md) when they are cells of the placebo check. Other results
go in a short README in `data/contrib/<your-login>-<problem>/`, linked from the problem's issue.
