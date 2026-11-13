# Contributing

Contributions are welcome at three depths, and only the last one needs a background in memory research.

## Quick start

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research
cd adaptive-agent-memory-research
python -m pip install -r requirements-dev.txt
python tasks.py check
```

`python tasks.py check` runs every gate CI runs, in the order CI runs them, and
exits non-zero if any of them fails. It is the answer to *"did I break
anything?"* and the one command a pull request must pass. It takes about five to six minutes (321 s measured once on one Windows machine, when the suite had 2,661 tests with 21 skipped; the suite has grown since, and the CI run shows the current count), almost all of it the test suite, once the one-time install (about 230 MB, mostly `transformers`, which is needed only to import one frozen audit script) is done. CI also runs the memory module's tests on Python 3.14 and a diff guard on `memory/events.jsonl`, which `check` does not. Use a full clone (no `--depth`), because one audit test reads an old commit with `git show`; on Windows, if git prints "Filename too long", run `git config --global core.longpaths true` first.

The test suite should pass with no failures. A green run still reports some
skipped tests. Most need optional local inputs that a fresh clone does not have
(a Mem0 virtualenv, a CUPMem checkout, `ripgrep`); skipping them is expected.

The other targets, for when you do not want to wait for the whole thing
(timings measured on one laptop):

```bash
python tasks.py fast      # ~0.2s -- memory integrity + source pipeline; fine in a pre-commit hook
python tasks.py test      # ~6min -- the test suite alone
python tasks.py audit     # ~10s  -- both audits, without the test suite
python tasks.py --list    # what each target runs, and roughly how long it takes
```

For the newer parts of the repository, run only what you touched:

```bash
python -m pytest -q tests/test_wmb_memory_kernel.py tests/test_wmb_kernel_v2.py   # the memory module: 22 + 94 tests, about 25 s, needs only pytest
python -m pytest -q tests/test_wmb_*.py               # the writer-memory benchmark and the module: 309 tests, about a minute
python -m pytest -q tests/test_lifesim_*.py           # LifeSim: 859 tests, about 2 minutes
```

Each gate is still an ordinary script, so you can always run one directly —
`python scripts/verify_memory_integrity.py` and friends — and `tasks.py` prints
the exact command before it runs it, so a failure tells you what to re-run.

Two of these tell you what the project checks about itself and are worth reading
the output of even when they pass: `verify_memory_integrity.py` covers the
invariants of the append-only memory log, and `audit_repository_claims.py`
covers declared hashes, registry paths and cross-references.

If any of this fails on your machine, open an issue saying so. Setup that only
works for the maintainer is a real defect and reporting it is a real
contribution.

## Fork and pull request

Nobody, including regular contributors, needs or gets direct write access to `main`. Fork the repository, create a branch, push it to your fork and open a pull request against `main`. CI runs on the pull request; a maintainer reviews and merges. Follow the [first contribution walkthrough](docs/00-project/first-contribution-walkthrough.md) for the steps from a fresh fork through reading CI. The broader guide, with tasks by interest (programming, testing, reading publications, reproducing experiments, proposing mechanisms, independent review), is [Join the research](docs/00-project/join-the-research.md).

Two issue templates exist for contributions that are not code: a [reproduction report](.github/ISSUE_TEMPLATE/05-reproduction-report.md) (you ran something and want to say what matched) and a [mechanism proposal](.github/ISSUE_TEMPLATE/06-mechanism-proposal.md) (you have an idea: state the failure it addresses and the cheapest test that could show it does not work).

## Three ways in

### 1. Software work, no research background

Look for [`good first issue`](../../labels/good%20first%20issue) and [`no-expertise-needed`](../../labels/no-expertise-needed).

These are ordinary, scoped engineering tasks with explicit acceptance criteria. You do not need to read the research to do them well. Comment on the issue to claim it so two people do not duplicate the work.

### 2. Engineering the research machinery

Look for [`track:engine`](../../labels/track%3Aengine).

These build what the research needs in order to run at all: sealed held-out splits, error-decorrelation measurement, the association layer, a bitemporal schema. They need care and taste but not domain expertise. Read the linked design document in the issue before starting, and say in the issue if you think the design is wrong — that is more valuable than implementing something you believe is mistaken.

### 3. Evidence and review

Look for [`research`](../../labels/research) and [`independent-review`](../../labels/independent-review).

Read [the independence ladder](docs/00-project/independence-ladder.md) first. It explains why much of what once required an expert reviewer is now a mechanical check, and what genuinely still needs human judgement. It also explains why disclosing prior exposure to an artifact is treated as good practice rather than as a disqualification.

### Taking an issue

Comment on the issue before you start — "I'll take this", or the part you will do — so two people do not duplicate the work. Read the whole issue first: most say what "done" means and roughly how long the work takes (the `effort:S`, `effort:M` and `effort:L` labels mean an hour or two, half a day and several sessions). If the first step is a design question, post your answer as a comment before writing code. If you stop, say so in the issue; someone else can pick up from your notes. Ask questions in the issue itself, in any language, rather than privately, so the answer helps the next person. A negative or partial result is a valid result and is recorded as one.

Areas have their own labels: [`kernel`](../../labels/kernel) (the memory module), [`wmb`](../../labels/wmb) (the writer-memory benchmark), [`lifesim`](../../labels/lifesim) (the synthetic-life generator). The pinned issue [Status and where help is wanted](../../issues/84) lists everything open by effort.

## The writer-memory track

Since November 2026 part of the work is a memory for an agent that writes, and the instruments to test it. Where things are and how to run them:

| Area | Where | Run | Worth knowing |
|---|---|---|---|
| The memory module | live line: `scripts/wmb/kernel/memory_kernel.py` (0.2.0), `tests/test_wmb_kernel_v2.py`; frozen: `scripts/wmb/memory_kernel.py` (0.1.0), `tests/test_wmb_memory_kernel.py` | `python -m pytest -q tests/test_wmb_memory_kernel.py tests/test_wmb_kernel_v2.py` (22 + 94 tests, about 25 s, pytest only; CI runs them on Python 3.14 too) | One standard-library file with no effects on import. Version 0.1.0 is frozen as the instrument of WMB-R1: its digest is declared in that study's `config.json`, so the file is not edited (see "Frozen files" below). Version 0.2.0 is now pinned by nine experiment manifests as well, so it is not edited either: the next kernel version is a new versioned module next to it, with its own `VERSION`, CHANGELOG and tests (the owner's decision of 2026-11-13; see `scripts/wmb/kernel/README.md`) |
| The writer-memory benchmark (WMB) | `scripts/wmb/`, `data/lab/wmb-v0/`, `data/lab/wmb-r1-retrieval/`, [specification](docs/11-research-laboratory/memory-benchmark-spec-v0.md) | `python -m pytest -q tests/test_wmb_*.py` (403 tests, about a minute; needs `requirements-dev.txt`) | The judge battery, the small-sample statistics, the record contract and R1. Experiments on a live account's texts publish aggregates only, so some pipelines cannot be re-run outside the maintainers' machine; their tests run on invented fixtures |
| AAM experiments | `data/lab/aam-*/` (each README is the preregistration and the results) | see the README of the experiment (most have a "Files" section) | Not entered in `data/lab/experiment-registry.csv`. Anything that calls a hosted model needs an issue and a decision first (see below) |
| LifeSim | `scripts/corpus/lifesim/`, `scripts/lifesim/`, `data/lab/aam-lifesim/` | `python -m pytest -q tests/test_lifesim_*.py` (859 tests, about 2 minutes; ten of the twelve files need only pytest) | A deterministic generator of synthetic lives. Use development seeds 0 to 999 only |

## Research principles

These apply to every contribution that touches a claim.

- Prefer primary sources: peer-reviewed papers, official preprints, official repositories, dataset cards.
- Mark preprints and unreplicated claims clearly.
- Do not convert an analogy into a fact.
- **Preserve negative evidence and failed ideas.** A run that produced nothing is recorded, not deleted.
- Record exact versions, dates, benchmark settings, and judge models.
- Do not commit external repositories, datasets, or paper PDFs unless redistribution is explicitly allowed.

For every important claim, state six things: the primary source; what it actually demonstrates; its limitations and competing interpretations; the separation between a biological finding and any proposed AI analogue; the analogue rewritten as a falsifiable hypothesis; and what evidence would reject it.

### Confidence vocabulary

`established` · `supported` · `preliminary` · `hypothesis` · `analogy` · `speculation` · `rejected`

Use the weakest label the evidence supports.

## Making a change

Work on a branch and open a pull request. CI runs the suite on Python 3.11 and 3.12, runs the memory module's tests on Python 3.14 (pytest only), verifies the memory log, runs the repository claim audit (it fails on a critical finding, that is a declared hash that no longer matches a frozen file), and rejects any pull request that deletes or rewrites a line of `memory/events.jsonl`.

That last rule is not a formality. The canonical log is append-only: a conclusion is revised by appending a supersession that records the reason, never by editing history so it looks consistent in hindsight.

Keep a pull request to one topic. Describe what sources were added, what claims changed, and what disagreements remain open.

## Frozen files, thresholds and seeds

A preregistered experiment here has a README (the question, the arms, the readings and the thresholds, written before any result) and a `config.json` with its parameters and the SHA-256 digests of the scripts and inputs it ran. The commit that fills those digests is the *freeze*, and after it the frozen files are not edited. If you find a bug in a frozen script or a mistake in a README, open an issue and say what you found; the fix goes in a new version, or in an amendment appended to the README with its reason (see the "Amendments" sections of the existing experiments), never in a silent edit. Shared helpers are frozen this way too, because every experiment pins the scripts it ran, so check before you edit: `python scripts/pinned_files.py PATH` lists the manifests that pin a file (`--check` exits 1 for a frozen one, for a pre-commit hook), and a frozen helper gets a new versioned successor instead of an edit. CI will tell you when a change touches a frozen file: the claim audit (`python scripts/audit_repository_claims.py`) and, for WMB-R1, a test that compares the declared digests with the files. If one of them fails because of your change, do not edit the declaration or the test to make it pass; say so in the pull request, and the maintainers record the change (as `data/lab/wmb-v0/slice0/SUPERSEDED.json` does for slice 0).

Thresholds, practical-significance margins and the rule that turns a number into a verdict are fixed before the first number and are not changed after seeing data, even when the data show they were badly chosen; the honest response is to report the reading as it came out, say the threshold was mistaken, and register a new version with new seeds. Seeds follow the same logic: development seeds are for debugging and may be reused, but confirmation seeds and sealed test epochs are looked at once, so do not run them (LifeSim's confirmation seeds are 5000 to 5099). A gate that fails on the real generator is reported as failed, never tuned away; a null, mixed or negative result is a complete answer. Anything that calls a hosted model API needs an issue and a decision first; no key appears in a script, a README or a log. Never commit texts from private sources (where an experiment used a live account's texts, only aggregates are published) and never paste absolute paths of your machine into a document; use paths relative to the repository.

## Adding a paper

1. Add a row to `data/catalogs/papers-curated.csv`, including `reading_state`.
2. Add important claims to `docs/07-literature/evidence-ledger.csv`.
3. Add a reading note only after reading the source, not merely its abstract.
4. Include limitations and relevance to a research question.

`status` records what kind of publication it is; `reading_state` records how far
we engaged with it. They are different questions and were conflated until the
audit measured the cost: of 174 catalogued sources, 57 had never been cited by any claim and only 18 had a full-read note (on 23 August; today: 220, 57 and 24; `python scripts/audit_source_pipeline.py` prints the current figures). See
[`data/catalogs/README-reading-state.md`](data/catalogs/README-reading-state.md).

Raise a reading state in the same change that adds its artifact — `full-read`
with the note, `abstract-read` with the abstract-level claim. A state raised
without the artifact is a claim about work that left no trace.

## Adding a repository

1. Add it to `data/catalogs/repositories-seed.csv`.
2. Record purpose, category, license, and proposed use.
3. Refresh metadata using `scripts/refresh-github-catalog.ps1`.
4. Do not vendor its source into this repository.

## Templates

```text
Claim:
Status: established | supported | preliminary | hypothesis | analogy | rejected
Source:
Population/system:
What was measured:
What was not demonstrated:
Relevance to agent memory:
Competing explanation:
Falsifiable test:
```

```text
Date:
Decision:
Reason:
Evidence:
Alternatives:
Revisit when:
```

## Project memory

This repository keeps its own append-only research memory in `memory/events.jsonl`, readable through `tools/project_memory/cli.py` or an MCP server. If your change establishes a durable decision, a sourced finding, an important failure, or a new hypothesis, record it:

```bash
python tools/project_memory/cli.py add --kind finding \
  --title "..." --summary "..." --source "path/or/url" --confidence medium
