# AAMR EXP-A (EXP-ABS-0): specyfikacja, wersja 0.1 — PROJEKT DO AUDYTU

2026-11-14. Redakcja: Claude (Fable 5.2).
**Status: projekt. NIE zamrożony, NIE zaimplementowany, NIE uruchomiony.** Właściciel zatwierdził wyłącznie przygotowanie protokołu. Zamrożenie, implementacja i start wymagają osobnych zgód.

Pliki w tym folderze (`[machine-local path omitted]\`):
- `SPEC_EXP_A_v0.1.md` — ten dokument;
- `power\expA_power_sim.py`, `.out` — symulacja mocy (bez wywołań modelu);
- `prior\prior_evidence.py`, `.out` — dowody wstępne z NIGHT-2 i liczby wykonalności.

Podstawa: audyt K1 `[machine-local path omitted]`; protokół K1 v1.0.1 (wzorzec kontroli, niezmieniany).
Żaden zamrożony artefakt K1, NIGHT-1, NIGHT-2 ani koordynatora nie został zmieniony. `sealed/` nie było czytane.

---

## 0. Co ten eksperyment może, a czego nie może rozstrzygnąć

**Może:** na 54 zadaniach, na których blok pamięci powtarzalnie pomaga (33) albo szkodzi (21), ustalić, czy swoista pomoc i swoista szkoda dobranych śladów **zależą od konkretnych wartości** w śladach, czy przetrwają ich usunięcie.

**Nie może:**
- wykazać, że abstrakcja poprawia pamięć na benchmarku. Zadania są wybrane na podstawie wcześniejszych wyników. Nawet w najlepszym scenariuszu zysk na całych 148 zadaniach wyniósłby około +4 pp wobec M i +6 pp wobec N, czyli poniżej wykrywalności tego benchmarku (K1: połowa przedziału 8 pp);
- rozróżnić efektów pośrednich. Test odróżnia „większość” od „mniejszości” zachowanego efektu; przy około 25–75% wynik będzie zwykle nierozstrzygnięty (sekcja 9);
- obalić abstrakcji jako idei. Wynik negatywny dotyczy tej jednej, zamrożonej reguły.

**Zdanie obowiązkowe w każdym raporcie:** „Wynik dotyczy 54 zadań wybranych na podstawie wcześniejszych wyników NIGHT-2. Nie jest dowodem poprawy ani pogorszenia na całym benchmarku.”

---

## 1. Zmiany względem propozycji z audytu K1 i ich powody

Propozycja A z audytu miała trzy wady, które ten projekt usuwa.

| # | Wada pierwotnej propozycji | Poprawka |
|---|---|---|
| 1 | Kryterium „M-abs − M ≥ +20 pp na zadaniach straty” spełniłaby **każda** zmiana bloku. Zadania straty wybrano dlatego, że blok M wypada na nich źle; w K1 losowe ślady S dają tam 41% wobec 11% dla M, a neutralna proza P 60%. | Punktem odniesienia jest blok niedobrany w tej samej postaci. Mierzony jest efekt swoisty doboru: M − S (postać surowa) i M-abs − S-abs (postać abstrakcyjna). Dochodzi ramię S. |
| 2 | Wynik NIGHT-2 dla maskowania potraktowałem tylko zbiorczo (14 wobec 22). Na poziomie grup jest on wprost niekorzystny dla hipotezy (sekcja 2). | Dowody wstępne są wpisane, a nowa reguła różni się od M2 w nazwanych punktach (sekcja 5). |
| 3 | 21 zadań straty przy równej liczbie bloków daje za małą precyzję (rozstrzygnięcie w 61% przy skrajnych scenariuszach). | 9 bloków dla zadań straty, 4 dla zadań zysku (sekcja 9). |

Dodatkowo: 30 „pozostałych” zadań z pierwotnej propozycji usunięto. Nie służyły żadnemu kontrastowi, a kosztowały około 30% budżetu.

---

## 2. Dowody wstępne (dane istniejące, bez nowych wywołań)

Źródło: `prior\prior_evidence.out`.

**2.1 Powtarzalność grup.** Grupy zdefiniowane wynikiem NIGHT-2 (temperatura 0), odsetki z bloków próbkowanych K1 (dane niezależne od definicji):

| Grupa | n | N | P | X | S | M |
|---|---|---|---|---|---|---|
| G: M rozwiązało, N nie | 33 | 17,2 | 24,2 | 29,3 | 38,4 | 75,8 |
| L: N rozwiązało, M nie | 21 | 77,8 | 60,3 | 60,3 | 41,3 | 11,1 |

Efekt swoisty doboru M − S: +37 pp [24; 51] w G i −30 pp [−47; −14] w L.

**2.2 Szkoda w L ma trzy warstwy.** Sama obecność tekstu: −18 pp (N → P). Ślady z domeny zamiast prozy: −19 pp (P → S). Dobór: −30 pp (S → M). Abstrakcja może dotyczyć najwyżej trzeciej warstwy. Poziom N (78%) jest dla bloku pamięci w L praktycznie nieosiągalny.

**2.3 Maskowanie w NIGHT-2 (etap E1, 60 zadań treningowych, jeden przebieg przy temperaturze 0).**

| Zadania E1 | n | M2 rozwiązało | M1 rozwiązało | K1 próbkowane: N / S / M |
|---|---|---|---|---|
| R+ rozwiązało, N nie | 11 | 4 | 5 | 18 / 48 / 79 |
| N rozwiązało, R+ nie | 9 | 2 | 2 | 82 / 37 / 7 |

- Na zadaniach zysku ślady z zamaskowanymi wartościami straciły większość pomocy (4 z 11 przy poziomie M około 79%).
- Na zadaniach straty nie przywróciły wyniku (2 z 9; poziom losowych śladów to 37%, poziom N 82%).
- To pojedyncze losowania na 9 i 11 zadaniach, więc dowód jest słaby. Kierunek jest jednak niekorzystny dla hipotezy, że usunięcie wartości usuwa szkodę i zachowuje pomoc.
- M2 miało wady wykonania, które mogły same zaszkodzić (sekcja 5): model wypisał znacznik `<...>` jako wartość w 9 z 60 epizodów.

**Ocena przed eksperymentem:** najbardziej prawdopodobny wynik to „abstrakcja niszczy także pomoc”. Eksperyment jest wart wykonania jako próba obalenia, nie jako oczekiwane potwierdzenie.

---

## 3. Hipotezy

Oznaczenia: λ_G = jaka część swoistej pomocy doboru zostaje po abstrakcji (w grupie G); λ_L = jaka część swoistej szkody doboru zostaje po abstrakcji (w grupie L).

| Hipoteza | λ_G | λ_L | Znaczenie |
|---|---|---|---|
| **H_D** (testowana): szkodę niosą wartości, pomoc niesie struktura | > 0,5 | < 0,5 | abstrakcja jest obiecującą reprezentacją |
| H_W: wszystko, co swoiste, siedzi w konkretnych wartościach | < 0,5 | < 0,5 | pamięć działa jako prawie-kopia; abstrakcja usuwa także korzyść |
| H_S: pomoc i szkodę niesie struktura (funkcje, kolejność) | > 0,5 | > 0,5 | wartości nie są mechanizmem; kopiowanie wartości to objaw, nie przyczyna |
| H_Z: abstrakcja zachowuje szkodę, a niszczy pomoc | < 0,5 | > 0,5 | najgorszy przypadek |

Dowolna zmiana bloku, która osłabia swoisty efekt jednakowo w obie strony, daje λ_G = λ_L. Dlatego **tylko wynik niesymetryczny (λ_G > 0,5 i λ_L < 0,5) popiera H_D**; nie da się go uzyskać samym „rozmyciem” bloku.

---

## 4. Ramiona

Wszystkie bloki mają ten sam nagłówek co w K1, bajt w bajt, bez dodatkowych zdań. Blok trafia przed prośbą tury i znika z historii po turze (jak w K1; `run_episode_x` bez zmian).

| Ramię | Treść | Po co |
|---|---|---|
| **N** | brak bloku | Poziom bez pamięci; definicja szkody i korzyści praktycznej. |
| **P** | neutralna proza K1, długość dopasowana do bloku **M-abs** tej tury | Blok bez treści: górna granica tego, co da się odzyskać w L, i dolna granica w G. |
| **M** | dobrane ślady surowe (plany R+ z K1, bez zmian) | Ponowny pomiar efektu, który ma być rozłożony. |
| **S** | losowe ślady z domeny, surowe (reguła K1, nowe losowania) | Odniesienie dla efektu swoistego doboru w postaci surowej. Bez tego ramienia zmiana M → M-abs miesza usunięcie wartości z samą wymianą bloku. |
| **M-abs** | te same ślady co M, po abstrakcji (sekcja 5) | Manipulacja. |
| **S-abs** | te same ślady co S w danym bloku, po abstrakcji | Odniesienie dla efektu swoistego w postaci abstrakcyjnej; kontrola długości i formy. |

Układ jest czynnikowy 2 × 2 (dobór × postać) z dwoma poziomami odniesienia (N, P). M i M-abs mają identyczne identyfikatory śladów; S i S-abs także.

Ramię S nie było na liście właściciela. Jest konieczne dla poprawnego kontrastu (wada 1 w sekcji 1). Ramię P ma najmniejszą wartość dla kontrastów głównych; wariant bez P opisuje sekcja 11.

Ramię X (ślady z obcej domeny) pominięto: w K1 zachowywało się jak P w obu grupach.

---

## 5. Abstrakcja wspomnienia

### 5.1 Reguła (deterministyczna, bez modelu)

Wejście: wiersz puli (prośba, kroki `wywołanie -> wynik`, etykieta) i dokumentacja funkcji BFCL. Żadnych odpowiedzi wzorcowych, żadnych próśb zadań testowych.

1. **Nazwy funkcji, kolejność kroków i nazwy parametrów zostają** bez zmian.
2. **Wartość argumentu zostaje dosłownie**, gdy jest:
   - wartością logiczną, albo
   - literałem wymienionym w opisie tego parametru w dokumentacji funkcji (całe słowo, z rozróżnieniem wielkości liter) **i** nie występuje jako całe słowo, z rozróżnieniem wielkości liter, w prośbie tego śladu.
   Pierwszy warunek zachowuje słownik API (`'START'`, lista drzwi, `pedalPosition=1`, `mode='l'`). Drugi usuwa wartości, które w tamtym zadaniu wybrał użytkownik (klasa podróży, miasto), nawet jeśli dokumentacja je wymienia.
3. **Każda inna wartość znika.** Parametr zostaje jako sama nazwa: `book_flight(access_token, card_id, travel_date, travel_from, travel_to, travel_class)`.
4. **Pochodzenie:** jeśli usunięta wartość występuje w wyniku wcześniejszego kroku tego samego śladu, po wywołaniu dopisuje się uwagę `[booking_id: from the result of book_flight above]`. Uwaga stoi poza nawiasem wywołania.
5. **Wynik udany:** tylko nazwy pól najwyższego poziomu: `-> returns booking_id, transaction_id`. Wartości znikają.
6. **Wynik z błędem:** komunikat zostaje; wartości usunięte w punkcie 3 są w nim zastępowane przez `[...]`.
7. **Prośba śladu:** wartości usunięte w punkcie 3 są w tekście zastępowane przez `[nazwa_parametru]`. Reszta tekstu bez zmian.
8. **Kontrola szczelności:** żadna usunięta wartość o długości co najmniej 3 znaków nie może wystąpić nigdzie w gotowym bloku. Naruszenie zatrzymuje przygotowanie.

Przykład (ślad TRAVEL z K1):

```
surowy:
[1] Request: ... Can you purchase comprehensive travel insurance for $120, using the same credit card ...
    Steps:
      purchase_insurance(access_token='abc123xyz', insurance_type='comprehensive', insurance_cost=120.0, booking_id='3426812', card_id='id15583') -> {"insurance_id": "498276044", "insurance_status": true}
    Outcome: PASSED

po abstrakcji:
[1] Request: ... Can you purchase [insurance_type] travel insurance for $[insurance_cost], using the same credit card ...
    Steps:
      purchase_insurance(access_token, insurance_type, insurance_cost, booking_id, card_id) -> returns insurance_id, insurance_status
    Outcome: PASSED
```

Przykład (ślad VC): `startEngine(ignitionMode='START') -> error: All doors must be locked ...`, `lockDoors(unlock=False, door=['driver', 'passenger', 'rear_left', 'rear_right']) -> returns lockStatus, remainingUnlockedDoors`, `pressBrakePedal(pedalPosition=1) -> returns ...`, `fillFuelTank(fuelAmount) -> returns fuelLevel`.

### 5.2 Co zostaje, co znika

| Zostaje | Znika |
|---|---|
| które funkcje, w jakiej kolejności, z jakimi parametrami | identyfikatory, tokeny, numery kart i rezerwacji |
| stałe procedury z dokumentacji (tryb zapłonu, lista drzwi, pozycja pedału) | kwoty, daty, nazwy plików i katalogów, nazwiska |
| warunki z komunikatów błędów („najpierw zamknij drzwi”) | wartości wybrane przez użytkownika w tamtym zadaniu |
| to, że wartość pochodzi z wyniku wcześniejszego kroku | wartości wyników, w tym fakty o środowisku (kod pocztowy miasta, kod lotniska) |
| sens prośby i etykieta wyniku | |

Zabezpieczenia przed utratą istotnych warunków działania: punkt 2 (słownik API), punkt 4 (pochodzenie), punkt 6 (komunikaty błędów). Świadomie tracone są fakty o środowisku zawarte w wynikach. Jeśli pomoc pamięci pochodzi z takich faktów, eksperyment pokaże to jako utratę pomocy (H_W), bez rozróżnienia między „prawie-kopią” a „faktem o środowisku”.

Wykonalność na 114 śladach puli (wariant bez drugiego warunku z punktu 2; `prior_evidence.out`): zachowane wartości to 16% w GFS, 67% w VC, 14% w TRAVEL. Szacowana długość bloku po abstrakcji: około 55–65% bloku surowego (z udziału znaków; do pomiaru w etapie T).

Przed zamrożeniem wykonawca generuje **tabelę decyzji reguły dla wszystkich 584 wartości** w puli (zostaje / znika / uwaga o pochodzeniu). Tabela jest zatwierdzana przez właściciela i audytora. Po obejrzeniu jakichkolwiek wyników modelu reguły nie wolno zmieniać.

### 5.3 Różnice względem maskowania M2 z NIGHT-2

Kod M2: `aamr_night2.py`, funkcje `classify`, `mask_rows`, `masked_block` (wiersze 282–417).

| Cecha | M2 (NIGHT-2) | M-abs (ten projekt) |
|---|---|---|
| Słownik API | maskowany, gdy słowo wystąpiło w prośbie bez względu na wielkość liter: `startEngine(ignitionMode=<ignitionMode>)`, `activateParkingBrake(mode=<mode>)`, lista drzwi jako cztery znaczniki | zachowany (punkt 2) |
| Znacznik w miejscu wartości | `card_id=<card_id>`, `booking_id=<from an earlier result>`; model skopiował znacznik w 9 z 60 epizodów | brak czegokolwiek w miejscu wartości; pochodzenie jako uwaga poza wywołaniem |
| Prośba śladu | znaczniki wstawiane także w miejsce słów języka („proceed to `<ignitionMode>` the engine”) | zastępowane tylko wartości usunięte z argumentów |
| Nagłówek | dodatkowe zdanie instrukcji, którego nie miały inne ramiona | identyczny we wszystkich ramionach |
| Wartości nieznalezione w prośbie ani wynikach | zostawały (np. `cardholder_name='Michael Smith'`, `expiration_date='12/2028'`) | znikają |
| Pomiar | jeden przebieg, temperatura 0, 60 zadań treningowych, bez odniesienia dla wymiany bloku | reżim próbkowany, 4–9 bloków, odniesienia S i S-abs, zadania o znanym efekcie |

M-abs należy do tej samej rodziny co M2. Jeśli wynik będzie negatywny mimo usunięcia tych wad, będzie to mocniejszy dowód przeciw H_D niż wynik M2.

---

## 6. Zadania

- **G:** 33 zadania, na których w NIGHT-2 ramię pamięci rozwiązało zadanie, a N nie (22 testowe, 11 treningowych; GFS 13, VC 11, TRAVEL 9).
- **L:** 21 zadań, na których N rozwiązało, a ramię pamięci nie (12 testowych, 9 treningowych; TRAVEL 11, GFS 5, VC 5).
- Listy identyfikatorów: `prior\prior_evidence.out`. Definicja używa wyłącznie NIGHT-2. K1 służy tylko do planu mocy, więc jego liczby dla tych grup są nieobciążone.
- TradingBot (100–149) pozostaje nietknięty.

---

## 7. Przebieg i kontrole

### 7.1 Reżim i bloki

- Model, skrót, opcje próbkowania i harness jak w blokach próbkowanych K1: `qwen2.5:14b-instruct`, temperatura 0,7, top_p 0,8, top_k 20, `num_ctx` 8192, `num_predict` 512, najwyżej 8 kroków na turę.
- **9 bloków próbkowanych**, ziarna 8001–8009 (nieużywane wcześniej). Zadania L biorą udział we wszystkich 9, zadania G w blokach 1–4.
- W bloku zadanie przechodzi przez wszystkie 6 ramion.
- Bloku przy temperaturze 0 nie ma: pojedynczy przebieg jest jednym losowaniem (audyt K1, sekcja 2.5).

### 7.2 Kolejność ramion

Kwadrat łaciński 6 × 6 zrównoważony ze względu na sąsiedztwo (Williamsa). Wiersz kwadratu dla zadania wyznacza zamrożona permutacja zadań; w kolejnym bloku wiersz przesuwa się o jeden. Każde ramię zajmuje każdą pozycję jednakowo często w obrębie grupy (z dokładnością do reszty z dzielenia). Kolejność zadań w bloku losowana z ziarna bloku.

### 7.3 Ziarna i niedeterminizm

- Wspólne ziarno wszystkich ramion w bloku, jak w K1 (audyt: brak wpływu na niezgodność między ramionami).
- Losowania S (i przez to S-abs) oraz bloki P: osobna instancja na blok, ziarna z identyfikatora (zadanie, tura, blok).
- Wszystkie wnioski opierają się na kontrastach w obrębie tego samego bloku i zadania. Niedeterminizm stosu jest częścią szumu próbkowania i wchodzi do przedziałów.
- **Kontrola pomostowa (opisowa):** odsetki N, M, S w G i L obok wartości K1. Wersja Ollamy i skrót modelu zapisane; inna wersja niż w K1 jest odnotowana jako zastrzeżenie, nie unieważnia kontrastów wewnętrznych.

### 7.4 Długość promptów

- M-abs i S-abs są krótsze od M i S z konstrukcji. Efekt samej długości i formy mierzy para S-abs − S; kontrasty główne go odejmują.
- S: losowanie z dopasowaniem długości do bloku M tury, reguła K1 (|ln r| ≤ ln 1,2). S-abs powstaje z tych samych śladów, więc jego długość nie jest dopasowywana osobno.
- P: długość z `c_d` × długość treści bloku M-abs, budowa jak w K1. Etap T mierzy tokeny na znak bloków abstrakcyjnych.
- **Kryterium równowagi:** średnia nierównowaga tokenów M-abs wobec S-abs oraz M wobec S w granicach ±5% w każdej grupie (jak B1 w K1), liczona na zadanie.
- Niespełnienie: zastrzeżenie „długość” przy odpowiednim kontraście i analiza wrażliwości na podzbiorze zadań z nierównowagą do ±10%. Bez reguły zmieniającej stan (słabość reguły LEN z K1: audyt, sekcja 2.4).

### 7.5 Przecieki

Kontrole K1 L1–L10 bez zmian (hak audytu, `BfclK1`, pochodzenie puli i planów, zamrożenie bodźców skrótami). Dodatkowo:

| # | Kontrola | Warunek zatrzymania |
|---|---|---|
| LA1 | Proces abstrakcji | odczyt czegokolwiek poza pulami K1 i 7 plikami dokumentacji funkcji |
| LA2 | Szczelność bloku | usunięta wartość (≥ 3 znaki) obecna w bloku M-abs lub S-abs |
| LA3 | Tożsamość śladów | identyfikatory śladów M-abs różne od M, albo S-abs różne od S w tym samym bloku |
| LA4 | Nagłówek | pierwsza linia dowolnego bloku różna od nagłówka K1 |
| LA5 | Ślepota przebiegu | dziennik postępu wypisuje wyniki albo liczniki na ramię; analiza przed zamknięciem danych |

Jawne ograniczenie: wybór zadań korzysta z wyników NIGHT-2, czyli pośrednio z odpowiedzi wzorcowych. To jest powód, dla którego wynik nie jest dowodem korzyści (sekcja 0).

Miara opisowa po przebiegu: udział linii identycznych z wywołaniem wzorcowym (L9) dla wszystkich czterech ramion ze śladami.

### 7.6 Kontrole manipulacji (po przebiegu, przed odczytem kontrastów)

- **MC1, kopiowanie znaczników:** odsetek epizodów M-abs i S-abs, w których model wpisał jako wartość argumentu nazwę parametru w nawiasie kwadratowym, samą nazwę parametru albo fragment uwagi o pochodzeniu. Powyżej 5% epizodów: stan „MANIPULACJA NIEUDANA”, bez wniosków o mechanizmie.
- **MC2, kontrola dodatnia:** nadwyżka użycia wartości obecnych tylko w bloku w ramieniu M wobec poziomu przypadkowego (N względem bloku M) musi się powtórzyć (dolna granica 95% > 0). Brak: zastrzeżenie, że zjawisko kopiowania nie wystąpiło w tym przebiegu.
- **MC3:** ta sama miara dla M-abs względem wartości surowego bloku M powinna być na poziomie przypadkowym. Raportowana.

---

## 8. Estymandy, kontrasty i reguły decyzji (do zamrożenia)

### 8.1 Miara

`Y(i,a,r)` = 1, gdy zadanie `i` rozwiązane w ramieniu `a` w bloku `r`; limit kroków, przepełnienie kontekstu i nieprawidłowe wyjście liczone jako 0 (jak K1). Braki techniczne jak w K1 (7.2): blok zadania wchodzi do analizy tylko z kompletem sześciu ramion.

### 8.2 Estymand

Populacja skończona: te 33 i te 21 zadań, zamrożone bodźce; losowe jest tylko próbkowanie modelu. Wnioski nie dotyczą innych zadań.

Dla zadania `i` i bloku `r`:
- efekt swoisty surowy: `s(i,r) = Y(i,M,r) − Y(i,S,r)`;
- efekt swoisty po abstrakcji: `a(i,r) = Y(i,M-abs,r) − Y(i,S-abs,r)`;
- kontrast: `c(i,r) = a(i,r) − ½·s(i,r)`.

**Kontrasty główne:** `T_G` = średnia `c` po zadaniach G; `T_L` = średnia `c` po zadaniach L.
- `T_G > 0` znaczy: po abstrakcji zostaje ponad połowa swoistej pomocy (λ_G > 0,5).
- `T_L > 0` znaczy: po abstrakcji zostaje mniej niż połowa swoistej szkody (λ_L < 0,5).

Próg ½ jest ustalony z góry i taki sam w obu grupach.

### 8.3 Przedziały

- **Główne:** przedział dwustronny 95% dla populacji skończonej. Wariancja: dla każdego zadania wariancja `c(i,r)` między blokami, podzielona przez liczbę bloków zadania; suma po zadaniach podzielona przez n². Kwantyl t z liczbą stopni swobody równą sumie (bloki − 1) po zadaniach.
- **Wrażliwość (obowiązkowa, obok):** przedział t 95% po zadaniach, jak w K1. Rozbieżność decyzji między oboma przedziałami raport odnotowuje zdaniem „wynik nie przenosi się poza te zadania”.
- **Wielokrotne porównania:** rodzina główna to dwa kontrasty. Poparcie wymaga obu naraz, więc błąd fałszywego poparcia nie przekracza 2,5%. Obalenie następuje przez którykolwiek z dwóch, więc łączny błąd fałszywego obalenia nie przekracza 5%. Wszystko poza rodziną główną jest opisowe, z przedziałami 95% bez korekty.

### 8.4 Warunek wstępny

Efekty, które mają być rozłożone, muszą wystąpić w tym przebiegu: dolna granica średniej `s` w G powyżej 0 i górna granica średniej `s` w L poniżej 0. W przeciwnym razie stan **NIEWAŻNY** dla danej grupy („efekt swoisty nie powtórzył się”), bez wniosków o mechanizmie w tej grupie.

### 8.5 Stany (odczyt generuje kod)

| Stan | Warunek | Zdanie |
|---|---|---|
| **POPARCIE H_D** | dolne granice `T_G` i `T_L` powyżej 0 | „Na tych zadaniach usunięcie wartości usuwa większość swoistej szkody i zachowuje większość swoistej pomocy.” |
| **OBALENIE: szkoda nie zależy od wartości** | górna granica `T_L` poniżej 0 | „Ślady bez wartości zachowują większość swoistej szkody. Kopiowanie wartości nie jest jej główną przyczyną.” |
| **OBALENIE: pomoc wymaga wartości** | górna granica `T_G` poniżej 0 | „Ślady bez wartości tracą większość swoistej pomocy. Abstrakcja w tej postaci nie zachowuje korzyści pamięci.” |
| **CZĘŚCIOWE** | dokładnie jeden z kontrastów rozstrzygnięty na korzyść H_D, drugi nierozstrzygnięty | zdanie tylko o rozstrzygniętej połowie |
| **NIEROZSTRZYGNIĘTE** | pozostałe przypadki | „Przedziały obejmują próg połowy.” |
| NIEWAŻNY / MANIPULACJA NIEUDANA | 8.4, 7.6, kontrole przecieków, braki jak w K1 | bez wniosków |

Oba obalenia mogą wystąpić razem.

**Kryterium sukcesu hipotezy:** stan POPARCIE H_D.
**Kryterium obalenia hipotezy właściciela** (szkoda przez kopiowanie wartości): stan „szkoda nie zależy od wartości”.
**Kryterium obalenia abstrakcji jako naprawy:** którykolwiek stan OBALENIE.

Uwaga interpretacyjna zapisana z góry: samo `T_L > 0` nie dowodzi kopiowania. Ten sam wynik daje każda zmiana, po której blok przestaje pasować do zadania. Dopiero łącznie z `T_G > 0` wynik wskazuje na wartości.

### 8.6 Analiza korzyści i szkód (opisowa)

1. **Drabina w każdej grupie**, odsetki i różnice 95%: N → P → S-abs → M-abs oraz N → P → S → M. Pokazuje, ile szkody i pomocy pochodzi z samej obecności tekstu, ze śladów domeny i z doboru, w obu postaciach.
2. **Względem braku pamięci:** M-abs − N i M − N w G i w L osobno.
3. **Bilans na 54 zadaniach:** średnia M-abs − M i M-abs − N, z etykietą „bilans na zadaniach wybranych; nie jest oszacowaniem dla benchmarku”.
4. **Efekt postaci na ślady losowe:** S-abs − S w obu grupach.
5. **Znaczniki mechanizmu** na poziomie tur, z poziomem przypadkowym z ramienia N: użycie wartości z bloku, użycie funkcji spoza wzorca obecnych w bloku, kategorie nieudanych tur, zaliczenie tury 0.
6. **Zgodność podgrup:** `T_G` i `T_L` osobno dla zadań testowych i treningowych oraz dla domen. Bez wniosków; tylko informacja, czy kierunek jest spójny.
7. Wskaźnik niesymetrii λ_G − λ_L z przedziałem bootstrapowym po zadaniach.

Raport nie zawiera zdań, że abstrakcja poprawia albo pogarsza pamięć na benchmarku, ani zdań o braku efektu przy stanie NIEROZSTRZYGNIĘTE. Kod sprawdza to wyrażeniami regularnymi, jak w K1.

---

## 9. Plan mocy

Symulacja `power\expA_power_sim.py` (3 000 prób na komórkę). Prawdopodobieństwa zadań z K1, ściągnięte do średniej grupy tak, by średnie grup równały się nieobciążonym wartościom K1. Założenie: S-abs zachowuje się jak S; M-abs = S-abs + λ · (M − S).

Plan: **4 bloki dla G, 9 bloków dla L, 6 ramion.**

| Prawdziwy stan | POPARCIE | OBALENIE: szkoda zostaje | OBALENIE: pomoc znika |
|---|---|---|---|
| H_D (λ_G = 1, λ_L = 0) | 77% | 0% | 0% |
| H_D słabsze (0,75; 0,25) | 12% | 0% | 0% |
| H_W: niszczy oba (0; 0) | 0% | 0% | 88% |
| H_S: struktura niesie oba (1; 1) | 0% | 93% | 0% |
| symetryczne osłabienie (0,5; 0,5) | 0% | 3% (błąd) | 3% (błąd) |
| H_Z (0; 1) | 0% | 93% | 87% |

- Połowa przedziału: około 11–12 pp w G i 9–10 pp w L, przy odległości scenariuszy skrajnych od progu 19 i 15 pp.
- Wrażliwość na założenia: POPARCIE przy H_D od 68% do 85%; przy przesunięciu S-abs względem S o ±10 pp od 74% do 80%.
- Przedział po zadaniach (wrażliwość) daje moc niższą o 5–13 pp (POPARCIE przy H_D: 64%).
- Warunek wstępny (8.4) spełniony w 100% symulacji.
- Przy równych 5 blokach grupa L byłaby rozstrzygana tylko w 61–72% (dlatego 9 bloków dla L).

**Ograniczenia interpretacji:**
- Przy efektach pośrednich (około 25–75% zachowanego efektu) najbardziej prawdopodobny jest stan NIEROZSTRZYGNIĘTE.
- Moc policzono przy założeniu, że efekty K1 (+37 i −30 pp) powtórzą się w pełni.
- Stany dotyczą tej reguły abstrakcji, tej puli, tego modelu, tych 54 zadań.

---

## 10. Oddzielenie od testu generalizacji i zabezpieczenia przed przeuczeniem

**EXP-A nie zawiera testu generalizacji i nie udaje, że go zawiera.** Powody:

1. Pozostałe 94 zadania nie są niezależnym zbiorem: to dopełnienie wyboru, a wszystkie 148 zadań były już wielokrotnie używane (pilot, S1, NIGHT-1, NIGHT-2, K1).
2. Inne kategorie wieloturowe BFCL (`miss_func`, `miss_param`, `long_context`) to warianty tych samych 200 scenariuszy: te same klasy w 200 z 200 zadań, identyczna pierwsza prośba w 117–195 z 200. Nie są niezależne.
3. Jedyny nietknięty zbiór to TradingBot (50 zadań). Wymagałby budowy puli i dałby około 30 zadań testowych, czyli przedział rzędu ±15 pp. To za mało, by coś potwierdzić, a rezerwa zostałaby zużyta. **Rekomendacja: nie używać rezerwy w EXP-A.**
4. Test na całych 148 zadaniach nie wykryłby nawet najlepszego możliwego wyniku (około +4 pp wobec M).

Zabezpieczenia stosowane zamiast zbioru walidacyjnego:

| Zabezpieczenie | Przed czym chroni |
|---|---|
| Reguła abstrakcji deterministyczna, zbudowana tylko z puli i dokumentacji funkcji, zamrożona skrótem przed pierwszym wywołaniem; tabela decyzji dla 584 wartości zatwierdzona z góry | dopasowywanie reguły do znanych przypadków porażek |
| Zakaz przebiegów próbnych na zadaniach G i L przed zamrożeniem; etap T tylko techniczny, bez zapisu wyników | strojenie po wynikach |
| Grupy zdefiniowane wyłącznie przez NIGHT-2; K1 tylko do planu mocy | wybór zadań pod oczekiwany wynik |
| Punkt odniesienia S / S-abs i wymóg wyniku niesymetrycznego | artefakt wyboru zadań (każda zmiana bloku „pomaga” w L) |
| Progi, stany i zdania odczytu w kodzie, zamrożone przed startem | odczyt dopasowany do danych |
| Zdanie obowiązkowe o zakresie (sekcja 0) | przedstawianie efektu na zadaniach wybranych jako poprawy benchmarku |

**Etap 2 (osobny protokół, osobna zgoda, tylko po stanie POPARCIE):** pomiar korzyści wymaga nowych zadań i większego instrumentu, czyli propozycji B z audytu K1 (jednostką jest tura, ponad 500 jednostek) albo innego zbioru z co najmniej kilkuset niezależnymi zadaniami. Przy stanie OBALENIE etap 2 dla abstrakcji nie ma uzasadnienia.

---

## 11. Budżet i czas

Zmierzone w K1: 9,3–10,0 wywołania na epizod (średnio około 9,6), 25 796 wywołań w około 10 godzin, czyli 1,40 s na wywołanie.

| Wariant | Epizody | Wywołania (9,5 na epizod) | Czas |
|---|---|---|---|
| **Rekomendowany:** 6 ramion, G 4 bloki, L 9 bloków | 1 926 | około 18 300 | około 7,1–7,3 h |
| Bez P: 5 ramion, G 4, L 9 | 1 605 | około 15 250 | około 6,0 h |
| Minimalny: 5 ramion, G 4, L 8 | 1 500 | około 14 250 | około 5,6 h |
| Odrzucony: 6 ramion, po 5 bloków | 1 620 | około 15 400 | 6,0 h, ale L rozstrzygane w 61–72% |

- Etap T (techniczny, tokeny na znak bloków abstrakcyjnych, `c_d` dla P): do 300 wywołań.
- **Limit twardy: 22 000 wywołań.** Bramki budżetu jak w K1, zależne wyłącznie od liczby wywołań: przed każdym blokiem prognoza z zapasem 10%.
- Kolejność bloków 1–9; bloki 1–4 zawierają G i L, bloki 5–9 tylko L. Przerwanie przez limit po bloku 6 lub później zostawia analizę L z mniejszą liczbą bloków; reguła minimalna: co najmniej 4 bloki G i 6 bloków L, inaczej NIEWAŻNY.
- Koszt: 0 USD, wyłącznie lokalna Ollama.

Wartość na jednostkę kosztu: wariant rekomendowany kosztuje 71% wywołań K1 i daje rozstrzygnięcie w 77–93% scenariuszy skrajnych. Ramię P to 16% budżetu i nie wchodzi do kontrastów głównych; jego usunięcie nie zmienia mocy, ale odbiera odniesienie „blok bez treści” w drabinie szkody.

---

## 12. Największe ryzyka metodologiczne

1. **Jedna operacjonalizacja.** Wynik negatywny obala tę regułę, nie każdą abstrakcję. Kontrole MC1–MC3 ograniczają ryzyko, że reguła sama psuje blok, ale go nie usuwają.
2. **Usunięcie wyników usuwa też fakty o środowisku.** Stan „pomoc wymaga wartości” nie rozróżni prawie-kopii od użytecznych faktów (kody lotnisk, kody pocztowe).
3. **Mało zadań straty (21) i próg połowy.** Efekty pośrednie pozostaną nierozstrzygnięte.
4. **Zadania wybrane.** Wszystkie liczby dotyczą 54 zadań; poprawność kontrastu zależy od tego, czy S-abs jest właściwym odniesieniem dla „bloku niedobranego”.
5. **Długość.** Bloki abstrakcyjne są krótsze. Para S-abs − S odejmuje efekt średni, ale nie wyklucza interakcji długości z doborem.
6. **Wnioskowanie dla populacji skończonej.** Jest właściwe dla celowo wybranych zadań, lecz daje węższe przedziały niż analiza po zadaniach; raport podaje oba.
7. **Kolejne użycie tych samych zadań i śladów** (piąte lub szóste). Zamrożony protokół ogranicza swobodę analityka, nie cofa wcześniejszej ekspozycji.
8. **Niedeterminizm i możliwa zmiana stosu** między K1 a nowym przebiegiem. Kontrasty są wewnętrzne; kontrola pomostowa pokaże rozjazd.
9. **Nierówna liczba bloków** w grupach komplikuje wykonawcę i reguły braków.

---

## 13. Decyzje właściciela (otwarte)

| # | Decyzja | Rekomendacja |
|---|---|---|
| DA1 | Zestaw ramion | 6: N, P, M, S, M-abs, S-abs (S jest dodatkiem do listy właściciela) |
| DA2 | Bloki | G 4, L 9; ziarna 8001–8009 |
| DA3 | Próg zachowanego efektu | ½ w obu grupach |
| DA4 | Przedział główny | populacja skończona 95%; po zadaniach jako obowiązkowa wrażliwość |
| DA5 | Reguła abstrakcji | sekcja 5.1; w szczególności punkt 2 (drugi warunek) i punkt 5 (wyniki jako same nazwy pól) |
| DA6 | Próg MC1 | 5% epizodów |
| DA7 | Limit twardy | 22 000 wywołań |
| DA8 | Rezerwa TradingBot | nie używać |
| DA9 | Wykonawca | osobny katalog poza repozytoriami, wzorzec K1, start przez koordynatora dopiero po osobnej zgodzie |

---

## 14. Pytania do audytora (Opus)

1. Czy kontrast `c = a − ½·s` i wymóg wyniku niesymetrycznego rzeczywiście wykluczają artefakt wyboru zadań? Czy istnieje mechanizm inny niż H_D, który daje `T_G > 0` i `T_L > 0`?
2. Czy S-abs jest właściwym odniesieniem, skoro jego długość nie jest dopasowywana osobno do M-abs?
3. Czy reguła 5.1 jest jednoznaczna i wykonalna bez decyzji uznaniowych? Które wartości w tabeli decyzji budzą wątpliwości?
4. Czy wnioskowanie dla populacji skończonej jest uzasadnione jako główne przy tym zakresie wniosków?
5. Czy próg ½ i poziomy 95% są rozsądne przy 21 zadaniach straty, czy lepszy byłby inny kompromis między mocą a ostrością tezy?
6. Czy symulacja mocy zawyża moc (założenie pełnego powtórzenia efektów K1, niezależność bloków)?
7. Czy brak ramienia rozróżniającego „prawie-kopię” od „faktów o środowisku” jest dopuszczalny w pierwszym przebiegu?
8. Czy wariant bez P byłby lepszym użyciem budżetu?
