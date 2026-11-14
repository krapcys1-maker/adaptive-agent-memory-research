# AAMR-NIGHT-2: raport wygenerowany automatycznie

Raport powstał deterministycznie z zamrożonych surowych danych (`raw-freeze.json`), według reguł z `SPEC_AAMR_NIGHT2.md` i `PROTOCOL.md`. Wszystkie wyniki mają status rozwojowy. Interpretacja jest w osobnym pliku `WNIOSKI.md` (jeśli powstał).

## Stan programu

| Etap | Status | Uwagi |
|---|---|---|
| preflight_q14 | done |  |
| E1 | done |  |
| E2 | done |  |
| build_c | done |  |
| E3 | done |  |
| E4 | done |  |
| preflight_q9 | done |  |
| E5 | done |  |
| final | None |  |

## Koszty

- Lokalne próby w programie: 16106 (ponowienia 0), test techniczny 32, razem 16138 (limit 21 500). Wywołania płatne: 0.
- Według budżetu: {'T': 6, 'E1': 2807, 'E2': 1101, 'E4': 3506, 'E3': 6025, 'E5': 2661}; według modelu: {'qwen2.5:14b-instruct': 13442, 'qwen3.5:9b-q4_K_M': 2664}.
- Czas modeli (s): {'qwen2.5:14b-instruct': 19348.9, 'qwen3.5:9b-q4_K_M': 1957.3}; okno 2026-11-13T05:37:08.389532+00:00 – 2026-11-13T11:45:43.348142+00:00.
- Budowa pamięci: `{"attempts": {"other": 14906, "E2_forks": 1101, "C-RB": 61, "C-G": 38}, "K": "V0q", "K_build_calls": 0, "K_note": "V0: tournament forks of E2; V0q: notes Q written in NIGHT-1 (20 local writer calls there)", "C-RB_build_calls": 61, "C-G_build_calls": 38}`

## E1 (EXP-MASK-0): pamięć sukcesów z maskowaniem, 60 zadań treningowych

Zadania kompletne: 60.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 60 | 20 | 91 | 196 | 6 | 573 | 1153588 | 0 |
| R+ | 60 | 22 | 73 | 111 | 16 | 548 | 1314841 | 0 |
| M2 | 60 | 14 | 73 | 117 | 26 | 549 | 1301847 | 0 |
| M1 | 60 | 18 | 78 | 152 | 9 | 561 | 1260699 | 0 |
| N' | 60 | 20 | 91 | 174 | 6 | 575 | 1160478 | 0 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne |
|---|---|---|---|---|---|
| R+ vs N | 11 | 9 | +2 | 0.4119 | 0.8238 |
| M2 vs N | 5 | 11 | -6 | 0.9616 | 0.2101 |
| M1 vs N | 8 | 10 | -2 | 0.7597 | 0.8145 |
| N' vs N | 0 | 0 | +0 | 1.0000 | 1.0000 |

| Ramię | zyski wg przyczyny | straty wg przyczyny |
|---|---|---|
| R+ | {'memory': 11} | {'copy': 7, 'memory': 2} |
| M2 | {'memory': 5} | {'copy': 6, 'memory': 5} |
| M1 | {'memory': 8} | {'copy': 5, 'memory': 5} |
| N' | {} | {} |

| Domena | zadania | N | R+ | M2 | M1 | N' |
|---|---|---|---|---|---|---|
| VC | 20 | 6 | 8 | 4 | 7 | 6 |
| GFS | 20 | 5 | 6 | 4 | 4 | 5 |
| TRAVEL | 20 | 9 | 8 | 6 | 7 | 9 |

**Wybór E\*:** `{"E_star": "R+", "tasks": 60, "solved": {"N": 20, "R+": 22, "M2": 14, "M1": 18, "N'": 20}, "losses_vs_N": {"R+": 9, "M2": 11, "M1": 10}}`

**H14:** `{"verdict": "refuted", "M": "M1", "solved_R+": 22, "solved_M": 18, "losses_R+": 9, "losses_M": 10, "copy_losses": {"R+": 7, "M2": 6, "M1": 5, "N'": 0}}`

