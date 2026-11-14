# K1 (EXP-PLACEBO-0): raport końcowy (generowany z zamrożonych danych)

> ZASADA INTERPRETACJI (D1): próg 10 pp służy wyłącznie pytaniu, czy efekt sięga 10 pp. Efekty mniejsze niż 10 pp mogą być rzeczywiste i użyteczne. Brak wykazania efektu 10 pp ani brak wykrycia efektu nie są dowodem braku korzyści z pamięci.

## Odczyt (kod `k1_v04_reading.read`)

- M - P: nic nie rozstrzygnięto; przedział [-6,0; 11,4] pp obejmuje zarówno zero, jak i 10 pp (format, domena i dobór łącznie).
- M - X: nic nie rozstrzygnięto; przedział [-4,4; 12,5] pp obejmuje zarówno zero, jak i 10 pp (domena i dobór przy stałym formacie śladu).
- M - S: efektu nie wykryto; przedział [-8,1; 7,7] pp dopuszcza efekty najwyżej do 7,7 pp (dobór śladów do zadania). Wynik wyklucza, że ten składnik w reżimie próbkowanym daje tyle, ile cały historyczny zysk M - N przy temperaturze 0 (8,1 pp). DŁUGOŚĆ (WR5): po korekcie długości stan V4 zamiast V5. Różnica długości bloków może wyjaśniać ten wynik; efektu nie przypisuje się treści pamięci.
- ZŁOŻONE-C: żaden kontrast nie wykrył efektu. To nie jest dowód braku efektu treści.
- OPISOWO (bez stanu): M - N = 1,8 pp (95%: -5,5; 9,1); P - N = -0,9 pp (95%: -6,2; 4,4). Efekty kontrastów liczone są względem ramion kontrolnych, nie względem braku bloku.
- PRZENOSZALNOŚĆ (nie zmienia stanu głównego): M - S: wykryto zależność przez wspólne ślady (ρ̃ = +0.030, p = 0.016); stan przy przedziale poszerzonym x1.23: V5.
- M - S: zależny od domeny (warstwa E3-VC: 16,7 pp, 95% wyklucza 0 ze znakiem przeciwnym).
- Kontrola dryfu bloku A niespełniona (zgodność N lub M z NIGHT-2 poniżej progu); stany z bloków próbkowanych pozostają ważne.

## Stan bloków i bramek

- bloki próbkowane: `{"S1": "done", "S2": "done", "S3": "done", "A": "done"}`
- ukończone i użyte: `["S1", "S2", "S3"]`; wykluczone zadania: 0
- bramki i etap T: `{"T.json": {"status": "done", "gpu_full": true, "digest_ok": true, "ollama": {"version": "0.40.16"}, "api_ps": [{"name": "qwen2.5:14b-instruct", "model": "qwen2.5:14b-instruct", "size": 10290085231, "digest": "7cdf5a0187d5c58cc5d369b255592f7841d1c4696d45a8c8a9489440385b22f6", "details": {"parent_model": "", "format": "gguf", "family": "qwen2", "families": ["qwen2"], "parameter_size": "14.8B", "quantization_level": "Q4_K_M"}, "expires_at": "2026-11-13T22:55:57.9344914+02:00", "size_vram": 10290085231, "context_length": 8192, "runner": "llamacpp"}], "reason": null}, "c_d.json": {"rho_M": {"GFS": 0.25240302094061107, "TRAVEL": 0.2980022341724469, "VC": 0.28990261669206724}, "ref_check": [{"task": "multi_turn_base_63", "rep": 1, "prompt_eval_count": 1209, "reference": 1209}, {"task": "multi_turn_base_63", "rep": 2, "prompt_eval_count": 1209, "reference": 1209}, {"task": "multi_turn_base_31", "rep": 1, "prompt_eval_count": 1686, "reference": 1686}, {"task": "multi_turn_base_31", "rep": 2, "prompt_eval_count": 1686, "reference": 1686}, {"task": "multi_turn_base_171", "rep": 1, "prompt_eval_count": 1744, "reference": 1744}, {"task": "multi_turn_base_171", "rep": 2, "prompt_eval_count": 1744, "reference": 1744}], "c_d": {"VC": 1.28691627736434, "GFS": 1.114161374299119, "TRAVEL": 1.3325808477237049}, "status": "done", "at": "2026-11-13T20:46:52.831046+00:00"}, "P_check.json": {"blocks": 2056, "header_failures": 0, "max_len_dev": 6, "L4b_max": 0.019417475728155338, "pass": true, "p_blocks_sha256": "785d073b1133b89cf4d71a134d08446a2b2de6fc8d0a4b07d119d612ec1a5032"}, "T_m.json": {"tasks": ["multi_turn_base_54", "multi_turn_base_69", "multi_turn_base_75", "multi_turn_base_96", "multi_turn_base_19", "multi_turn_base_5", "multi_turn_base_36", "multi_turn_base_25", "multi_turn_base_179", "multi_turn_base_196", "multi_turn_base_198", "multi_turn_base_155"], "calls": [10, 8, 10, 7, 8, 8, 16, 11, 10, 11, 5, 4], "mean": 9.0, "at": "2026-11-13T20:49:02.943152+00:00"}, "gate_A.json": {"m": 9.0, "P_A": 4396, "P_S": 7326, "used": 177, "need": 19048, "go": true}, "gate_S1": {"m": 9.0, "P_S": 7326, "used": 4415, "need": 7326, "go": true}, "gate_S2": {"m": 9.570478723404255, "P_S": 7791, "used": 11504, "need": 7791, "go": true}, "gate_S3": {"m": 9.61260053619303, "P_S": 7825, "used": 18649, "need": 7825, "go": true}}`
- kontrola przecieków po przebiegu: `{"violations": 0, "checked_sources": 9686, "examples": []}`

