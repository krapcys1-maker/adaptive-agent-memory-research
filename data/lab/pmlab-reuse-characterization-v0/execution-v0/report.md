# Reuse component characterization run v0

Status: completed synthetic development characterization after protocol freeze `8ed9dce`  
Authority: implementation evidence only; no architecture selection or natural-benchmark claim

## Result

| Retrieval arm | Recall@5 | All required@5 | MRR@5 | Forbidden intrusion@5 | Cross-language Recall@5 | Candidate-null on unanswerable | Warm p50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| FTS5 | 0.711 | 0.632 | 0.697 | 0.050 | 0.250 | 0.000 | 0.262 ms |
| FastEmbed MiniLM | 0.982 | 0.947 | 0.829 | 0.200 | 1.000 | 0.000 | 52.136 ms |
| FTS5 + FastEmbed RRF | 0.868 | 0.842 | 0.789 | 0.150 | 0.750 | 0.000 | 52.395 ms |

The dense diagnostic recovered nearly every authored semantic target, including all cross-language cases, but retrieved a forbidden record in four of twenty queries. FTS5 had one forbidden intrusion. RRF improved substantially over FTS5 but was worse than the dense component on recall, all-required evidence, cross-language recall, terminology shift, and forbidden intrusion.

This is direct counterevidence to two unsafe assumptions:

1. higher semantic recall is not the same as safer memory;
2. an untuned hybrid does not necessarily beat its strongest component.

All three arms returned candidates for the unanswerable password query. Nearest-neighbor retrieval and non-empty lexical hits therefore remain candidate generation, not abstention or evidence completeness.

## Failure localization

FTS5 missed complete required evidence in seven answerable cases. Its main failures were cross-language retrieval, low-overlap paraphrases, and one prospective-scheduling paraphrase. It retrieved the stale plaintext-key record for the backup-key query.

FastEmbed missed one of three required records in the multi-project donor question. Its four forbidden intrusions were:

- obsolete automatic reinforcement;
- obsolete automatic reinforcement beside the correct utility records;
- stale plaintext-key storage beside the current keyring record;
- the superseded vector-source-of-truth proposal beside the current derived-index decision.

RRF inherited three forbidden intrusions and lost some dense-only semantic gains. At `k=60` and depth 10, agreement between the two components dominated, so a strong dense-only candidate could fall when sparse evidence was absent or misleading.

## Citations and context packs

All 36 source locators resolved to byte-identical evidence. All cited and bucketed packed items had valid locators. No stale record entered the current/supporting sections and no untrusted record entered a bucketed pack.

| Retrieval arm | Raw required retained | Cited required retained | Bucketed required retained | Bucketed omissions |
|---|---:|---:|---:|---:|
| FTS5 | 0.711 | 0.711 | 0.684 | 6 |
| FastEmbed | 0.982 | 0.982 | 0.982 | 14 |
| RRF | 0.868 | 0.868 | 0.825 | 12 |

The 768-byte budget exposed a real packaging tradeoff. Citations and section headers consume context. The bucketed pack preserved every dense-required item in this fixture, but dropped required evidence for one FTS5 and one RRF case. Omission counts alone are not enough; the pack must identify whether a required obligation was lost.

The bucket labels were authored metadata. Perfect placement validates deterministic plumbing only. It does not validate automatic classification of current, supporting, stale, conflicting, or untrusted content.

## Runtime and reproducibility

- FastEmbed: `0.8.0`; mean-pooling behavior reported by the library at runtime.
- ONNX source revision: `faf4aa4225822f3bc6376869cb1164e8e3feedd0`.
- ONNX SHA-256: `634d0f66c29dc934c8fa72b8a4fe91dd4d420a22f1d82a241058d4316e659a99`.
- Model cache: 252,141,277 bytes.
- Corpus vectors: 55,296 bytes for 36 × 384 float32 values.
- First model load including download: 25.681 s; first corpus embedding: 1.910 s.
- Warm model load: 0.635 s; warm corpus embedding: 1.100 s.
- Two fresh Python processes produced the same ranking SHA-256: `0bf4d21773b37df9525dbb576281d014c034d76831579f94627cb5c1e10d1ec9`.
- No chat-model/API calls and no API cost.

## Characterization decision

- **Admit exact citations** as a required contract: deterministic validity passed.
- **Admit bucketed packing as a testable formatter**, not as a classifier or final ordering policy.
- **Retain FTS5** as the minimal sparse baseline.
- **Retain FastEmbed/MiniLM only as a restricted diagnostic**; its semantic gain and safety loss both require natural replication.
- **Retain RRF as a comparator, not a default**; it did not beat the dense component here.
- **Keep abstention, trust filtering, validity filtering, and evidence completeness outside raw retrieval.**

## Next tests

1. On a frozen development set, compare full citations with compact citation IDs plus a footer dictionary under equal byte budgets.
2. Factor context order: retrieval order, current-first, relevance-first with stale-at-end, and duplicated critical evidence at the end. Use a provider-neutral reader and test position effects.
3. Filter or quarantine untrusted/stale candidates before the reader; do not rely on section labels as an instruction-injection defense.
4. Measure component complementarity and per-query discordance before assuming RRF can outperform its stronger component.
5. In the locked natural benchmark, compare multilingual E5-small against FTS5 and RRF only after independent eligibility and evidence labels are complete.

