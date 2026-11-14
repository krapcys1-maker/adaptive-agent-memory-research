# AAMR EXP-A v0.1 — niezależny audyt metodologiczny

2026-11-14. Audytor: Claude (Opus 5.5). Przedmiot: `[machine-local path omitted]` wraz z `power\` i `prior\`.

**Zakres i ograniczenia przestrzegane w audycie:** bez wywołań Qwena, Ollamy i płatnych API; nic nie zaimplementowano, protokół nie jest zamrożony; wyniki K1 i NIGHT-2 tylko czytane; `sealed/` nie było czytane; koordynator, repozytoria i GitHub nietknięte; specyfikacja Fable'a niezmieniona. Wszystkie nowe pliki leżą wyłącznie w `[machine-local path omitted]\`.

---

## 0. Werdykt

**ACCEPT WITH FIXES.** Przed zamrożeniem trzeba wprowadzić poprawki K1–K6. Bez nich nie zamrażać.

Projekt jest staranny i w kilku miejscach lepszy od propozycji A z audytu K1. Ramię S, odniesienia w tej samej postaci, wymóg wyniku niesymetrycznego i rachunek mocy robią dokładnie to, co obiecują. Audyt znalazł jednak trzy problemy, które w obecnej wersji uniemożliwiają poprawne rozstrzygnięcie pytania:

1. **Reguła abstrakcji w obecnym brzmieniu jest niewykonalna.** W mojej niezależnej implementacji kontrola LA2 zatrzymałaby przygotowanie w 104 z 534 bloków M (19%) i 67 z 534 bloków S (13%) dla zadań G/L. Ta sama stała API (`'START'`, `'USD'`, `'economy'`, `'engage'`) bywa zachowana albo usunięta, zależnie od wielkości liter w prośbie (sekcja 6).
2. **Estymand nie odpowiada pytaniu.** Pytanie brzmi: czy kopiowanie wartości odpowiada za **część** strat. Kontrast główny pyta, czy odpowiada za **większość** (próg ½). Mierzy przy tym tylko szkodę swoistą dla doboru (M − S) i z definicji odejmuje szkodę z kopiowania obecną także w losowych śladach S. Dane K1 wskazują, że to właśnie tam może leżeć znaczna część efektu kopiowania (sekcja 2.3).
3. **Etykiety stanów mówią więcej, niż wynika z testu.** „Pomoc wymaga wartości” uzyska każda abstrakcja, która ogólnie psuje blok. „Kopiowanie nie jest główną przyczyną” dotyczy tylko szkody swoistej (sekcja 2.2).

Wszystkie trzy da się naprawić bez zmiany zamrożonych danych i bez nowych ramion. Po poprawkach eksperyment **rozstrzygnie pytanie o asymetrię**: czy usunięcie wartości zdejmuje więcej szkody niż pomocy. Moc wynosi 98% przy H_D, a przy połowicznej asymetrii około 50–60% wobec 2–11% przy obecnej regule (sekcja 4). **Rekomenduję wydanie około 18 300 lokalnych wywołań po poprawkach**, nie w wersji v0.1.

---

## 1. Czy sześć ramion odróżnia usuwanie szkodliwych wartości od ogólnego osłabienia (pyt. 1, pyt. autora 14.1)

**Co działa.** Przy jednakowym osłabieniu (λ_G = λ_L = λ) mamy T_G = (λ − ½)·s_G i T_L = (λ − ½)·s_L, a s_G > 0 > s_L. Oba kontrasty nie mogą być wtedy jednocześnie dodatnie. Symulacja to potwierdza: przy osłabieniu jednakowym 0,25, 0,5 i 0,75 stan POPARCIE występuje w 0,0–0,1% prób. Sprawdziłem też osłabienie na skali logitów zamiast skali prawdopodobieństw. Przy połowicznym skurczu różnicy logitów wychodzi λ_G ≈ 0,53 i λ_L ≈ 0,61, czyli nieliniowość działa **przeciw** H_D. Logika „tylko wynik niesymetryczny popiera H_D” jest poprawna.

**Czego układ nie wyklucza.** Są mechanizmy inne niż H_D, które dają T_G > 0 i T_L > 0:

| # | Mechanizm | Dlaczego daje wzór H_D | Ocena |
|---|---|---|---|
| M-a | **Różna dawka manipulacji w grupach.** Reguła usuwa 96% wartości w TRAVEL, 85% w GFS i 40% w VC. L to w 52% TRAVEL, G w 27%; VC to 33% G i 24% L. | Osłabienie silniejsze tam, gdzie usunięto więcej, czyli częściej w L, daje λ_L < λ_G bez udziału wartości jako takich. | Umiarkowany (średnio usunięte 73% wartości w G wobec 80% w L), ale realny. Poprawka K5: wynik standaryzowany domenami. |
| M-b | **Abstrakcja zmienia naraz trzy rzeczy:** wartości argumentów, wartości wyników (fakty o środowisku) i tekst prośby. | Wynik POPARCIE nie mówi, która z trzech zmian zdjęła szkodę. „Kopiowanie wartości” to tylko jedna z nich. | Spec. to przyznaje (12.2). Zaradzić można bez nowych ramion: znaczniki na poziomie tur jako miara mechanizmu, zapisana z góry (N7). |
| M-c | **Przepisanie prośby z natywnymi słowami.** Reguła 7 zamienia także słowa języka, np. „a crucial [travel_class] meeting” (ślad 169:t0, wartość `'business'`). | Ślady TRAVEL tracą więcej sensu i przestają przypominać zadanie; to częstsze w L. | To ten sam rodzaj wady, który spec. przypisuje M2 („proceed to `<ignitionMode>` the engine”). Poprawka K1c. |

Wniosek: sześć ramion **wystarcza do odróżnienia jednakowego osłabienia**, ale nie odróżnia „usunięcia wartości” od „usunięcia wartości + wyników + części sensu prośby”. Raport musi to nazywać, a analiza zawierać kontrole M-a i M-b.

---

## 2. Interpretacja przyczynowa kontrastu głównego i kryteriów (pyt. 2, pyt. autora 14.1)

### 2.1 Kontrast `c = a − ½·s`

Jest liniowy, nieobciążony i zawiera się w obrębie bloku, więc nie wymaga zgadywania s z K1. Poprawność kontrastu potwierdzam. Wymóg „oba dolne końce > 0” to test przecięcia–sumy: fałszywe POPARCIE ≤ 2,5% (symulacja na granicy λ_G = 0,5, λ_L = 0 daje 2,0–2,8%).

### 2.2 Asymetria kryteriów i nadinterpretacja etykiet

| Stan | Co test faktycznie pokazuje | Co głosi etykieta | Problem |
|---|---|---|---|
| OBALENIE: szkoda nie zależy od wartości (λ_L > ½) | Większość **swoistej** szkody przetrwała tę abstrakcję. | „Kopiowanie wartości nie jest jej główną przyczyną.” | Wniosek dotyczy wyłącznie szkody swoistej doboru, nie całej szkody pamięci. Ważny tylko przy MC3 na poziomie przypadkowym. |
| OBALENIE: pomoc wymaga wartości (λ_G < ½) | Większość swoistej pomocy nie przetrwała tej abstrakcji. | „Pomoc wymaga wartości.” | Ten stan daje każde ogólne zepsucie bloku: przy osłabieniu jednakowym 0,25 pojawia się w 33% prób. Nazwa przyczynowa jest nieuprawniona. |
| Kryterium obalenia hipotezy właściciela = λ_L > ½ | Kopiowanie nie jest **większościową** przyczyną szkody swoistej. | Obalenie „szkody przez kopiowanie”. | Hipoteza właściciela mówi o **części** strat. Próg ½ testuje „większość”. |

Pierwsze obalenie jest bardziej wiarygodne od drugiego: ogólne osłabienie pcha λ_L w dół, w stronę H_D, więc nie może sfałszować wyniku λ_L > ½. Drugie obalenie jest podatne na każde zepsucie bloku. Spec. traktuje oba symetrycznie (8.5).

### 2.3 Najważniejsza luka: szkoda z kopiowania jest w dużej części nieswoista

Spec. 2.2 twierdzi, że „abstrakcja może dotyczyć najwyżej trzeciej warstwy” (S → M). **To nieprawda:** S-abs jest również abstrahowane, więc abstrakcja działa też na warstwę P → S (−19 pp w L). Kontrast główny odejmuje `S-abs − S` jako „efekt postaci”, choć ten efekt może być w dużej mierze właśnie efektem usunięcia kopiowalnych wartości z losowych śladów domeny.

Sprawdziłem to na **istniejących epizodach K1** (S1–S3, zero wywołań; `scripts\audit_copy_k1.py`). Badam wartość „tylko z bloku”: wartość argumentu obecną w bloku, nieobecną w prośbach ani we wcześniejszych wynikach, z wyłączeniem słownika API. Poziom przypadkowy wyznacza N względem bloku M tej samej tury.

| Grupa | Ramię | Epizody z ≥1 wartością tylko z bloku | Rozwiązane: z kopią | Rozwiązane: bez kopii |
|---|---|---|---|---|
| L | N (przypadek) | 42,9% | 20/27 (74%) | 29/36 (81%) |
| L | S | 34,9% | 3/22 (14%) | 23/41 (56%) |
| L | M | 55,6% | 1/35 (3%) | 6/28 (21%) |
| G | N (przypadek) | 14,1% | 3/14 | 14/85 |
| G | S | 14,1% | 6/14 | 32/85 |
| G | M | 28,3% | 19/28 (68%) | 56/71 (79%) |

To tylko opis, z zakłóceniami: epizody długie i zagubione emitują więcej wartości. Trzy obserwacje są jednak istotne dla projektu:
- W L kopia współwystępuje z porażką **zarówno w M, jak i w S**, ale nie w N. Kopiowanie szkodzi więc także w ślepym bloku domenowym.
- W L 22 z 28 epizodów M **bez** żadnej kopii też kończy się porażką (79% wobec 22% dla N). Kopiowanie nie jest konieczne do szkody, więc λ_L ≈ 0 jest mało prawdopodobne.
- Ilustracja, nie oszacowanie: gdyby epizody z kopią zachowały się jak te bez kopii, M w L wzrosłoby z 11% do około 21%, a S z 41% do około 56%. Szkoda łączna M − N zmalałaby o około 10 pp, a S − N o około 15 pp, natomiast **swoista** M − S pozostałaby prawie bez zmian (−30 → −35). Kontrast główny byłby wtedy ślepy na cały efekt kopiowania.
- W G kopia nie współwystępuje z sukcesem (68% wobec 79%). To osłabia przekonanie spec. (2.3), że „abstrakcja niszczy także pomoc”. Dowody wstępne są więc **niejednoznaczne**, a nie jednostronnie niekorzystne. To podnosi wartość informacyjną eksperymentu.

Wniosek: kontrast `S-abs − S` (8.6.4, obecnie opisowy) i kontrast treści względem P muszą wejść do rodziny wnioskowania (K2).

---

## 3. Wybór 54 zadań, regresja do średniej, uogólnienie (pyt. 3)

- **Regresja do średniej jest widoczna i prawidłowo obsłużona.** Grupy zdefiniowane jednym przebiegiem przy temperaturze 0 dawały w NIGHT-2 M − N = ±100 pp. W niezależnych blokach K1 jest to +59 pp w G i −67 pp w L, a N w G ma 17% zamiast 0%. Spec. słusznie planuje na liczbach K1, które są niezależne od definicji grup, i mierzy s ponownie w tym samym przebiegu. Kontrast `c` nie jest obciążony selekcją, bo s i a pochodzą z nowych danych.
- **Warunek wstępny 8.4 jest prawie pewny** (100% w obu symulacjach), więc nie chroni przed niczym. Realne zagrożenie to osłabienie efektu, nie jego brak. Przy s mniejszym o 25%, co mieści się w przedziale K1 [24; 51], moc POPARCIA przy H_D spada z 72% do 37% (sekcja 4).
- **Wybór po K1.** Grupy pochodzą z NIGHT-2, ale decyzja o eksperymencie i jego kształcie zapadła po obejrzeniu wyników K1 dla tych grup. To nie obciąża kontrastów w nowych danych, ale jest szóstym użyciem tych samych zadań i śladów (spec. 12.7). Zgadzam się z oceną spec.
- **20 zadań treningowych** (11 w G, 9 w L) to zadania, na których wybrano prezentację R+ (E\*). Mogą mieć zawyżony efekt doboru. Spec. przewiduje podgrupy test/trening opisowo; to wystarcza.
- **Uogólnienie jest bardzo ograniczone.** Zadania o skrajnym efekcie pamięci mogą mieć inny mechanizm niż zadania typowe; na 27 zadaniach „oba rozwiązały” M ≈ S ≈ N. L to w połowie TRAVEL. Zdanie obowiązkowe z sekcji 0 jest konieczne i wystarczające. Do tego etykiety stanów muszą zawierać „na tych zadaniach” (dziś ma je tylko POPARCIE; poprawka N1).

---

## 4. Niezależna weryfikacja mocy (pyt. 4, pyt. autora 14.5–14.6)

Własna symulacja: `scripts\audit_power.py`, 2 000 prób na scenariusz. Różni się od symulacji Fable'a w trzech miejscach. Prawdopodobieństwa zadań w każdej próbie **losuję** z rozkładu a posteriori beta-dwumianowego zamiast stałego ściągnięcia W. Przedział fp liczę z kwantylem t i stopniami swobody dokładnie jak w 8.3. Dodaję korelację ramion w bloku (ρ) i osłabienie efektu (κ).

### 4.1 Odtworzenie i wrażliwość reguły spec. (plan G 4 / L 9)

| Scenariusz | Fable | Audyt: baza | κ = 0,75 | ρ = 0,3 | κ = 0,75, ρ = 0,3 |
|---|---|---|---|---|---|
| H_D (1; 0): POPARCIE | 77% | 72% | 37% | 82% | 47% |
| H_D słabsze (0,75; 0,25): POPARCIE | 12% | 11% | 4% | 15% | 5% |
| H_W (0; 0): pomoc znika | 88% | 88% | 65% | 93% | 74% |
| H_S (1; 1): szkoda zostaje | 93% | 90% | 61% | 94% | 70% |
| zgodny z M2 (0; 0,5): pomoc znika / L nierozstrzygnięte | — | 87% / 12% | 67% / 30% | 93% / 7% | 73% / 25% |
| fałszywe POPARCIE na granicy (0,5; 0) | — | 2,2% | 1,5% | 2,8% | 2,0% |
| fałszywe obalenie na granicy, jeden kontrast | 3% | 2,1–2,8% | 2,2–3,3% | 2,0–3,2% | 2,4–3,2% |

- **Liczby autora odtwarzają się** w granicach 2–5 pp; moja symulacja ma nieco więcej szumu, bo propaguje niepewność p zadań.
- **Moc silnie zależy od powtórzenia efektu.** Spec. podaje „77–93%”, a realny zakres przy H_D to około 37–82%. Zdanie z 9 („moc policzono przy założeniu pełnego powtórzenia”) jest uczciwe, ale za słabe. Liczba w raporcie powinna być przedziałem.
- **Wspólne ziarno działa na korzyść.** Dodatnia korelacja ramion w bloku podnosi moc. Przedział fp liczony z wariancji między blokami pozostaje przy tym poprawny.
- **Błąd I rodzaju przedziału fp** wynosi 2,0–3,3% przy nominalnych 2,5%. Lekka liberalność przy 4 blokach G jest dopuszczalna. Jako wrażliwość warto dodać bootstrap bloków w obrębie zadań.
- **Korekta wielokrotności jest poprawna.** Fałszywe POPARCIE ≤ 2,5% (test przecięcia–sumy), łączne fałszywe obalenie ≤ 5% (dwa testy jednostronne po 2,5%), CZĘŚCIOWE ≤ 2,5% na połowę.
- **Główna słabość reguły:** przy jakimkolwiek efekcie pośrednim wynik jest prawie zawsze NIEROZSTRZYGNIĘTY albo CZĘŚCIOWY. Przy (1; 0,5) i (0,5; 0), czyli przy wyraźnej asymetrii, POPARCIE wynosi 2%.

### 4.2 Proponowany estymand: asymetria Δ = λ_G − λ_L

λ w grupie liczę jako średnie a / średnie s z bieżącego przebiegu. Wariancję daje metoda delta z wariancji fp i kowariancji a, s w obrębie zadań. Test jednostronny Δ > 0 na poziomie 2,5%.

| Scenariusz | Δ prawdziwe | Δ > 0 (baza) | Δ > 0 (κ = 0,75) | POPARCIE wg spec. (baza) |
|---|---|---|---|---|
| H_D (1; 0) | 1,0 | **98%** | 83% | 72% |
| (0,75; 0,25) | 0,5 | **53%** | 30% | 11% |
| (1; 0,5) | 0,5 | **47%** | 23% | 2% |
| (0,5; 0) | 0,5 | **58%** | 31% | 2% |
| jednakowe osłabienie 0,25 / 0,5 / 0,75 | 0 | 2,3 / 1,8 / 1,6% (błąd) | 1,4 / 1,4 / 1,0% | 0% |
| zgodny z M2 (0; 0,5) | −0,5 | 0% (Δ < 0 w 62%) | 0% (37%) | 0% |

- Δ **wprost koduje pytanie**: czy usunięcie wartości zdejmuje większą część szkody niż pomocy. Na mocy konstrukcji jest odporny na jednakowe osłabienie; błąd pozostaje przy nominalnych 2,5%.
- Przy efektach połowicznych daje 5–25 razy większą moc niż koniunkcja dwóch testów z progiem ½.
- Sam test „a − s > 0 w L”, czyli „abstrakcja zdjęła **jakąś** szkodę”, **nie nadaje się** na kontrast główny: przy jednakowym osłabieniu 0,5 jest istotny w 66% prób. Odpowiedź na pytanie o „część” musi przejść przez G jako lustro, a to właśnie robi Δ.

### 4.3 Alokacja bloków

G 5 / L 9 daje POPARCIE 79% (wobec 72%) za około +1 570 wywołań. Przy Δ jako estymandzie głównym moc G 4 / L 9 wystarcza. **Plan G 4 / L 9 zostawić.**

---

## 5. Długość promptów (pyt. 5, pyt. autora 14.2)

Pomiar na prawdziwych blokach K1 dla zadań G/L (`scripts\audit_abstraction.py`). Mój renderer bloku surowego odtwarza `block_text` K1 bajt w bajt w 2 933 z 2 933 przypadków; blok abstrakcyjny renderuje moja implementacja reguły 5.1.

| | G | L |
|---|---|---|
| długość M-abs / M | 0,88 | 0,84 |
| długość S-abs / S | 0,85 | 0,83 |
| średnie ln(M / S), postać surowa | −0,002 | +0,033 |
| średnie ln(M-abs / S-abs) | **+0,029** | **+0,046** |
| tury z \|ln\| > ln 1,2: surowe / abstrakcyjne | 6% / **43%** | 10% / **41%** |
| średnie ln(M-abs / S-abs) na zadanie: zakres | −0,21 … +0,33 | −0,13 … +0,30 |

Wnioski:
1. **Szacunek spec. „55–65% bloku surowego” jest błędny.** Faktycznie jest to 82–93%, bo limit 1 400 znaków na ślad i 160 znaków na wynik już ściska bloki surowe, a większość bloku to tekst prośby. Różnica długości surowe/abstrakcyjne jest więc mała (12–18%) i **nie uniemożliwia interpretacji**.
2. **Problem leży gdzie indziej:** S-abs nie jest dopasowane do M-abs. Średnio różnica wynosi +3% (G) i +5% (L), czyli na granicy kryterium ±5% z 7.4. Na poziomie tury nierównowaga powyżej 20% dotyczy 41–43% tur, a na poziomie zadania sięga +33%. Interakcji długości z doborem nie da się wtedy odróżnić od efektu wartości.
3. **Konkretna kontrola (K4):** wspólne dopasowanie długości przy losowaniu S, czyli |ln(S/M)| ≤ ln 1,2 **oraz** |ln(S-abs / M-abs)| ≤ ln 1,1. Jest to deterministyczne i obywa się bez modelu. Sprawdziłem wykonalność (`scripts\audit_joint_match.py`): na wszystkich 195 z 195 tur G/L istnieje para kandydatów, mediana to 142 pary, minimum 10, a w 187 turach jest ≥ 20 par. Do tego zapisana z góry wrażliwość: regresja `c(i,r)` względem ln(M-abs/S-abs) tury.
4. **P:** spec. dopasowuje P do M-abs, co wymaga nowego `c_d` w etapie T i zrywa porównywalność z P w K1. Ponieważ M-abs ≈ 0,85·M, rekomenduję **P dopasowane do M surowego, regułą K1 bez zmian** (N3). Upraszcza to też etap T.

---

## 6. Reguła abstrakcji i tabela 584 wartości (pyt. 6, pyt. autora 14.3)

Niezależna implementacja reguły 5.1 (z drugim warunkiem z punktu 2): `scripts\audit_abstraction.py`. Tabela: `out\decision_table_584.csv` (584 wiersze; decyzja i flagi niejednoznaczności dla każdej wartości).

### 6.1 Wynik reguły

| Domena | Wartości | Zostaje (logiczne + słownik API) | Usunięte | W tym z uwagą o pochodzeniu |
|---|---|---|---|---|
| GFS | 95 | 14 (15%) | 81 | 25 |
| VC | 164 | 98 (60%) | 66 | 16 |
| TRAVEL | 325 | **12 (4%)** | 313 | 23 |

Liczby „16% / 67% / 14%” w spec. 5.2 dotyczą wariantu **bez** drugiego warunku. Z tym warunkiem TRAVEL zachowuje 4% wartości, a nie 14%.

### 6.2 Problemy

| Kod | Problem | Skala | Skutek |
|---|---|---|---|
| **R1** | **Decyzja na poziomie wystąpienia, nie parametru.** Ta sama stała API jest zachowana lub usunięta zależnie od prośby: `startEngine.ignitionMode='START'` 27 razy zostaje, 3 razy znika; podobnie `activateParkingBrake.mode`, `compute_exchange_rate.*`, `displayCarStatus.option`, `pressBrakePedal.pedalPosition`. | 9 z 96 par (funkcja, parametr) | Niespójny słownik API; konflikt z LA2 (R2). |
| **R2** | **LA2 niewykonalne.** Usunięta wartość (≥ 3 znaki) zostaje widoczna w bloku: (C1) wartość usunięta w jednym śladzie występuje w innym śladzie bloku (`'travel'`, `'doors'`); (C2) ta sama wartość jest stałą API w innym śladzie; (C4) wartość pokrywa się z nazwą parametru lub pola wyniku (`'file_name'`, `'booking_id'`; pula zawiera np. `rm(file_name='file_name')`). | 104/534 bloków M, 67/534 S | Przygotowanie zatrzymane w około 19% bloków. |
| **R3** | **Wielkość liter decyduje o klasie wartości.** `'START'` zostaje, gdy prośba mówi „start”, a znika, gdy mówi „START”. | 17 wystąpień | Arbitralność. |
| **R4** | **Pochodzenie tylko w obrębie śladu.** 181 usuniętych wartości nie występuje ani w prośbie, ani we wcześniejszych wynikach **tego** śladu. Pochodzą z wcześniejszych tur epizodu źródłowego, z wartości domyślnych albo z wnioskowania modelu (np. `fillFuelTank(fuelAmount=50)` przy prośbie o „pełny bak”). M2 brało pod uwagę cały epizod źródłowy. | 181/584 (31%) | Utrata użytecznej wiedzy proceduralnej (pełny bak = 50) bez śladu, że wartość w ogóle istniała. |
| **R5** | **Prośba: podmiana słów języka.** „crucial [travel_class] meeting”. | nieznana; dotyczy wartości będących zwykłymi słowami | Ta sama wada, którą spec. zarzuca M2 (5.3, wiersz 3). |
| **R6** | **Liczby w innej postaci w prośbie** (`insurance_cost=1500` przy „$1,500”, `value=50000`) zostają w tekście prośby, a krótkie wartości < 3 znaki są poza kontrolą LA2. | 2 + 2 | Drobne przecieki wartości. |
| **R7** | **Liczby jako „literał dokumentacji”.** `pedalPosition=1` i `priority=1` zostają, bo „1” występuje w opisie parametru. | 11 | Wynik poprawny, ale przypadkowy. |

### 6.3 Stałe API kontra wartości instancji; wiedza potrzebna do decyzji; ryzyko utraty wiedzy

- Spośród 96 par (funkcja, parametr) 7 ma w opisie znacznik `[Enum]`. To mechaniczne, sprawdzalne kryterium słownika API, którego reguła nie wykorzystuje.
- Informacje potrzebne do poprawnej decyzji i tracone przez regułę: (a) stałe wynikające z wartości domyślnych i środowiska (pojemność baku, kod lotniska z wyniku `get_nearest_airport_by_city`), (b) format wartości (daty ISO, format identyfikatora), (c) to, że wartość pochodzi z wcześniejszej tury. Utrata (b) i (c) to nie usunięcie „kopii”, tylko informacji o formacie i przepływie danych. Przechyla to wynik w stronę „pomoc znika” (H_W) z powodów innych niż kopiowanie.
- **Przemycenie odpowiedzi wzorcowej:** reguła czyta tylko pulę i dokumentację, a plany M powstają z jądra leksykalnego próśb (K1), nie z odpowiedzi wzorcowych. Ryzyko wnosi **zatwierdzanie tabeli przez ludzi**, którzy znają wyniki K1 dla G/L. Ręczne wyjątki dla pojedynczych wartości otwierają drogę do dopasowania reguły do znanych porażek. Poprawka K1e: zatwierdza się regułę i jej zgodność, nie pojedyncze wartości.

### 6.4 Rekomendacja dla tabeli bez ręcznej analizy 584 wartości (DA5)

1. **Klasyfikacja na poziomie parametru (96 wierszy), mechanicznie z danych bez wyników modelu:**
   - *stała API:* parametr z `[Enum]` lub z listą literałów w opisie, którego wartość w puli wymienia prośba śladu w < 50% wystąpień. Wartość zostaje **zawsze**, w każdym śladzie i bloku;
   - *wybór użytkownika:* jak wyżej, ale prośba wymienia wartość w ≥ 50% wystąpień (`travel_class`, `displayCarStatus.option`, `get_nearest_airport_by_city.location`). Wartość znika zawsze;
   - *instancja:* pozostałe parametry. Wartość znika zawsze; wartości logiczne zostają.
2. **Spójność na poziomie bloku:** wartość usunięta w jakimkolwiek śladzie bloku jest usuwana ze wszystkich jego miejsc, jak w M2 (`block_markers`).
3. **LA2 przedefiniowane:** dotyczy tylko tokenów niebędących nazwą funkcji, parametru, pola wyniku ani stałą API. Kontrola na całe słowo z rozróżnieniem wielkości liter, dodatkowo dla liczb w postaciach „1500 / 1,500 / 1500.0”.
4. **Pochodzenie (R4):** albo cały epizod źródłowy (jak M2), albo jawna uwaga „[value from earlier in that task]”. Wybór należy do właściciela; rekomenduję cały epizod, bo inaczej reguła usuwa przepływ danych, a nie tylko wartości.
5. **Prośba (R5):** podmiana tylko wartości parametrów klasy „instancja” lub „wybór użytkownika”, tylko w cudzysłowie albo jako token zawierający cyfrę, `_`, `.`, `-` lub wielką literę w środku słowa. Zwykłe słowa zostają.
6. **Weryfikacja niezależna zamiast ręcznej:** wykonawca generuje tabelę swoją implementacją, a audytor drugą, niezależną (moja jest gotowa i wymaga tylko dostosowania do punktów 1–5). Warunek zamrożenia: zero różnic na 584 wartościach albo każda różnica rozstrzygnięta zmianą **reguły**, nigdy wyjątkiem. Właściciel zatwierdza 96-wierszową tabelę parametrów, a ludzie oglądają losową próbkę 30 śladów po abstrakcji pod kątem czytelności. Flagi A1–A8 z `decision_table_584.csv` służą jako lista kontrolna.

---

## 7. EXP-A a maskowanie M2 z NIGHT-2 (pyt. 7)

Kod M2 (`aamr_night2.py`, 282–417) przeczytany w całości.

| Element | M2 | M-abs | Czy to nowa manipulacja? |
|---|---|---|---|
| Wyniki udane jako same klucze | **tak** (`mask_ok`) | tak (reguła 5) | **Nie.** Spec. 5.3 tego nie odnotowuje: utrata faktów o środowisku była już w M2. |
| Wartości z prośby i z wcześniejszych wyników | maskowane | usuwane | Nie, ta sama treść informacyjna. |
| Wartości „znikąd” | zostawały | usuwane | Tak, ale to 31% wartości (R4), przeważnie przepływ danych. |
| Znaczniki w miejscu wartości | `<param>` | brak | Tak: usuwa wadę wykonania (9/60 epizodów ze znacznikiem). |
| Słownik API | maskowany | zachowany, w obecnym brzmieniu niespójnie (R1, R3) | Tak, po poprawce K1. |
| Zdanie w nagłówku | dodatkowe | brak | Tak: usuwa zakłócenie. |
| Pomiar | 1 przebieg, temp. 0, 60 zadań, bez odniesień | próbkowanie, 4–9 bloków, S i S-abs | **Tak: to główna nowość.** |

**Ocena:** pod względem informacji usuwanej z bloku M-abs to **oczyszczona replikacja M2**, nie nowa manipulacja. Nowe są usunięcie dwóch zakłóceń (znaczniki, nagłówek), zachowanie słownika API oraz przede wszystkim **pomiar**: odniesienia S/S-abs, próbkowanie i zadania o znanym efekcie. To uzasadnia eksperyment. Wynik M2 nie był rozstrzygający (9 i 11 zadań, po jednym losowaniu), a nowe dane K1 o kopiowaniu (sekcja 2.3) nie są jednostronnie niekorzystne. Raport musi uczciwie nazwać EXP-A „replikacją M2 w lepszym instrumencie”, nie „nową regułą”.

---

## 8. Szczelność, kolejność, ziarna, niedeterminizm, limity, zatrzymanie (pyt. 8)

| Element | Ocena | Uwagi |
|---|---|---|
| Kontrole L1–L10 i LA1–LA5 | dobre | LA2 wymaga przedefiniowania (R2). LA3 i LA4 trywialne do spełnienia. LA5 (ślepota) poprawne. |
| Kolejność: kwadrat Williamsa 6 × 6 | poprawna, ponad potrzebę | Epizody są niezależne, a przenoszenie między nimi zachodzi tylko przez stan serwera (pamięć podręczna, dryf czasowy). Zrównoważenie pozycji wystarcza. W G każde zadanie zobaczy tylko 4 z 6 wierszy, więc pozycja jest zrównoważona po zadaniach, nie w zadaniu; to dopuszczalne. |
| Wspólne ziarno w bloku | korzystne | Daje dodatnią korelację ramion (moc +10 pp przy ρ = 0,3), a przedział fp pozostaje poprawny. Zapisać, że ziarna 8001–8009 i losowania S są rozłączne z K1. |
| Niedeterminizm Ollamy | dobrze ujęty | Wersja i skrót modelu zapisane; kontrola pomostowa jest opisowa. Zalecam liczbowy próg ostrzeżenia, np. N w L poza przedziałem K1, bez zmiany stanu. |
| Budżet: 9,5 wywołania na epizod | potwierdzone | K1 na zadaniach G/L: 8,9–10,2 na epizod, prognoza 18 074 dla ramion surowych. Liczba wywołań ramion abstrakcyjnych jest nieznana: brak wartości może wymuszać dodatkowe wywołania `get_*`. Limit 22 000 daje około 20% zapasu, czyli wytrzymuje wzrost wywołań w ramionach abstrakcyjnych do około +40%. Rekomenduję, by etap T zmierzył wywołania na epizod M-abs na zadaniach spoza G/L. |
| Zatrzymanie | poprawne | Bloki 1–4 zawierają G, więc przerwanie przez limit dotyka tylko L. Minimum G 4 / L 6 rozsądne. |
| Braki (komplet 6 ramion) | poprawne | Wzór wariancji uwzględnia R_i. |
| **MC1, próg 5% bezwzględnie** | **wadliwy** | W K1 zbliżony znacznik (wartość równa nazwie parametru, w nawiasach, `UPPER_SNAKE`) występuje już w 2–9% epizodów **bez** abstrakcji (N w G: 9,1%; M w L: 6,3%; `scripts\audit_calls_mc1.py`). Próg bezwzględny 5% mógłby więc odpalić bez winy reguły. Poprawka K6. |

---

## 9. Dziewięć decyzji z sekcji 13

| # | Decyzja | Rekomendacja audytora |
|---|---|---|
| DA1 | Ramiona | **6 ramion, zgoda.** S jest konieczne. **P zostawić** (nie wariant bez P): P jest odniesieniem dla kontrastu treści (K2), a ten obejmuje kopiowanie z losowych śladów, czyli połowę pytania właściciela. Za 16% budżetu to najlepsza pozycja w planie. P dopasowane do M surowego (N3). |
| DA2 | Bloki | **G 4, L 9, ziarna 8001–8009, zgoda.** Przy Δ jako estymandzie głównym G 5 nie jest potrzebne. |
| DA3 | Próg ½ | **Zachować jako drugorzędną klasyfikację wielkości.** Główny estymand: Δ = λ_G − λ_L > 0 (K2). Próg ½ odpowiada na „czy większość”, a Δ na „czy część, ponad ogólne osłabienie”. |
| DA4 | Przedział główny | **Populacja skończona, zgoda**, z warunkiem: zdania o mechanizmie (każdy stan OBALENIE i POPARCIE) wymagają zgodności z przedziałem po zadaniach. Bez zgodności zdanie dostaje dopisek „na tych 54 zadaniach; nie przenosi się poza nie”. |
| DA5 | Reguła abstrakcji | **Nie zatwierdzać w brzmieniu v0.1.** Poprawki K1a–K1e (sekcja 6.4). Wybór pochodzenia (R4) należy do właściciela; rekomenduję cały epizod źródłowy. |
| DA6 | Próg MC1 | **Zmienić na względny:** nadwyżka MC1 w M-abs nad M (i S-abs nad S) na tych samych zadaniach i blokach, górna granica 95% ≤ 5 pp. Definicję znacznika zamrozić z góry (K6). |
| DA7 | Limit twardy | **22 000, zgoda**, plus pomiar wywołań ramion abstrakcyjnych w etapie T. |
| DA8 | Rezerwa TradingBot | **Nie używać, zgoda.** |
| DA9 | Wykonawca | **Zgoda** (osobny katalog, wzorzec K1, start po osobnej zgodzie). Dodać: dwie niezależne implementacje reguły abstrakcji z porównaniem tabel (6.4, punkt 6). |

---

## 10. EXP-A a alternatywa B (instrument na poziomie tury) (pyt. 10)

| Kryterium | EXP-A (po poprawkach) | B (tura, 520 jednostek, N/P/S/M, 3 bloki) |
|---|---|---|
| Pytanie | Mechanizm: czy szkoda i pomoc zależą od wartości. | Średni efekt pamięci z precyzją ±3–5 pp. |
| Związek z pytaniem właściciela o kopiowanie | **Bezpośredni.** | Pośredni. Bez ramion M-abs nie mówi nic o kopiowaniu. |
| Wartość informacyjna | Wysoka w obu kierunkach: Δ > 0 → abstrakcja ma sens; Δ < 0 lub λ_L > ½ → kopiowanie nie wyjaśnia szkody swoistej, a abstrakcja odpada. | Średnia–wysoka, plus trwały instrument. K1 wskazuje już średni efekt około +2 pp, więc B prawdopodobnie potwierdzi „brak średniej korzyści” z węższym przedziałem. |
| Nowe ryzyka | reguła abstrakcji (naprawialne); jedna operacjonalizacja | Nowa reguła przecieków: odtworzenie stanu z wywołań wzorcowych, czyli **jawne użycie odpowiedzi wzorcowych**. Tury jednego zadania zależne. |
| Koszt | około 18 300 wywołań, około 7 h, 0 USD | około 20 600 wywołań, około 8 h, 0 USD, większy nakład na implementację (odtwarzanie stanu) |
| Zależność | Wynik A decyduje, czy B ma zawierać M-abs. | B nie odpowiada na pytanie A. |

**Rekomendacja: EXP-A (po poprawkach) jako następny, B potem.** Uzasadnienie: (1) pytanie właściciela dotyczy mechanizmu, a tylko A go testuje przyczynowo; (2) istniejące dane K1 dają w tej sprawie realną niepewność (sekcja 2.3), więc oczekiwany zysk informacji jest duży; (3) koszt pieniężny jest zerowy, a A jest tańsze i prostsze od B; (4) przy POPARCIU B jest naturalnym etapem 2 z ramieniem M-abs, zgodnie ze spec. 10.

---

## 11. Lista problemów

### Krytyczne (blokują zamrożenie)

| # | Problem | Sekcja |
|---|---|---|
| K1 | Reguła abstrakcji niewykonalna i niespójna: LA2 zatrzymuje przygotowanie w około 19% bloków M; stałe API klasyfikowane zależnie od wielkości liter; pochodzenie tylko w obrębie śladu (31% wartości bez śladu); podmiana słów języka w prośbie. | 6 |
| K2 | Estymand nie odpowiada pytaniu o **część** strat i pomija szkodę nieswoistą (P → S), na którą abstrakcja też działa. Twierdzenie spec. 2.2 („najwyżej trzecia warstwa”) jest błędne. | 2.2–2.3, 4.2 |
| K3 | Etykiety stanów mówią więcej niż testy („pomoc wymaga wartości”, „kopiowanie nie jest główną przyczyną”). | 2.2 |
| K4 | S-abs niedopasowane do M-abs: nierównowaga na granicy kryterium ±5% średnio i do +33% na zadanie, bez korekty. | 5 |
| K5 | Brak kontroli różnej dawki manipulacji między grupami (skład domen G ≠ L). | 1 |
| K6 | Bezwzględny próg MC1 5% przy poziomie bazowym 2–9% bez abstrakcji. | 8 |

### Niekrytyczne

| # | Problem |
|---|---|
| N1 | Zdanie „na tych zadaniach” tylko w stanie POPARCIE; dodać do wszystkich stanów. |
| N2 | Moc podana jako „77–93%”; realny zakres przy H_D to 37–82%, zależnie od powtórzenia efektu. Podać przedział. |
| N3 | P dopasowane do M-abs wymaga nowego `c_d` i zrywa porównywalność z K1. Dopasować do M surowego regułą K1. |
| N4 | Szacunek długości bloku abstrakcyjnego „55–65%” błędny (faktycznie 82–93%); liczby wykonalności 5.2 dotyczą wariantu bez drugiego warunku (TRAVEL 4%, nie 14%). |
| N5 | Spec. 5.3 nie odnotowuje, że wyniki jako same klucze były już w M2. |
| N6 | Lekka liberalność przedziału fp (do 3,3% przy nominalnych 2,5%). Dodać bootstrap bloków jako wrażliwość. |
| N7 | Znaczniki mechanizmu (8.6.5) są tylko opisowe. Zapisać z góry kierunek oczekiwany przy H_D: spadek wartości tylko z bloku w nieudanych turach M-abs w L, przy zachowanym odsetku „funkcji spoza wzorca obecnych w bloku”. Pozwoli to oddzielić kopiowanie wartości od kopiowania struktury. |
| N8 | Kontrola pomostowa bez liczbowego progu ostrzeżenia. |
| N9 | Liczba wywołań ramion abstrakcyjnych nieznana; zmierzyć w etapie T. |

---

## 12. Proponowane poprawki (bez zmiany zamrożonych danych)

Żadna poprawka nie zmienia zadań, puli, planów M, nagłówka, harnessu, modelu, opcji próbkowania ani zamrożonych wyników K1/NIGHT-2.

- **K1a–e (reguła):** klasyfikacja na poziomie parametru; spójność w bloku; LA2 na tokenach wartości; pochodzenie z całego epizodu źródłowego (decyzja właściciela); podmiana w prośbie tylko tokenów wartości; dwie niezależne implementacje i zero różnic jako warunek zamrożenia (6.4).
- **K2 (estymandy):** rodzina główna z korektą Holma na poziomie 2,5% jednostronnie:
  1. Δ_swoiste = λ_G − λ_L, gdzie λ = średnie(M-abs − S-abs) / średnie(M − S);
  2. Δ_treści = λᴾ_G − λᴾ_L, gdzie λᴾ = średnie(M-abs − P) / średnie(M − P). Obejmuje kopiowanie z każdego śladu, a P jest odniesieniem niezależnym od postaci.

  Stany z progiem ½ zostają jako klasyfikacja wielkości (drugorzędna). `S-abs − S` w G i L staje się kontrastem drugorzędnym z zapisanym kierunkiem. Przed zamrożeniem symulację mocy trzeba rozszerzyć o Δ_treści; moja implementacja Δ_swoiste jest w `scripts\audit_power.py`.
- **K3 (etykiety):** „pomoc wymaga wartości” → „swoista pomoc nie przetrwała tej abstrakcji”; „kopiowanie nie jest główną przyczyną” → „większość swoistej szkody doboru przetrwała usunięcie wartości (na tych zadaniach)”. Kryterium obalenia hipotezy właściciela: **górne granice Δ_swoiste i Δ_treści poniżej zera**, przy MC3 na poziomie przypadkowym. Oznacza to, że usunięcie wartości zdejmuje mniej szkody niż pomocy, także licząc kopiowanie z losowych śladów. Samo λ_L > ½ pozostaje opisem wielkości („kopiowanie nie jest większościową przyczyną szkody swoistej”), a nie obaleniem.
- **K4 (długość):** wspólne dopasowanie S do długości M (surowej, ln 1,2) i M-abs (abstrakcyjnej, ln 1,1); wykonalność sprawdzona na 195 z 195 tur. Wrażliwość: regresja `c` na ln(M-abs/S-abs).
- **K5 (dawka):** Δ standaryzowane domenami (wspólne wagi domen 54 zadań) jako obowiązkowa wrażliwość; rozbieżność znaku → dopisek „wynik zależy od składu domen”. TRAVEL (9 G, 11 L) osobno, opisowo.
- **K6 (MC1):** próg względny (nadwyżka M-abs nad M, górna granica ≤ 5 pp), definicja znacznika zamrożona z góry.
- N1–N9 jak w liście.

---

## 13. Czy eksperyment rozstrzygnie zaplanowane pytanie?

- **W wersji v0.1: nie w pełni.** Najbardziej prawdopodobny wynik, zgodny z M2 (λ_G ≈ 0, λ_L ≈ 0,5), to „pomoc znika” (87%) i L nierozstrzygnięte. Raport powiedziałby wtedy „abstrakcja niszczy pomoc”, co może być ogólnym zepsuciem bloku, i nic o tym, czy kopiowanie odpowiada za **część** strat. Przy efektach połowicznych wynik jest prawie zawsze CZĘŚCIOWY lub NIEROZSTRZYGNIĘTY. Do tego reguła w obecnym brzmieniu zatrzyma przygotowanie.
- **Po poprawkach: tak, w zakresie mechanizmu na tych 54 zadaniach.** Δ_swoiste rozstrzyga asymetrię z mocą 98% przy H_D i około 50–60% przy połowicznej asymetrii, a znak ujemny wykrywa w scenariuszu M2 w 62%. Fałszywy wynik przy jednakowym osłabieniu nie przekracza 2,5%. Δ_treści obejmuje kopiowanie z losowych śladów. Nie rozstrzygnie: (a) czy chodzi o wartości argumentów, czy o fakty z wyników; do tego służą znaczniki z N7 i ewentualny etap 2; (b) niczego o całym benchmarku.

## 14. Czy wydać około 18 300 lokalnych wywołań?

**Tak, po wprowadzeniu K1–K6 i rozszerzeniu symulacji o Δ_treści. Nie w wersji v0.1.** Koszt pieniężny wynosi zero, a czas maszyny około 7 h. Po poprawkach każdy wynik zmienia kierunek prac (abstrakcja jako reprezentacja albo jej porzucenie na rzecz bramkowania lub momentu użycia, propozycja C z audytu K1). Istniejące dane nie rozstrzygają kwestii, bo są obserwacyjne i niejednoznaczne. W wersji v0.1 wywołania byłyby wydane na pytanie „czy większość”, na które dowody wstępne już skłaniają do odpowiedzi, przy regule, która nie przejdzie własnej kontroli LA2.

---

## 15. Pliki audytu i odtwarzalność

`[machine-local path omitted]\`:
- `RAPORT_AUDYT_EXP_A_v0.1.md`: ten raport;
- `scripts\audit_abstraction.py` → `out\audit_abstraction.out`, `out\decision_table_584.csv`, `out\block_lengths_GL.csv`: niezależna implementacja reguły 5.1, tabela 584 wartości z flagami A1–A9, długości bloków, kontrola LA2;
- `scripts\diag_leak.py` → `out\diag_leak.out`: przyczyny naruszeń LA2, klasy parametrów;
- `scripts\audit_power.py` → `out\audit_power.out`: niezależna symulacja mocy, scenariusze osłabienia i korelacji, estymandy alternatywne;
- `scripts\audit_copy_k1.py` → `out\audit_copy_k1.out`: kopiowanie wartości w istniejących epizodach K1 (opis, nie test);
- `scripts\audit_calls_mc1.py` → `out\audit_calls_mc1.out`: wywołania na epizod w G/L, poziom bazowy znacznika MC1;
- `scripts\audit_joint_match.py` → `out\audit_joint_match.out`: wykonalność wspólnego dopasowania długości S.

Uruchomienie: `python -I -X utf8 -B <skrypt>` z katalogu `scripts`. Skrypty czytają wyłącznie `[machine-local path omitted]}`, `…\aamr-night2-2026-11-13\run\sessions` i dokumentację funkcji BFCL. Nie piszą poza `out\`.

Zastrzeżenia audytu: reguła abstrakcji w mojej implementacji jest interpretacją spec. 5.1 tam, gdzie spec. milczy (listy mieszane, dopasowanie pochodzenia podciągiem, renderowanie uwag). Liczby z sekcji 6 mogą się więc różnić od implementacji wykonawcy o kilka procent, ale problemy R1–R4 wynikają wprost z brzmienia reguły. Analiza kopiowania w K1 jest opisowa i zakłócona; nie stanowi dowodu przyczynowego.
