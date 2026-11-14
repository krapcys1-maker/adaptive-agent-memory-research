# Aneks C2: tolerancja dopasowania długości X i S (D12)

2026-11-13. Claude (Opus 5.5). Status: **projekt aneksu do nowej wersji protokołu.** Zamrożonej v1.0 (`e585ed8d…`) ani `FREEZE.json` nie zmieniam.
Dane: `tests/t_v10_conformity.py` → `tests/WYNIKI_ZGODNOSC_v1.0.out` (bodźce `base/stim/` po poprawce C1).

## 1. Konflikt

| | Brzmienie albo źródło | Definicja |
|---|---|---|
| **Definicja słowna v1.0** | sek. 2 (X): „przewidywana liczba tokenów … mieści się w **±20%** bloku M tej tury, a w razie braku najbliższe”; to samo w sek. 12 i w tabeli D12 (sek. 13) | **liniowa:** przyjąć, gdy \|r − 1\| ≤ 0,20, gdzie r = przewidywane tokeny losowania / przewidywane tokeny bloku M; zakres r ∈ [0,80; 1,20] |
| **Definicja prototypu** | zamrożony `k1/v0.4/testy/t_d9_length.py` (`FREEZE.json`, sha `e9016bc0…`), funkcja `matched`: `TOL = math.log(1.20)`, warunek `abs(math.log(…/target_tok)) <= TOL` | **logarytmiczna:** przyjąć, gdy \|ln r\| ≤ ln 1,2; zakres r ∈ [1/1,2; 1,2] = **[0,8333; 1,2000]**, czyli **−16,67% … +20,00%**; „najbliższe” = najmniejsze \|ln r\| |

Z prototypu pochodzą liczby, które v1.0 przytacza jako skutek D12:
- nierównowaga X +1,8% i S +2,2% (sek. 2);
- wstrzymanie prawdziwych wykryć przez regułę LEN: 4% (X) i 8% (S) (sek. 2 i 7.5).

Obie liczby odsyłają do `t_d9_length.out`. Tekst reguły i jej przytoczone skutki opisują więc dwie różne reguły.

## 2. Granice matematyczne

- Reguła logarytmiczna jest symetryczna w skali ln: ln(1/1,2) = −0,1823 ≤ ln r ≤ 0,1823.
- W skali liniowej daje to od −16,67% do +20%.
- Różnica między regułami dotyczy wyłącznie r ∈ [0,8000; 0,8333), czyli losowań **krótszych** od bloku M o 16,7–20%. Reguła liniowa je przyjmuje, logarytmiczna odrzuca i losuje dalej (do 200 prób).
- Górna granica (+20%) jest w obu regułach ta sama.

## 3. Liczba zmieniających się losowań

Z 1 542 losowań na ramię (3 instancje × 514 tur z niepustym blokiem M):

| Wariant | Różne losowania X | Różne losowania S | Fallback „najbliższe” X / S |
|---|---|---|---|
| wybrany: logarytmiczny, ρ dosłowne (po C1) = obecne bodźce | 0 | 0 | 157 / 21 |
| dosłowne ±20% liniowe, ρ dosłowne | **160** | **286** | 133 / 9 |
| prototyp: logarytmiczny, ρ ze znakami + 2 (przed C1); bodźce, z których pochodzą liczby v1.0 | 2 | 19 | 158 / 21 |

Obecne bodźce to dokładnie losowania regułą logarytmiczną (kontrola regeneracji: PASS).

Uwaga dla właściciela: przez decyzję C1 (dosłowne ρ) obecne bodźce różnią się od bodźców prototypu w **21 z 3 084** losowań (X 2, S 19). Liczby nierównowagi praktycznie się nie zmieniają (tabela 4).

## 4. Wpływ na długości i ryzyko systematycznej nierównowagi

Nierównowaga na zadanie x_i = ln(T_i(M)/T_i(C)), tokeny przewidywane jak w sek. 2. Reguła LEN: model `t_d9_length.py`, część B, przy prawdziwym efekcie treści +15 pp i braku wpływu długości.

| Wariant | M − X: średnio (5–95% na zadanie) | M − S: średnio (5–95%) | B1 (\|średnia\| ≤ 5%) | LEN wstrzymuje prawdziwe efekty X / S |
|---|---|---|---|---|
| **wybrany (log, po C1)** | **+1,83%** (−11,2 … +21,1) | **+2,31%** (−5,7 … +11,4) | spełnione | **3% / 8%** |
| dosłowne ±20% | +3,86% (−11,2 … +24,7) | +4,11% (−3,5 … +14,0) | spełnione, ale blisko progu | **14% / 20%** |
| prototyp (log, przed C1) | +1,84% (−11,2 … +21,2) | +2,24% (−5,7 … +11,0) | spełnione | 3% / 8% |

