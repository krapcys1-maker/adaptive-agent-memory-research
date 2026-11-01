# Retrieval Confidence Signal — Exploratory Test v1 ("Mechanism D")

Preregistration: `PM-20260824-3885f6ac`. **Verdict: `MECHANISM_D_FAIL` — DROP.** Selection: [`selection.json`](../../data/lab/arena/retrieval-confidence-signal-v1/selection.json). Results: [`results.json`](../../data/lab/arena/retrieval-confidence-signal-v1/results.json).

## Mechanism

Read-side, deterministic, zero LLM. When the top-1 vs top-2 retrieved item's Mem0 similarity score margin is below a fixed 0.10 (calibrated at $0 from already-collected scores on 8 already-used units, before this probe set was chosen), append one fixed, content-free note prompting the reader to check less-prominent candidates. Inert otherwise. Target: reader over-trusting the most prominent retrieved item under ambiguous retrieval — a distinct axis from `RAW_PROVENANCE` (content absence) and the dropped state mechanism (temporal validity).

## Bug encountered and fixed live (bug-discipline protocol followed)

The original run script's ingest loop had no cap-reached exception handling (only the reader/judge loop did). The provider proxy's own hard cap correctly refused the 5th unit's ingest mid-way (`openai.APIStatusError` 402, "$0.3455 spent... the cap for this scope is $0.35"), but the unhandled exception crashed the script before any output was written — discarding the *record* of 4 units that had, in fact, already been cleanly and fully ingested (real, paid, on-disk-persisted work). Fixed: wrapped the ingest loop in the same cap-aware handling as the reader/judge loop (`run_retrieval_confidence_v1.py`), and — since re-running from scratch would double-pay for the 4 already-completed units — wrote a small continuation script (`run_retrieval_confidence_v1_continue.py`) that reopens the *same* persisted store, reuses the 4 completed banks via a free `query()` call (no LLM, no re-ingest), and runs only reader+judge. The 5th unit (`08e075c7`) is dropped, not resumed — resuming a partially-ingested bank is not a state this project's methodology has ever validated, and completing it would need more ingest spend beyond the original cap. **Sample size: n=4, not the preregistered n=5 — disclosed, not hidden.** No experimental contract term (mechanism, threshold, reader, judge) changed.

## Results

| unit | type | margin | flagged | BASE | +D |
|---|---|---|---|---|---|
| `118b2229` | single-session-user | 0.271 | no | OK | OK (identical text) |
| `0a995998` | multi-session | 0.038 | **yes** | WRONG | WRONG |
| `09ba9854` | multi-session | 0.003 | **yes** | OK | OK |
| `0db4c65d` | temporal-reasoning | 0.048 | **yes** | WRONG | WRONG |

**Net repairs: 0. Regressions: 0.** 3 of 4 units triggered the flag; 0 of those 3 changed correctness in either direction.

## Archaeology ($0, before deciding)

Answer *text* differs between arms on all 3 flagged units (the reader visibly reacts to the note — rephrasing, adding hedges — so the note is not silently ignored), but the underlying *evidence used* never changes. On the two flagged-and-wrong units, the transcripts show why: both are **absence** failures, not **prominence** failures — `0a995998` ("items of clothing to pick up") and `0db4c65d` (the two event dates for a day-count question) have the needed fact **missing from the retrieved set entirely**, not present-but-buried under a more prominent competitor. A margin-based "check the less-prominent candidate" note cannot help when no candidate — prominent or not — contains the needed information. `09ba9854` was already correct in both arms (a genuine near-tied-score case, margin 0.003, but both top candidates happened to jointly support the correct $50 answer, so there was nothing to disambiguate). `118b2229`, the one unflagged unit (margin 0.27, confidently unambiguous), was unaffected as expected — the mechanism is inert there by design, confirmed.

**Classification: `REGIME_MISMATCH`, not `MECHANISM_FAILURE`.** The transform itself works exactly as specified (fires only below threshold, provably inert above it, per its own 8/8 passing unit tests) and visibly reaches the reader. What this small sample lacked was the mechanism's actual precondition: a case where the *correct* answer is retrieved but *not* top-ranked, and a near-tied score genuinely reflects that ambiguity rather than a shared absence. None of this run's 4 units happened to have that shape.

## Decision: DROP (no repair attempted)

Per the campaign's repair-budget rule, a repair is justified only for a single, deterministic, harness-level flaw — not for "the sample didn't happen to contain the target regime," which is a legitimate small-n outcome, not a bug. Tuning probe selection *after seeing which units lacked the right shape* would be exactly the prohibited post-hoc cherry-picking. **DROP for this V1 sample size and selection**, not a claim that the underlying idea is refuted — the precondition (gold present but not top-ranked, genuine score ambiguity) was never tested, only assumed likely enough to be worth a first look.

## Cost

Original interrupted run: $0.345535 (4 units fully ingested before the cap stopped; 1 unit's partial ingest abandoned, not billed further). Continuation (reader/judge only, no re-ingest): $0.001626. **Total: $0.347161.**
