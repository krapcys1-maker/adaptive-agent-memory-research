# Recenzja metodologiczna planu T39-TEMPORAL (zadanie #9)

## 1. Werdykt: **revise**

Diagnoza C3 i projekt `as_of(valid, known)` są spójne z dowodami, a szkielet protokołu jest właściwy (zapieczętowany held-out, testy mutacyjne, nowe ID eksperymentu). W obecnej postaci wynik nie mógłby jednak ani potwierdzić, ani obalić skuteczności warstwy, z trzech powodów:

- **Jedyne kryterium konfirmacyjne (FC8) jest niedookreślone.** Nie ma rozmiaru H, składu rodzin ani definicji błędu krytycznego, a próg 0.95 nie wynika z żadnego wcześniejszego wyniku.
- **Kontrola przecieku (FC2) opiera się na `basis_ids`,** czyli na deklaracji samej badanej warstwy.
- **Plan porzucił ramiona porównawcze,** które w REV-V0 były źródłem falsyfikowalności.

Wszystkie braki da się usunąć bez zmiany strategii i bez kosztu.

## 2. Zakres i ograniczenia tej recenzji

Dostałem 7 plików, a plan cytuje 22. Nie mam fixture (`events.jsonl`, `queries.jsonl`), kodu (`run_revision_v0.py`, `upcast.py`, `memory_store.py`), manifestu REV-V0 ani raportów mechanizmu B i kotwicy. Numeracja też się różni: `07_results.json` z planu to u mnie `context/03_results.json`, `02_SCHEMA.md` to `context/04_SCHEMA.md`, `22_response.md` to `context/06_response.md`.

**Potwierdziłem w dostępnych plikach:**
- Ramię bitemporal odpowiada na C3 poprawnie w `valid_at` i błędnie w `as_known_at` (`context/03_results.json:604-621`).
- Ramię `valid_only` odpowiada na C3 poprawnie w obu zapytaniach (`context/03_results.json:424-441`).
- Fixture nie ma zapytania `current` dla C3: w `context/03_results.json` C3 występuje tylko jako `valid_at` i `as_known_at`.
- Oczekiwane odpowiedzi z ręcznego śladu 18/18 (`context/07_response.md:96`) zgadzają się z polami `expected`.
- Reprodukcja 6/6 oraz H2 dev: newest 0.200, resolver 1.000, abstencja 0.200 (`context/06_response.md:3,80`).
- Cytaty ze SCHEMA są wierne (`context/04_SCHEMA.md:21,51,71-78`).

**Nie mogłem zweryfikować:** śladu w kodzie resolwera, luk G1–G13, przypisań „mutant → przypadek zabijający”, treści X1–X10 względem fixture ani stanu blokad manifestu REV-V0. Traktuję je jako twierdzenia planu.

**Jedna rozbieżność do sprawdzenia.** Plan twierdzi, że usunięcie filtra transakcyjnego psuje m.in. C7 (`context/07_response.md:98`). Tymczasem ramię `valid_only`, które takiego filtra nie ma, odpowiada na C7 `as_known_at` poprawnie `None` (`context/03_results.json:524-531`). Mutant M1 nadal ginie na C1, C4×2 i C5 (`:384-391, 454-481`). Pokazuje to jednak, że ręczna analiza wymaga maszynowego potwierdzenia, zanim stanie się częścią prerejestracji.

## 3. Ocena kryteriów FC1–FC12

Kryteria są w `context/07_response.md:211-222`.

