# Optional DeepSeek PMLAB-MAP challenge arm v0

Status: frozen input ready for API run; no output yet

This run reuses the exact frozen `pmlab-map-deepseek-v0` system prompt, `deepseek-v4-flash`, temperature zero, disabled thinking, response schema, and per-result validation adapter. Only the post-freeze challenge's model-facing queries and public schema/entity catalogs replace the construction fixture.

The worker is optional, replaceable, and never gold. Gold graphs, criticality, strata, and evaluation metadata are excluded from the request. Invalid outputs are scored as failures.
