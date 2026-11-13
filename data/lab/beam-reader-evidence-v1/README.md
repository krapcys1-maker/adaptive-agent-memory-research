# Full BEAM local reader comparison: citation contract rejected

All200probes/10histories/10abilities executed,605local calls including five passed controls. **Reject adoption of this new read-time variant.** It delivers fewer complete-rubric passes than raw lexical retrieval and introduces one newly assessed material contradiction. It reduces many wrong assertions by refusing more often, but does not solve the hard task. This is Codex-authored exploratory assessment, **not official BEAM accuracy, independent confirmation or transfer of the earlier55/59graph method**.

## Fixed comparison and freezes

[Protocol](PLAN.md) and runner frozen439f9c7; complete matrix frozenb8e3f83 before inference. Exact installed Qwen2.5 14B Q4_K_M digest and options pinned; no other model, API, judge, planner, retry or fallback. Complete [raw receipt](raw-freeze.json) committed64f7f0b **before** the first semantic reference join. [Native replay](artifact-audit.json) reconstructs all605requests/responses and200identical B/C evidence pairs with zero failures. All600primary outputs parse and stop normally; no native length truncation. Model identity unchanged and owned worker unloaded.

N sees no evidence; B sees ordinary lexical windows; C sees exactly B's evidence plus a quote/unknown output contract. Long window IDs are aliases with canonical mappings. A common6000byte complete-message limit applies; max5999bytes, full native request max6647under10000cap. Different schemas/prompts cost different compute. No extra semantic capture at ingestion; this is not the earlier graph candidate or a competitor reproduction.

## Authored semantic result

Reviewed all382distinct within-question answer texts against the fixed original rubrics. Candidate arm names masked in the review packet; identical text deduplicated only within a question. Author knows the experiment and inspected common/full sources in ambiguous cases, so this is **not fully blind**. Each candidate has a private final verdict/reason; the public [content-free verdict projection](authored-verdict-projection.json), [review manifest](review-manifest.json) and [complete score](score.json) bind the evidence without uploading private text.

| Arm | Conservative complete-rubric passes | Authored material contradictions |
|---|---:|---:|
| N: no memory | 19/200 | 0 |
| B: raw lexical | 39/200 | 39 |
| C raw | 31/200 | 20 |
| C delivered | 32/200 | 14 |

All200remain in the denominator. Eight reference cases are flagged (3defective/5ambiguous), treated as uncertain failures in the conservative primary count. Possible pass-count bounds are N19–27, B39–47, Craw31–39, Cdelivered32–40; these overlapping sensitivity bounds are not confidence intervals. Within usable references, judgement and rubric completeness remain fallible. No significance, equivalence or current-company ranking claim.

B→Cdelivered:24both pass,8gains,15losses,153both fail. B→Craw:5gains/13losses. Cguard loses two correct raw answers (BEAM10M-5-Q0011 and7-Q0015) and converts three raw abstention errors into correct refusals, net+1versus Craw. The newly assessed delivered contradiction is3-Q0011. Its Banswer refers to regression tests, while C's bare count answers the integration-test question incorrectly; this authored distinction is not independent adjudication. The quality-gain screen fails regardless.

N's19passes are all appropriate abstention. On the180non-abstention probes, N0, B29, Cdelivered14. This is not standalone model intelligence or a demonstrated retrieval ceiling. Every lexical pack omits candidates; limited evidence, the quote requirement, output constraints and model reasoning can all contribute. We have not quantified semantic evidence completeness or the model-given-complete-evidence ceiling.

| Ability | N | B | C delivered |
|---|---:|---:|---:|
| abstention | 19/20 | 10/20 | 18/20 |
| contradiction resolution | 0/20 | 0/20 | 0/20 |
| event ordering | 0/20 | 0/20 | 0/20 |
| information extraction | 0/20 | 12/20 | 9/20 |
| instruction following | 0/20 | 5/20 | 1/20 |
| knowledge update | 0/20 | 7/20 | 4/20 |
| multi session reasoning | 0/20 | 0/20 | 0/20 |
| preference following | 0/20 | 5/20 | 0/20 |
| summarization | 0/20 | 0/20 | 0/20 |
| temporal reasoning | 0/20 | 0/20 | 0/20 |

