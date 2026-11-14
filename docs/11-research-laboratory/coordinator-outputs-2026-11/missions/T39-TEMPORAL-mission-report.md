# Raport misji T39-TEMPORAL

Issue #39: warstwa zapytań temporalnych i pułapka C3 (future-effective supersession)  
Stan cyklu: **halted**, zatrzymanie: **plan_exhausted**. Źródło AAMR: `1f6a1fd02bb3`. Wygenerowano 2026-11-13T11:41:33+00:00 (mechanicznie, bez modelu).

## Co czeka na Ciebie

- **#1** [halt] Pętla zatrzymana: brak kolejnego zadania w zatwierdzonym planie. integracja przygotowana ([machine-local path omitted]  
  opcje: close; `python -m aamr_coord approvals approve 1 --option ...`

## Zadania

| # | Zadanie | Wykonawca | Stan | Próby | Dowody | Wynik |
|---|---|---|---|---|---|---|
| 7 | reproduce | tests | succeeded | 1 | — | 6/6 oczekiwań zgodnych z dokumentacją |
| 8 | investigate | opus | succeeded | 1 | — | C3 (PMLAB-REV-V0) wynika z dwóch błędów w gałęzi as_known_at resolwera bitemporal (context/12_run_revision_v0.py:104-114). Rekord C3-a uznano za martwy tylko dlatego, że istnieje następca C3-b, choć sukcesja zamyka przedział dopiero na C3-b.valid_from=2026-09-01. Fallback `or live` zamienił brak od… |
| 9 | method-review | fable | succeeded | 1 | — | werdykt: revise. Diagnoza C3 i projekt as_of(valid, known) są spójne z dostępnymi dowodami (context/03_results.json:604-621, 424-441; context/04_SCHEMA.md:71-78), a szkielet protokołu (zapieczętowany held-out, mutacje, nowe ID eksperymentu) jest właściwy. Plan nie może jednak jeszcze potwierdzić an… |
| 10 | owner-brief | sonnet | succeeded | 1 | — | Misja T39-TEMPORAL (koszt 0 USD, bez implementacji). ODTWORZONO: reprodukcja w Dockerze zgodna z dokumentacją w 6/6 oczekiwań (context/02_response.md): REV-V0 bitemporal 0.944 exact i 0 przecieków, one_timestamp 0.389, błąd C3 as_known_at w ramieniu bitemporal; H2 dev newest 0.200, resolver 1.000. … |

### #7 reproduce (tests)

- pełny wynik: `[machine-local path omitted]`

### #8 investigate (opus)

- kryteria falsyfikowalne: 12
- ryzyka: 12
- pełny wynik: `[machine-local path omitted]`

### #9 method-review (fable)

- werdykt: **revise**; falsyfikowalność: nie
- wymagane zmiany: 14
- pełny wynik: `[machine-local path omitted]`

### #10 owner-brief (sonnet)

- pełny wynik: `[machine-local path omitted]`

## Decyzje naukowe (z ostatniego zadania, które je zestawiło)

Modele tylko rekomendują. Nic z poniższego nie jest zatwierdzone.

