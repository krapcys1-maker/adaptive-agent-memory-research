# adaptive-agent-memory-research

**Experience memory for LLM agents that act — built up from the simplest thing that works, one measured step at a time.**

An agent that does tasks (in a home simulator, a science lab simulator, later with real tools) should get better from its own experience without retraining the model. This project asks a narrow question first and earns every next step with a measurement:

> Does showing an agent the *right* pieces of its earlier successful runs, at the *right* moment, make it solve more tasks — and is it the match that helps, or just showing any example?

**Status (15 November 2026): new direction, nothing measured yet in it.** The repository changed course after an external literature and code review. Earlier research lines are kept, with their results and negative findings, in the [archive index](docs/ARCHIVE_INDEX.md). The previous README is preserved unchanged at [README at commit 34936e9](https://github.com/krapcys1-maker/adaptive-agent-memory-research/blob/34936e9/README.md).

---

## Why this direction

A review of recent work, read in full where it shaped a decision ([research map](docs/research-map/README.md)), points the same way from several sides:

- **Retrieving earlier successful steps by the agent's current state, at every step, is the best-supported simple mechanism** for agents that act. In one study (AdaMEM, ICML 2026) it raised ALFWorld success from 45.2% to 59.3% with a 4B model; a synthesis step on top added about 6 points within run-to-run noise, and synthesis *without* memory made things worse. One study, one model — a reason to test, not a promise.
- **Simple baselines are hard to beat.** Plain retrieval over raw history beats elaborate memory systems on conversation benchmarks, and turning on every component at once is consistently worse than the best subset.
- **Memory can hurt.** Repeatedly rewriting memory with an LLM degrades it across seven frameworks; similar-but-wrong stored experiences lower precision; gains shrink with stronger models.
- **Experience memory is barely deployed.** Products mostly store user facts or note files. There is room to find out, properly, what actually helps.

## How we work: the ladder

Each rung adds **one** thing and is compared, on the same tasks, model and budget, with the rung below, with no memory, and with a *random-bank* control (same amount of retrieved text, chosen at random). After every rung we read every task that was gained or lost and write down **why**, before choosing the next rung.

| Rung | Variant | What it tells us |
|---|---|---|
| 0 | no memory, 3 seeds | baseline and the noise floor (how many tasks flip by chance) |
| 1 | fixed expert examples per task type | is a plain example enough? |
| 2 | random entries from the bank, every step | does showing *anything* from the domain help? |
| 3 | random entries of the same task type | is matching the task type enough? |
| 4 | retrieval by task description, once at the start | match to the task |
| 5 | retrieval by the current state, every step | match to the situation |
| 6+ | one improvement per rung (better retrieval key, shorter entries, a show-or-nothing gate, a bank that grows online, success/failure pairs, …) | chosen from what the earlier rungs taught us |

Rules that keep it honest: development on a frozen 60-task subset of ALFWorld `valid_seen`; **ALFWorld `valid_unseen` stays untouched until a single confirmation at the end**; decision rules written down before each run; raw runs frozen by SHA-256; no shortcut that could move the result (for example, no cutting the step limit). Details: [ROADMAP.md](ROADMAP.md).

## Benchmarks

- **ALFWorld** (MIT; train 3,553 / valid_seen 140 / valid_unseen 134 games) — main development and confirmation set. A local 4B model solves roughly 60–70% without memory, so there is room both ways.
- **ScienceWorld** (Apache-2.0; 30 task types, 7,200 variations) — second world, more units for small effects.
- **A tool-use benchmark** — the real target; to be chosen.
- **Our own overlays** on those tasks, for harms the benchmarks do not measure: a polluted bank, a stale entry, a cold start with an empty bank, a growing bank, a change of model.

## Help wanted

You do not need a GPU for most of it. Good first tasks will be listed under the milestone **Experience memory: ladder v1** in the issues: a random-bank control arm, a per-task gain/loss table and viewer, the polluted-bank overlay, summaries of papers we have only read as abstracts, a ScienceWorld port. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [first-contribution walkthrough](docs/00-project/first-contribution-walkthrough.md).

## What stays from before

- **Method tools** we keep using: decision-rule simulation before a run (`scripts/rule_characteristics.py`), raw-run freezing and errata instead of edits, the experiment registry, the export tool with a protected-data check.
- **The project-memory engine** (`tools/project_memory/`, an append-only log with an MCP server) still works and records this project's own decisions. Setup is in the [previous README](https://github.com/krapcys1-maker/adaptive-agent-memory-research/blob/34936e9/README.md#give-claude-code-persistent-project-memory-in-two-minutes).
- **All earlier research lines and their results, including the negative ones** — see the [archive index](docs/ARCHIVE_INDEX.md).

## License

Code under Apache-2.0, documentation and data under CC BY 4.0, as before (see `LICENSE`, `LICENSES/`, `REUSE.toml`). Third-party code will carry its own licence and attribution.
