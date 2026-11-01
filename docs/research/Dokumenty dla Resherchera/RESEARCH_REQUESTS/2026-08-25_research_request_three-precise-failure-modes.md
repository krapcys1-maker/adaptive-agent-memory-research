---
id: arr-2026-08-25-001
type: RESEARCH_REQUEST
status: OPEN
created: 2026-08-25
source: AAMR
target: ResearchOS
priority: HIGH
target_failure: trzy konkretne, nazwane failure modes (patrz niżej) -- NIE ogólny "popraw pamięć agenta"
linked_gap: GAP-002 (RETRIEVAL_ANCHOR_FAILURE część, "b"), GAP-003 (TEMPORAL_REPRESENTATION_LOSS), GAP-004 (ASSISTANT_TURN_REPRESENTATION_LOSS)
linked_experiment: Ledger Entry Q (SEMANTIC_ENTROPY_SUFFICIENCY_GATE, DROP -- źródło części dowodów poniżej); Entry H (RAW_PROVENANCE, REPLICATED_VALIDATED_TRANSPLANT); Entry N (TEMPORAL_ANCHOR_AT_CONTEXT x TEMPORAL_BOUNDARY, FAIL_ON_REPLICATION_GATE); Entry O/P (EXTRACTION_COMPLETENESS_VERIFICATION_PASS, EXPLORATORY_SUPPORTED -> FAILED_REPLICATION)
testability_status: mieszany per failure mode -- patrz sekcje niżej
max_expected_external_cost_usd: 0 (to jest pure research request -- żaden AAMR spend nie jest autoryzowany przez ten dokument)
desired_output: max 1-3 candidates/ TOTAL (nie per failure mode) -- ciasna, precyzyjna lista, nie kolejna szeroka kampania
stop_condition: jeśli po tym poszukiwaniu żaden kandydat nie spełnia WSZYSTKICH czterech kryteriów filtra AAMR (sekcja niżej), ten request zamyka się jako WAITING_FOR_RESEARCH -- to jest poprawny, oczekiwany wynik, NIE porażka. AAMR nie testuje niczego, dopóki nie wróci kwalifikujący się kandydat.
---

# Kontekst -- dlaczego ten request jest inny niż poprzednie

Campaign V2 (16 zamkniętych ledger entries, A-Q) jest teraz **zamrożona** -- pozostały budżet (~$0.61 z $5.00) nie mieści już bezpiecznie pełnego testu eksploracyjnego z realnym marginesem bezpieczeństwa. To NIE jest kolejna szeroka "znajdź nam jakiś mechanizm" prośba. AAMR ma teraz wystarczająco dużo skumulowanej ewidencji (16 zamkniętych mechanizmów, spójna absence-taxonomy), żeby powiedzieć DOKŁADNIE, czego szuka. Ten request celuje w **dokładnie trzy, precyzyjnie zdefiniowane failure modes**, każdy z konkretnym, code-verified lub corpus-verified dowodem z tego projektu. ResearchOS **nie ma wymyślać mechanizmów od zera** -- ma znaleźć **istniejące, zmierzone** rozwiązania (`EXTERNAL_MEASURED` / `CODE_VERIFIED` / `REPO_ARTIFACT_VERIFIED`) i sprawdzić, czy faktycznie celują w jeden z tych trzech problemów.

# Trzy failure modes (dokładne definicje AAMR)

## 1. `ASSISTANT_TURN_REPRESENTATION_LOSS` (= GAP-004)

**Definicja:** potrzebna informacja ISTNIEJE w oryginalnej konwersacji, ale pipeline ekstrakcji (`as_records()`, współdzielona przez KAŻDY mechanizm w tym projekcie) nigdy jej nie zapisuje ani nie reprezentuje w pamięci -- bo `as_records()` celowo (nie przez bug) odrzuca wszystkie assistant-role turns przed dotarciem do Mem0, ze względu na CUPMem-fair-comparison design.

