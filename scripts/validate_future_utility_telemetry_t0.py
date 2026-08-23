#!/usr/bin/env python3
"""Validate synthetic T0 future-utility telemetry without external packages."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab" / "pmlab-future-utility-v0"
SCHEMA = LAB / "telemetry-event-v0.1.schema.json"
VALID = LAB / "t0" / "valid-deliveries.jsonl"
INVALID = LAB / "t0" / "invalid-cases.json"
REPORT = LAB / "t0" / "validation-report.json"

SCHEMA_VERSION = "pmlab-utility-telemetry-v0.1"
EVENT_TYPES = {
    "memory_registered",
    "task_registered",
    "candidate_set_frozen",
    "retrieval_observed",
    "exposure_assigned",
    "exposure_observed",
    "behavior_reference",
    "outcome_observed",
    "cost_observed",
    "observation_window_closed",
    "correction",
    "causal_effect_estimated",
}
COMMON_REQUIRED = {
    "schema_version", "event_id", "idempotency_key", "event_type", "phase",
    "occurred_at", "recorded_at", "producer", "privacy", "payload",
}
COMMON_ALLOWED = COMMON_REQUIRED | {"task_id", "memory_id"}
PROHIBITED_KEYS = {
    "raw_content", "raw_conversation", "raw_prompt", "prompt_text", "memory_body",
    "model_output", "chain_of_thought", "private_reasoning", "scratchpad", "password",
    "api_key", "authorization_header", "cookie", "email", "phone", "legal_name",
}
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{12,}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
)
EVENT_ID_RE = re.compile(r"^TE-[A-F0-9]{16}$")
IDEM_RE = re.compile(r"^IDEM-[A-F0-9]{16}$")
TASK_RE = re.compile(r"^TASK-[A-F0-9]{12}$")
MEMORY_RE = re.compile(r"^MEM-[A-F0-9]{12}$")
ASSIGN_RE = re.compile(r"^ASG-[A-F0-9]{12}$")
GOVERNANCE_RE = re.compile(r"^GOV-[A-F0-9]{12}$")
DEPENDENCE_RE = re.compile(r"^DEP-[A-F0-9]{12}$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
OUTCOME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class TelemetryError(ValueError):
    """A deterministic telemetry contract failure."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TelemetryError(message)


def exact_fields(value: Any, required: set[str], allowed: set[str], name: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{name} must be an object")
    missing = required - set(value)
    extra = set(value) - allowed
    require(not missing, f"{name} missing fields: {sorted(missing)}")
    require(not extra, f"{name} unexpected fields: {sorted(extra)}")
    return value


def parse_time(value: Any, name: str) -> datetime:
    require(isinstance(value, str), f"{name} must be a date-time string")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryError(f"{name} is not ISO date-time") from exc


def require_string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    require(isinstance(value, str), f"{name} must be a string")
    require(allow_empty or bool(value.strip()), f"{name} must be nonempty")
    return value


def require_hash(value: Any, name: str) -> str:
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, f"{name} must be sha256")
    return value


def require_number(value: Any, name: str, *, minimum: float | None = None) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name} must be numeric")
    if minimum is not None:
        require(value >= minimum, f"{name} must be >= {minimum}")
    return float(value)


