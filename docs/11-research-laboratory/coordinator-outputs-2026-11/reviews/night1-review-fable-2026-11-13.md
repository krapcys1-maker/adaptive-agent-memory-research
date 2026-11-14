# AAMR-NIGHT-1: niezależna ocena i decyzja o następnym kierunku

Data: 2026-11-13. Autor: Claude (Fable 5.2), na zlecenie właściciela.
Status: ocena i decyzja. Nie uruchomiłem żadnego modelu. Niczego nie zmieniłem w wynikach NIGHT-1, w gałęziach
ani w repozytorium; nie było push ani merge.

## 0. Decyzja w skrócie

**Kierunek: złożyć pierwszą wersję systemu (v0) z dwóch pamięci, które już mamy, usunąć zmierzony mechanizm
szkód i zmierzyć całość na tle konkurentów. Program AAMR-NIGHT-2, specyfikacja w `SPEC_AAMR_NIGHT2.md`.**

Nie przyjmuję rekomendacji Opusa (EXP-VER-1, weryfikacja każdej lekcji) jako samodzielnego następnego
eksperymentu. Zostaje ona jednym z etapów, w zmienionej formie. Powody, wszystkie z surowych danych nocy:

1. Największa zmierzona dźwignia to połączenie pamięci, a nie weryfikacja. Na 58 nietkniętych zadaniach pamięć
   sukcesów i notatki przy błędzie odzyskują **różne** zadania: 12 tylko pamięć sukcesów, 5 tylko notatki, 2
   wspólne. Razem pokrywają 35 zadań przy 17 bez pamięci. Tych dwóch pamięci nikt jeszcze nie uruchomił razem.
2. Największa zmierzona szkoda ma konkretny, naprawialny mechanizm. Pamięć sukcesów traci 9 zadań, z czego
   **8 przez skopiowanie wartości albo kroku z pokazanego przykładu** (kod lotniska, priorytet zgłoszenia, nazwa
   katalogu, dodatkowe ustawienie budżetu).
3. Weryfikacja lekcji ma na nowych domenach mały zapas: notatki straciły tam 2 zadania z 58. Do tego reguła
   zaproponowana przez Opusa **nie odrzuciłaby** błędnej lekcji Qwena: w teście na stanach treningowych ta lekcja
   rozwiązała 3 błędy z 6 (bez notatki 2) i zaliczyła 3 tury (bez notatki 2).
4. Warunek „lepszy niż konkurencja” wymaga konkurentów w naszym harnessie. Nocny program ich nie uruchomił, a
   zużył 58 zadań przeznaczonych w strategii na pierwsze uczciwe porównanie.

Czego nie zmieniam: celu projektu, architektury C0–C7 jako hipotezy, reguły „lepszy niż konkurencja” co do
istoty. Zmienia się jedno: zbiór, na którym odbędzie się ostateczne porównanie (sekcja 6).

## 1. Co przeczytałem i co przeliczyłem

Przeczytane w całości: `WNIOSKI.md`, `REPORT.md`, `PROTOCOL.md`, `followup.json`, artefakty pamięci (wszystkie
teksty lekcji D, Q, F dla trzech domen, bramka b1), sesje surowe `sA`, `sC`, `sD`, `sE`, `census`, `b1` (jsonl),
fragmenty `scripts/aamr_night1.py` (sesje, ramiona, dostawca pamięci sukcesów), aktualna `STRATEGIA_AAMR.md`
z `AKTUALIZACJA_1`.

Przeliczone samodzielnie z surowych wierszy sesji, bez użycia kodu analizy Opusa (`tier_e/`, wszystko bez modelu):

| Skrypt | Co liczy |
|---|---|
| `n1_01_scoreboard.py` | wyniki wszystkich ramion, pary zysk/strata, porównania izolujące jeden składnik, łączenie sesji, komplementarność |
| `n1_02_lessons.py` | test b1 w rozbiciu na sygnatury, reguły bramki odtworzone na b1, skutek każdej notatki w turach z danym błędem, pokrycie |
| `n1_03_rplus_anatomy.py` | tura rozstrzygająca dla każdego zadania zyskanego lub straconego przez pamięć sukcesów |
| `n1_04_copy_losses.py` | mechaniczna miara „strata przez skopiowanie z przykładu” (implementacja wzorcowa dla NIGHT-2) |

