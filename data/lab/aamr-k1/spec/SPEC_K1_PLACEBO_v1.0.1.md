# AAMR-K1 (EXP-PLACEBO-0): specyfikacja, wersja 1.0.1 (errata do 1.0; ZAMROŻONA)

2026-11-13. Redakcja: Claude (Opus 5.5). Treść wersji 0.4 (`../v0.4/SPEC_K1_PLACEBO_v0.4.md`, po poprawkach W1–W9 i warunkach D9, D11) uzupełniona o pomiar szumu z pilotażu K1-CAL-NM i o stan decyzji właściciela.
Status: **ZAMROŻONA 2026-11-13 (errata v1.0.1; obowiązuje zamiast 1.0); niewykonana.** Errata zastępuje wersję 1.0 (sha256 `e585ed8dac5670f906e7deceaf89b306a89bece30acd2da06b8d5be781dd38df`; `../v1.0/` bez zmian). Zakres: sekcja „Errata v1.0.1”. Zmiany tylko według sekcji 6.

Pliki erraty (ten folder): `kontrola_erraty.py` z wynikiem `kontrola_erraty.out` (niezależne odtworzenie losowań D12 i wartości kontrolnych), `zastosuj_errate.py` (dokładny zapis zmian tekstu), `kontrola_spojnosci.py` z wynikiem `kontrola_spojnosci.out` (różnica tekstu względem 1.0), `zamroz_v101.py` (procedura zamrożenia). Charakterystyka przy zmierzonym szumie bez zmian: `../v1.0-rc/k1_power_measured.py`, `.out`. Źródło erraty: `D:/aamr-k1-executor/ANEKS_C2_D12.md` i `D:/aamr-k1-executor/DZIENNIK_DECYZJI_K1.md` (decyzje właściciela C1–C4).
Dowody i testy wersji 0.4: `../v0.4/` (`../v0.4/ZAMKNIECIE_K1_v0.4.md`, `../v0.4/UZUPELNIENIE_D9_D11.md`, `../v0.4/testy/`). Pilotaż: `../../pilot-nm/` (raport `report/RAPORT_PILOTAZ_NM.md`; wyniki według ramion zapieczętowane, nieotwarte).
Wersje poprzednie, bez zmian: `../v1.0/` (zamrożona 1.0 i jej `FREEZE.json`), `../v1.0-rc/`, `../v0.4/`, `../v0.3/`, `../SPEC_K1_PLACEBO.md` (0.2), `../SPEC_K1_PLACEBO_v0.1.md`.

## Co ten eksperyment może, a czego nie może rozstrzygnąć

Na 148 zadaniach **nie da się wiarygodnie rozdzielić wpływu dodatkowego tekstu, formatu śladów i treści pamięci, jeśli efekty są rzędu historycznego (3–9 pp).** Żadna analiza tego nie zmieni; ograniczeniem jest liczba zadań.

| Jeśli prawdziwy efekt w kontraście wynosi | K1 wykryje go w | K1 wykluczy poziom 10 pp w |
|---|---|---|
| 0 pp | 1% (błąd) | 62% |
| 5 pp | 15% | 15% |
| 8 pp (cały historyczny zysk M − N) | 43% | 4% |
| 10 pp | 64% | 1% (błąd) |
| 15 pp | 98% | 0% |

Liczby policzono przy szumie **zmierzonym** w pilotażu K1-CAL-NM: `w` = 0,159, `b` = 0,307, odsetek rozwiązań 0,345 (sekcja 9.0). Wcześniej, przy szumie zakładanym, podawano zakresy, np. przy 10 pp 35–71%. W narożnikach przedziałów 95% zmierzonego szumu wykrycie przy 10 pp wynosi 41–81%. Model symulacji jest nadal modelem: `b` zmierzono między M i N, a nie między M i ramionami kontrolnymi K1.

K1 jest eksperymentem **ograniczającym i kalibrującym**:

- może wykryć efekty od około 12 pp (84% przy 12 pp, 98% przy 15 pp);
- może wykluczyć poziom 10 pp, gdy efekt jest bliski zera (62%);
- zmierzy niezgodność między M a ramionami P, X i S, której pilotaż nie mierzył;
- przy efektach 3–8 pp żaden z trzech kontrastów nie wykryje efektu w 29–86% przebiegów.

Próg 10 pp przekracza cały historyczny zysk M − N (8,1 pp). Wykluczenie 10 pp dla pojedynczego składnika mówi więc mało o tym, skąd pochodzi zysk historyczny; realnym produktem K1 przy efektach rzędu historycznego będą stany V4 i V5 oraz pomiar szumu.

Rozdzielenie składników przy efektach 3–9 pp wymaga instrumentu z około 1 000 i więcej niezależnych zadań (roboczo K1b), poza zakresem tej specyfikacji.

## Zmiany względem wersji 0.3

| # | Zmiana | Sekcja | Źródło |
|---|---|---|---|
| 1 | Historia rozmowy opisana zgodnie z harnessem: blok z zakończonej tury jest usuwany; T-zgodność sprawdza pełną treść żądania przy każdym wywołaniu | 2, 6.3 | W1 |
| 2 | L6a: hak audytu z listą dozwolonych plików i programów; podklasa BFCL bez obu plików odpowiedzi; plany M i pule wyodrębnione do plików K1 (NIGHT-2 czyta `exposure.json`, który zawiera dane liczone z odpowiedzi wzorcowych) | 2, 5 | W2 + ustalenia N10–N12 |
| 3 | L4a: rdzenie słów, liczebniki słowne, warianty domenowe, pełne pule, rozszerzony zbiór znaków | 5 | W3 |
| 4 | Odczyt: V5 z górną granicą i warunkiem 8,1 pp; złożone A i B bez twierdzeń ponad stany; zakazy sprawdzane po rdzeniach; stan NIEWAŻNY w kodzie | 8 | W4, W6 |
| 5 | Estymand skończonej populacji; diagnostyka zależności z `ρ̃` (korekta obciążenia), `ρ*` dla V4, liczby symulacji z odtworzeniem i z ich celem | 7.4 | W5 |
| 6 | NIEWAŻNY od 8 wykluczonych zadań; ponowienia i brak techniczny zdefiniowane; reguła braków bloku A | 7.2, 7.6 | W6 |
| 7 | Budżet: próg 30 000 zamiast 34 000; bramka przed blokiem A i przed każdym blokiem próbkowanym | 10 | W7 |
| 8 | Długość P: definicja treści bloku i budowy; `c` osobno dla domeny; tolerancja ±5% na sumie tokenów domeny (±5% na każdy blok jest nieosiągalne) | 2, 6.3 | W8 + ustalenie N13 |
| 9 | L9 przeliczone na pełnych pulach, dla ramienia S wersji 0.3 | 5 | W9 |
| 10 | Wielkość X − P nazwana „ślady obcej domeny zamiast prozy (format i obce narzędzia)” | 3 | Z2 kontroli |
| 11 | Analizy wrażliwości przemianowane na WR1–WR4 (kolizja nazw z poprawkami W1–W9) | 7.5 | porządkowe |

Zmiany w wersji 1.0 względem 0.4 (po warunkach właściciela i pilotażu):

| # | Zmiana | Sekcja | Źródło |
|---|---|---|---|
| 12 | Pochodzenie bodźców M jako kontrola L10; dozwolone użycie odpowiedzi wzorcowych zdefiniowane | 2, 5 | warunek D11 |
| 13 | Hak audytu: kopie, dowiązania, `multiprocessing`, `ctypes`, sieć, późna instalacja; jawne ograniczenia | 5 | warunek D11 |
| 14 | Nierównowaga długości na zadanie: kryterium B1, analiza WR5, reguła LEN w odczycie | 2, 7.5, 8, 11 | warunek D9 |
| 15 | Losowanie X i S z dopasowaniem długości | 2 | D12 (zatwierdzona 2026-11-13) |
| 16 | Charakterystyka reguł przy szumie zmierzonym w pilotażu; tabela otwierająca i sekcja 9.0 | 0, 9 | pilotaż K1-CAL-NM |
| 17 | Stan decyzji D1–D12 i procedura zamrożenia | 13, 14 | — |

### Errata v1.0.1 (decyzje właściciela C1–C4, 2026-11-13)

Errata usuwa niezgodności między słowami wersji 1.0 a regułami, z których pochodzą jej liczby i zamrożone bodźce. Nie zmienia hipotez, estymandów, definicji ramion jako wielkości, zadań, stanów, progu, poziomów ufności, liczby bloków, kontrastów, reguł odczytu ani parametrów próbkowania modelu.

| # | Decyzja | Brzmienie w 1.0 | Brzmienie w 1.0.1 | Skutek dla bodźców i testów | Sekcje |
|---|---|---|---|---|---|
| E1 (C2) | tolerancja D12: reguła logarytmiczna zamrożonego prototypu | „mieści się w ±20% bloku M tej tury, a w razie braku najbliższe” | przyjęcie, gdy \|ln r\| ≤ ln 1,2, czyli r ∈ [1/1,2; 1,2] = [0,8333; 1,2000] (od −16,67% do +20,00%); w razie braku losowanie o najmniejszym \|ln r\|; r = przewidywane tokeny losowania / przewidywane tokeny bloku M tej tury; definicje przewidywanych tokenów zapisane wprost | żaden bodziec się nie zmienia: zamrożone losowania wykonawcy są dokładnie losowaniami tej reguły (0/1 542 różnic w X i 0/1 542 w S, niezależne odtworzenie). Wariant liniowy ±20% zmieniłby 160 losowań X i 286 S, podniósłby nierównowagę do +3,9% (X) i +4,1% (S) i częstość wstrzymań reguły LEN do około 14–17% (X) i 19–20% (S); nie jest przyjęty | 2, 12, 13 |
| E2 (C1) | podstawa ρ: znaki całego bloku, bez separatora | „ρ = Σ tokenów bloków / Σ znaków bloków” (prototypy liczyły znaki bloku + 2) | to samo brzmienie z doprecyzowaniem: znaki bloku łącznie z linią nagłówka, bez separatora `\n\n`; tokeny to różnica `prompt_eval_count`, która obejmuje także separator | ρ domeny wyższe o 0,12–0,21% niż w prototypie; `c_d` zmienia się o mniej niż 0,1%; 21 z 3 084 losowań X i S innych niż w prototypie (X 2, S 19); wartości kontrolne przeliczone na regułach przyjętych (tabela niżej) | 2 |
| E3 (C3) | WR5, dalsze tury | „znaki treści × tokeny na znak ramienia i domeny wyznaczone z tury 0” | tokeny na znak ramienia i domeny = dokładne tokeny tury 0 / znaki treści bloku tury 0 | tylko analiza; wpływ na `x_i` ≤ 0,0004 w skali ln (próg B1 0,049) | 7.5 |
| E4 (C4) | blok A po drugim wyjątku albo po limicie twardym | „przy drugim wystąpieniu blok kończy się jako nieukończony” | blok A ma status NIEUKOŃCZONY, a program zatrzymuje się do decyzji właściciela; A nie jest powtarzany przy wznowieniu i nie wchodzi do checkera, zamrożenia ani analizy; odpowiedź drugorzędna (7.6) ma stan NIEWAŻNY | bez wpływu na bodźce; dotyczy sterowania przebiegiem | 7.2, 7.6 |

