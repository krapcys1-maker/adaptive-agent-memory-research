# Event-Time Resolution at Extraction — Calibration v1

Capability calibration only (per the explicit scope: `E2 CALIBRATION-ONLY`, hard new spend cap $0.03). Not a benchmark run. Not approval for full E2.

Pre-registration: `PM-20260824-e9f15438`. Data: [`calibration.json`](../../data/lab/arena/event-time-resolution-calibration-v1/calibration.json). Patch: [`EVENT_TIME_RESOLUTION_AT_EXTRACTION.patch`](../../data/lab/arena/event-time-resolution-calibration-v1/vendor-patch/EVENT_TIME_RESOLUTION_AT_EXTRACTION.patch), manifest with baseline/patched SHA256 in the same directory. Parent commit: `d82afa42c1997b7a3be79e0a02a205e80eeb81bc`.

## Question

Given a correct per-session `reference_date` AND an explicit instruction to resolve relative temporal expressions against it, does Mem0 1.0.6's fact-extraction step represent `EVENT_TIME` as an absolute date? Isolated against a `reference_date`-only CONTROL, which prior calibration ([`calibration-per-session-reference-date.json`](../../data/lab/arena/base-plus-x-v1/calibration-per-session-reference-date.json)) already showed is inert on its own.

## Treatment and control

- **CONTROL:** correct `reference_date`, `resolve_relative_time=False` — byte-identical to the already-calibrated-inert `PER_SESSION_REFERENCE_DATE_AT_EXTRACTION` treatment.
- **TREATMENT:** same `reference_date`, `resolve_relative_time=True` — adds exactly one instruction bullet immediately after the `"Today's date is ..."` line: *"When a fact contains a relative time expression such as 'today', 'yesterday', 'tomorrow', 'last month', or 'next year', resolve it against the reference date above and store the fact with the corresponding absolute date whenever this can be done unambiguously. Do not invent a date when the text does not provide enough temporal information."*

Both arms call `get_fact_retrieval_messages()` + a single `llm.generate_response()` directly — the exact fact-retrieval call shape `memory.add()` uses internally (`main.py:449-454`) — with no update-memory-decision call, no dedup, no vector-store write, no retrieval. 1 call per (case, arm), 10 calls total. Confirmed via `tests/test_mem0_event_time_resolution_patch.py` (no LLM call) that CONTROL is byte-identical to the prior treatment and that TREATMENT differs from CONTROL by exactly one inserted line.

## Cost gate (before the first paid call)

Mem0 1.0.6's `_add_to_vector_store` makes **two** model calls per `add()` (extraction + a separate update-memory-decision call) — checked directly in code before projecting cost, per the required "recompute if the real implementation does more than one call" rule. This calibration deliberately calls only the extraction step directly, bypassing the second call entirely (out of scope: no dedup/retrieval changes), so the real call count is 1 per (case, arm) = **10 total**, matching the pre-registered "maximum 10" call discipline exactly.

Projected (from the prior calibration's measured per-call cost): ~10 calls, ~$0.008 projected spend, cap $0.03, ~$0.022 headroom. Scope `e2-calib-` confirmed at $0 before the first call.

## Results

| case | reference_date | expected | CONTROL facts | TREATMENT facts | changed? |
|---|---|---|---|---|---|
| CASE1_TODAY | 2022-11-17 | 2022-11-17 | "...shopping **today**..." | "...shopping **today**..." | NO |
| CASE2_YESTERDAY | 2023-01-28 | 2023-01-27 | "...appointment **yesterday**..." | "...appointment **yesterday**..." | NO |
| CASE3_NEXT_YEAR | 2022-06-15 | 2023 | "...marathon **next year**" | "...marathon **next year**" | NO |
| CASE4_LAST_MONTH | 2023-03-10 | 2023-02 | "...dog **last month**..." | "...dog **last month**..." | NO |
| CASE5_NO_DATE | 2023-02-10 | none (negative control) | 2 non-temporal facts | identical 2 facts | NO |

**Every parsed fact is byte-identical between CONTROL and TREATMENT in all 5 cases.** The only raw-response difference anywhere is one cosmetic leading whitespace character in CASE5's CONTROL response, before JSON parsing — the parsed `facts` lists are identical. No absolute date was introduced in any of the four date-bearing cases; every relative expression ("today", "yesterday", "next year", "last month") is preserved verbatim, exactly as in the earlier `PER_SESSION_REFERENCE_DATE_AT_EXTRACTION`-only calibration.

## Primary metrics

- `CONTROL_RESOLVED = 0/4`
- `TREATMENT_RESOLVED = 0/4`
- `FABRICATED_DATE_ON_NONE = NO` (moot — nothing changed to fabricate)
- `CONTROL_VS_TREATMENT_TEXT_CHANGED = NO` for all 5 cases
- `RELATIVE_EXPRESSION_PRESERVED = YES` for all 4 date-bearing cases
- `ABSOLUTE_DATE_INTRODUCED = NO` for all cases
- `SESSION_TIME_OVERRIDES_EVENT_TIME = UNRESOLVED` — no case produced any absolute event date to check for an override; this calibration's design (isolated relative-expression cases, no competing in-text explicit date) never exercised that specific risk pathway. It remains untested, not cleared.

## Verdict: `E2_CALIBRATION_FAIL`

Both independent trigger conditions from the pre-registered gate hold: `resolved_count = 0/4` (≤1/4 threshold), **and** the explicit instruction changed extraction behavior in 0 of 5 cases. Per the pre-registered discipline, this means:

**"Mem0 extraction cannot currently be induced to represent resolved EVENT_TIME under this minimal instruction-only treatment."**

Not "temporal grounding is impossible" — only that this specific, minimal, instruction-only intervention on top of a correct reference date does not move the model's behavior at all, on this model (`deepseek-chat`) and this prompt structure.

## What this does and does not mean

This calibration measured whether a bare instruction bullet changes behavior — it did not. It does **not** establish that no instruction could work: a more directive phrasing, a worked few-shot example, or a structural change (e.g., asking the model to output a separate `resolved_date` field rather than editing the fact string) might behave differently. None of those were tried, per the explicit "if calibration fails: STOP, do not re-tune wording, do not add few-shots" discipline (`PM-20260824-e9f15438`). A few-shot or restructured variant would need to be separately approved as a new, named treatment.

## Full E2 eligibility

**`NOT_ELIGIBLE`.** `EVENT_TIME_RESOLUTION_AT_EXTRACTION`, as calibrated here, does not clear the capability bar a full E2 benchmark run would need to be worth its cost. This closes the specific mechanistic hope raised by [`TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md`](TEMPORAL_ALIGNMENT_AND_DISTRACTION_ARCHAEOLOGY_V1.md)'s `E2_CALIBRATION_JUSTIFIED` label under this specific minimal instruction design — it does not close the underlying `00ca467f`-style session-vs-event-time negative-transfer problem, which remains open and undesigned-for.

## Spend

Total: **$0.002811** against a $0.03 hard cap (10 calls, extraction-only, no dedup/update-decision call). Scope `e2-calib-`, verified $0 before the first call.
