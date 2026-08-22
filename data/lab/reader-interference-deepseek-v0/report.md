# DeepSeek reader-level stale-value interference pilot

Status: invalid due to label leakage; excluded from interpretation

Forty frozen synthetic cases crossed eight histories with five conditions: gold only, gold plus unrelated records, gold before four stale versions, gold after four stale versions, and stale-only.

DeepSeek V4 Flash returned the exact expected value, immutable evidence ID, and abstention decision in 40/40 cases, but the request payload accidentally included all three expected fields. The result is invalid. Run cost remains recorded as USD 0.00796224.

This run provides no evidence about reader interference. It demonstrates a benchmark leakage failure and motivates a mandatory payload audit that verifies gold fields are absent before every model call.

The next reader stress curve should vary stale count `{1,4,16,64}`, value similarity, missing or contradictory validity metadata, gold position, instruction explicitness, and query language. Gold-only and stale-only remain mandatory controls.
