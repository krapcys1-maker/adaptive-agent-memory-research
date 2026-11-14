# Weryfikacja mechaniczna NIGHT-1

Wygenerowano 2026-11-14T14:53:14+00:00. Błędy blokujące: brak.

| Poziom | Status |
|---|---|
| execution | pass |
| integrity | pass |
| provenance | pass |
| statistics | pass |
| comparability | pass |
| leakage | pass |
| mechanism | computed |
| replication | none |
| hypothesis | undecided |

Kontrola przecieków: pass; źródła pamięci 49, zadania testowe 58, pokrycie 0.

Efekty względem ramienia bazowego (pary zadań, dokładny McNemar):

| Porównanie | Pary | Zyski | Straty | Δ | p |
|---|---|---|---|---|---|
| sA:TrP-vs-N | 30 | 4 | 1 | 3 | 0.375 |
| sA:TrO-vs-N | 30 | 7 | 1 | 6 | 0.0703 |
| sA:TrS-vs-N | 30 | 4 | 1 | 3 | 0.375 |
| sA:TrQ-vs-N | 30 | 4 | 1 | 3 | 0.375 |
| sA:TrF-vs-N | 30 | 9 | 1 | 8 | 0.0215 |
| sA:N'-vs-N | 30 | 0 | 0 | 0 | 1.0 |
| sA:TrW-vs-N | 30 | 5 | 1 | 4 | 0.2188 |
| sA:Tr-vs-N | 30 | 4 | 1 | 3 | 0.375 |
| sC:TrO-vs-N | 20 | 2 | 0 | 2 | 0.5 |
| sC:TrP-vs-N | 20 | 0 | 0 | 0 | 1.0 |
| sD:N'-vs-N | 58 | 1 | 0 | 1 | 1.0 |
| sD:TrQ-vs-N | 58 | 7 | 2 | 5 | 0.1797 |
| sD:TrF-vs-N | 58 | 6 | 2 | 4 | 0.2891 |
| sD:R+-vs-N | 58 | 14 | 9 | 5 | 0.4049 |
| sD:TrD-vs-N | 58 | 2 | 0 | 2 | 0.5 |
| sE:N'-vs-N | 30 | 0 | 0 | 0 | 1.0 |
| sE:TrP-vs-N | 30 | 3 | 0 | 3 | 0.25 |
| sE:Tr-vs-N | 30 | 3 | 0 | 3 | 0.25 |
| sE:TrO-vs-N | 30 | 9 | 0 | 9 | 0.0039 |

Zielone testy i poprawne wykonanie nie są dowodem skuteczności; hipotezę rozstrzyga właściciel po niezależnej recenzji.
