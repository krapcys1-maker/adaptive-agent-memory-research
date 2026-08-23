#!/usr/bin/env python3
"""Run a frozen, budgeted DeepSeek M1 advisory review of utility telemetry T0."""

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
RUN_ID = "deepseek-v4-flash-future-utility-t0-review-20260823"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
LAB = ROOT / "data" / "lab" / "pmlab-future-utility-v0"
POLICY = ROOT / "docs" / "11-research-laboratory" / "future-utility-telemetry-privacy-and-capture-policy-v0.md"
VALIDATOR = ROOT / "scripts" / "validate_future_utility_telemetry_t0.py"
PROMPT_VERSION = "future-utility-t0-adversarial-m1-v1"
VERDICTS = {"accept_t0_with_limits", "needs_revision", "reject_t0_instrument"}


SYSTEM_PROMPT = """You are an adversarial reviewer of a local-first LLM-memory telemetry instrument.
Return one valid JSON object and no prose. The packet is author-provided construction evidence, not ground truth. Seek privacy leakage, covert raw-content capture, identity linkage, bad correction/deletion semantics, retry inflation, invalid joins, temporal bias, missing-data and censoring mistakes, exposure/selection confounding, reward-credit errors, premature causal language, and unsafe progression to natural capture.

You are an author-operated DeepSeek model, not a human, privacy professional, statistician, institutionally independent reviewer, or approval authority. Never call yourself independent. You cannot authorize T1, randomized withholding, adaptive ranking, deletion, retention, emotional salience, or causal utility. Separate T0 instrument integrity from scientific validity.

Return exactly:
{"job_id":"exact input","verdict":"accept_t0_with_limits|needs_revision|reject_t0_instrument","fatal_issues":["strings"],"major_issues":["strings"],"minor_issues":["strings"],"missing_privacy_controls":["strings"],"missing_causal_controls":["strings"],"accepted_t0_claims":["strings"],"claims_not_supported":["strings"],"required_repairs_before_t1":["strings"],"next_test":"string","confidence":0.0}

Confidence must be in [0,1]. An empty issue list is allowed. Do not request or infer private user content."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def build_jobs() -> list[dict[str, Any]]:
    manifest = json.loads((LAB / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((LAB / "t0" / "validation-report.json").read_text(encoding="utf-8"))
    schema = json.loads((LAB / "telemetry-event-v0.schema.json").read_text(encoding="utf-8"))
    invalid = json.loads((LAB / "t0" / "invalid-cases.json").read_text(encoding="utf-8"))
    common = {
        "authority_boundary": manifest["t0_result_authority"],
        "current_phase_locks": {
            key: manifest[key]
            for key in (
                "t1_natural_capture_authorized", "t2_replay_authorized",
                "t3_randomized_exposure_authorized", "t4_utility_model_authorized",
                "adaptive_policy_authorized", "canonical_memory_mutation_authorized",
            )
        },
        "event_types": schema["properties"]["event_type"]["enum"],
        "common_required_fields": schema["required"],
        "privacy_contract": POLICY.read_text(encoding="utf-8"),
        "t0_result": report,
        "registered_invalid_cases": [
            {"case_id": row["case_id"], "expected_error": row["expected_error"]}
            for row in invalid
        ],
        "validator_invariants": [
            "strict top-level and per-event fields",
            "T0 only synthetic nonsensitive events and no external processing",
            "raw content, prompts, outputs, chain of thought, credentials, email and similar keys/patterns rejected",
            "event_id plus idempotency_key exact retry collapse; conflicting reuse rejected",
            "recorded_at nondecreasing for logical events",
            "memory -> task -> candidate -> retrieval -> assignment -> exposure -> behavior/outcome joins",
            "randomized or synthetic assignment needs propensity; natural observation uses null propensity",
            "behavior reference requires a shown exposure event reference",
            "outcome name/unit/window must be preregistered",
            "closure outstanding outcomes must exactly equal missing outcomes and censoring is explicit",
            "correction targets one prior non-correction event, stays under payload, and corrected event revalidates without mutating original",
            "causal_effect_estimated rejected before T4",
        ],
        "artifact_hashes": {
            "schema": sha256(LAB / "telemetry-event-v0.schema.json"),
            "validator": sha256(VALIDATOR),
            "privacy_policy": sha256(POLICY),
            "valid_deliveries": sha256(LAB / "t0" / "valid-deliveries.jsonl"),
            "invalid_cases": sha256(LAB / "t0" / "invalid-cases.json"),
            "report": sha256(LAB / "t0" / "validation-report.json"),
        },
        "data_boundary": "Only public project contracts, synthetic aggregate results, enums, hashes, and invalid-case names are supplied. No transcript, user content, credentials, raw memory, or model output is supplied.",
    }
    return [
        {
            "job_id": "privacy-and-governance",
            "review_focus": "Find missing privacy, minimization, linkage, access, retention, correction, deletion, export, external-worker, and authorization controls. Decide only whether the T0 claim is bounded correctly and what must precede T1.",
            **common,
        },
        {
            "job_id": "measurement-and-causal-integrity",
            "review_focus": "Find join, idempotency, time, censoring, outcome, assignment, exposure, interference, credit-assignment, policy-drift, and causal-language defects. Decide only whether the synthetic T0 instrument result is interpretable and what must precede T1.",
            **common,
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
        "run_budget_usd": 0.10,
        "global_budget_usd": 10.0,
        "prompt_freeze_commit": None,
        "visible_to_worker": ["public contracts", "synthetic aggregate report", "event enums", "validator invariants", "artifact hashes"],
        "hidden_from_worker": ["conversation", "user content", "raw memories", "credentials", "API key", "private files", "chain of thought"],
        "authority": "author-operated M1 advisory review; not independent privacy/statistical approval and cannot unlock T1-T4",
        "hashes": {
            "jobs.jsonl": sha256(RUN_DIR / "jobs.jsonl"),
            "prompt.txt": sha256(RUN_DIR / "prompt.txt"),
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
    for name in ("jobs.jsonl", "prompt.txt"):
        if sha256(RUN_DIR / name) != manifest["hashes"][name]:
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
        "job_id", "verdict", "fatal_issues", "major_issues", "minor_issues",
        "missing_privacy_controls", "missing_causal_controls", "accepted_t0_claims",
        "claims_not_supported", "required_repairs_before_t1", "next_test", "confidence",
    }
    if not isinstance(value, dict) or set(value) != expected or value["job_id"] != job_id:
        raise ValueError("review response differs from exact schema or job ID")
    if value["verdict"] not in VERDICTS:
        raise ValueError("invalid reviewer verdict")
    list_fields = expected - {"job_id", "verdict", "next_test", "confidence"}
    for field in list_fields:
        if not isinstance(value[field], list) or any(not isinstance(item, str) or not item.strip() for item in value[field]):
            raise ValueError(f"invalid string list: {field}")
    if not isinstance(value["next_test"], str) or not value["next_test"].strip():
        raise ValueError("next_test must be nonempty")
    if not isinstance(value["confidence"], (int, float)) or not 0 <= value["confidence"] <= 1:
        raise ValueError("confidence must be within [0,1]")
    return value


def run(env_file: Path, run_budget: float, global_budget: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if not 0 < run_budget <= 0.25 or not 0 < global_budget <= 10:
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
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(job, ensure_ascii=False)}]
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
        "status": manifest["status"], "valid_reviews": len(predictions), "calls_this_invocation": calls,
        "errors_logged": len(shared.read_jsonl(RUN_DIR / "errors.jsonl")),
        "run_conservative_cost_usd": round(sum(float(row.get("conservative_cost_usd", 0)) for row in shared.read_jsonl(LEDGER) if row.get("run_id") == RUN_ID), 8),
        "all_runs_conservative_cost_usd": shared.ledger_total(), "authority": manifest["authority"],
    }
    shared.write_json(RUN_DIR / "api-summary.json", summary)
    return summary


def finalize() -> dict[str, Any]:
    manifest = verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("all advisory reviews must be complete")
    rows = sorted(shared.read_jsonl(RUN_DIR / "predictions.jsonl"), key=lambda row: row["job_id"])
    result = {
        "status": "review-finalized",
        "evidence_tier": "M1-author-operated-model-advisory",
        "reviewer": MODEL,
        "reviews": len(rows),
        "verdict_counts": {verdict: sum(row["verdict"] == verdict for row in rows) for verdict in sorted(VERDICTS)},
        "fatal_issues": sorted({item for row in rows for item in row["fatal_issues"]}),
        "major_issues": sorted({item for row in rows for item in row["major_issues"]}),
        "missing_privacy_controls": sorted({item for row in rows for item in row["missing_privacy_controls"]}),
        "missing_causal_controls": sorted({item for row in rows for item in row["missing_causal_controls"]}),
        "required_repairs_before_t1": sorted({item for row in rows for item in row["required_repairs_before_t1"]}),
        "next_tests": [row["next_test"] for row in rows],
        "authority": "advisory challenge only; not independent validation and cannot unlock T1-T4",
    }
    shared.write_json(RUN_DIR / "review-summary.json", result)
    lines = [
        "# DeepSeek advisory review of future-utility telemetry T0", "",
        "Status: finalized M1 author-operated model review", "",
        "This review is adversarial advice, not human, institutional, privacy, or statistical independence. It cannot unlock T1-T4.", "",
    ]
    for row in rows:
        lines.extend([f"## {row['job_id']}", "", f"Verdict: `{row['verdict']}` (confidence {row['confidence']:.2f}).", "", f"Next test: {row['next_test']}", ""])
        for heading, field in (("Fatal issues", "fatal_issues"), ("Major issues", "major_issues"), ("Required before T1", "required_repairs_before_t1"), ("Unsupported claims", "claims_not_supported")):
            if row[field]:
                lines.extend([f"### {heading}", "", *[f"- {item}" for item in row[field]], ""])
    (RUN_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
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
    execute.add_argument("--run-budget-usd", type=float, default=0.10)
    execute.add_argument("--global-budget-usd", type=float, default=10.0)
    execute.add_argument("--max-tokens", type=int, default=2500)
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
