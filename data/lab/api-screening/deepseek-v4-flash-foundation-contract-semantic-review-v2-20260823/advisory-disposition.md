# Disposition of DeepSeek Foundation contract semantic challenge

Status: reviewed author-operated advisory; `needs_revision`; not independent L5

Frozen input: `040faec`

Frozen raw response: `1d22765`

Response ID: `7ff880bb-dd4a-4cf5-a0b8-76d6598ed392`

Cost: USD 0.01086404; conservative project ledger after call: USD 0.99692120

The model returned all A01-A12 findings in the frozen schema, recommended both
contracts as `conditional`, denied the parent experiment, and made A11 same-author
bias blocking. This is a cross-family author-operated challenge, not completion of
independent semantic L5.

## Finding disposition

| ID | Disposition | Reason and next control |
|---|---|---|
| A01 | partial reject | The event schema already contains `source_object_sha256` and exact span, the validator compares both to raw bytes, and the contract explicitly says derived summaries are not canonical. Retain the useful stronger question: an unseen fixture should attack record-envelope/chain integrity, not claim the fields are absent. |
| A02 | partial accept | Accept an explicit as-of gate preventing later corrections from entering earlier knowledge states. Reject the proposed rule that a correction's `valid_from` must lie inside the original interval; late corrections and open intervals make that rule unsound. |
| A03 | accept | Freeze a separate payload-free denied-capture/governance receipt and test retention/access at exposure, not only capture. Synthetic construction does not test privacy enforcement. |
| A04 | partial accept | The validator already requires revision targets and causal parents to be earlier, which prevents simple cycles and missing targets. Add unseen concurrent-revision, conflicting-authority, and branch-merge cases. |
| A05 | partial accept | Keep F3 selection/context and F4 reader-use separate, but require hashed index snapshots, retrieval sets, context packs, and explicit corruption probes. Do not merge reader failure back into packing. |
| A06 | accept | Add correlated-probe, stale-cache, partial-corruption, replica disagreement, encryption-key-loss, and alternate-domain recovery cases. Key loss must be typed as effective unavailability unless physical-byte destruction is independently shown. |
| A07 | accept | Null hashes in the authored downstream receipts are a real construction weakness. Require a hash or an explicit typed `ephemeral_unavailable` reason and exercise unknown/skipped states. |
| A08 | accept | Git and a same-author receipt establish registered artifact order, not full process isolation. The unseen run needs OS/container allowlisting, no network, immutable external logs where feasible, and a different operator. |
| A09 | partial accept | The current fork is too homogeneous. Reject an unrelated *unanswerable* task as the repair. A second-author prefix should contain heterogeneous neutral evidence from several domains, then reveal answerable tasks whose required subsets and consequences differ. |
| A10 | partial reject | A reveal query is supposed to expose the future task and temporal scope; that is not answer leakage. The supplied queries contain no `Cedar` or `Birch` answer atom. Retain strict reader/gold storage separation and add a mechanical answer-atom leakage test. |
| A11 | accept blocking | A model hired by the author cannot remove same-author bias. No construction result advances without a different author/operator and unseen fixtures. |
| A12 | partial accept | Predefine semantic attacks across all dimensions. The model's `10 valid + 10 invalid` quota is an unpowered convenience, not a scientific threshold; sample breadth must be justified by dimension coverage and later error-rate estimation. |

## Decision

- Canonical contract: `conditional`; create v0.2 candidate only from accepted repairs,
  and never rewrite the frozen v0.1 construction.
- Delayed-reveal contract: `conditional`; the existing fork is spent and remains
  descriptive construction evidence.
- Independent L5: still absent.
- Parent `PMLAB-FOUNDATION-001`: denied.
- Product architecture: no decision.

## Next frozen work

Create a v0.2 second-author packet that asks for heterogeneous canonical histories,
denied-capture receipts, concurrent corrections, hashed/ephemeral stage artifacts,
unknown states, correlated recovery faults, OS-level prefix isolation, answer-atom
leakage attacks, and multiple answerable future-task families. The author may define
the contract and scoring rules, but must not author the unseen subject traces or
their semantic verdicts.

