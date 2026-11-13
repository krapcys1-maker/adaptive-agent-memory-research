# AAMR-NIGHT-2: protokół wykonawczy (zamrożony przed pierwszym wywołaniem eksperymentalnym)

Data: 2026-11-13. Wykonawca: Claude (Opus 5.5), na podstawie przekazania Fable 5.2.

## 0. Status

Normatywna jest specyfikacja `SPEC_AAMR_NIGHT2.md` v0.1, skopiowana tu bez zmian
(sha256 `b44e6c17142b62f28790860357c206c46bbb932a28ac25e1d18b39d1570309a1`, identyczna z
`GH_REVIVAL/night1-review-2026-11-13/SPEC_AAMR_NIGHT2.md`). Hipotezy H14–H16, ramiona, zbiory zadań, progi i reguły
decyzji są tamte. Ten plik zapisuje wyłącznie decyzje implementacyjne i rozstrzygnięcia niejasności według reguły z §10
specyfikacji: wariant prostszy i bliższy NIGHT-1. Wszystkie zapadły przed pierwszym wywołaniem eksperymentalnym.

Kod: `scripts/aamr_night2.py`, `scripts/aamr_night2_analysis.py`, `scripts/reasoningbank_prompts.py`.
Testy: `tests/test_aamr_night2.py`. Konfiguracja i budżety: `config.json`.
Kod pilota, S1 i NIGHT-1 jest importowany, nie zmieniany. Ścieżki modułu NIGHT-1 są przekierowane na foldery NIGHT-2
zaraz po imporcie.

Surowe dane poza Git: `GH_REVIVAL/aamr-night2-2026-11-13/run/`. Test techniczny: `.../smoke-run/`, wliczony w budżet T.

## 1. Wejścia tylko do odczytu (sha256)

| Plik | sha256 |
|---|---|
| `data/lab/experience-pilot-v0/pools/A_plus.jsonl` | `037c76f2…3113` |
| `data/lab/experience-pilot-v0/pools/A.jsonl` | `c086dffa…95dd` |
| `data/lab/experience-pilot-v0/exposure.json` | `cd9757f3…cd9f` |
| `data/lab/experience-xfer-v1/lessons.jsonl` | `af563e62…f960` |
| `data/lab/experience-xfer-v1/g-guidance.json` | `a619193f…b7f` |
| NIGHT-1 `run/artifacts/memory_GFS.json` | `271516fa…0925` (zgodne z `raw-freeze.json` NIGHT-1) |
| NIGHT-1 `run/artifacts/memory_TRAVEL.json` | `75c4eb49…ed3` (zgodne) |
| NIGHT-1 `run/artifacts/lessons_VC_Q.json`, `lessons_VC_F.json` | `cf3a8ce4…99`, `07c71147…1fd` (zgodne) |
| NIGHT-1 `run/sessions/census.jsonl` | `68e2cb90…418` (zgodne) |
| `scripts/reasoningbank_prompts.py` (kopia `instruction.py` ReasoningBank, Apache-2.0, oryginał `31b3ec98…cb82`) | `5f38cbcd…9d89` |

Przebiegi treningowe bez pamięci: VC z pilota (`e1a`, `e1b`), GFS i TRAVEL z sesji `census` NIGHT-1. Wszystkie 114 śladów
sukcesu w pulach zgadzają się z epizodem źródłowym (prośba i wywołania), co sprawdza test.

## 2. Test zgodności z NIGHT-1 (§10)

Suchy przebieg na zapisanych odpowiedziach NIGHT-1: 146 epizodów (sA: N; sD: N, R+), 1 372 prośby do modelu.

- 1 367 próśb jest identycznych bajt w bajt.
- 5 próśb (zadanie 17, tura 2, ramiona N i R+) różni się tylko nazwą instancji, którą executor BFCL wkleja do komunikatu
  błędu. Stało się tak, bo agent przekazał tekst kodu jako argument. Nazwa jest z założenia unikalna dla każdego procesu,
  więc między NIGHT-1 a każdym kolejnym przebiegiem też się różni. Po ujednoliceniu tej nazwy prośby są identyczne.
