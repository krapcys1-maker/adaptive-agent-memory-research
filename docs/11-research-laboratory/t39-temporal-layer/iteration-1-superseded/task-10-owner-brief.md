# Brief dla właściciela: T39-TEMPORAL (zadanie #10)

Korzystałem tylko z plików w `context/`. Niczego nie uruchamiałem ani nie publikowałem, koszt wyniósł 0 USD. Szkic komentarza jest w JSON poniżej, oznaczony jako niepublikowany.

## Co odtworzono
- Reprodukcja w Dockerze zgadza się z dokumentacją w 6 z 6 oczekiwań (`context/02_response.md`).
  - REV-V0: bitemporal 0.944 exact i 0 przecieków, one_timestamp 0.389.
  - Błąd C3 `as_known_at` w ramieniu bitemporal się powtarza.
  - H2 dev: newest 0.200, resolver 1.000.
- Przyczyna C3 to dwa błędy w gałęzi `as_known_at` resolwera (`context/03_response.md` §1.2).
  1. Rekord uznano za martwy tylko dlatego, że istnieje następca.
  2. Fallback `or live` zamienił brak odpowiedzi na nieobowiązujące 7%.
- Poprawna reguła już istnieje w gałęzi `valid_at` tego samego pliku.

## Co ustalono, także negatywnie
- Ta sama reguła żywotności siedzi w kodzie produkcyjnym (`current_records`, `get().is_active`, `rebuild_index`). Przyszła sukcesja usuwa więc obowiązujący rekord z wyszukiwania.
- `derive_temporal_view` nie ma odcięcia transakcyjnego, nie ujawnia rodzaju następcy i przy rozwidleniu po cichu wybiera ostatni zapis. Listę G1–G13 wyprowadzono z samego tekstu kodu, nikt jej nie uruchomił.
- Wyniki negatywne z wcześniejszych prac:
  - mechanizm B dostał werdykt DROP (0 napraw netto);
  - kotwica czasowa v3 zakończyła się FAIL, po wcześniejszym E1 SUPPORTED;
  - korpusy REV-V0 i H2 napisali autorzy znający rodziny przypadków;
  - manifest REV-V0 jest nieaktualny, a wszystkie jego blokady mają wartość `false`.
- Wszystkie ramiona mają 1.00 na `current`. Oś czasowa ma wartość tylko dla pytań historycznych.
- Ręczny ślad 18/18 projektu jest analizą, a nie pomiarem.

## Plan po ocenie metodologicznej
- Werdykt recenzji to **revise**, z `falsifiability_ok = false` (`context/04_response.md`). Strategia zostaje bez zmian, zmiany są bezkosztowe.
- Diagnoza C3 i projekt `as_of(valid, known)` są spójne z dowodami.
- Brakuje trzech rzeczy:
  - **FC8** (jedyne kryterium konfirmacyjne) nie ma rozmiaru H, składu rodzin ani definicji błędu krytycznego.
  - **FC2** opiera się na `basis_ids`, czyli na deklaracji badanej warstwy. Potrzebny jest test nieinterferencji.
  - Plan porzucił ramiona porównawcze, które dawały REV-V0 falsyfikowalność.
- Pięć kryteriów (FC4, FC6, FC8, FC11, FC12) nie ma operacyjnego warunku obalenia.
- Do wykonania są zmiany R1–R14.
- Kolejność: zamrożenie decyzji, niezależny autor H z pieczęcią, implementacja, mutanty i bramki, otwarcie H raz, raport.

## Zastrzeżenia do wiarygodności
- Recenzent miał 7 z 22 plików, więc luk G1–G13 i przypisań mutantów nie zweryfikował.
- Znalazł jedną rozbieżność: plan twierdzi, że usunięcie filtra transakcyjnego psuje C7. Ramię `valid_only` bez tego filtra odpowiada na C7 poprawnie (`context/04_response.md` §2). Trzeba to potwierdzić maszynowo przed prerejestracją.

