# AAMR-NIGHT-2: specyfikacja (v0.1)

Data: 2026-11-13. Autor: Claude (Fable 5.2). Wykonawca: Claude (Opus).
Podstawa: `OCENA_NIGHT1.md` w tym samym folderze, `strategy-2026-11-12/STRATEGIA_AAMR.md` z aktualizacjami 1 i 2,
surowe dane NIGHT-1.

## 0. Cel i pytanie

**Pytanie główne:** czy system złożony z pamięci sukcesów (bez kopiowania cudzych wartości) i notatek naprawczych
podawanych po błędzie rozwiązuje co najmniej o 10 pp więcej zadań niż agent bez pamięci, przy najwyżej 4
zadaniach straconych, i jak wypada wobec dwóch ramion w stylu konkurentów w tym samym harnessie.

Trzy hipotezy, nie więcej:

| Hipoteza | Treść | Gdzie testowana |
|---|---|---|
| H14 | Zamiana wartości specyficznych dla zadania na znaczniki w przykładach sukcesu usuwa straty przez kopiowanie i zachowuje zyski | etap E1 (zadania treningowe), powtórnie E3 |
| H15 | Przykłady sukcesu i notatki po błędzie sumują się: razem dają więcej niż każde osobno | etap E3 |
| H16 | Wybór notatki przez turniej na stanach treningowych, z regułą braku regresji, daje lepszy zestaw niż pojedynczy niezweryfikowany pisarz | etap E2 (kontrole o znanej odpowiedzi), etap E3 |

**Status dowodów:** wszystko w tym programie jest **rozwojowe**. Zadania VC, systemu plików i podróży były już
używane. Program nie potwierdza systemu; wybiera konfigurację i decyduje, czy warto zużyć egzamin na TradingBot.

## 1. Granice (nie do zmiany przez wykonawcę)

- 0 wywołań płatnych. Żadnego DeepSeek, żadnego płatnego API. Notatki Flash z NIGHT-1 wolno czytać z dysku tylko
  jako porównanie w etapie E2 (bez ramienia agenta).
- TradingBot (id 100–149, wszystkie cztery odmiany BFCL) nietknięty: nie czytać treści, nie uruchamiać. Strażnik
  w kodzie zostaje.
- Bez push i merge. Commity tylko lokalne, na nowej gałęzi.
- Nie zmieniać plików ani wyników pilota, S1 i NIGHT-1, ani zamrożonego kodu (`experience_pilot_v0.py`,
  `experience_xfer_v1.py`, `aamr_night1.py`). Nowy kod importuje stary.
- Twardy limit: 21 500 lokalnych prób (każda liczona). Budżety etapów w sekcji 8.
- Dane wysyłane tylko do lokalnej Ollamy.

## 2. Wspólne warunki

- BFCL multi-turn base, checkout `6ea5797`, oficjalny checker, pętla agenta `run_episode_x` bez zmian, temperatura
  0, seed 7, `num_ctx` 8192, `num_predict` 512, najwyżej 8 kroków na turę.
- Agent: `qwen2.5:14b-instruct` (digest `7cdf5a01…`). Etap E5: `qwen3.5:9b-q4_K_M` z ustawieniami z NIGHT-1.
- Podziały bez zmian:
  - VC: podział pilota, 20 treningowych i 30 testowych.
  - System plików (GFS) i podróże (TRAVEL): podział NIGHT-1 (`split()`), 20 + 30 i 20 + 28.
  - **Zadania treningowe:** 60. **Zadania rozwojowe-testowe:** 88 (30 + 30 + 28).
- Każde porównanie w jednej sesji; kolejność ramion losowana osobno dla zadania; analiza na zadaniach kompletnych
  we wszystkich ramionach porównania; dokładny test McNemara.
- Pamięć zamrożona na czas sesji testowej. Zadania rozwojowe-testowe nie trafiają do budowy pamięci, do pisarzy
  ani do etapów E1 i E2.
- Limit pamięci w turze: blok najwyżej 2 800 znaków; notatka najwyżej 600 znaków; notatka dla danej sygnatury raz
  na epizod (jak w NIGHT-1).

