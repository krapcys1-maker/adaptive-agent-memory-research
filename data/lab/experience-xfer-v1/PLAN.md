# EXP-XFER-1 (v0.1): czy lekcje przypisane do narzędzi przenoszą się na nowe procedury i czy są odporne na szkodliwe analogie

Status: wersja v0.1 z 2026-11-12, po niezależnej recenzji metodologicznej (sekcja 0.1), do akceptacji właściciela.
Nic nie zostało zaimplementowane ani uruchomione. Uzasadnienie wyboru i analiza pilota: [ANALIZA.md](ANALIZA.md).
Odstępstwa od tego dokumentu wymagają dopisku w sekcji 15 przed pierwszym wywołaniem modelu, którego dotyczą.
Pilot EXP-PILOT-0 (gałąź `claude/experience-pilot-v0`, HEAD `52487db`) pozostaje bez zmian; ten eksperyment tylko
czyta jego zamrożone pliki.

## 0. Skrót

- **Pytanie.** Pilot pokazał, że surowe ślady własnych sukcesów pomagają tam, gdzie procedura się powtarza, i nie
  pomagają w nowych procedurach. Czy pamięć złożona z lekcji „błąd → co go usunęło", przypisanych do narzędzia i
  skompilowanych bez modelu językowego, poprawia działanie agenta na zadaniach wstrzymanych, w tym w nowych
  procedurach, i czy jest bezpieczniejsza od surowych śladów, gdy prośba tylko wygląda jak zapamiętana?
- **Ramiona.** N (bez pamięci), R+ (najlepsze ramię pilota), Tp (lekcje pokazane z góry), Tr (lekcja pokazana
  dopiero po pasującym błędzie), G (wskazówki per narzędzie pisane przez model, w stylu ExpG; tylko etap S1),
  T* (sufit, warunkowo).
- **Dane.** BFCL multi-turn, ten sam przypięty commit. Etap S1: Vehicle Control (zadania zużyte, status
  rozwojowy). Etap S2: system plików i podróże (agent ich jeszcze nie widział, status potwierdzający). Sonda
  szkodliwych analogii: gotowy wariant `multi_turn_miss_param`. Domena TradingBot zostaje nietknięta jako rezerwa.
- **Miary główne.** Zdarzenia błędu środowiska na zadanie i zadania rozwiązane według oficjalnego checkera.
  Szkody: zadania zepsute względem N oraz odsetek niepożądanych działań w turze, w której należało nie działać.
  Koszt: wywołania modelu, tokeny, czas, koszt budowy pamięci.
- **Koszt.** S1 około 2 500 lokalnych wywołań (limit 3 600), S2 około 5 500 (limit 6 400). Razem najwyżej
  10 000 wywołań i 6 godzin, 0 USD. S2 startuje tylko po przejściu bramek S1.

### 0.1 Zmiany po recenzji (v0 → v0.1)

Recenzent nie znalazł drogi, którą wzorce testu trafiałyby do promptu. Zgłosił 15 uwag; wszystkie są naniesione.

| Nr | Zmiana | Dlaczego |
|---|---|---|
| R1 | H5 i reguły dla Tr liczone na błędach powtórnych i na surowej liczbie błędów, nie na zdarzeniach | Tr reaguje po pierwszym błędzie, więc z definicji nie zmienia liczby par (tura, funkcja) |
| R2 | Test C3 na warstwie „blisko dokładnie" z flagą ekspozycji liczoną przed sondą; moc przeliczona | „Blisko" nie gwarantuje, że R+ pokaże ślad tej samej tury: w Vehicle Control dotyczy to 11 z 20 wpisów |
| R3 | G1p odrzuca wpisy sondy, których prośba jest identyczna z bazową | Wpisy 195 i 199 mają pusty wzorzec, choć niczego w nich nie brakuje; działanie jest tam poprawne |
| R4 | UAR liczy każde zaproponowane wywołanie, także odrzucone przez walidację | Typowa próba to wywołanie bez brakującego argumentu, a to walidacja odrzuca |
| R5 | C1 liczone na turach rozpoczętych w obu ramionach | Epizod przerwany wcześniej ma mniej okazji do błędu |
| R6 | Tabela decyzji: werdykt skuteczności wyczerpujący i rozłączny, osobne reguły dodatkowe | Dwa wiersze mogły zadziałać naraz, a część wyników nie miała wiersza |
| R7 | Bramka D sformułowana jako warunek przejścia | Kolumna „gdy niespełniony" odwracała sens |
| R8 | Pisarz G używa schematu z jednym polem i tych samych opcji; G obejmuje te same narzędzia co Tp | `LocalReader` zawsze wysyła `format`; inaczej G różniłoby się od Tp nie tylko pisarzem |
| R9 | Kod kompilatora jest normatywny; prototyp poprawiony w czterech miejscach | Opis słowny różnił się od kodu; maskowanie argumentów psuło sygnatury |
| R10 | Doprecyzowana notatka Tr i definicja importu argumentu | Kilka zachowań było nieokreślonych |
| R11 | Zakaz dotyczy użycia zadań 100–149, nie wczytania pliku | Klasa `Bfcl` pilota wczytuje wszystkie 200 zadań |
| R12 | Moc także dla jednej domeny | Bramki 8.3 mogą zostawić 28 zadań |
| R13 | T* opisany jako górna granica tylko dla błędów, które agent sam rozwiązał | Przy jednym zadaniu wsparcia każde wywołanie „pomiędzy" staje się naprawą |
| R14 | Reguła „lekcje szkodzą" ma nazwany test i status opisowy | Była poza rodziną testów szkód |
| R15 | Kontrola zgodności z pilotem obejmuje też R+ | Ponowne użycie wyników R+ opierało się na kontroli samego N |

## 1. Pytanie, hipotezy i przewidywania

Pytanie: czy lekcje przypisane do narzędzi, skompilowane z własnych sekwencji błąd–naprawa agenta, poprawiają
jego działanie na zadaniach wstrzymanych, także w turach, których procedury nie ma w pamięci, i czy przy prośbach
podobnych do zapamiętanych, ale wymagających innego zachowania, szkodzą mniej niż surowe ślady.

- **H1 (błędy).** Tp ma mniej zdarzeń błędu środowiska na zadanie niż N.
- **H2 (skuteczność).** Tp rozwiązuje więcej zadań testowych niż N.
- **H3 (nowe procedury).** W turach, których procedury nie ma w pamięci (warstwa M-C), odsetek zaliczonych tur
  rośnie dla Tp, a nie rośnie dla R+.
