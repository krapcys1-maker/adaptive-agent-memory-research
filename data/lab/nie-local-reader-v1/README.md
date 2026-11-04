# NIE bridge → local reader: recorded results

**A narrow working candidate, not a deployed persona or a general memory verdict.** The pilot tests eight authored fields with fixture-supplied routing, a structured fictional writer and one local quantized Qwen 7B reader at temperature 0. It does not replace the negative P2 result or evaluate the actual NIE prompts/hosted reader. No NIE source, prompt, private biography, deployment, frozen kernel or confirmation epoch changed.

The [execution plan](../../../docs/00-project/nie-local-reader-pilot-2026-11-04.md), cases, questions, seeds and resource ceilings were committed before generation (`bfe8617`). Results, failed attempts, response content, prompt/usage ledgers, committed-source digests and local-runtime details are preserved below. No hidden thinking fields are stored.

## What the complete run found

Each arm has 16 writer chains × 3 reader turns. Direct question starts fresh; the paraphrase starts a new session; pressure retains only the paraphrase exchange. The initial writer answer is never in a no-memory conversation.

| Arm | Correct detail retrieved | Raw model answers agreeing | Delivered answers agreeing | Chains correct on all 3 turns |
| --- | --- | --- | --- | --- |
| N — no stored context | 0/48 | 0/48 | 0/48 | 0/16 |
| K — current bridge, natural question | 32/48 | 16/48 | 16/48 | 0/16 |
| O — oracle correct-note context | 48/48 | 36/48 | 36/48 | 4/16 |
| V — supplied slot cue + retrieved-fact guard | 48/48 | 36/48 | 48/48 | 16/16 |

| Turn | K retrieved / agreeing | O agreeing | V raw / delivered agreeing |
| --- | --- | --- | --- |
| Direct | 16/16 · 16/16 | 16/16 | 16/16 · 16/16 |
| Paraphrase after reset | 0/16 · 0/16 | 16/16 | 16/16 · 16/16 |
| Misleading pressure | 16/16 · 0/16 | 4/16 | 4/16 · 16/16 |

Two failures are separable. Natural paraphrases intentionally avoid the stored note's words, and K retrieves none after the session reset. Even with the correct note supplied (O), the reader retains the choice in only 4 of 16 pressure turns: it abstains with UNKNOWN in ten and adopts the wrong suggested value in two. A retrieved note alone is therefore insufficient for consistency in this construction.

V adds the predeclared slot keywords without including the chosen value. It retrieves the correct note in all 48 turns, but the raw reader is still correct in only 36. The runtime guard corrects 12 raw answers from actually retrieved typed claims, producing 48 correct delivered values and 16 complete chains. Those twelve corrections consist of ten UNKNOWN answers and two incorrect values, not twelve hallucinated values. The raw and corrected counts are separate: this is a code-enforced narrow contract, **not 48 independently correct model answers**.

One recorded example: field `sunday_tea`, stored value `assam`, raw answer `UNKNOWN`, delivered `assam`. The guard receives only the shown items and slot ID, never the scoring gold or the complete archive.

Both seeds produce the same writer choice within each field. These are eight authored semantic cases with repeated runs, not sixteen independent histories; no population interval or generalized accuracy claim is made. The no-memory reader was explicitly told to abstain on missing facts, so its zero agreement is an absence baseline, not a surprising discovery. Its 48 outputs comprise 31 UNKNOWN answers and 17 unsupported values; agreement alone would hide that distinction. K has 16 correct, 16 UNKNOWN and 16 unsupported values; O and raw V each have 36 correct, ten UNKNOWN and two wrong values.

## Failed writer run and explicit repair

`run-001` completed 24 calls: controls/canaries plus sixteen writer calls. Every writer chose a pool member but emitted the slot ID as the JSON key rather than `value`. The strict contract rejected all sixteen; no journal/read chain was fabricated, and readiness was false. Keep that run as a valid negative syntax-contract result.

Before `run-002`, the amendment changed **only writer transport** from generic JSON mode to a JSON schema requiring exactly `value` and the existing pool enum. Reader transport, instructions, thresholds, questions, model, seeds and scoring stayed unchanged. All sixteen writes then passed and all 216 planned calls completed. This repair is result-informed and disclosed, not independent confirmation. The original config and execution remain intact.

## Negative-control coverage and one separate follow-up

