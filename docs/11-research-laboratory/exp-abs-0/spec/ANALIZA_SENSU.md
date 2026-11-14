# EXP-A v0.2: czy ten eksperyment ma sens?

2026-11-14. Claude (Opus 5.5). Podstawa: `SPEC_EXP_A_v0.2.md`, `power/expA_power_v02.out`, audyt v0.1, dane K1 i NIGHT-2 (tylko odczyt).

## 1. Krótko

**Tak, ma sens, ale jako eksperyment rozstrzygający jedną gałąź badań, a nie jako droga do poprawy benchmarku.** Po poprawkach v0.2 każdy prawdopodobny wynik prowadzi do konkretnej decyzji, a koszt pieniężny wynosi zero. Nie ma powodu, by uruchamiać go teraz: pakiet jest gotowy i może poczekać. Przed startem zostaje do zrobienia wykonawca epizodów i etap T.

## 2. Co eksperyment daje, a czego nie

| Daje | Nie daje |
|---|---|
| Przyczynowy test: czy usunięcie wartości zdejmuje więcej szkody niż pomocy, na dwóch poziomach (dobór, cała treść bloku) | Dowodu poprawy pamięci na benchmarku. Nawet najlepszy wynik to około +4–6 pp na 148 zadaniach, poniżej rozdzielczości tego benchmarku. |
| Odpowiedź na Twoje pytanie o **część** strat, odporną na ogólne osłabienie bloku | Rozdzielenia „kopii wartości argumentów” od „faktów z wyników narzędzi” (znaczniki tylko wskazują) |
| Wynik dla tej reguły abstrakcji, na 54 zadaniach o powtarzalnym efekcie | Uogólnienia na inne zadania czy modele |

## 3. Mapa decyzji: co zrobisz po każdym wyniku

| Wynik | Szacowane prawdopodobieństwo* | Co oznacza | Następny krok |
|---|---|---|---|
| POPARCIE (dowolne) | wysokie, jeśli H_D prawdziwa (90–100%) | Kopiowanie wartości niesie część szkody ponad ogólne osłabienie; abstrakcja to obiecująca naprawa reprezentacji. | Etap 2: większy instrument (propozycja B z audytu K1) z ramieniem M-abs, około 20 000 wywołań. |
| OBALENIE / KIERUNEK_PRZECIWNY | 48–86% w scenariuszu zgodnym z M2 | Usunięcie wartości zabiera bardziej pomoc niż szkodę; abstrakcja w tej postaci nie jest naprawą. | Zamknąć gałąź abstrakcji. Przejść do bramkowania lub momentu użycia (propozycja C) albo do instrumentu B bez abstrakcji. |
| NIEROZSTRZYGNIĘTE | około 96% przy jednakowym osłabieniu; 22–52% w scenariuszu M2 | Brak wykrywalnej asymetrii: abstrakcja zmienia pomoc i szkodę mniej więcej jednakowo, więc nie naprawia bilansu. | Jak przy obaleniu, ze słabszą pewnością. Przedział Δ pokazuje, jak dużą asymetrię wykluczono. |

\* Prawdopodobieństwa pochodzą z symulacji dla zadanego scenariusza; to nie są prawdopodobieństwa scenariuszy.

Każdy wynik zmienia więc kierunek prac. Wynik „pusty”, który nic nie rozstrzyga, jest możliwy głównie przy osłabieniu efektów K1 (25% mniej) połączonym z częściową asymetrią; wtedy rozstrzygnięcie zapada w około 50–70% prób.

## 4. Co jest najbardziej prawdopodobne

- **Przeciw H_D:** maskowanie M2 w NIGHT-2 straciło większość pomocy (4 z 11) i nie przywróciło wyniku na zadaniach straty (2 z 9); pojedyncze losowania, ale kierunek jest wyraźny. Ponadto 79% epizodów M w L kończy się porażką także bez żadnej kopii wartości.
- **Za H_D lub jej częścią:** w K1 kopia wartości współwystępuje z porażką w L zarówno w M (1 z 35 rozwiązanych), jak i w S (3 z 22). W G kopia nie współwystępuje z sukcesem.
- **Moja ocena:** najbardziej prawdopodobne są OBALENIE lub NIEROZSTRZYGNIĘTE na poziomie swoistym. Na poziomie treści (Δ_treści) wynik dodatni ma realną szansę, bo właśnie tam dane K1 pokazują kopiowanie z losowych śladów. Niepewność jest prawdziwa, więc eksperyment niesie informację. Gdyby wynik był z góry przesądzony, nie byłoby po co go robić.

## 5. Koszt

| Pozycja | Wielkość |
|---|---|
| Wywołania modelu | około 18 000 (prognoza 18 036) + etap T do 300; limit 22 000 |
| Czas maszyny | około 7 h lokalnej Ollamy, 0 USD |
| Praca do wykonania | wykonawca epizodów (adaptacja `worker.py`/`supervisor.py` z K1 do 6 ramion i zamrożonego pliku bodźców), etap T, integracja z koordynatorem, raport. Bodźce, analiza, moc i testy są gotowe. |
| Koszt naukowy | szóste użycie tych samych 54 zadań i śladów; ta sama pula nie posłuży już jako „świeży” zbiór dla tej hipotezy |

## 6. Alternatywy

| Opcja | Kiedy lepsza od EXP-A |
|---|---|
| **B: instrument na poziomie tury** (około 20 600 wywołań) | Gdy ważniejsze jest pytanie „czy pamięć w ogóle pomaga średnio”, a nie „dlaczego szkodzi”. K1 sugeruje średnio około +2 pp, więc B prawdopodobnie da „brak średniej korzyści” z węższym przedziałem. Wymaga jawnego użycia odpowiedzi wzorcowych do odtworzenia stanu. |
| **C: moment użycia** (blok dopiero po błędzie narzędzia) | Gdy celem jest praktyczna poprawa bilansu. Audyt K1 uzależnił jego sens od wyniku A; przy obaleniu A to naturalny następny krok. |
| **Nic na razie** | Gdy nie planujesz dalszych prac nad reprezentacją pamięci. Wtedy EXP-A nie zmieni żadnej decyzji. |
| Dalsza analiza istniejących danych | Bez wywołań nie da wyniku przyczynowego; obserwacyjne dane K1 są już opisane. |

## 7. Rekomendacja

1. **Zatwierdzić v0.2 jako kandydata do zamrożenia** (decyzje DB1–DB5 w spec. 13). Nie zamrażać jeszcze, skoro nie planujesz startu: zamrożenie warto zrobić tuż przed budową wykonawcy, żeby nie trzeba było go cofać.
2. **Nie uruchamiać teraz.** Nic nie traci ważności: bodźce są deterministyczne, a test T3 potwierdza identyczną przebudowę.
3. **Gdy zdecydujesz się dalej pracować nad pamięcią:** najpierw EXP-A, bo rozstrzyga, czy gałąź abstrakcji w ogóle istnieje. Potem C albo B, zależnie od wyniku. Jeśli Twoim priorytetem jest pytanie o średni efekt, a nie o mechanizm, kolejność odwraca się na B → A.
4. **Przed startem:** przegląd 30 losowych bloków abstrakcyjnych (DB5), budowa wykonawcy z testami jak w K1, etap T i sprawdzenie, czy prognoza wywołań mieści się w 20 000.
