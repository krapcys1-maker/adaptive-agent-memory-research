# Dokumenty z Resherchera — ResearchOS → AAMR outbox

**Jedna strona dwukierunkowego mostu (2026-08-24).** Ten folder: ResearchOS → AAMR, write-only od strony ResearchOS. Druga strona, `../Dokumenty dla Resherchera/`: AAMR → ResearchOS, read-only od strony ResearchOS — tam AAMR publikuje `researchos_contract_v1.json` (testability envelope, otwarte luki, DO_NOT_REDISCOVER, aktywne research requesty). ResearchOS nigdy nie pisze do `Dokumenty dla Resherchera/` i nigdy nie czyta ani nie modyfikuje żadnych innych plików w repo `adaptive-agent-memory-research` poza tymi dwoma folderami (plus jednorazowe, read-only audyty finalnych/autorytatywnych dokumentów AAMR na wyraźne polecenie, udokumentowane osobno w ResearchOS-owym `docs/postmortems/`).

## Co tu trafia

Tylko rzeczy, które ResearchOS uznał za warte przekazania testerowi AAMR:

- kandydaci mechanizmów do sprawdzenia
- ważne wnioski z paperów / repo
- negative evidence
- sprzeczności wymagające eksperymentu
- research gaps
- pytania do testera
- propozycje eksperymentów
- informacje o preconditions
- flagi "to wygląda jak duplikat istniejącego mechanizmu"

## Co tu NIE trafia

- chain-of-thought
- surowe logi
- każdy znaleziony paper
- luźne notatki
- pełne raporty ResearchOS bez potrzeby
- wyniki oznaczone jako VALIDATED, jeśli nie zostały przetestowane przez AAMR

## Struktura

```
Dokumenty z Resherchera/
  README.md
  candidates/   — mechanizmy, propozycje eksperymentów, precondition-checki, duplicate-flagi
                  (type: mechanism_candidate | experiment_proposal | precondition_note | duplicate_flag)
                  _TEMPLATE_candidate.md — ogólny przypadek
                  _TEMPLATE_aamr_request_response.md — gdy source_request_id jest ustawiony (patrz niżej)
  notes/        — informacyjne, bez implikowanego testu
                  (type: external_signal | negative_evidence | contradiction | research_gap)
  questions/    — pytania wprost do testera
                  (type: question)
```

Każdy folder zawiera plik(i) `_TEMPLATE_*.md` — kopiuj jako punkt startowy dla nowego wpisu, nie edytuj templatu samego w sobie.

## Odpowiedź na konkretny AAMR research request

Jeśli wpis odpowiada na konkretny, OPEN request z `../Dokumenty dla Resherchera/RESEARCH_REQUESTS/`, użyj `candidates/_TEMPLATE_aamr_request_response.md` zamiast ogólnego szablonu — ma pełny, wymagany zestaw sekcji (what we found / what we did not find / external evidence / negative evidence / testability check / duplicate check / preconditions / cheapest meaningful test / what would falsify it / uncertainties) i pola `source_request_id` / `source_gap_id` / `researchos_run_id` w frontmatterze. Zwykły `_TEMPLATE_candidate.md` też ma te trzy pola (opcjonalnie) na wypadek, gdyby wpis luźno nawiązywał do requestu bez pełnej struktury odpowiedzi.

## Nazewnictwo plików

`YYYY-MM-DD_<type>_<krótki-slug>.md`, np.:

```
candidates/2026-08-24_mechanism_candidate_conditional-raw-fallback.md
```

`id` w frontmatterze: `rmc-YYYY-MM-DD-NNN` (numer porządkowy w ramach dnia), np. `rmc-2026-08-24-001`.

## Reguła: IMMUTABLE / APPEND-ONLY

**Plik utworzony przez ResearchOS nie jest później edytowany — ani przez ResearchOS, ani przez AAMR — w celu zmiany statusu eksperymentalnego.** `status: PENDING_AAMR_REVIEW` ustawiane przy tworzeniu pliku jest wartością na stałe. Zachowujemy w ten sposób nienaruszony zapis tego, co ResearchOS twierdził i jakie evidence miał *przed* eksperymentem, oddzielnie od tego, co AAMR faktycznie zmierzył.

AAMR, po przetestowaniu kandydata, tworzy **osobny** plik wyniku/review (np. `rmc-2026-08-24-001_aamr-review.md`, w lokalizacji po stronie AAMR — poza tym folderem), powiązany przez `id` kandydata. Ten outbox nigdy nie zawiera plików tworzonych przez AAMR.

## Dwie różne etykiety — nie mylić

**`researchos_label`** — ocena ResearchOS, czy warto to testować (sufit, nie walidacja):

- `INTERESTING`
- `EXTERNAL_SIGNAL`
- `STRONG_EXTERNAL_SIGNAL`
- `CANDIDATE_FOR_TEST`
- `NEEDS_PRECONDITION_CHECK`

**`external_evidence_status`** — jaki rodzaj dowodu stoi za twierdzeniem (niezależna oś):

- `PAPER_CLAIM`
- `EXTERNAL_MEASURED`
- `REPO_CLAIM`
- `CODE_VERIFIED`
- `REPO_ARTIFACT_VERIFIED`
- `INFERENCE`
- `HYPOTHESIS`

Przykład: `researchos_label: CANDIDATE_FOR_TEST` + `external_evidence_status: EXTERNAL_MEASURED` oznacza: *ResearchOS uważa mechanizm za wart testu, i istnieje zewnętrzny zmierzony wynik* — **to nadal nie znaczy, że AAMR go zwalidował.**

**Statusy zarezerwowane wyłącznie dla AAMR** (ResearchOS nigdy ich nie nadaje, nigdy nie edytuje tego pliku żeby je wpisać — trafiają do osobnego pliku review):

- `EXPLORATORY_POSITIVE`
- `FAILED`
- `PRECONDITION_UNAVAILABLE`
- `REPLICATED_VALIDATED_TRANSPLANT`

## Pola — referencja

Wspólne dla wszystkich typów: `id`, `type`, `researchos_label`, `status`, `created`, `source_run`, `source_refs`, `confidence`.

Dodatkowe w `candidates/`: `external_evidence_status`, `target_failure`, `expected_positive_regime`, `possible_negative_regime`, `preconditions`, `duplicate_of`, `estimated_test_cost_usd`.

Opcjonalne, gdy wpis odpowiada na coś z `Dokumenty dla Resherchera/` (2026-08-24): `source_request_id`, `source_gap_id`, `researchos_run_id` — patrz sekcja wyżej.

Nie wszystkie pola są obowiązkowe — wypełniaj te, które mają zastosowanie; resztę zostaw puste lub usuń.
