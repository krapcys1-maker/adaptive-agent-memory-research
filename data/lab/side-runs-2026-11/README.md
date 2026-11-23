**Status:** exploratory side runs outside the lab pipeline; per-game outcomes only.

# Side runs since V6 (November 2026): per-game solved tables

One CSV per run. Each row is one game × arm × seed, with the columns `unit`, `arm`, `seed` and `solved` (1 = the game
was won within 50 steps). The `ds-hard-1.csv` table has one more column, `excluded_by_length_rule`: 1 marks the 4
`mismatched_type` episodes that the study plan excludes from Q2 and Q3, because their block length differed by more
than 10% from `retrieved_task`.

Every `unit` id is already public: each is a game of the published V6 package (`../autolab-alfworld-ladder-r4-v6/`) or
the published V5B package (`../autolab-alfworld-ladder-r4-v5b/`). The tables hold no actions, prompts, model outputs,
memory text or logs. Those stay private.

What the runs are, how to read them, and their limits:
- [V6 addendum](../../../docs/11-research-laboratory/errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md)
- [V5B addendum](../../../docs/11-research-laboratory/errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md)
- [side-studies note](../../../docs/11-research-laboratory/side-studies-2026-11.md)

| file | run | model, mode | rows | SHA-256 |
|---|---|---|---:|---|
| `v6-seed1.csv` | V6 games, `placebo` and `retrieved_task` at seed 1 | Qwen3-4B, normal | 600 | `54c11e9fadeee247ec39557f57996a8a068b5bf3880790010338e3a427ac1b60` |
| `v5b-seed1.csv` | V5B games, `none` and `retrieved_task` at seed 1 | Qwen3-4B, normal | 402 | `56ecc1bc983e270c339b5e9e6ec7a724765e5607a72a10b983ab40b4e862ef16` |
| `d8-v6.csv` | V6 games, `d8_instruction`, seed 0 | Qwen3-4B, normal | 300 | `4007b8a0fb4de1251283ebffb0ffa84c87ae16631353c513cccae538f0be4a82` |
| `d8-v5b-pilot.csv` | V5B transform games, `d8_instruction`, seed 0 (first D8 pilot) | Qwen3-4B, normal | 114 | `ec39529b0ea49e5703163906f78410c2909f3e9e14addcb4a04a19a161352a39` |
| `ds-pilot-normal.csv` | 20 V6 games, `none` and `retrieved_task` | DeepSeek V4.1 Flash, normal | 40 | `18bcc698f4bd9e85b2155f89bab94c223cb530a93b978d76f51bfdce4bbea88b` |
| `ds-pilot-hard.csv` | the same 20 games | DeepSeek V4.1 Flash, HARD | 40 | `17ecb333566776a9ec8899a84af32fec86a6c26ed32800372fb70fa1b59f1a72` |
| `ds-hard-1.csv` | 200 V6 games, 4 arms (775 episodes recorded) | DeepSeek V4.1 Flash, HARD | 775 | `a4965221b41516490816eb549318e24d2f0b448ec5b7cb986506d2837ee88df3` |
| `ds-hard-2.csv` | 100 of those games, 4 arms | DeepSeek V4.1 Flash, HARD | 400 | `54163d3dd0e9b224e5eeb0995ede997f0edfc33ce478c807db1069303e712c2c` |
| `nemo-floor.csv` | 100 of the DS-HARD-1 games, 3 arms | Mistral Nemo 12B, HARD | 300 | `039fd49eb0fcacd804f9c6df57148aa86446596ee7624991e85692659cfdd446` |
| `nemo-pilot.csv` | NEMO-1 qualification pilot, 4 arms (65 of 80 episodes recorded) | Mistral Nemo 12B, HARD | 65 | `a3c0112f6cfd42215138d0e2082541abec9e1ee0ba8951a02f0d5b058c2590ad` |

`tests/test_v6_seed1_d8_addendum.py` recomputes the headline contrasts of the addenda and the note from these tables
and from the packages' `per_unit.csv`.

**Not in these tables, so not checkable from the repository:**
- step counts, which the Wilcoxon step tests use;
- per-step format counters and invalid-command rates;
- the shown walkthroughs (memory sources), which the source-overlap and exposure counts use;
- costs;
- the rules and plans themselves.

The documents above give the SHA-256 of those files as commitments.
