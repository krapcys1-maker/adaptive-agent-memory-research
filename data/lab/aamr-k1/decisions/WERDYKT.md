# K1: werdykt pakietu wykonawczego

2026-11-13. Claude (Opus 5.5).

## Werdykt: **READY FOR FREEZE**

Ten werdykt dotyczy **kodu i bodźców**, nie zgody na start. Wykonawca pięciu ramion działa i przechodzi wszystkie testy offline. Żadna otwarta decyzja nie blokuje implementacji, bo każda jest parametrem z wpisaną rekomendacją. Wyjątek: wariant „2 kontrasty” w D3 wymagałby zmiany zamrożonego kodu odczytu v0.4.

Samo zamrożenie i start czekają na właściciela:
- **D8** po raporcie pilotażu N/M;
- **D1, D3, D4, D7, D12**;
- potwierdzenie D2, D5, D6 i D11 dla K1;
- przyjęcie wyborów technicznych T1–T11.

Szczegóły: `DECYZJE_BRAKUJACE.md`. Do tego czasu nadzorca **odmawia prawdziwego modelu** kodem 3 (test U2). Protokołu nie zamroziłem.

## Testy (bez modelu, Ollamy, GPU, sieci i płatnych API)

`tests/WYNIKI_TESTOW.out`: **13/13 PASS** (U0–U12, 269 s). `tests/WYNIKI_RUNNER.out`: **2/2 PASS**. `tests/WYNIKI_RYZYKA_T.out`: **R1–R4 PASS**.

| Test | Wynik |
|---|---|
| U0 prototypy | 5 modułów v0.4 bajt w bajt; ich testy własne (T-stan, T-odczyt, T-komórki) PASS |
| U1 przygotowanie | 148 zadań; L10: 114 wierszy puli, 520/520 kluczy planów odtworzonych pod hakiem; korpus P 199 zdań, 0 błędów L4a; L1: 0 naruszeń na 1 022 źródłach w M, X1–3, S1–3; L2 wykrywa podłożone ślady; L3: 0; L4b maks. 0,020 (próg 0,05); odchylenie P od celu ≤ 6 znaków (próg 12); nagłówki 0 błędów; przewidywana nierównowaga z D12: X +1,84%, S +2,24% (specyfikacja +1,8 / +2,2) |
| U2 przypadki negatywne | L4a zatrzymuje 10/10 podłożonych zdań; hak → 97 dla odpowiedzi wzorcowych, `exposure.json`, sesji i odpowiedzi NIGHT-2, katalogu `eval/`, obcego adresu i podprocesu (także w procesie losowań); bramki: P_A 4 689 i P_S 7 815 przy `m` 9,6, stop powyżej `m` 14,0; manipulacja bodźcem → kod 3 bez katalogu `run/`; prawdziwy model bez zgód → kod 3 |
| U3 T-zgodność | blok A, N i M odtworzone z odpowiedzi NIGHT-2: 2 796 żądań identycznych bajt w bajt + 4 identyczne po normalizacji nazwy instancji, 0 brakujących (jak W1) |
| U4 pełny przebieg na atrapie | T → A (444) → S1–S3 (3 × 740) → zamrożenie → checker → analiza → raport; 18 857 wywołań; dziennik postępu bez wyników (L7); P bez źródeł; kontrola przecieków po przebiegu 0/10 220; kontrola przecieków koordynatora: pass, a przy złej deklaracji fail |
| U5 wznowienia | awaria w każdym bloku → 4 restarty, 0 powtórzonych lub zgubionych epizodów, odczyt identyczny jak bez awarii |
| U6 bramki | stop przed A (kod 4, bez wydatku); S3 pominięty przez bramkę → analiza na 2 blokach; limit twardy w S2 → blok nieukończony, < 2 bloki → NIEWAŻNY |
| U7 wrapper koordynatora + atrapa runnera | DONE.json i raw-freeze.json; idempotencja; STOPPED.json z kodem 3 i 4; awaria → wznowienie bez znaczników |
| U8 analiza syntetyczna | +30 pp → V1 we wszystkich kontrastach i zdanie B; brak efektu → V4/V5 i zdanie C; 7 wykluczeń ważne, 8 → NIEWAŻNY; 0 zakazanych zdań |
| U9 T-analiza-b | NIGHT-2: 22/12 i 11/9; 1 260 par; ρ̂ −0,059; średnia permutacyjna −0,041; ρ̃ −0,018 (jak w specyfikacji) |
| U10 T12 | 6 wywołań odniesienia równe; atrapa z „cache” → stop kodem 3 przed kalibracją (9 wywołań) |
| U11 zasada D1 | 729 odczytów bez twierdzeń o braku korzyści; zasada w raporcie |
| U12 `--stop-after-T` | etap T ręcznie, potem polecenie runnera kończy przebieg identycznie jak bez przerwy; istniejący lock → odmowa |
| Runner koordynatora | K1 pod prawdziwym `aamr_coord.lab.runner` w izolowanym świecie testowym: DONE, RUN_REPORT, przecieki pass (88 testowych, 0 pokrycia); manipulacja → STOPPED kod 3, jedno uruchomienie |