**Liczby Opusa się zgadzają.** Wszystkie wyniki ramion, pary zysków i strat oraz wartości p z `REPORT.md`
odtworzyłem dokładnie. Integralność przebiegu jest dobra: protokół zamrożony przed startem, trzy poprawki
techniczne opisane przed sesją sA, sumy kontrolne, powtórka N w każdej sesji, placebo, zero błędów. Zastrzeżenia
dotyczą interpretacji i wyboru następnego kroku, nie rzetelności pomiaru.

## 2. Ocena krytyczna wyników

### 2.1 EXP-FIX-0: werdykt „supported” na 14B jest słabszy, niż brzmi

Reguła przeszła (TrO 15, N 9), ale 6 punktów przewagi składa się z dwóch różnych rzeczy:

| Porównanie (14B, 30 zadań testowych VC) | zyski : straty | p jednostronne |
|---|---|---|
| TrO wobec N (reguła) | 7 : 1 | 0,035 |
| Tr wobec N (same notatki o `startEngine`) | 4 : 1 | 0,19 |
| TrP wobec Tr (placebo przy błędzie baku) | 0 : 0 | 1,0 |
| **TrO wobec TrP (sama wyrocznia)** | **3 : 0** | **0,125** |

- Połowę przewagi dają trzy notatki o `startEngine`, które są też w ramieniu placebo. Sama wyrocznia dodaje 3
  zadania (67, 71, 97). To za mało, by pojedyncza sesja na 14B była istotna.
- Efekt wyroczni jest jednak spójny. 14B test 3:0, 14B trening 2:0, 9B 6:0. Po połączeniu sesji 14B: 5:0
  (p = 0,031). Na poziomie tur z błędem baku: **15 z 25 zaliczonych z wyrocznią, 3 z 25 z placebo, 4 z 26 bez
  pamięci** (trzy sesje razem). Łączenie zrobiłem po obejrzeniu wyników, więc ma status eksploracyjny.
- Hipoteza H5 w zapisanej postaci („odzyska co najmniej 5 zadań z 30”) na 14B **nie jest spełniona przez samą
  wyrocznię** (3), na 9B jest (6). Poprawny odczyt: treść przy błędzie działa; rozmiar efektu na 14B jest
  mniejszy, niż zakładałem.
- Wyrocznię napisałem sam, znając porażki z zadań testowych VC. To dane rozwojowe.

### 2.2 Skąd +3 dla notatek o `startEngine`

Opus ma rację co do mechanizmu, potwierdziłem go na wszystkich turach. Bez pamięci agent po uruchomieniu silnika
zwalnia hamulec w 4 z 20 tur (14B) i 7 z 26 tur (9B). Z notatkami: 0 z 21 i 0 z 26. Błąd agent i tak rozwiązuje
sam. Notatka poprawia więc **zakończenie procedury**, a nie naprawę błędu.

Czego nie wiemy: czy to skutek treści notatki, czy samego przerwania. Placebo dotyczyło tylko błędu baku; dla
`startEngine` kontroli nie było.

### 2.3 Pisarze lekcji: twierdzenie „Flash wygrał jedną lekcją” jest za mocne

Flash wobec Qwena na VC: 17 wobec 12, pięć zadań różnicy (67, 74, 80, 82, 97).

- Dwa z nich (67, 97) to błąd baku. Jedno (80) to inna sygnatura, `estimate_distance`: z notatką Flash błąd
  rozwiązany w 6 z 6 tur i 5 tur zaliczonych, z notatką Qwena 3 z 7 i 3. Jedno (74) to `startEngine`, jedno (82)
  to szum sprzed pamięci.
- Notatka Flash o drzwiach każe od razu wcisnąć hamulec, więc drugi błąd `startEngine` prawie znika (6 tur zamiast
  ok. 20). Stąd spadek błędów narzędzi z 87 do 47.
- Lekcja Qwena o baku nie jest po prostu błędna. Zawiera dobrą instrukcję („sprawdź poziom paliwa”) i złą diagnozę
  („bak pełny, nic nie rób”). W teście na stanach treningowych trzy razy doprowadziła do poprawnego dolania, a
  raz zepsuła turę, którą agent bez notatki zaliczał. Taką treść trudniej wyłapać niż jawny fałsz.

