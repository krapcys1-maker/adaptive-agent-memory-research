# Research direction review, 2026-11-01

Subject: the owner's vision "Adaptive Associative Memory and Long-Term Cognitive Development in Autonomous LLM Agents" (pasted 2026-11-01), checked against what this repository actually contains on branch `revival/phase0` at commit `e306bf2`.

Evidence labels used throughout: **MEASURED** (read from a committed file, or from a command run in a scratch clone, path given), **INFERENCE** (my reasoning from measured facts), **UNVERIFIED** (not checked, or not checkable here). Paths are relative to the repository root. Nothing in the repository was edited and no model or network call was made; the full suite was run once in a scratch clone (1085 passed, 20 skipped) and the corpus H1 lexical baseline was re-run there.

## 1. Verdict

1. The direction is compatible with the project's history and with its doctrine only if it is run as **one mechanism under test (a compact associative trace) inside a small Tier E study**, not as a named five-layer architecture; the doctrine refuses to name an architecture until three mechanisms pass tier I1, and the project has one mechanism at "replicated" status whose own evidence is 2 repairs in 17 units.
2. Roughly half of the infrastructure exists (append-only archive, token-fair arm registry, cost-aware adapter contract, spend ledger, deterministic corpus generator with a leakage-proof reveal split), but **the five pieces the first study needs do not exist**: a goal-change generator, a vocabulary-mismatch control, an operational-forgetting state, a summarization arm, and a trace arm.
3. The corpus the owner would naturally reuse has **no headroom** on the delayed-relevance question: the committed lexical re-run solves the DELAYED and REDERIVE families at recall 1.000 for k=1, 5 and 10, and the dense probe also reaches 1.000, so an advantage for traces cannot be shown there without a new, harder generator.
4. The associative idea collides with prior negative results (PMLAB-ASSOC-E1 inconclusive, E2 retracted as leakage, E3 harm of -0.114 Recall@5; ledger Entry L null), with the evidence that verbatim raw beats compact extraction (Entry H), and with the paused preregistrations, the work-in-progress limit and the spend-frozen V3 budget; each has a resolution that keeps history intact (section 6).
5. V-H1 and V-H5 are testable first and cheaply (model-free retrieval on an extended generator); V-H2 needs a small addition; V-H3 and V-H4 are not testable with anything here and should wait for the agent-integration phase; a complete first run is estimated at about $1.5 to $5 (INFERENCE from measured per-call costs), none of it authorised yet. *Update (2026-11-01, after the first run):* the retrieval-level stages (E0) ran for $0 and gave a null for D; the answer-level stage would cost about $0.55 to $1.19 and is not planned.

## 2. Fit table

Status: **exists** = usable as is; **partial** = something real but not the vision's meaning; **missing** = nothing found.

