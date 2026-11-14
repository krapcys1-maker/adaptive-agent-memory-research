# Recenzja NIGHT-2 (zadanie #15)

**Werdykt: WRÓCIĆ DO SKŁADNIKÓW.** Zgadzam się z raportem: rekomendacja wynika z zamrożonej reguły (SPEC §9 z rozstrzygnięciem PROTOCOL D17), a żaden z czterech warunków „GOTOWE DO EGZAMINU" nie jest spełniony. Egzamin na TradingBot powinien pozostać niewykorzystany.

**Zakres sprawdzenia.** Miałem `results.json`, `REPORT.md`, specyfikację, protokół i weryfikację koordynatora, bez surowych sesji i bez `WNIOSKI.md`. Sprawdziłem spójność wewnętrzną (sumy rozwiązanych, sumy po domenach, budżety, liczniki rozwidleń E2), zastosowanie każdej reguły do liczb oraz wartości p. Sześć wartości p przeliczyłem dokładnie (np. TrT 79/4096, TrQ 299/4096, TrT wobec TrQ 93/256), pozostałe w przybliżeniu; rozbieżności nie znalazłem. Przeliczenia z surowych plików nie robiłem.

## Co potwierdzam

| Element | Reguła i liczby | Werdykt raportu | Ocena |
|---|---|---|---|
| Test główny | V0 35, N 28 (+7, p jednostronne 0,148); straty 13 ≥ 8; TRAVEL 10 < 13 | obalone | Zgoda. Obala wyłącznie klauzula strat; sama różnica +7 dałaby „pośrednie". Po odjęciu dwóch niestabilnych zadań (81, 43) strat jest 11, nadal ≥ 8. |
| H14 (E1) | M = M1: rozwiązane 18 wobec 22 dla R+; straty 10 wobec 9; straty przez kopię 5 wobec 7 | obalona | Zgoda, obie klauzule obalenia spełnione. Dotyczy tej implementacji maskowania (zastrzeżenie 6). |
| E\* | R+ 22, M1 18, M2 14 | R+ | Zgoda. Powtórka H14 w E3 słusznie nie dotyczy. |
| H15 | V0 35 ≤ max(E\* 38, TrT 36) | obalona | Zgoda. System złożony jest poniżej obu składników (V0 wobec E\*: 1 zyskane, 4 stracone). |
| H16 | TrT 36 ≥ TrQ 34 + 2; straty 2 ≤ 3; kontrola narzędzia ważna (wybrane F, S niedopuszczalna) | wsparta | Reguła zastosowana poprawnie, ale wynik leży dokładnie na progu (zastrzeżenie 2). |
| K | V0 35 < V0q 34 + 2 | V0q | Zgoda. |
| Konkurenci (E4) | K 32, C-G 31, różnica 1 ≤ 1; straty 11 wobec 8; K − N = 5 | K nie przed | Zgoda. |
| Drugi model (E5) | K 40, N 35 (+5); straty 12 > 4 | nierozstrzygnięte | Zgoda. |
| Dryf, budżet, granice | N zgodne z NIGHT-1 w 86 z 88; 16 138 z 21 500 prób; 0 płatnych; brak zadań 100–149; zbiory treningowe i testowe rozłączne | – | Zgoda. |

**Zgodność z regułą mechaniczną:** rekomendacja raportu jest zgodna. Warunek „POPRAWIĆ" (K nie przed konkurentami) też jest dosłownie spełniony, ale D17, zamrożone przed startem, daje pierwszeństwo „obalone".

## Co podważam