Źródła pamięci (wszystko już istnieje, budowa bez nowych wywołań, o ile nie zaznaczono inaczej):

| Składnik | VC | GFS, TRAVEL |
|---|---|---|
| pula sukcesów | `experience-pilot-v0/pools/A_plus.jsonl` | `run/artifacts/memory_{GFS,TRAVEL}.json` → `a_plus` |
| lekcje deterministyczne D | `experience-xfer-v1/lessons.jsonl` | `memory_*.json` → `deterministic_lessons` |
| notatki Q (Qwen) | `run/artifacts/lessons_VC_Q.json` | `memory_*.json` → `Q.rows` z `check.ok` |
| notatki F (Flash), tylko do E2 | `lessons_VC_F.json` | `memory_*.json` → `F.rows` z `check.ok` |
| przebiegi treningowe bez pamięci | przebiegi pilota (jak w b1) | sesja `census` |

## 3. Etap E1 (EXP-MASK-0): pamięć sukcesów bez kopiowania, na zadaniach treningowych

**Po co na zadaniach treningowych.** Mechanizm kopiowania opisałem na 58 zadaniach testowych. Na zadaniach
treningowych pamięci sukcesów nikt nie uruchamiał, więc są dla tej hipotezy świeże. Tu też wybieramy wariant,
żeby nie stroić go na zadaniach rozwojowych-testowych.

**Pula bez własnego zadania.** Dla zadania treningowego `t` pula to ślady sukcesów z pozostałych 19 zadań
treningowych tej samej domeny. Wyszukiwanie jak w R+ (jądro leksykalne 0.2.0, tekst prośby, bez bramki).

**Ramiona (60 zadań, 14B):**

| Ramię | Blok na początku tury |
|---|---|
| N, N′ | brak |
| R+ | 2 surowe ślady (jak w pilocie i NIGHT-1) |
| M2 | te same 2 ślady, wartości zamaskowane |
| M1 | tylko pierwszy z tych śladów, zamaskowany |

**Maskowanie (normatywne co do znaczenia; implementacja z testami jednostkowymi):**

1. Wyszukiwanie działa na niezamaskowanym tekście. M2 pokazuje dokładnie te same ślady co R+, M1 pierwszy z nich.
   Różni się wyłącznie prezentacja.
2. Dla każdej wartości argumentu w każdym wywołaniu śladu (listy i słowniki element po elemencie). Kontekst
   pochodzenia bierze się z **całego epizodu źródłowego** (przebieg treningowy), nie tylko z samego śladu:
   - wartość logiczna i `None`: zostaje;
   - wartość występuje w prośbie tej tury albo wcześniejszych tur zadania źródłowego (napis: bez rozróżniania
     wielkości liter, od 2 znaków; liczba: jako cały token liczbowy): zamiana na `<nazwa_parametru>`, a to samo
     wystąpienie w pokazanej prośbie śladu zamieniane na ten sam znacznik;
   - w przeciwnym razie wartość występuje w wyniku dowolnego wcześniejszego kroku epizodu źródłowego (także z
     wcześniejszych tur): zamiana na `<from an earlier result>`;
   - w przeciwnym razie data w postaci `RRRR-MM-DD`: zamiana na `<YYYY-MM-DD>`;
   - w przeciwnym razie zostaje (stałe proceduralne, np. `a=True`, `mode='c'`, `pedalPosition=1`).
3. Wyniki kroków: udany wynik jako `ok` z listą kluczy najwyższego poziomu (np. `-> ok {nearest_airport}`);
   wynik z błędem jako komunikat z wartościami zamaskowanymi tak, jak robi to `error_key`, z zachowaniem wielkości
   liter.
4. Układ bloku jak w `render_block`. Do nagłówka dochodzi jedno zdanie: `Values written as <...> belonged to that
   earlier task; take the real values from the current request and from your own tool results.`
