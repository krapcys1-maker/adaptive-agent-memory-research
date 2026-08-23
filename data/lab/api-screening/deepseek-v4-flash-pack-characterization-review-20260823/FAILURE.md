# Failed DeepSeek pack-characterization audit packet

Status: failed instrument; no review verdict exists

The input packet was frozen at `f96dcbe6609403662fb9432fb92a6a816a5d2785`. Two API attempts used the same frozen prompt and data:

| Attempt | Response ID | Prompt tokens | Completion tokens | Conservative cost |
|---|---|---:|---:|---:|
| 1 | `55d3fd0e-07f8-4699-a45d-32834eb548ff` | 53,500 | 3,000 | USD 0.02750000 |
| 2 | `336b7d7b-773c-4810-965f-2fa447233e00` | 53,500 | 6,000 | USD 0.03146000 |

Both responses repeated list items until the completion limit and ended inside a JSON string. Neither parses under the frozen schema. They are preserved as `invalid-raw-response-01.json` and `invalid-raw-response-02.json`; no content from them is accepted as an audit finding.

Total failed cost: USD 0.05896000.

Disposition: preserve this failed run, reduce the review packet to only claim-relevant aggregates and per-case receipts, cap list lengths explicitly, freeze it under a new run ID, and allow at most one v2 API attempt.