Wartości kontrolne po erracie (reguła E1 z podstawą E2; `kontrola_erraty.out`; te same wartości nierównowagi w `D:/aamr-k1-executor/tests/WYNIKI_ZGODNOSC_v1.0.out`):

| Wielkość | 1.0 (prototyp, ρ ze znakami + 2) | 1.0.1 (reguły przyjęte) |
|---|---|---|
| nierównowaga M − X, średnio (5–95% na zadanie) | +1,8% (−11% … +21%) | +1,83% (−11,2% … +21,1%) |
| nierównowaga M − S, średnio (5–95% na zadanie) | +2,2% (−6% … +11%) | +2,31% (−5,7% … +11,4%) |
| nierównowaga M − P, średnio (5–95% na zadanie) | −0,2% (−7% … +8%) | −0,1% (−6,9% … +8,0%) |
| B1 dla P, X, S | spełnione | spełnione |
| LEN wstrzymuje prawdziwe efekty +15 pp (symulacja, 600 prób; dwie niezależne implementacje) | 4% (X), 8% (S) | około 3–4% (X), 8% (S) |
| losowania z wyborem „najbliższe” (żadne z 200 nie spełnia reguły) | — | X 157 / 1 542, S 21 / 1 542 |

Tabela zmian względem wersji 0.2 (z wersji 0.3) obowiązuje z poprawionym wierszem 6: „Ramię S: losowe ślady z tej samej domeny, rozłączne z M dla całego zadania (wybór estymandu). Permutacja z wersji 0.2 jest wykonalna przy rozłączności w obrębie tury; przy rozłączności dla całego zadania nie istnieje w warstwie E1-VC” (źródło: własne; korekta po kontroli końcowej).

## 1. Granice (nie do zmiany przez wykonawcę)

- 0 wywołań płatnych; wyłącznie lokalna Ollama; `paid_calls = 0`.
- TradingBot (id 100–149, wszystkie odmiany) nietknięty; strażnik `guard_task` zostaje.
- Bez push i merge; commity tylko lokalne, na nowej gałęzi w nowym katalogu roboczym.
- Bez zmian w zamrożonym kodzie i wynikach pilota, S1, NIGHT-1, NIGHT-2; nowy kod importuje stary.
- Bez zmian w koordynatorze, jego bazie i harmonogramie poza własnym zadaniem programu, usuwanym po zakończeniu.
- Twardy limit lokalnych wywołań: 30 000 (sekcja 10).

## 2. Ramiona

Blok, jeśli jest, trafia przed prośbą tury jak w NIGHT (`block + "\n\n" + request`). **Po zakończeniu tury blok jest usuwany z historii; zostaje w niej sama prośba** (jak w NIGHT-2: `experience_xfer_v1.py:460`, funkcja `run_episode_x`). W każdej turze model widzi wyłącznie blok tej tury. K1 używa `run_episode_x` bez zmian.

**Wszystkie bloki zaczynają się tym samym nagłówkiem**, bajt w bajt, po którym następuje znak nowej linii:
`EXPERIENCE FROM EARLIER TASKS (it may or may not be relevant; use it only if it helps):`
**Treść bloku** = blok bez linii nagłówka i tego znaku nowej linii.

| Ramię | Treść pod nagłówkiem | Od poprzedniego szczebla różni się |
|---|---|---|
| **N** | brak bloku | — |
| **P** | neutralna proza, liczba tokenów jak w bloku M tej samej tury (średnio w domenie) | obecnością tekstu pod nagłówkiem pamięci |
| **X** | ślady sukcesu z **innej domeny**, tyle samo śladów co w M | formatem śladu i obcymi narzędziami |
| **S** | **losowe** ślady z tej samej domeny i zbioru, rozłączne z M tego zadania | wiedzą o domenie |
| **M** | prawidłowa pamięć: R+ bez zmian (jądro leksykalne 0.2.0, k = 2) | doborem śladów do zadania |

Wszystkie pięć ramion jest obowiązkowych.

**M.**
- Dla 88 zadań testowych plan z NIGHT-2 (R+): VC z `experience-pilot-v0/exposure.json`, pole `retrieval[·]["R+"]`; GFS i TRAVEL z `memory_{GFS,TRAVEL}.json`, pole `rplus_plan`. Dla 60 treningowych plan „bez własnego zadania” z `e1_retrieval_plan.json`. Pule: `success_pool` (A+: VC 31, GFS 26, TRAVEL 57 śladów).
- **Przed zamrożeniem** proces przygotowawczy wyodrębnia plany do `k1_plans_M.json` (wyłącznie identyfikatory śladów na `zadanie:tura`), pule do `k1_pool_{VC,GFS,TRAVEL}.json` i listy zadań do `k1_tasks.json`. Procesy budujące bodźce i epizody czytają tylko te pliki. Powód: `exposure.json` zawiera także pole `exposure`, liczone z odpowiedzi wzorcowych zadań testowych (`experience_pilot_v0.py:970–994`).
- **Pochodzenie (kontrola L10, przed zamrożeniem):** samo wyodrębnienie nie wystarcza. Plany są dopuszczone tylko wtedy, gdy osobny proces pod hakiem L6a, z dostępem wyłącznie do tekstów próśb, wyodrębnionych pul i list zadań, odtworzy je bajt w bajt tym samym kodem NIGHT (jądro 0.2.0, `build_index`, `retrieve`, `UNGATED`, k = 2), a pule odtworzą się z zapisanych epizodów treningowych bez pamięci (pochodzenie „A”, etykieta PASSED, zadanie źródłowe ze zbioru treningowego). Opis pochodzenia i wynik: `../v0.4/UZUPELNIENIE_D9_D11.md`, test `../v0.4/testy/t_n10_provenance.out` (520/520 kluczy zgodnych).
- **Dozwolone użycie odpowiedzi wzorcowych:** wyłącznie (a) etykieta sukcesu tury w epizodach **treningowych** (dobór śladów do puli A+, z założenia projektu pamięci) i nigdy dla zadania bieżącego; (b) wybór populacji: NIGHT-1 wykluczył z testu TRAVEL 2 zadania z pustą turą wzorcową (`multi_turn_base_167`, `_180`; `aamr_night1.py:472`), lista zadań jest zamrożona. Każde inne użycie odpowiedzi testowych lub danych z nich liczonych zatrzymuje K1 (L6a, L10).
- Bloki renderuje `plan_provider` z `aamr_night2.py` (prezentacja R+) bez zmian. Przy temperaturze 0 żądania do modelu są bajt w bajt zgodne z NIGHT-2 (sprawdzone: test W1).

**P.**
- Korpus neutralny: co najmniej 150 zdań oznajmujących po angielsku, wyłącznie o geologii i botanice, ASCII. Temat pogody wykluczony. Każde zdanie przechodzi L4a.
- **Długość treści** (bez linii nagłówka i znaku nowej linii) = `round(c_d × długość treści bloku M tej samej tury)` w znakach, gdzie `d` to domena zadania. Pusty blok M daje brak bloku P w tej turze.
- **Budowa:** zdania losowane w całości (generator z ziarnem `(zadanie, tura, instancja)`, kolejność z permutacji korpusu), łączone pojedynczą spacją, dopóki długość nie przekracza celu. Następne zdanie, które przekroczyłoby cel, jest dodawane w całości, jeśli tak jest bliżej celu; w przeciwnym razie przycinane na granicy słowa do długości najbliższej celowi i kończone kropką; jeśli bliżej celu jest nie dodawać niczego, blok kończy się na poprzednim zdaniu. Odchylenie od celu na blokach NIGHT-2: najwyżej 5 znaków (test W8).
- **Współczynnik `c_d`** (osobno dla VC, GFS, TRAVEL): `c_d = ρ_M,d / ρ_P,d`, gdzie `ρ = Σ tokenów bloków / Σ znaków bloków`, gdzie znaki bloku liczy się łącznie z linią nagłówka i bez separatora `\n\n` (errata E2, C1), a tokeny jak niżej (różnica `prompt_eval_count`, która obejmuje także separator). `ρ_M,d` z danych NIGHT-2: liczba tokenów bloku M w turze 0 = `prompt_eval_count` (M, t0, s0) − `prompt_eval_count` (N, t0, s0) tego samego zadania (147 bloków, bez nowych wywołań). `ρ_P,d` z etapu T: 10 bloków P na domenę (budowa z `c = 1`) w turze 0 zadań, wywołanie z opcjami bloku A i `num_predict` = 1, liczy się tylko `prompt_eval_count` (odjęty od wartości N z NIGHT-2).
- Losowanie: instancja 0 w bloku A, instancje 1–3 w blokach próbkowanych.
- Bez szkieletu śladu (`[1] Request:`, `Steps:`); za format odpowiada ramię X.
- Dopasowanie tokenów jest **średnie w domenie**, nie na blok: stosunek tokenów na znak bloków M różni się między blokami (VC 0,265–0,314, GFS 0,235–0,288, TRAVEL 0,258–0,327); przy jednym `c_d` w ±5% mieści się 70% bloków (test W8). Warunek właściciela do D9: nierównowaga długości jest mierzona i raportowana **na zadanie**, z kryterium B1 i analizą WR5 (sekcje 7.5, 8). Przewidywana nierównowaga P na zadanie z zamrożonych bodźców: średnio −0,1%, kwantyle 5–95% od −6,9% do +8,0% (podstawa E2; `kontrola_erraty.out`).