| Vision element | Existing component(s) | Status | Note |
|---|---|---|---|
| Layer A, working memory (context supplied to the model) | `tools/project_memory/memory_store.py` `context()` (budget in characters); `scripts/corpus/arms.py` `_fill` (budget in whitespace words) | partial | Budget is enforced, but in two different units, neither a model token (MEASURED: `char_budget` 1000-50000, `DEFAULT_TOKEN_BUDGET = 250` words). |
| Layer B, active memory (recent, goals, unresolved) | `memory/CURRENT_STATE.md` reserved share in `context()` (`CONTEXT_STATE_SHARE = 0.4`); record field `status` (default `active`) | partial | "Active" is a hand-written state file plus a status string. No goal object, no unresolved-problem tracking. |
| Layer C, consolidated memory | reviewed Markdown in `memory/records/`; "Reflection Stage 1" (five exact-only detectors, per `memory/CURRENT_STATE.md`; I did not locate the code) | partial | No process that derives lessons from several experiences. The ledger records that a contradiction detector was written and removed after 4 of 4 false positives. |
| Layer D, associative memory | `scripts/run_association_graph_e1.py`, `_e2.py`, `_e3.py`; record field `related_ids`; `scripts/corpus/address_extract.py`, `entity_canon.py`; glossary query expansion in `memory_search` | partial | Lab code over project documents, not an engine feature. Graph-as-fusion is closed negative. `PMLAB-H1-ADDR-E2` (infer a memory address from text) is registered, not run. |
| Layer E, experience archive | `memory/events.jsonl` (append-only canonical log); `scripts/verify_memory_integrity.py` (21 registered mutations); CI guard against deleting or rewriting a line | exists | The strongest existing component. Operationally "never lose the original" is already enforced. |
| Operational forgetting (kept, not supplied) | `scripts/corpus/arms.py` `_before` (day filter); supersession in `memory_supersede`; registry row `PMLAB-FORG-F3-001` "Reversible active forgetting" (`blocked-corpus-not-built`) | missing as a mechanism | Nothing marks an experience "dormant but recoverable". Supersession is the only state change. |
| Associative traces (few concepts, relations, pointers to archive) | none as a data structure. Nearest: `related_ids`, `address_extract.py` | missing | |
| Dynamic importance | arms `frequency` and `recency` in `scripts/corpus/arms.py`; `PMLAB-COMP-C4-001` salience review packet (no controller) | missing | Only static scorers exist. The salience protocol explicitly forbids implementing a controller before independent review. |
| Predicted importance vs measured usefulness | `docs/11-research-laboratory/future-utility-telemetry-protocol-v0.md`; `data/lab/pmlab-future-utility-v0/` (event schemas v0, v0.1; T0.1 synthetic validation; blind audit packet); `docs/03-human-ai-bridge/hypotheses.md` H2 | partial | The estimand and event schema exist; the protocol is observation-only and says it "must not adapt retention, consolidation, deletion, retrieval rank". No predictor. T1-T4 locked. |
| Baseline A, no memory | `scripts/arena/fixed_reader.py` arm `baseline` (question alone); `recency` and `random` arms for corpus H1 | partial | The no-memory arm exists only for the frozen LongMemEval artefacts. Not run on corpus H1. |
| Baseline B, conventional retrieval | `scripts/run_corpus_h1_baseline.py` (FTS5 BM25); `scripts/run_corpus_h1_dense_probe.py` (MiniLM, local); Mem0 and Hindsight adapters in `scripts/arena/` | exists | Local, free, deterministic. Mem0 and Hindsight were measured only on legacy versions (section 6). |
| Baseline C, summarization | none. Corpus README: "P0 native product compaction ... None is implemented against this corpus"; grep for summariz in `scripts/corpus`, `scripts/arena` found no arm | missing | |
| Baseline D, adaptive associative memory | `scripts/arena/aamr_adapter.py` | partial | Reference adapter for `CANDIDATE-0`, a registered negative artifact; not the vision's mechanism. |
| Equal budgets across arms | `scripts/corpus/arms.py` (all arms through one `_fill` at one budget); `scripts/run_corpus_h1_reader.py` | partial | Fair inside corpus H1. The adapter contract only *reports* `context_tokens`; it does not enforce a budget. Three budget units coexist (words, characters, reported words). |
| Cost accounting | `scripts/arena/adapter.py` `Cost`/`Measure` (calls, input and output tokens, wall microseconds, per-field observability, lower-bound rule); `scripts/arena/spend_ledger.py` (cap checked before each call); `scripts/arena/decoding.py` (`PRICE_PER_MTOK = {input 0.27, output 1.10}`) | exists | Covers ingest and query. Maintenance over time (re-evaluation after a goal change) has no slot. |
| Isolated or replay environment | `MemoryStore(root)` and CLI `--root`; simulated `day` and `asked_at` in corpus H1 and in the adapter `query(question, asked_at)` | partial | A store can live in a separate root. But `created_at` is `_utc_now()` and cannot be supplied, so replaying 30 days stamps every event with wall-clock time (INFERENCE from `memory_store.py` `add()`; only `valid_from` is injectable). No replay of any real agent exists. |
| Split: agent / engine / experiment framework | engine: `tools/project_memory` plus `scripts/corpus`; framework: `scripts/arena`, `data/lab/experiment-registry.csv`, `scripts/registry_summary.py` | partial | The engine/framework split exists in practice. There is no agent side, no connector and no stable engine interface; the arena adapters wrap third-party systems, not this engine. |

## 3. Gaps and unnecessary complexity

### Missing for the first small study (concrete)

1. **A goal-aware experience generator.** `history_family_spec.py`, `build_history_family.py` and `build_delayed_reveal.py` contain the word "goal" zero times (MEASURED). Needed: goal-declaration events, a goal change at a known day, and probes phrased in terms of the new goal.
2. **A vocabulary-mismatch dial.** Nothing controls lexical overlap between the old event and the later cue (see 5b). Needed: a parameter (for example none, partial, synonym-only) applied to the cue.
3. **An operational-forgetting state.** An active set under a fixed budget, an archive reachable only through a pointer, and a recorded "dormant" flag, so that "forgotten but recoverable" is a measurable condition rather than a metaphor.
4. **Arm C and arm D.** A deterministic or model-based summarizer and the trace mechanism, both behind one interface (section 5d). Also a no-memory arm on this corpus.
5. **A context-retrieval interface separate from answering.** `Answer.text` in the adapter contract is "the answer"; Mem0's adapter returns its top hit as the answer. The study needs `retrieve(cue, goal, budget) -> context + cost` and a single shared reader.
6. **One budget unit.** The vision says about 4,000 tokens; the repository measures words and characters.
7. **Repetition and uncertainty.** `reader-v0-report.md` states "No repetitions"; the vision asks for several seeds and intervals. The generator takes a seed, so fresh corpora are cheap, but no runner loops over seeds.
8. **A reader-side scoring fix.** In `reader-v0-fts5` 3 of 12 DELAYED probes were marked unanswered although the gold event was in context 12 of 12 times; the missing fragment was the `file:line` string (MEASURED, `data/lab/corpus-h1/reader-v0-fts5/results.json`). Strict fragment matching is currently the limiting factor, not memory.
9. **A registry row and a preregistration** under the doctrine (section 6.2).

### What the new work should not carry along (no deletions proposed)

