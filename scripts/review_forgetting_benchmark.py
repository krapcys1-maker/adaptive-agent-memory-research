#!/usr/bin/env python3
"""Ask a budgeted DeepSeek worker for adversarial F1/F2 design criticism.

The output is an unreviewed candidate queue. It cannot alter gold labels,
accepted evidence, decisions, or project memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from scripts import screen_literature as shared
except ImportError:  # Direct `python scripts/...` execution.
    import screen_literature as shared


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "lab" / "pmlab-forgetting-dev"
OUTPUT_ROOT = ROOT / "data" / "lab" / "api-screening"
MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
PROMPT_VERSION = "forgetting-benchmark-adversarial-review-v1"

SYSTEM_PROMPT = """You are an adversarial benchmark-methodology reviewer.
You receive only a synthetic development-instrument description and aggregate results.
Return one valid JSON object and no prose. Do not treat authored labels or perfect scores
as independent evidence. Look specifically for tautological probes, label leakage,
unfair oracle advantages, metric artifacts, missing controls, ambiguity between failed
pipeline stage and physical data loss, and conclusions that exceed the design.

JSON shape:
{
  "results": [
    {
      "job_id": "exact input job_id",
      "severity": "none|low|medium|high",
      "findings": [
        {"code": "short-code", "claim": "short issue", "why": "short reason", "fix": "testable repair"}
      ],
      "minimum_next_action": "one concrete action",
      "do_not_conclude": "one prohibited inference"
    }
  ]
}

