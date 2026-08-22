# Optional DeepSeek PMLAB-MAP construction arm v1

Status: adapter-repair input freeze in preparation; no v1 API output yet

V1 reuses the exact v0 corpus, model-visible jobs, system prompt, model, temperature, and language-separated batches. It changes only the API audit adapter after v0 revealed batch-atomic validation and missing raw-response persistence.

Every raw response is written before semantic-schema validation. Each requested query is then validated independently, so one invalid graph cannot erase valid sibling results. Invalid or missing results remain scored failures and are not retried as if they were new evidence.