## Kontrasty główne

| kontrast | estymata pp | przedział | stan | ρ̂ | ρ̃ | p | ρ* | WR4 (88) | LEN |
|---|---|---|---|---|---|---|---|---|---|
| M - P | +2.7 | [-6.0; 11.4] | V4 | -0.024 | +0.017 | 0.119 | brak | V4 | False |
| M - X | +4.1 | [-4.4; 12.5] | V4 | -0.044 | -0.003 | 0.581 | brak | V4 | False |
| M - S | -0.2 | [-8.1; 7.7] | V5 | -0.011 | +0.030 | 0.016 | 0.039 | V4 | True |

## Drabina opisowa (95%)

```json
{
 "P-N": {
  "estimate": -0.9009009009009014,
  "ci95": [
   -6.183208737441349,
   4.381406935639546
  ],
  "tasks": 148
 },
 "X-P": {
  "estimate": -1.3513513513513509,
  "ci95": [
   -6.279388474980319,
   3.5766857722776173
  ],
  "tasks": 148
 },
 "S-X": {
  "estimate": 4.279279279279279,
  "ci95": [
   -1.7550806818355413,
   10.3136392403941
  ],
  "tasks": 148
 },
 "M-S": {
  "estimate": -0.2252252252252251,
  "ci95": [
   -6.681671743896465,
   6.231221293446015
  ],
  "tasks": 148
 },
 "M-N": {
  "estimate": 1.8018018018018018,
  "ci95": [
   -5.530853249723093,
   9.134456853326697
  ],
  "tasks": 148
 }
}
```

## Blok A (temperatura 0)

```json
{
 "M-P": {
  "estimate_pp": 4.72972972972973,
  "interval95": [
   -4.4232512561733355,
   13.882710715632795
  ],
  "tasks": 148,
  "state": "V4"
 },
 "excluded": 0
}
```

## Kontrola dryfu

```json
{
 "E3/N": {
  "agree": 86,
  "of": 88,
  "min": 84,
  "ok": true
 },
 "E3/M": {
  "agree": 83,
  "of": 88,
  "min": 84,
  "ok": false
 },
 "E3/P-vs-N discordant": 22,
 "E3/M-vs-N discordant": 33,
 "E1/N": {
  "agree": 57,
  "of": 60,
  "min": 57,
  "ok": true
 },
 "E1/M": {
  "agree": 55,
  "of": 60,
  "min": 57,
  "ok": false
 },
 "E1/P-vs-N discordant": 12,
 "E1/M-vs-N discordant": 18,
 "NIGHT-2 M-vs-N discordant (E3 34/88, E1 20/60)": "reference"
}
```

