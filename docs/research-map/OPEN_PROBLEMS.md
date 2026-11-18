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
- A token-matched placebo block raised the solve rate by 13 points in V3. Most of that came from a decoding artefact:
  without extra text, the model often ended its answer at the first token. With `min_tokens = 8` for every arm (V4,
  300 games), empty answers are gone, and placebo and no memory are within 2 points of each other (0.45 vs 0.47).
- In V4 retrieved walkthroughs beat the placebo by 24 points (0.69 vs 0.45, interval [+0.18, +0.30]). Limits: one
  model, one seed, and five of the six task types (no `look_at_obj_in_light` games in V4's pool); the lab flags a
  measurement problem because the pre-registered format criterion was exceeded. V5B adds the sixth type and a
  format-matched control.
- In V4 the memory arm also makes more invalid actions per step (0.29 vs 0.20 for the placebo): walkthroughs may help
  planning while adding actions that do not fit the current room. Open question, see P1.
- In V4 the memory arm produces more answers without an action tag. A sample suggests that these are mostly answers
  cut off at max_tokens after long deliberation about a mismatch between the retrieved walkthrough and the current
  room.
- None of the agent-memory papers we surveyed used a length-matched placebo: not AdaMEM, ExpeL, RAP, TRAD, Memp or
  ReasoningBank.

## P1. Does the memory gain depend on how well the walkthrough matches? (CPU only)

- **Hypothesis:** the gain grows with goal similarity, and truncated or untagged answers cluster in low-similarity
  games.
- **Test:** re-analyse the published per-task tables. For V3, use
  [`per_unit.csv`](../../data/lab/autolab-alfworld-ladder-r4-v3/per_unit.csv); for V4,
  [`per_unit.csv`](../../data/lab/autolab-alfworld-ladder-r4-v4/per_unit.csv). Fit success and untagged rate against similarity, and run paired tests per task type.
- **Needs:** a laptop.
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

- **Hypothesis:** first-token end-of-sequence, and the placebo "gain" that came from it, depend on the model and the
  serving stack.
- **Test:** the placebo-check cell (#193) with `--min-tokens 0` and `8`, on another model (Qwen3-1.7B, Llama-3.2-3B,
  Gemma-3-4B) or another vLLM version.
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
