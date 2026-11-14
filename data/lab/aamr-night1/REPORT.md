# AAMR-NIGHT-1: raport wygenerowany automatycznie

Raport powstał deterministycznie z zamrożonych surowych danych (`raw-freeze.json`), według reguł z `PROTOCOL.md`. Interpretacja i rekomendacja są w osobnym pliku `WNIOSKI.md` (jeśli powstał).

## Stan programu

| Etap | Status | Uwagi |
|---|---|---|
| preflight_q14 | done |  |
| a0_writer | done |  |
| b0_writers | done |  |
| b1_quality | done |  |
| sA | done |  |
| census | done |  |
| d0_build | done |  |
| sD | done |  |
| sC | done |  |
| preflight_q9 | done |  |
| sE | done |  |
| final | w toku (ten raport) |  |

## Koszty

- Lokalne wywołania (próby): 9153 (w tym ponowienia 0); wg budżetu: {'A': 1822, 'B': 820, 'H': 307, 'D': 3697, 'C': 598, 'E': 1909}; wg modelu: {'qwen2.5:14b-instruct': 7244, 'qwen3.5:9b-q4_K_M': 1909}.
- Czas modeli lokalnych (s): {'qwen2.5:14b-instruct': 8641.6, 'qwen3.5:9b-q4_K_M': 1182.2}; okno: 2026-11-12T19:42:27.395514+00:00 – 2026-11-12T22:32:10.755165+00:00.
- DeepSeek Flash: 20 wywołań, rezerwacja 0.2 USD, górne oszacowanie z użycia 0.015235 USD (45589 tokenów wejścia, 1299 wyjścia).
- Koszt budowy pamięci (pisarze): `{"lessons_VC_F": {"calls": 5, "valid": 5, "of": 5, "prompt_tokens": 11178, "output_tokens": 317, "usd_upper": 0.003734}, "lessons_VC_Q": {"calls": 5, "valid": 5, "of": 5, "prompt_tokens": 11033, "output_tokens": 221, "usd_upper": 0}, "lessons_GFS_Q": {"calls": 10, "valid": 9, "of": 10, "prompt_tokens": 18814, "output_tokens": 438, "usd_upper": 0}, "lessons_GFS_F": {"calls": 10, "valid": 9, "of": 10, "prompt_tokens": 19017, "output_tokens": 630, "usd_upper": 0.006461}, "lessons_GFS_D": {"lessons": 2, "calls": 0, "open_problems": 8}, "lessons_TRAVEL_Q": {"calls": 5, "valid": 5, "of": 5, "prompt_tokens": 15729, "output_tokens": 203, "usd_upper": 0}, "lessons_TRAVEL_F": {"calls": 5, "valid": 5, "of": 5, "prompt_tokens": 15394, "output_tokens": 352, "usd_upper": 0.005041}, "lessons_TRAVEL_D": {"lessons": 2, "calls": 0, "open_problems": 3}}`

## Etap A: EXP-FIX-0 (Vehicle Control, 30 zadań testowych, dane rozwojowe)

Zadania kompletne we wszystkich ramionach: 30.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 30 | 9 | 46 | 87 | 5 | 302 | 549673 | 0 |
| N' | 30 | 9 | 46 | 87 | 5 | 302 | 550295 | 0 |
| Tr | 30 | 12 | 45 | 86 | 5 | 292 | 539392 | 35 |
| TrO | 30 | 15 | 48 | 80 | 5 | 310 | 592662 | 47 |
| TrP | 30 | 12 | 48 | 77 | 5 | 304 | 575715 | 47 |
| TrW | 30 | 13 | 48 | 77 | 5 | 308 | 583048 | 47 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| N' vs N | 0 | 0 | +0 | 1.000 | 1.000 | 46 vs 46 |
| Tr vs N | 4 | 1 | +3 | 0.188 | 0.375 | 45 vs 46 |
| TrO vs N | 7 | 1 | +6 | 0.035 | 0.070 | 48 vs 46 |
| TrP vs N | 4 | 1 | +3 | 0.188 | 0.375 | 48 vs 46 |
| TrW vs N | 5 | 1 | +4 | 0.109 | 0.219 | 48 vs 46 |