| Kryterium | Falsyfikowalne? | Próg uzasadniony REV-V0/H2? | Zastrzeżenie |
|---|---|---|---|
| **FC1** REV-V0 18/18 | Tak, po zamrożeniu D2 | Tak | Dziś ma dwa alternatywne progi (0.944 albo 1.000). Wyrocznia osiąga 1.000, a jedyny błąd bitemporal to C3 (`context/03_results.json:614-621, 926-934`), więc 18/18 jest osiągalne. Próg 0.944 z #39 (`context/01_issue-39.md:57`) to wynik sprzed poprawki i dopuszcza nową regresję. Projekt wyprowadzono ręcznie z tych 18 zapytań, więc FC1 sprawdza implementację, nie projekt. Etykiety nie przeszły niezależnej recenzji (`context/02_report.md:62`). |
| **FC2** 0 przecieków po `basis_ids` | Częściowo | Tak (zarejestrowany próg, `context/02_report.md:5`) | Detektor opiera się na samoopisie badanego kodu. Brak definicji `basis_ids` dla odpowiedzi `none`, `unknown` i `ambiguous`, a właśnie tam chowa się przeciek przez pola pochodne (przykład G1 z planu kończy się odpowiedzią „nic nie obowiązuje”). |
| **FC3** mutanty M1–M7 | Tak | Brak danych wcześniejszych, próg 100% naturalny | Nie określono, co znaczy „zabity” (błędna odpowiedź czy dowolny wyjątek) ani czy mutanty dotyczą modułu produkcyjnego. M2 i M7 mają po jednym przypadku zabijającym (X3, X4). Brak mutantów dla kilku reguł projektu (lista w R10). |
| **FC4** korekta ≠ sukcesja | Nie | Nie dotyczy | „Różne odpowiedzi” przechodzi także wtedy, gdy obie są błędne. Poprawna odpowiedź dla korekty w luce zależy od nierozstrzygniętych D3, D7 i X8. Brak sprawdzenia `valid_to`, choć #39 mówi „only one of them moves `valid_to`” (`context/01_issue-39.md:56`). |
| **FC5** append-only | Tak | Tak (`context/04_SCHEMA.md:25-28`) | Doprecyzować pomiar „0 zapisów w `memory/`”, np. montowanie tylko do odczytu albo skrót całego drzewa. |
| **FC6** totalność i zgodność na R | Nie | Brak | „Niewyjaśniona rozbieżność” i lista wyjątków tworzona po fakcie dają furtkę. R jest widoczny dla implementatora i nie ma etykiet. Wzorcem jest widok aktywny, który według planu sam realizuje regułę C3 (G6), więc zgodność z nim to test regresji, nie dowód poprawności. Kryterium koliduje z FC11. |
| **FC7** H2 dev TEMP-FUTURE 14/14 | Tak, po zamrożeniu adaptera | Tak (`context/05_manifest.json:14`, `context/06_response.md:80`) | To 14 instancji jednego szablonu, czyli jedna struktura. Adapter daje dużą swobodę badacza. Bramkę zawężono do jednej rodziny po obejrzeniu, które rodziny mapują się czysto. Autor resolwera znał rodziny (`context/01_issue-39.md:67,79`). |
| **FC8** held-out H ≥ 0.95 | Nie | Nie | Próg 0.95 nie pochodzi z żadnego wyniku: bitemporal miał 0.944, wyrocznia i resolwer H2 po 1.000. Bez n próg nic nie znaczy (przy n < 20 to 100%). Agregat może ukryć porażkę całej rodziny. „Każdy błąd sklasyfikowany przez recenzenta” pozwala ratować wynik po otwarciu. |
| **FC9** brak cichego zwycięzcy | Warunkowo | Tak (`context/02_report.md:5`) | Zależy od obecności rozwidleń w H. Semantyka rozwidlenia jest niespójna: krok 5 projektu mówi „ponad 1 rekord obejmujący T”, a lista kroków „ponad 1 następca” (`context/07_response.md:87,186`). |
| **FC10** determinizm | Tak | Nie dotyczy | Kryterium higieniczne o małej wartości dowodowej. |
| **FC11** głośna porażka na złej dacie | Nie | Brak | Zbiór „złych dat” i gramatyka poprawnych nie są określone. Plan sam podaje, że `created_at` z v1 nie jest walidowane (G5). Jeśli R zawiera nietypowy format, FC6 i FC11 są łącznie niespełnialne. |
| **FC12** uczciwość co do `current` | Nie | Nie dotyczy | „Próg” to obowiązek raportu, a warunek obalenia powtarza FC6. |

Sześć kryteriów (FC1, FC3, FC5, FC7, FC9, FC10) jest falsyfikowalnych wprost albo po zamrożeniu wskazanych decyzji, FC2 tylko częściowo. Pięć (FC4, FC6, FC8, FC11, FC12) nie ma operacyjnego warunku obalenia. Ponieważ jest wśród nich jedyne kryterium konfirmacyjne, oceniam `falsifiability_ok = false`.

Lista „co obala hipotezę” (`context/07_response.md:235`) nie zgadza się z listą FC. Pomija FC4, FC9, FC10 i FC11, a mówi o „krytycznym przecieku”, podczas gdy FC2 obala każdy przeciek.

## 4. Ochrona przed przeciekiem przyszłej informacji

