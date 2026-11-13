# Join the research

Status: reviewed. Last checked against GitHub on 13 November 2026 (`main` at `1b673d3`).

AAMR (Adaptive Agent Memory Research) studies long-term memory for LLM agents: local-first, model-agnostic, preregistered where possible, with negative results kept. It is an open project and wants more contributors, from one-hour fixes to long collaborations. This page is the detailed version of the "Join the Research" section of the [README](../../README.md). The rules that apply to every contribution are in [CONTRIBUTING.md](../../CONTRIBUTING.md); this page says what each kind of contribution looks like and how to begin.

## What AAMR is, in five lines

- **Goal.** Find out whether *measured future usefulness*, rather than similarity or retrieval frequency, should decide what an agent keeps, consolidates, revises and forgets. See [the five research questions](../../README.md#the-five-research-questions).
- **What works today.** A dependency-free, offline, append-only project memory with an MCP server and a CLI ([two-minute setup](../../README.md#give-claude-code-persistent-project-memory-in-two-minutes)); a one-file memory module; deterministic synthetic corpora and a synthetic-life generator; the mechanical checks that keep the evidence honest (`python tasks.py check`).
- **What is experimental.** Every claim that a memory *design* helps an agent. Nothing here is independently reviewed, and the [delivery audit](project-delivery-audit-2026-11-04.md) separates implemented tools from missing agent-level evidence. A generic adaptive-memory product is not validated.
- **How it is run.** Experiments are preregistered in a README before the first model call, frozen by SHA-256 digests, and reported with their limits. Failed and retracted results stay in the repository.
- **Where to look first.** [Status and where help is wanted (#84)](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/84) and the [laboratory map](../11-research-laboratory/lab-map.md).

## The first hour

1. `git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research` (a full clone: one audit test reads history), then `python -m pip install -r requirements-dev.txt` and `python tasks.py check`. About six minutes after the install on one Windows machine.
2. Try the memory tool on your own project: [two-minute setup](../../README.md#give-claude-code-persistent-project-memory-in-two-minutes). Rough edges you meet there are reportable.
3. Read the [laboratory map](../11-research-laboratory/lab-map.md) for the area you like (the memory module `kernel`, the writer-memory benchmark `wmb`, `lifesim`).
4. Choose a task below or ask in [Discussions](https://github.com/krapcys1-maker/adaptive-agent-memory-research/discussions/85) ("Introduce yourself").
5. Comment on the issue to claim it. Fork, branch, change, open a pull request against `main`.

Nobody has direct write access to `main` by default; maintainers merge reviewed pull requests after CI passes. You never need to ask for permission to fork and propose.

## What you can do

### Programming

Ordinary engineering with explicit acceptance criteria. The standard-library-only memory engine (`tools/project_memory/`) takes no new dependencies without a prior proposal in an issue.

- Small: [#46](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/46) inspect a harness catalogued as a benchmark; [#114](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/114) an advisory Markdown link check in CI; [#115](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/115) `reuse lint` in CI, or a documented reason it cannot run.
- Medium: [#74](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/74) a public labelled set for the reference guard.
- Large: [#39](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/39) temporal query layer, [#41](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/41) the first history family, [#80](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/80) and [#81](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/81) LifeSim instrument gates (development seeds only).

A change contains the code, its tests, and the output of `python tasks.py check`.

### Testing

- [#113](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/113): follow the README from zero as a newcomer and log every friction point. [#117](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/117): write the "first contribution" walkthrough this page lacks.
- Run the gates on your platform and Python version and report what happened. Success is a result too. Use the [reproduction report template](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/new?template=05-reproduction-report.md).
- Try to break an instrument: [#42](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/42) (the sealed split carries three guards, each added after its attack was reproduced; a fourth attack is worth more than a finished task).
- Write a minimal synthetic counterexample for an open boundary failure: [#106](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/106), [#107](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/107), [#108](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/108), [#110](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/110). These describe a candidate that lives in an open pull request (see below), so read the issue for the commit it refers to.

### Analysing publications

Reading that changes what the project claims: [#76](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/76) and [#75](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/75) (check citations against their sources), [#48](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/48) (verify six reported prior-art systems), [#37](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/37) (assign a reading state to uncited sources), [#7](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/7) (audit the public benchmarks). Follow [Adding a paper](../../CONTRIBUTING.md#adding-a-paper): a primary source, what it demonstrates, its limits, and a reading note only after reading beyond the abstract.

### Reproducing experiments

Every experiment under `data/lab/` has a README with its question, readings and thresholds, and most list the command that reproduces its analysis. Reproduce the analysis from the stored records, compare with the reported numbers, and file a [reproduction report](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/new?template=05-reproduction-report.md). Model outputs cannot be regenerated exactly, and some experiments used a live account's texts and publish only aggregates; the report should say which part you could and could not repeat. A mismatch is a finding, not an accusation. A ready first task that needs no model, GPU or key: [#116](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/116), recompute the statistics of the EXP-PILOT-0 results from its results file.

### Proposing your own mechanism

New ideas are welcome and the project does not discard an idea for being unfashionable. To propose one:

1. Float it in [Discussions → Ideas](https://github.com/krapcys1-maker/adaptive-agent-memory-research/discussions/87), or go straight to the [mechanism proposal template](https://github.com/krapcys1-maker/adaptive-agent-memory-research/issues/new?template=06-mechanism-proposal.md).
2. State the failure mode it addresses, the prior art you checked (the [related-work note](related-work-and-novelty.md) and the [systems catalog](../04-systems/catalog.md) are starting points), the cheapest test that could show it does not work, and its cost in context, calls and storage.
3. The maintainers and other contributors discuss it; if it survives, it enters an exploratory test under the [research-to-experiment gate](../11-research-laboratory/research-to-experiment-gate.md). The project's design stance is to build on what exists before inventing, and to compare any mechanism against a strong simple baseline.

A proposal is not evidence. A mechanism that is only described has the status `hypothesis`.

### Independent review

The scarcest resource. Read the [independence ladder](independence-ladder.md), then pick one of the [`independent-review`](https://github.com/krapcys1-maker/adaptive-agent-memory-research/labels/independent-review) issues. Disclose any prior exposure; it does not disqualify you.

## Open pull requests and what they mean for you

As of 13 November 2026 two pull requests are open. They are documented here so a newcomer does not mistake them for part of `main`.

| PR | State | What it is | How you can help |
|---|---|---|---|
| [#105](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/105) | Draft; large (277 files); CI green; mergeable | A source-grounded structured-memory candidate with boundary repairs and local reader comparisons. Its own description records that semantic capture, evidence sufficiency and fresh external confirmation are unresolved | Review; produce counterexamples for #106–#108 and #110. It is not a claim of general memory readiness |
| [#111](https://github.com/krapcys1-maker/adaptive-agent-memory-research/pull/111) | Open, ready for review; small (27 files); CI green; mergeable | EXP-PILOT-0: whether a local tool-using agent does better on a function-calling benchmark when shown its own earlier episodes. Its description reports an intermediate result: the preregistered "memory works" row was not met | Statistical re-analysis of its published `results.json`; replication on another local model |

Both append to `memory/events.jsonl` and to `data/lab/experiment-registry.csv` (a trial merge of the two branches conflicts on exactly those two files). The canonical-store guard in CI treats the log as append-only, so whichever merges second needs a rebase that keeps both sets of appended lines. Maintainers decide merge order. Reviews are welcome on either; please review the code and the evidence, and say what you inspected.

## Credit and conduct

Contributors are credited in the commit and pull-request history. Authorship of any future write-up has not been decided; the maintainers will state their criteria before one is drafted, not after. Disclosing a conflict of interest or prior exposure is good practice here. Criticism of a claim, a method or a result is expected; criticism of a person is not ([code of conduct](../../CODE_OF_CONDUCT.md)). Repository content is in English; issues and discussions may use any language.

## Rules that do not bend

These come from [CONTRIBUTING.md](../../CONTRIBUTING.md) and keep the evidence trustworthy:

- Frozen files, thresholds and seeds are not edited after the fact. Confirmation seeds and sealed epochs are not run.
- `memory/events.jsonl` is append-only; CI rejects a rewrite.
- No private data, keys or machine paths. Hosted-model API calls need an issue and a decision first.
- Findings need sources. Preprints and unreplicated claims are marked.
- Preserve negative evidence.

## Licence

Code is Apache-2.0; documentation, research notes and data are CC BY 4.0. By opening a pull request you license your contribution under the licence of the path it touches. See the [licence map](../../REUSE.toml) and [NOTICE](../../NOTICE).