5. Testy jednostkowe na rzeczywistych wierszach puli, co najmniej: ślad „list of files in tmp directory”
   (`cd(folder=<folder>)`, znacznik także w prośbie); ślad zadania 196 tura 2 (`budget_limit=<from an earlier
   result>`); ślad ze zgłoszeniem „high priority of 4” (`priority=<priority>`); żadna zamaskowana wartość nie
   występuje w gotowym bloku; identyfikatory śladów M2 równe R+.

Prototyp bez modelu: `tier_e/n1_05_mask_prototype.py` (do wykorzystania albo przepisania; normatywny jest tekst
wyżej). Na ośmiu stratach przez kopię z NIGHT-1 skopiowana wartość przestaje być widoczna w bloku w 7 przypadkach
(M2) i w 8 (M1); skopiowany dodatkowy krok znika w 0 z 3 (M2) i w 2 z 3 (M1). Maskowanych jest ok. 76% wartości
argumentów, blok wydłuża się o ok. 12%. To mówi, że źródło kopii znika, a nie że zyski zostają; to mierzy E1.

**Miary.** Rozwiązane; zyski i straty wobec N; **straty przez kopię** według `tier_e/n1_04_copy_losses.py`
(implementacja wzorcowa: wartość lub funkcja nieobecna u N w tej turze, nieobecna w prośbach zadania i we
wcześniejszych wynikach, obecna w bloku); błędy narzędzi; tokeny.

**Reguły (zamrożone):**

- **Wybór wariantu E\*:** najwięcej rozwiązanych spośród R+, M2, M1; przy remisie mniej strat wobec N; przy
  dalszym remisie kolejność M1, M2, R+.
- **H14:** niech M będzie lepszym z M1, M2 według reguły wyżej.
  - wsparta: straty(M) ≤ straty(R+) − 3 i rozwiązane(M) ≥ rozwiązane(R+) − 1;
  - obalona: R+ ma co najmniej 4 straty i straty(M) ≥ straty(R+) − 1, albo rozwiązane(M) ≤ rozwiązane(R+) − 3;
  - nietestowalna: R+ ma mniej niż 4 straty;
  - inaczej nierozstrzygnięta.
- E\* idzie do E3 niezależnie od werdyktu H14.

## 4. Etap E2 (EXP-NOTE-SEL): dobór notatek na stanach treningowych

**Stany.** Jak w b1 z NIGHT-1, rozszerzone na trzy domeny: dla każdej sygnatury błędu widzianej w co najmniej 2
zadaniach treningowych pierwsze wystąpienie w kolejnych zadaniach, najwyżej 8 stanów. Historia rozmowy odtworzona
bajt w bajt, stan środowiska przez ponowne wykonanie wywołań, po wyniku z błędem dochodzi notatka kandydata (albo
nic) i agent kontynuuje do końca tury. Miary: błąd rozwiązany (późniejsze udane wywołanie tej samej funkcji w
turze), tura zaliczona (checker na prefiksie zadania treningowego).

**Kandydaci na sygnaturę:**

| Źródło | Co to | Koszt |
|---|---|---|
| none | bez notatki | – |
| D | lekcja kompilatora, jeśli istnieje | 0 |
| Q | istniejąca notatka Qwena z NIGHT-1 | 0 |
| G0 | notatka ogólna, ten sam tekst dla każdej sygnatury (niżej) | 0 |
| X | notatka złożona z wykonanych napraw (niżej) | 0 wywołań pisarza |
| F | istniejąca notatka Flash; **tylko porównanie**, nie wchodzi do systemu | 0 |
| O, S, P | wyrocznia, lekcja „40 galonów”, placebo; **tylko błąd baku, tylko kontrola narzędzia** | 0 |

Tekst G0 (stały): `{function}: this error was also returned in earlier tasks, and repeating the call with guessed
arguments did not resolve it. Before calling {function} again, use a tool that reads the current state this call
depends on, and base the new arguments on what it returns.`

