# AAMR-K1: niezależny audyt naukowy eksperymentu

Data: 2026-11-14. Audytor: Claude (Fable 5.2). Tryb pracy: wyłącznie odczyt zamrożonych danych; zero wywołań modelu, GPU i płatnych API.

Źródła: raport `[machine-local path omitted]`, wyniki `...\base\report\results.json`, dane `...\base\eval\*.jsonl` i `...\base\run\sessions\*.jsonl`, kod `...\code\analyze.py`, `k1_length.py`, `k1_v04_reading.py`, `t_w6_cells.py`, protokół `[machine-local path omitted]` (sha256 `8b854b35…`, zgodny z kopią wykonawcy), NIGHT-2 `[machine-local path omitted]`.
Skrypty audytu: `[machine-local path omitted]` (każda liczba z tego raportu pochodzi z nich albo z plików wskazanych przy liczbie).

**Wszystko poza sekcją 2 jest analizą eksploracyjną** (dodaną po poznaniu wyników, bez korekty na wielokrotne porównania, o ile nie napisano inaczej). Nie zmienia stanów K1 ani progów.

---

## 1. Werdykt o wiarygodności K1

**K1 jest wiarygodny jako pomiar i poprawnie odczytany w części głównej.** Trzy kontrasty, przedziały 98,33% i stany odtworzyłem z surowych danych co do cyfry. Analiza jest zgodna z zamrożonym protokołem. Wniosek główny raportu jest uprawniony: żaden kontrast nie wykrył efektu, a przedziały M − P i M − X nie wykluczają ani zera, ani 10 pp.

Trzy zastrzeżenia do raportu:

1. **Zdanie „M − S wyklucza cały historyczny zysk 8,1 pp” jest formalnie poprawne, ale kruche.** Górna granica wynosi 7,69 pp przy progu 8,108, czyli zapas 0,42 pp. Przy poszerzeniu o wykrytą zależność przez wspólne ślady granica rośnie do 9,5 pp, po korekcie długości do 13,1 pp, a na 88 zadaniach testowych do 14,3 pp. Nie należy go cytować jako ustalenia.
2. **Zdanie „różnica długości bloków może wyjaśniać ten wynik” nie ma pokrycia w danych.** Flagę LEN wywołało wyłącznie poszerzenie przedziału po regresji, nie zależność wyniku od długości (sekcja 2.4).
3. **Raport jest niekompletny względem sekcji 11 protokołu.** Brakuje tablicy ramię × blok w 6 warstwach (pkt 2); WR1–WR3 i statystyki nierównowagi `x_i` są tylko w `results.json`, nie w `K1_RAPORT.md` (pkt 3 i 8). Nie wpływa to na stany.

Najważniejsze ustalenie audytu wykracza poza raport: **średni efekt bliski zera nie oznacza, że pamięć jest obojętna.** Na poziomie pojedynczych zadań blok pamięci silnie i powtarzalnie zmienia wynik w obu kierunkach, a te zmiany się znoszą (sekcja 3).

---

## 2. Weryfikacja statystyki (potwierdzająca)

### 2.1 Odtworzenie liczb

| Wielkość | Raport | Audyt (własny kod) |
|---|---|---|
| M − P, 98,33% | +2,70 [−5,97; 11,37], V4 | +2,7027 [−5,9683; 11,3737] |
| M − X | +4,05 [−4,35; 12,46], V4 | +4,0541 [−4,3500; 12,4581] |
| M − S | −0,23 [−8,14; 7,69], V5 | −0,2252 [−8,1370; 7,6865] |
| Odsetki N / P / X / S / M | 32,9 / 32,0 / 30,6 / 34,9 / 34,7 | identyczne |
| M − N (95%) | +1,8 [−5,5; 9,1] | identyczne |
| Blok A, M − P | +4,7 [−4,4; 13,9] | 56 wobec 49 ze 148; zyski 27, straty 20 |
| ρ̃ i p (M − P / M − X / M − S) | +0,017, 0,119 / −0,003, 0,581 / +0,030, 0,016 | +0,017, 0,115 / −0,003, 0,591 / +0,030, 0,020 (inne ziarno, 5 000 permutacji) |
| WR1 bootstrap | [−5,6; 11,0] / [−3,8; 12,6] / [−7,7; 7,4] | [−5,6; 11,0] / [−4,1; 12,2] / [−7,7; 7,2] |
| WR5: średnia `x`, α, przedział α, β | 0,0205 / 0,0280 / 0,0402 itd. | identyczne do 4 cyfr, z bodźców odtworzonych własnym kodem (5 917 z 5 917 długości bloków zgodnych z zapisem epizodów) |
| Dryf: zgodność z NIGHT-2 | N 86/88 i 57/60; M 83/88 i 55/60 | identyczne |

