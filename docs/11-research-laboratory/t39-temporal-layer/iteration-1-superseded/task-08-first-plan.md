# Zadanie #8 · T39-TEMPORAL: błąd C3, luki magazynu, wcześniejsze prace, projekt i kryteria

Przeczytałem wszystkie 22 pliki z `context/`. Nie uruchamiałem kodu ani modeli, koszt wyniósł 0 USD. Liczby z pomiarów pochodzą z wyniku reprodukcji (`context/22_response.md`) i z artefaktów historycznych. Zachowanie kodu ustaliłem z samego tekstu źródeł.

---

## 1. Mechanizm błędu C3

### 1.1 Rekordy z fixture
| id | created_at | valid_from | supersedes | supersession_kind | title |
|---|---|---|---|---|---|
| C3-a | 2026-01-10 | 2026-01-01 | — | — | rate is 5 percent |
| C3-b | 2026-01-15 | **2026-09-01** | C3-a | succession | rate is 7 percent |

Źródło: `context/10_events.jsonl:5-6`. Zapytania z `context/09_queries.jsonl:7-8`:
- `valid_at(2026-05-01)`, oczekiwane 5%;
- `as_known_at(2026-05-01)`, oczekiwane 5%, z notatką „a store ordering by write time alone answers 7 and is wrong”.

### 1.2 Ślad w `resolve_bitemporal`, gałąź `as_known_at` (`context/12_run_revision_v0.py:104-114`)
```text
visible   = [C3-a (01-10 ≤ T), C3-b (01-15 ≤ T)]        # filtr transakcyjny: poprawny
successor = {"C3-a": C3-b}                              # _superseded_by, l.57-58
live      = [C3-b]                                       # BŁĄD 1: C3-a „martwy”, bo następca ISTNIEJE
in_force  = [e for e in live if valid_from ≤ T] = []     # C3-b obowiązuje dopiero od 09-01
in_force  = [] or live = [C3-b]                          # BŁĄD 2: fallback `or live`
answer    = "rate is 7 percent"                          # zgodne z 22_response.md (bitemporal C3 as_known_at … got 7)
```
- **Błąd 1 (przyczyna).** Żywotność rekordu jest ustalana na osi transakcyjnej, czyli „ma następcę wśród znanych rekordów”. Tymczasem sukcesja nie odbiera przekonania o rekordzie, tylko zamyka jego przedział ważności na `valid_from` następcy. Według SCHEMA tylko korekta stwierdza, że rekord był błędny (`context/02_SCHEMA.md:71-75`).
- **Błąd 2 (maskowanie).** Gdy żaden żywy rekord nie obowiązuje w T, fallback zwraca rekord jeszcze nieobowiązujący. Bez niego odpowiedź byłaby `None`, czyli nadal zła, ale jawna. Z nim błąd staje się cichy.
- **Dowód, że to kwestia reguły, a nie danych.** Gałąź `valid_at` tego samego resolwera (`:126-140`) ma poprawną regułę: `if following["valid_from"] > at: live_at.append(candidate)` (l.136-137). Daje więc 5%, co potwierdza `context/07_results.json:604-611`. Ramię `valid_only` też poprawnie odpowiada 5% w obu zapytaniach C3 (`07_results.json:424-441`). Ramiona `transaction_only` i `one_timestamp` odpowiadają 7% (`22_response.md`, tail cmd-0).
- **Pola pochodne są poprawne, pułapka leży w ich interpretacji.** `derive_temporal_view` dla C3-a daje `expired_at = 2026-01-15` oraz `valid_to = 2026-09-01` (`context/03_upcast.py:212-218`). Kto użyje `expired_at` (oś transakcyjna, „wycofany”) jako filtra żywotności dla pytania o świat w T, odtworzy C3. W modelu SQL:2011 sukcesja kończy w czasie systemowym jedynie *otwartą* wersję faktu. Nadal obowiązuje wersja zamknięta [01-01, 09-01). Opis `expired_at` w SCHEMA („when the record was withdrawn”, `02_SCHEMA.md:51`) dla sukcesji jest więc semantycznie mylący.

### 1.3 Ten sam błąd ukryty w `current`
Gałąź `current` (`12_run_revision_v0.py:119-122`) filtruje po `valid_from <= "9999-12-31T23:59:59Z"`, co nie odrzuca niczego, więc w ogóle ignoruje czas ważności. Gdyby `current` zadano przed 09-01, odpowiedź brzmiałaby 7%. Fixture nie ma zapytania `current` dla C3 (`09_queries.jsonl:7-8`), dlatego błąd nie wychodzi. Dokładnie taki kształt ma rodzina H2 TEMP-FUTURE („What is … right now?”, asked_on 20, nowa reguła od dnia 40; `context/15_build_temporal_corpus_h2.py:80-93`).

---

## 2. Luki prawdziwego magazynu (na poziomie funkcji)