**Notatka X (naprawa wydobyta z wykonania).** Rozwidlenia z G0 służą też jako eksploracja. Jeśli po G0 błąd został
rozwiązany i tura zaliczona w stanach z co najmniej 2 różnych zadań, a ciąg nazw funkcji między notatką a
pierwszym udanym wywołaniem `{function}` jest w nich taki sam, powstaje X z szablonu (bez LLM):
`{function}: error "{komunikat}" was resolved in earlier tasks by calling {funkcje naprawy} and then {function}
again. Examples: {wywołanie -> wynik; function(argumenty) -> ok} | {drugi przykład z innego zadania}.` Limit 600
znaków. Brak dwóch zgodnych napraw: X nie powstaje. X jest następnie oceniany na wszystkich stanach sygnatury jak
każdy kandydat.

**Reguła wyboru (zamrożona), osobno dla każdej sygnatury, wśród D, X, Q, G0:**

- kandydat jest **dopuszczalny**, gdy (a) nie ma stanu, który „none” zalicza, a on nie; (b) rozwiązane ≥ none;
  (c) zaliczone ≥ none;
- wybrany zostaje dopuszczalny kandydat o największej parze (zaliczone, rozwiązane); remis rozstrzyga kolejność
  D, X, Q, G0;
- brak dopuszczalnego kandydata: sygnatura zostaje bez notatki.

Wynik: zestaw **T** (`notes_T.json`, per domena) z tabelą ocen wszystkich kandydatów.

**Kontrola narzędzia (znana odpowiedź, błąd baku).** Ta sama reguła zastosowana do zbioru {O, S, P, Q, F}.
Narzędzie jest **ważne**, gdy wybiera O albo F i gdy S nie jest dopuszczalna. Jeśli nie jest ważne: zestaw T
zastępuje się zestawem „D, a gdzie go nie ma, Q” (stan z NIGHT-1), H16 dostaje werdykt „narzędzie nieważne przy
tej liczbie stanów”, a program biegnie dalej.

Raportowane dodatkowo, bez wpływu na system: jak często F wygrałby turniej z najlepszym kandydatem lokalnym.

## 5. Etap E3 (EXP-V0-1): system złożony na 88 zadaniach rozwojowych-testowych, 14B

**Ramiona w kolejności priorytetu (cięcie od końca przy braku budżetu):**

| # | Ramię | Blok na początku tury | Notatki po błędzie |
|---|---|---|---|
| 1 | N | – | – |
| 2 | **V0** | E\* | T |
| 3 | N′ | – | – |
| 4 | E\* | E\* | – |
| 5 | TrT | – | T |
| 6 | V0q | E\* | Q (bez turnieju) |
| 7 | TrQ | – | Q (powtórzenie ramienia z NIGHT-1) |
| 8 | R+ | 2 surowe ślady (pomijane, jeśli E\* = R+) | – |

Blok dla zadań testowych: te same ślady, które NIGHT-1 i pilot wybrały dla R+ (`rplus_plan`, wyszukiwanie pilota);
zmienia się tylko prezentacja według E\*.

**Kontrola dryfu:** wynik N musi zgadzać się z N z NIGHT-1 (sA i sD) w co najmniej 84 z 88 zadań. Jeśli nie:
odnotować, analizę prowadzić wyłącznie wewnątrz nowej sesji.

**Test główny (zamrożony):**

- **v0 wsparte (rozwojowo):** V0 − N ≥ 9 zadań; McNemar jednostronny p ≤ 0,01; straty V0 wobec N ≤ 4; V0 ≥ N w
  każdej z trzech domen i V0 > N w co najmniej dwóch; V0 − N > 2 · |N′ − N|.
- **v0 obalone:** V0 − N ≤ 4 albo straty ≥ 8.
- inaczej **pośrednie**.

**Rodzina drugorzędna (Holm, jednostronnie, α = 0,05):**

| Porównanie | Hipoteza | Wsparta, gdy | Obalona, gdy |
|---|---|---|---|
| V0 wobec E\* i V0 wobec TrT | H15 | V0 ≥ max(E\*, TrT) + 3 | V0 ≤ max(E\*, TrT) |
| TrT wobec TrQ | H16 | TrT ≥ TrQ + 2 i straty(TrT) ≤ straty(TrQ) | TrT ≤ TrQ − 2 |
| E\* wobec R+ (jeśli różne) | H14, powtórka | straty przez kopię(E\*) ≤ straty przez kopię(R+) − 3 i E\* ≥ R+ − 1 | E\* ≤ R+ − 3 |

