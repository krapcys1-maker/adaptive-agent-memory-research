# NIE bridge: local reader and typed-fact acceptance pilot

Execution plan fixed before any generation call. This completes the pending reader boundary of the existing offline bridge; it is an engineering pilot, not a new confirmatory study, a replication of P2 or an independence promotion. Previous P2 results and frozen sources remain unchanged.

## Question and concrete intervention

Can a locally generated fictional detail survive publication-journal storage, time-filtered retrieval, three reader questions and misleading pressure? Separate failure to retrieve from failure to honor a retrieved detail. Test a concrete candidate: **explicit slot-cue routing plus a deterministic typed-fact output guard**. Do not test the old honor-the-record sentence alone again.

The new writer emits one value from a declared eight-value pool. A deterministic template records that choice as fictional text with an opt-in `typed_claim` (`slot`, `value`). This is a controlled structured writer, **not unconstrained prose extraction**. Legacy NIE journal rows remain supported; the producer in NIE is not changed. The claim remains `fiction_autobio`, not canonical biography/world knowledge. Validate that the typed value occurs as a whole phrase in its source text.

The guard receives **only items actually shown by the bridge** and a supplied slot ID. It never receives the expected answer or the complete archive. One unambiguous matching claim permits the stored value; conflicting claims, no claim, unsupported task/origin or missing evidence produce `UNKNOWN`. A wrong/malformed reader value can be corrected to that remembered value. This verifies a narrow structured contract; it is not a general factuality checker.

## Fixed design

- Existing local `qwen2.5:7b-instruct`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, Q4_K_M; local Ollama currently 0.40.13. No download, paid API or external destination. One sequential worker; no 14B model. Record service/model/GPU provenance. Unload only the model loaded by this run when finished, if it was not already loaded.
- Eight synthetic slots, two writer seeds (17, 43), three follow-ups (direct, paraphrase, a deterministic different-value suggestion). Temperature 0, context 4096, maximum 64 generated tokens per call, JSON output. The vocabulary, templates, cues, questions and prompts are committed before calls.
- Four arms: **N**, no stored context; **K**, current bridge with the natural question; **O**, oracle context containing the one correct available journal entry; **V**, bridge query augmented by the predeclared slot cue plus typed-fact guard. N/K/O/V use the same reader instructions. Each arm has its own history; V feeds its emitted guarded answer back when history is retained.
- **Session-boundary clarification before calls:** direct question starts a fresh session; the paraphrase starts another fresh session (discard the direct answer), so working-context retention cannot impersonate long-term memory. The pressure question retains only that paraphrase exchange. No initial writer exchange is included in any reader history.
- Routing is **supplied by the fixture**, not inferred from arbitrary questions. The cue contains slot keywords but never the selected value. Report routing coverage (K versus V), raw V answers and delivered V answers separately, so a routing gain is not attributed to the output guard.
- The writer's choice is not included in N's follow-up history. Foil = the next pool value cyclically after the choice. Every arm receives the same foil. Each seed/case has its own journal, with seven unrelated fixed distractors and one matching future entry; the future story mentions 2019 but is unavailable until November 5. Replay is November 3. Do not reinterpret story dates as availability.
- Three positive format/reading controls must pass before the main loop; no-record, future-only and conflicting-record controls also run. Repeat the first positive control twice after the main loop as drift/repeatability canaries. **216 planned generation calls**, hard cap 220 attempts and 1200 seconds, $0 API spend. No automatic generation retries, no resume/mixing identities, no model fallback, no threshold tuning after seeing results. Errors retain a partial run and produce no complete verdict.
- Writer output outside its pool is a recorded write failure: no retry or fabricated journal; end-to-end chain counts it as failed. Conditional read denominators and skipped follow-ups are explicit. All sixteen planned chains remain in the end-to-end denominator.

## Metrics and decision fixed before calls

Report exact counts by arm, turn and seed: stored-detail retrieval hit; raw answer agreement with the writer's accepted choice; delivered agreement; all-three-turn chain agreement; `UNKNOWN`, malformed answers and guard corrections/abstentions. Gold is used only by analysis, not by routing/guard execution. These are eight authored cases with two runs each, not sixteen independent life histories; no population confidence claim or production verdict.

Descriptive readiness for a **larger offline test only**: at least 15/16 V chains retain the choice across all three turns, at least 90% V retrieval hits, positive controls pass, and zero invented delivered values on the no-record/future/conflict controls. If V has no advantage over K, record that no extra benefit was demonstrated. If retrieval or reader fails, identify that stage and retain the failure. Even a pass leaves free prose, semantic slot routing, revisions/supersession, actual NIE prompts and the main hosted reader unvalidated. No live deployment follows this pilot.

The run manifest pins execution source/config/fixture digests, model digest, options and prompts. Save final response content and usage/timing metadata, never hidden thinking fields. Every attempt is reserved in a ledger before HTTP; incomplete/duplicate records cannot become a complete reading. All public inputs/outputs are authored synthetic data.

## API references

Use the local native [chat endpoint](https://docs.ollama.com/api/chat), [installed-model listing](https://docs.ollama.com/api/tags) and explicit [runtime parameters](https://docs.ollama.com/modelfile#valid-parameters-and-values). The installed service's actual responses are captured; current online documentation alone does not establish the behavior of this installed version.
