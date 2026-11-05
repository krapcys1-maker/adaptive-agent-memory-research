# Evidence diagnosis: the bottleneck is not just the reader

Model-free follow-up to the [completed rejected BEAM reader study](../beam-reader-evidence-v1/README.md). The whole176-case annotated subset has every declared source represented in only16final packets (28at the16candidate stage). A new literal context envelope exposes the lost example heading in the known regression, but its byte cost removes315of705previously selected windows. **Accept only the inspectable structural interface; keep the packet variant experimental and do not adopt it as a better answer method.** No new model call, score repair or independent confirmation.

## Complete coverage diagnostic

[Original protocol](../beam-evidence-boundary-v1/PLAN.md) frozen5b70e0e before processing. V1stopped on an explicit `--` reference marker in6-Q0004; its started/failure evidence and code remain immutable. [V2amendment](PLAN.md) frozen50e12e4 before the second corpus pass retains that marker as an unresolved target slot, with no guessed source and no target-denominator deletion. [Failed original receipt](failed-v1.json).

All200questions/10histories/10abilities remain in the report.176cases have nonempty reference declarations;24have no source_chat_ids field (20abstention and4summarization), not zero-evidence retrieval successes.1326declared slots:1325unique-per-case numeric references, one unresolved marker. All1325numeric references map exactly to original scope-specific messages;0archive misses. Sources1244user/81assistant. No IDs are guessed from expected answers, question wording or an ideal response.

| Fate of declared source target | Slots |
|---|---:|
| Explicit unresolved marker | 1 |
| Available but outside16lexical candidates | 1216 |
| Retrieved but omitted by complete-message budget | 34 |
| Source represented partially | 5 |
| Source represented fully | 70 |

Any declared source appears in74/176candidate sets and56/176final packets. All targets appear in28candidate sets and16final packets; those16also retain full source text for each declared target. The unresolved slot prevents an all-target result for its case. Targets are counted once per case; overlap/repeated windows do not inflate character coverage. [Full summary](result.json), [all200content-free case metrics](case-metrics.jsonl).

| Ability | Cases with reference field | All targets in16candidates | All targets shown |
|---|---:|---:|---:|
| abstention | 0 | 0 | 0 |
| contradiction resolution | 20 | 7 | 4 |
| event ordering | 20 | 0 | 0 |
| information extraction | 20 | 12 | 9 |
| instruction following | 20 | 0 | 0 |
| knowledge update | 20 | 6 | 2 |
| multi session reasoning | 20 | 0 | 0 |
| preference following | 20 | 2 | 1 |
| summarization | 16 | 0 | 0 |
| temporal reasoning | 20 | 1 | 0 |

Five families have0complete target-source packets: event ordering, instruction following, multi-session reasoning, summarization and temporal reasoning. This does **not** establish a model or semantic-memory ceiling. An annotation may omit alternative evidence or contain unrelated/defective targets, and message presence alone does not show that all needed facts were understood. Existing Bhas12passes/4failures among16all-shown cases,6/34among40some-shown,11/109among120none-shown and10/14among24without annotations. The11passes with no declared target shown explicitly prevent interpreting this proxy as necessary-and-sufficient evidence recall. These are descriptive cross-tabs of already frozen authored verdicts, not causal failure adjudication or a new answer score.

## Structural context successor

New `tools/source_context_v1.py` validates each immutable window against its full original source and attaches exact Unicode/UTF8spans for the **complete first nonblank paragraph** and active ATXheading ancestry. It includes both ancestries when a window crosses a section boundary. Nested headings close at an equal/shallower level; declared fenced-code rules exclude heading-like code. Origins, source hashes, scope/cutoff and canonical window mappings survive. Source text remains data in the user message; it never changes native roles or grants authority.

The builder receives **no reference IDs, rubrics, expected answers or authored scores**. It keeps the old matched B/Cselected candidate order and Bsystem, adding complete dependencies before checking the same6000byte UTF8/native-escaped complete-message cap. It omits an unaffordable unit whole, with an explicit reason; no prefix cropping to get a pass. All200new packets are nonempty, max5995bytes.705old selected windows→390new;197packets lose windows.314units fail remaining-budget capacity and one cannot fit even alone. All-target case coverage16→15on the same annotated subset. Shown literal dependencies total106909UTF8bytes, including charged repeated context; this is not a model-token estimate.

Known7-Q0000sourceM007239 remains selected and now includes the exact Example Scenarios heading that old text omitted. This only makes the frame available. **No new reader was run to establish that it uses the frame correctly.** A full archive/query example is not uploaded. Source ingestion and current offline processing costs are separate.

The interface reports semantic status **unresolved** even for a full source. It is not a mode classifier or observed-event gate. Ordinary distant prose, blockquote/setext/indented structures and general intent/negation scope are not interpreted. A retained negative synthetic counterexample places a qualifier in a later ordinary paragraph: it is still absent. Do not close semantic#110, promote an absent cue into an observed fact or claim general truth preservation. [Exact contract](../../../docs/04-systems/source-context-v1.md).

## Verification, cost and decision

71new focused tests (46context,17diagnostic-v1,8marker-amendment) pass. With the46existing reader/window checks,117pass. Early test-development issues (overlong Windows parameter IDs and a fixture accidentally crossing a section boundary) were fixed before the source freeze; no criterion or old result was relaxed. Full [authored replay](artifact-audit.json) reconstructs187734source-message mappings,200context packets and1326target slots with zero failures and complete budgets. [Three forged private copies](mutation-audit.json) are rejected, including a rebound hash for changed context or a deleted unresolved slot. These are author checks, not independent semantic review.

Full diagnostic8.266seconds/1548160outputbytes; full replay8.282seconds. Loaded671selected full sources/1568000textbytes from read-only snapshots; complete archive/sidecar hashing and source mapping are included in diagnostic wall time. These are machine-local measurements, not a portable latency ranking. Source parsing makes0model calls. Hashes of source inputs, immutable snapshots, H1/API/BEAMledgers are unchanged before/after. PR105cumulative4824=4361local+463Flash, oldH13262/3300,newBEAM605/650,paid reservations$1.852 and recorded upper estimate$0.073913unchanged.

Decision: structural dependency/budget/replay conditions pass; **keep envelope experimental**, since evidence retention falls and general prose scope remains unresolved. No better BEAM answer score is claimed. Prioritize label-free retrieval of source roles, persistent instruction/preference records and multi-source evidence under an explicit shared budget, then freeze a new reader test on unused material. Current BEAM is development. More unconstrained calls to a larger reader cannot identify the present evidence-composition problem. General efficient capture, old graph transfer and a compatible competitor comparison remain open. No NIE/persona/deployment/frozen predecessor change.
