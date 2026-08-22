# Optional API worker policy

Status: accepted research policy

## Decision

No external model API is required for the current research-memory system or for the first retrieval benchmarks. Canonical files, provenance, `rg`, SQLite FTS5, local embeddings, and benchmark scoring can all run on the user's disk.

An API model may later be admitted as a **replaceable batch worker** when the screened workload is large enough to justify it. It must not become the source of truth, the only reader of a source, the final scientific reviewer, or the owner of project memory.

This separates two questions:

1. **Where memory lives and how it is retrieved** — local, user-owned, reproducible infrastructure.
2. **Which model helps process material** — an optional adapter that may be OpenAI, DeepSeek, Gemini, Claude, a local model, or another provider.

## What an API worker may do

- classify discovery records for relevance;
- propose deduplication candidates;
- extract candidate claims from already extracted text;
- propose exact evidence locators for verification;
- produce structured draft source cards;
- translate search terms or generate additional search-query candidates;
- challenge a synthesis using a different model family;
- process a frozen batch for a registered cost/quality experiment.

Every output is a candidate until validated. The worker writes to a review queue, not directly to accepted claims, decisions, or benchmark gold labels.

## What it must not do alone

- promote an abstract or model summary to accepted evidence;
- assign final confidence to its own extraction;
- resolve a scientific contradiction without source-level review;
- judge the same retrieval system that supplied its context without controls;
- silently overwrite or delete canonical memory;
- receive confidential, personal, licensed, or sensitive documents without a recorded data-handling decision;
- make provider-specific fields part of the canonical memory schema.

## Provider-neutral boundary

```text
local documents
      |
      v
deterministic extraction and chunk IDs
      |
      v
local job manifest and redaction gate
      |
      v
provider adapter -> structured candidate JSON
      |                    |
      |                    v
      |              schema validator
      |                    |
      +--------------------v
                      review queue
                           |
                 source-level verification
                           |
                           v
                append-only accepted memory
```

Required common input fields:

- `job_id`, `source_id`, `chunk_id`, and content hash;
- task type and versioned prompt ID;
- permitted data class;
- requested JSON schema;
- token/output ceiling;
- model-provider adapter and model version.

Required output fields:

- input identifiers and hashes;
- candidate result with exact locator;
- uncertainty and abstention;
- model/provider/version, parameters, time, tokens, and cost;
- validation state and reviewer identity;
- error or refusal without loss of the original job.

## Admission experiment

Do not add a production batch agent merely because its per-token price is low. First register a small, frozen pilot containing easy, ambiguous, contradictory, out-of-scope, and locator-sensitive documents.

Compare the API-assisted workflow with the present subscription-assisted/manual workflow on:

- schema-valid output rate;
- verified relevance precision and recall;
- exact-locator accuracy;
- unsupported-claim and false-citation rate;
- abstention on insufficient evidence;
- reviewer minutes per accepted source card;
- total input/output tokens and actual cost;
- retry and provider-failure rate;
- agreement with an independent human or different model family;
- data-governance violations.

Admit the worker only if its preregistered thresholds are met, it materially reduces reviewer effort, all accepted claims remain traceable to sources, and removing the provider does not damage canonical memory. Keep null and failed pilots.

## Current provider note (checked 2026-08-22)

- DeepSeek's official API currently exposes `deepseek-v4-flash` and `deepseek-v4-pro` through OpenAI- and Anthropic-compatible interfaces. That compatibility makes it a plausible low-cost adapter candidate, not an architectural dependency.
- OpenAI API use requires an API project/key and metered API usage. It is not needed for the existing local MCP/CLI memory.
- Cloud data handling must be reviewed per provider and plan before sending a corpus. The default rule for this project is: unpublished, personal, confidential, or license-restricted full text stays local.
- Local dense retrieval does not require a chat-model API. Open-weight embedding models can create disk-resident vectors when the dense-retrieval stage gate opens.

Official operational references:

- DeepSeek API models and pricing: <https://api-docs.deepseek.com/quick_start/pricing/>
- DeepSeek API model list: <https://api-docs.deepseek.com/api/list-models/>
- DeepSeek privacy policy: <https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html>
- OpenAI API quickstart: <https://developers.openai.com/api/docs/quickstart/>
- OpenAI API data controls: <https://developers.openai.com/api/docs/guides/your-data/>

Provider documentation is mutable. Recheck model IDs, prices, retention, training use, storage location, licensing, and terms at the time of every registered pilot.
