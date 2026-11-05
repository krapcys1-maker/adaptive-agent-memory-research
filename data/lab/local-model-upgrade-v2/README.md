# RTX 3060 local model audit and controlled comparison

Decision: retain the historical defaults and judge. Qwen3.5 9B is a promising experimental reader, but fails the preregistered promotion screen. Gemma4 remains an incomplete, non-promotable trial. No memory algorithm, persona or production integration changed.

## A. Initial state and integrity

Ollama0.40.13; Windows11; i7-12700K; RTX3060 12288MiB, driver616.92;32GB installed RAM. Phase A was read-only in the project:29worktrees inspected,17dirty files (6,232,781bytes) privately copied and hash-verified;72449text files scanned with explicit exclusions. A later supporting-workflow check covered23396files. Environment secrets and raw research stay private. The original source at6a2025e was clean in the owned worktree. Project memory status/context ran against an exact audit mirror to avoid rebuilding the original index during Phase A.

| Initial model | Package GB | Role | Final decision |
|---|---:|---|---|
| `qwen2.5:14b-instruct` | 8.988 | Reader/capture baseline and historical judge default | KEEP |
| `llama3:8b` | 4.661 | No functional or historical experimental dependency found | REMOVED |
| `llava:13b` | 8.011 | Unused legacy vision package | REMOVED |
| `qwen7b_strict:latest` | 4.683 | Protected custom parameters over exactly the7B weights | KEEP |
| `qwen2.5vl:7b` | 5.969 | Distinct vision capability; external need uncertain | REVIEW; retained |
| `qwen2.5:7b-instruct` | 4.683 | Historical reader/writer and strict-profile parent | KEEP |

The strict profile and7B base share the same model blob `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730`; the strict profile is not independent fine-tuning evidence. Its temperature0.1/top_p0.9/context8192 remain unchanged. Historical `judge_writer_memory_sim.py` still defaults to14B; it was neither run nor replaced. External embedding/reranking models were preserved.

## B. Official packages installed

| Fixed tag | Exact manifest digest | Bytes | License |
|---|---|---:|---|
| `qwen3.5:9b-q4_K_M` | `56671c2ab9385f9cfcb404638e32cd62d88e3501d44822208363c010179a3c90` | 6550825550 | Apache-2.0 |
| `gemma4:12b-it-q4_K_M` | `6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b` | 8021618941 | Apache-2.0 |

