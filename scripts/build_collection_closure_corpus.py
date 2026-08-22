#!/usr/bin/env python3
"""Build the authored PMLAB-CLOSURE-001 construction corpus.

This builder creates data and gold labels only. No policy or scoring arm is
implemented here. The first commit containing its generated artifacts is the
freeze boundary for the later runner.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-collection-closure-dev-v0"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": "positive-incomplete",
        "stratum": "positive-certain-answer-in-incomplete-collection",
        "predicate": "release_channel",
        "entity": "Aster",
        "queries": ("Which release channel is recorded for Aster?", "Jaki kanał wydania zapisano dla Aster?"),
        "pattern": "positive",
        "tier": "NONE",
        "action": "ANSWER_SUPPORTED",
    },
    {
        "key": "not-attempted",
        "stratum": "retrieval-not-attempted",
        "predicate": "recovery_contact",
        "entity": "Birch",
        "queries": ("Is a recovery contact stored for Birch?", "Czy zapisano kontakt odzyskiwania dla Birch?"),
        "pattern": "not_attempted",
        "tier": "N0_NOT_RETRIEVED",
        "action": "RETRIEVE",
    },
    {
        "key": "searched-partial",
        "stratum": "searched-scope-with-unsearched-domain",
        "predicate": "approval",
        "entity": "Cedar",
        "queries": ("Was Cedar approved?", "Czy Cedar został zatwierdzony?"),
        "pattern": "partial_scope",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "PROBE_SCOPE",
        "critical": True,
    },
    {
        "key": "query-complete-slice",
        "stratum": "globally-incomplete-query-complete-entity-slice",
        "predicate": "owner",
        "entity": "Dune",
        "queries": ("Is there a current owner record for Dune?", "Czy istnieje aktualny wpis właściciela Dune?"),
        "pattern": "exact_complete",
        "tier": "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
        "action": "REPORT_BOUNDED_ABSENCE",
        "critical": True,
    },
    {
        "key": "time-gap",
        "stratum": "predicate-entity-complete-time-interval-incomplete",
        "predicate": "incident",
        "entity": "Elm",
        "queries": ("Was an Elm incident recorded during August 2026?", "Czy w sierpniu 2026 zapisano incydent Elm?"),
        "pattern": "time_gap",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "ABSTAIN_INCONCLUSIVE",
        "critical": True,
    },
    {
        "key": "expired",
        "stratum": "expired-exact-certificate",
        "predicate": "exception",
        "entity": "Fjord",
        "queries": ("Does Fjord have a current exception?", "Czy Fjord ma aktualny wyjątek?"),
        "pattern": "expired",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "PROBE_SCOPE",
        "critical": True,
    },
    {
        "key": "mutated",
        "stratum": "scope-mutated-after-certificate",
        "predicate": "decision",
        "entity": "Grove",
        "queries": ("Is there a current decision for Grove?", "Czy istnieje aktualna decyzja dla Grove?"),
        "pattern": "mutated",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "PROBE_SCOPE",
        "critical": True,
    },
    {
        "key": "replica-unavailable",
        "stratum": "required-replica-unavailable",
        "predicate": "signature",
        "entity": "Harbor",
        "queries": ("Is Harbor signed in durable memory?", "Czy Harbor jest podpisany w pamięci trwałej?"),
        "pattern": "replica_unavailable",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "PROBE_SCOPE",
        "critical": True,
    },
    {
        "key": "unauthorized",
        "stratum": "unsearched-unauthorized-partition",
        "predicate": "medical_note",
        "entity": "Iris",
        "queries": ("Is there a medical note for Iris?", "Czy istnieje notatka medyczna dla Iris?"),
        "pattern": "unauthorized",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "ABSTAIN_INCONCLUSIVE",
        "critical": True,
    },
    {
        "key": "index-only",
        "stratum": "indexes-complete-canonical-inventory-unknown",
        "predicate": "rollback_plan",
        "entity": "Juniper",
        "queries": ("Is a rollback plan stored for Juniper?", "Czy zapisano plan wycofania dla Juniper?"),
        "pattern": "index_only",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "PROBE_SCOPE",
        "critical": True,
    },
    {
        "key": "insert-changes",
        "stratum": "admissible-insertion-changes-negative-answer",
        "predicate": "reviewer",
        "entity": "Kite",
        "queries": ("Does Kite have a reviewer?", "Czy Kite ma recenzenta?"),
        "pattern": "insert_changes",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "ABSTAIN_INCONCLUSIVE",
        "critical": True,
    },
    {
        "key": "insert-independent",
        "stratum": "admissible-insertions-independent-of-query",
        "predicate": "owner",
        "entity": "Larch",
        "queries": ("Is there a current owner record for Larch?", "Czy istnieje aktualny wpis właściciela Larch?"),
        "pattern": "insert_independent",
        "tier": "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
        "action": "REPORT_BOUNDED_ABSENCE",
    },
    {
        "key": "explicit-negative",
        "stratum": "explicit-negative-fact-in-complete-scope",
        "predicate": "auto_deploy_enabled",
        "entity": "Moss",
        "queries": ("Is automatic deployment enabled for Moss?", "Czy automatyczne wdrażanie jest włączone dla Moss?"),
        "pattern": "explicit_negative",
        "tier": "N3_PROPOSITION_FALSE",
        "action": "ANSWER_EXPLICIT_NEGATIVE",
        "critical": True,
    },
    {
        "key": "absent-positive",
        "stratum": "absent-positive-without-explicit-negation",
        "predicate": "auto_deploy_enabled",
        "entity": "Nacre",
        "queries": ("Is automatic deployment enabled for Nacre?", "Czy automatyczne wdrażanie jest włączone dla Nacre?"),
        "pattern": "exact_complete",
        "tier": "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
        "action": "REPORT_BOUNDED_ABSENCE",
        "critical": True,
    },
    {
        "key": "predicate-mismatch",
        "stratum": "authoritative-source-wrong-predicate",
        "predicate": "encryption_key",
        "entity": "Onyx",
        "queries": ("Is an encryption key registered for Onyx?", "Czy dla Onyx zarejestrowano klucz szyfrowania?"),
        "pattern": "predicate_mismatch",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "ABSTAIN_INCONCLUSIVE",
        "critical": True,
    },
    {
        "key": "enumeration-match",
        "stratum": "bounded-enumeration-count-and-probes-match",
        "predicate": "open_task",
        "entity": "Pine",
        "queries": ("Are there any open tasks for Pine?", "Czy Pine ma otwarte zadania?"),
        "pattern": "enumeration_match",
        "tier": "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
        "action": "REPORT_BOUNDED_ABSENCE",
    },
    {
        "key": "enumeration-mismatch",
        "stratum": "bounded-enumeration-member-count-mismatch",
        "predicate": "open_task",
        "entity": "Quartz",
        "queries": ("Are there any open tasks for Quartz?", "Czy Quartz ma otwarte zadania?"),
        "pattern": "enumeration_mismatch",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "PROBE_SCOPE",
        "critical": True,
    },
    {
        "key": "conflict",
        "stratum": "complete-scope-with-current-conflict",
        "predicate": "provider",
        "entity": "Reed",
        "queries": ("Who is the current provider for Reed?", "Kto jest aktualnym dostawcą Reed?"),
        "pattern": "conflict",
        "tier": "NONE",
        "action": "ABSTAIN_CONFLICT",
        "critical": True,
    },
    {
        "key": "superseded-positive",
        "stratum": "complete-scope-with-superseded-and-current-record",
        "predicate": "provider",
        "entity": "Spruce",
        "queries": ("Who is the current provider for Spruce?", "Kto jest aktualnym dostawcą Spruce?"),
        "pattern": "superseded_positive",
        "tier": "NONE",
        "action": "ANSWER_SUPPORTED",
    },
    {
        "key": "no-authorized-current",
        "stratum": "only-stale-or-unauthorized-records-in-complete-scope",
        "predicate": "approver",
        "entity": "Thorn",
        "queries": ("Is there an authorized current approver for Thorn?", "Czy istnieje uprawniony aktualny zatwierdzający dla Thorn?"),
        "pattern": "no_authorized_current",
        "tier": "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
        "action": "REPORT_BOUNDED_ABSENCE",
        "critical": True,
    },
    {
        "key": "mixed-facets",
        "stratum": "multi-facet-with-different-closure-scopes",
        "predicate": "review",
        "entity": "Umber",
        "queries": ("Was Umber reviewed, and who approved it?", "Czy Umber został sprawdzony i kto go zatwierdził?"),
        "pattern": "mixed_facets",
        "tier": "MIXED",
        "action": "PARTIAL_WITH_SCOPED_GAP",
        "critical": True,
    },
    {
        "key": "ambiguous",
        "stratum": "ambiguous-entity-before-scope-mapping",
        "predicate": "code",
        "entity": "Vale",
        "queries": ("What is the Vale code?", "Jaki jest kod Vale?"),
        "pattern": "ambiguous",
        "tier": "NONE",
        "action": "ASK_CLARIFICATION",
    },
    {
        "key": "bilingual-map",
        "stratum": "bilingual-query-maps-to-exact-certificate",
        "predicate": "backup_location",
        "entity": "Willow",
        "queries": ("Is a backup location recorded for Willow?", "Czy zapisano lokalizację kopii zapasowej Willow?"),
        "pattern": "exact_complete",
        "tier": "N2_NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE",
        "action": "REPORT_BOUNDED_ABSENCE",
    },
    {
        "key": "wrong-map",
        "stratum": "query-mapped-to-wrong-certificate-scope",
        "predicate": "retention_rule",
        "entity": "Yarrow",
        "queries": ("Is a retention rule recorded for Yarrow?", "Czy zapisano regułę retencji dla Yarrow?"),
        "pattern": "wrong_map",
        "tier": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        "action": "REMAP_SCOPE",
        "critical": True,
    },
)


def opaque_id(key: str, language: str) -> str:
    digest = hashlib.sha256(f"{key}:{language}:closure-v0".encode()).hexdigest()[:10]
    return f"CLOS-{digest.upper()}"


def make_artifacts(spec: dict[str, Any], language: str) -> dict[str, Any]:
    case_id = opaque_id(spec["key"], language)
    predicate = spec["predicate"]
    entity = spec["entity"]
    exact_scope = {
        "predicates": [predicate],
        "entity_constraints": [entity],
        "valid_time": {"from": "2026-08-01", "to": "2026-08-22"},
        "namespaces": ["canonical-events"],
    }
    mapped_scope = dict(exact_scope)
    pattern = spec["pattern"]
    inventory_sequence = 41
    certificate_sequence = 41
    status = "complete"
    expires_at = "2026-08-23T00:00:00Z"
    registered = ["primary-disk", "offline-replica"]
    available = list(registered)
    expected_count = observed_count = 2
    retrieval_attempted = True
    retrieved: list[str] = []
    records: list[dict[str, Any]] = []
    exceptions = {"unavailable": [], "unauthorized": [], "unsearched": []}
    basis = "reconciled-replicas"
    insertion_changes = False
    certificate_predicate = predicate

    if pattern == "positive":
        records = [{"record_id": f"{case_id}-R1", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "stable", "current": True, "authorized": True}]
        retrieved = [records[0]["record_id"]]
        available = ["primary-disk"]
        exceptions["unsearched"] = ["offline-replica"]
        status = "partial"
    elif pattern == "not_attempted":
        retrieval_attempted = False
        available = []
        exceptions["unsearched"] = list(registered)
        status = "unknown"
    elif pattern == "partial_scope":
        available = ["primary-disk"]
        exceptions["unsearched"] = ["offline-replica"]
        status = "partial"
    elif pattern == "time_gap":
        status = "partial"
        exact_scope["valid_time"] = {"from": "2026-08-01", "to": "2026-08-31"}
        mapped_scope = dict(exact_scope)
    elif pattern == "expired":
        status = "expired"
        expires_at = "2026-08-21T00:00:00Z"
    elif pattern == "mutated":
        inventory_sequence = 42
    elif pattern == "replica_unavailable":
        available = ["primary-disk"]
        exceptions["unavailable"] = ["offline-replica"]
        status = "partial"
    elif pattern == "unauthorized":
        available = ["primary-disk"]
        exceptions["unauthorized"] = ["private-medical"]
        registered.append("private-medical")
        status = "partial"
    elif pattern == "index_only":
        registered = ["fts5-index", "rg-view", "canonical-events"]
        available = ["fts5-index", "rg-view"]
        exceptions["unsearched"] = ["canonical-events"]
        status = "partial"
        basis = "index-agreement"
    elif pattern == "insert_changes":
        insertion_changes = True
        status = "partial"
    elif pattern == "insert_independent":
        insertion_changes = False
    elif pattern == "explicit_negative":
        records = [{"record_id": f"{case_id}-R1", "predicate": predicate, "entity": entity, "polarity": "negative", "value": False, "current": True, "authorized": True}]
        retrieved = [records[0]["record_id"]]
    elif pattern == "predicate_mismatch":
        certificate_predicate = "checksum"
        status = "complete"
        basis = "authoritative-source"
    elif pattern == "enumeration_match":
        basis = "exhaustive-enumeration"
        expected_count = observed_count = 3
        registered = ["member-a", "member-b", "member-c"]
        available = list(registered)
    elif pattern == "enumeration_mismatch":
        basis = "exhaustive-enumeration"
        expected_count, observed_count = 4, 3
        registered = ["member-a", "member-b", "member-c", "member-d"]
        available = registered[:3]
        exceptions["unavailable"] = ["member-d"]
        status = "partial"
    elif pattern == "conflict":
        records = [
            {"record_id": f"{case_id}-R1", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "North", "current": True, "authorized": True},
            {"record_id": f"{case_id}-R2", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "South", "current": True, "authorized": True},
        ]
        retrieved = [row["record_id"] for row in records]
    elif pattern == "superseded_positive":
        records = [
            {"record_id": f"{case_id}-R1", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "OldCo", "current": False, "authorized": True},
            {"record_id": f"{case_id}-R2", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "NewCo", "current": True, "authorized": True},
        ]
        retrieved = [row["record_id"] for row in records]
    elif pattern == "no_authorized_current":
        records = [
            {"record_id": f"{case_id}-R1", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "Past", "current": False, "authorized": True},
            {"record_id": f"{case_id}-R2", "predicate": predicate, "entity": entity, "polarity": "positive", "value": "Hidden", "current": True, "authorized": False},
        ]
        retrieved = [row["record_id"] for row in records]
    elif pattern == "mixed_facets":
        status = "partial"
        records = [{"record_id": f"{case_id}-R1", "predicate": "review_status", "entity": entity, "polarity": "positive", "value": "reviewed", "current": True, "authorized": True}]
        retrieved = [records[0]["record_id"]]
    elif pattern == "ambiguous":
        status = "unknown"
        mapped_scope["entity_constraints"] = ["Vale-A", "Vale-B"]
    elif pattern == "wrong_map":
        mapped_scope["entity_constraints"] = ["Yarrow-archive"]

    certificate_scope = {
        "predicates": [certificate_predicate],
        "entity_constraints": [entity],
        "valid_time": {"from": "2026-08-01", "to": "2026-08-22"},
        "namespaces": ["canonical-events"],
    }
    if pattern == "time_gap":
        certificate_scope["valid_time"] = {"from": "2026-08-01", "to": "2026-08-15"}

    inventory = {
        "inventory_id": f"{case_id}-INV",
        "mutation_sequence": inventory_sequence,
        "registered_domains": registered,
        "available_domains": available,
        "expected_member_count": expected_count,
        "observed_member_count": observed_count,
        "records": records,
    }
    probes = {
        "probe_set_id": f"{case_id}-PRB",
        "inventory_id": inventory["inventory_id"],
        "results": [
            {
                "probe_id": f"{case_id}-P{index + 1}",
                "domain": domain,
                "status": "success" if domain in available else ("unauthorized" if domain in exceptions["unauthorized"] else "unavailable"),
                "failure_domain": domain,
            }
            for index, domain in enumerate(registered)
        ],
    }
    certificate = {
        "certificate_id": f"{case_id}-CRT",
        "query_shape": certificate_scope,
        "collection_scope": {
            "authorization_boundary": "user-owned-project-memory",
            "registered_domains": registered,
        },
        "completeness_basis": {"method": basis, "inventory_version": inventory["inventory_id"], "probe_set_id": probes["probe_set_id"]},
        "exceptions": exceptions,
        "freshness": {
            "issued_at": "2026-08-22T10:00:00Z",
            "expires_at": expires_at,
            "certified_mutation_sequence": certificate_sequence,
        },
        "status": status,
    }
    insertions = {
        "insertion_set_id": f"{case_id}-UPD",
        "allowed_insertions": [
            {
                "update_id": f"{case_id}-U1",
                "predicate": predicate if insertion_changes else "unrelated_note",
                "entity": entity if insertion_changes else f"other-{entity}",
                "admissible": True,
                "changes_query_answer": insertion_changes,
            }
        ],
    }

    obligations = {"O1": spec["tier"]}
    if pattern == "mixed_facets":
        obligations = {
            "review_status": "NONE",
            "approver": "N1_NOT_FOUND_IN_SEARCHED_SCOPE",
        }

    case = {
        "case_id": case_id,
        "pair_group": spec["key"],
        "language": language,
        "query": spec["queries"][0 if language == "en" else 1],
        "observed": {
            "retrieval_attempted": retrieval_attempted,
            "retrieved_record_ids": retrieved,
            "mapped_query_shape": mapped_scope,
            "inventory_id": inventory["inventory_id"],
            "probe_set_id": probes["probe_set_id"],
            "certificate_id": certificate["certificate_id"],
            "insertion_set_id": insertions["insertion_set_id"],
        },
        "gold": {
            "stratum": spec["stratum"],
            "critical": bool(spec.get("critical", False)),
            "query_shape": exact_scope,
            "expected_negative_tier": spec["tier"],
            "expected_negative_tier_by_obligation": obligations,
            "expected_action": spec["action"],
            "certificate_applicable": certificate_scope == exact_scope,
            "certificate_current": status not in {"expired", "invalid"} and inventory_sequence == certificate_sequence,
            "all_required_domains_available": set(registered) == set(available),
            "admissible_insertion_changes_answer": insertion_changes,
        },
    }
    return {"case": case, "inventory": inventory, "probes": probes, "certificate": certificate, "insertions": insertions}


def make_corpus() -> dict[str, list[dict[str, Any]]]:
    bundle = {"cases": [], "inventories": [], "probes": [], "certificates": [], "insertions": []}
    artifact_keys = {
        "cases": "case",
        "inventories": "inventory",
        "probes": "probes",
        "certificates": "certificate",
        "insertions": "insertions",
    }
    for spec in SPECS:
        for language in ("en", "pl"):
            artifacts = make_artifacts(spec, language)
            for key in bundle:
                bundle[key].append(artifacts[artifact_keys[key]])
    return bundle


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def write_corpus(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    bundle = make_corpus()
    for key, rows in bundle.items():
        write_jsonl(output / f"{key}.jsonl", rows)

    case_rows = bundle["cases"]
    manifest = {
        "experiment_id": "PMLAB-CLOSURE-001",
        "dataset": "pmlab-collection-closure-dev-v0",
        "status": "authored-construction-freeze",
        "freeze_boundary": "first git commit containing builder, tests, manifest, and all five JSONL artifacts",
        "case_count": len(case_rows),
        "corpus_sha256": content_hash(bundle),
        "artifact_sha256": {key: content_hash(rows) for key, rows in bundle.items()},
        "strata": dict(sorted(Counter(row["gold"]["stratum"] for row in case_rows).items())),
        "languages": dict(sorted(Counter(row["language"] for row in case_rows).items())),
        "negative_tiers": dict(sorted(Counter(row["gold"]["expected_negative_tier"] for row in case_rows).items())),
        "expected_actions": dict(sorted(Counter(row["gold"]["expected_action"] for row in case_rows).items())),
        "critical_cases": sum(row["gold"]["critical"] for row in case_rows),
        "limitations": [
            "authored construction corpus with visible gold labels",
            "bilingual pairs share semantics and must be split by pair_group",
            "inventories certificates probes and insertions are synthetic diagnostic artifacts",
            "no natural-language scope mapper policy or scoring runner is implemented",
            "passing can validate only state-machine and artifact-contract semantics",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_corpus(), ensure_ascii=False, indent=2))
