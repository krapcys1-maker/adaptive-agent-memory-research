# Contributors

People who contributed to this project, grouped by their roles in the [CRediT](https://credit.niso.org/) taxonomy.
How credit and co-authorship are decided is in [AUTHORSHIP.md](AUTHORSHIP.md). This page records contributions;
co-authorship of a report is decided by those rules at the report's cut-off, announced in
[#84](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/84).

Entries are added by the maintainer when a contribution is merged or validated. If you are missing, or want to be
credited under another name, open an issue.

## Investigation

| Contributor | Contribution |
|---|---|
| [@2018cx](https://github.com/2018cx) | Placebo-check cell `placebo-v4-B03-r1-mt0-fr0`, run on an A100 and merged in [#243](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/243). It passed the lab's code checks and the CPU replay of all 60 action sequences. It is a sensitivity cell: its vLLM version (0.20.0) differs from the reference, and its game text (`put … in/on …`) matches the older game archive. Its TextWorld version (1.6.2) also differs; that is recorded but does not decide the class. Its lab spot-check passed on 2026-11-24 ([report](data/contrib/placebo-v4-B03-r1-mt0-fr0/spotcheck/README.md)). |

## Formal analysis

| Contributor | Contribution |
|---|---|
| [@2018cx](https://github.com/2018cx) | Analyses of the V5B result: per-task outcomes ([#239](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/239)), action-format counter coverage ([#240](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/240)), scoring after mixed retry exhaustion ([#241](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/241)) and placebo versus no-memory outcomes by task ([#242](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/242)). |