## Aktualizacja po odpowiedzi właściciela (2026-11-13)

- D1, D3, D7, D12 przyjęte kierunkowo (status w konfiguracji; bramka dalej zamknięta). Warunek do D1 w raporcie (U11).
- D5 i D11 nie pokrywają K1 w pełni; zmienione na „do potwierdzenia” (`T1_T12_I_ZGODY.md`).
- Nowe: T12 (kontrola odniesienia tokenów na żywym modelu), `--stop-after-T` (punkt kontrolny właściciela), `CHECKLISTA_STARTOWA_K1.md`.

## Znaleziska w trakcie pracy (naprawione)

1. **Heartbeat a runner na Windows.** `os.replace` na `heartbeat.json` kończy się `WinError 5`, gdy runner koordynatora czyta ten plik. Proces roboczy padał, a drugi taki błąd zatrzymywał przebieg. Teraz zapis heartbeat ma ponowienia i nigdy nie przerywa procesu.
   - Kod pilotażu ma ten sam wzorzec. Działa ręcznie, bez runnera, więc go nie dotyczy, ale ma znaczenie, jeśli kiedyś trafi pod runner.
2. **Graf wspólnych śladów (7.4).** Liczby ze specyfikacji (1 260 par, ρ̂ −0,059, 68 grup WR2) wynikają z tur zapisanych w epizodach M NIGHT-2, nie ze wszystkich tur planu (1 314 par). Zamroziłem definicję v0.3; to wybór T9.
3. **Test zgodności.** Gdy blok M w turze jest pusty, żądania N i M są identyczne, a NIGHT-2 ma dla nich różne odpowiedzi. Odtwarzam więc każde ramię osobno. To był błąd testu, nie wykonawcy.

## Ograniczenia, których testy nie pokrywają

- **Etap T z prawdziwym modelem.** Nie sprawdziłem `c_d`, T-długości (b) ani `m` na prawdziwym modelu. Atrapa liczy znaki JSON zamiast tokenów, więc w atrapie M − P ma nierównowagę +21,8%. Reguła LEN ją poprawnie oznacza; to cecha atrapy.
  - Przy prawdziwym modelu `prompt_eval_count` mogłoby obejmować tylko część promptu nieobjętą cache. Wtedy strażnik T6 zatrzyma program przed blokiem A.
- **Atrapa nie rozwiązuje zadań.** Stany kontrastów sprawdzono na wynikach syntetycznych (U8), a dryf bloku A tylko mechanicznie.
- **Miara L9 dla S** wynosi 12,6% zamiast 11,1% ze specyfikacji. Wartość ze specyfikacji liczono dla losowań bez D12; to miara opisowa.
- **Wariant D3 „2 kontrasty”** nie jest zaimplementowany (patrz wyżej).