**Reguły decyzji (zamrożone):** `{"N": 9, "N_prime": 9, "noise_abs_N_prime_minus_N": 0, "TrO_minus_N": 6, "TrO_minus_TrP": 3, "mcnemar_TrO_vs_N_one_sided": 0.03515625, "capacity_turns_in_TrO": 8, "capacity_turns_passed_fraction": 0.5, "verdict": "supported", "Tr_minus_N": 3, "Tr_replicated": true, "TrW": 13, "TrW_close_to_TrO": false, "TrW_close_to_N": false}`

Tury z błędem pojemności baku:

| Ramię | tury | zaliczone | odczyt paliwa po błędzie | udane tankowanie | notatka pokazana | zgodność kwoty |
|---|---|---|---|---|---|---|
| N | 9 | 1 | 0 | 0 | 0 | {} |
| N' | 9 | 1 | 0 | 0 | 0 | {} |
| Tr | 8 | 0 | 0 | 0 | 0 | {} |
| TrO | 8 | 4 | 8 | 8 | 8 | {'capacity_50': 8} |
| TrP | 8 | 0 | 1 | 3 | 8 | {'no_level_read': 2, 'capacity_50': 1} |
| TrW | 8 | 1 | 5 | 3 | 8 | {'other_amount': 1, 'capacity_50': 2} |

Spis porażek N (pierwsza nieudana tura): `{"failed": 21, "classes": {"error_unresolved": 8, "no_error_wrong_or_extra_action": 7, "error_resolved_turn_still_wrong": 3, "limit_steps": 3}, "error_adjacent": 11, "error_adjacent_share": 0.5238095238095238}`

## Etap B: jakość lekcji na danych treningowych i bramka

`{"summary": {"none": {"forks": 19, "resolved": 13, "turn_passed": 7}, "D": {"forks": 10, "resolved": 10, "turn_passed": 4}, "O": {"forks": 6, "resolved": 5, "turn_passed": 3}, "Q": {"forks": 19, "resolved": 15, "turn_passed": 8}, "F": {"forks": 19, "resolved": 18, "turn_passed": 9}}, "gate": {"Q": {"available": true, "valid": 5, "of": 5, "leaks": 0, "coverage_ok": true, "leak_ok": true, "replay_resolved": 15, "replay_resolved_none": 13, "replay_ok": true, "admitted": true}, "F": {"available": true, "valid": 5, "of": 5, "leaks": 0, "coverage_ok": true, "leak_ok": true, "replay_resolved": 18, "replay_resolved_none": 13, "replay_ok": true, "admitted": true}}}`

## Etap B i sonda szkody: ramiona TrQ, TrF, TrS w tej samej sesji

Zadania kompletne: 30.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 30 | 9 | 46 | 87 | 5 | 302 | 549673 | 0 |
| N' | 30 | 9 | 46 | 87 | 5 | 302 | 550295 | 0 |
| Tr | 30 | 12 | 45 | 86 | 5 | 292 | 539392 | 35 |
| TrO | 30 | 15 | 48 | 80 | 5 | 310 | 592662 | 47 |
| TrP | 30 | 12 | 48 | 77 | 5 | 304 | 575715 | 47 |
| TrW | 30 | 13 | 48 | 77 | 5 | 308 | 583048 | 47 |
| TrQ | 30 | 12 | 49 | 72 | 5 | 316 | 605902 | 57 |
| TrF | 30 | 17 | 46 | 47 | 6 | 302 | 565212 | 39 |
| TrS | 30 | 12 | 48 | 75 | 5 | 307 | 580747 | 47 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| N' vs N | 0 | 0 | +0 | 1.000 | 1.000 | 46 vs 46 |
| Tr vs N | 4 | 1 | +3 | 0.188 | 0.375 | 45 vs 46 |
| TrO vs N | 7 | 1 | +6 | 0.035 | 0.070 | 48 vs 46 |
| TrP vs N | 4 | 1 | +3 | 0.188 | 0.375 | 48 vs 46 |
| TrW vs N | 5 | 1 | +4 | 0.109 | 0.219 | 48 vs 46 |
| TrQ vs N | 4 | 1 | +3 | 0.188 | 0.375 | 49 vs 46 |
| TrF vs N | 9 | 1 | +8 | 0.011 | 0.021 | 46 vs 46 |
| TrS vs N | 4 | 1 | +3 | 0.188 | 0.375 | 48 vs 46 |


