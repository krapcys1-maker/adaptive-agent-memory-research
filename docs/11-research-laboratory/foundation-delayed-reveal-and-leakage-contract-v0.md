# Foundation delayed-reveal and future-query leakage contract v0

Status: prefix-contract freeze candidate; model-free; reveal content not yet authored

Contract ID: `PMLAB-FOUNDATION-REVEAL-001`

Parent experiment: `PMLAB-FOUNDATION-001`

## Question

Can a benchmark demonstrate that write-side memory processing did not receive the
future task, its answer, its required evidence labels, or its consequence weights?

This is an information-flow contract. It does not measure retrieval or reader
quality.

## Three separately frozen layers

1. **Prefix:** the exact canonical event stream available to every write-side arm.
2. **Reveal:** the future query/task made available only after prefix processing is
   frozen.
3. **Gold:** required/forbidden evidence, supported action, and consequence weights,
   never exposed to a write-side component or primary reader.

The prefix is committed before reveal or gold content is authored. Git ancestry and
exact blob comparison are mandatory evidence. A timestamp or author attestation
alone is insufficient.

## Leakage evidence levels

| Level | What is checked | What it can establish |
|---|---|---|
| `L0_BYTE_FIELD` | schemas, exact bytes, forbidden keys/paths, opaque IDs | no registered reveal/gold field was embedded directly |
| `L1_LEXICAL` | query/prefix token and n-gram overlap | descriptive similarity only; neither proof nor disproof of leakage |
| `L2_PROCESS_ACCESS` | frozen allowed-input set, observed read paths, phase order | the registered write-side process did not read reveal/gold artifacts |
| `L3_COUNTERFACTUAL_FORK` | one byte-identical prefix maps to multiple incompatible later tasks | the prefix does not uniquely encode one authored future task |
| `L4_REPRODUCIBLE_BUILD` | clean-process rebuild from prefix-only commit | registered prefix processing is reproducible without later artifacts |
| `L5_INDEPENDENT_SEMANTIC` | blinded reviewer attacks semantic hints and task construction | external semantic challenge; still not metaphysical proof of blindness |

Construction may pass L0-L4. L5 remains a promotion gate.

## Prefix contract

The prefix record contains only:

- an opaque prefix ID;
- the frozen canonical-event contract and source Git commit/path/hash;
- ordered immutable event IDs, accepted count, and exact payload bytes;
- prefix cutoff and freeze time;
- producer name/version;
- an allowlist of write-side input paths;
- registered forbidden input classes;
- an access-receipt path.

It may not contain a query, task description, answer, relevance label, required or
forbidden event set, consequence weight, reader prompt, scorer, reveal schedule, or
semantic importance label. Event IDs and task/reveal IDs must be opaque and must not
encode a category or answer.

## Reveal and gold contracts

Every reveal is created after the prefix-freeze commit and records:

- opaque reveal and counterfactual-set IDs;
- the exact prefix ID/hash it uses;
- authored, available, and query-cutoff times;
- query text, language, task family, and reader-visible fields;
- a separate opaque gold ID.

Gold records are stored separately and contain required/forbidden event IDs,
supported answer/action state, consequence weight, and abstention policy. The
reader receives the reveal but never the gold fields.

At least three reveal rows must use the byte-identical construction prefix. They
must include at least two incompatible supported answer states and at least two
different required-evidence sets. Shared topic or vocabulary is expected and is not
treated as leakage.

## Write-side access receipt

The receipt freezes:

- phase `prefix_only_before_reveal_authorship`;
- exact allowed paths and exact observed read paths;
- forbidden classes: reveal, gold, query, scorer, prompt packet, backend output;
- `reveal_artifacts_present=false` and `gold_artifacts_present=false`;
- no model API use;
- source and prefix hashes.

The later audit fails if any observed path is outside the allowlist, if a forbidden
class appears, or if Git shows reveal/gold content in the prefix-freeze commit.

## Construction order

1. Freeze this contract, schemas, one prefix, and its prefix-only access receipt.
2. Commit them and record that commit as the prefix freeze.
3. Only then author and freeze reveal, gold, schedule, and invalid-mutation fixtures.
4. Commit those exact bytes.
5. Only then build and freeze the deterministic L0-L4 auditor.
6. Execute once, preserve results, and keep the parent benchmark locked.

## Registered invalid classes

The later mutation fixture must at minimum cover:

- query or gold IDs inserted into the prefix;
- a write-side read path pointing to reveal/gold;
- reveal authored before the prefix freeze;
- reveal available at or before the prefix cutoff;
- prefix hash or source hash mismatch;
- non-opaque IDs that encode the answer/category;
- a counterfactual set with fewer than three tasks;
- counterfactual rows using different prefix bytes;
- no incompatible answer states or no different required-evidence sets;
- reader-visible gold fields;
- missing/duplicate reveal or gold joins.

## Non-claims

Passing L0-L4 shows only that the registered artifact and process boundaries resist
the registered mechanical leakage attacks. It does not prove that an author had no
prior idea of future tasks, that semantics are independent, or that a memory system
works. L5 independent review and a separately authored unseen history remain
required.

## Evidence basis

- `foundation-compaction-memory-benchmark-protocol-v0.md`
- `natural-history-retrieval-benchmark-protocol-v0.md`
- `data/lab/pmlab-natural-history-v0/query-log-contract-v0.schema.json`
- `scripts/audit_pmlab_split_leakage.py`
- `data/lab/pmlab-v0.1-split-audit/direct-template-inspection.md`
- `docs/12-interdisciplinary-memory/rate-distortion-information-bottleneck-and-decision-memory-audit-v0.md`