def walk_privacy(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            require(key not in PROHIBITED_KEYS, f"prohibited key at {path}/{key}")
            walk_privacy(child, f"{path}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk_privacy(child, f"{path}/{index}")
    elif isinstance(value, str):
        require(not any(pattern.search(value) for pattern in SECRET_PATTERNS), f"secret-like string at {path}")


def validate_privacy(event: dict[str, Any]) -> None:
    privacy = exact_fields(
        event["privacy"],
        {"capture_basis", "sensitivity", "redaction_count", "external_processing_allowed", "governance_receipt_id", "retention_class", "access_scope"},
        {"capture_basis", "sensitivity", "redaction_count", "external_processing_allowed", "governance_receipt_id", "retention_class", "access_scope"},
        "privacy",
    )
    require(privacy["capture_basis"] in {"synthetic", "explicit_user_scope", "project_artifact_allowlist", "not_captured"}, "invalid capture_basis")
    require(privacy["sensitivity"] in {"none", "internal", "personal", "secret", "private_reasoning"}, "invalid sensitivity")
    require(isinstance(privacy["redaction_count"], int) and privacy["redaction_count"] >= 0, "redaction_count must be a nonnegative integer")
    require(isinstance(privacy["external_processing_allowed"], bool), "external_processing_allowed must be boolean")
    require(not (privacy["sensitivity"] != "none" and privacy["external_processing_allowed"]), "sensitive event cannot allow external processing")
    require(privacy["governance_receipt_id"] is None or (isinstance(privacy["governance_receipt_id"], str) and GOVERNANCE_RE.fullmatch(privacy["governance_receipt_id"])), "governance_receipt_id invalid")
    require(privacy["retention_class"] in {"synthetic_disposable", "project_research", "restricted"}, "invalid retention_class")
    require(privacy["access_scope"] in {"local_research_only", "approved_external_worker"}, "invalid access_scope")
    require(not privacy["external_processing_allowed"] or privacy["access_scope"] == "approved_external_worker", "external processing requires approved_external_worker scope")
    if event["phase"] == "T0":
        require(privacy["capture_basis"] == "synthetic" and privacy["sensitivity"] == "none", "T0 permits synthetic nonsensitive events only")
        require(privacy["external_processing_allowed"] is False, "T0 external processing is prohibited")
        require(privacy["governance_receipt_id"] is None and privacy["retention_class"] == "synthetic_disposable" and privacy["access_scope"] == "local_research_only", "T0 requires disposable local synthetic governance")
    elif privacy["capture_basis"] in {"explicit_user_scope", "project_artifact_allowlist"}:
        require(privacy["governance_receipt_id"] is not None, "natural capture requires governance receipt")
    walk_privacy(event)


def validate_payload(event: dict[str, Any]) -> None:
    kind = event["event_type"]
    payload = event["payload"]
    prefix = f"{event['event_id']}.{kind}.payload"

    if kind == "memory_registered":
        required = {"content_sha256", "memory_version", "provenance_class", "authorization_state", "trust_state", "validity_state"}
        allowed = required | {"transaction_time", "valid_from", "valid_to"}
        p = exact_fields(payload, required, allowed, prefix)
        require_hash(p["content_sha256"], f"{prefix}.content_sha256")
        require(isinstance(p["memory_version"], int) and p["memory_version"] >= 1, f"{prefix}.memory_version invalid")
        require(p["provenance_class"] in {"canonical_project_event", "reviewed_project_document", "synthetic_fixture", "external_source_claim"}, f"{prefix}.provenance_class invalid")
        require(p["authorization_state"] in {"authorized", "denied", "unknown"}, f"{prefix}.authorization_state invalid")
        require(p["trust_state"] in {"reviewed", "unreviewed", "contested"}, f"{prefix}.trust_state invalid")
        require(p["validity_state"] in {"current", "stale", "superseded", "unknown"}, f"{prefix}.validity_state invalid")
        for field in ("transaction_time", "valid_from", "valid_to"):
            if field in p and p[field] is not None:
                parse_time(p[field], f"{prefix}.{field}")

    elif kind == "task_registered":
        required = {"task_family", "language", "criticality", "query_cutoff", "observation_window_end", "dependence_cluster_id", "outcome_specs", "policy_versions"}
        p = exact_fields(payload, required, required, prefix)
        require_string(p["task_family"], f"{prefix}.task_family")
        require(p["language"] in {"pl", "en", "mixed", "other"}, f"{prefix}.language invalid")
        require(p["criticality"] in {"ordinary", "critical"}, f"{prefix}.criticality invalid")
        parse_time(p["query_cutoff"], f"{prefix}.query_cutoff")
        parse_time(p["observation_window_end"], f"{prefix}.observation_window_end")
        require(isinstance(p["dependence_cluster_id"], str) and DEPENDENCE_RE.fullmatch(p["dependence_cluster_id"]), f"{prefix}.dependence_cluster_id invalid")
        require(isinstance(p["outcome_specs"], list) and p["outcome_specs"], f"{prefix}.outcome_specs must be nonempty")
        names: set[str] = set()
        for index, spec in enumerate(p["outcome_specs"]):
            label = f"{prefix}.outcome_specs[{index}]"
            s = exact_fields(spec, {"name", "unit", "direction", "window_days"}, {"name", "unit", "direction", "window_days"}, label)
            require(isinstance(s["name"], str) and OUTCOME_RE.fullmatch(s["name"]) is not None, f"{label}.name invalid")
            require(s["name"] not in names, f"{prefix}.outcome_specs duplicate name")
            names.add(s["name"])
            require_string(s["unit"], f"{label}.unit")
            require(s["direction"] in {"higher_better", "lower_better", "harm"}, f"{label}.direction invalid")
            require(isinstance(s["window_days"], int) and 0 <= s["window_days"] <= 3650, f"{label}.window_days invalid")
        policy_fields = {"retrieval", "reranker", "reader", "prompt", "model", "exposure"}
        policies = exact_fields(p["policy_versions"], policy_fields, policy_fields, f"{prefix}.policy_versions")
        for key, value in policies.items():
            require_string(value, f"{prefix}.policy_versions.{key}", allow_empty=False)

    elif kind == "candidate_set_frozen":
        fields = {"candidate_set_sha256", "candidate_memory_ids", "corpus_cutoff", "selection_policy"}
        p = exact_fields(payload, fields, fields, prefix)
        require_hash(p["candidate_set_sha256"], f"{prefix}.candidate_set_sha256")
        require(isinstance(p["candidate_memory_ids"], list), f"{prefix}.candidate_memory_ids must be a list")
        require(len(p["candidate_memory_ids"]) == len(set(p["candidate_memory_ids"])), f"{prefix}.candidate_memory_ids contains duplicates")
        require(all(isinstance(item, str) and MEMORY_RE.fullmatch(item) for item in p["candidate_memory_ids"]), f"{prefix}.candidate_memory_ids invalid")
        parse_time(p["corpus_cutoff"], f"{prefix}.corpus_cutoff")
        require_string(p["selection_policy"], f"{prefix}.selection_policy")

    elif kind == "retrieval_observed":
        fields = {"eligible", "eligibility_reason", "retrieved", "rank", "component_scores", "candidate_count"}
        p = exact_fields(payload, fields, fields, prefix)
        require(isinstance(p["eligible"], bool) and isinstance(p["retrieved"], bool), f"{prefix} eligibility fields must be boolean")
        require_string(p["eligibility_reason"], f"{prefix}.eligibility_reason")
        require(p["rank"] is None or (isinstance(p["rank"], int) and p["rank"] >= 1), f"{prefix}.rank invalid")
        require(p["retrieved"] == (p["rank"] is not None), f"{prefix}.retrieved and rank disagree")
        require(isinstance(p["component_scores"], dict) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p["component_scores"].values()), f"{prefix}.component_scores invalid")
        require(isinstance(p["candidate_count"], int) and p["candidate_count"] >= 0, f"{prefix}.candidate_count invalid")

    elif kind == "exposure_assigned":
        fields = {"assignment_id", "mechanism", "arm", "propensity", "safety_exclusion"}
        p = exact_fields(payload, fields, fields, prefix)
        require(isinstance(p["assignment_id"], str) and ASSIGN_RE.fullmatch(p["assignment_id"]), f"{prefix}.assignment_id invalid")
        require(p["mechanism"] in {"synthetic_validation", "natural_observation", "randomized", "deterministic_safety_override"}, f"{prefix}.mechanism invalid")
        require(p["arm"] in {"include", "withhold", "natural", "forced_include"}, f"{prefix}.arm invalid")
        require(p["propensity"] is None or (isinstance(p["propensity"], (int, float)) and not isinstance(p["propensity"], bool) and 0 < p["propensity"] <= 1), f"{prefix}.propensity invalid")
        require(p["safety_exclusion"] is None or isinstance(p["safety_exclusion"], str), f"{prefix}.safety_exclusion invalid")

    elif kind == "exposure_observed":
        fields = {"assignment_id", "shown", "context_position", "withhold_reason", "context_packet_sha256"}
        p = exact_fields(payload, fields, fields, prefix)
        require(isinstance(p["assignment_id"], str) and ASSIGN_RE.fullmatch(p["assignment_id"]), f"{prefix}.assignment_id invalid")
        require(isinstance(p["shown"], bool), f"{prefix}.shown must be boolean")
        require(p["context_position"] is None or (isinstance(p["context_position"], int) and p["context_position"] >= 0), f"{prefix}.context_position invalid")
        require(p["withhold_reason"] is None or isinstance(p["withhold_reason"], str), f"{prefix}.withhold_reason invalid")
        require_hash(p["context_packet_sha256"], f"{prefix}.context_packet_sha256")

    elif kind == "behavior_reference":
        fields = {"output_sha256", "reference_type", "evidence_event_ids", "explicit_user_feedback"}
        p = exact_fields(payload, fields, fields, prefix)
        require_hash(p["output_sha256"], f"{prefix}.output_sha256")
        require(p["reference_type"] in {"citation", "quoted_fact", "action_dependency", "explicit_user_reference"}, f"{prefix}.reference_type invalid")
        require(isinstance(p["evidence_event_ids"], list) and p["evidence_event_ids"], f"{prefix}.evidence_event_ids must be nonempty")
        require(len(p["evidence_event_ids"]) == len(set(p["evidence_event_ids"])), f"{prefix}.evidence_event_ids contains duplicates")
        require(all(isinstance(item, str) and EVENT_ID_RE.fullmatch(item) for item in p["evidence_event_ids"]), f"{prefix}.evidence_event_ids invalid")
        require(p["explicit_user_feedback"] in {"positive", "negative", "neutral", "not_observed"}, f"{prefix}.explicit_user_feedback invalid")

    elif kind == "outcome_observed":
        fields = {"outcome_name", "value", "unit", "window_days", "assessor_id", "assessor_blinded", "harm_flags"}
        p = exact_fields(payload, fields, fields, prefix)
        require(isinstance(p["outcome_name"], str) and OUTCOME_RE.fullmatch(p["outcome_name"]), f"{prefix}.outcome_name invalid")
        require(isinstance(p["value"], (int, float, bool)), f"{prefix}.value invalid")
        require_string(p["unit"], f"{prefix}.unit")
        require(isinstance(p["window_days"], int) and 0 <= p["window_days"] <= 3650, f"{prefix}.window_days invalid")
        require_string(p["assessor_id"], f"{prefix}.assessor_id")
        require(isinstance(p["assessor_blinded"], bool), f"{prefix}.assessor_blinded must be boolean")
        harms = {"stale_action", "privacy_leak", "unsupported_answer", "forbidden_intrusion", "wasted_work"}
        require(isinstance(p["harm_flags"], list) and len(p["harm_flags"]) == len(set(p["harm_flags"])) and set(p["harm_flags"]) <= harms, f"{prefix}.harm_flags invalid")

    elif kind == "cost_observed":
        fields = {"input_cache_hit_tokens", "input_cache_miss_tokens", "output_tokens", "usd", "latency_ms", "local_compute_ms", "price_manifest_id"}
        p = exact_fields(payload, fields, fields, prefix)
        for field in ("input_cache_hit_tokens", "input_cache_miss_tokens", "output_tokens"):
            require(isinstance(p[field], int) and p[field] >= 0, f"{prefix}.{field} invalid")
        for field in ("usd", "latency_ms", "local_compute_ms"):
            require_number(p[field], f"{prefix}.{field}", minimum=0)
        require(p["price_manifest_id"] is None or isinstance(p["price_manifest_id"], str), f"{prefix}.price_manifest_id invalid")

    elif kind == "observation_window_closed":
        fields = {"window_end", "censoring_reason", "outstanding_outcome_names"}
        p = exact_fields(payload, fields, fields, prefix)
        parse_time(p["window_end"], f"{prefix}.window_end")
        require(p["censoring_reason"] in {"none", "observation_window_ended", "task_abandoned", "outcome_unavailable", "policy_change"}, f"{prefix}.censoring_reason invalid")
        require(isinstance(p["outstanding_outcome_names"], list) and len(p["outstanding_outcome_names"]) == len(set(p["outstanding_outcome_names"])), f"{prefix}.outstanding_outcome_names invalid")
        require(all(isinstance(item, str) and OUTCOME_RE.fullmatch(item) for item in p["outstanding_outcome_names"]), f"{prefix}.outstanding_outcome_names invalid")

    elif kind == "correction":
        fields = {"target_event_id", "field_corrections", "reason"}
        p = exact_fields(payload, fields, fields, prefix)
        require(isinstance(p["target_event_id"], str) and EVENT_ID_RE.fullmatch(p["target_event_id"]), f"{prefix}.target_event_id invalid")
        require(isinstance(p["field_corrections"], dict) and p["field_corrections"], f"{prefix}.field_corrections must be nonempty")
        require(all(isinstance(path, str) and path.startswith("/payload/") for path in p["field_corrections"]), f"{prefix}.field_corrections paths must remain under payload")
        require(all(value is None or isinstance(value, (str, int, float, bool)) for value in p["field_corrections"].values()), f"{prefix}.field_corrections values must be scalar")
        require_string(p["reason"], f"{prefix}.reason")

    elif kind == "causal_effect_estimated":
        fields = {"design_id", "estimand", "estimator", "population", "contrast", "estimate", "interval_low", "interval_high", "sample_size", "cost_adjusted", "harm_adjusted"}
        p = exact_fields(payload, fields, fields, prefix)
        for field in ("design_id", "estimand", "estimator", "population", "contrast"):
            require_string(p[field], f"{prefix}.{field}")
        for field in ("estimate", "interval_low", "interval_high"):
            require_number(p[field], f"{prefix}.{field}")
        require(p["interval_low"] <= p["estimate"] <= p["interval_high"], f"{prefix} interval does not contain estimate")
        require(isinstance(p["sample_size"], int) and p["sample_size"] >= 1, f"{prefix}.sample_size invalid")
        require(isinstance(p["cost_adjusted"], bool) and isinstance(p["harm_adjusted"], bool), f"{prefix} adjustment flags must be boolean")


def validate_event_shape(event: Any) -> dict[str, Any]:
    e = exact_fields(event, COMMON_REQUIRED, COMMON_ALLOWED, "event")
    require(e["schema_version"] == SCHEMA_VERSION, "unsupported schema_version")
    require(isinstance(e["event_id"], str) and EVENT_ID_RE.fullmatch(e["event_id"]), "invalid event_id")
    require(isinstance(e["idempotency_key"], str) and IDEM_RE.fullmatch(e["idempotency_key"]), "invalid idempotency_key")
    require(e["event_type"] in EVENT_TYPES, "invalid event_type")
    require(e["phase"] in {"T0", "T1", "T2", "T3", "T4"}, "invalid phase")
    occurred = parse_time(e["occurred_at"], "occurred_at")
    recorded = parse_time(e["recorded_at"], "recorded_at")
    require(recorded >= occurred, "recorded_at precedes occurred_at")
    producer = exact_fields(e["producer"], {"component", "version"}, {"component", "version"}, "producer")
    require_string(producer["component"], "producer.component")
    require_string(producer["version"], "producer.version")
    if "task_id" in e:
        require(isinstance(e["task_id"], str) and TASK_RE.fullmatch(e["task_id"]), "invalid task_id")
    if "memory_id" in e:
        require(isinstance(e["memory_id"], str) and MEMORY_RE.fullmatch(e["memory_id"]), "invalid memory_id")
    requires_task = {
        "task_registered", "candidate_set_frozen", "retrieval_observed", "exposure_assigned",
        "exposure_observed", "behavior_reference", "outcome_observed", "cost_observed",
        "observation_window_closed",
    }
    requires_memory = {
        "memory_registered", "retrieval_observed", "exposure_assigned",
        "exposure_observed", "behavior_reference",
    }
    forbids_task = {"memory_registered"}
    forbids_memory = {
        "task_registered", "candidate_set_frozen", "outcome_observed", "cost_observed",
        "observation_window_closed", "correction",
    }
    require(e["event_type"] not in requires_task or "task_id" in e, f"{e['event_type']} requires task_id")
    require(e["event_type"] not in requires_memory or "memory_id" in e, f"{e['event_type']} requires memory_id")
    require(e["event_type"] not in forbids_task or "task_id" not in e, f"{e['event_type']} forbids task_id")
    require(e["event_type"] not in forbids_memory or "memory_id" not in e, f"{e['event_type']} forbids memory_id")
    validate_privacy(e)
    validate_payload(e)
    return e


def get_pointer(value: dict[str, Any], pointer: str) -> Any:
    current: Any = value
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        require(isinstance(current, dict) and token in current, f"correction path does not exist: {pointer}")
        current = current[token]
    return current


def validate_stream(deliveries: list[dict[str, Any]], *, require_closed: bool = True) -> dict[str, Any]:
    logical: list[dict[str, Any]] = []
    by_event: dict[str, dict[str, Any]] = {}
    by_idem: dict[str, dict[str, Any]] = {}
    retries = 0
    previous_recorded_at: datetime | None = None
    for delivery in deliveries:
        event = validate_event_shape(delivery)
        event_id = event["event_id"]
        idem = event["idempotency_key"]
        if event_id in by_event or idem in by_idem:
            prior_event = by_event.get(event_id)
            prior_idem = by_idem.get(idem)
            require(prior_event is not None and prior_idem is not None and prior_event is prior_idem, "event_id or idempotency_key reused independently")
            require(canonical(prior_event) == canonical(event), "conflicting retry reuses event identity")
            retries += 1
            continue
        recorded_at = parse_time(event["recorded_at"], f"{event_id}.recorded_at")
        require(previous_recorded_at is None or recorded_at >= previous_recorded_at, "logical event recorded_at order regressed")
        previous_recorded_at = recorded_at
        by_event[event_id] = event
        by_idem[idem] = event
        logical.append(event)

    memories: dict[str, dict[str, Any]] = {}
    tasks: dict[str, dict[str, dict[str, Any]]] = {}
    task_events: dict[str, dict[str, Any]] = {}
    candidates: dict[str, set[str]] = {}
    retrievals: dict[tuple[str, str], dict[str, Any]] = {}
    assignments: dict[str, dict[str, Any]] = {}
    shown: dict[tuple[str, str], str] = {}
    behavior: set[tuple[str, str]] = set()
    outcomes: dict[tuple[str, str], dict[str, Any]] = {}
    closures: dict[str, dict[str, Any]] = {}
    corrections = 0
    corrected_targets: set[str] = set()
    effects = 0

    for event in logical:
        kind = event["event_type"]
        task_id = event.get("task_id")
        memory_id = event.get("memory_id")
        payload = event["payload"]

        if kind == "memory_registered":
            require(memory_id not in memories, f"memory registered twice: {memory_id}")
            memories[memory_id] = event
        elif kind == "task_registered":
            require(task_id not in tasks, f"task registered twice: {task_id}")
            require(parse_time(payload["query_cutoff"], f"{task_id}.query_cutoff") <= parse_time(event["occurred_at"], f"{task_id}.occurred_at"), f"query cutoff follows task registration: {task_id}")
            require(parse_time(payload["observation_window_end"], f"{task_id}.observation_window_end") >= parse_time(event["occurred_at"], f"{task_id}.occurred_at"), f"observation window ends before task registration: {task_id}")
            tasks[task_id] = {spec["name"]: spec for spec in payload["outcome_specs"]}
            task_events[task_id] = event
        elif kind == "candidate_set_frozen":
            require(task_id in tasks, f"candidate set references unknown task: {task_id}")
            require(task_id not in candidates, f"candidate set frozen twice: {task_id}")
            unknown = set(payload["candidate_memory_ids"]) - set(memories)
            require(not unknown, f"candidate set references unregistered memories: {sorted(unknown)}")
            candidates[task_id] = set(payload["candidate_memory_ids"])
        elif kind == "retrieval_observed":
            require(task_id in candidates, f"retrieval precedes candidate set: {task_id}")
            require(memory_id in candidates[task_id], f"retrieval memory is outside candidate set: {memory_id}")
            require((task_id, memory_id) not in retrievals, f"retrieval observed twice: {task_id}/{memory_id}")
            require(payload["candidate_count"] == len(candidates[task_id]), f"candidate_count mismatch: {task_id}/{memory_id}")
            retrievals[(task_id, memory_id)] = event
        elif kind == "exposure_assigned":
            require((task_id, memory_id) in retrievals, f"assignment precedes retrieval: {task_id}/{memory_id}")
            assignment_id = payload["assignment_id"]
            require(assignment_id not in assignments, f"assignment_id reused: {assignment_id}")
            mechanism = payload["mechanism"]
            arm = payload["arm"]
            if mechanism in {"randomized", "synthetic_validation"}:
                require(payload["propensity"] is not None, "random or synthetic assignment requires propensity")
                require(arm in {"include", "withhold"}, "random or synthetic assignment requires include/withhold arm")
            elif mechanism == "natural_observation":
                require(payload["propensity"] is None and arm == "natural", "natural observation requires null propensity and natural arm")
            else:
                require(arm == "forced_include" and payload["safety_exclusion"], "safety override requires forced_include and reason")
            if tasks[task_id] and next(e for e in logical if e["event_type"] == "task_registered" and e["task_id"] == task_id)["payload"]["criticality"] == "critical":
                require(arm not in {"withhold"}, "critical task memory cannot be withheld")
            assignments[assignment_id] = event
        elif kind == "exposure_observed":
            assignment_id = payload["assignment_id"]
            require(assignment_id in assignments, f"exposure references unknown assignment: {assignment_id}")
            assignment = assignments[assignment_id]
            require((assignment["task_id"], assignment["memory_id"]) == (task_id, memory_id), "exposure and assignment join mismatch")
            expected_shown = assignment["payload"]["arm"] in {"include", "natural", "forced_include"}
            require(payload["shown"] == expected_shown, "exposure shown state conflicts with assignment arm")
            if payload["shown"]:
                require(payload["context_position"] is not None and payload["withhold_reason"] is None, "shown exposure requires position and no withhold reason")
                shown[(task_id, memory_id)] = event["event_id"]
            else:
                require(payload["context_position"] is None and isinstance(payload["withhold_reason"], str) and payload["withhold_reason"].strip(), "withheld exposure requires reason and no position")
        elif kind == "behavior_reference":
            require((task_id, memory_id) in shown, "behavior reference requires prior shown exposure")
            for evidence_id in payload["evidence_event_ids"]:
                require(evidence_id in by_event and logical.index(by_event[evidence_id]) < logical.index(event), f"behavior evidence must reference a prior event: {evidence_id}")
            require(shown[(task_id, memory_id)] in payload["evidence_event_ids"], "behavior evidence must include the exposure event")
            behavior.add((task_id, memory_id))
        elif kind == "outcome_observed":
            require(task_id in tasks, f"outcome references unknown task: {task_id}")
            require(task_id not in closures, f"outcome occurs after observation window closure: {task_id}")
            require(parse_time(event["occurred_at"], f"{event['event_id']}.occurred_at") <= parse_time(task_events[task_id]["payload"]["observation_window_end"], f"{task_id}.observation_window_end"), f"outcome occurs after preregistered observation window: {task_id}")
            name = payload["outcome_name"]
            require(name in tasks[task_id], f"outcome was not preregistered: {task_id}/{name}")
            spec = tasks[task_id][name]
            require(payload["unit"] == spec["unit"] and payload["window_days"] == spec["window_days"], f"outcome contract mismatch: {task_id}/{name}")
            require((task_id, name) not in outcomes, f"logical outcome observed twice: {task_id}/{name}")
            outcomes[(task_id, name)] = event
        elif kind == "cost_observed":
            require(task_id in tasks, f"cost references unknown task: {task_id}")
        elif kind == "observation_window_closed":
            require(task_id in tasks, f"closure references unknown task: {task_id}")
            require(task_id not in closures, f"observation window closed twice: {task_id}")
            registered_end = task_events[task_id]["payload"]["observation_window_end"]
            require(payload["window_end"] == registered_end, f"closure differs from preregistered observation window: {task_id}")
            require(parse_time(event["occurred_at"], f"{event['event_id']}.occurred_at") >= parse_time(registered_end, f"{task_id}.observation_window_end"), f"closure precedes observation window end: {task_id}")
            observed = {name for task, name in outcomes if task == task_id}
            missing = set(tasks[task_id]) - observed
            outstanding = set(payload["outstanding_outcome_names"])
            require(outstanding == missing, f"closure outstanding outcomes mismatch: {task_id}")
            if payload["censoring_reason"] == "none":
                require(not outstanding, f"uncensored closure has missing outcomes: {task_id}")
            else:
                require(bool(outstanding), f"censoring reason without outstanding outcomes: {task_id}")
            closures[task_id] = event
        elif kind == "correction":
            target_id = payload["target_event_id"]
            require(target_id in by_event and logical.index(by_event[target_id]) < logical.index(event), "correction target must be a prior logical event")
            require(by_event[target_id]["event_type"] not in {"correction", "causal_effect_estimated"}, "correction cannot target correction/effect event")
            require(target_id not in corrected_targets, "T0 permits one correction event per target")
            corrected = copy.deepcopy(by_event[target_id])
            for pointer, replacement in payload["field_corrections"].items():
                get_pointer(by_event[target_id], pointer)
                set_pointer(corrected, pointer, replacement)
            validate_event_shape(corrected)
            corrected_targets.add(target_id)
            corrections += 1
        elif kind == "causal_effect_estimated":
            require(event["phase"] == "T4", "causal_effect_estimated is prohibited before T4")
            effects += 1

    if require_closed:
        require(set(tasks) == set(closures), "every T0 task must close its observation window")

    memory_tasks: dict[str, set[str]] = {}
    for task_id, memory_id in retrievals:
        memory_tasks.setdefault(memory_id, set()).add(task_id)
    for memory_id, related_tasks in memory_tasks.items():
        if len(related_tasks) > 1:
            clusters = {task_events[task]["payload"]["dependence_cluster_id"] for task in related_tasks}
            require(len(clusters) == 1, f"shared memory tasks require one dependence cluster: {memory_id}")

    pair_levels: dict[tuple[str, str], str] = {}
    for pair, retrieval in retrievals.items():
        if retrieval["payload"]["eligible"] or retrieval["payload"]["retrieved"]:
            pair_levels[pair] = "U1"
    for pair in shown:
        pair_levels[pair] = "U2"
    for pair in behavior:
        pair_levels[pair] = "U3"
    for pair in shown:
        if any(task == pair[0] for task, _ in outcomes):
            pair_levels[pair] = "U4"
    level_counts = Counter(pair_levels.values())

    return {
        "deliveries": len(deliveries),
        "logical_events": len(logical),
        "exact_retries_collapsed": retries,
        "memory_count": len(memories),
        "task_count": len(tasks),
        "dependence_cluster_count": len({event["payload"]["dependence_cluster_id"] for event in task_events.values()}),
        "shared_memory_across_task_count": sum(len(task_ids) > 1 for task_ids in memory_tasks.values()),
        "closed_task_count": len(closures),
        "censored_task_count": sum(event["payload"]["censoring_reason"] != "none" for event in closures.values()),
        "correction_count": corrections,
        "causal_effect_event_count": effects,
        "maximum_observational_level_counts": {level: level_counts.get(level, 0) for level in ("U1", "U2", "U3", "U4")},
        "logical_event_type_counts": dict(sorted(Counter(event["event_type"] for event in logical).items())),
    }


def set_pointer(value: dict[str, Any], pointer: str, replacement: Any) -> None:
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer.lstrip("/").split("/")]
    current: Any = value
    for token in tokens[:-1]:
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    final = tokens[-1]
    if isinstance(current, list):
        current[int(final)] = replacement
    else:
        current[final] = replacement