| # | Funkcja | Luka | Skutek |
|---|---|---|---|
| G1 | `upcast.derive_temporal_view` (`03_upcast.py:177-219`) | Brak parametru odcięcia transakcyjnego (`known_at`): wylicza końce z **całego** logu | Kto zbuduje `as_known_at` na tym widoku, przecieka przez pola pochodne. Przykład: C2 `as_known_at(2026-06-05)`. Prawda to „brown”, bo C2-b zapisano dopiero 06-10. Widok z pełnego logu daje C2-a `valid_to=06-01`, czyli nic nie obowiązuje. Metryka `leaked()` (`12_run_revision_v0.py:156-163`) sprawdza tylko rekord-odpowiedź, więc tego nie wykryje |
| G2 | jw. | Nie udostępnia `superseded_by` ani rodzaju następcy, wystawia tylko `expired_at`/`valid_to` | Wywołujący nie odróżni odwołania rekordu (korekta) od zamknięcia przedziału (sukcesja). Najprostsza żywotność „ma `expired_at`” to dokładnie C3 |
| G3 | jw. `successor[target] = event` (l.206-210) | Przy dwóch następcach jednego rekordu wygrywa ostatni w kolejności pliku, bez sygnału | „Silent winner” to krytyczne odrzucenie z `08_manifest.json:27-33` |
| G4 | jw. | `valid_to` liczone tylko od bezpośredniego następcy | Łańcuch A →succ B →corr C (poprawiona data zmiany) daje A `valid_to = B.valid_from`, mimo że B uznano za błędny |
| G5 | jw. | Porównania czasu odbywają się na łańcuchach znaków. Brak parsowania i walidacji `created_at` dla v1 | Niepoprawny format porówna się po cichu. To właśnie lekcja z Graphiti „parse failure is silent” (`11_…comparison-v0.md:63-69`) |
| G6 | `MemoryStore.current_records` / `get` (`04_memory_store.py:421-438`) | Aktywny znaczy „niezastąpiony”: żywotność czysto transakcyjna | **To reguła C3 w kodzie produkcyjnym.** `get("C3-a")["is_active"] == False`, choć C3-a obowiązuje do 09-01 |
| G7 | `MemoryStore.rebuild_index` (`:503-505`) i z nim `search`/`context` | Pomija zastąpione rekordy. Metadane indeksu nie mają `valid_from`/`valid_to` (`:506-515`) | Od chwili zapisu przyszłej sukcesji rekord nadal obowiązujący znika z wyszukiwania. Filtrowania czasowego nie da się dodać bez przebudowy indeksu. Reguła wprost w `02_SCHEMA.md:21` |
| G8 | `load_events` / `timeline` (`:404-419`, `:440-444`) | Zwracają surowe zdarzenia, bez upcastu. `memory_store.py` w ogóle nie importuje `upcast` | Widok czasowy nie jest używany przez żadną ścieżkę magazynu w migawce, tylko przez testy (`05_test_upcast.py:22-31`) |
| G9 | brak | Nie ma `current()`, `valid_at(T)` ani `as_known_at(T)` | `01_issue-39.md:6` |
| G10 | `MemoryStore.supersede` (`:342-402`) | (a) domyślnie `supersession_kind="unclassified"`, więc nowe zapisy nie dostają `valid_to`; (b) `valid_from` domyślnie = czas zapisu także dla korekty; (c) brak walidacji `succession.valid_from ≥ predecessor.valid_from`; (d) sprawdzenie `is_active` przez `get()` jest **poza** blokadą `_append` | (a) oś ważności dalej pusta dla nowych danych; (b) korekta bez daty zostawia lukę [stare valid_from, teraz); (c) ujemne przedziały; (d) wyścig TOCTOU, dwóch piszących może stworzyć rozwidlenie, które G3 rozstrzygnie po cichu |
| G11 | brak klucza podmiotu | Łańcuchy istnieją tylko przez `supersedes`. Fixture grupuje po `tags` (`12_…:53-54`), a `supersede` pozwala tagi zmienić (`:367`) | Warstwa musi definiować łańcuch przez spójną składową `supersedes`, nie przez tagi |
| G12 | `tests/test_upcast.py` | Testuje wyłącznie pola pochodne (`:232-284`). Brak testów zapytań, przecieków i mutacji | Kryterium #39 „test, który pada po usunięciu filtra” nie ma pokrycia |
| G13 | runner REV-V0 (`12_…:172`) | Resolwer dostaje cały słownik zapytania razem z `expected`. Ślepota jest tylko konwencją. Wykrywanie przecieków opiera się na `title`, nie na `id` | Kontrola przecieków jest za słaba jak na bramkę |

---

## 3. Wcześniejsze prace i ich wyniki (także negatywne)

| Praca | Wynik | Ograniczenia i wynik negatywny | Źródło |
|---|---|---|---|
| **PMLAB-REV-V0-001** | bitemporal 0.944 exact, 0 przecieków, 0 krytycznych; valid_only 0.778 (4 przecieki); transaction_only 0.722 (valid_at 0.20); one_timestamp 0.389 (as_known_at 0.00, 6 przecieków). Odtworzone 6/6 w Dockerze | Wszystkie ramiona mają 1.00 na `current`: oś czasowa nic nie daje dla pytań o teraz. Jedyny błąd ramienia bitemporal to C3. Korpus napisał implementator schematu, n=1, 6 z 11 rodzin. Ramiona to reimplementacje | `06_report.md`, `07_results.json`, `22_response.md` |
| Manifest REV-V0 | status „preregistration-draft-…-no-run-no-result”, **wszystkie blokady `false`** (m.in. `half_open_interval_policy_independently_reviewed`, `oracle_labels_independently_reviewed`, `prospective_test_reserved`). Ramiona T0–T5 różnią się od uruchomionych (brak T1 i T5) | Manifest jest nieaktualny wobec raportu. Polityka przedziałów i etykiety wyroczni nigdy nie przeszły niezależnej recenzji | `08_manifest.json` |
| **PMLAB-H2-TEMP-E1 (dev)** | newest 0.200, resolver 1.000, abstencja 0.200 (=CONFLICT). Newest trafia tylko CORRECTION (1.000), w pozostałych rodzinach 0 | Autor znał rodziny. Resolwer używa regexów na treści pytania (`14_…:48-50`) i heurystyki „drugi od końca” (`:106`). Inny schemat: dni jako liczby, `record_kind`, `source`, **przechowywane `valid_to`** w OVERLAP (`15_…:132-135`) wbrew zasadzie „derived, never stored”. Odtworzono tylko split dev | `14_`, `15_`, `16_manifest.json`, `22_response.md` |
| **Mechanizm B, CURRENT_STATE_OVER_HISTORY** | Stage 1: **DROP**. BASE 12/12 i +B 12/12, 0 napraw netto. Rdzeń mechanizmu zadziałał 0 razy w 24 wykonaniach. Retest naprawczy też się nie powiódł (hipoteza błędna). Koszt 0.022315 + 0.041754 USD | Mem0 1.0.6 skonsolidował historię przy zapisie i nadpisuje `metadata.timestamp`. W RET1_JOB zachował środkowy fakt. Prerejestracja nie miała pytań historycznych. Wniosek z dokumentu: brak dowodu, a nie dowód przeciwny | `17_`, `18_`, `19_preregistration.json` |
| **Kotwica czasowa E1** | TEMPORAL_ANCHOR_SUPPORTED: +2 netto (native), +3 (wide), 0 regresji | Placebo +1 przy wide. +SRC −1 przy obu punktach. 10 jednostek | `21_READ_SIDE_TEMPORAL_ANCHOR_V1.md` |
| **Kotwica czasowa v3 (TEMPORAL_BOUNDARY)** | **MECHANISM_I_FAIL**: 0 napraw netto na 8 jednostkach, 0 regresji. Stage 2 wcześniej −1 netto. Trzecia z rzędu porażka rodziny mechanizmów, więc zmiana strategii. Koszt 0.559315 USD | Błędy wynikały z braku pobranych dokumentów. Powtórzyła się pułapka SESSION_EVENT_DIVERGENT: czas sesji ≠ czas zdarzenia, czyli te same dwie osie | `20_TEMPORAL_ANCHOR_BOUNDARY_V3.md` |
| Porównanie modeli (Graphiti/SQL:2011) | Przyjęto 4 pola na 2 osiach i jeden mechanizm z dwoma znacznikami czasu | Nie kopiować cichego porzucania dat. Brak modelu wygasania (decay) przyjęto jako ograniczenie | `11_temporal-memory-model-comparison-v0.md` |
| PMLAB-STALE-E1 *(cytowane pośrednio)* | Pary zastąpień na 99,5 percentylu podobieństwa, 2 pary z cosinusem 1.000. Stary fakt najbliższym sąsiadem 6/9 bez filtra | Raport nie jest w context/, cytuję za `17_…:24` i `03_upcast.py:109-113` | pośrednie |
| PMLAB-H1-COMPOSE-E1 *(pośrednie)* | Resolwer nic nie zmienia na H1, wyniki identyczne do trzech miejsc po przecinku (wynik negatywny) | Raport nie jest w context/ | `15_…:5-9` |

