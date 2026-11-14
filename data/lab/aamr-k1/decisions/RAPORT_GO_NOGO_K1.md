# K1: raport GO / NO-GO

> **Aktualizacja:** D5 i D11 zatwierdzone. T1–T12 częściowo wstrzymane: kontrola zgodności z v1.0 wykryła rozbieżności C1–C4. Szczegóły i warianty: `DZIENNIK_DECYZJI_K1.md`.

2026-11-13, Claude (Opus 5.5).

Tryb pracy:
- czytałem tylko jawny raport pilotażu (`report/RAPORT_PILOTAZ_NM.md`, `report/public.json`); **`sealed/` nie otwierałem**;
- nie było wywołań Ollamy ani modelu;
- runner i konfiguracja koordynatora bez zmian (`git status` w `[machine-local path omitted]` czysty);
- zamrożonego protokołu nie zmieniałem.

## Werdykt: **NO-GO teraz, wyłącznie formalnie**

Technicznie nic nie blokuje startu. Wykonawca jest zgodny z K1 v1.0 i przechodzi komplet testów z sek. 6.3.

Start blokują:
- brakujące zgody (wykaz niżej);
- kroki konfiguracji koordynatora, które należą do właściciela.

Po ich udzieleniu werdykt brzmi **GO**, z etapem T jako pierwszym punktem kontrolnym (`CHECKLISTA_STARTOWA_K1.md`, sekcja D).

Wykonawca egzekwuje to sam. Nadzorca z prawdziwym modelem kończy się kodem 3 z listą braków: D5, D11 i T1–T12 (test U2).

## 1. Spójność decyzji z jawnym raportem N/M

| Decyzja | Co mówi raport pilotażu | Ocena |
|---|---|---|
| D8 = pełne K1 | Protokół pilotażu: zamrozić K1, gdy wykrycie 10 pp ≥ 40%. Raport: 63,0% (`recommendation: freeze K1…`), v1.0: 64,3%. W najgorszym narożniku 95% szumu 41% | **spójna**; margines w najgorszym narożniku minimalny |
| D4 = 3 bloki | 3 bloki: wykrycie 64% / wykluczenie 62%; 2 bloki: 57% / 55% | **spójna** (3 bloki lepsze o 6–7 pp) |
| D4 a budżet | 9,51 wywołania na epizod przy 0,7 (sd 3,3). Prognoza K1: ≈ 25 600 z 30 000 (85%). Bramka A potrzebuje ≈ 20 400. S3 wypadnie dopiero, gdy ramiona próbkowane mają średnio > 11,1 wywołania na epizod (+17% wobec N/M) | **spójna**; ryzyko: dłuższe epizody X i S nie były mierzone (sek. 10 v1.0) |
| D4 a czas | 1,44 s na wywołanie (pilotaż) → ≈ 10,2 h; `max_hours` runnera = 14 | **spójna** |
| D1 = 10 pp | Wykluczenie 10 pp przy braku efektu 62%; przy 8 pp tylko 41%. Zasada interpretacji właściciela jest w każdym raporcie (U11) | **spójna** |
| D3, D7 | 3 kontrasty przy 98,33%: 64/62. Alternatywy (2 kontrasty, 95%) mają wyższą moc kosztem kontroli łącznego błędu | **spójna** z rekomendacją |
| D12 | Pilotaż jej nie dotyczy. Dopasowanie liczone na zamrożonych bodźcach: X +1,84%, S +2,24% (spec +1,8 / +2,2) | **spójna** |
| D2 | `w` = 0,159 > 0: powtórzenia przy 0,7 się różnią, więc reżim ma sens (obawa z D2 dotyczyła `w` ≈ 0 przy 0,3) | **spójna** |
| Środowisko | Bramka D0: 20/20 i 20/20 zgodnych wyników; 20/20 i 19/20 identycznych pierwszych odpowiedzi; Ollama 0.40.16, skrót modelu zgodny; 0 błędów technicznych; 0 nieprawidłowych wyjść; 10,5% epizodów kończy limit kroków (w K1 liczone jako 0, sek. 7.1) | **spójne**; ta sama Ollama i model są warunkiem T12 |

Zastrzeżenie (jest też w v1.0, sek. 9.0): `b` zmierzono między M i N. Niezgodność M z P, X i S może być inna, więc moc 64% to przybliżenie.

## 2. K1 v1.0 a konfiguracja wykonawcy