Wniosek: na VC notatki Flash są lepsze w dwóch sygnaturach z pięciu, nie w jednej. Na nietkniętych domenach
różnicy nie ma (21 wobec 22). Teza „lokalny pisarz wystarcza” pozostaje hipotezą.

### 2.4 Transfer: jedyny test potwierdzający nie testował tego, co miał

- Test główny (TrD > N) dał +2 przy p = 0,25. Kompilator deterministyczny wytworzył po 2 lekcje na domenę.
  Notatka pokazała się w 12 z 58 epizodów i objęła **6 z 29** pierwszych nieudanych tur z błędem.
- To było do przewidzenia: w `AKTUALIZACJA_1` policzyłem, że kompilator daje 2–3 lekcje z 20 zadań. Test główny
  sprawdził więc mechanizm przy prawie zerowej dawce. Wynik mówi: „kompilator progowy nie daje pokrycia w nowych
  domenach”. Nie mówi: „notatki przy błędzie nie przenoszą się”.
- Notatki pisane przez LLM pokryły 24 z 29 takich tur i dały +5 (Qwen) i +4 (Flash). Kierunek zgodny, bez
  istotności (Holm: żadne ramię). Na poziomie tur z błędem: zaliczonych 13 ze 114 bez pamięci, 24 z 99 z notatkami
  Qwena, 25 ze 111 z notatkami Flash.
- **Koszt strategiczny.** 58 zadań systemu plików i podróży było w strategii zbiorem dla pierwszego uczciwego
  porównania z konkurentami (etap 2). Zostały zużyte, zanim powstały ramiona konkurentów. Właściciel zlecił test
  transferu, więc samo użycie było w mandacie; słaby był dobór ramienia głównego. Skutek opisuję w sekcji 6.

### 2.5 Pamięć sukcesów: największy zysk, największa szkoda, jasny mechanizm

| 58 nietkniętych zadań | zyski | straty | wynik |
|---|---|---|---|
| system plików (30) | 7 | 1 | 10 wobec 4 (p = 0,035, eksploracyjnie) |
| podróże (28) | 7 | 8 | 12 wobec 13 |

- Zyski: w 7 z 14 zadań mniej błędów narzędzi w turze rozstrzygającej (przykład pokazuje właściwą procedurę).
- Straty: **8 z 9 to kopie z przykładu**, policzone mechanicznie (wartość lub funkcja nieobecna u N, nieobecna w
  prośbach i wcześniejszych wynikach zadania, obecna w bloku pamięci):

  | Zadanie | Co agent skopiował z przykładu |
  |---|---|
  | 49 | katalog `tmp` zamiast `temp` |
  | 152, 181 | `priority=4` z cudzego zgłoszenia |
  | 163, 191 | dodatkowy krok `set_budget_limit(7142.86)` po anulowaniu rezerwacji |
  | 165 | cel podróży `JFK` |
  | 182 | kod lotniska `SSV` zamiast `SVP` |
  | 183 | klasa `business` i dodatkowe `retrieve_invoice` |

- W podróżach pula ma 57 śladów, w systemie plików 26. Większa pula oznaczała tu więcej podobnych przykładów z
  cudzymi wartościami. To zgodne z obserwacją z literatury, że pamięć może szkodzić bardziej, gdy doświadczenia
  przybywa (2610.29357), ale u nas to jedna para domen, więc tylko hipoteza.

### 2.6 Szkody notatek

- Zadanie 49: notatki Qwena **i** Flash o błędzie `cd` radzą utworzyć katalog. Agent go utworzył, choć prośba
  wprost tego zakazywała. Lekcja deterministyczna dla tej samej sygnatury mówi „wywołaj `ls`”, bo powstała z
  wykonanych napraw. To jeden przypadek, ale pokazuje różnicę między treścią wyprowadzoną z wykonania a treścią
  dopisaną przez model.
