#!/usr/bin/env python3
"""Prepare, freeze, execute, and score PMLAB-PACK-READER-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402


BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
RUN_ID = "deepseek-v4-flash-pack-reader-v0-20260823"
RUN_DIR = BASE / "execution-deepseek-v4-flash-v0"
MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
MAX_TOKENS = 256
RUN_BUDGET_USD = 0.50
GLOBAL_BUDGET_USD = 10.0
PROMPT_VERSION = "pack-reader-v0"


SYSTEM_PROMPT = """You are a strict evidence reader. Use only the supplied evidence.
Bucket rules: <current> is authoritative for requested current facts; <supporting> may supply requested facts; <stale_conflicting> is superseded and must never replace a current or supporting value; <distractor> is unrelated.
Return every exact value atom requested by the question and cite every Rnn record that directly supports those atoms. Do not cite a locator, source alias, or record that does not directly support an answer atom. If the supplied evidence cannot answer the request, set abstain to true and return empty arrays.
Return exactly one JSON object with exactly these keys and no prose:
{"answer_atoms":["exact-value"],"citations":["R01"],"abstain":false}
Do not reveal reasoning or add any other field."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return shared.read_jsonl(path)


def records_for_case(case: dict[str, Any], corpus: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        row["local_id"]: row
        for row in corpus
        if row["group_id"] == case["group_id"] and row["language"] == case["language"]
    }


def ordered_ids(case: dict[str, Any], records: dict[str, dict[str, Any]], order_arm: str) -> list[str]:
    supplied = list(case["retrieval_order"])
    if order_arm == "O0_RETRIEVAL":
        return supplied
    if order_arm != "O1_GOVERNED":
        raise ValueError(f"unknown order arm: {order_arm}")
    priority = {"current": 0, "supporting": 1, "stale_conflicting": 2, "distractor": 3}
    return sorted(supplied, key=lambda local_id: priority[records[local_id]["bucket"]])


def serialize_evidence(
    case: dict[str, Any], records: dict[str, dict[str, Any]], format_arm: str, order_arm: str
) -> tuple[str, list[dict[str, str]]]:
    ids = ordered_ids(case, records, order_arm)
    identity: list[dict[str, str]] = []
    lines = ["EVIDENCE"]
    source_aliases: dict[str, str] = {}
    for local_id in ids:
        row = records[local_id]
        identity.append({"record_id": local_id, "text": row["text"]})
        span = f"L{row['line_start']}-L{row['line_end']}"
        if format_arm == "F0_FULL":
            locator = f"{row['source_path']}:{span}"
        elif format_arm == "F1_COMPACT":
            if row["source_path"] not in source_aliases:
                source_aliases[row["source_path"]] = f"S{len(source_aliases) + 1:02d}"
            locator = f"{source_aliases[row['source_path']]}:{span}"
        else:
            raise ValueError(f"unknown format arm: {format_arm}")
        lines.append(f"[{local_id}|{locator}] <{row['bucket']}> {row['text']}")
    if format_arm == "F1_COMPACT":
        lines.append("SOURCE DICTIONARY")
        for path, alias in source_aliases.items():
            lines.append(f"[{alias}]={path}")
    return "\n".join(lines), identity