| ID | Istota decyzji | Warianty | Rekomendacja Opusa | Ocena Fable | Konsekwencje dla poprawności | Twoja zgoda |
|---|---|---|---|---|---|---|
| A | Zakres wniosku eksperymentu (O1) | A1: tylko zgodność z zamrożoną semantyką i brak przecieku (nieinterferencja); A2: także użyteczność na realnych danych | — | — | — | — |
| B | Próg ponownego uruchomienia REV-V0: 18/18 czy >= 0.944 z Issue #39 (D2/O2) | B1: 18/18; B2: >= 0.944 | — | — | — | — |
| C | Definicja current() i wartości now (D1, L5) | C1: valid=now wstrzykiwane, known=koniec logu; wartości now dla każdego zapytania current zamrożone w prerejestracji; C2: known=now (zegar systemowy) | — | — | — | — |
| D | Semantyka supersesji 'unclassified', dominującej w realnym logu (D3) | D1: poprzednik znika z przekonań, valid_at w luce daje 'unknown'; D2: traktować jak korektę; D3: traktować jak sukcesję | — | — | — | — |
| E | valid_to przez poprawionego następcę, czyli A sukcesja B, B korekta C (D5, G4) | E1: valid_to z pierwszego nieodwołanego następcy; zmiana derive_temporal_view i testu na realnym logu; E2: bez zmiany | — | — | — | — |
| F | Konwencje: przedziały [valid_from, valid_to), warunek created_at <= T, remis według pozycji w logu, jedna definicja rozwidlenia (D6, D8) | F1: przyjąć wraz z kontraktem wyniku one/none/ambiguous/unknown i zlecić niezależną recenzję; F2: zostawić do implementacji | — | — | — | — |
| G | Autor, uruchamiający i pieczęć zbioru held-out H (D10/O4) | G1: autor niezależny od implementatora i autora planu, bez dostępu do sekcji 4 planu, X1-X10 i implementacji; skrót H przechowuje koordynator; uruchamia koordynator; G2: autor lub uruchamiający = implementator | — | — | — | — |
| H | Rozmiar, skład i tolerancja błędów H oraz ramiona porównawcze (FC8, O3, R3, R4) | H1: 0 błędnych rekordów, exact 1.000, progi per rodzina; rozmiar i minimum na rodzinę ustalone przed pieczęcią; ramiona REV-V0 i dzisiejszy widok aktywny uruchomione na X i H jako kontrola ważności; H2: exact >= 0.95 jak w planie | — | — | — | — |
| I | Wzmocnienie piszącego w Issue #39 (D7, G10): wymagany supersession_kind, korekta dziedziczy valid_from, walidacja kolejności, is_active pod blokadą | I1: osobne zadanie, ale przed wnioskami o wartości osi na realnych danych; I2: w zakresie #39 | — | — | — | — |
| J | Czy search, indeks i get().is_active przechodzą na widok czasowy, co zmienia SCHEMA.md:21 (D4/O7) | J1: osobny krok po #39 z własnym testem; C3 w wyszukiwaniu zgłoszone jako znana luka; J2: w ramach #39 | — | — | — | — |
| K | Znaczniki czasu: czas transakcyjny przy niemonotonicznym created_at oraz zachowanie przy złym znaczniku (O8, O9, R9, R13) | K1: najpierw audyt formatów i monotoniczności na kanonicznym logu (tylko odczyt), potem decyzja; wybór między pozycją w logu, odrzuceniem i flagą oraz między wyjątkiem dla całego magazynu a 'unknown' ; K2: decyzja teraz bez audytu | — | — | — | — |
| L | Niezależna recenzja 18 etykiet REV-V0 i polityki przedziałów oraz manifest (D11/O11, R12) | L1: recenzja przed użyciem REV-V0 jako bramki; nowy manifest dla PMLAB-REV-V0-002 z nowym plikiem wyników; stary manifest i 07_results.json bez zmian; L2: aktualizacja starego manifestu | — | — | — | — |
| M | Rola H2 (D9/O10): mapowanie schematu H2 na v2 i które rodziny są bramką | M1: bramką tylko TEMP-FUTURE 14/14; pozostałe rodziny raportowane; adapter zamrożony skrótem przed uruchomieniem i odcięty od złotych odpowiedzi; status (w zakresie lub poza) i przewidywanie per rodzi; M2: wszystkie rodziny jako bramka | — | — | — | — |
| N | Zestaw przypadków X1-X10 jako nowy fixture z jednoznacznymi oczekiwaniami (D12, R6, R7) | N1: nowy plik fixture (REV-V0 zamrożony); X7 i X9 z jedną oczekiwaną odpowiedzią; FC4 z dokładnymi oczekiwaniami dla korekty i sukcesji oraz asercją o valid_to; N2: zostawić X9 z oczekiwaniem 'flaga lub ambiguous' | — | — | — | — |

## Polecenia

- postęp: `python -m aamr_coord mission show T39-TEMPORAL`
- decyzje: `python -m aamr_coord approvals`
- zatrzymanie: `python -m aamr_coord mission stop T39-TEMPORAL --reason "..."`
