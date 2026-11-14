# AAMR EXP-A (EXP-ABS-0): specyfikacja, wersja 0.2 — PROJEKT DO ZATWIERDZENIA

2026-11-14. Redakcja v0.2: Claude (Opus 5.5), na podstawie v0.1 (Fable 5.2) i audytu `[machine-local path omitted]`.
**Status: projekt. NIE zamrożony, NIE uruchomiony.** Kod bodźców i analizy jest gotowy i przetestowany (sekcja 14). Wykonawcy epizodów (runnera) nie zbudowano. Zamrożenie, budowa wykonawcy i start wymagają osobnych zgód właściciela.

v0.1 (`[machine-local path omitted]\`) pozostaje bez zmian. Wszystko, czego ta wersja nie zmienia, obowiązuje w brzmieniu v0.1: zadania, pula, plany M, nagłówek, harness, model i opcje próbkowania. Żaden zamrożony artefakt K1, NIGHT-1, NIGHT-2 ani koordynatora nie został zmieniony. `sealed/` nie było czytane.

---

## 0. Zmiany względem v0.1

| Audyt | Zmiana w v0.2 | Sekcja |
|---|---|---|
| K1 (reguła niewykonalna) | Reguła abstrakcji P1–P8: decyzja zależna tylko od (funkcja, parametr, wartość); klasy parametrów wyznaczone mechanicznie z puli; usuwanie na poziomie bloku; pochodzenie także z wcześniejszych tur zadania źródłowego (z puli); daty w postaciach pisanych; LA2 z wyłączeniem słownika publicznego bloku. Wynik: 0 naruszeń LA2 na 1 355 blokach abstrakcyjnych (195 M-abs, 1 160 S-abs). | 5 |
| K2 (estymand) | Rodzina główna: asymetria Δ_swoiste = λ_G − λ_L oraz Δ_treści = λᴾ_G − λᴾ_L (względem P), Holm, jednostronnie 2,5%. Próg ½ przechodzi do klasyfikacji wielkości (drugorzędnie). | 3, 8 |
| K3 (etykiety) | Nowe stany i zdania. Obalenie hipotezy właściciela wymaga ujemnej asymetrii na obu poziomach. | 8.5 |
| K4 (długość) | Wspólne dopasowanie S do długości surowej (tokeny, ln 1,2) i abstrakcyjnej (znaki, ln 1,1) bloku M. Wynik: 97% tur dopasowanych, średnia nierównowaga −0,3% do −0,6%. | 7.4 |
| K5 (dawka) | Obowiązkowa wrażliwość: Δ standaryzowane składem domen; rozbieżność → dopisek. | 8.6 |
| K6 (MC1) | Próg względny: nadwyżka nad ramieniem surowym, górna granica 95% ≤ 5 pp. | 7.6 |
| N1 | „Na tych 54 zadaniach” w każdym zdaniu stanu. | 8.5 |
| N2 | Moc podana jako zakres przy osłabieniu i korelacji. | 9 |
| N3 | P dopasowane do surowego M regułą K1, z `c_d` K1 (bez nowego etapu T dla P); budowa P bajt w bajt jak w K1 (test). | 4 |
| N4, N5 | Poprawione liczby wykonalności; zapisane, że wyniki jako same klucze były już w M2. | 5.4, 5.5 |
| N6 | Wrażliwość po zadaniach: jackknife zadań dla Δ. | 8.6 |
| N7 | Kierunki znaczników mechanizmu zapisane z góry. | 8.7 |
| N9 | Etap T mierzy wywołania na epizod ramion abstrakcyjnych. | 11 |

---

## 1. Pytanie i zakres

**Pytanie:** czy kopiowanie konkretnych wartości ze wspomnień odpowiada za **część** szkody pamięci, ponad to, co dałoby ogólne osłabienie bloku?

**Operacjonalizacja:** jeśli usunięcie wartości zdejmuje **większy odsetek szkody** (w grupie L) **niż pomocy** (w grupie G), to część szkody zależy od wartości. Ogólne osłabienie zmniejsza oba efekty w tym samym stosunku, więc nie może dać takiej asymetrii.

**Może:** rozstrzygnąć znak asymetrii na 54 zadaniach o powtarzalnym efekcie pamięci, osobno dla efektu swoistego doboru (M wobec S) i dla całego efektu treści bloku (M wobec P).

**Nie może:** wykazać poprawy na benchmarku (sekcja 10 v0.1, bez zmian); rozróżnić wartości argumentów od faktów z wyników narzędzi (abstrakcja usuwa oba; znaczniki z 8.7 dają tylko wskazówkę); obalić abstrakcji jako idei. Wynik dotyczy tej reguły.

**Zdanie obowiązkowe w każdym raporcie:** „Wynik dotyczy 54 zadań wybranych na podstawie wcześniejszych wyników NIGHT-2. Nie jest dowodem poprawy ani pogorszenia na całym benchmarku.”

---

## 2. Dowody wstępne

Jak w v0.1, sekcja 2, z dwoma uzupełnieniami z audytu (dane istniejące, zero wywołań):

1. **Kopiowanie w K1 (S1–S3, zadania G/L; wartości instancji, bez słownika API).** Epizody z wartością obecną tylko w bloku:

   | Grupa | N (przypadek) | S | M |
   |---|---|---|---|
   | L | 43% | 35% | 56% |
   | G | 14% | 14% | 28% |

   W L epizody z kopią prawie zawsze kończą się porażką: w M 1 z 35 rozwiązanych, w S 3 z 22. Porażka bez kopii też jest częsta: w M rozwiązanych 6 z 28. W G kopia nie współwystępuje z sukcesem.
2. **Kontrola dodatnia MC2 na danych K1 (kod v0.2):** nadwyżka M nad N wynosi +8,6 pp [5,4; 11,9]. Miara działa, a kopiowanie występuje.

Ocena przed eksperymentem: dowody są **niejednoznaczne**. M2 (NIGHT-2) wskazuje, że abstrakcja niszczy pomoc. Dane K1 wskazują, że szkoda współwystępuje z kopiowaniem także w losowych śladach S, a pomoc nie współwystępuje z kopiowaniem. Szkoda swoista doboru może być w dużej części niezależna od wartości.

---

## 3. Estymandy

Dla grupy g i ramion A, B niech m_g(A − B) oznacza średnią po zadaniach średnich po blokach różnicy Y(A) − Y(B).

| Symbol | Definicja | Znaczenie |
|---|---|---|
| λ_g | m_g(M-abs − S-abs) / m_g(M − S) | odsetek **swoistego** efektu doboru, który przetrwał abstrakcję |
| λᴾ_g | m_g(M-abs − P) / m_g(M − P) | odsetek **całego** efektu treści bloku (domena + dobór), który przetrwał |
| Δ_swoiste | λ_G − λ_L | > 0: abstrakcja zdjęła większy odsetek szkody swoistej niż pomocy swoistej |
| Δ_treści | λᴾ_G − λᴾ_L | > 0: to samo dla całego efektu treści; obejmuje kopiowanie z losowych śladów domeny |

Przy jednakowym osłabieniu (ten sam odsetek zachowany w G i L, na dowolnym poziomie) Δ = 0. Nieliniowość na skali logitów działa przeciw Δ > 0 (audyt, sekcja 1). Zmiana względem v0.1 polega na tym, że próg ½ nie jest już kryterium głównym; T_G i T_L z v0.1 pozostają jako klasyfikacja wielkości (8.6).

Hipotezy, w zapisie λ (swoiste) i κ (nieswoiste, S wobec P):

| Hipoteza | Przewidywanie |
|---|---|
| H_D: szkoda zależy od wartości bardziej niż pomoc | Δ_swoiste > 0 i/lub Δ_treści > 0 |
| H_0: abstrakcja osłabia wszystko jednakowo (w tym „nic nie zmienia” i „niszczy wszystko”) | Δ = 0 |
| H_Z: pomoc zależy od wartości bardziej niż szkoda | Δ < 0 |

---

## 4. Ramiona

Sześć ramion jak w v0.1: N, P, M, S, M-abs, S-abs. Nagłówek bajt w bajt jak w K1. Blok przed prośbą tury, znika z historii po turze.

| Ramię | v0.2 |
|---|---|
| M | plan R+ z K1, render bajt w bajt jak K1 (test T4) |
| M-abs | te same ślady, reguła 5 |
| S | nowe losowanie z domeny na każdy blok (klucz `EXPA|S|zadanie|tura|blok`), bez śladów zadania i bez śladów M zadania (L1, L3), bez powtórzeń w zadaniu, ze **wspólnym dopasowaniem długości** (7.4) |
| S-abs | te same ślady co S w bloku, reguła 5 |
| P | proza K1, długość dopasowana do **surowego** bloku M tury regułą K1 (`c_d` z K1 `run/c_d.json`), ziarno `(EXPA, zadanie, tura, blok)`; budowa identyczna z K1 (test T4) |
| N | brak bloku |

---

## 5. Abstrakcja (reguła v0.2; kod `code/expA_abstract.py`)

Wejście: trzy pule K1 i trzy pliki dokumentacji funkcji BFCL tych domen. Bez modelu, bez odpowiedzi wzorcowych, bez wyników.

- **P1.** Nazwy funkcji, kolejność kroków i nazwy parametrów zostają.
- **P2.** Decyzja zależy tylko od (funkcja, parametr, wartość), nie od kontekstu śladu:
  - wartość logiczna zostaje;
  - literał opisu parametru (całe słowo, z rozróżnieniem wielkości liter) zostaje, **chyba że** parametr jest „wyborem użytkownika”;
  - każda inna wartość znika.

  „Wybór użytkownika” to parametr, którego wartość prośba śladu wymienia (całe słowo, z rozróżnieniem wielkości liter) w **ponad połowie** wystąpień w puli. Wartości wewnątrz list i słowników są oceniane osobno; parametr z choćby jedną usuniętą wartością znika w całości.
- **P3.** Usunięta wartość zostawia samą nazwę parametru: `f(a, b)`.
- **P4.** Pochodzenie: wartość obecna w wyniku wcześniejszego kroku śladu dostaje `[p: from the result of f above]`. W przeciwnym razie, jeśli jest obecna w prośbie lub wyniku wcześniejszej tury tego samego zadania źródłowego **w puli**, dostaje `[p: from an earlier turn of that task]`. W pozostałych przypadkach uwagi nie ma.
- **P5.** Wynik udany pokazuje tylko nazwy pól najwyższego poziomu: `-> returns a, b`.
- **P6.** Wynik z błędem: komunikat zostaje; każda wartość usunięta **gdziekolwiek w bloku** zamienia się w `[...]` (całe słowo, bez rozróżnienia wielkości liter); obcięcie do 160 znaków jak w surowym bloku.
- **P7.** Prośby: każda wartość usunięta gdziekolwiek w bloku zamienia się w `[p]`, gdzie p to parametr jej pierwszego wystąpienia w bloku. Liczby są wyszukiwane w postaciach pisanych (1500, 1,500, 1500.0), daty w postaciach słownych (2026-10-15, October 15, 2026, 15th of October…).
- **P8 (LA2).** Żadna usunięta wartość (≥ 3 znaki; liczby ≥ 2 cyfry znaczące) nie może wystąpić w gotowym bloku (całe słowo, bez rozróżnienia wielkości liter). Wyjątek stanowi słownik publiczny bloku: nazwy funkcji, parametrów i pól wyników oraz zachowane literały. Naruszenie zatrzymuje przygotowanie.

### 5.1 Klasy parametrów (mechanicznie z puli; `stim_preview/expA_param_table.csv`, 92 parametry)

- **Słownik API (8):** `startEngine.ignitionMode` (`'START'`), `lockDoors.door`, `pressBrakePedal.pedalPosition`, `activateParkingBrake.mode`, `compute_exchange_rate.base_currency`/`target_currency`, `wc.mode`, `find.path`.
- **Wybór użytkownika z literałami w dokumentacji (3):** `get_flight_cost.travel_class`, `displayCarStatus.option`, `get_nearest_airport_by_city.location`.
- Pozostałe parametry to instancje.

### 5.2 Tabela decyzji (`stim_preview/expA_decision_table.csv`, 585 wartości)

Jest o jedną więcej niż w v0.1, bo słownik `edit_ticket.updates` rozbito na 2 wartości.

| Domena | Zostaje | Znika | W tym z uwagą o pochodzeniu |
|---|---|---|---|
| GFS | 15 | 80 | P4 łącznie: 64 z wyniku kroku, 80 z wcześniejszej tury |
| VC | 101 | 63 | |
| TRAVEL | 12 | 314 | |

### 5.3 Weryfikacja bez ręcznego przeglądu 585 wartości

1. Właściciel zatwierdza **regułę** i 92-wierszową **tabelę klas parametrów**, nie pojedyncze wartości. Wyjątki dla pojedynczych wartości są zakazane; każda zmiana musi być zmianą reguły.
2. Test T2 skanuje niezależnie każdy z 1 355 bloków abstrakcyjnych i nie znajduje przecieku. Kontrola ujemna w tym samym teście: wartość dopisana do bloku jest wykrywana (25 z 25).
3. Testy T1 sprawdzają przypadki wzorcowe: stałe VC zostają, TRAVEL traci identyfikatory i daty, uwagi o pochodzeniu są poprawne, decyzja nie zależy od kontekstu.
4. Zalecane przed zamrożeniem: przegląd 30 losowych bloków abstrakcyjnych pod kątem czytelności, bez prawa do wyjątków.

### 5.4 Co jest świadomie tracone

- Fakty o środowisku w wynikach: kody lotnisk, kody pocztowe, pojemność baku (`fillFuelTank(fuelAmount=50)`, „pełny bak = 50”).
- Format wartości: daty ISO, postać identyfikatorów.
- Przepływ danych spoza puli: 314 usuniętych wartości nie ma uwagi o pochodzeniu.
- Podmiana zwykłych słów w prośbach, gdy wartość wyboru użytkownika jest słowem języka: „crucial [travel_class] meeting”, „extra [option] in the tank”. Zdarza się to przy parametrach `travel_class`, `option` i `location` (110 znaczników w prośbach M-abs; nie każdy jest podmianą zbędną).

Wszystkie te straty przesuwają wynik w stronę „pomoc nie przetrwała”. Właśnie dlatego kryterium główne to asymetria, a nie sam spadek pomocy.

### 5.5 Stosunek do M2 (NIGHT-2)

Pod względem treści usuwanej z bloku M-abs to oczyszczona replikacja M2. Wyniki jako same klucze, usuwanie wartości z prośby i wyników były już w M2. Nowe są: brak znaczników w miejscu wartości, brak dodatkowego zdania w nagłówku, spójny słownik API, pomiar w reżimie próbkowanym z odniesieniami S, S-abs i P.

Długość bloku abstrakcyjnego: około 91% bloku surowego w obu grupach (szacunek v0.1 „55–65%” był błędny).

---

## 6. Zadania

Bez zmian: G 33, L 21, definicja wyłącznie z NIGHT-2 (`code/expA_groups.py` → `stim_preview/expA_groups.json`, same identyfikatory, bez wyników). TradingBot nietknięty.

---

## 7. Przebieg i kontrole

### 7.1 Reżim

Jak v0.1: `qwen2.5:14b-instruct` z przypiętym skrótem z K1, temperatura 0,7, top_p 0,8, top_k 20, `num_ctx` 8192, `num_predict` 512, ≤ 8 kroków na turę. 9 bloków, ziarna 8001–8009. G w blokach 1–4, L w 1–9. Razem 1 926 epizodów.

### 7.2 Kolejność

Kwadrat Williamsa 6 × 6 (każde ramię raz w wierszu i kolumnie; każda uporządkowana para sąsiadów raz). Wiersz bazowy zadania wynika z zamrożonej permutacji w grupie (`EXPA|rows|g`); w bloku b wiersz przesuwa się o b − 1. Kolejność zadań w bloku jest losowana (`EXPA|order|b`). Wszystko jest zapisane w `stim_preview/expA_plan.json`.

### 7.3 Ziarna i niedeterminizm

Jak v0.1. Wspólne ziarno ramion w bloku. Losowania S są rozłączne z K1: test T5 wymaga, by mniej niż 20% wyborów pokrywało się z K1 S1. Wersja Ollamy i skrót modelu są zapisywane. Kontrola pomostowa (N, M, S wobec K1) jest opisowa i daje ostrzeżenie, gdy odsetek N w L wypada poza przedziałem K1.

### 7.4 Długość

- S: |ln(przewidziane tokeny S / tokeny M)| ≤ ln 1,2 (reguła D12 z K1) **oraz** |ln(znaki S-abs / znaki M-abs)| ≤ ln 1,1. Do 2 000 losowań; jeśli żadne nie spełnia warunku, wybierane jest najbliższe.
- Wynik budowy: dopasowane 1 121 z 1 160 tur-bloków (97%). Średnie ln(S/M) od −0,003 do −0,006. Udział |ln| > ln 1,2 w postaci abstrakcyjnej: G 0%, L 1,3%.
- Kryterium równowagi tokenów w przebiegu jak v0.1 (±5%), z wrażliwością: regresja c na ln(M-abs/S-abs).

### 7.5 Przecieki

L1–L10 jak w K1. Dodatkowo:

| # | Kontrola | v0.2 |
|---|---|---|
| LA1 | proces bodźców czyta tylko pliki z listy `READ` | hak audytu K1 (`k1_audit_hook`) w trybie egzekwowania; test T3: odczyt pliku wyników K1 kończy proces kodem 97 |
| LA2 | P8 | 0 naruszeń; niezależny ponowny skan T2 |
| LA3 | identyfikatory M-abs = M, S-abs = S | sprawdzane przy budowie |
| LA4 | pierwsza linia = nagłówek K1 | sprawdzane przy budowie |
| LA5 | ślepota przebiegu | jak v0.1 (dotyczy wykonawcy) |
| LA6 | podział procesów | grupy z NIGHT-2 wyznacza osobny proces; proces bodźców nie widzi wyników |

### 7.6 Kontrole manipulacji (kod `expA_analysis.py`)

- **MC1:** znacznik w argumencie, czyli wartość w nawiasie kwadratowym lub ostrym, nazwa własnego parametru albo fragment uwagi o pochodzeniu. Mierzona jest nadwyżka M-abs nad M i S-abs nad S, w parach zadanie-blok. **Niepowodzenie: górna granica 95% > 5 pp** → MANIPULACJA NIEUDANA. Poziom bazowy w K1: M 3,1%, N 4,3%, S 1,9% epizodów.
- **MC2 (kontrola dodatnia):** epizody z wartością instancji obecną tylko w bloku M, nadwyżka M nad N względem bloku M tury. Wymagane: dolna granica > 0; brak → zastrzeżenie. Na K1: +8,6 pp [5,4; 11,9].
- **MC3:** ta sama miara dla M-abs względem surowego bloku M; oczekiwany poziom przypadkowy, raportowane. Nadwyżka MC3 > 0 (górna granica) daje zastrzeżenie przy każdym stanie POPARCIE.

---

## 8. Analiza (kod `code/expA_analysis.py`; ten sam kod w symulacji mocy)

### 8.1 Miara

Jak v0.1. Blok zadania wchodzi do analizy tylko z kompletem sześciu ramion (`arrays_from_records`).

### 8.2 Przedziały

Średnie to średnie po zadaniach średnich po blokach (równe wagi zadań). Wariancja populacji skończonej: Σ var_i / R_i / n². Stopnie swobody: Σ(R_i − 1). Dla λ stosowana jest metoda delta z kowariancją licznika i mianownika w zadaniu. Dla Δ: SE² = var(λ_G) + var(λ_L), kwantyl t.

### 8.3 Rodzina główna

{Δ_swoiste, Δ_treści}, testy jednostronne, α = 0,025, procedura Holma, osobno dla kierunku dodatniego i ujemnego. Kierunki są rozłączne, więc łączny błąd fałszywego stanu nie przekracza 2,5% dla poparcia i 2,5% dla obalenia.

### 8.4 Warunki wstępne

- Dla Δ_swoiste: dolna granica m_G(M − S) > 0 i górna m_L(M − S) < 0.
- Dla Δ_treści: to samo dla M − P.

Niespełniony warunek usuwa danego członka z rodziny; Holm działa wtedy na jednym teście. Brak obu daje stan NIEWAŻNY.

### 8.5 Stany i zdania (generuje kod)

| Stan | Warunek | Zdanie |
|---|---|---|
| POPARCIE_OBA | oba Δ > 0 (Holm) | „Na tych 54 zadaniach usunięcie wartości zdejmuje większą część szkody niż pomocy pamięci, zarówno w efekcie swoistym doboru, jak i w całym efekcie treści bloku.” |
| POPARCIE_SWOISTE | tylko Δ_swoiste > 0 | „…zdejmuje większą część swoistej szkody doboru niż swoistej pomocy.” |
| POPARCIE_TRESCI | tylko Δ_treści > 0 | „…w całym efekcie treści bloku; efekt swoisty doboru nierozstrzygnięty.” |
| OBALENIE | oba Δ < 0 (Holm) | „…zdejmuje mniejszą część szkody niż pomocy, w obu poziomach. Kopiowanie wartości nie wyjaśnia szkody ponad ogólne osłabienie bloku.” |
| KIERUNEK_PRZECIWNY | jeden Δ < 0, drugi nierozstrzygnięty | zdanie o jednym poziomie |
| SPRZECZNE | jeden Δ > 0, drugi < 0 | bez interpretacji |
| NIEROZSTRZYGNIETE | pozostałe | „Przedziały asymetrii obejmują zero.” |
| NIEWAŻNY / MANIPULACJA NIEUDANA | 8.4, 7.5, 7.6, minimum bloków (G ≥ 4, L ≥ 6) | bez wniosków |

- **Kryterium sukcesu H_D:** dowolny stan POPARCIE, bez zastrzeżenia MC3.
- **Kryterium obalenia hipotezy właściciela:** stan OBALENIE.

Zakazane zdania (kontrola wyrażeniami regularnymi w kodzie): o poprawie lub pogorszeniu pamięci na benchmarku oraz o braku efektu.

### 8.6 Wrażliwość (obowiązkowa, w raporcie obok)

1. **Po zadaniach:** jackknife zadań dla obu Δ. Jeśli wynik rozstrzygnięty traci istotność, dodawany jest dopisek „wynik nie przenosi się poza te zadania”.
2. **Skład domen:** Δ z wagami ujednolicającymi skład domen G i L do składu 54 zadań. Jeśli wynik traci istotność, dodawany jest dopisek „wynik zależy od składu domen”.
3. **Długość:** regresja c(i,r) na ln(M-abs/S-abs).
4. **Wielkość (dawne stany v0.1, nowe nazwy):**
   - T_G > 0: „ponad połowa swoistej pomocy przetrwała”;
   - T_G < 0: „swoista pomoc w większości nie przetrwała tej abstrakcji”;
   - T_L > 0: „ponad połowa swoistej szkody zniknęła”;
   - T_L < 0: „większość swoistej szkody doboru przetrwała usunięcie wartości”.

### 8.7 Opisowe i mechanizm (kierunki zapisane z góry)

- Drabiny N → P → S → M i N → P → S-abs → M-abs w każdej grupie; S-abs − S, M-abs − M, M-abs − N; podgrupy test/trening i domeny.
- Przy H_D oczekiwane są: (a) spadek epizodów z wartością tylko z bloku w nieudanych epizodach M-abs względem M w L; (b) zachowany odsetek „funkcji spoza wzorca obecnych w bloku”. Kierunek (b) przy spadku szkody wskazywałby, że szkoda niesiona strukturą została, a zniknęła tylko ta od wartości.

---

## 9. Moc (kod `code/expA_power.py`, decyzje kodem z sekcji 8)

Prawdopodobieństwa zadań losowane z rozkładu a posteriori K1 w każdej próbie. Plan G 4 / L 9, 2 000 prób na scenariusz (`power/expA_power_v02.out`). Kolumny: odsetek prób z danym stanem.

| Scenariusz (λ_G, λ_L; κ_G, κ_L) | Prawdziwe Δ_sw / Δ_tr | dowolne POPARCIE | OBALENIE | KIER. PRZECIWNY | NIEROZSTRZ. |
|---|---|---|---|---|---|
| H_D swoiste (1, 0; 1, 1) | 1 / ≈0,6 | **99,7** (OBA 98,0) | 0 | 0 | 0,3 |
| H_D pełne (1, 0; 1, 0) | 1 / 1 | **100** | 0 | 0 | 0 |
| tylko nieswoista szkoda (1, 1; 1, 0) | 0 / ≈0,4 | **90,8** (TREŚCI 86,2) | 0 | 0,2 | 8,9 |
| częściowa asymetria (0,75, 0,25; 0,75, 0,25) | 0,5 / 0,5 | **95,9** | 0 | 0 | 4,1 |
| pomoc zostaje, połowa szkody (1, 0,5; 1, 0,5) | 0,5 / 0,5 | **97,5** | 0 | 0 | 2,5 |
| zgodny z M2 (0, 0,5; 0,5, 0,5) | −0,5 / <0 | 0 | **55,0** | 23,2 | 21,8 |
| H_Z (0, 1; 0, 1) | −1 / −1 | 0 | **99,3** | 0,7 | 0 |
| jednakowe 0 / 0,25 / 0,5 / 1 (błąd) | 0 / 0 | 1,1–2,1 | 0,3–0,4 | 1,1–1,7 | 96,4–97,0 |

Wrażliwość:

| Warunek | H_D swoiste | częściowa asymetria | tylko nieswoista | zgodny z M2: OBALENIE / PRZECIWNY | błąd przy jednakowym |
|---|---|---|---|---|---|
| osłabienie efektów o 25% (k = 0,75) | 90,2 | 72,3 | 52,9 | 25,4 / 22,9 | 0,8–1,6 |
| korelacja ramion w bloku ρ = 0,3 | 99,9 | 98,3 | 94,2 | 64,8 / 21,2 | 1,4–2,1 |

- Błąd fałszywego POPARCIA przy jednakowym osłabieniu wynosi 0,8–2,1% (nominalnie ≤ 2,5%). Fałszywe stany ujemne (OBALENIE + KIERUNEK_PRZECIWNY) to 1,4–2,8%; przy ρ = 0,3 jest to lekko powyżej nominału, w granicach błędu Monte Carlo (±0,4 pp).
- Dopiski wrażliwości przy H_D: „nie przenosi się poza te zadania” w 0,6–2,4% prób, „zależy od składu domen” w 1,0–1,8%. Przy częściowej asymetrii odpowiednio 6,0% i 9,2%.
- Dla porównania reguła v0.1 (koniunkcja progów ½): POPARCIE przy częściowej asymetrii 11%, przy (1, 0,5) 2%; scenariusz „tylko nieswoista szkoda” był dla niej niewykrywalny z konstrukcji.
- **Ograniczenie:** stan NIEROZSTRZYGNIETE przy jednakowym osłabieniu jest wynikiem poprawnym („brak asymetrii”). Raport podaje wtedy przedział Δ, czyli jak dużą asymetrię wykluczono, bez zdania o „braku efektu”.

---

## 10. Generalizacja

Bez zmian względem v0.1 (sekcja 10): brak testu generalizacji, rezerwa TradingBot nieużywana, etap 2 tylko po stanie POPARCIE.

---

## 11. Budżet

- 1 926 epizodów. Prognoza na stawkach K1 dla G/L i ramion (ramiona abstrakcyjne jak surowe): **18 036 wywołań**, około 7 h.
- Limit twardy 22 000 daje 22% zapasu; bramki jak w K1 (prognoza +10% przed blokiem).
- **Etap T (do 300 wywołań):** tokeny na znak bloków abstrakcyjnych i wywołania na epizod M-abs/S-abs na zadaniach spoza G/L, bez zapisu wyników zadań. Jeśli prognoza z etapu T przekroczy 20 000, właściciel decyduje przed startem.
- Przerwanie przez limit: minimum G 4 i L 6 bloków, inaczej NIEWAŻNY.
- Koszt pieniężny: 0 USD.

---

## 12. Ryzyka (po poprawkach)

1. Jedna operacjonalizacja abstrakcji; świadome straty z 5.4 przesuwają wynik w stronę „pomoc znika”. Asymetria to neutralizuje, ale tylko wtedy, gdy straty działają w G i L podobnie.
2. Wartości argumentów i fakty z wyników nie są rozdzielone.
3. Moc zależy od powtórzenia efektów K1 (sekcja 9).
4. Szóste użycie tych samych zadań i śladów.
5. Ratio λ przy małym mianowniku: warunek wstępny 8.4 chroni przed dzieleniem przez szum, ale przy osłabionych efektach przedziały się poszerzają.
6. Wykonawca epizodów nie jest jeszcze zbudowany ani przetestowany.

---

## 13. Decyzje właściciela

| # | Decyzja | Rekomendacja |
|---|---|---|
| DB1 | Przyjęcie zmian v0.2 (sekcja 0) | tak |
| DB2 | Rodzina główna {Δ_swoiste, Δ_treści} z Holmem | tak; alternatywa „tylko Δ_swoiste” jest prostsza, ale ślepa na kopiowanie z losowych śladów |
| DB3 | Pochodzenie P4 z puli (bez czytania pełnych epizodów NIGHT-1) | tak; pełne epizody wymagałyby rozszerzenia LA1 |
| DB4 | Ramiona, bloki, ziarna, limit | jak v0.1: 6 ramion, G 4 / L 9, 8001–8009, 22 000 |
| DB5 | Zatwierdzenie tabeli klas parametrów (92 wiersze) i reguły | po przeglądzie 30 losowych bloków |
| DB6 | Budowa wykonawcy (wzorzec K1) | osobna zgoda |
| DB7 | Zamrożenie (skróty z `STIM_MANIFEST.json` + skrót tej specyfikacji) | osobna zgoda |
| DB8 | Start | osobna zgoda; patrz `ANALIZA_SENSU.md` |

---

## 14. Pakiet i testy

`[machine-local path omitted]\`:
- `code/expA_groups.py`: grupy z NIGHT-2 (jedyny proces czytający wyniki NIGHT-2; zapisuje same identyfikatory);
- `code/expA_abstract.py`: reguła 5 (czyste funkcje);
- `code/expA_stim.py`: wszystkie bodźce i plan, pod hakiem audytu K1;
- `code/expA_analysis.py`: estymandy, stany, wrażliwość, MC1–MC3, składanie danych;
- `code/expA_power.py`: symulacja przez kod analizy;
- `stim_preview/`: zbudowane bodźce (**podgląd, nie zamrożone**) z `STIM_MANIFEST.json` (skróty wyjść, wejść i kodu);
- `tests/test_expA.py` → `tests/WYNIKI_TESTOW.out`: 32 testy, wszystkie OK;
- `power/expA_power_v02.out`: wynik symulacji.

Odtworzenie:

```
python -I -X utf8 -B code/expA_groups.py stim_preview
python -I -X utf8 -B code/expA_stim.py stim_preview
python -I -X utf8 -B tests/test_expA.py
python -I -X utf8 -B code/expA_power.py 2000 stim_preview/expA_groups.json
```

Nie zbudowano: wykonawcy epizodów (integracja bodźców z harnessem K1, bramki, raport), etapu T (wymaga modelu) ani raportu końcowego z danych rzeczywistych.