Kwantyl t(147) dla 98,33% wynosi 2,4217; korekta Bonferroniego na 3 kontrasty jest zastosowana poprawnie. Drabina opisowa ma przedziały 95% bez korekty, zgodnie z protokołem.

### 2.2 Zgodność implementacji z protokołem

- **Miara (7.1, 7.2):** 2 220 komórek, 0 braków technicznych, 0 wykluczonych zadań. 214 epizodów z limitem kroków i 4 z przepełnieniem kontekstu liczone jako 0. Zgodne.
- **Kontrasty (7.3):** średnia różnic po zadaniach, przedział t. Zgodne.
- **Stany i odczyt (8):** funkcja `state` i zdania z `k1_v04_reading.py` zgodne z tabelą stanów.
- **WR5 i LEN (7.5):** zgodne z brzmieniem erraty E3.
- **Kontrola przecieków po przebiegu:** sprawdza zgodność zapisanych śladów z zamrożonymi bodźcami i pochodzenie śladów (9 686 źródeł, 0 naruszeń). To kontrola reguł L1/L3, nie dowód braku jakiegokolwiek przecieku. Bloki M z założenia zawierają linie identyczne z wywołaniem wzorcowym (L9: 18,5% linii; S 12,6%).

### 2.3 Założenia, zależności, precyzja

- **Estymand a przedział.** Protokół deklaruje estymand skończonej populacji (te 148 zadań, losowe tylko próbkowanie), ale liczy przedział jak dla losowej próby zadań. Dla deklarowanego estymandu przedział jest wyraźnie za szeroki: w symulacji na empirycznych odsetkach pokrycie wynosi około 100% zamiast 98,33%. Błąd standardowy z samego szumu próbkowania to 2,0–2,3 pp wobec użytych 3,3–3,6 pp. Kierunek błędu jest ostrożny. *Eksploracyjnie*, dla tych 148 zadań: M − P [−2,5; 7,9], M − X [−0,7; 8,8], M − S [−5,7; 5,3]. Nadal żaden kontrast nie wykrywa efektu.
- **Wspólne ziarno w bloku.** Niezgodność między ramionami w tym samym bloku (M z N: 0,315) jest taka sama jak między blokami o różnych ziarnach (0,313). Wspólne ziarno nie zaniża niezgodności.
- **Kolejność ramion.** Rozkład pozycji ramion nie odbiega od losowego (χ², p = 0,30), a pozycja nie wpływa na wynik (p = 0,57).
- **Precyzja.** Połowa przedziału 7,9–8,7 pp, zgodnie z planem (8,9). K1 mógł wykryć efekty od około 12 pp. 38 ze 148 zadań nie rozwiązano ani razu w 15 epizodach, 4 rozwiązano zawsze.
- **`w` ramion P, X, S** (0,21 / 0,18 / 0,25) zawiera też zmienność bodźców między blokami, więc nie jest czystym szumem próbkowania. Czysty szum to `w(N)` = 0,153 i `w(M)` = 0,180.

### 2.4 Długość promptów i reguła LEN

