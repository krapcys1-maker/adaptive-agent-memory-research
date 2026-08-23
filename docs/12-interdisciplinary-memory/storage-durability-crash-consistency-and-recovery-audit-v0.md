# Storage durability, crash consistency, and recovery audit v0

Status: targeted primary-source and repository pass; deployment profile not frozen

Last reviewed: 2026-08-23

## Question

When may a disk-backed LLM memory claim that an accepted record is durable, intact, recoverable, or physically lost?

The answer is not `the write call returned`, `fsync returned`, `the checksum matches`, or `there are two paths`. Those observations cover different layers and can share a common failure domain. Durability requires a stated fault model, a write receipt, end-to-end integrity checks, independently inventoried copies, and demonstrated restore.

## Primary evidence

| Source | Contribution used here | Boundary |
| --- | --- | --- |
| [Pillai et al. 2014](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai) | application update protocols depend on subtle persistence properties that differ across file systems; Alice/Bob expose crash vulnerabilities and properties | six Linux file systems and selected applications; does not certify this Windows machine or our code |
| [Prabhakaran et al. 2005, IRON file systems](https://research.cs.wisc.edu/adsl/Publications/iron-sosp05.pdf) | partial disk errors and block corruption require explicit detection and recovery rather than a fail-stop assumption | older commodity file systems and magnetic-disk context; failure taxonomy remains relevant |
| [Bairavasundaram et al. 2008](https://www.usenix.org/conference/fast-08/analysis-data-corruption-storage-stack) | production study of 1.53 million drives found silent checksum mismatches and non-independent corruption within and across disks in one system | vendor/storage-stack population does not provide a rate for a personal SSD |
| [Saltzer, Reed, and Clark 1984](https://doi.org/10.1145/357401.357402) | end-to-end correctness requires the application endpoint to verify the completed transfer; lower-layer checks can reduce retries but not remove the endpoint obligation | design argument, not a backup product benchmark |
| [SQLite atomic commit and crash testing](https://sqlite.org/atomiccommit.html) | rollback/WAL protocols, sync ordering, and fault simulation provide atomic commit under stated VFS/device assumptions | SQLite explicitly depends on OS/filesystem/device behavior and does not add redundancy for arbitrary corruption |
| [SQLite corruption and backup guidance](https://www.sqlite.org/howtocorrupt.html) | unsafe live-file copies, missing hot journals, broken sync, controller behavior, and application bugs can corrupt a database; safe backup APIs exist | structural integrity does not prove application-level content completeness |

## Six properties that must remain separate

1. **Accepted:** the application validated and assigned an immutable operation ID.
2. **Atomically committed:** after a crash, either the whole transaction or none is visible.
3. **Durable under the declared fault model:** the committed transaction survives the stated process/OS/power/device failure.
4. **Integrity-verifiable:** later bytes can be compared with independently retained identity/checksum metadata.
5. **Recoverable:** an intact authorized copy or reconstruction path exists and has been restored successfully.
6. **Available to the memory pipeline:** schema, index, authorization, retrieval, and reader layers can use the recovered bytes.

An atomic but non-durable write may vanish cleanly. A durable corrupt copy may be present but wrong. A checksum can detect a mismatch but cannot reconstruct bytes. A valid backup can be unusable because the key or restore procedure is missing. A restored database can pass structural integrity while silently missing the latest accepted logical records.

## Candidate write-receipt ladder

| Tier | Evidence | Permitted claim |
| --- | --- | --- |
| W0 | application created operation ID | accepted in process only |
| W1 | language/runtime buffer flushed | submitted to OS path; not durable |
| W2 | atomic replace or database transaction returned | logical commit under runtime assumptions |
| W3 | file/data and required directory/journal sync returned | durability request completed under VFS/device assumptions |
| W4 | fresh-process restart re-read exact bytes and receipt | survived one observed restart; not general reliability |
| W5 | independently inventoried alternate-device/backend copy verified end-to-end | recoverable from the tested primary-domain loss |
| W6 | scheduled restore drill reconstructs canonical bytes, schema, indexes, and accepted-ID completeness | demonstrated recovery for that snapshot/fault profile |

No tier proves factual truth. W3 is not W5, and W5 is not W6.

## Atomic-write code audit

The pinned [`jagoff/memo`](https://github.com/jagoff/memo) helper at `645648a01ac370650579c2e91cbf7f6c03f97115` writes a temporary file, flushes and `fsync`s it, changes mode, and calls `os.replace`. This is a useful fault-test seed, not a portable durability primitive:

- it does not sync the parent directory after replacement;
- its locking path uses `fcntl`, which is not a Windows implementation;
- correctness still depends on filesystem and device persistence properties;
- it provides no alternate replica, scrubbing, backup, or restore receipt.

The project may borrow its temporary-file and replace shape only after platform-specific crash tests. It must not copy the word `durable` as evidence.

## SQLite boundary

SQLite is a strong default for a derived local index and perhaps later structured canonical views because it has explicit transactions and extensive crash tests. The current project still treats text/JSON as canonical and SQLite FTS5 as rebuildable, which reduces recovery coupling.

Important limits from SQLite's own documentation:

- rollback mode and WAL use different recovery mechanisms;
- a live database file must not be copied naively; use the backup API, `VACUUM INTO`, or another documented consistent method;
- database, WAL, and journal files form one recovery unit in relevant states;
- `fsync`/`FlushFileBuffers` and device-controller claims can be weaker than advertised;
- arbitrary application, filesystem, controller, or media corruption remains possible;
- `PRAGMA integrity_check` validates database structure, not the presence of every accepted memory operation.

Therefore a restore drill must join restored records against an external accepted-operation receipt manifest, not stop at `integrity_check=ok`.

## Checksums detect; redundancy and restore recover

An end-to-end checksum should cover canonical bytes in a deterministic framing and be checked after transfer/readback. The checksum record must itself be protected and versioned. A same-file checksum or hash stored only on the failed device is not an independent witness.

Periodic scrubbing is needed to discover latent corruption before all copies age past recovery. Because production corruption events can be spatially and temporally correlated, two disks in the same enclosure, controller, power supply, machine, or synchronized buggy writer cannot automatically be counted as independent.

Cryptographic identity also has limits:

- matching hashes make accidental unequal bytes extremely unlikely under the selected algorithm;
- hashes do not show that content is complete, true, authorized, or latest;
- an attacker able to replace both data and an unanchored manifest can defeat a local comparison;
- encryption protects confidentiality, not availability; lost keys destroy recoverability.

## Backup is a tested recovery path, not a copy count

A backup claim must declare:

- canonical objects and journals/WAL included;
- snapshot/transaction boundary;
- destination device, host, account, region, power, and administrative failure domains;
- encryption algorithm, key location, recovery authority, and key-loss procedure;
- retention, immutability/object-lock policy, deletion propagation, and privacy scope;
- recovery point objective (RPO) and recovery time objective (RTO);
- last successful end-to-end verification and last isolated restore drill;
- accepted operation IDs included and missing;
- software/configuration needed to rebuild derived indexes and serve retrieval.

An untested backup is only a candidate copy. A restore that overwrites the sole remaining source during testing is an unsafe drill.

## Repository candidates

### Litestream: directly relevant SQLite disaster-recovery comparator

[`benbjohnson/litestream`](https://github.com/benbjohnson/litestream) was cloned into ignored research cache at `63225f17ccbb8dedfb26d03f7d3d07e74c6cf69f` (Apache-2.0). It incrementally replicates SQLite changes and supports point-in-time restore plus optional `quick` or `full` SQLite integrity checks.

Useful segments:

- WAL monitoring and transaction-position receipts;
- file/S3/SFTP and other replica-client boundaries;
- point-in-time restore workflow;
- post-restore `PRAGMA quick_check`/`integrity_check` hooks;
- soak scenarios that repeatedly replicate, restore, and verify.

Critical boundary at the pinned revision: age encryption is explicitly rejected because it was removed during the LTX refactor and could otherwise have written plaintext. S3 server-side encryption options exist, but local file or other replicas require a separate confidentiality profile. Litestream must therefore remain a recovery comparator, not a privacy solution or canonical store.

### Restic: general encrypted snapshot/restore comparator

[`restic/restic`](https://github.com/restic/restic) is metadata-pinned at remote revision `a80be1478a4c537f8396e0db2b05120aa78f11e0` (BSD-2-Clause). It offers encrypted, deduplicated snapshots, repository checking, data verification, and restore. It is broader than SQLite and useful for canonical text/JSON plus manifests.

Restic is not downloaded because destination, key custody, retention, and restore drill requirements are not frozen. Its password/key loss can make data irrecoverable; its repository check does not replace application-level accepted-ID completeness.

## Required next benchmark

Upgrade `PMLAB-FORG-F1R-001` with two new independently reviewed probes:

- **P10 alternate-domain recovery:** disable the primary device/runtime and recover exact accepted bytes through a separately inventoried implementation and checksum path;
- **P11 isolated restore drill:** restore into a disposable isolated target, verify byte hashes, parse schemas, rebuild indexes, join all accepted IDs, run current/historical retrieval probes, and emit an RPO/RTO receipt.

Required injections include process kill before/after sync, torn/truncated/out-of-order writes, missing or mismatched journal/WAL, silent byte corruption, manifest corruption, stale backup, omitted latest accepted event, lost key, poisoned backup, primary and replica common-mode loss, and successful structural restore with logical-record omission.

## Current conclusion

The minimal durable-memory direction remains portable canonical text/JSON, deterministic receipts, atomic database/index transactions, rebuildable views, end-to-end checksums, and an external recovery path. SQLite, Litestream, and Restic cover useful parts of this stack; none alone proves durability or recoverability. The next evidence should be a real alternate-domain restore drill, not another same-disk repetition or a larger retrieval model.

## Open work

- independent storage/security review of W0-W6, P10, and P11;
- inventory an actually separate device or backend without exposing private data;
- freeze Windows-specific atomic replacement and directory durability tests;
- select consistent SQLite backup mode and WAL/journal handling;
- define accepted-operation receipt anchoring and manifest recovery;
- freeze key custody before any encrypted backup pilot;
- define deletion propagation separately from backup retention and recovery;
- run restore drills with content completeness, not structural checks alone.
