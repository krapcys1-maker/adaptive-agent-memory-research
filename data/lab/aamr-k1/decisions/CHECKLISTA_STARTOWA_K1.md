# K1: checklista startowa

> **Stan (K1 v1.0.1):** sekcje A–C wykonane (`tools/pre_T_check.py`: READY). Następny krok: sekcja D po osobnej zgodzie właściciela; ocena wyników etapu T: `python -I -X utf8 -B tools/review_T.py`.

Kolejność jest obowiązkowa. Kroki oznaczone **[W]** wykonuje albo zatwierdza właściciel.
Wszystkie polecenia uruchamia się z katalogu podanego przy nich.
`PY` = `[machine-local path omitted]`.

## A. Decyzje (przed zamrożeniem)

- [ ] **[W]** Pilotaż N/M zakończony: w `pilot-nm/run` jest `C2_DONE.json` albo stan końcowy w `meta/state.json`, a raport `report/RAPORT_PILOTAZ_NM.md` jest przeczytany. **`sealed/` pozostaje zamknięty.**
- [ ] **[W]** D8 (czy K1) i D4 (2 albo 3 bloki), podjęte na podstawie jawnych `w`, `b` i liczby wywołań na epizod.
- [ ] **[W]** Ostateczne zatwierdzenie D1 = 10 pp, D3 = 3 kontrasty, D7 = 98,33%, D12 = dopasowanie długości (dziś przyjęte kierunkowo).
- [ ] **[W]** Potwierdzenie D5 i D11 dla K1 w zakresie z `T1_T12_I_ZGODY.md` (runner koordynatora, brak git i manifest L8, dodatkowe odczyty NIGHT-2, T12).
- [ ] **[W]** T1–T12 przyjęte albo zmienione; opcja T2b (dolna granica `m`) rozstrzygnięta.

## B. Zamrożenie

- [ ] **[W]** Kopia specyfikacji z decyzjami (np. `k1/v0.5/SPEC_K1_PLACEBO_v0.5.md`) i jej sha256.
- [ ] `code/k1_config.json`:
  - `spec` wskazuje kopię;
  - `spec_frozen_sha256` = jej sha256;
  - statusy D1–D12 = `approved …`;
  - `sampled_blocks` = wynik D4.
- [ ] `PY -I -X utf8 -B code/prepare.py --base [machine-local path omitted]` daje `PREPARED`, bez `FAILED`.
- [ ] `PY -I -X utf8 -B tests/run_tests.py` daje `PASS` dla U0–U15.
  - Test U2 sprawdza, że odmowa wymienia dokładnie decyzje bez statusu `approved…` (i T1–T12, dopóki niezatwierdzone); po wszystkich zgodach odmowa znika, a U2 nadal przechodzi.
- [ ] Test runnera: `tests/test_coordinator_runner.py` daje 2 passed (polecenie w nagłówku pliku).
- [ ] `PY -I -X utf8 -B tests/t_risks_T.py` daje `PASS`.
- [ ] Po tym punkcie żadnych zmian w `code/`, `base/stim/`, korpusie ani specyfikacji. Każda zmiana zatrzymuje nadzorcę (L8, kod 3) albo runner (`pin`).

## C. Środowisko przed etapem T

- [ ] Nadzorca pilotażu zakończony: żaden proces `python` z `pilot-nm` w linii poleceń.
- [ ] GPU wolne:
  - `ollama ps` pokazuje pustą listę; jeśli trzeba, `ollama stop qwen2.5:14b-instruct`;
  - `nvidia-smi` pokazuje poniżej 2 000 MiB zajętej pamięci.
- [ ] Wersja Ollamy zapisana w notatce (pilotaż: 0.40.16). Inna wersja nie jest błędem, ale T12 sprawdzi zgodność tokenizacji z NIGHT-2.
- [ ] Komputer nie zaśnie przez około 11 h; dysk ma co najmniej 5 GB wolnego miejsca.
- [ ] Żadna inna sesja nie używa Ollamy.

## D. Etap T na prawdziwym modelu (ręcznie, punkt kontrolny właściciela)

