# Exact source-handle citation and pack-order run v1

Status: completed synthetic development characterization after freeze `96c901f`
Authority: serialization capacity only; no reader, classifier, retrieval, or architecture claim

Advisory review: a compact DeepSeek M1 audit returned `accept_characterization_with_limits`; it is author-operated, not independent. Its findings and one corrected aggregation claim are tracked in `data/lab/api-screening/deepseek-v4-flash-pack-characterization-review-v2-20260823/audit-disposition.md`.

## Primary result

All 864 packs passed exact span resolution, byte-identical evidence, trust filtering, stale-marker, omission-ledger, and UTF-8 budget gates. Two fresh processes produced byte-identical `packs.jsonl` SHA-256 `4145c30546a24299e9c3a8a0283e5ddb0208a98b3d6d601723c1787d5f1e820c`.

At 768 bytes, averaged across the three frozen order arms:

| Format | Macro required retention |
|---|---:|
| Full inline locator | 0.701 |
| Compact source handle plus in-pack footer | 0.789 |
| Compact minus full | **+0.088** |

The compact-minus-full delta was `+0.111` in the registered long-locator stratum and `+0.074` when required records reused a source path. `H-PACK2-01` and the registered directional `H-PACK2-02` therefore pass on this visible fixture.

The registered primary average includes the non-deployable oracle arm, where both formats scored `1.0`. Excluding oracle descriptively, the compact-minus-full difference is `+0.132` across retrieval and governed order. This post-hoc value is useful for reader-protocol planning but does not replace the frozen primary calculation.

## Budget and order interaction

| Budget | Format | Retrieval order | Governed order | Required oracle |
|---:|---|---:|---:|---:|
| 512 | full inline | 0.375 | 0.347 | 0.931 |
| 512 | compact footer | 0.403 | 0.431 | 0.868 |
| 768 | full inline | 0.438 | 0.667 | 1.000 |
| 768 | compact footer | 0.549 | 0.819 | 1.000 |
| 1024 | full inline | 0.604 | 0.931 | 1.000 |
| 1024 | compact footer | 0.743 | 0.986 | 1.000 |
| 1536 | full inline | 1.000 | 1.000 | 1.000 |
| 1536 | compact footer | 1.000 | 1.000 | 1.000 |

The compact representation is not uniformly better. At 512 bytes in the required-oracle arm it scored `0.868` versus `0.931` for full inline because the `SOURCES` footer has a fixed cost and very small packs may not reuse enough paths. At 1536 bytes both cited formats fit all trusted records, so retention ties. Post-hoc paired case IDs and reversals are recorded in `posthoc-analysis.json` without retuning.

With evidence and format fixed, governed-minus-retrieval retention at 768 bytes was `+0.229` for full inline and `+0.271` for compact citations. At 512 bytes the direction was small and format-dependent; at 1536 it disappeared. `H-PACK2-03` passes only as evidence that ordering can change capacity under pressure. It does not show that a reader will use governed order better.

## Serialization cost

When the 1536-byte budget allowed every trusted candidate, full inline packs averaged `1278.2` bytes and compact source-footer packs averaged `1098.4` bytes, a descriptive saving of `179.8` bytes (`14.1%`). This is fixture-dependent and reflects its path lengths and source reuse.

## Decisions

- Preserve `C0_FULL_INLINE` as the simplest exact citation baseline.
- Advance `C1_SOURCE_FOOTER` to a fresh controlled reader experiment; do not make it the default yet.
- Advance `O0_RETRIEVAL` and `O1_GOVERNED` as reader arms. Keep `O2_REQUIRED_ORACLE` only as a capacity ceiling.
- Do not add LLMLingua, RECOMP, learned compression, retrieval, or automatic trust/bucket inference to the reader test.
- The future reader experiment must equalize included evidence IDs and bytes where possible. Otherwise format capacity and reader comprehension remain confounded.

## Limitations

- All records and labels are authored and visible.
- Required-source reuse is a registered case property, not a causal isolation of all candidate-path reuse.
- Greedy first-fit-with-continue is only one packing algorithm.
- UTF-8 bytes are provider-neutral but not equal to provider token counts.
- No model read the compact handles or footer, so citation emission, answer accuracy, stale use, and position bias remain unknown.
- No uncertainty or generalization claim is made from 24 constructed cases.

## Gate decision

The deterministic integrity and numeric reader-stage gates pass. This authorizes drafting and freezing a fresh reader protocol; it does not authorize an API call until condition blinding, answer-bearing cases, equal-evidence controls, scoring rules, model manifest, and cost cap are frozen.
