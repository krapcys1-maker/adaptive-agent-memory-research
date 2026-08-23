# Contributing

Contributions are welcome at three depths, and only the last one needs a background in memory research.

## Quick start

```bash
git clone https://github.com/krapcys1-maker/adaptive-agent-memory-research
cd adaptive-agent-memory-research
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The suite should pass. One test is marked `xfail` because of a known cross-platform defect that is tracked in an open issue, so you will see either `1 xfailed` on Linux or `1 xpassed` on Windows. Both are expected; neither means your checkout is broken.

Two more things worth running before you change anything, because they tell you what the project checks about itself:

```bash
python scripts/verify_memory_integrity.py      # invariants of the append-only memory log
python scripts/audit_repository_claims.py      # declared hashes, registry paths, cross-references
```

If any of this fails on your machine, open an issue saying so. Setup that only works for the maintainer is a real defect and reporting it is a real contribution.

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

Work on a branch and open a pull request. CI runs the suite on Python 3.11 and 3.12, verifies the memory log, and rejects any pull request that deletes or rewrites a line of `memory/events.jsonl`.

That last rule is not a formality. The canonical log is append-only: a conclusion is revised by appending a supersession that records the reason, never by editing history so it looks consistent in hindsight.

Keep a pull request to one topic. Describe what sources were added, what claims changed, and what disagreements remain open.

## Adding a paper

1. Add a row to `data/catalogs/papers-curated.csv`, including `reading_state`.
2. Add important claims to `docs/07-literature/evidence-ledger.csv`.
3. Add a reading note only after reading the source, not merely its abstract.
4. Include limitations and relevance to a research question.

`status` records what kind of publication it is; `reading_state` records how far
we engaged with it. They are different questions and were conflated until the
audit measured the cost: of 174 catalogued sources, 57 had never been cited by
any claim and only 18 had a full-read note. See
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

## Code of conduct

All participants are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

Criticism of a claim, a method, or a result is welcome and expected; criticism of a person is not. Disclosing prior exposure or conflicts of interest is treated as good practice.
