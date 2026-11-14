# Raport misji T39-REVISION

T39: poprawa planu po recenzji Fable (R1-R14), rozstrzygnięcie M1/C7, ponowna niezależna recenzja  
Stan cyklu: **halted**, zatrzymanie: **plan_exhausted**. Źródło AAMR: `1f6a1fd02bb3`. Wygenerowano 2026-11-13T14:07:00+00:00 (mechanicznie, bez modelu).

## Co czeka na Ciebie

- **#3** [halt] Pętla zatrzymana: brak kolejnego zadania w zatwierdzonym planie. integracja przygotowana ([machine-local path omitted]  
  opcje: close; `python -m aamr_coord approvals approve 3 --option ...`

## Zadania

| # | Zadanie | Wykonawca | Stan | Próby | Dowody | Wynik |
|---|---|---|---|---|---|---|
| 11 | mutation-check | tests | succeeded | 1 | — | 3/3 oczekiwań zgodnych z dokumentacją; warianty: 3 |
| 12 | revise-plan | opus | succeeded | 1 | cyt. 159/159, cytaty 3/15, luki 0 ⚠ | PROJEKT DO RECENZJI, NIE ZATWIERDZONY. Koszt 0 USD, nic nie uruchamiano. Autor tej rewizji jest autorem planu #8 (konflikt interesów zgłoszony). (1) M1/C7 rozstrzygnięte na surowym wyjściu (context/from_mutation-check/RESULT_response.md:179-209): C7 as_known_at pada pod M1 tylko z fallbackiem 'or l… |
| 13 | method-rereview | fable | succeeded | 1 | cyt. 138/138, cytaty 2/3, luki 0 ⚠ | werdykt: accept. Accept warunkowy: protokół nadaje się do przedstawienia właścicielowi do zatwierdzenia; nie znaczy to, że warstwa działa (implementacja nie istnieje, nic nie uruchamiano, koszt 0 USD). R1-R14: 11 resolved, 3 partial (R6, R9, R12), 0 unresolved. M1/C7: surowe wyjście potwierdza rozs… |
| 14 | decision-table | sonnet | succeeded | 1 | cyt. 73/73, cytaty 2/4, luki 4 ⚠ | Tabela 18 decyzji (A-N z briefu oraz nowe O, P, Q, R z planu), wszystkie nierozstrzygnięte i wymagające zgody właściciela. Obowiązujący werdykt Fable (ponowna recenzja): accept warunkowy, falsifiability_ok = true (context/from_method-rereview/RESULT_response.md:3-9); protokół może trafić do właścic… |

### #11 mutation-check (tests)

- pełny wynik: `[machine-local path omitted]`

### #12 revise-plan (opus)

- kryteria: 14
- ryzyka: 10
- brakujące dowody: 11
- kontrola dowodów: 12 cytatów niezgodnych z plikiem (do sprawdzenia); nierozwiązane cytowania: ; niezgodne cytaty: 12
- pełny wynik: `[machine-local path omitted]`

### #13 method-rereview (fable)

- werdykt: **accept**; falsyfikowalność: tak
- brakujące dowody: 16
- kontrola dowodów: 1 cytatów niezgodnych z plikiem (do sprawdzenia); nierozwiązane cytowania: ; niezgodne cytaty: 1
- pełny wynik: `[machine-local path omitted]`

### #14 decision-table (sonnet)

- brakujące dowody: 9
- kontrola dowodów: 2 cytatów niezgodnych z plikiem (do sprawdzenia); nierozwiązane cytowania: ; niezgodne cytaty: 2
- pełny wynik: `[machine-local path omitted]`

## Decyzje naukowe (z ostatniego zadania, które je zestawiło)

Modele tylko rekomendują. Nic z poniższego nie jest zatwierdzone.