## E2 (EXP-NOTE-SEL): turniej notatek na stanach treningowych

Rozwidlenia: 351 ({'none': 70, 'Q': 68, 'G0': 70, 'F': 66, 'O': 6, 'S': 6, 'P': 6, 'X': 29, 'D': 30}). Użyty zestaw: **T**.

**Kontrola narzędzia (błąd baku, {O, S, P, Q, F}):** `{"winner": "F", "valid": true}`

Tabela kontroli: `{"none": {"states": 6, "resolved": 2, "passed": 2}, "O": {"states": 6, "resolved": 5, "passed": 3, "regressions": 0, "admissible": true}, "S": {"states": 6, "resolved": 5, "passed": 1, "regressions": 1, "admissible": false}, "P": {"states": 6, "resolved": 2, "passed": 2, "regressions": 0, "admissible": true}, "Q": {"states": 6, "resolved": 3, "passed": 3, "regressions": 1, "admissible": false}, "F": {"states": 6, "resolved": 5, "passed": 4, "regressions": 0, "admissible": true}}`

| Domena | Sygnatura | stany | X powstał | wybrany | oceny (stany/rozwiązane/zaliczone/regresje/dopuszczalny) |
|---|---|---|---|---|---|
| GFS | cat|cat: <v>: invalid character | 4 | False | None | none: 2/1/-/-; Q: 1/2/0/False; G0: 1/1/0/False |
| GFS | cd|cd: <v>: no such file or directory | 4 | False | None | none: 2/2/-/-; D: 1/2/1/False; Q: 4/0/2/False; G0: 1/2/1/False |
| GFS | cd|current directory is already the root | 2 | False | G0 | none: 0/1/-/-; Q: 2/0/1/False; G0: 1/1/0/True |
| GFS | cp|cp: cannot copy <v>: no such file or directory | 2 | False | Q | none: 1/2/-/-; Q: 1/2/0/True; G0: 1/2/0/True |
| GFS | cp|cp: path not allowed in destination | 2 | False | None | none: 1/0/-/-; Q: 0/0/0/False; G0: 0/0/0/False |
| GFS | echo|echo: cannot write to <v>: no such file | 4 | False | D | none: 4/0/-/-; D: 4/0/0/True; Q: 4/0/0/True; G0: 4/0/0/True |
| GFS | grep|grep: <arg>: no such file or directory | 2 | False | Q | none: 1/0/-/-; Q: 1/0/0/True; G0: 0/0/0/False |
| GFS | mv|mv: cannot move <v>: no such file or directory | 2 | False | Q | none: 0/0/-/-; Q: 1/1/0/True; G0: 0/0/0/True |
| GFS | mv|mv: path not allowed in destination | 2 | False | G0 | none: 1/0/-/-; G0: 2/1/0/True |
| GFS | tail|tail: <arg>: no such file or directory | 2 | False | Q | none: 1/1/-/-; Q: 2/2/0/True; G0: 1/1/0/True |
| TRAVEL | book_flight|invalid access token | 2 | False | G0 | none: 2/0/-/-; Q: 1/0/0/False; G0: 2/0/0/True |
| TRAVEL | book_flight|invalid departure airport code: <arg> | 2 | False | D | none: 2/1/-/-; D: 2/1/0/True; Q: 2/1/0/True; G0: 2/1/0/True |
| TRAVEL | compute_exchange_rate|no available exchange rate for the giv | 4 | False | None | none: 1/2/-/-; Q: 0/1/1/False; G0: 0/1/1/False |
| TRAVEL | get_flight_cost|no available route for the given airports | 7 | True | Q | none: 7/5/-/-; X: 6/5/0/False; Q: 7/5/0/True; G0: 7/4/1/False |
| TRAVEL | retrieve_invoice|booking not found | 2 | False | D | none: 2/1/-/-; D: 2/1/0/True; Q: 2/1/0/True; G0: 2/1/0/True |
| VC | estimate_distance|distance not found in database | 3 | False | Q | none: 1/1/-/-; Q: 2/1/0/True; G0: 1/1/0/True |
| VC | fillFuelTank|cannot fill gas above the tank capacity | 6 | True | G0 | none: 2/2/-/-; X: 4/4/0/True; Q: 3/3/1/False; G0: 5/4/0/True |
| VC | startEngine|all doors must be locked before starting the eng | 8 | True | D | none: 8/4/-/-; D: 8/4/0/True; X: 8/4/0/True; Q: 8/4/0/True; G0: 8/4/0/True |
| VC | startEngine|brake pedal needs to be pressed when starting th | 8 | True | D | none: 8/4/-/-; D: 8/4/0/True; X: 8/4/0/True; Q: 8/4/0/True; G0: 8/4/0/True |
| VC | startEngine|must press the brake fully before starting the e | 2 | False | D | none: 2/2/-/-; D: 2/2/0/True; Q: 2/2/0/True; G0: 2/1/1/False |