- **Documentation volume.** 2,152 tracked files; 1,583 under `data/lab`; tracked Markdown is at least 253,000 words, of which `docs/` is at least 190,000 (MEASURED with `git ls-files | xargs cat | wc -w`; nine paths containing spaces failed to read, so these are floors). `docs/07-literature` (50 files), `docs/11-research-laboratory` (43 files) and `docs/research` (35 files) are context, not prerequisites.
- **Process machinery.** 74 registry rows (39 completed, 20 blocked, 7 invalid, 8 awaiting; `scripts/registry_summary.py`), the independence ladder, sealed-split protocol, claim audit, and the 21 unexecuted preregistrations. The new study needs one registry row and the rules that bind it, not the apparatus.
- **Vendor patches.** `data/lab/arena/*/vendor-patch/` holds patched copies of Mem0 1.0.6 source (`mem0/memory/main.py`, `utils.py`) with `NOTICE.txt` files; the vision itself says licensing decisions are unresolved. The new engine should have zero dependency on them.
- **Bridge folders.** `docs/research/Dokumenty dla Resherchera/` (9 tracked files, the ResearchOS request channel), `data/lab/longmemeval-bridge-v0/` (16), `data/lab/stale-bridge/` (1). All tied to the LongMemEval arena and the frozen V2/V3 campaigns.
- **Arena mechanism runners.** About 30 `scripts/arena/run_*_v1.py` and `mech*` scripts exist for single mechanisms already dropped (Entries I, J, K, L, M, Q). They are history; the adapter contract and cost classes are the only parts worth reusing.
- **The legacy-version stack** (Mem0 1.0.6, Hindsight 0.9.1, the `external/venvs` environments, which are not tracked).

## 4. Testability of the provisional hypotheses

**Naming.** Use the prefix **V-H1 to V-H5** for the vision's hypotheses. "H1" through "H5" already mean the following (MEASURED by grep of tracked Markdown):

- Corpus H1 and H2 (`data/lab/corpus-h1/`, `data/lab/corpus-h2/`; `docs/00-project/operating-plan-and-rules.md` line 140) and the experiment ids `PMLAB-H1-BASE-E1`, `PMLAB-H1-READ-E1`, `PMLAB-H1-DENSE-E1`, `PMLAB-H1-ADDR-E2` (registry).
- `docs/03-human-ai-bridge/hypotheses.md`: H1 complementary stores, H2 causal future utility, H3 operational salience, H4 provenance-preserving consolidation, H5 type-conditioned retention (also H6, H7).
- Per-protocol H1-H3 in `natural-history-retrieval-benchmark-protocol-v0.md` (dense value, complementarity, cost boundary), `procedural-memory-retention-and-relearning-benchmark-protocol-v0.md`, `natural-completeness-controller-benchmark-protocol-v0.md`.
- Archaeology: `docs/research/TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md` uses H0 (noise) to H5 (harmful sibling); `docs/research/CONTEXT_AND_PROVENANCE_ABLATION_V1.md` uses H1 volume, H2 information kind, H3 raw provenance; also cited in `RAW_PROVENANCE_FRESH_REPLICATION_V1.md`, `CLEAN_RAW_PROVENANCE_RETEST_V2.md`, `MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md`, `hindsight-mechanism-sheet-v0.md`.
- Ledger "frontier H2" (`ZERO_ANSWER_DISPERSION_DIAGNOSTIC`) and "H0 (noise)". No tracked file named as a frontier map was found (`git ls-files | grep -i frontier` is empty), so those ids are only visible in the ledger text (UNVERIFIED beyond that).

| Hypothesis | Testable with current infrastructure? | What is missing | Cheapest honest test |
|---|---|---|---|
| **V-H1** associative traces preserve low-priority, later-relevant experiences vs deletion or summarization at equal budget | **No, not on corpus H1**; yes after a small generator extension | Headroom (5a); vocabulary-mismatch control; forgetting state; summarization and trace arms | Model-free, retrieval-only (it builds a fresh corpus, so under the selection table it is Tier C and needs an I1 sealed split to claim a tier; E0 ran it unsealed, as exploratory, and D was not supported: `data/lab/aam-e0-delayed-relevance/README.md`). Extend the generator with a delayed-relevance family whose later cue shares a controlled fraction of vocabulary with the event and arrives after a goal change. Arms at one 250-word budget: archive-wide FTS5 (the real upper reference), active-only FTS5 (operational forgetting with no trace, the honest "deletion" comparator), extractive summary, trace. Metric: gold event in context and forbidden-event intrusion, which are already scored by `run_corpus_h1_baseline.py`. Buy a reader only if retrieval separates the arms. |
| **V-H2** re-evaluating importance beats static scoring | **Not yet** | Goal-change events; a re-scoring rule; a static-importance comparator that is not just recency or frequency | Same generator and arms as V-H1; add a deterministic re-scoring step (for example goal-term overlap) triggered at the goal change, versus the same trace frozen at write time. Free if the re-scoring is deterministic. Do not use outcome feedback: the future-utility protocol forbids adapting retention until its T1-T4 gates open. |
| **V-H3** cross-domain transfer | **No** | A two-domain corpus with a shared abstract lesson, a transfer metric, and a reader; the repo's "domains" are services with identical templates | Defer. A cheap precursor is a two-domain synthetic with a mechanical answer; it needs a reader (about the cost in section 5c) and its construct validity is weak. The prior graph-expansion nulls (ledger Entry L: irrelevant associated content in both fired cases) suggest the cross-domain connections are the hardest part of the claim. |
| **V-H4** behavioral persistence over time | **No** | An agent loop, a longitudinal protocol, an attribution design separating memory from prompt and model change; telemetry T1-T4 are locked | Defer to the agent-integration phase. A replayed scripted agent can test persistence of one decision rule, but that is a different claim and should be named as such. The audit of the first real candidate (a live writing agent) adds that persistence needs recorded inputs it does not keep and that its live experiments run until 2027-02-10 (reported by that audit, not verified here). |
| **V-H5** efficiency (equal quality at fewer tokens or lower cost) | **Partially, as a by-product of V-H1** | Maintenance-cost slot (re-evaluation over time); one token unit | Report gold-in-context per 1,000 retrieved tokens and total ingest plus maintenance cost for each arm, using `Cost` and the baseline's existing recall-per-1k metric. Caution (5a): lexical retrieval already needs about 39 whitespace tokens at k = 1 on the DELAYED family (22.8 is the all-family mean), so an efficiency edge is unlikely on the existing corpus. |

