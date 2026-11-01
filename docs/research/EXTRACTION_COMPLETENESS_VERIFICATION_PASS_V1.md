# Extraction Completeness Verification Pass — Exploratory Test v1 ("Mechanism J")

Preregistration (calibration): `PM-20260824-f8d5e89c`. Calibration result: `PM-20260824-9d020373` (PASSED, 4/4 list cases split, 0 fabrication). Preregistration (full test): `PM-20260824-195a1656`. **Verdict: `MECHANISM_J_EXPLORATORY_SUPPORTED`.** Campaign V2's first positive exploratory signal, and the first mechanism to touch Mem0's own write-time extraction call.

## Mechanism

Write-side vendor patch to `external/venvs/mem0/Lib/site-packages/mem0/memory/{utils.py,main.py}` (`data/lab/arena/extraction-completeness-verification-v1/vendor-patch/`, manifest with before/after file hashes). After Mem0's normal extraction call, one additional LLM call re-reads the session text against the facts already extracted and returns two correction kinds: `facts_to_add` (missing entirely) and `facts_to_replace` (an already-extracted fact bundling multiple distinct enumerable items, split into individual facts). Gated off by default (`metadata["completeness_check_enabled"]`), so this project's shared BASE construction is untouched.

## Run interruption and continuation (disclosed)

