# Optional DeepSeek PMLAB-MAP construction arm v1

Status: completed optional-model construction arm; rejected for promotion; not held out

V1 reuses the exact v0 corpus, model-visible jobs, system prompt, model, temperature, and language-separated batches. It changes only the API audit adapter after v0 revealed batch-atomic validation and missing raw-response persistence.

Every raw response is written before semantic-schema validation. Each requested query is then validated independently, so one invalid graph cannot erase valid sibling results. Invalid or missing results remain scored failures and are not retried as if they were new evidence.

Results are in `report.md`; `error-analysis.md` records the gate failures and error taxonomy. Only 45/56 predictions passed the response schema, obligation F1 was 0.710, critical full recall was 0.607, end-to-end exact was 0.143, and two false closures occurred.
