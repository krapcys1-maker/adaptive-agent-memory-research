# AAMR-NIGHT-1 (EXP-FIX-0 and lesson writers): development result, transfer not confirmed

**Status: completed on 2026-11-13 as a development result. Negative on the one confirmatory transfer test; the mechanism result
is supported only at its thresholds.** Run by the maintainer's autonomous program (`scripts/aamr_night1.py`, started by the
Windows scheduler, no Claude session during the run). Protocol, report, numbers and conclusions below are the author's
(Claude Opus 5.5), not independently reviewed. The protocol, interpretation (`WNIOSKI.md`) and report text are written in
**Polish**; this README is the English summary. Imported into this repository on 2026-11-14.

## Short answer
- **EXP-FIX-0, does the right content delivered at the moment of an error repair the failure?** With a hand-written oracle:
  yes on development data, on two models. Qwen2.5 14B on the 30 Vehicle Control test tasks: 9 solved without memory, 12 with a
  placebo note, **15 with the oracle**; the registered rule gives "supported" but exactly at its thresholds (gain +6 against a
  threshold of 5, one-sided McNemar p = 0.035; one task different and it fails). Qwen3.5 9B: 10, 13, **19** (9 gains, 0 losses,
  p = 0.002). The replication on the 20 training tasks was inconclusive (6, 6, 8). The placebo alone gained +3 in two sessions.
- **Lesson writers (deterministic compiler, local Qwen, DeepSeek Flash).** On Vehicle Control Flash beat the best local writer
  (17 against 12 solved), but almost entirely through one error signature (fuel) on which the local writer's lesson was
  factually wrong; the deterministic checks passed it. On 58 previously untouched file-system and travel tasks no difference
  was detected (deterministic 19, Qwen 22, Flash 21, none without memory 17). The default stays the free local writer.
- **Transfer test (the only confirmatory one):** deterministic lessons against no memory on the untouched tasks, 19 against 17,
  +2, p = 0.25: **not confirmed**. No arm passed the Holm threshold in its family.
- **Memory can harm:** a stale lesson ("40 gallons") was followed literally in 6 of 8 error turns (0 solved), and every arm with
  memory lost the same task in session sA. Outputs are not deterministic at temperature 0 on longer contexts (13 of 58
  re-run episodes diverged without any memory).
- **Next admissible step, per the author:** EXP-VER-1, verify each lesson before it enters memory. Not run. Choice of a
  confirmatory set (the untouched TradingBot reserve) is the maintainer's decision.

## Cost
9 219 local calls (limit 12 000; Qwen2.5 14B 7 244, Qwen3.5 9B 1 909), 22 DeepSeek V4.1 Flash calls, upper-bound cost 0.016 USD
(reserved 0.22 USD, limit 3 USD), no paid Claude API.

## Files
| File | What it is |
|---|---|
| [PROTOCOL.md](PROTOCOL.md), [config.json](config.json) | the frozen protocol and configuration, with three technical amendments made before the first affected session (section 6 of the protocol) |
| [REPORT.md](REPORT.md), [results.json](results.json) | generated report and results under the frozen rules |
| [WNIOSKI.md](WNIOSKI.md) | the author's interpretation (Polish); the divergence, harm and lesson-agreement analysis in it is **exploratory** (made after the results were seen) |
| [followup.json](followup.json) | output of `scripts/aamr_night1_followup.py` (the exploratory analysis) |
| [raw-freeze.json](raw-freeze.json), [RAW_FREEZE_ERRATUM.md](RAW_FREEZE_ERRATUM.md) | the SHA-256 manifest of 17 raw files, published byte for byte, with an erratum on its recorded local path |

Code: `scripts/aamr_night1.py`, `scripts/aamr_night1_analysis.py`, `scripts/aamr_night1_followup.py`; tests: `tests/test_aamr_night1.py`
(with `tests/fixtures/aamr_night1_frozen_texts.json`, an in-repository copy of the frozen lesson texts the test checks against).

## Reproducibility and limits
- **The raw run (sessions, attempts, ledgers) is not in this repository.** The manifest pins 17 raw files by SHA-256, but nothing
  here lets a reader recompute those sums, and `aamr_night1_followup.py` cannot be rerun from a clean clone. The author's
  re-check after the run (0 mismatches) was not independently repeated.
- The frozen-spec test originally read a document outside the repository (the direction review that froze the two lesson texts),
  which made it fail in a clean clone. It now checks the program's `ORACLE` and `PLACEBO` constants against
  `tests/fixtures/aamr_night1_frozen_texts.json`, which records both texts with their SHA-256 and the SHA-256 of the source
  document. **How the fixture was checked against the source (2026-11-14):** the source document
  (`direction-review-2026-11-12/OCENA_KIERUNKU.md`, 18 705 bytes, kept outside this repository) hashes to
  `24f472b17360405b58eb6725fe9f1d1c4a54419da154017df3e920eb59afba97`, the value recorded in the fixture, and its first two
  `text` blocks (section 7) equal the fixture's `oracle` and `placebo` strings. The optional test
  `test_recorded_texts_match_the_direction_review_document` repeats this when the environment variable
  `AAMR_NIGHT1_SPEC_DOCUMENT` points at the document; it passes locally and is skipped in CI, where the document does not exist.
  The source document itself is not published here.
- One benchmark (BFCL multi-turn base, checkout `6ea5797`), one local model per session, one run per arm, 30, 20 and 58 tasks,
  no correction for multiple comparisons outside the sD family. The Vehicle Control results are development data: those tasks
  were known from the pilot and from EXP-XFER-1. No competitor was run in this harness, so nothing here supports "better than
  competitors".
- Builds on [../experience-xfer-v1/README.md](../experience-xfer-v1/README.md) and [../experience-pilot-v0/README.md](../experience-pilot-v0/README.md).
