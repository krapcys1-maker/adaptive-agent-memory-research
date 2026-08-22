# DeepSeek candidate-screening report

Status: completed candidate generation; source-level screening pending

## Scope

- Model: `deepseek-v4-flash`
- Frozen jobs: 125 (25 in each of five search profiles)
- API calls: 25
- Schema-valid outputs: 125/125
- API or schema errors: 0
- Conservative run cost: USD 0.0437338
- Conservative cumulative cost, including both pilots: USD 0.0613668
- Hard budget: USD 10.00

These are model-generated candidates, not accepted evidence. No coverage-matrix status is changed by this run.

## Normalized queue

| Profile | Include | Maybe | Exclude | Deterministic overrides |
|---|---:|---:|---:|---:|
| allocation/salience | 7 | 16 | 2 | 0 |
| complementary learning systems/replay | 9 | 14 | 2 | 1 |
| durable storage | 4 | 9 | 12 | 0 |
| prospective memory/metamemory | 9 | 13 | 3 | 1 |
| semantic compression | 8 | 5 | 12 | 0 |
| **Total** | **37** | **57** | **31** | **2** |

The normalized queue is `review-queue.jsonl`. Raw model outputs remain in `candidates.jsonl`.

## What the run established

1. The API is inexpensive enough for candidate generation at this scale.
2. Structured output was reliable in this run, but instruction following was not perfectly reliable.
3. The model twice marked records without abstracts as `include`, despite an explicit rule. The deterministic policy layer downgraded both to `maybe` and retained the raw model decision.
4. Query precision varies substantially by profile. Durable-storage and semantic-compression searches each produced 12/25 exclusions, indicating scope drift or overly broad queries.
5. Duplicate-title inspection found two repeated titles. DOI/source-identity deduplication is required before human screening.

## Known validity limits

- The same system designed the prompt and performed the first plausibility inspection; this is not independent review.
- OpenAlex metadata and reconstructed abstracts are discovery aids, not substitutes for reading the source.
- A plausible rationale does not establish that a paper supports a claim.
- Search-profile yield cannot be compared as prevalence because queries and source coverage differ.
- Cost uses conservative peak-rate accounting rather than treating cached input as guaranteed.

## Decision

Pass the worker for expanded **candidate generation only**. Do not let it promote evidence, modify claims, or mark a research area screened. Next, deduplicate by stable source identity and manually review all 37 `include` candidates plus a stratified sample of `maybe` and `exclude` decisions.
