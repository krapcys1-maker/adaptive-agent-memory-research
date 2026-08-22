# PMLAB-MAP DeepSeek construction error analysis

Status: completed optional-model construction analysis; inspectable data; not held out

## Disposition

The optional `deepseek-v4-flash` arm is rejected for promotion. It does not pass any of the main mapping gates and it adds schema-compliance failures that a production controller would have to treat as missing predictions.

| Measure | Result | Registered gate | Decision |
| --- | ---: | ---: | --- |
| schema-valid predictions | 45/56 (0.804) | all cases must be scoreable | fail |
| obligation F1 | 0.710 | >= 0.90 | fail |
| critical full recall | 0.607 | >= 0.95 | fail |
| entity accuracy | 0.873 | >= 0.95 | fail |
| predicate accuracy | 0.836 | >= 0.95 | fail |
| temporal-label accuracy | 0.673 | diagnostic only | fail as evidence of robustness |
| end-to-end exact | 0.143 | no construction promotion threshold | diagnostic failure |
| false closure | 2 | 0 | fail |
| safe critical unresolved handling | 0.833 | 1.0 | fail |

Invalid or missing outputs are scored as failures. The scorer does not repair, retry, or silently coerce model output.

## Interface failures

Eleven records failed the frozen response contract:

- seven used an empty entity string;
- two used a span that was not an exact substring of the query;
- two attached an unsafe certificate to an unresolved query.

The failures were not language-specific: seven occurred in English and four in Polish, while end-to-end exact was identical in both languages (0.143). This does not establish language parity because the corpus contains paired translations and is small.

## Semantic failure pattern

Only 8/56 records were end-to-end exact. Failures appear in 25/28 semantic groups. Atomic obligation discovery was sometimes correct while grounding, temporal scope, certificate state, or exact structure remained wrong. Complex composition groups also showed critical omissions: the model reached 11 critical omissions and only 0.571 structure exact.

The construction comparison therefore supports a stage-separated diagnosis:

1. response-schema compliance is a separate failure surface;
2. obligation discovery and graph structure are not equivalent to correct grounding;
3. entity, predicate, time, authorization, and completeness certificate must remain independently scored;
4. an average semantic score cannot override false closure or a critical omission.

## Validity boundary

The model saw only query text, the frozen fixture catalogs, and the frozen parser instructions; it did not see gold graphs or evaluation metadata. However, the underlying corpus was inspectable before this run and the prompt was designed for this fixture schema. The result measures construction behavior only. It is neither a held-out estimate nor evidence that this model should become a project dependency.

The first batch-atomic adapter defect remains preserved under `../pmlab-obligation-mapping-deepseek-v0/attempt-v0-batch-atomic-defect/`. Adapter v1 changed result handling and raw-response retention, not the prompt, jobs, model, temperature, or gold labels.

## Next admissible test

Freeze a new challenge after both the deterministic runner and optional-model prompt are fixed. The challenge must hold out compound signatures, schema families, surface forms, and ambiguity patterns. No failure from this construction run may be used to tune either arm before the challenge is scored.
