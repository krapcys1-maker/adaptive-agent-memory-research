# Matched reader transfer and model critiques

Fixed execution plan before generation. This is a bounded comparison of the existing typed-memory pilot, not a production test or new independent benchmark. The owner authorized local models and DeepSeek V4.1 Flash for tests, planning and candidate ideas. Pro is prohibited.

## Fixed source cohort

Reuse the **sixteen valid persisted journals** and eight cases from `data/lab/nie-local-reader-v1/run-002` at main `f6cce08f97f58b7fb78495889c81a1ee8580aff2`. Do not generate new writer values or rerun Qwen 7B. Its measured raw/delivered results are the reference, with explicit context/history matching checks. This holds the writer and memory corpus fixed across readers; it does not remove the limitations of eight authored fields, repeated seeds or fixture-supplied routing.

Compare two additional readers sequentially within each backend:

- Local Qwen2.5 14B Instruct, Q4_K_M, digest `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6`, Ollama on loopback only; context 4096, temperature 0, max 64 generated tokens. No other local model is loaded at the same time; unload only the model loaded by this run.
- Official DeepSeek endpoint, request ID **`deepseek-flash` only**, metadata must name V4.1 Flash. Non-thinking mode explicitly disabled, temperature 0, max 64 output tokens, ordinary JSON object output and no tools/search. Record service-returned model/fingerprint and usage. Do not assume the API supports Ollama's seed or provides bitwise determinism.

## Execution and metrics

Use the existing N/K/O/V definitions, source statements, direct/paraphrase/pressure questions, per-arm histories and reset before the paraphrase. Every turn reloads its journal from disk. V receives only actually shown typed evidence; no scoring gold. Use the repaired conflict control with seven unrelated distractors, alongside three positive controls, no-record and future-only controls, then two repeated canaries.

Exactly **200 planned reader calls per backend**: 192 primary observations and eight controls/canaries. No writer calls, automatic retries, model fallback, threshold/prompt changes or partial-run mixing. Record retrieval IDs/context separately from raw and delivered responses. Compare exact counts and chain agreement, plus abstentions, wrong values, corrections, control coverage, latency and token usage. Treat the 7B reference and new readers as different executions, with independent histories; do not pool them as independent populations.

After both readers finish, ask each for **one critique/planning response** (maximum 512 output tokens) using only public aggregate results, limitations and the owner's model policy. Request up to three concrete ideas with a falsification test and failure risk. Store them as model suggestions, not facts or automatic implementation instructions. This is a separate purpose and is excluded from benchmark counts.

## Resource and identity limits

- 201 planned generation calls per new model, maximum 205, at most 1800 seconds per phase. Total new planned calls 402; do not repeat the earlier 241-call pilot.
- API task cap **$1.00 cumulative reserved budget** and 205 paid attempts across all phases. Before each HTTP inference, permanently reserve $0.004 in a new append-only task ledger; never release reservations for a retry. Refuse more than four messages, more than 6000 UTF-8 message bytes or more than 512 output tokens. At verified peak upper rates ($0.30/M input, $1.20/M output), the supplied-byte token bound plus 4096+256-per-message framing allowance is below that reserve. Thinking is disabled, tools/search are absent. Record usage-priced upper estimates separately from reservations; neither is an account invoice. Any usage anomaly or unknown outcome stops the run while retaining its reservation.
- Credentials are loaded through the existing local helper, held only in process memory and never included in configs, requests recorded on disk, console output or error bodies. Connect only to `https://api.deepseek.com`; refuse redirects and all other paid model IDs before loading a key.
- Check the installed/advertised model before the first call and after the run. Preserve full execution source/config/input digests and old output files. No source edits after a run starts; write results to new files. No live agent prompts, code or deployment changes.

## Decision

Report whether the mechanism transfers across readers and whether a stronger local reader removes any raw failure. A tie or reversal is a valid result; the purpose is to decide where an API is useful and where local execution is enough. Retain the current typed-memory mechanism only as a candidate under its supplied-routing/structured-writer assumptions. The next product boundary remains real writing-format capture/routing; the comparison cannot validate that untested boundary.

API identity/pricing references: [model list](https://api-docs.deepseek.com/api/list-models/), [versions and prices](https://api-docs.deepseek.com/quick_start/pricing/), [thinking toggle](https://api-docs.deepseek.com/guides/thinking_mode/).