```json
{
  "summary": "Misja T39-TEMPORAL (koszt 0 USD, bez implementacji). ODTWORZONO: reprodukcja w Dockerze zgodna z dokumentacją w 6/6 oczekiwań (context/02_response.md): REV-V0 bitemporal 0.944 exact i 0 przecieków, one_timestamp 0.389, błąd C3 as_known_at w ramieniu bitemporal; H2 dev newest 0.200, resolver 1.000. USTALONO: C3 wynika z dwóch błędów w gałęzi as_known_at resolwera: (1) rekord uznany za martwy, bo istnieje następca, choć sukcesja zamyka przedział dopiero na valid_from następcy (2026-09-01); (2) fallback 'or live' zamienia brak odpowiedzi na nieobowiązujące 7% (context/03_response.md §1.2). Poprawna reguła istnieje w gałęzi valid_at tego samego pliku. Ta sama reguła żywotności działa w kodzie produkcyjnym (current_records, get().is_active, rebuild_index), a derive_temporal_view nie ma odcięcia transakcyjnego, nie ujawnia rodzaju następcy i przy rozwidleniu po cichu wybiera ostatni zapis (G1-G13; luki wyprowadzone z tekstu kodu, nie z uruchomienia). WYNIKI NEGATYWNE I OGRANICZENIA: mechanizm B dostał werdykt DROP (0 napraw netto); kotwica czasowa v3 zakończyła się FAIL (po wcześniejszym E1 SUPPORTED); korpusy REV-V0 i H2 napisali autorzy znający rodziny przypadków; manifest REV-V0 jest nieaktualny, wszystkie jego blokady mają wartość false; wszystkie ramiona mają 1.00 na current, więc oś czasowa ma wartość tylko dla pytań historycznych; ręczny ślad 18/18 projektu jest analizą, nie pomiarem. PLAN PO OCENIE METODOLOGICZNEJ: werdykt recenzji 'revise', falsifiability_ok=false (context/04_response.md). Diagnoza C3 i projekt as_of(valid, known) są spójne z dowodami. Brakuje: operacyjnego kryterium konfirmacyjnego FC8 (brak rozmiaru H, składu rodzin i definicji błędu krytycznego), niezależnego od implementacji testu przecieku (FC2 opiera się na basis_ids, czyli na deklaracji badanej warstwy; potrzebny test nieinterferencji), ramion porównawczych porzuconych względem REV-V0. Pięć kryteriów (FC4, FC6, FC8, FC11, FC12) nie ma operacyjnego warunku obalenia. Do wykonania zmiany R1-R14, bezkosztowe i bez zmiany strategii; kolejność: zamrożenie decyzji, niezależny autor H z pieczęcią, implementacja, mutanty i bramki, jednorazowe otwarcie H, raport z wynikami negatywnymi. ZASTRZEŻENIA: recenzent miał 7 z 22 plików, więc G1-G13 i przypisań mutantów nie zweryfikował; znalazł rozbieżność (plan twierdzi, że usunięcie filtra transakcyjnego psuje C7, a ramię valid_only bez tego filtra odpowiada na C7 poprawnie, context/04_response.md §2) do potwierdzenia maszynowego przed prerejestracją. Poniżej 14 decyzji dla właściciela (scalone D1-D12 z planu i O1-O11 z recenzji) oraz szkic komentarza do Issue #39, NIEOPUBLIKOWANY.",
  "decisions": [
    {
      "id": "A",
      "decision": "Zakres wniosku eksperymentu (O1)",
      "options": [
        {"option": "A1: tylko zgodność z zamrożoną semantyką i brak przecieku (nieinterferencja)", "consequence": "bez kosztu po stronie właściciela; raport nie może twierdzić, że warstwa jest użyteczna na realnych danych"},
        {"option": "A2: także użyteczność na realnych danych", "consequence": "wymaga 10-20 pytań historycznych do kanonicznego logu, ręcznie oznaczonych przez właściciela; dopiero to mierzy wartość osi czasowej"}
      ],
      "recommendation": "A1, chyba że właściciel zechce oznaczyć próbkę (wtedy A2)",
      "risk": "przy A1 wynik może być odczytany jako dowód wartości osi, której nie mierzono; plan sam przewiduje, że valid_at na kanonicznym logu da głównie 'unknown' (context/03_response.md §7, ryzyka)",
      "sources": ["context/04_response.md §6 pkt 1, O1", "context/03_response.md ryzyka"]
    },
    {
      "id": "B",
      "decision": "Próg ponownego uruchomienia REV-V0: 18/18 czy >= 0.944 z Issue #39 (D2/O2)",
      "options": [
        {"option": "B1: 18/18", "consequence": "osiągalne, bo jedyny błąd ramienia bitemporal to C3; nie dopuszcza nowej regresji"},
        {"option": "B2: >= 0.944", "consequence": "zgodne z literą Issue, ale dopuszcza jeden nowy błąd poza C3"}
      ],
      "recommendation": "B1; w Issue zaznaczyć, że próg zaostrzono",
      "risk": "niski; 18 etykiet nie przeszło niezależnej recenzji, więc 18/18 może utrwalić błąd etykiety (patrz decyzja L)",
      "sources": ["context/04_response.md §3 FC1", "context/01_issue-39.md"]
    },
    {
      "id": "C",
      "decision": "Definicja current() i wartości now (D1, L5)",
      "options": [
        {"option": "C1: valid=now wstrzykiwane, known=koniec logu; wartości now dla każdego zapytania current zamrożone w prerejestracji", "consequence": "deterministyczne; C5 przechodzi, bo C5-b ma created_at 2026-12-01, a dziś jest 2026-11-13"},
        {"option": "C2: known=now (zegar systemowy)", "consequence": "C5 pada; wynik zależy od daty uruchomienia"}
      ],
      "recommendation": "C1",
      "risk": "niezamrożone now jest parametrem do strojenia pod wynik; current(now) jest tożsame z valid_at(now), więc zapytania current nie dają niezależnego dowodu",
      "sources": ["context/03_response.md §4 pkt 6", "context/04_response.md §4 L5"]
    },
    {
      "id": "D",
      "decision": "Semantyka supersesji 'unclassified', dominującej w realnym logu (D3)",
      "options": [
        {"option": "D1: poprzednik znika z przekonań, valid_at w luce daje 'unknown'", "consequence": "uczciwe wobec braku danych; na kanonicznym logu wiele odpowiedzi to 'unknown'"},
        {"option": "D2: traktować jak korektę", "consequence": "więcej odpowiedzi, ale zgadywanie"},
        {"option": "D3: traktować jak sukcesję", "consequence": "fabrykacja przedziałów, sprzeczne ze SCHEMA"}
      ],
      "recommendation": "Wariant 'unknown' (pierwszy). Musi zapaść przed pieczęcią H",
      "risk": "warstwa może wyglądać na bezużyteczną na realnym logu, dopóki piszący nie zacznie podawać rodzaju supersesji (decyzja I)",
      "sources": ["context/03_response.md D3", "context/04_response.md O5"]
    },
    {
      "id": "E",
      "decision": "valid_to przez poprawionego następcę, czyli A sukcesja B, B korekta C (D5, G4)",
      "options": [
        {"option": "E1: valid_to z pierwszego nieodwołanego następcy; zmiana derive_temporal_view i testu na realnym logu", "consequence": "poprawna semantyka; zmienia istniejące oczekiwania testu (tests/test_upcast.py)"},
        {"option": "E2: bez zmiany", "consequence": "valid_to pochodzi z błędnego, odwołanego rekordu"}
      ],
      "recommendation": "E1, wymaga zatwierdzenia zmiany schematu przez właściciela",
      "risk": "zmiana wpływa na pole pochodne używane przez inne ścieżki; przypadek X5 testuje tę regułę",
      "sources": ["context/03_response.md D5, G4", "context/04_response.md O5"]
    },
    {
      "id": "F",
      "decision": "Konwencje: przedziały [valid_from, valid_to), warunek created_at <= T, remis według pozycji w logu, jedna definicja rozwidlenia (D6, D8)",
      "options": [
        {"option": "F1: przyjąć wraz z kontraktem wyniku one/none/ambiguous/unknown i zlecić niezależną recenzję", "consequence": "usuwa niespójność definicji rozwidlenia (więcej niż 1 następca albo więcej niż 1 rekord obejmujący T); konieczny krok przed etykietami H"},
        {"option": "F2: zostawić do implementacji", "consequence": "etykiety H powstałyby bez zamrożonej semantyki"}
      ],
      "recommendation": "F1",
      "risk": "polityka półotwartych przedziałów nigdy nie przeszła niezależnej recenzji (blokada manifestu REV-V0 nadal false)",
      "sources": ["context/04_response.md FC9, O5", "context/03_response.md D6, D8"]
    },
    {
      "id": "G",
      "decision": "Autor, uruchamiający i pieczęć zbioru held-out H (D10/O4)",
      "options": [
        {"option": "G1: autor niezależny od implementatora i autora planu, bez dostępu do sekcji 4 planu, X1-X10 i implementacji; skrót H przechowuje koordynator; uruchamia koordynator", "consequence": "zachowuje moc konfirmacyjną; koszt 0 USD"},
        {"option": "G2: autor lub uruchamiający = implementator", "consequence": "pieczęć jest fikcją, H jest kopią specyfikacji"}
      ],
      "recommendation": "G1",
      "risk": "autor H może powielić błędy planu, jeśli dostanie jego treść; spory o etykiety wolno rozstrzygać wyłącznie przed otwarciem",
      "sources": ["context/04_response.md R5, L7, L8, O4"]
    },
    {
      "id": "H",
      "decision": "Rozmiar, skład i tolerancja błędów H oraz ramiona porównawcze (FC8, O3, R3, R4)",
      "options": [
        {"option": "H1: 0 błędnych rekordów, exact 1.000, progi per rodzina; rozmiar i minimum na rodzinę ustalone przed pieczęcią; ramiona REV-V0 i dzisiejszy widok aktywny uruchomione na X i H jako kontrola ważności", "consequence": "ostre kryterium; porażka H jest trwałym wynikiem negatywnym pod nowym ID"},
        {"option": "H2: exact >= 0.95 jak w planie", "consequence": "próg bez uzasadnienia w wynikach; przy małym n oznacza 100%; agregat może ukryć porażkę rodziny"}
      ],
      "recommendation": "H1. Dodatkowo pokryć pięć rodzin nietestowanych w REV-V0 albo jawnie wyłączyć je z zakresu wniosków",
      "risk": "ostry próg może dać porażkę z powodu błędu etykiety; dlatego spory o etykiety tylko przed otwarciem",
      "sources": ["context/04_response.md FC8, R3, R4, O3"]
    },
    {
      "id": "I",
      "decision": "Wzmocnienie piszącego w Issue #39 (D7, G10): wymagany supersession_kind, korekta dziedziczy valid_from, walidacja kolejności, is_active pod blokadą",
      "options": [
        {"option": "I1: osobne zadanie, ale przed wnioskami o wartości osi na realnych danych", "consequence": "Issue #39 pozostaje węższe; do tego czasu nowe dane nie zasilają osi ważności"},
        {"option": "I2: w zakresie #39", "consequence": "większy zakres (effort:L rośnie); wyścig TOCTOU i rozwidlenia zostają zamknięte"}
      ],
      "recommendation": "I1",
      "risk": "przy I1 wynik nie dowodzi wartości osi dla nowych danych (powtórka pułapki SESSION_EVENT_DIVERGENT z kotwicy v3); właściciel musi to jawnie zaakceptować",
      "sources": ["context/03_response.md G10, D7", "context/04_response.md O6"]
    },
    {
      "id": "J",
      "decision": "Czy search, indeks i get().is_active przechodzą na widok czasowy, co zmienia SCHEMA.md:21 (D4/O7)",
      "options": [
        {"option": "J1: osobny krok po #39 z własnym testem; C3 w wyszukiwaniu zgłoszone jako znana luka", "consequence": "mniejsze ryzyko regresji; raport może twierdzić tylko, że C3 naprawiono w warstwie zapytań, nie w magazynie"},
        {"option": "J2: w ramach #39", "consequence": "naprawia C3 end-to-end, ale zmienia udokumentowane zachowanie wyszukiwania i wymaga przebudowy indeksu o valid_from/valid_to"}
      ],
      "recommendation": "J1",
      "risk": "do czasu J obowiązujący rekord z przyszłą sukcesją nadal znika z wyszukiwania",
      "sources": ["context/03_response.md G6, G7, D4", "context/04_response.md O7"]
    },
    {
      "id": "K",
      "decision": "Znaczniki czasu: czas transakcyjny przy niemonotonicznym created_at oraz zachowanie przy złym znaczniku (O8, O9, R9, R13)",
      "options": [
        {"option": "K1: najpierw audyt formatów i monotoniczności na kanonicznym logu (tylko odczyt), potem decyzja; wybór między pozycją w logu, odrzuceniem i flagą oraz między wyjątkiem dla całego magazynu a 'unknown' z flagą dla łańcucha", "consequence": "decyzja oparta na danych; rozstrzyga konflikt FC6 z FC11"},
        {"option": "K2: decyzja teraz bez audytu", "consequence": "ryzyko, że kanoniczny log zawiera nietypowy format, wtedy FC6 i FC11 są łącznie niespełnialne"}
      ],
      "recommendation": "K1",
      "risk": "porównania znaczników jako łańcuchów znaków (G5) mogą po cichu wpuścić rekord z przyszłości przy różnych offsetach",
      "sources": ["context/04_response.md L3, L10, R9, R13, O8, O9"]
    },
    {
      "id": "L",
      "decision": "Niezależna recenzja 18 etykiet REV-V0 i polityki przedziałów oraz manifest (D11/O11, R12)",
      "options": [
        {"option": "L1: recenzja przed użyciem REV-V0 jako bramki; nowy manifest dla PMLAB-REV-V0-002 z nowym plikiem wyników; stary manifest i 07_results.json bez zmian", "consequence": "zachowuje wyniki historyczne; dodaje krok recenzji"},
        {"option": "L2: aktualizacja starego manifestu", "consequence": "ryzyko nadpisania historii"}
      ],
      "recommendation": "L1. W ramach L maszynowo potwierdzić ręczny ślad 18/18 i przypisania mutantów, w tym rozbieżność C7/M1",
      "risk": "jeśli recenzja zmieni którąś etykietę, próg 18/18 (decyzja B) trzeba zaktualizować",
      "sources": ["context/03_response.md D11, manifest", "context/04_response.md R12, O11"]
    },
    {
      "id": "M",
      "decision": "Rola H2 (D9/O10): mapowanie schematu H2 na v2 i które rodziny są bramką",
      "options": [
        {"option": "M1: bramką tylko TEMP-FUTURE 14/14; pozostałe rodziny raportowane; adapter zamrożony skrótem przed uruchomieniem i odcięty od złotych odpowiedzi; status (w zakresie lub poza) i przewidywanie per rodzina zapisane z góry; innych splitów H2 nie otwierać; dla H2 valid zdefiniować kryterium albo usunąć", "consequence": "ogranicza strojenie adaptera; rodzina w zakresie, która zawiedzie, obala"},
        {"option": "M2: wszystkie rodziny jako bramka", "consequence": "ryzyko, że mapowanie H2 (przechowywane valid_to w OVERLAP, source vs source_refs) zafałszuje wynik"}
      ],
      "recommendation": "M1",
      "risk": "TEMP-FUTURE to 14 instancji jednego szablonu, więc jedna struktura; bramkę zawężono po obejrzeniu danych",
      "sources": ["context/03_response.md D9", "context/04_response.md FC7, R11, L6, O10"]
    },
    {
      "id": "N",
      "decision": "Zestaw przypadków X1-X10 jako nowy fixture z jednoznacznymi oczekiwaniami (D12, R6, R7)",
      "options": [
        {"option": "N1: nowy plik fixture (REV-V0 zamrożony); X7 i X9 z jedną oczekiwaną odpowiedzią; FC4 z dokładnymi oczekiwaniami dla korekty i sukcesji oraz asercją o valid_to", "consequence": "X staje się specyfikacją przez przykłady, bramką akceptacyjną"},
        {"option": "N2: zostawić X9 z oczekiwaniem 'flaga lub ambiguous'", "consequence": "przypadku nie da się oblać"}
      ],
      "recommendation": "N1. Pamiętać, że D i X to testy akceptacyjne bez mocy konfirmacyjnej (korpus napisał implementator schematu, projekt wyprowadzono z tych samych 18 zapytań)",
      "risk": "porażka na D lub X kończy się poprawką i ponownym przebiegiem; obalić może tylko H",
      "sources": ["context/04_response.md §5, FC4, R6, R7", "context/03_response.md D12"]
    }
  ],
  "draft_issue_comment": "[DRAFT - NOT PUBLISHED. Community Manager is in dry-run; the owner must approve before anything is posted to Issue #39.]\n\nDesign sketch for the temporal query layer (no code yet). Feedback on the points marked OPEN is very welcome.\n\n**Diagnosis of C3.** In `scripts/run_revision_v0.py` the bitemporal arm's `as_known_at` branch has two faults:\n1. It treats a record as dead as soon as a successor exists among the records known at T. A succession does not withdraw a record; it closes the validity interval at the successor's `valid_from`. Only a correction says the record was wrong.\n2. A fallback (`or live`) turns \"nothing is in force at T\" into \"return the successor\", which hides the first fault. Without the fallback the answer would be an explicit `None`.\n\nThe correct rule is already present in the same file's `valid_at` branch, which is why C3 passes there and fails only in `as_known_at`. The same liveness rule (a record is active if it has no successor) also appears in `MemoryStore.current_records`/`get().is_active` and in `rebuild_index`, so a future-effective succession currently drops the still-valid record from search. I read this from the source, I have not run it.\n\n**Proposed shape.** One pure function `as_of(valid_time, known_time)` over events upcast to v2; the three queries are special cases:\n- `current(now)` = `as_of(valid=now, known=end of log)`, with `now` injected rather than read from the clock;\n- `valid_at(T)` = `as_of(valid=T, known=end of log)`;\n- `as_known_at(T)` = `as_of(valid=T, known=T)`.\n\nRules:\n1. Known set = events with `created_at <= T`; ties broken by log position. Cut the log *before* deriving interval ends, because `derive_temporal_view` currently computes ends from the whole log (a leak through derived fields, e.g. an answer of \"nothing in force\" caused by a successor written after T).\n2. Only a correction removes a record from belief; a succession sets `valid_to = successor.valid_from`.\n3. Half-open intervals `[valid_from, valid_to)`; `None` means unbounded.\n4. Result has four states: `one`, `none` (no fallback), `ambiguous` (a fork returns both ids, never a silent winner), `unknown` (supersession of unclassified kind has no interval).\n5. The chain is the connected component of `supersedes`, computed from the known set only.\n6. The layer only derives; it never appends or rewrites events. It would live in a new module with thin `MemoryStore` methods on top of `load_events`.\n\n**How it would be tested.**\n- Re-run `PMLAB-REV-V0` against the real layer. A hand trace of my design gives 18/18, but that is an analysis, not a measurement, and the labels have not had independent review.\n- Treat the future-effective family of the H2 corpus as a second target, with the existing caveat that its author knew the families.\n- Add extension cases: a `current` query for C3 before and after 1 September, a leak through derived fields, an exact interval boundary, a fork, and a corrected successor date.\n- Mutation tests on the production module: removing the `created_at <= T` filter, taking interval ends from the full log, deciding liveness by the existence of a successor, restoring the fallback, swapping correction and succession, and closing the interval at the end.\n- A non-interference check for `as_known_at`: the answer must be identical on the full log, on the log truncated at T, and on a log with hostile future events appended.\n- A sealed held-out set written by someone other than the implementer, opened once. A failure there would be recorded as a negative result, not tuned away.\n\n**OPEN questions.**\n- What should `current()` return for a chain whose supersession is `unclassified` (most v1 data)? I lean towards `unknown` for the gap rather than inventing an interval.\n- Should `valid_to` follow the first non-withdrawn successor when a successor is later corrected? This changes `derive_temporal_view` and its test.\n- Should `search`/`is_active` move to the temporal view in this issue or in a follow-up? I propose a follow-up, with C3-in-search documented as a known gap.\n- Should the writer (`MemoryStore.supersede`) be tightened (explicit supersession kind, a correction inheriting `valid_from`, ordering checks) as part of this issue? Without that, new data will not populate the validity axis.\n\nOne honest caveat from the experiment itself stays: every arm scored 1.00 on `current`, so the value of this axis is entirely in historical questions. This sketch does not claim to measure value on real data.\n\nI would like to take this issue (or the query-layer slice) if the direction above looks right; I will wait for feedback on the open points before writing code.",
  "acceptance_met": [
    {
      "criterion": "Każda decyzja ma opcje i konsekwencje",
      "met": true,
      "evidence": "14 decyzji (A-N) z polami options (z konsekwencją każdej opcji), recommendation i risk; scalono D1-D12 z context/03_response.md i O1-O11 z context/04_response.md; decyzje zależne od siebie (np. D przed pieczęcią H, L przed użyciem progu z B) wskazano w polach risk i recommendation"
    },
    {
      "criterion": "Szkic komentarza oznaczony jako niepublikowany i bez danych prywatnych",
      "met": true,
      "evidence": "Pierwszy wiersz szkicu: '[DRAFT - NOT PUBLISHED ...]'. Szkic nie zawiera ścieżek lokalnych, adresów e-mail, identyfikatorów zadań ani kosztów; odwołuje się tylko do plików i faktów jawnych w Issue #39 (scripts/run_revision_v0.py, upcast.py, memory_store.py, PMLAB-REV-V0, korpus H2). Pominięto też wyniki wewnętrzne (mechanizm B, kotwica czasowa)"
    },
    {
      "criterion": "Brief obejmuje: co odtworzono, co ustalono (także negatywnie), plan po ocenie, decyzje z rekomendacją i ryzykiem",
      "met": true,
      "evidence": "Sekcje briefu i pole summary: reprodukcja 6/6 (context/02_response.md); przyczyna C3 i luki G1-G13, wyniki negatywne (context/03_response.md §1-3); werdykt 'revise' i zmiany R1-R14 (context/04_response.md); zastrzeżenie, że recenzent miał 7 z 22 plików, oraz rozbieżność C7/M1"
    },
    {
      "criterion": "Ograniczenia: brak eksperymentów, płatnych API i GPU; brak zmian w AAMR; strategia bez zmian",
      "met": true,
      "evidence": "Praca wyłącznie na plikach w context/, koszt 0 USD, bez uruchamiania kodu; rekomendacje nie zmieniają zatwierdzonej strategii (context/04_response.md §1: braki 'da się usunąć bez zmiany strategii'); decyzje wymagające właściciela wypisano jawnie"
    }
  ]
}
```

---

*Integration note (2026-11-14).* Imported unchanged in substance from the AAMR coordinator (task 10, source file `response.md`, SHA-256 of the original `33028689f6e90d07a3c7c569b54c37d08a12142847887b0fd0ae90dd0e6ed0d6`). The text is the AI-written original, in Polish. The only edits are listed in `PROVENANCE.json`. Status: **SUPERSEDED**. Nothing in it is an approved decision. See `README.md` in this directory.
