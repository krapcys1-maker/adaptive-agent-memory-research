# Contributing

## Principles

- Prefer primary sources: peer-reviewed papers, official preprints, official repositories, and dataset cards.
- Mark preprints and unreplicated claims clearly.
- Do not convert an analogy into a fact.
- Preserve negative evidence and failed ideas.
- Record exact versions, dates, benchmark settings, and judge models.
- Do not commit external repositories, datasets, or paper PDFs unless redistribution is explicitly allowed.

## Adding a paper

1. Add a row to `data/catalogs/papers-curated.csv`.
2. Add important claims to `docs/07-literature/evidence-ledger.csv`.
3. Add a reading note only after reading the source, not merely its abstract.
4. Include limitations and relevance to a research question.

## Adding a GitHub project

1. Add it to `data/catalogs/repositories-seed.csv`.
2. Record its purpose, category, license, and proposed use.
3. Refresh metadata using `scripts/refresh-github-catalog.ps1`.
4. Do not vendor its source into this repository.

## Claim template

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

## Decision template

```text
Date:
Decision:
Reason:
Evidence:
Alternatives:
Revisit when:
```

## Pull requests

- Keep a pull request focused on one research topic or catalog update.
- Describe sources added, claims changed, and open disagreements.
- Use absolute claims only when the evidence supports them.

## Independent benchmark review

The current highest-priority contribution is independent review of the PMLAB-MAP stage labels. Claim the dedicated GitHub issue template before opening author or advisory artifacts.

Reviewers receive only `data/lab/pmlab-map-stage-dev-v1/independent-adjudication-v1/blind/`. Complete and hash the review form plus attestation before any reveal comparison. Do not silently modify author labels: independent, advisory, author, and adjudicated labels remain separate records.

A reviewer with prior exposure can still provide useful criticism, but the contribution must disclose that exposure and cannot alone satisfy the blind independent-review gate. A model family already used for advisory review cannot be the sole independent reviewer.