| # | Element protokołu | Ryzyko |
|---|---|---|
| L1 | FC2, `basis_ids` | Detektor przecieku jest samoopisem badanej warstwy. Błąd w śledzeniu podstaw ukrywa przeciek. |
| L2 | FC2/FC3, przeciek przez pola pochodne (G1) | Wykrywa go tylko X3 (M2). Dla odpowiedzi abstynencyjnych brak definicji podstawy. |
| L3 | Krok 1 projektu, `known(tx)` po `created_at` | Jeśli `created_at` nie rośnie z pozycją w logu (import, replay, rozjazd zegarów), rekord dopisany później z wcześniejszą datą uchodzi za znany w T. Żadna kontrola po `created_at` tego nie wykryje. Raport wymienia te rodziny jako nietestowane (`context/02_report.md:63`). |
| L4 | Kontrola „`expected` i `note` usuwa runner” | Ślepota zależy od poprawności runnera. H2 trzyma zapytania i złote odpowiedzi osobno (`context/05_manifest.json:13,17`), więc wzorzec istnieje. |
| L5 | D1, wstrzykiwane `now` | Wartość `now` dla 6 istniejących zapytań `current` nie jest zamrożona, więc można ją dobrać pod 18/18. W projekcie `current(now)` jest tożsame z `valid_at(now)`, więc te zapytania nie dają niezależnego dowodu. |
| L6 | FC7, adapter H2 (D9) | Mapowanie pytania na typ zapytania i schematu H2 na v2 może być strojone pod wynik. Plan sam to zgłasza (`context/07_response.md:245`), ale protokół nie wymaga skrótu adaptera ani zakazu dostępu do złotych odpowiedzi. |
| L7 | Podział H, niezależność autora | Nie określono, co autor H może widzieć. Jeśli dostanie sekcję 4 planu i X1–X10, H będzie drugą kopią tej samej specyfikacji z tymi samymi błędami. Nie wiadomo, kto uruchamia H. Jeśli implementator, pieczęć jest fikcją. |
| L8 | FC8, klasyfikacja błędów po otwarciu | Błąd można przekwalifikować na błąd etykiety. |
| L9 | Podział R | Widoczny, bez etykiet. Parser i lista wyjątków mogą być dopasowywane do R aż do przejścia. |
| L10 | G5/FC11, znaczniki czasu jako łańcuchy | FC11 obejmuje tylko daty „złe”. Daty poprawne, lecz z różnymi offsetami, porównają się leksykograficznie źle i mogą wpuścić rekord z przyszłości. |
| L11 | Krok 5, łańcuch jako spójna składowa | Nie powiedziano, że składową wyznacza się wyłącznie z `known(tx)`. Uchwyt łańcucha przez rekord zapisany po T to kanał boczny. |
| L12 | Mapowanie `as_known_at(T) = as_of(T, T)` | Testowana jest tylko przekątna (V = K) i krawędź (K = ∞). Zamiana osi lub użycie złego parametru w filtrze nie jest wykrywalne na przekątnej. |

## 5. Nadmierne dopasowanie do znanych rodzin

- **D nie ma mocy konfirmacyjnej.** Korpus napisał implementator schematu (`context/02_report.md:6,62`), a projekt prześledzono ręcznie na tych samych 18 zapytaniach. FC1 to test akceptacyjny.
- **X1–X10 pisze autor projektu** z oczekiwaniami z własnych reguł (X5 „reguła D5”, X7 „D3”). X9 ma oczekiwanie alternatywne („flaga lub ambiguous”), więc nie da się go oblać. X to specyfikacja przez przykłady, nie dowód.
- **H2 dev jest jawny,** a `valid` to te same szablony. Plan słusznie nazywa go słabym held-outem, ale żadne kryterium go nie używa. To element protokołu bez funkcji.
- **Jedynym elementem o wartości konfirmacyjnej jest H,** a jego rozmiar, skład i niezależność są nieokreślone. REV-V0 pokrywa 6 z 11 rodzin (`context/02_report.md:63`). Plan nie wymaga, by H objął pozostałe pięć: nakładające się zakresy, rozjazd zegarów, niepewne przedziały, granice stref czasowych, replay/import.
- **Raportowanie łączy podziały** (FC2 liczy „D+X+H”). Wynik trzeba podawać osobno dla każdego podziału.

## 6. Czego brakuje, by wynik mógł potwierdzić lub obalić skuteczność

