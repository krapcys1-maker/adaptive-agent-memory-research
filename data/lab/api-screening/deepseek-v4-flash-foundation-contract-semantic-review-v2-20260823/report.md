# DeepSeek semantic challenge of Foundation contracts

Status: finalized author-operated cross-family challenge; not independent review

Overall verdict: `needs_revision`.

## Findings

### A01 — conditional / major

Canonical events reference exact bytes via storage_ref and content_sha256, but the schema does not bind the canonical event to the source object hash or span integrity beyond a single hash. The construction fixture has only two events; no evidence of collision or ambiguity handling. Derived summaries are not present, but the contract does not explicitly forbid treating summaries as canonical in later stages.

Required change: Add explicit integrity binding between canonical event and source object (e.g., include source_object_sha256 in the canonical event hash computation) and document that derived summaries are never canonical.

### A02 — conditional / major

Temporal fields are distinct and support as-of reconstruction, but the validator only rejects reversed validity and transaction before observation. It does not enforce that correction events have valid_from within the original validity interval or that supersession is monotonic. Late corrections could leak future state if not properly bounded.

Required change: Add validator rules for correction/supersession temporal consistency and ensure as-of queries cannot see future corrections.

### A03 — conditional / major

Authorization fields are present, but denied capture is only mentioned in the contract, not enforced in the schema (capture_allowed is const true). Retention and access scopes are defined but no enforcement or audit trail for later exposure is specified. The construction fixture uses synthetic data only, so privacy boundaries are untested.

Required change: Add a governance receipt schema for denied capture and enforce retention/access scope checks in the validator.

### A04 — conditional / major

Provenance and revision fields exist, but the validator does not check for cycles, missing targets, or conflicting concurrent revisions. The construction fixture has a single correction chain, so concurrency is untested. Ambiguous authority is not addressed.

Required change: Add validator rules for cycle detection, target existence, and conflict resolution for concurrent revisions.

### A05 — conditional / major

F0-F5 stages are defined with mandatory checks, but boundaries are not exhaustive: e.g., F2 does not include a check for index corruption, F3 does not include a check for context pack integrity. Overlap exists between F3 and F4 (delivered context vs exact evidence exposed). Missing telemetry is 'unknown', but the contract does not specify how to distinguish capture failure from durable-record failure when F0 passes but F1 fails.

Required change: Refine stage boundaries to be non-overlapping and add missing checks for index corruption and context pack integrity.

### A06 — conditional / major

The four-probe rule is conservative, but it can produce false negatives if all probes fail due to a common cause (e.g., encryption key loss) or if a stale cache returns raw bytes without content hash match. The construction fixture only shows a passing case; no invalid mutations for physical loss are provided in this packet.

Required change: Add invalid mutations for correlated probe failures and encryption key loss, and require that raw-byte recovery includes a content hash match to rule out stale caches.

### A07 — conditional / major

Receipts have hashes and chaining, but the schema allows null sha256 for many refs, and the construction fixture uses null for index, retrieval, context, reader, action, and evaluation refs. This prevents independent replay and tamper detection for those artifacts. Unknown-state handling is defined but not exercised.

Required change: Require non-null sha256 for all input/output refs except when the artifact is intentionally ephemeral, and add a receipt for unknown-state handling.

### A08 — conditional / major

The prefix commit and access receipt are same-author attestations. They prove that the registered write-side process did not read reveal/gold artifacts, but they do not prevent prior author knowledge, unlogged reads, or leakage through filenames, timestamps, or tool metadata. The receipt lists observed read paths but does not include a process isolation mechanism.

Required change: Add a process isolation mechanism (e.g., container with no network and no access to reveal/gold) and include a system-level audit log that cannot be modified by the author.

### A09 — conditional / major

The counterfactual set has three tasks with different required evidence sets and answer states, but they are all closely related to the same provider change. The tasks are not sufficiently incompatible to challenge write-side anticipation; a write-side could have anticipated the general topic and prepared multiple answers.

Required change: Add at least one counterfactual task that is semantically unrelated to the prefix content (e.g., a task about a different project or domain) to strengthen the fork.

### A10 — conditional / major

Reveal and gold are separated, but the answer-state catalog is stored in the same directory as gold and is not reader-visible. However, the catalog contains answer atoms that could be inferred from the reveal queries. The reader-visible fields are limited to reveal_id, query, language, but the query itself may leak the answer (e.g., 'Which provider is current' implies a provider change).

Required change: Ensure reveal queries do not contain answer atoms or temporal hints that could reveal the gold answer. Store answer-state catalog in a separate location with stricter access controls.

### A11 — fail / blocking

The same author designed the contract, fixture, mutations, validator, and repair. Git-separated freezes do not provide independence. The contracts explicitly state that L5 independent review and a separately authored unseen history are required, but this packet does not include any such independent artifact. Therefore, conclusions about semantic independence and external validity are blocked.

Required change: Obtain a second author to independently create the fixture, mutations, and validator, and conduct a blinded review before any promotion.

### A12 — conditional / major

The contract specifies a second-author fixture and L5 review, but the smallest unseen attack set is not fully specified. It should include semantic attacks on time, revision, privacy, and physical-loss rules, as well as leakage attacks through metadata and process isolation.

Required change: Define a concrete unseen second-author fixture with at least 10 valid and 10 invalid traces covering all registered invalid classes and additional semantic attacks, and require a blinded review before promotion.

## Authority boundary

This model review can propose repairs or deny advancement. It cannot satisfy a human/different-team review, create an unseen second-author fixture, authorize PMLAB-FOUNDATION-001, or select architecture.
