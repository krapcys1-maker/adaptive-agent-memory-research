# Second-Hop Associative Expansion — Exploratory Test v1 ("Mechanism G")

Preregistration: `PM-20260824-9dcd4352`. **Verdict: `MECHANISM_G_FAIL` — DROP.** First mechanism tested under Campaign V2 (external-discovery-first strategy); 1 of a possible 3 toward a strategy-level pivot, not a global stop.

## Mechanism

Read-side, deterministic except for one extra live (free) Mem0 `search()` call, gated on the compact top-10's own content. Seeds a second-hop query with the top-1 retrieved item's own text (A-MEM-inspired pseudo-relevance-feedback); any hit not already present in the top-10 (by id) is appended as `[associated] <text>`, capped at 1 new item. Inert (byte-identical to `BASE`) when the second hop returns nothing genuinely new. Precondition verified at $0 before spend: ~25% fire rate on 8 already-ingested `RAW_PROVENANCE` stores ([`EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md`](EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md)).

## Results

6/6 fresh, gold-blind units (`data/lab/arena/second-hop-expansion-v1/selection.json`). Mechanism fired (genuinely new item appended) on 2/6 (33%), consistent with the $0 precondition check. **Net repairs: 0. Regressions: 0. Effect: NULL on all 6 units**, including both fired ones.

| unit | type | fired | BASE | +G |
|---|---|---|---|---|
| `1e043500` | single-session-user | no | OK | OK |
| `1a8a66a6` | multi-session | yes (1 new) | WRONG | WRONG |
| `1c549ce4` | multi-session | no | OK | OK |
| `370a8ff4` | temporal-reasoning | no | WRONG | WRONG |
| `0f05491a` | knowledge-update | no | OK | OK |
| `18dcd5a5` | single-session-assistant | yes (2 new) | WRONG | WRONG |

## The two fired units, examined

**`1a8a66a6`** — "How many magazine subscriptions do I currently have?" (gold: 2). `BASE`'s top-10 already contains both relevant facts (`Canceled Forbes magazine subscription in early March...`, `Subscribed to The New Yorker in early February`); `BASE`'s answer hedges: confirms The New Yorker, states the total "cannot be determined." The associated second-hop item — `Planning to use Wave or FreshBooks for payment tracking` — is topically unrelated to magazine subscriptions (it was pulled in because it is semantically near the top-1 hit, not near the query). `+G`'s answer changes to a confident, still-wrong claim ("you have one magazine subscription... You canceled your Forbes subscription in early March") built entirely from facts already present in `BASE`'s own context — the associated item contributes nothing to that answer's content. With `READER_PARAMS` at `temperature=0`, this is a case of an irrelevant appended line perturbing a deterministic reader's output despite carrying no relevant information itself: a genuine mechanism risk (prompt-sensitivity), not a mechanism benefit, and not scored as a regression only because `BASE` was already wrong.

**`18dcd5a5`** — asks how many mummies a D&D one-shot party will face (gold: 4). The associated item — `Meditation and yoga sessions helped me relax and focus` — is unrelated to the question. `BASE` and `+G` give the identical "cannot be determined" answer; no perturbation this time.

## Classification: regime confirmed, mechanism itself doesn't help (semantic drift)

Unlike `D`/`E` (near-zero fire rate) this precondition fired close to its predicted ~25-33% rate — not a regime-mismatch null. The failure is mechanistic: seeding the second hop with the **top-1 item's own text** optimizes for similarity to that item, not to the original query, so the appended "associated" content drifts topically away from what the question actually needs. In both fired cases the associated item was irrelevant to the query. This is a structural property of adapting A-MEM's link-expansion pattern onto Mem0's flat `search()` (no query-conditioned link graph), not a tuning accident — matches the caveat already flagged for this candidate in the discovery pool.

## Verdict and campaign consequence

**DROP.** 0 repairs, 0 regressions, and one traceable case of irrelevant-content reader perturbation worth flagging for future annotation/append-style mechanisms (a new, distinct data point from the "judge-penalized epistemic caution" pattern in Entries I/J/K — this one is about content-irrelevant answer instability at `temperature=0`, not about hedging specifically).

Per Campaign V2's STOP semantics, this is failure **1 of 3** toward a strategy-level pivot back to external discovery — not a global stop. Continuing autonomously to the next candidate from the existing 28-entry pool.

## Cost

$0.414206 (6 units ingested, 1170 sessions across the batch; reader+judge negligible on top of ingest). No cap breaches, no contamination FAILs (2 units UNOBSERVABLE, not FAIL — consistent with prior UNOBSERVABLE rate in this harness).
