# PI-LLM / Unable-to-Forget code audit

Status: source and static audit complete; execution not attempted

## Artifact

- Repository: https://github.com/zhuangziGiantfish/Unable-to-Forget
- Audited commit: `51c131691e75c293694b883d5e310ab8523ed778`
- Commit date: 2025-11-04
- License: MIT
- Paper: https://arxiv.org/abs/2506.08184v3
- Local clone: `external/repos/zhuangziGiantfish__Unable-to-Forget/` (ignored)

## Reusable parts

- generators for repeated key-value updates;
- five interference dimensions: updates, key count, tracked-key count, value length, and presentation order;
- final-value exact-match scoring and response-position analysis;
- configuration examples for multiple provider families;
- bootstrapped confidence-interval stopping logic;
- prompt interventions for forget, focus, session reset, and mock-QA reset.

The most reusable contribution is the controlled corpus generator and error-position analysis. The provider client and large dependency stack should not become part of the project's memory core.

## Static findings

- All Python files compile under the local Python 3.12 interpreter, with several invalid-escape `SyntaxWarning` messages in response-parser regular expressions.
- No unit-test files were found in the 30-file revision.
- `requirements.txt` pins several 2024-era packages but does not provide hashes or a complete environment lock; it includes large Torch, Transformers, vLLM, and multi-provider dependencies.
- The repository tracks an `API.json` file even though `.gitignore` lists it. Its contents were not inspected. Any reproduction must use a fresh ignored credential file outside the clone and must never reuse or trust a tracked credential artifact.
- `core/pi_flow_upgrade.py` lines 762 and 765 use comparison (`n_forget == 0`) where assignment appears intended in `activelocate` and `meditation` branches. Those branches require repair and a unit test before use.
- Random word selection is described, but the audited execution path does not expose a clearly frozen global seed in the checked configuration; raw prompts and answers must therefore be preserved for reproduction.
- The README labels `core/` stable and `automation/` beta. This is author status, not independent validation.

## What was not reproduced

No model API run was performed. Reproducing the paper as written would require multiple paid providers, model snapshots that may drift, and a reviewed cost plan. Static compilation does not validate the reported accuracy curves or confidence intervals.

No public implementation was found for the 2026 WhenLoss paper during exact-title, arXiv-ID, author, and method-name searches on 2026-08-22. Its four-condition protocol can be reimplemented from the paper, but its numerical results remain unreproduced here.

## Admission decision

Admit the repository as an ignored, pinned **benchmark reference and corpus-generator candidate**. Do not import its credential loader, provider abstraction, dependency environment, or unreviewed parser into the minimal architecture.

Before any paid reproduction:

1. extract a provider-neutral deterministic generator;
2. add fixed seeds, schema validation, and parser unit tests;
3. remove all credential-file assumptions;
4. test local fixtures without API calls;
5. preregister model snapshots, repetitions, stopping rule, and cost cap;
6. compare current-state retrieval with historical-as-of retrieval, which the original final-value task does not measure.