- Średnia liczba tokenów promptu na wywołanie: P 2 398, X 2 373, S 2 396, M 2 400 (różnice do 1,1%). N jest krótsze o 15%, co dotyczy tylko opisowego M − N.
- Kryterium B1 (±5%) spełnione we wszystkich kontrastach: +2,1% (P), +2,8% (X), +4,1% (S). Zmierzona nierównowaga jest o około 2 pp większa niż przewidywana przy zamrożeniu (−0,1%, +1,8%, +2,3%), a M − S jest blisko granicy.
- **Flaga LEN dla M − S** wynika tylko z kryterium „stan po korekcie inny niż główny”. Regresja przesuwa estymatę z −0,2 na +2,4 pp i poszerza połowę przedziału z 7,9 do 10,7 pp, więc górna granica przekracza 10 pp. Nachylenie β = −65 pp [−224; 94] nie odróżnia się od zera.
- *Eksploracyjnie:* losowania S i X różnią się długością między blokami w obrębie tego samego zadania. Wynik nie zależy od tej długości (S: p = 0,65; X: p = 0,89). Dla P zmienność długości w zadaniu jest zbyt mała, by cokolwiek powiedzieć.
- **Ocena:** nie ma śladu, że długość wyjaśnia wyniki K1. Kryterium LEN „zmiana stanu” karze nieprecyzyjność korekty i przy stanie V5 blisko granicy włącza się niemal automatycznie. To słabość konstrukcji reguły, nie dowód problemu z długością.

### 2.5 Niezgodność dryfu w bloku A

- NIGHT-2 i K1 używały tego samego stosu: Ollama 0.40.16, ten sam skrót modelu (`run\state.json` w NIGHT-2, `T.json` w K1).
- 128 wywołań bloku A ma **identyczny skrót żądania** jak w NIGHT-2 i **inną odpowiedź**; 45 z nich to pierwsze wywołanie epizodu. Rozjechało się 129 z 296 epizodów (44%), wynik zmienił się w 15 (5,1%): N 5, M 10 (test Fishera p = 0,29, czyli brak dowodu, że M jest mniej stabilne).
- **To nie jest dryf wersji, tylko niedeterminizm stosu przy temperaturze 0.** Próg 84/88 i 57/60 skalibrowano na powtórkach N′ (1 i 0 zmian), które zaniżyły rozrzut. NIGHT-1 odnotował to samo zjawisko (13 z 58 epizodów).
- **Konsekwencje:** stany z bloków próbkowanych pozostają ważne. Natomiast każdy pojedynczy przebieg przy temperaturze 0 (cały NIGHT-1 i NIGHT-2) jest jednym losowaniem, nie wartością deterministyczną. Historyczne M − N = +12 zadań (8,1 pp) w powtórce K1-A daje +7 (4,7 pp): test 37 wobec 28, trening 19 wobec 21.
- Przyczyny niedeterminizmu (jądra GPU, pamięć podręczna, kolejność żądań) nie da się ustalić bez uruchamiania modelu.

---

## 3. Najważniejsze odkrycia i ograniczenia (eksploracyjne)

### 3.1 Efekt pamięci jest silnie niejednorodny, a średnia to wynik znoszenia

Rozrzut różnic między ramionami na zadaniach jest znacznie większy, niż tłumaczy szum próbkowania (test permutacyjny etykiet ramion w zadaniu):

| Para | Odch. std. prawdziwego efektu na zadanie | p |
|---|---|---|
| M − N | 38 pp | 0,0002 |
| M − P | 35 pp | 0,0002 |
| M − X | 34 pp | 0,0002 |
| M − S | 28 pp | 0,0002 |
| S − N | 29 pp | 0,0002 |
| P − N | 22 pp | 0,001 |
| X − P | 14 pp | 0,03 |

Nawet neutralna proza zmienia wyniki na konkretnych zadaniach, ale prawidłowa pamięć zmienia je najmocniej.

### 3.2 Wzorzec z NIGHT-2 powtarza się w niezależnych danych K1

Zadania pogrupowane według wyniku NIGHT-2 (temperatura 0), odsetki z bloków próbkowanych K1 (inne ziarna, inna temperatura):

| Grupa wg NIGHT-2 | n | N | P | X | S | M |
|---|---|---|---|---|---|---|
| M rozwiązało, N nie | 33 | 17,2 | 24,2 | 29,3 | 38,4 | **75,8** |
| N rozwiązało, M nie | 21 | **77,8** | 60,3 | 60,3 | 41,3 | 11,1 |
| oba rozwiązały | 27 | 87,7 | 76,5 | 71,6 | 77,8 | 80,2 |
| żadne | 67 | 4,5 | 9,0 | 5,5 | 13,9 | 3,5 |

