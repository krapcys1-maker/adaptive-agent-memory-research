# Charakterystyka reguł decyzyjnych przed zamrożeniem (P1)

Stan: gałąź `lab/p1-rule-calibration`, **niewdrożone**. Domyślnie wyłączone (`[lab.rule_check] required = false`), więc po scaleniu nie zmienia zachowania, dopóki właściciel tego nie włączy.

## Po co

Audyt z 2026-11-13 wykazał, że zamrożone reguły dawały werdykty, których dane nie uzasadniały. Tabela niżej porównuje liczby audytu z wynikami niezależnej symulacji z `aamr_coord/lab/rulecheck.py`. Werdykty historyczne pozostają bez zmian.

| Reguła | Audyt | Ten moduł |
|---|---|---|
| H16: próg +2 bez istotności, 8 par niezgodnych, brak efektu | 36,3% fałszywych wsparć | 0,3633 (dokładnie, 93/256) |
| Test główny NIGHT-2, rotacja 0,35, prawdziwe +10 zadań | wsparte 1,8%, obalone 83% | wsparte 1,4%, obalone 82,5% (bez warunków domenowych) |
| Test główny NIGHT-2, prawdziwe +18 zadań | 23% / 31% | 23,8% / 30,9% |
| Model bramki G2, powtórzenia deterministyczne, +5 pp | zamyka częściej, niż wspiera | wsparte 17%, zamknięte 33% |

## Co sprawdza bramka

Moduł działa jako czysta symulacja: nie otwiera bazy, nie czyta danych eksperymentów i nie zapisuje plików.

Odmawia zamrożenia, gdy zachodzi którykolwiek z warunków:

1. P(wsparcie | brak efektu) > `alpha_max` / liczność rodziny.
2. P(wsparcie | efekt = SESOI) < `power_min`. Protokół z `tier = "exploratory"` dostaje wtedy tylko ostrzeżenie, ale jego wynik nie zamyka kierunku i nie może być podstawą dalszych prac.
3. P(równoważność albo efekt ujemny | efekt = SESOI) > `false_close_max`. Ten warunek wyłapuje regułę „brak istotności = brak efektu”.
4. Stan nierozstrzygnięty jest nieosiągalny.
5. P(„praktycznie istotne” | efekt = SESOI/2) > `practical_leak_max`. Oznacza to, że reguła nie odróżnia efektu dodatniego od efektu praktycznie istotnego.
6. Brakuje deklaracji zależności obserwacji: ani `cluster_sizes` z `icc`, ani `independent_units` z uzasadnieniem.
7. Szum nie pochodzi z placebo ani perturbacji. Wartość |N′ − N| mierzy tylko niedeterminizm ponownego przebiegu.
8. Reguła liczy powtórzenia jako replikację, a ich korelacja wynosi co najmniej 0,9 (pseudoreplikacja), albo w regule ustawiono flagę `deterministic`.

Wyniki są zaliczane do kategorii:

| Kategoria | Znaczenie |
|---|---|
| `practical` | dolna granica przedziału ≥ SESOI |
| `positive` | efekt > 0, praktyczność nierozstrzygnięta |
| `inconclusive` | nierozstrzygnięte |
| `equivalent` | \|efekt\| < SESOI wykazane |
| `negative` | efekt < 0 wykazany |
| `invalid` | wynik nieważny |

Brak istotności daje `inconclusive`, nigdy `equivalent`.

## Użycie

```bash
python -m aamr_coord lab rulecheck --file reguła.json --n-sim 4000 --out raport.json
```

Kod wyjścia: 0 oznacza, że można zamrozić; 2 oznacza odmowę. Po włączeniu `required` dopuszczenie eksperymentu (`lab admit`) liczy charakterystykę od nowa ze specyfikacji przypiętej skrótem przy propozycji (`params.rule_spec_path`). Raportu autora nie przyjmuje.

## Decyzje właściciela (otwarte)

- Progi: `alpha_max` 0,05, `power_min` 0,80, `false_close_max` 0,05, `practical_leak_max` 0,25. To są propozycje i stanowią decyzję naukową.
- SESOI dla pamięci doświadczeń: strategia mówi o 5 pp, ale przy 88 zadaniach żadna reguła nie ma wtedy mocy.
- Włączenie `[lab.rule_check] required = true` i od kiedy.
- Model zależności dla BFCL: klastry według zadania źródłowego czy domeny, oraz wartość `icc`.
- Wymóg placebo jako źródła szumu dla K1. Specyfikację K1 przygotowuje inna sesja, a ten moduł jej nie dotyka.
