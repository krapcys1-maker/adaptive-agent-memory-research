# Reproducible kernel mutation check — issue 73

The formerly throwaway mutation checks now have a committed, standard-library-only runner: `scripts/wmb/mutate_kernel.py`. It registers 49 single-change mutants for each of the frozen 0.1.0 and live 0.2.0 kernels. Every old text must occur exactly once and the changed source must compile. Both original modules and original test files remain unchanged.

The registered properties reconstruct the published PR 64 claims (time boundaries, supersession, fiction scope, names, retrieval gates, privacy) and extend them to calibration, rendering, tokenization, zones, precision and guard thresholds. The original unpublished 23/100 mutation scripts were not recovered; these are explicitly named, inspectable new catalogues rather than a claim of byte-identical historical replication.

## Results

| Line | Original suite only | With additive boundary tests | Errors | Equivalent exceptions |
| --- | --- | --- | --- | --- |
| 0.1.0 | 37 killed / 12 survived | 49 killed / 0 survived | 0 | 0 |
| 0.2.0 | 47 killed / 2 survived | 49 killed / 0 survived | 0 | 0 |

The 28 additive cases in `tests/test_wmb_memory_kernel_mutants.py` close the observed gaps: inclusive index build, strict retrieval/replacement dates, mixed dimensions, plural and name boundaries, query truncation, calibration precision/time and guard/embedding boundaries. Eleven runner protocol cases cover catalogue applicability, baseline failure, invalid replacements, survivor/error exit codes, explicit equivalence reasons, output protection and timeout cleanup. Thirty-nine combined new tests pass.

The initial survivors and final tables are preserved in [the sanitized result packet](kernel-mutation-check-2026-11-04/results.json). No surviving mutant was silenced by changing a kernel or weakening an original assertion. These finite catalogues test selected properties; they do not prove correctness or measure guard recall on production text.

## Reproduce

```text
python scripts/wmb/mutate_kernel.py --workers 4
python scripts/wmb/mutate_kernel.py --module scripts/wmb/kernel/memory_kernel.py --workers 4
python scripts/wmb/mutate_kernel.py --list
python -m pytest -q tests/test_wmb_mutation_runner.py tests/test_wmb_memory_kernel_mutants.py
```

`--test-file` is repeatable, so either original suite can be selected alone to reproduce the initial-survivor comparison. `--only NAME` selects individual catalogue entries. `--json NEW_PATH` writes a new result file; existing artifacts and source files cannot be overwritten.

Every execution first runs an unmodified baseline in a temporary tree. Pytest exit 1 counts as a kill; collection errors, infrastructure errors and timeouts do not. A timeout terminates the test process tree before cleanup. The checkout is checked byte-for-byte after the run. The default worker count is one; four workers were used for the recorded runs. Mutation tests are fail-fast; the unchanged baseline still runs the full selected suites.

CI now checks both catalogues in separate Python 3.12 jobs with pytest only, and includes the additive/protocol suites in the existing kernel Python 3.14 job. The full project gate and exact-head GitHub status are recorded in the PR and local delivery receipt after completion.

## Coordination

PR 93 merged into PR 90 at `566d08509bc63b2002d497da07c0993c5893d894`; PR 90 subsequently passed all six checks and merged into main at `2e09a2a6412c406ef7a37032e74cf7115ca111e1`. The mutation work uses its own branch and worktree, based on that integrated state. The prior 329 memory events and both original kernel suites are preserved. NIE persona prompts, configuration, filters and deployment are separate work.