The full 8-unit run hit its own $1.20 cost cap mid-ingest, after 6/8 units completed BOTH the BASE and `+J` bank ingests cleanly (`$1.196073` spent, `mechj-v1-` scope) — the dual-bank design (BASE and `+J` require separate ingests, since `+J` changes what gets stored, not just how it's rendered) combined with real-corpus-scale completeness-check calls cost more than a single-ingest mechanism. `18bc8abd` and `1b9b7252` never started ingest and were dropped, not resumed — re-ingesting from scratch would double-pay, and resuming a partial dual-bank ingest is not a state this project's methodology relies on (same precedent as Mechanism D's own interruption, `run_retrieval_confidence_v1_continue.py`). A separate, small continuation (`run_extraction_completeness_v1_continue.py`, `mechj-v1-cont-` scope, $0.06 cap) reopened the 6 already-ingested banks (free `search()`, no re-ingest) and ran reader+judge only.

**A second bug surfaced live during the continuation**: the first two reader-call attempts crashed identically (`TypeError: process() takes no keyword arguments`, inside `httpx2`'s response decoder) — a stray system-wide `brotli.py` (resolving from the global Python environment, not the pinned Mem0 venv) shadows the expected brotli decoder and has an incompatible `Decompressor.process()` signature, crashing whenever DeepSeek's server happens to brotli-encode a response. Not retried a 3rd time per circuit-breaker discipline. Root-caused at $0 (client-side only) and fixed by forcing `Accept-Encoding: gzip, deflate` in the `OpenAI` client's `default_headers`, so the server never sends brotli-encoded responses — the continuation then ran cleanly. This is an ambient harness fragility (present since before this campaign, only now triggered by chance), not introduced by this mechanism; worth carrying forward as a standing fix for any future script constructing this same client.

**n=6 for this exploratory test, not the preregistered n=8** — disclosed, not hidden.

## Results

| unit | type | BASE | +J |
|---|---|---|---|
| `21436231` | single-session-user | OK | OK |
| `09d032c9` | single-session-preference | WRONG | **OK** |
| `2311e44b` | multi-session | WRONG | WRONG |
| `21d02d0d` | multi-session | OK | OK |
| `4dfccbf8` | temporal-reasoning | WRONG | **OK** |
| `184da446` | knowledge-update | OK | OK |

**Nominal: 2 net repairs, 0 regressions.** Archaeology below distinguishes one genuine, traceable repair from one judge-noise artifact — the preregistered gate (`≥1 net repair with a traceable causal path`) is evaluated on the genuine repair alone, honestly, rather than counting both.

## Archaeology

**`09d032c9`** (single-session-preference, "battery life tips") — **genuine, traceable repair.** `BASE`'s context frames the user's power bank only inside a travel-organizing fact ("Looking for advice on organizing tech accessories like portable power bank and wireless charging pad for travel") — plausible but the wrong shape for this question, since the reader gives up entirely ("no information about phone troubleshooting or battery optimization"). `+J`'s completeness pass split out a clean, standalone ownership fact — "Has a new portable power bank and wireless charging pad" — and separately "Has a wireless charging pad." `+J`'s answer explicitly and correctly grounds itself in exactly this: *"Since you have a new portable power bank and wireless charging pad, make it a habit to top up your phone during your commute and keep it on the charging pad at your desk."* This is precisely the gold answer's own requirement ("build upon their previous mention of purchasing a portable power bank... suggestions on how to optimize its use") and precisely the target failure this mechanism was designed for: a fact bundled inside an unrelated framing (travel organization) is split out and made independently usable.

**`4dfccbf8`** (temporal-reasoning, "what did I do with Rachel on Wednesday two months ago") — **judge-noise artifact, not a mechanism effect.** `BASE` and `+J`'s answers are substantively identical: both correctly identify "ukulele lessons with Rachel" as the relevant fact (present in **both** arms' context, unchanged by this mechanism) and both correctly decline to name a specific Wednesday, since neither arm's context contains a resolvable date. `+J`'s only new items (a marathon reflection, an unrelated birthday note) are irrelevant to the question and play no role in either answer's text. This is the same "near-identical honest abstentions, judge phrasing-sensitivity" pattern already documented twice elsewhere in this project (Stage 2's `0977f2af`; this campaign's own Mechanism H archaeology) — not counted as a real repair.

**`2311e44b`** (multi-session, "pages left in 'The Nightingale'", gold: 190) — stayed wrong on both arms; `+J`'s new items (workbook-writing notes, unrelated) are topically irrelevant to the page-count arithmetic needed, and neither the total-page-count nor pages-read figure appears in either context — a write-time extraction loss this specific completeness-check pass had no textual basis to recover (the missing number likely never survived into any session's raw captured text at all, or needs cross-session aggregation the per-session completeness check doesn't perform). No regression; the mechanism correctly added nothing false here.

**On the 3 already-correct units** (`21436231`, `21d02d0d`, `184da446`): `+J`'s context differs from `BASE`'s (new items added/split in every case, confirming the mechanism fires universally as designed) but never destabilizes a correct answer — 0 regressions across the full 6-unit sample.

## Classification

Genuine positive signal, distinguishable from the "fired but returned irrelevant content" pattern (Mechanism G) and the "precondition real but wrong subtype drawn" pattern (Mechanism H): here the mechanism fired on every unit, and on the one unit where its specific output (a cleanly split, previously-bundled fact) was actually relevant to the question, it produced a correct, traceable repair. On the other units it was either irrelevant-but-harmless (no regression) or coincidental (judge noise, not counted).

## Verdict and campaign consequence

**`MECHANISM_J_EXPLORATORY_SUPPORTED`.** Campaign V2's first mechanism-family success (after 3 consecutive failures — G, H, I — triggered the strategy pivot to AAMR-internal-evidence-informed discovery, which itself pivoted to a fresh external-discovery-rebuild workflow that surfaced this candidate). Per this project's established mechanism lifecycle (matching `RAW_PROVENANCE`'s own path: exploratory positive → fresh gold-blind replication → `REPLICATED_VALIDATED_TRANSPLANT`), the natural next step is a fresh replication on new units before this mechanism can be elevated to validated status — not undertaken in this turn; recorded as the clear next campaign action.

## Cost

Ingest (original run, `mechj-v1-`): $1.196073 (6/8 units, dual BASE/+J banks, stopped by its own $1.20 cap). Continuation (reader+judge only, `mechj-v1-cont-`): $0.002410. **Total: $1.198483.** Two benign/handled anomalies: many transient "Invalid JSON response" warnings during +J ingest (same pattern as every prior run in this project, at higher frequency here since the completeness-check response is longer and more prone to truncation on real session-scale text than on calibration's short synthetic cases — did not prevent the mechanism from working, confirmed by the stored-count deltas and the archaeology above) and the brotli/httpx2 decoder bug (root-caused and fixed at $0, described above).
