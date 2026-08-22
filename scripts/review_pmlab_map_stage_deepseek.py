#!/usr/bin/env python3
"""Run a blind, budgeted advisory review of PMLAB-MAP stage-dev labels.

DeepSeek sees the frozen review queue and entity catalog, never gold labels,
criticality, strata, scores, or author rationale. Adjudication is a separate
post-response operation. The worker is advisory and cannot confer independent
review status on the corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402


MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
RUN_ID = "deepseek-v4-flash-map-stage-advisory-review-20260822"
PROMPT_VERSION = "pmlab-map-stage-blind-advisory-v1"
CORPUS_FREEZE_COMMIT = "7481b44"
CORPUS_DIR = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
GLOBAL_LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"

CONTRACT_DECISIONS = {"accept", "typed_reject"}
REJECT_REASONS = {
    "none",
    "invalid_serialization",
    "missing_required_field",
    "non_source_span",
    "invalid_dependency",
    "unknown_catalog_id",
    "unsafe_unresolved_state",
}
ENTITY_ACTIONS = {
    "linked",
    "ambiguous_in_catalog",
    "missing_entity",
    "non_entity_phrase",
    "mention_not_detected",
}

SYSTEM_PROMPT = """You are a conservative blind annotation reviewer for a bilingual semantic-memory benchmark.
Return one valid JSON object and no prose. You do not know the author's labels, criticality, strata, model scores, or preferred architecture. Judge only the visible input and catalog.

For contract_span cases, candidate_payload is a synthetic object under review, not output from a model being scored. Check serialization, required fields, exact source spans, unique sequential obligation IDs, backward dependencies, catalog IDs, and safe unresolved handling. Return:
{"decision":"accept|typed_reject","reject_reason":"none|invalid_serialization|missing_required_field|non_source_span|invalid_dependency|unknown_catalog_id|unsafe_unresolved_state"}

For entity_linking cases, distinguish:
- linked: visible context supports one catalog entity, a supplied ref:O# coreference, or a visible multi-entity list;
- ambiguous_in_catalog: two or more catalog entries remain plausible;
- missing_entity: the phrase denotes a real entity in context but its referent is absent from this catalog;
- non_entity_phrase: the highlighted phrase is not an entity mention in context;
- mention_not_detected: no valid mention span was supplied.
Return exactly:
{"action":"linked|ambiguous_in_catalog|missing_entity|non_entity_phrase|mention_not_detected","candidate_ids":["catalog ids"],"selected_id":"catalog id or ref:O# or null","selected_ids":["catalog ids"]}
Always include selected_ids; use [] except for a true multi-entity selection. Candidate IDs contain every plausible catalog entry and no invented IDs.

Output exactly:
{"results":[{"case_id":"exact id","independent_label":{},"confidence":"high|medium|low","case_validity":"valid|minor_issue|material_issue|exclude","disputed_field":"field name or null","rationale":"brief evidence-based reason"}]}

