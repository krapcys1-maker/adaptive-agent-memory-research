# Invalid LongMemEval bridge execution v0

Status: invalid infrastructure run; retained as an immutable failure record

The primary process produced one B1 error on public question ID `c8f1aeed`. A fresh measurement process then failed at the same parser boundary before writing an artifact. The source conversation contains seven literal Unicode line separators (`U+2028`). `rg --json` correctly retained those characters inside JSON string data, but Python `str.splitlines()` incorrectly treated them as record boundaries and passed an unterminated fragment to `json.loads`.

The invalid primary output reported B1 macro Recall@5 `0.900000`, B2 `0.983333`, and B2-B1 `+0.083333` with a stratified interval `[0.000000, 0.183333]`. These numbers were observed before the repair and have no evidential status because the frozen contract declares any B1/B2 backend error inconclusive.

Protocol v0.1 was frozen before a repaired output. It permits only replacing Unicode-aware `splitlines()` with LF-delimited `split("\n")` in the shared `rg` JSONL parser, plus hashing that dependency in the environment lock. Tokenization, retrieval units, scoring, metrics, thresholds, and interpretation rules remain unchanged.

No source conversation, question text, answer, raw session ID, or evidence ID is stored here.