1. **Brak placebo dla bloku na początku tury.** N′ jest prawie deterministyczną powtórką (0–1 zmian), więc nie mierzy wrażliwości na samą obecność bloku. Wszystkie zyski mają przyczynę „memory" jako kategorię resztkową, bez sprawdzenia, czy wpis został użyty. Strategia (sekcja 2) wymaga ramienia bez treści.
2. **H16 jest wsparta tylko nominalnie.** Para TrT wobec TrQ to 5:3 (p = 0,363, Holm nie odrzuca), jedno zadanie zmienia werdykt, a jedna ze strat TrT to szum. W systemie złożonym turniej daje +1 (V0 35, V0q 34) i nie wchodzi do K.
3. **Turniej E2 ma małą moc.** 10 z 20 sygnatur ma po 2 stany, a 10 z 16 wybranych notatek remisuje z „none". Placebo P jest dopuszczalne, notatka X powstała 4 razy i nie została wybrana ani razu. Turniej działa jak filtr regresji, nie jak selektor treści.
4. **E4 i E5 oceniały słabszą konfigurację.** K = V0q (34) było w E3 poniżej E\* (38) i TrT (36), bo reguła wybierała tylko między V0 a V0q. Wnioski o H10 dotyczą V0q.
5. **Przewaga K nad konkurentami pochodzi wyłącznie z VC.** C-G ma tam wskazówki dla 1 narzędzia (`g_tools.VC = 1`). Na 58 zadaniach GFS + TRAVEL: N 18, K 19, C-RB 19, C-G 21. Ramiona konkurentów są też uproszczone (wyszukiwanie leksykalne, temperatura 0, etykieta z checkera).
6. **Maskowanie wymaga audytu.** W blokach zamaskowanych zostały widoczne wartości specyficzne (`cp:79.pdf` w M2, zadanie 26; `post_tweet:@mike53` w M1, zadanie 78). Liczba `invalid_calls` rośnie: N 6, R+ 16, M2 26. Różnice przy n = 60 nie są istotne.
7. **Poprawka nr 4 jest formalnym odstępstwem od SPEC §10.** Weszła po pierwszym wywołaniu E1 (3 restarty). Zgodności bloków bajt w bajt nie mogę stąd sprawdzić.
8. **Zadania 81 i 43 są niestabilne w samym N,** a w listach strat mają przyczynę „memory".
9. **Efekt pamięci sukcesów zależy od próbki zadań.** Na świeżych zadaniach E1 to +2 z 60 (11:9), na wielokrotnie używanych E3 +10 z 88. Szacunek z E3 może być zawyżony.
10. **Wielokrotne porównania.** TrT wobec N (p dwustronne 0,039) to jedyny nominalnie istotny wynik z 15, bez korekty.
11. **E5 nie powtarza wzoru po domenach.** Na 9B: GFS −1, TRAVEL +2; na 14B: GFS +4 do +5, TRAVEL −3. Zbiory zyskanych i straconych zadań są w dużej części inne.
12. **Braki raportu:**
    - Nie ma ekspozycji (które ślady i notatki pokazano), choć wymaga jej SPEC §5.
    - Tabela hipotez ze strategii (H1, H4, H10, H13) nie jest zaktualizowana.
    - Nagłówek tabeli E2 ma 5 etykiet dla 4 wartości.
    - Etap `final` ma status `None`.
    - `K_build_calls` wynosi 0, choć notatki Q kosztowały 20 wywołań w NIGHT-1.

## Obserwacje eksploracyjne (po fakcie, bez mocy werdyktu)

- **Straty są powtarzalne.** 10 z 11–12 strat K powtarza się między E3 i E4, w tym 8 w TRAVEL, z tymi samymi skopiowanymi wartościami (`set_budget_limit:7142.86`, `create_ticket:4.0`).
- **Pamięć sukcesów psuje dużą część tego, co N rozwiązuje.** Na 14B to 41–46% (9/20, 12/28, 13/28, 11/27); notatki po błędzie psują 7–11% (2/28, 3/28).
- **Składniki sobie przeszkadzają.** Z 5 zadań zyskanych tylko przez TrT (97, 82, 63, 1, 166) V0 nie zachowuje żadnego; liczba pokazanych notatek spada ze 104 do 58.
- **Notatki pomagają głównie w VC.** TrT daje tam +6, poza VC +2 (20 wobec 18).
- **Najsłabszy składnik to prezentacja pamięci sukcesów (C3).** Kopie to 7 z 12 strat K w E3 i 8 z 11 w E4, a zaplanowana naprawa (H14) zawiodła. 26 z 54 porażek K to porażki bez błędu, poza zasięgiem notatek.

