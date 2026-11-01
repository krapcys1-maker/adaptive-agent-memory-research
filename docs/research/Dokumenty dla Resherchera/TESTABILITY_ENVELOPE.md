# Testability Envelope

Co AAMR może i nie może teraz przetestować, i dlaczego. Grounded w `docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md` (Entries A-O), `docs/00-project/scope.md`, i bezpośrednim czytaniu kodu hosta (`external/venvs/mem0/Lib/site-packages/mem0`, pinned `mem0ai==1.0.6`). **Nie** czerpie z równoległych dokumentów (`RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md` itd.) jako źródła prawdy — patrz README.md tego folderu.

Host: Mem0 1.0.6 (pinned, `external/venvs/mem0`), korpus LongMemEval-S, reader/judge harness (`scripts/arena/`). Model: `deepseek-chat` przez `FixedDecoding` (temp=0 domyślnie).

Statusy: `CAN_TEST_NOW` | `CAN_TEST_WITH_PRECONDITION` | `CANNOT_TEST_NOW` | `UNKNOWN`.

---

## Read-side transformation

- **status:** CAN_TEST_NOW
- **reason:** dominująca kategoria dotychczasowych testów — czysta transformacja renderowanego kontekstu, zero zmian w Mem0.
- **evidence/source:** Entries A, B, I, J, K, L, M, N (6+ mechanizmów tego typu przetestowanych).
- **constraints:** brak — infrastruktura (`fixed_reader.py::user_message`) jest stabilna i wielokrotnie użyta.
- **reopen_condition:** n/a — zawsze otwarte.
- **last_updated:** 2026-08-24.

## Write-side extraction

- **status:** CAN_TEST_NOW
- **reason:** wymaga vendor patch do pinned venv (`external/venvs/mem0/Lib/site-packages/mem0/memory/{utils.py,main.py}`), z dyscypliną kalibracji-przed-wydatkiem — ale mechanika jest teraz **udowodniona end-to-end**: Entry O (`EXTRACTION_COMPLETENESS_VERIFICATION_PASS`) to pierwszy w pełni udany write-side patch tego projektu (kalibracja + 6-unitowy test eksploracyjny, realny traceable repair, 0 regresji). Wcześniej (Entry E, `EVENT_TIME_RESOLUTION_AT_EXTRACTION`) próba write-side była `CALIBRATION_FAILED` — mechanika patcha działała, ale konkretna instrukcja była inert.
- **evidence/source:** Entry O; Entry E (negatywny precedens tej samej ścieżki); `data/lab/arena/extraction-completeness-verification-v1/vendor-patch/manifest.json` (wzorzec patcha).
- **constraints:** (1) tylko sync path (`Memory._add_to_vector_store`, nie `AsyncMemory`) — to jedyna ścieżka, której używa `Mem0Adapter`. (2) każdy patch musi być gated (`metadata[...]=True` domyślnie `False`/absent), żeby nie zaburzyć współdzielonego BASE używanego przez każdy inny mechanizm. (3) kalibracja obowiązkowa przed jakimkolwiek płatnym testem eksploracyjnym (Entry E i Entry O oba to potwierdzają — w obu przypadkach kalibracja albo zatrzymała wydatek, albo złapała realny błąd projektowy przed wydatkiem). (4) koszt ~2x wyższy niż read-side (osobny ingest dla BASE i +ARM, ponieważ mechanizm zmienia CO się zapisuje, nie tylko jak się renderuje).
- **reopen_condition:** n/a — otwarte, z powyższymi ograniczeniami.
- **last_updated:** 2026-08-24.

## Deterministic post-processing

- **status:** CAN_TEST_NOW
- **reason:** czyste transformacje Pythona bez wywołania LLM, testowalne jednostkowo przy $0.
- **evidence/source:** `second_hop_expansion.py`, `temporal_anchor_at_context.py`, `hyde_query_reformulation.py` — wszystkie z pytest coverage.
- **constraints:** brak.
- **reopen_condition:** n/a.
- **last_updated:** 2026-08-24.

## Text-derived signals

- **status:** CAN_TEST_NOW
- **reason:** np. HyDE (Entry M) używa tekstu hipotetycznej odpowiedzi jako query — w pełni wykonalne, precondition potwierdzony przy $0.
- **evidence/source:** Entry M.
- **constraints:** brak infrastrukturalnych.
- **reopen_condition:** n/a.
- **last_updated:** 2026-08-24.

