# Independent review packet v0.1 for PMLAB-NATURAL-RET-001 contracts

Status: ready for one blind independent review; source artifacts are pinned to commit `2d5948de285a7818d8ff28e5a3c2c1d0f6cec9d7`.

## Purpose

Attempt to falsify the source-unit, authentic-query, and label-free token-feasibility contracts before any historical corpus builder exists. The review may recommend only whether a later development-builder review is warranted. It cannot select a byte ceiling, authorize corpus construction or retrieval, promote a model, or support an architecture claim.

## Independence and blindness

Read only the exact source-commit artifacts listed in `packet-manifest.json`. Before the completed form is immutably frozen, do not read:

- either DeepSeek advisory review directory listed in the manifest;
- the superseded v0 independent packet;
- any future builder, source-unit corpus, query labels, gold evidence, embedding, vector, ranking, or backend output.

A cross-family model review must use a genuinely different model family in one stateless context with no access to this conversation. A same-family or context-carrying review is advisory only. A human reviewer must not be an author of the reviewed contract.

## Required attack surface

The reviewer must cover all nine dimensions in the form, including the new `oversize_split_and_token_ceiling` dimension. In particular, challenge:

- a single CommonMark block larger than the ceiling;
- a no-whitespace Unicode string requiring a valid UTF-8 code-point split;
- repeated heading context that itself consumes most or all of the budget;
- missing, duplicate, reordered, or out-of-range split parts;
- byte-identical body reconstruction after removing repeated context;
- a byte-safe unit that is unsafe for E5 tokenization;
- the fact that the feasibility audit measures pre-split units and does not justify a ceiling.

## Procedure

1. Resolve every artifact from the exact source commit and verify its SHA-256 against the manifest.
2. Copy and complete `review-form.template.json` without viewing forbidden paths or outputs.
3. Freeze the completed form immutably.
4. Validate it with:

```text
python scripts/validate_natural_history_contract_review.py path/to/completed-review.json --packet-dir data/lab/pmlab-natural-history-v0/independent-contract-review-v0.1
```

`accept_for_development_builder_review` requires all nine dimensions accepted, no critical or major blocker, true attestations, and an explicit recommendation. Even that verdict leaves the byte ceiling null and requires author disposition plus a separate adversarial split implementation review before any builder authorization.
