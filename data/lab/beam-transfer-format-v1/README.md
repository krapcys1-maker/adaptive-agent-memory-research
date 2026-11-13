# BEAM format v1 — partial success and retained full-data rejection

Frozen code/plan `fc5429b` first prepared the previously cached conversation1:17,623messages,20probes. Exact reconstruction/readback succeeded with evaluator-only annotations kept out of reader files. [Content-free preparation receipt](preparation.json). No model, extraction, retrieval, answer scoring or candidate validation.

After the full pinned10-conversation source roster was fetched, v1 stopped at conversation7 on an explicit `time_anchor:null`. It required a string when the field existed. No complete full-data manifest was written; its failed output directory and source/script bytes remain retained. [Failure record](../beam-transfer-format-v2/failed-preparation.json).

The separately frozen [v2 successor](../beam-transfer-format-v2/README.md) preserves that timestamp as unknown, distinguishing explicit null from field absence. The format-only amendment uses no answer labels or model outcomes. Do not relabel v1's one-conversation success as full-tier readiness or erase its rejection.