## Embedding-derived signals

- **status:** CAN_TEST_NOW
- **reason:** Mem0 używa lokalnego FastEmbed/MiniLM natywnie; `search()` jest darmowy (zero wywołań LLM/providera) — potwierdzone wielokrotnie ($0 precondition-checki dla mechanizmów G, H, J).
- **evidence/source:** `scripts/arena/mem0_adapter.py` docstring; Entry L, M's own $0 precondition checks.
- **constraints:** brak.
- **reopen_condition:** n/a.
- **last_updated:** 2026-08-24.

## Retrieval-score-derived signals

- **status:** CAN_TEST_NOW
- **reason:** Mem0's własny `search()` zwraca relevance scores bezpośrednio — Entry I (`RETRIEVAL_CONFIDENCE_SIGNAL`) użył top1/top2 score margin wprost. DROP tego mechanizmu był z powodu regime mismatch (small n, nigdy nie trafił na target precondition), **nie** z powodu braku dostępu do sygnału.
- **evidence/source:** Entry I.
- **constraints:** żaden test tego typu jeszcze nie trafił na swój target precondition w praktyce — patrz `DO_NOT_REDISCOVER.md` Entry I dla dokładnego zakresu.
- **reopen_condition:** n/a (infrastrukturalnie zawsze dostępne); konkretny mechanizm Entry I wymaga nowego, celowanego (nie ślepego) samplingu, żeby dać mu uczciwy test.
- **last_updated:** 2026-08-24.

## Context composition

- **status:** CAN_TEST_NOW
- **reason:** praktycznie każdy przetestowany mechanizm to jakaś forma tego (base_ctx/plus_X_ctx assembly).
- **evidence/source:** Entries A, H, I, J, K, L, M, N, O.
- **constraints:** brak.
- **reopen_condition:** n/a.
- **last_updated:** 2026-08-24.

## Reranking

- **status:** CAN_TEST_WITH_PRECONDITION — ale `PRECONDITION_MOSTLY_ABSENT` w praktyce
- **reason:** infrastrukturalnie trywialne (context composition + retrieval scores oba CAN_TEST_NOW), ale **nigdy nie było czego przerankować**: gold_rank=1 w 17/17 obserwowanych retrievals w tym projekcie (znalezisko z archeologii kandydata `SERIAL_POSITION_CONTEXT_REORDER`, dyskwalifikowanego pre-spend w discovery pool v2 z dokładnie tego powodu).
- **evidence/source:** `docs/research/EXTERNAL_DISCOVERY_CANDIDATE_POOL_V2.md` (SERIAL_POSITION_CONTEXT_REORDER disqualification).
- **constraints:** reranking nie ma czego naprawiać przy obecnej szerokości retrieval (`compact`, ~10 items) i obecnej dystrybucji zapytań. Test wymagałby innej szerokości retrieval (np. wide/3000) albo innego zbioru pytań, gdzie gold NIE jest już rank 1.
- **reopen_condition:** znalezienie (gold-blind) próbki, gdzie gold_rank > 1 przy obecnej breadth — obecnie nieznalezione mimo 17 obserwacji.
- **last_updated:** 2026-08-24.

## Raw provenance expansion

- **status:** CAN_TEST_NOW, VALIDATED
- **reason:** jedyny w pełni zwalidowany mechanizm w projekcie.
- **evidence/source:** Entry H (`RAW_PROVENANCE`, `REPLICATED_VALIDATED_TRANSPLANT`).
- **constraints:** dociera tylko do top-1 hit session (single fixed pointer-follow, nie multi-hop) — znany limit, nie testowany do rozszerzenia w tej kampanii.
- **reopen_condition:** n/a — już zwalidowany; dalsze pytania (multi-hop, koszt) to osobne, otwarte luki — patrz `OPEN_TESTABLE_GAPS.md`.
- **last_updated:** 2026-08-24.

## Compact-vs-raw gating

