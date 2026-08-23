#!/usr/bin/env python3
"""Run a frozen DeepSeek cross-family challenge against the T0.1 blind audit packet."""

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
import validate_future_utility_independent_audit_v0 as audit_validator  # noqa: E402

MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
RUN_ID = "deepseek-v4-flash-future-utility-t01-blind-audit-20260823"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
BLIND = ROOT / "data" / "lab" / "pmlab-future-utility-v0" / "independent-audit-v0" / "blind"
COMPLETED_DIR = BLIND.parent
PROMPT_VERSION = "future-utility-t01-blind-falsification-v1"

SYSTEM_PROMPT = """You are an adversarial reviewer of a local-first LLM-memory telemetry protocol. Return one valid JSON object and no prose. Use only the supplied blind packet; absent controls are absent and must not be inferred. Seek fatal flaws in claim scope, experimental unit, bundle credit, interference, logging propensity and support, censoring and missingness, pseudonymous linkage, erasure lifecycle, access/security, digest semantics, and audit independence.

You are an author-operated DeepSeek model. You are not a human, lawyer, privacy professional, statistician, DPIA, institutionally independent reviewer, or approval authority. Prior DeepSeek-family review of schema v0 is disclosed. You cannot authorize T2-T4. T1 can only be deny, conditional, or allow_shadow_only under the manual.

Return exactly:
{"findings":[{"question_id":"A01","verdict":"pass|conditional|fail|not_assessable","severity":"none|minor|major|blocking","evidence_locators":["strings"],"rationale":"string","required_change":"string or null"}],"gate_recommendations":{"T1":"deny|conditional|allow_shadow_only","T2":"deny|conditional","T3":"deny","T4":"deny"},"blocking_findings":["question IDs in packet order"],"residual_risks":["strings"],"overall_rationale":"string"}

Return all ten findings A01-A10 in order. A pass requires severity none and null required_change. Every other verdict requires non-none severity and a concrete change. Every finding needs exact artifact/field or heading locators. Every blocking severity must appear in blocking_findings. Any blocking finding forces T1 deny; any fail prohibits allow_shadow_only."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def build_job() -> dict[str, Any]:
    manifest = audit_validator.verify_blank_packet()
    artifacts = {
        name: (BLIND / name).read_text(encoding="utf-8")
        for name in [*manifest["subject_artifacts"], "questions.json", "review-manual.md"]
    }
    return {
        "job_id": "PMLAB-UTILITY-001-T0.1-blind-audit",
        "packet_manifest_sha256": sha256(BLIND / "manifest.json"),
        "packet_source_revision": manifest["source_revision"],
        "artifacts": artifacts,
        "data_boundary": "Public project contracts and synthetic aggregate report only; no conversation, user content, raw memory, credentials, private files, or chain of thought.",
    }


def validate_result(value: dict[str, Any]) -> dict[str, Any]:
    expected = {"findings", "gate_recommendations", "blocking_findings", "residual_risks", "overall_rationale"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("review result differs from exact schema")
    ids = [row["question_id"] for row in json.loads((BLIND / "questions.json").read_text(encoding="utf-8"))["questions"]]
    findings = value["findings"]
    if not isinstance(findings, list) or [row.get("question_id") for row in findings] != ids:
        raise ValueError("review must cover A01-A10 exactly in order")
    fields = {"question_id", "verdict", "severity", "evidence_locators", "rationale", "required_change"}
    blocking = []
    for row in findings:
        if set(row) != fields or row["verdict"] not in audit_validator.VERDICTS or row["severity"] not in audit_validator.SEVERITIES:
            raise ValueError(f"invalid finding: {row.get('question_id')}")
        if not row["evidence_locators"] or any(not audit_validator.nonempty(item) for item in row["evidence_locators"]):
            raise ValueError("finding lacks evidence locator")
        if not audit_validator.nonempty(row["rationale"]):
            raise ValueError("finding lacks rationale")
        if row["verdict"] == "pass":
            if row["severity"] != "none" or row["required_change"] is not None:
                raise ValueError("pass contract violated")
        elif row["severity"] == "none" or not audit_validator.nonempty(row["required_change"]):
            raise ValueError("non-pass contract violated")
        if row["severity"] == "blocking":
            blocking.append(row["question_id"])
    if value["blocking_findings"] != blocking:
        raise ValueError("blocking list mismatch")
    gates = value["gate_recommendations"]
    if set(gates) != {"T1", "T2", "T3", "T4"} or gates["T1"] not in {"deny", "conditional", "allow_shadow_only"} or gates["T2"] not in {"deny", "conditional"} or gates["T3"] != "deny" or gates["T4"] != "deny":
        raise ValueError("invalid gate recommendations")
    if blocking and gates["T1"] != "deny":
        raise ValueError("blocking review must deny T1")
    if any(row["verdict"] == "fail" for row in findings) and gates["T1"] == "allow_shadow_only":
        raise ValueError("failed review cannot allow T1")
    if not isinstance(value["residual_risks"], list) or any(not audit_validator.nonempty(item) for item in value["residual_risks"]) or not audit_validator.nonempty(value["overall_rationale"]):
        raise ValueError("invalid residual risks or rationale")
    return value


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    shared.write_json(RUN_DIR / "job.json", build_job())
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "run_id": RUN_ID, "status": "prepared-uncommitted-input", "created_at": now(), "model": MODEL,
        "prompt_version": PROMPT_VERSION, "temperature": 0, "thinking": "disabled", "run_budget_usd": 0.10,
        "global_budget_usd": 10.0, "prompt_freeze_commit": None,
        "authority": "M2 cross-family author-operated model challenge; not human/legal/privacy/statistical or institutional independence and cannot unlock T1-T4",
        "hashes": {name: sha256(RUN_DIR / name) for name in ("job.json", "prompt.txt")},
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    path = RUN_DIR / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("run is not awaiting freeze")
    git("cat-file", "-e", f"{commit}^{{commit}}")
    for name in ("job.json", "prompt.txt"):
        committed = subprocess.check_output(["git", "show", f"{commit}:data/lab/api-screening/{RUN_ID}/{name}"], cwd=ROOT)
        committed_text = committed.decode("utf-8").replace("\r\n", "\n")
        working_text = (RUN_DIR / name).read_text(encoding="utf-8").replace("\r\n", "\n")
        if committed_text != working_text:
            raise ValueError(f"{name} differs from frozen commit")
    manifest.update({"status": "frozen-input-awaiting-api", "prompt_freeze_commit": commit})
    shared.write_json(path, manifest)
    return manifest


def verify() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "review-finalized"}:
        raise ValueError("input is not frozen")
    for name in ("job.json", "prompt.txt"):
        if sha256(RUN_DIR / name) != manifest["hashes"][name]:
            raise ValueError(f"frozen input mismatch: {name}")
    return manifest


def run(env_file: Path, run_budget: float, global_budget: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if not 0 < run_budget <= 0.25 or not 0 < global_budget <= 10:
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
    body = json.dumps({"model": MODEL, "messages": messages, "thinking": {"type": "disabled"}, "temperature": 0, "max_tokens": max_tokens, "response_format": {"type": "json_object"}, "stream": False}).encode("utf-8")
    request = urllib.request.Request(API_URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at": now(), "error_type": type(exc).__name__, "error": str(exc)})
        raise
    usage = raw.get("usage") or {}
    prompt_tokens, completion_tokens = int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0)
    ledger = {"at": now(), "run_id": RUN_ID, "model": raw.get("model", MODEL), "response_id": raw.get("id", ""), "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens, "conservative_cost_usd": round(shared.conservative_cost(prompt_tokens, completion_tokens), 8), "pricing_basis": "all input charged at configured peak cache-miss rate"}
    shared.append_jsonl(LEDGER, ledger)
    shared.write_json(RUN_DIR / "call.json", {**ledger, "latency_ms": round((time.perf_counter() - started) * 1000, 2)})
    content = ((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    (RUN_DIR / "raw-response.json").write_text(content + "\n", encoding="utf-8", newline="\n")
    result = validate_result(json.loads(content))
    shared.write_json(RUN_DIR / "review-result.json", result)
    manifest["status"] = "api-run-complete"
    manifest["response_id"] = raw.get("id", "")
    manifest["cost_usd"] = ledger["conservative_cost_usd"]
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return {"status": manifest["status"], "cost_usd": ledger["conservative_cost_usd"], "all_runs_cost_usd": shared.ledger_total()}


def finalize() -> dict[str, Any]:
    manifest = verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("API review is not complete")
    result = validate_result(json.loads((RUN_DIR / "review-result.json").read_text(encoding="utf-8")))
    blank_form = json.loads((BLIND / "review-form.json").read_text(encoding="utf-8"))
    completed_at = now()
    reviewer = {"reviewer_id_or_pseudonym": MODEL, "reviewer_kind": "model_external_author_operated", "family_or_affiliation": "DeepSeek API", "review_started_at": manifest["created_at"], "review_completed_at": completed_at}
    attestation_id = f"DS-{manifest['response_id'] or 'response-unavailable'}"
    completed_form = {**blank_form, "reviewer": reviewer, **result, "attestation_id": attestation_id}
    shared.write_json(COMPLETED_DIR / "completed-review-form.json", completed_form)
    blank_attestation = json.loads((BLIND / "attestation.json").read_text(encoding="utf-8"))
    completed_attestation = {**blank_attestation, "attestation_id": attestation_id, "reviewer_id_or_pseudonym": MODEL, "reviewer_kind": "model_external_author_operated", "family_or_affiliation": "DeepSeek API", "packet_manifest_sha256": sha256(BLIND / "manifest.json"), "statements": {key: True for key in blank_attestation["statements"]}, "conflicts_or_prior_exposure": "Author-operated run; DeepSeek model family previously reviewed telemetry schema v0, but this API request received only the frozen T0.1 blind packet and no author answer key.", "limitations": "No human, legal, privacy-professional, DPIA, institutional-independence, or statistical-reproduction authority; model output may be incomplete or wrong.", "signature_or_verifiable_acknowledgement": f"DeepSeek response ID {manifest['response_id']} bound to frozen run {manifest['prompt_freeze_commit']}"}
    shared.write_json(COMPLETED_DIR / "completed-attestation.json", completed_attestation)
    receipt = audit_validator.validate_completed(COMPLETED_DIR / "completed-review-form.json", COMPLETED_DIR / "completed-attestation.json")
    shared.write_json(COMPLETED_DIR / "completed-review-receipt.json", receipt)
    manifest["status"] = "review-finalized"
    manifest["completed_review_form_sha256"] = sha256(COMPLETED_DIR / "completed-review-form.json")
    manifest["receipt_sha256"] = sha256(COMPLETED_DIR / "completed-review-receipt.json")
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    frozen = sub.add_parser("freeze"); frozen.add_argument("--commit", required=True)
    execute = sub.add_parser("run"); execute.add_argument("--env-file", type=Path, default=ROOT.parent / ".env"); execute.add_argument("--run-budget-usd", type=float, default=0.10); execute.add_argument("--global-budget-usd", type=float, default=10.0); execute.add_argument("--max-tokens", type=int, default=6500); execute.add_argument("--timeout", type=float, default=180)
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
