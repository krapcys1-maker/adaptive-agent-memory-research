# Code architecture audit: memory mechanisms, model clients, harnesses: 13 November 2026

**Status:** technical audit of the code, written for contributors and maintainers. It is not a research result and changes no experiment, threshold, strategy or decision. No model, GPU, Ollama or paid API was used. Base: `main` at `20b3c2c`. The frozen BFCL experience-line code that is not on `main` was read from Git objects with `git show` and never checked out or edited: `experience_xfer_v1.py` (`claude/experience-xfer-v1`, `b7823a7`), `aamr_night1.py` (`claude/aamr-night1-2026-11-12`, `2ed2556`), `aamr_night2.py` and `reasoningbank_prompts.py` (`claude/aamr-night2-2026-11-13`, `9bfacbe`, while that run was executing). `experience_xfer_v1.py` and `aamr_night1.py` are byte-identical on all branches that carry them.

Small fixes that this audit allowed, and the versioned replacement of the spend ledger (finding 7), are on a separate branch and pull request, `claude/arch-fixes-2026-11-13` (section 8).

**Update after merging `main` at `3a0c5e9`** (pieces S1 to S3 of PR #105 integrated): 79 files under `scripts/` and 7 under `tools/` are now frozen (`python scripts/pinned_files.py --under scripts`, `--under tools`); the other counts in this report are of `20b3c2c`. The owner has since decided two of the questions this audit raised: the next kernel version is a new versioned module, not an edit of 0.2.0 (section 7, item 13), and the loops and model clients are not refactored yet; the contract and the order of migration are recorded in section 6.5.

## 1. Findings in brief

1. **Shared infrastructure is frozen by file digest, so changing it means copying it.** 61 of the Python files under `scripts/` are pinned by at least one live experiment manifest under the claim audit's rules, among them every model client on `main` (`llm_backends.py`, `nie_reader_pilot.py`, `flash_reader_client_v1.py`), both paid-call proxies and the spend ledger, `scripts/wmb/__init__.py`, and the kernel 0.2.0 that the kernel README and `CONTRIBUTING.md` call the *live line*. A committed one-line comment in that kernel produced 9 critical `declared-hash` findings in a throwaway worktree (section 4, D1). This, not carelessness, is why the BFCL line grew by copy-and-extend.
2. **The BFCL agent loop exists three times.** The step body (parse, validate, execute, collect results) of `experience_pilot_v0.run_episode` is copied into `experience_xfer_v1.run_episode_x` and again into `aamr_night1.run_fork`. NIGHT-1 and NIGHT-2 call `run_episode_x`.
3. **Model access has three interface shapes and seven implementations**, plus 17 scripts on `main` that build their own `/chat/completions` request with `urllib`, 25 that call the OpenAI SDK (whose version is declared nowhere in the repository), and 23 that load the DeepSeek key themselves. The de facto common contract is small and already shared by four classes: `ask(key, messages, seed, *, output_schema=None) -> {"text", "done_reason", "usage", "wall_seconds", ...}`.
4. **Cross-module mutation of module globals** wires the newest experiments to the older ones: `aamr_night1` replaces `experience_xfer_v1.note_text` at import time, `aamr_night2.redirect_n1()` rewrites six module globals of `aamr_night1`, and `metered_proxy.load_key()` rewrites `arena.provider_proxy.ROOT` without restoring it.
5. **Experiment code reaches outside the checkout by directory position** (`ROOT.parent / "<experiment>-2026-11-12"`, `bfcl_root: "../experience-pilot-2026-11-12/..."`). For anyone else the BFCL tests are skipped: 8 of 19 in the pilot's test file on `main`; on the branches 12 of 23 (S1), 5 of 15 (NIGHT-1) and all 26 (NIGHT-2).
6. **The same field name means two digests.** `request_sha256` in `attempts.jsonl` is `nie_reader_pilot.sha` (compact JSON separators) for the pilot and S1, and `experience_pilot_v0.sha` (default separators) for NIGHT-1 and NIGHT-2. Digests are comparable within an experiment, not across these two groups.
7. **Budget is kept by six ledgers with different semantics.** One defect was reproduced: under a cap scope, `arena.spend_ledger.SpendLedger` drops a torn line instead of counting it conservatively (section 4, D8). No ledger in the repository has a torn line today, so no recorded total is affected. Fixed for new runs by a versioned successor (`scripts/arena/spend_ledger_v2.py` with `scripts/flash_only_proxy_v2.py`); the frozen version 1 is unchanged.
8. **The well-designed contributor interfaces already exist, for question answering**: `arena.adapter.MemoryAdapter` with `validate_adapter`, and LifeSim's `LifeMemory` with bridges both ways. The BFCL line, where current work happens, has no equivalent; there a mechanism is a closure passed through a dict.

## 2. What was read and run

Read in full: `scripts/experience_pilot_v0.py`, `scripts/flash_reader_client_v1.py`, `scripts/llm_backends.py`, `scripts/metered_proxy.py`, `scripts/flash_only_proxy.py`, `scripts/arena/spend_ledger.py`, `tasks.py`, `scripts/wmb/kernel/README.md`. Read in part (the cited functions and the module outline): `scripts/nie_reader_pilot.py` (lines 1–160), `scripts/arena/adapter.py`, `scripts/lifesim/interface.py`, `scripts/wmb/kernel/memory_kernel.py`, `scripts/nie_memory_contract.py`, `scripts/audit_repository_claims.py` (declared-hash check), `.github/workflows/ci.yml`, `tests/test_experience_pilot_v0.py`, `tests/test_wmb_kernel_v2.py`; on the branches `experience_xfer_v1.py` (outline, lines 220–520), `aamr_night1.py` (outline, lines 145–500, 700–925), `aamr_night2.py` (outline, lines 40–62, 100–128, 993–1070) and the skip markers of their tests. Entry documents: `AGENTS.md`, `START_HERE.md`, `memory/CURRENT_STATE.md`, [operating doctrine](operating-doctrine.md), [laboratory map](../11-research-laboratory/lab-map.md), `CONTRIBUTING.md`, [agent integration contract](agent-integration-contract-v0.md), [minimal reuse architecture](../04-systems/minimal-reuse-architecture-v0.md). Not reviewed in detail: the 19 arena `run_*.py` runners and the other scripts that call a hosted model, beyond their HTTP, SDK and key-loading sites, `scripts/wmb/retrieval_bench.py` beyond its argument defaults, and the PR #105 runtime (`codex/structured-memory-runtime-2026-11-04`, 41 script files, not on `main`).

Mechanical scans over `main` (all reproducible with `git grep` or the commands named): 266 Python files, 77,769 lines in `scripts/` and `tools/`; `sys.path.insert` or `append` in 105 of them and in 81 of 167 test files; `importlib.util.spec_from_file_location` in 56 files; own definitions of `sha`, `file_sha`, `read_json`, `read_jsonl`, `write_json`, `append_jsonl` or `now_iso` in 65 files. Frozen-file count from `python scripts/pinned_files.py --under scripts` (fixes branch). Probes: the kernel edit above, and a reproduction of the ledger defect against a temporary file.

## 3. Architecture map

### 3.1 Layers

```text
 continuity memory of the project (not a researched mechanism)
   tools/project_memory/  MemoryStore (append-only events.jsonl, SQLite FTS index), MCP server, CLI
   scripts/verify_memory_integrity.py, scripts/audit_repository_claims.py, tasks.py, CI

 researched memory mechanisms                          harnesses that test them
   scripts/wmb/memory_kernel.py        0.1.0 frozen    AAM writer simulations (writer_memory_sim.py, followup_, replay_)
   scripts/wmb/kernel/memory_kernel.py 0.2.0 pinned    persona battery (persona_battery.py v0, _v1)
   scripts/nie_memory_contract.py, nie_persona_replay  WMB (scripts/wmb/: stats, contract, retrieval_bench)
   scripts/arena/*_adapter.py (mem0, graphiti,         arena (scripts/arena/run_*.py, judge_pilot, fixed_reader)
     hindsight, cupmem, aamr)                          LifeSim (scripts/corpus/lifesim/, scripts/lifesim/)
   scripts/lifesim/systems.py                          reader / hard-memory (reader_model_compare_v1, hard_memory_*)
   BFCL experience pools, lessons, masked exemplars    BFCL experience line (pilot -> S1 -> NIGHT-1 -> NIGHT-2)

 model access
   in-process, shape A  llm_backends.Generate(system, user, seed, opts)
   in-process, shape B  nie_reader_pilot.LocalReader, flash_reader_client_v1.FlashReader,
                        aamr_night1.LocalClient (branch), aamr_night2.ReplayClient (branch)
   in-process, shape C  aamr_night1.Gateway.ask(key, model_id, messages, schema, bucket, seed), aamr_night1.Flash (branch)
   inline urllib        17 scripts on main (review_*_deepseek.py, run_*_deepseek.py, run_pack_reader_benchmark, ...)
   OpenAI SDK, lazy     24 arena scripts and run_goalshift_e0.py, pointed at the local proxy
   local proxy          arena/provider_proxy.py <- metered_proxy.py <- flash_only_proxy.py (cap, ledger, key held)
 budget
   arena/spend_ledger.SpendLedger, flash_reader_client_v1.ReservationLedger, aamr_night1.Flash ledger (branch),
   experience_pilot_v0.ledger(), experience_xfer_v1.ledger() (branch), aamr_night1.Gateway.by_bucket (branch)
```

### 3.2 The BFCL experience line

This is where the current work happens, and the only line that runs a tool-using agent loop.

| Module | Where | Imports | Adds | Its memory interface |
|---|---|---|---|---|
| `experience_pilot_v0` (`p0`) | `main` | `nie_reader_pilot.LocalReader` (inside `make_client`), kernel 0.2.0 by file path (`load_kernel`) | `Bfcl` access to a pinned checkout, `Names`, `run_episode`, `evaluate_episode`, pools, `ledger`, `Stage` | `memory(task_id, turn_index, request) -> (rows, meta)`; the loop renders with `render_block` |
| `experience_xfer_v1` (`xv`) | branch | `p0` | `BfclX(p0.Bfcl)`, lesson compiler, `run_episode_x` (copy of the loop plus three hooks), `XStage` (copy of `Stage`), own `ledger` | `block(task_id, turn_index, request) -> (text, item_ids, meta)`; at-error notes through `tr_lessons={(function, error_key): lesson}` inside the loop, text from the module global `note_text` |
| `aamr_night1` (`n1`) | branch | `p0`, `xv`, `metered_proxy.load_key` (lazy) | `Gateway` (cache, buckets, bounded retry), `Flash`, `BfclN(xv.BfclX)`, `run_fork` (third loop copy), `run_session`, supervisor | arm spec dict `{"bucket", "tr", "block", "tr_by_domain", "block_by_domain"}`; `xv.note_text` replaced at import |
| `aamr_night2` (`n2`) | branch | `p0`, `xv`, `n1`, `reasoningbank_prompts` | `Gateway2(n1.Gateway)`, masking, tournament, `ReplayClient`, `compat()` | providers from `plan_provider`, `rb_provider`, `g_block_provider`; `n1.run_session` reused after `redirect_n1()` |

What the line does well and any successor should keep: every model client takes an injectable transport or factory (`LocalReader(request=)`, `FlashReader(key_loader=, transport=)`, `Gateway(transport=, sleep=)`, `Stage(client_factory=)`), so the tests run the real loop offline; responses are cached by call key and a cache hit with a different request digest is a `ProtocolError` (`n1.Gateway.ask`); logs are append-only with fsync and torn-tail repair (`n1.fsync_append`, `n1.repair_tail`); and `n2.compat()` replays NIGHT-1's stored responses through the frozen loop and checks that every request is byte-identical, with zero model calls. That replay is the instrument that makes the refactoring in section 6 verifiable.

### 3.3 Memory interfaces that exist

| Interface | Signature | Status | Used by |
|---|---|---|---|
| `arena.adapter.MemoryAdapter` (Protocol) | `name`, `query_mutates_state`, `reset()`, `ingest(records) -> Cost`, `query(question, asked_at=None) -> Answer`; `validate_adapter(adapter, fixture)`; `Measure` and `Cost` keep observability and lower bounds | implemented, tested, unpinned (`adapter_v0_1.py` is the pinned contract) | five adapters in `scripts/arena/`, LifeSim |
| `lifesim.interface.LifeMemory` (base class) | `reset(meta)`, `ingest(batch) -> Cost`, `query(question, asked_at, budget) -> LifeAnswer`, `stats()`; the base enforces time order, visibility and budget | implemented, pinned | `lifesim/systems.py`; `wrap_arena_adapter` and `as_arena_adapter` bridge to the arena contract |
| kernel functional API | `build_index`, `retrieve`, `render`, `log_record`, `guard`, `calibrate` | 0.1.0 frozen, 0.2.0 pinned | AAM, WMB, NIE bridge, BFCL pilot (as a lexical index over requests) |
| NIE typed claim | `validate_claim`, `parse_value`, `guard_answer`; `nie_persona_replay.replay` | pinned | NIE pilots, reader comparison |
| BFCL context provider | `p0`: `(task_id, ti, request) -> (rows, meta)`; `xv`: `-> (text, item_ids, meta)` | experiment code, frozen by policy | the four modules above |
| BFCL at-error hook | `tr_lessons` mapping inside `xv.run_episode_x`; `note` argument of `n1.run_fork` | experiment code | S1, NIGHT-1, NIGHT-2 |

The arena and LifeSim contracts serve *memory as an answerer* (ingest records, answer a question). The BFCL providers serve *memory as context* (a block before a user turn, a note after an error). These are two integration points, not two names for one, so this audit does not propose merging them (section 6.4).

## 4. Technical debt, with evidence

**D1. Freeze by file digest makes shared code immutable.** `audit_repository_claims.check_declared_hashes` compares every 64-hex digest declared under a path key in a JSON manifest under `data/` with the working copy and the Git blob; a mismatch is critical unless a `.DRIFT.json` note proves it from Git. Experiments pin every helper they ran, so shared helpers inherit the freeze. Pinned now (number of live manifests): `scripts/wmb/kernel/memory_kernel.py` 9, `llm_backends.py` 8, `writer_memory_sim.py` 7, `metered_proxy.py` 6, `nie_persona_replay.py` 6, `flash_only_proxy.py` 5, `nie_reader_pilot.py` 3, `flash_reader_client_v1.py` 3, `wmb/__init__.py` 3, `arena/provider_proxy.py` 1, `arena/spend_ledger.py` 1, `lifesim/interface.py` 1, and 49 others under `scripts/`. Nothing under `tools/` is pinned. Probe: appending `# probe` to the kernel and committing it in a throwaway worktree gave exactly 9 critical findings (exit 1). Consequences: the kernel README's "live: every later change goes here" and the same sentence in `CONTRIBUTING.md` are not true for 0.2.0 any more; a bug in a shared client can only be fixed in a successor; package `__init__` files cannot gain exports. The freeze itself is right for provenance; what is missing is a way to see it before editing (fixed, section 8) and a place for shared code that experiments pin by version rather than by every file (section 6).

**D2. Three copies of the agent loop.** `p0.run_episode` (lines 355–424), `xv.run_episode_x` (adds `system_template`, a text-returning `block`, `tr_lessons`, `stop_after_turn`) and `n1.run_fork` (rebuilds history with `n1.rebuild_history`, re-executes the prefix, hard-codes seed `7`). The call-validation and result block is the same text three times. A fix to the loop, for example a change in how an invalid output is reported, has to be made three times and can no longer be made in the frozen copies.

**D3. Model clients.** The seven in-process implementations are `llm_backends.ollama_chat` and `openai_chat`, `writer_memory_sim.ollama_chat` (an earlier copy of the first; both pinned), `LocalReader`, `FlashReader`, `n1.Gateway` and `n1.Flash`; `n1.LocalClient` and `n2.ReplayClient` adapt them. Shape A, `llm_backends`: no `ProxyHandler({})` (environment proxies apply, while `LocalReader` and `Gateway` disable them), and `openai_chat` retries on `ValueError` and `KeyError`, that is on a malformed paid response. Shape B: `LocalReader` lives in a NIE pilot module that imports `nie_memory_contract` and `nie_persona_replay` at module level, so the BFCL pilot depends on NIE modules to obtain an HTTP client; `FlashReader.ask` takes `max_tokens` where `LocalReader.ask` takes `output_schema`, and has no outbound privacy check, while `n1.Flash.ask` does (`PRIVACY_PATTERNS`, owner-specific terms included). Shape C: `n1.Gateway` adds the features a long run needs (cache, buckets, retry, `ensure_ollama`) but only on a branch; `n2.Gateway2.payload` overloads the `schema` argument with the sentinel string `"text"` to mean "no JSON format". Inline: 17 scripts build their own `/chat/completions` request with `urllib`; 24 arena scripts and `run_goalshift_e0.py` import `openai.OpenAI` inside functions, so the test suite never needs it, but no file in the repository declares the SDK version a run used; and 23 Python files implement their own `.env` key lookup (`ROOT / ".env"`, `ROOT.parent / ".env"`).

**D4. Cross-module mutation.** `aamr_night1.py` line 486: `xv.note_text = _note_text`, executed on import; any process that imports `aamr_night1` changes S1's at-error note function for everyone, including tests in the same pytest process. It preserves S1's text for lessons without a `text` field, so it is behaviour-preserving for S1 by construction, but nothing outside that comment says so. `aamr_night2.redirect_n1()` sets `n1.RUN`, `NWORK`, `NDATA`, `OUT`, `CONFIG_PATH` and `PROTOCOL_PATH`; it is guarded by `activate()`, but makes `n1` a singleton that only one experiment per process can use. `metered_proxy.load_key()` sets `pp.ROOT = main_checkout()` after the first lookup fails and never restores it. These were the only way to reuse code whose paths and helpers are module globals; a successor should pass them as parameters.

**D5. Directory-layout coupling and invisible skips.** `p0.WORK = ROOT.parent / "experience-pilot-2026-11-12"`, `xv.XWORK = ROOT.parent / "experience-transfer-2026-11-12"`, `n1.NWORK = ROOT.parent / "aamr-night1-2026-11-12"` (with `AAMR_NIGHT1_RUN` and `AAMR_NIGHT1_OUT` overrides, the right direction), and `data/lab/experience-pilot-v0/config.json` sets `bfcl_root` to `../experience-pilot-2026-11-12/bfcl/src/berkeley-function-call-leaderboard`. A clone anywhere else silently skips the BFCL tests (counts in section 1). `bfcl-pinned.json` records the commit and the SHA-256 of every BFCL file used, but no script fetches or verifies a checkout. On `main`, `scripts/wmb/retrieval_bench.py` has three machine-local absolute defaults (`--notes`, `--prep`, `--workdir`, lines 2175–2179; pinned).

**D6. Import by `sys.path`.** 105 scripts and 81 test files insert `scripts/` (or a subfolder) into `sys.path`; there is no `conftest.py` and `pytest.ini` sets no `pythonpath`. Modules import each other by bare name (`import experience_pilot_v0 as p0`, `import nie_memory_contract as contract`), so a module works only when its caller set up the path first. 56 files load modules by file path under private names; for frozen versions that is deliberate (`p0.load_kernel` asserts `VERSION == "0.2.0"`), elsewhere it is a work-around.

**D7. Duplicated helpers with diverging semantics.** 65 files define their own JSON and digest helpers. They are not equivalent: `nie_reader_pilot.sha` serialises with `separators=(",", ":")`, `experience_pilot_v0.sha` with the defaults, and both results are stored as `request_sha256` (finding 6). Write helpers differ too: `nie_reader_pilot.write` opens with mode `x` (never overwrite), `p0.write_json` overwrites, `n1.atomic_json` replaces atomically.

**D8. Ledgers.** Six budget mechanisms (section 3.1) with different units (USD per call, reservations per attempt, attempts per bucket, attempts per raw manifest), number types (`float` in `SpendLedger` and `n1.Flash`, `Decimal` in `ReservationLedger`) and locking (only `ReservationLedger` takes a lock file). Reproduced defect: `SpendLedger.entries()` turns a torn line into `{"usd": <largest so far>, "torn": True}` without a `run_id`, and `scoped_usd()` counts only entries whose `run_id` starts with `cap_scope`, so under a scope the torn line counts zero. With entries `$1.00` and a torn `$2.50` line in scope `e1`, `check(1.9)` under a `$3.00` cap passes. `metered_proxy.py` and `flash_only_proxy.py` are normally run with `--cap-scope`. The five ledgers in `data/lab/` have no torn line. The torn-line count is also a floor (the largest earlier entry), not the cost of the lost call.

**D9. Memory blocks.** Every experiment has its own block format and header (`p0.MEMORY_HEADER` with `render_item`, `xv.LESSON_HEADER` and `NOTE_PREFIX`, NIGHT-2's `masked_block`, `trace_block`, `rb_block_text`). That is correct: the presentation is part of each arm's protocol. The debt is structural: in `p0` the provider returns rows and the loop renders them, in `xv` the provider returns text, so a provider written for one loop cannot run in the other.

**D10. Tests that need data outside Git** use `skipif` with an English reason, but there is no marker that separates them, CI does not print skip reasons, and a green CI run therefore says nothing about the BFCL line.

**D11. Duplicated proxy entry points.** `flash_only_proxy.main` repeats `metered_proxy.main` argument by argument, including the literal cap ceiling `15` in two places.

## 5. Adding a memory mechanism today

*Question-answering mechanism.* Implement `arena.adapter.MemoryAdapter`, run `validate_adapter` on `synthetic_fixture()`, and LifeSim can run it through `wrap_arena_adapter`. This path is on `main`, documented in the module and needs no knowledge of the harness. It is the model to copy.

*Context mechanism for the tool-using agent* (the current line). A contributor has to: check out three experiment branches, none on `main`; import `p0`, `xv` and `n1` with `scripts/` on `sys.path`; write a closure with the signature `xv.run_episode_x` expects (not the one `p0.run_episode` expects); add it to an arm dict for `n1.run_session`; route model calls through `n1.Gateway` by setting `AAMR_NIGHT1_RUN` or calling an equivalent of `n2.redirect_n1`; place a BFCL checkout at the relative path above; and add an at-error note by changing the `tr_lessons` mapping or replacing `xv.note_text`, as NIGHT-1 did. Nothing checks that the closure does not read gold answers or test tasks except the guards inside each experiment (`xv.guard_task`).

## 6. How to unify without changing the research architecture

Rule for everything below: **new, versioned code next to the frozen code**; no frozen file is edited; an existing experiment is never migrated; a new experiment adopts the new code by pinning its digests. Equivalence is proved by replay, not argued.

### 6.1 One client contract

The contract that four classes already satisfy, written down as a `typing.Protocol` in a new module (for example `scripts/aamr_harness/clients.py`):

```text
ask(key: str, messages: list[dict], seed: int, *, output_schema: dict | None = None, max_tokens: int | None = None) -> Response
Response: key, text, done_reason, usage (provider fields kept as returned), wall_seconds, request_sha256, returned_model
optional lifecycle: preflight() -> dict, finish() -> dict, release() -> None
```

Implementations: `OllamaClient` (the union of `LocalReader` and `n1.Gateway`: digest-checked cache, buckets, retry policy explicit and off by default, proxies disabled, no redirects), `FlashClient` (`FlashReader`'s reservation ledger and identity checks plus `n1.Flash`'s outbound privacy check), `ReplayClient` (from NIGHT-2), `FakeClient`. One request-digest function with a versioned name (`request_sha256` of compact, sorted JSON, recorded as `digest: "compact-v1"`), so finding 6 cannot recur. One key loader (environment variable, then `.env` in the main checkout found through `git rev-parse --git-common-dir`; never printed), used by new code only.

### 6.2 One BFCL episode loop with hooks

`run_episode(bfcl, task, client, names, *, arm, key, ctx_limit, system=None, context=None, after_results=None, start=None, stop_after_turn=None, seed=7)`, where `context(task_id, turn, request) -> Block(text, item_ids, meta)` and `after_results(step, entries) -> list[str]` (the at-error notes), and `start` resumes from a recorded prefix as `n1.run_fork` does. Acceptance test: with the arms of NIGHT-1 and NIGHT-2 expressed as hooks, replaying their stored `responses.jsonl` through the new loop (the method of `n2.compat()`) gives byte-identical requests, except where BFCL echoes its per-process instance name, which NIGHT-2 already normalises. Until that test passes, no experiment uses the loop.

### 6.3 Arms and a provider check

An `ArmSpec` record (name, bucket, context hook, after-results hook, per-domain variants) and a registry that maps arm names in `config.json` to factories, replacing the dict spec of `n1.run_session`. A `validate_provider` in the spirit of `validate_adapter`: deterministic output for the same input; the hook receives only `(task_id, turn, request)` and the pool, never gold; item ids resolve in the declared pool; no test-task id in the pool; block within the declared character cap; an after-results hook fires only on an observed error. This is what lets an independent contributor submit a mechanism as one file.

### 6.4 What not to unify

The arena and LifeSim contracts (memory answers) and the context hooks (memory is shown to the agent) stay separate until an experiment needs one through the other; then a thin adapter is enough. The block formats stay per arm. The kernel stays one vendorable file. Pools, lesson compilers and maskers stay inside their experiments: they are the mechanisms under test, and their current form is evidence-bound.

### 6.5 Order of migration

The owner decided on 2026-11-13 that the loops and clients are not refactored yet. When they are, the order is fixed by what each step needs, and every step adds files; none edits a frozen one or migrates an existing experiment.

| Step | What | Needs before it starts | Accepted when |
|---|---|---|---|
| 0 | NIGHT-2 has finished; its raw data, report and code are frozen and committed | nothing; it is running | its own freeze manifest exists |
| 1 | Fail-closed spend ledger and the proxy entry point that uses it | nothing | done: `spend_ledger_v2.py`, `flash_only_proxy_v2.py`, tests of the reproduced defect, the cap, damaged ledgers and settlement |
| 2 | Client contract (6.1) as a module with `FakeClient` and `ReplayClient` and a conformance test; `OllamaClient` and `FlashClient` ported with every guard and test of `LocalReader`, `FlashReader`, `n1.Gateway` and `n1.Flash` | step 1 for the paid client | each old test, ported, passes against the new class; no experiment uses it yet |
| 3 | One BFCL loop with hooks (6.2) | steps 0 and 2 | replay of NIGHT-1's and NIGHT-2's stored responses through the new loop gives byte-identical requests except the normalised instance names, and a second reviewer who did not write the loop has checked that replay independently |
| 4 | `ArmSpec`, registry, `validate_provider` (6.3) | step 3 | the NIGHT-2 arms are expressible as specs and pass the validator |
| 5 | The first new experiment uses steps 2–4 and pins their digests | steps 2–4 and its own preregistration | its README and freeze, as for any experiment |

Kernel changes follow the same rule: the next version is a new module next to 0.2.0, with its own `VERSION`, CHANGELOG and tests.

## 7. Improvements ordered by benefit, risk and effort

Effort: S under a day, M a few days. "Safe now" means it touches no frozen file and needs no model call.

| # | Change | Files | Benefit | Risk | Effort | Safe now |
|---|---|---|---|---|---|---|
| 1 | Ask "is this file frozen?" before editing | new `scripts/pinned_files.py` | High: avoids red CI on 61 frozen files; makes D1 visible | Low (read-only) | S | **done**, fixes branch |
| 2 | Correct "live line" in kernel README; say that `tasks.py check` is CI's local part; correct its time estimate | `scripts/wmb/kernel/README.md`, `tasks.py` | Medium | None | XS | **done**, fixes branch |
| 3 | Guard against machine-local absolute paths in code | new `tests/test_no_local_absolute_paths.py` | Medium: portability, privacy; the three frozen lines are allowed by digest | Low: zero hits on S1, NIGHT-1, NIGHT-2 and PR #105 | S | **done**, fixes branch |
| 4 | Link item 1 from the "Frozen files" section of `CONTRIBUTING.md` and correct the kernel row there | `CONTRIBUTING.md` | High for newcomers | None | XS | yes; left to the community-documentation session |
| 5 | Fetch and verify a BFCL checkout against `bfcl-pinned.json`, location from an argument or environment variable | new script | High: unlocks the skipped BFCL tests for contributors | Low | S | yes (verification needs one download, by the user) |
| 6 | Register `needs_bfcl` and `needs_raw_run` markers; `-rs` in CI so skips are visible; later `pythonpath = scripts` in `pytest.ini` | `pytest.ini`, CI | Medium | Low; the path change needs a full run on both interpreters | S | markers yes; path change after open branches land |
| 7 | One reservation ledger (Decimal, lock, scope, fail-closed reading) for new runs | new `scripts/arena/spend_ledger_v2.py`, `scripts/flash_only_proxy_v2.py` | High: money safety; removes the D8 defect for new runs | Medium (paid-call guard) | S–M | **done**, infrastructure pull request; old ledgers and proxies unchanged |
| 8 | Client contract and implementations (6.1), one digest function, one key loader | new package | High | Medium: every guard of `FlashReader` and `n1.Flash` must be ported with its tests | M | yes, as new code; adoption only by new experiments |
| 9 | One BFCL loop with hooks (6.2), accepted only by replay byte-identity | new module | High: removes D2 and D4 for future work | Medium: any byte drift changes prompts; the replay test bounds it | M | after NIGHT-2 has finished and its raw data are frozen |
| 10 | `ArmSpec`, registry and `validate_provider` (6.3) | new module | High for independent contributors | Low | S–M | after 9 |
| 11 | Run roots from config, argument or environment, never `ROOT.parent` | new code only | Medium | Low | S | with 8–9 |
| 12 | Shared IO helpers (digest with named form, jsonl append with fsync and tail repair, atomic json) | new module | Medium | Low | S | with 8 |
| 13 | Kernel 0.2.0 policy: drift notes for nine manifests, or a new file for the next version | kernel | Medium | Provenance decision | XS | **decided** by the owner on 2026-11-13: a new versioned module; recorded in the kernel README and `CONTRIBUTING.md` |
| 14 | Successor fixes for the pinned defects (section 8.2) | successors of the pinned files | Medium | Low | S each | as part of 7 and 8 |

## 8. Fixes made, and defects left in frozen code

### 8.1 On `claude/arch-fixes-2026-11-13` (from `main` at `20b3c2c`, local only)

Commit `639294b`. `python tasks.py check` on it: 3,022 passed, 21 skipped; memory integrity and claim audit passed (no critical finding).

- `scripts/pinned_files.py`: for named files or a directory, lists the live manifests that pin each file, using the claim audit's own functions (`walk_json`, `resolve_declared_target`, `superseded_by_marker`, `digest_bytes`, `git_blob`), so the two cannot disagree; `--check` exits 1 when a named file is frozen, for a pre-commit hook; `--format json`. It confirms the probe: 9 manifests for kernel 0.2.0. It cannot see a freeze by policy (for example `experience_pilot_v0.py`, which no manifest pins but later experiments import), and says so. Tests: `tests/test_pinned_files.py` (11, synthetic trees plus the kernel).
- `tests/test_no_local_absolute_paths.py`: no drive-absolute or home-directory path in `scripts/`, `tools/` or `tasks.py`; the three frozen lines of `retrieval_bench.py` are allowed by the SHA-256 of the line, so the test does not repeat the paths, and the allowance fails if they disappear (3 tests).
- `scripts/wmb/kernel/README.md`: the layout row states that 0.2.0 is pinned and that the choice between drift notes and a new file is the maintainers'. `tasks.py`: `check` is described as the local part of CI (the kernel-mutation, other-interpreter and canonical-store-guard jobs run only in CI), and the test-suite estimate is the measured one.

Added after the owner's follow-up of 2026-11-13, on the same branch, after merging `main` at `3a0c5e9`:

- `scripts/arena/spend_ledger_v2.py`, `SpendLedgerV2`: reads version-1 lines, refuses (with `LedgerUnreadable`, a `TotalCapReached`, so the frozen handler answers HTTP 402 and forwards nothing) on a torn last line, invalid JSON, a non-object, a missing or empty `run_id`, an amount that is not a finite non-negative number, an unknown format or event, a settlement that matches no open reservation, a reused id, a missing file without `create=True`, non-UTF-8 bytes, or a lock it cannot take in time; `check` appends a reservation under a file lock and counts open reservations as spent; `record` settles the cheapest open reservation of the instance and charges at least the reservation when usage is not reported as known. Decimal sums. It reads the two committed version-1 ledgers to the same totals and refuses the three ledgers of other formats rather than misreading them.
- `scripts/flash_only_proxy_v2.py`: the frozen `flash_only_proxy.guarded_handler` and `provider_proxy.ProxyState` composed with the new ledger; the run cap is checked first, so its refusal leaves no reservation; `--new-ledger` is needed to start a ledger; the key is loaded only after every check passed.
- Tests: `tests/test_spend_ledger_v2.py` (43: the defect reproduced on the frozen version 1, version 2 refusing the same file, the cap and its inclusive edge, a second process and 40 concurrent checks, 18 kinds of damaged ledger each left byte-identical, settlement, unknown usage, a crash in flight, the committed ledgers) and `tests/test_flash_only_proxy_v2.py` (8, end to end against a local stub provider: settle after a 200, 402 past the cap, 402 on a torn ledger where version 1 would forward, 403 for another model without a reservation, a run-cap refusal without a reservation, an answer without usage charged its reservation, and command-line refusals before the key is loaded).
- The kernel decision in `scripts/wmb/kernel/README.md` and `CONTRIBUTING.md`, which also points to `pinned_files.py` in its "Frozen files" section; the laboratory map points new paid runs to the version-2 proxy.

### 8.2 Defects found in frozen files (report only; fix in successors)

| File, function | Defect | Effect today |
|---|---|---|
| `arena/spend_ledger.py` `SpendLedger.scoped_usd` | torn line ignored under a cap scope (D8) | none recorded; affects a crash during a scoped paid run. **Successor:** `spend_ledger_v2.py` |
| `arena/spend_ledger.py` `SpendLedger.by_run` | rounds the running total to 6 decimals at every addition | per-run totals drift: on one run of `data/lab/arena/spend-ledger.jsonl` it reports 2.334746 USD against an exact sum of 2.33472728; `total_usd` rounds once and is exact to 1e-6 |
| `arena/provider_proxy.py` `ProxyState.check` | checks the shared cap before the run cap | harmless with version 1; with a reserving ledger a run-cap refusal would leave a reservation, so `flash_only_proxy_v2.ProxyStateV2` checks the run cap first |
| `metered_proxy.py` `load_key` | rewrites `arena.provider_proxy.ROOT` permanently | later key lookups in the process search the main checkout |
| `flash_reader_client_v1.py` `FlashReader.ask` | no outbound privacy check, unlike `aamr_night1.Flash.ask` | used on synthetic inputs so far |
| `nie_reader_pilot.sha` vs `experience_pilot_v0.sha` | two digest definitions stored as `request_sha256` | cross-experiment comparison of request digests is invalid |
| `llm_backends.py` `openai_chat`, `ollama_chat` | environment proxies apply; a malformed paid response is retried | bounded by the proxy cap |
| `wmb/retrieval_bench.py` `main` | machine-local default paths | overridable by arguments |
| `flash_only_proxy.py` `main` | duplicate of `metered_proxy.main`, cap ceiling literal twice | none; a change must be made twice |

## 9. Limits

This is a reading of code and a few mechanical probes, by one reviewer, on one day. It did not run any experiment, so it makes no claim about which memory mechanism works. Counts are of `main` at `20b3c2c` and of the three branch heads named above; NIGHT-2 was running, and its final code may differ from `9bfacbe`. The improvement order weighs engineering benefit; whether and when to build items 7–10 depends on the research plan, which this audit does not set.
