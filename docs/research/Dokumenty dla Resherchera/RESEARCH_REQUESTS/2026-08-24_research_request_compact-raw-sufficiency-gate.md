---
id: arr-2026-08-24-001
type: RESEARCH_REQUEST
status: OPEN
created: 2026-08-24
source: AAMR
target: ResearchOS
priority: MEDIUM
target_failure: n/a -- to nie jest failure-repair; to jest cost-efficiency pytanie na już zwalidowanym mechanizmie (RAW_PROVENANCE, Ledger Entry H)
linked_gap: GAP-005 (OPEN_TESTABLE_GAPS.md)
linked_experiment: Ledger Entry H (RAW_PROVENANCE, REPLICATED_VALIDATED_TRANSPLANT); Ledger Entry I (RETRIEVAL_CONFIDENCE_SIGNAL, pokrewny ale różny sygnał, DROP)
testability_status: CAN_TEST_WITH_PRECONDITION (TESTABILITY_ENVELOPE.md § Compact-vs-raw gating)
max_expected_external_cost_usd: 0.15 (pierwszy cheap-proxy test AAMR-side, jeśli ResearchOS coś znajdzie)
desired_output: candidates/ (mechanism_candidate lub precondition_note), oceniony pod kątem czy transferuje do PERSYSTENTNEJ agent memory, nie single-turn RAG
stop_condition: albo ResearchOS dostarcza kandydata z evidence_class EXTERNAL_MEASURED lub silniejszym, konkretnie dla persistent-memory compact-vs-raw escalation (nie retrieve-or-not w single-turn RAG), albo po dwóch rundach researchu bez takiego znaleziska -- ten request zamyka się jako "brak bezpośrednio trafnego external evidence", nie jako "gate nie istnieje"
---

# Research Question

Czy istnieje tani (gold-free, dostępny w inference-time, bez fine-tuningu, bez hidden activations), zmierzony sygnał przewidujący, kiedy Mem0's compact retrieval jest niewystarczający -- specyficznie dla decyzji "czy zapłacić za `RAW_PROVENANCE`'s ~21x token overhead na tym konkretnym zapytaniu", nie dla ogólnego "czy retrievować z zewnętrznego korpusu" (single-turn RAG framing)?

# Why AAMR Needs This

AAMR ma teraz jeden w pełni zwalidowany mechanizm (`RAW_PROVENANCE`, Entry H) stosowany bezwarunkowo, bez obserwowanych regresji, z mean token overhead **21.4x** (zakres 5.6x-32.1x, zmierzone bezpośrednio na 8 jednostkach, `data/lab/arena/raw-provenance-fresh-replication-v1/results.json`). To jest pytanie o efektywność kosztową przy skali, nie o poprawność -- dokładnie ten typ pytania, gdzie external literature (nie kolejny AAMR eksperyment) jest najbardziej wartościowy, bo AAMR może TESTOWAĆ kandydata tanio (~$0.05-0.15, reusing already-frozen `RAW_PROVENANCE` arm-building code), ale nie ma czasu/budżetu na przeszukiwanie literatury o dziesiątkach możliwych proxy-sygnałów samodzielnie.

# What We Already Know

- `RAW_PROVENANCE` (Entry H) pomaga, bezwarunkowo, bez regresji -- **to pytanie nie jest już otwarte**, w przeciwieństwie do założenia w istniejącym kandydacie `Dokumenty z Resherchera/candidates/2026-08-24_mechanism_candidate_semantic-entropy-escalation-gate.md`.
- `RETRIEVAL_CONFIDENCE_SIGNAL` (Entry I) testował POKREWNY, ale RÓŻNY sygnał (top1/top2 score margin, jako proxy dla "gold jest ambiguous w rankingu") -- DROP z powodu regime mismatch (oba flagged-and-wrong units w tamtej próbce to były absence failures, nie ambiguous-ranking failures). To NIE testuje pytania "czy compact representation samo w sobie wystarcza", tylko wąskie "czy top1/top2 są blisko siebie".
- Semantic entropy (sample-and-cluster) jest zewnętrznie zwalidowany dla POKREWNEJ, ale innej decyzji: SUGAR (arXiv 2501.04899) testuje to dla "retrieve from external corpus or not" w single-turn RAG, nie dla "compact vs raw escalation" w persistent agent memory. To jest DOKŁADNIE ta luka transferu, którą ResearchOS's własny wcześniejszy kandydat już nazwał jako otwartą, nieprzetestowaną -- ten request prosi o pogłębienie TEGO konkretnego pytania, z odświeżonym uzasadnieniem (koszt, nie korekcja).
- AAMR's własna diagnostyka absence-taxonomy (Ledger Entries M, O) pokazuje, że dominujący failure mode w tym projekcie to write-time extraction loss i retrieval-ranking-miss, NIE "gold absent i model nie wie" w sensie, w jakim semantic entropy jest teoretycznie najsilniejszy -- to jest konkretny, AAMR-własny powód do sceptycyzmu wobec tego konkretnego sygnału, nie do automatycznego odrzucenia.

