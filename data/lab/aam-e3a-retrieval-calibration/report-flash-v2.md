# AAM-E3A retrieval calibration

Notes: 234; judged pairs: 926 (unparsed replies: 0); random negative controls rated 0: 0.817 of 230 (judge reliable: False).

## Relevance by cosine

| cosine | pairs | rated 0 | rated 1 | rated 2 |
|---|---|---|---|---|
| 0.00-0.30 | 314 | 0.783 | 0.207 | 0.010 |
| 0.30-0.40 | 201 | 0.607 | 0.383 | 0.010 |
| 0.40-0.50 | 192 | 0.401 | 0.521 | 0.078 |
| 0.50-0.60 | 110 | 0.209 | 0.554 | 0.236 |
| 0.60-0.70 | 53 | 0.019 | 0.340 | 0.641 |
| 0.70-0.80 | 23 | 0.000 | 0.087 | 0.913 |
| 0.80-1.00 | 8 | 0.000 | 0.000 | 1.000 |

## Injection at a threshold (up to three most similar earlier notes with cosine at least tau)

| tau | injected | notes served | coverage | per note | precision (1 or 2) | interval | rated 2 | noise (0) |
|---|---|---|---|---|---|---|---|---|
| 0.5 | 194 | 98 | 0.421 | 0.833 | 0.876 | (0.8225, 0.9154) | 0.459 | 0.124 |
| 0.55 | 124 | 67 | 0.288 | 0.532 | 0.944 | (0.8881, 0.9724) | 0.613 | 0.057 |
| 0.6 | 84 | 48 | 0.206 | 0.361 | 0.988 | (0.9356, 0.9979) | 0.750 | 0.012 |
| 0.65 | 54 | 36 | 0.154 | 0.232 | 1.000 | (0.9336, 1.0) | 0.852 | 0.000 |
| 0.7 | 31 | 23 | 0.099 | 0.133 | 1.000 | (0.8897, 1.0) | 0.935 | 0.000 |

Lowest threshold with precision of at least 0.80 and coverage of at least 0.10: **0.5**
