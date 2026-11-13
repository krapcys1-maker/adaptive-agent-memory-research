# Complete BEAM10M data boundary — no memory score yet

The first external-comparison preparation stage is complete: **all10pinned repository conversations,187,734messages and200probes**,20per ability across10abilities. Reader-facing questions/history are separate from evaluator-only answers, rubrics, reasoning and supporting-source annotations. This is a format/scale result, **not executed memory performance, independent confirmation or an official BEAM leaderboard result**.

## Provenance and preserved failure

- Official [BEAM repository](https://github.com/mohammadtavakoli78/BEAM), snapshot `b2da22eac88bb0874c64665f13457eb99835774a`.20selected JSON files total471,872,306bytes; [download receipt](download-receipt.json) verifies every pinned Git blob/size plus SHA-256. Source-only download plan was declared privately before fetching, capped600MB/600seconds, no automatic retry; two cached files were copied and the original cache was not changed. Source data and prepared text remain private, outside Git. Code licence and dataset rights remain distinct; no dataset content is redistributed here.
- The [upstream inference loader](https://github.com/mohammadtavakoli78/BEAM/blob/b2da22eac88bb0874c64665f13457eb99835774a/src/answer_probing_questions/answer_generation.py#L170) prefers `chat_trunecated.json` when present. We use that explicit selection; the tier name is not a new tokenizer measurement.
- V1code/plan `fc5429b` succeeded on the original one-conversation cache, then rejected an explicit unknown/null time anchor in conversation7 during full preparation. [Failure retained](failed-preparation.json), old script/tests/result unchanged. V2code/plan `24432f2` was committed before successful full preparation and accepts explicit null without guessing a time. [Plan](PLAN.md), [preparation/source identities](preparation.json).

## What was verified

[Offline reconstruction](artifact-audit.json) checks every187,734original message, role, raw time anchor and provenance location plus all200question/annotation pairs. All match. Source roles:93,868user and93,866assistant. Raw time anchors:909strings,186,824absent,1explicit null. Stream sequence is not a calendar or asserted fact validity.

Reader questions have exactly opaqueID/conversationID/question. Construction-only fields (187,734internalIDs,70,445indexes,93,868question-type entries) remain in audit metadata, never the reader projection. Evaluation annotations remain in a separate directory. All200probes are used; none selected by model success or expected value. Existing public-data/pretraining/prior-exposure limits remain; this is not a witnessed sealed split.

Six focused tests pass: projection boundaries, missing-message/ability failures, partial/full coverage, no overwrite, unknown-time roundtrip and rejection of label leakage even after an output hash is redeclared. Replay is authored by Codex and is not independent semantic evaluation. No external benchmark code was executed; its import-time downloads/default model clients were not loaded.

## Input scale decides the next implementation boundary

- Raw message text totals413,216,772UTF-8bytes. Message sizes:p50=1,351bytes,p95=5,546,p99=7,000,max=329,788. These are bytes, not tokens.
- **30,177messages** exceed the old H14500byte complete-note cap even without headers. Reusing that packet policy would omit some sources; do not silently truncate them or pretend all history reached the model.
- Scoped `(conversation,role,exact text)` has**187,054distinct keys and680duplicate opportunities**. This describes exact repetition only. It is not guaranteed model-approved cache reuse, a universal minimum call count, semantic validation or authorization to run187kextractor calls. It makes a naive one-message/one-call capture plan unattractive and motivates measured capture/windowing design.

Next: bounded evidence windows with offsets/source provenance and an explicit affordable capture policy, then freeze the complete end-to-end comparison. Arms must include true memory-off, ordinary retrieval, our declared candidate and a compatible pinned competitor before superiority claims. Do not silently replace the tested graph candidate with raw retrieval. Keep the same allowed reader/roster/declared budget and charge ingestion as well as query work.

The official framework uses [LLM rubric scoring](https://github.com/mohammadtavakoli78/BEAM/blob/b2da22eac88bb0874c64665f13457eb99835774a/README.md#4%EF%B8%8F%E2%83%A3-evaluate-generated-answers). Any permitted authored/manual or deterministic adaptation must be frozen and labelled separately, not announced as official accuracy. No model judge/Pro/fallback is authorized; only installed declared local workers and approved V4.1Flash for any later paid worker phase.

**This stage:0local/0paid model calls, no benchmark score and no cap extension.** Retained H1ledger3262/3300 and paid463attempts/$1.852reserved are unchanged, as is PR105's previous4219inference attempts. The registry adds one retrospective completed engineering-preparation row, keeping all79prior rows byte-for-byte. Next model execution remains unrun. No NIE/persona/frozen kernel/original dirty worktree change.