Label PL and EN rows independently. Do not force them to match. A translation mismatch should be reflected in labels or case_validity. Never infer hidden facts or use outside knowledge to add a catalog entity."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def build_jobs(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    forbidden = {"gold", "criticality", "split", "stratum", "provenance", "evaluation_metadata"}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in queue:
        text = canonical(row)
        if any(f'"{field}"' in text for field in forbidden):
            raise ValueError(f"review queue leaks forbidden field in {row.get('case_id')}")
        group_id = row["case_id"].rsplit("-", 1)[0]
        groups[group_id].append(
            {
                "case_id": row["case_id"],
                "language": row["language"],
                "stage": row["stage"],
                "input": row["input"],
            }
        )
    jobs = []
    for group_id in sorted(groups):
        cases = sorted(groups[group_id], key=lambda item: item["language"])
        if len(cases) != 2 or {item["language"] for item in cases} != {"en", "pl"}:
            raise ValueError(f"{group_id}: expected one EN and one PL case")
        if len({item["stage"] for item in cases}) != 1:
            raise ValueError(f"{group_id}: mixed stages")
        jobs.append({"job_id": group_id, "stage": cases[0]["stage"], "cases": cases})
    return jobs


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    queue = shared.read_jsonl(CORPUS_DIR / "independent-review-queue.jsonl")
    jobs = build_jobs(queue)
    shared.write_jsonl(RUN_DIR / "jobs.jsonl", jobs)
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "run_id": RUN_ID,
        "status": "prepared-uncommitted-input",
        "created_at": utc_now(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "corpus_freeze_commit": CORPUS_FREEZE_COMMIT,
        "prompt_freeze_commit": None,
        "semantic_groups": len(jobs),
        "cases": sum(len(job["cases"]) for job in jobs),
        "temperature": 0,
        "thinking": "disabled",
        "response_format": "json_object",
        "hard_cumulative_budget_usd": 10.0,
        "visible_to_worker": ["blind review cases", "entity catalog"],
        "hidden_from_worker": ["gold", "criticality", "stratum", "split", "provenance", "scores", "candidate implementation"],
        "authority": "advisory blind worker; not independent corpus review; cannot change gold",
        "hashes": {
            "jobs.jsonl": sha256(RUN_DIR / "jobs.jsonl"),
            "prompt.txt": sha256(RUN_DIR / "prompt.txt"),
            "independent-review-queue.jsonl": sha256(CORPUS_DIR / "independent-review-queue.jsonl"),
            "entity-catalog-v1.json": sha256(CORPUS_DIR / "entity-catalog-v1.json"),
        },
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(prompt_freeze_commit: str) -> dict[str, Any]:
    manifest_path = RUN_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("manifest is not awaiting freeze")
    git_output("cat-file", "-e", f"{prompt_freeze_commit}^{{commit}}")
    for name in ("jobs.jsonl", "prompt.txt"):
        committed = subprocess.check_output(
            ["git", "show", f"{prompt_freeze_commit}:data/lab/api-screening/{RUN_ID}/{name}"],
            cwd=ROOT,
        )
        if hashlib.sha256(committed).hexdigest() != manifest["hashes"][name]:
            raise ValueError(f"{name} is not identical in prompt freeze commit")
    manifest["prompt_freeze_commit"] = prompt_freeze_commit
    manifest["status"] = "frozen-input-awaiting-api"
    shared.write_json(manifest_path, manifest)
    return manifest


def verify_frozen_inputs() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "api-run-incomplete"}:
        raise ValueError(f"run input is not frozen: {manifest['status']}")
    paths = {
        "jobs.jsonl": RUN_DIR / "jobs.jsonl",
        "prompt.txt": RUN_DIR / "prompt.txt",
        "independent-review-queue.jsonl": CORPUS_DIR / "independent-review-queue.jsonl",
        "entity-catalog-v1.json": CORPUS_DIR / "entity-catalog-v1.json",
    }
    for name, path in paths.items():
        if sha256(path) != manifest["hashes"][name]:
            raise ValueError(f"frozen input mismatch: {name}")
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


