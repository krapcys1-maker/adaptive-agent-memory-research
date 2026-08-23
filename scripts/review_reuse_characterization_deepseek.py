#!/usr/bin/env python3
"""Frozen DeepSeek advisory review for PMLAB-REUSE-CHAR-001."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402


MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
RUN_ID = "deepseek-v4-flash-reuse-characterization-review-20260823"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
EXPERIMENT = ROOT / "data" / "lab" / "pmlab-reuse-characterization-v0"
PROTOCOL = ROOT / "docs" / "11-research-laboratory" / "reuse-characterization-benchmark-protocol-v0.md"
FOLLOWUP = ROOT / "docs" / "07-literature" / "retrieval-safety-context-order-followup-v0.md"


SYSTEM_PROMPT = """You are an adversarial scientific-method reviewer of a synthetic LLM-memory retrieval characterization. Return exactly one JSON object and no prose. Treat all inputs as author-produced, not ground truth. Check protocol timing, implementation/metric errors, hidden unfairness, leakage, overinterpretation, safety constructs, context-budget accounting, reproducibility, dependency/model ambiguity, and whether next tests isolate the observed failures.

You are an author-operated DeepSeek model, not a human or institutionally independent reviewer. You cannot confirm results, promote architecture, mutate project memory, or waive the natural-benchmark locks.

Return exactly:
{"verdict":"accept_characterization_with_limits|needs_revision|invalid","fatal_issues":["strings"],"major_issues":["strings"],"minor_issues":["strings"],"metric_or_calculation_checks":[{"item":"string","status":"consistent|inconsistent|not_assessable","reason":"string"}],"claims_supported":["strings"],"claims_not_supported":["strings"],"required_claim_boundary":"string","next_required_tests":["strings"],"confidence":0.0}

Do not infer that high retrieval recall improves final answers. Candidate-null is not abstention. Authored bucket labels do not validate bucket classification. Passing deterministic integrity gates does not validate evidence truth. A synthetic visible 20-query fixture has no architecture-selection authority."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate(value: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "verdict", "fatal_issues", "major_issues", "minor_issues", "metric_or_calculation_checks",
        "claims_supported", "claims_not_supported", "required_claim_boundary", "next_required_tests", "confidence",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("review differs from exact schema")
    if value["verdict"] not in {"accept_characterization_with_limits", "needs_revision", "invalid"}:
        raise ValueError("invalid verdict")
    for field in ("fatal_issues", "major_issues", "minor_issues", "claims_supported", "claims_not_supported", "next_required_tests"):
        if not isinstance(value[field], list) or any(not isinstance(item, str) or not item.strip() for item in value[field]):
            raise ValueError(f"invalid string list: {field}")
    checks = value["metric_or_calculation_checks"]
    if not isinstance(checks, list) or not checks:
        raise ValueError("metric checks required")
    for item in checks:
        if set(item) != {"item", "status", "reason"} or item["status"] not in {"consistent", "inconsistent", "not_assessable"}:
            raise ValueError("invalid metric check")
    if not isinstance(value["required_claim_boundary"], str) or not value["required_claim_boundary"].strip():
        raise ValueError("claim boundary required")
    if not isinstance(value["confidence"], (int, float)) or not 0 <= value["confidence"] <= 1:
        raise ValueError("confidence outside [0,1]")
    return value


def build_job() -> dict[str, Any]:
    summary = json.loads((EXPERIMENT / "execution-v0" / "summary.json").read_text(encoding="utf-8"))
    receipt = json.loads((EXPERIMENT / "execution-v0" / "reproducibility-receipt.json").read_text(encoding="utf-8"))
    manifest = json.loads((EXPERIMENT / "execution-v0" / "execution-manifest.json").read_text(encoding="utf-8"))
    return {
        "job_id": "PMLAB-REUSE-CHAR-001-M1",
        "review_focus": "Falsify the characterization report and its proposed next steps without granting architecture authority.",
        "protocol": PROTOCOL.read_text(encoding="utf-8"),
        "aggregate_summary": summary,
        "execution_manifest": manifest,
        "reproducibility_receipt": receipt,
        "author_report": (EXPERIMENT / "execution-v0" / "report.md").read_text(encoding="utf-8"),
        "primary_source_followup": FOLLOWUP.read_text(encoding="utf-8"),
        "authority_boundary": "Synthetic authored development characterization only; no independent labels, uncertainty interval, reader, natural transfer, or architecture promotion.",
        "data_boundary": "Public synthetic aggregate artifacts only; no conversations, credentials, private files, raw project memory, or chain of thought.",
    }


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    shared.write_json(RUN_DIR / "job.json", build_job())
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "run_id": RUN_ID,
        "status": "prepared-uncommitted-input",
        "created_at": now(),
        "model": MODEL,
        "temperature": 0,
        "thinking": "disabled",
        "run_budget_usd": 0.10,
        "global_budget_usd": 10.0,
        "prompt_freeze_commit": None,
        "authority": "M1 author-operated model advisory; not independent review and cannot promote architecture",
        "hashes": {name: sha256(RUN_DIR / name) for name in ("job.json", "prompt.txt")},
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    path = RUN_DIR / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("packet is not awaiting freeze")
    git("cat-file", "-e", f"{commit}^{{commit}}")
    for name in ("job.json", "prompt.txt"):
        committed = subprocess.check_output(["git", "show", f"{commit}:data/lab/api-screening/{RUN_ID}/{name}"], cwd=ROOT)
        if committed.decode("utf-8").replace("\r\n", "\n") != (RUN_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n"):
            raise ValueError(f"{name} differs from frozen commit")
    manifest.update({"status": "frozen-input-awaiting-api", "prompt_freeze_commit": commit})
    shared.write_json(path, manifest)
    return manifest


def verify() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "review-finalized"}:
        raise ValueError("review packet is not frozen")
    for name in ("job.json", "prompt.txt"):
        if sha256(RUN_DIR / name) != manifest["hashes"][name]:
            raise ValueError(f"frozen input mismatch: {name}")
    return manifest


