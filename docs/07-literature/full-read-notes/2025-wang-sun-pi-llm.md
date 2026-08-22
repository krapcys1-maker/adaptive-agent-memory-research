# Wang & Sun — Unable to Forget: proactive interference in LLMs

- Status: full text and code revision read; extracted; independent reproduction pending
- Version read: arXiv:2506.08184v3, 2025
- Source: https://arxiv.org/abs/2506.08184v3
- Code: https://github.com/zhuangziGiantfish/Unable-to-Forget at `51c131691e75c293694b883d5e310ab8523ed778`
- Local cache: `sources/papers/2025-Unable-to-Forget-Proactive-Interference-LLM.pdf` (ignored)

## Method and result

PI-LLM streams repeated values for up to 46 keys and asks for each final value. Update count ranged from 3 to 400; other tests varied key count, tracked-key count, value length, and random versus sequential presentation. The paper reports declining accuracy across a broad proprietary/open model set, older-value intrusions, and fixed-length controls. Natural-language forget/focus cues gave limited improvement; a mock-QA reset helped partially.

Exact locators: Sections 2–5 and Figures 1–13; model versions in Appendix B; code audit in `docs/04-systems/unable-to-forget-reproducibility-audit.md`.

## Limitations

- Synthetic final-value retrieval does not measure retention on disk or historical queries.
- Model snapshots and provider behavior may have changed since calls ended on 2025-05-05.
- Behavioral curves do not prove the paper's proposed internal executive or resource mechanism.
- The audited repository has no unit tests, a tracked credential-shaped file, parser warnings, and two likely assignment defects; no paid reproduction was run.

## Project consequence

Reuse the generator and error-position logic after extraction into a provider-neutral, deterministic harness. Add historical-as-of and provenance conditions before treating final-value performance as memory quality.