def validate_label(result: dict[str, Any], case: dict[str, Any], catalog_ids: set[str]) -> dict[str, Any]:
    if result.get("case_id") != case["case_id"]:
        raise ValueError("case ID mismatch")
    if result.get("confidence") not in {"high", "medium", "low"}:
        raise ValueError("invalid confidence")
    if result.get("case_validity") not in {"valid", "minor_issue", "material_issue", "exclude"}:
        raise ValueError("invalid case_validity")
    if result.get("disputed_field") is not None and not isinstance(result.get("disputed_field"), str):
        raise ValueError("disputed_field must be string or null")
    if not isinstance(result.get("rationale"), str) or not result["rationale"].strip():
        raise ValueError("rationale must be nonempty")
    label = result.get("independent_label")
    if not isinstance(label, dict):
        raise ValueError("independent_label must be an object")
    if case["stage"] == "contract_span":
        if set(label) != {"decision", "reject_reason"}:
            raise ValueError("contract label has wrong fields")
        if label["decision"] not in CONTRACT_DECISIONS or label["reject_reason"] not in REJECT_REASONS:
            raise ValueError("invalid contract label")
        if label["decision"] == "accept" and label["reject_reason"] != "none":
            raise ValueError("accepted contract must use reject_reason none")
        if label["decision"] == "typed_reject" and label["reject_reason"] == "none":
            raise ValueError("typed rejection requires a reason")
    else:
        if set(label) != {"action", "candidate_ids", "selected_id", "selected_ids"}:
            raise ValueError("entity label has wrong fields")
        if label["action"] not in ENTITY_ACTIONS:
            raise ValueError("invalid entity action")
        if not isinstance(label["candidate_ids"], list) or not isinstance(label["selected_ids"], list):
            raise ValueError("candidate_ids and selected_ids must be arrays")
        if set(label["candidate_ids"]) - catalog_ids or set(label["selected_ids"]) - catalog_ids:
            raise ValueError("unknown catalog ID")
        selected = label["selected_id"]
        if selected is not None and selected not in catalog_ids and not (isinstance(selected, str) and selected.startswith("ref:O")):
            raise ValueError("invalid selected_id")
        if label["action"] != "linked" and (selected is not None or label["selected_ids"]):
            raise ValueError("unresolved entity action cannot select an entity")
    return result


def batches(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def run(env_file: Path, budget_usd: float, batch_size: int, max_tokens: int, timeout: float) -> dict[str, Any]:
    if not 0 < budget_usd <= 10:
        raise ValueError("budget must be greater than zero and at most USD 10")
    manifest = verify_frozen_inputs()
    api_key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    jobs = shared.read_jsonl(RUN_DIR / "jobs.jsonl")
    catalog = json.loads((CORPUS_DIR / "entity-catalog-v1.json").read_text(encoding="utf-8"))
    catalog_ids = {item["id"] for item in catalog["entities"]}
    predictions_path = RUN_DIR / "predictions.jsonl"
    completed = {row["case_id"] for row in shared.read_jsonl(predictions_path)}
    pending_jobs = [job for job in jobs if any(case["case_id"] not in completed for case in job["cases"])]
    calls = 0
    for batch in batches(pending_jobs, batch_size):
        cases = [case for job in batch for case in job["cases"] if case["case_id"] not in completed]
        user_payload = {
            "instruction": "Review every case independently and return exactly one result per case_id.",
            "catalog": catalog,
            "semantic_groups": [{"job_id": job["job_id"], "stage": job["stage"], "cases": [case for case in job["cases"] if case in cases]} for job in batch],
        }
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]
        before = shared.ledger_total()
        preflight = shared.estimated_request_cost(messages, max_tokens)
        if before + preflight > budget_usd:
            raise RuntimeError(f"hard cumulative budget would be exceeded: {before:.6f} + {preflight:.6f} > {budget_usd:.2f}")
        started = time.perf_counter()
        try:
            response = request_payload(api_key, messages, timeout, max_tokens)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            usage = response.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            completion_tokens = int(usage.get("completion_tokens") or 0)
            cost = shared.conservative_cost(prompt_tokens, completion_tokens)
            ledger = {
                "at": utc_now(),
                "run_id": RUN_ID,
                "model": response.get("model", MODEL),
                "response_id": response.get("id", ""),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "conservative_cost_usd": round(cost, 8),
                "pricing_basis": "all input charged at configured peak cache-miss rate",
            }
            shared.append_jsonl(GLOBAL_LEDGER, ledger)
            case_ids = [case["case_id"] for case in cases]
            shared.append_jsonl(RUN_DIR / "calls.jsonl", {**ledger, "latency_ms": latency_ms, "case_ids": case_ids})
            content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            shared.append_jsonl(RUN_DIR / "raw-responses.jsonl", {"at": utc_now(), "response_id": response.get("id", ""), "case_ids": case_ids, "content": content})
            parsed = json.loads(content)
            results = parsed.get("results")
            if not isinstance(results, list):
                raise ValueError("response has no results array")
            by_id = {row.get("case_id"): row for row in results if isinstance(row, dict)}
            for case in cases:
                case_id = case["case_id"]
                if case_id not in by_id:
                    shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at": utc_now(), "case_id": case_id, "error_type": "missing-result", "error": "case_id absent from response"})
                    continue
                try:
                    validated = validate_label(by_id[case_id], case, catalog_ids)
                except ValueError as exc:
                    shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at": utc_now(), "case_id": case_id, "error_type": "result-validation", "error": str(exc), "raw_result": by_id[case_id]})
                    continue
                shared.append_jsonl(predictions_path, {**validated, "model": response.get("model", MODEL), "prompt_version": PROMPT_VERSION, "reviewed_at": utc_now()})
                completed.add(case_id)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at": utc_now(), "case_ids": [case["case_id"] for case in cases], "error_type": type(exc).__name__, "error": str(exc)})
        calls += 1
    predictions = shared.read_jsonl(predictions_path)
    status = "api-run-complete" if len({row["case_id"] for row in predictions}) == manifest["cases"] else "api-run-incomplete"
    manifest["status"] = status
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    summary = {
        "status": status,
        "model": MODEL,
        "cases": manifest["cases"],
        "valid_predictions": len(predictions),
        "valid_rate": len(predictions) / manifest["cases"],
        "errors_logged": len(shared.read_jsonl(RUN_DIR / "errors.jsonl")),
        "calls_this_invocation": calls,
        "run_conservative_cost_usd": round(sum(float(row["conservative_cost_usd"]) for row in shared.read_jsonl(GLOBAL_LEDGER) if row.get("run_id") == RUN_ID), 8),
        "all_runs_conservative_cost_usd": shared.ledger_total(),
        "hard_cumulative_budget_usd": budget_usd,
        "authority": "advisory only; no independent-review status",
    }
    shared.write_json(RUN_DIR / "api-summary.json", summary)
    return summary


