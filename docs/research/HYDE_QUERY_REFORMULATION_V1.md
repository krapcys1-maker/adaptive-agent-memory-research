# HyDE Query Reformulation — Exploratory Test v1 ("Mechanism H")

Preregistration: `PM-20260824-294f9581`. Campaign V2's second candidate, selected after Mechanism G's DROP.

## Selection: a fresh $0 diagnostic, not the next-ranked pool entry

Rather than mechanically take the next-highest-scored untested pool entry, this selection started from a question the pool's own ranking couldn't answer: what does this project's *actual, accumulated* failure distribution look like, and which candidate family targets it?

**Step 1 — absence-vs-misread tally.** Every `BASE`-wrong unit observed anywhere in this project to date (11 units, across `raw-provenance-fresh-replication-v1`, `retrieval-confidence-signal-v1`, `retrieval-rank-annotation-v1`, `second-hop-expansion-v1`, `sibling-entity-enumeration-v1`) was classified by reading its actual context and answer: was the needed fact present in the top-10 the reader saw (a "misread" failure, catchable by verification-against-context mechanisms) or absent from it (a "retrieval absence" failure, which no same-context verification can fix)?

| unit | source | class |
|---|---|---|
| `078150f1` | rawprov | absent (missing even in `raw_only` arm) |
| `0bc8ad93` | rawprov | absent (wrong in all 3 arms incl. `raw_only`) |
| `0e5e2d1a` | rawprov | RAW_PROVENANCE's own already-solved case (compact-only miss, `raw_only` succeeds) |
| `0a995998` | mechd | absent from top-10 (later found present in full store, see Step 2) |
| `0db4c65d` | mechd | absent (temporal-arithmetic: date never extracted) |
| `2ebe6c90` | mechf | absent (temporal-arithmetic: date never extracted) |
| `2ebe6c92` | mechf | absent (temporal-anchor: "today" un-datable from the compact fact) |
| `16c90bf4` | mechf | partial (Pilsner present, Lager absent; weak/borderline) |
| `10d9b85a` | meche | absent from top-10 (later found present in full store, see Step 2) |
| `0ea62687` | meche | absent (true — not in full store either, see Step 2) |
| `1568498a` | meche | absent (true — not in full store either, see Step 2) |

**9/11 (82%) are absence failures.** Zero are clean "evidence fully present, reader simply got it wrong" cases. This means the entire read-side verification/repair-against-same-retrieved-context tier this pool ranked well on evidence strength — `CHAIN_OF_VERIFICATION_FACTORED`, `PARAPHRASE_SELF_CONSISTENCY`, `VERBALIZED_CONFIDENCE_GATED_REPAIR`, `TARGETED_EVIDENCE_REPAIR`, `EVIDENCE_TAGGED_CITATION` — has almost no precondition to fire against in this project's actual failure distribution: every one of them requires the correcting evidence to already be present in the retrieved context, and 9/11 of the time it isn't. This is a genuine, project-specific reason to deprioritize that whole tier, distinct from (though consistent in spirit with) the earlier `CONTEXT_WRITE_TIME_ONLY_LEVERAGE` deprioritization of the conflict/supersession family.

**Step 2 — is "absent from top-10" the same as "absent from the store"?** Not necessarily: Mem0's write-time LLM extraction could have dropped the fact entirely (unfixable by any read-side or query-side mechanism), or the fact could be sitting in the store under a different rank the top-10 cutoff simply excludes (fixable by better retrieval). A $0 check — `memory.get_all()`, zero LLM calls — against two already-persisted stores from Mechanisms D and E found:

- `mechd-0a995998` ("how many items of clothing to pick up/return", gold 3): full store (100 items) contains *"Exchanged a pair of boots from Zara on 2/5 and still needs to pick up the new pair"* — directly relevant, present, but not in the top-10.
- `meche-10d9b85a` ("days spent at workshops/lectures/conferences in April", gold 3): full store contains *"Attended a lecture... on the 10th of April"* and *"Attended a 2-day workshop on 17th and 18th of April"* — both directly relevant (1 + 2 = 3, matching gold exactly), present, but neither in the top-10.
- `meche-0ea62687` and `meche-1568498a`: no keyword hits anywhere in either full store — true write-time absence, confirming not every "absent from top-10" case is retrieval-fixable.

**Step 3 — would a better-phrased query actually retrieve them?** A further $0 check re-queried the same two stores with a hand-written HyDE-style hypothetical sentence in place of the literal question (still zero LLM calls — Mem0's `search()` is local-embedding-only). In **both** cases the target fact moved from **absent** in the literal-question top-10 to **rank 1** in the hypothetical-query top-10. Independent corroboration: LongMemEval's own primary-source construction methodology (arXiv:2410.10813, appendix A.1) states evidence sessions are deliberately built to "convey the evidence statement indirectly" rather than in the question's own wording — phrasing mismatch between question and stored fact is a by-construction property of this exact benchmark, not a rare edge case.

This is the strongest, most direct $0 precondition confirmation of any mechanism tested in this campaign (2/2 clean hits, large effect — absent to rank 1 — versus the more modest partial fire rates that justified Mechanisms D/E/G).

## Mechanism

Read/query-side only. One extra small `temperature=0` LLM call per unit generates a short hypothetical memory-note sentence (`HYDE_PROMPT`, max_tokens=60) in the register Mem0's own compact facts use; Mem0's `search()` is then called with that hypothetical text **in place of** the literal question (the pure/faithful HyDE variant — no blend with the literal query, to keep this a clean one-variable test of the published technique, Gao et al. ACL 2023). Fully orthogonal to `RAW_PROVENANCE` (acts upstream of retrieval, not post-hoc content injection) and to Mechanism G (query reformulation, not second-hop expansion). Adds no caveat or annotation to the visible answer, so it does not carry the "judge-penalized epistemic caution" risk that sank three earlier mechanisms.

**Known, explicitly-flagged risk (not yet observed):** hallucination-guided retrieval drift — if the generated hypothetical confidently invents a wrong-but-plausible detail, it could steer retrieval *away* from the correct memory rather than toward it. This exploratory test's archaeology specifically checks for that failure shape on any regression.

Preregistration: `PM-20260824-294f9581`. **Verdict: `MECHANISM_H_FAIL` — DROP.**

## Results

6/6 fresh, gold-blind units (`data/lab/arena/hyde-query-reformulation-v1/selection.json`, 1 per LongMemEval-S category). The hypothetical-query top-10 differed from the literal-query top-10 on **6/6 units** (`new_from_hyde` 1–6 items) — the mechanism "fired" universally, a much higher rate than the 2/2 spot-check predicted, simply because any reformulated query embeds differently enough to shuffle *some* of a ~200-item store's top-10. **Net repairs: 0. Regressions: 0. Effect: NULL** on all 6 units.

| unit | type | new_from_hyde | BASE | +H |
|---|---|---|---|---|
| `1faac195` | single-session-user | 4 | OK | OK |
| `07b6f563` | single-session-preference | 5 | OK | OK |
| `1f2b8d4f` | multi-session | 1 | OK | OK |
| `4dfccbf7` | temporal-reasoning | 6 | WRONG | WRONG |
| `10e09553` | knowledge-update | 2 | OK | OK |
| `1903aded` | single-session-assistant | 5 | WRONG | WRONG |

## The two BASE-wrong units, examined — a different absence subtype than the one this candidate's precondition check confirmed

**`4dfccbf7`** — day-count between starting ukulele lessons and a guitar-tech visit (gold: 24–25 days). Neither `BASE` nor `+H`'s context contains an absolute date for either event — both compact facts say "today" (session-relative), never resolved to a calendar date. `+H`'s reformed query pulled in 6 different items (guitar-amp shopping, a soundbar purchase, a dress rehearsal) but none carry the missing dates either, because **the dates were never extracted into any compact fact in the first place** — this is a *temporal-representation-loss* failure, not a *retrieval-ranking* failure. No query reformulation, however well-phrased, can retrieve a date that Mem0 never stored.

**`1903aded`** — "what was the 7th job in the list you [the assistant] provided" (gold: Transcriptionist). Both arms' context only ever contains a vague "looking for work-from-home job ideas" summary — the individual 10-item list itself was compressed away at Mem0's write-time extraction and never survives as separately retrievable facts, in *either* query variant. Same shape as `1903aded`'s sibling case `0e5e2d1a` (Ledger Entry H's own target) — but unlike `0e5e2d1a`, `RAW_PROVENANCE`'s raw-session-injection would very plausibly fix this one (the list is presumably intact in the raw session text); `HyDE` cannot, since it only re-ranks among what Mem0 already chose to keep as separate compact items.

