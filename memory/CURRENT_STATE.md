# Current project state

Latest completed local upgrade: [report](../data/lab/local-model-upgrade-v2/README.md) and [delivery receipt](../data/lab/local-model-upgrade-v2/delivery.json). H1 memory-on 14B 73/84 versus 9B 82/84; BEAM memory-on 39/200 versus 40/200, memory-off 19/200 for both. Four unsupported 9B memory-off answers and the fixed gain screen prevent promotion. Gemma stopped at 251/655 with no full score. Task 1,564 local / zero paid; PR105 total 6,388. The existing result head 0688e9b has 12/12 successful CI jobs (3,587 passed / 21 skipped per Linux Python 3.11/3.12) and an actual verified private restore. Defaults, judge and personality remain unchanged; only unused Llama3/LLAVA were removed with reinstall identities saved.

Continuity is finalized in [HANDOVER](../HANDOVER.md); three superseded local-upgrade sections are preserved verbatim in [stage history](../data/lab/local-model-upgrade-v2/stage-history.md). No scoring, Gemma resume or spare-budget run is pending. Registry remains 88 historical rows; canonical memory is 378 events with its prior 377-event prefix preserved. This documentation update adds zero model calls; later documentation heads have separate PR checks. Dated phase records below describe earlier states.

## Objective

Research a local-first, model-agnostic long-term memory layer for LLM agents. The model context window remains working memory; durable evidence, experiences, conclusions, and procedures live on the user's disk.

## Current phase

Latest engineering continuation2026-11-05: [evidence diagnosis](../data/lab/beam-evidence-boundary-v2/README.md),200cases/176annotated/24missing.1326slots (1unresolved),1216notretrieved; all targets shown16/176only. New literal context preserves known example heading but reduces705windows to390and all-target cases16to15: experimental interface only, no adoption/semantic completeness/new score. V1strict-marker failure retained; v2amend50e12e4 before full pass.117focused tests/full200packet1326slot replay zero;3forged copies rejected.0newinference; counters unchanged. Registry85historical rows. General prose modality remains unresolved; retrieve sufficient source/instruction evidence next. Latest HANDOVER controls continuation.