Porównania bezpośrednie:

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| TrQ vs Tr | 1 | 1 | +0 | 0.750 | 1.000 | 49 vs 45 |
| TrF vs Tr | 5 | 0 | +5 | 0.031 | 0.062 | 46 vs 45 |
| TrF vs TrQ | 5 | 0 | +5 | 0.031 | 0.062 | 46 vs 49 |
| TrS vs TrO | 0 | 3 | -3 | 1.000 | 0.250 | 48 vs 48 |
| TrS vs Tr | 0 | 0 | +0 | 1.000 | 1.000 | 48 vs 45 |
| TrF vs TrW | 5 | 1 | +4 | 0.109 | 0.219 | 46 vs 48 |
| TrQ vs TrW | 1 | 2 | -1 | 0.875 | 1.000 | 49 vs 48 |


## Replikacja na 20 zadaniach treningowych Vehicle Control

Reguła: **inconclusive**.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 20 | 6 | 31 | 60 | 2 | 204 | 353328 | 0 |
| TrP | 20 | 6 | 30 | 57 | 2 | 193 | 348417 | 39 |
| TrO | 20 | 8 | 31 | 47 | 2 | 201 | 365019 | 41 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| TrP vs N | 0 | 0 | +0 | 1.000 | 1.000 | 30 vs 31 |
| TrO vs N | 2 | 0 | +2 | 0.250 | 0.500 | 31 vs 31 |


## Spis porażek w nowych domenach (zadania treningowe)

`{"GFS": {"tasks": 20, "solved": 5, "model_calls": 174, "failed": 15, "classes": {"error_unresolved": 1, "no_error_wrong_or_extra_action": 7, "limit_steps": 3, "error_resolved_turn_still_wrong": 4}, "error_adjacent": 5, "error_adjacent_share": 0.3333333333333333, "deterministic_lessons": 2, "signatures": 10, "open_problems": 8, "a_plus_rows": 26}, "TRAVEL": {"tasks": 20, "solved": 9, "model_calls": 205, "failed": 11, "classes": {"error_resolved_turn_still_wrong": 3, "no_error_wrong_or_extra_action": 4, "error_unresolved": 3, "limit_steps": 1}, "error_adjacent": 6, "error_adjacent_share": 0.5454545454545454, "deterministic_lessons": 2, "signatures": 5, "open_problems": 3, "a_plus_rows": 57}}`

## Transfer na nietknięte zadania testowe (system plików, podróże)

Zadania kompletne: 58. Plan: `{"arms": ["N", "TrD", "N'", "TrF", "TrQ", "R+"], "dropped_for_budget": [], "per_episode": 9.448275862068966}`

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 58 | 17 | 96 | 219 | 20 | 555 | 1206652 | 0 |
| N' | 58 | 18 | 89 | 219 | 40 | 556 | 1209994 | 0 |
| TrD | 58 | 19 | 89 | 211 | 23 | 555 | 1220635 | 12 |
| TrQ | 58 | 22 | 87 | 178 | 21 | 566 | 1278175 | 56 |
| TrF | 58 | 21 | 97 | 215 | 13 | 556 | 1282556 | 66 |
| R+ | 58 | 22 | 69 | 152 | 31 | 515 | 1267132 | 0 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| N' vs N | 1 | 0 | +1 | 0.500 | 1.000 | 89 vs 96 |
| TrD vs N | 2 | 0 | +2 | 0.250 | 0.500 | 89 vs 96 |
| TrQ vs N | 7 | 2 | +5 | 0.090 | 0.180 | 87 vs 96 |
| TrF vs N | 6 | 2 | +4 | 0.145 | 0.289 | 97 vs 96 |
| R+ vs N | 14 | 9 | +5 | 0.202 | 0.405 | 69 vs 96 |