- Zadanie 60 (VC) tracą wszystkie ramiona z notatkami. N zalicza je przypadkiem. Zgadzam się z opisem Opusa.
- Nieaktualna lekcja (40 galonów): agent wykonał ją w 6 z 8 tur. Ważny szczegół, którego Opus nie podkreślił:
  **błąd został „rozwiązany” w 8 z 8 tur, a zaliczonych tur było 0**. Sygnał „błąd zniknął” nie odróżnia treści
  nieaktualnej od poprawnej. Odróżnia je dopiero wynik zadania.

### 2.7 Rekomendacja Opusa (EXP-VER-1) w świetle danych

Test b1 w rozbiciu na sygnatury (stany / błąd rozwiązany / tura zaliczona):

| Sygnatura | bez notatki | wyrocznia | Qwen | Flash |
|---|---|---|---|---|
| bak paliwa | 6 / 2 / 2 | 6 / 5 / 3 | 6 / 3 / 3 | 6 / 5 / 4 |
| `estimate_distance` | 3 / 1 / 1 | – | 3 / 2 / 1 | 3 / 3 / 1 |
| `startEngine` (3 sygnatury, 10 stanów) | 10 / 10 / 4 | – | 10 / 10 / 4 | 10 / 10 / 4 |

- Reguła z `WNIOSKI.md` („rozwiązuje więcej błędów niż brak notatki i placebo, a liczba zaliczonych tur nie
  spada”) **dopuszcza** lekcję Qwena o baku: 3 > 2 i 3 ≥ 2. Zdanie „bramka per lekcja prawdopodobnie odrzuciłaby
  lekcję Qwena” nie ma pokrycia w danych.
- Lekcję Qwena odróżnia tylko jedno: zepsuła stan, który agent bez notatki zaliczał (zadanie 73). Reguła
  „żadnej regresji na stanach zaliczanych bez notatki” by ją odrzuciła, a wyrocznię i Flash dopuściła.
- Próg „co najmniej o 2 więcej rozwiązanych” odrzuca lekcję Qwena, ale odrzuca też wszystkie notatki o
  `startEngine`, które w teście dały +3.
- Przy 2–6 stanach na sygnaturę bramka progowa nie ma mocy. Lepiej działa **wybór najlepszego z kilku kandydatów**
  na tych samych stanach: w b1 ranking bak-paliwa wypadł poprawnie (Flash, wyrocznia, Qwen, brak).
- Test b1 przewidział zachowanie w teście w 4 z 5 przypadków jakościowych (bak: O, F, Q; dystans: F, Q).
  Nie przewidział zysku z notatek o `startEngine`.

Wniosek: pomysł jest dobry jako składnik, zły jako samodzielny następny eksperyment. Wchodzi do NIGHT-2 jako
etap 2: turniej kandydatów z regułą braku regresji i z kontrolami o znanej odpowiedzi.

## 3. Co jest udowodnione, a co pozostaje hipotezą

**Ustalone (w podanym zakresie):**

| # | Ustalenie | Podstawa | Zakres |
|---|---|---|---|
| U1 | Poprawna treść podana przy błędzie zamienia porażki w sukcesy; sama obecność notatki nie | tury z błędem baku 15/25 wobec 3/25 (placebo); zadania 11:0 w trzech sesjach | jedna sygnatura, jedna domena, dwa modele; dane rozwojowe |
| U2 | Agent wykonuje notatkę prawie dosłownie, także nieaktualną | 8/8 z wyrocznią, 6/8 z lekcją „40 galonów” | VC, 14B |
| U3 | Sygnał „błąd zniknął” nie wykrywa treści nieaktualnej | 8/8 rozwiązanych, 0/8 zaliczonych | VC, 14B |
| U4 | Kompilator progowy nie daje pokrycia w nowych domenach | 2 lekcje na domenę, 6/29 tur | potwierdzające (negatywne) |
| U5 | Surowe ślady sukcesów zmieniają wynik w obie strony | +14 / −9 na 58 zadaniach | nietknięte zadania, jedna sesja |
| U6 | Straty pamięci sukcesów to prawie wyłącznie kopie z przykładu | 8 z 9, miara mechaniczna | post hoc |
| U7 | Notatki i przykłady odzyskują różne zadania | 12 + 5 + 2 wspólne | post hoc |
| U8 | Powtórka bez pamięci prawie nie zmienia wyniku | 30/30, 30/30, 57/58 zgodnych | przebiegi rozbiegają się w 13/58, wynik w 1 |
| U9 | Bramka zbiorcza przepuszcza treść z błędną diagnozą | lekcja Qwena o baku | VC |
| U10 | Pamięć zbudowana na 14B działa na 9B, mocniej | wyrocznia +9, 9:0 | VC |