Review only what is supplied. Use an empty findings list if no issue is supported.
"""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_jobs() -> list[dict[str, Any]]:
    manifest = read_json(DATASET / "artifacts" / "manifest.json")
    f1 = read_json(DATASET / "artifacts" / "f1-summary.json")
    f2 = read_json(DATASET / "artifacts" / "f2-summary.json")
    shared_boundary = {
        "status": manifest["status"],
        "authority": manifest["authority"],
        "authored": True,
        "held_out": False,
        "independent_annotation": False,
    }
    return [
        {
            "job_id": "F1-STAGE-VS-LOSS",
            "question": "Can failed pipeline stage and physical data loss be confused by this contract?",
            "evidence": {**shared_boundary, "summary": f1, "probe_contract": "F0 write receipt; F1 canonical presence/checksum/schema/provenance/raw-byte recoverability; F2 retrieval; F3 context; F4 reader; F5 action or judge"},
        },
        {
            "job_id": "F1-INTERNAL-VALIDITY",
            "question": "Which cases are missing before the F1 instrument can estimate real localization accuracy?",
            "evidence": {**shared_boundary, "cases": manifest["f1_cases"], "fault_contract": "exactly one authored fault per trace", "summary": f1},
        },
        {
            "job_id": "F2-BASELINE-FAIRNESS",
            "question": "Is the B1/B2 versus B3 comparison fair and what can it actually establish?",
            "evidence": {**shared_boundary, "summary": f2, "b3_input": "gold history_id and gold as_of_version", "top_k": 5},
        },
        {
            "job_id": "F2-CURVE-VALIDITY",
            "question": "Which design artifacts could create the observed update-count curve?",
            "evidence": {**shared_boundary, "summary": f2, "corpus": "four templated histories, 64 revisions each", "queries": "current and historical-as-of at seven update counts"},
        },
        {
            "job_id": "NEXT-GATE",
            "question": "What is the minimum independently reviewable next gate before architecture claims?",
            "evidence": {**shared_boundary, "f1": f1, "f2": f2},
        },
    ]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(content: str, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = json.loads(content)
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("response does not contain a results array")
    expected = {job["job_id"] for job in jobs}
    received = {row.get("job_id") for row in results if isinstance(row, dict)}
    if received != expected or len(results) != len(expected):
        raise ValueError("response job IDs do not match frozen jobs")
    for row in results:
        if row.get("severity") not in {"none", "low", "medium", "high"}:
            raise ValueError(f"invalid severity for {row.get('job_id')}")
        if not isinstance(row.get("findings"), list):
            raise ValueError(f"findings must be a list for {row.get('job_id')}")
    return results


def prepare(run_id: str) -> dict[str, Any]:
    run_dir = OUTPUT_ROOT / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"run directory is not empty: {run_dir}")
    jobs = build_jobs()
    shared.write_jsonl(run_dir / "jobs.jsonl", jobs)
    jobs_path = run_dir / "jobs.jsonl"
    manifest = {
        "run_id": run_id,
        "status": "frozen-input",
        "jobs": len(jobs),
        "jobs_sha256": sha256_file(jobs_path),
        "dataset_manifest_sha256": sha256_file(DATASET / "artifacts" / "manifest.json"),
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "thinking": "disabled",
        "temperature": 0,
        "data_class": "public deterministic synthetic benchmark metadata and aggregate results",
        "authority": "unreviewed adversarial candidates only; cannot change gold or memory",
        "pricing_assumption_usd_per_million": {
            "input_all_cache_miss": shared.INPUT_PRICE_PER_MILLION_USD,
            "output": shared.OUTPUT_PRICE_PER_MILLION_USD,
        },
    }
    write_json(run_dir / "manifest.json", manifest)
    return manifest


def run(run_id: str, env_file: Path, budget_usd: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if budget_usd <= 0 or budget_usd > 10:
        raise ValueError("budget must be greater than 0 and no more than 10 USD")
    api_key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    run_dir = OUTPUT_ROOT / run_id
    manifest = read_json(run_dir / "manifest.json")
    jobs_path = run_dir / "jobs.jsonl"
    if sha256_file(jobs_path) != manifest["jobs_sha256"]:
        raise ValueError("jobs do not match frozen manifest")
    jobs = shared.read_jsonl(jobs_path)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps({"items": jobs}, ensure_ascii=False)},
    ]
    characters = sum(len(message["content"]) for message in messages)
    preflight = shared.conservative_cost(math.ceil(characters / 2), max_tokens)
    spent_before = shared.ledger_total()
    if spent_before + preflight > budget_usd:
        raise RuntimeError(
            f"hard budget would be exceeded: spent {spent_before:.6f}, next worst case {preflight:.6f}, cap {budget_usd:.2f}"
        )
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
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    usage = payload.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    cost = shared.conservative_cost(prompt_tokens, completion_tokens)
    ledger = {
        "at": shared.utc_now(),
        "run_id": run_id,
        "model": payload.get("model", MODEL),
        "response_id": payload.get("id", ""),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "conservative_cost_usd": round(cost, 8),
        "pricing_basis": "all input charged at configured peak cache-miss rate",
    }
    shared.append_jsonl(shared.BUDGET_LEDGER, ledger)
    shared.append_jsonl(
        run_dir / "calls.jsonl",
        {**ledger, "latency_ms": latency_ms, "job_ids": [job["job_id"] for job in jobs]},
    )
    content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    results = validate(content, jobs)
    candidates = [
        {
            **row,
            "model": payload.get("model", MODEL),
            "prompt_version": PROMPT_VERSION,
            "review_state": "model-candidate-unreviewed",
        }
        for row in results
    ]
    shared.write_jsonl(run_dir / "review-queue.jsonl", candidates)
    summary = {
        "run_id": run_id,
        "jobs": len(jobs),
        "schema_valid_outputs": len(candidates),
        "run_conservative_cost_usd": round(cost, 8),
        "all_runs_conservative_cost_usd": shared.ledger_total(),
        "hard_budget_usd": budget_usd,
        "authority": "model candidates only; manual benchmark review required",
    }
    write_json(run_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Budgeted adversarial review of F1/F2")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--run-id", required=True)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    run_parser.add_argument("--budget-usd", type=float, default=10.0)
    run_parser.add_argument("--max-tokens", type=int, default=3000)
    run_parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    try:
        result = prepare(args.run_id) if args.command == "prepare" else run(
            args.run_id, args.env_file, args.budget_usd, args.max_tokens, args.timeout
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
