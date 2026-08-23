#!/usr/bin/env python3
"""Audit the frozen Foundation delayed-reveal fixture at leakage levels L0-L4."""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-foundation-v0" / "delayed-reveal-v0"
PREFIX_DIR = BASE / "prefix-freeze-v0"
REVEAL_DIR = BASE / "reveal-freeze-v0"
PREFIXES = PREFIX_DIR / "prefixes.jsonl"
ACCESS = PREFIX_DIR / "write-side-access-receipt.json"
PREFIX_MANIFEST = PREFIX_DIR / "freeze-manifest.json"
REVEALS = REVEAL_DIR / "reader" / "reveals.jsonl"
GOLD = REVEAL_DIR / "gold" / "gold.jsonl"
STATES = REVEAL_DIR / "gold" / "answer-state-catalog.json"
SCHEDULE = REVEAL_DIR / "schedule.jsonl"
MUTATIONS = REVEAL_DIR / "invalid-mutations.json"
REVEAL_MANIFEST = REVEAL_DIR / "freeze-manifest.json"
DEFAULT_REPORT = REVEAL_DIR / "leakage-audit-report.json"
PREFIX_FREEZE_COMMIT = "f9980825b0217cddce7f1f4bd84a0cff715a4ad8"
REVEAL_FREEZE_COMMIT = "2bf98136eff5a06fe0055b4d0e21a5ff45d1e994"

