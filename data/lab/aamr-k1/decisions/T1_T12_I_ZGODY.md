# K1: wybory techniczne T1–T12 i zakres zgód D2, D5, D6, D11

2026-11-13. Do zatwierdzenia przez właściciela; **nic z tego nie jest zatwierdzone**.
Dowody offline:
- `tests/WYNIKI_RYZYKA_T.out` (R1–R4);
- `tests/WYNIKI_TESTOW.out` (U0–U12);
- `tests/WYNIKI_RUNNER.out`.

Wartości są zapisane w `code/k1_config.json`, w polach `T` i `technical_choices_unapproved`.

## Stan D1, D3, D7, D12 po Twojej odpowiedzi

W konfiguracji mają status „accepted directionally … final approval at freeze”. Bramka nadzorcza dalej odrzuca prawdziwy model (test U2), bo ostateczne zatwierdzenie przychodzi z zamrożeniem.

**Warunek do D1 jest wpisany w kod raportu.** Każdy raport K1 zaczyna się stałą „ZASADĄ INTERPRETACJI (D1)”: efekty mniejsze niż 10 pp mogą być rzeczywiste i użyteczne, a brak wykazania 10 pp nie jest dowodem braku korzyści. Zasada stoi poza zamrożonym kodem odczytu v0.4, który pozostał bez zmian.

Test U11 sprawdza 729 odczytów, w tym 665 z kontrastem w stanie V3 lub V5. Żaden nie zawiera twierdzenia o braku korzyści, a zasada przechodzi zamrożoną kontrolę zakazanych zwrotów.

## T1–T12

Etap T to wywołania techniczne przed pierwszym wywołaniem eksperymentalnym. Ich wyniki `solved` nie są nigdzie liczone.

| # | Co dokładnie znaczy | Proponowana wartość | Ryzyko | Dowód / mitygacja |
|---|---|---|---|---|
| **T1** | Ziarno epizodów pomiaru `m` (ramię N, temperatura 0,7) w etapie T. Specyfikacja (sek. 10) go nie podaje | 7000 | Pomijalne. Ziarno wpływa tylko na liczbę wywołań w 12 epizodach | Rozłączne z NIGHT (7), K1 (7001–7003) i pilotażem (9001–9002) |
| **T2** | Które 12 zadań treningowych mierzy `m` przed bramką bloku A | 4 na domenę, pierwsze według sha256(„K1-Tm\|id”) | Te 12 zadań przy temperaturze 0 w NIGHT-2 miało średnio **8,92** wywołania na epizod, wobec 9,46 dla N+M na 148 zadaniach (R3). Bramka przed A zaniża więc `m` o około 6%, a zapas 1,10 to pokrywa. Przy 0,7 epizody mogą być dłuższe. Skutek zaniżenia nie przekracza limitu twardego: przed każdym blokiem S bramka przelicza `m` z prawdziwych epizodów, a blok ucięty limitem jest nieukończony (T7). Najgorszy przypadek to mniej bloków, a przy < 2 blokach NIEWAŻNY po wydaniu budżetu | **Opcja T2b (do decyzji):** dolna granica `m` = max(9,6; wywołania na epizod z jawnego raportu pilotażu). Pilot ma to jako miarę jawną. Specyfikacja tej granicy nie przewiduje |
| **T3** | Zadania do kalibracji `c_d` i T-długości (b). Muszą mieć dokładną liczbę tokenów bloku M z NIGHT-2 (147 zadań) | Kolejność sha256(„K1-T\|id”) w domenie: 10 kalibracja, 10 T-długość, 20 rekalibracja, 10 drugie T-długość | Losowa porażka bramki ±5% na 10 blokach. Symulacja (R2): na zamrożonych listach \|rel\| ≤ 3,8% przy każdym założeniu o prozie (0,20–0,29 tokena na znak, szum ±3%). Na losowych podziałach porażka w 0–6% domen | Bramka ±5% to wymóg specyfikacji. Rekalibracja (T4) daje drugą szansę |
| **T4** | Co robi „jedno ponowne wyznaczenie `c_d` na 20 blokach” | Tylko w domenie, która nie przeszła: 20 nowych bloków P (c = 1) → nowe `c_d` → jedno nowe T-długość na 10 kolejnych blokach. Druga porażka → stop, kod 4 (decyzja właściciela) | Budżet T. Najgorszy przypadek przy rekalibracji wszystkich domen: 3 + 6 + 30 + 30 + 90 + ~107 (`m`) ≈ 266 z 300. Jeśli 12 epizodów pomiaru `m` przy 0,7 przekroczy razem ~180 wywołań, limit etapu T zatrzyma program (kod 4) | Limit etapu T = 300 jest w specyfikacji |
| **T5** | Podstawa „tokenów na znak” w `c_d` i D12 | Cały blok + 2 znaki separatora, dla M i P tak samo (jak prototypy v0.4) | Nagłówek (~89 znaków) jest wliczony po obu stronach. Daje to przesunięcie poniżej 2% sumy (R2) | Odtwarza przewidywania specyfikacji: X +1,84%, S +2,24% (spec +1,8 / +2,2) |
| **T6** | Strażnik wiarygodności: tokeny P na znak poza [0,15; 0,6] → stop | jak obok | Za szeroki, żeby złapać subtelne przekłamanie; to tylko druga linia obrony | Pierwszą linią jest T12 |
| **T7** | Limit twardy 30 000 osiągnięty wewnątrz bloku próbkowanego | Blok nieukończony; potem zamrożenie, checker i analiza na ukończonych blokach (sek. 7.2, 10). W T albo A → stop, kod 4 | Wydane wywołania bez wyniku z tego bloku. Przy < 2 blokach NIEWAŻNY | Test U6 (limit w S2 → nieukończony → NIEWAŻNY, bez przekroczenia limitu) |
| **T8** | Drugi wyjątek innego rodzaju niż przejściowy w tym samym bloku próbkowanym | Blok nieukończony, następny blok za bramką. W T albo A → stop, kod 3. Błąd protokołu (HTTP 400), hak i preflight → stop natychmiast | Utrata bloku | Test U5 (1 awaria na blok → wznowienie bez strat) |
| **T9** | Graf wspólnych śladów dla diagnostyki 7.4 i grup WR2 | Definicja v0.3: ślady z tur zapisanych w epizodach M NIGHT-2 → 1 260 par, 68 grup, ρ̂ NIGHT-2 = −0,059 (T-analiza-b, U9). Wariant „wszystkie tury planu” (1 314 par) tylko informacyjnie | Diagnostyka opisowa, nie zmienia stanu głównego. Przy dłuższych epizodach K1 graf może niedoszacować powiązań. Wariant pełny jest ostrożniejszy (2L/n 17,8 wobec 17,0) | Wybór zgodny z liczbami specyfikacji |
| **T10** | `test_sessions` w kontroli przecieków koordynatora | `["S1", "S2"]` | S3 nie jest sprawdzany przez koordynatora. Sprawdzają go: L1/L3 przy przygotowaniu (0/1 022) i kontrola po przebiegu w `analyze.py` (wszystkie bloki, U4: 0/10 220). Wpisanie S3 dałoby fałszywe „fail”, gdyby bramka pominęła S3 | U4: deklaracja pass; złe deklaracje → fail |
| **T11** | „Najwyżej 8 restartów na przebieg” przy wielu uruchomieniach nadzorcy przez runner | Licznik trwały w `meta/state.json`, wspólny dla wszystkich uruchomień | Brak; pilotaż liczył restarty tylko w jednym uruchomieniu | U5 |
| **T12** (nowy) | Kontrola odniesienia tokenów na żywym modelu przed kalibracją `c_d`: dla pierwszego zadania kalibracyjnego każdej domeny prompt ramienia N w turze 0 wysłany dwa razy (`num_predict` 1). Obie liczby `prompt_eval_count` muszą być **równe** wartości z NIGHT-2, inaczej stop (kod 3) | 6 wywołań w budżecie T | Fałszywy stop, jeśli Ollama/model różni się od NIGHT-2 choćby szablonem. To jest celowe: wtedy `c_d` byłoby liczone na złym odniesieniu | R1: w NIGHT-2 liczby były pełne (1 811/1 811 par rośnie z historią; identyczne żądania → równe liczby). U10: atrapa z „cache” → stop przed jakąkolwiek kalibracją, 9 wywołań |