- Przyczyna jest wskazana i nie dotyczy kodu NIGHT-2, więc test uznaję za zaliczony z tym udokumentowanym wyjątkiem.
- Polecenie: `python scripts/aamr_night2.py compat`.

## 3. Decyzje implementacyjne i rozstrzygnięcia niejasności

**D1. Maskowanie.**
- Reguła 2 ze specyfikacji jest wykonana dosłownie:
  - wykrywanie w prośbach i wynikach jak w implementacji wzorcowej `n1_04`: napisy jako podciąg bez rozróżniania wielkości
    liter, od 2 znaków; liczby jako cały token;
  - kontekst bierze się z całego epizodu źródłowego.
- Rozszerzenie wymuszone przez test jednostkowy ze specyfikacji („żadna zamaskowana wartość nie występuje w gotowym
  bloku”). Wartość zamaskowana gdziekolwiek w bloku dostaje swój pierwszy znacznik wszędzie, gdzie widać ją jako token:
  - w argumentach wcześniejszych wywołań;
  - w komunikatach błędów;
  - wewnątrz zachowanych napisów (np. `display_log(messages=[…])`).
- Bez tego rozszerzenia zostawały widoczne m.in. `JFK` we wcześniejszym wywołaniu tego samego śladu i nazwy drzwi
  w komunikacie błędu.
- Za wartości nie uważam: nazw parametrów, samych znaczników ani list kluczy w `ok {…}`.
- Zamiana w pokazanej prośbie obejmuje tylko całe słowa, żeby nie psuć tekstu. Wartość wykrytą tylko jako fragment
  dłuższego słowa maskuję w wywołaniu, ale w prośbie niczego nie zamieniam.
- Maskowane jest 77% wartości argumentów pul: 51% z prośby, 21% z wcześniejszego wyniku, 5% dat. M2 jest średnio
  o 1,6% dłuższe od R+.

**D2. Wyniki z błędem.** Maskuję jak `error_key`: napisy z argumentów wywołania na `<arg>`, wartości w cudzysłowie na
`<v>`, liczby na `<n>`. Wielkość liter zostaje, komunikat jest w całości, z przedrostkiem `error: `.

**D3. Limit bloku.**
- M1 i M2: najwyżej 2 800 znaków razem ze zdaniem w nagłówku (ucięcie na końcu bloku).
- R+: dokładnie jak w NIGHT-1 (`render_block`, ślady po najwyżej 1 400 znaków), bo musi być bajt w bajt zgodne.
- C-RB: najwyżej 2 800. C-G: całe wiersze, dopóki suma nie przekroczy 2 800.

**D4. Pule E1.** Wyszukiwanie jądrem 0.2.0 bez bramki, k = 2, po tekście prośby tury, jak `d0_build` w NIGHT-1. Pula dla
zadania `t` to ślady sukcesu pozostałych 19 zadań treningowych tej samej domeny.

**D5. Cięcie ramion.**
- Projekcja: liczba wywołań na epizod ramienia N w NIGHT-1 na tych samych zadaniach (sA, sD, census, pilot) × 1,05. Dla
  9B: 12,8 ze specyfikacji.
- Priorytet w E1, którego specyfikacja nie podaje: N, R+, M2, M1, N′.
- E3: kolejność ze specyfikacji. E4: N, K, C-RB, C-G. E5: N, K, N′.
- Ramię już rozpoczęte nie jest cięte.

**D6. H14.** Reguły sprawdzam w kolejności z tekstu: wsparta, obalona, nietestowalna, nierozstrzygnięta.

**D7. Stany E2.**
- Sygnatury z puli błędów zadań treningowych: VC z puli A pilota, GFS i TRAVEL z census.
- Dla każdej sygnatury pierwsze wystąpienie w kolejnych zadaniach treningowych, w kolejności podziału; najwyżej 8 stanów.
- Klucz rozwidlenia to stan i sha256 treści notatki, więc ta sama para (stan, treść) nie jest wywoływana dwa razy.
- Liczba stanów: VC 27 (5 sygnatur), GFS 26 (10), TRAVEL 17 (5). Rozwidleń bez X: 322.

