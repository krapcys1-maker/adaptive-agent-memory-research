# Dokumenty dla Resherchera — AAMR → ResearchOS outbox

**Kierunek: jednostronny, AAMR → ResearchOS.** To jest odwrotność `Dokumenty z Resherchera/` (ResearchOS → AAMR, jednostronny, istniejący wcześniej). AAMR czyta i zapisuje wyłącznie w tym folderze po swojej stronie protokołu — nie modyfikuje `Dokumenty z Resherchera/`.

## Po co ten folder istnieje

ResearchOS wcześniej zgadywał możliwości eksperymentalne AAMR — patrz `candidates/2026-08-24_mechanism_candidate_semantic-entropy-escalation-gate.md`, którego `duplicate_of` i `suggested_next_step` opierają się na stanie AAMR sprzed walidacji `RAW_PROVENANCE` (obecnie `REPLICATED_VALIDATED_TRANSPLANT`, Ledger Entry H) — założenie, które w chwili tworzenia tego kandydata było poprawne, ale już nie jest. Ten folder ma to systemowo wyeliminować: AAMR mówi wprost, co jest testowalne teraz, co nie, jakie są otwarte luki, czego nie warto odkrywać ponownie, i jakie pytania ResearchOS powinien zbadać — zamiast ResearchOS wnioskować to pośrednio z raportów.

## Role

- **ResearchOS** — external research: papers, GitHub, code archaeology, negative evidence, mechanism candidates, questions. Nie prowadzi eksperymentów, nie ma dostępu do hosta AAMR.
- **AAMR** — experiment design, precondition checks, controlled tests, replication, causal results. Jedyny podmiot uprawniony do nadawania statusów `AAMR_MEASURED` / `AAMR_VALIDATED` / `AAMR_REPLICATED`-klasy (dokładne nazwy statusów: patrz `MECHANISM_REGIME_EVIDENCE_LEDGER.md`, np. `REPLICATED_VALIDATED_TRANSPLANT`, `DROP`, `CALIBRATION_FAILED`). ResearchOS nigdy nie nadaje tych statusów — może tylko cytować je jako fakt, z odniesieniem do źródła.

## Struktura

```
Dokumenty dla Resherchera/
  README.md
  TESTABILITY_ENVELOPE.md      — co AAMR może/nie może teraz przetestować, i dlaczego
  OPEN_TESTABLE_GAPS.md        — otwarte, warte zbadania luki, z zależnościami
  DO_NOT_REDISCOVER.md         — mechanizmy już przetestowane; czego nie warto proponować ponownie
  RESEARCH_REQUESTS/
    _TEMPLATE_research_request.md
    <konkretne requesty>
```

## Źródło prawdy

Ten folder jest **snapshotem**, nie źródłem prawdy. Źródłem prawdy pozostają:

- `docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md` — jedyne miejsce, gdzie mechanizm dostaje status eksperymentalny.
- `memory/events.jsonl` (poprzez `project_memory` CLI/MCP) — preregistracje, findings, decyzje.
- Poszczególne raporty mechanizmów (`docs/research/<MECHANIZM>_V*.md`).

Jeśli coś w tym folderze jest sprzeczne z ledgerem — ledger wygrywa. Ten folder powinien być regenerowany/aktualizowany po każdym zamkniętym mechanizmie, nie utrzymywany ręcznie na bieżąco jako niezależny byt.

## Uwaga o równoległych dokumentach

W `docs/research/` istnieją też dokumenty z **równoległej, niezależnej sesji** tego samego repozytorium (`RELATED_WORK_AND_POSITIONING_2026-08-24.md`, `CROSS_PAPER_HYPOTHESIS_MAP_2026-08-24.md`, `GLOBAL_AGENT_MEMORY_FRONTIER_MAP_2026-08-24.md`, `MECHANISM_DEPENDENCY_SYNTHESIS_2026-08-24.md`, `RELATED_WORK_RED_TEAM_2026-08-24.md`, `RESEARCH_ROADMAP_EVIDENCE_DRIVEN_V1.md`) — mają własną numerację eksperymentów (E1/E2/E3, C1-C8), własny ledger wewnętrzny i opisują stan sprzed lub równoległy do wielu wyników w `MECHANISM_REGIME_EVIDENCE_LEDGER.md` (np. wciąż traktują status `RAW_PROVENANCE_EXPANSION` jako `DROP`/nierozstrzygnięty, podczas gdy w aktualnym ledgerze jest to `REPLICATED_VALIDATED_TRANSPLANT`, Entry H). Ten outbox **nie** czerpie z tamtych dokumentów jako źródła prawdy — wyłącznie z `MECHANISM_REGIME_EVIDENCE_LEDGER.md` i `memory/events.jsonl`.

## Machine-readable

`researchos_contract_v1.json` w tym samym folderze — deterministyczny snapshot generowany przez `scripts/build_researchos_contract.py`. Nie interpretuje wyników, nie zmienia statusów — tylko czyta i waliduje jawnie utrzymywane źródła. Zobacz komentarz na górze generatora.