- **status:** CAN_TEST_WITH_PRECONDITION
- **reason:** **WAŻNE — stan zmienił się od czasu, gdy powstał kandydat `semantic-entropy-escalation-gate`** (`Dokumenty z Resherchera/candidates/2026-08-24_mechanism_candidate_semantic-entropy-escalation-gate.md`). Ten kandydat zakłada, że wartość raw fallback jest wciąż otwartym pytaniem ("Sequence this after AAMR's own Experiment #3... resolves whether raw fallback helps at all"). To założenie **nie jest już prawdziwe w tym ledgerze**: Entry H (`RAW_PROVENANCE`) jest `REPLICATED_VALIDATED_TRANSPLANT` — raw fallback POMAGA, bez obserwowanych regresji, zaaplikowany bezwarunkowo. Wartość bramki (gate) nie jest już o poprawności — jest o **efektywności kosztowej**: przykładowy zmierzony narzut tokenów dla raw-augmented arm vs compact w Entry H's own artefaktach to rząd wielkości ~24x więcej tokenów na jedno zapytanie (np. 89 vs 2154 tokenów context dla jednej z badanych jednostek, `raw-provenance-fresh-replication-v1/results.json`).
- **evidence/source:** Entry H; `data/lab/arena/raw-provenance-fresh-replication-v1/results.json` (context_tokens per arm, mean ratio **21.4x** compact_plus_raw/compact across all 8 units, range 5.6x-32.1x — zweryfikowane bezpośrednio, nie pojedynczy przykład).
- **constraints (update 2026-08-25):** dwa cheap-proxy sygnały przetestowane, oba negatywne — retrieval score margin (Entry I, DROP, regime mismatch) i sample-and-cluster semantic entropy (Entry Q, DROP, `MECHANISM_SEG_FAIL` — trigger niepewny na n=2, remedy top-1-anchored dziedziczy ograniczenia `RAW_PROVENANCE`). GAP-005 zamknięty. Pozostałe nieprzetestowane rodziny sygnałów: query-type classification, candidate-set statystyki (liczba/gęstość/redundancja) — żaden nie zaproponowany ani nie zbadany dotychczas.
- **reopen_condition:** kandydat proponujący sygnał spoza już przetestowanych rodzin (nie score-margin, nie embedding-cosine sample-and-cluster entropy), LUB ten sam sygnał z innym remedy niż top-1-anchored single-hop raw injection — patrz `DO_NOT_REDISCOVER.md` Entry Q `reopen_condition`.
- **last_updated:** 2026-08-25.

## Supersession

