# Open Testable Gaps

Statusy: `OPEN` | `BLOCKED` | `WAITING_FOR_EXPERIMENT` | `SATURATED` | `CLOSED`.

---

## GAP-001 — Write-time extraction completeness, replication

- **title:** Czy `EXTRACTION_COMPLETENESS_VERIFICATION_PASS` (Entry O) replikuje na świeżej próbce?
- **target_failure:** write-time extraction loss (bundled enumerations, omitted facts) — absence subtype (1).
- **status:** CLOSED
- **priority:** N/A (zamknięte)
- **why_it_matters:** Entry O był jedynym `EXPLORATORY_SUPPORTED` mechanizmem tej kampanii poza `RAW_PROVENANCE`. Świeża replikacja była jedynym brakującym krokiem do statusu `REPLICATED_VALIDATED_TRANSPLANT`.
- **what_is_known:** replikacja WYKONANA (`data/lab/arena/extraction-completeness-verification-v2`, 8 świeżych jednostek, czysto do końca, oba operacyjne problemy z v1 naprawione proaktywnie). Wynik: 0 net repairs, 0 regresji — `MECHANISM_J_REPLICATION_FAILED` (Ledger Entry P). Mechanizm odpalał na każdej jednostce, ale 4 BASE-wrong jednostki w tej próbce trafiły na TRZY różne, już udokumentowane inne absence subtypes (temporal-representation-loss, knowledge-update/supersession, assistant-turn-scoping-loss), nie na target regime tego mechanizmu.
- **what_is_unknown:** rzeczywisty repair rate (obecnie ~1/14 ≈ 7% łącznie v1+v2) pozostaje niepewny przy tak rzadkim precondition -- większa próbka mogłaby dać czystszy sygnał, ale nie jest tu zaplanowana (budget-conscious pause, patrz `autonomous-research-budget-v2/ledger.json`).
- **what_was_already_tested:** patrz `EXTRACTION_COMPLETENESS_VERIFICATION_PASS_V1.md` i `_V2.md`.
- **allowed_mechanism_space:** n/a — zamknięte.
- **disallowed_mechanism_space:** identyczny mechanizm bez subtype-pre-screeningu (patrz reopen_condition).
- **required_preconditions:** —
- **desired_external_evidence:** n/a.
- **research_question:** n/a.
- **candidate_value_if_found:** n/a — Entry O pozostaje `EXPLORATORY_SUPPORTED`, nie zwalidowany, nie porzucony.
- **estimated_experiment_cost_band:** zrealizowane: $1.338754 (v2).
- **dependencies:** —
- **blocked_by:** —
- **reopen/close condition:** większa (>8 jednostek) LUB subtype-pre-screened (gold-blind, strukturalna nie treściowa) próbka specyficznie wzbogacona o pytania z bundled-enumeration shape.
- **last_updated:** 2026-08-25.

## GAP-002 — Retrieval-ranking-miss / retrieval-anchor failure