Wniosek dla projektu. Mechanizmy odczytowe (B, kotwica) zawiodły tam, gdzie warstwa zapisu niszczy historię albo myli czas zapisu z czasem zdarzenia. AAMR ma log append-only, więc tego problemu nie ma. Warunek: warstwa wyłącznie wylicza wartości i nigdy nie zapisuje, a piszący naprawdę podają `valid_from` i `supersession_kind` (G10).

---

## 4. Projekt warstwy `current()` / `valid_at(T)` / `as_known_at(T)`

**Zasada.** Jest jedna funkcja dwuosiowa `as_of(valid_time, known_time)`. Trzy zapytania z #39 to jej przypadki szczególne.

1. **Zbiór znanych rekordów.** `known(tx)` = zdarzenia z `created_at ≤ tx` po upcaście do v2. Remisy rozstrzyga pozycja w logu, bo jest to prawdziwy porządek transakcyjny pod blokadą. Wartość `tx = None` oznacza koniec logu.
2. **Wyprowadzenie końców wyłącznie z `known(tx)`.** To jest poprawka G1: wywołanie `derive_temporal_view(known(tx))`, czyli odcięcie *przed* wyprowadzeniem. Do tego potrzebne jest jawne wystawienie `superseded_by` i `supersession_kind` następcy (G2).
3. **Stan przekonań B(tx).** Należą do niego rekordy z `known(tx)` z wyjątkiem **odwołanych**, czyli takich, których następca w `known(tx)` jest korektą. Następca będący sukcesją **nie usuwa** rekordu, tylko nadaje mu `valid_to`. To reguła anty-C3. Następca `unclassified` zależy od decyzji D3.
4. **Przedział ważności.** Półotwarty `[valid_from, valid_to)`, gdzie `None` oznacza ∞. Przypadek C6 daje alice o 12:00:00 i bob o 12:00:01.
5. **Odpowiedź.** Rekordy z łańcucha (spójna składowa `supersedes`, G11), których przedział zawiera `valid_time`:
   - dokładnie 1 → `status: one`;
   - 0 → `none`, **bez fallbacku** (usunięcie błędu 2);
   - więcej niż 1 → `ambiguous` z listą id (zakaz cichego zwycięzcy, G3);
   - przedział nieznany (unclassified) → `unknown`.
   Każdy wynik niesie `basis_ids`: rekord-odpowiedź **oraz** rekordy, z których wyprowadzono jego przedział. Służą do kontroli przecieku po id.
6. **Mapowanie zapytań:**
   - `current(now)` = `as_of(valid=now, known=koniec logu)`. Parametr `now` musi być wstrzykiwany (decyzja D1). Przy `known=now` przypadek C5 by padł, bo C5-b ma `created_at` 2026-12-01, a dziś jest 2026-11-13 (`10_events.jsonl:11`, `09_queries.jsonl:13`).
   - `valid_at(T)` = `as_of(valid=T, known=koniec logu)`.
   - `as_known_at(T)` = `as_of(valid=T, known=T)`.
7. **Umiejscowienie.** Czyste funkcje w nowym module, np. `tools/project_memory/temporal.py`, plus cienkie metody `MemoryStore.current/valid_at/as_known_at`. Metody używają `load_events` i **nie wołają** `_append` ani `rebuild_index`. Runner REV-V0 w nowej wersji podstawia fixture jako `memory/events.jsonl` w katalogu tymczasowym i odpytuje `MemoryStore`, nie własny resolwer. Tak spełnia się kryterium „against the real store”. Do warstwy trafiają wyłącznie `{subject→chain, type, at}`, bez `expected` (G13).

**Ręczna weryfikacja projektu na 18 zapytaniach.** Prześledziłem rekordy z `10_events.jsonl`: C1 (black, black, brown), C2 (green, brown, brown), C3 (5, 5), C4 (68, 60, 70), C5 (open, closed), C6 (bob, alice), C7 (Warsaw, None, None). Wychodzi 18/18. To wynik analityczny, nie pomiar: kodu nie ma.

**Usunięcie filtra transakcyjnego** psuje C1 `as_known_at`, C4 ×2, C5 (krytyczne) i C7. Mutant jest więc wykrywalny, czego wymaga kryterium #39.

---

## 5. Kryteria skuteczności (próg i warunek obalenia)