Polecenie (katalog `[machine-local path omitted]`):
```
PY -I -X utf8 -B supervisor.py --base [machine-local path omitted] --transport ollama --stop-after-T
```

Ten tryb wykonuje tylko wywołania techniczne: 3 próby transportu, 6 wywołań T12, 60–150 wywołań kalibracji i T-długości oraz około 107 wywołań pomiaru `m`, łącznie ≤ 300. Zajmuje około 5–10 min. Trzyma `run/supervisor.lock`, więc runner nie wystartuje równolegle. Kończy się kodem 0 i nie startuje bloku A.

**Sprawdzenie wyników (wszystkie pliki w `base/run/`):**

| Plik | Kryterium przejścia | Kod tego pilnuje? |
|---|---|---|
| `T.json` | `status = done`; 3 próby `ok`; `digest_ok`; `gpu_full`; brak `thinking_present` | tak (stop kodem 3) |
| `c_d.json → ref_check` | 6 wpisów, `prompt_eval_count == reference` w każdym (T12) | tak (stop kodem 3, `T_ref_FAILED.json`) |
| `c_d.json → domains.*.rho_P` | tokeny prozy na znak w [0,15; 0,6]; oczekiwane ~0,20–0,30 | zakres tak (T6); wartość oczekiwana do oceny |
| `c_d.json → c_d` | Oczekiwane około 0,8–1,5 (VC ~0,29/ρ_P, GFS ~0,25/ρ_P, TRAVEL ~0,30/ρ_P). Wartość poza tym zakresem to sygnał do przyjrzenia się, nie błąd | nie; ocena właściciela |
| `c_d.json → domains.*.T_length_rel` | \|rel\| ≤ 5% (albo `pass_after_recal`); offline oczekiwane ≤ 3,8% | tak (stop kodem 4) |
| `P_check.json` | `pass`; `L4b_max` ≤ 0,05; `header_failures` 0; `max_len_dev` ≤ 12 | tak (stop kodem 3) |
| `STIM_T_FROZEN.json` | istnieje; zamraża `c_d.json` i sha bloków P | tak |
| `T_m.json → mean` | Liczba wywołań na epizod. Dla porównania: te 12 zadań w NIGHT-2 przy temperaturze 0 miało 8,92, a pilotaż (jawny raport) poda wartość przy 0,7 | nie; wpływa na bramkę A |
| `attempts.jsonl` | ≤ 300 wierszy z `"bucket": "T"` | tak (limit etapu T, kod 4) |

- [ ] **[W]** Decyzja: kontynuować do bloku A albo zatrzymać.
  - Przy prognozie `m` z `T_m.json` bramka A przepuszcza do `m` ≈ 14,0.
  - Prognoza całości to około 2 960 × `m` wywołań plus etap T; przy `m` = 9,6 daje to około 28 400 przy limicie 30 000.
- [ ] Po etapie T **nie** zmieniać niczego w `base/`. Pliki etapu T są częścią surowych danych przebiegu.

## E. Start bloków A i S pod runnerem koordynatora

- [ ] **[W]** Dopisanie `integration/k1.coordinator.local.toml` do `[machine-local path omitted]`; `<K1_SPEC_FROZEN>` uzupełnione w `spec` i `pin`.
- [ ] **[W]** `integration/k1.lab-propose.json` z uzupełnionym `protocol_path`, potem (katalog `[machine-local path omitted]`):
  - `python -m aamr_coord lab propose --file …`;
  - `python -m aamr_coord lab admit K1`.
- [ ] `python -m aamr_coord runner check` zwraca „warunki startu: SPEŁNIONE”.
- [ ] **[W]** `[runner] enabled = true`. Przy następnym ticku runner uruchamia wrapper i nadzorcę bez `--stop-after-T`. Nadzorca widzi `T_DONE.json` i przechodzi do bramki przed A (test U12).

## F. W trakcie przebiegu (bez zaglądania w wyniki)

- Wolno patrzeć na:
  - `run/heartbeat.json` (etap, liczba epizodów, wywołania);
  - `run/progress.log` (same liczniki);
  - `run/gate_*.json`, `meta/state.json` (restarty, błędy na blok);
  - `meta/supervisor.log`.
