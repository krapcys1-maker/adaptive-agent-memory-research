#!/usr/bin/env python3
"""Run a frozen blind DeepSeek leakage audit for PMLAB v0.1 at evidence tier M1."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402
import validate_pmlab_v01_leakage_review as base_validator  # noqa: E402


MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
RUN_ID = "deepseek-v4-flash-pmlab-v01-leakage-review-20260822"
PROMPT_VERSION = "pmlab-v01-model-blind-leakage-m1-v1"
PACKET = ROOT / "data" / "lab" / "project-memory-lab-v0.1-construction"
BLIND = PACKET / "blind"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"
LEAKAGE_TYPES = {
    "repeated_lexical_frame", "repeated_syntactic_frame", "semantic_task_equivalence",
    "category_or_relation_disclosure", "identifier_or_filename_cue", "project_exposure_cue", "other",
}
SEVERITIES = {"low", "medium", "high", "material"}


SYSTEM_PROMPT = """You are the blind split-leakage auditor for an LLM memory benchmark.
Return one valid JSON object and no prose. You do not know author labels, evidence IDs, backend outputs, generator code, or preferred conclusions.

For the one visible category, compare every development query against every test query. Reject the category when test wording repeats a material lexical/syntactic frame, exposes the target relation or answer structure, or is semantically the same templated task with only slot substitutions. Shared topic alone is not leakage. Different natural questions may test the same capability if their surface and task construction cannot be predicted from development forms.

Search adversarially for:
- repeated lexical or syntactic templates;
- semantic task equivalence hidden by synonyms or translation;
- category, relation, answer-shape, filename, identifier, or project-exposure cues;
- development forms that teach a shortcut for test forms.

Return exactly:
{"category_review":{"category":"exact category","decision":"accept|reject","material_overlap_example_ids":["IDs"],"notes":"concise rationale","findings":[{"development_example_id":"ID","test_example_id":"ID","leakage_type":"repeated_lexical_frame|repeated_syntactic_frame|semantic_task_equivalence|category_or_relation_disclosure|identifier_or_filename_cue|project_exposure_cue|other","severity":"low|medium|high|material","reason":"specific comparison"}]}}

