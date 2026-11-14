# Weryfikacja mechaniczna NIGHT-2

Wygenerowano 2026-11-14T14:53:15+00:00. Błędy blokujące: brak.

| Poziom | Status |
|---|---|
| execution | warn |
| integrity | pass |
| provenance | pass |
| statistics | pass |
| comparability | pass |
| leakage | pass |
| mechanism | computed |
| replication | none |
| hypothesis | undecided |

Kontrola przecieków: pass; źródła pamięci 57, zadania testowe 88, pokrycie 0.

Efekty względem ramienia bazowego (pary zadań, dokładny McNemar):

| Porównanie | Pary | Zyski | Straty | Δ | p |
|---|---|---|---|---|---|
| E1:M2-vs-N | 60 | 5 | 11 | -6 | 0.2101 |
| E1:M1-vs-N | 60 | 8 | 10 | -2 | 0.8145 |
| E1:R+-vs-N | 60 | 11 | 9 | 2 | 0.8238 |
| E1:N'-vs-N | 60 | 0 | 0 | 0 | 1.0 |
| E3:V0q-vs-N | 88 | 18 | 12 | 6 | 0.3616 |
| E3:N'-vs-N | 88 | 0 | 1 | -1 | 1.0 |
| E3:V0-vs-N | 88 | 20 | 13 | 7 | 0.2962 |
| E3:E*-vs-N | 88 | 22 | 12 | 10 | 0.1214 |
| E3:TrT-vs-N | 88 | 10 | 2 | 8 | 0.0386 |
| E3:TrQ-vs-N | 88 | 9 | 3 | 6 | 0.146 |
| E4:C-G-vs-N | 88 | 12 | 8 | 4 | 0.5034 |
| E4:C-RB-vs-N | 88 | 11 | 8 | 3 | 0.6476 |
| E4:K-vs-N | 88 | 16 | 11 | 5 | 0.4421 |
| E5:N'-vs-N | 88 | 0 | 1 | -1 | 1.0 |
| E5:K-vs-N | 88 | 17 | 12 | 5 | 0.4583 |

Zielone testy i poprawne wykonanie nie są dowodem skuteczności; hipotezę rozstrzyga właściciel po niezależnej recenzji.