- Na 33 zadaniach „zysku”: M − S = +37 pp [24; 51], M − P = +52 pp [39; 64].
- Na 21 zadaniach „straty”: M − S = −30 pp [−47; −14], M − N = −67 pp [−81; −52].
- Ramiona kontrolne układają się w stopnie między N a M: dobór śladów ma znaczenie na konkretnych zadaniach, w obu kierunkach. Bilans: +19,3 − 14,0 − 2,6 zadania, czyli +1,8 pp.

### 3.3 Informacja w bloku nie jest wąskim gardłem

- Bloki M pokrywają wszystkie funkcje wzorcowe tury w 67% przypadków (25% zawiera dokładną linię wzorcową). Bloki S: 25% (11%). X: 0%.
- Mimo to na 391 sparowanych turach, gdzie blok M pokrywa funkcje wzorcowe, a blok S nie, odsetek zaliczeń jest taki sam: M 74,2%, S 74,7%.
- Ramię N samo wywołuje wszystkie funkcje wzorcowe w około 91% tur. Nieudane tury to głównie nadmiarowe wywołania (38%), właściwe funkcje z błędnymi argumentami lub liczbą (22–28%), limit kroków (11–14%). Sam brak funkcji wzorcowej to 10–12%.

### 3.4 Pamięć pomaga na pierwszej turze, potem zysk znika

Zaliczenie tury 0: N 64,9%, P 66,7%, X 62,6%, S 66,9%, M 71,4%; M − N = +6,5 pp [0,2; 12,8] (bootstrap po zadaniach, bez korekty). W turze 1 przewagi już nie ma (M 67,5%, N 69,5%, przy większym zbiorze M). Miara „wszystkie tury zaliczone” sprowadza +6,5 pp do +1,8 pp.

### 3.5 Zanieczyszczenie jest mierzalne, z kontrolą

Miara: model używa wartości obecnej w bloku, a nieobecnej w prośbach i wcześniejszych wynikach narzędzi. Poziom przypadkowy: ta sama miara dla ramienia N względem bloku M, którego N nie widziało.

- Wartość z bloku: M 16,3% tur wobec 10,9% przypadkowo; nadwyżka +5,4 pp [2,6; 8,3].
- Funkcja spoza wzorca obecna w bloku: M 26,0% wobec 19,7%; nadwyżka +6,3 pp [2,6; 10,1].
- W zadaniach „straty” znaczniki występują w 37 z 56 nieudanych tur M (66%) wobec 14 z 54 (26%) dla N na tych samych turach.
- Pięć najgorszych śladów (każdy pokazany 6–9 zadaniom, M − N od −25 do −39 pp) pochodzi z TRAVEL.

### 3.6 Domeny

| Domena | M − N | S − N | M − S |
|---|---|---|---|
| GFS (50) | +8,0 [−3,3; 19,3] | +8,7 [−1,6; 18,9] | −0,7 |
| VC (50) | +4,0 [−7,3; 15,3] | −6,0 | +10,0 [0,0; 20,0] |
| TRAVEL (48) | −6,9 [−22,8; 8,9] | +3,5 | −10,4 [−24,0; 3,1] |

Zróżnicowanie M − S między domenami: p = 0,04 bez korekty. Kierunek (GFS zysk, TRAVEL strata) zgadza się z NIGHT-1 i NIGHT-2, ale sam K1 tego nie rozstrzyga.

### 3.7 Ograniczenia

- 148 zadań daje wykrywalność od około 12 pp; efektów 3–8 pp K1 nie rozróżnia.
- 26% zadań jest poza zasięgiem modelu w każdym ramieniu; 16 z 38 zawodzi w tej samej turze we wszystkich 15 epizodach.
- Jedna pula śladów, jeden model, jedna prezentacja (2 surowe ślady przed prośbą).
- Analizy z sekcji 3 wybrano po obejrzeniu danych; grupy z 3.2 zdefiniowano na niezależnych danych, ale reszta wymaga potwierdzenia.

---

## 4. Sukcesy i porażki pamięci

Metryki liczył kod jednakowo dla wszystkich ramion. Dodatkowo oceniłem ręcznie 24 nieudane tury bez etykiety ramienia i bez bloku pamięci (`scripts\blind_cases.txt`, klucz w `blind_key.json`).

