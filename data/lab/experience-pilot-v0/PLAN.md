# EXP-PILOT-0 (v1): czy pamięć doświadczeń poprawia działanie agenta

Status: wersja v1 po recenzji metodologicznej 2026-11-12, do akceptacji właściciela. Zastępuje `SPEC.md` (v0,
zachowany bez zmian obok). Nic nie zostało zaimplementowane ani uruchomione; BFCL nie został pobrany. Odstępstwa
od tego dokumentu wymagają dopisku w sekcji 14 przed pierwszym wywołaniem modelu, którego dotyczą.

## 0. Zmiany względem v0 i ich uzasadnienie

Hipotezy H1–H4 i progi decyzji z sekcji 11 v0 są bez zmian. Zmiany dotyczą ramion kontrolnych, operacjonalizacji
H3/H4, izolacji, checkera i budżetu. Wiersze 11 dodane w v1 są opisowe albo dotyczą tylko nowego ramienia R+.

| Nr | Zmiana | Dlaczego |
|---|---|---|
| Z1 | Nowe ramię R+ (pula A tylko `PASSED`, zawsze 2 najlepsze, bez bramki). R+–R mierzy filtr, S–R+ mierzy bramkę | R i S w v0 różnią się naraz filtrem, bramką, liczbą wstrzykniętych elementów i etykietami w bloku; H4 nie dało się przypisać mechanizmowi |
| Z2 | N′ zredukowane do kontroli determinizmu na 5 zadaniach; pełne N′ tylko, gdy kontrola wykaże różnicę | Przy `temperature 0` N′ najpewniej powtórzy N bit w bit (smoke test 2026-11-01: identyczne powtórzenia), więc 270 wywołań dałoby próg szumu 0. Zaoszczędzony budżet idzie na R+ |
| Z3 | Warstwy H3 liczone względem zawartości pamięci (pula A), nie tylko wzorców treningu; dodana warstwa „ekspozycji" (co ramię faktycznie pokaże) i podwarstwa C-reguła | „Rozwiązania nie ma w pamięci" (H3) dotyczy pamięci, a dla R/S pamięć to własne trajektorie agenta, nie wzorce. Retrieval jest deterministyczny, więc ekspozycję można policzyć przed E2 |
| Z4 | Porównania turowe tylko na turach osiągniętych w obu porównywanych ramionach; minimum 10 tur w warstwie C | Odsetek wśród tur osiągniętych w v0 zależy od wyniku wcześniejszych tur (selekcja po wyniku) |
| Z5 | Placebo: pula F tylko z tur używających wyłącznie funkcji GorillaFileSystem; długość bloku dopasowana do R; jednoznaczne ziarno | Zadania 0–49 mają klasy dodatkowe wspólne z testem (Twitter/Message/Ticket/Math): placebo uczyłoby tych API. Różna długość bloku i niejednoznaczny `indeks_tury` |
| Z6 | Unikalna `model_name` dla każdego wywołania executora i checkera; checker dostaje tylko wykonane wywołania; kontrola zgodności powtórki z przebiegiem | Executor BFCL trzyma instancje środowisk w `globals()` pod nazwą `{model_name}_{test_entry_id}_{klasa}`. Druga ocena tego samego zadania w jednym procesie (etykietowanie prefiksów 5.1, dwa odtworzenia G1, ramiona) startuje ze stanu końcowego poprzedniej |
| Z7 | Reguła dla wyjścia niepoprawnego jako całość (nieparsowalny JSON, `done_reason = length`); doprecyzowana walidacja typów | v0 definiuje tylko niepoprawne pojedyncze wywołanie |
| Z8 | Test jednostkowy szczelności oparty na pochodzeniu elementów, nie na braku napisów | W warstwie A blok pamięci legalnie zawiera napis identyczny z wzorcem testu (z innego zadania); test z v0 musiałby nie przechodzić |
| Z9 | G2 mierzy zajętość VRAM i czas przy wybranym `num_ctx`; po E1b projekcja kosztu z pomiaru; E3 tylko przy wystarczającej rezerwie | 14B zajmował 11,2 z 12,3 GiB już przy kontekście 4096; przy 8192 cache KV rośnie o ok. 0,75 GiB, więc częściowe przeniesienie na CPU jest prawdopodobne, a z nim kilkukrotne spowolnienie |
| Z10 | Statyczne odczyty w E0 (po pobraniu): komunikaty błędów `startEngine`, metody korzystające z `_random`, typy błędów checkera, tury z pustym wzorcem, wspólne konfiguracje początkowe | Kilka twierdzeń o BFCL w tej recenzji pochodzi z mojej znajomości kodu, nie z odczytu przypiętego commitu; muszą zostać potwierdzone przed E1a |