`material_overlap_example_ids` must contain every ID involved in a finding that makes you reject. It may be empty on acceptance. Do not reject merely because development and test belong to the same named capability. Do not infer hidden answers."""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def build_jobs() -> list[dict[str, Any]]:
    rows = shared.read_jsonl(BLIND / "queries.jsonl")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    allowed = {"example_id", "split", "language", "query", "query_time", "family"}
    for row in rows:
        public = {key: row[key] for key in allowed}
        grouped[row["category"]].append(public)
    jobs = []
    for category in sorted(grouped):
        items = sorted(grouped[category], key=lambda row: (row["split"], row["example_id"]))
        splits = {name: sum(row["split"] == name for row in items) for name in ("development", "test")}
        if splits != {"development": 5, "test": 5}:
            raise ValueError(f"{category}: expected five development and five test forms")
        jobs.append({"job_id": f"leakage-{category}", "category": category, "queries": items})
    if len(jobs) != 12:
        raise ValueError("expected twelve categories")
    return jobs


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    shared.write_jsonl(RUN_DIR / "jobs.jsonl", build_jobs())
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    packet_manifest = json.loads((PACKET / "manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "run_id": RUN_ID,
        "status": "prepared-uncommitted-input",
        "created_at": now(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "evidence_tier": "M1",
        "candidate_query_freeze_commit": packet_manifest["candidate_freeze_commit"],
        "prompt_freeze_commit": None,
        "categories": 12,
        "queries": packet_manifest["queries"],
        "temperature": 0,
        "thinking": "disabled",
        "response_format": "json_object",
        "run_budget_usd": 0.25,
        "global_budget_usd": 10.0,
        "visible_to_worker": ["blind query forms", "development/test assignment", "category", "language", "query time", "synthetic/project family"],
        "hidden_from_worker": ["author labels", "evidence corpus content", "builder source", "backend outputs", "other reviewer forms", "preferred decision"],
        "authority": "author-operated external model; blind M1 review, not human or cross-family independence",
        "hashes": {
            "jobs.jsonl": sha256(RUN_DIR / "jobs.jsonl"),
            "prompt.txt": sha256(RUN_DIR / "prompt.txt"),
            "blind_queries.jsonl": sha256(BLIND / "queries.jsonl"),
            "blind_corpus.jsonl": sha256(BLIND / "corpus.jsonl"),
        },
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    path = RUN_DIR / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("run is not awaiting freeze")
    git("cat-file", "-e", f"{commit}^{{commit}}")
    for name in ("jobs.jsonl", "prompt.txt"):
        committed = subprocess.check_output(["git", "show", f"{commit}:data/lab/api-screening/{RUN_ID}/{name}"], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != manifest["hashes"][name]:
            raise ValueError(f"{name} differs from the frozen commit")
    manifest["prompt_freeze_commit"] = commit
    manifest["status"] = "frozen-input-awaiting-api"
    shared.write_json(path, manifest)
    return manifest


def verify() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "api-run-incomplete", "review-finalized"}:
        raise ValueError("run input is not frozen")
    checks = {
        "jobs.jsonl": RUN_DIR / "jobs.jsonl", "prompt.txt": RUN_DIR / "prompt.txt",
        "blind_queries.jsonl": BLIND / "queries.jsonl", "blind_corpus.jsonl": BLIND / "corpus.jsonl",
    }
    for name, path in checks.items():
        if sha256(path) != manifest["hashes"][name]:
            raise ValueError(f"frozen input mismatch: {name}")
    return manifest


def request(api_key: str, messages: list[dict[str, str]], max_tokens: int, timeout: float) -> dict[str, Any]:
    body = json.dumps({
        "model": MODEL, "messages": messages, "thinking": {"type": "disabled"}, "temperature": 0,
        "max_tokens": max_tokens, "response_format": {"type": "json_object"}, "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def validate_prediction(value: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    item = value.get("category_review")
    required = {"category", "decision", "material_overlap_example_ids", "notes", "findings"}
    if not isinstance(item, dict) or set(item) != required or item["category"] != job["category"]:
        raise ValueError("category review fields or category mismatch")
    if item["decision"] not in {"accept", "reject"} or not isinstance(item["notes"], str):
        raise ValueError("invalid decision or notes")
    ids = {row["example_id"] for row in job["queries"]}
    material = item["material_overlap_example_ids"]
    if not isinstance(material, list) or len(material) != len(set(material)) or not set(material) <= ids:
        raise ValueError("invalid material-overlap IDs")
    if item["decision"] == "accept" and material:
        raise ValueError("accepted category cannot list material-overlap IDs")
    if item["decision"] == "reject" and (not material or not item["notes"].strip()):
        raise ValueError("rejection requires material IDs and notes")
    if not isinstance(item["findings"], list):
        raise ValueError("findings must be a list")
    by_id = {row["example_id"]: row for row in job["queries"]}
    for finding in item["findings"]:
        expected = {"development_example_id", "test_example_id", "leakage_type", "severity", "reason"}
        if not isinstance(finding, dict) or set(finding) != expected:
            raise ValueError("finding fields differ from contract")
        dev = finding["development_example_id"]
        test = finding["test_example_id"]
        if dev not in by_id or test not in by_id or by_id[dev]["split"] != "development" or by_id[test]["split"] != "test":
            raise ValueError("finding does not reference a valid development/test pair")
        if finding["leakage_type"] not in LEAKAGE_TYPES or finding["severity"] not in SEVERITIES:
            raise ValueError("invalid leakage type or severity")
        if not isinstance(finding["reason"], str) or not finding["reason"].strip():
            raise ValueError("finding reason is blank")
    material_finding_ids = {
        example_id
        for finding in item["findings"]
        if finding["severity"] == "material"
        for example_id in (finding["development_example_id"], finding["test_example_id"])
    }
    if item["decision"] == "accept" and material_finding_ids:
        raise ValueError("accepted category cannot contain a material finding")
    if item["decision"] == "reject" and not material_finding_ids:
        raise ValueError("rejected category requires at least one material finding")
    if item["decision"] == "reject" and not material_finding_ids <= set(material):
        raise ValueError("material-overlap IDs must include every material finding ID")
    return item


def run(env_file: Path, run_budget: float, global_budget: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if not 0 < run_budget <= 1 or not 0 < global_budget <= 10:
        raise ValueError("invalid run/global budget")
    manifest = verify()
    api_key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    predictions_path = RUN_DIR / "predictions.jsonl"
    completed = {row["category"] for row in shared.read_jsonl(predictions_path)}
    calls = 0
    for job in shared.read_jsonl(RUN_DIR / "jobs.jsonl"):
        if job["category"] in completed:
            continue
        payload = {"instruction": "Audit every development/test pair in this category.", **job}
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
        preflight = shared.estimated_request_cost(messages, max_tokens)
        prior_run = sum(float(row.get("conservative_cost_usd", 0)) for row in shared.read_jsonl(LEDGER) if row.get("run_id") == RUN_ID)
        prior_global = shared.ledger_total()
        if prior_run + preflight > run_budget or prior_global + preflight > global_budget:
            raise RuntimeError(f"budget gate: run {prior_run:.6f}+{preflight:.6f}/{run_budget:.2f}; global {prior_global:.6f}+{preflight:.6f}/{global_budget:.2f}")
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
            shared.append_jsonl(RUN_DIR / "calls.jsonl", {**ledger, "latency_ms": round((time.perf_counter() - started) * 1000, 2), "category": job["category"]})
            content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            shared.append_jsonl(RUN_DIR / "raw-responses.jsonl", {"at": now(), "response_id": response.get("id", ""), "category": job["category"], "content": content})
            prediction = validate_prediction(json.loads(content), job)
            shared.append_jsonl(predictions_path, {**prediction, "model": response.get("model", MODEL), "prompt_version": PROMPT_VERSION, "reviewed_at": now()})
            completed.add(job["category"])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at": now(), "category": job["category"], "error_type": type(exc).__name__, "error": str(exc)})
        calls += 1
    predictions = shared.read_jsonl(predictions_path)
    manifest["status"] = "api-run-complete" if len({row["category"] for row in predictions}) == manifest["categories"] else "api-run-incomplete"
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    summary = {
        "status": manifest["status"], "model": MODEL, "evidence_tier": "M1", "categories": manifest["categories"],
        "valid_category_reviews": len(predictions), "calls_this_invocation": calls,
        "errors_logged": len(shared.read_jsonl(RUN_DIR / "errors.jsonl")),
        "run_conservative_cost_usd": round(sum(float(row.get("conservative_cost_usd", 0)) for row in shared.read_jsonl(LEDGER) if row.get("run_id") == RUN_ID), 8),
        "all_runs_conservative_cost_usd": shared.ledger_total(),
        "authority": "blind author-operated model review; not human or cross-family independence",
    }
    shared.write_json(RUN_DIR / "api-summary.json", summary)
    return summary


def finalize() -> dict[str, Any]:
    manifest = verify()
    if manifest["status"] != "api-run-complete":
        raise ValueError("all category reviews must be complete")
    predictions = {row["category"]: row for row in shared.read_jsonl(RUN_DIR / "predictions.jsonl")}
    template = json.loads((BLIND / "leakage-review-form.json").read_text(encoding="utf-8"))
    template.update({
        "reviewer_id": "deepseek-v4-flash-blind-m1",
        "reviewer_family_or_affiliation": "DeepSeek API; author-operated external model; common-mode dependence disclosed",
        "review_started_at": min(row["reviewed_at"] for row in predictions.values()),
        "review_completed_at": max(row["reviewed_at"] for row in predictions.values()),
        "whole_packet_decision": "accept" if all(row["decision"] == "accept" for row in predictions.values()) else "reject",
        "conflicts_prior_exposure_or_assistance": "Author-operated API. DeepSeek family performed earlier unrelated project screening and mapper diagnostics, but this fresh context received only the frozen blind query jobs and prompt. No human or cross-family independence claimed.",
        "signature_or_verifiable_acknowledgement": f"{RUN_ID}:{manifest['prompt_freeze_commit']}",
    })
    template["statements"] = {key: True for key in template["statements"]}
    for category in template["category_reviews"]:
        row = predictions[category]
        template["category_reviews"][category] = {
            "decision": row["decision"], "material_overlap_example_ids": row["material_overlap_example_ids"], "notes": row["notes"],
        }
    review_path = RUN_DIR / "completed-model-leakage-review.json"
    shared.write_json(review_path, template)
    base = base_validator.validate(review_path)
    receipt = {
        **base,
        "status": "model-blind-leakage-review-contract-valid",
        "evidence_tier": "M1",
        "human_independence_satisfied": False,
        "cross_family_independence_satisfied": False,
        "model_review_common_mode_risk": True,
        "experimental_annotation_permitted": base["decision"] == "accept",
        "confirmatory_baseline_permitted": False,
        "authority": "M1 model-reviewed exploratory gate only",
    }
    shared.write_json(RUN_DIR / "model-review-receipt.json", receipt)
    manifest["status"] = "review-finalized"
    manifest["decision"] = receipt["decision"]
    manifest["completed_review_sha256"] = sha256(review_path)
    manifest["receipt_sha256"] = sha256(RUN_DIR / "model-review-receipt.json")
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    frozen = sub.add_parser("freeze")
    frozen.add_argument("--commit", required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    execute.add_argument("--run-budget-usd", type=float, default=0.25)
    execute.add_argument("--global-budget-usd", type=float, default=10.0)
    execute.add_argument("--max-tokens", type=int, default=2500)
    execute.add_argument("--timeout", type=float, default=120)
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
