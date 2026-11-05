# Local model-derived chains on H1 development and validation

Issue #47 still needs the result it actually asks for: stale-answer leakage from
chains derived from raw text. After the completed hard-suite implementation,
run this existing missing arm, not another architecture proposal.

Only H1 prefix-v0 (development/dev-a) and valid-b history/queries are allowed.
Never open construction-labels or sealed-c. Extraction receives **text only**,
no event ID, family, gold, question or construction property. Source IDs in model
prompts are opaque. Model proposals use the unchanged v2 extraction prompt and
native local schema. Every source is saved first. Exact-duplicate text can reuse
a prior literal-grounded proposal with explicit derivation/source provenance;
this is not another generation. Keep all empty and quarantined sources.

For each of all 84 questions in each split, compare a matched base and chain arm
using the same frozen kernel lexical ranking, local Qwen 14B, seed 7, three-note
and 4500-byte cap. The chain arm looks up a retrieved note's derived
(subject,predicate) keys and promotes its newest available chain source; it
then fills from the ranked notes. No oracle chain/label map. **Rank is a retrieval
prior, not a truth predicate**; the reader still sees raw notes and dates.
Nothing is written during questions. No missing answer creates a new fact.

Freeze complete raw outputs before separate scoring uses the existing H1
mechanical answer/leak marker scorer. Report every family, not only OBSOLETE:
answering, leakage, gold/forbidden retrieval, abstention, empty capture,
quarantines, call counts and timing. Report historical no-chain .833 and oracle
.000 OBSOLETE bounds with their different reader/protocol warning, and the
matched local base. Do not claim a cross-model .833->X gain as matched evidence.

Exploratory development target: derived chains reduce OBSOLETE leakage compared
with the matched base without reducing OBSOLETE answering. Other-family
regressions remain visible. The old E2-A stale-context gate and previous failures
are not relabelled as passed. A negative result is retained and diagnosed.

Local only, no API calls. Four phases (capture/read for each split), <=600 actual
attempts and 3600 seconds per phase, **<=1200 attempts cumulatively**, enforced by
one append-only local ledger and exclusive client lock. Native output cap 512,
context 4096, installed pinned Qwen 14B only, one GPU, no downloads or retries.
Stop on a failed transport control. No model judge/project planning, NIE edits,
frozen-kernel changes or deployment. Models only exercise the implemented memory
mechanism. Commit code, tests and this plan before any generation.
