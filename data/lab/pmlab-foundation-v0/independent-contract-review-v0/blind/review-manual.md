# Blind semantic review manual: Foundation contracts v0

Review only the artifact list in `packet-manifest.json`, the twelve questions, and
the blank form. Do not inspect any construction result, audit report, completion
receipt, project-memory summary, API review, invalid-mutation file, or architecture
preference.

Your job is falsification, not approval. Treat absent controls as absent. Separate:

- structural validity from semantic sufficiency;
- recoverable bytes from valid durable records and physical loss;
- transaction order from valid time and causality;
- a same-author access attestation from independently observed process isolation;
- multiple queries over one prefix from evidence that an author could not anticipate
  their semantic family;
- a construction fixture from an unseen second-author replication.

For each A01-A12 question return one verdict, severity, exact artifact locators,
rationale, and a concrete required change or null. A `pass` requires direct evidence
in the packet. Use `not_assessable` when the packet cannot decide the question.

This review may recommend whether each contract is ready for an unseen second-author
fixture. It may never authorize the parent compaction/memory benchmark or a product
architecture.

