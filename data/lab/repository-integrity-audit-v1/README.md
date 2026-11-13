# Integrity audit receipts — 2026-11-04

Read the [report](../../../AUDIT_REPORT.md) and [handover](../../../HANDOVER.md).
This is the implementing agent's self-audit, not independent review.

- `safety-receipt.json`: verified private backup/restore scope and explicit exclusions.
- `preservation.json`: original worktree/NIE/frozen-artifact preservation comparison.
- `engineering-checks.json`: Git/object, syntax, memory/claim gate, environment and heuristic credential scan receipts; nonzero pip check is retained.
- `boundary-counterexamples.json`: five reproduced limitations. `observed:true` means a failure/limitation was reproduced, never a memory capability pass.
- `h1-results-replay.json`: both v5 artifact replays and exact deterministic rescores, paired gains/losses and recorded baseline repeatability differences.
- `cost-accounting.json`: cumulative PR105 attempts and recorded usage/reservations, not an account invoice.

Offline reproduction: `python scripts/reviews/audit_structured_runtime_boundaries_2026_11_04.py`.
It creates only temporary synthetic stores, calls no model/network and does not edit frozen sources.
Full local logs, inventory and private recovery bundles remain outside Git and must not be uploaded.