def build_packets() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fixture_manifest = read_json(BASE / "manifest.json")
    if fixture_manifest["status"] != "fixture-and-opaque-schedule-frozen-before-runner":
        raise ValueError("fixture is not frozen before runner construction")
    cases = {row["case_id"]: row for row in load_jsonl(BASE / "cases.jsonl")}
    corpus = load_jsonl(BASE / "corpus.jsonl")
    mappings = {row["condition_id"]: row for row in load_jsonl(BASE / "internal" / "condition-map.jsonl")}
    schedule = load_jsonl(BASE / "blind" / "schedule.jsonl")
    packets: list[dict[str, Any]] = []
    identities: dict[str, list[list[dict[str, str]]]] = defaultdict(list)
    forbidden = ("F0_FULL", "F1_COMPACT", "O0_RETRIEVAL", "O1_GOVERNED", "expected_answer", "stale_atoms", "required_local_ids")
    for scheduled in schedule:
        mapping = mappings[scheduled["condition_id"]]
        if mapping["case_id"] != scheduled["case_id"]:
            raise ValueError("condition schedule mapping mismatch")
        case = cases[mapping["case_id"]]
        records = records_for_case(case, corpus)
        evidence, identity = serialize_evidence(case, records, mapping["format_arm"], mapping["order_arm"])
        user = evidence + "\n\nQUESTION\n" + case["question"]
        packet = {
            "sequence": scheduled["sequence"],
            "condition_id": scheduled["condition_id"],
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
            "serialized_utf8_bytes": len(user.encode("utf-8")),
        }
        serialized = json.dumps(packet, ensure_ascii=False)
        if any(item in serialized for item in forbidden):
            raise ValueError(f"prompt packet leaks treatment or gold name: {packet['condition_id']}")
        if user.count("QUESTION\n") != 1 or not user.startswith("EVIDENCE\n"):
            raise ValueError("prompt layout invariant failed")
        packets.append(packet)
        identities[case["case_id"]].append(sorted(identity, key=lambda row: row["record_id"]))
    identity_ok = all(len(rows) == 4 and all(row == rows[0] for row in rows[1:]) for rows in identities.values())
    audit = {
        "passed": len(packets) == 128 and len({row["condition_id"] for row in packets}) == 128 and identity_ok,
        "conditions": len(packets),
        "case_condition_counts": dict(sorted(Counter(mappings[row["condition_id"]]["case_id"] for row in packets).items())),
        "same_record_ids_and_text_across_arms": identity_ok,
        "treatment_or_gold_names_absent_from_packets": True,
        "evidence_before_single_question": True,
        "system_prompt_has_no_solved_example": True,
    }
    return packets, audit


