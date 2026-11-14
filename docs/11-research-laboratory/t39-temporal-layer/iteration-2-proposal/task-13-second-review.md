# Ponowna recenzja metodologiczna poprawionego planu T39-REVISION (zadanie #13)

## 1. Werdykt: **accept** (warunkowy), falsifiability_ok = true

Protokół nadaje się do przedstawienia właścicielowi do zatwierdzenia. Nie znaczy to, że warstwa działa: implementacja nie istnieje, niczego nie uruchamiałem (koszt 0 USD).

- Z 14 uwag 11 uznaję za rozwiązane, 3 za rozwiązane częściowo (R6, R9, R12), żadnej za nierozwiązaną.
- Znalazłem 13 nowych, drobnych braków. Każdy to poprawka jednego–dwóch zdań w prerejestracji, bez zmiany strategii.
- Warunek akceptacji: N1–N4 muszą wejść do prerejestracji przed napisaniem i pieczęcią H. Nie wymagają kolejnej rundy recenzji planu, tylko sprawdzenia przy zamrażaniu.

## 2. Zakres

Tym razem miałem pełny materiał, w tym pełne pliki stdout wariantów, których autor rewizji nie miał (`context/from_revise-plan/RESULT_response.md:251-251`). Cytaty planu sprawdzałem na plikach wyrywkowo; znalazłem jeden błąd numeru wiersza (N13). Przypisania mutantów, ślad 18/18 i wynik widoku aktywnego prześledziłem ręcznie na fixture. To analiza, nie pomiar.

## 3. Rozstrzygnięcie M1/C7 na surowym wyjściu

| Wariant | exact bitemporal | przecieki | C7 as_known_at | Dowód |
|---|---|---|---|---|
| oryginał | 0.9444 | 0 | poprawne | `context/from_mutation-check/cmd-0.txt:3-12`, jedyna linia bitemporal `:84-84` |
| M1 (fallback zostaje) | 0.6111 | 6 | błędne, `got city is Warsaw LEAK` | `context/from_mutation-check/variant-M1-cmd-0.txt:84-90` |
| NOFALLBACK | 0.9444 | 0 | poprawne; C3 daje `got None` | `context/from_mutation-check/variant-NOFALLBACK-cmd-0.txt:84-84` |
| M1_NOFALLBACK | 0.6667 | 4 | poprawne | `context/from_mutation-check/variant-M1_NOFALLBACK-cmd-0.txt:84-89` |

Przechwycenia z raportu zgadzają się z pełnymi plikami. Liczby są spójne: 7 linii błędów to 11/18, 6 linii to 12/18. Łatki odpowiadają wierszom 107 i 113 źródła (`context/from_mutation-check/RESULT_response.md:212-253`, `context/07_run_revision_v0.py:104-114`).

**Wniosek.** Rozstrzygnięcie Opusa jest poprawne: C7 pada pod M1 wyłącznie przy fallbacku `or live` (`context/07_run_revision_v0.py:113-113`). Projekt nie ma fallbacku, więc zdanie planu (`psuje C1` … i C7, `context/from_revise-plan/from_investigate/RESULT_response.md:98-98`) jest dla projektu fałszywe. C7 zabija M4 na valid_at, nie M1.

**Moje wcześniejsze rozumowanie było wadliwe**, choć wniosek dla projektu się utrzymał:

- Wnioskowałem przez analogię z ramienia valid_only (`context/from_method-review/RESULT_response.md:27-27`). To ramię zwraca None na C7, bo nie ma fallbacku (`context/07_run_revision_v0.py:92-94`), a nie dlatego, że filtr jest tam nieistotny. Czynnika decydującego nie wskazałem.
- Na istniejącym resolwerze dosłowna mutacja M1 psuje C7. Zdanie planu czytane jako opis starego resolwera było więc prawdziwe, a moja wątpliwość w tym odczytaniu błędna.
- Lista „C1, C4×2, C5” potwierdziła się w obu wariantach, ale była niepełna: na starym resolwerze M1 psuje też C2 (`context/from_mutation-check/variant-M1-cmd-0.txt:85-85`).

Ograniczenie pozostaje: warianty dotyczą starego resolwera. Tabela przypisań M1–M15 (`context/from_revise-plan/RESULT_response.md:32-49`) zgadza się z moim niezależnym śladem na fixture (`context/05_events.jsonl:1-14`, `context/04_queries.jsonl:1-18`), ale do bramki BA6 jest analityczna.

## 4. Uwagi R1–R14

