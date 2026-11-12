# AAMR-NIGHT-1: protokół (zamrożony przed pierwszym wywołaniem modelu)

Data: 2026-11-12. Autor: Claude (Opus 5.5), na zlecenie właściciela („AAMR — autonomiczny program eksperymentalny”).
Program: `scripts/aamr_night1.py`, analiza: `scripts/aamr_night1_analysis.py`, konfiguracja: `config.json`.
Surowe dane poza Git: `GH_REVIVAL/aamr-night1-2026-11-12/run/`. Ten plik ma sha256 zapisany w identyfikatorze
konfiguracji; zmiana po starcie zatrzymuje program (kod wyjścia 2).

Podstawa: `strategy-2026-11-12/STRATEGIA_AAMR.md` (etap 0, sekcja 5) z `AKTUALIZACJA_1` (ramię N′) i
`direction-review-2026-11-12/OCENA_KIERUNKU.md` sekcja 7 (EXP-FIX-0: teksty lekcji i reguły decyzji). Teksty
wyroczni i placebo są przepisane bez zmian do `scripts/aamr_night1.py` (stałe `ORACLE`, `PLACEBO`).

## 0. Wspólne warunki

- BFCL multi-turn base, checkout `6ea5797`, oficjalny checker; pętla agenta S1 (`run_episode_x`) bez zmian; dostarczanie
  lekcji „po pasującym błędzie, raz na epizod” jak ramię Tr w S1. Temperatura 0, seed 7, `num_ctx` 8192,
  `num_predict` 512, najwyżej 8 kroków na turę.
- Agent: `qwen2.5:14b-instruct` (digest `7cdf5a01…`) we wszystkich etapach poza E. Etap E: `qwen3.5:9b-q4_K_M`
  (digest `56671c2a…`), `think: false`, `presence_penalty` 0 (domyślne 1,5 psuje deterministyczny JSON), reszta jak wyżej.
- Podziały: Vehicle Control (VC) = podział pilota (20 treningowych, 30 testowych; dane rozwojowe, już zużyte). System
  plików (GFS, id 0–49) i podróże (TRAVEL, id 150–199): ta sama metoda (rosnące id, `random.Random(20261112).shuffle`,
  20 + 30). Z testu podróży wypadają 167 i 180 (puste tury wzorca): 58 zadań testowych GFS + TRAVEL, nigdy dotąd
  nieużywanych. TradingBot (100–149) pozostaje nietknięty (strażnik w kodzie).
- Kolejność ramion losowana osobno dla każdego zadania; wszystkie ramiona jednego porównania w jednej sesji.
- Analiza tylko na zadaniach kompletnych we wszystkich ramionach porównania. Test: dokładny McNemar.
- Pamięć zamrożona na czas testu. Zadania testowe nie trafiają do żadnego pisarza ani kompilatora.

## 1. Etapy i ramiona

| Etap | Dane | Ramiona | Budżet (lokalne) |
|---|---|---|---|
| preflight_q14 | sondy techniczne | 3 sondy JSON, model w całości na GPU, digest | A |
| a0_writer | VC trening | lokalny pisarz lekcji o błędzie baku (dla TrW) | A |
| b0_writers | VC trening | pisarze Q (Qwen 14B) i F (DeepSeek Flash) dla każdej sygnatury błędu z ≥ 2 zadań | B, Flash |
| b1_quality | VC trening | test lekcji w prawdziwych stanach błędu z przebiegów pilota (sekcja 3) | B |
| sA | VC test, 30 | **A:** N, N′, Tr, TrO, TrP, TrW; **B:** TrQ, TrF (jeśli przeszły bramkę); **H:** TrS | A 2300, B 1000, H 400 |
| census | GFS + TRAVEL trening, 40 | N | D |
| d0_build | z census | lekcje deterministyczne, pisarze Q i F, pula sukcesów R+ | D, Flash |
| sD | GFS + TRAVEL test, 58 | N, TrD, N′, TrF, TrQ, R+ (kolejność priorytetu przy cięciu budżetu) | D 5300 |
| sC | VC trening, 20 | N, TrP, TrO | C 800 |
| preflight_q9, sE | VC test, 30 | N, TrO, TrP, Tr, N′ na `qwen3.5:9b` | E 2000 |
| final | — | zamrożenie sha256, analiza, raport, lokalny commit | 0 |

Łączny twardy limit: 12 000 lokalnych prób (każda próba liczona, także nieudana), 200 wywołań Flash, 3 USD
(rezerwacja 0,01 USD na wywołanie, więc praktyczny sufit 2 USD). Bufor T (150) na test techniczny przed nocą.

Ramiona:

- **N, N′**: bez pamięci; N′ to drugi przebieg tej samej sesji (próg szumu).
- **Tr**: trzy lekcje deterministyczne S1 (`experience-xfer-v1/lessons.jsonl`, wszystkie o `startEngine`).
- **TrO / TrP**: Tr oraz wyrocznia / placebo przy błędzie „Cannot fill gas above the tank capacity.”.
- **TrW**: Tr oraz lekcja o tym błędzie napisana przez lokalny model (sekcja 2), bez wzorca.
- **TrQ / TrF**: wyłącznie lekcje pisarza Q / F dla wszystkich sygnatur VC (zastępują lekcje deterministyczne).
- **TrS** (sonda szkody, zmiana warunków): Tr oraz wyrocznia napisana dla starszego baku 40 galonów (wszystkie „50” → „40”).
- **TrD**: lekcje kompilatora S1 (bez LLM) z przebiegów census danej domeny.
- **R+**: dwa udane ślady z census danej domeny, wyszukane po treści prośby (jak R+ w pilocie, bez bramki).

## 2. Pisarze lekcji (porównanie sposobów tworzenia pamięci)

- Trzy źródła: D (kompilator, 0 wywołań), Q (`qwen2.5:14b-instruct`), F (`deepseek-flash`, tylko przez klienta z
  rezerwacjami). Q i F dostają **identyczne** wejście: opisy narzędzi klasy, której dotyczy błąd; komunikat błędu;
  do 6 tur treningowych z tym błędem (prośba, wywołania i wyniki, wynik tury z checkera na zadaniu treningowym).
  Polecenie: notatka do 60 słów, tylko narzędzia z listy, bez wymyślonych wartości, JSON `{"note": ...}`.
  Notatka dostaje prefiks z nazwą narzędzia i limit 600 znaków. Ciągi ≥ 12 cyfr i adresy e-mail są maskowane w
  wejściu obu pisarzy. Strażnik prywatności blokuje wysyłkę, jeśli wejście zawiera ścieżki lokalne lub identyfikatory
  właściciela. Dane to publiczny benchmark BFCL (fikcyjne osoby i wartości).
- Kontrole deterministyczne każdej notatki: poprawny JSON i niepusta; każdy identyfikator w stylu kodu i każda nazwa
  wywołania istnieje w opisach narzędzi lub w wejściu pisarza; brak tokenów występujących tylko w zadaniach testowych
  (liczby, ciągi z wzorców i konfiguracji, nazwy własne). Notatka, która nie przejdzie, nie jest używana.

## 3. Test jakości lekcji na danych treningowych i bramka (b1)

- Stany: przebiegi pilota (ramię N) na 20 zadaniach treningowych VC. Dla każdej sygnatury pierwsze wystąpienie w
  kolejnych zadaniach: do 6 dla błędu baku, do 4 dla pozostałych. Historia rozmowy odtworzona bajt w bajt, stan
  środowiska odtworzony przez ponowne wykonanie wywołań. Po wyniku z błędem dochodzi notatka źródła (albo nic) i agent
  kontynuuje na żywo do końca tej tury.
- Miary (środowisko, nie opinia modelu): błąd rozwiązany (późniejsze udane wywołanie tej samej funkcji w turze),
  tura zaliczona (checker na prefiksie zadania treningowego).
- Źródła: none, D, O (wyrocznia, kontrola dodatnia, tylko błąd baku), Q, F.
- **Bramka dopuszczenia Q/F do testów z agentem:** źródło dostępne; ważne notatki dla ≥ 60% sygnatur; zero wycieków;
  liczba rozwiązanych błędów w teście ≥ wynik „none” − 2 na tych samych stanach. Niespełniona bramka: ramię
  pomijane w sA i sD, reszta programu biegnie dalej. W sD pisarz musi mieć ważne notatki dla ≥ 60% sygnatur w obu
  domenach.

## 4. Hipotezy i reguły decyzji

**EXP-FIX-0 (sA, ramiona A; status: rozwojowy, zadania zużyte).** Reguły z `OCENA_KIERUNKU.md` §7 + N′:
- utrzymana: TrO ≥ N + 5, McNemar jednostronny p ≤ 0,05, TrO ≥ TrP + 3, ≥ 1/2 tur z błędem baku w TrO zaliczona,
  TrO − N > |N′ − N|;
- obalona: TrO ≤ N + 2 albo < 1/3 tur z błędem baku zaliczona albo TrO ≤ TrP + 1;
- pośrednia: inaczej. Tr z S1 powtórzony, jeśli Tr ≥ N + 3. TrW „blisko TrO”, jeśli TrO − TrW ≤ 1; „blisko N”, jeśli TrW − N ≤ 1.