**On the 4 already-correct units**, the reformed query swapped 1–5 items for different ones (`07b6f563`: same iPhone-accessory facts stayed in reach, less-relevant filler churned) without ever destabilizing a correct answer — 0 regressions, and no sign of the hallucination-guided-drift failure mode this candidate's own archaeology flagged as its biggest risk.

## Classification: precondition real, but this sample's failures were the wrong absence subtype

The Step-2/Step-3 $0 diagnostics (see above) confirmed a real, large-effect precondition — a query-phrasing mismatch that moves a *present-in-store* fact from unranked to rank 1 — on two known, already-examined units. This exploratory test's *fresh, gold-blind* 6-unit draw happened not to contain that specific subtype of absence: its 2 failures were both instances of facts that were never separately extracted into the compact store at all (a *write-time* extraction loss), a different failure this candidate's mechanism has no leverage over by construction. This is a small-n draw property, not evidence the confirmed precondition doesn't occur in this project — but per the preregistered gate ("0 net repairs" triggers `FAIL`, honored literally rather than re-litigated post hoc), the formal verdict is `MECHANISM_H_FAIL`.

## Verdict and campaign consequence

**DROP.** 0 repairs, 0 regressions — a clean null, not a net-negative like Mechanism F, and mechanistically distinct from Mechanism G's "fired but returned irrelevant content" pattern: here the mechanism fired and returned *topically on-target* items (guitar/ukulele-adjacent, WFH-job-adjacent) that simply didn't happen to contain the specific missing detail, because that detail was never extracted at write time in the first place.

This is Campaign V2's **2nd consecutive** mechanism-family failure (G, H) — 2 of 3 toward the strategy-pivot STOP threshold, not yet triggered. A useful general finding carried forward: **this project's retrieval-absence failures are not one uniform class.** At minimum three distinct subtypes are now documented — (1) write-time extraction loss (fixable only by `RAW_PROVENANCE`-style raw injection or an extraction-side fix), (2) retrieval-ranking miss with the fact present in the full store (this candidate's confirmed-but-undersampled target), (3) temporal-representation loss — a session-relative expression ("today") never resolved to an absolute date, unfixable by either raw injection or query reformulation. Subtype (3) recurred in **4 of the 13** `BASE`-wrong units observed project-wide to date (`0db4c65d`, `2ebe6c90`, `2ebe6c92`, `4dfccbf7`) — the single largest identified cluster in this project's whole failure taxonomy, and the exact target of the already-twice-attempted `TEMPORAL_ANCHOR_AT_CONTEXT` mechanism (Ledger Entries A/B).

## Cost

$0.437383 (6 units ingested, 287 sessions; +1 hypothetical-generation call per unit; reader+judge on 2 arms negligible on top of ingest). One benign transient "Invalid JSON response" ingest warning, same pattern as every prior run in this project — no contamination FAILs (1 UNOBSERVABLE, consistent with prior rate).
