# Foundation v0.2 second-author challenge contract

Status: recruitment and submission contract; no unseen submission exists

Challenge ID: `PMLAB-FOUNDATION-SECOND-AUTHOR-002`

## Purpose

Remove the main same-author validity defect without pretending that another prompt
to another model is institutional independence. A different person or team creates
unseen traces and semantic verdicts against a frozen interface. The project freezes
their submission commit before inspecting outcomes or adapting any validator.

This challenge may falsify or revise the v0.1 contracts. It cannot authorize the
parent compaction benchmark by itself.

## Role separation

Preferred roles are:

1. **contract custodian:** project team; freezes v0.2 interface and does not author
   subject traces;
2. **fixture author:** external person/team; creates unseen valid and invalid traces;
3. **operator:** runs the frozen checks in a clean environment and preserves logs;
4. **semantic reviewer:** judges whether expected failure reasons and task/gold
   boundaries are defensible without seeing project results.

One external person may hold roles 2 and 3 if disclosed. They may not count as both
fixture author and independent semantic reviewer. An author-operated API model may
assist but cannot occupy role 4.

## Blind boundary

The external contributor receives this contract, the public v0.1 schemas, and blank
submission templates. They should not use:

- construction results or completion receipts;
- v0.1 invalid-mutation files;
- prior DeepSeek response or author disposition;
- `memory/CURRENT_STATE.md` or project-memory findings about expected defects;
- validator implementation details beyond the frozen public interface.

Prior public exposure must be disclosed; it does not automatically disqualify a
reviewer but changes the independence claim.

## Required semantic coverage

Coverage is dimension-based, not an arbitrary case quota. Every dimension needs at
least one valid trace and one targeted invalid/ambiguous attack where logically
possible.

### Canonical and governance

- exact payload/source/span integrity and record-envelope tampering;
- original, late correction, supersession, and historical as-of reconstruction;
- concurrent conflicting revisions and conflicting authority;
- missing/unknown occurrence or validity time without invented precision;
- authorized capture, payload-free denied capture, restricted retention, and later
  unauthorized exposure;
- causal-parent and revision target errors;
- duplicated idempotency key and replayed append;
- schema-valid but semantically inconsistent provenance.

### Receipts and failure localization

- F0-F5 success, failure, unknown, and skipped states;
- non-null artifact hash or typed `ephemeral_unavailable` reason;
- index corruption, retrieval-set corruption, context-pack corruption, reader miss,
  action denial, duplicate action, and evaluator error;
- correlated probe failure, stale cache, partial corruption, replica disagreement,
  encryption-key loss, alternate-domain recovery, and genuine byte destruction;
- physical-byte loss separated from effective unavailability and invalid record.

### Delayed reveal and information flow

- one heterogeneous prefix with neutral events from at least three domains;
- multiple later answerable tasks that require different evidence subsets,
  temporal scopes, and consequence profiles;
- at least one task whose future importance cannot be inferred from frequency,
  surprise, topic, filename, or recency alone;
- answer-atom, gold-ID, consequence, task-family, filename, timestamp, and metadata
  leakage attacks;
- OS/container read allowlist, network state, observed file-access log, and operator
  identity;
- reader-visible reveal separated from gold and scorer;
- identical-prefix comparison plus a matched prefix whose apparent anomaly is noise.

## Submission order

1. Contributor registers a stable identity/pseudonym, conflicts, roles, and tool/model
   assistance before authoring.
2. Contributor creates traces, labels, README, environment receipt, and manifest in
   their own branch/repository.
3. Contributor publishes one immutable Git commit and SHA-256 artifact manifest.
4. Project records that commit without reading hidden semantic labels.
5. Only after the submission freeze may the project run the already frozen generic
   validator or write a new validator version. Any validator change after seeing a
   failure is a new exploratory instrument and cannot retroactively pass the frozen
   submission.
6. Raw logs freeze before scoring/disposition.

## Required submission artifacts

- `submission-manifest.json` from the template;
- `canonical-events.jsonl` and payload objects or a documented equivalent;
- `governance-receipts.jsonl` including denied-capture cases without payload;
- `stage-receipts.jsonl`;
- `prefixes.jsonl`, reader-visible `reveals.jsonl`, and access logs;
- restricted or sealed `gold.jsonl` with a public cryptographic commitment;
- `case-inventory.json` mapping opaque IDs to coverage dimensions, not answers;
- environment/tool/model receipt;
- reviewer form and attestation from a role not authoring the fixture;
- README with reproduction command and every known limitation.

Private or embargoed gold may stay outside Git if a keyed commitment, custodian,
release condition, and later verification method are declared. Unkeyed hashes of
low-entropy private answers are not sufficient.

## Acceptance of a submission

A submission is **eligible for challenge execution** only if:

- its commit and artifact hashes verify;
- roles and prior exposure are disclosed;
- every required dimension is covered or explicitly marked impossible with reason;
- no real personal, secret, licensed-restricted, or unsafe payload is included;
- parent execution remains denied;
- the project did not alter the subject fixture after freeze.

Eligibility is not a pass. A critical privacy leak, false physical-loss claim,
future-answer leak, unsupported action, hidden label exposure, or unverifiable
fixture mutation rejects promotion regardless of average accuracy.

## Output claims

Allowed after a valid run:

- which contract invariants survived or failed this unseen submission;
- exact failure reasons, uncertainty, and repair candidates;
- whether the contract is ready for another unseen replication.

Forbidden:

- human-like memory;
- universal durability or privacy;
- architecture superiority;
- parent benchmark authorization from one external fixture;
- independence when the same author/model supplied both fixture and verdict.