## 5. Facts the first experiment depends on

### 5a. Corpus H1: DELAYED and REDERIVE, and whether baselines already solve them

**Definitions (MEASURED, `scripts/corpus/history_family_spec.py`, `data/lab/corpus-h1/reveal-v0/`).** The corpus is 538 events over 30 days, 7,784 words in total (mean 14.5 words per event), 84 probes in seven families of 12 (`prefix-v0/history.jsonl`, `reveal-v0/queries.jsonl`, `gold.jsonl`).

- **DELAYED (12 probes).** One early event (day 2-6): "Connection pool exhausted under load in {service}. Root cause in src/db/{module}.py:{line} ... sized {n} while the worker count was {m} ... read-only credentials ..." followed by one noise event. The probe is asked on day 26-30 (gap 21-27 days measured over the 12 probes): "We are seeing pool exhaustion in {service} again. Has this happened before, where, and what was the cause?" Gold is that single event; no forbidden event. The service differs per probe (12 distinct questions).
- **REDERIVE (12 probes).** One event stating how many functions `src/util/{package}.py` exports; the probe asks the same count. Constructed so that reading the file would answer it.

**Retrieval results (MEASURED).** Lexical = FTS5 BM25, OR of terms, `scripts/run_corpus_h1_baseline.py`. I re-ran the script from the committed corpus in a scratch clone; the output is byte-identical to the committed `data/lab/corpus-h1/baseline-v0.1-rerun-2026-11-01/results.json`.

| Family | Source | recall@1 | recall@5 | recall@10 |
|---|---|---:|---:|---:|
| DELAYED | re-run, current corpus | 1.000 | 1.000 | 1.000 |
| DELAYED | `baseline-v0` (earlier, superseded corpus state) | 0.083 | 0.417 | 0.833 |
| REDERIVE | re-run, current corpus | 1.000 | 1.000 | 1.000 |
| REDERIVE | `baseline-v0` | 0.167 | 0.833 | 1.000 |
| FAILFIX | re-run | 0.583 | 1.000 | 1.000 |
| RARE-EXC | re-run | 0.917 | 1.000 | 1.000 |
| BILINGUAL, POISON | re-run | 1.000 | 1.000 | 1.000 |
| OBSOLETE | re-run | 0.000 | 0.000 | 0.167 |

Token figures, overall, re-run: mean retrieved tokens 22.8 at k=1, 117.3 at k=5, 245.9 at k=10 (words, not model tokens); intrusion@10 0.25; forbidden outranks gold 0.000 over 48 probes. I did not compute per-family token means.

**Dense probe (MEASURED, `data/lab/corpus-h1/dense-probe-v0/results.json`, `PMLAB-H1-DENSE-E1`, MiniLM multilingual, local, one 250-word budget fill):** gold reached the context for DELAYED 1.000 (lexical 1.000), REDERIVE 1.000 (1.000), BILINGUAL 1.000, FAILFIX 1.000, POISON 1.000, OBSOLETE 0.500 (lexical 0.167), RARE-EXC 0.250 (lexical 1.000). Overall 0.821 dense vs 0.881 lexical; an oracle router over both reaches 0.929.

**End to end (MEASURED, `reader-v0-report.md`, `reader-v0-fts5/results.json`):** at a 250-token budget with `deepseek-v4-flash`, fts5 answered DELAYED 0.750 while the gold event was retrieved in 12 of 12; the 3 failures omitted the `file:line` fragment.