Wybrane źródła notatek: `{"VC": {"Q": 1, "G0": 1, "D": 3}, "GFS": {"G0": 2, "Q": 4, "D": 1}, "TRAVEL": {"G0": 1, "D": 2, "Q": 1}}`
Flash wobec najlepszego kandydata lokalnego (tylko porównanie): `{"signatures_with_F": 19, "F_would_win": 4}`

## E3 (EXP-V0-1): system złożony, 88 zadań rozwojowych-testowych, 14B

Zadania kompletne: 88.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 88 | 28 | 144 | 310 | 33 | 869 | 1777749 | 0 |
| V0 | 88 | 35 | 93 | 166 | 32 | 841 | 2038661 | 58 |
| N' | 88 | 27 | 142 | 299 | 30 | 865 | 1770618 | 0 |
| E* | 88 | 38 | 97 | 192 | 38 | 810 | 1953890 | 0 |
| TrT | 88 | 36 | 140 | 250 | 31 | 894 | 1898602 | 104 |
| V0q | 88 | 34 | 90 | 138 | 50 | 844 | 2060372 | 63 |
| TrQ | 88 | 34 | 145 | 282 | 30 | 902 | 1920315 | 119 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne |
|---|---|---|---|---|---|
| V0 vs N | 20 | 13 | +7 | 0.1481 | 0.2962 |
| N' vs N | 0 | 1 | -1 | 1.0000 | 1.0000 |
| E* vs N | 22 | 12 | +10 | 0.0607 | 0.1214 |
| TrT vs N | 10 | 2 | +8 | 0.0193 | 0.0386 |
| V0q vs N | 18 | 12 | +6 | 0.1808 | 0.3616 |
| TrQ vs N | 9 | 3 | +6 | 0.0730 | 0.1460 |

| Domena | zadania | N | V0 | N' | E* | TrT | V0q | TrQ |
|---|---|---|---|---|---|---|---|---|
| VC | 30 | 10 | 13 | 9 | 14 | 16 | 14 | 13 |
| GFS | 30 | 5 | 12 | 5 | 12 | 5 | 10 | 6 |
| TRAVEL | 28 | 13 | 10 | 13 | 12 | 15 | 10 | 15 |

| Ramię | zyski wg przyczyny | straty wg przyczyny |
|---|---|---|
| V0 | {'memory': 20} | {'copy': 9, 'memory': 4} |
| N' | {} | {'noise_before_memory': 1} |
| E* | {'memory': 22} | {'copy': 8, 'memory': 4} |
| TrT | {'memory': 10} | {'memory': 1, 'noise_before_memory': 1} |
| V0q | {'memory': 18} | {'memory': 5, 'copy': 7} |
| TrQ | {'memory': 9} | {'memory': 3} |

**Kontrola dryfu (N wobec NIGHT-1):** `{"tasks": 88, "agree": 86, "ok": true, "flipped": ["multi_turn_base_81", "multi_turn_base_43"]}`

**Test główny:** `{"verdict": "refuted", "V0": 35, "N": 28, "diff": 7, "p_one_sided": 0.1481031842995435, "losses": 13, "noise_abs_Nprime_minus_N": 1, "domains_V0_ge_N": false, "domains_V0_gt_N": 2}`