| ID | Istota decyzji | Warianty | Rekomendacja Opusa | Ocena Fable | Konsekwencje dla poprawności | Twoja zgoda |
|---|---|---|---|---|---|---|
| A | Zakres wniosku eksperymentu | A1: tylko zgodność z zamrożoną semantyką i nieinterferencja; A2: także użyteczność na realnych danych (10-20 pytań historycznych oznaczonych przez właściciela, próg zapisany przed oznaczeniem) | A1, chyba że właściciel oznaczy próbkę (A2) | poprawna; A1 zgodne z hipotezą, raport nie może twierdzić o użyteczności; przy A2 próg przed oznaczeniem próbki | Przy A1 wynik może być odczytany jako dowód wartości osi, której nie mierzono; wartość osi mierzy dopiero A2. | tak |
| B | Próg ponownego uruchomienia REV-V0 | B1: 18/18; B2: >= 0.944 (litera Issue #39; dopuszcza jeden nowy błąd poza C3) | B1; próg liczony na etykietach po niezależnej recenzji (L) | poprawna; 18/18 osiągalne (ślad zgodny), ale dopiero po recenzji etykiet (L); jest to analiza, nie pomiar | 18 etykiet nie przeszło niezależnej recenzji, więc 18/18 może utrwalić błąd etykiety; zmiana etykiety wymusza aktualizację progu. | tak |
| C | Definicja current() i wartości now | C1: valid=now wstrzykiwane, known=koniec logu; now zamrożone w prerejestracji (plan: now = 2026-11-13T00:00:00Z); C2: known=now z zegara systemowego (C5 pada, wynik zależy od daty uruchomienia) | C1, now zamrożone | poprawna z zastrzeżeniem; każde now >= 2026-06-01 daje oczekiwane wyniki; decyzja C musi zapaść przed zamrożeniem now; wstrzykiwane now odstępuje od sygnatury z Issue | Niezamrożone now jest parametrem do strojenia pod wynik; current(now) jest tożsame z valid_at(now), więc zapytania current nie dają niezależnego dowodu. | tak |
| D | Semantyka supersesji 'unclassified' | D1: poprzednik znika z przekonań, valid_at w luce daje 'unknown'; D2: traktować jak korektę (zgadywanie); D3: traktować jak sukcesję (fabrykacja przedziałów, sprzeczne ze SCHEMA) | wariant 'unknown' w luce; przed pieczęcią H | poprawna; wariant unknown zgodny ze SCHEMA; S musi podać dokładne odpowiedzi dla current i valid_at po obu stronach luki | Warunkuje rodzinę F8 w H, X7 i listę rozbieżności R (BA8); na kanonicznym logu wiele odpowiedzi będzie 'unknown', warstwa może wyglądać na bezużyteczną. | tak |
| E | valid_to przez poprawionego następcę (A sukcesja B, B korekta C) | E1: valid_to z pierwszego nieodwołanego następcy; zmiana derive_temporal_view i testu na realnym logu; E2: bez zmiany (valid_to z błędnego, odwołanego rekordu) | E1 ze zgodą na zmianę derive_temporal_view i testu na realnym logu | poprawna, wymaga zgody właściciela; E1 to zmiana kodu produkcyjnego poza samą warstwą | E1 daje poprawną semantykę, ale zmienia pole pochodne używane przez inne ścieżki i istniejące oczekiwania testu; mutant M13 nie ma przypadku zabijającego w D (potrzebne X5 i dodatkowy łańcuch); rodzina F9 w H. | tak |
| F | Konwencje przedziałów, remisów i jedna definicja rozwidlenia | F1: przyjąć [valid_from, valid_to), created_at <= T, remis wg pozycji w logu, kontrakt one/none/ambiguous/unknown, niezależna recenzja; F2: zostawić do implementacji; w ramach F1 do wyboru: F-a (ambiguous, gdy w B(tx) więcej niż 1 rekord łańcucha obowiązuje w T) albo F-b (każde rozwidlenie w known(tx) daje ambiguous dla T >= valid_from rozwidlonego rekordu); osobn… | F1 z F-b i X9 = unknown z kodem przyczyny; recenzja niezależna | do świadomego wyboru; F-b ostrożne, ale abstynuje też tam, gdzie poprzednik obowiązuje w każdej gałęzi, i jest trwałe (schemat nie ma scalenia); H tego nie rozstrzygnie, bo mierzy zgodność z S; dopisać odpowiedź w luce po korekcie (N4) | F2 pozostawia etykiety H bez zamrożonej semantyki; polityka półotwartych przedziałów nigdy nie przeszła niezależnej recenzji; wybór F-a/F-b jest merytoryczny i nieweryfikowalny przez H. | tak |
| G | Autor, etykietujący, uruchamiający i pieczęć zbioru held-out H | G1: autor niezależny od implementatora i autora planu, bez dostępu do planu, X i implementacji; skrót H u koordynatora; uruchamia koordynator; G2: autor lub uruchamiający = implementator (pieczęć fikcyjna) | G1: świeża izolowana sesja, najlepiej innego modelu niż implementator, lub właściciel; uruchamia koordynator; Opus i Fable wykluczeni jako autorzy | poprawna po N5; recenzent też wykluczony jako autor H; koszt sesji autora i etykietującego nie jest zerowy z definicji; N5: autor i drugi etykietujący mają być różnymi modelami albo jednym z nich właściciel | Dwie sesje tego samego modelu dają skorelowane etykiety; autor H może powielić błędy planu, jeśli go zobaczy; spory o etykiety tylko przed otwarciem. | tak |
| H | Rozmiar, skład, tolerancja H i ramiona porównawcze | H1: 0 błędnych rekordów, exact 1.000, progi per rodzina; ramiona REV-V0 i widok aktywny jako kontrola ważności; H2: exact >= 0.95 (próg bez uzasadnienia, agregat może ukryć porażkę rodziny); do rozstrzygnięcia w H1: tolerancja błędnych abstencji 0 albo do 1 niekrytycznej na rodzinę | H1 z tolerancją 0 we wszystkich trzech kategoriach; min. 72 zapytania, >= 4 łańcuchy i 6 zapytań na rodzinę; WK1 <= 0.80 dla ramion bazowych | poprawna po N1 i N7; tolerancja 0 uzasadniona determinizmem; próg 0.80 pochodzi z jednego eksperymentu; wynik 0 błędów na konstruowanych zapytaniach nie uprawnia do twierdzeń o częstości | Ostry próg może dać fałszywą porażkę przy błędzie etykiety; N1: WK1 częściowo pusty (ramiona nie zwracają ambiguous/unknown); N7: brak progu dla bitemporal_v0; porażka H jest trwałym wynikiem negatywnym. | tak |
| I | Wzmocnienie piszącego w Issue #39 (wymagany supersession_kind, korekta dziedziczy valid_from, walidacja kolejności, is_active pod blokadą) | I1: osobne zadanie, ale przed wnioskami o wartości osi na realnych danych; I2: w zakresie #39 (większy zakres, effort:L rośnie) | I1 z jawną akceptacją, że wynik nie dowodzi wartości osi dla nowych danych | poprawna; domyślne unclassified i valid_from = czas zapisu potwierdzone w kodzie; właściciel musi jawnie przyjąć brak dowodu wartości osi dla nowych danych | Przy I1 nowe dane nie zasilają osi ważności do czasu osobnego zadania (powtórka pułapki SESSION_EVENT_DIVERGENT z kotwicy v3); I2 zamyka wyścig TOCTOU i rozwidlenia. | tak |
| J | Czy search, indeks i get().is_active przechodzą na widok czasowy (zmiana SCHEMA.md:21) | J1: osobny krok po #39 z własnym testem; C3 w wyszukiwaniu jako znana luka; J2: w ramach #39 (naprawa end-to-end, zmiana udokumentowanego zachowania wyszukiwania, przebudowa indeksu) | J1; raport twierdzi tylko o naprawie w warstwie zapytań | poprawna; ramię active_view mierzy lukę; raport twierdzi tylko o warstwie zapytań | Do czasu J obowiązujący rekord z przyszłą sukcesją nadal znika z wyszukiwania; raport nie może twierdzić o naprawie w magazynie. | tak |
| K | Oś transakcyjna przy niemonotonicznym created_at i zachowanie przy złym znaczniku | K1: najpierw audyt formatów i monotoniczności na kanonicznym logu (tylko odczyt), potem decyzja (pozycja w logu / odrzucenie / flaga; wyjątek dla magazynu albo 'unknown' z flagą dla łańcucha); K2: decyzja teraz bez audytu | K1 (najpierw audyt R, potem decyzja) | poprawna; najpierw audyt; S haszować po zamknięciu K (N8); przesłanek audytu nie da się sprawdzić bez kanonicznego logu | K2 grozi łączną niespełnialnością FC6 i FC11; porównania znaczników jako łańcuchów mogą wpuścić rekord z przyszłości przy różnych offsetach; K warunkuje rodziny F12-F14 w H i BA11. | tak |
| L | Niezależna recenzja 18 etykiet REV-V0 i polityki przedziałów oraz manifest | L1: recenzja przed użyciem REV-V0 jako bramki; nowy manifest PMLAB-REV-V0-002; stary manifest i wyniki bez zmian; L2: aktualizacja starego manifestu (ryzyko nadpisania historii) | L1 (nowy manifest); M1/C7 rozstrzygnięte maszynowo, pozostałe przypisania mutantów analityczne do BA6 | poprawna; nowy manifest, wszystkie blokady starego false; recenzent etykiet niewskazany | Jeśli recenzja zmieni etykietę, trzeba zaktualizować próg z decyzji B; przypisania mutantów i ślad 18/18 to analiza, nie pomiar, do BA1/BA6. | tak |
| M | Rola H2 (mapowanie schematu H2 na v2, które rodziny są bramką) | M1: bramką FUTURE (w planie poszerzone o HISTORICAL); reszta raportowana; adapter zamrożony skrótem i odcięty od gold; statusy zapisane z góry; inne splity nie otwierane; M2: wszystkie rodziny jako bramka (ryzyko zafałszowania mapowaniem) | M1 w wersji poszerzonej o HISTORICAL; CORRECTION tylko raport; OVERLAP i CONFLICT poza zakresem; H2 valid usunięty | poprawna jako bramka bez mocy konfirmacyjnej; statusy ustalone po obejrzeniu generatora (ujawnione); każda rodzina to jeden szablon | Bramkę zawężono po obejrzeniu danych; FUTURE to jedna struktura; adapter ma dużą swobodę, łagodzoną skrótem i brakiem dostępu do gold. | tak |
| N | Fixture X (zestaw przypadków X1-X10) z jednoznacznymi oczekiwaniami | N1: nowy plik fixture (REV-V0 zamrożony); X7 i X9 z jedną odpowiedzią; asercja o valid_to; N2: zostawić X9 z oczekiwaniem 'flaga lub ambiguous' (przypadku nie da się oblać) | N1; X uzupełnione tak, by każdy mutant miał >= 2 łańcuchy zabijające | poprawna; X pisze autor planu, więc bez mocy konfirmacyjnej (ujawnione); dodać regułę aneksów (N10) | D i X to testy akceptacyjne bez mocy konfirmacyjnej; porażka kończy się poprawką i ponownym przebiegiem, obalić może tylko H; treść uzupełnień X nie istnieje. | tak |
| O | NOWA: zestaw mutantów i definicja zabicia | O1: M1-M15, zabicie = błędna odpowiedź w nazwanym teście na >= 2 łańcuchach; crash nie liczy się; równoważne zgłaszane z dowodem przed przebiegiem; O2: zestaw z planu M1-M7 | O1 | poprawna po N10; równoważność semantyczna, przyjmowana przez kogoś innego niż implementator; rozważyć M16 (N12) | Zgłoszenie równoważności może ukryć słaby test, stąd dowód zapisany przed przebiegiem; przypisania mutantów dla projektu są analityczne do bramki BA6. | tak |
| P | NOWA: ważność H i postępowanie przy porażce lub naruszeniu protokołu | P1: WK1 przed implementacją (próg <= 0.80 i dyskryminacja per rodzina); porażka TK trwała; naruszenie protokołu unieważnia wynik bez potwierdzenia; P2: ważność sprawdzana po otwarciu | P1 | poprawna po N1 i N2; WK1 przed implementacją zamyka furtkę; N2: reguła ma być asymetryczna (naruszenie unieważnia tylko potwierdzenie, porażka TK zostaje) | P2 pozwala unieważnić niewygodny wynik po fakcie; przy symetrycznym unieważnieniu (obecny zapis P1) naruszenie mogłoby unieważnić także wynik negatywny. | tak |
| Q | NOWA: ścieżka odczytu i pomiar append-only (G14) | Q1: warstwa czyta log nową funkcją bez initialize(), a BA7 wymaga też niezmienionego mtime; Q2: warstwa używa load_events, a BA7 dopuszcza zmianę mtime events.jsonl | Q1 | Q1 lepsze; G14 potwierdzone w kodzie (load_events woła initialize, które wykonuje touch; sygnatura indeksu zależy od mtime); skutek touch niesprawdzalny na plikach | Przy Q2 sam odczyt może unieważniać sygnaturę indeksu i wywołać przebudowę; zachowanie touch nie zostało potwierdzone uruchomieniem. | tak |
| R | NOWA (nie mylić z uwagami R1-R14): czy as_of(valid, known) jest publicznym API | R-a: tylko trzy zapytania z #39; as_of prywatne; X bez zapytań pozaprzekątniowych poza valid_at; R-b: as_of publiczne; X i H zawierają zapytania z known różnym od valid i od końca logu | R-a dla #39; zamiana osi (M14) wykrywalna przez valid_at w D | poprawna; przy prywatnym as_of mutant M14 wystarcza, ślad potwierdza zabicie na C1 i C3 valid_at | Przy R-b bez testów pozaprzekątniowych błąd osi w publicznym API pozostaje niewykryty (L12). | tak |

## Polecenia

- postęp: `python -m aamr_coord mission show T39-REVISION`
- decyzje: `python -m aamr_coord approvals`
- zatrzymanie: `python -m aamr_coord mission stop T39-REVISION --reason "..."`