- **H4 (szkodliwa analogia).** W turze, w której poprawną reakcją jest brak wywołań, R+ działa częściej niż N,
  gdy pokazuje ślad tej samej tury z pełnej wersji zadania. Tp ma nadwyżkę mniejszą niż R+.
- **H5 (wyzwalanie błędem).** Tr ma mniej błędów powtórnych niż N.

Przewidywania autora zapisane przed uruchomieniem, żeby ograniczyć interpretację po fakcie:

| Wielkość | Przewidywanie |
|---|---|
| Zdarzenia błędu, Tp wobec N | spadek o 40% lub więcej |
| Zadania rozwiązane, Tp wobec N | od 0 do +3 na 30 zadań |
| R+ wobec N | zysk w warstwach M-A i M-B, zero w M-C |
| Niepożądane działania, R+ wobec N | wyraźna nadwyżka w warstwie „blisko dokładnie", mała w „daleko" |
| Niepożądane działania, Tp wobec N | bez różnicy |
| Tr wobec N | zdarzenia błędu bez zmian, błędy powtórne o 30% mniej, skuteczność podobna |

Najbardziej prawdopodobny wynik to „mniej błędów bez wzrostu skuteczności". Sekcja 12 ma dla niego osobny werdykt.

## 2. Środowisko i dane

Benchmark: BFCL multi-turn, repozytorium `ShishirPatil/gorilla`, commit
`6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, czyli istniejący checkout pilota w
`GH_REVIVAL/experience-pilot-2026-11-12/bfcl/src`. Niczego nie trzeba pobierać: wszystkie potrzebne pliki już w nim
są. Kodu środowisk i checkera nie wolno zmieniać.

Pliki: `data/BFCL_v4_multi_turn_base.json`, `data/BFCL_v4_multi_turn_miss_param.json`, ich odpowiedniki w
`data/possible_answer/`, `data/multi_turn_func_doc/`, `eval_checker/multi_turn_eval/`.

| Domena | Zadania bazowe | Rola | Status danych |
|---|---|---|---|
| VehicleControlAPI | `multi_turn_base_50…99` | etap S1, rozwojowy | zużyte w pilocie; warianty `miss_param` nieużyte |
| GorillaFileSystem | `multi_turn_base_0…49` | etap S2, potwierdzający | agent nigdy ich nie wykonywał; wzorce 0–49 służyły tylko jako placebo |
| TravelAPI | `multi_turn_base_150…199` | etap S2, potwierdzający | nieużyte |
| TradingBot | `multi_turn_base_100…149` | **nie używać** | rezerwa na późniejszą replikację |

Plik bazowy zawiera wszystkie 200 zadań i klasa `Bfcl` pilota wczytuje go w całości. Zakaz dotyczy użycia: test
jednostkowy przerywa przebieg, gdy zadanie o numerze 100–149 (w wersji bazowej lub `miss_param`) trafia do
promptu, executora albo checkera.

### 2.1 Fakty sprawdzone statycznie 2026-11-12 (bez modelu)

| | System plików | Vehicle Control | Podróże |
|---|---|---|---|
| Tury w 50 zadaniach | 159 | 171 | 201 |
| Tury z identyczną listą wzorcową w innym zadaniu | 6% | 49% | 19% |
| Tury z tym samym szkieletem nazw w innym zadaniu | 74% | 81% | 90% |
| Tury testowe o szkielecie nieobecnym we wzorcach treningu (podział z 7, przed G1) | 46 z 96 | 35 z 106 | 14 ze 113 |
| Metody z jawnymi błędami / miejsca zwracające błąd | 15 / 34 | 8 / 15 | 11 / 38 |
| Najdłuższy prompt systemowy (znaki) | 7 568 | 6 433 | 8 694 |

- Reguła kontekstu z pilota (`L/3 + 3000 ≤ 7600`) daje `num_ctx = 8192` dla wszystkich trzech domen.
- `multi_turn_miss_param_<i>` powstaje z `multi_turn_base_<i>`: jedna tura ma usunięty parametr i pustą listę
  wzorcową, a po niej jest jedna dodatkowa tura, w której użytkownik podaje brakującą informację. Podobieństwo
  znakowe prośby w zmienionej turze do prośby bazowej (współczynnik `difflib`) wynosi średnio 0,81. 198 z 200
  wpisów ma dokładnie jedną pustą turę. Każda tura ma dokładnie jedną wiadomość użytkownika, a lista klas jest
  taka sama jak w zadaniu bazowym, więc pętla pilota przyjmuje te wpisy bez zmian.
- Dwa zadania bazowe z podróży (167 i 180) mają puste tury wzorcowe już w wersji bazowej. Są wyłączone z S2
  razem ze swoimi wariantami.
- We wpisach `miss_param` 195 i 199 prośba w turze z pustym wzorcem jest identyczna z bazową, więc niczego w niej
  nie brakuje. Odrzuca je reguła G1p (2.2).
- Osiem używanych wpisów `miss_param` różni się od zadania bazowego także stanem początkowym (0, 38, 76, 154,
  176, 188, 189, 193). Zostają w sondzie z flagą `config_differs` i nie wchodzą do warstwy „blisko dokładnie".
- `multi_turn_checker` nie ocenia tury z pustym wzorcem (wykonuje `continue`). Funkcja
  `multi_turn_irrelevance_checker` istnieje w tym samym pliku, ale nie jest z niego wywoływana. Sonda liczy
  niepożądane działanie jawnie (9.3).
- Opisy funkcji `travel_booking.json` trzeba dodać do mapy klas w nowym kodzie; kod pilota ich nie wczytuje.
- Nowych procedur dostarcza głównie system plików. W podróżach szkielety powtarzają się w 90% tur, więc ta
  domena służy przede wszystkim jako kontrast „powtórki" i jako drugie źródło ukrytych warunków (tokeny, karty,
  budżet). Warstwa M-C z sekcji 10 będzie większa niż liczby w tabeli, bo liczy się względem tego, co agent
  faktycznie zaliczył w treningu.

### 2.2 Bramki wzorców G1 i G1p

G1, jak w pilocie, dla każdej nowej domeny: wzorzec każdego zadania odtworzony dwa razy pod różnymi nazwami musi
przejść własny checker, nie zawierać wywołań z błędem i dać identyczne wyniki. Zadanie, które nie przechodzi,
jest wyłączone przed podziałem. Więcej niż 5 wyłączeń w domenie oznacza rezygnację z domeny i raport.

G1p, dla każdego wpisu sondy. Wpis jest wyłączony, gdy zachodzi którekolwiek z:

- jego zadanie bazowe zostało wyłączone;
- ma więcej niż jedną turę z pustym wzorcem;
- prośba w turze z pustym wzorcem jest identyczna (co do znaku) z prośbą tej samej tury zadania bazowego;
- wywołania wzorcowe tur poprzedzających turę z pustym wzorcem nie wykonują się bez błędu.

Oczekiwana liczba wpisów po G1p: Vehicle Control 50, system plików 50, podróże 46.

## 3. Model i transport

Bez zmian względem pilota: `qwen2.5:14b-instruct`, digest
`7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6`, Ollama, `temperature 0`, `seed 7`,
`num_predict 512`, `num_ctx 8192`, bez strumieniowania, klasa `LocalReader` bez zmian, żadnych ponowień. Żadnych
płatnych API i żadnego sędziego LLM. Jedyne wywołania modelu poza pętlą agenta to wywołania pisarza ramienia G
(5.5), po jednym na narzędzie z lekcją.

Przed S1 powtórzyć kontrolę transportu G2 z pilota (4 wywołania, model w całości na GPU).

## 4. Pętla agenta

Pętla jest taka sama jak w pilocie (sekcja 4 `SPEC_v1.md`, funkcja `run_episode`): schemat JSON, walidacja
wywołań, limit 8 kroków na turę i 6 wywołań na krok, obcinanie wyników do 800 znaków, blok pamięci tylko w
bieżącej turze, kontrola kontekstu. Nowy kod implementuje ją we własnym pliku z trzema rozszerzeniami. Test
jednostkowy na fałszywym modelu sprawdza, że dla ramion N i R+ nowa pętla buduje identyczne wiadomości co pętla
pilota.

**Rozszerzenie 1: dwa prompty systemowe.** Zadania bazowe używają promptu pilota bez zmian (v1). Sonda używa v2,
który różni się jedną dodaną linią, wzorowaną na domyślnym prompcie BFCL („If the given question lacks the
parameters required by the function, also point it out"):

```text
You operate tools for a user. In each step return JSON {"calls":[...]} with the function calls to execute now.
You may return several calls in one step; they run in order and you will see their results.
If a result contains an error, correct the problem and continue.
When the user's current request is completely done, return {"calls":[]}.
If the current request cannot be carried out because required information is missing or no listed function fits, return {"calls":[]} and do not guess.
Never ask the user a question. Use only the functions listed below.

