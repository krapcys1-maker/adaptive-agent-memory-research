# Do Not Rediscover

Transkrypcja `docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md` (Entries A-Q) do formatu ResearchOS. **Ledger jest źródłem prawdy** — ten plik jest pochodną, regenerowaną, nie edytowaną ręcznie niezależnie.

Dozwolone statusy: `VALIDATED` | `REPLICATED_VALIDATED` | `FAILED` | `FAILED_REPLICATION` | `DROP` | `PAUSED` | `PRECONDITION_UNAVAILABLE` | `PRECONDITION_ABSENT` | `REGIME_DEPENDENT` | `ALREADY_OWNED` | `EXTERNAL_ONLY` | `UNKNOWN`.

---

### Entry A — `TEMPORAL_ANCHOR_AT_CONTEXT` × `SESSION_EVENT_ALIGNED`

- **canonical_name:** TEMPORAL_ANCHOR_AT_CONTEXT
- **aliases:** session-timestamp rendering, `[YYYY-MM-DD] {fact}` prefix
- **status:** `REGIME_DEPENDENT` (SUPPORTED, qualified — nie DROP, nie zwalidowany)
- **source_system:** Hindsight (donor), GRAVITY (external anchoring class)
- **AAMR_experiment_ids:** E1 (exploratory), Stage 2 (fresh replication), Mechanism I / Entry N (narrow confirmatory)
- **result:** pozytywny w wąskim regime (`TEMPORAL_BOUNDARY`, duration/arithmetic pytania), 0 regresji w 3 niezależnych próbkach; nie replikował w szerszym regime (Entry B).
- **failure_reason:** n/a — nie failed, status to "supported but narrow."
- **positive_regime:** duration/arithmetic pytania między dwoma nazwanymi wydarzeniami, gdzie potrzebna data jest faktycznie retrieved.
- **negative_regime:** `SESSION_EVENT_DIVERGENT` (Entry B) — wiele faktów dzieli jeden później-zapisany session timestamp rozbieżny z ich własną in-text datą.
- **precondition_status:** PRECONDITION_ABSENT często w praktyce — potrzebna data musi być w retrieved top-10, co nie zawsze się dzieje (retrieval-absence, nie problem tego mechanizmu).
- **do_not_retry:** nie w tym samym designie (session-timestamp rendering) bez nowej, jeszcze węższej regime-selekcji.
- **reopen_condition:** dedykowana replikacja na jednostkach z potwierdzonym $0 precondition (data faktycznie w top-10).
- **related_mechanisms:** Entry B, Entry N, GAP-003 (structured write-side alternative).

### Entry B — `TEMPORAL_ANCHOR_AT_CONTEXT` × `SESSION_EVENT_DIVERGENT`

- **canonical_name:** TEMPORAL_ANCHOR_AT_CONTEXT (negative-transfer subcase)
- **aliases:** —
- **status:** `REGIME_DEPENDENT` (OBSERVED_CASE, negative)
- **source_system:** n/a — obserwacja, nie osobny mechanizm.
- **AAMR_experiment_ids:** Stage 2 (`00ca467f` regression)
- **result:** negatywny w tym konkretnym regime — recap-session z wieloma faktami o różnych in-text datach, jedna wspólna session-data myli readera.
- **failure_reason:** wiele faktów dzieli jeden później-zapisany session timestamp.
- **positive_regime:** n/a (to jest negative-regime entry).
- **negative_regime:** many-item filter/count pytania z rozbieżnym session-vs-event-time.
- **precondition_status:** trap znany i strukturalnie unikany przez późniejsze klasyfikatory (Entry N).
- **do_not_retry:** unconditional temporal anchoring na many-item filter/count pytaniach.
- **reopen_condition:** n/a — to jest znany, udokumentowany failure mode do unikania, nie kandydat do retestu.
- **related_mechanisms:** Entry A, Entry N.

### Entry C — `HARMFUL_SIBLING_DISTRACTION`

