# PMLAB-MAP stage development v1

Status: annotation contract frozen; first contract/entity tranche authored and unreviewed; no candidates implemented

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

## First authored tranche

`contract-entity-groups-v1.jsonl` contains 22 semantic groups expanded to 44 paired rows:

- 8 contract/span groups covering valid nested output, wrong-but-valid output, malformed/missing fields, and dependency/ID integrity;
- 14 entity groups covering aliases, catalog collisions, missing entities, non-entity phrases, coreference, and multi-entity relations.

`cases.jsonl` contains gold and provenance. `model-cases.jsonl` and `independent-review-queue.jsonl` exclude gold, criticality, split, stratum, and author rationale. The manifest status remains `authored-unreviewed-development-data`; these cases may not be used as reviewed evidence or as a confirmation set.

## Blind advisory review

After the corpus freeze at `7481b44`, DeepSeek V4 Flash reviewed all 44 rows from a prompt and job packet frozen at `ceae9d4`. The worker saw the review inputs and catalog but not gold, criticality, strata, scores, provenance, or a candidate implementation.

- 44/44 responses passed the output validator at a conservative cost of USD 0.01322860;
- exact label agreement was 40/44 overall and 30/34 on critical rows;
- entity/NIL labels agreed on 28/28 rows;
- four contract rows disagreed: both languages of `ST-C03` and `ST-C07`;
- direct traces show that `ST-C03` uses a non-source paraphrase and that `ST-C07` contains a forward dependency, so the model objections are retained but do not alter gold;
- the worker's `case_validity` field is unusable because it conflated deliberately defective payloads with defective benchmark cases.

The complete raw and derived record is under `../api-screening/deepseek-v4-flash-map-stage-advisory-review-20260822/`. This remains an advisory worker review, not the independently signed review required for corpus freeze.
