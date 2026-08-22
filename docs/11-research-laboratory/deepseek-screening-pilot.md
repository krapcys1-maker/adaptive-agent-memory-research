# DeepSeek V4 Flash screening admission pilot

Status: completed; admitted for candidate generation only

## Purpose

Test whether a low-cost API worker can prepare useful literature-screening candidates without becoming an evidence authority. The worker receives only public bibliographic metadata and abstracts already present in the OpenAlex discovery catalog.

## Hard constraints

- model: `deepseek-v4-flash`;
- thinking mode disabled;
- JSON output required and schema validated;
- cumulative conservative budget cap: USD 10;
- cost calculated using configured peak cache-miss input and output rates;
- API key loaded from an ignored `.env` file and never logged;
- no private files, full copyrighted PDFs, personal data, or secrets;
- outputs remain `model-candidate-unreviewed` until source-level review;
- no candidate writes directly to the evidence ledger or accepted project memory.

## Pilot

Five profiles, five records each:

1. complementary learning systems and replay;
2. allocation and neuromodulated salience;
3. semantic compression and rate-distortion;
4. prospective memory, offloading, and metamemory;
5. durable, temporal, and provenance-preserving storage.

Selection is frozen and hashed before the first API call. It mixes highly cited, recent, and deterministic-hash candidates so that the pilot is not only a popularity sample.

## Admission checks

Required before expanding to 25 records per profile:

- 100% parseable JSON and exact job-ID coverage, or a documented infrastructure retry;
- no invented DOI/source identity;
- decisions are plausible from the supplied abstract in a manual spot check;
- uncertainty is used where metadata are insufficient;
- excluded and included examples both occur unless the frozen sample genuinely lacks one class;
- no output is represented as a fully read or verified claim;
- conservative projected cumulative cost remains below USD 10.

Scientific precision, recall, locator accuracy, and reviewer-time reduction require a later independently labeled gold sample. Passing this pilot authorizes expanded candidate generation, not scientific reliance.

## Artifacts

- `scripts/screen_literature.py` — deterministic preparation, API adapter, validation, resume, and hard budget enforcement;
- `data/lab/api-screening/<run-id>/manifest.json` — frozen input and pricing assumptions;
- `jobs.jsonl` — public screening inputs;
- `candidates.jsonl` — unreviewed structured outputs;
- `calls.jsonl` and global `budget-ledger.jsonl` — token, model, latency, and conservative cost audit;
- `errors.jsonl` — retained API and schema failures;
- `summary.json` — run totals and validation rate.

## Interface references

Retrieved 2026-08-22 from the official DeepSeek documentation:

- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/json_mode/
- https://api-docs.deepseek.com/quick_start/pricing/

The run manifest freezes the accounting rates used for this experiment because live API pricing can change.

## Outcome

The 25-record v1 pilot was preserved as a failed policy check after a missing-abstract record was marked `include`. Prompt v2 passed the repeated 25-record pilot. The expanded 125-record run produced 125/125 schema-valid outputs and no API errors, but repeated the same policy violation twice. A deterministic post-validator downgraded both decisions and preserved the model outputs for audit. Cumulative conservative cost across both pilots and the expanded run was USD 0.0613668.