**Test główny (TrD > N):** `{"TrD_minus_N": 2, "p_one_sided": 0.25, "noise": 1, "confirmed": false}`
Rodzina Holma: `{"TrQ": {"p": 0.08984375, "threshold": 0.0125, "reject": false}, "TrF": {"p": 0.14453125, "threshold": 0.016666666666666666, "reject": false}, "R+": {"p": 0.2024364471435547, "threshold": 0.025, "reject": false}, "TrD": {"p": 0.25, "threshold": 0.05, "reject": false}}`

Porównania:

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| TrF vs TrD | 4 | 2 | +2 | 0.344 | 0.688 | 97 vs 89 |
| TrQ vs TrD | 5 | 2 | +3 | 0.227 | 0.453 | 87 vs 89 |
| TrF vs TrQ | 0 | 1 | -1 | 1.000 | 1.000 | 97 vs 87 |
| R+ vs TrD | 13 | 10 | +3 | 0.339 | 0.678 | 69 vs 89 |

Wyniki per domena: `{"GFS": {"N": 4, "N'": 5, "TrD": 5, "TrQ": 6, "TrF": 5, "R+": 10, "tasks": 30}, "TRAVEL": {"N": 13, "N'": 13, "TrD": 14, "TrQ": 16, "TrF": 16, "R+": 12, "tasks": 28}}`
Spis porażek N: `{"failed": 41, "classes": {"error_resolved_turn_still_wrong": 11, "no_error_wrong_or_extra_action": 12, "error_unresolved": 12, "limit_steps": 6}, "error_adjacent": 23, "error_adjacent_share": 0.5609756097560976}`

## Drugi model: qwen3.5:9b na 30 zadaniach testowych Vehicle Control

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 30 | 10 | 52 | 79 | 4 | 386 | 794973 | 0 |
| N' | 30 | 10 | 52 | 79 | 4 | 386 | 794973 | 0 |
| Tr | 30 | 13 | 52 | 80 | 2 | 379 | 791618 | 43 |
| TrO | 30 | 19 | 52 | 71 | 2 | 383 | 807984 | 53 |
| TrP | 30 | 13 | 50 | 86 | 2 | 372 | 780001 | 50 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne | zdarzenia błędu (x vs y) |
|---|---|---|---|---|---|---|
| N' vs N | 0 | 0 | +0 | 1.000 | 1.000 | 52 vs 52 |
| Tr vs N | 3 | 0 | +3 | 0.125 | 0.250 | 52 vs 52 |
| TrO vs N | 9 | 0 | +9 | 0.002 | 0.004 | 52 vs 52 |
| TrP vs N | 3 | 0 | +3 | 0.125 | 0.250 | 50 vs 52 |


**Reguły (jak EXP-FIX-0):** `{"N": 10, "N_prime": 10, "noise_abs_N_prime_minus_N": 0, "TrO_minus_N": 9, "TrO_minus_TrP": 6, "mcnemar_TrO_vs_N_one_sided": 0.001953125, "capacity_turns_in_TrO": 10, "capacity_turns_passed_fraction": 0.7, "verdict": "supported", "Tr_minus_N": 3, "Tr_replicated": true}`

## Czy DeepSeek pomaga bardziej niż lokalne rozwiązania (reguła z protokołu)