1. **Definicja „skuteczności”.** Plan miesza trzy twierdzenia: zgodność implementacji z zamrożoną semantyką na przypadkach konstruowanych, brak przecieku (nieinterferencja) i użyteczność na prawdziwych danych. Protokół testuje najwyżej dwa pierwsze. Plan sam przewiduje, że `valid_at` na R może dawać głównie `unknown` (`context/07_response.md:241`), a wartość osi leży wyłącznie w pytaniach historycznych (`context/02_report.md:48-50`). Dla R nie ma żadnej etykiety historycznej.
2. **Ramiona porównawcze.** REV-V0 mógł obalić schemat, bo porównywał ramiona (`context/02_report.md:10`). Jeśli na H ramię `valid_only` albo dzisiejszy widok aktywny też uzyskają około 1.0, wynik warstwy nic nie znaczy. H2 ma taką własność zapisaną w manifeście (`context/05_manifest.json:15`).
3. **Rozdział bramek akceptacyjnych od testu konfirmacyjnego.** Porażka na D lub X kończy się poprawką i ponownym przebiegiem, więc niczego nie obala. Jednorazowy jest tylko H. Plan nie mówi, co oznacza porażka H: powinna być trwałym wynikiem negatywnym pod nowym ID.
4. **Niezależny od implementacji test przecieku** (R2 poniżej).
5. **Niezależna recenzja etykiet D i polityki przedziałów.** Według planu to otwarte blokady manifestu REV-V0, a kolejność protokołu takiego kroku nie zawiera.
6. **Zamrożona prerejestracja ze skrótami:** fixture X, adapter H2, definicje mutantów, lista wyjątków R, wartości `now`, skrót H, commit implementacji przed otwarciem H.

## 7. Wymagane zmiany przed dopuszczeniem eksperymentu

- **R1 (cały protokół).** Zapisać hipotezę i podzielić kryteria na bramki akceptacyjne (powtarzalne, D+X) i test konfirmacyjny (jednorazowy, H plus nieinterferencja). Uzgodnić listę „co obala” z FC1–FC12. Porażkę H zapisać jako trwały wynik negatywny.
- **R2 (FC2; L1, L2).** Dodać test nieinterferencji dla każdego `as_known_at(T)` na D, X, H i R. Wynik na pełnym logu ma być identyczny z wynikiem na logu obciętym do `created_at ≤ T` oraz na logu z dopisanymi wrogimi zdarzeniami przyszłymi (sukcesja, korekta, rozwidlenie). `basis_ids` zostaje jako diagnostyka, z definicją także dla odpowiedzi abstynencyjnych.
- **R3 (FC8).** Przed pieczęcią ustalić:
  - rozmiar H i minimalną liczbę przypadków na rodzinę;
  - pokrycie pięciu nietestowanych rodzin albo ich jawne wyłączenie z zakresu wniosków;
  - definicję błędu krytycznego z zarejestrowanego progu: przeciek przyszłości, cichy zwycięzca, błędna rekonstrukcja sprzed korekty;
  - próg jako liczbę dopuszczalnych błędów, z punktacją trójdzielną (poprawna, błędny rekord, abstencja) i progami per rodzina.
  
  Rekomenduję 0 błędnych rekordów i exact 1.000, bo warstwa i wyrocznia są deterministyczne. Tolerancję zatwierdza właściciel.
- **R4 (FC8, FC1).** Uruchomić na X i H ramiona porównawcze: cztery ramiona REV-V0 i dzisiejszy widok aktywny. H jest ważny tylko wtedy, gdy każde ramię jednoosiowe oblewa z góry ustaloną część przypadków.
- **R5 (podział H; L7, L8).** Zoperacjonalizować niezależność i pieczęć:
  - autor H dostaje tylko SCHEMA, opis semantyki z #39, zamrożone decyzje i listę rodzin, bez sekcji 4 planu, X1–X10 i implementacji;
  - skrót H przechowuje koordynator, poza zasięgiem implementatora;
  - commit implementacji jest zamrożony przed otwarciem;
  - H uruchamia strona inna niż implementator;
  - spory o etykiety rozstrzyga się wyłącznie przed otwarciem, a późniejsze nie zmieniają werdyktu.
