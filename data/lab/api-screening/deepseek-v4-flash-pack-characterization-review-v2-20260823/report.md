# DeepSeek advisory review of PMLAB-PACK-001/002

Status: finalized M1 author-operated model review; not independent validation

Verdict: `accept_characterization_with_limits` (confidence 0.88).

## Required claim boundary

Claims are limited to deterministic serialization capacity on a visible authored 24-case fixture. No reader, classifier, retriever, or architecture selection is supported. O2_REQUIRED_ORACLE is a non-deployable ceiling and should not be used for deployable comparisons. Fresh reader protocol with blinded conditions and equal evidence controls is required before any API use.

## Fatal issues

- None reported.

## Major issues

- Reader-stage gate conflates numeric retention difference with reader comprehension readiness; fresh reader protocol still required.
- O2_REQUIRED_ORACLE included in primary 768 average, inflating compact-minus-full delta; non-deployable ceiling should be excluded.
- No statistical uncertainty or effect-size confidence reported; 24-case authored sample limits generalization.

## Minor issues

- Source-reuse stratum uses case-level property, not per-record reuse isolation.
- Greedy first-fit packing is only one algorithm; sensitivity not assessed.
- UTF-8 bytes not provider token counts; cost claims limited.

## Claims supported

- Compact source-footer improves required retention over full inline at 768 bytes on this fixture.
- Improvement is present in long-locator and source-reuse strata.
- Governed order can change retention capacity under budget pressure.
- All integrity gates pass for the deterministic serialization.

## Claims not supported

- Reader comprehension or citation emission benefit.
- Natural transfer or generalizability beyond authored fixture.
- Provider token cost equivalence or savings.
- Architecture or reader-order selection authority.

## Next required tests

- Fresh reader protocol with blinded condition labels and answer-bearing cases.
- Equalize included evidence IDs and bytes across formats to isolate comprehension.
- Exclude O2_REQUIRED_ORACLE from primary deployable comparisons.
- Sensitivity analysis with alternative packing algorithms and budget granularity.