**Konfiguracja do dalszych etapów (K):** V0, jeśli V0 ≥ V0q + 2; w przeciwnym razie V0q (tańsza budowa: bez
turnieju). Jeśli V0q nie pobiegło z braku budżetu: K = V0.

**Miary w raporcie:** rozwiązane ogółem i per domena; zyski i straty z przyczyną (pamięć, szum przed pamięcią,
kopia) metodą z `aamr_night1_followup.py` i `n1_04_copy_losses.py`; tury z błędem zaliczone; zdarzenia błędu;
wywołania i tokeny; ekspozycja (które ślady i notatki pokazano); koszt budowy pamięci w wywołaniach.

## 6. Etap E4 (EXP-V0-1C): ramiona w stylu konkurentów, osobna sesja

Sesja na tych samych 88 zadaniach, 14B: **N, K, C-RB, C-G**. To zarazem powtórzenie porównania K wobec N.

**C-RB (styl ReasoningBank).**
- Budowa: dla każdego z 60 epizodów treningowych bez pamięci jedno lokalne wywołanie 14B, które wyciąga do 3
  pozycji pamięci (tytuł, opis, treść). Prompty dla trajektorii udanej i nieudanej z ich kodu:
  `sota-research-2026-11-12/external/google-research_reasoning-bank/third_party/src/minisweagent/memory/`
  (`instruction.py`, `induce_memory.py`; Apache-2.0, zachować informację o pochodzeniu). Dostosować wyłącznie opis
  formatu trajektorii.
- Etykieta sukcesu z checkera zamiast ich sędziego LLM (korzystne dla konkurenta; odnotować).
- Użycie: na początku tury 1 pozycja najbliższa prośbie (k = 1 jak u nich), wyszukiwanie tym samym jądrem
  leksykalnym co nasze (u nich osadzenia; odnotować jako odstępstwo, lokalnie nie ma modelu osadzeń).
- Limit bloku 2 800 znaków, ten sam nagłówek co nasz blok.

**C-G (styl ExpG).** Wskazówki per narzędzie pisane przez lokalny model z trajektorii treningowych, jak ramię G w
S1: dla VC gotowe (`experience-xfer-v1/g-guidance.json`), dla GFS i TRAVEL tym samym promptem i schematem
(`guidance_request`, jedno wywołanie na narzędzie), prezentacja przez `guidance_block_provider`.

Oba ramiona budowane wyłącznie z przebiegów treningowych. Koszt budowy (wywołania, tokeny) w raporcie.

**Reguła (zamrożona):** niech C to lepsze z C-RB, C-G.
- **K przed konkurentami (rozwojowo):** K − C ≥ 4 zadania i straty(K) ≤ straty(C) + 1;
- **K nie przed konkurentami:** K − C ≤ 1;
- inaczej nierozstrzygnięte.
- Osobno raportowany warunek kosztu: wywołania LLM na budowę pamięci K wobec C (dla K liczą się rozwidlenia E2,
  jeśli K = V0).

## 7. Etap E5: drugi model

`qwen3.5:9b-q4_K_M`, 88 zadań: **N, K, N′**. Pamięć zbudowana z przebiegów 14B, bez zmian.
Reguła: **powtórzone**, gdy K − N ≥ 5 i straty ≤ 4; **niepowtórzone**, gdy K − N ≤ 2; inaczej nierozstrzygnięte.

## 8. Budżet i kolejność

| Etap | Zawartość | Szacunek | Budżet |
|---|---|---|---|
| T | test techniczny (wznowienie, sondy JSON, oba modele) | 100 | 150 |
| E1 | 5 ramion × 60 zadań × ok. 9,7 | 2 900 | 3 100 |
| E2 | ok. 460 rozwidleń × ok. 2,6 | 1 200 | 2 200 |
| E3 | 8 ramion × 88 × ok. 9,7 | 6 800 | 7 400 |
| E4 | budowa ok. 110 + 4 ramiona × 88 × ok. 9,7 | 3 500 | 4 000 |
| E5 | 3 ramiona × 88 × ok. 12,8 | 3 400 | 3 800 |
| | **razem** | **17 900** | **20 650** (limit twardy 21 500) |

