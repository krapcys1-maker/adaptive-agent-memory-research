# AAMR-K1: wykonawca pięcioramiennego K1 (N, P, X, S, M)

> **Stan 2026-11-13: READY do ręcznego etapu T** — specyfikacja K1 v1.0.1 (`spec/`), wszystkie zgody i blokady T1–T12 zamknięte (`DZIENNIK_DECYZJI_K1_v1.0.1.md`). Kontrola: `tools/pre_T_check.py`; ocena etapu T: `tools/review_T.py`.

> **Dziennik decyzji:** `DZIENNIK_DECYZJI_K1.md`. Kontrola przed etapem T: `python -I -X utf8 -B tools/pre_T_check.py`.

2026-11-13. Claude (Opus 5.5), osobna sesja. Katalog poza repozytoriami. **Nic tu nie wywołało modelu, Ollamy ani GPU.**
Pilotaż N/M, jego katalog, `sealed/`, NIGHT-2, koordynator (`[machine-local path omitted]`), baza i Harmonogram: tylko odczyt, bez zmian.

**Stan aktualny: `RAPORT_GO_NOGO_K1.md`.** Werdykt i decyzje: `WERDYKT.md`, `DECYZJE_BRAKUJACE.md`, `T1_T12_I_ZGODY.md`. Start i zatrzymanie: `CHECKLISTA_STARTOWA_K1.md`.

## Zawartość

| Ścieżka | Co to jest |
|---|---|
| `code/k1_config.json` | model, reżimy, bloki A/S1–S3, ziarna, limit 30 000, bramki, parametry etapu T, **decyzje D1–D12 ze statusem**, wybory techniczne T1–T11 |
| `code/k1_lib.py` | ścieżki, polityka haka, `BfclK1`, budowa P (prototyp W8), losowanie D12 (prototyp D9), dostawcy bloków 5 ramion, bramki, L1/L3/L4b, L8 |
| `code/prepare.py` | wyodrębnienie bodźców, L10 (G1, G2), korpus P przez L4a, L1/L2/L3, L4b, nagłówki, długość P, listy etapu T, `k1_test_tasks_88.json`, graf 7.4, manifest L8 |
| `code/rebuild_worker.py` | G2: odtworzenie planów M pod hakiem, bez odpowiedzi wzorcowych |
| `code/draw_worker.py` | pod hakiem: tabela tokenów z NIGHT-2 (`prompt_eval_count`, tura 0) i losowania X, S (D12) |
| `code/worker.py` | proces epizodów pod hakiem: T (preflight, `c_d`, T-długość, kontrole P, zamrożenie `c_d`, pomiar `m`), A, S1–S3 za bramkami |
| `code/supervisor.py` | nadzorca: L8, odmowa prawdziwego modelu bez zgód, fazy, restarty (trwałe), zamrożenie, checker, analiza; kody 0/3/4 |
| `code/checker.py` | checker w osobnym procesie (`p0.evaluate_episode`) |
| `code/analyze.py` | analiza sek. 7–8, 11: komórki (W6), kontrasty 98,33%, WR1–WR5, LEN, ρ̂/ρ̃/ρ*, blok A, dryf, drabina, szum, L9, kontrola przecieków po przebiegu, odczyt kodem v0.4 |
| `code/k1_audit_hook.py`, `k1_l4.py`, `k1_length.py`, `k1_v04_reading.py`, `t_w6_cells.py` | prototypy v0.4 **bajt w bajt** (`materials/PROTOTYPES_SHA256.txt`; test U0) |
| `materials/corpus_P_source.txt` | korpus P: 199 zdań (geologia, botanika), każde przechodzi L4a; `corpus_P_candidates.txt` = 245 kandydatów przed filtrem |
| `base/` | przygotowany katalog K1: `stim/` (bodźce, pule, plany, korpus, losowania X/S, tabela tokenów, listy L4a, graf, listy T), `meta/` (manifest L8, pochodzenie) |
| `tests/run_tests.py`, `tests/WYNIKI_TESTOW.out` | testy offline U0–U15 i wynik |
| `spec/` | kopia bajt w bajt zamrożonej K1 v1.0 i `FREEZE.json` (sprawdzana przy starcie) |
| `tests/t_risks_T.py`, `tests/WYNIKI_RYZYKA_T.out` | ryzyka T1–T12 i zakres zgód (R1–R4) |
| `tests/test_coordinator_runner.py` | K1 pod prawdziwym wykonawcą koordynatora w jego izolowanym świecie testowym |
| `integration/` | wpis do `coordinator.local.toml` i propozycja `lab propose` (gotowe, **niedopisane**) |

## Przebieg (po zamrożeniu)

```
python -I -X utf8 -B code/prepare.py --base [machine-local path omitted]
python -I -X utf8 -B code/supervisor.py --base [machine-local path omitted] --transport ollama
```
Drugie polecenie uruchamia koordynator (przez `night_wrapper.py`), nie człowiek. Dziś kończy się kodem 3: „real model refused: owner approvals missing”.

Kolejność: T (≤ 300 wywołań) → bramka przed A → A (444 epizody, temperatura 0) → bramka → S1, S2, S3 (po 740 epizodów, 0,7) → zamrożenie → checker → analiza → `report/K1_RAPORT.md`, `report/results.json`.

## Uwagi

- Bez git: polecenie nie prosiło o commity; integralność zapewnia manifest L8 (sha256 kodu, bodźców, konfiguracji, korpusu, specyfikacji i plików startowych interpretera). Każda zmiana pliku z manifestu zatrzymuje nadzorcę przed pierwszym wywołaniem (test U2, U7).
- `base/` jest przygotowany dla wartości rekomendowanych; po decyzjach właściciela trzeba ponownie uruchomić `prepare.py` (nowy manifest) i testy.
- `tests/_tmp/` zawiera bazy robocze testów (do usunięcia).
