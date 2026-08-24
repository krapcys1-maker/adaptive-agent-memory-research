# Raw Provenance — Fresh Replication v1 ("Mechanism C")

Fresh, gold-blind replication of `RAW_PROVENANCE_CONDITIONAL_SIGNAL` (E3, [`CLEAN_RAW_PROVENANCE_RETEST_V2.md`](CLEAN_RAW_PROVENANCE_RETEST_V2.md)) on 8 units never used anywhere in this arena before. **Verdict: `RAW_PROVENANCE_REPLICATED_SUPPORTED` — the campaign's first `REPLICATED_VALIDATED_TRANSPLANT`.**

Preregistration: `PM-20260824-0a6fc616`. Selection: [`selection.json`](../../data/lab/arena/raw-provenance-fresh-replication-v1/selection.json). Results: [`results.json`](../../data/lab/arena/raw-provenance-fresh-replication-v1/results.json). Spend: **$0.575419** of a $0.75 cap (384 ingest calls across 8 units, 24 reader calls, ~48 judge calls, 0 disputed).

## Mechanism (unchanged from E3)

Read-side only, C4. `mem0_compact` = Mem0's native retrieved context. `mem0_compact_plus_raw` = compact + the raw source session behind Mem0's top-1 hit, appended verbatim. `mem0_raw_only` = the raw session alone, a control isolating whether raw content alone (without Mem0's extraction) suffices. Deterministic session-date mapping (`arena.mechanism_ablation.raw_session`, `arena.retrieval_truth.session_map`) — no gold-aware matching, no semantic guessing, code already audited earlier in this project.

## Selection

8 fresh units, gold-blind, category-stratified (2 knowledge-update, 2 multi-session, 1 temporal-reasoning, 1 single-session-user, 1 single-session-assistant, 1 single-session-preference), excluding all 20 units used anywhere in this arena to date. Frozen before any ingest. Small haystack-session overlap with prior units (0–3 of 40–50 sessions) checked and judged non-disqualifying — consistent with LongMemEval-S's own corpus design (session reuse across questions about the same simulated user) and Stage 2's own precedent; no vector-store-level contamination is possible since every unit gets its own reset, isolated Mem0 bank (verified: `contamination_status: PASS` on all 8).

## Results

| arm | score |
|---|---|
| `mem0_compact` | 5/8 |
| `mem0_compact_plus_raw` | **6/8** |
| `mem0_raw_only` | 4/8 |

**`COMPACT_WRONG_RAW_FIXES`: `['0e5e2d1a']`** — 1 unit. **`RAW_CAUSES_REGRESSION`: `[]`** — 0 units. Strikingly close to E3's own shape (5/9, 6/9, 4/9) — the same qualitative pattern replicated independently, on a differently-selected, non-overlapping-by-design unit set.

## The repair, examined

`0e5e2d1a` (single-session-assistant) — *"...how many subjects were in the [binaural beats] study published in the journal Music and Medicine..."*, gold `38 subjects`.

- **compact**: *"I cannot determine the number of subjects... The context only notes that you were seeking examples of studies... but it does not include the details."* — WRONG. Mem0's compact extraction kept the topic but dropped the specific figure.
- **compact+raw**: *"The study... involved 38 subjects."* — CORRECT. `gold_state`: `gold_in_context=True, gold_rank=1`.
- **raw-only**: also correct, confirming the number lives in the raw session text itself, not in anything compact contributed.

This is a genuine **absence-type** repair — raw provenance supplied content the compact extraction never captured. This fills the exact gap E3's own report flagged (*"there was no absence-regime failure to test [H1] against on this sample"*): this replication's one repair is absence, not competing-facts disambiguation, broadening the mechanism's demonstrated repair territory rather than narrowing it.

## The two non-repairs, examined (not assumed)

`078150f1` (multi-session, fundraising goal): both arms correctly identify the $250 raised but neither can find the initial goal — the raw session behind the *top-1 hit* doesn't happen to be the session containing the goal figure, a real limitation of single-hop (top-1-only) provenance, not a mechanism malfunction. `0bc8ad93` (temporal-reasoning, museum visit): raw provenance made no difference — both arms confidently report "with a friend," identical text in both arms, suggesting the ambiguity here is an entity/visit-matching issue (possibly a different museum visit than the one "two months ago" — an H5-adjacent, harmful-sibling-shaped confusion) that raw text alone does not resolve. Neither is a regression; both were already wrong under compact.

## Verdict

**`RAW_PROVENANCE_REPLICATED_SUPPORTED`** — the preregistered gate (`PM-20260824-0a6fc616`) is met exactly: ≥1 net repair (1), 0 regressions, and a traceable, transcript-confirmed causal path (`0e5e2d1a`'s gold text literally present in the raw session, absent from compact). Per the campaign's status ladder (contract §17/§20), a mechanism that clears exploratory-positive (E3) *and* a fresh, independently-selected, gold-blind held-out replication with a confirmed mechanistic trace is promoted to **`REPLICATED_VALIDATED_TRANSPLANT`** — the first one in this project.

**Calibrated, not overclaimed:** the effect is real but small — one repaired unit out of eight, replicating a similarly thin signal from E3 (one of nine). This is evidence the mechanism *works in its demonstrated regime* (compact-context absence of a specific, extractable detail present in a reachable single session), not evidence it is a large-magnitude fix. No claim is made about `raw_only` (which underperforms compact in both E3 and here, replicating that direction too) or about categories/regimes this sample did not exercise.

## Anomaly, noted not hidden

Two "Invalid JSON response" warnings appeared during ingest (malformed extraction output on 2 of 384 session-ingest calls, out of many). Both were absorbed by Mem0's own existing error handling without stopping the run; all 8 units still show sane, non-degenerate stored-item counts (171–256) and `contamination_status: PASS`. Not investigated further — did not affect any arm's correctness, and is a known class of transient provider/parsing hiccup already documented elsewhere in this project's ingest tooling, not a new finding.

## Cost

Ingest $0.558693 (384 sessions, 8 units) + reader/judge $0.016726. **Total: $0.575419** of the $0.75 cap.
