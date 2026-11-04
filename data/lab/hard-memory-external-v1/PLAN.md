# Hard external memory diagnostic — frozen before execution

The owner explicitly requested a difficult test beyond the authored eight-slot pilot, and continued execution rather than stopping at another plan. Execute the existing external conflict-resolution task now. This bounded diagnostic is not a new independent confirmation experiment or architecture promotion. Do not modify existing freezes, sealed splits, kernels, NIE or old worktrees.

## Primary task

Use **all 100 questions** of `factconsolidation_mh_262k` from official [MemoryAgentBench](https://github.com/HUST-AI-HYZ/MemoryAgentBench), dataset [ai-hyz/MemoryAgentBench](https://huggingface.co/datasets/ai-hyz/MemoryAgentBench) revision `7ea066982b140a19337e17e60d45d4076e042faf`. The conflict-resolution parquet hash is in config. The selected history has 1,118,123 characters and 18,333 lines, including a preamble, with counterfactual updates. Keep source ordering and raw assertions. No answer-selected records, manually supplied slot, gold chain map, typed claims or deterministic answer correction is available to retrieval/readers.

Preparation separates the unchanged archive and questions from a gold file. Inference accepts only archive/packets/questions and never opens answers. Use one source line per memory item, opaque ordinal IDs and the original numbered text; source-order timestamps only encode ingestion order, not inferred validity or supersession. No automatic current/stale labels are supplied. Save retrieval packets, restart in a new process, and reload the packets from disk for inference. Every completion is stateless. Do not patch retrieval or prompts after inspecting this run's answers.

Arms, selected before question/answer inspection:

- **N:** no memory, local diagnostic for unsupported prior-knowledge answers.
- **K:** shipped kernel 0.2.0 lexical profile, k=3, ordinary thresholds, no supplied routing. An infinite offline timeout removes scheduling as a confound; this is not a live-latency claim.
- **B:** same frozen kernel BM25 implementation, threshold-free diagnostic ranking (lex_tau=1e-9, min_evidence=0, names off), up to 24 candidates. This changes a diagnostic profile, not shipped defaults. Both K and B have the same 4500-byte serialized context ceiling. Selected records are shown in original source order so recency remains visible.

The reader prompt explicitly treats recorded assertions as counterfactual and asks for UNKNOWN when evidence is insufficient. JSON `value` output is parsed and scored as emitted. No repair/retry or scoring gold enters that prompt. This is an offline adapter using raw assertion storage, not a complete memory-system leaderboard submission, trained extractor or claim about 200 elapsed years.

## Models and resources

- Existing local Qwen2.5 14B Instruct, pinned installed digest, temperature 0, context 4096, max 64 output tokens. N/K/B: 300 primary calls plus three positive controls, planned 303, hard local maximum 305 and 1800 seconds. One GPU worker; unload only its owned model.
- Official DeepSeek V4.1 Flash only, canonical `deepseek-flash`, thinking disabled, temperature 0, max 64 output tokens. K/B: 200 primary calls plus three controls, planned 203, maximum 205 and 1800 seconds. Reuse the already frozen Flash-only client and identity checks. A **new explicitly declared $1 task budget** uses its own permanent ledger, $0.004 reserved before every attempt: planned reserves $0.812. This is a different dataset/task from PR #103; retain its earlier ledger unchanged. No Pro/other provider/fallback/automatic retry. Message ceiling remains four messages / 6000 UTF-8 bytes.
- Total planned **506 new generations**, zero planning/idea/judge calls. The local no-memory arm is not an API no-memory baseline.

## Scoring and decision

Commit source/config before packet construction and generation. Freeze all raw completion hashes before joining gold. Primary metric: normalized exact-match accuracy over all 100 questions, maximum over official gold aliases. Normalization follows the official scorer's lowercase, ASCII-punctuation removal, article removal and whitespace collapse. Also report token F1 and substring match separately; never replace a failed exact match by a substring success. Malformed/truncated/UNKNOWN answers remain visible and are wrong unless explicitly in the gold. Partial runs cannot receive a complete score.

Reconstruct every shown context/request from packet bytes, raw response parsing and per-question scores. Compare K versus B within each backend; do not pool question repeats, arms or readers as independent samples. Report confidence intervals descriptively. A declared engineering readiness target is **at least 80/100 exact answers on Flash K**, with K not worse than the unlocked B diagnostic. Missing it means the present ordinary memory path is not ready for this hard task; it is not a claim that the benchmark itself is unsolvable. No threshold is changed after results. If K fails, preserve the failure and diagnose retrieval versus reading before a separately versioned repair.

Public records contain source/code identities, opaque question IDs, retrieval IDs/counts, scores, usage and decisions. Full source conversations/questions/answers/prompts/completions stay in the external local evidence directory. Do not silently publish source text or claim this is the official full-agent MemoryAgentBench protocol: ingestion granularity, bounded context, prompt and reader differ and will be documented.

## Further hard suites inspected

Cache pinned official sources for BEAM-10M, LongMemEval-V2 and MemoryArena and document scale, evaluation dependencies and limitations. BEAM's first 10M history was downloaded as JSON (never load untrusted pickle files). Those suites are not reported as executed or passed until an actual adapter/run and appropriate scoring exist.