- **status:** CAN_TEST_WITH_PRECONDITION
- **reason:** naiwne podejście (osobny mechanizm obok Mem0's własnej rekoncyliacji) jest `PRECONDITION_ABSENT` — Mem0's własna, żywa (nie stub) logika ADD/UPDATE/DELETE (`_update_memory`/`_delete_memory` w pinned venv, CODE_VERIFIED) już absorbuje ten target failure przed jakimkolwiek read-side mechanizmem (Entry G, DROP). Interwencja MUSIAŁABY wejść WEWNĄTRZ wywołania rekoncyliacji Mem0 (`get_update_memory_messages`) — technicznie teraz udowodnione możliwe (Entry O's vendor-patch pattern), ale nie próbowane w tym konkretnym punkcie.
- **evidence/source:** Entry F, G (naiwne podejście, DROP); Entry O (dowód, że patch WEWNĄTRZ Mem0's write path jest wykonalny).
- **constraints:** wymaga patcha wewnątrz `get_update_memory_messages`/reconciliation call, nie równoległego mechanizmu.
- **reopen_condition:** n/a — otwarte z powyższym ograniczeniem.
- **last_updated:** 2026-08-24.

## Contradiction handling

- **status:** CAN_TEST_WITH_PRECONDITION
- **reason:** identyczne ograniczenie jak supersession — ta sama Mem0 reconciliation absorbuje sprzeczności przed dotarciem do read-side mechanizmu.
- **evidence/source:** ten sam co supersession.
- **constraints:** ten sam co supersession.
- **reopen_condition:** n/a.
- **last_updated:** 2026-08-24.

## Provenance routing

- **status:** CAN_TEST_WITH_PRECONDITION
- **reason:** związane z compact-vs-raw gating — patrz wyżej.
- **evidence/source:** patrz compact-vs-raw gating.
- **constraints:** patrz compact-vs-raw gating.
- **reopen_condition:** n/a.
- **last_updated:** 2026-08-24.

## Deterministic controllers

- **status:** CANNOT_TEST_NOW
- **reason:** wymaga ≥2 niezależnie zwalidowanych mechanizmów z mierzoną wariancją reżimu (jeden jednostkę-klasę gdzie A>B, inną gdzie B>A). Projekt ma obecnie 1 zwalidowany mechanizm (Entry H); Entry O jest `EXPLORATORY_SUPPORTED`, nie zwalidowany. Warunek strukturalnie niespełniony.
- **evidence/source:** `validated_mechanisms_count_project_total: 1` w `data/lab/arena/autonomous-research-budget-v2/ledger.json`.
- **constraints:** —
- **reopen_condition:** drugi mechanizm osiąga `REPLICATED_VALIDATED_TRANSPLANT` (najbliższy kandydat: Entry O po świeżej replikacji).
- **last_updated:** 2026-08-24.

## API-level self-consistency

- **status:** CAN_TEST_WITH_PRECONDITION
- **reason:** mechanicznie trywialne (wielokrotne próbkowanie przez `decoding.py`, już używane gdzie indziej w projekcie) — ale cała rodzina (CoVe, self-consistency, verbalized-confidence, RARR, HoT) była **deprioryzowana jako grupa**, nie testowana indywidualnie, po diagnostyce $0 pokazującej, że 9-10/13 obserwowanych błędów `BASE` to retrieval-absence, nie evidence-present-but-misread — jedyny failure mode, który ta rodzina mogłaby naprawić.
- **evidence/source:** Entry M's source diagnostic (project memory, absence-taxonomy tally).
- **constraints:** test tej rodziny bez wcześniejszego, celowanego przesiania próbki (gold-blind, np. przez sprawdzenie czy potrzebny fakt istnieje w retrieved top-10 przy $0) będzie prawdopodobnie underpowered, tak jak większość testów tej kampanii.
- **reopen_condition:** n/a — otwarte, z zastrzeżeniem powyżej.
- **last_updated:** 2026-08-24.

---

## Poza zakresem badawczej fazy (per `docs/00-project/scope.md`)

## Model fine-tuning

- **status:** CANNOT_TEST_NOW
- **reason:** `scope.md`: "Training a large model before establishing deterministic and classical-ML baselines" — jawnie poza zakresem tej fazy badawczej.
- **evidence/source:** `docs/00-project/scope.md` §Out of scope.
- **constraints:** —
- **reopen_condition:** formalna decyzja projektu o przejściu do kolejnej fazy (nie zależy od AAMR samego).
- **last_updated:** 2026-08-24.

## Hidden states / internal activations

- **status:** CANNOT_TEST_NOW
- **reason:** `scope.md` System boundary: "must not assume access to hidden model activations or provider-side training."
- **evidence/source:** `docs/00-project/scope.md` §System boundary.
- **constraints:** —
- **reopen_condition:** formalna zmiana system boundary.
- **last_updated:** 2026-08-24.

## Provider-side training

- **status:** CANNOT_TEST_NOW
- **reason:** identyczne jak hidden states — ten sam explicit system boundary.
- **evidence/source:** `docs/00-project/scope.md` §System boundary.
- **constraints:** —
- **reopen_condition:** formalna zmiana system boundary.
- **last_updated:** 2026-08-24.

## Direct weight updates

- **status:** CANNOT_TEST_NOW
- **reason:** implikowane przez zakaz fine-tuningu i hidden-activation access — nie ma ścieżki do modyfikacji wag bez jednego z tych dwóch.
- **evidence/source:** `docs/00-project/scope.md`.
- **constraints:** —
- **reopen_condition:** formalna zmiana system boundary.
- **last_updated:** 2026-08-24.

## Custom logprobs

- **status:** UNKNOWN
- **reason:** `scope.md` nie zakazuje jawnie logprobs na poziomie API (odrębne od "hidden activations") — ale ten projekt nigdy nie sprawdził, czy endpoint DeepSeek używany przez `FixedDecoding`/`provider_proxy.py` w ogóle je udostępnia. Nie zgaduję.
- **evidence/source:** brak — niezweryfikowane.
- **constraints:** wymaga bezpośredniego sprawdzenia API (darmowe/tanie: jedno wywołanie z `logprobs=True`).
- **reopen_condition:** AAMR wykonuje ten $0-$0.001 check.
- **last_updated:** 2026-08-24.