- **canonical_name:** HARMFUL_SIBLING_DISTRACTION
- **aliases:** —
- **status:** `UNKNOWN` (OBSERVED_CASE, n=1, explicitly nie promowany do measured general failure mode)
- **source_system:** n/a — failure-mode candidate, nie mechanizm-fix.
- **AAMR_experiment_ids:** E1 (`gpt4_f420262c`)
- **result:** 1 potwierdzony przypadek; 0/5 w niezależnej Stage 2 próbce.
- **failure_reason:** n/a.
- **positive_regime:** n/a (to jest failure-mode identification, nie fix).
- **negative_regime:** n/a.
- **precondition_status:** PRECONDITION_UNAVAILABLE do measured general law przy n=1.
- **do_not_retry:** n/a — nie ma jeszcze fix do przetestowania.
- **reopen_condition:** dedykowana gold-blind próbka enumeration/identification pytań ze znanymi close-rank sibling entities.
- **related_mechanisms:** żaden bezpośredni fix zaproponowany.

### Entry D — `AUTHORITY_COLLAPSE_SAFE_CONSOLIDATION`

- **canonical_name:** AUTHORITY_COLLAPSE_SAFE_CONSOLIDATION
- **aliases:** —
- **status:** `EXTERNAL_ONLY` (AAMR_UNTESTED, NOT_ACTIONABLE_YET)
- **source_system:** zewnętrzny paper ("When Memory Becomes Authority", arXiv:2608.01679)
- **AAMR_experiment_ids:** żaden.
- **result:** n/a — AAMR nie ma mechanizmu konsolidacji do przetestowania.
- **failure_reason:** n/a.
- **positive_regime:** n/a.
- **negative_regime:** n/a.
- **precondition_status:** PRECONDITION_UNAVAILABLE — AAMR nie ma dziś żadnego consolidation/summarization mechanizmu.
- **do_not_retry:** n/a.
- **reopen_condition:** przed zaprojektowaniem PIERWSZEGO AAMR consolidation/summarization mechanizmu — to powinno bramkować taki design, nie być testowane samodzielnie.
- **related_mechanisms:** żaden istniejący.

### Entry E — `EVENT_TIME_RESOLUTION_AT_EXTRACTION`

- **canonical_name:** EVENT_TIME_RESOLUTION_AT_EXTRACTION
- **aliases:** inline relative-time resolution instruction
- **status:** `FAILED` (CALIBRATION_FAILED, NOT_ELIGIBLE dla pełnego testu)
- **source_system:** Hindsight (native write-time grounding, funkcjonalny odpowiednik)
- **AAMR_experiment_ids:** E2 calibration
- **result:** 0/5 przypadków zmieniło zachowanie ekstrakcji — instrukcja inertna na `deepseek-chat`.
- **failure_reason:** prompt's own few-shot examples modelują USUWANIE relative-time słów, neutralizując dodaną instrukcję (root cause zidentyfikowany dopiero podczas Entry O's archeologii, patrz GAP-003).
- **positive_regime:** żaden zaobserwowany.
- **negative_regime:** ten konkretny design (bare prose instruction bez zmiany few-shot) na `deepseek-chat`.
- **precondition_status:** PRECONDITION_ABSENT dla tego konkretnego designu.
- **do_not_retry:** identyczny design (inline instruction, unrevised few-shot) bez zmiany.
- **reopen_condition:** strukturalnie różny design (np. dedicated structured output field zamiast inline substitution — patrz GAP-003, DETERMINISTIC_TEMPORAL_RESOLVER_POSTPROCESS).
- **related_mechanisms:** Entry A, Entry N, GAP-003.

### Entry F/G — `CURRENT_STATE_OVER_HISTORY`