- Nie otwierać `eval/` ani nie liczyć wyników z `run/sessions/` przed `report/` (L7).
- Czas: około 10 h przy 1,4 s na wywołanie. Runner zatrzymuje przebieg po 14 h (`max_hours`).

## G. Procedura bezpiecznego zatrzymania

Gwarancje zapisu danych:
- każdy epizod jest dopisywany z `fsync` do `run/sessions/<blok>.jsonl`;
- każda odpowiedź modelu trafia do `responses.jsonl`, zanim epizod się zakończy;
- po przerwaniu tracony jest najwyżej bieżący epizod. Wznowienie odtwarza zapisane odpowiedzi tego epizodu i dokończy go tym samym kodem (test U5).

**G1. Zatrzymanie tylko K1, z możliwością wznowienia** (zalecane):
1. Katalog `[machine-local path omitted]`: `python -m aamr_coord pause --reason "K1: …"`. Runner nie uruchomi już niczego nowego.
2. PID z `[machine-local path omitted]` (to wrapper), potem `taskkill /PID <pid> /T /F`. Polecenie zatrzymuje wrapper, nadzorcę i proces roboczy, ale nie dotyka Ollamy ani pilotażu.
3. Zwolnienie GPU (opcjonalnie): `ollama stop qwen2.5:14b-instruct`.
4. Stan: brak `DONE.json` i `STOPPED.json`, dane zachowane.
   - Wznowienie: `python -m aamr_coord resume`; runner uruchomi nadzorcę ponownie, licząc kolejne uruchomienie (limit 6).
   - Restarty procesu roboczego nadzorca liczy dalej w `meta/state.json` (limit 8).

**G2. Zatrzymanie awaryjne całego koordynatora** (także agentów):
- `python -m aamr_coord stop --reason "…"` albo utworzenie pliku `[machine-local path omitted]`;
- koordynator zabija drzewo procesów K1 przy następnym ticku i blokuje wznowienia aż do `resume` lub usunięcia pliku `STOP`;
- dane zachowane jak w G1.

**G3. Definitywne zakończenie K1 bez wyniku:**
1. Najpierw G1.
2. **[W]** Ręcznie zapisać `base/run/STOPPED.json` z polem `reason`. Wrapper i runner traktują go jako zakończenie z decyzją właściciela; brak wznowień.
3. `[runner] enabled = false`.

**Czego nie robić:**
- nie usuwać ani nie edytować plików w `run/`;
- nie zmieniać `code/`, `base/stim/` ani specyfikacji w trakcie; runner zabije proces (`pin`), a nadzorca odmówi startu (L8);
- nie uruchamiać drugiego nadzorcy ręcznie przy żywym `supervisor.lock`;
- nie wyładowywać modelu w trakcie bloku. To nie psuje danych, ale wywołania odpadną z błędem przejściowym, a proces będzie restartowany.

**Zatrzymania automatyczne (decyzja właściciela; `STOPPED.json`, bez wznowień):**

| Kod 3 | Kod 4 |
|---|---|
| naruszenie haka (97) | bramka przed A |
| błąd protokołu (HTTP 400, T12, T6, P_check) | T-długość po rekalibracji |
| preflight (obcy model w GPU) | limit etapu T lub limit twardy poza blokiem S |
| L8 | |
| brak zgód | |
| ponad 8 restartów | |
| drugi błąd w T albo A | |

## H. Po przebiegu

- [ ] `run/DONE.json`, `out/raw-freeze.json`, `report/K1_RAPORT.md` (z zasadą D1 na początku), `report/results.json`.
- [ ] Raport runnera (`workspace/lab/K1/RUN_REPORT.md`): kontrola przecieków `pass`, przypięte pliki niezmienione.
- [ ] **[W]** `[runner] enabled = false`. K1 nie ma własnego zadania Harmonogramu; nie ma czego usuwać.
- [ ] Interpretacje po fakcie wyłącznie w osobnych plikach, jako eksploracyjne (sek. 6.7).
