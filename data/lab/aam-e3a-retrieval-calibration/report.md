# AAM-E3A retrieval calibration

Notes: 234; judged pairs: 926 (unparsed replies: 0); random negative controls rated 0: 0.861 of 230 (judge reliable: False).

## Relevance by cosine

| cosine | pairs | rated 0 | rated 1 | rated 2 |
|---|---|---|---|---|
| 0.00-0.30 | 314 | 0.844 | 0.153 | 0.003 |
| 0.30-0.40 | 201 | 0.617 | 0.378 | 0.005 |
| 0.40-0.50 | 192 | 0.297 | 0.641 | 0.062 |
| 0.50-0.60 | 110 | 0.209 | 0.600 | 0.191 |
| 0.60-0.70 | 53 | 0.000 | 0.396 | 0.604 |
| 0.70-0.80 | 23 | 0.000 | 0.130 | 0.870 |
| 0.80-1.00 | 8 | 0.000 | 0.000 | 1.000 |

## Injection at a threshold (up to three most similar earlier notes with cosine at least tau)

| tau | injected | notes served | coverage | per note | precision (1 or 2) | interval | rated 2 | noise (0) |
|---|---|---|---|---|---|---|---|---|
| 0.5 | 194 | 98 | 0.421 | 0.833 | 0.881 | (0.8284, 0.9197) | 0.417 | 0.119 |
| 0.55 | 124 | 67 | 0.288 | 0.532 | 0.968 | (0.92, 0.9874) | 0.573 | 0.032 |
| 0.6 | 84 | 48 | 0.206 | 0.361 | 1.000 | (0.9563, 1.0) | 0.714 | 0.000 |
| 0.65 | 54 | 36 | 0.154 | 0.232 | 1.000 | (0.9336, 1.0) | 0.833 | 0.000 |
| 0.7 | 31 | 23 | 0.099 | 0.133 | 1.000 | (0.8897, 1.0) | 0.903 | 0.000 |

Lowest threshold with precision of at least 0.80 and coverage of at least 0.10: **0.5**