**D8. Notatka X.**
- Ciąg: nazwy poprawnych wywołań po notatce aż do pierwszego udanego wywołania danej funkcji.
- Wybieram grupę o tym samym ciągu z największą liczbą różnych zadań, co najmniej 2; przy remisie wcześniejszą.
- Przykłady: pierwsze dwa zadania tej grupy, wynik ucięty do 120 znaków.
- Pusty ciąg daje: `… resolved in earlier tasks by calling {function} again.`
- Komunikat: pierwszy komunikat sygnatury, 110 znaków jak w NIGHT-1.
- Limit 600 znaków.

**D9. Kontrola narzędzia.** Remis rozstrzyga kolejność z tekstu: O, S, P, Q, F. „F wobec najlepszego lokalnego” liczę jako
turniej na zbiorze {wybrany kandydat lokalny, F}, przy remisie wygrywa lokalny.

**D10. Zestaw zastępczy.** Lekcje D tam, gdzie istnieją, w pozostałych sygnaturach notatki Q. Obejmuje wszystkie lekcje D
i Q domeny.

**D11. E3.**
- Ślady dla zadań testowych: VC z `exposure.json` pilota (R+), GFS i TRAVEL z `rplus_plan` NIGHT-1.
- Notatki Q jak w NIGHT-1 (wiersze z `check.ok`).
- Kolejność notatek w mapie: kolejność sygnatur w zestawie.

**D12. Rodzina drugorzędna.** Werdykty H15, H16 i powtórki H14 według progów z tabeli specyfikacji. Wartości p z McNemara
z korektą Holma (jednostronnie, α = 0,05) raportuję obok; nie są warunkiem werdyktu, tak jak rodzina Holma w NIGHT-1.

**D13. Straty.** Zawsze: zadania rozwiązane przez N, a nierozwiązane przez ramię. Liczone w tej samej sesji, na zadaniach
kompletnych we wszystkich ramionach sesji.

**D14. C-RB.**
- Instrukcja systemowa ReasoningBank bez zmian, w wariancie z `minisweagent/memory/instruction.py`, jedynym pod ścieżką
  ze specyfikacji. Treść użytkownika w ich układzie `format_examples` (zapytanie, trajektoria, sygnał poprawności,
  „Updated Memory”).
- Dostosowany jest wyłącznie format trajektorii: prośby tur, potem `<action>wywołanie</action>` i
  `<result>wynik ≤160 znaków</result>`, całość ≤16 000 znaków.
- Wyjście w Markdown, bez formatu JSON; parsuję najwyżej 3 pozycje.
- Odstępstwa od oryginału:
  - temperatura 0 (u nich 1,0);
  - etykieta z checkera zamiast sędziego LLM;
  - wyszukiwanie naszym jądrem leksykalnym zamiast osadzeń;
  - lokalny 14B jako pisarz.
- k = 1 jak u nich (`select_memory(n=1)`): jedna pozycja to pamięć jednego epizodu treningowego, czyli jego najwyżej
  3 elementy. Indeksem jest tekst wszystkich próśb epizodu, zapytaniem prośba bieżącej tury. Epizodów bez sparsowanego
  elementu nie indeksuję.

**D15. C-G.**
- VC: gotowe `g-guidance.json`, jak w specyfikacji.
- GFS i TRAVEL: jedno wywołanie `guidance_request` na narzędzie użyte w co najmniej 2 zadaniach treningowych domeny
  (16 i 22 narzędzia). Pula to wszystkie wiersze treningowe domeny.
- Blok: nagłówek lekcji, potem po jednym wierszu na dostępne narzędzie, w kolejności częstości w treningu.
- Odstępstwo od ExpG: tam wskazówki są przy każdym narzędziu, u nas limit 2 800 wymusza wybór.

**D16. Lepszy konkurent C.** Więcej rozwiązanych, przy remisie mniej strat, potem C-RB.

**D17. Reguła rekomendacji.** Specyfikacja nie obejmuje wszystkich kombinacji. Gdy warunki „GOTOWE” nie są spełnione,
a test główny nie jest „obalone”, wynik to „POPRAWIĆ NAJSŁABSZY SKŁADNIK”.