def run(env_file: Path, run_budget: float, global_budget: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if not 0 < run_budget <= 0.10 or not 0 < global_budget <= 10:
        raise ValueError("invalid budget")
    manifest = verify()
    if manifest["status"] == "api-run-complete":
        return {"status": "already-complete"}
    key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    job = json.loads((RUN_DIR / "job.json").read_text(encoding="utf-8"))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(job, ensure_ascii=False)}]
    preflight = shared.estimated_request_cost(messages, max_tokens)
    if preflight > run_budget or shared.ledger_total() + preflight > global_budget:
        raise RuntimeError("budget gate would be exceeded")
    body = json.dumps({
        "model": MODEL, "messages": messages, "thinking": {"type": "disabled"}, "temperature": 0,
        "max_tokens": max_tokens, "response_format": {"type": "json_object"}, "stream": False,
    }).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.load(response)
    usage = raw.get("usage") or {}
    prompt_tokens, completion_tokens = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
    ledger = {
        "at": now(), "run_id": RUN_ID, "model": raw.get("model", MODEL), "response_id": raw.get("id", ""),
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "conservative_cost_usd": round(shared.conservative_cost(prompt_tokens, completion_tokens), 8),
        "pricing_basis": "all input charged at configured peak cache-miss rate",
    }
    shared.append_jsonl(LEDGER, ledger)
    shared.write_json(RUN_DIR / "call.json", {**ledger, "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
    content = ((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    (RUN_DIR / "raw-response.json").write_text(content + "\n", encoding="utf-8", newline="\n")
    shared.write_json(RUN_DIR / "review-result.json", validate(json.loads(content)))
    manifest.update({"status": "api-run-complete", "response_id": raw.get("id", ""), "cost_usd": ledger["conservative_cost_usd"]})
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "cost_usd": ledger["conservative_cost_usd"], "all_runs_cost_usd": shared.ledger_total()}


def finalize() -> dict[str, Any]:
    manifest = verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("API review is not complete")
    result = validate(json.loads((RUN_DIR / "review-result.json").read_text(encoding="utf-8")))
    lines = [
        "# DeepSeek advisory review of PMLAB-REUSE-CHAR-001", "",
        "Status: finalized M1 author-operated model review; not independent validation", "",
        f"Verdict: `{result['verdict']}` (confidence {result['confidence']:.2f}).", "",
        "## Required claim boundary", "", result["required_claim_boundary"], "",
        "## Fatal issues", "", *([f"- {item}" for item in result["fatal_issues"]] or ["- None reported."]), "",
        "## Major issues", "", *([f"- {item}" for item in result["major_issues"]] or ["- None reported."]), "",
        "## Claims supported", "", *[f"- {item}" for item in result["claims_supported"]], "",
        "## Claims not supported", "", *[f"- {item}" for item in result["claims_not_supported"]], "",
        "## Next required tests", "", *[f"- {item}" for item in result["next_required_tests"]], "",
    ]
    (RUN_DIR / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    manifest.update({"status": "review-finalized", "review_result_sha256": sha256(RUN_DIR / "review-result.json")})
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "verdict": result["verdict"], "major_issues": len(result["major_issues"])}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    freeze_parser = sub.add_parser("freeze"); freeze_parser.add_argument("--commit", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    run_parser.add_argument("--run-budget-usd", type=float, default=0.10)
    run_parser.add_argument("--global-budget-usd", type=float, default=10.0)
    run_parser.add_argument("--max-tokens", type=int, default=3500)
    run_parser.add_argument("--timeout", type=float, default=180)
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