- Dane rozwojowe (sA): `{"verdict": "flash_better", "TrF": 17, "best_local": "Tr", "best_local_solved": 12, "diff": 5, "p_one_sided": 0.03125, "noise_band": 1}`
- Nietknięte zadania (sD): `{"verdict": "no_detected_difference", "TrF": 21, "best_local": "TrQ", "best_local_solved": 22, "diff": -1, "p_one_sided": 1.0, "noise_band": 2}`

## Otwarte problemy (nierozwiązane błędy w pierwszej nieudanej turze ramienia N, liczone po zadaniach)

`{"sA": {"fillFuelTank|cannot fill gas above the tank capacity": 7, "estimate_distance|distance not found in database": 3, "get_user_id|user <v> not found in the workspace": 1, "get_message_stats|no user is currently logged in": 1, "startEngine|all doors must be locked before starting the engine": 1}, "census": {"mv|mv: cannot move <v>: no such file or directory": 2, "cat|cat: <v>: invalid character": 2, "mv|mv: path not allowed in destination": 1, "cp|file <v> already exists in directory <v>": 1, "cp|cp: path not allowed in destination": 1, "sort|sort: <arg>: no such file or directory": 1, "grep|grep: <arg>: no such file or directory": 1, "tail|tail: <arg>: no such file or directory": 1, "resolve_ticket|<v>": 1, "edit_ticket|<v>": 1, "compute_exchange_rate|no available exchange rate for the given currencies": 1, "cancel_booking|booking not found": 1}, "sD": {"get_flight_cost|no available route for the given airports": 5, "grep|grep: <arg>: no such file or directory": 4, "cat|cat: <v>: invalid character": 3, "mv|mv: cannot move <v>: no such file or directory": 2, "cp|cp: cannot copy <v>: no such file or directory": 2, "cat|cat: <v>: no such file or directory": 2, "compute_exchange_rate|no available exchange rate for the given currencies": 2, "cp|cp: path not allowed in destination": 1, "mkdir|mkdir: cannot create directory <v>: file exists": 1, "cd|current directory is already the root": 1, "cd|cd: <arg>: unsupported path": 1, "cd|cd: <v>: no such file or directory": 1}, "sE": {"fillFuelTank|cannot fill gas above the tank capacity": 6, "estimate_distance|distance not found in database": 1}}`

## Status dowodów

- Potwierdzające: test główny sD (TrD > N) i rodzina Holma w sD, na 58 zadaniach nigdy wcześniej nieużywanych.
- Zarejestrowane z góry, ale na danych rozwojowych (zadania VC znane z pilota i S1): reguły EXP-FIX-0 (sA), replikacja (sC), drugi model (sE), porównanie pisarzy w sA.
- Eksploracyjne: tury z błędem baku, zgodność z nieaktualną lekcją (TrS), spis porażek, otwarte problemy, koszty, wszystkie porównania niewymienione wyżej.

## Odczyt regułowy następnego kroku (STRATEGIA_AAMR.md 5.3; decyzja należy do właściciela)

- H5 utrzymana na danych rozwojowych: C6 (treść dla otwartych problemów podawana przy błędzie) staje się głównym polem pracy.
- Transfer TrD > N na nietkniętych zadaniach: niepotwierdzony.
- Brak wykazanej przewagi Flash nad lokalnymi źródłami: domyślnie pamięć budowana lokalnie (0 USD).
- Replikacja H5 na 20 innych zadaniach VC: inconclusive.
- H5 na qwen3.5:9b: supported.
- Największy otwarty problem na nowych domenach (bez pamięci): get_flight_cost|no available route for the given airports w 5 zadaniach; kandydat na następną treść C6.
- Etap 1 strategii (konkurenci w naszym harnessie) pozostaje warunkiem twierdzenia „lepszy niż konkurencja”.

## Błędy techniczne

Linie w `errors.log`: 0. Restarty: `null`.