**X.**
- Odwzorowanie domen VC → GFS → TRAVEL → VC w obrębie zbioru.
- Dla każdej tury tyle śladów, ile ma blok M tej tury, losowanych bez zwracania z pełnej puli domeny źródłowej. **Dopasowanie długości (D12, w brzmieniu erraty E1):** do 200 losowań z ziarnem `(zadanie, tura, instancja, próba)`. Dla losowania r = przewidywane tokeny losowania / przewidywane tokeny bloku M tej tury, gdzie przewidywane tokeny losowania = znaki treści × ρ domeny śladów (`ρ_d` jak w `c_d`, E2), a przewidywane tokeny bloku M = znaki treści bloku M × ρ bloku M tury 0 tego zadania (ρ domeny, gdy zadanie nie ma pomiaru; pomiar ma 147 ze 148 zadań). Przyjmuje się pierwsze losowanie z \|ln r\| ≤ ln 1,2, czyli r ∈ [0,8333; 1,2000] (od −16,67% do +20,00%); gdy żadne z 200 nie spełnia warunku, losowanie o najmniejszym \|ln r\|. Reguła jest dokładnie funkcją `matched` zamrożonego prototypu `../v0.4/testy/t_d9_length.py`, z podstawą ρ z E2. Renderowanie przez `render_block`, jak M.
- Skutek uboczny: ślady X w 99,5% linii wywołują funkcje niedostępne w zadaniu docelowym (kontrola końcowa, R2).

**S.**
- Dla każdej tury tyle śladów, ile ma blok M tej tury, losowanych z pełnej puli tej samej warstwy (domena × zbiór) po odjęciu: (a) wszystkich śladów, które M pokazuje temu zadaniu w **którejkolwiek** turze, (b) śladów pochodzących z tego zadania. W obrębie zadania bez powtórzeń, dopóki wystarcza śladów. Dopasowanie długości jak w X (D12, errata E1), z ρ domeny zadania.
- Na pełnych pulach każde zadanie ma zapas co najmniej 7 śladów ponad potrzebę wszystkich tur bez powtórzeń (najmniej: E3-GFS), żadne nie wymaga powtórzeń (test W9).
- Trzy bloki próbkowane używają trzech niezależnych losowań.
- **Rozłączność z M dla całego zadania jest wyborem estymandu:** S nie zawiera żadnego śladu, który wyszukiwanie dobrało do tego zadania w którejkolwiek turze. Nie wynika z historii rozmowy, bo bloki z niej znikają.
- Odczyt: M − S mierzy wartość **doboru** śladów (wyszukiwania), nie wartość „stałych przykładów”.
- Bez dopasowania (losowanie samą liczbą śladów, wersja 0.4 przed D12; liczby z prototypu, ρ ze znakami + 2, wariant nieprzyjęty) M jest średnio dłuższe od X o 5,3% i od S o 7,0% tokenów, a na zadanie rozrzut sięga od −54% do +144% (X); kryterium B1 nie byłoby spełnione, a reguła LEN wstrzymałaby przypisanie treści w 52% (X) i 82% (S) prawdziwych wykryć. Z dopasowaniem według E1 i E2: X +1,83% (5–95% na zadanie od −11,2% do +21,1%), S +2,31% (od −5,7% do +11,4%); wstrzymanie prawdziwych wykryć około 3–4% (X) i 8% (S); wybór „najbliższe” w 157 (X) i 21 (S) z 1 542 losowań (`kontrola_erraty.out`).

## 3. Estymandy i pytania

Oznaczenie: Δ(A − B) = różnica średniego odsetka rozwiązanych zadań między ramionami A i B w reżimie próbkowanym, **średnia po 148 zadaniach K1, przy zamrożonych bodźcach** (plany M, pule, korpus P, losowania S i X, `c_d`); losowe jest tylko próbkowanie modelu (sekcja 7.4). Próg praktyczny: 10 pp.

Drabina (każdy szczebel to osobna wielkość; suma czterech daje M − N):

| Wielkość | Różnica | Co znaczy | Rola |
|---|---|---|---|
| kontekst | P − N | sam tekst pod nagłówkiem pamięci | opisowa |
| ślady obcej domeny zamiast prozy | X − P | format śladu **i** obce narzędzia (ślady wywołują funkcje niedostępne w zadaniu) | opisowa |
| domena | S − X | ślady z właściwej domeny zamiast obcej | opisowa |
| dobór | **M − S** | ślady dobrane zamiast losowych z domeny | **kontrast główny C3** |
| treść przy stałym formacie | **M − X** | domena i dobór łącznie | **kontrast główny C2** |
| pamięć ponad neutralny tekst | **M − P** | format, domena i dobór łącznie | **kontrast główny C1** |
| całość | M − N | efekt bloku pamięci | opisowa |

Dla każdego z trzech kontrastów głównych dwa pytania z wykluczającymi się odpowiedziami: czy Δ > 0 (albo Δ ≤ 0) oraz czy Δ ≥ 10 pp (albo Δ < 10 pp).

Zakres wniosków:
- Wielkości są zdefiniowane względem konkretnych ramion kontrolnych. Każde ramię kontrolne ma własne skutki uboczne: proza pod nagłówkiem pamięci bywa myląca, ślady z obcej domeny podają nieistniejące narzędzia, ślady losowe podają cudze wartości. Nie istnieje kontrola obojętna, dlatego raport zawsze podaje obok M − N i P − N.
- Wnioski dotyczą tych 148 zadań, tej puli śladów (31 + 26 + 57 śladów sukcesu i pule „bez własnego zadania”), trzech domen, modelu `qwen2.5:14b-instruct` i reżimu próbkowania. Nie dotyczą pamięci w ogóle ani innej puli.

## 4. Reżimy i powtórzenia

| Blok | Reżim | Ramiona | Rola |
|---|---|---|---|
| **A** | temperatura 0, seed 7, jak NIGHT-2 | N, M, P | kontrola dryfu; odpowiedź drugorzędna przy temperaturze 0 (sekcja 7.6) |
| **S1, S2, S3** | temperatura 0,7, top_p 0,8, top_k 20; seed 7001, 7002, 7003 | N, P, X, S, M | **analiza główna** |

- Pozostałe opcje modelu bez zmian: `num_ctx` 8192, `num_predict` 512, najwyżej 8 kroków na turę.
- W bloku każde zadanie przechodzi przez wszystkie ramiona; kolejność ramion losowana dla zadania i bloku.
- Analiza główna mierzy **oczekiwany** efekt przy próbkowaniu. To inna wielkość niż historyczne różnice przy temperaturze 0; na pytanie dosłowne odpowiada blok A, z mniejszą mocą.
- Wspólne ziarno wszystkich ramion w bloku nie narusza analizy po zadaniach, ale może zaniżać mierzoną niezgodność między ramionami; raport to odnotowuje.

## 5. Kontrola przecieków

Każda kontrola zatrzymuje program; brak danych do sprawdzenia jest błędem, nie zaliczeniem.

