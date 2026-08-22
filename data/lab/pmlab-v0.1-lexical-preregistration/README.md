# PMLAB v0.1 lexical baseline preregistration

Status: unchanged lexical-v0 protocol migrated to repaired v0.1 query hashes; execution locked

This directory freezes the comparison contract before independent gold exists and before any backend sees the 120-query corpus. It does not contain results.

The primary comparison is SQLite FTS5/BM25 (`B2`) versus the tokenized ripgrep scan (`B1`). No-memory (`B0`) is an incremental-memory control and reviewed evidence (`O`) is a scorer ceiling. The protocol can reject FTS5 and retain ripgrep; adding an index is not assumed to be progress.

Pure retrieval does not decide whether an answer is supported. The ten unanswerable cases therefore report empty-candidate behavior and candidate count, not “abstention accuracy.” A later completeness controller and fixed reader must earn that claim separately.

`execution_authorized` remains false until two independent forms are receipt-frozen, disagreements are adjudicated, gold is hashed, and the source/provenance/template audit is accepted. Changing a metric, threshold, query rule, indexed field, or safety guardrail after labels or backend output creates a new protocol version.

The label-free split audit rejected the original v0 query split before labels or backend execution. V0.1 changed all 60 test query forms while preserving the evidence corpus byte for byte and all non-query authored relations. Its automated descriptive audit flagged 0 of 300 cross-split pairs, but independent leakage review is still required.

This migration changes no backend, metric, threshold, bootstrap, safety guardrail, or decision rule from protocol commit `e111a57`. It binds that contract to candidate commit `cc904dd` and blind-query SHA-256 `6dca3fcea6e7b7830231444d6e8050952843bbe8974f78633889e6ac76c056bf`.
