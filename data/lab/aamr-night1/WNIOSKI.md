# AAMR-NIGHT-1: wnioski (13.11.2026)

Raport liczbowy, wygenerowany automatycznie według zamrożonych reguł: `REPORT.md` i `results.json`. Ten plik to interpretacja. Analiza dodatkowa (rozbieżność przebiegów, szkody, zgodność z lekcjami) powstała **po** obejrzeniu wyników, więc ma status eksploracyjny: `scripts/aamr_night1_followup.py` → `followup.json`.

## 0. Przebieg i integralność

- Program wystartował o 21:42 i skończył o 00:33. Przeszedł wszystkie 12 etapów, bez błędów (`errors.log` pusty) i bez restartów. Uruchamiał go Harmonogram zadań, bez udziału sesji Claude.
- `raw-freeze.json` zawiera sha256 17 surowych plików. Po zakończeniu przeliczyłem je ponownie: 0 rozbieżności. Skrypt analizy dodatkowej sprawdza te sumy przed każdym odczytem.
- Przed sesją sA wprowadziłem trzy poprawki techniczne, opisane w `PROTOCOL.md` §6. Po zobaczeniu wyników nie zmieniłem żadnej hipotezy, progu, reguły ani zbioru zadań.

## 1. EXP-FIX-0: czy poprawna treść podana przy błędzie naprawia porażkę

| Sesja (model, zadania) | N | N′ | Tr | TrP (placebo) | TrO (wyrocznia) | reguła |
|---|---|---|---|---|---|---|
| sA (Qwen2.5 14B, 30 testowych VC) | 9 | 9 | 12 | 12 | **15** | supported |
| sC (14B, 20 treningowych VC) | 6 | – | – | 6 | 8 | inconclusive |
| sE (Qwen3.5 9B, 30 testowych VC) | 10 | 10 | 13 | 13 | **19** | supported |

- **Werdykt dla 14B: „supported”, ale dokładnie na progach.** Zysk TrO względem N wynosi +6 przy progu 5. Wartość p z testu McNemara to 0,035 jednostronnie i 0,07 dwustronnie. Przewaga TrO nad placebo to +3 przy progu 3. Tury z błędem pojemności baku: 4/8 zaliczonych przy progu 1/2. Gdyby jedno zadanie wypadło inaczej, reguła by nie przeszła.
- **Mechanizm widać bezpośrednio** (tury z błędem pojemności baku, eksploracyjnie):
  - TrO w 8/8 tur odczytał poziom paliwa i dolał dokładnie do 50.
  - Placebo zaliczyło 0/8 tur, N 1/9.
- **Na 9B efekt jest wyraźny:** +9 przy 9 zyskach i 0 stratach (p = 0,002). TrO ma +6 nad placebo i zalicza 7/10 tur z błędem baku.
- **Replikacja na 20 zadaniach treningowych VC wyszła nierozstrzygnięta:** +2 przy 0 stratach, placebo +0.
- Powtórzenie N′ nie zmieniło żadnego wyniku. W sA rozbiegło się z N w 1/30 epizodów, w sE w 0/30.
- **Wniosek.** Dostarczanie treści w momencie błędu działa, jeśli treść jest poprawna. Kierunek TrO > placebo > N powtórzył się we wszystkich trzech sesjach i na dwóch modelach. Na danych rozwojowych hipoteza H5 jest utrzymana.
- **Czego nie wiadomo.** Nadal nie ma automatycznego sposobu na wytworzenie takiej treści. Wyrocznię napisałem ręcznie.

Skąd się bierze +3 dla Tr (lekcje deterministyczne) i dla placebo (TrP = Tr + placebo przy błędzie baku)? Rozbieżność trajektorii zaczyna się po notatce o `startEngine`. Jednak test na stanach treningowych pokazuje, że te błędy agent rozwiązuje sam w 10/10 przypadków. W 3 z 4 zyskanych zadań różnica polega na czym innym: po notatce agent nie wykonuje na końcu zbędnego `releaseBrakePedal()`. To uboczny efekt notatki, a nie naprawa samego błędu.

## 2. Pisarze lekcji: deterministyczne / lokalny Qwen / DeepSeek Flash

| | N | deterministyczne | Qwen (TrQ) | Flash (TrF) | reguła z protokołu |
|---|---|---|---|---|---|
| sA, VC (rozwojowe, 30) | 9 | 12 | 12 | **17** | `flash_better` (+5 nad najlepszym lokalnym, p = 0,031) |
| sD, GFS+Travel (nietknięte, 58) | 17 | 19 | **22** | 21 | `no_detected_difference` (−1) |
| test na stanach treningowych (19 stanów; rozwiązane błędy) | 13 | – | 15 | 18 | obie lekcje dopuszczone |

