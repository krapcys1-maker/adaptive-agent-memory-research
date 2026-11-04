# Matched local/API reader transfer — 4 November 2026

**Decision:** the existing typed-memory mechanism transfers to a stronger local reader and the authorized Flash API in this small offline task. Qwen 14B is adequate here; an API is useful as a transfer check, not required for every iteration. Increasing reader strength does **not** fix the ordinary retrieval path's paraphrase misses. Next work should target text-to-slot routing and typed capture under realistic writing prompts.

This is eight authored semantic cases, not a production validation or independent population sample. There are sixteen persisted writer chains, but both writer seeds selected the same value per field. No NIE source, personality, prompts, filters or deployment changed. No model was asked to plan the project, propose ideas or judge the result; Codex owns implementation, auditing, interpretation and next-step decisions.

## Method and preserved evidence

[PLAN.md](PLAN.md), [config.json](config.json), the [usage policy](../../../docs/00-project/reader-model-usage-policy-2026-11-04.md), clients and reconstruction auditor were committed before inference at `272bf1ba56eb167258112efb9887551805bdc92e`. The previous plan's model-critique phase was removed before any generation following the owner's clarification. There were **400 new calls: 200 Qwen 14B and 200 Flash; zero planning calls, writer regeneration, retries or fallback calls**.

The journals and questions come from the [7B pilot](../nie-local-reader-v1/README.md), run-002. Each backend makes 192 primary calls (eight slots × two chains × four arms × three turns) plus eight controls/canaries. The paraphrase starts a fresh conversation; pressure sees the paraphrase exchange within its arm. Every primary turn reloads its persisted journal. Controller seeds are recorded for both readers; no unsupported seed parameter is sent to the API. Ollama uses temperature 0, context 4096, max 64 tokens; the API uses temperature 0, max 64 tokens, JSON-object output and explicitly disabled thinking. These transport settings do not establish cross-service determinism.

| Arm | Evidence and output |
| --- | --- |
| N | No memory; abstention is appropriate when the fictional fact is absent |
| K | Ordinary lexical retrieval with the existing profile; raw answer |
| O | Oracle single correct note; raw answer, a diagnostic upper condition |
| V | Supplied slot cue, retrieved typed evidence and existing deterministic output contract |

## Results

Each cell is **raw agreement → delivered agreement**, out of 48 turns. The 7B reference was not rerun; its primary scores were recomputed from preserved final responses and shown evidence.

| Reader | N | K | O | V | V complete chains |
| --- | --- | --- | --- | --- | --- |
| Qwen 7B, previous run | 0 → 0 | 16 → 16 | 36 → 36 | 36 → 48 | 16/16 |
| Qwen 14B, new local run | 0 → 0 | 26 → 26 | 48 → 48 | 48 → 48 | 16/16 |
| DeepSeek V4.1 Flash, new API run | 0 → 0 | 32 → 32 | 48 → 48 | 46 → 48 | 16/16 |

All three executions show the target on **32/48 K turns**, with **0/16 paraphrase hits**. Accordingly K completes zero three-turn chains even for Flash. With memory shown on the pressure turn, K raw agreement is 0/16 for 7B, 10/16 for 14B and 16/16 for Flash. Better reading can help when evidence arrives; it cannot recover these hidden facts from missing retrieval.

In V, 14B needs no correction. Flash needs two UNKNOWN corrections, both the same Sunday-tea case under pressure in the repeated writer chains. They are **not two independent failures or invented wrong values**. The contract uses only shown typed claims, never scoring gold. A 48/48 delivered endpoint therefore does not mean 48 independently correct raw model answers, nor demonstrate that a guard is necessary for every reader: local 14B already attains 48/48 raw here.

No-memory raw responses are UNKNOWN on 42/48 turns for 14B (six unsupported values) and 48/48 for Flash. In K the new readers emit no wrong values; their remaining answers are UNKNOWN. Both new backends pass all eight controls: three positive tokens, no-record, future-only, actually exposed two-way conflict and two repeated canaries. Raw negative-control answers are also UNKNOWN. The two canaries are byte-identical to the first response within each backend; that small check is not a general determinism guarantee.

## Audit, resources and reproducibility

The [reconstruction auditor](../../../scripts/audit_reader_model_compare_v1.py) rebuilds all **200 requests and 192 primary contexts, histories, guards and scores per new backend**. It rejects forged contexts, answers, summaries, hashes, controls and duplicate records in regression tests. The [report builder](../../../scripts/report_reader_model_compare_v1.py) independently accounts for the previous raw/delivered endpoint, matches **all 192 questions and evidence contexts per new backend** to the 7B reference, and rechecks the cumulative API ledger. Histories after answers differ across readers by design; matching contexts is not a claim that all later conversation messages are identical.

Artifacts: [comparison and input digests](comparison.json), [local run](runs/local14b/), [Flash run](runs/flash/), [permanent API reservations/usage](api-spend-ledger.jsonl). Final responses are retained; credentials, authorization headers and hidden thinking are absent.

| Resource | Qwen 14B | Flash |
| --- | --- | --- |
| Identity | `qwen2.5:14b-instruct`, Q4_K_M, digest `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6` | requested/returned `deepseek-flash`; before/after metadata name `DeepSeek-V4.1-Flash` |
| Phase wall time | 118.56 s, including first-call load | 207.14 s |
| Median completion wall time | 0.235 s | 1.0075 s |
| Input / output tokens | 35,346 / 1,348 | 37,681 / 1,227 |
| API accounting | $0 API | 200 permanent reserves: $0.800; usage-priced upper estimate **$0.012777**, zero unknown-usage attempts; task ceiling $1 |

Tokenizers and environments differ. These timings are observations on this machine/service, not speed rankings for other tasks. The API estimate uses verified peak uncached rates ($0.30/M input, $1.20/M output); reservations are conservative bounds and neither number is an account invoice. Only official Flash is permitted, with preflight/returned-model checks and no Pro fallback. The provider's dated pricing page identifies the canonical alias as V4.1 Flash 1017, while the actual metadata provides the less specific name above. The alias does not pin hosted weights. The owned local model was unloaded after execution.

Offline checks (no model calls):

```text
python scripts/audit_reader_model_compare_v1.py data/lab/reader-model-compare-v1/runs/local14b
python scripts/audit_reader_model_compare_v1.py data/lab/reader-model-compare-v1/runs/flash
python scripts/report_reader_model_compare_v1.py
python -m pytest tests/test_reader_model_compare_v1.py -q
python tasks.py check
```

## Remaining boundary and next decision

The supplied slot cue and well-formed typed writer remain assumptions. This result does not validate capture from free prose, unseen fields, negation, canonical-card conflicts, revisions, true unknown-slot versus retrieval-miss classification, actual NIE prompts or downstream writing quality. UNKNOWN is an internal recall result; retain NIE's improvisation-and-write-back policy. A retrieval miss must not overwrite an existing fact as though it were a new one.

The next useful engineering step is a separately versioned offline capture/routing boundary: keep emitted fiction plus provenance, obtain a candidate typed claim from the actual writing format, and measure routing/capture errors separately from retrieval and answer errors. Start locally; use only approved Flash when a transfer check resolves a concrete uncertainty. Do not lower global kernel thresholds or modify NIE's personality on the strength of these closed-slot results. P2's previous failure, LifeSim's four development validity failures and R1's judge limitation remain unchanged.