Zero complete passes on multi-session reasoning, event ordering, summarization and temporal reasoning are substantive failures. The written temporal rubrics require both duration and endpoints: a correct bare duration still fails the complete-rubric criterion. Some instruction/preference rubrics only require a named item or numeric content and do not fully validate factual accuracy; these weak criteria are documented in private review notes, not expanded after outputs.

## Reference and provenance failures

Confirmed source/reference defects:2-Q0000demands abstention despite assistant debugging steps for the same error being in the visible history;2-Q0019requires2025dates although cited original messages anchor2024;3-Q0019conflicts between an11day answer and12day rubric. Other ambiguous cases conflate a future target with completion (4-Q0002), considering a move with having moved (7-Q0002), current-trip experience with pre-trip experience (8-Q0002), another person's coordination with the user's own actions (10-Q0003), or epsilon-delta wording with an epsilon-N sequence proof (5-Q0008). No reference was rewritten and no inconvenient case dropped. Source-level authority still matters: an assistant proposal is not automatically an observed user fact.

In7-Q0000, the raw Banswer presents a hypothetical example quotation from a retrieved suffix as actual past advice; Crefuses that case. Full source BEAM10M-7-M007239 has an Example Scenarios heading omitted from that suffix. The origin role and partial-source flag survive; the semantic frame does not. This is a concrete mode/context-loss failure, not permission to treat all source quotes as true. [Synthetic regression](../../../tests/test_beam_qualifier_counterexample_v1.py) shows a literal guard accepting a non-observed recommendation while offsets and full-source reconstruction remain valid. A passing test reproduces this limitation; it is **not a repair** and makes0additional model calls.

## Cost, engineering checks and decision

| Arm,200primary calls | Native prompt count | Native generated count | Median wall seconds | Sum wall seconds |
|---|---:|---:|---:|---:|
| N | 31805 | 1260 | 0.3290 | 69.293 |
| B | 281845 | 7116 | 1.8045 | 475.225 |
| C | 298445 | 9933 | 2.0705 | 588.377 |

All605native prompt/eval counts: 613469/18390; these are service-reported counters, not a tokenized full-corpus measurement. Reader phase1176.156seconds including controls/load/overhead; C/Bmedian ratio1.1474. Complete private reader archive 5918045bytes. Source ingestion also costs [74.812seconds/2,616,798,059outputbytes](../beam-source-windows-v1/README.md), including2,159,546,368databasebytes;0ingestion model calls does not mean zero ingestion cost. Retrieval preparation for200queries takes14.718seconds within that stage.

New BEAMledger605/650, historical H13262/3300unchanged. PR105cumulative4824attempts=4361local+463Flash. Paid cap500/$2, reservations$1.852/recorded usage upper estimate$0.073913unchanged;0newAPI. No electricity/portable dollar estimate invented. [Supplement](supplement.json) includes duplicate-answer and accounting diagnostics.

[Three forged private-copy traces](audit-mutations.json) are rejected, including rebound hashes for a changed native request or delivered answer; unmodified605call copy replays successfully. Original outputs are untouched and no model is called. 57focused checks pass, including33window,13reader,10review-boundary and one qualifier counterexample check. [Execution-head CI](execution-head-ci.json):12successful jobs,3434passed/21skipped on each Linux3.11/3.12, applying tob8e3f83; later evaluator/result/docs commits need their own CI. [Preservation](../beam-source-windows-v1/preservation.json) matches14old worktrees/32035files,NIE/shared plan/20frozen paths. No original dirty checkout, old runner/result, persona, integration or deployment changed.

Prespecified screen: quality gain **fails**, no-new-contradiction **fails**, <=2xmedian latency passes. Decision is **reject adoption**, preserve this result and treat BEAM as development for any subsequent tuning. Next admissible engineering work is preserving evidence modality/context and measuring evidence completeness before spending on another broad reader run. General efficient capture, old graph transfer and a matched competitor remain open. This single public, small-context, one-seed exploratory run has ten history clusters, not600independent observations.
