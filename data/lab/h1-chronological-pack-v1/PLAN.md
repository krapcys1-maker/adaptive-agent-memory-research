# Whole-H1 chronological packing — exploratory paired protocol

2026-11-05. Successor to the density diagnostic, whose 144 frozen primary outputs contain one stale leak in `stale_repeat_first` and none in the other five arms. This motivates testing a general ordering change; it does not establish a universal ordering cure. All H1 public development and validation-B cases are already spent.

## Fixed intervention and roster

Run every one of the 84 questions in each split, all seven families: 168 cases, two conditions, 336 primary calls plus three transport controls. Both conditions are **new generations**, not inherited scores. Alternate their execution order by global case index.

- `original`: exactly the recorded v5 automatic selected source IDs, order, full source text, source roles, dates, question and system message, verified against its native request.
- `chronological`: the same complete notes, stably sorted by increasing recording day; equal-day notes retain their original order. No deletion, new evidence, explicit overwrite rule, label or answer-specific branch. No gold source IDs, case family or expected answer is used to transform a packet.

Preserve all IDs including any repeats; up to three complete notes and 4500 UTF-8 context bytes. Validate scope and source time. Reject a mismatch/truncation, rather than silently change a packet. Report unchanged pairs as such, not as novel independent evidence. This isolates order within the existing selected evidence; automatic source selection itself is inherited from the already charged v5 Flash reranker, and is not independently revalidated.

Only installed pinned `qwen2.5:14b-instruct` Q4_K_M, original model digest, seed7, temperature0, native answer schema, output512/context4096. Freeze all input/packet/code hashes before generation and the complete raw output before scoring. Retain every failed attempt; no retry, fallback, API/model judge, NIE write or production change.

## Resource boundary

Use the existing cumulative H1 local ledger and the prior explicit cap3300 (amendment `6a24f95`), without a reset. Before this phase it has2923 attempts; reserve room for all339 calls, resulting in3262. Phase cap339, deadline2400seconds. Zero new paid calls; API cap500/$2 and ledger stay unchanged. Unload only this phase's owned model. A failure stays incomplete; do not score a subset as a complete run.

## Measurement and decision, fixed before inference

Use the unchanged mechanical H1 `answered`, `leaked`, `clean_answered` and abstention metrics over all cases, by split and all seven families. Report every paired gain/loss, parse errors, native token counts, exact same-message pairs, and original-arm drift against saved v5 answers. Do not pool 336 generations as336 independent cases or substitute secondary metrics after a failure.

Descriptive engineering screen: promote only to a fresh-transfer candidate if validation has **no new leak**, more clean answers than the contemporaneous original, and no family loses a clean answer in aggregate. Report development separately. Any tradeoff or no gain rejects automatic adoption; retain it as a diagnostic. This is not a calibrated statistical/industry threshold and not sealed confirmation. Keep validQ000043 explicitly identified as an already-known case, never a separately tuned target. Even a pass does not authorize integration/deployment or a vendor-superiority claim.