| Sytuacja | Liczba zadań | Co widać |
|---|---|---|
| M wygrywa z N i P (≥ 2/3) | 13 | Wszystkie 13 to zadania „zysku” z NIGHT-2. N zawodzi tam przez nadmiarowe wywołania i błędne argumenty; M zalicza tę samą turę w 65 z 82 przypadków, w 24 z 65 dosłownie powtarzając linię z bloku. |
| M przegrywa z N lub P (≥ 2/3) | 25 (z obojgiem: 11) | 17 to zadania „straty” z NIGHT-2. 12 z 25 to TRAVEL. W nieudanej turze M: obce wartości lub funkcje z bloku w 66% przypadków wobec 26% poziomu przypadkowego. |
| S wygrywa z M (≥ 2/3) | 15 | 8 z TRAVEL. Przy czystym szumie oczekiwałoby się około 7 (zakres 2–12). |
| M wygrywa z S (≥ 2/3) | 13 | 6 z VC. Również ponad poziom szumu. |
| M i S podobne (≤ 1/3) | 120 | Większość zadań; w GFS oba ramiona zyskują podobnie wobec N. |
| Wszystkie ramiona zawodzą | 38 | Rozkład przyczyn taki sam w każdym ramieniu. Blok M pokrywał tam funkcje wzorcowe w 62 ze 114 nieudanych tur, bez skutku. |

Ocena zaślepiona: 3 przypadki oznaczyłem jako „obca wartość”, 2 jako „możliwa”. Po odtajnieniu: 1 pewny w M (data i numer rezerwacji ze śladu), 1 pewny w S, 2 możliwe w M, a 1 w N okazał się moim błędem (wartość pochodziła z wyniku narzędzia). Ręczna ocena jest więc mniej wiarygodna niż miara automatyczna z poziomem odniesienia. Dominujące przyczyny porażek we wszystkich ramionach nie mają związku z pamięcią: pominięte przejście do katalogu, ilość paliwa wymagająca odczytu stanu, zgadywane kody lotnisk, zbędne dodatkowe wywołania.

Korelacja a przyczyna: nadwyżka kopiowania w M jest ustalona z kontrolą. To, że kopiowanie *powoduje* utratę zadania, jest wnioskiem z asocjacji i wymaga eksperymentu (sekcja 6, A).

---

## 5. Ranking wyjaśnień

| # | Wyjaśnienie | Ocena | Pewność |
|---|---|---|---|
| 1 | **D. Wspomnienia czasem zanieczyszczają**, obok realnej pomocy na innych zadaniach; średnia to bilans | Zanieczyszczenie występuje (nadwyżka z kontrolą, powtarzalne zadania straty). Że to główna przyczyna zerowego bilansu: prawdopodobne, nieudowodnione | wysoka co do zjawiska; średnia co do roli |
| 2 | **A/B w wersji zawężonej:** ślady niosą wiedzę o funkcjach, którą model w większości już ma, a nie niosą informacji o stanie i wartościach bieżącego zadania, która decyduje | Zgodne z 3.3 | średnia do wysokiej |
| 3 | **E. Benchmark i miara są mało czułe** | Pewne jako ograniczenie (moc, 26% zadań na dnie, miara wszystkich tur); jako wyjaśnienie braku efektu częściowe | średnia |
| 4 | **C. Ogólny kontekst domeny równie użyteczny** | Prawdziwe w GFS; fałszywe jako opis całości, bo M i S różnią się na zadaniach (p = 0,0002) | niska do średniej |
| 5 | A dosłownie: wspomnienia nie zawierają istotnych informacji | Sprzeczne z danymi (pokrycie 67% wobec 25%) | niska |
| 6 | B dosłownie: model nie wykorzystuje informacji | Sprzeczne z danymi (M zmienia zachowanie najmocniej, model kopiuje z bloku) | bardzo niska |

---

## 6. Wnioski i kierunek

### 6.1 Co K1 wspiera, osłabia, czego nie rozstrzyga