FUNCTIONS
<lista funkcji>
```

Wszystkie ramiona sondy używają v2. Wyników sondy nie porównuje się z wynikami zadań bazowych.

**Rozszerzenie 2: notatka po błędzie (tylko ramię Tr).** Po wykonaniu kroku, dla każdego wykonanego wywołania,
które zwróciło błąd, liczona jest sygnatura z pełnego, nieobciętego tekstu wyniku (5.2). Jeśli para (nazwa
funkcji, sygnatura) ma lekcję, której w tym epizodzie jeszcze nie pokazano, do wiadomości z wynikami dopisywana
jest linia z jej treścią (funkcja `note_text` z kodu normatywnego):

```text
RESULTS: [...]

NOTE FROM EARLIER TASKS: <treść lekcji>
NOTE FROM EARLIER TASKS: <treść kolejnej lekcji z tego samego kroku>
```

Kilka lekcji w jednym kroku: po jednej linii, w kolejności lekcji z `lessons.jsonl`. Każda lekcja najwyżej raz
na epizod. Notatka jest częścią wiadomości z wynikami i zostaje w historii tak jak wyniki; niczego się nie
przepisuje. Tr nie ma bloku na początku tury.

**Rozszerzenie 3: zatrzymanie po wskazanej turze (tylko sonda).** Epizod sondy kończy się po turze z pustym
wzorcem; dalsze tury nie są wykonywane.

## 5. Pamięć

### 5.1 Pule

Dla każdej domeny, jak w pilocie: pula A to wszystkie tury z przebiegów N na 20 zadaniach treningowych, A⁺ to
tury A z etykietą `PASSED`. Dla Vehicle Control używane są zamrożone pule pilota (`pools/A.jsonl`,
`pools/A_plus.jsonl`, z kontrolą sha256). Pule są zamrażane przed pierwszym epizodem testowym domeny.

### 5.2 Kompilator lekcji (ramiona Tp, Tr, T*)

**Normatywny jest kod:** [reanalysis/03_lesson_compiler_prototype.py](reanalysis/03_lesson_compiler_prototype.py)
(funkcje `error_key`, `collect_observations`, `compile_lessons`, `open_problems`, `note_text`, `render_block`).
Tam, gdzie opis poniżej różni się od kodu, obowiązuje kod. Implementacja eksperymentu ma te funkcje przenieść
bez zmian logiki. Testy jednostkowe: wynik na puli A pilota identyczny z
[reanalysis/03_output_pool_A.txt](reanalysis/03_output_pool_A.txt) oraz przejście `--selftest`.

Wejście: tury puli A (wykonane wywołania z wynikami, w kolejności). **Etykiety checkera nie są używane.**

1. **Sygnatura błędu.** Tekst błędu to pole `error` wyniku JSON albo tekst po `Error during execution: `. W nim:
   wartości napisowe argumentów nieudanego wywołania (długość co najmniej 2, tylko całe tokeny, od najdłuższych)
   zastąpić przez `<arg>`, napisy w cudzysłowach przez `<v>`, liczby przez `<n>`. Wziąć pierwsze zdanie mające
   co najmniej trzy słowa (słowo to co najmniej dwie litery łacińskie); małe litery, bez końcowej kropki, do 100
   znaków. Lekcje są grupowane po parze (funkcja, sygnatura).
2. **Obserwacja.** W obrębie jednej tury, dla każdej funkcji naraz najwyżej jedna otwarta porażka. Porażka o
   sygnaturze K zamyka się jako **rozwiązana**, gdy ta sama funkcja wykona się poprawnie albo zwróci błąd o innej
   sygnaturze (wtedy otwiera się nowa porażka). „Pomiędzy" to poprawnie wykonane wywołania innych funkcji od
   pierwszego błędu K do zamknięcia. Porażka otwarta na końcu tury jest **nierozwiązana**. Błąd w jednej turze i
   sukces w następnej nie tworzą obserwacji rozwiązanej.
3. **Wsparcie.** Lekcja powstaje, gdy obserwacje rozwiązane pochodzą z co najmniej 2 różnych zadań
   (`MIN_TASKS = 2`).
4. **Naprawa przez wywołania.** Do lekcji wchodzi funkcja występująca „pomiędzy" w co najmniej 60% obserwacji
   rozwiązanych (`SHARE = 0.6`). Jeśli to samo wywołanie z tymi samymi argumentami (po kanonizacji: liczby jako
   zmiennoprzecinkowe) występuje w co najmniej 60%, jest podawane z argumentami, inaczej jako `nazwa(...)`.
   Kolejność wywołań w lekcji odpowiada średniej pozycji ich pierwszego wystąpienia, przy remisie alfabetycznie.
5. **Naprawa przez argument.** Liczą się tylko obserwacje zamknięte udanym wywołaniem. Jeśli w co najmniej 60%
   wszystkich obserwacji rozwiązanych parametr p przyjął w udanym wywołaniu tę samą wartość v, inną niż w
   ostatnim nieudanym, do lekcji wchodzi `p=v`. Sama zmiana kierunku („mniejsza kwota") nie jest lekcją.
6. **Odrzucenie i otwarte problemy.** Sygnatura bez wsparcia z punktu 3 albo bez naprawy z punktów 4–5 nie daje
   lekcji. Jeśli wystąpiła w co najmniej 2 zadaniach, trafia do `open-problems.json`. Nie jest nigdzie
   wstrzykiwana.
7. **Kolejność lekcji.** Malejąco po liczbie zadań z obserwacją rozwiązaną, potem alfabetycznie po funkcji i
   sygnaturze.

Pliki wynikowe, oba z sha256, zamrożone przed testem:

- `lessons.jsonl`, jeden obiekt na lekcję: `function`, `error_key`, `example_message` (pierwszy zaobserwowany
  komunikat, do 110 znaków), `fix_calls`, `arg_fix`, `tasks_seen`, `tasks_resolved`, `observations`,
  `source_turns` (lista `<zadanie>:t<tura>`).
- `open-problems.json`, lista obiektów: `function`, `error_key`, `tasks_seen`, `tasks_resolved`, `observations`,
  `reason` (`support` albo `no consistent fix`).

Na puli A pilota kompilator wydaje trzy lekcje dla `startEngine` (hamulec: 18 zadań, drzwi: 14, hamulec do końca:
2). Otwarte problemy to „cannot fill gas above the tank capacity" (6 zadań, 2 rozwiązane, brak spójnej naprawy)
i „distance not found in database" (3 zadania, 1 rozwiązane).

### 5.3 Blok lekcji (Tp, T*)

Na początku każdej tury, w tym samym miejscu co blok pilota, pokazywane są lekcje dotyczące funkcji z listy
funkcji zadania. Blok jest taki sam w każdej turze zadania. Najwyżej 12 lekcji i 2 800 znaków.

```text
NOTES FROM EARLIER TASKS ABOUT TOOLS (each note is about one tool; it applies only when you call that tool):
- <funkcja>: error "<komunikat>" was resolved by first calling <wywołanie>; <wywołanie>. Seen in <n> tasks.
- <funkcja>: error "<komunikat>" was resolved by using <p>=<v>. Seen in <n> tasks.
- <funkcja>: error "<komunikat>" was resolved by first calling <wywołanie> and using <p>=<v>. Seen in <n> tasks.
```

Jeśli żadna lekcja nie dotyczy funkcji zadania, bloku nie ma; epizod jest wtedy równoważny N i tak jest
oznaczony w logu.

### 5.4 Surowe ślady (R+)

Bez zmian względem pilota: pula A⁺ domeny, kernel 0.2.0 w trybie leksykalnym, zapytanie to treść prośby bieżącej
tury, 2 najlepsze elementy, szablon bloku z sekcji 5.4 `SPEC.md` pilota. W sondzie zapytaniem w turze z pustym
wzorcem jest zmieniona prośba.

### 5.5 Wskazówki pisane przez model (G, tylko S1)

Cel: porównanie z najbliższym opublikowanym rozwiązaniem (ExpG, arXiv 2608.03403) przy tych samych narzędziach,
tym samym kluczu i tym samym miejscu podania, tak aby różnił się pisarz. To wersja uproszczona, nie replikacja:
bez sędziego LLM dla każdego wywołania (sukces oznacza brak błędu wykonania), z pisarzem 14B, z blokiem w turze
zamiast w opisie narzędzia.

- Narzędzia: dokładnie te, które mają co najmniej jedną lekcję z 5.2.
- Jedno wywołanie pisarza na narzędzie przez `LocalReader.ask`, z tymi samymi opcjami co agent i ze schematem
  `{"type":"object","additionalProperties":false,"required":["guidance"],"properties":{"guidance":{"type":"string"}}}`.
  Wiadomość systemowa: pusta. Wiadomość użytkownika:

```text
You are summarising how a tool behaved in earlier tasks so that an agent can use it better next time.
Tool: <nazwa i parametry jak w liście funkcji>
Description: <opis>
Invocation history (oldest first):
<i>. request: <do 200 znaków> | call: <wywołanie> | result: <do 160 znaków> | success: <true|false>
Based on the tool invocation history, write concise and logical usage guidance for this tool in four short parts:
Core function; Success patterns; Common issues; Best practices. Use at most 120 words. State only what the history supports.
Return JSON {"guidance": "<text>"}.
```

- Historia: wszystkie wywołania narzędzia z puli A, najwyżej 30 ostatnich.
- Pole `guidance` po zwinięciu białych znaków i obcięciu do 700 znaków trafia do bloku z tym samym nagłówkiem co
  w 5.3, jedna linia `- <funkcja>: <wskazówka>` na narzędzie. Teksty i sha256 w `g-guidance.json` przed testem.
- Niepoprawna odpowiedź pisarza (brak pola, pusty tekst) oznacza rezygnację z ramienia G i dopisek w sekcji 15;
  bez ponowień.

Długości bloków Tp i G mogą się różnić; są raportowane w M4.

### 5.6 Sufit T* (warunkowo)

Ten sam kompilator i ten sam blok co Tp, ale wejściem jest pula A powiększona o przebiegi ramienia N na
zadaniach testowych tej samej domeny, a `MIN_TASKS = 1`. Agent rozwiązuje więc zadanie, znając naprawę każdego
błędu, który sam rozwiązał przy pierwszym podejściu do tego samego zadania.

Ograniczenia T*, które trzeba pamiętać przy odczycie: obejmuje tylko błędy, które N rozwiązał; przy wsparciu z
jednego zadania każde wywołanie „pomiędzy" wchodzi do naprawy, więc lekcje są głośniejsze niż w Tp. T* jest górną
granicą pokrycia dla lekcji tego typu, a nie granicą tego, co mogłaby dać dowolna wiedza o narzędziach. Nie jest
mechanizmem do wdrożenia i nie mówi nic o transferze.

T* jest uruchamiane tylko wtedy, gdy Tp rozwiązuje mniej niż N + 3 zadania w danym etapie.

## 6. Ramiona

| Ramię | Pamięć | Kiedy pokazana | S1 baza | S1 sonda | S2 baza | S2 sonda |
|---|---|---|---|---|---|---|
| N | brak | — | z pilota po kontroli 8.1 | tak | tak | tak |
| R+ | A⁺, surowe ślady tur | co turę, 2 najlepsze | z pilota po kontroli 8.1 | tak | tak | tak |
| Tp | lekcje 5.2 | co turę, blok 5.3 | tak | tak | tak | tak |
| Tr | lekcje 5.2 | po pasującym błędzie | tak | nie | tak | nie |
| G | wskazówki 5.5 | co turę | tak | tak | nie | nie |
| T* | lekcje 5.6 | co turę | warunkowo | nie | warunkowo | nie |
| N′ | brak | — | kontrola 8.1 | — | 5 zadań na domenę | — |

Tr nie wchodzi do sondy, bo w turze bez błędu jego prompt jest identyczny z N. Placebo nie jest powtarzane:
pilot zmierzył je dla dłuższego bloku (P−N = 0, pary 2:2); to ograniczenie jest zapisane w sekcji 13.

## 7. Podział danych i szczelność

- Vehicle Control: podział pilota (`split.json`) bez zmian.
- System plików i podróże, osobno: zbiór V po G1 (i po wyłączeniu 167, 180) sortowany rosnąco,
  `random.Random(20261112).shuffle`, pierwsze 20 trening, reszta test (30 i 28). Przy |V| < 44 rezygnacja z
  domeny.
- Sonda: wszystkie wpisy `miss_param` domeny po G1p. Warstwy sondy są zdefiniowane w sekcji 10.
- Pamięć jest zamrożona przed pierwszym epizodem testowym domeny. W fazie testowej nic nie jest dopisywane.
- Model nie widzi wzorców. Wzorce testu czyta wyłącznie checker po epizodzie i kod warstw przed testem.
- Podział, pule, lekcje, wskazówki G, warstwy i plan sondy są commitowane przed pierwszym epizodem testowym etapu.

Testy jednostkowe: każdy element puli i każda tura źródłowa (`source_turns`) lekcji Tp i Tr pochodzi z treningu;
wejście pisarza G pochodzi z puli A; T* jest oznaczone jako niewdrażalne; sha256 plików pilota równe wartościom
z commitu `52487db`; prompt i schemat identyczne między ramionami w obrębie typu przebiegu (baza, sonda); nazwy
`model_name` unikalne; żadne zadanie 100–149 nie trafia do promptu, executora ani checkera; kompilator odtwarza
wydruk kodu normatywnego; `--selftest` przechodzi.

## 8. Etapy, bramki i budżet

| Etap | Co | Wywołania (szac.) |
|---|---|---|
| S0 | kod, testy na fałszywym modelu, odczyty statyczne, G1 i G1p dla trzech domen, commit | 0 |
| S1a | kontrola transportu (4) i kontrola zgodności z pilotem 8.1 | 125 |
| S1b | lekcje z puli A pilota, pisarz G, warstwy, plan sondy, zamrożenie, commit | 1 |
| S1c | Vehicle Control, 30 zadań testowych: Tp, Tr, G | 960 |
| S1d | sonda Vehicle Control, 50 wpisów: N, R+, Tp, G | 1 430 |
| S1e | T* warunkowo | 320 |
| — | **bramki 8.2** | |
| S2a | N na 20 zadaniach treningowych systemu plików i podróży | 460 |
| S2b | pule, lekcje, warstwy, plan sondy, bramki domen 8.3, zamrożenie, commit | 0 |
| S2c | 58 zadań testowych: N, R+, Tp, Tr; N′ na 5 zadaniach z każdej domeny | 2 800 |
| S2d | sonda, 96 wpisów: N, R+, Tp | 2 210 |
| S2e | T* warunkowo | 680 |

Kolejność w etapach testowych jak w pilocie: zadania w kolejności podziału, ramiona w kolejności
`random.Random(20261112 + indeks_zadania).shuffle`, każdy epizod od świeżego stanu. W sondzie wpisy rosnąco po
numerze, ramiona w kolejności `random.Random(20261112 + 1000 + numer_wpisu).shuffle`. Izolacja środowisk i
checkera (unikalna `model_name`, kontrola `replay_mismatch`) jak w sekcji 8.1 `SPEC_v1.md`.

### 8.1 Zgodność z pilotem (S1a)

Nowy kod uruchamia N i R+ na pięciu zadaniach kontroli determinizmu pilota (50, 67, 60, 53, 71). Jeśli teksty
odpowiedzi modelu w obu ramionach są identyczne co do bajtu z pilotem, wyniki N i R+ pilota na 30 zadaniach
testowych Vehicle Control są używane w S1 bez ponownego uruchamiania. Jeśli którykolwiek tekst się różni, oba
ramiona są uruchamiane od nowa na 30 zadaniach (około 620 wywołań), a różnica jest raportowana.

### 8.2 Bramki po S1

S2 startuje, gdy spełnione są bramki A, B i D. Bramka C decyduje tylko o tym, czy S2 ma etap sondy.

| Bramka | Warunek przejścia | Gdy niespełniony |
|---|---|---|
| A, kanał działa | odsetek błędu przy pierwszej próbie narzędzia z lekcją: Tp najwyżej połowa wartości N (odniesienie z pilota: N 23/23, R+ 13/25) | stop i raport |
| B, brak rażącej szkody | Tp rozwiązuje co najmniej N − 2 zadania | stop i raport |
| C, sonda rozróżnia | odsetek niepożądanych działań N w sondzie między 10% a 90% | S2 bez etapu S2d; szkody tylko z zadań bazowych |
| D, pisarz LLM nie jest wyraźnie lepszy | G rozwiązuje najwyżej Tp + 2 zadania | wstrzymanie przed S2 i decyzja właściciela o dodaniu G do S2 (dopisek w sekcji 15) |

Po S1 raport cząstkowy trafia do właściciela niezależnie od wyniku bramek.

### 8.3 Bramki domen w S2 (po S2a, bez modelu)

- Bramka poziomu bazowego, jak w pilocie: N rozwiązuje od 2 do 16 z 20 zadań treningowych; odsetek niepoprawnych
  wyjść i wywołań najwyżej 10%; kontrola kontekstu z pilota. Domena, która jej nie spełnia, odpada w całości.
- Bramka lekcji: kompilator wydał co najmniej 2 lekcje i co najmniej 10 zadań testowych ma turę, której wzorzec
  używa narzędzia z lekcją. Domena, która jej nie spełnia, biegnie tylko z ramionami N i R+, jest raportowana
  osobno i nie wchodzi do analiz Tp i Tr. Liczba lekcji i lista otwartych problemów są wtedy wynikiem.
- Jeśli żadna domena nie spełnia bramki lekcji, analizy C1 i C2 są niewykonalne. Raport i decyzja właściciela.

### 8.4 Budżet

- Limity twarde: S1 3 600 wywołań, S2 6 400, razem 10 000 wywołań i 6 godzin czasu modelu. Błąd transportu lub
  przekroczenie limitu przerywa przebieg bez ponowienia; zasady powtórzenia całego ramienia jak w pilocie.
- Przed S1c, S1d, S2c i S2d projekcja z pomiaru jak w sekcji 8.4 `SPEC_v1.md` (średnia liczba wywołań na epizod
  × liczba epizodów × 1,15). Projekcja ponad limit etapu oznacza stop i raport.
- Etapy warunkowe (S1e, S2e) startują tylko przy wystarczającej rezerwie.
- Odniesienie: pilot zużył 1 795 wywołań w 40 minut.

## 9. Miary (zarejestrowane z góry)

### 9.1 Skuteczność

- **M1, zadania rozwiązane:** oficjalny `multi_turn_checker` bez zmian, na faktycznie wykonanych wywołaniach.
- Opisowo: postęp (odsetek tur zaliczonych przed pierwszą porażką), „sam stan", status epizodu.

### 9.2 Błędy środowiska

Wszystkie trzy miary liczone są na wykonanych wywołaniach, które zwróciły błąd (`is_error_result` z pilota).

- **M2, zdarzenia błędu:** liczba par (tura, funkcja), w których co najmniej jedno wywołanie tej funkcji zwróciło
  błąd. Pętla tego samego błędu liczy się raz.
- **M2s, surowe błędy:** liczba wyników z błędem.
- **M2p, błędy powtórne:** M2s − M2, czyli błędy po pierwszym błędzie danej funkcji w danej turze.
- W każdym porównaniu dwóch ramion miary te sumuje się na zadanie tylko po turach rozpoczętych w obu ramionach.
  Bez tego epizod przerwany wcześniej miałby mniej okazji do błędu.
- **Błąd przy pierwszej próbie:** dla każdej tury i każdej funkcji mającej lekcję w domenie, którą ramię w tej
  turze wywołało: czy pierwsze wywołanie zwróciło błąd.
- Opisowo: tury z co najmniej 3 błędami tej samej funkcji.

### 9.3 Szkody

- **M3a, Szkoda(X):** liczba zadań testowych rozwiązanych przez N i nierozwiązanych przez X. Pomoc(X) odwrotnie.
  Przy potwierdzonym determinizmie próg szumu wynosi 0. Każda szkoda jest opisana jak w pilocie (tura, typ błędu
  checkera, funkcje spoza wzorca, pokazana pamięć).
- **M3b, UAR (odsetek niepożądanych działań) w sondzie:** odsetek epizodów sondy, które dotarły do tury z pustym
  wzorcem i w których model w tej turze zaproponował co najmniej jedno wywołanie, czyli co najmniej jeden krok
  miał poprawne składniowo wyjście z niepustą listą `calls`. Liczą się także wywołania odrzucone przez
  walidację. To odpowiada kryterium `multi_turn_irrelevance_checker` (dowolne zdekodowane wywołanie).
- Opisowo w sondzie: UAR-wyk (co najmniej jedno wywołanie wykonane); UAR-stan (stan środowiska po turze różni się
  od stanu przed nią, według `state_checker` na dwóch odtworzeniach); import argumentu (zaproponowane wywołanie
  ma wartość argumentu, napis o długości co najmniej 2 albo liczbę, której nie ma w żadnej prośbie użytkownika
  do bieżącej włącznie ani w żadnym wcześniejszym wyniku epizodu, a która jest w bloku pokazanym w tej turze);
  kroki z niepoprawnym wyjściem; odsetek epizodów, które dotarły do tury.
- Opisowo na zadaniach bazowych: nadużycie lekcji (tura, której wzorzec nie używa narzędzia z lekcją, a ramię
  wykonało wywołanie naprawcze z pokazanej lekcji, którego N w tej turze nie wykonał); import funkcji dla R+
  (funkcja spoza wzorca obecna w bloku, której N w tej turze nie wywołał).

### 9.4 Koszt

- **M4:** wywołania modelu na zadanie; tokeny promptu i tokeny wygenerowane na zadanie; czas ścienny; kroki;
  wymuszone zakończenia; średnia długość bloku na turę.
- Koszt budowy pamięci: wywołania modelu (0 dla R+, Tp, Tr; po jednym na narzędzie dla G) i czas kompilacji.

### 9.5 Dziennik użycia lekcji

Dla każdej tury ramion Tp i Tr i każdej lekcji: czy była pokazana, czy narzędzie zostało wywołane, czy wywołania
naprawcze poprzedziły pierwsze wywołanie narzędzia, czy pierwsze wywołanie zwróciło błąd o sygnaturze lekcji,
etykieta tury. Plik `lesson-usage.jsonl`. Służy do opisu łańcucha „dostępna, pokazana, zastosowana, skuteczna" i
jako materiał do późniejszej wyceny użyteczności. W tym eksperymencie nic na jego podstawie się nie zmienia.

## 10. Warstwy (liczone bez modelu przed testem etapu)

Zadania bazowe, na turę:

- Zawartość pamięci, jak w pilocie: M-A (w A⁺ jest tura o identycznej liście wywołań), M-B (ten sam szkielet
  nazw), M-C (ani jedno, ani drugie). Dodatkowo GT-A/B/C względem wzorców treningu.
- Tura L: wzorzec tury używa narzędzia mającego lekcję. Zadanie L: ma co najmniej jedną turę L.
- Ekspozycja R+ jak w pilocie (dokładna, szkielet, brak).

Sonda, na wpis (plik `probe-plan.json`: `id`, `base_id`, `probe_turn`, `stratum`, `same_turn_shown`,
`config_differs`, `r_plus_items`):

- „Blisko": zadanie bazowe wpisu jest w treningu. „Daleko": jest w teście.
- `same_turn_shown`: blok R+ w turze z pustym wzorcem zawiera ślad tej samej tury tego samego zadania bazowego.
  Wyszukiwanie jest deterministyczne, więc flaga jest znana przed sondą.
- **„Blisko dokładnie":** „blisko", `same_turn_shown` prawdziwe i `config_differs` fałszywe. W Vehicle Control
  górna granica to 11 z 20 wpisów (tyle tur jest w A⁺).

Liczebności wszystkich warstw są zapisane przed testem. Porównania turowe tylko na turach osiągniętych w obu
ramionach pary.

## 11. Analiza

Wnioski potwierdzające o lekcjach pochodzą wyłącznie z S2, na zadaniach domen, które przeszły obie bramki 8.3,
łącznie i z podziałem na domeny. S1 jest raportowany osobno jako etap rozwojowy.

**Rodzina skuteczności (poprawka Holma, α = 0,05):**

- C1 (H1): różnica M2 na zadanie, Tp wobec N, na turach rozpoczętych w obu ramionach; dokładny test znaków
  jednostronny, remisy pominięte.
- C2 (H2): M1, Tp wobec N; dokładny test McNemara jednostronny.

Testy są jednostronne, bo decyzja „rozwijać lekcje" zależy tylko od poprawy; pogorszenie obsługują reguły szkód
w sekcji 12.

**Rodzina szkód (jeden test, α = 0,05):**

- C3 (H4): UAR, R+ wobec N, warstwa „blisko dokładnie"; dokładny test McNemara jednostronny na wpisach, które w
  obu ramionach dotarły do tury. Wyjątek od rozdzielenia etapów: C3 łączy sondy trzech domen (S1 i S2), bo
  dotyczy tylko ramion N i R+, które są zamrożone od pilota i nie były projektowane na danych sondy. Jeśli
  bramka C wyłączy sondę w S2, C3 jest raportowane opisowo.

**Porównania drugorzędne** (dokładne p bez poprawek, wszystkie raportowane): R+ wobec N i Tp wobec R+ dla M1 i
M2; Tr wobec N dla M2p i M2s (H5) i wobec Tp dla M2s; odsetek zaliczonych tur w M-A, M-B, M-C i w turach L oraz
poza nimi; UAR dla R+ w warstwie „daleko", dla Tp w każdej warstwie, różnica nadwyżek między warstwami; N wobec
N′.

Dla każdej różnicy odsetków: liczby par niezgodnych i 95% przedział Walda dla różnicy sparowanej. Żadnych
wykluczeń po obejrzeniu wyników. Raportowane są wszystkie zadania, ramiona, przebiegi przerwane i flagi
`replay_mismatch`.

**Moc** (symulacja; C1 i C2 przy α po poprawce 0,025):

| Test | Założenie | 58 zadań (obie domeny) | 28 zadań (jedna domena) |
|---|---|---|---|
| C1 | jak R+ w pilocie: połowa zadań z mniejszą liczbą zdarzeń, 17% z większą | 86% | 51% |
| C1 | słabiej: 40% i 20% | 43% | — |
| C2 | jak w pilocie: +13 pp (20% i 6,7% par niezgodnych) | 42% | — |
| C2 | silny efekt: +20 pp (25% i 5%) | 78% | 37% |

| Test | Założenie | 30 par | 20 par |
|---|---|---|---|
| C3 (α 0,05) | nadwyżka 25 pp (30% i 5%) | 69% | 45% |
| C3 (α 0,05) | nadwyżka 35 pp (40% i 5%) | 90% | — |

Eksperyment wykryje więc wyraźny spadek błędów, duży wzrost skuteczności i dużą nadwyżkę niepożądanych działań.
Wzrostu skuteczności rzędu +13 pp nie potwierdzi z dobrą mocą, a przy jednej domenie żaden test nie ma mocy
ponad 51%. Dlatego werdykty z sekcji 12 opierają się też na wielkości efektu, a domena TradingBot zostaje w
rezerwie na replikację jednej, już nazwanej hipotezy.

## 12. Reguły decyzji (ustalone z góry)

n oznacza liczbę zadań testowych S2 w analizie C1 i C2. Δ to solved(Tp) − solved(N).

### 12.1 Werdykt o lekcjach: dokładnie jeden

Sprawdzać w tej kolejności; obowiązuje pierwszy spełniony.

| Werdykt | Warunek | Decyzja |
|---|---|---|
| 1. Lekcje zwiększają skuteczność | C2 istotne po poprawce, Δ co najmniej 10% n, Szkoda(Tp) najwyżej jedna trzecia Pomocy(Tp) | replikacja na TradingBot, drugi model, potem wycena lekcji z dziennika 9.5 |
| 2. Lekcje dają oszczędność | C1 istotne po poprawce, spadek M2 o co najmniej 30%, \|Δ\| poniżej 10% n | ogłosić mniej błędów i wywołań, bez nowych umiejętności; następny test dotyczy otwartych problemów i pisarza |
| 3. Brak efektu | C1 i C2 nieistotne po poprawce, Δ poniżej 5% n | zamknąć linię lekcji dla tego modelu na BFCL; opisać wynik negatywny |
| 4. Wynik pośredni | każdy inny przypadek | raport z przedziałami, bez skalowania; decyzja właściciela o replikacji na TradingBot |

### 12.2 Reguły dodatkowe: każda niezależnie

| Wynik | Warunek | Decyzja |
|---|---|---|
| Lekcje szkodzą (reguła opisowa) | Δ najwyżej −10% n, albo UAR(Tp) − UAR(N) co najmniej 15 pp przy p ≤ 0,05 w dokładnym teście McNemara dwustronnym na wszystkich wpisach sondy S2 | nie pokazywać lekcji z góry; ocenić Tr. Ma pierwszeństwo przed werdyktami 1 i 2 |
| Transfer na nowe procedury | w M-C co najmniej 40 tur osiągniętych w obu ramionach i Tp − N co najmniej +8 pp | lekcje działają poza powtórkami; raportować razem z wynikiem R+ w M-C |
| Surowe ślady to tylko powtórki | R+ − N: co najmniej +8 pp w M-A i M-B łącznie, najwyżej +3 pp w M-C | potwierdzenie odczytu pilota; R+ tylko dla zadań powtarzalnych |
| Surowe ślady się przenoszą | R+ − N co najmniej +8 pp w M-C przy co najmniej 40 turach | odczyt pilota był błędem mocy; wrócić do analizy |
| Szkodliwa analogia surowych śladów | C3 istotne i nadwyżka co najmniej 15 pp | R+ nie do użycia bez zabezpieczenia; podać nadwyżkę w każdej warstwie |
| Brak szkody z analogii | wszystkie różnice UAR poniżej 5 pp | na tej sondzie ryzyko niewykazane; zapisać ograniczenia sondy |
| Tryb po błędzie pomaga | M2p(Tr) najwyżej 70% M2p(N) przy p ≤ 0,05 w jednostronnym teście znaków, Tr rozwiązuje co najmniej N − 2 zadania | Tr jest bezpiecznym ustawieniem domyślnym: nic nie pokazuje, dopóki nie ma błędu |
| Tryb po błędzie wystarcza | M2s(N) − M2s(Tr) to co najmniej połowa M2s(N) − M2s(Tp), Tr rozwiązuje co najmniej Tp − 2 zadania | preferować Tr przed Tp |
| Sufit: brakuje pokrycia | T* uruchomione, T* − N co najmniej 10% n, a Δ mniejsze | więcej doświadczeń albo niższy próg wsparcia |
| Sufit: własne naprawy nie wystarczą | T* uruchomione, T* − N poniżej 10% n | nawet znajomość własnych napraw z tych samych zadań nie podnosi skuteczności; potrzebna wiedza, której błędy rozwiązane przez agenta nie niosą |

## 13. Czego eksperyment nie pokaże

- Niczego o innych modelach, innych benchmarkach ani o zadaniach bez jawnych błędów środowiska.
- Wartości lekcji dla błędów cichych. W pilocie to większość porażek; kompilator ich nie widzi.
- Wartości uczonej użyteczności, konsolidacji, zapominania. Dziennik 9.5 tylko zbiera dane.
- Wierności wobec ExpG: ramię G jest uproszczone i biegnie tylko w etapie rozwojowym.
- Rozdzielenia wpływu klucza od wpływu jednostki: Tp różni się od R+ jednym i drugim, a także długością bloku.
- Wpływu samej obecności bloku: brak placebo dla lekcji. Pilot zmierzył placebo tylko dla dłuższego bloku.
- Zmienności losowej modelu: `temperature 0` daje jeden przebieg na zadanie.
- Zachowania sondy pod promptem v1: sonda używa v2.
- Granicy tego, co mogłaby dać dowolna wiedza o narzędziach: T* ogranicza tylko lekcje z własnych napraw.
- Poprawności etykiet BFCL ponad G1 i G1p.
- Wniosków potwierdzających o lekcjach z Vehicle Control: mechanizm zaprojektowano po obejrzeniu porażek na tych
  zadaniach.

## 14. Miejsce w projekcie i artefakty

- Gałąź `claude/experience-xfer-v1` od `claude/experience-pilot-v0` (`52487db`). Bez wypychania, bez PR i bez
  scalania do `main` bez decyzji właściciela. Bez zmian w plikach pilota, PR #105, kernelu, NIE i plikach
  zamrożonych.
- Kod: `scripts/experience_xfer_v1.py`, `scripts/experience_xfer_v1_analysis.py`,
  `tests/test_experience_xfer_v1.py`. Funkcje pilota wolno importować; plików pilota nie wolno edytować.
- Dane w repozytorium: `data/lab/experience-xfer-v1/` (`PLAN.md` jako kopia tego dokumentu, `config.json`,
  `s0-static.json`, `g1.json`, podziały, pule z sha256, `lessons.jsonl`, `open-problems.json`,
  `g-guidance.json`, `strata.json`, `exposure.json`, `probe-plan.json`, `lesson-usage.jsonl`,
  `raw-freeze.json`, `results-s1.json`, `results-s2.json`, `README.md`).
- Surowe przebiegi poza Git: `GH_REVIVAL/experience-transfer-2026-11-12/raw/`.
- Kolejność commitów: (1) kod, testy, konfiguracja, plan, odczyty statyczne, G1 i G1p przed pierwszym
  wywołaniem; (2) lekcje, wskazówki G, warstwy i plan sondy S1 przed S1c; (3) zamrożenie surowych wyników S1;
  (4) wyniki S1 i decyzja bramek; (5) podziały, pule, lekcje, warstwy i plan sondy S2 przed S2c; (6) zamrożenie
  surowych wyników S2; (7) wyniki i README.
- Wiersz w `data/lab/experiment-registry.csv` i zdarzenia w pamięci projektu po zakończeniu, jak w pilocie.

## 15. Dziennik odstępstw

(pusty)

## 16. Decyzje właściciela potrzebne przed implementacją

1. Zgoda na budżet: do 10 000 lokalnych wywołań i 6 godzin (S1 do 3 600, S2 do 6 400), 0 USD. Wariant
   minimalny: zgoda tylko na S1 i osobna decyzja o S2 po raporcie cząstkowym.
2. Zgoda na zużycie zadań bazowych systemu plików i podróży oraz wariantów `miss_param` trzech domen.
   TradingBot pozostaje rezerwą.
3. Ramię G: zostawić (jedno wywołanie pisarza na narzędzie i dwa ramiona w S1, około 680 wywołań) albo usunąć.
4. Kto implementuje i czy implementacja ma zacząć się od razu po akceptacji.
