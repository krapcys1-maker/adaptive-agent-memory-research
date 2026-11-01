# AAM-E3A retrieval calibration

Notes: 234; judged pairs: 926 (unparsed replies: 0); random negative controls rated 0: 0.709 of 230 (judge reliable: False).

## Relevance by cosine

| cosine | pairs | rated 0 | rated 1 | rated 2 |
|---|---|---|---|---|
| 0.00-0.30 | 314 | 0.669 | 0.306 | 0.025 |
| 0.30-0.40 | 201 | 0.343 | 0.607 | 0.050 |
| 0.40-0.50 | 192 | 0.156 | 0.698 | 0.146 |
| 0.50-0.60 | 110 | 0.109 | 0.518 | 0.373 |
| 0.60-0.70 | 53 | 0.000 | 0.170 | 0.830 |
| 0.70-0.80 | 23 | 0.000 | 0.000 | 1.000 |
| 0.80-1.00 | 8 | 0.000 | 0.000 | 1.000 |

## Injection at a threshold (up to three most similar earlier notes with cosine at least tau)

| tau | injected | notes served | coverage | per note | precision (1 or 2) | interval | rated 2 | noise (0) |
|---|---|---|---|---|---|---|---|---|
| 0.5 | 194 | 98 | 0.421 | 0.833 | 0.938 | (0.895, 0.9643) | 0.598 | 0.062 |
| 0.55 | 124 | 67 | 0.288 | 0.532 | 0.976 | (0.9313, 0.9917) | 0.734 | 0.024 |
| 0.6 | 84 | 48 | 0.206 | 0.361 | 1.000 | (0.9563, 1.0) | 0.893 | 0.000 |
| 0.65 | 54 | 36 | 0.154 | 0.232 | 1.000 | (0.9336, 1.0) | 0.982 | 0.000 |
| 0.7 | 31 | 23 | 0.099 | 0.133 | 1.000 | (0.8897, 1.0) | 1.000 | 0.000 |

Lowest threshold with precision of at least 0.80 and coverage of at least 0.10: **0.5**