| R | Ocena | Uzasadnienie |
|---|---|---|
| R1 | resolved | Hipoteza, podział BA/WK/TK i reguły decyzyjne (`context/from_revise-plan/RESULT_response.md:147-162`, `:226-226`). Zastrzeżenie N2. |
| R2 | resolved | Nieinterferencja na D, X, R, H; klasy wrogich zdarzeń; basis_ids dla abstencji (`:174-183`). Brak kontroli pozytywnej detektora (N6). |
| R3 | resolved | Rozmiar 72–150, minima na rodzinę, błąd krytyczny, punktacja trójdzielna, próg 0/0/0 (`:193-198`). Status F12–F15 trzeba zamknąć przed pieczęcią (N8). |
| R4 | resolved | Ramiona i WK1 przed implementacją (`:160-160`, `:164-173`), lepiej niż prosiłem. Próg częściowo pusty (N1), brak progu dla bitemporal_v0 (N7). |
| R5 | resolved (na papierze) | Wejścia i zakazy autora, drugi etykietujący, pieczęć, otwarcie przez koordynatora (`:185-201`). Niejasna niezależność na poziomie modelu (N5). Infrastruktury nie da się sprawdzić na plikach. |
| R6 | partial | Mechanizm zamrożenia i wartość now są (`:100-100`, `:214-214`). Odpowiedź w luce po korekcie nie trafiła do żadnej decyzji składającej się na S (N4). |
| R7 | resolved | BA3 z dokładnymi oczekiwaniami i asercją valid_to (`:151-151`). Równoważność M5 na D potwierdzam: każda korekta ma valid_from poprzednika (`context/05_events.jsonl:1-2`, `:7-11`). |
| R8 | resolved | Lista rozbieżności wyliczana z góry i haszowana, kryterium dwustronne, raport pokrycia z interpretacją (`:156-156`). Samego R nie mam. |
| R9 | partial | Audyt, gramatyka, korpus błędnych wartości są (`:159-159`). Offsety „tylko jeśli audyt je znajdzie” zostawiają L10 bez testu, a „test statyczny 0 porównań łańcuchowych” nie jest operacyjny (N11). Wymuszenie formatu Z przez pisarza potwierdzam (`context/10_memory_store.py:49-49`, `:378-381`). |
| R10 | resolved | M1–M15, definicja zabicia, 2 łańcuchy, crash się nie liczy (`:154-154`, `:128-145`). Doprecyzować równoważność (N10). |
| R11 | resolved | Adapter haszowany, statusy i przewidywania per rodzina, H2 valid usunięty (`:157-157`). Dwie lektury pytania `before the correction?` potwierdzam (`context/from_revise-plan/15_build_temporal_corpus_h2.py:95-110`). |
| R12 | partial | M1/C7 rozstrzygnięte; recenzja etykiet zaplanowana, niewykonana; maszynowe potwierdzenie śladu przesunięte do BA1/BA6 (`:106-106`). Przesunięcie jest uzasadnione i bramkowane. |
| R13 | resolved | Oś transakcyjna po audycie (decyzja K), składowa łańcucha z known(tx), mutant M15 (`:107-107`). Kolejność haszowania S do poprawy (N8). |
| R14 | resolved | Gold w osobnym pliku, punktacja w osobnym procesie (`:108-108`). Wadę starego runnera potwierdzam (`context/07_run_revision_v0.py:170-172`). |

## 5. Falsyfikowalność, ramiona, nieinterferencja, H

- **Falsyfikowalność: tak.** TK1 i TK2 mają operacyjne progi, są jednorazowe i wykonywane na zamrożonym commicie; każda bramka ma warunek obalenia. Zakres wniosku to zgodność z S i nieinterferencja, nie poprawność S ani użyteczność na realnym logu. Przy n ≥ 72 konstruowanych zapytaniach wynik 0 błędów nie uprawnia do twierdzeń o częstości błędów.
- **Ramiona.** Zestaw jest właściwy. Potwierdzam analitycznie, że widok aktywny na D daje te same 7/18 co one_timestamp (11 linii błędów: `context/from_mutation-check/cmd-0.txt:64-74`).
- **Nieinterferencja.** Właściwość i klasy zdarzeń są dobre, ograniczenia opisane uczciwie (`context/from_revise-plan/RESULT_response.md:179-179`).
- **Niezależność i pieczęć H.** Wystarczające jako projekt.

Słabości tych czterech elementów opisują pozycje N1–N3 i N5–N9 poniżej.

## 6. Nowe uwagi

| # | Waga | Uwaga i poprawka |
|---|---|---|
| N1 | ważna | WK1 jest częściowo pusty. Ramiona nie potrafią zwrócić ambiguous ani unknown (`:172-172`), a 15–40% H to złote abstencje (`:194-194`), więc próg ≤ 0.80 mogą spełnić z samej konstrukcji. Liczyć WK1 i warunek per rodzina na zapytaniach o złotym statusie one lub none. |
| N2 | ważna | Naruszenie protokołu unieważnia wynik symetrycznie (`:226-226`), więc może też unieważnić wynik negatywny. Reguła powinna być asymetryczna: naruszenie unieważnia tylko potwierdzenie, porażka TK na zamrożonym commicie zostaje. |
| N3 | ważna | Brak kontraktu uchwytu zapytania i formatu plików H: jak zapytanie wskazuje łańcuch i co zwraca as_known_at dla uchwytu zapisanego po T. Issue podaje zapytania bez argumentu podmiotu (`context/01_issue-39.md:45-47`), fixture grupuje po tagach (`context/07_run_revision_v0.py:53-54`). Dopisać do S przed pracą autora H. |
| N4 | średnia | Odpowiedź w luce po korekcie (X8, F11, BA3) nie jest objęta decyzjami C, D, E, F, K. Dopisać do decyzji F i do S. |
| N5 | średnia | Wykluczenie „Opus i Fable” nie mówi, czy chodzi o model, czy o sesję; inny model jest tylko „zalecany” (`:185-186`). Dwie sesje tego samego modelu dają skorelowane etykiety. Wymagać, by autor i drugi etykietujący byli różnymi modelami albo jednym z nich był właściciel. |
| N6 | średnia | Brak kontroli pozytywnej detektora nieinterferencji. Mutanty przeciekowe (M1, M2a, M2b, M15) powinny być wykryte przez sam test NI, nie tylko przez testy poprawności. |
| N7 | średnia | bitemporal_v0 nie ma progu (`:168-168`). Dodać do WK1: wynik poniżej 1.000 na H i co najmniej jeden błąd w rodzinie F3. Inaczej H może nie sprawdzać poprawki C3. |
| N8 | niska | S jest haszowana w kroku 0, a decyzja K zamyka się w kroku 2 (`:214-216`). Haszować S po K; ostateczny status F12–F15 zapisać przed krokiem 4. |
| N9 | niska | Nie określono punktacji wyjątku warstwy na zapytaniu H ani walidacji formatu H przed pieczęcią. Wyjątek liczyć jako błąd w rodzinie. |
| N10 | niska | Równoważność mutanta ma znaczyć równoważność semantyczną na wejściach dopuszczonych przez S, przyjmowaną przez kogoś innego niż implementator. Dodać regułę aneksów do zamrożonego X: tylko dopisywanie, nowy skrót. |
| N11 | niska | Znaczniki z offsetem muszą być albo w gramatyce (z testem porządku), albo w korpusie wartości błędnych. Test statyczny zastąpić behawioralnym. |
| N12 | niska | Zalecany mutant M16: as_known_at ocenia ważność na końcu osi zamiast w T. Tak zachowuje się ramię transaction_only, które na D myli się tylko na C3 (`context/from_mutation-check/cmd-0.txt:77-77`), więc X potrzebuje drugiego łańcucha. |
| N13 | niska | Errata: blokada prospective_test_reserved jest w wierszu 42, nie 41 (`context/06_manifest.json:42-42`). Uzupełnienie dla M4 różni się między tabelą a JSON (`:38-38` i `:133-133`). Proza wymienia 8 z 9 przyjętych uwag (`:55-55`). |

