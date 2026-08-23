# ProsusAI/MemEval repository audit v0

Status: static audit complete; benchmark not executed (requires paid OpenAI API calls); catalog row corrected

Audited repository: [ProsusAI/MemEval](https://github.com/ProsusAI/MemEval)

Revision: `807ae6d7d8a5b76f6fe964d5a581d96c036e2ac4` (`main`, authored 2026-03-16)

License: Apache-2.0 with `NOTICE` (MIH AI B.V.)

Audit date: 2026-08-23

## Disposition

The hypothesis in issue #35 is confirmed: **MemEval is a comparison harness, not a
dataset.** It runs nine memory systems over two existing benchmarks while holding
the answering model, the embedder, the answer decoding parameters and the scoring
pipeline constant, and it accounts for token cost end to end across ingestion,
retrieval and answering.

That fairness property is the one the benchmark ladder needs and would otherwise
have to build, so the previous filing was wrong in all three of its fields:
`governance` (it is not a governance project), priority `B` (it belongs with the
LongMemEval and MemBase rows, which are `A`), and download `no`.

It was filed under `governance` on the strength of its name, next to four other
repositories whose names also contain "MemEval". The name is the only thing they
share.

Not adopted wholesale. The constants below are repeated in each adapter rather
than enforced by the registry, so the fairness property is a convention this
project would have to re-verify per adapter rather than inherit.

## Claimed

From `README.md`, as written:

- "Fair evaluation framework for agent memory".
- Standardizes "same LLM, same embeddings, same scoring pipeline, and end-to-end
  token cost tracking across ingestion, retrieval, and answer generation".
- "ships with 9 memory systems and 2 benchmarks (LoCoMo and LongMemEval)".
- Evaluation "combines token F1 with LLM-as-judge scores, with per-category
  breakdowns".
- Reported `Tokens` "excludes embedding and judge calls".
- Introduces PropMem, claimed as "the strongest measured quality-to-cost tradeoff
  in our runs".

Results tables are **self-reported**: the authors wrote the harness, the PropMem
system it ranks first, and the report. Nothing here reproduces them.

## Verified from the code

Each item below was read at the revision above. Nothing in this section rests on
the README.

### 1. Which memory systems does it integrate today?

**Nine**, counted as modules in `src/agents_memory/systems/` that export both
`SYSTEM_INFO` and `run`, which is the registration contract in
`systems/__init__.py`:

| module | architecture, per its own `SYSTEM_INFO` |
| --- | --- |
| `fullcontext.py` | full conversation in prompt (upper bound) |
| `graphiti.py` | temporal knowledge graph (Kuzu embedded) |
| `hindsight.py` | biomimetic memory, multi-strategy retrieval (TEMPR) |
| `mem0.py` | memory extraction + vector search |
| `memory_r1.py` | two-agent RL, SFT+GRPO on Qwen-2.5-7B |
| `memu.py` | memory service with file-based memorize |
| `openclaw.py` | hybrid BM25 + vector chunk retrieval |
| `propmem.py` | proposition-based entity-centric retrieval |
| `simplemem.py` | multi-round retrieval with parallel processing |

Agrees with the README's nine. Registration is by directory scan
(`pkgutil.iter_modules`), so the count is whatever is present, not a declared
list.

### 2. What does it hold constant?

- **Answering LLM** — one `--llm-model` (default `gpt-4.1`,
  `scripts/run_full_benchmark.py:186`) threaded into every adapter's `run()` and
  recorded in the result payload (`:323`, `:328`).
- **Embedder** — `text-embedding-3-small`, in `mem0.py:48`, `memu.py:44`,
  `openclaw.py:36` and `:46`, `simplemem.py:36` and `:48`, and the documented
  `hindsight.py:12` container environment.
- **Answer decoding** — `max_tokens=50, temperature=0.1` on the final answer call:
  `fullcontext.py:73-74`, `hindsight.py:152-153`, `mem0.py:101-102`, and the same
  pair in the remaining adapters.
- **Scoring** — every system goes through the same `_qa_results_async` in
  `systems/_helpers.py`: `compute_f1` against ground truth for all, then either the
  generic three-dimension judge or the native LongMemEval binary-accuracy judge
  (`judge_fn="longmemeval"`), selected per benchmark rather than per system.
- **Data** — the same conversations and QA pairs, loaded by the benchmark module.

**Constants are per-adapter, not enforced.** Each value above is a literal
repeated in each file. `systems/__init__.py` registers any module exporting
`SYSTEM_INFO` and `run`; it validates neither. An adapter using a different
embedder or temperature would register and run silently.

### 3. Which datasets?

**Both LongMemEval and LoCoMo**, and only those two.
`benchmarks/locomo.py:12-18` declares `"LoCoMo"`, 10 conversations, 1986 QA pairs,
5 categories. `benchmarks/longmemeval.py:37-43` declares `"LongMemEval"`, 500
questions, 6 categories, variable-size haystacks. `benchmarks/__init__.py`
discovers them the same way `systems/` does, and **silently skips modules whose
dependencies are missing** (`except ImportError: continue`) — so an incomplete
install presents as a shorter benchmark list rather than an error.

### 4. Token cost end to end, or answer quality only?

**End to end, by two independent mechanisms**, which is the part worth knowing.

`token_tracker.py` monkey-patches the OpenAI client — chat completions, responses,
sync, async, parse and streaming — and accumulates prompt and completion tokens
per model. Because it patches the client rather than instrumenting call sites, it
counts ingestion, retrieval and answering alike, which is what makes the README's
end-to-end claim true.

Local models are not on that path. `systems/memory_r1.py` runs a fine-tuned
Qwen2.5-7B and imports `training/memory_r1/local_token_tracker` (`:64`), a second
tracker that counts from the tokenizer instead. Its own docstring states the split.

So the harness measures cost, not only quality — but by two trackers, neither of
which is a general interception point.

### 5. What does it not control for?

Listed so this project does not inherit them silently:

- **Retrieval depth.** No shared top-k. `mem0.py:80` passes `limit=20`;
  `hindsight.py:128-129` passes `budget="high", max_tokens=4096`. Token totals are
  comparable across systems; the amount of context each retrieved is not.
- **The answering model, for one system.** `memory_r1.py:31` pins
  `Qwen/Qwen2.5-7B-Instruct` and generates locally (`:107`, `:163`), so
  `--llm-model` does not apply to it. The "same LLM" property has an exception the
  README does not name.
- **Token accounting for any future non-OpenAI adapter.** The two trackers cover
  the OpenAI SDK and this one local model. An adapter calling a different provider
  or a self-hosted server would register, run, and report approximately zero
  tokens — reading as free rather than as unmeasured.
- **Judge model drift.** The judge defaults are environment-overridable and differ
  between judges: `JUDGE_MODEL` defaults to `gpt-5.2` (`evaluation.py:39`) while
  `LONGMEMEVAL_JUDGE_MODEL` defaults to `gpt-4o` (`:222`). Judge scores are only
  comparable within one run.
- **Adapter conformance.** Nothing checks that a registered system uses the shared
  constants.

## Where claimed and verified diverge

They agree on the system count, the two benchmarks, the constants, the scoring
combination, and end-to-end token accounting.

Two things the README asserts that the code qualifies:

- "same LLM" is true of eight of the nine systems; `memory_r1` runs a local model.
- "same embeddings" is true as written but is a convention repeated per adapter,
  not a property the framework enforces.

One silence worth recording: the README says token figures exclude embedding and
judge calls, which is accurate and honest, but nothing states that a non-OpenAI
adapter would contribute nothing to the totals.

## Catalog changes

- `data/catalogs/repository-revisions.csv` — pinned at
  `807ae6d7d8a5b76f6fe964d5a581d96c036e2ac4`, status
  `available-apache-2-static-audit-not-executed`.
- `data/catalogs/repositories-seed.csv` — `governance,B,no` →
  `comparison-harness,A,yes`, primary use `cross-system memory comparison rig`,
  and the to-do note replaced with what the inspection found.

## Observation, not changed here

`zjunlp/MemBase` (seed row 22) is catalogued `benchmark` with the note "Modern
LongMemEval and LoCoMo harness". If that description is right, it is a harness
filed under the category of the things it runs — the same conflation corrected
here. Out of scope for this issue; worth its own inspection.