**Hipotezy (jeszcze nie pokazane):**

- Że notatki przy błędzie zwiększają liczbę rozwiązanych zadań na nowych domenach (+5 i +4, bez istotności).
- Że pamięć sukcesów pomaga netto poza systemem plików (trzy obserwacje po +4 do +5, żadna istotna).
- Że obie pamięci się sumują. Nie były uruchomione razem.
- Że zysk notatek o `startEngine` pochodzi z treści, a nie z przerwania.
- Że lokalny pisarz wystarcza. Na VC napisał gorsze notatki w dwóch sygnaturach z pięciu.
- Że weryfikacja na stanach treningowych odsiewa złe lekcje. Dane b1 temu nie sprzyjają w wersji progowej.
- Że rodzaj pomocnej pamięci zależy od domeny. Obserwacja po fakcie.
- Że system jest lepszy od konkurencji. Nie było żadnego ramienia konkurenta.

## 4. Porównanie z wcześniejszymi badaniami i konkurencją

**Z naszymi wynikami:**

| Zjawisko | Pilot | S1 | NIGHT-1 | Odczyt |
|---|---|---|---|---|
| N na 30 zadaniach VC | 10 | 9 | 9 i 9 | poziom odniesienia stabilny |
| pamięć sukcesów R+ wobec N | 14 wobec 10 (VC) | 13 wobec 9 (VC) | 22 wobec 17 (nowe domeny) | trzy razy +4 do +5; pierwszy raz widać cenę: 9 strat |
| notatka po błędzie (Tr) wobec N | – | 13 wobec 9 (5:1) | 12 wobec 9 (4:1) | powtórzone na tych samych zadaniach; mechanizm uboczny |
| błąd baku bez pamięci | 0 odczytów paliwa w 52 turach | to samo | 1 z 9 tur zaliczona | największa pojedyncza przyczyna porażek VC potwierdzona |
| porażki przy błędzie w innych domenach (H7) | – | – | 29 z 41 pierwszych nieudanych tur zawiera błąd narzędzia | zjawisko ogólne, nie tylko VC |

**Z konkurencją (liczby z ich publikacji, w ich harnessach; brak porównania bezpośredniego):**

- Konkurenci dają małym modelom 3–6 pp ponad brak pamięci (ReMe na Qwen3-14B +3,2 pp; GTTA na Qwen2.5-14B
  +3,5 pp). Nasze pojedyncze składniki na nietkniętych zadaniach dały po +8,6 pp (22 wobec 17 z 58), bez
  istotności. Rząd wielkości jest obiecujący, ale to nie jest porównanie.
- Wynik na 9B (10 → 19 z 30 z ręcznie napisaną treścią po porażce) jest zgodny z pracą „Compliance Trap”
  (10,8 → 30,5 w ich zadaniach): mały model wykonuje podaną treść. Ta sama cecha tłumaczy szkody.
- „Surowe lepsze niż streszczenia” (2611.03930) zgadza się z siłą surowych śladów i z przypadkiem zadania 49.
  Nasze dane dodają zastrzeżenie: surowy ślad przenosi też cudze wartości. AWM rozwiązuje to zamianą wartości na
  zmienne; tego mechanizmu jeszcze nie sprawdziliśmy.
- ReasoningBank pokazuje jeden wpis (k = 1). W naszych stratach dwa razy zaszkodził drugi z dwóch przykładów
  (163, 191). To argument za sprawdzeniem k = 1.

## 5. Wybór kierunku

Reguła ze strategii: wybrać test o największej oczekiwanej liczbie odzyskanych zadań na wywołanie.

