# AAMR-NIGHT-2 (E1 to E5): composed memory system against no memory and competitor-style arms: development result, negative on the main test

**Status: completed on 2026-11-13 as a development result. The frozen main test came out "refuted"; every effect in the run is
small and not significant at the registered level. Not confirmatory.** Run by the maintainer's autonomous program
(`scripts/aamr_night2.py`, started by the Windows scheduler, no Claude session during the run) on the specification
`SPEC_AAMR_NIGHT2.md` v0.1 (handed over by Fable 5.2, copied here unchanged, SHA-256
`b44e6c17142b62f28790860357c206c46bbb932a28ac25e1d18b39d1570309a1`) and the executor's protocol (Claude Opus 5.5). The
specification, protocol and report are in **Polish**; this README is the English summary. The numbers below are copied from the
generated `REPORT.md` and `results.json`, not recomputed here. There is **no author interpretation file** for this run
(`REPORT.md` points to a `WNIOSKI.md` "if it was written"; it was not). Imported into this repository on 2026-11-14.

## Short answer
- **Main test (E3, 88 development-test tasks, Qwen2.5 14B): composed system V0 against no memory: 35 against 28 solved, +7
  (20 gains, 13 losses), one-sided exact McNemar p = 0.148. The frozen rule says "refuted".** The registered rule (specification
  section 5) supports only at V0 - N >= 9 with p <= 0.01 and at most 4 losses, and refutes at V0 - N <= 4 **or at 8 or more losses**; here
  the difference (+7) is above the first refutation clause and the verdict comes from the loss clause alone (13 losses). The re-run of the no-memory arm
  differed by 1 task. The assembled system gained in two of three domains only.
- **Read "refuted" with the rule's characteristics in mind.** A loss cap of 8 on arms that disagree with the baseline on 33 tasks (20 + 13) is
  easy to hit by noise. This repository's own audit of decision rules
  ([decision-rule-characteristics.md](../../../docs/11-research-laboratory/decision-rule-characteristics.md), simulated with the audit's
  noise model) reports that this main-test rule "refutes" in about 83% of runs even when the true gain is +10 tasks and supports in
  about 1.8%. A "refuted" from this rule is weak evidence that no effect exists; it is evidence that the effect was not large
  enough to pass a strict rule on 88 tasks.
- **The other arms of E3** (against no memory, 28): E* (the best success-memory arm of E1, R+) 38, +10, p = 0.061; TrT (notes
  selected per error signature by the E2 tournament, shown after the matching error) 36, +8, p = 0.019; V0q 34, +6; TrQ (Qwen-written
  notes) 34, +6. Hypothesis verdicts of the frozen rules: H15 refuted, **H16 "supported"** (TrT 36 against TrQ 34: 5 tasks gained and 3
  lost against each other, 8 discordant pairs). H16's rule has a 93/256 = 36.3% false-support probability at 8 discordant pairs with no
  effect (the figure of the decision-rule audit), and the Holm family did not reject (p = 0.363 against a threshold of 0.0167).
  **Treat H16 "supported" as no evidence.**
- **E1 (EXP-MASK-0, 60 training tasks): masked success memories did not help.** No memory 20, raw success traces R+ 22, masked M1
  18 and M2 14; H14 refuted. The masked arms lost tasks through copied values and through the memory itself.
- **E2 (note tournament on training states):** a note source was chosen per error signature from the candidates listed in the report
  (351 forks); the Flash-written candidate was compared only (it would have won on 4 of 19 signatures).
- **E4 (competitor-style arms, 88 tasks, no memory 27):** K 32, C-RB (ReasoningBank-style) 30, C-G (guidance-style) 31; the frozen
  rule says **K is not ahead** of the best competitor-style arm. These arms are the executor's own re-implementations of
  those styles, not the competitors' released systems, so nothing here supports or refutes "better than competitors".
- **E5 (second model, Qwen3.5 9B, 88 tasks):** no memory 35, K 40, +5 (17 gains, 12 losses), p = 0.229: inconclusive.
- **The frozen recommendation rule says: GO BACK TO THE COMPONENTS** (the largest remaining failure class is "no error, wrong or
  extra action"). The exam on the untouched TradingBot reserve was not run; whether it ever is, is the maintainer's decision.
- **Drift check:** the no-memory arm agreed with NIGHT-1's on 86 of 88 tasks (2 flipped).

## Cost
16 138 local calls (limit 21 500; by budget 16 106 in the program plus 32 in the technical test; by model 13 442 with Qwen2.5 14B and
2 664 with Qwen3.5 9B), 0 paid calls, about 5.9 hours of model time (21 306 s) inside a wall-clock window of about 6.1 hours.

## Files
| File | What it is |
|---|---|
| [SPEC_AAMR_NIGHT2.md](SPEC_AAMR_NIGHT2.md) | the normative specification, copied unchanged |
| [PROTOCOL.md](PROTOCOL.md), [config.json](config.json) | the executor's protocol and configuration, frozen before the first experimental call; four technical amendments are dated and classed in the protocol (three before the first experimental call, **one during the run**: a name collision on case-insensitive Windows file names in E1's retrieval plan) |
| [REPORT.md](REPORT.md), [results.json](results.json) | the generated report and results under the frozen rules |
| [raw-freeze.json](raw-freeze.json), [RAW_FREEZE_ERRATUM.md](RAW_FREEZE_ERRATUM.md) | the SHA-256 manifest of 19 raw files, published byte for byte, with an erratum on its recorded local path |

Code: `scripts/aamr_night2.py`, `scripts/aamr_night2_analysis.py`, `scripts/reasoningbank_prompts.py`; tests `tests/test_aamr_night2.py`.
The program imports NIGHT-1's code ([../aamr-night1/README.md](../aamr-night1/README.md)); amendment 1 redirects its paths at activation.

## Reproducibility and limits
- **The raw run (sessions, attempts, ledgers) is not in this repository.** The manifest pins 19 raw files by SHA-256 but nothing here
  lets a reader recompute those sums. Whether the author re-checked them after the run is not recorded in a file of this directory.
- **In CI most of the 27 tests of this experiment are skipped**: they need the pinned BFCL checkout and NIGHT-1's raw data. All 27 pass
  on the maintainer's machine, where those exist, with the same file contents (compared by Git blob). A clean clone checks only the unit-level tests.
- One benchmark (BFCL multi-turn base), two local models, one run per arm, 60 and 88 tasks. The task sets were partly used in earlier
  experiments, so all results are development data (as the report says). No correction for multiple comparisons except the Holm
  family stated in the report.
- Ollama is not fully deterministic at temperature 0 on longer contexts: re-run arms diverged by up to 1 task here and 13 of 58 episodes in NIGHT-1.
- Builds on [../experience-xfer-v1/README.md](../experience-xfer-v1/README.md) and [../aamr-night1/README.md](../aamr-night1/README.md).