Sprawdzone w kodzie `origin/main` (`1b673d3`) bez uruchamiania: `LocalReader.ask` przyjmuje listę wiadomości i
schemat w polu `format`, zapisuje `prompt_eval_count`, nie ponawia i ma własny limit `max_calls` / `max_seconds`
(funkcja `validate` tego modułu z limitem 220 wywołań dotyczy pilota NIE i nie wolno jej używać). Kernel 0.2.0 ma
klucze profilu `lex_tau`, `min_evidence`, `names`, `timeout_ms` (dopuszcza nieskończoność) oraz `k` z domyślną
wartością 3; profil podany jako słownik dziedziczy z profilu `kernel`, nie `lexical`.

## 1. Pytanie i hipotezy (bez zmian)

Pytanie: czy agent na lokalnym modelu, który dostaje własne doświadczenia z wcześniejszych zadań, częściej
doprowadza środowisko do poprawnego stanu w nowych zadaniach niż bez pamięci, i czy selektywne użycie pamięci
zmniejsza szkody.

- H1 (pamięć pomaga): R lub S ma wyższy odsetek rozwiązanych zadań testowych niż N.
- H2 (to nie efekt promptu): P nie daje takiego zysku.
- H3 (to nie samo kopiowanie): zysk występuje także w turach, których dokładnego rozwiązania nie ma w pamięci.
- H4 (selektywność): S ma mniej przypadków szkody niż R przy nie gorszym wyniku.

Rozkład H4 (v1, opisowy): H4a filtr sukcesów = R+ wobec R; H4b bramka = S wobec R+. R+ nie jest ramieniem H1.

Pilot rozstrzyga decyzję „skalować / poprawić pamięć / porzucić ten benchmark" (sekcja 11). Nie jest
potwierdzeniem żadnej hipotezy: 30 zadań testowych wykrywa tylko duże efekty.

## 2. Środowisko i dane

Benchmark: BFCL multi-turn base, domena Vehicle Control.

- Repozytorium: `ShishirPatil/gorilla`, katalog `berkeley-function-call-leaderboard/bfcl_eval`, licencja
  Apache-2.0. Przypiąć commit `6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`; sprawdzić, że istnieje, i zapisać
  sha256 każdego pobranego pliku.
- Pliki: `data/BFCL_v4_multi_turn_base.json`, `data/possible_answer/BFCL_v4_multi_turn_base.json`, cały
  `data/multi_turn_func_doc/`, cały `eval_checker/multi_turn_eval/`.
- Zadania pilota: `multi_turn_base_50` … `multi_turn_base_99` (klasa główna `VehicleControlAPI`).
- Pula placebo: `multi_turn_base_0` … `multi_turn_base_49`, tylko trajektorie wzorcowe, z filtrem z 5.2.

Kodu środowisk i checkera nie wolno zmieniać. Dozwolona jest wyłącznie korekta ścieżek importu albo izolowane
środowisko wirtualne z instalacją przypiętego checkoutu.

### 2.1 Co wiadomo o benchmarku (bez zmian względem v0; odczyt plików z `main`)

- Zadanie ma 1–7 tur (171 tur w 50 zadaniach, średnio 3,4; 2,1 wywołania wzorcowego na turę).
- Ocena po każdej turze: publiczne atrybuty stanu wobec stanu po wzorcu oraz zawieranie wyników wywołań
  wzorcowych w wynikach agenta. Zadanie rozwiązane, gdy wszystkie tury przechodzą oba testy.
- `startEngine` zwraca błąd przy otwartych drzwiach lub niewciśniętym do końca hamulcu; opis funkcji o tym nie
  mówi. Sekwencja drzwi → hamulec → start występuje we wzorcach 44 z 50 zadań.
- 84 ze 171 tur (49%) ma identyczną listę wywołań wzorcowych jak tura innego zadania; 139 (81%) ten sam szkielet.
- Etykiety były wielokrotnie poprawiane; bramka G1.
- Liczby EvoMemBench nie są punktem odniesienia.

### 2.2 Do potwierdzenia statycznie w E0, po pobraniu, bez modelu (v1, Z10)

Wynik każdego punktu trafia do `e0-static.json` przed E1a.

