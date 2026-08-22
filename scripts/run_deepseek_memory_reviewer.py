#!/usr/bin/env python3
"""Run a frozen, budgeted DeepSeek advisory review of memory-lab evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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
RUN_ID = "deepseek-v4-flash-memory-evidence-audit-20260823"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
BRIDGE = ROOT / "data" / "lab" / "longmemeval-bridge-v0"
PMLAB = ROOT / "data" / "lab" / "pmlab-v0.1-lexical-exploratory-m2" / "test"
PROMPT_VERSION = "memory-evidence-adversarial-review-m1-v1"
VERDICTS = {"accept_with_limits", "needs_revision", "reject_claim"}


SYSTEM_PROMPT = """You are an adversarial scientific-method reviewer of an LLM-memory research project.
Return one valid JSON object and no prose. Treat every supplied artifact as author-provided evidence, not ground truth. Look for protocol drift, invalid inference, metric/construct mismatch, leakage, low power, multiple testing, contaminated public data, common-mode model dependence, and claims that exceed the experiment.

You are an author-operated DeepSeek model, not a human reviewer and not statistically or institutionally independent. Never describe yourself as independent. You cannot change project files or accept claims into canonical memory. Your output is advisory and must preserve failures and uncertainty.

Return exactly:
{"job_id":"exact input","verdict":"accept_with_limits|needs_revision|reject_claim","fatal_issues":["strings"],"major_issues":["strings"],"minor_issues":["strings"],"claims_supported":["strings"],"claims_not_supported":["strings"],"required_claim_boundary":"string","next_required_test":"string","confidence":0.0}

`confidence` must be between 0 and 1. A boundary-touching confidence interval is not positive evidence against the null. Passing a preregistered descriptive rule does not create confirmatory or architecture authority. Distinguish retrieval candidate generation from correct answer abstention."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def selected_fields(value: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    return {field: value[field] for field in fields}


