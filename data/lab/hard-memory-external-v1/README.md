# Hard external memory test: ordinary retrieval fails

**The existing ordinary kernel path scores 0/100 exact answers on both readers.** The frozen self-set readiness target was 80/100 on Flash K. It is not met. That target was not calibrated as an industry standard; the [audit](../../../docs/00-project/project-delivery-audit-2026-11-04.md) records the authors' much lower published FC-MH results under different settings, which cannot be used as a direct comparison. The previous eight-slot 48/48 delivered result does not establish a working general memory system, superiority to memory companies or recall over centuries.

This is the **entire 100-question `factconsolidation_mh_262k` variant** of official [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench), not a self-authored easy fixture or a sample selected for success. It remains one shared public history, not 100 independent histories. This offline raw-line adapter differs from the official incremental-agent protocol; these are not comparable full-agent leaderboard scores.

## What was frozen and tested

[Plan](PLAN.md), [configuration](config.json), [runner/scorer](../../../scripts/hard_memory_external_v1.py) and tests were committed at `6a3a61c` before preparation/inference. The [prepared input identities](preparation.json) were committed at `501fb95`. Source: dataset revision `7ea066982b140a19337e17e60d45d4076e042faf`, conflict-resolution parquet SHA-256 `24d5c3f09ce0ce15625cb9f8a98f44f0d864ca6c94d7b4ad04eb697ca3a5ff45`.

The archive has **1,118,123 characters and 18,333 stored lines**. All raw assertions and their order are retained. No correct slot, evidence location, chain, current/stale annotation, gold-derived entity, typed claim or answer correction is available to the reader/retriever. A separate preparation process writes archive/questions and a separate gold file. Generation reads only gold-free persisted packets; regression tests trap and reject any attempt to open gold.

N is no memory (local only). K uses the shipped 0.2.0 lexical thresholds and k=3. B uses the identical frozen kernel BM25 implementation with an unlocked diagnostic profile and up to 24 candidates. Both have a 4500-byte evidence ceiling. The offline deadline is infinite to remove scheduling failures, so this is not a shipped latency test. Retained records appear in source order and the prompt specifies that later counterfactual assertions override earlier ones. Every completion is a fresh conversation; the parsed model answer is scored without repair.

## Primary results

| Reader / arm | Exact answers | Mean token F1 | UNKNOWN | Other wrong values | Malformed/truncated | Nonempty context |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen 14B N | 0/100 | 0.000 | 100 | 0 | 0 | 0/100 |
| Qwen 14B K | **0/100** | 0.000 | 99 | 1 | 0 | 70/100 |
| Qwen 14B B | 1/100 | 0.015 | 92 | 7 | 0 | 100/100 |
| DeepSeek V4.1 Flash K | **0/100** | 0.000 | 90 | 10 | 0 | 70/100 |
| DeepSeek V4.1 Flash B | 4/100 | 0.040 | 83 | 13 | 0 | 100/100 |

The endpoint is normalized exact match over official aliases, not retrieval success. Lowercase, ASCII punctuation removal, article removal and whitespace collapse follow the official scorer's normalization. Token F1 and substring match are separate diagnostics; substring success never changes a failed exact match. All 100 questions are answerable according to the source. UNKNOWN can be an appropriate reader reaction to insufficient **shown** evidence while still being an end-to-end failure to answer an answerable question. The local no-memory arm does not measure an API no-memory baseline.

For scale only, nominal 95% Wilson intervals are 0.0–3.7% for 0/100, 0.2–5.4% for 1/100 and 1.6–9.8% for 4/100. They do not establish independent-population uncertainty: questions share one history and are public. The observed full-variant counts are the decision basis.

## Failures, controls and provenance

The original Flash run completed 203 calls: 200 primary plus three successful controls. The first local run stopped on its first positive control: it produced an incorrect JSON key, an unrelated description and reached the output limit. It had called **zero primary questions**. That failed run was retained and unloaded. A [separate local-only control amendment](LOCAL_CONTROL_AMENDMENT.md), frozen at `288e8cb` before reading benchmark outputs/gold, reused the already executed control prompt/seed from PR #102/#103. Primary packets, prompts, seeds and settings remained unchanged. The amended local run completed 303 calls and all controls. Including the failed control, v1 used **304 local and 203 paid calls**, within the original 305/205 caps.

