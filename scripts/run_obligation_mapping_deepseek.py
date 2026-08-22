#!/usr/bin/env python3
"""Freeze, run, and score an optional DeepSeek PMLAB-MAP construction arm."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402


MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
PROMPT_VERSION = "pmlab-map-deepseek-v0"
ADAPTER_VERSION = "pmlab-map-deepseek-adapter-v1"
CORPUS_FREEZE_COMMIT = "4b6c47e"
PROMPT_FREEZE_COMMIT = "6a288f6"
RUN_ID = "pmlab-map-deepseek-v1"
RUN_DIR = ROOT / "data" / "lab" / "pmlab-obligation-mapping-deepseek-v1"
CORPUS_DIR = ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0"
GLOBAL_LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
OPERATORS = {
    "SELECT", "FILTER", "PROJECT", "AGGREGATE", "GROUP", "SUPERLATIVE", "COMPARATIVE",
    "UNION", "INTERSECTION", "DIFFERENCE", "SORT", "BOOLEAN", "ARITHMETIC",
}
STATUSES = {"resolved", "ambiguous", "unauthorized", "unsupported_structure"}
CERTIFICATES = {"applicable", "ambiguous", "inapplicable", "derived", "explicit-negative", "requires-complete-scope"}


SYSTEM_PROMPT = """You are a conservative semantic parser for a local-memory benchmark.
Return one valid JSON object and no prose. Parse every supplied query independently.
Do not infer facts or answer the query. Produce only its required computation graph and grounded scope.
Never force an entity, predicate, time, authorization, or certificate when it is ambiguous, NIL, denied, or unsupported.

Output exactly:
{"results":[{"query_id":"exact id","query_status":"resolved|ambiguous|unauthorized|unsupported_structure","nodes":[{"obligation_id":"O1","operator":"allowed operator","span_text":"exact substring of raw_query","depends":[],"entity":"grounding string","predicate":"exact predicate id or null","namespaces":["exact ids"],"time":"canonical time string","authorization":"allowed|denied|inherit:O1[,O2]","certificate":"applicable|ambiguous|inapplicable|derived|explicit-negative|requires-complete-scope"}]}]}