- **Przewaga Flash na VC wynika głównie z jednej sygnatury błędu: paliwa.**
  - Lekcja Qwena o paliwie jest merytorycznie błędna: „tank is already full (50 gallons) … If full, no action needed”. Mimo to przeszła wszystkie kontrole deterministyczne. W turach z tym błędem agent z lekcją Qwena w 5/9 rezygnował z tankowania i zaliczył 1/9.
  - Lekcja Flash jest poprawna („only the difference needed to reach 50”). Agent zaliczył z nią 6/9 tur, więcej niż z wyrocznią (4/8). Liczba błędów narzędzi spadła z 87 (N) do 47.
- **Na nietkniętych domenach systemu plików i podróży różnicy nie wykryto.** TrQ zmniejszył liczbę błędów narzędzi z 219 do 178, TrF tylko do 215.
- **Kontrole deterministyczne sprawdzają nazwy i wycieki, ale nie prawdziwość treści.** Bramka B liczona łącznie dopuściła błędną lekcję Qwena.
  - W rozbiciu na sygnatury sygnał był widoczny: przy paliwie bez notatki agent rozwiązał 2/6 błędów, z lekcją Qwena 3/6, z Flash 5/6, z wyrocznią 5/6.
  - Bramka liczona dla każdej lekcji osobno prawdopodobnie odrzuciłaby lekcję Qwena. To obserwacja post hoc, wymaga osobnego testu.
- **Koszt pisania lekcji:**
  - Flash: 20 lekcji, 0,015 USD według górnego oszacowania.
  - Qwen: 20 lokalnych wywołań.
  - Lekcje deterministyczne: 0 wywołań. W nowych domenach kompilator wytworzył jednak tylko po 2 lekcje na domenę, więc notatka pokazała się 12 razy na 58 zadań.
- **Odpowiedź na pytanie z zadania.** Czy DeepSeek pomaga bardziej niż rozwiązanie lokalne? Na danych rozwojowych tak, ale wyłącznie dzięki jednej lekcji, w której lokalny pisarz się pomylił. Na danych potwierdzających tak nie jest. Domyślny wybór to pisarz lokalny (0 USD). Flash ma sens jako drugi pisarz, gdy lekcja lokalna nie przejdzie weryfikacji; kosztuje ok. 0,0008 USD za lekcję.

## 3. Transfer na nietknięte zadania: jedyny test potwierdzający

- **Test główny TrD > N nie został potwierdzony:** 19 vs 17, +2, p = 0,25.
- **W rodzinie Holma żadne ramię nie przeszło progu:**
  - TrQ: +5, p = 0,09.
  - TrF: +4, p = 0,14.
  - R+: +5, p = 0,20, przy 14 zyskach i 9 stratach.
- **Lekcje deterministyczne prawie nie zadziałały, bo prawie się nie pokazywały.** Z 23 epizodów TrD, które rozbiegły się z N, 15 rozbiegło się jeszcze przed jakąkolwiek notatką, czyli z powodu szumu.
- **Szum był tu większy niż na VC.** Powtórzenie N′ rozbiegło się z N w 13/58 epizodów, choć w żadnym nie było pamięci. Wynik zmienił się w 1/58 zadań. Ollama przy dłuższych kontekstach nie jest deterministyczna mimo temperatury 0.
- **Eksploracyjnie, w podziale na domeny:**
  - R+ (wcześniejsze udane trajektorie): system plików 10 vs 4, podróże 12 vs 13.
  - Lekcje: podróże 16 vs 13, system plików 5–6 vs 4.
  - Pomocny rodzaj pamięci może zależeć od domeny. Ta hipoteza nie była zarejestrowana z góry.

## 4. Szkody pamięci

- **Nieaktualna lekcja (TrS, „40 gallons”).** Agent wykonał ją dosłownie w 6/8 tur z błędem baku i zaliczył 0/8. Nie sprawdził stanu, choć `displayCarStatus` był pod ręką. Netto względem N szkoda jest niewielka, bo N i tak zalicza te tury w 1/9. Agent jednak ślepo słucha pamięci, więc pamięć błędna lub nieaktualna przenosi się wprost na działanie.
- **Wszystkie ramia z pamięcią w sA tracą to samo zadanie 60.**
  - Użytkownik mówi tam, że już zatankował. N zalicza je przypadkiem: błędna próba tankowania kończy się błędem pojemności.
  - Po notatce agent tankuje skutecznie, a to zmienia stan i powoduje porażkę.
  - Pamięć pomogła tu wykonać źle zrozumiane polecenie.
- **sD:**
  - TrQ: 2 straty, obie po notatce.
  - TrF: 2 straty, 1 po notatce, 1 z szumu.
  - R+: 9 strat, wszystkie po bloku pamięci. Ta pamięć zmienia najwięcej: rozbiega się z N we wszystkich 58 epizodach.
- **Koszt użycia pamięci:** od −2% do +10% tokenów wejścia względem N (najwięcej TrQ w sA). Liczba wywołań modelu praktycznie się nie zmienia.

