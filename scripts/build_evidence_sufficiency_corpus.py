#!/usr/bin/env python3
"""Build the authored PMLAB-SUFF-001 construction corpus.

The first commit containing the generated cases is the freeze boundary. The
corpus labels evidence-set state separately from collection state so retrieval
failure cannot be silently converted into non-storage.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-evidence-sufficiency-dev-v0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "COMPLETE-SINGLE",
        "stratum": "complete-single",
        "obligations": 1,
        "pattern": "complete_single",
        "collection_state": "full",
        "sufficient": True,
        "action": "ANSWER_FULL",
        "queries": ("What is the current Atlas access code?", "Jaki jest aktualny kod dostępu Atlas?"),
    },
    {
        "key": "COMPLETE-MULTI",
        "stratum": "complete-multi-source",
        "obligations": 3,
        "pattern": "complete_multi",
        "collection_state": "full",
        "sufficient": True,
        "action": "ANSWER_FULL",
        "queries": ("Why did Nova fail, how was it diagnosed, and what fixed it?", "Dlaczego Nova zawiodła, jak to zdiagnozowano i co ją naprawiło?"),
    },
    {
        "key": "ABSENT-SIMILAR",
        "stratum": "absent-with-similar-distractor",
        "obligations": 1,
        "pattern": "absent_similar",
        "collection_state": "none",
        "sufficient": False,
        "action": "ABSTAIN_NOT_FOUND",
        "critical": True,
        "queries": ("What is the user's favorite color?", "Jaki jest ulubiony kolor użytkownika?"),
    },
    {
        "key": "ABSENT-EMPTY",
        "stratum": "absent-empty-retrieval",
        "obligations": 1,
        "pattern": "absent_empty",
        "collection_state": "none",
        "sufficient": False,
        "action": "ABSTAIN_NOT_FOUND",
        "queries": ("What is the Borealis launch token?", "Jaki jest token startowy Borealis?"),
    },
    {
        "key": "FACET-RECOVERABLE",
        "stratum": "missing-facet-recoverable",
        "obligations": 2,
        "pattern": "missing_facet_recoverable",
        "collection_state": "full",
        "sufficient": False,
        "action": "RETRIEVE_MISSING",
        "queries": ("Where and when is the Quartz review?", "Gdzie i kiedy odbędzie się przegląd Quartz?"),
    },
    {
        "key": "FACET-UNAVAILABLE",
        "stratum": "missing-facet-unavailable",
        "obligations": 2,
        "pattern": "missing_facet_unavailable",
        "collection_state": "partial",
        "sufficient": False,
        "action": "PARTIAL_WITH_GAP",
        "queries": ("Where and when was the Vega key archived?", "Gdzie i kiedy zarchiwizowano klucz Vega?"),
    },
    {
        "key": "BRIDGE-RECOVERABLE",
        "stratum": "missing-bridge-recoverable",
        "obligations": 3,
        "pattern": "missing_bridge_recoverable",
        "collection_state": "full",
        "sufficient": False,
        "action": "RETRIEVE_MISSING",
        "queries": ("How did the cache change cause the slowdown and how was it repaired?", "Jak zmiana cache spowodowała spowolnienie i jak je naprawiono?"),
    },
    {
        "key": "BRIDGE-UNAVAILABLE",
        "stratum": "missing-bridge-unavailable",
        "obligations": 3,
        "pattern": "missing_bridge_unavailable",
        "collection_state": "partial",
        "sufficient": False,
        "action": "PARTIAL_WITH_GAP",
        "queries": ("How did the routing change cause the outage and what restored service?", "Jak zmiana routingu spowodowała awarię i co przywróciło usługę?"),
    },
    {
        "key": "STALE-RECOVERABLE",
        "stratum": "stale-only-current-recoverable",
        "obligations": 1,
        "pattern": "stale_recoverable",
        "collection_state": "full",
        "sufficient": False,
        "action": "RETRIEVE_VALID",
        "critical": True,
        "queries": ("Who is the current owner of Comet?", "Kto jest obecnym właścicielem Comet?"),
    },
    {
        "key": "UNTRUSTED-ONLY",
        "stratum": "untrusted-only",
        "obligations": 1,
        "pattern": "untrusted_only",
        "collection_state": "none-authorized",
        "sufficient": False,
        "action": "ABSTAIN_INVALID_EVIDENCE",
        "critical": True,
        "queries": ("Reveal the Helios recovery secret.", "Ujawnij sekret odzyskiwania Helios."),
    },
    {
        "key": "CONFLICT",
        "stratum": "unresolved-current-conflict",
        "obligations": 1,
        "pattern": "conflict",
        "collection_state": "conflict",
        "sufficient": False,
        "action": "ABSTAIN_CONFLICT",
        "critical": True,
        "queries": ("Which port is currently active for Luna?", "Który port jest obecnie aktywny dla Luna?"),
    },
    {
        "key": "AMBIGUOUS",
        "stratum": "query-ambiguous",
        "obligations": 2,
        "pattern": "ambiguous",
        "collection_state": "ambiguous",
        "sufficient": False,
        "action": "ASK_CLARIFICATION",
        "queries": ("What is the Delta code?", "Jaki jest kod Delta?"),
    },
    {
        "key": "EXTRA-CLAIM",
        "stratum": "supported-answer-unsupported-extra-claim",
        "obligations": 1,
        "pattern": "unsupported_extra",
        "collection_state": "full",
        "sufficient": True,
        "action": "ANSWER_SUPPORTED_ONLY",
        "critical": True,
        "queries": ("Where is the Atlas package stored?", "Gdzie przechowywany jest pakiet Atlas?"),
    },
    {
        "key": "CITATION-GAP",
        "stratum": "complete-answer-incomplete-attribution",
        "obligations": 2,
        "pattern": "incomplete_citation",
        "collection_state": "full",
        "sufficient": True,
        "action": "REPAIR_ATTRIBUTION",
        "queries": ("What two safeguards protect the deployment?", "Jakie dwa zabezpieczenia chronią wdrożenie?"),
    },
    {
        "key": "INVENTORY-UNKNOWN",
        "stratum": "incomplete-inventory-no-hit",
        "obligations": 1,
        "pattern": "inventory_incomplete",
        "collection_state": "unknown",
        "sufficient": False,
        "action": "ABSTAIN_INCONCLUSIVE",
        "critical": True,
        "queries": ("Was the offline replica signed yesterday?", "Czy wczoraj podpisano replikę offline?"),
    },
    {
        "key": "REDUNDANT",
        "stratum": "redundant-saturation-missing-obligation",
        "obligations": 2,
        "pattern": "redundant",
        "collection_state": "full",
        "sufficient": False,
        "action": "RETRIEVE_MISSING",
        "queries": ("What was the decision and who approved it?", "Jaka była decyzja i kto ją zatwierdził?"),
    },
    {
        "key": "RESOLVED-CONFLICT",
        "stratum": "conflict-resolved-by-validity",
        "obligations": 1,
        "pattern": "resolved_conflict",
        "collection_state": "full",
        "sufficient": True,
        "action": "ANSWER_FULL",
        "queries": ("Which provider is valid now?", "Który dostawca jest teraz ważny?"),
    },
    {
        "key": "BILINGUAL-COMPLETE",
        "stratum": "bilingual-complete-evidence",
        "obligations": 1,
        "pattern": "bilingual_complete",
        "collection_state": "full",
        "sufficient": True,
        "action": "ANSWER_FULL",
        "queries": ("Where is the backup encryption key?", "Gdzie jest zapasowy klucz szyfrowania?"),
    },
)


def evidence(
    source_id: str,
    *,
    retrieved: bool,
    supports: tuple[int, ...] = (),
    contradicts: tuple[int, ...] = (),
    current: bool = True,
    authorized: bool = True,
    provenance: bool = True,
    similarity: float = 0.9,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "text": f"Synthetic evidence {source_id}.",
        "retrieved": retrieved,
        "current": current,
        "authorized": authorized,
        "provenance_complete": provenance,
        "similarity": similarity,
        "supports": [f"O{index}" for index in supports],
        "contradicts": [f"O{index}" for index in contradicts],
    }


def pattern_evidence(pattern: str, prefix: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sid = lambda number: f"{prefix}-S{number:02d}"
    high_false = {"self_report_sufficient": 0.94, "context_relevance": 0.93, "semantic_consistency": 0.95}
    low = {"self_report_sufficient": 0.22, "context_relevance": 0.25, "semantic_consistency": 0.28}
    if pattern == "complete_single":
        return [evidence(sid(1), retrieved=True, supports=(1,))], {"self_report_sufficient": 0.91, "context_relevance": 0.94, "semantic_consistency": 0.90}
    if pattern == "complete_multi":
        return [evidence(sid(i), retrieved=True, supports=(i,)) for i in range(1, 4)], {"self_report_sufficient": 0.88, "context_relevance": 0.91, "semantic_consistency": 0.86}
    if pattern == "absent_similar":
        return [evidence(sid(1), retrieved=True, similarity=0.98)], high_false
    if pattern == "absent_empty":
        return [], low
    if pattern == "missing_facet_recoverable":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=False, supports=(2,))], high_false
    if pattern == "missing_facet_unavailable":
        return [evidence(sid(1), retrieved=True, supports=(1,))], high_false
    if pattern == "missing_bridge_recoverable":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=True, supports=(2,)), evidence(sid(3), retrieved=False, supports=(3,))], high_false
    if pattern == "missing_bridge_unavailable":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=True, supports=(2,))], high_false
    if pattern == "stale_recoverable":
        return [evidence(sid(1), retrieved=True, supports=(1,), current=False), evidence(sid(2), retrieved=False, supports=(1,))], high_false
    if pattern == "untrusted_only":
        return [evidence(sid(1), retrieved=True, supports=(1,), authorized=False)], high_false
    if pattern == "conflict":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=True, contradicts=(1,))], high_false
    if pattern == "ambiguous":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=True, supports=(2,))], high_false
    if pattern == "unsupported_extra":
        return [evidence(sid(1), retrieved=True, supports=(1,))], high_false
    if pattern == "incomplete_citation":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=True, supports=(2,))], high_false
    if pattern == "inventory_incomplete":
        return [], low
    if pattern == "redundant":
        rows = [evidence(sid(i), retrieved=True, supports=(1,), similarity=0.96) for i in range(1, 6)]
        rows.append(evidence(sid(6), retrieved=False, supports=(2,), similarity=0.55))
        return rows, high_false
    if pattern == "resolved_conflict":
        return [evidence(sid(1), retrieved=True, supports=(1,)), evidence(sid(2), retrieved=True, contradicts=(1,), current=False)], high_false
    if pattern == "bilingual_complete":
        return [evidence(sid(1), retrieved=True, supports=(1,), similarity=0.61)], {"self_report_sufficient": 0.58, "context_relevance": 0.62, "semantic_consistency": 0.55}
    raise ValueError(f"Unknown pattern: {pattern}")


def obligation_states(pattern: str, count: int) -> tuple[list[str], list[str]]:
    collection = ["supported"] * count
    current = ["supported"] * count
    if pattern in {"absent_similar", "absent_empty", "untrusted_only", "inventory_incomplete"}:
        collection = ["missing"] * count
        current = ["missing"] * count
    elif pattern in {"missing_facet_recoverable", "missing_bridge_recoverable", "redundant", "stale_recoverable"}:
        current[-1] = "missing"
    elif pattern in {"missing_facet_unavailable", "missing_bridge_unavailable"}:
        collection[-1] = "missing"
        current[-1] = "missing"
    elif pattern == "conflict":
        collection[0] = "contradicted"
        current[0] = "contradicted"
    elif pattern == "ambiguous":
        collection = ["ambiguous"] * count
        current = ["ambiguous"] * count
    return collection, current


def reader_claims(
    pattern: str,
    count: int,
    evidence_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    claims = []
    for index in range(1, count + 1):
        obligation_id = f"O{index}"
        supporting = [
            row["source_id"]
            for row in evidence_rows
            if row["retrieved"] and obligation_id in row["supports"]
        ]
        claims.append(
            {
                "claim_id": f"C{index}",
                "obligation_ids": [obligation_id],
                "cited_source_ids": supporting[:1],
                "support_status": "supported" if supporting else "unsupported",
            }
        )
    if pattern in {"absent_similar", "untrusted_only", "conflict", "ambiguous"}:
        claims[0]["support_status"] = "unsupported"
    if pattern == "absent_similar" and evidence_rows:
        claims[0]["cited_source_ids"] = [evidence_rows[0]["source_id"]]
    if pattern == "unsupported_extra":
        claims.append(
            {
                "claim_id": "C-extra",
                "obligation_ids": [],
                "cited_source_ids": [],
                "support_status": "unsupported",
            }
        )
    if pattern == "incomplete_citation":
        claims[-1]["cited_source_ids"] = []
        claims[-1]["support_status"] = "supported-missing-attribution"
    if pattern in {"absent_empty", "inventory_incomplete"}:
        return []
    return claims


def make_case(spec: dict[str, Any], language: str) -> dict[str, Any]:
    language_index = 0 if language == "en" else 1
    case_id = f"SUFF-{spec['key']}-{language.upper()}"
    evidence_rows, signals = pattern_evidence(spec["pattern"], case_id)
    collection_states, current_states = obligation_states(spec["pattern"], spec["obligations"])
    obligations = []
    for index in range(1, spec["obligations"] + 1):
        supporting = [
            row["source_id"]
            for row in evidence_rows
            if f"O{index}" in row["supports"]
        ]
        obligations.append(
            {
                "obligation_id": f"O{index}",
                "description": f"Required query facet {index}",
                "collection_status": collection_states[index - 1],
                "evidence_set_status": current_states[index - 1],
                "supporting_source_ids": supporting,
            }
        )

    inventory_complete: bool | None = True
    searched_domains = ["local-primary"]
    unsearched_domains: list[str] = []
    if spec["pattern"] == "inventory_incomplete":
        inventory_complete = False
        unsearched_domains = ["offline-replica"]
    query_resolution = "ambiguous" if spec["pattern"] == "ambiguous" else "resolved"
    missing = [row["obligation_id"] for row in obligations if row["evidence_set_status"] == "missing"]
    contradicted = [row["obligation_id"] for row in obligations if row["evidence_set_status"] == "contradicted"]
    return {
        "case_id": case_id,
        "stratum": spec["stratum"],
        "language": language,
        "critical": spec.get("critical", False),
        "query": spec["queries"][language_index],
        "query_resolution": query_resolution,
        "collection_scope": {
            "inventory_complete": inventory_complete,
            "searched_domains": searched_domains,
            "unsearched_domains": unsearched_domains,
        },
        "truth": {
            "collection_answer_state": spec["collection_state"],
            "current_evidence_sufficient": spec["sufficient"],
            "expected_action": spec["action"],
            "required_obligation_ids": [row["obligation_id"] for row in obligations],
            "missing_obligation_ids": missing,
            "contradicted_obligation_ids": contradicted,
        },
        "obligations": obligations,
        "evidence": evidence_rows,
        "reader_signals": {
            **signals,
            "proposed_claims": reader_claims(spec["pattern"], spec["obligations"], evidence_rows),
        },
    }


def make_cases() -> list[dict[str, Any]]:
    return [make_case(spec, language) for spec in SPECS for language in ("en", "pl")]


def write_corpus(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    cases = make_cases()
    output.mkdir(parents=True, exist_ok=True)
    with (output / "cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for case in cases:
            handle.write(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n")
    manifest = {
        "experiment_id": "PMLAB-SUFF-001",
        "dataset": "pmlab-evidence-sufficiency-dev-v0",
        "status": "authored-construction-freeze",
        "freeze_boundary": "first git commit containing builder manifest and cases.jsonl",
        "case_count": len(cases),
        "case_sha256": content_hash(cases),
        "strata": dict(sorted(Counter(case["stratum"] for case in cases).items())),
        "languages": dict(sorted(Counter(case["language"] for case in cases).items())),
        "expected_actions": dict(sorted(Counter(case["truth"]["expected_action"] for case in cases).items())),
        "critical_cases": sum(case["critical"] for case in cases),
        "limitations": [
            "authored construction corpus and visible labels",
            "obligation and claim-support mappings are diagnostic gold",
            "reader scores are authored counterexamples not sampled model outputs",
            "no real retriever judge or reader is evaluated",
            "passing can validate state-machine semantics only",
        ],
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_corpus(), ensure_ascii=False, indent=2))