- **canonical_name:** CURRENT_STATE_OVER_HISTORY
- **aliases:** state/supersession mechanism, StateMem-style
- **status:** `DROP` (harness precondition never met, mechanizm nie obalony logicznie)
- **source_system:** StateMem, STALE, StateAuditor (zewnętrzne archeologie)
- **AAMR_experiment_ids:** Stage 1 (12 synthetic probes)
- **result:** DROP w V1 harness — Mem0's własna, żywa (nie stub) logika ADD/UPDATE/DELETE rekoncyliacji (CODE_VERIFIED w pinned venv) już absorbuje target failure zanim jakikolwiek read-side mechanizm go zobaczy.
- **failure_reason:** precondition (stale facts survivable to read-time) nigdy nie zaistniał w tym harnessie — Mem0 usuwa/aktualizuje je wcześniej.
- **positive_regime:** żaden zaobserwowany w tym harnessie.
- **negative_regime:** n/a — mechanizm nieużyty, nie porażka wykonania.
- **precondition_status:** PRECONDITION_ABSENT dla naiwnego (równoległego) designu; CAN_TEST_WITH_PRECONDITION dla designu WEWNĄTRZ Mem0's reconciliation call (patrz TESTABILITY_ENVELOPE.md Supersession, teraz technicznie udowodnione możliwe przez Entry O's vendor-patch pattern).
- **do_not_retry:** naiwny (równoległy do Mem0's reconciliation) design.
- **reopen_condition:** design interweniujący WEWNĄTRZ `get_update_memory_messages`/reconciliation call, nie obok niego. Uwaga: discovery-rebuild v2 znalazła fałszywy `CODE_VERIFIED` claim próbujący ponownie otworzyć to jako "Mem0 v2.0.18, purely additive" — zweryfikowane jako FAŁSZYWE (niewłaściwy branch źródła sprawdzony), oryginalny DROP stoi.
- **related_mechanisms:** supersession/contradiction handling w TESTABILITY_ENVELOPE.md.

### Entry H — `RAW_PROVENANCE` (C4)

- **canonical_name:** RAW_PROVENANCE
- **aliases:** RAW_PROVENANCE_EXPANSION, raw session injection behind top-1 hit
- **status:** `REPLICATED_VALIDATED` — **jedyny w pełni zwalidowany mechanizm projektu.**
- **source_system:** TierMem, Verbatim Chunks, Eywa (zewnętrzne, konwergentne wsparcie)
- **AAMR_experiment_ids:** E3 (exploratory), fresh 8-unit replication
- **result:** pozytywny, zreplikowany, mechanistically confirmed trace, 0 regresji obserwowanych. Mean token overhead ~21.4x compact_plus_raw/compact (zakres 5.6x-32.1x).
- **failure_reason:** n/a.
- **positive_regime:** `COMPACT_ABSENCE_OR_UNDERDETAIL` — detal utracony w compact extraction, obecny w raw session behind top-1 hit.
- **negative_regime:** nie znaleziono negatywnego regime; znany LIMIT (nie failure): nie dociera poza top-1 hit session (single fixed pointer-follow, brak multi-hop).
- **precondition_status:** potwierdzony, powszechny w praktyce.
- **do_not_retry:** n/a — już zwalidowany, nie do ponownego "odkrycia".
- **reopen_condition:** n/a. Rozszerzenia (multi-hop, cost-gating) to OSOBNE, otwarte pytania — patrz GAP-005.
- **related_mechanisms:** GAP-004 (assistant-turn-scoping, znany limit tej samej ścieżki `as_records()`), GAP-005 (cost-efficiency gate).

### Entry I — `RETRIEVAL_CONFIDENCE_SIGNAL`

- **canonical_name:** RETRIEVAL_CONFIDENCE_SIGNAL
- **aliases:** score-margin flag, top1/top2 confidence proxy
- **status:** `PRECONDITION_UNAVAILABLE` (small-n regime mismatch, mechanizm nigdy nie trafił na target precondition)
- **source_system:** "When Confidence Takes the Wrong Path" (arXiv:2606.22728)
- **AAMR_experiment_ids:** Mechanism D exploratory (n=4, przerwany przez provider cap)
- **result:** NULL. 3/4 flagged (margin<0.10), 0 repairs, 0 regresji. Odpowiedź TEKSTOWO zmienia się, poprawność nie.
- **failure_reason:** oba flagged-and-wrong units to absence failures (fakt całkowicie brakujący z top-10), nie ambiguous-ranking failures — sygnał nie mógł pomóc z konstrukcji.
- **positive_regime:** genuine score ambiguity gdzie gold jest retrieved ale nie top-ranked — NIEPRZETESTOWANY (ten konkretny regime nigdy nie wystąpił w n=4).
- **negative_regime:** absence failures (mechanizm nie ma czego naprawić).
- **precondition_status:** PRECONDITION_UNAVAILABLE przy tej próbce, teoretycznie CAN_TEST_WITH_PRECONDITION przy celowanej selekcji.
- **do_not_retry:** identyczna, ślepa selekcja bez pre-screeningu.
- **reopen_condition:** gold-blind selekcja jednostek, gdzie $0 check potwierdza score-margin<threshold I gold jest retrieved-but-not-top1 (nie absence).
- **related_mechanisms:** GAP-005 (compact-vs-raw gate używa pokrewnego, ale RÓŻNEGO pytania — "czy compact wystarczy", nie "czy top1/top2 są blisko siebie").

### Entry J — `SAME_CATEGORY_ENTITY_ENUMERATION`

- **canonical_name:** SAME_CATEGORY_ENTITY_ENUMERATION
- **aliases:** sibling-entity disambiguation
- **status:** `PRECONDITION_ABSENT` (regime mismatch, mechanizm nigdy nie odpalił)
- **source_system:** arXiv:2606.10388 ("Right Family, Wrong Skill")
- **AAMR_experiment_ids:** Mechanism E exploratory (n=8)
- **result:** 0/8 odpaleń — inert (byte-identical to BASE) na każdej jednostce.
- **failure_reason:** precondition (≥2 distinct same-category entities co-retrieved) koreluje z SZEROKĄ retrieval breadth (208 items w jedynym znanym prawdziwym przypadku) — nie z `compact` (~10-item) breadth, którego ten test użył.
- **positive_regime:** szeroka retrieval breadth (np. `_3000`/wide operating point) — NIEPRZETESTOWANE.
- **negative_regime:** `compact` breadth.
- **precondition_status:** PRECONDITION_ABSENT przy `compact` breadth.
- **do_not_retry:** przy `compact` breadth.
- **reopen_condition:** test przy szerokiej retrieval breadth (matching znanego prawdziwego przypadku).
- **related_mechanisms:** GAP-006 (reranking, ta sama breadth-dependency uwaga).

### Entry K — `RETRIEVAL_RANK_ANNOTATION`

- **canonical_name:** RETRIEVAL_RANK_ANNOTATION
- **aliases:** `[rank N/M, relevance X.XX]` prefix
- **status:** `FAILED` (fired universally, net negative)
- **source_system:** ogólna motywacja "confident-but-wrong" family.
- **AAMR_experiment_ids:** Mechanism F exploratory (n=8)
- **result:** odpaliło 8/8 (uniwersalne precondition zadziałało jak zaprojektowano), ale 0 repairs, 1 regression.
- **failure_reason:** regresja to "judge-penalized epistemic caution" — dodana struktura/adnotacja indukuje reader hedging, który strict binary judge karze nawet gdy substancja jest porównywalna. Wzorzec potwierdzony 3x niezależnie w projekcie (E1's `+SRC`, Stage2, ten mechanizm).
- **positive_regime:** żaden zaobserwowany.
- **negative_regime:** unconditional annotation-style interwencje ogólnie — wzorzec cross-mechanism.
- **precondition_status:** confirmed universal (odpaliło wszędzie), ale efekt negatywny.
- **do_not_retry:** jakikolwiek unconditional annotation/formatting mechanizm bez explicit ochrony przed hedging.
- **reopen_condition:** design explicite wymuszający committed answer (nigdy nie emitujący hedge) — patrz Entry M's HYDE (żaden hedging risk, bo nie dotyka widocznej odpowiedzi wcale).
- **related_mechanisms:** cross-cutting "judge-penalized epistemic caution" pattern — dotyczy KAŻDEGO przyszłego annotation-style kandydata.

### Entry L — `SECOND_HOP_ASSOCIATIVE_EXPANSION`

- **canonical_name:** SECOND_HOP_ASSOCIATIVE_EXPANSION
- **aliases:** A-MEM-style second Mem0 search seeded by top-1 hit
- **status:** `DROP` (regime confirmed, mechanizm nie pomaga: semantic drift)
- **source_system:** A-MEM (agiresearch/A-mem, NeurIPS 2025)
- **AAMR_experiment_ids:** Mechanism G exploratory (n=6)
- **result:** odpaliło 2/6 (~33%, zgodnie z przewidywaniem), ale skojarzony item był ZAWSZE topically nieistotny dla query.
- **failure_reason:** seedowanie drugiego hopu tekstem top-1 hit (nie query) optymalizuje pod podobieństwo do top-1, nie do query — strukturalny semantic drift, nie przypadek strojenia.
- **positive_regime:** żaden zaobserwowany.
- **negative_regime:** każdy przypadek, gdzie hop2 jest seedowany top-1's tekstem zamiast query.
- **precondition_status:** confirmed real fire rate (~33%), ale treść zawsze nietrafna.
- **do_not_retry:** identyczny design (seed=top-1 text).
- **reopen_condition:** query-seeded (nie top-1-seeded) second hop — nietestowane, explicite zasugerowane jako alternatywa w ledgerze.
- **related_mechanisms:** GAP-002 (multi-query fan-out to inny, potencjalnie lepszy sposób osiągnięcia podobnego celu).

### Entry M — `HYDE_QUERY_REFORMULATION`

- **canonical_name:** HYDE_QUERY_REFORMULATION
- **aliases:** HyDE, hypothetical document embeddings dla Mem0 search
- **status:** `DROP` (precondition confirmed real gdzie indziej, ta próbka wylosowała inny absence subtype)
- **source_system:** HyDE (Gao et al., ACL 2023)
- **AAMR_experiment_ids:** Mechanism H exploratory (n=6)
- **result:** odpaliło 6/6, ale 2 BASE-wrong units w tej próbce to write-time-extraction-loss (subtype 1), nie retrieval-ranking-miss (subtype 2, target tego mechanizmu). $0 check na 2 INNYCH, już zbadanych jednostkach potwierdził realny, duży efekt precondition (absent→rank1, 2/2).
- **failure_reason:** small-n draw property, nie refutacja precondition.
- **positive_regime:** retrieval-ranking-miss (fact present w store, unranked pod literal query) — CONFIRMED REAL gdzie indziej, niedostatecznie próbkowany w tym teście.
- **negative_regime:** write-time-extraction-loss (subtype 1) — ten mechanizm strukturalnie nie może tego naprawić.
- **precondition_status:** confirmed real (2/2 w dedykowanym $0 checku), ale rzadki w porównaniu do subtype 1 w tym projekcie (~2/13 vs ~9/13 wszystkich BASE-wrong units).
- **do_not_retry:** plain single-shot HyDE bez pre-screeningu na ten konkretny subtype.
- **reopen_condition:** większa próbka LUB gold-blind pre-screening (przez `memory.get_all()` full-store dump) konkretnie dla subtype-2 przypadków.
- **related_mechanisms:** GAP-002 (multi-query fan-out, alternatywny mechanizm dla tego samego subtype).

### Entry N — `TEMPORAL_ANCHOR_AT_CONTEXT` × `TEMPORAL_BOUNDARY`

- **canonical_name:** TEMPORAL_ANCHOR_AT_CONTEXT (narrow confirmatory replication)
- **aliases:** patrz Entry A.
- **status:** `FAILED_REPLICATION` na gate (0 repairs, wymagane ≥2), ale 0 regresji — nie DROP, Entry A pozostaje SUPPORTED/qualified.
- **source_system:** patrz Entry A.
- **AAMR_experiment_ids:** Mechanism I confirmatory replication (n=8)
- **result:** 0 net repairs, 0 regresji. Obydwa BASE-wrong units to retrieval-absence, nie "dates present but unrendered" — dokładny gap tego mechanizmu.
- **failure_reason:** small-n draw property — 3 niezależne próbki (E1, Stage 2's TEMPORAL_BOUNDARY bucket, ten test) teraz pokazują 0 regresji w regime, ale genuine "dates present, unrendered" repair opportunities są rzadkie.
- **positive_regime:** patrz Entry A — teraz jeszcze węziej potwierdzone.
- **negative_regime:** patrz Entry B.
- **precondition_status:** confirmed safe (0/3 samples z regresją w-regime), efficacy at typical sample size unconfirmed.
- **do_not_retry:** identyczny design bez pre-screeningu na genuine "unrendered date" przypadki.
- **reopen_condition:** większa próbka LUB pre-screened selekcja (gold-blind, $0 sprawdzenie że potrzebna data para faktycznie istnieje w top-10).
- **related_mechanisms:** Entry A, Entry E, GAP-003.

### Entry O — `EXTRACTION_COMPLETENESS_VERIFICATION_PASS`

- **canonical_name:** EXTRACTION_COMPLETENESS_VERIFICATION_PASS
- **aliases:** ProMem-style completeness check, write-time "what did you miss" pass
- **status:** `REGIME_DEPENDENT` (`EXPLORATORY_SUPPORTED` przy exploratory teście, `FAILED_REPLICATION` na fresh replikacji — nigdy `REPLICATED_VALIDATED`, nigdy `DROP`)
- **source_system:** ProMem (measured direct na LongMemEval, ablation izolujący ten etap)
- **AAMR_experiment_ids:** kalibracja (`PM-20260824-9d020373`), exploratory test v1 (n=6, `PM-20260824-195a1656`), fresh replication v2 (n=8, `PM-20260824-df787f9d`)
- **result:** v1: 1 genuine, traceable repair (power-bank fact split z niewłaściwej ramy travel-organizing), 1 druga nominalna "naprawa" poprawnie reklasyfikowana jako judge noise, 0 regresji. v2 (świeża replikacja, Entry P): 0 net repairs, 0 regresji — mechanizm odpalał na każdej jednostce, ale 4 BASE-wrong jednostki trafiły na TRZY różne inne, już udokumentowane absence subtypes (temporal-representation-loss, knowledge-update/supersession, assistant-turn-scoping-loss), nie na target regime tego mechanizmu.
- **failure_reason:** replikacja: regime-rarity, nie flaw w mechanizmie — łączny repair rate v1+v2 to ~1/14 (~7%) świeżych jednostek pokazujących rzeczywisty target precondition.
- **positive_regime:** sesje z enumerable listą (numbered, comma/and-separated), którą Mem0's własna ekstrakcja bunduje w jeden fact string -- POTWIERDZONY realny (v1), ale RZADKI (~1/14 świeżych jednostek).
- **negative_regime:** cross-session write-time extraction loss (`2311e44b`); temporal-representation-loss (`5e1b23de`); knowledge-update/supersession (`2133c1b5`); assistant-turn-scoping-loss (`1d4da289`) — wszystkie strukturalnie poza zasięgiem tego mechanizmu, 0 szkody w każdym przypadku.
- **precondition_status:** confirmed real (CODE_VERIFIED w pinned venv, shipped few-shot example uczy merging) ale RZADKI w praktyce -- nie replikuje niezawodnie przy n=6-8.
- **do_not_retry:** identyczny mechanizm bez subtype-pre-screeningu przy podobnym n (6-8) — prawdopodobnie znowu wylosuje inny absence subtype.
- **reopen_condition:** większa (>8 jednostek) LUB subtype-pre-screened (gold-blind, strukturalna) próbka specyficznie wzbogacona o pytania z bundled-enumeration shape.
- **related_mechanisms:** GAP-003 (pokrewny write-side subtype-3 kandydat), Entry E (poprzednia write-side próba, inny mechanizm), Entries M/N (ten sam "confirmed-real-precondition, small-n draw missed it" pattern, teraz obserwowany 4. raz w tej kampanii).

### Entry P — `EXTRACTION_COMPLETENESS_VERIFICATION_PASS` (fresh replication)

- **canonical_name:** EXTRACTION_COMPLETENESS_VERIFICATION_PASS (replikacja Entry O)
- **aliases:** patrz Entry O.
- **status:** `FAILED_REPLICATION` na gate (0 repairs, wymagane ≥1), ale 0 regresji — Entry O pozostaje `EXPLORATORY_SUPPORTED`, nie `DROP`.
- **source_system:** patrz Entry O.
- **AAMR_experiment_ids:** replikacja v2 (n=8, `PM-20260824-df787f9d`)
- **result:** 0 net repairs, 0 regresji na 8 świeżych jednostkach. Mechanizm odpalał uniwersalnie (kontekst różnił się w każdej jednostce), ale nigdy nie zmienił osądzonego wyniku.
- **failure_reason:** small-n draw property — 4 BASE-wrong jednostki trafiły na 3 różne, inne absence subtypes.
- **positive_regime:** patrz Entry O — teraz potwierdzone jako rzadki (~1/14).
- **negative_regime:** patrz Entry O.
- **precondition_status:** confirmed safe (0/2 samples z regresją), efficacy rzadka.
- **do_not_retry:** identyczny design bez pre-screeningu przy podobnym n.
- **reopen_condition:** patrz Entry O.
- **related_mechanisms:** Entry O, Entry N (identyczny "FAIL_ON_REPLICATION_GATE, 0 regresji" shape).

### Entry Q — `SEMANTIC_ENTROPY_SUFFICIENCY_GATE`

- **canonical_name:** SEMANTIC_ENTROPY_SUFFICIENCY_GATE
- **aliases:** semantic-entropy-escalation-gate (ResearchOS's original name, `rmc-2026-08-24-001`), sample-and-cluster black-box entropy gate, SUGAR-style compact-vs-raw gate
- **status:** `FAILED`
- **source_system:** SUGAR (arXiv 2501.04899), Kuhn et al. (Nature 2024, black-box semantic entropy). Pierwszy kandydat tej kampanii pochodzący z ResearchOS handoff (`rmc-2026-08-24-001`), nie z AAMR's własnej discovery-rebuild puli.
- **AAMR_experiment_ids:** kalibracja (`PM-20260825-41d5d71e`, $0, reuse już-oznaczonych danych), przyczynowy test (`PM-20260825-e88248ff`, n=6, $0.435904)
- **result:** BASE 3/6, GATE 3/6, 0 regresji, escalacja odpaliła selektywnie (2/6) ale 0/2 traceable repairs. Kalibracja sama w sobie była czysta (separacja +0.804) — to remedy i trigger na konkretnej próbce zawiodły, nie sam podstawowy sygnał.
- **failure_reason:** dwa złożone problemy. (1) Trigger niepewny na n=2 escalated: 1 prawdziwy positive, 1 clustering artifact (embedding-cosine clustering rozdzieliło niemal identyczne odpowiedzi na 3 klastry). (2) Remedy (`raw_session()`, top-1-anchored, single-hop, bez session-level date stamps) dziedziczy dokładnie te same ograniczenia co `RAW_PROVENANCE` (Entry H) — oba escalated units trafiły na już znane absence subtypes: retrieval-ranking-miss (2) skomponowany z assistant-turn-scoping-loss (4) w jednym przypadku, i (nieescalowany, ale wciąż zły) temporal-representation-loss (3) w drugim, żaden z nich strukturalnie nienaprawialny przez ten konkretny remedy.
- **positive_regime:** teoretyczna — absence-type failures (informacja rzeczywiście nieobecna w compact context). Nie zaobserwowano na tej próbce.
- **negative_regime:** presence-type failures (informacja obecna, reader błędnie nie generalizuje/nie stosuje) — dokładnie ryzyko, które ResearchOS's własny kandydat nazwał `possible_negative_regime` PRZED testem. Także: absence-type failures poza zasięgiem top-1-anchored single-hop remedy (subtypes 2, 3, 4).
- **precondition_status:** podstawowy sygnał (semantic entropy separuje known-sufficient/known-insufficient) confirmed real w kalibracji — ale trigger (embedding-cosine clustering) i remedy (single-hop raw injection) każdy z osobna niewystarczające na tym failure mix.
- **do_not_retry:** identyczny design (embedding-cosine trigger + top-1-anchored `raw_session()` remedy) bez zmiany co najmniej jednego z dwóch komponentów.
- **reopen_condition:** kandydat proponujący (a) inną metodę clusteringu dla triggera (np. bidirectional NLI entailment zamiast embedding-cosine, żeby uniknąć `0edc2aef`-class artefaktu), LUB (b) inny remedy niż top-1-anchored single-hop raw injection (np. multi-hop, albo remedy niosący session-level date stamps) — z jasnym uzasadnieniem, dlaczego omija te dwie konkretne, zmierzone porażki.
- **related_mechanisms:** Entry H (`RAW_PROVENANCE`, remedy code shared, limitations inherited), Entry I (`RETRIEVAL_CONFIDENCE_SIGNAL`, pokrewny ale różny sygnał — score margin, nie sample-and-cluster entropy), GAP-002/GAP-003 (inne, niezależne kandydaci na te same absence subtypes 2/3).