# What Must Not Be Rediscovered

Patrz `DO_NOT_REDISCOVER.md` Entry I (`RETRIEVAL_CONFIDENCE_SIGNAL`) -- nie proponuj identycznego score-margin designu ponownie bez nowego uzasadnienia, dlaczego różni się od już przetestowanego. Entry H (`RAW_PROVENANCE`) jest już zwalidowany -- nie proponuj ponownego testu "czy raw fallback pomaga w ogóle."

# Current Host Constraints

Patrz `TESTABILITY_ENVELOPE.md`. Kluczowe: (1) embedding-derived i retrieval-score-derived sygnały są `CAN_TEST_NOW` (Mem0's własny `search()` zwraca relevance scores bezpośrednio, darmowo). (2) Model fine-tuning, hidden activations, provider-side training są `CANNOT_TEST_NOW` (scope.md system boundary) -- **nie proponuj żadnego kandydata wymagającego tego**. (3) Custom logprobs to `UNKNOWN` -- jeśli kandydat tego wymaga, zaznacz to explicite jako `NEEDS_PRECONDITION_CHECK`, nie zakładaj dostępności.

# Allowed Solution Space

Dowolny gold-free, inference-time-dostępny proxy sygnał: sample-and-cluster semantic entropy (black-box, bez logprobs), retrieval score/confidence statystyki, query-type classification, candidate-set statystyki (liczba, gęstość, redundancja), cokolwiek nie wymagającego fine-tuningu ani hidden activations.

# Disallowed Solution Space

Fine-tuning, hidden activations, provider-side training, direct weight updates (wszystkie `CANNOT_TEST_NOW`). Token-level entropy wymagający logprobs, chyba że explicite oznaczone jako `NEEDS_PRECONDITION_CHECK` z jasnym stwierdzeniem, że dostępność logprobs w tym API jest niezweryfikowana.

# Evidence Wanted

Zmierzone (nie tylko claimed) wyniki dla dowolnego cheap proxy sygnału SPECYFICZNIE testowanego na decyzji "czy zwiększyć context (raw/verbatim) w PERSYSTENTNEJ agent memory", nie na "czy retrievować z zewnętrznego korpusu w single-turn RAG". Jeśli nic bezpośrednio trafnego nie istnieje, powiedz to wprost (`NEEDS_PRECONDITION_CHECK` lub `INTERESTING` z jasnym opisem luki transferu) zamiast rozciągać single-turn RAG evidence na to pytanie bez zaznaczenia różnicy.

# Negative Evidence Wanted

Czy istnieją znane przypadki, gdzie semantic-entropy-style albo pokrewne sygnały failują specyficznie na "gold present but reader still wrong" failure mode (a nie "gold absent, model nie wie") -- to jest dominujący pattern w AAMR's własnych danych (Ledger Entries M, O), i jest to konkretny, sformułowany PRZED odpowiedzią powód, dla którego efekt może być mniejszy niż na benchmarkach, gdzie te sygnały były pierwotnie walidowane.

# Precondition Questions

Czy istnieje tani sposób odróżnienia "compact wystarczy" od "compact nie wystarczy" bez dostępu do gold, możliwy do zmierzenia na już zebranych AAMR danych (np. korelacja między istniejącym `RAW_PROVENANCE` repair/no-repair rozkładem z Entry H i jakimkolwiek kandydackim sygnałem) PRZED budową pełnego mechanizmu?

# What Would Change an Experiment

Jeśli ResearchOS znajdzie kandydata z `evidence_class: EXTERNAL_MEASURED` lub `REPO_ARTIFACT_VERIFIED`, konkretnie dla persistent-memory compact-vs-raw escalation (nie single-turn retrieve-or-not), AAMR zaprojektuje $0 precondition check przeciwko już-zebranym `RAW_PROVENANCE` danym (Entry H) przed jakimkolwiek płatnym testem -- dokładnie ta sama dyscyplina co przy każdym poprzednim mechanizmie w tej kampanii.

# Stop Condition

Patrz frontmatter.