```json
{
  "verdict": "WRÓCIĆ DO SKŁADNIKÓW",
  "agrees_with_report": true,
  "mechanical_rule_outcome": "WRÓCIĆ DO SKŁADNIKÓW: test główny obalony (V0 35 wobec N 28, straty 13 >= 8). Rekomendacja raportu jest zgodna z regułą SPEC §9 w rozstrzygnięciu PROTOCOL D17 (obalone ma pierwszeństwo przed warunkiem K nie przed konkurentami). Żaden z czterech warunków GOTOWE nie jest spełniony.",
  "rationale": "Reguły zamrożone zastosowano poprawnie do liczb z results.json; sumy, podziały po domenach, budżety i wartości p są spójne. Test główny jest obalony klauzulą strat (13, po odjęciu dwóch niestabilnych zadań 11, próg 8), przy różnicy +7 i p jednostronnym 0,148. System złożony jest poniżej obu składników (V0 35, E* 38, TrT 36), maskowanie nie usunęło strat i obniżyło zyski (M1 18 wobec R+ 22), K nie wyprzedza konkurentów (32 wobec 31, a poza VC 19 wobec 21), a drugi model daje +5 przy 12 stratach. Egzamin jest jednorazowy i nie ma podstaw, by go teraz zużyć. Przeliczenia z surowych sesji nie wykonałem, bo nie było ich w kontekście.",
  "key_findings": [
    "Test główny: V0 35, N 28 (+7, p jednostronne 0,148), straty 13; obalony wyłącznie przez straty, wynik odporny na dwa niestabilne zadania (81, 43).",
    "H15 obalona: V0 35 <= max(E* 38, TrT 36); z 5 zadań zyskanych tylko przez TrT V0 nie zachowuje żadnego (eksploracyjnie).",
    "H14 obalona dla tej implementacji: M1 18 wobec R+ 22 rozwiązanych, straty 10 wobec 9, straty przez kopię 5 wobec 7; E* = R+.",
    "H16 wsparta dokładnie na progu: TrT 36, TrQ 34, straty 2 wobec 3; para 5:3, p = 0,363, Holm nie odrzuca; w systemie złożonym V0 35 wobec V0q 34.",
    "E4: K 32, C-G 31, C-RB 30, N 27; K nie przed konkurentami; na 58 zadaniach GFS+TRAVEL K 19, C-G 21, N 18 (eksploracyjnie).",
    "E5 (9B): K 40, N 35 (+5), straty 12; nierozstrzygnięte; wzór po domenach odwrotny niż na 14B.",
    "Straty K są powtarzalne: 10 wspólnych między E3 i E4, 8 w TRAVEL, kopie stanowią 7 z 12 i 8 z 11; pamięć sukcesów psuje 41-46% zadań rozwiązywanych przez N, notatki po błędzie 7-11% (eksploracyjnie).",
    "Najczystszy składnik to notatki po błędzie: TrT +8 (10:2, p dwustronne 0,039 bez korekty), TrQ +6 (9:3); zysk skupiony w VC (+6), poza VC +2.",
    "Granice dotrzymane: 16 138 z 21 500 prób, 0 wywołań płatnych, brak zadań TradingBot, zbiory treningowe i testowe rozłączne, dryf N 86 z 88."
  ],
  "hypotheses_update": [
    {"hypothesis": "test główny v0", "verdict": "obalone", "evidence": "V0 35 wobec N 28, straty 13 >= 8, TRAVEL 10 < 13 (results.json E3.main)"},
    {"hypothesis": "H14", "verdict": "obalona (dla tej implementacji maskowania)", "evidence": "E1: M1 18 wobec R+ 22; straty 10 wobec 9; straty przez kopię R+ 7, M2 6, M1 5; invalid_calls M2 26 wobec R+ 16"},
    {"hypothesis": "H14 powtórka w E3", "verdict": "nie dotyczy", "evidence": "E* = R+"},
    {"hypothesis": "H15", "verdict": "obalona", "evidence": "V0 35, E* 38, TrT 36; V0 wobec E* 1 zyskane i 4 stracone"},
    {"hypothesis": "H16", "verdict": "wsparta nominalnie, na progu, nieistotna statystycznie", "evidence": "TrT 36, TrQ 34, straty 2 wobec 3; p jednostronne 0,363; kontrola narzędzia ważna na 6 stanach; V0 35 wobec V0q 34"},
    {"hypothesis": "H10 (rozwojowo)", "verdict": "niewsparta: K nie przed konkurentami", "evidence": "E4: K 32, C-G 31, straty 11 wobec 8; poza VC K 19 wobec C-G 21"},
    {"hypothesis": "drugi model (E5)", "verdict": "nierozstrzygnięte", "evidence": "K 40, N 35, straty 12 > 4"},
    {"hypothesis": "H1 (pamięć sukcesów pomaga)", "verdict": "propozycja aktualizacji: zysk netto powtarzalny, cena wysoka", "evidence": "E* +10 (22:12) w E3, R+ +2 (11:9) w E1; 9 z 20 i 12 z 28 zadań N straconych"},
    {"hypothesis": "H4 (lekcja po błędzie bez szkód)", "verdict": "propozycja aktualizacji: wsparta rozwojowo po raz kolejny", "evidence": "TrT 10:2, TrQ 9:3; poza VC tylko +2 i +3"},
    {"hypothesis": "H13 (wynik nie spada z doświadczeniem)", "verdict": "propozycja aktualizacji: obserwacja przeciw powtórzona", "evidence": "TRAVEL: E* 12 wobec N 13, K 10 wobec 13 w E3 i E4; GFS: E* 12 wobec 5"}
  ],
  "concerns": [
    "Brak ramienia placebo dla bloku na początku tury; N' to prawie deterministyczna powtórka (0-1 zmian), więc warunek szumu jest słabym zabezpieczeniem, a przyczyna memory przy zyskach jest kategorią resztkową bez sprawdzenia użycia wpisu.",
    "H16 wsparta dokładnie na progu (36 wobec 34), p = 0,363, Holm nie odrzuca; D12 uznaje progi bez istotności; jedno zadanie zmienia werdykt, a jedna strata TrT to szum.",
    "Turniej E2 ma małą moc: 10 z 20 sygnatur ma po 2 stany, 10 z 16 wybranych notatek remisuje z none, placebo P jest dopuszczalne, X wybrana 0 razy z 4; kontrola narzędzia na 6 stanach.",
    "E4 i E5 oceniały K = V0q (34), które w E3 było słabsze od E* (38) i TrT (36); reguła K nie pozwalała wybrać samego składnika.",
    "C-G w VC ma wskazówki dla 1 narzędzia; przewaga K nad konkurentami pochodzi wyłącznie z VC, na GFS+TRAVEL K 19 wobec C-G 21; ramiona konkurentów uproszczone (wyszukiwanie leksykalne, temperatura 0, etykieta z checkera, pisarz 14B).",
    "Maskowanie: w blokach zamaskowanych widoczne wartości specyficzne (cp:79.pdf w M2 zadanie 26, post_tweet:@mike53 w M1 zadanie 78); wzrost invalid_calls (N 6, R+ 16, M2 26); obalenie dotyczy implementacji, różnice przy n = 60 nieistotne.",
    "Poprawka nr 4 wprowadzona po pierwszym wywołaniu E1 (KeyError VC, 3 restarty) jest formalnym odstępstwem od SPEC §10; zgodności bloków bajt w bajt nie da się sprawdzić z dostarczonego kontekstu.",
    "Zadania 81 i 43 są niestabilne w samym N (dryf, N'), a w listach strat mają przyczynę memory; werdykt testu głównego jest na to odporny (11 >= 8).",
    "Efekt pamięci sukcesów zależy od próbki: +2 z 60 na świeżych zadaniach E1 wobec +10 z 88 na wielokrotnie używanych zadaniach E3; szacunek z E3 może być zawyżony.",
    "Wielokrotne porównania: TrT wobec N (p dwustronne 0,039) to jedyny nominalnie istotny wynik z 15, bez korekty.",
    "E5: ten sam wynik netto (+5), ale inne zadania i odwrotny wzór po domenach (9B: GFS -1, TRAVEL +2; 14B: GFS +4 do +5, TRAVEL -3); po 1 epizodzie context_overflow w E* i V0q.",
    "Nakładanie się warunków w SPEC §9 (K nie przed konkurentami daje POPRAWIĆ, obalone daje WRÓCIĆ); rozstrzyga dopiero D17.",
    "Braki raportu: brak ekspozycji wymaganej w SPEC §5, brak aktualizacji tabeli hipotez ze strategii (H1, H4, H10, H13), nagłówek tabeli E2 z 5 etykietami dla 4 wartości, etap final ze statusem None i done false w results.json, K_build_calls 0 mimo 20 wywołań pisarza w NIGHT-1; WNIOSKI.md nie było w kontekście.",
    "Ograniczenie recenzji: sprawdzono spójność results.json i REPORT.md z regułami; nie przeliczano wyników z surowych sesji, bo nie było ich w kontekście."
  ],
  "requires_owner_decision": true,
  "owner_questions": [
    "Czy potwierdzasz rozstrzygnięcie D17: przy teście głównym obalonym wynik to WRÓCIĆ DO SKŁADNIKÓW, mimo że warunek POPRAWIĆ (K nie przed konkurentami) też jest dosłownie spełniony?",
    "Czy po powrocie do składników bazą mają być notatki po błędzie (TrT: +8, 2 straty), a pamięć sukcesów ma wracać dopiero po ograniczeniu strat? To zmienia definicję v0 ze strategii, więc wymaga Twojej decyzji.",
    "Czy H16 ma w księdze hipotez status wsparta (progi, D12), czy nierozstrzygnięta (odczyt z korektą Holma, p = 0,363)?",
    "Czy kolejne specyfikacje mają obowiązkowo zawierać placebo dla bloku na początku tury, zgodnie ze strategią (sekcja 2)? NIGHT-2 go nie miał.",
    "Czy dla H10 miarodajne jest 88 zadań (K 32 wobec C-G 31), czy 58 zadań spoza VC zgodnie ze strategią 4.2 (K 19 wobec C-G 21), skoro C-G ma w VC wskazówki dla 1 narzędzia?",
    "Czy akceptujesz poprawkę nr 4 (po pierwszym wywołaniu E1) jako nieszkodliwe odstępstwo od SPEC §10, czy ma być odnotowana jako zastrzeżenie przy wynikach E1?",
    "Czy reguła wyboru K ma w przyszłości dopuszczać konfigurację z jednym składnikiem, gdy system złożony przegrywa ze składnikami (zasada 10 strategii)?"
  ],
  "proposed_next_tasks": [
    {
      "agent": "opus",
      "kind": "analysis",
      "title": "Audyt maskowania na zamrożonych danych E1 (bez wywołań modelu)",
      "goal": "Ustalić, czy obalenie H14 dotyczy idei, czy implementacji: dlaczego w blokach M1 i M2 zostały widoczne skopiowane wartości i skąd wzrost invalid_calls.",
      "acceptance": [
        "Tabela 11 strat przez kopię (M2 6, M1 5) z fragmentem bloku, skopiowaną wartością lub funkcją i powodem braku maskowania",
        "Liczba nieprawidłowych wywołań M2 i M1 zawierających dosłowny znacznik w nawiasach ostrych, z przykładami",
        "Jawny wniosek: wada idei, wada implementacji albo nierozstrzygalne z tych danych",
        "Zero wywołań modelu; zamrożone pliki bez zmian (sha256 zgodne z raw-freeze.json); wynik w osobnym pliku eksploracyjnym"
      ]
    },
    {
      "agent": "opus",
      "kind": "analysis",
      "title": "Dossier 10 powtarzalnych strat K (E3 i E4) z pierwszym zepsutym ogniwem",
      "goal": "Dla zadań 83, 22, 152, 151, 183, 191, 181, 165, 182, 163 wskazać pokazany ślad, skopiowany element i klasę według procesu ze strategii (sekcja 6, krok 3).",
      "acceptance": [
        "Wiersz na zadanie: identyfikator pokazanego śladu, skopiowana wartość lub funkcja, tura rozstrzygająca, klasa ogniwa",
        "Zestawienie po śladach źródłowych: ile strat powoduje każdy ślad",
        "Osobno 8 zadań TRAVEL z oceną, czy stratę powoduje treść śladu, czy sama obecność bloku",
        "Zero wywołań modelu; status eksploracyjny; osobny plik"
      ]
    },
    {
      "agent": "sonnet",
      "kind": "analysis",
      "title": "Raport ekspozycji i użycia pamięci dla E3-E5 (uzupełnienie SPEC §5)",
      "goal": "Z zamrożonych sesji wypisać, które ślady i notatki pokazano w każdym ramieniu, oraz sprawdzić dla zysków K, czy pokazany wpis został zastosowany.",
      "acceptance": [
        "Tabela ekspozycji na ramię: liczba tur z blokiem, liczba różnych śladów, notatki według sygnatury",
        "Dla każdego z 18 zysków K w E3 i 16 w E4: pokazany wpis i zgodność wywołań agenta z wpisem (tak, nie, częściowo)",
        "Odsetek zysków z zastosowanym wpisem podany liczbowo",
        "Zero wywołań modelu; REPORT.md i results.json bez zmian"
      ]
    },
    {
      "agent": "fable",
      "kind": "docs",
      "title": "Projekt aktualizacji 3 strategii po NIGHT-2 (do zatwierdzenia przez właściciela)",
      "goal": "Zaktualizować księgę hipotez (H1, H4, H10, H13, H14-H16) i stan składników C3-C6 liczbami z NIGHT-2 oraz przedstawić warianty powrotu do składników, bez zmiany zatwierdzonej strategii.",
      "acceptance": [
        "Każdy status hipotezy z liczbą i wskazaniem pola w results.json lub REPORT.md",
        "Warianty decyzji opisane jako propozycje z listą pytań do właściciela; żadnej zmiany progów ani celu",
        "Wnioski eksploracyjne wyraźnie oddzielone od werdyktów zamrożonych",
        "Dokument jako projekt; istniejące pliki strategii bez zmian"
      ]
    },
    {
      "agent": "sonnet",
      "kind": "docs",
      "title": "Errata do REPORT.md NIGHT-2 (osobny plik)",
      "goal": "Spisać usterki raportu bez modyfikowania zamrożonych wyników: nagłówek tabeli E2, status etapu final, koszt budowy K, brak ekspozycji, niestabilne zadania 81 i 43 w listach strat.",
      "acceptance": [
        "Lista usterek z odwołaniem do sekcji raportu i poprawnym odczytem",
        "sha256 REPORT.md, results.json i raw-freeze.json bez zmian",
        "Żadna pozycja erraty nie zmienia werdyktu ani liczby w tablicach wyników"
      ]
    }
  ],
  "sources": [
    "context/04_SPEC_AAMR_NIGHT2.md",
    "context/08_PROTOCOL.md",
    "context/06_results.json",
    "context/05_REPORT.md",
    "context/09_DONE.json",
    "context/07_raw-freeze.json",
    "context/10_verification.md",
    "context/01_STRATEGIA_AAMR.md",
    "context/02_AKTUALIZACJA_1_NOWE_PUBLIKACJE.md",
    "context/03_AKTUALIZACJA_2_PO_NIGHT1.md"
  ]
}
```