**Conclusion.** The corpus has **no headroom** on DELAYED or REDERIVE. A budget of 250 words is 3.2% of the corpus, which sounds restrictive, but the DELAYED cue names the service and the phrase "pool exhaustion", so a word index finds the event first. Remaining headroom is in OBSOLETE (a supersession problem, not an association problem, cf. `PMLAB-STALE-E1` in `memory/CURRENT_STATE.md`) and in dense RARE-EXC. A trace cannot show an advantage over lexical retrieval on the families that match the vision. Also note that the README table in `data/lab/corpus-h1/README.md` that I read (DELAYED 0.833, POISON forbidden-above-gold 0.25) describes `baseline-v0`, not the re-run; the re-run's own README says not to cite the 25%.

### 5b. Can the existing generator produce goal changes and vocabulary mismatch?

- **Goal changes: no** (MEASURED, zero occurrences of "goal" in the spec and both builders). Events are `agent_note`, `tool_result`, `user_message` (442/60/36 events); each case has one probe with a fixed question template.
- **Vocabulary mismatch: not controllably.** On average 28% of DELAYED question tokens, 33% for REDERIVE, 18% for OBSOLETE and 69% for BILINGUAL appear in the gold event (my token-overlap calculation over `queries.jsonl` and `history.jsonl`; crude, not stemmed). The only designed mismatch is language (BILINGUAL), and that corpus states the fact in both languages, so a lexical match exists.
- **What can be reused (MEASURED):** deterministic LCG, no clock; family templates instantiated `--instances` times; `event_id()` shared so the reveal can name a gold event without opening the history; a test (`tests/test_history_family_construction.py`) that runs the reveal with and without the history and requires identical output. A new family is a pure addition to `FAMILIES` and per the spec's docstring does not renumber existing instances.

### 5c. Real cost figures

All from committed files; the model is a DeepSeek family model throughout.

| Quantity | Value | Source |
|---|---|---|
| Reader call, 250-token context, `deepseek-v4-flash` | $0.077 for 168 calls = **$0.00046/call**; fts5 arm $0.0415 for 84 calls = $0.00049/call | `data/lab/corpus-h1/reader-v0-report.md`, `reader-v0-fts5/results.json` |
| Mean paid call across the whole arena, `deepseek-chat` | 19,585 calls, $19.44, **$0.00099/call**, mean 2,419 prompt and 309 completion tokens | `data/lab/arena/spend-ledger.jsonl` (my aggregation), `scripts/arena/decoding.py` prices |
| Mem0 or Hindsight unit, ingest plus read plus judge, about 50 sessions | about $0.07 per unit (Entry L $0.414/6 units; Entry Q $0.436/6; raw-provenance replication $0.575/8) | ledger Entries L, Q, H; spend ledger run ids |
| Ingest through an LLM per item | CUPMem 7.75 calls and 13,220 prompt tokens per session, about $0.21 per 48-session unit (floor); Hindsight about $0.00146/call | `data/lab/arena/run-cost-projection.json`, spend ledger |
| Harness-defect discovery pilot | $0.021 found five defects before the full run | `reader-v0-report.md` |
| Campaign budget | V2 closed at $4.393354 of $5.00; V3 cap $10.00, spent $0.00, **frozen** | `data/lab/arena/autonomous-research-budget-v2/ledger.json`, `-v3/ledger.json` |
| Local embeddings, FTS5, deterministic scoring | $0 | corpus H1 baseline and dense probe |

**Estimate (INFERENCE, arithmetic on the figures above).** Take 150 experiences, 3 goal phases, 40 probes per phase (120 probes), 4 arms, 3 repeats: 1,440 reader calls.