## 5. Koszty

| Pozycja | Zużycie | Limit |
|---|---|---|
| Lokalne wywołania (program + 66 testu dymnego) | 9 219, 0 ponowień | 12 000 |
| w tym Qwen2.5 14B / Qwen3.5 9B | 7 244 (2 h 24 min GPU) / 1 909 (20 min) | – |
| DeepSeek Flash (program + 2 testu dymnego) | 22 wywołania | 200 |
| Koszt API: górne oszacowanie z liczby tokenów / zarezerwowane | 0,016 USD / 0,22 USD | 3 USD |
| Płatne Claude API | 0 | 0 |

Według bucketów: A 1 822, B 820, H 307, D 3 697, C 598, E 1 909, T 66. Żaden bucket nie został wyczerpany, a z planu sD nie trzeba było usuwać żadnego ramienia.

## 6. Błędy i ograniczenia

1. **Wyniki VC (sA, sC, sE) mają status rozwojowy.** Zadania znamy z pilota i z S1. Reguła EXP-FIX-0 na 14B przeszła na samych progach.
2. **Mała próba:** 30, 20 i 58 zadań, jeden przebieg na ramię. Porównania w sA nie są korygowane na wielokrotność; korekta Holma objęła tylko rodzinę w sD.
3. **N′ mierzy wyłącznie losowość ponownego przebiegu.** Nie mierzy wpływu samej zmiany kontekstu. Ten wpływ kontroluje placebo, a w sA i sE placebo samo dawało +3.
4. **Bramka B oceniała pisarza łącznie, nie każdą lekcję osobno**, i przepuściła błędną treść. Kontrole deterministyczne nie badają, czy treść jest prawdziwa.
5. **Kontrola wycieków odrzuciła dwie poprawne lekcje.** Lekcję Flash o `echo` odrzuciła przez słowo „Before” jako token występujący tylko w zadaniach testowych. Lekcję Qwena o `mv` odrzuciła przez przykładową nazwę `source_file`. To błędy ostrożnościowe, czyli wykluczenia, a nie wycieki.
6. **Ollama nie jest deterministyczna przy dłuższych kontekstach** (13/58 rozbieżności w sD). Część różnic w sD to szum.
7. **Zbiór jest jeden:** BFCL multi-turn base. Drugi model sprawdziłem tylko na VC. Konkurentów nie testowałem w naszym harnessie, więc nadal nie mogę twierdzić, że to „lepsze niż konkurencja”.
8. **Nietknięte zadania GFS i Travel są już wykorzystane.** W bazie BFCL nieużywana pozostaje tylko domena TradingBot (zadania 100–149), trzymana w rezerwie.

## 7. Rekomendacja następnego eksperymentu

**Najcenniejszy problem: jak automatycznie wytwarzać poprawną treść na moment błędu i weryfikować ją przed dopuszczeniem do pamięci.** Wskazują na to trzy wyniki tej nocy:

1. Poprawna treść działa: wyrocznia na dwóch modelach, lekcja Flash o paliwie.
2. Agent wykonuje treść błędną: lekcja nieaktualna w 6/8 tur, błędna lekcja Qwena w 5/9 tur bez tankowania.
3. Obecne kontrole błędnej treści nie wychwytują.

**Proponowany eksperyment EXP-VER-1: weryfikacja każdej lekcji przed dopuszczeniem.**

- **Jak działa.** Każda kandydująca lekcja (deterministyczna, Qwen, Flash) przechodzi test na stanach treningowych, w których wystąpiła jej sygnatura. Dopuszczam ją tylko wtedy, gdy rozwiązuje więcej błędów niż brak notatki i placebo, a liczba zaliczonych tur nie spada.
- **Koszt.** Ok. 20 lokalnych wywołań na lekcję. Flash wchodzi tylko jako zapasowy pisarz dla lekcji, które nie przejdą weryfikacji.
- **Pomiar.** Pamięć z weryfikacją kontra bez weryfikacji kontra N kontra placebo.
- **Ochrona przed nieaktualną treścią.** Do lekcji dodać jedno zdanie, które każe najpierw sprawdzić bieżący stan środowiska, a dopiero potem zastosować liczby z lekcji. Szkodę sprawdzić ramieniem TrS.
- **Zbiór potwierdzający to decyzja właściciela.** Jedyną czystą opcją jest rezerwa TradingBot, z protokołem zamrożonym przed pierwszym wywołaniem. Warianty BFCL takie jak `miss_param` czy `long_context` dzielą pytania z bazą, więc grozi przeciek.

Etap 1 strategii, czyli konkurenci uruchomieni w tym samym harnessie, nadal jest warunkiem twierdzenia „lepszy niż konkurencja”. Nie zmieniam celu projektu na podstawie jednego eksperymentu.