- **H15:** `{"verdict": "refuted", "V0": 35, "E*": 38, "TrT": 36}`
- **H16:** `{"verdict": "supported", "TrT": 36, "TrQ": 34, "losses_TrT": 2, "losses_TrQ": 3}`
- **H14_repeat:** `{"verdict": "not_applicable (E* = R+)"}`
- Rodzina Holma: `{"TrT_vs_TrQ": {"p": 0.36328125, "threshold": 0.016666666666666666, "reject": false}, "V0_vs_TrT": {"p": 0.6320605995715596, "threshold": 0.025, "reject": false}, "V0_vs_E*": {"p": 0.96875, "threshold": 0.05, "reject": false}}`

**Konfiguracja K:** `{"K": "V0q", "V0": 35, "V0q": 34, "tasks": 88}`

Spis porażek K (taksonomia NIGHT-1): `{"failed": 54, "classes": {"error_resolved_turn_still_wrong": 15, "error_unresolved": 10, "no_error_wrong_or_extra_action": 26, "invalid_call_no_env_error": 1, "limit_steps": 2}, "error_adjacent": 25, "error_adjacent_share": 0.46296296296296297}`

Otwarte problemy K: `{"mkdir|mkdir: cannot create directory <v>: file exists": 3, "cp|cp: cannot copy <v>: no such file or directory": 2, "fillFuelTank|cannot fill gas above the tank capacity": 1, "view_messages_sent|no user is currently logged in": 1, "get_message_stats|no user is currently logged in": 1, "search_messages|no user is currently logged in": 1, "get_user_id|user <v> not found in the workspace": 1, "cp|cp: path not allowed in destination": 1, "grep|grep: <arg>: no such file or directory": 1, "mv|mv: cannot move <v>: no such file or directory": 1, "compute_exchange_rate|no available exchange rate for the given currencies": 1, "get_flight_cost|no available route for the given airports": 1}`
Otwarte problemy N: `{"fillFuelTank|cannot fill gas above the tank capacity": 6, "get_flight_cost|no available route for the given airports": 5, "grep|grep: <arg>: no such file or directory": 4, "cp|cp: cannot copy <v>: no such file or directory": 3, "estimate_distance|distance not found in database": 2, "cp|cp: path not allowed in destination": 2, "mv|mv: cannot move <v>: no such file or directory": 2, "cat|cat: <v>: no such file or directory": 2, "cat|cat: <v>: invalid character": 2, "compute_exchange_rate|no available exchange rate for the given currencies": 2, "startEngine|all doors must be locked before starting the engine": 1, "mkdir|mkdir: cannot create directory <v>: file exists": 1}`

Zadania stracone przez K wobec N (tura rozstrzygająca, przyczyna):

- multi_turn_base_83 (VC), tura 0: memory
- multi_turn_base_81 (VC), tura 0: memory
- multi_turn_base_43 (GFS), tura 3: memory
- multi_turn_base_22 (GFS), tura 1: memory; notatki w turze ['cp|cp: path not allowed in destination']
- multi_turn_base_152 (TRAVEL), tura 0: copy; skopiowane ['compute_exchange_rate:USD'] ['compute_exchange_rate', 'get_credit_card_balance']; notatki w turze ['compute_exchange_rate|no available exchange rate for the given currencies']
- multi_turn_base_151 (TRAVEL), tura 0: memory
- multi_turn_base_183 (TRAVEL), tura 1: copy; skopiowane ['book_flight:business', 'get_flight_cost:business'] ['retrieve_invoice']; notatki w turze ['retrieve_invoice|booking not found']
- multi_turn_base_191 (TRAVEL), tura 4: copy; skopiowane ['set_budget_limit:7142.86'] ['set_budget_limit']
- multi_turn_base_181 (TRAVEL), tura 4: copy; skopiowane ['create_ticket:4.0'] []
- multi_turn_base_165 (TRAVEL), tura 2: copy; skopiowane ['book_flight:JFK', 'get_flight_cost:JFK', 'get_nearest_airport_by_city:New York'] []; notatki w turze ['get_flight_cost|no available route for the given airports']
- multi_turn_base_182 (TRAVEL), tura 0: copy; skopiowane ['get_flight_cost:SSV'] []
- multi_turn_base_163 (TRAVEL), tura 1: copy; skopiowane ['set_budget_limit:7142.86'] ['set_budget_limit']