```

Findings and failures require at least one source reference; the mechanical gate enforces it. Never store secrets, credentials, personal data, or speculation labelled as fact.

## Independent review

Independent review remains the strongest tier of evidence and the project's scarcest resource. It is no longer the only door — see the [independence ladder](docs/00-project/independence-ladder.md) — but it is still what confirmatory claims require.

If you are reviewing a frozen packet: use only the `blind/` directory of that packet, complete and hash the review form and attestation before any reveal comparison, and do not modify author labels. Independent, advisory, author, and adjudicated labels stay as separate records.

A reviewer with prior exposure can still provide useful criticism. Disclose the exposure; it does not disqualify the contribution, it just means that contribution alone cannot satisfy the blind gate. A model family already used for advisory review cannot be the sole independent reviewer.

## Licensing of contributions

Code (`tools/`, `scripts/`, `tests/`, `.github/workflows/`) is Apache-2.0; documentation, research notes and experiment data are CC BY 4.0. The path map is [`REUSE.toml`](REUSE.toml) and the third-party notices are in [`NOTICE`](NOTICE). By opening a pull request you agree that your contribution is licensed under the licence of the path it touches (inbound = outbound), and that you have the right to contribute it. Do not commit text, data or code you may not redistribute.

## Code of conduct

All participants are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

Criticism of a claim, a method, or a result is welcome and expected; criticism of a person is not. Disclosing prior exposure or conflicts of interest is treated as good practice.
