# Reuse-Before-Inventing Audit v0

Status: static audit complete; runtime reproduction partial  
Audit date: 2026-08-23  
Decision scope: research architecture and benchmark candidates, not production approval

## Executive decision

Do not adopt another memory product wholesale. Reuse narrow, testable boundaries from several projects behind our own evidence-first contract:

1. **GoodMemory** for typed evidence, bi-temporal records, storage ports, retrieval traces, write ownership, and evaluation gates.
2. **mnemos** for cited file retrieval, path confinement, deterministic chunking, and a simple reciprocal-rank-fusion baseline.
3. **mcp-local-memory** for the distinction between recall exposure and explicit feedback, plus a small SQLite/FTS5 comparison implementation.
4. **memo** for authoritative Markdown with a rebuildable index, atomic-write ideas, and context packs that separate current, supporting, and stale/conflicting evidence.
5. Official or established libraries for protocol, embeddings, encryption, PII detection, secret scanning, and time scheduling.

This is a composite reference architecture, not an invitation to merge four codebases. Every borrowed implementation must retain its license notice, be pinned to a revision, and pass an isolated characterization test before it enters the core.

## Audit method

- cloned the four candidate repositories at exact revisions;
- inspected implementation files, tests, manifests, and root license text;
- counted repository and test-like files only as a maturity signal, never as proof of correctness;
- attempted a clean dependency installation where the local runtime made that meaningful;
- separated `adopt_dependency`, `adapt_with_attribution`, `comparator_only`, `reference_only`, and `reject_for_now` decisions;
- recorded both useful boundaries and traps in `reuse-component-adoption-register-v0.csv`.

## Candidate findings

### GoodMemory — contract donor, not wholesale dependency

- Repository: `hjqcan/GoodMemory`
- Revision: `08ebbb50097dc9cf03810391f37a2d8e22f20ca2`
- License: MIT
- Static size signal: 3,762 tracked paths and 858 test-pattern paths.
- Local reproduction: Git objects are available, but a full Windows checkout failed because generated fixture/report paths exceed the standard path-length limit.

Useful boundaries:

- `src/domain/records.ts`: separates observation time, validity interval, expiry, and transaction timestamps.
- `src/evidence/contracts.ts`: links source messages, excerpts, source URIs, and derived memory records.
- `src/storage/ports.ts`: narrow storage interfaces keep the domain independent from SQLite, Postgres, and vector stores.
- `src/recall/retrievalTrace.ts`: exposes channel ranks, fusion, reranking, latency, and fallback rather than returning an unexplained result.
- `src/remember/writeOwnership.ts`: makes multi-record writes and rollback ownership explicit.
- evaluation gates: benchmark claims are versioned and fail closed when provenance or execution evidence is incomplete.

Do not copy blindly:

- the whole repository is too large for a minimal, causally attributable baseline;
- provider and host integrations expand the dependency surface;
- constructors that infer maximal confidence from absent input would violate our unknown-by-default evidence policy;
- Windows checkout and runtime support require an explicit compatibility lane.

Decision: **adapt contracts and tests with attribution**; do not make the package the core.

### mnemos — best small reference for cited local retrieval

- Repository: `arhuman/mnemos`
- Revision: `0bdf9de70350ff4659ce7af9ee25536b14fe8b9d`
- License: MIT in the root file; GitHub license metadata did not identify it reliably.
- Static size signal: 363 tracked paths and 115 Go test files.
- Local reproduction: blocked because Go is not installed in the current environment.

Useful boundaries:

- `internal/security/paths.go`: root confinement, traversal rejection, exclusion rules, and symlink escape checks;
- `internal/security/secrets.go`: a swappable, high-precision secret-scanner interface;
- `internal/search/hybrid.go` and `rerank.go`: deterministic reciprocal-rank fusion with lexical fallback and stable ties;
- `internal/chunk/`: Markdown/code/text chunkers with golden tests;
- exact `file#section` and line-range citations, with the file corpus remaining authoritative;
- thin CLI and MCP adapters over the same application operations.

Do not copy blindly:

- the Go implementation should be ported only if our language choice differs;
- optional dense retrieval scans vectors linearly and is not an ANN solution;
- its evaluation queries are largely derived from indexed documents and can overestimate natural-question retrieval;
- its built-in secret rules deliberately trade recall for precision and are not a complete privacy layer.

Decision: **adapt RRF, citation, path-safety, and golden-test patterns with attribution**.

### mcp-local-memory — compact comparator with a valuable feedback distinction

- Repository: `Beledarian/mcp-local-memory`
- Revision: `86450ce477607bdd97f5b63db8f9ccf760429bc7`
- License: MIT; bundled `sqlite-vec` carries MIT/Apache notices.
- Static size signal: 80 tracked paths and 34 test-pattern paths.
- Local reproduction: `npm ci` failed on Windows with Node 24.13.0 because `better-sqlite3@11` had no matching prebuilt binary and native compilation could not proceed without Visual Studio C++ Build Tools.

Useful boundaries:

- `src/db/schema.ts`: separate ledgers for explicit feedback and bounded recall exposure;
- `src/tools/core.ts`: recall does not itself assert that a memory was useful;
- `src/lib/scoring.ts`: a compact hybrid ranking baseline and capped reinforcement model;
- small SQLite/FTS5/MCP surface suitable for characterization tests.

Do not copy blindly:

- its main memory row has insufficient evidence, version, and temporal provenance for our canonical contract;
- embeddings and vector dimensions are tightly coupled to a 384-dimensional default;
- `context_provider.ts` uses substring matching and approximate character truncation, and suppresses some failures;
- decay/importance formulas are hypotheses to benchmark, not truths about memory;
- extension loading needs a stronger trust and integrity policy.

Decision: **use as a comparator and adapt only the exposure-versus-feedback ledger pattern**.

### memo — authoritative-text and context-pack donor

- Repository: `jagoff/memo`
- Revision: `645648a01ac370650579c2e91cbf7f6c03f97115`
- License: MIT
- Static size signal: 1,556 tracked paths and 672 test-pattern paths.
- Local reproduction: intentionally not installed; it requires Python 3.13+, declares macOS/Linux support, and has a large platform-specific ML dependency surface.

Useful boundaries:

- Markdown is authoritative and SQLite is a rebuildable derivative index;
- `src/memo/atomic_io.py`: temporary file, flush/fsync, permissions, and atomic replace pattern;
- `src/memo/context_pack.py`: current, supporting, and stale/conflicting buckets; sensitive-memory omission; deterministic budget trimming with omission reporting;
- time-travel and evidence-oriented test cases.

Do not copy blindly:

- `atomic_io.py` uses `fcntl`, so it is not directly portable to Windows;
- the package is a broad product rather than a minimal experimental kernel;
- platform-specific embedding dependencies would undermine provider and operating-system neutrality.

Decision: **adapt context-pack semantics and cross-platform atomic-write tests, not the package**.

## Established components to adopt instead of rebuilding

| Need | Candidate | Decision | Boundary and caution |
|---|---|---|---|
| Provider-neutral local tool protocol | `modelcontextprotocol/python-sdk` | adopt after version pin | Official MIT SDK; expose memory operations through `stdio` first and keep domain logic protocol-free. SDK v2 is a breaking line, so pin the chosen major. |
| Local embedding runtime | `qdrant/fastembed` | benchmark as optional adapter | Apache-2.0; compare against the existing sentence-transformers lane. Embeddings remain a replaceable retrieval channel, never the source of truth. |
| Vector storage | `asg017/sqlite-vec` | already pinned; optional adapter | Keep exact/small-corpus baselines and vector dimension in index metadata. Rebuild indexes when the model changes. |
| Encryption at rest | `sqlcipher/sqlcipher` | compatibility spike | BSD-3-Clause; useful for full SQLite encryption, but key custody, backups, and binary distribution remain our responsibility. |
| PII detection/redaction | `data-privacy-stack/presidio` | optional privacy worker | MIT; useful but explicitly non-exhaustive. Never treat a clean scan as proof that content is safe. |
| Secret scanning | `gitleaks/gitleaks` CLI/core | adopt for ingestion/commit gates | Core is MIT. Do not assume the separately licensed `gitleaks-action` has the same terms. Rotate a leaked secret even after deleting it from current files. |
| Time-based prospective triggers | `agronholm/apscheduler` 3.x stable | optional scheduler adapter | MIT. Use it only to calculate and persist due work. Event/state predicates and action authorization stay in our domain. The 4.x line is prerelease and must not be silently selected. |

## Explicit non-adoptions

- **LiteLLM as the memory core:** no. A model gateway may help an optional API worker, but provider routing is independent of persistent memory and its current licensing/deployment surface needs a separate audit.
- **A graph database in v0:** no. Graphiti and graph retrieval remain experiment arms; FTS5 plus explicit evidence and temporal links is the minimal causal baseline.
- **Approximate vector search in v0:** no. It adds another source of retrieval error before corpus scale demonstrates a need.
- **Automatic emotional reinforcement:** no. Emotion/appraisal is an experimental signal. Recall exposure is not utility, and affect must not silently raise truth confidence.
- **Automatic destructive forgetting:** no. Start with suppress, supersede, quarantine, and reversible archive; test deletion separately.

## Integration gate for any borrowed segment

A segment may move from the register into implementation only when all conditions hold:

1. exact upstream revision and license are recorded;
2. the copied or ported boundary is smaller than the alternative dependency;
3. characterization tests demonstrate current upstream behavior;
4. our counterexample tests cover provenance loss, stale/conflicting evidence, privacy, rollback, and platform failure;
5. a third-party notice and source link are added if code is copied or materially translated;
6. benchmark results show an improvement over the minimal FTS5 baseline under equal evidence and context budgets;
7. removal or rollback remains possible without losing canonical raw records.

## What this audit changes

The minimal project should begin with canonical append-only observations, typed evidence links, a rebuildable SQLite/FTS5 index, deterministic fusion, inspectable retrieval traces, and a budgeted context pack. Dense retrieval, learned controllers, graph expansion, affective salience, decay, and destructive forgetting stay behind experiment flags until their own benchmark gates pass.
