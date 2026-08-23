#!/usr/bin/env python3
"""Validate the frozen Foundation event/receipt construction fixture.

This dependency-free validator was created after the contract fixture was frozen at
FREEZE_COMMIT. It checks only authored construction semantics; it is not a storage,
retrieval, reader, or action implementation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab" / "pmlab-foundation-v0"
CONSTRUCTION = LAB / "construction-v0"
EVENTS = CONSTRUCTION / "canonical-events.jsonl"
RECEIPTS = CONSTRUCTION / "stage-receipts.jsonl"
MUTATIONS = CONSTRUCTION / "invalid-mutations.json"
FREEZE_MANIFEST = CONSTRUCTION / "freeze-manifest.json"
DEFAULT_REPORT = CONSTRUCTION / "construction-validation-report.json"
FREEZE_COMMIT = "a7b15d6d62abb929d2073390c4a6cf29b517ba48"

EVENT_FIELDS = {
    "schema_version", "event_id", "idempotency_key", "event_type", "evidence",
    "time", "actor", "scope", "authorization", "provenance", "revision",
}
RECEIPT_FIELDS = {
    "schema_version", "receipt_id", "trace_id", "sequence", "previous_receipt_id",
    "stage", "status", "observed_at", "component", "authorization_state",
    "input_refs", "output_refs", "checks", "failure_codes", "data_loss_state", "note",
}
STAGES = (
    "F0_CAPTURE", "F1_DURABLE_RECORD", "F2_INDEX_ADDRESS", "F3_SELECT_PACK",
    "F4_READER_USE", "F5_ACTION_EVAL",
)
REQUIRED_CHECKS = {
    "F0_CAPTURE": {"source_seen", "capture_authorized", "canonical_append_acknowledged"},
    "F1_DURABLE_RECORD": {"direct_id_read", "full_scan_read", "raw_bytes_recoverable", "content_hash_match", "schema_valid", "provenance_valid"},
    "F2_INDEX_ADDRESS": {"index_membership", "oracle_query_retrieval"},
    "F3_SELECT_PACK": {"retrieved_set_contains_required", "delivered_context_contains_required", "validity_filter_passed", "authorization_filter_passed", "omission_report_present"},
    "F4_READER_USE": {"exact_evidence_exposed", "answer_supported", "citations_resolve"},
    "F5_ACTION_EVAL": {"action_authorized", "action_idempotent", "external_effect_observed", "evaluator_correct"},
}
EVENT_TYPES = {
    "message_observed", "tool_result_observed", "file_span_observed",
    "decision_recorded", "outcome_observed", "correction_recorded",
}
CHECK_STATES = {"pass", "fail", "unknown", "skipped"}
AUTH_STATES = {"authorized", "denied", "unknown", "not_applicable"}
LOSS_STATES = {"confirmed", "ruled_out", "unknown", "not_applicable"}
REF_KINDS = {
    "source", "canonical_event", "canonical_bytes", "index_snapshot",
    "retrieval_set", "context_pack", "reader_output", "action_receipt", "evaluation",
}
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
EVENT_ID_RE = re.compile(r"^EV-[A-F0-9]{16}$")
IDEM_RE = re.compile(r"^IDEM-[A-F0-9]{16}$")
RECEIPT_ID_RE = re.compile(r"^RCPT-[A-F0-9]{16}$")
TRACE_ID_RE = re.compile(r"^TRACE-[A-F0-9]{12}$")
FAILURE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,79}$")
PROHIBITED_KEYS = {
    "semantic_summary", "chain_of_thought", "private_reasoning", "scratchpad",
    "password", "api_key", "authorization_header", "cookie",
}


class ContractError(ValueError):
    """A deterministic Foundation construction-contract failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def exact_fields(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{name} must be an object")
    missing = fields - set(value)
    extra = set(value) - fields
    require(not missing, f"{name} missing fields: {sorted(missing)}")
    require(not extra, f"{name} unexpected field: {sorted(extra)}")
    return value


def parse_time(value: Any, name: str, *, nullable: bool = False) -> datetime | None:
    if value is None and nullable:
        return None
    require(isinstance(value, str), f"{name} must be an ISO date-time")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{name} must be an ISO date-time") from exc


def require_string(value: Any, name: str, *, max_length: int = 500, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    require(isinstance(value, str) and bool(value.strip()), f"{name} must be nonempty")
    require(len(value) <= max_length, f"{name} exceeds maximum length")
    return value


def require_hash(value: Any, name: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, f"{name} must be sha256")
    return value


def walk_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            require(key not in PROHIBITED_KEYS, f"unexpected field {key} at {path}")
            walk_prohibited(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_prohibited(child, f"{path}/{index}")


def validate_event_shape(event: dict[str, Any]) -> None:
    exact_fields(event, EVENT_FIELDS, "event")
    require(event["schema_version"] == "foundation-canonical-event-v0.1", "event schema_version")
    require(isinstance(event["event_id"], str) and EVENT_ID_RE.fullmatch(event["event_id"]) is not None, "event_id format")
    require(isinstance(event["idempotency_key"], str) and IDEM_RE.fullmatch(event["idempotency_key"]) is not None, "idempotency_key format")
    require(event["event_type"] in EVENT_TYPES, "event_type")

    evidence = exact_fields(event["evidence"], {"content_sha256", "byte_length", "media_type", "storage_ref", "source_locator", "source_object_sha256", "exact_span"}, "evidence")
    require_hash(evidence["content_sha256"], "evidence.content_sha256")
    require(isinstance(evidence["byte_length"], int) and not isinstance(evidence["byte_length"], bool) and evidence["byte_length"] > 0, "evidence.byte_length")
    require_string(evidence["media_type"], "evidence.media_type", max_length=100)
    require_string(evidence["storage_ref"], "evidence.storage_ref")
    require(evidence["storage_ref"].startswith("data/lab/pmlab-foundation-v0/construction-v0/raw/"), "storage_ref outside frozen raw directory")
    require(".." not in Path(evidence["storage_ref"]).parts, "storage_ref traversal")
    require_string(evidence["source_locator"], "evidence.source_locator")
    require_hash(evidence["source_object_sha256"], "evidence.source_object_sha256", nullable=True)
    span = evidence["exact_span"]
    if span is not None:
        exact_fields(span, {"unit", "start", "end"}, "exact_span")
        require(span["unit"] in {"utf8_byte", "unicode_codepoint", "line"}, "exact_span unit")
        require(isinstance(span["start"], int) and isinstance(span["end"], int) and 0 <= span["start"] < span["end"], "exact_span bounds")
        if span["unit"] == "utf8_byte":
            require(span["end"] - span["start"] == evidence["byte_length"], "exact_span byte length")

    times = exact_fields(event["time"], {"occurred_at", "observed_at", "valid_from", "valid_to", "transaction_at", "precision", "timezone"}, "time")
    parse_time(times["occurred_at"], "occurred_at", nullable=True)
    observed = parse_time(times["observed_at"], "observed_at")
    valid_from = parse_time(times["valid_from"], "valid_from", nullable=True)
    valid_to = parse_time(times["valid_to"], "valid_to", nullable=True)
    transaction = parse_time(times["transaction_at"], "transaction_at")
    require(valid_from is None or valid_to is None or valid_from < valid_to, "valid interval is reversed or empty")
    require(transaction is not None and observed is not None and transaction >= observed, "transaction precedes observation")
    require(times["precision"] in {"second", "minute", "hour", "day", "unknown"}, "time.precision")
    require_string(times["timezone"], "time.timezone", max_length=100)

    actor = exact_fields(event["actor"], {"actor_id", "actor_kind"}, "actor")
    require_string(actor["actor_id"], "actor.actor_id", max_length=120)
    require(actor["actor_kind"] in {"user", "model", "tool", "system", "external"}, "actor_kind")
    scope = exact_fields(event["scope"], {"workspace_id", "session_id", "task_id"}, "scope")
    require_string(scope["workspace_id"], "scope.workspace_id", max_length=120)
    require_string(scope["session_id"], "scope.session_id", max_length=120, nullable=True)
    require_string(scope["task_id"], "scope.task_id", max_length=120, nullable=True)

    auth = exact_fields(event["authorization"], {"capture_basis", "capture_allowed", "external_processing_allowed", "sensitivity", "access_scopes", "retention_class", "governance_receipt_id"}, "authorization")
    require(auth["capture_basis"] in {"synthetic", "explicit_user_scope", "project_artifact_allowlist"}, "capture_basis")
    require(auth["capture_allowed"] is True, "capture_allowed must be true for canonical event")
    require(isinstance(auth["external_processing_allowed"], bool), "external_processing_allowed")
    require(auth["sensitivity"] in {"none", "internal", "personal", "secret"}, "sensitivity")
    require(isinstance(auth["access_scopes"], list) and auth["access_scopes"], "access_scopes")
    require(len(auth["access_scopes"]) == len(set(auth["access_scopes"])), "duplicate access scope")
    require(set(auth["access_scopes"]) <= {"local_research", "approved_external_worker", "user_only"}, "access scope")
    require(auth["retention_class"] in {"synthetic_disposable", "project_research", "restricted"}, "retention_class")
    if auth["governance_receipt_id"] is not None:
        require(re.fullmatch(r"GOV-[A-F0-9]{12}", auth["governance_receipt_id"]) is not None, "governance receipt")
    if auth["external_processing_allowed"]:
        require("approved_external_worker" in auth["access_scopes"] and auth["governance_receipt_id"] is not None, "external processing lacks governance")
        require(auth["sensitivity"] != "secret", "secret external processing forbidden")

    provenance = exact_fields(event["provenance"], {"producer_component", "producer_version", "upstream_event_ids", "causal_parent_ids"}, "provenance")
    require_string(provenance["producer_component"], "producer_component", max_length=100)
    require_string(provenance["producer_version"], "producer_version", max_length=100)
    for key in ("upstream_event_ids", "causal_parent_ids"):
        require(isinstance(provenance[key], list) and len(provenance[key]) == len(set(provenance[key])), f"{key} unique list")
        require(all(isinstance(item, str) and EVENT_ID_RE.fullmatch(item) is not None for item in provenance[key]), f"{key} format")

    revision = exact_fields(event["revision"], {"relation", "target_event_id", "reason"}, "revision")
    require(revision["relation"] in {"original", "corrects", "supersedes"}, "revision relation")
    if revision["target_event_id"] is not None:
        require(isinstance(revision["target_event_id"], str) and EVENT_ID_RE.fullmatch(revision["target_event_id"]) is not None, "revision target format")
    require_string(revision["reason"], "revision reason", max_length=240, nullable=True)
    walk_prohibited(event)


def validate_events(events: list[dict[str, Any]]) -> None:
    require(bool(events), "no events")
    for event in events:
        validate_event_shape(event)
    ids = [event["event_id"] for event in events]
    idempotency = [event["idempotency_key"] for event in events]
    require(len(ids) == len(set(ids)), "duplicate event_id")
    require(len(idempotency) == len(set(idempotency)), "duplicate idempotency_key")
    seen: set[str] = set()
    previous_transaction: datetime | None = None
    for event in events:
        transaction = parse_time(event["time"]["transaction_at"], "transaction_at")
        require(previous_transaction is None or transaction >= previous_transaction, "transaction order")
        previous_transaction = transaction
        relation = event["revision"]["relation"]
        target = event["revision"]["target_event_id"]
        if relation == "original":
            require(target is None and event["revision"]["reason"] is None, "original revision must not have target or reason")
        else:
            require(target in seen, "revision target must name an earlier event")
            require(event["revision"]["reason"] is not None, "revision reason required")
        require(event["event_id"] not in event["provenance"]["causal_parent_ids"], "self causal parent")
        require(set(event["provenance"]["causal_parent_ids"]) <= seen, "causal parent must be earlier")
        if event["event_type"] == "correction_recorded":
            require(relation in {"corrects", "supersedes"}, "correction event requires revision target")
        evidence = event["evidence"]
        path = ROOT / evidence["storage_ref"]
        require(path.is_file(), "canonical bytes missing")
        raw = path.read_bytes()
        require(len(raw) == evidence["byte_length"], "canonical byte length mismatch")
        require(sha256_bytes(raw) == evidence["content_sha256"], "content hash mismatch")
        if evidence["source_object_sha256"] is not None:
            require(sha256_bytes(raw) == evidence["source_object_sha256"], "source object hash mismatch")
        seen.add(event["event_id"])


def validate_ref(value: Any, name: str) -> None:
    ref = exact_fields(value, {"kind", "id", "sha256"}, name)
    require(ref["kind"] in REF_KINDS, f"{name} kind")
    require_string(ref["id"], f"{name}.id", max_length=200)
    require_hash(ref["sha256"], f"{name}.sha256", nullable=True)


def validate_receipt_shape(receipt: dict[str, Any]) -> None:
    exact_fields(receipt, RECEIPT_FIELDS, "receipt")
    require(receipt["schema_version"] == "foundation-stage-receipt-v0.1", "receipt schema_version")
    require(isinstance(receipt["receipt_id"], str) and RECEIPT_ID_RE.fullmatch(receipt["receipt_id"]) is not None, "receipt_id format")
    require(isinstance(receipt["trace_id"], str) and TRACE_ID_RE.fullmatch(receipt["trace_id"]) is not None, "trace_id format")
    require(receipt["stage"] in STAGES, "stage")
    require(isinstance(receipt["sequence"], int) and receipt["sequence"] == STAGES.index(receipt["stage"]), "stage sequence")
    require(receipt["previous_receipt_id"] is None or (isinstance(receipt["previous_receipt_id"], str) and RECEIPT_ID_RE.fullmatch(receipt["previous_receipt_id"]) is not None), "previous receipt format")
    require(receipt["status"] in CHECK_STATES, "receipt status")
    parse_time(receipt["observed_at"], "receipt observed_at")
    component = exact_fields(receipt["component"], {"name", "version"}, "component")
    require_string(component["name"], "component.name", max_length=100)
    require_string(component["version"], "component.version", max_length=100)
    require(receipt["authorization_state"] in AUTH_STATES, "authorization state")
    require(isinstance(receipt["input_refs"], list) and isinstance(receipt["output_refs"], list), "receipt refs")
    for index, ref in enumerate(receipt["input_refs"]):
        validate_ref(ref, f"input_refs[{index}]")
    for index, ref in enumerate(receipt["output_refs"]):
        validate_ref(ref, f"output_refs[{index}]")
    require(isinstance(receipt["checks"], list) and receipt["checks"], "checks")
    check_ids: list[str] = []
    for check in receipt["checks"]:
        exact_fields(check, {"check_id", "status", "evidence_ref"}, "check")
        require(isinstance(check["check_id"], str) and re.fullmatch(r"[a-z][a-z0-9_]{1,79}", check["check_id"]) is not None, "check_id")
        require(check["status"] in CHECK_STATES, "check status")
        require_string(check["evidence_ref"], "check evidence_ref", max_length=300, nullable=True)
        check_ids.append(check["check_id"])
    require(len(check_ids) == len(set(check_ids)), "duplicate check")
    missing = REQUIRED_CHECKS[receipt["stage"]] - set(check_ids)
    require(not missing, f"missing required checks: {sorted(missing)}")
    statuses = {check["check_id"]: check["status"] for check in receipt["checks"]}
    if receipt["status"] == "pass":
        require(all(statuses[check] == "pass" for check in REQUIRED_CHECKS[receipt["stage"]]), "pass receipt has non-pass check")
        require(not receipt["failure_codes"], "pass receipt has failure code")
    elif receipt["status"] == "fail":
        require(any(statuses[check] == "fail" for check in REQUIRED_CHECKS[receipt["stage"]]), "failed receipt lacks failed required check")
        require(bool(receipt["failure_codes"]), "failed receipt lacks failure code")
    require(isinstance(receipt["failure_codes"], list) and len(receipt["failure_codes"]) == len(set(receipt["failure_codes"])), "failure codes unique list")
    require(all(isinstance(code, str) and FAILURE_RE.fullmatch(code) is not None for code in receipt["failure_codes"]), "failure code format")
    require(receipt["data_loss_state"] in LOSS_STATES, "data loss state")
    require_string(receipt["note"], "receipt note", max_length=500, nullable=True)
    if receipt["stage"] != "F1_DURABLE_RECORD":
        require(receipt["data_loss_state"] == "not_applicable", "data loss not applicable outside F1")
    else:
        loss_checks = ("direct_id_read", "full_scan_read", "raw_bytes_recoverable", "content_hash_match")
        values = [statuses[name] for name in loss_checks]
        if receipt["data_loss_state"] == "confirmed":
            require(all(value == "fail" for value in values), "confirmed physical loss lacks four failed probes")
        elif receipt["data_loss_state"] == "ruled_out":
            require(any(value == "pass" for value in values), "ruled-out physical loss lacks recovery evidence")
        elif receipt["data_loss_state"] == "not_applicable":
            raise ContractError("F1 data loss state cannot be not_applicable")
    if receipt["status"] == "pass" and receipt["stage"] in {"F0_CAPTURE", "F1_DURABLE_RECORD", "F3_SELECT_PACK", "F4_READER_USE", "F5_ACTION_EVAL"}:
        require(receipt["authorization_state"] == "authorized", "passing exposure-capable stage is not authorized")
    walk_prohibited(receipt)


def validate_receipts(receipts: list[dict[str, Any]]) -> None:
    require(bool(receipts), "no receipts")
    for receipt in receipts:
        validate_receipt_shape(receipt)
    require(len(receipts) == len(STAGES), "construction trace must cover six stages")
    require([receipt["stage"] for receipt in receipts] == list(STAGES), "stage order")
    require([receipt["sequence"] for receipt in receipts] == list(range(len(STAGES))), "sequence order")
    require(len({receipt["receipt_id"] for receipt in receipts}) == len(receipts), "duplicate receipt_id")
    require(len({receipt["trace_id"] for receipt in receipts}) == 1, "multiple trace ids")
    previous_time: datetime | None = None
    for index, receipt in enumerate(receipts):
        expected_previous = None if index == 0 else receipts[index - 1]["receipt_id"]
        require(receipt["previous_receipt_id"] == expected_previous, "previous receipt chain mismatch")
        observed = parse_time(receipt["observed_at"], "receipt observed_at")
        require(previous_time is None or observed >= previous_time, "receipt time order")
        previous_time = observed


def pointer_parent(value: Any, pointer: str) -> tuple[Any, str]:
    require(pointer.startswith("/"), "mutation path")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]
    parent = value
    for part in parts[:-1]:
        require(isinstance(parent, dict) and part in parent, "mutation path missing")
        parent = parent[part]
    return parent, parts[-1]


def apply_mutations(collection: list[dict[str, Any]], case: dict[str, Any]) -> list[dict[str, Any]]:
    result = copy.deepcopy(collection)
    id_field = "event_id" if case["target"] == "events" else "receipt_id"
    for mutation in case["mutations"]:
        target_id = mutation[id_field]
        item = next((row for row in result if row[id_field] == target_id), None)
        require(item is not None, "mutation target missing")
        operation = mutation["op"]
        if operation in {"add", "replace"}:
            parent, key = pointer_parent(item, mutation["path"])
            require(isinstance(parent, dict), "mutation parent")
            if operation == "replace":
                require(key in parent, "mutation replace path missing")
            parent[key] = mutation["value"]
        elif operation == "remove_check":
            item["checks"] = [check for check in item["checks"] if check["check_id"] != mutation["check_id"]]
        elif operation == "replace_check":
            check = next((check for check in item["checks"] if check["check_id"] == mutation["check_id"]), None)
            require(check is not None, "mutation check missing")
            check[mutation["field"]] = mutation["value"]
        elif operation == "duplicate_check":
            check = next((check for check in item["checks"] if check["check_id"] == mutation["check_id"]), None)
            require(check is not None, "mutation check missing")
            item["checks"].append(copy.deepcopy(check))
        else:
            raise ContractError(f"unsupported mutation operation: {operation}")
    return result


def verify_frozen_bytes(manifest: dict[str, Any]) -> None:
    require(manifest["status"] == "contract-and-authored-fixture-frozen-before-validator", "freeze manifest status")
    require(manifest["runner_present_at_freeze"] is False, "runner unexpectedly present at freeze")
    require(manifest["api_authorized"] is False and manifest["api_budget_usd"] == 0, "construction API authorization")
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"frozen artifact missing: {artifact['path']}")
        raw = path.read_bytes()
        require(len(raw) == artifact["bytes"], f"frozen byte length changed: {artifact['path']}")
        require(sha256_bytes(raw) == artifact["sha256"], f"frozen hash changed: {artifact['path']}")
        blob = subprocess.run(
            ["git", "show", f"{FREEZE_COMMIT}:{artifact['path']}"],
            cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
        require(blob == raw, f"working bytes differ from freeze commit: {artifact['path']}")


def git_head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()


def run(report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    manifest = load_json(FREEZE_MANIFEST)
    events = load_jsonl(EVENTS)
    receipts = load_jsonl(RECEIPTS)
    mutation_manifest = load_json(MUTATIONS)
    schemas = [
        load_json(LAB / "contracts" / "canonical-event-v0.1.schema.json"),
        load_json(LAB / "contracts" / "stage-receipt-v0.1.schema.json"),
    ]
    require(all(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema" for schema in schemas), "schema draft")
    verify_frozen_bytes(manifest)
    validate_events(events)
    validate_receipts(receipts)

    mutation_results = []
    for case in mutation_manifest["cases"]:
        try:
            if case["target"] == "events":
                validate_events(apply_mutations(events, case))
                validate_receipts(receipts)
            elif case["target"] == "receipts":
                validate_events(events)
                validate_receipts(apply_mutations(receipts, case))
            else:
                raise ContractError("invalid mutation target")
        except ContractError as exc:
            error = str(exc)
            require(case["expected_error"].lower() in error.lower(), f"{case['case_id']} wrong error: {error}")
            mutation_results.append({"case_id": case["case_id"], "rejected": True, "error": error})
        else:
            raise ContractError(f"{case['case_id']} was accepted")

    checks = [
        {"check_id": "frozen_bytes_match_manifest_and_commit", "passed": True, "count": len(manifest["artifacts"])},
        {"check_id": "schemas_parse_and_pin_draft", "passed": True, "count": len(schemas)},
        {"check_id": "canonical_events_valid", "passed": True, "count": len(events)},
        {"check_id": "raw_content_hashes_and_lengths_match", "passed": True, "count": len(events)},
        {"check_id": "revision_and_temporal_invariants_valid", "passed": True, "count": len(events)},
        {"check_id": "six_stage_trace_valid", "passed": True, "count": len(receipts)},
        {"check_id": "physical_loss_rule_valid", "passed": True, "count": 1},
        {"check_id": "registered_invalid_mutations_rejected", "passed": True, "count": len(mutation_results)},
    ]
    report = {
        "schema_version": "foundation-construction-validation-report-v0.1",
        "contract_id": manifest["contract_id"],
        "parent_experiment_id": manifest["parent_experiment_id"],
        "status": "passed-authored-model-free-construction",
        "freeze_commit": FREEZE_COMMIT,
        "validator_head": git_head(),
        "model_api_used": False,
        "api_cost_usd": 0,
        "independent_review": False,
        "parent_execution_authorized": False,
        "claim_limit": "Contract and validator agree on one frozen authored synthetic fixture; no operational memory claim.",
        "counts": {"canonical_events": len(events), "stage_receipts": len(receipts), "invalid_mutations": len(mutation_results)},
        "checks": checks,
        "mutation_results": mutation_results,
        "next_gate": "independent semantic attack plus unseen second-author traces before any promotion",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate frozen Foundation event/receipt construction fixture")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.report)
    print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "invalid_mutations": report["counts"]["invalid_mutations"]}, indent=2))


if __name__ == "__main__":
    main()