- **Wspiera:** brak średniego efektu rzędu 12 pp i więcej wobec P, X, S w reżimie próbkowanym; średni efekt doboru (M − S) mały; wyniki przy temperaturze 0 są pojedynczymi losowaniami.
- **Osłabia:** tezę, że R+ daje oczekiwany zysk około 8 pp (w reżimie próbkowanym +1,8 pp; test +4,5, trening −2,2); tezę, że „to tylko dodatkowy tekst” (P zachowuje się jak N, nie jak M); tezę, że pamięć jest obojętna.
- **Nie rozstrzyga:** czy istnieje średni efekt 3–8 pp; M − P i M − X; przenoszalności na inną pulę, model i prezentację; wpływu samego nagłówka.

### 6.2 Porównanie z NIGHT-1 i NIGHT-2

| | NIGHT-1 (R+) | NIGHT-2 (E\*/R+) | K1 blok A | K1 próbkowany |
|---|---|---|---|---|
| Reżim | temp. 0, 1 przebieg | temp. 0, 1 przebieg | temp. 0, 1 przebieg | temp. 0,7, 3 bloki |
| Test | 22 wobec 17 z 58 (14/9) | 38 wobec 28 z 88 (22/12) | 37 wobec 28 (21/12) | +4,5 pp [−5,0; 14,1] |
| Trening | — | 22 wobec 20 z 60 (11/9) | 19 wobec 21 (8/10) | −2,2 pp [−13,9; 9,4] |
| Kontrola placebo bloku | brak | brak | P: 49 ze 148, jak N | P, X, S |