- **title:** Czy multi-query fan-out / ranking-miss detection naprawia więcej niż pojedynczy HyDE? Czy remedy zakotwiczone gdzie indziej niż top-1 naprawia RETRIEVAL_ANCHOR_FAILURE?
- **target_failure:** dwie POKREWNE, ale rozróżnialne twarze absence subtype (2): (a) **query-side ranking-miss** — gold fact obecny w store, ale poza top-10 dla dosłownego pytania (Entry M's target); (b) **remedy-side anchor failure, `RETRIEVAL_ANCHOR_FAILURE`** — nowo zaostrzone przez Entry Q (`1de5cff2`): nawet gdy trigger poprawnie wykrywa niewystarczalność, remedy (`raw_session()`) jest zakotwiczone WYŁĄCZNIE do Mem0's własnego top-1 hit; gdy ten top-1 jest topically zły, remedy dokłada nieistotny raw content zamiast pomagać. To nie jest problem query reformulation (a) — to problem TEGO, do czego remedy patrzy, niezależnie od tego, jak dobre jest query.
- **status:** OPEN
- **priority:** HIGH (podniesiony 2026-08-25 — jeden z trzech precyzyjnych celów nowego research requestu `arr-2026-08-25-001`)
- **why_it_matters:** Entry M potwierdził realny precondition dla (a) (fact present-in-store-but-unranked, 2/2 w $0 checku) ale świeża 6-unitowa próbka nie trafiła na ten konkretny subtyp. Entry Q (2026-08-25) dostarczył CODE_VERIFIED evidence dla (b): `raw_session()` (używany zarówno przez `RAW_PROVENANCE`, Entry H, jak i `SEMANTIC_ENTROPY_SUFFICIENCY_GATE`, Entry Q) deterministycznie podąża za rank-1 hitem Mem0's własnego `search()` — gdy ten jest zły, każdy mechanizm dziedziczący ten kod remedy dziedziczy też tę słabość, niezależnie od jakości triggera decydującego KIEDY eskalować. Kandydaci z discovery-rebuild v3 (`MULTI_QUERY_FUSION_RETRIEVAL`, rank 5; `RANKING_MISS_DETECTION_GATE`, rank 8) celują w (a), nie w (b) — żaden dotychczasowy kandydat nie celuje bezpośrednio w (b).
- **what_is_known:** patrz Entry M (a), Entry Q (b), `EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md`.
- **what_is_unknown:** czy multi-query fan-out faktycznie zwiększa trafność na (a) w tym harnessie; czy jakikolwiek multi-candidate/multi-hop remedy design naprawia (b) bez utraty (b)'s prostoty/taniości.
- **what_was_already_tested:** pojedynczy HyDE (Entry M, DROP na tej próbce, precondition confirmed real gdzie indziej) — celował w (a). (b) nigdy nie testowany jako osobny target — tylko obserwowany jako ubocza porażka wewnątrz Entry H i Entry Q.
- **allowed_mechanism_space:** read-side, query-time reformulation/fan-out (dla a), LUB read-side remedy-selection niezakotwiczony wyłącznie do top-1 (np. multi-candidate raw injection, confidence-gated anchor selection) (dla b) — embedding-based, bez fine-tuningu.
- **disallowed_mechanism_space:** dokładnie ten sam single-shot HyDE bez modyfikacji (per "don't retune the same failed action"); dokładnie ten sam top-1-anchored `raw_session()` bez zmiany anchor-selection logiki.
- **required_preconditions:** żadne nowe infrastrukturalnie dla (a). Dla (b): `raw_session()`/`session_map` już istnieją i są frozen/reużywalne — rozszerzenie do multi-candidate wymaga tylko iterowania po top-K zamiast top-1.
- **desired_external_evidence:** primary-source measured numbers dla multi-query/RRF-style fan-out (a) — już częściowo dostarczone przez discovery-rebuild v3 (SmartSearch 88.4% na LongMemEval-S wprost, RAG-Fusion +19% NDCG@10 ogólna domena). Dla (b): measured evidence o remedy-anchor-selection strategiach w retrieval-augmented systemach (nie tylko trigger/UQ literatura — to jest INNE pytanie niż SUGAR/semantic entropy, które już przetestowano, Entry Q).
- **research_question:** patrz `RESEARCH_REQUESTS/2026-08-25_research_request_three-precise-failure-modes.md`.
- **negative_evidence_wanted:** dla (a) — czy istnieją znane przypadki, gdzie multi-query fan-out pogarsza wynik na benchmarku podobnym do LongMemEval. Dla (b) — czy istnieją znane przypadki, gdzie multi-candidate/multi-hop remedy selection zwiększa koszt bez poprawy trafności (np. przez rozmycie kontekstu wieloma słabymi kandydatami zamiast jednym mocnym).
- **candidate_value_if_found:** kolejny kandydat na drugi zwalidowany mechanizm.
- **estimated_experiment_cost_band:** ~$0.50-0.80 dla (a) (podobne do Entry M); nieznane dla (b), zależy od projektu (prawdopodobnie podobne, reużywa Entry H's arm-building code).
- **dependencies:** żadne twarde — niezależne od GAP-001.
- **blocked_by:** nic.
- **reopen/close condition:** zamyka się po pierwszym pełnym teście eksploracyjnym kandydata celującego w (a) LUB (b) — osobno, nie łącznie (to są dwa różne mechanizmy nawet jeśli ten sam gap number).
- **last_updated:** 2026-08-25.

## GAP-003 — Structured write-time temporal field (subtype 3, alternative design)

- **title:** Czy `DETERMINISTIC_TEMPORAL_RESOLVER_POSTPROCESS` (structured field, nie inline substitution) naprawia temporal-representation-loss?
- **target_failure:** temporal-representation-loss — absence subtype (3), największy pojedynczy klaster w projekcie (4/13+ BASE-wrong units).
- **status:** OPEN
- **priority:** HIGH (podniesiony 2026-08-25 — jeden z trzech precyzyjnych celów nowego research requestu `arr-2026-08-25-001`, tam nazwany `TEMPORAL_REPRESENTATION_LOSS`)
- **why_it_matters:** subtype (3) to największy nienaprawiony klaster. Entry E (inline instruction) był `CALIBRATION_FAILED` — inert. Entry N (read-side TEMPORAL_ANCHOR, restricted to TEMPORAL_BOUNDARY) był `FAIL_ON_REPLICATION_GATE`, ale bez regresji. Discovery-rebuild v3's archeologia (rank 2 kandydat) zidentyfikowała konkretny, prawdopodobny root cause Entry E's porażki: few-shot examples w promptcie *modelują* usuwanie relative-time słów, neutralizując dodaną instrukcję. Structured JSON field (osobne detekcja + deterministyczne rozwiązanie w Pythonie, bez LLM arithmetic) to nowy, nietestowany kąt.
- **what_is_known:** patrz `EXTERNAL_DISCOVERY_CANDIDATE_POOL_V3.md` DETERMINISTIC_TEMPORAL_RESOLVER_POSTPROCESS archaeology (VIABLE_WITH_CAVEATS verdict). Entry Q (2026-08-25, `6e984301`) dostarczył kolejną, niezależną, primary-source-verified instancję: gold wymagał arytmetyki dat między dwiema sesjami (11 lutego → 4 marca = 3 soboty), i ani compact context, ani `raw_session()`'s remedy format (czysty `user:/assistant:` tekst, bez session-level date stamps) nigdy nie niosą informacji potrzebnej do tej arytmetyki — potwierdza, że nawet mechanizmy skierowane na inne subtype'y (jak Entry Q) rutynowo trafiają na subtype (3) jako "collateral" niepowodzenie, dalej wzmacniając priorytet tego gapa.
- **what_is_unknown:** czy structured-field design faktycznie omija few-shot-modeling problem.
- **what_was_already_tested:** Entry E (inline instruction, inert); Entry A/N (read-side rendering, nie write-side resolution).
- **allowed_mechanism_space:** write-side, structured JSON output field + deterministyczny post-processing (stdlib `datetime`, bez LLM arithmetic).
- **disallowed_mechanism_space:** ten sam inline-substitution design co Entry E.
- **required_preconditions:** kalibracja przed jakimkolwiek płatnym testem (ten sam wymóg co Entry O).
- **desired_external_evidence:** przykłady structured-output temporal resolution w innych systemach agent-memory (Mem0 sam nie ma tego pola, CODE_VERIFIED).
- **research_question:** czy istnieją zmierzone (nie tylko claimed) przykłady structured-field date resolution w extraction pipelines poprawiające dokładność end-to-end, nie tylko samą ekstrakcję.
- **candidate_value_if_found:** trzeci kandydat na drugi zwalidowany mechanizm.
- **estimated_experiment_cost_band:** kalibracja ~$0.05, pełny test ~$0.80-1.20 (podobny do Entry O, dual-bank).
- **dependencies:** żadne twarde.
- **blocked_by:** nic.
- **reopen/close condition:** zamyka się po pierwszej kalibracji + (jeśli passed) pełnym teście.
- **last_updated:** 2026-08-24.

## GAP-004 — Assistant-turn-scoping-loss (subtype 4)

- **title:** Czy włączenie assistant-authored turns do ingestu naprawia `single-session-assistant` category (11.2% benchmarku)?
- **target_failure:** assistant-turn-scoping-loss — nowy, czwarty absence subtype, odkryty podczas Mechanism H's archeologii. `as_records()` (shared ingest function, używana przez BASE każdego mechanizmu w projekcie) celowo odrzuca wszystkie assistant-role turns przed dotarciem do Mem0 (deliberate CUPMem-comparability design, nie bug). 4/4 obserwowane `single-session-assistant` units project-wide to `BASE`-wrong, spójne z jedną wspólną przyczyną.
- **status:** BLOCKED
- **priority:** HIGH (podniesiony 2026-08-25 — jeden z trzech precyzyjnych celów nowego research requestu `arr-2026-08-25-001`, tam nazwany `ASSISTANT_TURN_REPRESENTATION_LOSS`; nadal BLOCKED na design decision, nie na budget)
- **why_it_matters:** 56/500 (11.2%) pytań w LongMemEval-S to ta kategoria, strukturalnie zablokowana obecnym designem harnessu — nie problem jakości ekstrakcji Mem0, tylko zakresu tego, co w ogóle dociera do Mem0.
- **what_is_known:** direct corpus inspection (`16c90bf4`) potwierdza: gold answer istnieje wyłącznie w assistant's turn; user's turn ma tylko częściowe echo. Entry Q (`1de5cff2`, 2026-08-25) dostarczył 6. niezależną, code-verified instancję (nie tylko corpus-inspected — prześledzone przez faktyczny `as_records()` w kodzie), skomponowaną dodatkowo z GAP-002(b)'s retrieval-anchor failure: gdy potrzebny fakt jest structurally unreachable (ten gap), jakikolwiek remedy zakotwiczony do "najbliższej" sesji (GAP-002b) trafi w złą, tylko powierzchownie podobną sesję zamiast się poddać — dwa gaps mogą współwystępować w jednej jednostce.
- **what_is_unknown:** czy włączenie assistant turns faktycznie naprawia te przypadki (nietestowane), i czy to zaburza fair-comparison-z-CUPMem cel, dla którego `as_records()` je odrzuca.
- **what_was_already_tested:** nic bezpośrednio — to obserwacja, nie test.
- **allowed_mechanism_space:** OSOBNA ścieżka ingestu dla nowego banku/mechanizmu (nowy zestaw rekordów włączający assistant turns), NIE modyfikacja `as_records()` samej (to zepsułoby współdzielony BASE każdego innego mechanizmu w projekcie).
- **disallowed_mechanism_space:** jakakolwiek zmiana `as_records()` bezpośrednio.
- **required_preconditions:** careful design izolujący nowy ingest path od reszty projektu — nie zaprojektowane jeszcze.
- **desired_external_evidence:** czy inne systemy agent-memory włączają assistant-authored content do pamięci, i jakie compliance/prywatność uwagi to rodzi (asystent może powtarzać dane wrażliwe użytkownika).
- **research_question:** jakie są precedensy (kod/paper) na selektywne włączanie assistant turns do memory extraction bez włączania WSZYSTKICH assistant treści (np. tylko treści bezpośrednio odpowiadające na pytanie usera)?
- **candidate_value_if_found:** naprawiłby strukturalnie 11.2% benchmarku, obecnie poza zasięgiem KAŻDEGO testowanego mechanizmu (włącznie z `RAW_PROVENANCE`, który też polega na `as_records()`).
- **estimated_experiment_cost_band:** nieznane — zależy od projektu izolowanej ścieżki ingestu.
- **dependencies:** design decision (jak izolować od shared BASE) musi poprzedzić jakikolwiek test.
- **blocked_by:** brak zaprojektowanej izolowanej ścieżki ingestu — to jest blocker, nie brak pomysłu na mechanizm.
- **reopen/close condition:** odblokowuje się po zaprojektowaniu izolowanej ścieżki ingestu (AAMR-side decision, nie ResearchOS).
- **last_updated:** 2026-08-24.

## GAP-005 — Compact-vs-raw sufficiency gate (cost-efficiency framing)

- **title:** Czy istnieje tani proxy sygnał przewidujący, kiedy `RAW_PROVENANCE`'s ~21x token overhead jest warty zapłacenia?
- **target_failure:** n/a — to nie jest failure-repair, to jest cost-efficiency question na już zwalidowanym mechanizmie.
- **status:** CLOSED
- **priority:** N/A (zamknięte)
- **why_it_matters:** **To jest dokładnie luka, którą celuje ResearchOS's istniejący kandydat (`semantic-entropy-escalation-gate`), ale z odświeżonym uzasadnieniem.** Kandydat zakładał, że wartość raw fallback jest wciąż nierozstrzygnięta — to już nieprawda (Entry H, `REPLICATED_VALIDATED_TRANSPLANT`). Prawdziwe uzasadnienie: zmierzony ~21x narzut tokenów (mean, 8 units, zakres 5.6x-32.1x) na bezwarunkowe zastosowanie `RAW_PROVENANCE` — bramka miałaby wartość kosztową, nie korekcyjną.
- **what_is_known:** Entry H (raw fallback pomaga, bez regresji, bezwarunkowo); token overhead ratio (patrz wyżej); Entry I (`RETRIEVAL_CONFIDENCE_SIGNAL`, score-margin proxy) DROP z powodu regime mismatch — nie testuje TEGO konkretnego pytania (czy compact jest wystarczający), testował inne (czy top1/top2 margin jest wąski).
- **what_is_unknown:** czy jakikolwiek tani, gold-free proxy sygnał (semantic entropy, retrieval confidence, score margin, candidate-set statistics) koreluje z rzeczywistą niewystarczalnością compact representation w TYM projekcie.
- **what_was_already_tested:** Entry I testował pokrewny, ale inny sygnał (score margin jako proxy for "gold ambiguous", nie "compact insufficient") — DROP, regime mismatch, nigdy nie trafił na target precondition.
- **allowed_mechanism_space:** dowolny gold-free, inference-time-dostępny sygnał (semantic entropy sample-and-cluster, retrieval score statistics, query-type classification) — read-side/query-side, nie wymaga fine-tuningu ani hidden activations (per scope.md).
- **disallowed_mechanism_space:** cokolwiek wymagającego fine-tuningu, hidden activations, lub logprobs bez wcześniejszego potwierdzenia dostępności (patrz `TESTABILITY_ENVELOPE.md` "Custom logprobs": UNKNOWN).
- **required_preconditions:** żadne infrastrukturalne — `RAW_PROVENANCE`'s arm-building code już istnieje i jest frozen/reużywalny.
- **desired_external_evidence:** zmierzone (nie tylko claimed) wyniki sample-and-cluster semantic entropy albo pokrewnych proxy sygnałów, SPECYFICZNIE dla decyzji compact-vs-raw-escalation w PERSYSTENTNEJ agent memory (nie jednorazowego "retrieve or not" w single-turn RAG — ResearchOS's własny kandydat już to rozróżnienie nazwał jako otwartą, nieprzetestowaną transfer question).
- **negative_evidence_wanted:** czy istnieją znane przypadki, gdzie semantic-entropy-style sygnały failują specyficznie na "gold present but reader still wrong" failure mode (dominujący w tym projekcie per ResearchOS's własny kandydat, §possible_negative_regime) — zamiast na "gold absent" (gdzie te sygnały są teoretycznie najsilniejsze).
- **precondition_questions:** czy istnieje tani sposób odróżnienia "compact wystarczy" od "compact nie wystarczy" bez dostępu do gold, mierzalny na już-zebranych AAMR danych (np. korelacja między istniejącym `RAW_PROVENANCE` repair/no-repair rozkładem i jakimkolwiek kandydackim sygnałem) przed budową pełnego mechanizmu.
- **research_question:** n/a — zamknięte. Patrz `RESEARCH_REQUESTS/2026-08-24_research_request_compact-raw-sufficiency-gate.md` (CLOSED) dla pełnej historii.
- **what_is_known (update 2026-08-25):** ResearchOS's kandydat `rmc-2026-08-24-001` (`SEMANTIC_ENTROPY_SUFFICIENCY_GATE`) przetestowany bezpośrednio przez AAMR — $0 kalibracja (separacja +0.804, czysta) → 6-jednostkowy przyczynowy test świeżych, gold-blind jednostek. Wynik: `MECHANISM_SEG_FAIL` (Ledger Entry Q) — 0/2 traceable repairs mimo selektywnego odpalania (2/6); trigger niepewny (1 prawdziwy positive, 1 clustering artifact na n=2); remedy (`raw_session()`, top-1-anchored) dziedziczy dokładnie te same ograniczenia co `RAW_PROVENANCE` (single-hop, brak session-level date stamps) — oba escalated units trafiły na już znane absence subtypes (2, 4), których ten remedy nie mógł naprawić z konstrukcji.
- **candidate_value_if_found:** zrealizowane negatywnie — żaden przetestowany proxy (semantic entropy, sample-and-cluster) nie skorelował się z użyteczną naprawą na tej próbce. Przyszły kandydat z INNYM remedy (nie top-1-anchored single-hop) lub INNĄ metodą clusteringu (nie embedding-cosine, np. bidirectional NLI entailment) nie byłby duplikatem — patrz `DO_NOT_REDISCOVER.md` Entry Q, `do_not_retry`.
- **estimated_experiment_cost_band:** zrealizowane: $0.003309 (kalibracja) + $0.435904 (test) = $0.439213.
- **dependencies:** —
- **blocked_by:** —
- **reopen/close condition:** reopen jeśli przyszły kandydat proponuje inny remedy (nie top-1-anchored raw injection) lub inną metodę clusteringu dla triggera, z nowym uzasadnieniem dlaczego omija te dwie konkretne, zmierzone porażki.
- **last_updated:** 2026-08-25.

## GAP-006 — Reranking

- **title:** Czy reranking ma jakiekolwiek zastosowanie przy obecnej retrieval breadth?
- **target_failure:** wrong item order under budget truncation.
- **status:** SATURATED
- **priority:** LOW
- **why_it_matters:** gold_rank=1 w 17/17 obserwowanych retrievals (SERIAL_POSITION_CONTEXT_REORDER's archeologia, discovery pool v2) — nie ma czego przerankować przy obecnej compact (~10-item) breadth.
- **what_is_known:** patrz wyżej.
- **what_is_unknown:** czy inna breadth (wide/3000) albo inny zbiór pytań zmieniłby ten wynik.
- **what_was_already_tested:** `SERIAL_POSITION_CONTEXT_REORDER` disqualified pre-spend na dokładnie tej podstawie.
- **allowed_mechanism_space:** n/a — SATURATED przy obecnym regime.
- **disallowed_mechanism_space:** ten sam test przy tej samej breadth.
- **required_preconditions:** —
- **desired_external_evidence:** —
- **research_question:** n/a chyba że breadth regime się zmieni.
- **candidate_value_if_found:** n/a.
- **estimated_experiment_cost_band:** n/a.
- **dependencies:** —
- **blocked_by:** —
- **reopen/close condition:** reopen jeśli gold-blind próbka przy innej breadth pokaże gold_rank > 1.
- **last_updated:** 2026-08-24.

## GAP-007 — Controller / interaction test

- **title:** Kiedy AAMR może zbudować router między ≥2 zwalidowanymi mechanizmami?
- **target_failure:** n/a — meta-pytanie o gotowość, nie o konkretny failure mode.
- **status:** WAITING_FOR_EXPERIMENT
- **priority:** N/A (structural gate, nie do testowania samo w sobie)
- **why_it_matters:** to jest cel kampanii wyższego poziomu (2 zwalidowane mechanizmy + interaction test = zbliżenie do global STOP tego etapu).
- **what_is_known:** 1 zwalidowany mechanizm (Entry H). GAP-001 (Entry O's replikacja) zamknięty NEGATYWNIE (Entry P, `MECHANISM_J_REPLICATION_FAILED`) — Entry O pozostaje `EXPLORATORY_SUPPORTED`, nie zwalidowany.
- **what_is_unknown:** czy GAP-002 lub GAP-003 dostarczy drugiego zwalidowanego mechanizmu.
- **what_was_already_tested:** n/a.
- **allowed_mechanism_space:** n/a — nie dla ResearchOS teraz.
- **disallowed_mechanism_space:** **NIE wysyłać ResearchOS po router/controller mechanizm teraz** — precondition (≥2 zwalidowane mechanizmy z measured regime variance) niespełniony, i pozostaje niespełniony po zamknięciu GAP-001.
- **required_preconditions:** GAP-002 LUB GAP-003 dostarczy drugiego zwalidowanego mechanizmu (GAP-001 już wyczerpany negatywnie).
- **desired_external_evidence:** n/a teraz.
- **research_question:** n/a teraz.
- **candidate_value_if_found:** n/a teraz.
- **estimated_experiment_cost_band:** n/a teraz.
- **dependencies:** GAP-002, GAP-003 (jedyne pozostałe ścieżki do drugiego mechanizmu po zamknięciu GAP-001).
- **blocked_by:** GAP-002, GAP-003.
- **reopen/close condition:** otwiera się automatycznie, gdy GAP-002 lub GAP-003 osiąga `REPLICATED_VALIDATED_TRANSPLANT`.
- **last_updated:** 2026-08-25.
