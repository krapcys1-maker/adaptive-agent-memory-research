# ALFWorld checks that need no GPU

Three small scripts for the experience-memory ladder (see `docs/research-map/`). They read ALFWorld data and trajectory banks. None of them calls a language model or needs a GPU.

| Script | What it answers | Needs |
|---|---|---|
| `goal_phrasing.py` | How often each split writes transform goals in the adjective form ("put a cool egg in microwave") rather than the verb form ("cool some egg and put it in microwave"). Use it to stratify a development sample | ALFWorld data (`json_2.1.1`) |
| `replay_walkthroughs.py` | Replays the planner walkthrough stored in every game file, in the installed action syntax, and saves full trajectories with observations. Use it as an expert bank or as a pool for random-bank controls | `alfworld` and `textworld` installed |
| `check_bank_syntax.py` | Share of actions in a trajectory bank that the installed ALFWorld accepts. Run it before reusing any public bank | Python only (`pandas` for `.parquet`) |
| `power_paired.py` | Simulated power of a paired two-arm comparison at a given noise level (share of tasks that flip between identical runs), for 60/134/274 tasks and 1 or 3 seeds | `numpy` |

## Results on 15 November 2026

Measured with ALFWorld data `json_2.1.1` and the ALFWorld version installed by the AdaMEM repository.

**Goal phrasing:** adjective-form transform goals are 22% of `train`, 28% of `valid_seen` and 25% of `valid_unseen`.

**Walkthrough replay:** 30 random `train` games were solved 30 of 30, with all actions admissible. Speed was 1.5 s per game on an idle CPU and 6 s per game with other work running. All 3553 `train` games take roughly 1.5–6 hours of CPU time.

**Bank syntax:**

| Bank | Compatible actions | Trajectories with an incompatible action |
|---|---|---|
| ETO `alfworld_sft` | 87.1% | 92% |
| AgentGym AgentTraj-L | 91.5% | 90% |
| AgentBank | 87.5% | 91% |

Almost all incompatible actions are the old "put X in/on Y". The installed version writes "move X to Y" for receptacles.

## Caveats

- **Walkthroughs never search.** The planner knows where every object is. A bank of walkthroughs teaches procedures, not where to look. Compare it with a bank of the agent's own successful runs before using it alone.
- **Translated banks need a replay check.** Rewriting "put X in/on Y" as "move X to Y" is simple. Replay a translated trajectory in the environment before trusting it.