| Dźwignia | Zapas na 58 nietkniętych zadaniach | Koszt sprawdzenia | Ocena |
|---|---|---|---|
| Połączenie przykładów i notatek | do +12 ponad najlepsze pojedyncze ramię | ok. 850 wywołań na ramię | **największa** |
| Usunięcie kopii z przykładów | do +8 (tyle strat ma tę przyczynę) | ok. 850 na ramię, 2 300 na strojenie | **duża, naprawialna** |
| Dobór i weryfikacja notatek | +2 na nowych domenach, +2 do +5 na VC | ok. 1 500 | średnia; ważna dla bezpieczeństwa |
| Konkurenci w harnessie | 0 zadań, ale bez tego nie ma twierdzenia | ok. 3 500 | warunek konieczny |
| 22 zadania nierozwiązane przez żadne ramię | nieznany | spis porażek, bez modelu | później |

Stąd program: najpierw naprawić i dostroić pamięć sukcesów na zadaniach treningowych, potem dobrać notatki na
stanach treningowych, potem zmierzyć system złożony na 88 zadaniach rozwojowych, potem konkurenci i drugi model.
Szczegóły, reguły decyzji i budżet: `SPEC_AAMR_NIGHT2.md`.

Rozważone i odłożone:

- **EXP-VER-1 samodzielnie:** mały zapas, narzędzie bez mocy w wersji progowej (2.7).
- **S2 z EXP-XFER-1:** zastąpione przez NIGHT-1 i NIGHT-2. Zamykam je formalnie, żeby nie wisiał zaprojektowany,
  a niewykonany eksperyment.
- **Egzamin na TradingBot teraz:** nie. To ostatnie czyste dane; system i ramiona konkurentów muszą być najpierw
  zamrożone.
- **Drugi benchmark:** potrzebny dla wiarygodności zewnętrznej, ale dopiero gdy v0 przejdzie egzamin.

## 6. Zmiana w strategii, którą wymusza NIGHT-1

Warunek 1 z „lepszy niż konkurencja” mówił o 58 zadaniach z dwóch domen nieużytych do projektowania. Tych zadań
już nie ma. W BFCL czysty pozostaje tylko TradingBot, ale w czterech odmianach (podstawowa, brak funkcji, brak
parametru, długi kontekst): 50 scenariuszy, 200 zadań, żadne nie było czytane ani uruchamiane.

Nowy zapis warunku 1: 20 scenariuszy TradingBot do budowy pamięci, **30 scenariuszy × 4 odmiany = 120 zadań
egzaminu**, analiza po scenariuszach; ramiona: brak pamięci, v0, najlepszy konkurent z NIGHT-2; wszystko
zamrożone przed pierwszym wywołaniem. Warunek 4 (powtórzenie na TradingBot) zmienia się w powtórzenie egzaminu
na drugim modelu. Egzamin jest jednorazowy i **wymaga Twojej zgody**; NIGHT-2 go nie uruchamia.

Do czasu egzaminu wszystkie wyniki na VC, systemie plików i podróżach mają status rozwojowy. Szczegóły zmian w
tabeli hipotez: `strategy-2026-11-12/AKTUALIZACJA_2_PO_NIGHT1.md`.

## 7. Ograniczenia tej oceny

- Analizy z sekcji 2.5, 2.7 i 5 powstały po obejrzeniu wyników. Mechanizm kopiowania opisałem na tych samych 58
  zadaniach, na których NIGHT-2 będzie mierzyć poprawkę. Dlatego poprawka jest najpierw strojona i sprawdzana na
  zadaniach treningowych, na których pamięci sukcesów nikt jeszcze nie oglądał.
- Miara „strata przez kopię” jest mechaniczna i może przeoczyć kopię przez parafrazę. Zadanie 151 zostało
  sklasyfikowane jako „inne”.
- Nie uruchamiałem modeli, więc nie sprawdziłem, czy maskowanie wartości zachowuje zyski. To jest pytanie etapu 1.
  Bez modelu sprawdziłem tylko tyle (`tier_e/n1_05_mask_prototype.py`): po zamaskowaniu skopiowana wartość
  przestaje być widoczna w bloku w 7 z 8 strat przy dwóch przykładach i w 8 z 8 przy jednym; skopiowany
  dodatkowy krok znika dopiero przy jednym przykładzie (2 z 3).
- Liczby konkurentów pochodzą z ich publikacji, sprawdzonych wcześniej; w tej ocenie nie czytałem ich ponownie.