| Control | Actually shown matching evidence | Raw model value | Delivered value | Interpretation |
| --- | --- | --- | --- | --- |
| No record | none | UNKNOWN | UNKNOWN | Absence branch exercised |
| Future-only record | none | UNKNOWN | UNKNOWN | Availability filter + absence branch exercised |
| Original conflict control | none | UNKNOWN | UNKNOWN | Uninformative about conflict: the gate showed nothing |
| Separate conflict follow-up | two contradictory records | amber | UNKNOWN | Conflicting-evidence branch actually exercised |

The original conflict result remains unchanged. The supplementary control adds the same seven unrelated slot distractors as the main design, leaving all profile/threshold/model/guard settings unchanged. It mechanically checks that both contradictory records are shown before making its **one** model call. Its result is separate from the primary arm counts and explicitly post-result. Three positive reading/format controls pass; the two repeated canaries are byte-identical to their first answer. These constructed controls do not establish real-world precision or semantic safety.

## Provenance and verification

- `run-001/manifest.json`: execution source `8d17c4f62dd1ef4b1fc1c2e836aa14d63555f92e`; 24 calls, 16 write failures.
- `run-002/manifest.json`: execution source `783ce4bb00d0df34ae932fd4d447c517b7ba1ea8`; 216 calls, 16 valid chains.
- `conflict-followup/`: one separately declared coverage-control call.
- `reanalysis-audit.json`: every recorded execution-source digest matches its committed file; reanalysis reproduces both saved summaries without differences; the original conflict control is explicitly marked unexercised.
- Total **241 generation calls**, within the 244 task ceiling; **$0 paid API spend**, no downloads. Calls go only to the fixed loopback service, sequentially; the local model was unloaded after each run.
- Service-reported model: Qwen2.5 7B Instruct, Q4_K_M, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`; Ollama 0.40.13; RTX 3060 / driver 616.92. Options and runtime timings are captured, not inferred from a model alias.
- Forty-five focused tests pass: claims/legacy compatibility, malformed/conflicting evidence, full fake chains, history/session isolation, caps, refusal of remote URLs, incomplete/corrupt coverage, writer-schema isolation and record preservation. Full gates/CI are recorded on the delivery PR.

## Persisted-storage readback

The original model calls used the in-memory copy of the rows already written to `journals.jsonl`. A separate readback audit reloads that file and reproduces **all 192 reader contexts, shown items and selected IDs exactly**. No model was called again and no primary score changed. The current runner now explicitly reloads the unique persisted chain before each reader turn; missing or duplicate chains fail instead of falling back to a live writer variable. The audit records its own analysis commit separately from execution provenance.

## Interface and remaining boundary

An opt-in journal field looks like `"typed_claim":{"slot":"kettle_colour","value":"teal"}`. It is preserved in the existing bridge's item metadata, retains `fiction_autobio` origin, and must have a whole-phrase occurrence in its source text. Old rows keep their item IDs. Replay schema v2 records the contract dependency digest. The guard refuses untyped, conflicting or absent facts instead of silently promoting prose to truth.

**Value occurrence is not semantic entailment.** This pilot constructs affirmative text from the writer's explicit structured choice. It does not infer claims from arbitrary prose, understand negation, detect contradictions against the full canonical card, infer arbitrary query slots or resolve revisions/supersession. Existing NIE journal producers do not yet emit the new optional field. The supplied slot router is an oracle-like fixture assumption; broader gains cannot be attributed to a solved semantic-routing problem.

The recorded decision is to retain typed routing/output validation as a **candidate for a larger offline test**, conditional on the typed producer and correct routing. Next: validate capture of typed details and routing against actual writing prompts, then transfer to the main hosted reader under its own fixed cap. Do not deploy automatically, change the global retrieval thresholds or replace the prior persona verdict.

## Commands

Run only into a new directory from a clean committed source tree; the installed model digest must match and no other Ollama model may be loaded. A separately budgeted reproduction uses:

```powershell
python scripts/nie_reader_pilot.py --output NEW_RUN --config data/lab/nie-local-reader-v1/config-v2.json
python scripts/reviews/nie_reader_conflict_control.py --output NEW_CONTROL
python -m pytest -q tests/test_nie_reader_pilot.py tests/test_nie_memory_contract.py tests/test_nie_persona_replay.py
python tasks.py check
```

Every attempt is reserved before transport. No generation retry, partial-run resume, model fallback, input/output overwrite, hidden paid call or live-agent hook exists. Incomplete/corrupt records cannot receive a complete reading. The saved completed runs need no repetition merely to recreate documentation.
