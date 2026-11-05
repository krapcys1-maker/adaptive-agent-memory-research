# BEAM read-time evidence contract — exploratory common-reader comparison

2026-11-05. Owner explicitly authorized continued implementation, tests and local/approved Flash workers. Freeze the entire following mechanism before generating answers or inspecting expected-answer/rubric values. We have inspected schema shapes/counts and performed gold-free format/retrieval preparation only. Public data/prior exposure is not a witnessed sealed split.

## Question and fixed arms

Does a read-time citation contract improve answer quality or reduce material contradictions over **the same retrieved evidence** for an adequate local model? All200probes/10histories/10abilities; no success-selected subset. This is a new source-evidence candidate, **not the old offline graph method** or an official BEAM/vendor leaderboard reproduction. It avoids interpreting187kmessage records before queries, but has not solved general capture, graph transfer, consolidation or agency.

- N: no-memory reader, no evidence.
- B: ordinary lexical window retrieval, raw JSON answer.
- C: exactly B's selected evidence, answer plus unknown flag and up to3literal quotes referencing shown window aliases. Code accepts a non-UNKNOWN answer only if all declared references/quotes are valid; otherwise delivers UNKNOWN. Quotes12–240Unicode code points, literal matching, no normalization. This verifies location/spelling, **not semantic entailment, authority correctness or temporal truth**.

Use frozen access-v1 candidates and only its already selected window set. Replace long canonical window IDs by short packet-local E0/E1/... aliases, retaining a private canonical mapping and all other evidence/source fields. If B/C systems together exceed the6000byte messages ceiling (UTF-8/native ASCII-escaped), remove the last window for **both**, never choose by an answer. Record every omission and alias; no fake corroboration/repeated evidence. C's schema enumerates only shown aliases. Baseline has no quote requirement. Report C raw and delivered outputs separately, including correct raw answers lost to guard refusal; never repair with gold.

Question text, available history, common role/partial-context policy, model identity and decoding are fixed. Prompt/schema differ by treatment and their cost is charged; this is a whole output-contract comparison, not proof of equal total compute or graph-state effects. Fresh conversation per case/arm; rotate N/B/C execution order by global case index. No answer-directed retry or fallback. All final outputs and errors remain retained.

## Explicit resource declaration before new calls

Only installed `qwen2.5:14b-instruct`, Q4_K_M, digest7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6. Temperature0/seed7, context4096, output512, native JSON schemas; complete request ceiling10000ASCII-serialized bytes, messages6000. Phase605attempts:600primary plus3unrelated transport and2Ccontract controls. Deadline3600seconds; per-request timeout180. Controls must pass before primary calls. Unload only the owned model, refuse if another task has one loaded.

This is a **new BEAM task ledger** with cumulative cap650, not a reset of H1 or prior failed calls. Expected0before/605after; preserve every attempt including a failed control. Existing H1ledger3262/3300 and paid463/$1.852reserved remain unchanged and their hashes are checked before/after. PR105 existing local3756 plus this phase605 gives4361local/4824total if complete, with no double counting. Max BEAM650 implies a separate disclosed PR-local ceiling4406; this phase does not authorize filling unused allowance with retries. Paid cap500/$2 unchanged; **zero new API calls** in this phase. Flash is not a judge/planner and no external judge is invoked.

## Freezes, evaluation and decision

Commit code/config, prepared matrix and source identities before inference; commit the complete raw-output freeze before any score/reference join. Verify all605native requests/responses, complete200x3roster, same B/C evidence, aliases, parse/guard behavior and source/ledger hashes. Malformed outputs stay explicit; do not count safe UNKNOWN fallback from a malformed response as a correct answer. Native truncation is reported.

Official BEAM uses an LLM judge; this experiment will **not claim official accuracy**. After raw freeze, construct a private authored-review packet from original references/rubrics. Mask arm names and deduplicate identical valid answer strings within the **same question** (never across questions); retain mappings to every raw/delivered arm. Codex assesses rubric satisfaction and material contradiction from these fixed references, with a short auditable reason; no API/local judge. This is self-authored assessment, not independent or fully blind review. Ambiguous/defective references are flagged and retained in the200denominator, with conservative failed/uncertain bounds; do not alter gold or rewrite a rubric after outputs. Structural evidence validity and semantic rubric satisfaction remain separate.

Primary descriptive outcome: delivered complete-rubric pass/200; also N/B/Craw, refusal, material contradiction, parse/truncation, guard false-refusal tradeoffs, all10abilities and all10histories. Ten histories are shared clusters, not600independent tests. Report paired gains/losses, exact duplicate answers and actual ingestion/query tokens/time/storage. No significance/equality/vendor claim from public single-seed data.

Prespecified engineering screen for **fresh-transfer candidacy only**: Cdelivered has more rubric passes than B, no new material contradiction versus B within any history, and median primary Cwall time at most2xB. Failing any condition rejects adoption; a pass still does not authorize integration or prove a universal gain. If authored evaluation is incomplete, record pending rather than substituting an easy lexical metric. Any subsequent tuning makes this run development evidence and requires another unused test.