## Czy zgody z pilotażu obejmują pełne K1

Zgody pochodzą z `pilot-nm/ZATWIERDZENIA.md`.

| # | Zatwierdzone w pilotażu | Co robi K1 | Pokrycie |
|---|---|---|---|
| **D2** | temperatura 0,7, top_p 0,8, top_k 20 | Bloki S1–S3: dokładnie ten reżim; `num_ctx` 8192 i `num_predict` 512 jak w pilotażu. Blok A (temperatura 0, seed 7) i wywołania T (`num_predict` 1) wynikają ze specyfikacji, nie z D2 | **Tak, dokładnie** dla reżimu próbkowania |
| **D5** | sesja Opus według wzoru NIGHT-2, wyłącznie lokalna Ollama, katalog poza repozytoriami, bez push | (1) Przebieg uruchamia **wykonawca koordynatora** przez `night_wrapper`, a nie sesja ani ręczne polecenie. (2) Katalog `[machine-local path omitted]` jest **bez git**; specyfikacja (sek. 1) mówi o commitach lokalnych na nowej gałęzi, zamiast tego jest manifest L8. (3) Etap T proponuję uruchomić ręcznie (`--stop-after-T`) | **Nie w pełni.** Status w konfiguracji: wymaga potwierdzenia. Do decyzji: zgoda na runner koordynatora oraz git lokalny albo manifest |
| **D6** | 148 zadań (88 + 60) | Te same zadania. Bodźce K1 (zadania, plany M, pule) są **identyczne** z zamrożonymi bodźcami pilotażu (R4). WR4 na 88 zadaniach zaimplementowane | **Tak, dokładnie** |
| **D11** | hak audytu, `BfclK1` bez odpowiedzi wzorcowych, plany i pule z kontrolą L10 | K1 dodaje elementy spoza tej listy (patrz niżej) | **Częściowo.** Status w konfiguracji: wymaga potwierdzenia |

Elementy D11, które K1 dodaje ponad zgodę z pilotażu:
- (a) listy L4a dla korpusu P;
- (b) brak techniczny ze statusu checkera; pilotaż też go używał, ale nie był wymieniony w zgodzie;
- (c) proces losowań pod hakiem czyta `responses.jsonl` z NIGHT-2. Bierze z niego tylko `prompt_eval_count` tury 0, bez odpowiedzi wzorcowych;
- (d) przygotowanie czyta z sesji NIGHT-2 tylko `memory.items` ramienia M (graf T9);
- (e) wywołania T12.

Skutek w kodzie: D5 i D11 mają teraz status bez „approved”, więc nadzorca odrzuci prawdziwy model, dopóki nie potwierdzisz ich dla K1.
