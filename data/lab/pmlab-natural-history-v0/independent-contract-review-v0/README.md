# Independent review packet for PMLAB-NATURAL-RET-001 contracts

Status: superseded before any review; the single-oversized-block split rule was incomplete; use the next packet revision

Source commit: `ebe82013066afac292d6747102ec57e4ffa7ab84`

## Purpose

Review whether the source-unit and authentic-query contracts are sufficiently explicit to permit construction of a retrospective **development-only** historical corpus. Acceptance cannot authorize dense-model selection, backend execution, prospective test collection, architecture promotion, or a confirmatory claim.

The reviewer should attempt to falsify:

1. exact Git cutoff reconstruction without working-tree/future leakage;
2. stable, versioned, recomputable unit identity;
3. CommonMark heading/direct-body semantics and deterministic splitting;
4. RFC 4180 CSV and RFC 8785/I-JSON JSONL canonicalization;
5. exact-duplicate collapse, aliases, and exclusion coverage;
6. byte-identical backend projection and hidden metadata;
7. private query receipts, storage class, and pre-output capture ordering;
8. development/test isolation and remaining locks.

## Review sources

Read only the source artifacts listed and hashed in `packet-manifest.json`. Do not read either DeepSeek contract-review directory under `data/lab/api-screening/` before freezing your form; those are advisory outputs and would anchor an independent review.

Copy `review-form.template.json`, fill every field, and run:

```text
python scripts/validate_natural_history_contract_review.py path/to/completed-review.json
```

Commit or otherwise immutably freeze the completed form before any comparison with author or M1 dispositions. A cross-family model reviewer must use a genuinely different model family, one stateless review context, and no hidden access to this task's conversation. Same-family or context-carrying review is advisory only and cannot satisfy this packet.

## Acceptance boundary

`accept_for_development_builder_review` requires every dimension to be `accept`, no critical or major blocker, all blindness attestations true, and a validator receipt. Even then, the project must record a separate author disposition and freeze the byte ceiling plus adversarial builder tests before construction. Any builder output remains development data, not a test result.