PREFIX_FIELDS = {
    "schema_version", "prefix_id", "canonical_contract_version", "source_commit",
    "source_path", "source_sha256", "canonical_event_ids", "accepted_event_count",
    "accepted_payload_utf8_bytes", "prefix_cutoff", "frozen_at", "producer",
    "write_side_allowed_inputs", "write_side_forbidden_input_classes", "access_receipt_path",
}
REVEAL_FIELDS = {
    "schema_version", "reveal_id", "counterfactual_set_id", "prefix_id",
    "prefix_sha256", "gold_id", "authored_at", "available_at", "query_cutoff",
    "query", "language", "task_family", "reader_visible_fields",
}
GOLD_FIELDS = {
    "schema_version", "gold_id", "reveal_id", "required_event_ids",
    "forbidden_event_ids", "supported_answer_state", "supported_action",
    "consequence_weight", "abstention_allowed",
}
PREFIX_ID_RE = re.compile(r"^PFX-[A-F0-9]{16}$")
REVEAL_ID_RE = re.compile(r"^RVL-[A-F0-9]{16}$")
GOLD_ID_RE = re.compile(r"^GOLD-[A-F0-9]{12}$")
STATE_ID_RE = re.compile(r"^STATE-[A-F0-9]{12}$")
CF_ID_RE = re.compile(r"^CF-[A-F0-9]{12}$")
EVENT_ID_RE = re.compile(r"^EV-[A-F0-9]{16}$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
FORBIDDEN_PREFIX_FIELDS = {
    "query", "task", "task_family", "answer", "answer_atoms", "gold", "gold_id",
    "required_event_ids", "forbidden_event_ids", "consequence_weight", "reader_prompt",
    "scorer", "reveal_id", "supported_answer_state", "semantic_importance",
}


class LeakageError(ValueError):
    """A deterministic delayed-reveal contract failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LeakageError(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def exact_fields(value: Any, fields: set[str], name: str, error: str | None = None) -> dict[str, Any]:
    require(isinstance(value, dict), f"{name} must be object")
    missing = fields - set(value)
    extra = set(value) - fields
    require(not missing, f"{name} missing fields: {sorted(missing)}")
    require(not extra, error or f"{name} unexpected fields: {sorted(extra)}")
    return value


def parse_time(value: Any, name: str) -> datetime:
    require(isinstance(value, str), f"{name} time format")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LeakageError(f"{name} time format") from exc


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout


def verify_manifest(manifest: dict[str, Any], commit: str) -> None:
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        require(path.is_file(), f"frozen artifact missing: {artifact['path']}")
        raw = path.read_bytes()
        require(len(raw) == artifact["bytes"], f"frozen byte length changed: {artifact['path']}")
        require(sha256(raw) == artifact["sha256"], f"frozen hash changed: {artifact['path']}")
        require(git_bytes(commit, artifact["path"]) == raw, f"frozen commit bytes differ: {artifact['path']}")


def walk_prefix_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            require(key not in FORBIDDEN_PREFIX_FIELDS, f"prefix forbidden field: {key}")
            walk_prefix_fields(child)
    elif isinstance(value, list):
        for child in value:
            walk_prefix_fields(child)


def validate_prefixes(prefixes: list[dict[str, Any]], access: dict[str, Any]) -> None:
    require(len(prefixes) == 1, "construction requires one prefix")
    prefix = prefixes[0]
    exact_fields(prefix, PREFIX_FIELDS, "prefix", "prefix forbidden field or unexpected field")
    walk_prefix_fields(prefix)
    require(prefix["schema_version"] == "foundation-history-prefix-v0.1", "prefix schema version")
    require(isinstance(prefix["prefix_id"], str) and PREFIX_ID_RE.fullmatch(prefix["prefix_id"]) is not None, "prefix id format")
    require(isinstance(prefix["source_commit"], str) and re.fullmatch(r"[a-f0-9]{40}", prefix["source_commit"]) is not None, "source commit format")
    require(isinstance(prefix["source_sha256"], str) and HASH_RE.fullmatch(prefix["source_sha256"]) is not None, "source hash format")
    require(isinstance(prefix["canonical_event_ids"], list) and len(prefix["canonical_event_ids"]) == len(set(prefix["canonical_event_ids"])), "prefix event IDs")
    require(all(isinstance(x, str) and EVENT_ID_RE.fullmatch(x) is not None for x in prefix["canonical_event_ids"]), "prefix event id format")
    require(prefix["accepted_event_count"] == len(prefix["canonical_event_ids"]), "accepted event count")
    require(parse_time(prefix["frozen_at"], "prefix frozen") > parse_time(prefix["prefix_cutoff"], "prefix cutoff"), "prefix frozen before cutoff")
    allowed = prefix["write_side_allowed_inputs"]
    require(isinstance(allowed, list) and allowed and len(allowed) == len(set(allowed)), "allowed inputs")
    require(prefix["write_side_forbidden_input_classes"] == ["backend_output", "gold", "query", "reader_prompt", "reveal", "scorer"], "forbidden input classes")

    source = git_bytes(prefix["source_commit"], prefix["source_path"])
    require(sha256(source) == prefix["source_sha256"], "prefix source hash mismatch")
    events = [json.loads(line) for line in source.decode("utf-8").splitlines() if line.strip()]
    by_id = {event["event_id"]: event for event in events}
    require(list(by_id) == prefix["canonical_event_ids"], "prefix ordered event IDs")
    total_bytes = sum(by_id[event_id]["evidence"]["byte_length"] for event_id in prefix["canonical_event_ids"])
    require(total_bytes == prefix["accepted_payload_utf8_bytes"], "prefix accepted bytes")

    expected_access_fields = {
        "schema_version", "phase", "prefix_id", "source_commit", "source_sha256",
        "allowed_read_paths", "observed_read_paths", "forbidden_input_classes",
        "reveal_artifacts_present", "gold_artifacts_present", "model_api_used",
        "api_cost_usd", "attestation",
    }
    exact_fields(access, expected_access_fields, "access receipt")
    require(access["phase"] == "prefix_only_before_reveal_authorship", "access phase")
    require(access["prefix_id"] == prefix["prefix_id"], "access prefix join")
    require(access["source_commit"] == prefix["source_commit"] and access["source_sha256"] == prefix["source_sha256"], "access source join")
    require(access["allowed_read_paths"] == allowed, "access allowlist mismatch")
    require(set(access["observed_read_paths"]) <= set(allowed), "observed read outside allowlist")
    require(access["reveal_artifacts_present"] is False and access["gold_artifacts_present"] is False, "later artifacts present during prefix phase")
    require(access["model_api_used"] is False and access["api_cost_usd"] == 0, "prefix API use")


def validate_reveals(reveals: list[dict[str, Any]], prefixes: list[dict[str, Any]]) -> None:
    prefix = prefixes[0]
    prefix_hash = sha256(PREFIXES.read_bytes())
    for reveal in reveals:
        exact_fields(reveal, REVEAL_FIELDS, "reveal")
        require(reveal["schema_version"] == "foundation-task-reveal-v0.1", "reveal schema version")
        require(isinstance(reveal["reveal_id"], str) and REVEAL_ID_RE.fullmatch(reveal["reveal_id"]) is not None, "reveal id format")
        require(isinstance(reveal["counterfactual_set_id"], str) and CF_ID_RE.fullmatch(reveal["counterfactual_set_id"]) is not None, "counterfactual id format")
        require(isinstance(reveal["gold_id"], str) and GOLD_ID_RE.fullmatch(reveal["gold_id"]) is not None, "gold id format")
        require(reveal["prefix_id"] == prefix["prefix_id"], "reveal prefix join")
        require(reveal["prefix_sha256"] == prefix_hash, "prefix hash mismatch")
        authored = parse_time(reveal["authored_at"], "reveal authored")
        available = parse_time(reveal["available_at"], "reveal available")
        cutoff = parse_time(prefix["prefix_cutoff"], "prefix cutoff")
        frozen = parse_time(prefix["frozen_at"], "prefix frozen")
        require(authored > frozen, "reveal authored before prefix freeze")
        require(available > cutoff, "reveal not delayed")
        require(available >= authored, "reveal available before authored")
        require(parse_time(reveal["query_cutoff"], "query cutoff") >= available, "query cutoff before reveal")
        require(isinstance(reveal["query"], str) and len(reveal["query"].strip()) >= 3, "query text")
        require(reveal["language"] in {"pl", "en", "mixed", "other"}, "reveal language")
        require(reveal["task_family"] in {"current_state", "historical_as_of", "change_reconstruction", "noise_control"}, "task family")
        require(reveal["reader_visible_fields"] == ["reveal_id", "query", "language"], "reader visible fields")
    ids = [row["reveal_id"] for row in reveals]
    require(len(ids) == len(set(ids)), "duplicate reveal id")
    require(len({row["gold_id"] for row in reveals}) == len(reveals), "duplicate reveal gold id")


def validate_gold(gold: list[dict[str, Any]], reveals: list[dict[str, Any]], states: dict[str, Any]) -> None:
    for row in gold:
        exact_fields(row, GOLD_FIELDS, "gold")
        require(row["schema_version"] == "foundation-reveal-gold-v0.1", "gold schema version")
        require(isinstance(row["gold_id"], str) and GOLD_ID_RE.fullmatch(row["gold_id"]) is not None, "gold id format")
        require(isinstance(row["reveal_id"], str) and REVEAL_ID_RE.fullmatch(row["reveal_id"]) is not None, "gold reveal id format")
        require(isinstance(row["supported_answer_state"], str) and STATE_ID_RE.fullmatch(row["supported_answer_state"]) is not None, "answer state format")
        for key in ("required_event_ids", "forbidden_event_ids"):
            require(isinstance(row[key], list) and len(row[key]) == len(set(row[key])), f"{key} unique list")
            require(all(isinstance(x, str) and EVENT_ID_RE.fullmatch(x) is not None for x in row[key]), f"{key} format")
        require(bool(row["required_event_ids"]), "required evidence empty")
        require(not set(row["required_event_ids"]) & set(row["forbidden_event_ids"]), "required and forbidden overlap")
        require(row["supported_action"] in {"answer_supported", "answer_with_change_history", "abstain"}, "supported action")
        require(isinstance(row["consequence_weight"], int) and 1 <= row["consequence_weight"] <= 5, "consequence weight")
        require(isinstance(row["abstention_allowed"], bool), "abstention flag")
    reveal_pairs = {(row["reveal_id"], row["gold_id"]) for row in reveals}
    gold_pairs = {(row["reveal_id"], row["gold_id"]) for row in gold}
    require(reveal_pairs == gold_pairs, "reveal gold join mismatch")
    require(len(gold_pairs) == len(gold), "duplicate gold join")

    require(states.get("reader_visible") is False, "state catalog reader visible")
    state_rows = states.get("states")
    require(isinstance(state_rows, list) and state_rows, "state catalog")
    state_ids = [row.get("state_id") for row in state_rows]
    require(len(state_ids) == len(set(state_ids)) and all(isinstance(x, str) and STATE_ID_RE.fullmatch(x) is not None for x in state_ids), "state catalog ids")
    require(set(state_ids) == {row["supported_answer_state"] for row in gold}, "state catalog join")
    require(all(isinstance(row.get("answer_atoms"), list) and row["answer_atoms"] for row in state_rows), "state answer atoms")


def validate_counterfactual_fork(reveals: list[dict[str, Any]], gold: list[dict[str, Any]]) -> None:
    require(len(reveals) >= 3, "counterfactual fork requires at least three reveals")
    require(len({row["counterfactual_set_id"] for row in reveals}) == 1, "counterfactual set mismatch")
    require(len({(row["prefix_id"], row["prefix_sha256"]) for row in reveals}) == 1, "counterfactual prefix bytes differ")
    require(len({row["task_family"] for row in reveals}) >= 3, "counterfactual task families insufficient")
    require(len({row["supported_answer_state"] for row in gold}) >= 2, "counterfactual answers not incompatible")
    require(len({tuple(row["required_event_ids"]) for row in gold}) >= 2, "counterfactual evidence sets do not differ")


def validate_schedule(schedule: list[dict[str, Any]], reveals: list[dict[str, Any]]) -> None:
    require(len(schedule) == len(reveals), "schedule row count")
    by_id = {row["reveal_id"]: row for row in reveals}
    require(len(by_id) == len(reveals), "duplicate reveal id")
    for row in schedule:
        require(set(row) == {"available_at", "gold_access_for_reader", "prefix_id", "reader_surface", "reveal_id"}, "schedule fields")
        require(row["reveal_id"] in by_id, "schedule reveal join")
        reveal = by_id[row["reveal_id"]]
        require(row["available_at"] == reveal["available_at"] and row["prefix_id"] == reveal["prefix_id"], "schedule value join")
        require(row["gold_access_for_reader"] is False, "reader gold access")
        require(row["reader_surface"] == "reveal_id_query_language_only", "reader schedule surface")


def pointer_parent(value: Any, pointer: str) -> tuple[Any, str]:
    require(pointer.startswith("/"), "mutation path")
    parts = pointer[1:].split("/")
    parent = value
    for part in parts[:-1]:
        require(isinstance(parent, dict) and part in parent, "mutation path missing")
        parent = parent[part]
    return parent, parts[-1]


def mutate(dataset: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dataset)
    target = result[case["target"]]
    for change in case["mutations"]:
        operation = change["op"]
        if case["target"] == "access":
            item = target
        else:
            id_field = {"prefixes": "prefix_id", "reveals": "reveal_id", "gold": "gold_id"}[case["target"]]
            item = next((row for row in target if row[id_field] == change["id"]), None)
            require(item is not None, "mutation target missing")
        if operation in {"add", "replace"}:
            parent, key = pointer_parent(item, change["path"])
            require(isinstance(parent, dict), "mutation parent")
            if operation == "replace":
                require(key in parent, "mutation replace path missing")
            parent[key] = change["value"]
        elif operation == "append":
            parent, key = pointer_parent(item, change["path"])
            require(isinstance(parent, dict) and isinstance(parent.get(key), list), "mutation append path")
            parent[key].append(change["value"])
        elif operation == "remove":
            target.remove(item)
        else:
            raise LeakageError(f"unsupported mutation: {operation}")
    return result


def validate_all(dataset: dict[str, Any]) -> None:
    validate_prefixes(dataset["prefixes"], dataset["access"])
    validate_reveals(dataset["reveals"], dataset["prefixes"])
    validate_counterfactual_fork(dataset["reveals"], dataset["gold"])
    validate_gold(dataset["gold"], dataset["reveals"], dataset["states"])
    validate_schedule(dataset["schedule"], dataset["reveals"])


def lexical_metrics(prefix_text: str, queries: list[str]) -> list[dict[str, Any]]:
    prefix_tokens = set(re.findall(r"[^\W_]+", prefix_text.casefold()))
    rows = []
    for index, query in enumerate(queries, start=1):
        query_tokens = set(re.findall(r"[^\W_]+", query.casefold()))
        rows.append({
            "reveal_index": index,
            "token_jaccard": len(prefix_tokens & query_tokens) / len(prefix_tokens | query_tokens),
            "sequence_ratio": difflib.SequenceMatcher(None, prefix_text.casefold(), query.casefold()).ratio(),
            "decision_use": "descriptive_only_not_leakage_verdict",
        })
    return rows


def run(report_path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    prefix_manifest = load_json(PREFIX_MANIFEST)
    reveal_manifest = load_json(REVEAL_MANIFEST)
    require(prefix_manifest["reveal_content_authored"] is False and prefix_manifest["gold_content_authored"] is False, "prefix manifest says later artifacts existed")
    require(reveal_manifest["prefix_freeze_commit"] == PREFIX_FREEZE_COMMIT, "prefix freeze commit mismatch")
    verify_manifest(prefix_manifest, PREFIX_FREEZE_COMMIT)
    verify_manifest(reveal_manifest, REVEAL_FREEZE_COMMIT)
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", PREFIX_FREEZE_COMMIT, REVEAL_FREEZE_COMMIT], cwd=ROOT).returncode == 0
    require(ancestor, "prefix commit is not ancestor of reveal commit")
    later_tree = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", PREFIX_FREEZE_COMMIT, "--", "data/lab/pmlab-foundation-v0/delayed-reveal-v0/reveal-freeze-v0"],
        cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE,
    ).stdout.strip()
    require(not later_tree, "prefix freeze commit contains reveal or gold")

    dataset = {
        "prefixes": load_jsonl(PREFIXES), "access": load_json(ACCESS),
        "reveals": load_jsonl(REVEALS), "gold": load_jsonl(GOLD),
        "states": load_json(STATES), "schedule": load_jsonl(SCHEDULE),
    }
    validate_all(dataset)
    invalid = load_json(MUTATIONS)["cases"]
    mutation_results = []
    for case in invalid:
        try:
            validate_all(mutate(dataset, case))
        except LeakageError as exc:
            error = str(exc)
            require(case["expected_error"].lower() in error.lower(), f"{case['case_id']} wrong error: {error}")
            mutation_results.append({"case_id": case["case_id"], "rejected": True, "error": error})
        else:
            raise LeakageError(f"{case['case_id']} was accepted")

    source = git_bytes(dataset["prefixes"][0]["source_commit"], dataset["prefixes"][0]["source_path"]).decode("utf-8")
    prefix_text = " ".join(json.loads(line)["evidence"]["source_locator"] for line in source.splitlines() if line.strip())
    metrics = lexical_metrics(prefix_text, [row["query"] for row in dataset["reveals"]])
    report = {
        "schema_version": "foundation-delayed-reveal-leakage-audit-v0.1",
        "contract_id": "PMLAB-FOUNDATION-REVEAL-001",
        "status": "passed-authored-L0-L4-construction",
        "prefix_freeze_commit": PREFIX_FREEZE_COMMIT,
        "reveal_freeze_commit": REVEAL_FREEZE_COMMIT,
        "model_api_used": False,
        "api_cost_usd": 0,
        "independent_semantic_review_L5": False,
        "levels": {
            "L0_BYTE_FIELD": {"passed": True, "evidence": "exact frozen bytes, schemas, opaque IDs, forbidden-field checks"},
            "L1_LEXICAL": {"passed": None, "evidence": "descriptive metrics only", "metrics": metrics},
            "L2_PROCESS_ACCESS": {"passed": True, "evidence": "observed reads are a subset of prefix-only allowlist; later tree absent"},
            "L3_COUNTERFACTUAL_FORK": {"passed": True, "evidence": "one identical prefix, three task families, three answer states, three required-evidence sets"},
            "L4_REPRODUCIBLE_BUILD": {"passed": True, "evidence": "ordered event IDs and payload bytes reconstructed from prefix source commit without reveal tree"},
            "L5_INDEPENDENT_SEMANTIC": {"passed": False, "evidence": "not performed"},
        },
        "counts": {"prefixes": 1, "reveals": len(dataset["reveals"]), "gold_rows": len(dataset["gold"]), "invalid_mutations": len(mutation_results)},
        "mutation_results": mutation_results,
        "claim_limit": "Same-author mechanical L0-L4 construction only; semantic independence, author blindness, and memory quality are not established.",
        "parent_execution_authorized": False,
        "next_gate": "independent blinded L5 semantic attack and unseen second-author prefix/reveal fork",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = run(args.report)
    print(json.dumps({"status": report["status"], "levels": {k: v["passed"] for k, v in report["levels"].items()}, "invalid_mutations": report["counts"]["invalid_mutations"]}, indent=2))


if __name__ == "__main__":
    main()