| Pozycja | Stan |
|---|---|
| Zamrożenie | `k1/v1.0/SPEC_K1_PLACEBO_v1.0.md`, sha256 `e585ed8d…dd38df`, zgodne z `FREEZE.json` (19:29:44 UTC) |
| Kopia w katalogu wykonawczym (v1.0, sek. 6.1) | `spec/SPEC_K1_PLACEBO_v1.0.md`, bajt w bajt (ten sam sha). `k1_config.json`: `spec` → kopia, `spec_frozen_sha256` = `e585…`. Sprawdzane przy starcie (nadzorca) i w manifeście L8. **Było rozbieżne; poprawione** |
| Prototypy w `FREEZE.json` | `k1_audit_hook.py`, `k1_l4.py`, `k1_length.py`, `k1_v04_reading.py`, `t_w6_cells.py` w wykonawcy mają **identyczne** sha jak w `FREEZE.json` |
| Treść v1.0 a v0.4 | Zmiany 12–17 (L10, hak, WR5/LEN, D12, moc przy zmierzonym szumie, decyzje). Wszystkie były już zaimplementowane; brak zmian reguł ramion, stanów, progów, ziaren i budżetu |
| Decyzje w `k1_config.json` | D1, D3, D4, D7, D8, D12: `approved 2026-11-13`. D2, D6, D9, D10: przyjęte wcześniej. **D5, D11: czekają na potwierdzenie dla K1.** `technical_choices_approved: false` |
| Wymogi v1.0 sprawdzone w kodzie | A: N, M, P przy temperaturze 0, seed 7. S1–S3: 0,7 / 0,8 / 20, seed 7001–7003. `num_ctx` 8192, `num_predict` 512, limit 30 000, bramki sek. 10, odczyt kodem v0.4, WR1–WR5, LEN, ρ̃/ρ*, NIEWAŻNY od 8 wykluczeń |

## 3. Rozbieżności (wszystkie wykryte; stan po tej sesji)

| # | Rozbieżność | Czy blokowała start | Stan |
|---|---|---|---|
| R1 | Konfiguracja wykonawcy wskazywała v0.4 bez skrótu, a v1.0 wymaga kopii bajt w bajt sprawdzanej przy starcie | tak (odmowa prawdziwego modelu) | **poprawione** |
| R2 | **Szablon integracyjny** (`[machine-local path omitted]`) zawiera tylko `[[experiments]]` K1. `load_config` łączy plik `.local.toml` przez `deep_merge`, który **zastępuje listy**, więc NIGHT-1 i NIGHT-2 znikają z konfiguracji. Sprawdzone na kopii konfiguracji: bez pliku lokalnego [NIGHT-1, NIGHT-2]; z szablonem [K1]; z poprawionym wpisem [NIGHT-1, NIGHT-2, K1] | nie blokowało K1, ale cicho psuło koordynator | **poprawione** w `integration/k1.coordinator.local.toml` (NIGHT-1 i NIGHT-2 powtórzone bez zmian). **Nie używać szablonu z pakietu** |
| R3 | Brakowało testów z sek. 6.3 na prawdziwym kodzie: T-analiza-a, mutant T-zgodności, T-budżet (Monte Carlo), negatywne przypadki T-pochodzenia | tak (sek. 6.3: testy przed startem) | **dodane**: U13 (66,3% / 61,1% wobec 64,6% / 61,8% symulacji), U3 (mutant: 359 żądań niezgodnych), U14 (0 przekroczeń 30 000), U15 (6/6 kontroli negatywnych) |
| R4 | Raport nie miał pozycji z sek. 11 pkt 1, 7 i 8 (kontrole przygotowania, flaga tokenów ±10%, rozkład P/M, S/M i X/M, porównanie z szumem z 9.0) | tak (raport musi być zamrożony przed startem) | **dodane** |
| R5 | `DECYZJE_DO_ZAMROZENIA.md` i v1.0 sek. 13 zapisują D5 i D11 jako zatwierdzone. Zatwierdzenie pochodziło jednak z pilotażu, a K1 różni się w obu punktach (sekcja 4) | tak, do potwierdzenia | **otwarte**: zgoda właściciela |
| R6 | Wybory techniczne T1–T12 nie są w v1.0. Sek. 6.4 dopuszcza poprawki techniczne „z wpisem w protokole” | tak | **otwarte**: zgoda i wpis w protokole (sekcja 5) |
| R7 | `[machine-local path omitted]` nie istnieje; K1 nie jest w rejestrze (`lab propose`/`admit`); `[runner] enabled = false` | tak | **otwarte**: kroki właściciela (checklista, sekcja E) |
| R8 | Zadanie Harmonogramu AAMR-NIGHT2 (pamięć projektu: usunąć przed przebiegiem bez nadzoru) | — | **już usunięte**; jest tylko AAMR-COORDINATOR. Procesy pilotażu nie działają |
| R9 | `zamroz.py` drugiej sesji uruchomił `k1/v0.4/testy/run_all.py`, który nadpisał pliki `*.out` w v0.4 (21:29). Skróty nowych wyników są w `FREEZE.json` | nie | do odnotowania; bez wpływu na K1 |

