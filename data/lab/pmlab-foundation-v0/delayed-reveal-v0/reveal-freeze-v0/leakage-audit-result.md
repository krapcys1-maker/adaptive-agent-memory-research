# Foundation delayed-reveal leakage construction result v0

Status: authored mechanical L0-L4 passed; L5 independent semantic review absent

The prefix contract and prefix-only access boundary froze at `f998082`. Reveal,
gold, schedule, and 14 invalid mutations were authored later and froze at
`2bf9813`. Git confirms that the reveal/gold tree does not exist in the prefix
commit and that the prefix commit is an ancestor of the reveal commit.

Auditor v0 froze at `5a08f8a` and failed before producing a result because generic
join checks masked two registered mutation reason classes. That failure is retained
in `AUDIT_FAILURE_V0.md`. The fixture, thresholds, and expected errors were not
changed. A one-line validation-order repair froze at `d04377f` before the successful
run.

## Result

- `L0_BYTE_FIELD`: pass — exact commit bytes, opaque IDs, field boundaries, and
  forbidden prefix fields validated;
- `L1_LEXICAL`: descriptive only — no pass/fail claim;
- `L2_PROCESS_ACCESS`: pass — observed reads remained inside the prefix-only
  allowlist and later artifacts were absent from the prefix commit;
- `L3_COUNTERFACTUAL_FORK`: pass — one byte-identical prefix supports three task
  families, three incompatible answer states, and three required-evidence sets;
- `L4_REPRODUCIBLE_BUILD`: pass — ordered event IDs and payload bytes reconstruct
  from the prefix source commit without the reveal tree;
- `L5_INDEPENDENT_SEMANTIC`: not performed.

All 14 registered invalid mutations were rejected for their registered reason
class. Targeted tests passed 4/4 and the full repository suite passed 289 tests with
two pre-existing SWIG deprecation warnings. No API call was made; cost was USD 0.

## Claim limit

This is same-author mechanical construction evidence. It does not prove author
blindness, semantic independence, operational memory quality, or architecture
value. The parent `PMLAB-FOUNDATION-001` remains locked.

Next gate: freeze a blinded L5 review packet for an independent reviewer and obtain
an unseen second-author prefix/reveal fork. Do not repair the spent construction
fixture in place.