Raw hashes were committed before gold joins: [original Flash](flash-raw-freeze.json) and [failed local](local-failed-raw-freeze.json) at `288e8cb`, [amended local](local-control-v2-raw-freeze.json) at `02e38f3`. The scorer validates committed freezes, complete denominators, exact request messages/settings and raw-versus-saved answer identity. Public content-free per-question scores: [Flash](flash-scores.json), [local](local-scores.json). Full packets, prompts, final responses and source data remain in the external local evidence directory. No old result or frozen kernel was edited to obtain a pass.

API requests/returned identities are exclusively `deepseek-flash`; before/after advertised name is `DeepSeek-V4.1-Flash`, with thinking disabled and no fallback or retry. The cumulative hard-task ledger records **203 permanent reservations, $0.812**, usage-priced peak/uncached upper estimate **$0.025240**, zero unknown-usage attempts, against the declared $1 ceiling. This is an estimate and reservation bound, not an account invoice. The PR #103 budget/ledger remains separate and unchanged. Local execution uses pinned Qwen2.5 14B Q4_K_M and costs $0 API.

## Diagnosis and continuing repair

K supplies no context for 30/100 questions. Simply unlocking ranking is insufficient: B supplies some text for all 100 but answers only 1–4. Post-run inspection of the first three source-order cases shows an earlier relation in the shown evidence while the next entity/relation needed by the multi-hop question is absent. This is a concrete diagnosis from inspected cases, not a verified cause classification for all 100 failures. Gold answer phrases exist somewhere in the source archive for all 100 questions, which alone does not prove that the entire supporting chain is retrievable or unambiguous.

The separately frozen [local iterative follow-up](../hard-memory-iterative-v1/PLAN.md) tests bounded read/search rounds without adding gold routing, inferred current labels or answer correction. It uses these same spent public questions after diagnosis and must be reported as post-hoc development. An improvement cannot replace the original failed result or establish external transfer. Its own execution record reports the eventual outcome.

**Audit addendum:** the completed iterative follow-up reached only [4/100](../hard-memory-iterative-v1/README.md), after 402 primary rounds. Two [post-hoc evidence-complete controls](AUDIT_CONTROLS.md), using the last two paid slots in the original task cap, scored [1/2](audit-controls-scores.json). Therefore an exclusively retrieval-based explanation was premature: representation, prompt and reader reasoning remain possible causes. The cumulative [same-task ledger](api-ledger.jsonl) now has **205 attempts, $0.820 permanent reservations and $0.025397 usage-priced upper estimate**, with zero unknown usage. The original 203-call run's recorded completion/budget remains unchanged as historical evidence. The [project audit](../../../docs/00-project/project-delivery-audit-2026-11-04.md) explains why this module/adapter result is not the whole project's score.

## Reproduction and remaining limits

Run software checks without inference:

```text
python -m pytest tests/test_hard_memory_external_v1.py tests/test_hard_memory_iterative_v1.py -q
python tasks.py check
```

Real execution needs the externally downloaded pinned parquet (`pyarrow` is only needed at preparation), the declared installed reader or authorized API key, and **new** output directories. The original runner's scoring CLI expects an absolute `--raw-freeze` path; do not edit its frozen source to adjust that invocation. Source data is fetched by pinned revision, never by executing downloaded pickle or benchmark scripts with unreviewed model defaults.

This measures a raw-line storage/retrieval adapter and readers, not a complete agent's learning, forgetting, free-prose capture, long-term operational durability, NIE production writing or comparison with commercial memory services. No sealed internal confirmation data was opened. The [verified GitHub benchmark selection](../../../docs/05-benchmarks/hard-external-benchmark-selection-2026-11-04.md) also covers BEAM-10M, LongMemEval-V2 and MemoryArena; downloaded or inspected suites are not relabelled as executed.