Czas GPU: ok. 5,5 godziny. Koszt: 0 USD. Kolejność: T, E1, E2, budowa C-RB i C-G, E3, E4, E5, zamrożenie i raport.
Etap zależny jest pomijany, gdy zależność nie przeszła; niezależne biegną dalej (jak w NIGHT-1). Wyczerpanie
budżetu etapu zatrzymuje ramiona o najniższym priorytecie.

## 9. Raport końcowy i reguła następnego kroku

Raport generowany z zamrożonych surowych danych (sha256), według reguł tej specyfikacji; interpretacja w osobnym
pliku. Obowiązkowo:

1. Tablica wyników wszystkich sesji, z N′.
2. Werdykty H14, H15, H16, testu głównego, reguły konkurentów i drugiego modelu.
3. Spis porażek konfiguracji K według taksonomii NIGHT-1 oraz lista otwartych problemów.
4. Zyski i straty z przyczynami; lista zadań straconych przez K z turą rozstrzygającą.
5. Koszty budowy i użycia pamięci.
6. Aktualizacja tabeli hipotez ze strategii.

**Reguła rekomendacji egzaminu (decyzję podejmuje właściciel):**

- **GOTOWE DO EGZAMINU**, gdy: test główny „wsparte”; w E4 K − N ≥ 6; K przed konkurentami; E5 „powtórzone”.
- **POPRAWIĆ NAJSŁABSZY SKŁADNIK**, gdy test główny „pośrednie” albo K nie jest przed konkurentami: raport
  wskazuje składnik według spisu porażek i strat.
- **WRÓCIĆ DO SKŁADNIKÓW**, gdy test główny „obalone”.

Egzamin (do osobnej decyzji, **nie uruchamiać**): TradingBot, 20 scenariuszy na budowę pamięci, 30 scenariuszy × 4
odmiany BFCL = 120 zadań, ramiona N, K, najlepszy konkurent, analiza po scenariuszach, protokół zamrożony przed
pierwszym odczytem zadań.

## 10. Zasady przebiegu

- Protokół, konfiguracja, kod i testy zamrożone i zacommitowane lokalnie przed pierwszym wywołaniem
  eksperymentalnym. Poprawki techniczne dozwolone tylko przed pierwszym wywołaniem etapu, którego dotyczą, z
  wpisem w protokole; hipotezy, progi, ramiona i zbiory zadań bez zmian.
- Test zgodności przed startem: suchy przebieg na zapisanych odpowiedziach NIGHT-1 musi dla ramion N i R+ dać
  bajt w bajt te same prośby do modelu co w sesjach sA i sD. Bez tego nie startować.
- Jeśli specyfikacja jest niejednoznaczna: wybrać wariant prostszy i bliższy NIGHT-1, zapisać wybór w protokole
  przed startem etapu. Nie pytać właściciela.
- Awarie, wznowienia, pamięć podręczna odpowiedzi, nadzorca: jak w NIGHT-1. Po zakończeniu usunąć zadanie
  harmonogramu.
- Niczego nie dodawać po starcie. Analizy dodatkowe po obejrzeniu wyników mają status eksploracyjny i osobny plik.
- Wiersz w rejestrze eksperymentów i zdarzenia pamięci projektu jak dla NIGHT-1.

## 11. Czego ten program nie rozstrzyga

- Nie potwierdza systemu na czystych danych. Robi to dopiero egzamin.
- Ramiona konkurentów są uproszczone (wyszukiwanie leksykalne, etykieta z checkera, lokalny model jako pisarz).
- Jeden benchmark. Drugi model tylko jako agent, nie jako budowniczy pamięci.
- Notatka X powstaje tylko tam, gdzie agent po ogólnej wskazówce sam znajdzie naprawę. Dla pozostałych sygnatur
  treść nadal pochodzi od pisarza albo jej nie ma.
