# Research Methodology

Status: reviewed

## Evidence hierarchy

Prefer, in order:

1. Systematic reviews, meta-analyses, and consensus reports.
2. Peer-reviewed primary studies with accessible methods and data.
3. Peer-reviewed conference papers for fast-moving ML research.
4. Official preprints with code or data.
5. Official technical documentation and repositories.
6. Independent replications and benchmark audits.
7. Engineering reports with reproducible settings.
8. Blog posts, discussions, and anecdotes only as leads.

Authority does not replace methodological scrutiny. A benchmark result is not comparable unless data version, prompts, reader model, judge, context limits, and cost are aligned.

## Claim review

Each claim should answer:

- What population, dataset, or system was studied?
- What intervention or comparison was made?
- What outcome was measured?
- What alternative explanations remain?
- Does the source support causation, association, or only a proposal?
- Does the result generalize to long-running agents?
- What would falsify the proposed AI mapping?

Important claims require a detailed claim card with an exact section, page, figure, table, code line, commit, or dataset row. An abstract is a discovery and triage source; it is not sufficient for a high-confidence mechanism claim.

## Independent challenge

The extractor of a consequential claim must not be its only reviewer. A reviewer should receive the source and claim without being told which architecture the project prefers, then record:

- whether the locator supports the wording;
- omitted boundary conditions;
- plausible alternative explanations;
- contradictory or null evidence;
- whether confidence should increase, decrease, or remain unchanged.

Multiple agents using the same model and visible reasoning are not automatically independent. Use separated contexts, different model families, blinded labels, or human review according to consequence.

## Biological translation rule

Never infer this:

```text
humans have mechanism X
therefore an AI implementation named X will work
```

Use this chain:

```text
empirical finding
→ abstract computational problem
→ candidate engineering mechanism
→ simpler baseline
→ controlled experiment
→ rejection criterion
```

## Negative evidence

Preserve:

- failed replications;
- benchmark contamination;
- judge instability;
- null results;
- mechanisms that add cost without benefit;
- cases where summaries lose decisive details;
- cases where retrieval increases hallucination or stale-memory errors.

## Updating conclusions

Do not silently overwrite a conclusion. Record:

- previous claim;
- new evidence;
- reason for revision;
- date and author;
- downstream hypotheses affected.

## Research versus implementation

Code in this phase supports discovery, downloading, cataloging, and reproducibility. It is not the product implementation. Architecture decisions remain provisional until supported by evidence and baseline experiments.