## 4. Ostateczne propozycje zgód D5 i D11 dla K1

**D5 (wykonawca i środowisko).** Proponowane brzmienie zgody:

> K1 wykonuje kod z `[machine-local path omitted]` (poza repozytoriami), wyłącznie z lokalną Ollamą (`qwen2.5:14b-instruct`, sha `7cdf5a01…`), bez płatnych API i bez push. Etap T uruchamiam ręcznie (`--stop-after-T`). Bloki A i S1–S3 uruchamia wykonawca koordynatora (`aamr_coord.lab.runner`) przez `night_wrapper.py`, na podstawie wpisu `integration/k1.coordinator.local.toml` dopisanego jako `[machine-local path omitted]`. Wpis jest „własnym zadaniem programu” w rozumieniu sek. 1 i zostaje wyłączony (`enabled = false`) po zakończeniu. Katalog wykonawczy nie używa git; integralność zapewnia manifest L8 (sha256 kodu, bodźców, konfiguracji, korpusu, specyfikacji i plików startowych) sprawdzany przy każdym starcie, oraz `pin` runnera.

Rzeczywiste konsekwencje:
- koordynator dostaje prawo uruchamiania K1 bez nadzoru przez około 10 h, z limitami 6 uruchomień i 14 h;
- bez git nie ma historii zmian kodu; manifest wykrywa zmianę, ale nie pokazuje różnic.
- Alternatywa: `git init` lokalnie i jeden commit przed startem (sek. 1 dopuszcza commity lokalne). Drobna i bezpieczna; mogę to zrobić na Twoje polecenie.

**D11 (kontrole techniczne).** v1.0 obejmuje: hak L6a, `BfclK1`, L10, listy L4a, brak techniczny ze statusu checkera. Proponowane brzmienie uzupełnienia:

> Zatwierdzam dla K1 dodatkowo:
> (a) proces losowań X/S pod hakiem L6a z listą odczytu rozszerzoną o `NIGHT-2 run/responses.jsonl`. Używane jest wyłącznie `usage.prompt_eval_count` tury 0 ramion N i M, potrzebne dla `c_d` i D12 zgodnie z sek. 2; plik nie zawiera odpowiedzi wzorcowych, a linie TradingBot są odrzucane przed parsowaniem;
> (b) przygotowanie (proces weryfikujący bez haka, jak w pilotażu) odczytuje z sesji NIGHT-2 wyłącznie `memory.items` ramienia M, aby zbudować graf wspólnych śladów 7.4 w definicji v0.3 (1 260 par, 68 grup WR2);
> (c) kontrolę T12 w etapie T.

Rzeczywiste konsekwencje:
- (a) i (b) nie dają procesowi epizodów żadnego nowego dostępu. Proces epizodów czyta tylko `stim/`, a próby odczytu odpowiedzi, sesji i `responses.jsonl` kończą się kodem 97 (U2);
- (c) dodaje 6 wywołań i warunek zatrzymania.

Bez (a) `c_d` i D12 nie mają danych wejściowych. Bez (b) diagnostyka 7.4 nie odtwarza liczb specyfikacji (T-analiza-b).

## 5. T1–T12: rzeczywiste konsekwencje

Szczegóły i dowody: `T1_T12_I_ZGODY.md`. Po zatwierdzeniu: `technical_choices_approved: true` w `k1_config.json`, ponowne `prepare.py` (nowy manifest) i testy. Wpis w protokole (sek. 6.4) stanowi ten raport razem z `T1_T12_I_ZGODY.md`.