Rules:
- One node is one independently answerable facet or derived computation.
- Node IDs are O1, O2, ... in dependency order; dependencies refer only backward.
- Computation operators are SELECT, FILTER, PROJECT, AGGREGATE, GROUP, SUPERLATIVE, COMPARATIVE, UNION, INTERSECTION, DIFFERENCE, SORT, BOOLEAN, ARITHMETIC.
- Entity grounding uses an exact catalog id, type:<type>, ref:O1, refs:O1,O2, id|id for a relation requiring two grounded entities, ambiguous:id,id, or nil:<mention>.
- A derived computation normally has predicate null, namespaces [], entity ref:/refs:, inherited time/authorization, and certificate derived.
- Time, authorization, and completeness are scope annotations, never computation operators.
- Explicit proposition-level falsity uses explicit-negative. Collection-bounded absence uses requires-complete-scope, never explicit-negative.
- Ambiguous/NIL cases use query_status ambiguous and no applicable certificate. Denied private data uses unauthorized. Unsupported counterfactual/future conditionals use unsupported_structure and nodes [].
- Preserve all coordinated facets even if they use the same entity.
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return shared.read_jsonl(path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    shared.append_jsonl(path, value)


def prepare() -> dict[str, Any]:
    existing = [] if not RUN_DIR.exists() else [path for path in RUN_DIR.iterdir() if path.name != "README.md"]
    if existing:
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    model_cases = read_jsonl(CORPUS_DIR / "model-cases.jsonl")
    jobs = [
        {
            "query_id": row["query_id"],
            "language": row["language"],
            "raw_query": row["raw_query"],
            "reference_clock": row["reference_clock"],
            "schema_version": row["schema_version"],
            "entity_catalog_version": row["entity_catalog_version"],
        }
        for row in model_cases
    ]
    shared.write_jsonl(RUN_DIR / "jobs.jsonl", jobs)
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT, encoding="utf-8", newline="\n")
    manifest = {
        "experiment": "PMLAB-MAP-001-optional-model-construction",
        "status": "frozen-input",
        "created_at": utc_now(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "prompt_freeze_commit": PROMPT_FREEZE_COMMIT,
        "corpus_freeze_commit": CORPUS_FREEZE_COMMIT,
        "case_count": len(jobs),
        "temperature": 0,
        "thinking": "disabled",
        "response_format": "json_object",
        "data_class": "synthetic public benchmark fixtures",
        "authority": "replaceable model comparator; never gold",
        "hard_cumulative_budget_usd": 10.0,
        "hashes": {
            "jobs.jsonl": sha256(RUN_DIR / "jobs.jsonl"),
            "prompt.txt": sha256(RUN_DIR / "prompt.txt"),
            "schema-v0.json": sha256(CORPUS_DIR / "schema-v0.json"),
            "entities-v0.json": sha256(CORPUS_DIR / "entities-v0.json"),
            "model-cases.jsonl": sha256(CORPUS_DIR / "model-cases.jsonl"),
        },
        "known_limitations": ["inspectable construction corpus", "single model", "no independent labels", "no held-out challenge"],
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def verify_frozen_inputs() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    checks = {
        "jobs.jsonl": RUN_DIR / "jobs.jsonl",
        "prompt.txt": RUN_DIR / "prompt.txt",
        "schema-v0.json": CORPUS_DIR / "schema-v0.json",
        "entities-v0.json": CORPUS_DIR / "entities-v0.json",
        "model-cases.jsonl": CORPUS_DIR / "model-cases.jsonl",
    }
    for label, path in checks.items():
        if sha256(path) != manifest["hashes"][label]:
            raise ValueError(f"frozen input mismatch: {label}")
    return manifest


def request_payload(api_key: str, messages: list[dict[str, str]], timeout: float, max_tokens: int) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "thinking": {"type": "disabled"},
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def validate_response(content: str, batch: list[dict[str, Any]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    payload = json.loads(content)
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("response has no results array")
    expected = {item["query_id"] for item in batch}
    received = {item.get("query_id") for item in results if isinstance(item, dict)}
    if received != expected or len(results) != len(expected):
        raise ValueError(f"query IDs mismatch: expected {sorted(expected)}, got {sorted(str(x) for x in received)}")
    jobs = {item["query_id"]: item for item in batch}
    predicates = {item["id"] for item in schema["predicates"]}
    namespaces = {item["id"] for item in schema["namespaces"]}
    validated = []
    for result in results:
        qid = result["query_id"]
        if result.get("query_status") not in STATUSES:
            raise ValueError(f"{qid}: invalid query_status")
        nodes = result.get("nodes")
        if not isinstance(nodes, list):
            raise ValueError(f"{qid}: nodes must be an array")
        if result["query_status"] == "unsupported_structure" and nodes:
            raise ValueError(f"{qid}: unsupported structure must have no nodes")
        previous: list[str] = []
        for index, node in enumerate(nodes, start=1):
            expected_id = f"O{index}"
            if node.get("obligation_id") != expected_id:
                raise ValueError(f"{qid}: expected node id {expected_id}")
            if node.get("operator") not in OPERATORS:
                raise ValueError(f"{qid}:{expected_id}: invalid operator")
            span = node.get("span_text")
            if not isinstance(span, str) or not span or span not in jobs[qid]["raw_query"]:
                raise ValueError(f"{qid}:{expected_id}: span is not an exact query substring")
            depends = node.get("depends")
            if not isinstance(depends, list) or any(dep not in previous for dep in depends):
                raise ValueError(f"{qid}:{expected_id}: dependencies must refer backward")
            previous.append(expected_id)
            predicate = node.get("predicate")
            if predicate is not None and predicate not in predicates:
                raise ValueError(f"{qid}:{expected_id}: unknown predicate {predicate}")
            if not isinstance(node.get("namespaces"), list) or set(node["namespaces"]) - namespaces:
                raise ValueError(f"{qid}:{expected_id}: unknown namespace")
            if node.get("certificate") not in CERTIFICATES:
                raise ValueError(f"{qid}:{expected_id}: invalid certificate")
            for field in ("entity", "time", "authorization"):
                if not isinstance(node.get(field), str) or not node[field]:
                    raise ValueError(f"{qid}:{expected_id}: {field} must be nonempty")
            if result["query_status"] in {"ambiguous", "unauthorized"} and node["certificate"] in {"applicable", "explicit-negative", "requires-complete-scope"}:
                raise ValueError(f"{qid}:{expected_id}: unsafe certificate for unresolved status")
        validated.append(result)
    return validated


def batches_by_language(pending: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    batches = []
    for language in ("en", "pl"):
        items = [item for item in pending if item["language"] == language]
        batches.extend(items[i : i + batch_size] for i in range(0, len(items), batch_size))
    return batches


def run(env_file: Path, budget_usd: float, batch_size: int, max_tokens: int, timeout: float) -> dict[str, Any]:
    if budget_usd <= 0 or budget_usd > 10:
        raise ValueError("budget must be greater than 0 and no more than 10 USD")
    manifest = verify_frozen_inputs()
    key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    jobs = read_jsonl(RUN_DIR / "jobs.jsonl")
    schema = json.loads((CORPUS_DIR / "schema-v0.json").read_text(encoding="utf-8"))
    entities = json.loads((CORPUS_DIR / "entities-v0.json").read_text(encoding="utf-8"))
    predictions_path = RUN_DIR / "predictions.jsonl"
    completed = {item["query_id"] for item in read_jsonl(predictions_path)}
    attempted_invalid = {item["query_id"] for item in read_jsonl(RUN_DIR / "errors.jsonl") if item.get("query_id")}
    pending = [item for item in jobs if item["query_id"] not in completed | attempted_invalid]
    calls = 0
    for batch in batches_by_language(pending, batch_size):
        user_payload = {
            "instruction": "Parse every case and return one result per exact query_id.",
            "reference": {
                "predicates": [{"id": item["id"], "namespace": item["namespace"], "aliases": item["aliases"]} for item in schema["predicates"]],
                "namespaces": [item["id"] for item in schema["namespaces"]],
                "entities": entities,
                "canonical_time_values": ["current", "all", "after:2026-08-01", "relative:last-month", "recurrence:weekly-monday", "event-anchor:audit:scope", "ambiguous:local-timezone-and-evening-boundary", "inherit:O1", "inherit:O1,O2"],
            },
            "cases": batch,
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        preflight = shared.estimated_request_cost(messages, max_tokens)
        before = shared.ledger_total()
        if before + preflight > budget_usd:
            raise RuntimeError(f"hard cumulative budget would be exceeded: {before:.6f} + {preflight:.6f} > {budget_usd:.2f}")
        started = time.perf_counter()
        try:
            response = request_payload(key, messages, timeout, max_tokens)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            usage = response.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            cost = shared.conservative_cost(prompt_tokens, completion_tokens)
            ledger = {
                "at": utc_now(), "run_id": RUN_ID, "model": response.get("model", MODEL),
                "response_id": response.get("id", ""), "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens, "conservative_cost_usd": round(cost, 8),
                "pricing_basis": "all input charged at configured peak cache-miss rate",
            }
            append_jsonl(GLOBAL_LEDGER, ledger)
            append_jsonl(RUN_DIR / "calls.jsonl", {**ledger, "latency_ms": elapsed_ms, "query_ids": [item["query_id"] for item in batch]})
            content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            append_jsonl(RUN_DIR / "raw-responses.jsonl", {"at": utc_now(), "response_id": response.get("id", ""), "query_ids": [item["query_id"] for item in batch], "content": content})
            parsed = json.loads(content)
            response_results = parsed.get("results")
            if not isinstance(response_results, list):
                raise ValueError("response has no results array")
            by_id = {item.get("query_id"): item for item in response_results if isinstance(item, dict)}
            for job in batch:
                qid = job["query_id"]
                if qid not in by_id:
                    append_jsonl(RUN_DIR / "errors.jsonl", {"at": utc_now(), "query_id": qid, "error_type": "missing-result", "error": "query_id absent from response"})
                    continue
                try:
                    validated = validate_response(json.dumps({"results": [by_id[qid]]}, ensure_ascii=False), [job], schema)[0]
                except (ValueError, json.JSONDecodeError) as exc:
                    append_jsonl(RUN_DIR / "errors.jsonl", {"at": utc_now(), "query_id": qid, "error_type": "result-validation", "error": str(exc), "raw_result": by_id[qid]})
                    continue
                append_jsonl(predictions_path, {**validated, "model": response.get("model", MODEL), "prompt_version": PROMPT_VERSION, "adapter_version": ADAPTER_VERSION, "parsed_at": utc_now()})
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            append_jsonl(RUN_DIR / "errors.jsonl", {"at": utc_now(), "query_ids": [item["query_id"] for item in batch], "error_type": type(exc).__name__, "error": str(exc)})
        calls += 1
    predictions = read_jsonl(predictions_path)
    errors = read_jsonl(RUN_DIR / "errors.jsonl")
    attempted = {item["query_id"] for item in predictions} | {item["query_id"] for item in errors if item.get("query_id")}
    summary = {
        "status": "api-run-complete" if len(attempted) == len(jobs) else "api-run-incomplete",
        "model": MODEL,
        "jobs": len(jobs),
        "valid_predictions": len(predictions),
        "schema_valid_rate": len(predictions) / len(jobs),
        "attempted_cases": len(attempted),
        "errors": len(errors),
        "calls_this_invocation": calls,
        "run_conservative_cost_usd": round(sum(float(item["conservative_cost_usd"]) for item in read_jsonl(GLOBAL_LEDGER) if item.get("run_id") == RUN_ID), 8),
        "all_runs_conservative_cost_usd": shared.ledger_total(),
        "hard_budget_usd": budget_usd,
        "frozen_manifest_hash": hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest(),
    }
    shared.write_json(RUN_DIR / "api-summary.json", summary)
    return summary


def load_scorer():
    path = ROOT / "scripts" / "run_obligation_mapping_construction.py"
    spec = importlib.util.spec_from_file_location("map_scorer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def score() -> dict[str, Any]:
    verify_frozen_inputs()
    scorer = load_scorer()
    cases = {item["query_id"]: item for item in read_jsonl(CORPUS_DIR / "cases.jsonl")}
    predictions = {item["query_id"]: {"query_status": item["query_status"], "nodes": item["nodes"]} for item in read_jsonl(RUN_DIR / "predictions.jsonl")}
    rows = []
    for qid, case in cases.items():
        prediction = predictions.get(qid, {"query_status": "unsupported_structure", "nodes": []})
        rows.append(scorer.score_case(case, "deepseek_v4_flash", prediction))
    summary = scorer.summarize(rows)["deepseek_v4_flash"]
    results_text = "".join(canonical_json(item) + "\n" for item in rows)
    shared.write_jsonl(RUN_DIR / "scored-results.jsonl", rows)
    shared.write_json(RUN_DIR / "score-summary.json", summary)
    api_summary = json.loads((RUN_DIR / "api-summary.json").read_text(encoding="utf-8"))
    report = [
        "# DeepSeek V4 Flash PMLAB-MAP construction arm",
        "",
        "Status: optional replaceable model comparator on inspectable construction data; not held out",
        "",
        f"- valid predictions: {api_summary['valid_predictions']}/{api_summary['jobs']};",
        f"- conservative run cost: USD {api_summary['run_conservative_cost_usd']:.8f};",
        f"- cumulative project API cost: USD {api_summary['all_runs_conservative_cost_usd']:.8f};",
        f"- obligation F1: {summary['obligation_f1']:.3f};",
        f"- critical full recall: {summary['critical_full_recall']:.3f};",
        f"- end-to-end exact: {summary['end_to_end_exact_rate']:.3f};",
        f"- entity/predicate/time: {summary['link_accuracy']['entity']:.3f} / {summary['link_accuracy']['predicate']:.3f} / {summary['link_accuracy']['time']:.3f};",
        f"- false closure: {summary['false_closure_count']};",
        f"- critical unresolved safe handling: {summary['critical_unresolved_safe_rate']:.3f}.",
        "",
        "The model saw only model-facing queries plus the frozen public fixture catalogs, not gold graphs or evaluation metadata. The corpus itself was inspectable before the run, so these values only establish construction behavior. Any invalid/missing batch remains a failure; model output never edits gold.",
        "",
    ]
    (RUN_DIR / "report.md").write_text("\n".join(report), encoding="utf-8", newline="\n")
    run_manifest = {
        "status": "completed-construction-model-comparator",
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "corpus_freeze_commit": CORPUS_FREEZE_COMMIT,
        "prediction_count": len(predictions),
        "scored_case_count": len(rows),
        "hashes": {
            "predictions.jsonl": sha256(RUN_DIR / "predictions.jsonl"),
            "scored-results.jsonl": sha256(RUN_DIR / "scored-results.jsonl"),
            "score-summary.json": sha256(RUN_DIR / "score-summary.json"),
            "report.md": sha256(RUN_DIR / "report.md"),
        },
        "authority": "optional comparator; not gold; not held out",
    }
    shared.write_json(RUN_DIR / "result-manifest.json", run_manifest)
    return {"api": api_summary, "score": summary}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    runner = commands.add_parser("run")
    runner.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    runner.add_argument("--budget-usd", type=float, default=10.0)
    runner.add_argument("--batch-size", type=int, default=7)
    runner.add_argument("--max-tokens", type=int, default=5000)
    runner.add_argument("--timeout", type=float, default=120.0)
    commands.add_parser("score")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "prepare":
        result = prepare()
    elif args.command == "run":
        result = run(args.env_file, args.budget_usd, args.batch_size, args.max_tokens, args.timeout)
    else:
        result = score()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