## Pomiar szumu

```json
{
 "w": {
  "N": 0.15315315315315317,
  "P": 0.21171171171171174,
  "X": 0.18468468468468469,
  "S": 0.2522522522522523,
  "M": 0.1801801801801802
 },
 "b": {
  "M,N": 0.3153153153153153,
  "M,P": 0.32882882882882886,
  "M,X": 0.2972972972972973,
  "M,S": 0.3130630630630631
 },
 "variance": {
  "MP": {
   "var_rep": 0.20945945945945948,
   "var_task": 0.11992094134951273,
   "tasks_needed": {
    "half 2.5 pp, R=1": 3021,
    "half 2.5 pp, R=3": 1740,
    "half 2.5 pp, R=5": 1484,
    "half 5.0 pp, R=1": 756,
    "half 5.0 pp, R=3": 435,
    "half 5.0 pp, R=5": 371
   }
  },
  "MX": {
   "var_rep": 0.17792792792792794,
   "var_task": 0.11893015464444037,
   "tasks_needed": {
    "half 2.5 pp, R=1": 2723,
    "half 2.5 pp, R=3": 1635,
    "half 2.5 pp, R=5": 1417,
    "half 5.0 pp, R=1": 681,
    "half 5.0 pp, R=3": 409,
    "half 5.0 pp, R=5": 355
   }
  },
  "MS": {
   "var_rep": 0.23423423423423426,
   "var_task": 0.07989111560540134,
   "tasks_needed": {
    "half 2.5 pp, R=1": 2881,
    "half 2.5 pp, R=3": 1449,
    "half 2.5 pp, R=5": 1163,
    "half 5.0 pp, R=1": 721,
    "half 5.0 pp, R=3": 363,
    "half 5.0 pp, R=5": 291
   }
  }
 },
 "vs_simulation": {
  "w_measured": 0.19639639639639642,
  "w_assumed": [
   0.02,
   0.28
  ],
  "b_measured": 0.31362612612612617,
  "b0_columns": [
   0.2,
   0.3,
   0.38
  ],
  "column": 0.3,
  "pilot_measured_spec_9_0": {
   "w": 0.159,
   "b": 0.307,
   "detect_10pp": 0.643,
   "exclude_10pp_at_0": 0.615
  },
  "note": "3 bloki"
 }
}
```

## Tokeny na znak (tura 0)

```json
{
 "M/TRAVEL": 0.31530194332206374,
 "S/TRAVEL": 0.30594563271943886,
 "P/TRAVEL": 0.2320790717662226,
 "X/TRAVEL": 0.30297397769516726,
 "M/GFS": 0.27813504823151125,
 "X/GFS": 0.3136860867437878,
 "P/GFS": 0.2456527583230754,
 "S/GFS": 0.2756520068522758,
 "P/VC": 0.2324662379079032,
 "S/VC": 0.30422058427221277,
 "X/VC": 0.27702751793660885,
 "M/VC": 0.3073699778161203
}
```

## Tokeny promptu na wywołanie

```json
{
 "N": 2037.6766899766899,
 "P": 2398.1879936808846,
 "X": 2373.430184331797,
 "S": 2395.8092402953084,
 "M": 2399.8932297985925
}
```

## Błędne wywołania

```json
{
 "N": {
  "invalid_outputs": 0,
  "invalid_calls": 204,
  "nonexistent_functions": 0
 },
 "P": {
  "invalid_outputs": 9,
  "invalid_calls": 149,
  "nonexistent_functions": 0
 },
 "X": {
  "invalid_outputs": 0,
  "invalid_calls": 122,
  "nonexistent_functions": 0
 },
 "S": {
  "invalid_outputs": 1,
  "invalid_calls": 120,
  "nonexistent_functions": 0
 },
 "M": {
  "invalid_outputs": 1,
  "invalid_calls": 165,
  "nonexistent_functions": 0
 }
}
```

## Zyski i straty wobec N