Pełna lista FC1–FC12 jest w bloku JSON. Najważniejsze:
- **FC1.** REV-V0 na prawdziwej warstwie: 18/18, w tym oba zapytania C3. Obala: którekolwiek C3 błędne albo exact < 0.944. Próg #39 (≥ 0.944) dopuszcza jeden błąd poza C3; proponuję 1.000 (decyzja D2).
- **FC2.** 0 przecieków liczonych po id **łącznie z rekordami w `basis_ids`** (przeciek przez pola pochodne). Obala: ≥ 1.
- **FC3.** 100% zabitych mutantów M1–M7. Obala: którykolwiek mutant przeżyje.
- **FC4.** Korekta i sukcesja dają różne `valid_at` w luce [poprzednik.valid_from, następca.valid_from). Obala: identyczne odpowiedzi.
- **FC5.** sha256 `events.jsonl` bez zmian po pełnym zestawie zapytań, zero zapisów w `memory/`.
- **FC6.** Totalność i zgodność na kanonicznym logu (180+ zdarzeń). Obala: wyjątek albo niewyjaśniona rozbieżność `current()` z dzisiejszym widokiem aktywnym.
- **FC7.** H2 dev TEMP-FUTURE 14/14.
- **FC8.** Zapieczętowany zbiór held-out: 0 błędów krytycznych, exact ≥ 0.95.

---

## 6. Szkic protokołu

**Podziały:**
- **D**: REV-V0 (zamrożony, tylko odczyt) i H2 dev; widoczne dla implementatora.
- **X**: nowe przypadki X1–X10 z tego planu, w **nowym** pliku fixture; widoczne.
- **H**: held-out napisany przez niezależnego autora; sha256 zapisany przed implementacją; otwierany raz.
- **R**: kanoniczny log (totalność i zgodność).
- **H2 valid**: tylko słaby „held-out szablonowy”, bo to te same szablony z innymi podmiotami.

**Kontrola przecieków:**
- `expected` i `note` usunięte z wejścia warstwy;
- przeciek liczony po id na `basis_ids`;
- mutacje jako test samego zestawu testów;
- zakaz strojenia po otwarciu H;
- nowe ID eksperymentu (np. `PMLAB-REV-V0-002`), bez nadpisywania `07_results.json`.

**Co obala hipotezę:** krytyczny przeciek na dowolnym podziale, porażka rodziny C3 lub TEMP-FUTURE, przeżycie mutanta, H < 0.95 albo błąd krytyczny na H, naruszenie zasady append-only, brak totalności na R.

---

## 7. Decyzje dla właściciela

D1–D12 są rozpisane w JSON. Kluczowe:
- definicja `current()` (wstrzykiwane `now`, `known` = koniec logu);
- próg 18/18 zamiast 0.944;
- semantyka supersesji `unclassified`, które dominują w realnym logu;
- czy `search`, indeks i `is_active` przechodzą na widok czasowy, co zmienia `SCHEMA.md:21`;
- reguła `valid_to` przez poprawionego następcę (G4);
- czy wzmocnienie piszącego (G10) wchodzi w zakres #39;
- mapowanie H2;
- autor zbioru held-out.