**Mechanizm.** Reguła liniowa przyjmuje losowania krótsze od M o 16,7–20%, a dłuższych powyżej +20% nie przyjmuje żadna reguła. Asymetria względem ln przesuwa więc X i S w stronę krótszych bloków. Wychodzi to systematycznie, w każdym zadaniu w tę samą stronę: M jest dłuższe o około 4% zamiast około 2%.

Skutek dla odczytu: B1 nadal przechodzi, ale reguła LEN około 3–5 razy częściej odmawiałaby przypisania prawdziwego efektu treści pamięci (14–20% zamiast 3–8%). To zmienia charakterystykę kontrastów M − X i M − S opisaną w v1.0 i zatwierdzoną w D12.

## 5. Przyczyna wyboru prototypu (decyzja właściciela C2, 2026-11-13)

- Reguła logarytmiczna wygenerowała bodźce kontrolne i liczby, na których oparto D12: +1,8% / +2,2%, LEN 4% / 8%. Właściciel zatwierdzał D12 w przekonaniu o tych właściwościach.
- Daje mniejszą i bardziej symetryczną nierównowagę długości (tabela 4).
- Właściciel **nie zatwierdza cichej reinterpretacji** „±20%”. Wybór wymaga jawnego, formalnego zapisu.

## 6. Czy sekcja 6 v1.0 pozwala na formalne sprostowanie? **Nie.**

| Przepis v1.0 | Brzmienie | Zastosowanie do C2 |
|---|---|---|
| 6.4 | „Poprawki techniczne tylko przed pierwszym wywołaniem bloku, którego dotyczą, z wpisem w protokole. **Ramiona**, zadania, stany, próg, poziom ufności, reguły odczytu i parametry próbkowania **bez zmian**.” | Tolerancja D12 wyznacza zawartość ramion X i S (160 i 286 różnych losowań) oraz charakterystykę reguły LEN. Wybór reguły innej niż słowna zmienia ramię względem tekstu. **6.4 tego nie obejmuje** |
| 6.6 | „Niejasność: wariant **prostszy i bliższy NIGHT-2**, zapisany przed blokiem, którego dotyczy.” | Słowa „±20%” są jednoznaczne i powtórzone w sek. 2, 12 i 13. Nawet traktując konflikt z przytoczonymi liczbami jako niejasność: NIGHT-2 nie ma odpowiednika tej reguły, a „prostszy” jest wariant liniowy. **6.6 wskazałaby wariant przeciwny do decyzji właściciela** |
| 14.4 | „Po zamrożeniu zmiany są możliwe tylko według sekcji 6 (poprawki techniczne z wpisem w protokole).” | Brak innej drogi w obrębie v1.0 |

**Wniosek: przed startem K1 potrzebna jest formalna nowa wersja protokołu.**

## 7. Proponowany zakres nowej wersji (do decyzji właściciela; nie wykonane)

**Wersja v1.0.1 (errata).** Zmiany wyłącznie redakcyjne co do faktów, wszystkie inne przepisy bez zmian:
1. Sek. 2 (X, S), sek. 12 i tabela D12 w sek. 13: „±20%” zastąpione zdaniem: „\|ln(przewidywane/cel)\| ≤ ln 1,2, czyli od −16,67% do +20%; w razie braku losowanie o najmniejszym \|ln(przewidywane/cel)\|”, z odesłaniem do `t_d9_length.py` (`matched`).
2. Sek. 2 (`c_d`): bez zmian. C1 wykonawca już stosuje dosłownie.
3. Zapis decyzji C1, C3, C4 (wykonanie zgodne z dosłownym tekstem) i tego aneksu w historii zmian.
4. Zamrożenie tą samą procedurą co v1.0 (`zamroz.py` albo jego odpowiednik): nowy plik, nowy sha256, nowy `FREEZE.json`. v1.0 zostaje bez zmian jako poprzednia wersja.

Po zamrożeniu v1.0.1 po stronie wykonawcy:
- kopia v1.0.1 do `spec/`;
- `spec` i `spec_frozen_sha256` w `k1_config.json`;
- `D12_tolerance` → `approved` (v1.0.1), `technical_choices_approved = true`;
- `prepare.py`, pełne testy, test runnera, kontrola zgodności;
- w `integration/` ścieżka `spec`/`protocol_path`/`pin` na v1.0.1.

Bodźce się nie zmienią, bo reguła wykonawcy już jest logarytmiczna.

**Alternatywa w granicach v1.0 bez nowej wersji:** dosłowne ±20% liniowe. Wymaga zmiany jednego warunku w `k1_lib.matched_draw` i ponownego `prepare.py`. Daje bodźce i skutki z tabeli 4 (wiersz „dosłowne”), czyli LEN 14% / 20%. Ta droga jest sprzeczna z decyzją właściciela C2.