## 7. Decyzje A–R: ocena metodologiczna

| Dec. | Ocena | Uwagi |
|---|---|---|
| A | poprawna | A1 zgodne z hipotezą. Raport nie może twierdzić o użyteczności; przy A2 próg przed oznaczeniem próbki. |
| B | poprawna | 18/18 osiągalne (mój ślad się zgadza), ale dopiero po recenzji etykiet (L). |
| C | poprawna, z zastrzeżeniem | Potwierdzam: każde now ≥ 2026-06-01 daje oczekiwane wyniki przy known = koniec logu. Etykieta C5 current (`context/04_queries.jsonl:13-13`) zakłada ten wariant, bo C5-b zapisano 12-01 (`context/05_events.jsonl:11-11`). Decyzja C musi więc zapaść przed zamrożeniem now. Wstrzykiwane now to odstępstwo od sygnatury z Issue. |
| D | poprawna | Wariant unknown zgodny ze SCHEMA (`context/08_SCHEMA.md:76-78`). S musi podać dokładne odpowiedzi dla current i valid_at po obu stronach luki. |
| E | poprawna, wymaga zgody | E1 zmienia derive_temporal_view i test na realnym logu (`context/from_revise-plan/05_test_upcast.py:261-284`). To zmiana kodu produkcyjnego poza samą warstwą. |
| F | do świadomego wyboru | F-b jest ostrożne, ale abstynuje także tam, gdzie poprzednik obowiązuje w każdej gałęzi, i jest trwałe (schemat nie ma scalenia). H tego nie rozstrzygnie, bo mierzy zgodność z S. Dopisać N4; kod przyczyny przy unknown nie jest punktowany. |
| G | poprawna po N5 | Ja też jestem wykluczony jako autor H (znam plan i X). Koszt sesji autora i etykietującego nie jest zerowy z definicji (`:228-228`). |
| H | poprawna po N1, N7 | Tolerancja 0 uzasadniona determinizmem. Próg 0.80 pochodzi z jednego eksperymentu (`context/03_report.md:29-29`). |
| I | poprawna | Domyślne unclassified i valid_from = czas zapisu potwierdzam (`context/10_memory_store.py:354-354`, `:379-379`). Właściciel musi jawnie przyjąć brak dowodu wartości osi dla nowych danych. |
| J | poprawna | Ramię active_view mierzy lukę. Raport twierdzi tylko o warstwie zapytań (`context/10_memory_store.py:433-438`, `:503-505`). |
| K | poprawna | Najpierw audyt. Poprawić kolejność haszowania S (N8). Przesłanek audytu nie da się sprawdzić bez logu. |
| L | poprawna | Nowy manifest. Wszystkie blokady starego są false (`context/06_manifest.json:34-46`). Recenzent etykiet nie jest wskazany. |
| M | poprawna jako bramka | Statusy ustalone po obejrzeniu generatora (ujawnione). Każda rodzina to jeden szablon. Adapter ma dużą swobodę, łagodzoną skrótem. |
| N | poprawna | X pisze autor planu, więc bez mocy konfirmacyjnej (ujawnione). Dodać regułę aneksów (N10). |
| O | poprawna po N10 | Rozważyć M16 (N12). |
| P | poprawna po N1, N2 | WK1 przed implementacją zamyka furtkę. |
| Q | Q1 lepsze | Potwierdzam G14: load_events woła initialize (`context/10_memory_store.py:404-405`), które wykonuje `self.events_path.touch(exist_ok=True)` (`:240-243`), a sygnatura zależy od mtime (`:472-481`). initialize tworzy też katalogi. Skutku touch nie da się sprawdzić na plikach. |
| R | poprawna | Przy prywatnym as_of M14 wystarcza; mój ślad potwierdza zabicie na C1 i C3 valid_at. |

## 8. Czego nie da się sprawdzić na plikach

Pełna lista jest w polu missing_evidence. Najważniejsze: nie istnieją implementacja, specyfikacja S, fixture X, generator NI, adaptery i samo H; nie mam kanonicznego logu ani dokumentu z definicjami jedenastu rodzin.

