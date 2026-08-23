#!/usr/bin/env python3
"""Frozen budgeted M1 advisory review of the natural-history source-unit contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402


MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
RUN_ID = "deepseek-v4-flash-natural-history-contract-review-20260823"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
RUN_CAP = 0.05
GLOBAL_CAP = 10.0


SYSTEM_PROMPT = """You are an adversarial scientific-method, data-contract, Git-history, retrieval-evaluation, and privacy reviewer. Return exactly one JSON object and no prose. Review a proposed natural project-history source-unit and pre-output query contract before any builder or backend exists.

Try to falsify: historical cutoff reconstruction; stable IDs across snapshots; Git SHA-1/SHA-256 distinctions; working-tree/future leakage; Markdown direct-body semantics; exact duplicate aliases; oversize splitting; CSV and JSONL canonicalization; symlinks/submodules; backend-visible equality; query-origin privacy; unverifiable pre-output attestations; development/test sequencing; and whether the described schema actually enforces the prose.

You are an author-operated DeepSeek M1 advisory, not an independent reviewer. You cannot authorize a corpus builder, backend run, model selection, test start, or architecture. Do not invent repository contents or external-source findings.

Return exactly:
{"verdict":"admit_for_independent_review|needs_revision|invalid","fatal_issues":["string"],"major_issues":[{"issue":"string","artifact":"string","why":"string","repair":"string"}],"minor_issues":["string"],"schema_prose_mismatches":[{"field_or_rule":"string","mismatch":"string","repair":"string"}],"leakage_or_privacy_attacks":[{"attack":"string","expected_control":"string","residual_risk":"string"}],"invariants_to_test":["string"],"claims_allowed":["string"],"claims_forbidden":["string"],"builder_must_remain_locked":true,"confidence":0.0}
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate(value: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "verdict", "fatal_issues", "major_issues", "minor_issues", "schema_prose_mismatches",
        "leakage_or_privacy_attacks", "invariants_to_test", "claims_allowed", "claims_forbidden",
        "builder_must_remain_locked", "confidence",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("review differs from exact schema")
    if value["verdict"] not in {"admit_for_independent_review", "needs_revision", "invalid"}:
        raise ValueError("invalid verdict")
    for field in ("fatal_issues", "minor_issues", "invariants_to_test", "claims_allowed", "claims_forbidden"):
        if not isinstance(value[field], list) or any(not isinstance(item, str) or not item.strip() for item in value[field]):
            raise ValueError(f"invalid list: {field}")
    for item in value["major_issues"]:
        if set(item) != {"issue", "artifact", "why", "repair"} or any(not isinstance(v, str) or not v.strip() for v in item.values()):
            raise ValueError("invalid major issue")
    for item in value["schema_prose_mismatches"]:
        if set(item) != {"field_or_rule", "mismatch", "repair"}:
            raise ValueError("invalid schema mismatch")
    for item in value["leakage_or_privacy_attacks"]:
        if set(item) != {"attack", "expected_control", "residual_risk"}:
            raise ValueError("invalid attack row")
    if value["builder_must_remain_locked"] is not True:
        raise ValueError("M1 cannot unlock builder")
    if not isinstance(value["confidence"], (int, float)) or not 0 <= value["confidence"] <= 1:
        raise ValueError("invalid confidence")
    return value


def build_job() -> dict[str, Any]:
    paths = {
        "protocol": "docs/11-research-laboratory/natural-history-retrieval-benchmark-protocol-v0.md",
        "primary_source_audit": "docs/07-literature/natural-history-source-unit-contract-audit-v0.md",
        "eligibility_inventory": "data/lab/pmlab-natural-history-v0/corpus-eligibility-audit-v0.md",
        "eligibility_policy": "data/lab/pmlab-natural-history-v0/corpus-eligibility-policy-v0.json",
        "source_unit_schema": "data/lab/pmlab-natural-history-v0/source-unit-contract-v0.schema.json",
        "query_log_schema": "data/lab/pmlab-natural-history-v0/query-log-contract-v0.schema.json",
        "experiment_manifest": "data/lab/pmlab-natural-history-v0/manifest.json",
        "schema_tests": "tests/test_natural_history_contracts.py",
    }
    return {
        "job_id": "PMLAB-NATURAL-RET-001-CONTRACT-M1",
        "task": "Find contract gaps that must be repaired before independent review or builder construction.",
        "artifacts": {name: (ROOT / path).read_text(encoding="utf-8") for name, path in paths.items()},
        "timing": "No source-unit builder, corpus, authentic query set, dense model selection, backend execution, or result exists.",
        "authority_boundary": "M1 advisory only; every suggestion receives deterministic author disposition and independent review remains required.",
        "data_boundary": "Public repository design artifacts only; no private queries, credentials, project-memory context, or chain of thought.",
    }


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    shared.write_json(RUN_DIR / "job.json", build_job())
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "run_id": RUN_ID, "status": "prepared-uncommitted-input", "model": MODEL,
        "temperature": 0, "thinking": "disabled", "run_budget_usd": RUN_CAP,
        "global_budget_usd": GLOBAL_CAP, "prompt_freeze_commit": None,
        "hashes": {name: sha256(RUN_DIR / name) for name in ("job.json", "prompt.txt")},
        "authority": "author-operated M1 advisory; not independent review and cannot unlock the builder",
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("packet is not awaiting freeze")
    git("cat-file", "-e", f"{commit}^{{commit}}")
    relative = RUN_DIR.relative_to(ROOT).as_posix()
    for name in ("job.json", "prompt.txt"):
        committed = subprocess.check_output(["git", "show", f"{commit}:{relative}/{name}"], cwd=ROOT)
        if committed.decode("utf-8").replace("\r\n", "\n") != (RUN_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n"):
            raise ValueError(f"{name} differs from freeze commit")
    manifest.update({"status": "frozen-input-awaiting-api", "prompt_freeze_commit": commit})
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def verify() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "review-finalized"}:
        raise ValueError("packet is not frozen")
    for name, expected in manifest["hashes"].items():
        if sha256(RUN_DIR / name) != expected:
            raise ValueError(f"frozen input mismatch: {name}")
    return manifest


def run(env_file: Path, run_budget: float, global_budget: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if run_budget != RUN_CAP or global_budget != GLOBAL_CAP:
        raise ValueError("runtime caps must equal frozen caps")
    manifest = verify()
    key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    job = json.loads((RUN_DIR / "job.json").read_text(encoding="utf-8"))
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(job, ensure_ascii=False)}]
    preflight = shared.estimated_request_cost(messages, max_tokens)
    if preflight > run_budget or shared.ledger_total() + preflight > global_budget:
        raise RuntimeError("budget gate would be exceeded")
    shared.write_json(RUN_DIR / "preflight.json", {"peak_cache_miss_usd": preflight, "run_cap_usd": run_budget, "global_before_usd": shared.ledger_total()})
    body = json.dumps({
        "model": MODEL, "messages": messages, "thinking": {"type": "disabled"}, "temperature": 0,
        "max_tokens": max_tokens, "response_format": {"type": "json_object"}, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.load(response)
    usage = raw.get("usage") or {}
    prompt_tokens, completion_tokens = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
    ledger = {
        "at": shared.utc_now(), "run_id": RUN_ID, "model": raw.get("model", MODEL), "response_id": raw.get("id", ""),
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
    return {"status": manifest["status"], "cost_usd": ledger["conservative_cost_usd"], "global_cost_usd": shared.ledger_total()}


def finalize() -> dict[str, Any]:
    manifest = verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("API review is not complete")
    result = validate(json.loads((RUN_DIR / "review-result.json").read_text(encoding="utf-8")))
    lines = [
        "# DeepSeek M1 review of the natural-history contracts", "",
        "Status: finalized author-operated advisory; not independent review and builder remains locked", "",
        f"Verdict: `{result['verdict']}` at confidence {result['confidence']:.2f}.", "",
        "## Fatal issues", "", *([f"- {item}" for item in result["fatal_issues"]] or ["- None reported."]), "",
        "## Major issues", "", *([f"- **{item['issue']}** — {item['why']} Repair candidate: {item['repair']}" for item in result["major_issues"]] or ["- None reported."]), "",
        "## Required invariants", "", *[f"- {item}" for item in result["invariants_to_test"]], "",
        "## Authority boundary", "", "This review may generate repair candidates only. It cannot satisfy independent review or authorize a builder/backend run.",
    ]
    (RUN_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    manifest.update({"status": "review-finalized", "review_result_sha256": sha256(RUN_DIR / "review-result.json")})
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "verdict": result["verdict"], "major_issues": len(result["major_issues"])}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--commit", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    run_parser.add_argument("--run-budget-usd", type=float, default=RUN_CAP)
    run_parser.add_argument("--global-budget-usd", type=float, default=GLOBAL_CAP)
    run_parser.add_argument("--max-tokens", type=int, default=4000)
    run_parser.add_argument("--timeout", type=float, default=180)
    sub.add_parser("finalize")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare()
    elif args.command == "freeze":
        result = freeze(args.commit)
    elif args.command == "run":
        result = run(args.env_file, args.run_budget_usd, args.global_budget_usd, args.max_tokens, args.timeout)
    else:
        result = finalize()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