## E4 (EXP-V0-1C): ramiona w stylu konkurentów

Zadania kompletne: 88.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 88 | 27 | 126 | 277 | 41 | 862 | 1756173 | 0 |
| K | 88 | 32 | 94 | 153 | 49 | 847 | 2063283 | 71 |
| C-RB | 88 | 30 | 131 | 243 | 30 | 885 | 2012961 | 0 |
| C-G | 88 | 31 | 109 | 195 | 49 | 813 | 1918243 | 0 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne |
|---|---|---|---|---|---|
| K vs N | 16 | 11 | +5 | 0.2210 | 0.4421 |
| C-RB vs N | 11 | 8 | +3 | 0.3238 | 0.6476 |
| C-G vs N | 12 | 8 | +4 | 0.2517 | 0.5034 |

| Domena | zadania | N | K | C-RB | C-G |
|---|---|---|---|---|---|
| VC | 30 | 9 | 13 | 11 | 10 |
| GFS | 30 | 5 | 9 | 8 | 9 |
| TRAVEL | 28 | 13 | 10 | 11 | 12 |

| Ramię | zyski wg przyczyny | straty wg przyczyny |
|---|---|---|
| K | {'memory': 16} | {'copy': 8, 'memory': 3} |
| C-RB | {'memory': 11} | {'copy': 1, 'memory': 7} |
| C-G | {'memory': 12} | {'memory': 8} |

**Reguła konkurentów:** `{"verdict": "K_not_ahead", "C": "C-G", "K": 32, "C_solved": 31, "losses_K": 11, "losses_C": 8, "K_minus_N": 5}`

## E5: drugi model (qwen3.5:9b)

Zadania kompletne: 88.

| Ramię | tasks | solved | error_events | error_results | invalid_calls | model_calls | prompt_tokens | notes_shown |
|---|---|---|---|---|---|---|---|---|
| N | 88 | 35 | 104 | 169 | 11 | 891 | 1837528 | 0 |
| K | 88 | 40 | 77 | 131 | 8 | 873 | 2127689 | 68 |
| N' | 88 | 34 | 106 | 187 | 11 | 897 | 1850819 | 0 |

| Porównanie | zyskane | stracone | różnica | p jednostronne | p dwustronne |
|---|---|---|---|---|---|
| K vs N | 17 | 12 | +5 | 0.2291 | 0.4583 |
| N' vs N | 0 | 1 | -1 | 1.0000 | 1.0000 |

| Domena | zadania | N | K | N' |
|---|---|---|---|---|
| VC | 30 | 9 | 13 | 9 |
| GFS | 30 | 10 | 9 | 9 |
| TRAVEL | 28 | 16 | 18 | 16 |

| Ramię | zyski wg przyczyny | straty wg przyczyny |
|---|---|---|
| K | {'memory': 17} | {'memory': 9, 'copy': 3} |
| N' | {} | {'noise_before_memory': 1} |

**Reguła:** `{"verdict": "inconclusive", "K_minus_N": 5, "losses": 12, "K": 40, "N": 35, "N'": 34}`

## Tabela hipotez (aktualizacja)

| Hipoteza | Werdykt w NIGHT-2 (rozwojowo) |
|---|---|
| H14 (E1) | refuted |
| H14 (E3 repeat) | not_applicable (E* = R+) |
| H15 | refuted |
| H16 | supported |
| H10 (rozwojowo, E4) | K_not_ahead |
| test główny v0 | refuted |
| drugi model (E5) | inconclusive |

## Reguła rekomendacji egzaminu (decyzja należy do właściciela)

**WRÓCIĆ DO SKŁADNIKÓW**

Wskazanie składnika (mechanicznie): `{"K_failure_classes": {"error_resolved_turn_still_wrong": 15, "error_unresolved": 10, "no_error_wrong_or_extra_action": 26, "invalid_call_no_env_error": 1, "limit_steps": 2}, "K_loss_causes": {"memory": 5, "copy": 7}, "largest_failure_class": "no_error_wrong_or_extra_action"}`

Egzaminu na TradingBot program nie uruchamia.

