# PMLAB-PACK-001 pre-run audit

Status: failed instrument before runner implementation or outcome observation  
Frozen commit: `79137918d128cf6244c0462bd6b95fdac6ee39ea`

## Fatal construct defect

The frozen compact arm specified one handle for each complete `path:line-line` locator. All 36 fixture records have distinct line ranges. A footer would therefore contain one complete path and line range for every included record, while the evidence line would additionally contain a handle. It could not exploit multiple records from the same source path and would generally be at least as expensive as the full-inline arm.

This contradicts the intended source-reuse mechanism in `H-PACK-02`. Running the protocol would answer whether an intentionally redundant serialization loses capacity, not whether a compact source dictionary helps.

## Disposition

- Do not implement or run v0.
- Preserve its protocol, fixture, hashes, and registry row.
- Reuse the untouched fixture in a new frozen protocol because no outcome or runner exists.
- Repair only the treatment: map `[Snn]` to one source path and keep `Lstart-Lend` inline with each record.
- Continue to require a complete in-pack dictionary, exact span resolution, byte-identical evidence, and explicit omissions.

No hypothesis result exists for v0.