Delivery verification: result/source50158dd has12/12successful CI jobs,3447pass/21skip on both Linux3.11/3.12. [Receipt](../data/lab/beam-reader-evidence-v1/delivery.json) binds verified GitHub writes (#51/#7/#84/PR105/new#110) and an actual clean private restoration (220files/78refs/fsck0). Later delivery/docs need their own CI. Memory371events/0violations; no new inference or integration. The completed study below remains rejected.

**Latest completed reader study (2026-11-05):** [full BEAM result](../data/lab/beam-reader-evidence-v1/README.md),200probes/10histories,605local/0API. Authored conservative N19/B39/Craw31/Cdel32 of200;8reference cases uncertain. N's passes are abstention; non-abstention N0/B29/Cdel14 of180. B→Cdel8gains15losses; contradictions39→14 but one new case; two correct raw answers lost to guard. Reject adoption under the prior screen. Not official/independent/blind/general-memory or old-graph transfer evidence. Protocol439f9c7/matrixb8e3f83/raw64f7f0b precede references.57focused checks; executed-head CI12/12success,3434pass21skip per Linux3.11/3.12. New task ledger605/650; H13262/3300 and paid463 unchanged; cumulative4824=4361local+463Flash. Source frame can be lost despite valid literal spans: next inspect modality/context and evidence completeness, with no automatic new paid run or NIE change. Registry83historical entries; latest HANDOVER controls continuation.

**Latest external-transfer stage (2026-11-05):** [BEAM format/evidence audit](../data/lab/beam-transfer-format-v2/README.md) completed for all10pinned conversations:187,734messages/200probes, exact reconstruction, reader/evaluator separation. V1partial success/full-data null-time failure retained; v2 preserves unknown time.6focused checks,0model calls, no memory accuracy/official score.30,177texts exceed old4500byte cap and187,054scoped role/text keys are distinct: next work is bounded provenance windows/capture cost, then a full frozen model comparison. Caps/ledgers unchanged (H13262/3300,API463/$1.852), prior4219inference attempts unchanged. Registry80historical rows; memory366events/0violations. HANDOVER has exact freezes; NIE/old code/data preserved.



**Active laboratory (2026-11-05):** [operating view and positioning](../docs/11-research-laboratory/active-lab-2026-11-05.md). Source-grounded state-memory prototype plus existing research instruments; no unique architecture or validated product. APEX/Graphiti/CAR overlap the main ideas. One next common-protocol external comparison under#51/#7; concepts remain a ranked backlog. Freeze the whole pipeline before unused data, keep true N/ordinary retrieval/candidate/competitor separate, and report full cost/failures. No new inference or cap extension. Code/results58bdcfc CI12/12, full3377pass/21skip on each Linux3.11/3.12 ([receipt](../data/lab/h1-chronological-pack-v1/delivery.json)); later docs are separate. Memory365events/0violations. Read the latest HANDOVER before historical blocks below.



**Owner clarification (2026-11-05):** [true baseline coverage, publication age and fitting risk](../docs/05-benchmarks/memory-baselines-and-benchmark-age-2026-11-05.md). Existing N/V and original hard local N/K controls are preserved; the later structured55/59 has no contemporaneous matched N, and H1 base is memory-on. Old-model competitor results are historical, not a current ranking. Public MAB/H1 reuse leaves unresolved overfitting risk; freezes/no direct gold do not establish generalization. Full pipeline must freeze before unused external data. Reanalysis matched400old requests/384contexts without new inference; memory364events/0violations. All call/cost caps and non-adoption decisions below remain unchanged.



**Latest continuation — 2026-11-05:** [HANDOVER](../HANDOVER.md) has the exact freezes and costs. Completed [density](../data/lab/h1-evidence-density-v1/README.md):147local, one devQ000045 stale leak in repeat-old/correction-first, other five arms24/24. Completed [all-family order comparison](../data/lab/h1-chronological-pack-v1/README.md):339local, dev77→75/84, valid70→72/84 and2→0leaks; only17reordered pairs,151same-message controls. Same-seed native variability and a mechanical scorer wording miss are explicit. Fresh-transfer candidate only, no adoption. The historical v5 results76/71 remain unchanged.

H1 ledger3262/3300 after prior explicit amendment; PR105 total4219attempts (3756local/463Flash). No new API, reservations$1.852/usage upper estimate$0.073913 unchanged; local worker unloaded. New packet audits480primary, zero failures; pinned focused tests10pass. Earlier full3372/20 and12-jobCI receipts apply to their recorded heads. Registry79rows with old prefix/history preserved. [Competitive calibration](../docs/05-benchmarks/mab-comparison-and-model-bottleneck-2026-11-05.md) includes CAR41% at262K alongside older reference points: our55/59exact (55/60secondary SubEM) is promising development evidence, not a matched company ranking. Next work is a common-protocol external comparison, not single-case tuning. NIE/old worktrees/frozen code/shared plan remain unchanged.

The older blocks below are preserved historical snapshots; their pending experiments and caps/counts are superseded above.



**Current continuation (2026-11-05):** [HANDOVER](../HANDOVER.md) supersedes older
status snapshots. Audit committed/pushed at `5eeb8cc`; new boundary code at
`b353695` passes focused checks and all 12 CI jobs. Exact-text replay prevents
the reproduced shell generalizations, but has zero reuse opportunities for
18,223 previously template-served MAB sources; safe efficient capture remains
open. New scoped/time-bounded query packets preserve 100 old MAB packets and
200 saved executions. Legacy claims are not retroactively revalidated.

[Whole-family local controls](../data/lab/h1-obsolete-controls-v1/README.md):
original packs 23/24 answered with one stale leak (valid Q000043), oracle-only
and both two-note orders 24/24 each without leakage. This is an oracle-ID
diagnostic, not automatic memory transfer or a fix for the original pack.
99 new local generations, zero API; H1 ledger 2776/2800, API unchanged at
463 calls/$1.852 reserved. PR105 total 3733 attempts (3270 local/463 Flash).
Full gates in both global and isolated pinned environments: 3372 pass/20 skip,
memory/claim checks pass; pinned pip check is clean. No global package/NIE change.
Community issues #106–#108 and PR105 are updated. One next repetition/neutral
volume study is designed but not run; its 147 calls exceed the 24 remaining
local attempts and require a prior explicit amendment. No ledger reset.

**Current integrity self-audit (2026-11-04):** read [AUDIT_REPORT](../AUDIT_REPORT.md)
and [HANDOVER](../HANDOVER.md) before the older snapshots below. A private
backup was actually restored and checked. Original worktree/NIE/frozen-path
preservation checks pass. The new candidate has confirmed HIGH defects:
conditional/compound cache assertions, future learned-schema prompt leakage,
and a remaining stale reader answer. PR105 stays draft; no general readiness
or deployment claim is supported. No feature repair, commit/push or new model
call occurred during this audit.

H1 v5 completed: dev base 62 -> 76/84 `answered`, OBSOLETE leaks 12 -> 0/12;
valid base 66 -> 71/84, leaks 9 -> 1/12. Valid includes 11 gains and 6 losses;
case Q000043 is stale despite a shown correction. Gold source retrieval 84/84
does not imply correct answers. V5 adds Flash source reranking/context and
inherits frozen v4 baselines; it is not a pure-chain or equal-cost effect.
PR105 totals 3634 actual generation attempts (3171 local/463 Flash), permanent
paid reservations $1.852 and recorded usage upper estimate $0.073913, not an
invoice. Last full suite: 3041 pass/20 skip; current published CI: 10 successes
and 2 macOS cancellations for runner capacity. Local environment has nine pip
conflicts and pytest 9.1.1 versus pinned 8.4.2. See audit receipts for scope.

The following engineering and delivery entries are historical snapshots;
pending-H1 and earlier call-count statements are superseded by this block.

**Active engineering delivery (2026-11-04, PR #105):** the separate
[structured runtime](../data/lab/structured-memory-v1/README.md) now completes
raw text capture, model-derived literal claims, state/provenance and executable
question paths. On the same spent FC-MH262k100 development questions it scores
local 55/100 and Flash 59/100 exact; the 80/100 aspiration is unmet. These are
system-computed answers, not raw reader scores or a leaderboard comparison.
Post-hoc Flash SubEM is 60; only 64 enumerated schemas contain gold, and a
fixed-plan oldest-state intervention scores 1. Capture retains four quarantines.
The [complete fact-only H1 comparison](../data/lab/h1-model-chains-v1/README.md)
is negative: derived chains leave OBSOLETE leakage at 12/12 dev and 9/12 valid,
with no answering gain. Evidence-kind addressing and literal case grounding
are being executed as explicit amendments; their success is not assumed.
All earlier negative artifacts, frozen kernels and NIE ownership remain intact.

**Latest audit verdict (2026-11-04):** [the delivery audit](../docs/00-project/project-delivery-audit-2026-11-04.md)
finds working continuity tooling, modules and substantial experiments, but no
validated generic adaptive memory product. On the [complete hard 100-question
262k variant](../data/lab/hard-memory-external-v1/README.md), the ordinary raw-line
kernel adapter scores 0/100 exact on both Qwen 14B and Flash; unlocked BM25 scores
1/100 and 4/100. A post-hoc local iterative follow-up reaches only 4/100 after
402 primary rounds; two evidence-complete Flash audit controls score 1/2.
These are scoped adapter/reader diagnostics, not the whole project's score.
The authors' FC-MH baselines are also low under different settings; the 80%
bar is our self-set aspiration, not a calibrated industry readiness standard.
The existing AAMR-CANDIDATE-0 is domain-limited and resolves 0/100 addresses on
that corpus; its earlier 0/4 external pilot was already a known negative result.
Generic capture/addressing and integrated delivery remain open. NIE's local
history path is limited to two entries from 60 days in E23 on; its separate
shadow does not change prompts. Deployed server state is not verified.

**Prior controlled boundary:** the [matched reader comparison](../data/lab/reader-model-compare-v1/README.md)
retains its narrow result: eight authored slots with supplied routing/typed
claims, local V 48/48 raw and Flash V 46/48 raw to 48/48 delivered. It does not
solve free-text capture or general transfer. P2's failed stability reading,
LifeSim's four development validity failures and R1's judge limitation remain.

**November orientation (2026-11-04):** the [laboratory map](../docs/11-research-laboratory/lab-map.md)
is the entry point for AAM writing-memory experiments, the persona battery, WMB,
the shared kernel and LifeSim. Persona corrections are integrated; new runs use
the [v1 entry point](../data/lab/aam-p-persona-v1/README.md). Kernel mutations and
CLI `verify` provide mechanical checks. LifeSim portability does not establish
instrument validity: its unresolved development gates and unrun confirmation
experiments remain explicit. Read each experiment's latest results/amendments;
preserved preregistration headers can describe an earlier state.

Evidence collection and gated laboratory testing, run in three parallel tracks — engine, experiment, community — under [`docs/00-project/operating-doctrine.md`](../docs/00-project/operating-doctrine.md). New preregistrations are paused until the existing unexecuted drafts are triaged. No validated final architecture is claimed.

## How to read this file

This is the **short** current state. The full diagnostic history lives in [`DIAGNOSTICS_ARCHIVE.md`](DIAGNOSTICS_ARCHIVE.md), which is indexed and searchable but deliberately not forced into every context bundle. Nothing was deleted when it was moved out.

## What the memory tool now is

Git-tracked append-only JSONL plus reviewed Markdown is canonical. SQLite FTS5 is a disposable index. MCP stdio serves Codex, Claude Code and other clients; the CLI is the documented fallback. No model API key, vector database, graph database, or cloud account is required. External API models are optional, replaceable batch workers; they may write review candidates but never accepted evidence.

**Schema version 2** carries valid time. `created_at` and `expired_at` are transaction time, `valid_from` and `valid_to` are valid time, plus `claim_class` and `supersession_kind`. The two end-of-interval fields are **derived from the successor at read time**, never stored, because an append-only log cannot edit the record it ends and a stored end could drift from the revision that caused it. Version-1 events still read correctly through `tools/project_memory/upcast.py`.

## What is mechanically enforced

- CI runs the suite on Python 3.11 and 3.12 and blocks on the repository claim audit.
- `scripts/verify_memory_integrity.py` checks every invariant decidable from the bytes of `events.jsonl`, measured by 21 registered mutations.
- The canonical-store guard fails any pull request that deletes or rewrites a line of the log, or commits the disposable index.
- `.gitattributes` disables end-of-line conversion, so a declared hash reproduces on every platform.

## Settled this phase

- **Association graph as retrieval fusion: closed, negative.** `PMLAB-ASSOC-E1` inconclusive, `E2` retracted as a leakage artifact, `E3` measured harm at −0.114 Recall@5 on mechanical gold. The flaw is seeding expansion from lexical hits, which helps in neither regime. The graph is retained as *structure*, not as fusion.
- **Supersession cannot be solved by retrieval.** `PMLAB-STALE-E1`: a superseded fact and its replacement sit at the 99.5th percentile of corpus similarity, two pairs at cosine exactly 1.000. It must live in the schema.
- **Cross-language retrieval.** `PMLAB-XLANG-E1` measured Polish Recall@10 at 0.156 against English 1.000, with 26 of 45 queries returning nothing. A glossary lifted it to 0.867; local dense retrieval reached 0.978 in `E2`, but its safety cost is unmeasured and dense makes stale intrusion structurally worse.
- **Provenance repair.** 843 of 1348 lab files diverged between working copy and blob; now 0. Six broken freezes resolved as two distinct defects. Zero critical audit findings.
- **Both time axes are needed.** `PMLAB-REV-V0` compared five temporal resolvers: bitemporal reached exact 0.944 with perfect `valid_at`, zero leaks and zero critical failures, while each single-axis arm failed precisely the question the other axis answers. Caveat that bounds the claim: every arm scored 1.00 on `current`, so the value exists only in historical questions.
- **Tier I3 cannot be instantiated yet.** `PMLAB-DECORR-E1` found the one two-reviewer dataset has gold derived from the labels being measured, and the one gold-free mechanical dimension produced zero errors, so correlation is undefined rather than zero. Any claim resting on a model panel is recorded as `asserted`.
- **Reflection Stage 1 is exact-only.** Five detectors, each proven to fire on a constructed case. A polarity contradiction detector was written and removed after measurement: all four of its hits on the live corpus were false positives, because this project's prose is saturated with negation by design.

## Open blockers

1. Dense retrieval is **not** adopted. Its recall case is settled; its safety case is untouched and needs forbidden and stale intrusion measured against the new valid-time labels.
2. Independent review remains the scarcest tier. Four packets need it; the [independence ladder](../docs/00-project/independence-ladder.md) exists so that most claims no longer do.
3. Of 21 unexecuted preregistrations, 0 have a corpus and 18 need a reader model. The binding constraint was never reviewer scarcity — it is that no fixture exists.
4. Key grinding in the sealed split cannot be prevented offline. The manifest records whether a key was externally witnessed.

## Immediate priorities

1. Build one corpus family. Four fixtures would unblock sixteen experiments; treating the drafts as 21 separate items is why none moved.
2. Measure dense retrieval's forbidden and stale intrusion before considering any index change.
3. Run the six-round coverage protocol and repair the distinction between discovered, screened, read, and independently reviewed sources.
4. Fully read and snowball the comparative source seeds for animal, motor, skeletal-muscle, immune, transcriptional, non-neural, CRISPR, and collective memory.
5. Test emotional salience only after utility labels and consequence-weighted retention metrics exist; never equate operational signals with subjective emotion.
6. Preserve rejected ideas, null results, and failed runs as labeled evidence.
7. Run a synthesis checkpoint after 25 screened records or three newly primary-read decisive sources in one topic.
