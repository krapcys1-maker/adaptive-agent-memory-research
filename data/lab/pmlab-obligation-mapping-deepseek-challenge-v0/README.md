# Optional DeepSeek PMLAB-MAP challenge arm v0

Status: completed post-freeze challenge arm; rejected for promotion

This run reuses the exact frozen `pmlab-map-deepseek-v0` system prompt, `deepseek-v4-flash`, temperature zero, disabled thinking, response schema, and per-result validation adapter. Only the post-freeze challenge's model-facing queries and public schema/entity catalogs replace the construction fixture.

The worker is optional, replaceable, and never gold. Gold graphs, criticality, strata, and evaluation metadata are excluded from the request. Invalid outputs are scored as failures.

The run returned 13/28 schema-valid predictions at USD 0.01164504, taking cumulative project API spending to USD 0.37780424. Obligation F1 was 0.325, critical full recall 0.292, end-to-end exact 0.107, and two false closures occurred. See `report.md` and `error-analysis.md`.