1. Dosłowne komunikaty błędów `startEngine`. Jeśli wskazują brakujący warunek (drzwi, hamulec), reguła jest
   odkrywalna w epizodzie z samego błędu; wtedy oczekiwany efekt pamięci dotyczy głównie liczby błędów i kroków,
   a mniej rozwiązanych zadań. To nie zmienia progów, ale musi być zapisane przed E1a jako znane ryzyko mocy.
2. Mechanizm nazw instancji w executorze (`globals()`, klucz z `model_name` i `test_entry_id`) oraz to, jak
   checker nazywa instancje ewaluacji i wzorca. Od tego zależy 8.1.
3. Lista typów błędów zwracanych przez `multi_turn_checker` i liczba tur z pustą listą wzorcową w zadaniach 50–99.
4. Metody klas środowisk używające losowości (`_random` lub podobne) i zadania, których wzorzec je wywołuje.
   Wynik takich wywołań zależy od liczby wcześniejszych losowań, więc dodatkowe wywołania agenta mogą zmienić
   wyniki porównywane w teście odpowiedzi. Flaga `random_dependent` na turę.
5. Dla każdego zadania 50–99: czy `initial_config` każdej klasy jest identyczny z konfiguracją innego zadania.
   Flaga `same_world` na zadanie testowe (po podziale: identyczna konfiguracja z jakimś zadaniem treningowym).

## 3. Model i transport

- Model: `qwen2.5:14b-instruct`, digest `7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6`,
  przez Ollama. Ten sam model, opcje i prompt systemowy we wszystkich ramionach.
- Opcje: `temperature 0`, `seed 7`, `num_predict 512`, bez strumieniowania. `num_ctx` wybierane jak w v0: L =
  znaki najdłuższego promptu systemowego wśród 50 zadań; `L/3 + 3000 ≤ 7600` → 8192, inaczej 12288. Wartość
  wspólna, w `config.json`.
- Klient: klasa `LocalReader` z `scripts/nie_reader_pilot.py` bez zmian. Funkcji `validate` tego modułu nie
  używać. Jedna instancja `LocalReader` na etap, z `max_calls` i `max_seconds` równymi pozostałej części limitu
  twardego.
- Żadnych płatnych API, innego modelu, sędziego LLM ani wywołań modelu do budowy pamięci.

## 4. Pętla agenta (identyczna we wszystkich ramionach)

Dla każdej tury zadania:

1. Do historii trafia wiadomość użytkownika: opcjonalny blok pamięci (5.4), potem treść prośby.
2. Krok: wywołanie modelu z całą historią. Wyjście wymuszone schematem JSON w polu `format`:
   `{"calls":[{"name": <enum nazw dostępnych funkcji>, "arguments": {…}}]}`, `maxItems` 6,
   `additionalProperties: false`.
3. Wyjście jako całość (v1, Z7): jeśli tekst nie parsuje się jako JSON zgodny ze schematem albo
   `done_reason = "length"`, nic nie jest wykonywane, krok się liczy, a do historii trafia
   `RESULTS: [{"error": "invalid output: response is not valid JSON for the required schema"}]`. Powrót do kroku 2.
4. Pusta lista `calls` kończy turę. W przeciwnym razie każde wywołanie jest walidowane: nazwa z listy; obecne
   wszystkie parametry wymagane; brak kluczy spoza opisu; typy JSON zgodne z opisem, przy czym liczba całkowita
   jest akceptowana tam, gdzie opis wymaga liczby zmiennoprzecinkowej, i żadna inna konwersja nie jest robiona.
   Niepoprawne nie jest wykonywane; jego wynikiem jest `{"error": "invalid call: …"}`. Poprawne są zamieniane na
   napis `nazwa(k=repr(v), …)` i wykonywane w kolejności przez executor BFCL. Do `eval` nie trafia żaden tekst
   modelu poza tak zbudowanym napisem.
5. Wyniki wracają jako wiadomość użytkownika `RESULTS: [...]`; każdy wynik obcięty do 800 znaków ze znacznikiem
   `...[truncated]`. Powrót do kroku 2.
6. Limit 8 kroków na turę. Przekroczenie kończy epizod jako nierozwiązany (`forced_termination`).

Prompt systemowy, renderowanie listy funkcji, usuwanie bloku pamięci z poprzednich tur i kontrola kontekstu: bez
zmian względem v0 (tekst promptu dosłownie jak w v0 sekcja 4). Kontrola po E1b (≥ 10% epizodów treningowych z
największym promptem + 1 000 tokenów na limicie → stop przed E2) bez zmian.

## 5. Pamięć

### 5.1 Jednostka doświadczenia (bez zmian)