def apply_mutations(base: list[dict[str, Any]], case: dict[str, Any]) -> list[dict[str, Any]]:
    events = copy.deepcopy(base)
    for mutation in case["mutations"]:
        operation = mutation["op"]
        event_id = mutation.get("event_id")
        matches = [index for index, event in enumerate(events) if event["event_id"] == event_id]
        if operation == "remove_event":
            require(bool(matches), f"invalid fixture mutation target: {event_id}")
            events = [event for event in events if event["event_id"] != event_id]
        elif operation in {"replace", "add"}:
            occurrence = mutation.get("occurrence", 0)
            require(occurrence < len(matches), f"invalid fixture occurrence: {event_id}/{occurrence}")
            set_pointer(events[matches[occurrence]], mutation["path"], mutation["value"])
        else:
            raise TelemetryError(f"unknown fixture mutation operation: {operation}")
    return events


def validate_invalid_cases(base: list[dict[str, Any]], cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    require(len(cases) == len({case["case_id"] for case in cases}), "invalid fixture case IDs contain duplicates")
    results: list[dict[str, str]] = []
    for case in cases:
        require(set(case) == {"case_id", "expected_error", "mutations"}, f"{case.get('case_id')}: invalid case contract")
        expected = require_string(case["expected_error"], f"{case['case_id']}.expected_error")
        try:
            validate_stream(apply_mutations(base, case))
        except TelemetryError as exc:
            message = str(exc)
            require(expected in message, f"{case['case_id']}: expected error {expected!r}, got {message!r}")
            results.append({"case_id": case["case_id"], "observed_error": message})
        else:
            raise TelemetryError(f"{case['case_id']}: invalid fixture was accepted")
    return results


def build_report() -> dict[str, Any]:
    schema = load_json(SCHEMA)
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "schema draft mismatch")
    require(schema.get("properties", {}).get("schema_version", {}).get("const") == SCHEMA_VERSION, "schema version mismatch")
    valid = load_jsonl(VALID)
    invalid = load_json(INVALID)
    valid_result = validate_stream(valid)
    invalid_results = validate_invalid_cases(valid, invalid)
    return {
        "experiment_id": "PMLAB-UTILITY-001",
        "phase": "T0",
        "status": "synthetic-schema-validation-passed",
        "schema_version": SCHEMA_VERSION,
        "hashes": {
            "schema_sha256": sha256(SCHEMA),
            "valid_deliveries_sha256": sha256(VALID),
            "invalid_cases_sha256": sha256(INVALID),
        },
        "valid_stream": valid_result,
        "invalid_cases": {
            "total": len(invalid_results),
            "rejected": len(invalid_results),
            "results": invalid_results,
        },
        "privacy": {
            "raw_content_fields_accepted": 0,
            "external_processing_events": 0,
            "synthetic_nonsensitive_only": True,
        },
        "authority": "T0 instrument integrity only; no natural capture, causal utility, randomized exposure, adaptive ranking, retention, consolidation, or architecture claim",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--check-report", action="store_true")
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check_report:
        require(REPORT.exists(), "validation report does not exist")
        require(REPORT.read_text(encoding="utf-8") == rendered, "validation report differs from deterministic recomputation")
    if args.write_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