- **R6 (D1, D3, D5, D6, D8, X6–X9).** Zamrozić semantykę przed napisaniem etykiet H: wartość `now` dla każdego zapytania `current`, semantykę `unclassified`, `valid_to` przez poprawionego następcę, konwencję przedziałów i remisów, rozwidlenie (jedna z dwóch definicji), odpowiedź w luce po korekcie. X7 i X9 muszą mieć po jednej oczekiwanej odpowiedzi.
- **R7 (FC4).** Zastąpić „różne odpowiedzi” dokładnymi oczekiwanymi wynikami dla obu rodzajów supersesji. Dodać asercję o `valid_to` (ustawione tylko przy sukcesji) i o `as_known_at` sprzed zapisu korekty.
- **R8 (FC6, FC12).** Listę łańcuchów, w których `current()` może różnić się od widoku aktywnego, wyliczyć niezależnym skryptem z surowych zdarzeń i zahaszować przed implementacją. Każda rozbieżność spoza listy obala. FC12 scalić z FC6. Dodać raport pokrycia na R (udział `one`/`none`/`ambiguous`/`unknown`) z wnioskiem zapisanym z góry.
- **R9 (FC11, FC6; L10).** Przed zamrożeniem zrobić audyt formatów `created_at` i `valid_from` w R, tylko do odczytu. Zdefiniować gramatykę poprawnych znaczników i jawny korpus błędnych. Dodać przypadki z mieszanymi offsetami stref.
- **R10 (FC3).** Mutanty stosować do modułu produkcyjnego. „Zabity” oznacza błędną odpowiedź w nazwanym teście, nie dowolny wyjątek. Każdy mutant ma mieć co najmniej dwa niezależne przypadki zabijające. Dodać mutanty:
  - granica `created_at ≤ T` kontra `<`;
  - granica początku przedziału;
  - cichy zwycięzca rozwidlenia;
  - łańcuch po tagach;
  - `current` ignorujące czas ważności (błąd z sekcji 1.3 planu);
  - `valid_to` z odwołanego następcy;
  - zamiana osi.
- **R11 (FC7, H2 valid; L6).** Adapter H2 zamrozić skrótem przed uruchomieniem i odciąć od złotych odpowiedzi. Dla każdej z pięciu rodzin zapisać z góry przewidywanie i status (w zakresie lub poza, z powodem). Rodzina w zakresie, która zawiedzie, obala. Dla H2 valid zdefiniować kryterium albo usunąć go z protokołu. Pozostałych splitów H2 nie otwierać.
- **R12 (FC1, sekcja 4 planu).** Przed użyciem REV-V0 jako bramki przeprowadzić niezależną recenzję 18 etykiet i polityki przedziałów. Ręczny ślad 18/18 i przypisania mutantów potwierdzić maszynowo, w tym wyjaśnić rozbieżność C7/M1.
- **R13 (krok 1 projektu; L3, L11).** Zdefiniować oś transakcyjną przy niemonotonicznym `created_at`: pozycja w logu, odrzucenie albo flaga. Zrobić audyt monotoniczności na R. Zapisać, że składową łańcucha wyznacza się wyłącznie z `known(tx)`.
- **R14 (kontrola przecieków; L4).** Złote odpowiedzi trzymać w osobnym pliku, nigdy nieładowanym w procesie wywołującym warstwę. Punktacja jako osobny krok.

**Zalecane, nieblokujące:**
- zapytania pozaprzekątniowe (`known ≠ valid`) w X i H, albo jawne niewystawianie ich w API (L12);
- nieinterferencja i test różnicowy na losowych logach z zamrożonym ziarnem;
- doprecyzowanie pomiaru FC5.

## 8. Decyzje wymagające właściciela

Recenzja nie zmienia zatwierdzonej strategii. Poniższe punkty uzupełniają D1–D12 z planu.

- **O1.** Zakres wniosku: tylko zgodność i brak przecieku, czy także użyteczność na realnych danych. To drugie wymaga 10–20 pytań historycznych do kanonicznego logu, ręcznie oznaczonych przez właściciela.
- **O2.** Zaostrzenie progu z #39 (≥ 0.944) do 18/18 (D2). Rekomenduję: tak.
- **O3.** Tolerancja błędów na H: rekomendowane 0 błędnych rekordów i exact 1.000 zamiast 0.95.
- **O4.** Kto pisze i kto uruchamia H (D10). Rekomenduję autora innego niż implementator i autor planu oraz uruchomienie przez koordynatora.
- **O5.** D3, D5, D6, D8 oraz semantyka rozwidlenia i korekty w luce muszą zapaść przed pieczęcią H. To warunek wstępny, nie decyzje równoległe.
- **O6.** D7 (wzmocnienie piszącego). Jeśli zostaje poza #39, właściciel akceptuje, że wynik nie dowodzi wartości osi ważności dla nowych danych.
- **O7.** D4. Jeśli `search` i `is_active` zostają przy starej regule, raport nie może twierdzić, że C3 naprawiono w magazynie, tylko że w warstwie zapytań.
- **O8.** Definicja czasu transakcyjnego przy niemonotonicznym `created_at`.
- **O9.** Zły znacznik czasu: wyjątek dla całego magazynu czy `unknown` z flagą dla łańcucha. Decyzja rozstrzyga konflikt FC6/FC11.
- **O10.** Rola H2 (D9): które rodziny są w zakresie i czy wolno użyć splitów innych niż dev.
- **O11.** Czy niezależna recenzja etykiet REV-V0 (R12) ma zamknąć blokady nieaktualnego manifestu (D11), czy powstaje nowy manifest dla `PMLAB-REV-V0-002`.