Jedna tura jednego zadania treningowego: treść prośby, wykonane wywołania z wynikami (także błędami) w kolejności,
etykieta z oficjalnego checkera na prefiksie tur: `PASSED`, `FAILED` dla pierwszej nieudanej tury, `UNVERIFIED`
dla tur po niej. Każde wywołanie checkera dla prefiksu używa własnej `model_name` (8.1).

### 5.2 Skąd pochodzą doświadczenia

- Pula A (własna): wszystkie tury z przebiegów N na 20 zadaniach treningowych. A⁺ = tury A z etykietą `PASSED`.
- Pula G (wyrocznia): tury wzorców tych samych 20 zadań treningowych wykonanych w środowisku, etykieta `PASSED`.
- Pula F (placebo, v1, Z5): tury wzorców zadań 0–49, w których każde wywołanie wzorcowe jest metodą klasy
  `GorillaFileSystem` i żadna nazwa funkcji tej tury nie występuje na liście funkcji żadnego zadania 50–99. Liczebność
  F po filtrze zapisać w E0; przy mniej niż 40 turach stop i raport.

Pule są zapisywane jako pliki JSONL z sha256 i zamrożone przed pierwszym epizodem testowym. Każde ramię buduje
własny indeks z pliku swojej puli; sha256 puli i profil wyszukiwania trafiają do logu każdego epizodu. W fazie
testowej nic nie jest dopisywane.

### 5.3 Wyszukiwanie

Silnik: `scripts/wmb/kernel/memory_kernel.py` 0.2.0 bez zmian. Profil podawany jako pełny słownik z
`embed: "off"`, `names: False`, `timeout_ms: inf`, `k: 2` (domyślne `k` kernela to 3). Element indeksu:
`Item(kind="event", origin="account_history", text=<treść prośby tury treningowej>)`, daty rosnące w kolejności
zadań treningowych, `now` późniejsze od wszystkich. Zapytanie: treść prośby bieżącej tury testowej.

- Bez bramki (R na A, R+ na A⁺, O na G): `lex_tau = 1e-9`, `min_evidence = 0`. Element bez żadnego wspólnego
  słowa z zapytaniem nie przechodzi także wtedy; liczba wstrzykniętych elementów jest logowana.
- Z bramką (S na A⁺): `lex_tau` i `min_evidence` z kalibracji. Gdy nic nie przechodzi, tura bez bloku.

Kalibracja bramki bez zmian względem v0 (leave-one-task-out na A⁺, siatka `lex_tau ∈ {0.10, 0.15, …, 0.50}` ×
`min_evidence ∈ {0.8, 1.4}`, F1, remisy na wyższe `lex_tau`, potem wyższe `min_evidence`), wynik w
`gate-calibration.json` przed E2.

### 5.4 Blok pamięci (bez zmian)

Szablon jak w v0; elementy w kolejności rankingu, każdy obcięty do 1 400 znaków.

### 5.5 Dobór placebo (v1, Z5)

Dla tury testowej t niech `len_R(t)` = długość w znakach bloku, który pokazałoby R (retrieval jest deterministyczny,
więc liczy się to przed E2), a `n_R(t)` = liczba jego elementów. P losuje `n_R(t)` elementów z F generatorem
`random.Random(int(sha256(f"{task_id}:{turn_index}").hexdigest()[:16], 16))`, najwyżej 50 losowań bez zwracania
par, i bierze pierwszą próbkę o długości bloku w przedziale `len_R(t) ± 15%`, a gdy żadna nie trafi, próbkę
najbliższą. Przy `n_R(t) = 0` P nie wstrzykuje. Wybór placebo dla wszystkich tur jest zapisany w
`placebo-plan.json` przed E2.

## 6. Ramiona

| Ramię | Pula | Wstrzyknięcie | Po co |
|---|---|---|---|
| N | — | brak bloku | poziom bazowy |
| N′ (v1) | — | brak bloku; dokładne powtórzenie N na pierwszych 5 zadaniach testowych, przeplecione z innymi ramionami jak w E2 | kontrola determinizmu; pełne 30 zadań tylko według 8.3 |
| P | F | zawsze, `n_R(t)` elementów dobranych według 5.5 | placebo: format, długość, przykłady wywołań bez wiedzy o domenie testu |
| R | A | zawsze, 2 najlepsze | proste wyszukiwanie doświadczeń |
| R+ (v1) | A⁺ | zawsze, 2 najlepsze | izoluje filtr sukcesów (R+–R) i bramkę (S–R+) |
| S | A⁺ | tylko powyżej bramki | selektywne użycie |
| O (warunkowe) | G | zawsze, 2 najlepsze | sufit: doskonałe doświadczenia |