**D18. Kontrola dryfu.** N z E3 porównuję z N z NIGHT-1: sA dla VC, sD dla GFS i TRAVEL.

**D19. Strażnicy.**
- Strażnik TradingBot z S1 działa przy każdym wywołaniu executora i checkera. Loader BFCL wczytuje cały plik danych do
  pamięci, jak w NIGHT-1, ale żadne zadanie TradingBot nie trafia do promptu, executora ani checkera.
- `base_url` musi wskazywać lokalną Ollamę, `paid_calls` = 0.
- Naruszenie strażnika zatrzymuje program i zapisuje powód w `STOPPED.json`.

**D20. Kolejność etapów i zależności.**
- Kolejność: preflight_q14, E1, E2, build_c (budowa C-RB i C-G, budżet E4), E3, E4, preflight_q9, E5, final.
- E3 zależy od E1 i E2. E4 od E3 i build_c. E5 od E3 i preflight_q9.
- Preflighty liczą się do budżetu T.

## 4. Budżet (jawny rejestr)

Każda próba trafia do `attempts.jsonl` (fsync), zanim zostanie wysłana. Limity sprawdzane są przed każdą próbą: limit
etapu, a potem limit łączny.

| Pozycja | Budżet |
|---|---|
| T (test techniczny i preflighty) | 150 |
| E1 | 3 100 |
| E2 | 2 200 |
| E3 | 7 400 |
| E4 (budowa C-RB i C-G oraz sesja) | 4 000 |
| E5 | 3 800 |
| **razem / limit twardy** | **20 650 / 21 500** |
| wywołania płatne | 0 |

## 5. Zakończenie

Etap `final`:
- zamraża surowe pliki (`raw-freeze.json`, sha256);
- liczy `results.json` i generuje `REPORT.md` według reguł;
- robi lokalny commit.

Interpretacja trafia do `WNIOSKI.md`, a analizy po fakcie do osobnego pliku eksploracyjnego. Na koniec usuwam zadanie
harmonogramu `AAMR-NIGHT2`. Egzaminu na TradingBot program nie uruchamia.

## 6. Poprawki techniczne po zamrożeniu

1. Przed pierwszym wywołaniem modelu, także testowym. Moduł `aamr_night2` przekierowywał ścieżki modułu NIGHT-1 już przy
   imporcie. Kiedy testy NIGHT-1 i NIGHT-2 biegły w jednym procesie, testy NIGHT-1 dostawały konfigurację NIGHT-2 (4 testy
   nie przechodziły). Przekierowanie robi teraz jawna funkcja `activate()`, wywoływana przez każdy punkt wejścia programu;
   kontekst bez niej się nie utworzy. Działanie programu się nie zmienia. 90 testów (pilot, S1, NIGHT-1, NIGHT-2) przechodzi
   razem.
2. Po teście technicznym, przed pierwszym wywołaniem eksperymentalnym. W teście 14B opisał trzecią pozycję ReasoningBank
   drugim nagłówkiem `## Description` zamiast `## Content`. Parser bierze teraz w takim przypadku drugi `Description` jako
   treść. To wyłącznie korzyść dla ramienia konkurenta C-RB.
3. Po teście technicznym. Nadzorca uruchomiony przez `python.exe` z widocznym oknem konsoli zginął z kodem 0xC000013A
   (zamknięcie konsoli albo Ctrl+C), zaraz po preflighcie 9B. Danych nic nie straciło: nowy nadzorca przejął
   nieaktualną blokadę i dokończył test. Zadanie harmonogramu uruchamia teraz `pythonw.exe` (bez okna) i co 20 minut
   wznawia nadzorcę, jeśli zginie. Wynik testu technicznego: wszystkie 6 etapów `done`. Prób było 32: preflight 14B 3,
   dwa epizody 20, jedno rozwidlenie G0 3 (błąd rozwiązany, tura zaliczona), jedno wywołanie ReasoningBank (3 pozycje),
   preflight 9B 3, jeden epizod 9B 2. Test przerwania w trakcie epizodu nie zdążył zadziałać (epizod 9B był za krótki),
   więc zrobię go na początku E1 i opiszę w raporcie.

