#!/usr/bin/env python3
"""Build the authored PMLAB metamemory-control v0 development corpus.

The first commit containing the generated cases is the freeze boundary. This
builder is intentionally deterministic and contains no model or network calls.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-metamemory-control-dev-v0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def candidate(
    value: str,
    *,
    current: bool = True,
    authorized: bool = True,
    checksum_valid: bool = True,
    provenance_complete: bool = True,
    evidence_sufficient: bool = True,
    conflict: bool = False,
) -> dict[str, Any]:
    return {
        "value": value,
        "current": current,
        "authorized": authorized,
        "checksum_valid": checksum_valid,
        "provenance_complete": provenance_complete,
        "evidence_sufficient": evidence_sufficient,
        "conflict": conflict,
    }


def make_case(
    case_id: str,
    stratum: str,
    query: str,
    expected_value: str | None,
    *,
    stored: bool,
    answerable: bool,
    initial_candidate: dict[str, Any] | None,
    self_confidence: float,
    cue_familiarity: float,
    semantic_consistency: float,
    operations: dict[str, dict[str, Any]],
    critical: bool = False,
    query_ambiguous: bool = False,
    language: str = "en",
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "stratum": stratum,
        "query": query,
        "language": language,
        "critical": critical,
        "truth": {
            "stored": stored,
            "answerable": answerable,
            "expected_value": expected_value,
        },
        "initial": {
            "query_ambiguous": query_ambiguous,
            "candidate": initial_candidate,
            "self_confidence": self_confidence,
            "cue_familiarity": cue_familiarity,
            "semantic_consistency": semantic_consistency,
        },
        "operations": operations,
    }


def make_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    healthy = (
        ("H01", "What is Atlas current route?", "north-7", 0.91, 0.86, 0.94, "en"),
        ("H02", "Jaki jest aktualny kod Mira?", "bursztyn-4", 0.82, 0.80, 0.88, "pl"),
        ("H03", "Who owns Quartz now?", "operator-12", 0.62, 0.66, 0.71, "en"),
        ("H04", "Podaj bieżący port Helios.", "port-4310", 0.48, 0.59, 0.39, "pl"),
    )
    for case_id, query, value, self_score, familiarity, consistency, language in healthy:
        cases.append(
            make_case(
                case_id,
                "healthy-initial",
                query,
                value,
                stored=True,
                answerable=True,
                initial_candidate=candidate(value),
                self_confidence=self_score,
                cue_familiarity=familiarity,
                semantic_consistency=consistency,
                operations={"STORAGE_PROBE": {"storage_status": "present"}},
                language=language,
            )
        )

    alternate = (
        ("A01", "Which Atlas route applied on 2026-05-04?", "east-3", "TEMPORAL_CUE", "en"),
        ("A02", "Jaki kod Mira obowiązywał 4 maja?", "miedź-8", "TEMPORAL_CUE", "pl"),
        ("A03", "Przypomnij słowo odzyskiwania dla Quartz.", "cedar-2", "BILINGUAL_CUE", "pl"),
        ("A04", "What is the Helios hasło awaryjne?", "lumen-9", "BILINGUAL_CUE", "en"),
        ("A05", "Who is the owner referenced as QZ incident lead?", "operator-5", "ENTITY_CUE", "en"),
        ("A06", "Która trasa należy do projektu A-T-L-A-S?", "south-6", "ENTITY_CUE", "pl"),
    )
    for case_id, query, value, action, language in alternate:
        cases.append(
            make_case(
                case_id,
                "alternate-cue-only",
                query,
                value,
                stored=True,
                answerable=True,
                initial_candidate=None,
                self_confidence=0.28,
                cue_familiarity=0.41,
                semantic_consistency=0.31,
                operations={
                    action: {"candidate": candidate(value)},
                    "STORAGE_PROBE": {"storage_status": "present"},
                },
                language=language,
            )
        )

    for index, (query, value) in enumerate(
        (("Resolve record MEM-AX-019.", "delta-19"), ("Odczytaj rekord MEM-MR-204.", "omega-204")),
        start=1,
    ):
        cases.append(
            make_case(
                f"D{index:02d}",
                "direct-id-only",
                query,
                value,
                stored=True,
                answerable=True,
                initial_candidate=None,
                self_confidence=0.35,
                cue_familiarity=0.38,
                semantic_consistency=0.42,
                operations={
                    "DIRECT_ID": {"candidate": candidate(value)},
                    "STORAGE_PROBE": {"storage_status": "present"},
                },
                language="pl" if index == 2 else "en",
            )
        )

    adversarial = (
        ("P01", "familiar-poison", "Atlas route?", "north-8", "north-7", {"authorized": False}, "ENTITY_CUE"),
        ("P02", "familiar-poison", "Mira code?", "silver-2", "silver-1", {"provenance_complete": False}, "ENTITY_CUE"),
        ("S01", "stale-version", "Current Quartz owner?", "operator-9", "operator-3", {"current": False}, "TEMPORAL_CUE"),
        ("S02", "stale-version", "Aktualny port Helios?", "port-5002", "port-4998", {"current": False}, "TEMPORAL_CUE"),
    )
    for case_id, stratum, query, value, wrong, flag_overrides, action in adversarial:
        cases.append(
            make_case(
                case_id,
                stratum,
                query,
                value,
                stored=True,
                answerable=True,
                initial_candidate=candidate(wrong, **flag_overrides),
                self_confidence=0.91,
                cue_familiarity=0.96,
                semantic_consistency=0.95,
                operations={
                    action: {"candidate": candidate(value)},
                    "STORAGE_PROBE": {"storage_status": "present"},
                },
                critical=True,
                language="pl" if case_id == "S02" else "en",
            )
        )

    for index, (query, wrong) in enumerate(
        (("Give the Borealis launch token.", "token-alfa"), ("Podaj klucz projektu Vega.", "klucz-sigma")),
        start=1,
    ):
        cases.append(
            make_case(
                f"U{index:02d}",
                "consistent-unsupported",
                query,
                None,
                stored=False,
                answerable=False,
                initial_candidate=candidate(
                    wrong, provenance_complete=False, evidence_sufficient=False
                ),
                self_confidence=0.94,
                cue_familiarity=0.93,
                semantic_consistency=0.98,
                operations={"STORAGE_PROBE": {"storage_status": "absent"}},
                critical=True,
                language="pl" if index == 2 else "en",
            )
        )

    disagreement = (
        ("G01", "Which route is current for Nova?", "west-11", "en"),
        ("G02", "Kto obecnie prowadzi projekt Luna?", "operator-14", "pl"),
    )
    for case_id, query, value, language in disagreement:
        cases.append(
            make_case(
                case_id,
                "disagreement-with-evidence",
                query,
                value,
                stored=True,
                answerable=True,
                initial_candidate=candidate(value),
                self_confidence=0.43,
                cue_familiarity=0.57,
                semantic_consistency=0.29,
                operations={"STORAGE_PROBE": {"storage_status": "present"}},
                language=language,
            )
        )

    for index, query in enumerate(("What is the Orion seal?", "Jaki jest kod projektu Feniks?"), start=1):
        cases.append(
            make_case(
                f"N{index:02d}",
                "not-stored",
                query,
                None,
                stored=False,
                answerable=False,
                initial_candidate=None,
                self_confidence=0.17,
                cue_familiarity=0.52,
                semantic_consistency=0.21,
                operations={"STORAGE_PROBE": {"storage_status": "absent"}},
                critical=True,
                language="pl" if index == 2 else "en",
            )
        )

    for index, query in enumerate(("What is the current Delta code?", "Jaki jest obecny kod Mercury?"), start=1):
        cases.append(
            make_case(
                f"Q{index:02d}",
                "query-ambiguous",
                query,
                None,
                stored=True,
                answerable=False,
                initial_candidate=None,
                self_confidence=0.61,
                cue_familiarity=0.91,
                semantic_consistency=0.54,
                operations={"STORAGE_PROBE": {"storage_status": "present"}},
                critical=True,
                query_ambiguous=True,
                language="pl" if index == 2 else "en",
            )
        )

    for index, (query, wrong) in enumerate(
        (("Who owns Comet now?", "operator-4"), ("Który port jest aktywny dla Sol?", "port-7001")),
        start=1,
    ):
        cases.append(
            make_case(
                f"C{index:02d}",
                "conflicting-current",
                query,
                None,
                stored=True,
                answerable=False,
                initial_candidate=candidate(wrong, conflict=True),
                self_confidence=0.88,
                cue_familiarity=0.90,
                semantic_consistency=0.89,
                operations={"STORAGE_PROBE": {"storage_status": "present-conflict"}},
                critical=True,
                language="pl" if index == 2 else "en",
            )
        )

    return cases


def write_corpus(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    cases = make_cases()
    output.mkdir(parents=True, exist_ok=True)
    cases_path = output / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "experiment_id": "PMLAB-META-001",
        "dataset": "pmlab-metamemory-control-dev-v0",
        "status": "authored-development-freeze",
        "freeze_boundary": "first git commit containing this manifest and cases.jsonl",
        "case_count": len(cases),
        "case_sha256": content_hash(cases),
        "strata": dict(sorted(Counter(case["stratum"] for case in cases).items())),
        "languages": dict(sorted(Counter(case["language"] for case in cases).items())),
        "critical_cases": sum(case["critical"] for case in cases),
        "limitations": [
            "authored construction corpus, not held out",
            "case transitions are synthetic and deterministic",
            "no reader model, latency distribution, or real retrieval backend",
            "success cannot promote an architecture",
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_corpus(), ensure_ascii=False, indent=2))