def build_jobs() -> list[dict[str, Any]]:
    base_protocol = json.loads((BRIDGE / "execution-protocol.json").read_text(encoding="utf-8"))
    repair = json.loads((BRIDGE / "execution-protocol-v0.1.json").read_text(encoding="utf-8"))
    bridge = json.loads((BRIDGE / "execution-v0.1" / "final-summary.json").read_text(encoding="utf-8"))
    pmlab = json.loads((PMLAB / "final-summary.json").read_text(encoding="utf-8"))
    selection = json.loads((BRIDGE / "manifest.json").read_text(encoding="utf-8"))["selection"]
    common = {
        "data_boundary": "No raw questions, answers, conversations, source session IDs, API keys, or personal files are supplied.",
        "authority_boundary": "Public transfer diagnostic and M2 exploratory evidence only; no confirmatory or architecture promotion authority.",
    }
    return [
        {
            "job_id": "protocol-integrity",
            "review_focus": "Check chronological preregistration, invalid-run handling, repair scope, controls, reproducibility, and whether v0.1 is interpretable after prior outcome exposure.",
            **common,
            "base_protocol": selected_fields(base_protocol, ["authority", "adapter", "retrieval_contract", "primary_outcome", "sanity_controls", "interpretation_rule", "execution_sequence"]),
            "repair_protocol": repair,
            "valid_result_controls": bridge["controls"],
            "valid_result_hash": bridge["primary_results_sha256"],
        },
        {
            "job_id": "statistics-and-constructs",
            "review_focus": "Check calculations, sample size, bootstrap interpretation, aggregation, abstention construct, latency comparability, and exact claim strength.",
            **common,
            "selection": selection,
            "primary_outcome": base_protocol["primary_outcome"],
            "interpretation_rule": base_protocol["interpretation_rule"],
            "result": selected_fields(bridge, ["decision", "controls", "paired_bootstrap", "b2_minus_b1_by_question_type", "backends", "warm_latency", "limitations"]),
        },
        {
            "job_id": "architecture-and-next-gate",
            "review_focus": "Determine the strongest defensible conclusion across internal and public retrieval evidence, identify what remains untested, and specify the next minimal falsifiable experiment.",
            **common,
            "pmlab_exploratory": selected_fields(pmlab, ["confirmatory", "architecture_promotion_permitted", "decision", "bootstrap", "fresh_process_rankings_deterministic", "summary"]),
            "public_bridge": selected_fields(bridge, ["decision", "architecture_effect", "paired_bootstrap", "b2_minus_b1_by_question_type", "backends", "controls", "limitations"]),
            "candidate_next_stage": "Compare B2 against local dense and hybrid retrieval under matched top-k/context bytes, while separately testing a completeness controller for abstention and stale/poison intrusion.",
        },
    ]


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    jobs = build_jobs()
    shared.write_jsonl(RUN_DIR / "jobs.jsonl", jobs)
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "run_id": RUN_ID,
        "status": "prepared-uncommitted-input",
        "created_at": now(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "jobs": len(jobs),
        "temperature": 0,
        "thinking": "disabled",
        "response_format": "json_object",
        "run_budget_usd": 0.25,
        "global_budget_usd": 10.0,
        "prompt_freeze_commit": None,
        "visible_to_worker": ["content-free protocols, aggregate metrics, hashes, limitations, invalid-run disclosure"],
        "hidden_from_worker": ["raw datasets", "question text", "answers", "conversations", "session IDs", "API key", "personal files"],
        "authority": "author-operated same-family M1 advisory review; not human, institutional, or confirmatory independence",
        "hashes": {
            "jobs.jsonl": sha256(RUN_DIR / "jobs.jsonl"),
            "prompt.txt": sha256(RUN_DIR / "prompt.txt"),
            "bridge_final_summary.json": sha256(BRIDGE / "execution-v0.1" / "final-summary.json"),
            "pmlab_final_summary.json": sha256(PMLAB / "final-summary.json"),
        },
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    path = RUN_DIR / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("review packet is not awaiting freeze")
    git("cat-file", "-e", f"{commit}^{{commit}}")
    for name in ("jobs.jsonl", "prompt.txt"):
        committed = subprocess.check_output(["git", "show", f"{commit}:data/lab/api-screening/{RUN_ID}/{name}"], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != manifest["hashes"][name]:
            raise ValueError(f"{name} differs from frozen commit")
    manifest["prompt_freeze_commit"] = commit
    manifest["status"] = "frozen-input-awaiting-api"
    shared.write_json(path, manifest)
    return manifest


def verify() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "api-run-incomplete", "review-finalized"}:
        raise ValueError("review input is not frozen")
    checks = {
        "jobs.jsonl": RUN_DIR / "jobs.jsonl",
        "prompt.txt": RUN_DIR / "prompt.txt",
        "bridge_final_summary.json": BRIDGE / "execution-v0.1" / "final-summary.json",
        "pmlab_final_summary.json": PMLAB / "final-summary.json",
    }
    for name, path in checks.items():
        if sha256(path) != manifest["hashes"][name]:
            raise ValueError(f"frozen review input mismatch: {name}")
    return manifest


def request(api_key: str, messages: list[dict[str, str]], max_tokens: int, timeout: float) -> dict[str, Any]:
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def validate_prediction(value: dict[str, Any], job_id: str) -> dict[str, Any]:
    expected = {
        "job_id", "verdict", "fatal_issues", "major_issues", "minor_issues", "claims_supported",
        "claims_not_supported", "required_claim_boundary", "next_required_test", "confidence",
    }
    if not isinstance(value, dict) or set(value) != expected or value["job_id"] != job_id:
        raise ValueError("review response differs from exact schema or job ID")
    if value["verdict"] not in VERDICTS:
        raise ValueError("invalid reviewer verdict")
    for field in ("fatal_issues", "major_issues", "minor_issues", "claims_supported", "claims_not_supported"):
        if not isinstance(value[field], list) or any(not isinstance(item, str) or not item.strip() for item in value[field]):
            raise ValueError(f"invalid string list: {field}")
    for field in ("required_claim_boundary", "next_required_test"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"blank required field: {field}")
    if not isinstance(value["confidence"], (int, float)) or not 0 <= value["confidence"] <= 1:
        raise ValueError("confidence must be within [0,1]")
    return value


def run(env_file: Path, run_budget: float, global_budget: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if not 0 < run_budget <= 0.5 or not 0 < global_budget <= 10:
        raise ValueError("invalid run/global budget")
    manifest = verify()
    api_key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    completed = {row["job_id"] for row in shared.read_jsonl(RUN_DIR / "predictions.jsonl")}
    calls = 0
    for job in shared.read_jsonl(RUN_DIR / "jobs.jsonl"):
        if job["job_id"] in completed:
            continue
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(job, ensure_ascii=False)},
        ]
        preflight = shared.estimated_request_cost(messages, max_tokens)
        run_spend = sum(float(row.get("conservative_cost_usd", 0)) for row in shared.read_jsonl(LEDGER) if row.get("run_id") == RUN_ID)
        if run_spend + preflight > run_budget or shared.ledger_total() + preflight > global_budget:
            raise RuntimeError("budget gate would be exceeded")
        started = time.perf_counter()
        try:
            response = request(api_key, messages, max_tokens, timeout)
            usage = response.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            ledger = {
                "at": now(), "run_id": RUN_ID, "model": response.get("model", MODEL), "response_id": response.get("id", ""),
                "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                "conservative_cost_usd": round(shared.conservative_cost(prompt_tokens, completion_tokens), 8),
                "pricing_basis": "all input charged at configured peak cache-miss rate",
            }
            shared.append_jsonl(LEDGER, ledger)
            shared.append_jsonl(RUN_DIR / "calls.jsonl", {**ledger, "job_id": job["job_id"], "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
            content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            shared.append_jsonl(RUN_DIR / "raw-responses.jsonl", {"at": now(), "response_id": response.get("id", ""), "job_id": job["job_id"], "content": content})
            prediction = validate_prediction(json.loads(content), job["job_id"])
            shared.append_jsonl(RUN_DIR / "predictions.jsonl", {**prediction, "model": response.get("model", MODEL), "reviewed_at": now()})
            completed.add(job["job_id"])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at": now(), "job_id": job["job_id"], "error_type": type(exc).__name__, "error": str(exc)})
        calls += 1
    predictions = shared.read_jsonl(RUN_DIR / "predictions.jsonl")
    manifest["status"] = "api-run-complete" if len({row["job_id"] for row in predictions}) == manifest["jobs"] else "api-run-incomplete"
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    summary = {
        "status": manifest["status"], "model": MODEL, "valid_reviews": len(predictions), "calls_this_invocation": calls,
        "errors_logged": len(shared.read_jsonl(RUN_DIR / "errors.jsonl")),
        "run_conservative_cost_usd": round(sum(float(row.get("conservative_cost_usd", 0)) for row in shared.read_jsonl(LEDGER) if row.get("run_id") == RUN_ID), 8),
        "all_runs_conservative_cost_usd": shared.ledger_total(),
        "authority": manifest["authority"],
    }
    shared.write_json(RUN_DIR / "api-summary.json", summary)
    return summary


def finalize() -> dict[str, Any]:
    manifest = verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("all advisory reviews must be complete")
    rows = sorted(shared.read_jsonl(RUN_DIR / "predictions.jsonl"), key=lambda row: row["job_id"])
    verdict_counts = {verdict: sum(row["verdict"] == verdict for row in rows) for verdict in sorted(VERDICTS)}
    result = {
        "status": "review-finalized",
        "evidence_tier": "M1-author-operated-model-advisory",
        "reviewer": MODEL,
        "reviews": len(rows),
        "verdict_counts": verdict_counts,
        "fatal_issues": sorted({item for row in rows for item in row["fatal_issues"]}),
        "major_issues": sorted({item for row in rows for item in row["major_issues"]}),
        "claim_boundaries": [row["required_claim_boundary"] for row in rows],
        "next_required_tests": [row["next_required_test"] for row in rows],
        "authority": "advisory challenge only; not independent validation and cannot promote architecture or confirmatory claims",
    }
    shared.write_json(RUN_DIR / "review-summary.json", result)
    report_lines = [
        "# DeepSeek advisory review of memory evidence", "", "Status: finalized M1 author-operated model review", "",
        "This is an adversarial second-model reading, not human or institutional independence. It cannot turn exploratory evidence into confirmation.", "",
        "## Verdicts", "",
    ]
    for row in rows:
        report_lines.extend([f"### {row['job_id']}", "", f"Verdict: `{row['verdict']}` (confidence {row['confidence']:.2f}).", "", f"Claim boundary: {row['required_claim_boundary']}", "", f"Next test: {row['next_required_test']}", ""])
        if row["fatal_issues"]:
            report_lines.extend(["Fatal issues:", "", *[f"- {item}" for item in row["fatal_issues"]], ""])
        if row["major_issues"]:
            report_lines.extend(["Major issues:", "", *[f"- {item}" for item in row["major_issues"]], ""])
    (RUN_DIR / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8", newline="\n")
    manifest["status"] = "review-finalized"
    manifest["review_summary_sha256"] = sha256(RUN_DIR / "review-summary.json")
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    frozen = sub.add_parser("freeze"); frozen.add_argument("--commit", required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    execute.add_argument("--run-budget-usd", type=float, default=0.25)
    execute.add_argument("--global-budget-usd", type=float, default=10.0)
    execute.add_argument("--max-tokens", type=int, default=3000)
    execute.add_argument("--timeout", type=float, default=180)
    sub.add_parser("finalize")
    args = parser.parse_args()
    if args.command == "prepare": result = prepare()
    elif args.command == "freeze": result = freeze(args.commit)
    elif args.command == "run": result = run(args.env_file, args.run_budget_usd, args.global_budget_usd, args.max_tokens, args.timeout)
    else: result = finalize()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
