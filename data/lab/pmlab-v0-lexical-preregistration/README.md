# PMLAB v0 lexical baseline preregistration

Status: protocol frozen; execution locked

This directory freezes the comparison contract before independent gold exists and before any backend sees the 120-query corpus. It does not contain results.

The primary comparison is SQLite FTS5/BM25 (`B2`) versus the tokenized ripgrep scan (`B1`). No-memory (`B0`) is an incremental-memory control and reviewed evidence (`O`) is a scorer ceiling. The protocol can reject FTS5 and retain ripgrep; adding an index is not assumed to be progress.

Pure retrieval does not decide whether an answer is supported. The ten unanswerable cases therefore report empty-candidate behavior and candidate count, not “abstention accuracy.” A later completeness controller and fixed reader must earn that claim separately.

`execution_authorized` remains false until two independent forms are receipt-frozen, disagreements are adjudicated, gold is hashed, and the source/provenance/template audit is accepted. Changing a metric, threshold, query rule, indexed field, or safety guardrail after labels or backend output creates a new protocol version.
