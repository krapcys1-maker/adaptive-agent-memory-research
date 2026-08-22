# DeepSeek mapping attempt v0 — rejected adapter instrument

Status: rejected API instrument; semantic scores prohibited

The frozen prompt was sent in eight seven-case batches for 56 construction queries. The calls cost USD 0.02018324 conservatively and raised the cumulative project ledger to USD 0.34616340.

Only the first batch was accepted (7/56 predictions). Seven later responses each contained at least one schema violation, but the adapter validated the batch atomically and discarded every other result in that response. It also recorded the validation error without first preserving the raw response content. Therefore the 0.125 schema-valid rate is not an interpretable model rate, and semantic scoring is prohibited.

Repair boundary: keep the corpus, jobs, prompt, model, temperature, and batch plan unchanged; add raw-response persistence before validation and validate each result independently. The repaired adapter gets a new run directory and run ID. This attempt remains in the global budget ledger and is never deleted.
