# K1: dziennik decyzji i poprawek technicznych (sek. 6.4 v1.0)

Specyfikacja: K1 v1.0, sha256 `e585ed8dac5670f906e7deceaf89b306a89bece30acd2da06b8d5be781dd38df`, kopia w `spec/`. Wartości w kodzie: `code/k1_config.json` (`decisions`, `technical_choices_status`).

| Data | Pozycja | Decyzja właściciela | Zapis w wykonawcy |
|---|---|---|---|
| 2026-11-13 | D1, D3, D4, D7, D8, D12 | zatwierdzone (v1.0 sek. 13; D4 = 3 bloki, D8 = pełne K1, po jawnym raporcie pilotażu) | `approved 2026-11-13` |
| 2026-11-13 | D2, D6, D9, D10 | zatwierdzone wcześniej; pokrywają K1 (`T1_T12_I_ZGODY.md`) | bez zmian |
| 2026-11-13 | **D5** dla pełnego K1 | **zatwierdzone** w brzmieniu z `RAPORT_GO_NOGO_K1.md`, sek. 4: runner przez `night_wrapper`, ręczny etap T, brak git (manifest L8 + `pin`) | `approved 2026-11-13 …` |
| 2026-11-13 | **D11** dla pełnego K1 | **zatwierdzone** z dodatkami: (a) odczyt `prompt_eval_count` z `responses.jsonl` NIGHT-2 w procesie pod hakiem; (b) `memory.items` ramienia M z sesji NIGHT-2 do grafu 7.4; (c) T12 | `approved 2026-11-13 …` |
| 2026-11-13 | **T1–T12** | **zaakceptowane warunkowo.** Warunek: żaden wybór nie zmienia metodologii, bodźców ani reguł oceny v1.0; bez T2b; kontrole, limity i T12 zachowane | patrz niżej |
| 2026-11-13 | T2b | **odrzucone** (nie wprowadzone) | `T2: approved (without T2b)` |

## Kontrola zgodności z v1.0 przed zapisem T1–T12

Plik: `tests/t_v10_conformity.py` → `tests/WYNIKI_ZGODNOSC_v1.0.out`. Zgodnie z poleceniem właściciela zatrzymałem zatwierdzanie pozycji, które **nie są dosłownie zgodne** z tekstem v1.0.

| # | Gdzie | Tekst v1.0 | Wykonawca | Skutek zmierzony offline | Wpływ na metodologię / bodźce |
|---|---|---|---|---|---|
| **C2** | D12 (sek. 2) | „mieści się w **±20%** bloku M tej tury” | jak zamrożony prototyp `t_d9_length.py` (w `FREEZE.json`): \|ln(przewidywane/cel)\| ≤ ln 1,2, czyli **−16,7% … +20%**; „najbliższe” w skali log | Reguła wykonawcy daje dokładnie liczby podane w v1.0: X **+1,84%**, S **+2,24%** (spec +1,8 / +2,2). Dosłowne ±20% zmienia **159/1 542 losowań X i 292/1 542 losowań S** i podnosi nierównowagę do X **+3,85%**, S **+4,12%** (próg B1: 5%) | **Tak, bodźce X i S.** Tekst v1.0 jest wewnętrznie niespójny: reguła słowna i podane skutki pochodzą z różnych wariantów |
| **C1** | `c_d`, T5 (sek. 2) | ρ = Σ tokenów bloków / Σ **znaków bloków** | znaki bloku **+ 2** (separator `\n\n`, który `prompt_eval_count` też liczy); jak prototyp | ρ_M,d +0,12…+0,21%; `c_d` < 0,1%; w D12 2–4 losowania na 1 542 | pomijalny, ale literalnie różny (bodźce P i X/S) |
| **C3** | WR5 (sek. 7.5) | dalsze tury: **znaki treści** × tokeny na znak | znaki bloku + 2 | x_i: średnio −0,00001, maks. 0,0004 w skali log (próg B1 0,049) | pomijalny; tylko analiza |
| **C4** | T7, T8 dla bloku A (sek. 7.2, 10) | drugi wyjątek w bloku / limit twardy → „blok kończy się jako **nieukończony**” | blok A: **stop programu** (kod 3/4, decyzja właściciela) | bez wpływu na bodźce; zmienia tylko to, czy program sam przechodzi do S1 | przebieg sterowania; dosłownie niezgodny |

Pozycje zgodne i zatwierdzone: T1, T2 (bez T2b), T3, T4, T6, T7 i T8 dla bloków próbkowanych, T9, T10, T11, T12.