```json
{
  "verdict": "accept",
  "falsifiability_ok": true,
  "summary": "Accept warunkowy: protokół nadaje się do przedstawienia właścicielowi do zatwierdzenia; nie znaczy to, że warstwa działa (implementacja nie istnieje, nic nie uruchamiano, koszt 0 USD). R1-R14: 11 resolved, 3 partial (R6, R9, R12), 0 unresolved. M1/C7: surowe wyjście potwierdza rozstrzygnięcie Opusa. C7 as_known_at pada pod M1 tylko przy fallbacku or-live (context/from_mutation-check/variant-M1-cmd-0.txt:90-90), a bez fallbacku przechodzi (context/from_mutation-check/variant-M1_NOFALLBACK-cmd-0.txt:84-89). Zdanie planu #8 jest fałszywe dla projektu bez fallbacku. Moje wcześniejsze rozumowanie było wadliwą analogią: ramię valid_only zwraca None na C7, bo nie ma fallbacku (context/07_run_revision_v0.py:92-94); nie wskazałem czynnika decydującego i pominąłem C2. Wniosek dla projektu się utrzymał, ale dla starego resolwera moja wątpliwość była błędna. Falsyfikowalność: TK1 i TK2 mają operacyjne progi i są jednorazowe; zakres wniosku to zgodność z S i nieinterferencja. Nowe uwagi N1-N13, wszystkie jako poprawki jednego-dwóch zdań w prerejestracji. Warunek akceptacji: N1 (WK1 liczony tylko na zapytaniach wyrażalnych przez ramiona), N2 (naruszenie protokołu nie unieważnia wyniku negatywnego), N3 (kontrakt uchwytu zapytania i format H w specyfikacji S) i N4 (luka po korekcie w S) muszą wejść przed napisaniem i pieczęcią H. Przypisania mutantów, ślad 18/18 i wynik active_view 7/18 potwierdziłem własnym śladem na fixture; to analiza, nie pomiar.",
  "review_items": [
    {"id": "R1", "status": "resolved", "assessment": "Hipoteza H-T39 zapisana; bramki BA1-BA11 oddzielone od WK1 i TK1-TK2; obala wyłącznie TK1 lub TK2; porażka TK trwała.", "evidence": "context/from_revise-plan/RESULT_response.md:147-162; context/from_revise-plan/RESULT_response.md:226-226", "remaining": "N2: unieważnienie przy naruszeniu protokołu jest symetryczne."},
    {"id": "R2", "status": "resolved", "assessment": "Test nieinterferencji na D, X, R i H; równość pełnej krotki; klasy wrogich zdarzeń; basis_ids zdefiniowane dla abstencji; ograniczenia opisane.", "evidence": "context/from_revise-plan/RESULT_response.md:174-183; context/07_run_revision_v0.py:156-163", "remaining": "N6: brak kontroli pozytywnej detektora."},
    {"id": "R3", "status": "resolved", "assessment": "Rozmiar 72-150, co najmniej 4 łańcuchy i 6 zapytań na rodzinę, definicja błędu krytycznego, punktacja trójdzielna, próg 0/0/0 per rodzina; F16 wyłączona, F12-F15 warunkowe.", "evidence": "context/from_revise-plan/RESULT_response.md:189-198; context/03_report.md:63-63; context/08_SCHEMA.md:48-56", "remaining": "N8: ostateczny status F12-F15 przed pracą autora H; rodziny niewłączone jawnie poza zakresem wniosków."},
    {"id": "R4", "status": "resolved", "assessment": "Cztery ramiona REV-V0, widok aktywny i oracle na D, X i H; WK1 przez koordynatora przed implementacją, implementator dostaje tylko bit. Analitycznie potwierdzam active_view = 7/18 na D.", "evidence": "context/from_revise-plan/RESULT_response.md:160-160; context/from_revise-plan/RESULT_response.md:164-173; context/from_mutation-check/cmd-0.txt:64-74", "remaining": "N1: próg częściowo pusty; N7: brak progu dla bitemporal_v0."},
    {"id": "R5", "status": "resolved", "assessment": "Na papierze: lista wejść i zakazów autora H, drugi etykietujący, pieczęć sha256 u koordynatora, zamrożony commit, otwarcie przez koordynatora, spory o etykiety tylko przed pieczęcią.", "evidence": "context/from_revise-plan/RESULT_response.md:185-201", "remaining": "N5: niezależność na poziomie modelu; infrastruktura koordynatora niesprawdzalna na plikach."},
    {"id": "R6", "status": "partial", "assessment": "Mechanizm zamrożenia jest (krok 0, S haszowana), now = 2026-11-13T00:00:00Z, X7 i X9 mają po jednej rekomendowanej odpowiedzi, definicja rozwidlenia do wyboru F-a/F-b. Potwierdzam, że każde now >= 2026-06-01 daje oczekiwane wyniki current przy known = koniec logu. Brakuje: odpowiedź w luce po korekcie nie jest objęta żadną decyzją składającą się na S.", "evidence": "context/from_revise-plan/RESULT_response.md:100-100; context/from_revise-plan/RESULT_response.md:214-214; context/04_queries.jsonl:1-18; context/05_events.jsonl:1-14", "remaining": "N4."},
    {"id": "R7", "status": "resolved", "assessment": "BA3 z dokładnymi oczekiwaniami, asercją valid_to i rekonstrukcją sprzed korekty. Równoważność M5 na D potwierdzam: każda korekta ma valid_from poprzednika.", "evidence": "context/from_revise-plan/RESULT_response.md:151-151; context/05_events.jsonl:1-2; context/05_events.jsonl:7-11; context/01_issue-39.md:56-56", "remaining": "Treść uzupełnień X nie istnieje."},
    {"id": "R8", "status": "resolved", "assessment": "FC12 scalone z FC6 w BA8; lista rozbieżności wyliczana regułami z surowych zdarzeń i haszowana przed implementacją; kryterium dwustronne; raport pokrycia z interpretacją zapisaną z góry; R jako bramka.", "evidence": "context/from_revise-plan/RESULT_response.md:156-156; context/10_memory_store.py:421-438", "remaining": "Kanonicznego logu nie ma w context/; reguły zależne od decyzji D nie są wypisane."},
    {"id": "R9", "status": "partial", "assessment": "Audyt formatów, gramatyka, korpus wartości błędnych i decyzja K są w planie; wymuszenie formatu Z przez pisarza v2 potwierdzam. Znaczniki z offsetem są testowane tylko, jeśli audyt je znajdzie, co zostawia ryzyko L10; test statyczny '0 porównań łańcuchowych' nie jest operacyjny.", "evidence": "context/from_revise-plan/RESULT_response.md:103-103; context/from_revise-plan/RESULT_response.md:159-159; context/10_memory_store.py:49-49; context/10_memory_store.py:378-381", "remaining": "N11."},
    {"id": "R10", "status": "resolved", "assessment": "M1-M15 na module produkcyjnym; zabicie = błędna odpowiedź w nazwanym teście na co najmniej 2 łańcuchach; crash nieliczony; wszystkie mutanty, o które prosiłem, dodane. Tabela przypisań na D zgadza się z moim niezależnym śladem.", "evidence": "context/from_revise-plan/RESULT_response.md:32-49; context/from_revise-plan/RESULT_response.md:128-145; context/from_revise-plan/RESULT_response.md:154-154", "remaining": "N10, N12; rozbieżność uzupełnienia dla M4 (N13)."},
    {"id": "R11", "status": "resolved", "assessment": "Adapter haszowany i odcięty od gold; status i przewidywanie per rodzina; FUTURE i HISTORICAL jako bramka, CORRECTION raportowana, OVERLAP i CONFLICT poza zakresem z powodem; H2 valid usunięty. Dwie lektury pytania w CORRECTION i przechowywane valid_to w OVERLAP potwierdzam.", "evidence": "context/from_revise-plan/RESULT_response.md:157-157; context/from_revise-plan/15_build_temporal_corpus_h2.py:95-110; context/from_revise-plan/15_build_temporal_corpus_h2.py:128-142; context/11_manifest.json:13-17", "remaining": "Statusy ustalono po obejrzeniu generatora (ujawnione); plików danych H2 nie ma w context/."},
    {"id": "R12", "status": "partial", "assessment": "M1/C7 rozstrzygnięte maszynowo; niezależna recenzja 18 etykiet zaplanowana (krok 1), niewykonana; maszynowe potwierdzenie śladu 18/18 i przypisań przesunięte do BA1 i BA6. Przesunięcie jest uzasadnione i bramkowane. Mój ślad projektu na D daje 18/18 (analiza).", "evidence": "context/from_revise-plan/RESULT_response.md:106-106; context/from_revise-plan/RESULT_response.md:215-215; context/06_manifest.json:34-46", "remaining": "Recenzent etykiet niewskazany; N10 (reguła aneksów)."},
    {"id": "R13", "status": "resolved", "assessment": "Oś transakcyjna definiowana decyzją K po audycie monotoniczności; składowa łańcucha wyłącznie z known(tx); mutant M15; obcięcie w NI według tej samej definicji.", "evidence": "context/from_revise-plan/RESULT_response.md:107-107; context/from_revise-plan/RESULT_response.md:176-179; context/10_memory_store.py:367-367", "remaining": "N8: S haszowana przed zamknięciem K."},
    {"id": "R14", "status": "resolved", "assessment": "Zapytania bez expected i note; gold w osobnym pliku; punktacja w osobnym procesie po zahaszowaniu odpowiedzi; dotyczy D, X i H. Wadę starego runnera potwierdzam.", "evidence": "context/from_revise-plan/RESULT_response.md:108-108; context/07_run_revision_v0.py:170-172; context/11_manifest.json:13-17", "remaining": "Brak."}
  ],
  "m1_c7_assessment": {
    "question": "Czy usunięcie filtra created_at <= T (M1) psuje C7 as_known_at?",
    "raw_evidence": [
      {"variant": "base", "bitemporal_exact": 0.9444, "future_leaks": 0, "c7_as_known_at": "poprawne", "source": "context/from_mutation-check/cmd-0.txt:3-12; context/from_mutation-check/cmd-0.txt:84-84"},
      {"variant": "M1 (fallback zostaje)", "bitemporal_exact": 0.6111, "future_leaks": 6, "c7_as_known_at": "błędne: got city is Warsaw LEAK", "source": "context/from_mutation-check/variant-M1-cmd-0.txt:3-12; context/from_mutation-check/variant-M1-cmd-0.txt:84-90"},
      {"variant": "NOFALLBACK", "bitemporal_exact": 0.9444, "future_leaks": 0, "c7_as_known_at": "poprawne; C3 daje None", "source": "context/from_mutation-check/variant-NOFALLBACK-cmd-0.txt:3-12; context/from_mutation-check/variant-NOFALLBACK-cmd-0.txt:84-84"},
      {"variant": "M1_NOFALLBACK", "bitemporal_exact": 0.6667, "future_leaks": 4, "c7_as_known_at": "poprawne", "source": "context/from_mutation-check/variant-M1_NOFALLBACK-cmd-0.txt:3-12; context/from_mutation-check/variant-M1_NOFALLBACK-cmd-0.txt:84-89"}
    ],
    "captures_match_full_stdout": true,
    "patches_match_source": "Łatki odpowiadają wierszom 107 i 113 źródła (context/from_mutation-check/RESULT_response.md:212-253; context/07_run_revision_v0.py:104-114).",
    "verdict": "Rozstrzygnięcie Opusa jest poprawne. C7 pada pod M1 wyłącznie przy fallbacku or-live (context/07_run_revision_v0.py:113-113). Projekt nie ma fallbacku, więc zdanie planu #8 (context/from_revise-plan/from_investigate/RESULT_response.md:98-98) jest dla projektu fałszywe; C7 zabija M4 na valid_at, nie M1.",
    "opus_resolution_correct": true,
    "my_earlier_reasoning": "Wadliwe. Wnioskowałem przez analogię z ramienia valid_only (context/from_method-review/RESULT_response.md:27-27), które zwraca None na C7, bo nie ma fallbacku (context/07_run_revision_v0.py:92-94), a nie dlatego, że filtr jest nieistotny. Nie wskazałem czynnika decydującego (fallback). Na istniejącym resolwerze dosłowna mutacja M1 psuje C7, więc zdanie planu czytane jako opis starego resolwera było prawdziwe, a moja wątpliwość w tym odczytaniu błędna. Lista C1, C4x2, C5 potwierdziła się, ale była niepełna: na starym resolwerze M1 psuje też C2 (context/from_mutation-check/variant-M1-cmd-0.txt:85-85).",
    "my_earlier_conclusion_for_design": "Utrzymane: w projekcie bez fallbacku M1 nie ginie na C7.",
    "limitation": "Warianty dotyczą starego resolwera. Przypisania M1-M15 dla projektu są analityczne do BA6; mój niezależny ślad na fixture je potwierdza, ale to nie pomiar."
  },
  "heldout_assessment": {
    "independence": "Wystarczająca jako projekt: autor H bez dostępu do planu, rewizji, recenzji, X, REV-V0, H2, kodu ramion i generatora NI; drugi etykietujący na ślepo; spory rozstrzyga właściciel przed pieczęcią (context/from_revise-plan/RESULT_response.md:185-188).",
    "seal": "Wystarczająca jako projekt: sha256 plików i manifestu w rekordzie misji, pliki poza sandboksem implementatora, pieczęć ostateczna po WK1, jednorazowe otwarcie przez koordynatora na zamrożonym commicie, zakaz zmiany etykiet po otwarciu (context/from_revise-plan/RESULT_response.md:199-201).",
    "falsifiability": "TK1 (0 krytycznych, 0 błędnych rekordów, 0 błędnych abstencji w każdej rodzinie) i TK2 (0 różnic krotki) mają operacyjne progi; WK1 przed implementacją zamyka furtkę unieważnienia po fakcie.",
    "weaknesses": [
      "N1: WK1 częściowo pusty, bo ramiona nie wyrażają ambiguous ani unknown",
      "N2: naruszenie protokołu może unieważnić wynik negatywny",
      "N3: brak kontraktu uchwytu zapytania i formatu plików H",
      "N5: niezależność na poziomie modelu niejednoznaczna; inny model tylko zalecany",
      "N6: detektor nieinterferencji bez kontroli pozytywnej",
      "N7: brak progu dla bitemporal_v0, więc H może nie sprawdzać poprawki C3",
      "N9: brak punktacji wyjątku i walidacji formatu przed pieczęcią",
      "Autor H zna Issue #39, więc rodzina F3 może powielać kształt C3 (ujawnione w planie)"
    ],
    "scope_of_conclusion": "Zgodność z zamrożoną specyfikacją S i nieinterferencja na konstruowanych rodzinach. Nie obejmuje poprawności S, użyteczności na kanonicznym logu ani częstości błędów.",
    "verifiable_on_files": false,
    "conditions_before_seal": ["N1", "N2", "N3", "N4", "N5", "N7", "N8"]
  },
  "decision_assessments": [
    {"id": "A", "assessment": "poprawna", "note": "A1 zgodne z hipotezą; raport nie może twierdzić o użyteczności; przy A2 próg zapisany przed oznaczeniem próbki."},
    {"id": "B", "assessment": "poprawna", "note": "18/18 osiągalne (mój ślad się zgadza), ale dopiero po niezależnej recenzji etykiet (decyzja L)."},
    {"id": "C", "assessment": "poprawna z zastrzeżeniem", "note": "Każde now >= 2026-06-01 daje oczekiwane wyniki przy known = koniec logu. Etykieta C5 current (context/04_queries.jsonl:13-13) zakłada ten wariant, bo C5-b zapisano 12-01 (context/05_events.jsonl:11-11); decyzja C musi zapaść przed zamrożeniem now. Wstrzykiwane now to odstępstwo od sygnatury z Issue (context/01_issue-39.md:45-47)."},
    {"id": "D", "assessment": "poprawna", "note": "Wariant unknown zgodny ze SCHEMA (context/08_SCHEMA.md:76-78). S musi podać dokładne odpowiedzi dla current i valid_at po obu stronach luki."},
    {"id": "E", "assessment": "poprawna, wymaga zgody właściciela", "note": "E1 zmienia derive_temporal_view i test na realnym logu (context/from_revise-plan/05_test_upcast.py:261-284); to zmiana kodu produkcyjnego poza samą warstwą."},
    {"id": "F", "assessment": "do świadomego wyboru", "note": "F-b jest ostrożne, ale abstynuje także tam, gdzie poprzednik obowiązuje w każdej gałęzi, i jest trwałe, bo schemat nie ma operacji scalenia. H tego nie rozstrzygnie. Dopisać odpowiedź w luce po korekcie (N4). Kod przyczyny przy unknown nie jest punktowany."},
    {"id": "G", "assessment": "poprawna po N5", "note": "Recenzent tej sesji też jest wykluczony jako autor H. Koszt sesji autora i etykietującego nie jest zerowy z definicji (context/from_revise-plan/RESULT_response.md:228-228)."},
    {"id": "H", "assessment": "poprawna po N1 i N7", "note": "Tolerancja 0 uzasadniona determinizmem. Próg 0.80 pochodzi z jednego eksperymentu (context/03_report.md:29-29). Wynik 0 błędów na konstruowanych zapytaniach nie uprawnia do twierdzeń o częstości."},
    {"id": "I", "assessment": "poprawna", "note": "Domyślne unclassified i valid_from = czas zapisu potwierdzone (context/10_memory_store.py:354-354; context/10_memory_store.py:379-379). Właściciel musi jawnie przyjąć brak dowodu wartości osi dla nowych danych."},
    {"id": "J", "assessment": "poprawna", "note": "Ramię active_view mierzy lukę; raport twierdzi tylko o warstwie zapytań (context/10_memory_store.py:433-438; context/10_memory_store.py:503-505)."},
    {"id": "K", "assessment": "poprawna", "note": "Najpierw audyt. S haszować po zamknięciu K (N8). Przesłanek audytu nie da się sprawdzić bez kanonicznego logu."},
    {"id": "L", "assessment": "poprawna", "note": "Nowy manifest, stary bez zmian; wszystkie blokady starego są false (context/06_manifest.json:34-46). Recenzent etykiet niewskazany."},
    {"id": "M", "assessment": "poprawna jako bramka bez mocy konfirmacyjnej", "note": "Statusy ustalone po obejrzeniu generatora (ujawnione). Każda rodzina to jeden szablon. Adapter ma dużą swobodę, łagodzoną skrótem i brakiem dostępu do gold."},
    {"id": "N", "assessment": "poprawna", "note": "X pisze autor planu, więc bez mocy konfirmacyjnej (ujawnione). Dodać regułę aneksów (N10)."},
    {"id": "O", "assessment": "poprawna po N10", "note": "Równoważność ma być semantyczna i przyjmowana przez kogoś innego niż implementator. Rozważyć M16 (N12)."},
    {"id": "P", "assessment": "poprawna po N1 i N2", "note": "WK1 przed implementacją jest lepsze niż moja pierwotna propozycja."},
    {"id": "Q", "assessment": "Q1 lepsze", "note": "G14 potwierdzone w kodzie: load_events woła initialize (context/10_memory_store.py:404-405), initialize wykonuje touch i tworzy katalogi (context/10_memory_store.py:240-243), sygnatura zależy od mtime (context/10_memory_store.py:472-481). Skutek touch niesprawdzalny na plikach."},
    {"id": "R", "assessment": "poprawna", "note": "Przy prywatnym as_of mutant M14 wystarcza; mój ślad potwierdza zabicie na C1 i C3 valid_at."}
  ],
  "new_issues": [
    {"id": "N1", "severity": "ważna", "issue": "WK1 częściowo pusty: ramiona nie zwracają ambiguous ani unknown, a 15-40% H to złote abstencje, więc próg <= 0.80 może być spełniony z konstrukcji.", "fix": "Liczyć WK1 i warunek per rodzina tylko na zapytaniach o złotym statusie one lub none.", "when": "przed pieczęcią H", "evidence": "context/from_revise-plan/RESULT_response.md:160-160; context/from_revise-plan/RESULT_response.md:172-172; context/from_revise-plan/RESULT_response.md:194-194"},
    {"id": "N2", "severity": "ważna", "issue": "Naruszenie protokołu unieważnia wynik symetrycznie, więc może unieważnić także wynik negatywny.", "fix": "Reguła asymetryczna: naruszenie unieważnia tylko potwierdzenie; porażka TK na zamrożonym commicie zostaje.", "when": "przed prerejestracją", "evidence": "context/from_revise-plan/RESULT_response.md:226-226"},
    {"id": "N3", "severity": "ważna", "issue": "Brak kontraktu uchwytu zapytania i formatu plików H: jak zapytanie wskazuje łańcuch i co zwraca as_known_at dla uchwytu zapisanego po T. Nie obejmuje tego żadna z decyzji C, D, E, F, K składających się na S.", "fix": "Dopisać do S i do formatu H przed pracą autora H.", "when": "przed napisaniem H", "evidence": "context/01_issue-39.md:45-47; context/07_run_revision_v0.py:53-54; context/from_revise-plan/RESULT_response.md:187-187"},
    {"id": "N4", "severity": "średnia", "issue": "Odpowiedź w luce po korekcie (X8, F11, BA3) nie jest objęta żadną decyzją właściciela.", "fix": "Dopisać do decyzji F i do S.", "when": "przed napisaniem H", "evidence": "context/from_revise-plan/from_investigate/RESULT_response.md:204-204; context/from_revise-plan/RESULT_response.md:236-236"},
    {"id": "N5", "severity": "średnia", "issue": "Wykluczenie Opusa i Fable nie mówi, czy dotyczy modelu, czy sesji; inny model jest tylko zalecany; dwie sesje tego samego modelu dają skorelowane etykiety.", "fix": "Wymagać, by autor i drugi etykietujący byli różnymi modelami albo jednym z nich był właściciel.", "when": "decyzja G", "evidence": "context/from_revise-plan/RESULT_response.md:185-186; context/from_revise-plan/RESULT_response.md:237-237"},
    {"id": "N6", "severity": "średnia", "issue": "Brak kontroli pozytywnej detektora nieinterferencji.", "fix": "Mutanty przeciekowe M1, M2a, M2b i M15 muszą być wykryte przez sam test NI, nie tylko przez testy poprawności.", "when": "BA5/BA6", "evidence": "context/from_revise-plan/RESULT_response.md:153-154"},
    {"id": "N7", "severity": "średnia", "issue": "Ramię bitemporal_v0 nie ma progu, więc H może nie sprawdzać poprawki C3.", "fix": "Dodać do WK1: bitemporal_v0 poniżej 1.000 na H i co najmniej jeden błąd w rodzinie F3.", "when": "przed pieczęcią H", "evidence": "context/from_revise-plan/RESULT_response.md:168-168"},
    {"id": "N8", "severity": "niska", "issue": "S haszowana w kroku 0, decyzja K zamykana w kroku 2; status rodzin F12-F15 pozostaje warunkowy.", "fix": "Haszować S po zamknięciu K; ostateczny status F12-F15 zapisać przed krokiem 4.", "when": "prerejestracja", "evidence": "context/from_revise-plan/RESULT_response.md:214-216; context/from_revise-plan/RESULT_response.md:190-190"},
    {"id": "N9", "severity": "niska", "issue": "Nieokreślona punktacja wyjątku warstwy na zapytaniu H i brak walidacji formatu H przed pieczęcią.", "fix": "Wyjątek liczyć jako błąd w rodzinie; walidacja schematu H przez koordynatora przed pieczęcią.", "when": "prerejestracja", "evidence": "context/from_revise-plan/RESULT_response.md:195-195; context/from_revise-plan/RESULT_response.md:200-200"},
    {"id": "N10", "severity": "niska", "issue": "Równoważność mutanta nieokreślona; brak reguły aneksów do zamrożonego X i mutantów.", "fix": "Równoważność semantyczna na wejściach dopuszczonych przez S, przyjmowana przez stronę inną niż implementator; do X wolno tylko dopisywać, z nowym skrótem.", "when": "prerejestracja", "evidence": "context/from_revise-plan/RESULT_response.md:154-154; context/from_revise-plan/RESULT_response.md:245-245"},
    {"id": "N11", "severity": "niska", "issue": "Znaczniki z offsetem testowane tylko, jeśli audyt je znajdzie; test statyczny braku porównań łańcuchowych nie jest operacyjny.", "fix": "Znaczniki z offsetem umieścić w gramatyce (z testem porządku) albo w korpusie wartości błędnych; test statyczny zastąpić behawioralnym.", "when": "prerejestracja", "evidence": "context/from_revise-plan/RESULT_response.md:103-103; context/from_revise-plan/RESULT_response.md:159-159"},
    {"id": "N12", "severity": "niska", "issue": "Brak mutanta dla as_known_at oceniającego ważność na końcu osi zamiast w T (zachowanie ramienia transaction_only, które na D myli się tylko na C3).", "fix": "Dodać M16 i drugi łańcuch zabijający w X.", "when": "decyzja O", "evidence": "context/from_mutation-check/cmd-0.txt:77-77; context/07_run_revision_v0.py:69-80"},
    {"id": "N13", "severity": "niska", "issue": "Errata: blokada prospective_test_reserved jest w wierszu 42, nie 41; uzupełnienie dla M4 różni się między tabelą a JSON; proza wymienia 8 z 9 przyjętych uwag.", "fix": "Poprawić przy prerejestracji.", "when": "prerejestracja", "evidence": "context/06_manifest.json:42-42; context/from_revise-plan/RESULT_response.md:38-38; context/from_revise-plan/RESULT_response.md:133-133; context/from_revise-plan/RESULT_response.md:55-55"}
  ],
  "missing_evidence": [
    "Implementacja warstwy as_of nie istnieje: przypisania mutantów M1-M15 dla projektu, ślad 18/18, równoważność M5 na D i wynik active_view 7/18 to analiza (moja i autora), nie pomiar",
    "Specyfikacja semantyki S nie istnieje: nie da się ocenić, czy jednoznacznie wyznacza etykiety H",
    "Fixture X (uzupełnienia ponad X1-X10) nie istnieje: przypisania zabijających przypadków w X niesprawdzalne",
    "Generator wrogich zdarzeń NI, adapter ramion, adapter H2, skrypt listy rozbieżności R, runner i scorer PMLAB-REV-V0-002 nie istnieją",
    "Format plików H i kontrakt uchwytu zapytania nie są zdefiniowane",
    "Kanoniczny memory/events.jsonl (podział R): rozmiar, formaty znaczników, monotoniczność created_at, rozkład supersession_kind",
    "docs/11-research-laboratory/revision-benchmark-extension.md (definicje jedenastu rodzin): mapowanie F1-F16 na rodziny protokołu niesprawdzalne",
    "docs/12-interdisciplinary-memory/temporal-provenance-versioning-and-correction-audit-v0.md",
    "Pliki danych H2 (events, queries, gold) i istnienie splitów innych niż dev; przewidywania 14/14 dla adaptera są analityczne",
    "Zachowanie Path.touch(exist_ok=True) na istniejącym pliku i na systemie plików tylko do odczytu (skutek G14): wymaga uruchomienia",
    "Zmodyfikowane pliki skryptu wariantów mutation-check: w context/ są tylko diffy i skróty, nie same pliki",
    "CONTRIBUTING.md i tasks.py check",
    "Raporty PMLAB-STALE-E1 i PMLAB-H1-COMPOSE-E1",
    "Infrastruktura koordynatora: miejsce przechowywania pieczęci i kontrola dostępu sandboksu implementatora",
    "Dostępność i tożsamość niezależnego autora H, drugiego etykietującego i recenzenta etykiet REV-V0",
    "Decyzje właściciela A-R nie zapadły: oceny dotyczą rekomendacji, nie rozstrzygnięć"
  ]
}
```

---

*Integration note (2026-11-14).* Imported unchanged in substance from the AAMR coordinator (task 13, source file `response.md`, SHA-256 of the original `4daee7c71b19c89942acac243f344801a19577b09ffff5ff1c428786d0639143`). The text is the AI-written original, in Polish. The only edits are listed in `PROVENANCE.json`. Status: **REVIEW (AI)**. Nothing in it is an approved decision. See `README.md` in this directory.