| # | Wartość | Co realnie zmienia w przebiegu | Najgorszy skutek | Rekomendacja |
|---|---|---|---|---|
| T1 | ziarno 7000 pomiaru `m` | tylko liczba wywołań 12 epizodów etapu T | brak | przyjąć |
| T2 | 12 zadań treningowych (4 na domenę) | `m` dla bramki przed A. Te zadania przy temperaturze 0 dawały 8,92 wobec 9,46 średnio (−6%, zapas 1,10). Pilotaż: 9,51 przy 0,7 | Bramka A przepuszcza przebieg, który potem nie zmieści S3; wtedy analiza na 2 blokach (moc 57% zamiast 64%) | przyjąć bez T2b (dolnej granicy `m`): przy zmierzonych 9,5 bramka ma duży zapas |
| T3 | listy zadań kalibracji i T-długości (kolejność sha256) | które bloki P mierzą tokeny | Fałszywa porażka T-długości: offline ≤ 3,8% na zamrożonych listach (próg 5%) | przyjąć |
| T4 | rekalibracja na 20 nowych blokach, potem drugie T-długość | do +90 wywołań T | Stop kodem 4 przed blokiem A (bez wydatku eksperymentalnego) | przyjąć |
| T5 | tokeny na znak liczone na całym bloku + 2 znaki | sposób liczenia `c_d` i D12 | < 2% przesunięcia sumy | przyjąć |
| T6 | strażnik 0,15–0,6 tokena na znak | dodatkowy stop w T | fałszywy stop praktycznie niemożliwy | przyjąć |
| T7 | limit twardy w bloku S → blok nieukończony, analiza dalej | zachowanie przy wyczerpaniu budżetu | NIEWAŻNY, gdy zostaje < 2 bloki | przyjąć (zgodne z sek. 7.2, 10) |
| T8 | drugi błąd w bloku S → blok nieukończony; w T lub A → stop | zachowanie przy awariach | utrata bloku | przyjąć |
| T9 | graf 7.4 z tur zapisanych w NIGHT-2 | tylko diagnostyka przenoszalności i WR2 | diagnostyka może niedoszacować powiązań (wariant pełny: 1 314 par) | przyjąć (odtwarza liczby specyfikacji) |
| T10 | `test_sessions = ["S1","S2"]` | zakres kontroli przecieków koordynatora | S3 sprawdza tylko kontrola po przebiegu w analizie | przyjąć |
| T11 | licznik restartów trwały między uruchomieniami | limit 8 restartów obejmuje cały przebieg | wcześniejszy stop przy wielu awariach | przyjąć |
| T12 | 6 wywołań odniesienia tokenów | stop, jeśli `prompt_eval_count` ≠ NIGHT-2 | Stop przed kalibracją, gdy Ollama lub szablon się zmieniły. Celowe, bo inaczej `c_d` byłoby błędne | przyjąć |

## 6. Testy (stan końcowy, bez modelu)

| Zestaw | Wynik |
|---|---|
| `tests/WYNIKI_TESTOW.out` | **16/16 PASS** (U0–U15, 272 s). Pokrywa wszystkie testy z sek. 6.3 osiągalne offline. Wyjątek: T-długość (b), która z definicji wymaga modelu i jest w etapie T |
| `tests/WYNIKI_RYZYKA_T.out` | **4/4 PASS** (R1 pełne liczby tokenów w NIGHT-2; R2 T-długość; R3 reprezentatywność `m`; R4 bodźce K1 = bodźce pilotażu) |
| `tests/WYNIKI_RUNNER.out` | **2/2 PASS**: prawdziwy `aamr_coord.lab.runner` w izolowanym świecie testowym. DONE, przecieki pass (88 testowych, 0 pokrycia); manipulacja bodźcem → STOPPED kodem 3, jedno uruchomienie |
| `base/` | przygotowany ponownie po wszystkich zmianach; manifest L8 bez różnic |

## 7. Wykaz brakujących zgód (do GO)

| # | Zgoda | Kto | Skutek w kodzie |
|---|---|---|---|
| 1 | **D5 dla K1** w brzmieniu z sekcji 4 (runner koordynatora, ręczny etap T, brak git albo `git init`) | właściciel | status D5 → `approved…` w `k1_config.json` |
| 2 | **D11 dla K1**: uzupełnienia (a), (b), (c) z sekcji 4 | właściciel | status D11 → `approved…` |
| 3 | **T1–T12** jako poprawki techniczne sek. 6.4 (bez T2b) | właściciel | `technical_choices_approved: true` → ponowne `prepare.py` i testy |
| 4 | Start etapu T na prawdziwym modelu (`--stop-after-T`); tylko wywołania techniczne, ≤ 300 | właściciel | checklista, sekcja D |
| 5 | Decyzja po etapie T: kontynuować do bloku A | właściciel | — |
| 6 | Utworzenie `[machine-local path omitted]` z `integration/k1.coordinator.local.toml` (**nie** z szablonu pakietu) | właściciel | zmiana konfiguracji produkcyjnej |
| 7 | `lab propose` (`integration/k1.lab-propose.json`) i `lab admit K1` | właściciel | rejestr koordynatora |
| 8 | `runner check` = SPEŁNIONE, potem `[runner] enabled = true` | właściciel | start bloków A i S1–S3 |

Punkty 1–3 mogę wpisać do konfiguracji wykonawcy, gdy je potwierdzisz. Punkty 4–8 wykonujesz Ty albo wyraźnie mi je zlecasz.
