# Owner's model-use policy — 2026-11-04

Use existing local models wherever they are adequate. Use the API when it adds value for evaluation, transfer to the intended reader, planning changes or proposing candidate ideas. The owner explicitly authorized both uses. Model-generated plans remain candidate suggestions until checked against evidence and tests.

**The only permitted paid/API model is DeepSeek V4.1 Flash. Never call Pro.** Use the canonical request ID `deepseek-flash` only, after verifying the provider's model metadata names V4.1 Flash. Reject other model IDs before credential loading or transport; do not fall back to an older model, Pro or another provider. Preserve this restriction across future tasks.

The [provider's current pricing/version page](https://api-docs.deepseek.com/quick_start/pricing/) identifies `deepseek-flash` as DeepSeek-V4.1-Flash-1017. [The model list API](https://api-docs.deepseek.com/api/list-models/) currently advertises that ID as DeepSeek-V4.1-Flash. Record requested and returned identities and timestamps; an API alias is not a pinned local weight digest.

Local inventory checked 2026-11-04: Qwen2.5 7B Instruct (`845dbda0ea48…`, Q4_K_M), Qwen2.5 14B Instruct (`7cdf5a0187d5…`, Q4_K_M), Llama3 8B, two vision models and a strict-profile alias sharing the 7B weights. Use 7B for inexpensive iteration and 14B sequentially for a stronger local comparison when GPU memory permits. Do not count the strict alias as independent model evidence. Existing local smoke tests and the PR #102 reader pilot are prior evidence, not new results.

Declare task-specific call and cost caps before paid generation, keep a cumulative reservation ledger, record final responses/usage without secrets or hidden thinking, and leave private agent data local unless explicitly selected for an authorized test. Preserve original worktrees, source versions and negative results; document changes for Claude.