```json
{
 "P": {
  "gains": 29,
  "losses": 29
 },
 "X": {
  "gains": 24,
  "losses": 31
 },
 "S": {
  "gains": 37,
  "losses": 30
 },
 "M": {
  "gains": 42,
  "losses": 36
 }
}
```

## Miara L9

```json
{
 "M": {
  "by_task_pct": 18.461920500863023,
  "by_turn_block_pct": 16.965656479275157
 },
 "S": {
  "by_task_pct": 12.584778159095222,
  "by_turn_block_pct": 10.874991847754494
 },
 "X": {
  "by_task_pct": 0.09652509652509651,
  "by_turn_block_pct": 0.09727626459143969
 }
}
```

## Odsetki rozwiązań (%)

```json
{
 "N": 32.88288288288288,
 "P": 31.981981981981978,
 "X": 30.630630630630627,
 "S": 34.909909909909906,
 "M": 34.68468468468468
}
```

## Kontrola długości (sek. 11 pkt 8)

```json
{
 "P/M per block, turn 0 (exact tokens), q05/50/95": [
  0.9003831417624522,
  0.9821428571428571,
  1.0666666666666667
 ],
 "c_d": {
  "VC": 1.28691627736434,
  "GFS": 1.114161374299119,
  "TRAVEL": 1.3325808477237049
 },
 "S/M per turn (predicted tokens), q05/50/95": [
  0.8082099801136402,
  0.9624885313646805,
  1.1712538455290642
 ],
 "X/M per turn (predicted tokens), q05/50/95": [
  0.7907510844450085,
  0.985928863963282,
  1.202868317244078
 ]
}
```

## Tokeny promptu względem M

```json
{
 "N": [
  -0.15093027278230253,
  true
 ],
 "P": [
  -0.0007105466595491716,
  false
 ],
 "X": [
  -0.011026759498386607,
  false
 ],
 "S": [
  -0.0017017379992471104,
  false
 ]
}
```

## Kontrole przygotowania L1–L4b, L10

```json
{
 "G1_rows": 114,
 "G2_keys": 520,
 "L1": {
  "M": {
   "checked": 1022,
   "violations": 0
  },
  "S1": {
   "checked": 1022,
   "violations": 0
  },
  "S2": {
   "checked": 1022,
   "violations": 0
  },
  "S3": {
   "checked": 1022,
   "violations": 0
  },
  "X1": {
   "checked": 1022,
   "violations": 0
  },
  "X2": {
   "checked": 1022,
   "violations": 0
  },
  "X3": {
   "checked": 1022,
   "violations": 0
  }
 },
 "L2": {
  "own_task_detected": true,
  "test_source_detected": true
 },
 "L3_violations": {
  "1": 0,
  "2": 0,
  "3": 0
 },
 "L4a_domain_stems": 408,
 "L4a_domain_words": 451,
 "L4a_failures": 0,
 "L4b_max": 0.0196078431372549,
 "P_blocks_checked": 2056,
 "P_len_dev_max": 6,
 "T_tasks": {
  "cal": {
   "GFS": 10,
   "TRAVEL": 10,
   "VC": 10
  },
  "len": {
   "GFS": 10,
   "TRAVEL": 10,
   "VC": 10
  },
  "len2": {
   "GFS": 10,
   "TRAVEL": 10,
   "VC": 10
  },
  "m_tasks": 12,
  "recal": {
   "GFS": 20,
   "TRAVEL": 20,
   "VC": 20
  }
 },
 "corpus_sentences": 199,
 "draw_rule": "D12 log rule of the frozen prototype t_d9_length.py: |ln(predicted/target)| <= ln 1.2, i.e. -16.67%..+20%; 200 attempts, else closest by |ln| (owner choice C2, 2026-11-13; formal status: ANEKS_C2_D12.md)",
 "failures": [],
 "header_failures": 0,
 "predicted_length_imbalance_pct": {
  "S": 2.31,
  "X": 1.83
 },
 "shared_graph": {
  "definition": "traces of the turns recorded in NIGHT-2 M episodes (v0.3)",
  "first_trace_groups": 68,
  "pairs": 1260,
  "pairs_full_plan_variant": 1314
 },
 "tasks": 148
}
```

