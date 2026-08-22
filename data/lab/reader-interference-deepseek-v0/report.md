# DeepSeek reader-level stale-value interference pilot

Status: completed exploratory single-model null result

Forty frozen synthetic cases crossed eight histories with five conditions: gold only, gold plus unrelated records, gold before four stale versions, gold after four stale versions, and stale-only.

DeepSeek V4 Flash returned the exact expected value, immutable evidence ID, and abstention decision in 40/40 cases. Run cost was USD 0.00796224; cumulative conservative worker cost became USD 0.07532140.

This is evidence against a reader-interference effect under these narrow conditions: explicit `valid_from`/`valid_to`, an algorithmic validity instruction, four stale competitors, batched cases, and synthetic exact values. It is not evidence that reader interference is absent generally.

The next reader stress curve should vary stale count `{1,4,16,64}`, value similarity, missing or contradictory validity metadata, gold position, instruction explicitness, and query language. Gold-only and stale-only remain mandatory controls.