Ramiona H1 to nadal R i S. O uruchamiane tylko, gdy ani R, ani S nie przekroczy N o 3 zadania, i tylko przy
rezerwie z 8.4. Czwarta komórka układu 2×2 („wszystkie etykiety, z bramką") nie wchodzi do pilota; jest pierwszym
dodatkiem przy skalowaniu.

## 7. Podział danych i szczelność

- Podział bez zmian: V z G1 sortowane rosnąco, `random.Random(20261112).shuffle`, 20 trening, 30 test; przy
  |V| < 50 mniejszy test, przy |V| < 44 stop. Podział losowy po zadaniach zostaje, bo zmiana na podział
  grupowany zmieniłaby populację H1; czystszy test H3 to zadanie dla skalowania (sekcja 11).
- Podział i lista wykluczeń commitowane przed pierwszym wywołaniem modelu.
- Model nigdy nie widzi trajektorii wzorcowych zadania, które rozwiązuje. Żadna pula nie zawiera tur zadań
  testowych. Wzorce testu czyta wyłącznie checker po epizodzie oraz kod warstw 9.3 przed E2, bez modelu.
- Parametry bramki zależą tylko od treningu. Prompty, szablony i progi nie zmieniają się po pierwszym epizodzie
  testowym.
- Testy jednostkowe (v1, Z8): każdy element każdej puli ma `source_task_id` spoza zbioru testowego; każdy element
  pokazany w epizodzie testowym ma pochodzenie z puli swojego ramienia (sha256 zgodny); prompt systemowy i schemat
  wyjścia identyczne między ramionami; blok pamięci w limicie znaków; placebo nie zawiera funkcji z list zadań
  testowych; dwie oceny tego samego zestawu wywołań w jednym procesie dają ten sam wynik (8.1).

## 8. Etapy, bramki i kryteria przerwania

| Etap | Co | Wywołania | Bramka (niespełniona = stop i raport) |
|---|---|---|---|
| E0 | Vendoring, renderer, pętla, odczyty 2.2, testy na fałszywym modelu | 0 | testy przechodzą; `e0-static.json` zapisany; \|F\| ≥ 40 |
| G1 | Odtworzenie wzorców 50 zadań VC dwa razy, każde pod inną `model_name` | 0 | jak w v0; stop przy > 5 wykluczeniach |
| G2 | Transport: 3 wywołania ze znaną odpowiedzią + 1 wywołanie z najdłuższym promptem systemowym | 4 | 3 z 3 poprawne; `/api/ps`: `size_vram = size` (cały model na GPU) przy wybranym `num_ctx`; zmierzony czas wywołania zapisany |
| E1a | N na pierwszych 10 zadaniach treningowych | ok. 100 | jak w v0 (niepoprawne wyjście lub wywołanie ≤ 10%; brak `context_overflow`) |
| E1b | N na pozostałych 10; pule A, A⁺, G, F; kalibracja; warstwy 9.3; plan placebo; projekcja 8.4 | ok. 100 | jak w v0 (N 2–16 z 20; ≥ 10 tur `PASSED`) oraz projekcja 8.4 |
| E2 | Test: N, P, R, R+, S na 30 zadaniach i N′ na 5 | ok. 1 395 | — |
| E3 | Warunkowo O na 30 zadaniach | ok. 270 | rezerwa 8.4 |

Jeśli w G2 model nie mieści się w całości na GPU, stop przed E1a i raport z pomiarem; decyzję (mniejszy
`num_ctx` z przeliczeniem 4, kwantyzacja cache KV, akceptacja spowolnienia) podejmuje właściciel i dopisuje się ją
do sekcji 14.

### 8.1 Izolacja środowisk i checkera (v1, Z6)

- Każde wywołanie executora i checkera dostaje unikalną `model_name`:
  `xp0_<etap>_<ramię>_<zadanie>_<cel>_<licznik>` (cel: `live`, `label<k>`, `g1a`, `g1b`, `eval`), po zamianie
  znaków `-./` na `_`. Żadna nazwa nie jest użyta dwa razy w jednym procesie; kod to sprawdza i przerywa przebieg.
- Każdy epizod dostaje głęboką kopię wpisu zadania.
- Checker dostaje wyłącznie wywołania faktycznie wykonane, pogrupowane w tury i kroki; wywołania odrzucone przez
  walidację i kroki z niepoprawnym wyjściem nie trafiają do checkera.
- Checker odtwarza wywołania w świeżej instancji. Dla każdego wywołania porównuje się wynik z przebiegu na żywo z
  wynikiem odtworzenia; różnica daje flagę epizodu `replay_mismatch`. Epizody z flagą zostają w wynikach i są
  raportowane osobno; nie są wykluczane.
- Miara „sam stan" (9.1) używa oficjalnej funkcji sprawdzania stanu z checkera w każdej turze, we własnej pętli;
  miara główna używa `multi_turn_checker` bez zmian.

### 8.2 Kolejność i przerwania

- Kolejność w E2: zadania w kolejności podziału; dla każdego zadania ramiona (z N′ dla pierwszych 5) w kolejności
  `random.Random(20261112 + indeks_zadania).shuffle`. Każdy epizod od świeżego stanu.
- Błąd transportu lub przekroczenie limitu przerywa przebieg bez ponowienia. Dozwolone powtórzenie całego ramienia
  od zera pod nowym identyfikatorem; przerwany przebieg zostaje w archiwum.
- Jeśli E2 zostanie przerwane, porównania parami obejmują zadania ukończone we wszystkich ramionach; zadanie
  niedokończone jest raportowane i nie wchodzi do porównań.
- Reguła dla E1b przy < 2 rozwiązanych (miarą główną staje się postęp, gdy średni postęp ≥ 0,25) i stop przy > 16:
  bez zmian.

### 8.3 Kontrola determinizmu (v1, Z2)

Jeśli na 5 zadaniach N′ ma tę samą sekwencję tekstów odpowiedzi modelu co N we wszystkich epizodach, N uznaje się
za deterministyczne: próg szumu = 0, a Szkoda/Pomoc (9.2) liczy się względem samego N. Jeśli którykolwiek epizod
się różni, N′ biegnie na pozostałych 25 zadaniach (ok. 225 wywołań) i obowiązują definicje v0 (N i N′).

### 8.4 Budżet i projekcja (v1, Z9)

- Limit twardy bez zmian: 2 000 wywołań i 6 godzin (8 godzin przy `num_ctx = 12288`).
- Planowane: G2 4 + E1 ok. 200 + E2 ok. 1 395 = ok. 1 600 wywołań. Przy pełnym N′ ok. 1 825. E3 ok. 270.
- Po E1b, bez modelu: m = średnia liczba wywołań na epizod N w treningu, s = średni czas wywołania. Projekcja E2 =
  `m × (5 × 30 + 5) × 1,15`. Jeśli wykorzystane + projekcja > 2 000 wywołań albo czas projekcji przekracza limit
  czasu, stop przed E2 i raport.
- E3 startuje tylko, gdy pozostały limit ≥ `m × 30 × 1,2` wywołań i pozostały czas wystarcza według s; inaczej O
  jest odkładane i raportowane jako niewykonane z powodu budżetu.
- Uzasadnienie liczby 1 395: m ≈ 9 (3,4 tury × ok. 2,6 kroku; minimum to 2 kroki na turę, bo tura kończy się
  pustą listą). Przy 3,5 kroku na turę m ≈ 12 i E2 ≈ 1 860, co przekracza limit razem z E1; dlatego projekcja z
  pomiaru, a nie z założenia.

## 9. Miary

### 9.1 Skuteczność (bez zmian)

Główna: zadania testowe rozwiązane według oficjalnego checkera. Postęp, „sam stan", liczby błędów, niepoprawnych
wywołań, niepoprawnych wyjść (v1) i kroków.

### 9.2 Szkoda

- Szkoda(X), Pomoc(X) jak w v0; przy determinizmie (8.3) względem samego N.
- Dla każdej szkody: indeks tury, typ błędu checkera, funkcje agenta spoza wzorca, elementy pamięci pokazane w tej
  turze.
- Dla S: odsetek tur bez wstrzyknięcia. Dla R, R+, S: Szkoda na 100 tur ze wstrzyknięciem (v1).
- Rozkład H4 (v1, opisowo): Szkoda(R+) − Szkoda(R) przypisana filtrowi; Szkoda(S) − Szkoda(R+) przypisana
  bramce, z zastrzeżeniem, że bramka zmniejsza też samą ekspozycję.

### 9.3 Warstwy tur testowych (liczone bez modelu po E1b, przed E2; v1, Z3, Z4)

Właściwość wzorców (jak v0, ważna dla O):

- GT-A „powtórka": lista wywołań wzorcowych tury (z argumentami) identyczna z listą wzorcową tury treningowej.
- GT-B „ta sama procedura": ten sam szkielet nazw, inne argumenty. GT-C „nowa": szkieletu nie ma w treningu.

Zawartość pamięci (główna operacjonalizacja H3 dla R, R+, S):

- M-A: w A⁺ jest tura, której wykonana lista wywołań bez wywołań z błędem jest identyczna z listą wzorcową tury
  testowej. M-B: ten sam szkielet, inne argumenty. M-C: ani jedno, ani drugie.
- C-reguła: tury M-C, których wzorzec zawiera `startEngine` (albo inną funkcję z warunkiem wstępnym potwierdzonym
  w 2.2). To jedyna warstwa, w której zysk wskazywałby na przeniesienie reguły, a nie procedury.

Ekspozycja (osobno dla każdego ramienia z pamięcią; deterministyczna, więc znana przed E2):

- E-dokładna: pokazany blok zawiera dokładną listę wzorcową tury; E-szkielet: zawiera szkielet; E-brak: żadne;
  E-pusta: blok nie został wstrzyknięty.

Flagi na turę lub zadanie z 2.2: `random_dependent`, `same_world`.

Raportowanie: dla każdej warstwy i pary (X, N) odsetek tur zaliczonych wyłącznie na turach osiągniętych zarówno w
X, jak i w N, oraz liczba takich tur. Liczebności wszystkich warstw zapisać przed E2. H3 jest nierozstrzygalne w
pilocie, gdy w M-B jest mniej niż 15 tur albo w M-C mniej niż 10 tur osiągniętych w obu ramionach pary (próg 15
dla B z v0; minimum dla C dodane, bo bez niego 10 pp mogłoby oznaczać jedną turę).

### 9.4 Koszt (bez zmian)

## 10. Analiza

- Porównania parami na tych samych zadaniach: R–N i S–N (dokładny McNemar jednostronny), P–N, S–R, R+–R, S–R+,
  R+–N (dwustronny); N–N′ tylko przy pełnym N′. Bez poprawek na wielokrotność; wszystkie pary raportowane.
- Próg szumu: liczba zadań o różnym wyniku w N i N′ (0 przy determinizmie 8.3). Opisowo raportowana też liczba
  zadań o różnym wyniku w P i N jako wrażliwość na zaburzenie promptu.
- Raportowane wszystkie zadania i ramiona, także przebiegi przerwane i flagi `replay_mismatch`. Żadnych wykluczeń
  po obejrzeniu wyników.

## 11. Reguły decyzji (ustalone z góry)

Wiersze v0 bez zmian; „warstwy B i C" w wierszu „Tylko zapamiętywanie" oznaczają M-B i M-C z 9.3, liczone na
turach osiągniętych w obu ramionach pary.

| Wynik | Warunek | Decyzja |
|---|---|---|
| Pamięć działa | R lub S rozwiązuje ≥ 6 zadań więcej niż N, McNemar p ≤ 0,05, różnica większa niż próg szumu, a P najwyżej 2 zadania więcej niż N | skalować: domeny BFCL o małym udziale powtórek (system plików 6%, podróże 19%), więcej zadań, czwarta komórka 2×2, podział grupowany po szkieletach |
| Tylko zapamiętywanie | warunek wyżej spełniony, ale w M-B i M-C odsetek zaliczonych tur R i S nie przewyższa N o co najmniej 10 pp | nie ogłaszać uczenia; następny test w domenie o małym udziale powtórek |
| Efekt promptu | P rozwiązuje ≥ 3 zadania więcej niż N | zysk R i S liczyć względem P, nie N |
| Selekcja pomaga | Szkoda(S) < Szkoda(R) i S rozwiązuje co najmniej tyle zadań co R minus 1 | zachować bramkę; w pilocie wynik opisowy, z rozkładem H4a/H4b |
| Brak efektu, jest sufit | R i S najwyżej 2 zadania ponad N, a O ≥ 6 ponad N | poprawiać pamięć, nie benchmark |
| Brak efektu, brak sufitu | R, S i O najwyżej 2 zadania ponad N | nie skalować, zmienić model lub środowisko |
| Pamięć szkodzi | R lub S rozwiązuje ≥ 3 zadania mniej niż N | opisać przypadki; nie skalować bez zmiany mechanizmu |
| (v1) Tylko R+ | R+ ≥ 6 ponad N, a R i S nie spełniają wiersza „Pamięć działa" | wynik eksploracyjny: filtr bez bramki do potwierdzenia na nowych zadaniach; nie ogłaszać H1 |
| (v1) O pominięte | warunek uruchomienia O spełniony, ale brak rezerwy 8.4 | wiersze „sufit" nierozstrzygnięte; decyzja właściciela o dodatkowym budżecie |

## 12. Czego pilot nie pokaże (v0 plus)

- Uogólnienia poza jedną domenę z jedną dominującą ukrytą regułą.
- Małych efektów (wykrywalne różnice rzędu 20 pp i więcej).
- Przewagi nad innymi systemami pamięci, wartości destylacji, konsolidacji ani uczonej użyteczności.
- Poprawności etykiet BFCL ponad G1.
- (v1) Czy zysk wynika z trafności wyszukiwania, czy z samego zanurzenia w doświadczeniach tej domeny: brak ramienia
  „losowe doświadczenia z A". Kandydat na skalowanie.
- (v1) Rozdzielenia „bramka wybiera trafnie" od „bramka rzadziej wstrzykuje": brak ramienia z losową maską o tej
  samej częstości.

## 13. Miejsce w projekcie i artefakty

Bez zmian względem v0, z dodanymi plikami `e0-static.json`, `placebo-plan.json`, `exposure.json` w
`data/lab/experience-pilot-v0/` i wpisem `PLAN.md` jako kopią v1. Kolejność commitów: (1) kod, testy,
konfiguracja, plan i `e0-static.json` przed E1a; (2) podział, pule z sha256, kalibracja, warstwy, ekspozycja i plan
placebo przed E2; (3) zamrożenie surowych wyników; (4) wyniki i README. Bez scalania do `main`, bez zmian w PR #105,
kernelu, NIE i zamrożonych plikach.

## 14. Dziennik odstępstw

Wpisy przed pierwszym wywołaniem modelu (2026-11-12, implementacja Claude Opus 5.5). Żaden nie zmienia hipotez, miar ani progów.

1. Doprecyzowanie: wiadomość wyników ma postać `RESULTS: [{"call": <napis wywołania lub nazwa>, "result": <wynik ≤ 800 znaków>}]`.
2. Doprecyzowanie renderera: parametry nieobowiązkowe mają w linii opisu znacznik `[optional]`; funkcje oddzielone pustą linią.
3. Doprecyzowanie 5.1: „wykonane wywołania" w elemencie pamięci to tylko wywołania przekazane do executora; wywołania odrzucone przez walidację i kroki z niepoprawnym wyjściem nie trafiają do pamięci ani do checkera.
4. Doprecyzowanie kalibracji 5.3: cel y = wśród dwóch najlepszych w rankingu bez bramki jest trafienie pozytywne; decyzja ŷ = co najmniej jeden element przechodzi bramkę o danych parametrach.
5. Doprecyzowanie bramki E1a: odsetek = (niepoprawne wyjścia + niepoprawne wywołania) / (niepoprawne wyjścia + wszystkie zaproponowane wywołania).
6. G2: cztery wywołania ze znaną odpowiedzią (krótkie, najdłuższy prompt systemowy, to samo żądanie powtórzone dla kontroli pamięci podręcznej, krótkie z pustą listą); wszystkie muszą być poprawne.
7. E0: wykrywanie metod losowych obejmuje metody publiczne wołające prywatne pomocnicze z `_random` (stąd `send_message`). Liczba tur z identyczną listą wzorcową wynosi 86 (v0 podawał 84), bo normalizacja mapuje argumenty pozycyjne na nazwane i liczby całkowite na zmiennoprzecinkowe.
8. E0 potwierdził z kodu przypiętego commitu: komunikaty błędów `startEngine` nazywają brakujący warunek (drzwi, hamulec, hamulec do końca), więc reguła jest odkrywalna w epizodzie; executor trzyma instancje w `globals()` pod `{model_name}_{test_entry_id}_{class}_instance`; brak tur z pustym wzorcem w zadaniach 50–99; `num_ctx = 8192` (L = 6 433 znaki).

## 15. Decyzje właściciela potrzebne przed implementacją

1. Zgoda na pobranie plików BFCL z GitHuba (jak w v0).
2. Akceptacja zamiany: pełne N′ (ok. 270 wywołań) → kontrola determinizmu na 5 zadaniach (ok. 45) i nowe ramię R+
   (ok. 270). Planowo ok. 1 600 wywołań, przy pełnym N′ ok. 1 825; limit twardy 2 000 bez zmian.
3. Gdy G2 pokaże, że model przy wybranym `num_ctx` nie mieści się w całości na GPU: stop i decyzja wtedy (domyślnie
   w tej wersji) albo zgoda z góry na akceptację spowolnienia w limicie 6/8 godzin.
