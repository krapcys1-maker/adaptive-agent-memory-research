# PMLAB-MAP stage development v1

Status: design and annotation contract frozen as a candidate; no cases authored yet

This directory defines the next development instrument after both integrated PMLAB-MAP arms failed post-freeze challenge v0. It is not a parser implementation and contains no candidate outputs.

## Purpose

Build minimal pairs that isolate one mapper stage at a time:

1. contract and exact-span alignment;
2. obligation graph and unsupported-structure status;
3. entity candidate retrieval plus typed NIL/ambiguity;
4. predicate and namespace candidate retrieval/selection;
5. temporal and authorization scope;
6. completeness-certificate routing.

Construction and challenge v0 may inform development strata, but their rows cannot be copied into a future confirmation set. `stage-dev-v1` is development data. A separately authored and independently reviewed stage challenge must be frozen after candidate mechanisms are fixed.

## Files

- `case-schema-v1.json` — provider-neutral envelope and stage-specific output contracts;
- `case-allocation-v1.csv` — preregistered semantic-group quotas for development and later challenge authoring;
- `annotation-manual-v1.md` — labeling and disagreement rules;
- `independent-review-checklist-v1.md` — blind review packet requirements.

## Freeze order

1. Review this contract and allocation without candidate outputs.
2. Author semantic groups; expand each group to paired PL/EN rows.
3. Run deterministic structural validation.
4. Obtain independent review of critical labels and a sample of ordinary labels.
5. Adjudicate while preserving original labels and dispositions.
6. Commit the generated development corpus.
7. Only then implement or modify stage candidates.

The future stage challenge repeats steps 2-6 after candidate versions are frozen, using new semantic groups, catalogs, schemas, surfaces, and ambiguity patterns.