Verified [Qwen package](https://ollama.com/library/qwen3.5:9b-q4_K_M), [Qwen developer card](https://huggingface.co/Qwen/Qwen3.5-9B), [Gemma fixed GGUF package](https://ollama.com/library/gemma4:12b-it-q4_K_M) and [Google developer guide](https://developers.googleblog.com/gemma-4-12b-the-developer-guide/). Both are Q4_K_M. Qwen9 is a dense hybrid recurrent/full-attention model; Gemma12 is a dense package with a native draft assistant. No27B, global environment/package/Ollama upgrade or daemon restart. The Gemma download followed the predefined technical gate, before semantic scores were available.

## C. Complete paired results

All84H1valid questions and200BEAM10M questions per complete model, each with/without memory;84same-seed H1 M repeats and3transport controls per model. Frozen original retrieval packets/gold/evaluators; sourcea71765f precedes inference, raw/auditor freeze633306c precedes reference join. Memory benefit is M minus N, separately for each model and corpus. H1 is mechanical clean success; BEAM is Codex-authored full-rubric assessment, not official BEAM accuracy or independent/fully blind review.

| Dataset / model | Memory off | Memory on | Benefit pp | Contradiction/leak N / M | M median seconds | M generation tokens/s |
|---|---:|---:|---:|---:|---:|---:|
| H1 / Qwen2.5 14B | 0/84 | 73/84 | 86.90 | 0 / 1 | 1.117 | 34.73 |
| BEAM / Qwen2.5 14B | 19/200 | 39/200 | 10.00 | 1 / 43 | 1.797 | 35.53 |
| H1 / Qwen3.5 9B | 0/84 | 82/84 | 97.62 | 4 / 0 | 0.516 | 54.87 |
| BEAM / Qwen3.5 9B | 19/200 | 40/200 | 10.50 | 0 / 36 | 1.109 | 57.98 |

H1 M:86.90% versus97.62%; BEAM M:19.50% versus20.00%. The contradiction columns are operational proxies, not an exhaustive truth/hallucination audit. Eight uncertain BEAM references remain in all200denominators: M bounds39–47 and40–48. Some instruction rubrics test surface compliance only; a fuel-budget pass does not validate arithmetic. There is no changed gold, dropped failure or vendor ranking.

H1 target-source coverage is84/84 in M for both models; five packets also show a forbidden/obsolete source. Source selection did not improve. The inherited BEAM annotation-source proxy has all targets shown in16/176annotated cases; this is not semantic evidence sufficiency or a model ceiling. Retrieval over long archives is distinct from a filled long model context. Actual maximum native prompt counts were1856/1864tokens despite the8192ceiling. Historical capture/reranking costs were not remeasured or erased.

| Resource / consistency | Qwen14B | Qwen9B |
|---|---:|---:|
| Whole-GPU peak MiB | 11836.0 | 8458.0 |
| Native allocated VRAM bytes | 10290085231 | 5862210928 |
| Whole-host RAM peak GiB | 27.743 | 28.295 |
| Median all-primary wall seconds | 0.4375 | 0.437 |
| Median primary generation tokens/s | 37.85 | 58.69 |
| H1 repeat exact text matches /84 | 55 | 84 |

All1310complete-run outputs were valid JSON, normal stops, zero native errors. Same-seed repeated clean counts:14B71/84,9B82/84; exact text55/84 versus84/84. Fixed seed does not guarantee deterministic14B behavior. Whole-host/GPU samples include desktop background load; a read-only supporting scan overlapped part of9B. No samples were excluded. Timing is descriptive. RSS sampling covers names containing ollama and excludes the separately named llama-server worker, so it is not total model RAM.

V1 stopped at3controls because an otherwise correct refusal had one terminal period; failed V1 remains immutable. V2 explicitly amended transport punctuation only, with identical655packets and unchanged quality criteria. Gemma V2 stopped after251/655 on another connected TCP process (PID36812), whose identity was unavailable after exit. A connection does not prove inference contention.248primary calls cover H1 plus only40BEAM questions; no repeats. No full quality score, resume, backfill, adoption or hidden rerun. Observed whole-GPU peak is in gemma-incomplete.json; nativePS reports about1.45GB despite7GB+ weights/roughly11GB measured whole GPU, so its footprint/residency must not be inferred from that number.

## D. Integration and validation

No candidate is promoted.9B improves H1 M and memory-on latency, but four N answers fabricate disabling deployment gates/checks. They are real affirmative outputs, not negated-phrase scoring errors. All four follow M and are English; language/order are confounded, so cache carry-over is an unproven hypothesis. The primary all-arm median is effectively unchanged and BEAM gain is only0.5pp, below the predefined5pp alternative. The original screen therefore rejects promotion; M-only speed and VRAM savings do not retroactively replace that screen.

New isolated versioned runners, native auditor and authored-review tool preserve old code/defaults.63focused boundary/forgery checks pass. Runtime sourcea71765f passed12CI jobs (3577passed/21skipped per Linux3.11/3.12). Raw/review-tool633306c has its own successful12-job CI42020602267. Local earlier preflight3544passed/20skipped. Later result/delivery heads have separate CI; see delivery receipt.301prior verdicts were reused only for identical question/reference/answer;133new verdicts were authored,434total within-question distinct answers. Reasons/raw data stay private.

## E. Cleanup and rollback

Supported native commands removed only `llama3:8b` and `llava:13b`, after fresh functional/history/direct-blob checks, configuration/manifest exports, no active client and no loaded target. At execution Ollama was idle. All six retained model digests match pre-removal state; custom profile and14B/7B remain. No model folders/shared blobs were manually changed. Native deletion removed11exclusive blobs totaling12,672,481,170bytes (about11.80GiB); filesystem free-space delta12,672,724,992bytes includes ordinary concurrent metadata changes. The decision is based on non-use, not a vision-quality comparison.

Reinstall using supported commands, then require the exact digests below. If a registry tag changes, stop rather than treating another digest as historical restoration. Full original manifest/template/system/parameters/license exports are in the private audit/recovery archive.

```powershell
ollama pull llama3:8b
ollama pull llava:13b
```

| Reinstalled tag | Required original digest |
|---|---|
| `llama3:8b` | `365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1` |
| `llava:13b` | `0d0eb4d7f485d7d0a21fd9b0c1d5b04da481d2150a097e81b64acb59758fdef6` |

Verify with `(Invoke-RestMethod http://127.0.0.1:11434/api/tags).models | Select-Object name,digest`. Model weights are not uploaded/backed up in Git; exact future registry retention is outside this project.

## F. Reproduction and continuity

Common decoding: temperature0, seed7, context8192, output512, top_p1, top_k0, repeat_penalty1, frequency_penalty0. Qwen3.5 native presence_penalty1.5 is retained; others0. Gemma draft_num_predict3 retained. Explicit think:false when supported, native JSON schemas, fresh chat per case, alternating N/M order, one owned worker, no fallback/retry or hidden thinking retained. Packages/templates/tokenizers differ; this is not equal logit processing/compute. Full per-call native token/time counters and identity/reservation replays are retained.

Task1564/2000 =3failed V1 controls+655baseline+655Qwen9+251Gemma.0new paid/API calls. PR105now6388attempts =5925local+463historical Flash; old H13262/3300,BEAM605/650 and API ledger bytes remain unchanged. Paid historical reservations1.852USD/recorded usage upper0.073913USD unchanged. No spare-budget filling is authorized.

Private artifacts: `D:\Pamiec LLM\GH_REVIVAL\local-llm-upgrade-2026-11-05`; audit/export/copies in the dated Codex visualization directory. Actual restoration evidence is recorded in the private VERIFIED.json and delivery receipt. Shared C-017/root Claude handoff point here; no other-agent ACK is implied. No NIE personality, shared plan, original dirty worktree, frozen predecessor or historical answer was edited.

## G. RTX3060 recommendation

Keep14B as the historical/default comparison and evaluator identity. Qwen3.5 9B is the strongest next experimental reader candidate here: much higher H1 M success, stable repeat and lower measured GPU footprint, but it needs a separately frozen no-evidence/order-isolation diagnostic before promotion. Gemma is not ranked: its incomplete trial cannot justify replacement. The next admissible work is exclusive-worker controls on unsupported gate advice plus source/evidence-selection repair. No new model call, persona integration or deployment is authorized by these descriptive results.
