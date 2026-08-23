# Foundation contract construction fixture v0

This is a synthetic, model-free contract fixture for
`PMLAB-FOUNDATION-CONTRACT-001`. It is not a memory implementation and is not an
execution of the parent compaction benchmark.

The two raw UTF-8 files are the only payload bytes. `canonical-events.jsonl`
references them by exact path, length, and SHA-256. `stage-receipts.jsonl` contains
one complete diagnostic trace. `invalid-mutations.json` registers adversarial
changes that a validator must reject for the stated reason class.

Freeze order:

1. contract prose, schemas, raw bytes, valid records, and invalid mutations;
2. commit the exact fixture;
3. only then build the deterministic validator;
4. preserve validator output and byte hashes in a later execution receipt.

Passing the authored fixture is construction evidence only. Independent semantic
review and unseen fixtures remain required.

