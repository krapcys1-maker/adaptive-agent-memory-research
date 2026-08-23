# Disposition of the compact natural-history contract M1 review

Status: author disposition complete; accepted repairs applied to design v0.2; independent review and builder lock remain

The compact DeepSeek M1 review returned `needs_revision` with confidence 0.90. It is an author-operated advisory, not independent review. Every item below is judged against the actual schema, policy, and JSON Schema capabilities.

## Accepted or partially accepted

- **Canonical unit ID** — accepted as a deterministic-validator requirement. JSON Schema cannot recompute SHA-256 from sibling fields, so the requested schema-only repair is impossible. The future builder validator must recompute and reject mismatches.
- **Private receipt strength** — accepted in part. Mode-specific receipt shapes now require a 128-bit-form random ID or HMAC-SHA-256 digest plus generation metadata. A validator/generator must enforce CSPRNG/HMAC use because a regex cannot prove entropy or origin.
- **Duplicate aliases** — accepted. `source_aliases` now uses `uniqueItems`, and the deterministic validator must also enforce canonical-source selection.
- **Byte ceiling receipt** — accepted in the experiment manifest, not repeated in every unit. It remains null and execution-locked until the label-free feasibility audit freezes one value.
- **Backend projection** — accepted as a serializer/audit invariant. The schema already fixes `backend_visible_fields` to exactly `unit_id,search_text`; only an execution test can prove that hidden fields were not serialized.
- **Unsafe control characters** — accepted. Search text permits tab and LF but rejects other C0 controls and DEL.
- **Test/query/label exclusion** — already registered, retained, and promoted to an explicit deterministic-validator requirement.
- **Capture ordering** — accepted as a monotonic `capture_sequence`; it supports ordering audit but still cannot independently prove blindness.

## Rejected as contradicted or technically impossible

- The claim that SHA-1/SHA-256 consistency was unenforced is contradicted. Both algorithm fields are required, conditional patterns restrict the corresponding ID lengths, and a test already rejects mismatches.
- JSON Schema cannot reject a random-looking value because it was secretly derived from query text. Shape validation is now stronger, while generation provenance remains a procedural and executable control.
- JSON Schema cannot prove which fields a retrieval adapter transmits. That requires a projection function and byte-level test.
- A public user question is not necessarily private, and a private origin is not inferable from `origin_type` alone. `storage_class` remains an explicit reviewed classification rather than a guessed schema implication.
- Alias locators may refer to heterogeneous exact-duplicate source types, so they are intentionally strings rather than forced into the canonical unit's locator kind.

## Consequence

The repairs improve the review candidate but do not unlock corpus construction. Independent design review, a label-free byte/token feasibility audit, and adversarial historical reconstruction fixtures remain required.