def prepare(fixture_commit: str) -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    git("cat-file", "-e", f"{fixture_commit}^{{commit}}")
    committed_manifest = subprocess.check_output(
        ["git", "show", f"{fixture_commit}:data/lab/pmlab-pack-reader-v0/manifest.json"], cwd=ROOT
    )
    current_manifest = (BASE / "manifest.json").read_bytes()
    if committed_manifest.replace(b"\r\n", b"\n") != current_manifest.replace(b"\r\n", b"\n"):
        raise ValueError("current fixture manifest differs from the declared freeze commit")
    packets, audit = build_packets()
    if not audit["passed"]:
        raise ValueError("prompt packet audit failed")
    shared.write_jsonl(RUN_DIR / "prompt-packets.jsonl", packets)
    shared.write_json(RUN_DIR / "prompt-audit.json", audit)
    (RUN_DIR / "system-prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    files = ("prompt-packets.jsonl", "prompt-audit.json", "system-prompt.txt")
    one_attempt = sum(shared.estimated_request_cost(row["messages"], MAX_TOKENS) for row in packets)
    manifest = {
        "experiment_id": "PMLAB-PACK-READER-001",
        "run_id": RUN_ID,
        "status": "prepared-uncommitted-prompt-packet",
        "fixture_freeze_commit": fixture_commit,
        "prompt_freeze_commit": None,
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "temperature": 0,
        "thinking": "disabled",
        "max_tokens": MAX_TOKENS,
        "conditions": len(packets),
        "run_budget_usd": RUN_BUDGET_USD,
        "global_budget_usd": GLOBAL_BUDGET_USD,
        "one_attempt_preflight_usd": round(one_attempt, 8),
        "all_conditions_retry_preflight_usd": round(one_attempt * 2, 8),
        "hashes": {name: sha256(RUN_DIR / name) for name in files},
        "runner_sha256": sha256(Path(__file__)),
        "authority": "author-operated M1 synthetic reader compatibility run; not independent validation",
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    manifest = read_json(RUN_DIR / "manifest.json")
    if manifest["status"] != "prepared-uncommitted-prompt-packet":
        raise ValueError("prompt packet is not awaiting freeze")
    git("cat-file", "-e", f"{commit}^{{commit}}")
    relative_run = RUN_DIR.relative_to(ROOT).as_posix()
    for name, expected in manifest["hashes"].items():
        committed = subprocess.check_output(["git", "show", f"{commit}:{relative_run}/{name}"], cwd=ROOT)
        if hashlib.sha256(committed.replace(b"\r\n", b"\n")).hexdigest() != hashlib.sha256((RUN_DIR / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest():
            raise ValueError(f"{name} differs from prompt freeze commit")
        if sha256(RUN_DIR / name) != expected:
            raise ValueError(f"{name} differs from prepared hash")
    committed_runner = subprocess.check_output(["git", "show", f"{commit}:scripts/run_pack_reader_benchmark.py"], cwd=ROOT)
    if hashlib.sha256(committed_runner.replace(b"\r\n", b"\n")).hexdigest() != hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest():
        raise ValueError("runner differs from prompt freeze commit")
    manifest.update({"status": "frozen-prompt-awaiting-api", "prompt_freeze_commit": commit})
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def verify_frozen() -> dict[str, Any]:
    manifest = read_json(RUN_DIR / "manifest.json")
    allowed = {"frozen-prompt-awaiting-api", "raw-responses-frozen", "scored"}
    if manifest["status"] not in allowed or not manifest.get("prompt_freeze_commit"):
        raise ValueError("prompt packet is not frozen")
    for name, expected in manifest["hashes"].items():
        if sha256(RUN_DIR / name) != expected:
            raise ValueError(f"frozen input mismatch: {name}")
    fixture = read_json(BASE / "manifest.json")
    for relative, expected in fixture["hashes"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError(f"fixture mismatch: {relative}")
    return manifest


def validate_response(content: str) -> dict[str, Any]:
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) != {"answer_atoms", "citations", "abstain"}:
        raise ValueError("response differs from exact schema")
    if not isinstance(value["answer_atoms"], list) or any(not isinstance(item, str) or not item.strip() for item in value["answer_atoms"]):
        raise ValueError("invalid answer_atoms")
    if not isinstance(value["citations"], list) or any(not isinstance(item, str) or not re_fullmatch_record(item) for item in value["citations"]):
        raise ValueError("invalid citations")
    if not isinstance(value["abstain"], bool):
        raise ValueError("invalid abstain")
    return value


def re_fullmatch_record(value: str) -> bool:
    return len(value) == 3 and value[0] == "R" and value[1:].isdigit()


def preflight() -> dict[str, Any]:
    manifest = verify_frozen()
    packets = load_jsonl(RUN_DIR / "prompt-packets.jsonl")
    one = sum(shared.estimated_request_cost(row["messages"], manifest["max_tokens"]) for row in packets)
    worst = one * 2
    result = {
        "conditions": len(packets),
        "one_attempt_usd": round(one, 8),
        "all_conditions_retry_usd": round(worst, 8),
        "run_cap_usd": manifest["run_budget_usd"],
        "global_spent_before_usd": shared.ledger_total(),
        "global_cap_usd": manifest["global_budget_usd"],
        "passes": worst <= manifest["run_budget_usd"] and shared.ledger_total() + worst <= manifest["global_budget_usd"],
    }
    shared.write_json(RUN_DIR / "preflight.json", result)
    if not result["passes"]:
        raise RuntimeError("peak cache-miss preflight exceeds a frozen cap")
    return result


def call_model(key: str, messages: list[dict[str, str]], max_tokens: int, timeout: float) -> tuple[dict[str, Any], float]:
    body = json.dumps({
        "model": MODEL, "messages": messages, "thinking": {"type": "disabled"},
        "temperature": 0, "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response), (time.perf_counter() - started) * 1000


def run(env_file: Path, run_budget: float, global_budget: float, timeout: float) -> dict[str, Any]:
    if run_budget != RUN_BUDGET_USD or global_budget != GLOBAL_BUDGET_USD:
        raise ValueError("runtime caps must equal the frozen caps")
    manifest = verify_frozen()
    if manifest["status"] == "scored":
        raise ValueError("run is already scored")
    preflight()
    key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    packets = load_jsonl(RUN_DIR / "prompt-packets.jsonl")
    completed = {row["condition_id"]: row for row in load_jsonl(RUN_DIR / "responses.jsonl")}
    local_calls = load_jsonl(RUN_DIR / "calls.jsonl")
    run_spend = sum(float(row.get("conservative_cost_usd", 0)) for row in local_calls)
    new_calls = 0
    for packet in packets:
        condition_id = packet["condition_id"]
        if condition_id in completed:
            continue
        final: dict[str, Any] | None = None
        errors: list[str] = []
        for attempt in (1, 2):
            next_peak = shared.estimated_request_cost(packet["messages"], manifest["max_tokens"])
            if run_spend + next_peak > run_budget or shared.ledger_total() + next_peak > global_budget:
                raise RuntimeError("hard budget gate would be exceeded")
            try:
                raw, latency_ms = call_model(key, packet["messages"], manifest["max_tokens"], timeout)
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                errors.append(f"attempt {attempt} transport: {type(exc).__name__}: {exc}")
                shared.append_jsonl(RUN_DIR / "errors.jsonl", {"condition_id": condition_id, "attempt": attempt, "kind": "transport", "error": str(exc)})
                if attempt == 2:
                    final = {"condition_id": condition_id, "schema_valid": False, "value": None, "errors": errors}
                continue
            usage = raw.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            cost = shared.conservative_cost(prompt_tokens, completion_tokens)
            ledger = {
                "at": shared.utc_now(), "run_id": RUN_ID, "condition_id": condition_id, "attempt": attempt,
                "model": raw.get("model", MODEL), "response_id": raw.get("id", ""),
                "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                "conservative_cost_usd": round(cost, 8),
                "pricing_basis": "all input charged at configured peak cache-miss rate",
            }
            shared.append_jsonl(LEDGER, ledger)
            shared.append_jsonl(RUN_DIR / "calls.jsonl", {**ledger, "latency_ms": round(latency_ms, 2)})
            run_spend += cost
            new_calls += 1
            content = ((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            shared.append_jsonl(RUN_DIR / "raw-responses.jsonl", {
                "condition_id": condition_id, "attempt": attempt, "response_id": raw.get("id", ""), "content": content,
            })
            try:
                value = validate_response(content)
            except (ValueError, json.JSONDecodeError) as exc:
                errors.append(f"attempt {attempt} schema: {type(exc).__name__}: {exc}")
                shared.append_jsonl(RUN_DIR / "errors.jsonl", {"condition_id": condition_id, "attempt": attempt, "kind": "schema", "error": str(exc)})
                if attempt == 2:
                    final = {"condition_id": condition_id, "schema_valid": False, "value": None, "errors": errors}
                continue
            final = {"condition_id": condition_id, "schema_valid": True, "value": value, "errors": errors}
            break
        if final is None:
            raise RuntimeError(f"condition did not produce a final record: {condition_id}")
        shared.append_jsonl(RUN_DIR / "responses.jsonl", final)
        completed[condition_id] = final
        if len(completed) % 10 == 0 or len(completed) == len(packets):
            print(json.dumps({"completed": len(completed), "conditions": len(packets), "new_http_calls": new_calls, "run_spend_usd": round(run_spend, 8)}), flush=True)
    if len(completed) != len(packets):
        raise RuntimeError("not all conditions have a terminal response")
    raw_files = ("calls.jsonl", "raw-responses.jsonl", "responses.jsonl")
    manifest.update({
        "status": "raw-responses-frozen", "terminal_responses": len(completed),
        "http_calls": len(load_jsonl(RUN_DIR / "calls.jsonl")), "run_cost_usd": round(run_spend, 8),
        "raw_hashes": {name: sha256(RUN_DIR / name) for name in raw_files},
    })
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "terminal_responses": len(completed), "http_calls": manifest["http_calls"], "run_cost_usd": manifest["run_cost_usd"], "global_cost_usd": shared.ledger_total()}


def normalized_set(values: list[str]) -> set[str]:
    return {unicodedata.normalize("NFC", value.strip()) for value in values}


def safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def score() -> dict[str, Any]:
    manifest = verify_frozen()
    if manifest["status"] != "raw-responses-frozen":
        raise ValueError("raw responses must freeze before gold is joined")
    for name, expected in manifest["raw_hashes"].items():
        if sha256(RUN_DIR / name) != expected:
            raise ValueError(f"raw response mismatch: {name}")
    responses = {row["condition_id"]: row for row in load_jsonl(RUN_DIR / "responses.jsonl")}
    mappings = {row["condition_id"]: row for row in load_jsonl(BASE / "internal" / "condition-map.jsonl")}
    gold = {row["case_id"]: row for row in load_jsonl(BASE / "internal" / "gold.jsonl")}
    cases = {row["case_id"]: row for row in load_jsonl(BASE / "cases.jsonl")}
    scored = []
    for condition_id, mapping in mappings.items():
        response = responses[condition_id]
        truth = gold[mapping["case_id"]]
        case = cases[mapping["case_id"]]
        value = response["value"] if response["schema_valid"] else {"answer_atoms": [], "citations": [], "abstain": False}
        answer = normalized_set(value["answer_atoms"])
        citations = normalized_set(value["citations"])
        expected_answer = normalized_set(truth["answer_atoms"])
        expected_citations = normalized_set(truth["required_local_ids"])
        valid_ids = set(case["all_local_ids"])
        stale = normalized_set(truth["stale_atoms"])
        scored.append({
            "condition_id": condition_id, "case_id": mapping["case_id"], "group_id": truth["group_id"], "language": truth["language"],
            "format_arm": mapping["format_arm"], "order_arm": mapping["order_arm"],
            "schema_valid": response["schema_valid"], "answer_atoms": sorted(answer), "citations": sorted(citations), "abstain": value["abstain"],
            "exact_answer": answer == expected_answer,
            "answer_true_positive": len(answer & expected_answer), "answer_predicted": len(answer), "answer_required": len(expected_answer),
            "exact_required_citations": citations == expected_citations,
            "citation_true_positive": len(citations & expected_citations), "citation_predicted": len(citations), "citation_required": len(expected_citations),
            "unresolved_citations": sorted(citations - valid_ids), "stale_atoms_used": sorted(answer & stale),
            "conflict_resolved": answer == expected_answer and not (answer & stale),
            "inappropriate_abstention": bool(value["abstain"]),
        })
    shared.write_jsonl(RUN_DIR / "scored.jsonl", scored)
    arms = []
    arm_rows: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for format_arm in ("F0_FULL", "F1_COMPACT"):
        for order_arm in ("O0_RETRIEVAL", "O1_GOVERNED"):
            rows = [row for row in scored if row["format_arm"] == format_arm and row["order_arm"] == order_arm]
            arm_rows[(format_arm, order_arm)] = rows
            by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                by_group[row["group_id"]].append(row)
            group_exact = sum(len(group) == 2 and all(row["exact_answer"] for row in group) for group in by_group.values())
            arms.append({
                "format_arm": format_arm, "order_arm": order_arm, "cases": len(rows), "groups": len(by_group),
                "schema_valid_rate": safe_ratio(sum(row["schema_valid"] for row in rows), len(rows)),
                "case_exact_answer_accuracy": safe_ratio(sum(row["exact_answer"] for row in rows), len(rows)),
                "group_exact_answer_count": group_exact, "group_exact_answer_accuracy": safe_ratio(group_exact, len(by_group)),
                "answer_recall": safe_ratio(sum(row["answer_true_positive"] for row in rows), sum(row["answer_required"] for row in rows)),
                "answer_precision": safe_ratio(sum(row["answer_true_positive"] for row in rows), sum(row["answer_predicted"] for row in rows)),
                "exact_required_citation_accuracy": safe_ratio(sum(row["exact_required_citations"] for row in rows), len(rows)),
                "required_citation_recall": safe_ratio(sum(row["citation_true_positive"] for row in rows), sum(row["citation_required"] for row in rows)),
                "unresolved_citation_rate": safe_ratio(sum(len(row["unresolved_citations"]) for row in rows), sum(row["citation_predicted"] for row in rows)),
                "stale_atom_use_rate": safe_ratio(sum(bool(row["stale_atoms_used"]) for row in rows), len(rows)),
                "conflict_resolution_accuracy": safe_ratio(sum(row["conflict_resolved"] for row in rows), len(rows)),
                "inappropriate_abstention_rate": safe_ratio(sum(row["inappropriate_abstention"] for row in rows), len(rows)),
            })
    arm = {(row["format_arm"], row["order_arm"]): row for row in arms}
    gate_details: list[dict[str, Any]] = []
    gate_details.append({"gate": "schema_validity", "passed": all(row["schema_valid_rate"] >= 0.95 for row in arms)})
    gate_details.append({"gate": "unresolved_citations", "passed": all(row["unresolved_citation_rate"] == 0 for row in arms)})
    gate_details.append({"gate": "no_stale_atoms", "passed": all(row["stale_atom_use_rate"] == 0 for row in arms)})
    gate_details.append({
        "gate": "absolute_reader_competence",
        "passed": all(
            row["group_exact_answer_count"] >= 14
            and row["required_citation_recall"] >= 0.95
            and row["inappropriate_abstention_rate"] <= 0.05
            for row in arms
        ),
    })
    format_passes = []
    for order_arm in ("O0_RETRIEVAL", "O1_GOVERNED"):
        full, compact = arm[("F0_FULL", order_arm)], arm[("F1_COMPACT", order_arm)]
        format_passes.append(compact["group_exact_answer_count"] >= full["group_exact_answer_count"] - 1 and compact["required_citation_recall"] - full["required_citation_recall"] >= -0.05)
    gate_details.append({"gate": "compact_compatibility", "passed": all(format_passes), "within_order_passes": format_passes})
    order_passes = []
    for format_arm in ("F0_FULL", "F1_COMPACT"):
        retrieval, governed = arm[(format_arm, "O0_RETRIEVAL")], arm[(format_arm, "O1_GOVERNED")]
        order_passes.append(governed["stale_atom_use_rate"] <= retrieval["stale_atom_use_rate"] and governed["group_exact_answer_accuracy"] - retrieval["group_exact_answer_accuracy"] >= -0.05)
    gate_details.append({"gate": "governed_order_compatibility", "passed": all(order_passes), "within_format_passes": order_passes})
    prompt_audit = read_json(RUN_DIR / "prompt-audit.json")
    gate_details.append({"gate": "identical_evidence", "passed": prompt_audit["same_record_ids_and_text_across_arms"]})
    summary = {
        "experiment_id": "PMLAB-PACK-READER-001", "reader": MODEL,
        "status": "single-family-synthetic-reader-scored", "arms": arms, "gates": gate_details,
        "all_compatibility_gates_passed": all(row["passed"] for row in gate_details),
        "groups_are_units": True,
        "claim_boundary": "Author-built synthetic fixture and one author-operated reader family; no retrieval, natural-history, cross-family, or architecture claim.",
        "run_cost_usd": manifest["run_cost_usd"],
    }
    shared.write_json(RUN_DIR / "summary.json", summary)
    manifest.update({"status": "scored", "scored_sha256": sha256(RUN_DIR / "scored.jsonl"), "summary_sha256": sha256(RUN_DIR / "summary.json")})
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--fixture-commit", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--commit", required=True)
    sub.add_parser("preflight")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    run_parser.add_argument("--run-budget-usd", type=float, default=RUN_BUDGET_USD)
    run_parser.add_argument("--global-budget-usd", type=float, default=GLOBAL_BUDGET_USD)
    run_parser.add_argument("--timeout", type=float, default=120.0)
    sub.add_parser("score")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.fixture_commit)
    elif args.command == "freeze":
        result = freeze(args.commit)
    elif args.command == "preflight":
        result = preflight()
    elif args.command == "run":
        result = run(args.env_file, args.run_budget_usd, args.global_budget_usd, args.timeout)
    else:
        result = score()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