Źródła NIGHT: `...\aamr-night1-worktree\data\lab\aamr-night1\REPORT.md`, `...\aamr-night2-worktree\data\lab\aamr-night2\REPORT.md`, surowe sesje `...\aamr-night2-2026-11-13\run\sessions\`.

Dlaczego historyczne +8,1 pp maleje do +1,8 pp:
1. **Progowanie.** Przy temperaturze 0 zmiana prawdopodobieństwa z 0,17 na 0,76 liczy się jako pełne zadanie.
2. **Szum pojedynczego przebiegu.** Powtórka daje +7 zamiast +12.
3. **Selekcja i wielokrotne użycie.** E\* wybrano jako najlepsze z trzech na zbiorze treningowym; zadania testowe i ich ślady były używane w pilocie, S1 i NIGHT-1.

Obserwacje NIGHT zgodne z K1: straty R+ po bloku pamięci i kopiowanie (analiza po fakcie), ślepe podążanie za nieaktualną notatką (TrS), wzorzec domen.
Obserwacja, która komplikuje prostą naprawę: w NIGHT-2 ślady z zamaskowanymi wartościami wypadły gorzej niż surowe (M2 14, M1 18 wobec R+ 22 i N 20 na 60 zadaniach, jeden przebieg).

### 6.3 Poprawiać retrieval czy zmienić reprezentację

Dane K1 nie wskazują trafności wyszukiwania jako wąskiego gardła: wyszukiwanie już dostarcza śladów znacznie trafniejszych niż losowe (67% wobec 25% pokrycia funkcji), a ta przewaga nie przekłada się na wynik. Problem leży w tym, **co** i **kiedy** trafia do promptu: surowe ślady epizodów z cudzymi wartościami pomagają tam, gdzie zadanie jest prawie kopią, i szkodzą tam, gdzie model przenosi szczegóły. Dalsze strojenie rankingu przy tej samej prezentacji ma małą oczekiwaną wartość. Kierunek wart sprawdzenia to reprezentacja i warunki użycia, ale wynik M2/M1 z NIGHT-2 ostrzega, że samo maskowanie nie wystarczy.

### 6.4 Pamięć „pajęczynowa”

- **Za:** zależność przez wspólne ślady w M − S (ρ̃ = +0,030, p = 0,016–0,020) i wyraźnie „dobre” oraz „złe” ślady sugerują, że jednostką o trwałych właściwościach jest ślad. Wagi powiązań uczone z wyników mogłyby tłumić ślady szkodliwe.
- **Przeciw:** nic w K1 nie wskazuje, że brakuje powiązań. Porażki nie wynikają z brakującego kontekstu (brak funkcji to 10–12% nieudanych tur), tylko z nadmiaru szczegółów i ze stanu zadania. Sieć powiązań zwykle wprowadza do promptu więcej treści, czyli zwiększa ryzyko zanieczyszczenia. Uczenie wag wymaga wielu obserwacji na ślad; teraz 71 śladów ma po 6 lub więcej zadań.
- **Ocena:** hipoteza otwarta, ale nie następny krok. Najpierw trzeba wiedzieć, czy szkodę da się usunąć (A) i mieć instrument mierzący 3–5 pp (B). Potem pamięć pajęczynową można porównać jako jedno z ramion z płaską pamięcią o tej samej prezentacji i z tymi samymi kontrolami P i S.

### 6.5 Proponowane eksperymenty (do decyzji właściciela; nic nie wdrożono)

**A. Rozdzielenie pomocy od zanieczyszczenia na zadaniach o powtarzalnym efekcie (rekomendowany jako pierwszy).**
- *Pytanie:* czy stratę powodują skopiowane wartości, i czy zysk przetrwa ich usunięcie.
- *Zadania:* 33 „zysku”, około 29 „straty” (21 z NIGHT-2 i 8 z K1), 30 losowych pozostałych jako kontrola nowych szkód.
- *Ramiona:* N, P, M (surowe ślady), M-abs (te same ślady, wartości zastąpione typami, bez wyników narzędzi), S-abs (losowe ślady domeny w tej samej postaci). 4 bloki próbkowane.
- *Koszt:* około 92 × 5 × 4 × 9,5 ≈ 17 500 wywołań lokalnych, około 7 godzin, 0 USD.
- *Dane:* istniejące pule i plany K1; nowy, zamrożony przed startem kod abstrakcji.
- *Placebo:* P (długość), S-abs (postać bez doboru).
- *Obalenie:* hipoteza zanieczyszczenia przewiduje M-abs − M ≥ +20 pp na zadaniach straty. Jeśli górna granica przedziału jest poniżej +15 pp, kopiowanie wartości nie jest przyczyną. Jeśli na zadaniach zysku M-abs traci ponad połowę przewagi M nad N, zysk pochodzi z konkretnych wartości i prawie-kopii, a abstrakcja nie jest drogą naprzód.
- *Wartość informacyjna:* wysoka. Każdy wynik zmienia kierunek: albo naprawa reprezentacji, albo bramkowanie, albo wniosek, że surowy ślad jest użyteczny tylko jako prawie-kopia. Kontrast M-abs − M liczony w nowych danych nie jest obciążony doborem zadań.

**B. Instrument na poziomie tury (rozstrzyga E i średni efekt).**
- *Pytanie:* jaki jest średni efekt M − N, M − P, M − S z precyzją około ±3–5 pp, bez rozmywania przez miarę wszystkich tur.
- *Projekt:* jednostką jest tura ze stanem ustawionym odtworzeniem wywołań wzorcowych wcześniejszych tur (520 tur ze 148 zadań). Ramiona N, P, S, M, 3 bloki.
- *Koszt:* około 520 × 4 × 3 × 3,3 ≈ 20 600 wywołań, około 8 godzin.
- *Dane i ryzyko:* wymaga użycia odpowiedzi wzorcowych wcześniejszych tur do ustawienia stanu i historii, czyli nowej, jawnej reguły przecieków. Tury jednego zadania są zależne, więc analiza po zadaniach. Rozszerzenie na inne kategorie BFCL dla ponad 1 000 jednostek: dostępność niezweryfikowana.
- *Placebo:* P i S.
- *Obalenie:* jeśli przedział M − N na turach mieści się w ±3 pp, średniej korzyści praktycznie nie ma także na poziomie tury. Jeśli zysk z tury 0 (+6,5 pp) się nie powtórzy, był artefaktem eksploracji.
- *Wartość informacyjna:* średnia do wysokiej; daje też trwały instrument dla kolejnych wariantów pamięci.

**C. Moment i warunek użycia (po A).**
- *Pytanie:* czy tę samą treść da się podać tak, by zachować zyski i ograniczyć straty.
- *Ramiona:* N, M-zawsze, M-po-błędzie (te same ślady pokazane dopiero po błędzie narzędzia), P-po-błędzie (placebo tej samej długości w tym samym momencie).
- *Koszt:* 148 × 4 × 3 × około 10 ≈ 17 800 wywołań.
- *Obalenie:* hipoteza przewiduje mniej strat przy zachowanych zyskach. Odrzucona, jeśli M-po-błędzie nie różni się od P-po-błędzie albo traci zyski z zadań z grupy „zysku”. W NIGHT-2 ramiona z notatkami po błędzie miały 2–3 straty wobec 12 dla bloku, ale bez placebo bloku i w jednym przebiegu.
- *Wartość informacyjna:* średnia; zależy od wyniku A.

---

## 7. Trzy kategorie ustaleń

**POTWIERDZONE PRZEZ DANE**
- Liczby, przedziały i stany K1 odtwarzają się z surowych danych; analiza jest zgodna z protokołem v1.0.1.
- Żaden z trzech kontrastów nie wykrył efektu; M − P i M − X nie wykluczają ani 0, ani 10 pp.
- Przedziały są ostrożne względem deklarowanego estymandu skończonej populacji.
- Niezgodność dryfu wynika z niedeterminizmu przy identycznych żądaniach na tym samym stosie, nie ze zmiany wersji.
- Flaga LEN dla M − S wynika z poszerzenia przedziału po korekcie, a nie z wykazanej zależności od długości.
- Zamrożone artefakty nie zostały zmienione (skróty `K1_RAPORT.md`, `results.json` i specyfikacji zgodne z `closure_2026-11-14\SHA256SUMS.txt` i `FREEZE.json`).

**HIPOTEZY EKSPLORACYJNE** (wsparte danymi K1, wymagają potwierdzenia)
- Efekt pamięci jest niejednorodny i powtarzalny na zadaniach; średnia to bilans zysków i strat.
- Zanieczyszczenie obcymi wartościami i funkcjami jest istotną przyczyną strat.
- Wąskim gardłem nie jest trafność wyszukiwania, tylko postać i moment podania treści oraz stan zadania.
- Pamięć pomaga głównie w pierwszej turze.
- Wzorzec domen: GFS zysk także z losowych śladów, VC zysk z doboru, TRAVEL strata.
- Historyczne +8,1 pp jest zawyżone przez progowanie, szum i selekcję.

**JESZCZE NIEZWERYFIKOWANE**
- Związek przyczynowy między kopiowaniem a utratą zadania.
- Czy abstrakcja śladów zachowuje zyski (wynik M2/M1 z NIGHT-2 sugeruje ostrożność).
- Istnienie średniego efektu 3–8 pp.
- Przenoszalność na inną pulę, model, prezentację; wpływ nagłówka.
- Źródło niedeterminizmu przy temperaturze 0.
- Wartość pamięci z dynamicznymi powiązaniami: brak danych za i przeciw poza pośrednimi.
- Surowych danych NIGHT-1 nie przeliczałem; liczby NIGHT-1 pochodzą z jego raportu.

---

## 8. Przebieg audytu i odstępstwa

- Nie uruchomiono Ollamy, GPU ani płatnych API. Nie zmieniono koordynatora, GitHuba, zamrożonych artefaktów ani `sealed/`. Zapieczętowany pilotaż N/M nie został otwarty.
- Jedyne zapisy: ten folder (`[machine-local path omitted]`) i katalog tymczasowy sesji.
- Odstępstwo do odnotowania: pomocnicza sesja zbierająca fakty o NIGHT-1/NIGHT-2 wykonała po jednym `git log` i `git status` w katalogach `aamr-night1-worktree` i `aamr-night2-worktree`. `git status` może odświeżyć pamięć podręczną indeksu w `.git`; plików roboczych nie zmienia.
- Odpowiedzi wzorcowe BFCL czytałem wyłącznie w analizie po przebiegu (jak miara L9 w protokole).
- Moje pierwsze, przybliżone odtworzenie WR5 dało inne liczby niż raport; po dokładnym odtworzeniu z bodźców rozbieżność zniknęła. Błąd był po mojej stronie.

---

*Integration note (2026-11-14).* Imported from the audit folder of the AI auditor (Fable 5.2); SHA-256 of the original `4b5050c905030220b9ea31daf708a55c5640e605fd9e3f23189cb520ea525851`. The text is the original, in Polish; the only edits are the machine-local path replacements listed in `PUBLISHED_FILES.json`. It is an AI audit written after the results were known (everything outside its section 2 is exploratory by its own statement), not an independent human review. See `README.md` in this directory.