def normalized_label(label: dict[str, Any]) -> dict[str, Any]:
    value = dict(label)
    if "selected_ids" not in value:
        value["selected_ids"] = []
    return value


def adjudicate() -> dict[str, Any]:
    verify_frozen_inputs()
    cases = {row["case_id"]: row for row in shared.read_jsonl(CORPUS_DIR / "cases.jsonl")}
    predictions = {row["case_id"]: row for row in shared.read_jsonl(RUN_DIR / "predictions.jsonl")}
    rows = []
    for case_id in sorted(cases):
        case = cases[case_id]
        prediction = predictions.get(case_id)
        if prediction is None:
            rows.append({"case_id": case_id, "stage": case["stage"], "language": case["language"], "criticality": case["criticality"], "status": "missing_prediction", "exact_agreement": False})
            continue
        gold = normalized_label(case["gold"])
        proposed = normalized_label(prediction["independent_label"])
        rows.append(
            {
                "case_id": case_id,
                "semantic_group_id": case["semantic_group_id"],
                "stage": case["stage"],
                "language": case["language"],
                "criticality": case["criticality"],
                "gold": gold,
                "advisory_label": proposed,
                "exact_agreement": canonical(gold) == canonical(proposed),
                "confidence": prediction["confidence"],
                "case_validity": prediction["case_validity"],
                "disputed_field": prediction["disputed_field"],
                "rationale": prediction["rationale"],
                "authority": "advisory-model-disagreement-only",
            }
        )
    shared.write_jsonl(RUN_DIR / "comparison.jsonl", rows)
    group_predictions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("semantic_group_id"):
            group_predictions[row["semantic_group_id"]].append(row)
    parity = {
        group: len(items) == 2 and canonical(items[0].get("advisory_label")) == canonical(items[1].get("advisory_label"))
        for group, items in group_predictions.items()
    }
    valid = [row for row in rows if row["status"] != "missing_prediction"] if rows and "status" in rows[0] else [row for row in rows if "advisory_label" in row]
    exact = [row for row in rows if row.get("exact_agreement")]
    critical = [row for row in rows if row["criticality"] == "critical"]
    summary = {
        "status": "advisory-comparison-complete" if len(predictions) == len(cases) else "advisory-comparison-incomplete",
        "cases": len(cases),
        "predictions": len(predictions),
        "exact_agreement": len(exact),
        "exact_agreement_rate": len(exact) / len(cases),
        "critical_exact_agreement": sum(bool(row.get("exact_agreement")) for row in critical),
        "critical_cases": len(critical),
        "critical_exact_agreement_rate": sum(bool(row.get("exact_agreement")) for row in critical) / len(critical),
        "bilingual_groups_with_matching_advisory_labels": sum(parity.values()),
        "bilingual_groups": len(parity),
        "case_validity_counts": dict(Counter(row.get("case_validity", "missing") for row in rows)),
        "by_stage": {
            stage: {
                "cases": len(stage_rows),
                "exact": sum(bool(row.get("exact_agreement")) for row in stage_rows),
                "rate": sum(bool(row.get("exact_agreement")) for row in stage_rows) / len(stage_rows),
            }
            for stage, stage_rows in ((stage, [row for row in rows if row["stage"] == stage]) for stage in sorted({row["stage"] for row in rows}))
        },
        "authority": "disagreement queue only; human/independent review still required",
        "gold_mutated": False,
    }
    shared.write_json(RUN_DIR / "comparison-summary.json", summary)
    disagreements = [row for row in rows if not row.get("exact_agreement")]
    report = [
        "# PMLAB-MAP stage blind advisory review",
        "",
        "Status: DeepSeek advisory disagreement queue; not independent corpus review",
        "",
        f"- valid predictions: {len(predictions)}/{len(cases)};",
        f"- exact agreement with authored gold: {len(exact)}/{len(cases)} ({summary['exact_agreement_rate']:.3f});",
        f"- critical exact agreement: {summary['critical_exact_agreement']}/{len(critical)} ({summary['critical_exact_agreement_rate']:.3f});",
        f"- bilingual advisory parity: {sum(parity.values())}/{len(parity)} groups;",
        f"- disagreement rows: {len(disagreements)}.",
        "",
        "The model saw no gold labels, criticality, strata, scores, author rationale, or candidate implementation. Agreement is not proof of label validity, and disagreement does not automatically replace gold. Every disagreement remains an adjudication target; human or otherwise genuinely independent review is still required by the frozen protocol.",
        "",
        "## Disagreement queue",
        "",
    ]
    if not disagreements:
        report.append("No exact-label disagreements were produced.")
    else:
        for row in disagreements:
            report.append(f"- `{row['case_id']}` ({row['stage']}, {row['criticality']}): {row.get('disputed_field') or 'exact label'} — {row.get('rationale', 'missing prediction')}")
    (RUN_DIR / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    return summary


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    freezer = commands.add_parser("freeze")
    freezer.add_argument("--prompt-freeze-commit", required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    runner.add_argument("--budget-usd", type=float, default=10.0)
    runner.add_argument("--batch-size", type=int, default=3)
    runner.add_argument("--max-tokens", type=int, default=5000)
    runner.add_argument("--timeout", type=float, default=120.0)
    commands.add_parser("adjudicate")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "prepare":
        result = prepare()
    elif args.command == "freeze":
        result = freeze(args.prompt_freeze_commit)
    elif args.command == "run":
        result = run(args.env_file, args.budget_usd, args.batch_size, args.max_tokens, args.timeout)
    else:
        result = adjudicate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
