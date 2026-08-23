# Compact DeepSeek M1 review of natural-history contracts

Status: finalized author-operated advisory; not independent review and builder remains locked

Verdict: `needs_revision` at confidence 0.90.

## Fatal issues

- The source-unit schema does not enforce that unit_id is derived from the specified canonical identity fields, allowing arbitrary opaque IDs.
- The query-log schema permits origin_receipt.mode 'private_random_receipt' without requiring the receipt to be independently random or keyed, violating the unkeyed-hash prohibition.
- The contract lacks a rule that source_aliases entries must have distinct locators, risking duplicate alias collapse ambiguity.
- The policy requires freezing the UTF-8 byte ceiling before test, but the schema has no field to record that ceiling, so compliance cannot be verified.
- The contract does not require that backend_visible_fields be enforced at the data layer, only described, allowing accidental leakage.

## Repair candidates

- **major — source-unit-contract-v0.schema.json**: Add a conditional schema rule that unit_id must match the SHA-256 of the canonical identity string (version, source_type, path, locator, search_text_sha256) to prevent arbitrary IDs. Test: Generate a unit with a non-canonical unit_id and assert schema validation fails.
- **major — query-log-contract-v0.schema.json**: For origin_receipt.mode 'private_random_receipt', require the value to be at least 128 bits of entropy and not derived from query text or locator; for 'private_keyed_digest', require a key_id field outside Git. Test: Submit a query log with a receipt equal to SHA-256(query_text) and assert validation fails.
- **major — source-unit-contract-v0.schema.json**: Add a uniqueness constraint on source_aliases entries by (path, locator) to prevent duplicate aliases and ensure deterministic collapse. Test: Create a unit with two identical alias entries and assert validation fails.
- **major — policy_digest**: Add a required field 'utf8_byte_ceiling' to the source-unit schema or a separate manifest to record the frozen ceiling before test. Test: Validate that the ceiling is present and consistent across all units in a test run.
- **major — source-unit-contract-v0.schema.json**: Add a schema-level assertion that backend_visible_fields is exactly ['unit_id','search_text'] and that no other fields are serialized to the backend, enforced by a test that inspects the serialized output. Test: Serialize a unit and assert the output contains only unit_id and search_text.
- **minor — source-unit-contract-v0.schema.json**: Clarify that search_text must be the exact bytes before tokenization and add a pattern to forbid control characters except newline/tab. Test: Submit a unit with a null byte in search_text and assert validation fails.
- **minor — query-log-contract-v0.schema.json**: Require that query_cutoff_commit and git_object_format are consistent with the repository's actual object format, verified by a test that checks the commit's length. Test: Provide a sha1 commit with git_object_format 'sha256' and assert validation fails.
- **minor — policy_digest**: Add a rule that no test query log or label path may appear in any source unit's path or locator, and enforce via a test that scans all units. Test: Create a unit with path containing 'test_query_log' and assert validation fails.

## Authority boundary

The review supplies candidates for deterministic disposition only and cannot authorize a builder or backend run.
