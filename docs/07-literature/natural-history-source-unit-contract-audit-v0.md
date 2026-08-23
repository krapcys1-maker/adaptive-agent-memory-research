# Natural-history source-unit and query-provenance contract audit v0

Status: primary-source design audit plus label-free tokenizer feasibility; contract revision 0.2 awaits a replacement independent-review packet, and no corpus builder or backend run is authorized

## Question

What must freeze before historical project files can become fair, privacy-aware, byte-identical retrieval units across `rg`, FTS5, local dense retrieval, and RRF?

## Primary-source constraints

- Git commits point to complete trees rather than stored diffs. A historical tree can be enumerated without checking it out, and `<revision>:<path>` addresses the exact blob at that revision. Git blobs are content objects independent of their path. These properties support read-only reconstruction from a query cutoff, but only if the builder never falls back to the current working tree. [Git user manual](https://git-scm.com/docs/user-manual), [Git revision syntax](https://git-scm.com/docs/revisions), [Git data model](https://git-scm.com/docs/gitdatamodel.html)
- Git object names may be SHA-1 or SHA-256. They hash typed Git objects and are not the same value as a plain file checksum, so the contract must record the algorithm and retain a portable SHA-256 over the exact blob bytes separately. [Git hash-function transition](https://git-scm.com/docs/hash-function-transition.html)
- CommonMark 0.31.2 distinguishes block structure from inline parsing and defines both ATX and Setext headings. Regexes that recognize only lines beginning with `#` can split headings inside fenced code or miss Setext headings. [CommonMark 0.31.2](https://spec.commonmark.org/0.31.2/)
- CSV headers define field names and CSV fields may contain commas, quotes, and line breaks. Splitting rows or columns with raw string operations is not an admissible canonicalizer. [RFC 4180](https://www.rfc-editor.org/rfc/rfc4180.html)
- Hashing parsed JSON is reproducible only after a byte-level canonicalization contract. JCS defines deterministic property order and UTF-8 output on the I-JSON subset; I-JSON rejects duplicate member names. [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), [RFC 7493](https://www.rfc-editor.org/rfc/rfc7493.html)
- A transformed identifier does not become anonymous merely because the direct locator is removed. Pseudonymised data that can be attributed using additional information remains personal data. This reinforces the project's existing decision not to publish unkeyed hashes of private content or locators. [EDPB Guidelines 01/2025](https://www.edpb.europa.eu/public-consultations/guidelines-012025-on-pseudonymisation_en)

## Accepted contract repairs

### Historical reconstruction

For each query cutoff, enumerate `git ls-tree -r --full-tree <commit>` and read eligible bytes only through the addressed Git object. Do not checkout, stash, or read a same-named working-tree file. Record:

- cutoff commit plus declared Git object format;
- typed Git blob object name plus algorithm;
- portable SHA-256 of the exact file bytes;
- exact source path and unit locator;
- UTF-8 decoding outcome and a counted exclusion reason.

Symlinks, gitlinks/submodules, binary blobs, and non-UTF-8 text fail closed in v0. They may become separately registered source classes later; following them would silently admit current or external state into a historical snapshot.

### Stable unit identity

The snapshot commit is provenance, not part of the unit identity. `unit_id` is derived from a versioned canonical tuple of source type, historical path, logical locator, and `search_text_sha256`. Therefore:

- unchanged content at the same locator keeps one opaque ID across snapshots;
- an edit produces a new ID while the earlier version remains addressable;
- a rename produces a new path-bound ID and may be linked later by an explicit provenance edge;
- exact duplicate collapse selects one deterministic canonical source and preserves the other locators as aliases.

Including the snapshot commit in the ID was rejected because it would turn every unchanged unit into a different retrieval identity at every query cutoff and make longitudinal gold unnecessarily unstable.

### Markdown section semantics

Use a CommonMark-aware block parser for ATX and Setext headings. Each unit contains the normalized heading-path text followed by the direct body up to the first child heading; child bodies are separate units. Historical CRLF/CR becomes LF, only outer blank lines are stripped, and internal Unicode/whitespace is preserved without NFC rewriting. The heading path is part of `search_text` because generic headings such as “Result” or “Limitations” otherwise lose their subject. The filesystem path remains hidden from primary backends. Non-empty preamble becomes an explicit preamble unit.

Project-memory search text uses a fixed semantic allowlist in this order: title, summary, non-empty body, and tags. IDs, operation/kind, confidence/status, timestamps, provenance references, supersession, and relations stay hidden in the primary representation. Their historical records remain available to gold/provenance logic, so hiding them from B1/B2/C1 is not deletion.

Line locators preserve the historical source range. Oversized direct bodies split at parsed CommonMark block boundaries after a development-only UTF-8 ceiling freezes. A block larger than the ceiling uses the latest fitting Unicode whitespace boundary and then, only if no whitespace exists, a valid UTF-8 code-point boundary. Parts have zero overlap, repeat heading context, and carry hidden split method/order metadata. Reconstruction must recover every direct-body byte exactly once after repeated context is removed. A code fence, list item, block quote, or HTML block must not be misread as a heading boundary.

### Structured rows

- CSV is parsed according to the historical header. Search text consists of header-value pairs in original column order. Missing, duplicate, or width-mismatched headers fail closed.
- JSONL admits one I-JSON object per line. Search text is the RFC 8785 JCS UTF-8 serialization. Duplicate names, non-I-JSON numbers, arrays or primitives where an object is required, and parser repairs fail closed.
- Canonicalization changes representation, not evidence. Exact historical row bytes and locators remain available for audit and citations.

### Query provenance and privacy

The earlier `origin_ref_hash` field is rejected. A short private path, username, task identifier, or repeated phrase may be recoverable by enumeration, and an unkeyed digest also creates a durable cross-dataset linkage key.

Revision 0.2 instead distinguishes:

- explicit public Git locators;
- independently random private receipts with a mapping outside Git;
- keyed digests whose key and mapping remain outside Git.

Verbatim private query text is `local_restricted` and must not be committed to the public repository. Public benchmark artifacts contain opaque query IDs, allowed aggregate metadata, and integrity receipts only. The pre-output attestation records procedure but is not proof of blindness; capture ordering still needs an auditable hook or immutable user/reviewer submission.

## Rejected shortcuts

- Index the latest checkout for every historical query.
- Derive a unit ID from snapshot commit alone or expose path/category in the ID.
- Parse Markdown headings with an ATX-only regular expression.
- Hide heading text while indexing only direct body.
- Split CSV with commas or hash ordinary JSON serialization without a canonical contract.
- Treat Git object IDs as plain SHA-256 file checksums.
- Publish an unkeyed hash of a private origin locator and call it anonymous.
- Follow symlinks or submodules from a historical tree into current external state.

## Remaining gates

1. Obtain a design review that specifically challenges stable identity, Markdown direct-body semantics, structured-row canonicalization, exclusions, and private query receipts.
2. Freeze a development-only UTF-8 ceiling after a label-free unit-size inventory and tokenizer feasibility audit; do not inspect retrieval outcomes.
3. Implement the read-only historical builder with adversarial fixtures for future leakage, working-tree contamination, duplicate headings, code fences, Setext headings, malformed CSV/JSONL, symlinks, and duplicate content.
4. Produce a source-unit manifest twice in fresh processes and require byte-identical hashes.
5. Build only retrospective development queries with admissible pre-output provenance. Prospective test collection and every dense/backend run remain locked.

This audit repairs the design contract. It is not independent review, corpus evidence, retrieval evidence, or permission to choose a dense model.

## Post-audit M1 disposition

A large frozen DeepSeek M1 packet failed by truncating invalid JSON and produced no verdict. A separately frozen compact packet returned `needs_revision`. Accepted repairs add mode-specific receipt shapes, unique aliases, a manifest-level byte-ceiling receipt, capture sequence, control-character rejection, and explicit executable validators. Schema-only requests to prove cryptographic derivation, entropy, or backend serialization were translated into executable invariants because JSON Schema cannot establish them. Claims that the required SHA algorithm/length pairs were unenforced were rejected as contradicted by the conditional schemas and tests. The full disposition is in `data/lab/api-screening/deepseek-v4-flash-natural-history-contract-review-v2-20260823/advisory-disposition.md`. M1 remains non-independent and the builder stays locked.