| # | Kontrola | Warunek zatrzymania | Test regresji (prototyp w `../v0.4/testy/`) |
|---|---|---|---|
| L1 | Pole `source_task` każdego śladu w M, S, X | ślad z zadania bieżącego; dla zadań testowych ślad spoza zbioru treningowego; **zero sprawdzonych źródeł** | podłożony własny ślad musi zatrzymać; na planach NIGHT-2: 0 z 148 |
| L2 | Kontrola pozytywna L1 | brak wykrycia podłożonego śladu | — |
| L3 | Ramię S | ślad wspólny z M tego zadania w którejkolwiek turze; ślad z własnego zadania; inna liczba śladów niż w M | prototyp 0.3: 0 naruszeń; zapas na pełnych pulach ≥ 7 (`t_w9_l9_s_reserve.out`) |
| L4a | Korpus neutralny, część twarda | (1) cyfra; (2) liczebnik słowny (zero–ninety, hundred, thousand, million, billion, dozen, half, twice, thrice, z liczbą mnogą), także w złożeniach z łącznikiem; (3) you, your, yours, yourself, yourselves; (4) znak `( ) [ ] { } " `` ` `` _ = / \ < > \|`, apostrof prosty nie między dwiema literami, dowolny znak spoza ASCII; (5) **słowo domenowe porównywane po rdzeniu**: zdanie i lista sprowadzane do rdzeni tą samą funkcją (końcówki -ies→y, -ing, -ed, -es, -s, gdy zostają co najmniej 3 litery; potem podwojona spółgłoska końcowa skracana, końcowe -e odcinane). Lista = składniki identyfikatorów funkcji i parametrów oraz literały `enum` z dokumentacji klas zadań + składniki literałów argumentów i kluczy wyników z **pełnych** pul trzech domen + zamrożona lista wariantów domenowych (synonimy i pisownie spoza identyfikatorów, np. petrol, tyre, aircraft, luggage) − zamrożona lista słów funkcyjnych (zamknięta klasa: przyimki, spójniki, zaimki, określniki). Obie listy i lista domenowa ze skrótem w L8 | `k1_l4.py`, `t_w3_l4.out`: zatrzymane 25/25 (m.in. „tanks”, „forty”, „fueled”, „petrol”, „tyres”, „twenty-five”, nawias, `=`, `/`, „café”, cudzysłów typograficzny); przechodzi 19/19 legalnych (m.in. „Earth's”) |
| L4b | Bliskość leksykalna P do prośby | wskaźnik Jaccarda słów treściowych bloku P i prośby tury powyżej 0,05 | próbka: maksimum 0,022; bloki M: mediana 0,082 |
| L5 | TradingBot | zadanie 100–149 w prompcie, executorze albo checkerze | jak w NIGHT |
| L6a | Dostęp do odpowiedzi wzorcowych | **Hak audytu** (`sys.addaudithook`) jako pierwsza instrukcja każdego procesu, który tworzy bodźce (wyodrębnienie planów i pul, korpus P, losowania S i X, `c_d`) albo wykonuje epizody, przed importem harnessu. Hak dopuszcza: odczyt plików z zamrożonej listy (`BFCL_v4_multi_turn_base.json`, 7 plików `multi_turn_func_doc/*.json`, konfiguracja K1, `k1_plans_M.json`, `k1_pool_*.json`, korpus, losowania, `c_d`), odczyt plików kodu (`.py .pyc .pyd .dll`) z instalacji Pythona, katalogu skryptów harnessu i pakietu BFCL, zapis i odczyt w katalogu przebiegu tego procesu, uruchomienie wyłącznie programu Ollama użytkownika (bramka NIGHT restartuje go przy awarii, `aamr_night1.py:285`). Każde inne otwarcie pliku, zapis poza katalogiem przebiegu, kopia, dowiązanie twarde lub symboliczne albo przeniesienie pliku do katalogu przebiegu ze źródła spoza listy, uruchomienie innego programu (`subprocess`, `os.system`, `os.spawn*`, `os.startfile`, `multiprocessing` przez `_winapi.CreateProcess`), połączenie sieciowe poza lokalnym serwerem Ollama, załadowanie przez `ctypes` biblioteki innej niż `kernel32` albo pobranie z niej funkcji plików, procesów lub ładowania bibliotek kończy proces kodem 97 przez `os._exit` (błędu nie da się przechwycić). Hak odmawia instalacji, jeśli harness jest już zaimportowany. Nadzorca może uruchomić wyłącznie pełne, zamrożone polecenie procesu roboczego, który instaluje własny hak (hak nie przechodzi na proces potomny). Proces epizodu używa podklasy `BfclK1` klasy `n1.BfclN`: ten sam konstruktor bez wczytywania `possible_answer/BFCL_v4_multi_turn_base.json` (`experience_pilot_v0.py:122`) i bez `probe_gt`/`probe_tasks` z `BfclX` (`experience_xfer_v1.py:263–264`); dostęp do `gt` i `probe_gt` zgłasza błąd. Checker działa w osobnym procesie, po zamknięciu zapisu epizodów, z własnym katalogiem wyników, którego proces epizodu nie czyta | `k1_audit_hook.py`, `t_w2_audit_hook.out`, 13/13: (1) `n1.BfclN` pod hakiem → 97; (2) `BfclK1` + wyodrębnione bodźce: wszystkie 296 epizodów N i M odtworzone pod hakiem bez zatrzymania, bajt w bajt jak NIGHT-2; (3) kopia pliku odpowiedzi pod inną ścieżką → 97; (4) podproces Pythona i `os.system` → 97, restart Ollamy (zastępnik, ścieżka ze spacją) przechodzi; ponadto przechwycenie wyjątku, `os.open`, `pathlib`, zapis poza katalogiem, ścieżka NIGHT-2 przez `exposure.json` → 97; checker z własną polityką czyta odpowiedzi. Ograniczenia haka (D11): 32/32, m.in. `multiprocessing`, `shutil.copy2`, `os.link`, `os.symlink`, `os.rename`, `os.spawnv`, `os.startfile`, `ctypes` (`CDLL`, `CreateFileW`, `LoadLibraryW`), TCP i UDP poza dozwolonym adresem → 97; dozwolone połączenie lokalne przechodzi; późna instalacja odrzucona; dozwolony proces potomny bez własnego haka czyta odpowiedzi (ograniczenie), proces roboczy K1 z hakiem → 97 |
| L6b | Kontrola negatywna L6 | zatrzymanie na legalnym bloku, którego wywołanie pokrywa się z odpowiedzią wzorcową | przebieg (2) zawiera 681 takich linii w 81 epizodach i nie został zatrzymany |
| L7 | Ślepota przebiegu | dziennik postępu wypisuje `solved` albo liczniki na ramię; analiza uruchomiona przed etapem `final`; bramki budżetu korzystają wyłącznie z liczby wywołań | — |
| L8 | Zamrożenie bodźców | brak skrótu sha256: korpusu, `k1_plans_M.json`, `k1_pool_*.json`, `k1_tasks.json`, losowań S i X, `c_d`, listy domenowej L4a, listy słów funkcyjnych, listy wariantów domenowych, listy plików dozwolonych L6a, listy par zadań o wspólnym śladzie, plików uruchamianych przed hakiem (`.pth`, `sitecustomize`, jeśli są) | — |
| L10 | Pochodzenie bodźców M | (G1) wiersz puli o pochodzeniu innym niż „A”, z etykietą inną niż PASSED, z zadania spoza zbioru treningowego, albo pula różna od wierszy odtworzonych z zapisanych epizodów treningowych; (G2) plany różne od odtworzonych pod hakiem z danych bez odpowiedzi; naruszenie haka w procesie odtwarzającym; puste porównanie | `t_n10_provenance.out`: 114 wierszy i 520/520 kluczy zgodnych, odtworzenie deterministyczne; zatrzymują: wpis planu podmieniony z użyciem odpowiedzi, wiersz z puli G pilota (wykonane odpowiedzi), wiersz z zadania testowego, puste porównanie, producent czytający `exposure.json`, `memory_GFS.json` albo plik odpowiedzi |

Zakres L6a: chroni przed przypadkowym dostępem kodu K1 lub importowanej funkcji harnessu do odpowiedzi w procesie, który buduje prompty. Nie jest piaskownicą wobec celowo wrogiego kodu. Ograniczenia znane i nieusuwalne hakiem: kod uruchamiany przy starcie interpretera przed hakiem (stąd skróty w L8); dozwolony proces potomny nie dziedziczy haka (stąd wyłącznie zamrożone polecenie procesu roboczego z własnym hakiem); wywołanie funkcji przez `ctypes` nie generuje zdarzenia audytu w CPython 3.12, kontrolowane jest tylko pobranie funkcji po nazwie; kopia odpowiedzi zapisana jako plik kodu. Pełna lista: `../v0.4/UZUPELNIENIE_D9_D11.md`.

Dlaczego L4 i L6 zmieniono (względem 0.2):
- L4 w wersji 0.2 zakazywała wszystkich słów z próśb (2 223 słowa, w tym „the”, „and”). Lista L4a 0.4 ma 451 słów (408 rdzeni) i jest wykonalna; ceną jest kilkanaście pospolitych słów, których autor korpusu musi unikać (base, care, current, front, history, level, mode, pressure, record, root, slope, state, temperature, time, type; także np. „years”, „pine”).
- L6 w wersji 0.2 wymagała, by prompt nie zawierał wywołań wzorcowych. W legalnych blokach M jest około 680 takich linii na 2 807 (24%), w 81–82 ze 148 zadań. Kontrola po napisach zatrzymałaby program na poprawnej pamięci. L6a sprawdza dostęp do danych, czyli to, co faktycznie byłoby przeciekiem.

**Miara opisowa L9 (po przebiegu, bez wpływu na stany):** odsetek pokazanych linii wywołań (pierwsze 8 kroków śladu, po usunięciu białych znaków) identycznych z wywołaniem wzorcowym bieżącego zadania; średnia po zadaniach, obok średnia po blokach tur. Na planach NIGHT-2 i pełnych pulach: M 18,5% (po blokach tur 17,0%), bloki M innych zadań warstwy 14,0% (11,7%), ramię S tej wersji 11,1% (9,6%; 20 losowań), X 0,0% (4 linie z 56 424). Liczy ją proces analizy po zamrożeniu surowych danych.

Jawne ograniczenie: wyniki N i M przy temperaturze 0 są znane z NIGHT-2. Nieznane są P, X, S i cały reżim próbkowany.

## 6. Prerejestracja i zasady przebiegu

1. Wersja 1.0 została zamrożona skryptem `../v1.0-rc/zamroz.py` (`../v1.0/FREEZE.json`). Errata 1.0.1 jest zamrażana skryptem `zamroz_v101.py`: powstaje `../v1.0.1/SPEC_K1_PLACEBO_v1.0.1.md` ze skrótem sha256 w `../v1.0.1/FREEZE.json`; obowiązuje wersja 1.0.1. Katalog wykonawczy K1 dostaje kopię bajt w bajt; jej skrót jest sprawdzany przy starcie (L8).
2. Kod, testy, konfiguracja, korpus, plany, pule, losowania, `c_d` i **skrypt analizy z regułami odczytu** są zamrożone przed pierwszym wywołaniem eksperymentalnym. Wywołania etapu T (sekcja 10) nie są eksperymentalne; ich wyniki `solved` nie są zapisywane.
3. Testy wymagane przed startem (każdy test z pustym zakresem jest niezaliczony):

| Test | Co sprawdza | Prototyp i wynik (`../v0.4/testy/`) |
|---|---|---|
| T-stan | funkcja stanu na siatce i granicach: [3, 8] → V3; [−2, 8] → V5; [2, 14] → V2; [−3, 12] → V4; [11, 20] → V1; [−9, −1] → V6; [0, 10] → V4; [0, 9,99] → V5; [10, 15] → V1; ponadto rozłączność stanów na siatce co 0,5 pp | `k1_v04_reading.py` |
| T-odczyt | każde zdanie kontrastu twierdzi tylko to, co wynika z jego przedziału (siatka co 0,5 pp na [−20; 25], 3 kontrasty); zdania złożone na 1 000 kombinacjach; kontrprzykłady N3 (a)–(c) z dokładną treścią; zakazane zwroty po rdzeniach; NIEWAŻNY | `k1_v04_reading.out`: 12 558 zdań, 1 000 kombinacji, zgodne |
| T-nagłówek | pierwsza linia każdego bloku P, X, S, M równa `MEMORY_HEADER` bajt w bajt | `t_w8_p_length.out` (P: 1 491/1 491) |
| T-długość | dla P: (a) długość treści bloku w znakach w granicach ±12 znaków od celu, każdy blok; (b) dla każdej domeny suma tokenów 10 nowych bloków P (etap T) w granicach ±5% sumy tokenów odpowiadających bloków M; przy niepowodzeniu jedno ponowne wyznaczenie `c_d` na 20 blokach, potem zatrzymanie | (a) `t_w8_p_length.out`: maks. 5 znaków; (b) wymaga modelu, etap T |
| T-L1…L8 | kontrola pozytywna i negatywna każdej kontroli przecieków | L4a: `t_w3_l4.out`; L6a/L6b: `t_w2_audit_hook.out` |
| T-S | 0 naruszeń rozłączności dla trzech losowań; liczba śladów równa M | zapas: `t_w9_l9_s_reserve.out` |
| T-analiza-a | na danych syntetycznych odtwarza odsetki z `k1_power_sim_v3.out` w granicach błędu Monte Carlo | — |
| T-analiza-b | na surowych danych NIGHT-2 odtwarza 22 zyski i 12 strat (E\* wobec N, 88 zadań testowych), 11 zysków i 9 strat (R+ wobec N, 60 treningowych) oraz `ρ̂` = −0,059, średnią permutacyjną −0,041 ± 0,003 i `ρ̃` = −0,018 | `t_w5_dependence.out` |
| T-komórki | reguły 7.2 i 7.6 na danych syntetycznych: blok nieukończony, < 2 bloki, 7 i 8 wykluczeń, parowanie w bloku, limit kroków jako 0, zatrzymanie przez L, pusty zakres, blok A | `t_w6_cells.out`: 14 przypadków |
| T-budżet | reguła sekcji 10 nigdy nie planuje ani nie wydaje ponad 30 000 | `t_w7_budget.out` |
| T-pochodzenie | kontrola L10 (G1, G2) na prawdziwych plikach K1 i jej kontrole negatywne | `t_n10_provenance.out` |
| T-nierównowaga | na zamrożonych bodźcach: B1 dla P, X, S; WR5 i LEN na danych skonstruowanych; reguła LEN w odczycie | `t_d9_length.out`, `k1_v04_reading.out` |
| T-zgodność | przebieg odtworzeniowy bloku A dla N i M: zamiast modelu klient podaje zapisane odpowiedzi NIGHT-2 (`responses.jsonl`); pełne żądanie (lista wiadomości, schemat, opcje, seed) przy **każdym** wywołaniu każdej tury ma sha256 równe zapisanemu w NIGHT-2 (wyjątek: nazwa instancji executora w wyniku błędu, sprawdzana po normalizacji na `attempts.jsonl`). Test musi zawieść, gdy blok poprzedniej tury zostaje w historii; mutant to sprawdza | `t_w1_history_replay.out`: 296 epizodów, 2 800 wywołań, 2 796 identycznych, 4 różne tylko nazwą instancji; mutant „blok zostaje” różni się w 853/853 wywołaniach rozróżniających i w 0 pozostałych |

4. Poprawki techniczne tylko przed pierwszym wywołaniem bloku, którego dotyczą, z wpisem w protokole. Ramiona, zadania, stany, próg, poziom ufności, reguły odczytu i parametry próbkowania bez zmian.
5. **Reguła zatrzymania:** stała wielkość. Bez odczytów pośrednich, bez dokładania bloków, bez wcześniejszego kończenia z powodu wyników. Bramki budżetu (sekcja 10) zależą wyłącznie od liczby wywołań.
6. Niejasność: wariant prostszy i bliższy NIGHT-2, zapisany przed blokiem, którego dotyczy.
7. Raport generuje skrypt z zamrożonych surowych danych; zdania odczytu wypisuje kod. Interpretacja i analizy dodane po fakcie w osobnych plikach, jako eksploracyjne.
8. Stanu nie zmienia żaden model ani recenzja.

## 7. Analiza

### 7.1 Miara

- `Y(i,a,r)` = 1, gdy zadanie `i` rozwiązane w ramieniu `a` i bloku próbkowanym `r`; epizod zakończony limitem kroków, przepełnieniem kontekstu albo nieprawidłowym wyjściem liczy się jako 0.
- Jednostką jest zadanie. Powtórzenia i tury nie są obserwacjami.

### 7.2 Brakujące komórki i stan NIEWAŻNY

- **Ponowienia (jak NIGHT-2):** wywołanie modelu do 4 prób (przerwy 15, 45, 90 s; HTTP 400 jest błędem protokołu i zatrzymuje program); po nieudanych próbach proces roboczy kończy się, a nadzorca uruchamia go ponownie po 120 s, najwyżej 8 razy na przebieg; wznowiony epizod odtwarza zapisane odpowiedzi. Inny wyjątek w bloku: przy drugim wystąpieniu blok kończy się jako nieukończony. **Blok A (errata E4, C4):** po drugim wyjątku albo po osiągnięciu limitu twardego w bloku A blok A ma status NIEUKOŃCZONY, a program zatrzymuje się do decyzji właściciela; przy wznowieniu A nie jest powtarzany i nie wchodzi do checkera, zamrożenia ani analizy.
- **Brak techniczny epizodu:** wyjątek checkera (osobny proces, L6a) dla jednego epizodu; epizod ma status `technical_error`. Przekroczenie limitu kroków, kontekstu i nieprawidłowe wyjście nie są błędem technicznym (7.1).
- Blok jest **ukończony**, gdy program podjął wszystkie epizody wszystkich pięciu ramion dla wszystkich zadań. Bloki nieukończone nie wchodzą do analizy.
- `y(i,a)` = średnia `Y(i,a,r)` po tych ukończonych blokach, w których zadanie `i` ma wynik we **wszystkich pięciu** ramionach. Pary pozostają więc dobrane w obrębie bloku.
- Zadanie bez żadnego takiego bloku jest wykluczane i zliczane.
- Stan **NIEWAŻNY** dla wszystkich kontrastów, gdy: mniej niż 2 ukończone bloki próbkowane; wykluczono **co najmniej 8** zadań; program zatrzymała kontrola L1–L8. Odczyt składa się wtedy z jednego zdania „NIEWAŻNY: {przyczyna}; żadnych wniosków o kontrastach.” i wiersza opisowego (sekcja 8).

### 7.3 Kontrasty i przedziały

- Dla kontrastu M − C (C ∈ {P, X, S}): `d(i) = y(i,M) − y(i,C)`; estymata = średnia `d(i)` po zadaniach.
- **Przedział decyzyjny:** dwustronny przedział t dla średniej różnic po zadaniach na poziomie **98,33%** (1 − 0,05/3).
- Trzy przedziały pokrywają prawdziwe wartości jednocześnie z prawdopodobieństwem co najmniej 95% przy dowolnej zależności między kontrastami (wszystkie dzielą ramię M), jeśli każdy ma nominalne pokrycie. Gdy wszystkie pokrywają, żadne zdanie odczytu nie jest fałszywe. Symulacja (model z sekcji 9, zadania niezależne): co najmniej jedno fałszywe zdanie w 1,7–4,8% przebiegów; powtórka z ziarnem 4242: 1,6–4,7%.

### 7.4 Estymand i zależność przez wspólne ślady

Stan faktyczny na planach NIGHT-2: 66–77% par zadań w warstwie ma wspólny ślad w bloku M; łącznie 1 260 par na 148 zadań (2L/n = 17,0); każda z 6 warstw jest jedną spójną składową.

1. **Estymand główny jest skończoną populacją:** średnia po tych 148 zadaniach różnicy oczekiwanych odsetków, przy zamrożonych bodźcach; losowe jest tylko próbkowanie modelu. Przy ustalonych bodźcach wynik zadania zależy tylko od jego własnych epizodów, więc `d(i)` są niezależne między zadaniami, a przedział t po zadaniach jest dla tego estymandu ważny (ostrożny: wariancja `d(i)` zawiera też zróżnicowanie efektów między zadaniami) **niezależnie od wartości `ρ̂`**. Dla 60 zadań treningowych, które są źródłami puli, ten opis jest spójny; opis „zadania losowe przy ustalonej puli” nie byłby.
2. **Względem estymandu bezwarunkowego** (średnia po możliwych pulach śladów) zależności przez wspólne ślady nie da się skorygować statystycznie: estymator odporny na powiązane pary sprowadza się do 6 grup. Ilustracja na rzeczywistym grafie, w modelu autora (`../v0.3/review/h5_author_model_conditional.py`, odtworzone w `../v0.4/testy/repro/`, ziarna 77 i 4242): odsetek fałszywych zdań dla jednego kontrastu (nominalnie 1,67%) **względem estymandu bezwarunkowego** wynosi 2,1–2,2% przy odchyleniu przesunięcia na zadanie 0,05; 3,2–3,3% przy 0,10; 5,3–5,7% przy 0,15; 12,7–12,9% przy 0,30. Względem estymandu głównego (ta pula): 0,0–0,1%. To ilustracja w jednym modelu, nie dowód; niezależny model daje to samo jakościowo (bezwarunkowy 0,5–5,1%, warunkowy ≤ 0,4%; `../v0.4/testy/repro/h4_*.out`, część B).
3. **Diagnostyka przenoszalności, zapisana z góry** (dotyczy przenoszalności wniosku na inną pulę, nie ważności stanu głównego). Dla każdego kontrastu raport podaje:
   - `ρ̂`: korelacja stratum-standaryzowanych `d(i)` po parach zadań o wspólnym śladzie M;
   - średnią `ρ̂` w rozkładzie permutacyjnym w warstwach (2 000 permutacji, ziarno zamrożone) i **`ρ̃ = ρ̂ − ta średnia`** (pod niezależnością `ρ̂` ma średnią około −0,04, nie 0; `ρ̃` ma średnią −0,0007 ± 0,0006, test W5);
   - jednostronne p testu permutacyjnego;
   - **punkt przełamania** `ρ*`: najmniejsze ρ ∈ [0, 1], przy którym przedział poszerzony o czynnik `√(1 + ρ·2L/n)` wokół estymaty zmienia stan; gdy żadne ρ ∈ [0, 1] nie zmienia stanu (zawsze w V4), raport podaje „ρ* = brak; stan odporny na zależność”;
   - jeśli `ρ̃ > 0` i p < 0,05: zdanie z prefiksem „PRZENOSZALNOŚĆ (nie zmienia stanu głównego):” o wykrytej zależności przez wspólne ślady oraz stan policzony z przedziałem poszerzonym o `ρ̃`, wydrukowany obok stanu głównego. Stan główny pozostaje bez zmian.
4. Moc tej diagnostyki jest mała: przy efekcie śladów o odchyleniu 0,3 wykrywa zależność w 8% przebiegów, przy 0,6 w 32% (test W5c). Brak sygnału nie jest dowodem niezależności.

### 7.5 Analizy wrażliwości (opisowe)

- WR1: bootstrap po zadaniach z warstwami (10 000 losowań, ziarno stałe).
- WR2: przedział po 68 grupach pierwszego śladu (wyłącznie dla porównania z wersją 0.2; nie chroni przed zależnością opisaną w 7.4).
- WR3: test losowania znaków różnic w warstwach.
- WR4: wszystkie trzy kontrasty tylko na 88 zadaniach testowych. Powód: R+ wybrano jako E\* na 60 zadaniach treningowych, więc na nich możliwe jest zawyżenie przez selekcję. Moc niska (wykrycie przy 10 pp około 28–33%); służy tylko do sprawdzenia znaku.
- **WR5 (długość, warunek D9; kod `../v0.4/testy/k1_length.py`):** dla zadania `i` i ramienia C ∈ {P, X, S}: `T_i(a)` = średnia po blokach próbkowanych sumy tokenów bloków wszystkich tur zadania (bodźce są zamrożone, więc miara nie zależy od przebiegu epizodu); tokeny tury 0 dokładnie z przebiegu (`prompt_eval_count` ramienia minus N w turze 0 tego samego bloku), dalsze tury: znaki treści × tokeny na znak ramienia i domeny wyznaczone z tury 0, czyli dokładne tokeny tury 0 / znaki treści bloku tury 0 (errata E3, C3). Nierównowaga `x_i(C) = ln(T_i(M)/T_i(C))`.
  - **Kryterium dopuszczalnej nierównowagi B1:** |średnia `x_i(C)`| ≤ ln(1,05). B2: odsetek zadań z |`x_i`| > ln(1,25), raportowany.
  - **Analiza:** regresja `d_i = α + β·x_i` (MNK, błędy HC3, przedziały t 98,33%, n − 2 st. swobody); α = kontrast przy równej długości; podzbiór zadań z |`x_i`| ≤ ln(1,10), estymata i przedział 98,33% (opisowo).
  - **Reguła LEN** („długość może wyjaśniać wynik”): B1 niespełnione; albo stan przedziału α różny od stanu przedziału głównego; albo przedział β wyklucza 0 i |β · średnia x| ≥ połowa |estymaty|. Skutek w sekcji 8.
  - Charakterystyka (symulacja, `../v0.4/testy/t_d9_length.out`): przy efekcie treści +15 pp i braku wpływu długości reguła wstrzymuje przypisanie w 1% (P), około 3–4% (X z D12) i 8% (S z D12) (errata: `kontrola_erraty.out`); przy wyniku wytworzonym wyłącznie przez długość (średnia nierównowaga 6–10%) w 100% wykrytych przypadków.

Rozbieżność z analizą główną raport odnotowuje jako zastrzeżenie; stanu nie zmienia.

### 7.6 Odpowiedź drugorzędna przy temperaturze 0

Z bloku A: M − P na zadaniach, które mają wynik w M i P (wynik N nie jest potrzebny); przedział t 95%, stan według sekcji 8. Przy wykluczeniu co najmniej 8 zadań albo gdy blok A jest NIEUKOŃCZONY (7.2, errata E4) odpowiedź drugorzędna ma stan NIEWAŻNY. Poza rodziną, bez wpływu na stany główne, oznaczona jako odpowiedź na pytanie dosłowne o reżim NIGHT. Moc niska (jeden przebieg na ramię; dla orientacji wiersz „1 blok” w sekcji 9).

### 7.7 Miary opisowe i pomiar szumu

Przedziały 95% bez korekty, bez stanów:

- szczeble drabiny P − N, X − P, S − X oraz całość M − N; każda w 6 warstwach;
- zyski i straty wobec N, straty przez kopię (metoda `n1_04`), zdarzenia błędu, nieprawidłowe wywołania, **wywołania nieistniejących funkcji** (skutek uboczny X), tokeny promptu na wywołanie w każdym ramieniu, miara L9.

Pomiar szumu:

- `w(a)`: odsetek zadań z różnym wynikiem w dwóch blokach tego samego ramienia (średnia z trzech par);
- `b(a,a′)`: odsetek zadań niezgodnych między ramionami w jednym bloku;
- rozkład wariancji: `σ²_powt` = średnia po zadaniach wariancji `Y(i,M,r) − Y(i,C,r)` między blokami; `σ²_zad` = wariancja `d(i)` minus `σ²_powt / R`;
- blok A: niezgodność P z N i M z N przy temperaturze 0 obok wartości NIGHT-2 (34 z 88; 20 z 60);
- tabela: ile zadań i powtórzeń potrzeba, by połowa przedziału wynosiła 2,5 i 5 pp przy zmierzonej wariancji.

Kontrola dryfu (blok A): zgodność N i M z NIGHT-2 w co najmniej 84 z 88 zadań testowych i 57 z 60 treningowych. Niespełnienie: odnotować; stany z bloków próbkowanych pozostają ważne.

## 8. Stany i odczyt (zamrożone)

Z przedziału decyzyjnego [L, U] w punktach procentowych, dla każdego kontrastu dokładnie jeden stan:

| Stan | Warunek | Czy dodatni? | Czy co najmniej 10 pp? |
|---|---|---|---|
| V1 | L ≥ 10 | tak | tak |
| V2 | 0 < L < 10 ≤ U | tak | nierozstrzygnięte |
| V3 | 0 < L i U < 10 | tak | nie |
| V4 | L ≤ 0 i U ≥ 10 | nierozstrzygnięte | nierozstrzygnięte |
| V5 | L ≤ 0 ≤ U < 10 | nierozstrzygnięte | nie |
| V6 | U < 0 | nie (ujemny) | nie |

**Odczyt** generuje kod (`../v0.4/testy/k1_v04_reading.py`, funkcja `read(intervals, est, invalid)`), nie człowiek ani model. Kod sam liczy stan z przedziału, więc stan i zdanie nie mogą się rozejść.

- Każdy kontrast dostaje jedno zdanie z szablonu swojego stanu, z przedziałem. Zdanie dla V5: „{kontrast}: efektu nie wykryto; przedział [L; U] pp dopuszcza efekty najwyżej do U pp ({co mierzy}).” oraz:
  - przy U ≥ 8,108 (12/148): „Wynik nie wyklucza, że cały historyczny zysk M − N (8,1 pp przy temperaturze 0) pochodzi z tego składnika.”;
  - przy U < 8,108: „Wynik wyklucza, że ten składnik w reżimie próbkowanym daje tyle, ile cały historyczny zysk M − N przy temperaturze 0 (8,1 pp).”
- Etykiety „co mierzy”: M − P „format, domena i dobór łącznie”; M − X „domena i dobór przy stałym formacie śladu”; M − S „dobór śladów do zadania”.
- Zdania złożone, każde jako funkcja stanów:
  - A, gdy M − X albo M − S jest w V1–V3: „przy tym samym nagłówku i formacie wynik zależy od treści śladów: prawidłowa pamięć wypada lepiej niż {X | S | X i S}. Nie wynika z tego, że pamięć pomaga względem P ani N.” Gdy wykryto M − X, dodatkowo: „Przewaga nad X może wynikać ze szkody wyrządzanej przez ślady obcej domeny (patrz opisowe X − P).”;
  - B, gdy M − P jest w V1–V3: „prawidłowa pamięć wypada lepiej niż neutralny tekst tej samej długości pod tym samym nagłówkiem; różnicy M − P nie da się sprowadzić do samej obecności dodatkowego tekstu. O przewadze nad brakiem bloku mówi tylko opisowe M − N.”;
  - C, gdy wszystkie są w V4 lub V5: „żaden kontrast nie wykrył efektu. To nie jest dowód braku efektu treści.”;
  - D, gdy wszystkie są w V3, V5 lub V6: „każdy z trzech efektów, jeśli istnieje, jest mniejszy niż 10 pp”.
- Każdy odczyt kończy się wierszem opisowym z M − N i P − N.
- Stan NIEWAŻNY (7.2, 7.6): jedno zdanie „NIEWAŻNY: {przyczyna}; żadnych wniosków o kontrastach.” i wiersz opisowy; bez zdań kontrastów i zdań złożonych.
- **Reguła LEN (warunek D9):** gdy dla kontrastu spełniona jest reguła LEN (7.5, WR5), jego zdanie kończy się „DŁUGOŚĆ (WR5): {przyczyny}. Różnica długości bloków może wyjaśniać ten wynik; efektu nie przypisuje się treści pamięci.”, zdanie złożone A nie wymienia tego ramienia (zamiast tego „ZŁOŻONE-A wstrzymane dla …”), zdanie B jest wstrzymane, gdy dotyczy to M − P, a zdanie D jest wstrzymane, gdy górna granica przedziału α sięga 10 pp. Stan główny się nie zmienia; zmienia się tylko to, czy wolno przypisać efekt treści.
- Raport nie zawiera zdań o „stałych przykładach”, zdań twierdzących, że efektu treści nie ma (zdanie złożone C, które temu zaprzecza, jest dozwolone), zdań, że zysków „nie wolno przypisywać” pamięci, że pamięć pomaga lub nie pomaga ponad to, co mówią zdania kontrastów, ani że 148 zadań „nie wystarcza”. Zakazy sprawdza kod wyrażeniami regularnymi po rdzeniach (odmiany są wykrywane).

Zasady dodatkowe:
- Próg 10 pp jest wyższy od łącznego historycznego zysku M − N (12 zadań na 148, czyli 8,1 pp). Na pytanie „czy co najmniej 10 pp” K1 może odpowiedzieć „nie” albo nie odpowiedzieć; odpowiedź „tak” wymagałaby efektu około 20 pp.
- Stan V3 jest w tym projekcie praktycznie nieosiągalny: wymaga połowy przedziału poniżej 5 pp, a projekt daje 8–12 pp.
- Żaden stan nie zależy od liczby strat ani progów na licznikach.
- Znak estymaty w bloku A przeciwny do analizy głównej: zastrzeżenie „zależny od reżimu próbkowania”.
- Przedział jednej warstwy wykluczający zero ze znakiem przeciwnym: zastrzeżenie „zależny od domeny”.

## 9. Charakterystyka reguł

### 9.0 Przy szumie zmierzonym w pilotażu K1-CAL-NM (obowiązująca)

**Pomiar** (pilotaż 2026-11-13; 148 zadań; ramiona N i M; dwa bloki przy temperaturze 0,7; ziarna 9001 i 9002; raport `../../pilot-nm/report/`):
- `w(N)` = 16,9% (95%: 11,5–23,0), `w(M)` = 14,9% (9,5–20,3);
- `b(M,N)` = 30,4% (C1) i 31,1% (C2), przedziały 95% od 23,0 do 38,5;
- odsetek rozwiązań łącznie 34–35%;
- 9,5 wywołania na epizod.

Symulacja autora (`../v0.3/k1_power_sim_v3.py`, funkcja `run` bez zmian) w reżimie „stałym”, który przyjmuje zmierzoną niezgodność pojedynczego przebiegu, z `w` = 0,159, `b` = 0,307 i odsetkiem 0,345 (`k1_power_measured.py`, `.out`, 6 000 prób):

| Prawdziwy efekt | Wykryto dodatni | Wykluczono 10 pp | Połowa przedziału |
|---|---|---|---|
| −5 pp | 0% | 96% | 8,9 pp |
| 0 pp | 1% | 62% | 8,9 pp |
| 3 pp | 6% | 31% | 8,9 pp |
| 5 pp | 15% | 15% | 8,9 pp |
| 8 pp | 43% | 4% | 8,8 pp |
| 10 pp | 64% | 1% | 8,7 pp |
| 12 pp | 84% | 0% | 8,6 pp |
| 15 pp | 98% | 0% | 8,4 pp |
| 20 pp | 100% | 0% | 8,4 pp |

Cały eksperyment, trzy kontrasty z tym samym efektem:

| Prawdziwy efekt | Co najmniej jeden wykrywa | Wszystkie wykluczają 10 pp | Żaden nie wykrywa |
|---|---|---|---|
| 0 pp | 2% (błąd) | 32% | 96% |
| 3 pp | 14% | 8% | 86% |
| 5 pp | 34% | 2% | 66% |
| 8 pp | 72% | 0% | 29% |
| 10 pp | 89% | 0% | 11% |

Warianty decyzji przy efekcie równym progowi (wykrycie) i przy efekcie 0 (wykluczenie progu):
- plan: 64% / 62%;
- D4, 2 bloki: 57% / 55%;
- D3, 2 kontrasty (97,5%): 70% / 67%;
- D7, 95% na przedział: 79% / 77%;
- D1, próg 8 pp: 43% / 41%.

Wrażliwość na narożniki przedziałów 95% `w` i `b`: wykrycie przy 10 pp 41–81%, wykluczenie przy 0 pp 39–98%.

**Ograniczenia tej charakterystyki:**
- `b` zmierzono między M i N; niezgodność M z P, X i S może być inna. K1 ją zmierzy, a raport wskaże wiersz, który obowiązywał (sekcja 11, pkt 7).
- Model zakłada niezależne zadania; dla estymandu głównego to założenie jest spełnione (7.4).

### 9.1 Przy szumie zakładanym (przed pilotażem, dla porównania)

Bez zmian względem wersji 0.3 (`../v0.3/k1_power_sim_v3.py`; odtworzone bajt w bajt przy tym samym ziarnie, różnice do ±2 pp przy ziarnie 4242; niezależny model logit-normalny daje przy 10 pp wykrycie 50–53% wobec 48–58%; kontrola końcowa R8). Wyjątek: jeśli bramka budżetu z sekcji 10 pominie blok S3, obowiązuje wiersz „2 bloki”.

`k1_power_sim_v3.py`: 148 zadań, 3 bloki, trzy kontrasty, przedziały 98,33%, 6 000 prób na komórkę. Parametry nieznane przed przebiegiem:

- `b0`: niezgodność między ramionami w jednym przebiegu. Zmierzono 19–32% między ramionami z różnymi blokami i 36,5% między M a N (temperatura 0).
- `w`: zmienność próbkowania w obrębie ramienia; przy temperaturze 0 wynosi 1–3%, przy 0,7 jest nieznana.
- Reżim **addytywny**: cała niezgodność z temperatury 0 jest rzeczywista, a szum próbkowania dochodzi do niej (pesymistyczny w tej rodzinie modeli). Reżim **stały**: niezgodność łączna pozostaje równa `b0` (optymistyczny). Reżim addytywny nie jest ograniczeniem dolnym w ogóle: przy `b` > 0,38 albo przy zależności przez ślady względem celu bezwarunkowego moc i błąd są gorsze.

Jeden kontrast, reżim addytywny; w komórkach: **wykryto dodatni / wykluczono 10 pp** (%), zakres po `w` od 0,02 do 0,28:

| Prawdziwy efekt | b0 = 0,20 | b0 = 0,30 | b0 = 0,38 |
|---|---|---|---|
| −5 pp | 0 / 96–97 | 0 / 84–92 | 0 / 72–88 |
| 0 pp | 1 / 62–67 | 1 / 44–56 | 1 / 33–48 |
| 3 pp | 6 / 32–34 | 4–5 / 21–27 | 3–5 / 16–23 |
| 5 pp | 15–17 / 16–17 | 10–13 / 10–12 | 8–11 / 8–11 |
| 8 pp | 44–47 / 4 | 27–37 / 2–3 | 21–32 / 2 |
| 10 pp | 66–71 / 1 | 45–58 / 1 | 35–51 / 1 |
| 12 pp | 85–88 / 0 | 64–78 / 0 | 51–69 / 0 |
| 15 pp | 98–99 / 0 | 86–95 / 0 | 74–91 / 0 |
| 20 pp | 100 / 0 | 99–100 / 0 | 96–100 / 0 |

- Połowa przedziału: 8,2–8,8 pp (b0 = 0,20), 9,2–10,8 pp (0,30), 9,7–12,1 pp (0,38; przy prawdziwym efekcie 0: 10,2–12,1).
- Wykazanie poziomu 10 pp (V1): 1% przy efekcie 10 pp, 9–17% przy 15 pp, 38–74% przy 20 pp.
- Reżim stały, b0 = 0,30: wykrycie przy 10 pp 46–76%, wykluczenie przy 0 pp 44–88%.

Cały eksperyment, wszystkie trzy kontrasty z tym samym prawdziwym efektem (reżim addytywny, b0 = 0,30):

| Prawdziwy efekt | Co najmniej jeden kontrast wykrywa | Wszystkie trzy wykluczają 10 pp | Żaden niczego nie rozstrzyga |
|---|---|---|---|
| 0 pp | 2% (błąd) | 15–28% | 16–26% |
| 3 pp | 11–13% | 3–7% | 37–48% |
| 5 pp | 24–29% | 1–2% | 44–54% |
| 8 pp | 53–64% | 0% | 29–41% |
| 10 pp | 74–83% | 0% | 15–24% |

Wrażliwość (reżim addytywny, b0 = 0,30, `w` = 0,10 i 0,28): wykrycie przy 10 pp / wykluczenie przy 0 pp.

| Wariant | w = 0,10 | w = 0,28 |
|---|---|---|
| plan: 3 kontrasty, 3 bloki | 48% / 46% | 58% / 55% |
| 2 kontrasty (przedziały 97,5%) | 54% / 54% | 63% / 62% |
| 1 kontrast (95%) | 66% / 64% | 74% / 72% |
| 2 bloki | 46% / 43% | 48% / 46% |
| 1 blok | 37% / 36% | 31% / 29% |
| tylko 88 zadań testowych | 28% / 26% | 33% / 32% |
| próg 8 pp | bez zmian / 29% | bez zmian / 36% |
| próg 5 pp | bez zmian / 11% | bez zmian / 13% |

Błędy: fałszywe wykrycie w jednym kontraście około 1%; co najmniej jedno fałszywe zdanie w całym odczycie 1,7–4,8%, przy założeniu niezależnych zadań. Dla estymandu głównego (7.4, pkt 1) to założenie jest spełnione; dla estymandu bezwarunkowego nie.

Po przebiegu raport porównuje zmierzone `w` i `b` z założeniami i wskazuje kolumnę, która obowiązywała.

## 10. Budżet i kolejność

Zmierzone w NIGHT-2 przy temperaturze 0: 9,1–9,9 wywołania na epizod (E3 9,78, E1 9,35), średnio 1,41 s czasu zegarowego na wywołanie (mediana 1,05 s). Zmierzone w pilotażu przy temperaturze 0,7 dla N i M: 9,5 wywołania na epizod (odchylenie 3,3); 6 015 wywołań w 2 h 24 min, czyli około 1,44 s na wywołanie łącznie z narzutem. P, X i S nie były mierzone; pomiar w etapie T zostaje.

| Etap | Zawartość | Prognoza przy 9,6 wywołania na epizod |
|---|---|---|
| T | test techniczny (≤ 10), test zgodności (odtworzenie, 0 wywołań), `c_d`: 30 bloków P do kalibracji i 30 do T-długość (60), pomiar wywołań na epizod: ramię N na 12 zadaniach treningowych przy temperaturze 0,7, zapisywane wyłącznie liczby wywołań, bez `solved` (około 115) | ≤ 300 (limit etapu) |
| A | 3 ramiona × 148 | 4 689 |
| S1, S2, S3 | po 5 ramion × 148 | 3 × 7 815 |
| | **razem** | **28 434** z zapasem 10% (limit twardy 30 000); szacunek bez zapasu około 25 800 |

- Czas: około 10–10,5 godziny (25 800 wywołań × 1,37–1,44 s); koszt: 0 USD.
- **Prognoza:** `m` = średnia liczba wywołań na epizod ze wszystkich epizodów przy temperaturze 0,7 do danej chwili (pomiar T, potem ukończone bloki próbkowane); wyłącznie liczby wywołań, nigdy wyniki. `P_A = ceil(1,10 · m · 444)`, `P_S = ceil(1,10 · m · 740)`.
- **Bramka przed blokiem A:** blok A startuje tylko wtedy, gdy `wydane + P_A + 2 · P_S ≤ 30 000` (po bloku A muszą zmieścić się co najmniej dwa bloki próbkowane). W przeciwnym razie program zatrzymuje się przed blokiem A i zapisuje decyzję dla właściciela (przy `m` powyżej około 14,0).
- **Bramka przed każdym blokiem próbkowanym:** blok startuje tylko wtedy, gdy `wydane + P_S ≤ 30 000` (z `m` przeliczonym przed tym blokiem); w przeciwnym razie program pomija ten i dalsze bloki. Najwyżej 3 bloki próbkowane.
- Budżety bloków są prognozami, nie osobnymi limitami. Jedynym limitem twardym jest 30 000; blok przerwany przez limit twardy jest nieukończony i nie wchodzi do analizy (7.2).
- Kolejność: T, A, S1, S2, S3, zamrożenie, checker, analiza, raport.
- Decyzje bramek zapisywane w protokole przed blokiem, którego dotyczą.
- Awarie, wznowienia, nadzorca i rejestr prób jak w NIGHT-2 (7.2). Po zakończeniu usunąć zadanie harmonogramu programu.

Uzasadnienie (test W7): reguła 0.3 („2 bloki dopiero powyżej 34 000”) planowała ponad limit twardy przy `m` od około 10,2 do 11,5, a osobne limity bloków przy dłuższych epizodach X (×1,3–1,6) odrzucały kolejne bloki, marnując średnio 8–16 tys. wywołań; ważny przebieg (≥ 2 bloki) w 41–70% symulacji. Reguła 0.4 nigdy nie planuje ani nie wydaje ponad 30 000, nie marnuje wywołań na bloki odrzucane z powodu budżetu i daje ważny przebieg w 98–100% przy `m` ≤ 10,2 oraz 94–96% przy `m` = 11; poniżej tego niepowodzenie oznacza głównie zatrzymanie przed blokiem A, bez wydatku.

## 11. Raport końcowy

1. Stan etapów, koszty, poprawki, decyzje bramek, wyniki L1–L8 z liczbą sprawdzonych źródeł, miara L9 (obie agregacje).
2. Tablica wyników: ramię × blok, ogółem i w 6 warstwach.
3. Dla każdego kontrastu głównego: estymata, przedział decyzyjny, stan, obie odpowiedzi, `ρ̂`, średnia permutacyjna, `ρ̃`, p, `ρ*`, wyniki WR1–WR4.
4. Odczyt wygenerowany przez kod.
5. Drabina opisowa i odpowiedź drugorzędna z bloku A.
6. Pomiar szumu i tabela potrzebnej liczby zadań.
7. Porównanie założeń symulacji ze zmierzonymi wartościami.
8. Kontrola dryfu i kontrola długości: tokeny promptu każdego ramienia względem M (odchylenie ponad 10% jako flaga); rozkład stosunku tokenów P/M na blok (kwantyle 5–95%), `c_d` dla domen; rozkład stosunku długości S/M i X/M na turę; **na zadanie:** `x_i(C)` dla P, X, S (średnia, kwantyle 5–95%, B1, B2), WR5 (α, β, podzbiór zrównoważony) i wynik reguły LEN dla każdego kontrastu.
9. Wiersz w rejestrze eksperymentów i zdarzenia pamięci projektu.

## 12. Czego K1 nie rozstrzyga

- Nie rozdzieli wiarygodnie tekstu, formatu i treści przy efektach 3–9 pp (sekcja otwierająca i 9).
- Nie wykaże efektu co najmniej 10 pp, jeśli prawdziwy efekt jest mniejszy niż około 20 pp.
- Nie usuwa zależności przez wspólne ślady; wniosek dotyczy tej puli, a diagnostyka przenoszalności ma małą moc (7.4).
- Nie mierzy wpływu samego nagłówka: wszystkie bloki mają nagłówek pamięci. Placebo z neutralnym nagłówkiem wymagałoby szóstego ramienia.
- L4 nie wykrywa synonimów spoza zamrożonej listy wariantów (np. rzadkich określeń paliwa); korpus jest wąski tematycznie, a raport podaje L4b dla każdego bloku P.
- P jest dopasowane tokenami średnio w domenie, nie na blok; S i X przybliżeniem tokenów na turę z \|ln r\| ≤ ln 1,2, czyli od −16,67% do +20% (D12, errata E1). Nierównowagę na zadanie mierzy i ocenia WR5 z regułą LEN.
- Pilotaż zmierzył szum tylko dla N i M; charakterystyka z sekcji 9.0 jest przybliżeniem dla kontrastów z P, X i S.
- Nie dotyczy notatek po błędzie, porównania z Mem0, innych modeli ani TradingBot.
- Nie potwierdza niczego na czystych danych.

## 13. Decyzje właściciela

| # | Decyzja | Brzmienie w tej specyfikacji | Stan |
|---|---|---|---|
| D1 | Próg praktyczny | 10 pp | zatwierdzona 2026-11-13 |
| D2 | Reżim próbkowania | temperatura 0,7, top_p 0,8, top_k 20; seed 7001–7003 | zatwierdzona 2026-11-13 |
| D3 | Rodzina kontrastów | trzy: M − P, M − X, M − S | zatwierdzona 2026-11-13 |
| D4 | Bloki próbkowane | najwyżej 3, z bramkami z sekcji 10 | zatwierdzona 2026-11-13 |
| D5 | Wykonawca | sesja Opus według wzoru NIGHT-2, tylko lokalna Ollama, katalog roboczy poza repozytoriami | zatwierdzona 2026-11-13 |
| D6 | Jednostki | 148 zadań, z analizą WR4 na 88 testowych | zatwierdzona 2026-11-13 |
| D7 | Poziom ufności | 98,33% na przedział (łącznie ≥ 95%) | zatwierdzona 2026-11-13 |
| D8 | Kolejność | pilotaż N/M przed K1: wykonany 2026-11-13; rekomendacja protokołu (wykrycie przy 10 pp 64% ≥ 40%): zamrozić K1 | zatwierdzona; pilotaż wykonany |
| D9 | Długość P | `c_d` na domenę, ±5% na sumie tokenów; nierównowaga na zadanie, B1, WR5, reguła LEN | zatwierdzona warunkowo; warunki wpisane |
| D10 | Budżet | bramki z sekcji 10, limit twardy 30 000 | zatwierdzona |
| D11 | Kontrole techniczne | hak L6a, `BfclK1`, L10 (pochodzenie), listy L4a, brak techniczny ze statusu checkera | kierunek zatwierdzony; warunki wpisane i przetestowane |
| D12 | Długość X i S | losowanie z dopasowaniem przewidywanych tokenów: \|ln(przewidywane/cel)\| ≤ ln 1,2, czyli od −16,67% do +20% bloku M tury (sekcja 2; errata E1) | zatwierdzona 2026-11-13; tolerancja logarytmiczna wybrana przez właściciela 2026-11-13 (C2) |

Skutki alternatyw dla otwartych decyzji (przy zmierzonym szumie, sekcja 9.0) zestawia `DECYZJE_DO_ZAMROZENIA.md`.

## 14. Zamrożenie i dalsza droga

Errata 1.0.1 jest zamrażana przez `zamroz_v101.py` po kontroli spójności (`kontrola_spojnosci.py`: zmienione wyłącznie miejsca wymienione w sekcji „Errata v1.0.1”, bez zmian w hipotezach, progach, poziomach ufności, blokach i kontrastach) i po kontroli erraty (`kontrola_erraty.py`). Punkty niżej opisują zamrożenie wersji 1.0.

1. Właściciel zatwierdził D1, D3, D4, D7 i D12 w brzmieniu rekomendowanym (2026-11-13).
2. `zamroz.py`:
   - odmawia, jeśli w tekście pozostaje choć jedno oznaczenie decyzji niezatwierdzonej albo jeśli `../v0.4/testy/run_all.py` nie daje `ALL: PASS`;
   - zapisuje `../v1.0/SPEC_K1_PLACEBO_v1.0.md`, ze statusem „ZAMROŻONA” i z datą;
   - zapisuje `../v1.0/FREEZE.json` (sha256 specyfikacji, testów, prototypów kodu i raportu pilotażu, ale nie pliku zapieczętowanego).
3. Po zamrożeniu powstaje wykonawca K1 w osobnym katalogu poza repozytoriami, według wzoru pilotażu. Kod pilotażu daje gotowe:
   - przygotowanie i L10;
   - hak;
   - proces roboczy i nadzorcę;
   - checker;
   - pieczęć danych.
   
   Do dopisania:
   - korpus P przez L4a;
   - `c_d`;
   - losowania X i S z D12;
   - ramiona P, X, S;
   - analiza z odczytem v0.4 i WR5.
   
   Następnie wszystkie testy z sekcji 6.3 offline, potem osobna zgoda na start.
4. Specyfikacji nie poddaje się kolejnej pełnej recenzji. Po zamrożeniu zmiany są możliwe tylko według sekcji 6 (poprawki techniczne z wpisem w protokole).