**Dowód:** `docs/research/Dokumenty z Resherchera` niepotrzebne -- to jest AAMR-własny, code-verified fakt. 6 niezależnych instancji project-wide (najnowsza, code-verified nie tylko corpus-inspected: Entry Q's `1de5cff2` -- gold fact istnieje WYŁĄCZNIE w assistant turn, `as_records()` bezwarunkowo odrzuca role=="assistant"). 56/500 (11.2%) pytań LongMemEval-S to kategoria `single-session-assistant`, strukturalnie zablokowana.

**Czego AAMR potrzebuje:** precedensy (kod/paper) na SELEKTYWNE włączanie assistant-authored content do memory extraction -- NIE włączanie WSZYSTKICH assistant treści (co zepsułoby CUPMem-comparability i mogłoby duplikować/hałasować pamięć asystenta samego siebie), tylko treści bezpośrednio odpowiadającej na pytanie usera lub niosącej nową faktyczną informację. Jeśli istnieje system, który robi to selektywnie i ma na to zmierzony wynik (nie tylko architekturalny opis) -- to jest dokładnie to, czego szukamy.

**Blocker po stronie AAMR (nie do rozwiązania przez ResearchOS):** jakikolwiek kandydat musi wejść przez OSOBNĄ, izolowaną ścieżkę ingestu (nowy bank/mechanizm), NIE modyfikować `as_records()` samej -- to zepsułoby shared BASE każdego innego mechanizmu w projekcie. To jest projektowy fakt, nie coś do zakwestionowania.

## 2. `RETRIEVAL_ANCHOR_FAILURE` (= GAP-002, część "b")

**Definicja:** gdy mechanizm decyduje się eskalować z compact context do surowego (raw) źródła, remedy jest zakotwiczone WYŁĄCZNIE do top-1 hita retrieval (`raw_session()`, single-hop, deterministic pointer-follow). Gdy ten top-1 hit jest topically zły dla zapytania, remedy dokłada nieistotny raw content zamiast pomóc -- niezależnie od tego, jak dobry jest trigger decydujący KIEDY eskalować.

**WAŻNE ROZRÓŻNIENIE od poprzedniego pytania (nie duplikuj Entry M):** to NIE jest "gold fact jest poza top-10 dla dosłownego pytania" (query-side ranking-miss, już testowane jako HyDE, Entry M, DROP -- precondition confirmed real gdzie indziej, ale ta konkretna próbka trafiła w inny subtype). To jest pytanie o remedy-selection PO tym, jak trigger już zdecydował, że coś trzeba eskalować -- czy powinniśmy ufać JEDNEMU top-1 hitowi, czy rozważyć wielu kandydatów / lepiej wybrać, KTÓRĄ sesję pociągnąć.

**Dowód:** Entry Q (`1de5cff2`), CODE_VERIFIED: `evidence_times[0]`/`context_texts[0]` parują się z Mem0's własnym rank-1 hitem; `raw_session()` mechanicznie pociąga sesję za TYM hitem. Gdy rank-1 jest topically zły (tu: sesja o dżinsach/zegarkach zamiast o marce Veja), remedy dokłada bezużyteczny raw tekst. Ten sam kod (`raw_session()`) jest używany przez `RAW_PROVENANCE` (Entry H, zwalidowany, ale jego znane counterexamples -- `078150f1` -- mają dokładnie ten sam kształt: potrzebny fakt istnieje w INNEJ sesji niż top-1 hit) i przez `SEMANTIC_ENTROPY_SUFFICIENCY_GATE` (Entry Q).

**Czego AAMR potrzebuje:** measured evidence o remedy-anchor-selection strategiach w retrieval-augmented systemach -- multi-candidate raw injection, confidence-gated anchor selection, multi-hop pointer-follow. To jest INNE pytanie niż SUGAR/semantic entropy (już przetestowane jako trigger, Entry Q) -- to pytanie o to, CO wciągnąć, nie KIEDY.

## 3. `TEMPORAL_REPRESENTATION_LOSS` (= GAP-003)

**Definicja:** brak dat/relacji czasowych między sesjami uniemożliwia odpowiedź na pytania wymagające cross-session date arithmetic lub ordering -- nawet gdy WSZYSTKIE potrzebne fakty są retrieved (compact LUB raw), bo żadna reprezentacja (ani compact bullet, ani raw `user:/assistant:` text dump) nie niesie session-level date stamps.

**Dowód:** największy pojedynczy klaster w projekcie (obecnie 5+ niezależnych instancji, w tym Entry Q's `6e984301`, code/corpus-verified: gold wymagał arytmetyki między dwiema sesjami, 11 lutego → 4 marca = 3 soboty; ani compact context, ani `raw_session()`'s remedy format nigdy nie niosą tych dat). Dwie już przetestowane write-side/read-side próby: `EVENT_TIME_RESOLUTION_AT_EXTRACTION` (Entry E, inline instrukcja w prompt-cie ekstrakcji -- `CALIBRATION_FAILED`, 0/5, model ignoruje instrukcję) i `TEMPORAL_ANCHOR_AT_CONTEXT` (Entry A/B/N, read-side rendering session-timestampu -- `SUPPORTED, qualified`, ale wąski regime i `FAIL_ON_REPLICATION_GATE` na najnowszej replikacji).

**Czego AAMR potrzebuje:** measured examples structured-output temporal resolution w extraction pipelines -- osobne pole (nie inline substitution, które już zawiodło przez few-shot-modeling problem, patrz `EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md` archaeology dla `DETERMINISTIC_TEMPORAL_RESOLVER_POSTPROCESS`), z deterministycznym Python post-processingiem (stdlib `datetime`, bez LLM arithmetic) zamiast polegania na modelu do liczenia dat.

# Co ResearchOS MA zrobić (i czego NIE ma robić)

**MA:**
1. Dla każdego z trzech problemów -- sprawdzić GitHub (kod, nie tylko README), paper (measured ablations, nie tylko architektura), negative evidence (kiedy to podejście NIE działało), host-preconditions (czy wymaga fine-tuningu/hidden activations -- jeśli tak, `NEEDS_PRECONDITION_CHECK`, nie zakładać dostępności).
2. Klasyfikować evidence_class ściśle: `EXTERNAL_MEASURED` (zmierzone na jakimś benchmarku) / `CODE_VERIFIED` (kod istnieje i robi to, co twierdzi) / `REPO_ARTIFACT_VERIFIED` (artefakt w repo potwierdza) -- NIE `PAPER_CLAIM` czy `INFERENCE` bez wyraźnego oznaczenia jako słabszej klasy dowodu.
3. Sprawdzić `DO_NOT_REDISCOVER.md` PRZED zaproponowaniem czegokolwiek -- jeśli kandydat jest bliski Entry E, M, lub Q, wymagane jest jasne uzasadnienie, dlaczego się różni (nie kosmetyczna zmiana nazwy tego samego designu).
4. Zwrócić max 1-3 kandydatów TOTAL (nie per problem) -- jeśli więcej niż 3 kwalifikuje się, wybrać najsilniejsze evidence_class + najniższy koszt testu.

**NIE MA:**
1. Wymyślać nowego mechanizmu od zera bez istniejącego zmierzonego prior art.
2. Proponować identyczny design co Entry E (inline temporal instruction), Entry M (single-shot HyDE), lub Entry Q (embedding-cosine sample-and-cluster trigger + top-1-anchored remedy) bez jawnego, nowego uzasadnienia różnicy.
3. Rozciągać single-turn RAG evidence na te pytania bez zaznaczenia różnicy względem persystentnej agent memory (ten sam błąd, którego unikaliśmy przy poprzednim requeście).
4. Proponować cokolwiek wymagającego fine-tuningu, hidden activations, provider-side training, lub direct weight updates (`CANNOT_TEST_NOW`, patrz `TESTABILITY_ENVELOPE.md`).

# Filtr AAMR przed jakimkolwiek nowym wydatkiem

Każdy zwrócony kandydat MUSI spełnić WSZYSTKIE cztery kryteria, inaczej NIE jest testowany (żaden wyjątek):

1. **`CAN_TEST_NOW`** (nie `CAN_TEST_WITH_PRECONDITION` niespełnioną, nie `CANNOT_TEST_NOW`) -- per `TESTABILITY_ENVELOPE.md`.
2. **Nie duplikat** -- sprawdzony przeciwko `DO_NOT_REDISCOVER.md` (16 entries, A-Q) z jawnym uzasadnieniem różnicy, nie tylko innej nazwy.
3. **Celuje w DOKŁADNIE JEDEN** z trzech powyższych failure modes -- nie ogólny "poprawi pamięć", musi być traceable do konkretnego, nazwanego problemu.
4. **Tani causal contrast** -- reużywa, gdzie możliwe, już-frozen arm-building code (`mechanism_ablation.py`, `raw_session()`, `as_records()`) zamiast budować nową infrastrukturę od zera; szacowany koszt eksploracyjnego testu mieści się w rozsądnym ($2-3) budżecie dla POJEDYNCZEGO mechanizmu.

Jeśli ŻADEN zwrócony kandydat nie spełnia wszystkich czterech -- ten request zamyka się jako `WAITING_FOR_RESEARCH`. To jest poprawny wynik, nie porażka researchu. AAMR nie testuje niczego "na wszelki wypadek".

# Sekwencja po znalezieniu kandydata (informacyjne, nie zobowiązanie budżetowe tego requestu)

Jeśli kandydat przejdzie filtr: AAMR najpierw zaprojektuje tani calibration/precondition check (wzorem Entry Q's $0.003 kalibracji, reużywając już-persisted danych gdzie możliwe), DOPIERO potem jeden bounded exploratory test pod nowym, mechanizm-specyficznym budżetem Campaign V3 (~$2-3, nie "budżet na szukanie") -- replikacja tylko po realnym pozytywnym sygnale, dokładnie ta sama dyscyplina co przy każdym poprzednim mechanizmie w tym projekcie.

# What Would Change This Request

Kandydat z `evidence_class: EXTERNAL_MEASURED` lub `REPO_ARTIFACT_VERIFIED`, jawnie celujący w jeden z trzech powyższych failure modes (nie ogólny retrieval/memory improvement), przechodzący wszystkie 4 kryteria filtra AAMR.

# Stop Condition

Patrz frontmatter.