**Wstrzymane:** T5 (C1), T7/T8 dla bloku A (C4), tolerancja D12 (C2), WR5 dalsze tury (C3). `technical_choices_approved` = `false`, więc nadzorca nadal odmawia prawdziwego modelu.

## Propozycje rozstrzygnięć (do decyzji właściciela; nic nie wprowadzone)

| # | Wariant A: zgodność dosłowna z tekstem v1.0 | Wariant B: zgodność z zamrożonym prototypem i liczbami v1.0 | Rekomendacja |
|---|---|---|---|
| C2 | liniowe ±20%; ponowne `prepare.py`; nierównowaga X +3,85%, S +4,12%; liczby LEN z v1.0 (4%, 8%) przestają obowiązywać i trzeba je przeliczyć | log ±20% jak dziś; zapis w dzienniku: „±20% w sek. 2 rozumiane jak w zamrożonym `t_d9_length.py` (`TOL = log(1.20)`), z którego pochodzą liczby sek. 2 i 7.5” | **B**: zachowuje bodźce i wszystkie liczby, na których oparto D12; to wyjaśnienie niejasności (sek. 6.6), nie zmiana |
| C1 | znaki bez +2; ponowne `prepare.py` (2–4 losowania inne) | jak prototyp, z zapisem w dzienniku | **A**: zmiana trywialna, usuwa literalną niezgodność |
| C3 | znaki treści w WR5 | bez zmian | **A**: tylko analiza, bez bodźców |
| C4 | blok A po drugim błędzie albo limicie → nieukończony; program przechodzi do bramki przed S1; odpowiedź drugorzędna NIEWAŻNA | stop programu (dzisiaj) | **A**: dosłownie sek. 7.2 |

Po decyzji: wprowadzam wybrane warianty, a przy C1 albo C2-A także `prepare.py` i nowy manifest. Następnie pełne testy, `technical_choices_approved = true` i wpis w tym dzienniku.

## Decyzje właściciela C1–C4 (2026-11-13) i ich wykonanie

| # | Decyzja | Uzasadnienie (właściciel / dane) | Wykonanie w kodzie | Stan |
|---|---|---|---|---|
| **C1** | poprawka do dosłownej definicji ρ (sek. 2): ρ = Σ tokenów bloków / Σ znaków bloków | zgodność dosłowna; wpływ ρ +0,12…+0,21%, `c_d` < 0,1% | `draw_worker.py` (tabela tokenów), `worker.py` (etap T): znaki bloku bez +2 | **zatwierdzone, wdrożone**; bodźce przygotowane ponownie. 21 z 3 084 losowań X/S różni się od prototypu (X 2, S 19); nierównowaga X +1,83%, S +2,31% |
| **C2** | reguła logarytmiczna zamrożonego prototypu `t_d9_length.py`, **bez cichej reinterpretacji „±20%”** | ta reguła wygenerowała bodźce i liczby kontrolne, na których oparto D12 | reguła w kodzie bez zmian; etykieta w `k1_draws_SX.json` i `k1_config.json → d12` jawnie opisuje regułę log i granice (−16,67% … +20%) | **ZABLOKOWANE**: sek. 6.4 v1.0 wyklucza zmiany ramion, a 6.6 wskazałaby wariant liniowy. **Wymagana nowa wersja protokołu przed startem** (`ANEKS_C2_D12.md`) |
| **C3** | WR5: dalsze tury = znaki treści (sek. 7.5) | zgodność dosłowna; wpływ ≤ 0,0004 w skali log | `analyze.stimulus_chars`: znaki treści; ρ ramienia i domeny = dokładne tokeny tury 0 / znaki treści tury 0 | **zatwierdzone, wdrożone** |
| **C4** | zatrzymanie nadzorcy po drugim błędzie w bloku A zostaje; blok A jednoznacznie NIEUKOŃCZONY; bez dodatkowych prób | zgodność z 7.2 („blok nieukończony”) przy zachowaniu decyzji właściciela | `run/A_INCOMPLETE.json` (`status: NIEUKOŃCZONY`) po drugim błędzie (stop, kod 3) i po limicie twardym w A (stop, kod 4). Wznowienie nie uruchamia A ponownie; A poza checkerem, zamrożeniem i analizą; raport: `blocks.A = NIEUKOŃCZONY`, `block_A.status = NIEUKOŃCZONY` i zastrzeżenie | **zatwierdzone, wdrożone**; test U16 |

`technical_choices_approved` pozostaje `false` wyłącznie z powodu C2. Pozostałe pozycje T1–T12, C1, C3 i C4 mają status `approved`.
