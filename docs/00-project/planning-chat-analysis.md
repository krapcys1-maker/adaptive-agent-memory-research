# Analysis of the planning discussion

Status: reviewed

Source: user-provided planning discussion, 2026-08-22. The raw conversation is not republished; this note preserves only durable research implications.

## Conclusions retained

1. A large pile of PDFs and repositories is not a research result. The useful unit is an atomic, reviewable claim connected to exact evidence, limitations, conflicts, and project relevance.
2. Research coverage must be audited per topic using reproducible queries, multiple databases, backward and forward citation search, duplicate control, and a stopping rule based on diminishing new relevant evidence.
3. Source discovery, claim extraction, methodological criticism, experiment execution, and result review should be separated.
4. Product architecture should wait until a map of known results, contested claims, missing evidence, and valid benchmarks exists.
5. AI can accelerate screening and organization, but it must not be the unchallenged author, reviewer, and judge of the same result.

## Important qualifications

### "All information" is not attainable

The defensible output is not a percentage such as "95% of all literature." The denominator is unknowable and databases change. We can only report coverage under a declared protocol and say that a topic reached provisional saturation when repeated independent search rounds produce little new relevant evidence.

### Role names do not create independence

Several agents using the same model, prompt family, corpus, and visible conclusion may reproduce the same bias. For consequential claims, independence requires at least some of:

- separated contexts and hidden system labels;
- different query strategies;
- a second model family or human reviewer;
- frozen data and preregistered metrics;
- a critic instructed to find disconfirming evidence;
- reproduction from artifacts rather than the original narrative.

### Retrieval and answering must be evaluated separately

An incorrect answer may come from failed storage, failed retrieval, bad context construction, reader-model reasoning, or an invalid judge. End-to-end accuracy alone cannot identify the failing subsystem.

### Coverage counts are not evidence quality

Initial inventory audited on 2026-08-22 before comparative expansion:

- 684 deduplicated OpenAlex discovery leads;
- 49 manually curated literature records;
- 24 locally cached PDFs;
- 39 cataloged repositories and 24 local repository directories;
- 11 claims in the original evidence ledger.

The initial discovery process used 20 query families capped at 40 results each. It did not include comparative animal memory, motor consolidation, skeletal-muscle history, immune memory, transcriptional memory, CRISPR, or non-neural learning.

After adding 12 comparative query families, the catalog contains 1,066 unique leads across 32 query families: 1,037 are marked open access and 876 expose a PDF URL and abstract through OpenAlex. These are discovery metadata, not 1,066 read or relevant papers. Spot checks found obvious query drift, so all new biological results remain `discovered-unscreened` until manual screening and snowballing. No strong biological coverage claim is currently justified.

### Search saturation needs logged denominators

The proposed "three rounds below 5% novelty" rule is useful only if each round records screened results, unique relevant additions, databases, filters, and query strategy. It is a stopping aid, not proof of completeness.

## What already existed

- paper and repository catalogs;
- an evidence ledger;
- source-quality methodology;
- benchmark and experiment outlines;
- a local project-memory bootstrap;
- initial audits of major open-source systems.

## What was missing

- a comparative biological-memory program;
- search logs and a coverage state machine;
- explicit stage gates before architectural complexity;
- a frozen retrieval-backend ladder;
- stronger independence and blinding rules;
- a minimal architecture separating evidence, claims, experiments, memory, retrieval, and model providers.

These gaps are addressed in `docs/10-comparative-biological-memory/`, `docs/11-research-laboratory/`, and `data/lab/`.