- Reader at 250-word context: 1,440 x $0.00046 to $0.00099 = **$0.66 to $1.43**.
- Reader at a 4,000-token context (the vision's number): about 4,300 prompt plus 300 completion tokens at the ledger prices is about $0.0015/call, so about **$2.1**.
- Maintenance: arm C and arm D write-time calls (150 each) at $0.001 = $0.30; trace re-evaluation at 3 goal changes if done per memory by a model, 450 calls = $0.45; $0 if deterministic. About **$0.3 to $0.8** per pass.
- Judging: $0 if scoring stays mechanical (`answer_contains`), as in corpus H1.
- Total for one complete run: **about $1.5 to $5**; plus a pilot of a few cents. Matches the ledger's own sizing note of about $2-3 per mechanism cycle. Prices are DeepSeek's; the target agent's own model would cost more (UNVERIFIED). For comparison, the audit of the first real candidate (a live writing agent) estimates $31 to $52 for its own 30-day plan, which its independent check puts at 3.8 to 6.3 times that agent's October bill (reported, not verified here), against the frozen V3 cap of $10.
- Not measured: human review effort, authoring effort for the generator extension, and any cost of a 4,000-token budget on a stronger model.

### 5d. What a pluggable "arm" would reuse

- **`scripts/corpus/arms.py`**: `ARMS` registry of functions `(events, question, day, budget, stream) -> events`; one `_fill` shared by all arms; `_before` prevents future leakage. Reuse as the budget-fairness core. It has no ingest phase, no goal argument, no cost return.
- **`scripts/arena/adapter.py` and `adapter_v0_1.py`** (contract `ARENA-0.1`): `reset()`, `ingest(records) -> Cost`, `query(question, asked_at) -> Answer`; `Measure`/`Cost` with integer microseconds and per-field observability; `validate_adapter`; `query_mutates_state` declaration; `contract_digest()`. `tests/test_arena_adapter_contract.py` has 17 tests. Reuse the cost types and the "adapter reports signals, harness interprets" rule. Needs extension: a `goal`/`context` argument, an explicit `consolidate` or `tick` call for maintenance, and a budget argument.
- **`scripts/arena/fixed_reader.py`**: a single reader for all arms, anonymised contexts, `READER_PARAMS = {temperature 0, max_tokens 300}`; reuse as the shared reader.
- **`scripts/arena/spend_ledger.py`, `decoding.py`**: cap checked before the call; reuse unchanged.
- **`scripts/arena/aamr_adapter.py`**: a worked, model-free adapter, useful as a template.
- **`tools/project_memory`**: usable as the storage layer of an arm, and as the archive layer (events.jsonl); but see section 7 for the constraints.

## 6. Conflicts with the project's research history and rules

1. **Architecture.** `docs/00-project/operating-doctrine.md` ("What we deliberately do not have"): the project "refuses to name one until evidence supports it"; revisit when three independent mechanisms have each passed at least tier I1. Ledger Entry H's status is a procedural label whose evidence is 2 repairs and 0 regressions in 17 units on Mem0 1.0.6 (exact sign test p = 0.5, Entry R); `memory/CURRENT_STATE.md` lists no other mechanism. The vision's layers and arm D read as an architecture. *Resolution:* register arm D as a single mechanism hypothesis (the trace), call the layers a vocabulary, and revisit architecture only on the doctrine's condition. The vision already says the layers are conceptual (section 5 of the vision).
2. **WIP limit and paused preregistrations.** The doctrine allows "at most two experiments per track ... designed, not executed". `CURRENT_STATE.md` (line 9) still says new preregistrations are paused until the 21 unexecuted drafts are triaged, but that triage exists: `docs/11-research-laboratory/preregistration-triage-v1.md` classifies all 21 (1 execute now, 16 blocked on corpus and budget, 4 blocked on independent review, 0 retired) and the registry carries the result (20 blocked rows). Its standing rule is "Do not add a new preregistration until at least one family has an executed result", and the one "execute now" item, `PMLAB-REV-V0-001`, is now `completed-exploratory-threshold-met`. Whether that completed result satisfies the rule is the owner's judgement; if it does, `CURRENT_STATE.md` line 9 is stale. *Resolution:* state the pause from triage-v1 rather than from `CURRENT_STATE.md`, and ask the owner whether `REV-V0-001` satisfies the rule or an explicit exception is needed. *Possible overlap, unchecked:* `CURRENT_STATE.md` says "Build one corpus family. Four fixtures would unblock sixteen experiments", and a goal-aware generator might partly serve the blocked drafts. But triage-v1 defines the shared need of the `REV` drafts as a temporal corpus with supersessions and corrections, and of the `COMP` drafts as a multi-cycle compaction corpus with a reader, which a delayed-relevance generator does not provide; treat the overlap as a question, not a saving.
3. **Association and graph expansion.** `PMLAB-ASSOC-E1`: inconclusive (Recall@5 +0.0245, CI [-0.0343, 0.0833]). `E2`: retracted, 67.5% of graph-reachable targets were reachable only through the gold-generating group; neutralised result -0.0644 at k=5. `E3`: Recall@5 -0.1143, CI [-0.1786, -0.0536], harms about twice as many queries as it helps; decision "association-graph-as-retrieval-fusion closed" (registry). Ledger Entry L (second-hop expansion): net repairs 0, both fired cases returned irrelevant associated content, with "don't retune the same failed action". *Distinction that justifies continuing:* those tests expanded from lexical or top-1 hits over project documents (mechanical tag gold), whereas the vision's trace is written at storage time and activated by a new goal. *Resolution:* state the difference in the preregistration; do not seed activation from lexical hits; apply the E2 leakage lesson (a trace builder must not see the future cue or goal, and any link group that defines the gold must be removed from the reachable set); cite E1-E3 and Entry L as prior negative evidence in the study's first paragraph.
4. **Raw beats extraction.** Entry H: appending the verbatim source session to Mem0's top-1 hit gave 6/9 and 6/8 against compact 5/9 and 5/8, with `raw_only` underperforming compact; the cited external support is TierMem (raw 0.873 > routed 0.851 > summary 0.755) and Verbatim Chunks (43.9% vs 28.0%). Entry R notes the raw arm carried 16 to 32 times the context. The vision's arms C and D both compress. *Resolution:* define the trace as a pointer to the raw record and include "retrieve, then expand to the raw event" as a named comparator at the same total budget; if it equals the trace, the trace added nothing. This is the vision's own "if conventional RAG performs just as well, that is a valid outcome".
5. **Future-utility labels.** Already studied as `PMLAB-UTILITY-001`: T0.1 synthetic schema validated, T1-T4 locked; "observation-only. It must not adapt retention, consolidation, deletion, retrieval rank"; the primary estimand is task-level, and individual-memory utility requires a factorial or leave-one-out design. Also `docs/03-human-ai-bridge/hypotheses.md` H2. The vision (section 8) wants a controller that learns from later retrievals. *Resolution:* in the first study, usefulness comes only from the generator's construction labels, used for evaluation never for training; reuse the telemetry event schema when real streams exist; do not reinvent the labels.
6. **Legacy versions (Entry R).** All Entries A-Q used `mem0ai` 1.0.6 and `hindsight_api_slim` 0.9.1; upstream is Mem0 2.2.1 and Hindsight 1.1.0, nothing re-run; Entry R's next trigger is a re-baseline before any new spend. *Resolution:* use the repository's own FTS5 and dense retrieval as arm B for the first study, and defer Mem0 and Hindsight to a later comparison after the re-baseline.
7. **Gated budget.** The V3 ledger has a $10 cap, spend $0.00, and a gating condition: no spend until a candidate for `arr-2026-08-25-001` clears four filters, one of which is targeting exactly one of the three named failure modes (assistant-turn representation loss, retrieval-anchor failure, temporal representation loss). The vision's study targets none of them. `MEMORY.md` records Campaign V2 as frozen. *Resolution:* run the model-free Tier E part ($0) first; any reader spend needs a new explicit authorisation and a new ledger, not a withdrawal from V3. The estimate in 5c fits inside $10 but is not authorised by anything I found.
8. **Authority of synthetic corpora.** Corpus H1 README: synthetic, authored by the same agent that wrote the protocol, one family, templated surface variation; `operating-plan-and-rules.md` line 140: "Internal corpora are diagnostic instruments only" (I read only the first sentence). The protocol asks for results in two corpus families before a candidate advances. *Resolution:* label the first study Tier E; plan a second generator family before any claim.
9. **Deletion.** Vision section 7 requires deletion where privacy or retention demands. The canonical store is append-only, a CI guard fails a pull request that deletes or rewrites a log line, and `tools/project_memory` has no delete or redact operation (grep of `tools/project_memory/*.py` found none). *Resolution:* experimental stores live outside `memory/events.jsonl`; for the canonical store specify a tombstone or redaction event type before it is needed, as a separate decision.
10. **Budget unit.** Vision: about 4,000 tokens. Repository: 250 words (corpus H1), 12,000 characters (MCP default), reported words (adapters). *Resolution:* pin one tokenizer-based unit in the new interface and report the conversion.
11. **Novelty.** `docs/research/RELATED_WORK_AND_POSITIONING_2026-08-24.md` records as "clearly not novel": multiple memory types in one system and brain-inspired memory architecture (Microsoft six-mechanism paper, FluxMem, Engram, MemCon). `docs/00-project/related-work-and-novelty.md` concedes structured temporal memory to APEX-MEM. A-MEM-style link expansion was already tried (Entry L). Layered memory, consolidation, forgetting curves and association-based reactivation should be presented as replication or comparison unless the study isolates a specific effect, namely **dormant-until-goal-change reactivation under a fixed budget**, which I did not find tested in the repository (not checked against external literature beyond these notes: UNVERIFIED).
12. **Identifier collision.** See section 4; use V-H1 to V-H5, and prefix new experiment ids so they do not resemble `PMLAB-H1-*`.
13. **Historical drift is real here.** The corpus H1 baseline was not re-run after the corpus repair `cd5c3f4` (before it the 84 probes asked only 24 distinct questions); the re-run changed POISON forbidden-above-gold from 0.25 to 0.0 and DELAYED recall@10 from 0.833 to 1.000 (`baseline-v0.1-rerun-2026-11-01/README.md`). This supports the vision's section 16 requirement: freeze corpus digests with each result and keep the earlier file beside the later one, as was done.
14. **A real testbed is memory-contaminated and nondeterministic** (added 2026-11-01 after the audit of the first real candidate, a live writing agent; facts reported by that audit and its check, not verified here). The agent already injects about 14 ad hoc memory blocks into its prompts, records no prompts or responses, has no run identifier in its journal, and controls neither seed nor temperature. The vision's baseline A (no memory) can therefore only be a harness-level arm on such an agent, and a replay is a re-evaluation, not a reproduction. *Resolution:* the contract carries `capture` and `fidelity`; any real-agent stage is descriptive, read-only and downstream of synthetic results.

## 7. The integration surface today

**Transport and code.** MCP over stdio (`tools/project_memory/server.py`, `SERVER_INFO` name `adaptive-agent-project-memory` version `0.1.0`), CLI fallback (`cli.py`). No network, API key or vector database needed. Storage root is `--root` (default: the repository), with `memory/events.jsonl` canonical, an SQLite FTS5 index under `memory/.index` that is disposable, file locks `.events.lock` and `.index.lock`.

**MCP tools (7 plus one maintenance tool; MEASURED from `server.py`):**

| Tool | Arguments (defaults) | Notes |
|---|---|---|
| `memory_status` | none | counts, index state, schema version |
| `memory_search` | `query` (required); `limit` 1-50 (10); `kinds` (array of exact kinds such as `memory:decision` or `document`); `expand` (true) | FTS5 BM25 over active memories and project documents; `expand` applies `memory/glossary.json` cross-language expansion |
| `memory_context` | `query` (required); `char_budget` 1000-50000 (**12000, unit is characters**); `limit` 1-50 (12); `state_share` 0-1 (0.4) | builds a bundle: current-state summary plus retrieved evidence under the budget; CLI exposes only `--char-budget` |
| `memory_get` | `memory_id` | one record, with whether it is still active |
| `memory_timeline` | `limit` 1-200 (20); `kind` | recent events, newest first |
| `memory_add` | `kind` (enum: candidate, constraint, decision, failure, finding, hypothesis, procedure, question, session), `title`, `summary` required; `body`; `tags`; `source_refs`; `confidence` (unknown, low, medium, high); `status` ("active"); `related_ids`; `valid_from`; `claim_class` (dispositional, state, unclassified) | appends a `create` event |
| `memory_supersede` | `memory_id`, `reason` required; optional `title`, `summary`, `body`, `tags`, `source_refs`, `confidence`, `status`, `supersession_kind` (succession, correction, unclassified), `valid_from` | appends a `supersede` event; error if the memory is already superseded |
| `memory_rebuild_index` | none | rebuilds the disposable index |

CLI commands: `status`, `rebuild`, `search`, `context`, `timeline`, `get`, `add`, `supersede`.

**Budget unit:** characters, applied to the context bundle only; `memory_search` limits by count, not size.

**Record schema v2 (event fields written by `add`):** `schema_version` (2), `id` (`PM-YYYYMMDD-<8 hex>`), `operation` (`create` or `supersede`), `kind`, `title`, `summary`, `body`, `tags`, `source_refs`, `confidence`, `status`, `created_at` (transaction time, set by the store), `valid_from` (valid time; ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ` only), `claim_class`, `supersedes` (id or null), `supersession_kind`, `related_ids`. **`valid_to` and `expired_at` are never stored**; `upcast.derive_temporal_view` derives them from the successor at read time (succession ends `valid_to` at the successor's `valid_from`; correction sets only `expired_at`). Version-1 events upcast through `upcast.py`.

**What an external autonomous agent would still need (facts only):**

1. No way to supply `created_at`; replay of a simulated or historical session cannot set transaction time (`_utc_now()` in `add`).
2. No "as of" parameter on `memory_search` or `memory_context`; `derive_temporal_view` exists in `upcast.py` but is not exposed as a query argument.
3. The `kind` enum has nine project-research values; there is no kind for a raw agent experience, an observation, a goal, a feedback or outcome event, or a trace.
4. `title` and `summary` are required strings; there is no structured payload, no raw-event attachment and no stable external experience id (ids are generated).
5. No goal object and no way to pass a goal or task context to retrieval; only free-text `query`.
6. Retrieval is lexical FTS5 only, plus a glossary; no embeddings (local dense retrieval exists only in `scripts/`, not in the store). The index also covers repository documents, so a clean experimental root must contain nothing else.
7. No budget in tokens; no per-call cost or token report from the store (the arena `Cost` type exists but is not used by the store).
8. No delete, redact, dormant or reactivate operation; supersession is the only state change, and only an active memory can be superseded.
9. No batch write and no concurrent-session guarantee beyond file locks; no authentication or multi-tenant separation (separation is by `--root`).
10. No usage telemetry (retrieved, exposed, referenced, outcome); the schemas for it live in `data/lab/pmlab-future-utility-v0/telemetry-event-v0.1.schema.json` but are not emitted by the server.
11. No interface contract to the arena adapter: `scripts/arena/adapter.py` wraps third-party systems; nothing wraps `MemoryStore`.

## 8. What I could not verify

- The live writing agent, its data and its interface. Nothing in this repository describes it. Its maintainers audited it on 2026-11-01 (the report sits in that agent's folder, outside this repository), and an independent check of that audit found it accurate on the code and wrong in places, which the audit's author has since corrected. Reported by the audit and not verified by this project: the agent records no prompts or responses, its main journal has no run identifier, its environment is not deterministic, about 78 days of history exist, and about 14 ad hoc memory blocks are already in its prompts. At best it is a read-only re-evaluation target.
- Anything beyond the repository's own related-work notes about prior art for dormant-association reactivation.
- The code location of "Reflection Stage 1"; I relied on `memory/CURRENT_STATE.md`.
- The exact content of `PMLAB-ASSOC-E1..E3` corpora and gold construction beyond the registry and ledger text; I did not open their scripts.
- Per-family token-budget figures for the baseline (only overall means are in `results.json` summaries; I did not compute per-family means).
- Whether the `k` in the dense probe's "gold reached the context" is a depth or a 250-word fill: the script uses a 250-word fill (`DEFAULT_TOKEN_BUDGET`), so it is not directly comparable to recall@k.
- Whether the committed tests cover `tools/project_memory` server behaviour end to end; the full suite passed in a scratch clone but I read no server test.
- The costs for any model other than the DeepSeek models used in the ledger, and any human review effort.
- Uncommitted edits other people may be making in the worktree (`README.md`, ledger, two research documents showed as modified when I started); I judged by the committed content at `e306bf2`.