```json
{
  "summary": "C3 (PMLAB-REV-V0) wynika z dwóch błędów w gałęzi as_known_at resolwera bitemporal (context/12_run_revision_v0.py:104-114). Rekord C3-a uznano za martwy tylko dlatego, że istnieje następca C3-b, choć sukcesja zamyka przedział dopiero na C3-b.valid_from=2026-09-01. Fallback `or live` zamienił brak odpowiedzi na nieobowiązujące 7%. Ta sama reguła żywotności oparta na osi transakcyjnej działa w prawdziwym magazynie: current_records/get().is_active oraz rebuild_index usuwają C3-a z wyszukiwania w okresie jego ważności. derive_temporal_view nie ma odcięcia transakcyjnego, więc prowadzi do przecieku przez pola pochodne (C2 as_known_at 2026-06-05), nie ujawnia rodzaju następcy i przy rozwidleniu wybiera ostatni rekord bez sygnału. Wcześniejsze prace: REV-V0 0.944 (reprodukcja 6/6), H2 dev resolver 1.000 / newest 0.200 (konstruowane przez autora), mechanizm B DROP (0 zadziałań, Mem0 niszczy historię przy zapisie), kotwica czasowa E1 SUPPORTED, v3 FAIL. Projekt: jedna funkcja as_of(valid, known) z wyprowadzaniem końców tylko z rekordów znanych w known, odwołaniem tylko przez korektę, przedziałem półotwartym, wynikiem trójstanowym bez fallbacku i z basis_ids. Ręczna analiza daje 18/18 na fixture (to nie pomiar). 12 kryteriów falsyfikowalnych, protokół z zapieczętowanym held-out i mutacjami, 12 decyzji dla właściciela.",
  "root_cause": "Supersesję potraktowano jako odwołanie rekordu na osi transakcyjnej, a nie jako zamknięcie przedziału na osi ważności. W resolve_bitemporal/as_known_at (context/12_run_revision_v0.py:110-114) live = rekordy bez następcy wśród znanych w T. Dla T=2026-05-01 znane są C3-a (created 01-10, valid 01-01, 5%) i C3-b (created 01-15, valid 09-01, succession, 7%) z context/10_events.jsonl:5-6, więc live=[C3-b]. Filtr in_force daje [], a fallback `or live` przywraca C3-b, co daje 7% zamiast 5% (context/09_queries.jsonl:8; context/22_response.md). Poprawna reguła (sukcesja kończy fakt na valid_from następcy) istnieje w gałęzi valid_at tego samego pliku (l.136-137) i tam daje 5% (context/07_results.json:604-611). derive_temporal_view wylicza dla C3-a poprawne valid_to=09-01, ale też expired_at=01-15 (context/03_upcast.py:212-218). Użycie expired_at jako filtra żywotności odtwarza C3. Ten sam ukryty błąd ma gałąź current (l.119-122, warunek nic nie odrzuca), niewykryty, bo fixture nie zadaje current dla C3.",
  "real_store_gap": [
    {"id": "G1", "function": "tools/project_memory/upcast.py::derive_temporal_view", "gap": "brak parametru known_at; końce przedziałów wyliczane z całego logu", "consequence": "przeciek przez pola pochodne w as_known_at (C2 @2026-06-05: prawda 'brown', widok z pełnego logu: nic nie obowiązuje); metryka leaked() go nie wykrywa", "source": "context/03_upcast.py:177-219; context/12_run_revision_v0.py:156-163"},
    {"id": "G2", "function": "upcast.derive_temporal_view", "gap": "brak superseded_by i rodzaju następcy w widoku", "consequence": "nie da się odróżnić odwołania (korekta) od zamknięcia (sukcesja); żywotność 'ma expired_at' = C3", "source": "context/03_upcast.py:212-218"},
    {"id": "G3", "function": "upcast.derive_temporal_view", "gap": "successor[target]=event: przy rozwidleniu wygrywa ostatni zapis bez sygnału", "consequence": "cichy zwycięzca, krytyczne odrzucenie z manifestu", "source": "context/03_upcast.py:206-210; context/08_manifest.json:27-33"},
    {"id": "G4", "function": "upcast.derive_temporal_view", "gap": "valid_to tylko od bezpośredniego następcy", "consequence": "A->succ B->corr C (poprawiona data) zostawia valid_to z błędnego B", "source": "context/03_upcast.py:213-218"},
    {"id": "G5", "function": "upcast.derive_temporal_view / v1_to_v2", "gap": "brak parsowania i walidacji znaczników czasu; porównania łańcuchowe", "consequence": "ryzyko cichego złego porządku (lekcja z Graphiti)", "source": "context/03_upcast.py:133; context/11_temporal-memory-model-comparison-v0.md:63-69"},
    {"id": "G6", "function": "tools/project_memory/memory_store.py::MemoryStore.current_records / get", "gap": "aktywny = niezastąpiony (żywotność czysto transakcyjna)", "consequence": "reguła C3 w produkcji: is_active(C3-a)=False, choć obowiązuje do 09-01", "source": "context/04_memory_store.py:421-438"},
    {"id": "G7", "function": "MemoryStore.rebuild_index / search / context", "gap": "indeks pomija zastąpione rekordy; metadane bez valid_from/valid_to; search bez parametru as_of", "consequence": "obowiązujący rekord znika z wyszukiwania po zapisie przyszłej sukcesji; brak filtrowania czasowego", "source": "context/04_memory_store.py:503-515,623-664; context/02_SCHEMA.md:21"},
    {"id": "G8", "function": "MemoryStore.load_events / timeline", "gap": "surowe zdarzenia, bez upcastu; memory_store nie importuje upcast", "consequence": "widok czasowy nieużywany przez żadną ścieżkę magazynu w migawce (tylko testy)", "source": "context/04_memory_store.py:404-419,440-444; context/05_test_upcast.py:22-31"},
    {"id": "G9", "function": "(brak)", "gap": "nie ma current(), valid_at(T), as_known_at(T)", "consequence": "schemat bitemporalny niezapytywalny", "source": "context/01_issue-39.md:6"},
    {"id": "G10", "function": "MemoryStore.supersede", "gap": "domyślnie supersession_kind='unclassified'; valid_from domyślnie = czas zapisu także dla korekty; brak walidacji succession.valid_from >= poprzednik.valid_from; is_active sprawdzane przez get() poza blokadą _append (TOCTOU)", "consequence": "nowe zapisy bez osi ważności; luki po korektach; ujemne przedziały; możliwe rozwidlenia rozstrzygane po cichu (G3)", "source": "context/04_memory_store.py:342-402,280-289"},
    {"id": "G11", "function": "(model danych)", "gap": "brak klucza podmiotu; łańcuch tylko przez supersedes, fixture grupuje po tags, a supersede może tagi zmienić", "consequence": "łańcuch trzeba definiować jako spójną składową supersedes", "source": "context/12_run_revision_v0.py:53-54; context/04_memory_store.py:367"},
    {"id": "G12", "function": "tests/test_upcast.py", "gap": "tylko pola pochodne; brak testów zapytań, przecieków i mutacji", "consequence": "kryterium #39 o teście padającym po usunięciu filtra niepokryte", "source": "context/05_test_upcast.py:232-284"},
    {"id": "G13", "function": "scripts/run_revision_v0.py::run / leaked", "gap": "resolwer dostaje query z expected; przeciek wykrywany po title i tylko dla rekordu-odpowiedzi", "consequence": "ślepota tylko konwencyjna; przeciek przez pola pochodne niewidoczny", "source": "context/12_run_revision_v0.py:156-163,172"}
  ],
  "prior_work": [
    {"id": "PMLAB-REV-V0-001", "result": "bitemporal exact 0.944, valid_at 1.00, as_known_at 0.86, 0 przecieków, 0 krytycznych; valid_only 0.778 (4 przecieki, 1 krytyczny); transaction_only 0.722 (valid_at 0.20); one_timestamp 0.389 (as_known_at 0.00, 6 przecieków); reprodukcja 6/6 w Dockerze", "negative_or_limits": "jedyny błąd bitemporal to C3; wszystkie ramiona 1.00 na current; korpus autorstwa implementatora, n=1, 6 z 11 rodzin, reimplementacje", "sources": ["context/06_report.md", "context/07_results.json", "context/22_response.md"]},
    {"id": "PMLAB-REV-V0 manifest", "result": "status 'preregistration-draft-...-no-run-no-result', wszystkie blokady false", "negative_or_limits": "nieaktualny wobec raportu; polityka półotwartych przedziałów i etykiety wyroczni nigdy niezrecenzowane niezależnie; ramiona T0-T5 różnią się od uruchomionych", "sources": ["context/08_manifest.json"]},
    {"id": "PMLAB-H2-TEMP-E1 dev", "result": "newest 0.200 (tylko CORRECTION 1.000), resolver 1.000, abstencja 0.200 (CONFLICT); 70 sond, 5 rodzin", "negative_or_limits": "autor znał rodziny; regexy na treści pytania i heurystyka [-2]; inny schemat (dni int, record_kind, source, przechowywane valid_to w OVERLAP); odtworzono tylko dev", "sources": ["context/14_run_temporal_resolver_h2.py", "context/15_build_temporal_corpus_h2.py", "context/16_manifest.json", "context/22_response.md"]},
    {"id": "MECHANISM_B CURRENT_STATE_OVER_HISTORY Stage 1", "result": "DROP: BASE 12/12, +B 12/12, 0 napraw netto; rdzeń zadziałał 0 razy w 24 wykonaniach; retest naprawczy nieudany; koszt 0.022315+0.041754 USD", "negative_or_limits": "Mem0 1.0.6 konsoliduje stany przy zapisie i nadpisuje metadata.timestamp; RET1_JOB zachował środkowy fakt; brak pytań historycznych w prerejestracji; brak dowodu, nie dowód przeciwny", "sources": ["context/17_MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md", "context/18_MECHANISM_B_STAGE1_RESULTS_V1.md", "context/19_preregistration.json"]},
    {"id": "TEMPORAL_ANCHOR_AT_CONTEXT E1", "result": "SUPPORTED: +2 netto (native), +3 (wide), 0 regresji; koszt 0.073440 USD", "negative_or_limits": "placebo +1 przy wide; +SRC -1 przy obu punktach; 10 jednostek", "sources": ["context/21_READ_SIDE_TEMPORAL_ANCHOR_V1.md"]},
    {"id": "TEMPORAL_ANCHOR_BOUNDARY v3 (Mechanism I)", "result": "MECHANISM_I_FAIL: 0 napraw netto na 8 jednostkach, 0 regresji; trzecia z rzędu porażka, więc zmiana strategii; koszt 0.559315 USD", "negative_or_limits": "błędy z braku pobranych dokumentów; powtórzona pułapka SESSION_EVENT_DIVERGENT (czas sesji ≠ czas zdarzenia); Stage 2 -1 netto", "sources": ["context/20_TEMPORAL_ANCHOR_BOUNDARY_V3.md"]},
    {"id": "temporal-memory-model-comparison-v0", "result": "przyjęto 4 pola na 2 osiach (Graphiti/SQL:2011); jeden mechanizm zamiast correct/succeed", "negative_or_limits": "nie kopiować cichego porzucania dat; brak modelu wygasania przyjęty jako ograniczenie", "sources": ["context/11_temporal-memory-model-comparison-v0.md"]},
    {"id": "PMLAB-STALE-E1 (pośrednio)", "result": "pary zastąpień na 99,5 percentylu podobieństwa, 2 pary cosinus 1.000, stary fakt najbliższym sąsiadem 6/9 bez filtra", "negative_or_limits": "raport nie jest w context/", "sources": ["context/17_MECHANISM_B_STATE_SUPERSESSION_DESIGN_V1.md:24", "context/03_upcast.py:109-113"]},
    {"id": "PMLAB-H1-COMPOSE-E1 (pośrednio)", "result": "resolwer nic nie zmienia na H1, wyniki identyczne do 3 miejsc po przecinku (negatywny)", "negative_or_limits": "raport nie jest w context/", "sources": ["context/15_build_temporal_corpus_h2.py:5-9"]}
  ],
  "design": {
    "core": "as_of(valid_time, known_time, chain) jako czysta funkcja nad zdarzeniami po upcaście do v2",
    "steps": [
      "known(tx) = zdarzenia z created_at <= tx; remis rozstrzyga pozycja w logu; tx=None oznacza koniec logu",
      "wyprowadzenie końców wyłącznie z known(tx): derive_temporal_view(known(tx)) z ujawnionym superseded_by i rodzajem następcy (poprawki G1, G2)",
      "B(tx) = known(tx) minus rekordy odwołane korektą znaną w tx; sukcesja nie usuwa rekordu, tylko nadaje valid_to = successor.valid_from (reguła anty-C3); unclassified według D3",
      "przedział półotwarty [valid_from, valid_to), None = nieskończoność",
      "wynik trójstanowy: one | none | ambiguous | unknown, bez fallbacku, z basis_ids (rekord-odpowiedź i rekordy, z których wyprowadzono przedział)",
      "łańcuch = spójna składowa relacji supersedes (nie tags); fork, czyli więcej niż 1 następca, daje ambiguous"
    ],
    "queries": {
      "current(now)": "as_of(valid=now, known=koniec logu); now wstrzykiwane (D1)",
      "valid_at(T)": "as_of(valid=T, known=koniec logu)",
      "as_known_at(T)": "as_of(valid=T, known=T)"
    },
    "placement": "nowy moduł tools/project_memory/temporal.py (czyste funkcje) i cienkie metody MemoryStore.current/valid_at/as_known_at oparte na load_events; bez _append i rebuild_index",
    "benchmark_path": "nowy runner podstawia fixture jako memory/events.jsonl w katalogu tymczasowym i odpytuje MemoryStore; do warstwy trafiają tylko chain, type, at (bez expected)",
    "analytic_check_on_fixture": "ręczny ślad 18/18 (C1 black/black/brown, C2 green/brown/brown, C3 5/5, C4 68/60/70, C5 open/closed, C6 bob/alice, C7 Warsaw/None/None); to analiza, nie pomiar",
    "extension_cases_X": [
      "X1 C3 current(now=2026-05-01) -> 5%",
      "X2 C3 current(now=2026-10-01) -> 7%",
      "X3 C2 as_known_at(2026-06-05) -> brown (przeciek przez pola pochodne); valid_at(2026-06-05) -> green",
      "X4 C6 valid_at(2026-05-01T12:00:01Z) -> bob (koniec półotwarty)",
      "X5 C3 z korektą C3-c daty sukcesji na 2026-10-01: valid_at(2026-09-15) -> 5% (reguła D5)",
      "X6 fork: dwie sukcesje jednego rekordu -> ambiguous",
      "X7 łańcuch v1 unclassified: current -> następca; valid_at w luce -> unknown (D3)",
      "X8 korekta z późniejszym valid_from: valid_at przed nim -> none (nie poprzednik)",
      "X9 sukcesja z valid_from < valid_from poprzednika -> flaga lub ambiguous",
      "X10 C5 current(now=2026-11-13), known = koniec logu -> closed (dokumentuje D1)"
    ],
    "non_goals": ["brak zapisu do logu", "brak modelu wygasania (decay)", "brak wnioskowania sprzeczności przez LLM"]
  },
  "falsifiable_criteria": [
    {"id": "FC1", "criterion": "REV-V0 (18 zapytań) przez ścieżkę MemoryStore", "threshold": "18/18 exact (#39 wymaga min. 0.944)", "refuted_if": "dowolne zapytanie C3 błędne LUB exact < 0.944; przy przyjęciu D2 każde < 1.000"},
    {"id": "FC2", "criterion": "przecieki przyszłości liczone po id na basis_ids (łącznie z polami pochodnymi), D+X+H", "threshold": "0", "refuted_if": ">= 1 przeciek, w tym X3"},
    {"id": "FC3", "criterion": "testy mutacyjne: M1 bez filtra created_at<=T; M2 końce z pełnego logu; M3 żywotność przez istnienie następcy; M4 fallback 'or live'; M5 korekta jako sukcesja; M6 sukcesja jako korekta; M7 koniec przedziału domknięty", "threshold": "100% zabitych (M1 pada m.in. na C5, M2 na X3, M3/M4 na C3, M5 na C1 valid_at, M6 na C2 valid_at, M7 na X4)", "refuted_if": "którykolwiek mutant przechodzi zestaw"},
    {"id": "FC4", "criterion": "korekta i sukcesja różnią się: pary przypadków różniące się tylko supersession_kind, valid_at w luce [poprzednik.valid_from, następca.valid_from)", "threshold": "różne odpowiedzi w 100% par", "refuted_if": "identyczna odpowiedź w którejkolwiek parze"},
    {"id": "FC5", "criterion": "append-only", "threshold": "sha256 events.jsonl identyczny przed i po pełnym zestawie; 0 zapisów w memory/", "refuted_if": "zmiana skrótu lub jakikolwiek zapis"},
    {"id": "FC6", "criterion": "totalność i zgodność na kanonicznym logu (180+ zdarzeń)", "threshold": "0 wyjątków i 0 pominiętych; current() równe dzisiejszemu widokowi aktywnemu poza łańcuchami z przyszłą sukcesją lub unclassified wg D3, wymienionymi z nazwy", "refuted_if": "wyjątek, ciche pominięcie lub niewyjaśniona rozbieżność"},
    {"id": "FC7", "criterion": "H2 dev przez adapter (D9)", "threshold": "TEMP-FUTURE 14/14; pozostałe rodziny raportowane", "refuted_if": "TEMP-FUTURE < 14/14"},
    {"id": "FC8", "criterion": "zapieczętowany held-out H, otwierany raz", "threshold": "0 błędów krytycznych; exact >= 0.95; każdy błąd sklasyfikowany przez recenzenta", "refuted_if": "błąd krytyczny > 0 lub exact < 0.95"},
    {"id": "FC9", "criterion": "brak cichego zwycięzcy (X6 i forki w H)", "threshold": "100% przypadków -> ambiguous z oboma id", "refuted_if": "pojedyncza odpowiedź w którymkolwiek"},
    {"id": "FC10", "criterion": "determinizm: brak zależności od zegara w benchmarku", "threshold": "identyczny wynik w 2 przebiegach przy wstrzykniętym now i różnym zegarze systemowym", "refuted_if": "różnica wyników"},
    {"id": "FC11", "criterion": "głośna porażka przy złym znaczniku czasu", "threshold": "100% wstrzykniętych złych dat -> wyjątek", "refuted_if": "ciche pominięcie lub porównanie"},
    {"id": "FC12", "criterion": "uczciwość co do wartości current (zastrzeżenie z 06_report)", "threshold": "raport liczby łańcuchów na R, gdzie current() różni się od widoku aktywnego", "refuted_if": "current() zmienia odpowiedzi poza łańcuchami z przyszłą sukcesją lub decyzją D3 (regresja)"}
  ],
  "protocol_draft": {
    "splits": {
      "D_dev": "REV-V0 fixture (14 zdarzeń, 18 zapytań, zamrożony, tylko odczyt) oraz H2 dev (70 sond); widoczne",
      "X_extension": "X1-X10 w nowym pliku fixture (REV-V0 nienaruszony); widoczne",
      "H_heldout": "przypadki adwersaryjne od niezależnego autora; sha256 zapisany przed implementacją; etykiety z definicji przypadku, drugi recenzent etykietuje niezależnie, rozbieżności rozstrzyga właściciel przed otwarciem; otwierany raz",
      "R_real": "kanoniczny memory/events.jsonl: totalność, zgodność, FC5/FC6",
      "H2_valid": "tylko słaby held-out szablonowy (te same szablony, inne podmioty)"
    },
    "order": ["decyzje właściciela D1-D12 zamrożone", "zapieczętowanie H", "implementacja", "D+X", "mutacje (FC3)", "R (FC5, FC6, FC12)", "jednorazowe otwarcie H", "raport z wynikami negatywnymi"],
    "leak_controls": ["do warstwy trafiają tylko chain, type, at, now; expected i note usunięte przez runner", "przeciek po id na basis_ids zamiast po title", "testy mutacyjne jako test samego zestawu", "implementator bez dostępu do H", "zakaz strojenia po otwarciu H; poprawki dopiero w nowej wersji z nowym H", "nowe ID eksperymentu (np. PMLAB-REV-V0-002) i nowy plik wyników; 07_results.json nietknięty"],
    "thresholds": "jak w falsifiable_criteria",
    "what_refutes": ["dowolny krytyczny przeciek na dowolnym podziale", "porażka C3 lub TEMP-FUTURE (w tym X1)", "przeżycie dowolnego mutanta", "H exact < 0.95 lub błąd krytyczny na H", "zmiana skrótu logu", "brak totalności na R"],
    "cost": "0 USD; deterministyczne, bez modeli, bez GPU"
  },
  "risks": [
    "korpusy REV-V0 i H2 napisał autor znający rodziny: ryzyko dopasowania pod test; ograniczane przez H i mutacje",
    "zależność od zegara: C5-b ma created_at 2026-12-01, a dziś jest 2026-11-13; current z known=now obala C5 (D1)",
    "realny log to głównie v1 unclassified (valid_from=created_at): valid_at na R może dawać głównie unknown, a warstwa wyglądać na bezużyteczną (D3)",
    "piszący dalej produkuje unclassified i valid_from=teraz; bez G10 nowe dane nie zasilą osi ważności (powtórka SESSION_EVENT_DIVERGENT z 20_)",
    "wyścig TOCTOU w supersede może tworzyć rozwidlenia; obecnie rozstrzygane po cichu (G3)",
    "zmiana search lub is_active na widok czasowy zmienia udokumentowane zachowanie SCHEMA.md:21 (D4)",
    "H2 nie mapuje się 1:1 na schemat v2 (przechowywane valid_to w OVERLAP, source vs source_refs); złota odpowiedź dla 'before the correction' w CORRECTION odpowiada semantyce valid_at, nie as_known_at: ryzyko strojenia adaptera pod wynik (D9)",
    "próg #39 (>= 0.944) dopuszcza jeden błąd poza C3 (D2)",
    "manifest REV-V0 nieaktualny, blokady false: polityka przedziałów i wyrocznia niezrecenzowane (D6, D11)",
    "zmiana reguły valid_to (G4) zmienia oczekiwania testu na realnym logu (05_test_upcast.py:261-284)",
    "porównania łańcuchowe i nieznane formaty created_at w v1 (G5)",
    "lekcja z mechanizmu B: warstwa nie może niczego konsolidować ani nadpisywać, bo inaczej odczyt straci materiał"
  ],
  "owner_decisions": [
    {"id": "D1", "decision": "definicja current(): valid=now (wstrzykiwane), known=koniec logu; czy now wymagane w benchmarku", "recommendation": "tak; known=koniec logu (inaczej C5 pada)"},
    {"id": "D2", "decision": "próg ponownego REV-V0: 18/18 czy >= 0.944 z #39", "recommendation": "18/18"},
    {"id": "D3", "decision": "semantyka supersesji unclassified (v1): (a) usuń poprzednika z przekonań, valid_at w luce -> unknown; (b) traktuj jako korektę; (c) jako sukcesję (fabrykacja, sprzeczne z SCHEMA)", "recommendation": "(a)"},
    {"id": "D4", "decision": "czy search, indeks i get().is_active przechodzą na widok czasowy (naprawa C3 w wyszukiwaniu, zmiana SCHEMA.md:21), czy zostają osobno", "recommendation": "osobny krok po #39 z własnym testem; zgłosić jako znaną lukę"},
    {"id": "D5", "decision": "valid_to przez poprawionego następcę (A->succ B->corr C) i zmiana derive_temporal_view oraz testu na realnym logu", "recommendation": "tak, valid_to z pierwszego nieodwołanego następcy; zmiana schematu zatwierdzona przez właściciela"},
    {"id": "D6", "decision": "konwencja przedziałów: [valid_from, valid_to), created_at <= T, remis według pozycji w logu; recenzja niezależna (blokada w manifeście)", "recommendation": "przyjąć i zlecić recenzję"},
    {"id": "D7", "decision": "czy wzmocnienie piszącego (G10: wymagany supersession_kind, korekta dziedziczy valid_from, walidacja kolejności, is_active pod blokadą) wchodzi w zakres #39", "recommendation": "osobne zadanie, ale przed wnioskami o wartości osi na R"},
    {"id": "D8", "decision": "kontrakt wyniku trójstanowego (one/none/ambiguous/unknown) zamiast pojedynczego title|None", "recommendation": "tak; abstencja poprawna tylko tam, gdzie złota odpowiedź jej oczekuje"},
    {"id": "D9", "decision": "mapowanie H2 na v2 (record_kind->supersession_kind, OVERLAP z przechowywanym valid_to, CONFLICT source) i czy H2 jest bramką", "recommendation": "bramką tylko TEMP-FUTURE; reszta raportowana; mapowanie zamrożone przed uruchomieniem"},
    {"id": "D10", "decision": "kto pisze zapieczętowany held-out H (niezależny agent lub właściciel)", "recommendation": "autor inny niż implementator; koszt 0 USD"},
    {"id": "D11", "decision": "nowe ID eksperymentu dla ponownego uruchomienia i aktualizacja nieaktualnego manifestu bez nadpisywania wyników historycznych", "recommendation": "PMLAB-REV-V0-002; nowy plik wyników"},
    {"id": "D12", "decision": "przypadki X1-X10 jako nowy fixture (REV-V0 zamrożony)", "recommendation": "tak"}
  ],
  "acceptance_met": [
    {"criterion": "Mechanizm C3 wyjaśniony na konkretnych rekordach z fixture", "met": true, "evidence": "sekcja 1: ślad C3-a/C3-b (10_events.jsonl:5-6), zapytanie 09_queries.jsonl:8, linie 12_run_revision_v0.py:104-114 i 136-137, wynik 07_results.json:604-621 oraz 22_response.md"},
    {"criterion": "Luka prawdziwego magazynu wskazana na poziomie funkcji", "met": true, "evidence": "G1-G13: derive_temporal_view, current_records/get, rebuild_index/search/context, load_events/timeline, supersede, test_upcast, runner"},
    {"criterion": "Wcześniejsze wyniki (także negatywne) wymienione ze źródłami", "met": true, "evidence": "prior_work: REV-V0, manifest, H2, mechanizm B DROP, kotwica E1 i v3 FAIL, porównanie modeli, STALE-E1 i H1-COMPOSE (oba pośrednio)"},
    {"criterion": "Każde kryterium skuteczności ma próg i warunek obalenia", "met": true, "evidence": "FC1-FC12 z polami threshold i refuted_if"},
    {"criterion": "Jawna lista decyzji dla właściciela", "met": true, "evidence": "D1-D12 z rekomendacjami"}
  ]
}
```

---

*Integration note (2026-11-14).* Imported unchanged in substance from the AAMR coordinator (task 8, source file `response.md`, SHA-256 of the original `feb79ba942fea0a73bc3726747e8278f1e5dbb7870076c41827972f7fbfe1770`). The text is the AI-written original, in Polish. The only edits are listed in `PROVENANCE.json`. Status: **SUPERSEDED**. Nothing in it is an approved decision. See `README.md` in this directory.
