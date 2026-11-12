# DeepSeek spend ledger, November 2026 phase

`spend-ledger.jsonl` is the append-only log written by the local metering proxies (`scripts/metered_proxy.py`,
`scripts/flash_only_proxy.py`) for every paid call of the phase capped at 12 USD. One JSON object per call: timestamp
(UTC), model, prompt and completion tokens, cost in USD, run id, and whether the provider reported usage. It holds no
prompt or reply text.

The `usd` field is computed at the arena's list price, which the experiment READMEs describe as deliberately high. It is
an upper accounting figure, not the provider's invoice.

## Correction of 2026-11-12: the published file was incomplete

Until 2026-11-12 the committed file stopped at 2026-11-01T14:59:59Z. The proxies kept appending to the same file in a
local working tree, and those later rows were never committed, although the experiments they paid for were published.

| | Rows | USD | Last row (UTC) | SHA-256 |
|---|---:|---:|---|---|
| Committed before 2026-11-12 | 15,752 | 2.6915 | 2026-11-01T14:59:59 | `451582a8320a07702c590c8a673a82afaa1ba3b7bd0e6eb38c1bfabf295edde1` |
| This file | 29,627 | 7.4015 | 2026-11-02T17:51:58 | `4dd5fa1e56347710a3b1cb09a0f0075c9bc7adbabc322dc62fb9798cd5e5e694` |
| Added | 13,875 | 4.7100 | | |

What was checked, without any model or network call:

- The earlier committed file is a byte-for-byte prefix of this one. Nothing was rewritten or removed.
- Timestamps never decrease. Every row has the same eight fields, `via` is `proxy` and `usage_known` is true in all rows.
- The total stays under the 12 USD phase cap.
- The added rows for WMB-R1 match that experiment's own published spend line exactly: judge proxy 2,833 calls and
  0.226 USD, writer proxy 120 calls and 0.009 USD ([`../wmb-r1-retrieval/README.md`](../wmb-r1-retrieval/README.md)).

## Totals by run id

| Run id | Model | Rows | USD | First and last row (UTC) | Rows added on 2026-11-12 |
|---|---|---:|---:|---|---:|
| `e1-writer-ds` | deepseek-flash | 3,672 | 0.7561 | 11-01 14:11 to 14:45 | 0 |
| `e1-judge-ds` | deepseek-v4-pro | 6,039 | 0.9670 | 11-01 14:15 to 14:50 | 0 |
| `e1-flash-judge` | deepseek-flash | 8,513 | 1.2417 | 11-01 14:52 to 19:00 | 2,472 |
| `e1-flash-writer` | deepseek-flash | 4,539 | 1.1445 | 11-01 15:23 to 16:15 | 4,539 |
| `e1-wmbr1-judge` | deepseek-flash | 2,833 | 0.2258 | 11-02 02:27 to 02:44 | 2,833 |
| `e1-wmbr1-writer` | deepseek-flash | 120 | 0.0088 | 11-02 02:42 | 120 |
| `e1-ppersona-writer` | deepseek-flash | 3,475 | 3.0074 | 11-02 11:36 to 17:51 | 3,475 |
| `e1-ppersona-judge` | deepseek-flash | 436 | 0.0502 | 11-02 11:51 to 11:52 | 436 |
| Total | | 29,627 | 7.4015 | | 13,875 |

## Limits of this reconciliation

- **Attribution to experiments is partial.** `e1-wmbr1-*` belongs to WMB-R1 and `e1-ppersona-*` to the persona battery
  (`aam-p-persona-v0`, `aam-p-persona-v1`); their configurations name these run ids. No published configuration names
  `e1-flash-writer` or `e1-flash-judge`. Their added rows fall between 15:23 and 19:00 UTC on 2026-11-01, the evening on
  which the flash re-judgments and the E3A, E5, E6 and E6E runs were made, but the split of those rows between experiments
  is not established here.
- **One stated cap does not match.** The persona battery's README gives a run cap of 2.5 USD per run id. The cumulative
  figure for `e1-ppersona-writer` is 3.0074 USD. The ledger cannot show whether the cap applied to each proxy launch
  separately or was not enforced. The slice stop of 4.0 USD for the two persona run ids (3.0575 USD together) and the
  12 USD phase cap were respected.
- **Identical rows.** 2,978 rows are exact copies of another row (same second, tokens and cost). The proxies write one row
  per call with one-second timestamps, so identical concurrent calls produce identical rows; the ledger has no call id
  that would tell a repeated call from a double write. The totals above count every row.
- **The pro-model rows are the known deviation.** All 6,039 `deepseek-v4-pro` rows precede 2026-11-01T14:51Z. They are
  the judging pass the owner objected to, described in
  [`../aam-e1ds-writer-memory-sim/README.md`](../aam-e1ds-writer-memory-sim/README.md); every later row is `deepseek-flash`.
- **Scope.** This ledger covers only the proxies of this phase. Arena spend of August 2026 is in
  [`../arena/spend-ledger.jsonl`](../arena/spend-ledger.jsonl), and later paid calls of the structured-memory work are
  recorded with that work. No project-wide total is derived here.
- The file keeps the proxies' Windows line endings; `.gitattributes` stores it byte for byte.
