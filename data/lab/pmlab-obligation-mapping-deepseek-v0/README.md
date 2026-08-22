# Optional DeepSeek PMLAB-MAP construction arm

Status: input frozen; no API output yet

This directory freezes a replaceable `deepseek-v4-flash` comparator for the inspectable PMLAB-MAP construction corpus. It is not gold, not independent review, and not a held-out estimate.

The worker receives only `model-cases.jsonl`, the versioned fixture schema/entity catalogs, a reference clock, and the frozen output contract. It never sees gold graphs, evaluation metadata, strata, or scores. English and Polish translations are placed in separate stateless API batches so a translation pair does not appear in one request.

The global conservative USD 10 cap is checked before every request using cache-miss input pricing. Calls, token usage, latency, validation errors, predictions, and scoring artifacts are retained. Invalid outputs remain failures and cannot edit the corpus.