```json
{
  "verdict": "revise",
  "falsifiability_ok": false,
  "summary": "Diagnoza C3 i projekt as_of(valid, known) są spójne z dostępnymi dowodami (context/03_results.json:604-621, 424-441; context/04_SCHEMA.md:71-78), a szkielet protokołu (zapieczętowany held-out, mutacje, nowe ID eksperymentu) jest właściwy. Plan nie może jednak jeszcze potwierdzić ani obalić skuteczności warstwy. Jedyne kryterium konfirmacyjne FC8 nie ma rozmiaru H, składu rodzin ani definicji błędu krytycznego, a próg 0.95 nie wynika z REV-V0 ani H2. FC4, FC6, FC11 i FC12 nie mają operacyjnego warunku obalenia. Detektor przecieku FC2 opiera się na samoopisie badanej warstwy (basis_ids). Plan porzucił ramiona porównawcze, które dawały REV-V0 falsyfikowalność. Niezależność i pieczęć H nie są zoperacjonalizowane. D i X to testy akceptacyjne bez mocy konfirmacyjnej, bo projekt wyprowadzono ręcznie z tych samych przypadków. Progi FC1 (18/18), FC2 (0 przecieków) i FC7 (14/14) są uzasadnione wcześniejszymi wynikami. Ograniczenie recenzji: miałem 7 z 22 plików cytowanych w planie, więc śladu w kodzie, luk G1-G13 i przypisań mutantów nie weryfikowałem. Znalazłem jedną rozbieżność: twierdzenie, że mutant M1 pada na C7, nie zgadza się z wynikiem ramienia valid_only (context/03_results.json:524-531). Wymaganych zmian jest 14, wszystkie bez kosztu i bez zmiany strategii.",
  "leakage_risks": [
    {"id": "L1", "element": "FC2 / basis_ids", "risk": "Detektor przecieku jest samoopisem badanej warstwy; błąd w śledzeniu podstaw ukrywa przeciek.", "mitigation": "R2: test nieinterferencji (obcięcie logu i wstrzyknięcie przyszłych zdarzeń)."},
    {"id": "L2", "element": "FC2, FC3 / przeciek przez pola pochodne (G1)", "risk": "Wykrywany tylko przez X3 (mutant M2); brak definicji basis_ids dla odpowiedzi none, unknown i ambiguous.", "mitigation": "R2, R10."},
    {"id": "L3", "element": "krok 1 projektu: known(tx) po created_at", "risk": "Przy niemonotonicznym created_at (import, replay, rozjazd zegarów; rodziny nietestowane wg context/02_report.md:63) rekord dopisany później uchodzi za znany w T.", "mitigation": "R13: polityka i audyt monotoniczności na R."},
    {"id": "L4", "element": "kontrola: expected i note usuwa runner", "risk": "Ślepota zależy od poprawności runnera.", "mitigation": "R14: osobny plik złotych odpowiedzi i osobny krok punktacji, jak w H2 (context/05_manifest.json:13,17)."},
    {"id": "L5", "element": "D1: wstrzykiwane now", "risk": "Niezamrożona wartość now dla 6 zapytań current to parametr do strojenia; current(now) jest tożsame z valid_at(now).", "mitigation": "R6: wartości now zamrożone w prerejestracji."},
    {"id": "L6", "element": "FC7 / adapter H2 (D9)", "risk": "Mapowanie schematu i typu zapytania może być strojone pod wynik; bramkę zawężono do jednej rodziny po obejrzeniu danych.", "mitigation": "R11: skrót adaptera, brak dostępu do złotych odpowiedzi, przewidywania per rodzina z góry."},
    {"id": "L7", "element": "podział H: niezależność autora i uruchomienie", "risk": "Autor znający sekcję 4 planu i X1-X10 powieli te same błędy; uruchomienie przez implementatora łamie pieczęć.", "mitigation": "R5."},
    {"id": "L8", "element": "FC8: klasyfikacja błędów przez recenzenta po otwarciu", "risk": "Przekwalifikowanie błędu warstwy na błąd etykiety ratuje wynik.", "mitigation": "R5: spory o etykiety tylko przed otwarciem."},
    {"id": "L9", "element": "podział R (FC6)", "risk": "R jest widoczny i bez etykiet; parser i lista wyjątków mogą być dopasowywane do R. Wzorzec (widok aktywny) sam realizuje regułę C3 wg G6.", "mitigation": "R8, R9."},
    {"id": "L10", "element": "G5 / FC11: znaczniki czasu jako łańcuchy", "risk": "Poprawne znaczniki z różnymi offsetami porównane leksykograficznie mogą wpuścić rekord z przyszłości; FC11 obejmuje tylko daty błędne.", "mitigation": "R9: gramatyka, normalizacja, przypadki z mieszanymi offsetami."},
    {"id": "L11", "element": "krok 5 projektu: łańcuch jako spójna składowa supersedes", "risk": "Składowa wyznaczona z pełnego logu albo uchwyt przez rekord zapisany po T to kanał boczny.", "mitigation": "R13: składowa wyłącznie z known(tx)."},
    {"id": "L12", "element": "mapowanie as_known_at(T) = as_of(T, T)", "risk": "Testowana tylko przekątna i krawędź known = koniec logu; zamiana osi w filtrze niewykrywalna na przekątnej.", "mitigation": "Zalecane: zapytania pozaprzekątniowe w X i H; mutant zamiany osi w R10."}
  ],
  "required_changes": [
    {"id": "R1", "target": "cały protokół; lista what_refutes", "change": "Zapisać hipotezę; podzielić kryteria na bramki akceptacyjne (powtarzalne, D+X) i test konfirmacyjny (jednorazowy, H plus nieinterferencja); uzgodnić listę obalającą z FC1-FC12 (dziś brak FC4, FC9, FC10, FC11; krytyczny przeciek kontra każdy przeciek); porażkę H zapisać jako trwały wynik negatywny."},
    {"id": "R2", "target": "FC2", "change": "Dodać test nieinterferencji dla każdego as_known_at(T) na D, X, H i R: wynik identyczny na logu obciętym do created_at <= T i na logu z dopisanymi wrogimi zdarzeniami przyszłymi. basis_ids tylko pomocniczo, z definicją także dla none, unknown i ambiguous."},
    {"id": "R3", "target": "FC8", "change": "Przed pieczęcią ustalić rozmiar H, minimum przypadków na rodzinę, pokrycie 5 nietestowanych rodzin (context/02_report.md:63) albo ich jawne wyłączenie, definicję błędu krytycznego z zarejestrowanego progu (context/02_report.md:5), próg jako liczbę dopuszczalnych błędów z punktacją trójdzielną i progami per rodzina. Rekomendacja: 0 błędnych rekordów i exact 1.000."},
    {"id": "R4", "target": "FC8, FC1", "change": "Uruchomić na X i H ramiona porównawcze (cztery ramiona REV-V0 i dzisiejszy widok aktywny); H ważny tylko, gdy każde ramię jednoosiowe oblewa z góry ustaloną część przypadków."},
    {"id": "R5", "target": "podział H", "change": "Autor H bez dostępu do sekcji 4 planu, X1-X10 i implementacji; skrót H u koordynatora; commit implementacji zamrożony przed otwarciem; H uruchamia strona inna niż implementator; spory o etykiety wyłącznie przed otwarciem."},
    {"id": "R6", "target": "D1, D3, D5, D6, D8, X6-X9", "change": "Zamrozić semantykę przed etykietami H: now dla każdego zapytania current, unclassified, valid_to przez poprawionego następcę, konwencja przedziałów i remisów, jedna definicja rozwidlenia, odpowiedź w luce po korekcie. X7 i X9 z jedną oczekiwaną odpowiedzią."},
    {"id": "R7", "target": "FC4", "change": "Zastąpić wymóg różnych odpowiedzi dokładnymi oczekiwanymi wynikami dla korekty i sukcesji; dodać asercje o valid_to (tylko sukcesja) i o as_known_at sprzed zapisu korekty."},
    {"id": "R8", "target": "FC6, FC12", "change": "Listę dozwolonych rozbieżności current() z widokiem aktywnym wyliczyć niezależnym skryptem i zahaszować przed implementacją; FC12 scalić z FC6; dodać raport pokrycia na R (one/none/ambiguous/unknown) z wnioskiem zapisanym z góry."},
    {"id": "R9", "target": "FC11, FC6", "change": "Audyt formatów created_at i valid_from w R (tylko odczyt) przed zamrożeniem; gramatyka poprawnych znaczników; jawny korpus błędnych; przypadki z mieszanymi offsetami; rozstrzygnięcie konfliktu FC6/FC11."},
    {"id": "R10", "target": "FC3", "change": "Mutanty na module produkcyjnym; zabity oznacza błędną odpowiedź w nazwanym teście, nie dowolny wyjątek; co najmniej 2 niezależne przypadki zabijające na mutanta; dodać mutanty: granica created_at <= T, granica początku przedziału, cichy zwycięzca rozwidlenia, łańcuch po tagach, current ignorujące czas ważności, valid_to z odwołanego następcy, zamiana osi."},
    {"id": "R11", "target": "FC7, H2 valid", "change": "Adapter H2 zamrożony skrótem i odcięty od złotych odpowiedzi; dla 5 rodzin z góry zapisane przewidywanie i status w zakresie lub poza; rodzina w zakresie, która zawiedzie, obala; dla H2 valid zdefiniować kryterium albo usunąć; pozostałych splitów nie otwierać."},
    {"id": "R12", "target": "FC1, sekcja 4 planu", "change": "Niezależna recenzja 18 etykiet REV-V0 i polityki przedziałów przed użyciem jako bramki; maszynowe potwierdzenie ręcznego śladu 18/18 i przypisań mutantów, w tym wyjaśnienie rozbieżności C7/M1 (context/07_response.md:98 kontra context/03_results.json:524-531)."},
    {"id": "R13", "target": "krok 1 i 5 projektu", "change": "Zdefiniować oś transakcyjną przy niemonotonicznym created_at (pozycja w logu, odrzucenie albo flaga); audyt monotoniczności na R; składowa łańcucha wyłącznie z known(tx)."},
    {"id": "R14", "target": "kontrola przecieków", "change": "Złote odpowiedzi w osobnym pliku, nieładowanym w procesie wywołującym warstwę; punktacja jako osobny krok."}
  ],
  "owner_decisions": [
    {"id": "O1", "decision": "Zakres wniosku: tylko zgodność i brak przecieku, czy także użyteczność na realnych danych (wymaga 10-20 ręcznie oznaczonych pytań historycznych do kanonicznego logu).", "recommendation": "Ograniczyć wniosek do zgodności i nieinterferencji, chyba że właściciel oznaczy próbkę."},
    {"id": "O2", "decision": "Zaostrzenie progu z #39 (>= 0.944) do 18/18 (D2).", "recommendation": "Tak."},
    {"id": "O3", "decision": "Tolerancja błędów na H (FC8).", "recommendation": "0 błędnych rekordów i exact 1.000 zamiast 0.95."},
    {"id": "O4", "decision": "Kto pisze i kto uruchamia H (D10).", "recommendation": "Autor inny niż implementator i autor planu; uruchamia koordynator."},
    {"id": "O5", "decision": "D3, D5, D6, D8 oraz semantyka rozwidlenia i korekty w luce.", "recommendation": "Rozstrzygnąć przed pieczęcią H; to warunek wstępny."},
    {"id": "O6", "decision": "D7: czy wzmocnienie piszącego wchodzi w zakres #39.", "recommendation": "Jeśli poza zakresem, przyjąć jawnie, że wynik nie dowodzi wartości osi ważności dla nowych danych."},
    {"id": "O7", "decision": "D4: search i is_active przy starej regule.", "recommendation": "Raport może twierdzić tylko, że C3 naprawiono w warstwie zapytań, nie w magazynie."},
    {"id": "O8", "decision": "Definicja czasu transakcyjnego przy niemonotonicznym created_at.", "recommendation": "Rozstrzygnąć po audycie R (R13)."},
    {"id": "O9", "decision": "Zły znacznik czasu: wyjątek dla całego magazynu czy unknown z flagą dla łańcucha.", "recommendation": "Rozstrzygnąć po audycie formatów (R9); decyzja usuwa konflikt FC6/FC11."},
    {"id": "O10", "decision": "Rola H2 (D9): które rodziny w zakresie i czy wolno użyć splitów innych niż dev.", "recommendation": "Status per rodzina zapisany z góry; pozostałych splitów nie otwierać."},
    {"id": "O11", "decision": "Czy recenzja etykiet REV-V0 (R12) zamyka blokady starego manifestu, czy powstaje nowy manifest dla PMLAB-REV-V0-002 (D11).", "recommendation": "Nowy manifest; stary i wyniki historyczne bez zmian."}
  ]
}
```

---

*Integration note (2026-11-14).* Imported unchanged in substance from the AAMR coordinator (task 9, source file `response.md`, SHA-256 of the original `3e46001344f1e5a0dc7aa9907e9dcac5ba3c6deab7ef9a762ecdf0a77561840b`). The text is the AI-written original, in Polish. The only edits are listed in `PROVENANCE.json`. Status: **REVIEW (AI)**. Nothing in it is an approved decision. See `README.md` in this directory.