**Porównanie twórców (sA, rozwojowe; sD, na nietkniętych zadaniach).** „Flash pomaga bardziej niż lokalne
rozwiązania”, jeśli TrF − max(TrQ, Tr/TrD) ≥ 3 i McNemar jednostronny TrF względem lepszego lokalnego p ≤ 0,05 w sD;
różnica w granicach |N′ − N| + 1 = brak wykrytej różnicy. Raportowane też koszty budowy i jakość z b1.

**Sonda szkody TrS (eksploracyjna z przewidywaniem):** TrS rozwiąże mniej zadań niż TrO; mierzone: tury, w których po
notatce agent dolał dokładnie 40 − poziom (podążanie za nieaktualną pamięcią) zamiast 50 − poziom; zadania stracone
względem N.

**Replikacja H5 (sC, 20 innych zadań VC):** replikacja, jeśli TrO ≥ N + 3 i TrO ≥ TrP + 2; brak, jeśli TrO ≤ N + 1;
inaczej niejednoznaczna.

**Transfer (sD, potwierdzające, 58 nietkniętych zadań).** Test główny: TrD > N, McNemar jednostronny p ≤ 0,05 i
TrD − N > |N′ − N|. Rodzina drugorzędna z korektą Holma: TrD, TrQ, TrF, R+ względem N. Porównania TrF/TrQ wobec TrD
dwustronnie.

**Drugi model (sE):** te same reguły co EXP-FIX-0 (bez TrW), na własnym N i N′ modelu 9B. Lekcje Tr pochodzą z
przebiegów 14B (przeniesienie pamięci między modelami).

**Spis porażek (census, sA-N, sD-N, sE-N; eksploracyjny):** klasa pierwszej nieudanej tury: błąd nierozwiązany, błąd
rozwiązany a tura zła, nieprawidłowe wywołanie bez błędu środowiska, brak wywołania, brak błędu a złe lub zbędne
działanie, limit kroków, limit kontekstu. H7: udział porażek „przy błędzie” w nowych domenach.

Wszystko poza testami nazwanymi wyżej jest eksploracyjne. Wyniki VC (sA, sC, sE) mają status rozwojowy, bo zadania
VC i ich porażki znamy z pilota i S1.

## 5. Reguły przebiegu

- Etapy w ustalonej kolejności; etap zależny pomijany, gdy jego zależność nie przeszła (preflight → wszystko na danym
  modelu; census → d0 → sD; b0 → b1 → ramiona TrQ/TrF). Niezależne etapy biegną dalej.
- Przed sD: koszt ramion szacowany z census (wywołania na epizod × 1,15); ramiona dokładane w kolejności priorytetu,
  dopóki mieszczą się w budżecie D. Wyczerpanie budżetu w trakcie sesji zatrzymuje tylko ramiona tego budżetu;
  analiza bierze zadania kompletne.
- Awaria techniczna: najwyżej 4 próby jednego wywołania (odstępy 15, 45, 90 s), próba uruchomienia Ollamy; potem
  restart procesu przez nadzorcę (najwyżej 8 łącznie, przerwa 120 s); potem bezpieczne zatrzymanie z `STOPPED.json`.
  Żadne dane nie są kasowane; wznowienie od ostatniego zapisanego epizodu, odpowiedzi odtwarzane z pamięci podręcznej.
- Brak dostępu do Flash albo naruszenie limitu: ramiona F pomijane, reszta biegnie.
- Nie dodaje się etapów po starcie. Po zakończeniu: sha256 wszystkich plików surowych, potem analiza.

## 6. Poprawka techniczna przed startem (2026-11-12, przed pierwszym wywołaniem eksperymentalnym)

Test techniczny (`smoke-run`, budżet T: 66 prób lokalnych, 2 wywołania Flash, 0,0009 USD) przeszedł: obie wersje
modelu w całości na GPU, sondy JSON poprawne, przerwanie procesu w trakcie epizodu i wznowienie bez ponownego
wysłania zapisanych wywołań, Flash zwraca `deepseek-flash`. Jedna odpowiedź Flash zawierała token
`<|endoftext|>` w środku JSON. Przed parsowaniem notatki usuwane są ciągi postaci `<|...|>` (jednakowo dla wszystkich
źródeł). Hipotezy, ramiona, progi i dane bez zmian.

Druga poprawka przed startem: budżet D podniesiony z 4800 do 5300 (suma budżetów etapów 11 950 ≤ 12 000), bo
szacunek z testu technicznego (ok. 12 wywołań na epizod w zadaniach 3–4-turowych) odciąłby z góry ostatnie ramię
sD (R+). Budżety A (2300) i B (1000) bez zmian.
