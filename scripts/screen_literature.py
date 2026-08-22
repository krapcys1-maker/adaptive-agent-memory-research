#!/usr/bin/env python3
"""Prepare and run review-gated literature screening with a strict API budget.

The worker reads only public metadata already present in the discovery catalog.
Its outputs are candidates for human/source review, never accepted evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "catalogs" / "papers-discovered.csv"
OUTPUT_ROOT = ROOT / "data" / "lab" / "api-screening"
BUDGET_LEDGER = OUTPUT_ROOT / "budget-ledger.jsonl"
MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
PROMPT_VERSION = "screening-v2"

# Conservative peak prices observed in the official pricing page on 2026-08-22.
# All prompt tokens are charged as cache misses for the hard-cap estimate.
INPUT_PRICE_PER_MILLION_USD = 0.44
OUTPUT_PRICE_PER_MILLION_USD = 1.32

PROFILES = {
    "cls_replay": {
        "labels": {"human-consolidation", "sleep-awake-replay", "continual-learning-replay"},
        "brief": "fast/slow complementary learning, replay selection, consolidation, interference, and harmful replay",
    },
    "allocation_salience": {
        "labels": {"memory-allocation-engram", "neuromodulated-memory", "human-salience"},
        "brief": "competitive memory allocation and separable effects of arousal, valence, reward, surprise, stress, and consequence",
    },
    "semantic_compression": {
        "labels": {"semantic-memory-compression"},
        "brief": "rate-distortion, information bottleneck, semantic compression, decision loss, and reconstructive distortion",
    },
    "prospective_metamemory": {
        "labels": {
            "prospective-memory-offloading",
            "memory-metacognition",
            "metamemory-monitoring",
            "retrieval-control",
            "source-monitoring-confidence",
            "human-metamemory",
        },
        "brief": "prospective intentions, condition-triggered reminders, cognitive offloading, confidence, retrieval control, and abstention",
    },
    "durable_storage": {
        "labels": {"storage-crash-consistency", "temporal-provenance-storage"},
        "brief": "journaling, atomicity, checksums, fault injection, temporal validity, provenance, and recoverable versioning",
    },
}

SYSTEM_PROMPT = """You are a conservative literature librarian screening public metadata.
Return one valid JSON object and no prose. Never treat an abstract as verified evidence.
Do not invent methods, results, citations, page numbers, or evidence locators.
Classify only relevance for full-source review. Use 'unknown' when metadata is insufficient.
If an abstract is missing or non-informative, the decision must be 'maybe' or 'exclude', never 'include'.

JSON shape:
{
  "results": [
    {
      "job_id": "exact input job_id",
      "decision": "include|maybe|exclude",
      "relevance": 0,
      "source_type_guess": "primary|review|theory|methods|benchmark|other|unknown",
      "mechanism_classes": ["short labels"],
      "direct_relevance": "one short sentence",
      "critical_boundary": "one short limitation or unknown",
      "adversarial_search_terms": ["up to three short terms"],
      "reason": "one short screening reason"
    }
  ]
}

Relevance: 3 directly tests the profile mechanism; 2 materially informs it; 1 adjacent;
0 irrelevant. 'include' normally requires 3, 'maybe' normally requires 1-2.
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                values.append(json.loads(line))
    return values


def load_env_value(path: Path, name: str) -> str:
    existing = os.environ.get(name, "").strip()
    if existing:
        return existing
    if not path.exists():
        return ""
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            return value
    return ""


def catalog_rows() -> list[dict[str, str]]:
    with CATALOG_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def stable_key(row: dict[str, str]) -> str:
    identity = row.get("doi") or row.get("openalex_id") or row.get("title", "")
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def balanced_selection(rows: list[dict[str, str]], count: int) -> list[dict[str, str]]:
    """Mix highly cited, recent, and deterministic-hash candidates."""
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(candidates: list[dict[str, str]], limit: int) -> None:
        for row in candidates:
            identity = row.get("doi") or row.get("openalex_id") or row.get("title", "")
            if not identity or identity in seen:
                continue
            selected.append(row)
            seen.add(identity)
            if len(selected) >= limit:
                return

    cited = sorted(rows, key=lambda row: int(row.get("cited_by_count") or 0), reverse=True)
    recent = sorted(
        rows,
        key=lambda row: (int(row.get("year") or 0), int(row.get("cited_by_count") or 0)),
        reverse=True,
    )
    hashed = sorted(rows, key=stable_key)
    first = max(1, math.ceil(count / 3))
    second = max(first, math.ceil(2 * count / 3))
    add(cited, first)
    add(recent, second)
    add(hashed, count)
    return selected[:count]


def prepare(run_id: str, per_profile: int) -> dict[str, Any]:
    run_dir = OUTPUT_ROOT / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError(f"run directory is not empty: {run_dir}")
    rows = catalog_rows()
    jobs: list[dict[str, Any]] = []
    for profile, configuration in PROFILES.items():
        candidates = [
            row
            for row in rows
            if set(filter(None, row.get("discovery_queries", "").split(";")))
            & configuration["labels"]
        ]
        for index, row in enumerate(balanced_selection(candidates, per_profile), start=1):
            jobs.append(
                {
                    "job_id": f"{profile}-{index:03d}",
                    "profile": profile,
                    "profile_brief": configuration["brief"],
                    "source_id": row.get("openalex_id", ""),
                    "doi": row.get("doi", ""),
                    "title": row.get("title", ""),
                    "year": row.get("year", ""),
                    "type": row.get("type", ""),
                    "authors": row.get("authors", ""),
                    "venue": row.get("venue", ""),
                    "cited_by_count": row.get("cited_by_count", ""),
                    "discovery_queries": row.get("discovery_queries", ""),
                    "abstract": row.get("abstract", ""),
                    "content_hash": hashlib.sha256(
                        (row.get("title", "") + "\n" + row.get("abstract", "")).encode("utf-8")
                    ).hexdigest(),
                }
            )
    if len(jobs) != per_profile * len(PROFILES):
        raise ValueError(f"expected {per_profile * len(PROFILES)} jobs, prepared {len(jobs)}")
    jobs_path = run_dir / "jobs.jsonl"
    for job in jobs:
        append_jsonl(jobs_path, job)
    jobs_hash = hashlib.sha256(jobs_path.read_bytes()).hexdigest()
    manifest = {
        "run_id": run_id,
        "created_at": utc_now(),
        "status": "frozen-input",
        "catalog": str(CATALOG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "catalog_sha256": hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest(),
        "jobs": len(jobs),
        "jobs_sha256": jobs_hash,
        "per_profile": per_profile,
        "profiles": {
            name: {"labels": sorted(configuration["labels"]), "brief": configuration["brief"]}
            for name, configuration in PROFILES.items()
        },
        "prompt_version": PROMPT_VERSION,
        "model": MODEL,
        "thinking": "disabled",
        "temperature": 0,
        "data_class": "public bibliographic metadata and abstracts",
        "authority": "screening candidates only; no accepted evidence",
        "pricing_assumption_usd_per_million": {
            "input_all_cache_miss": INPUT_PRICE_PER_MILLION_USD,
            "output": OUTPUT_PRICE_PER_MILLION_USD,
        },
    }
    write_json(run_dir / "manifest.json", manifest)
    return manifest


def conservative_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens * INPUT_PRICE_PER_MILLION_USD
        + completion_tokens * OUTPUT_PRICE_PER_MILLION_USD
    ) / 1_000_000


def ledger_total() -> float:
    return round(sum(float(row.get("conservative_cost_usd", 0)) for row in read_jsonl(BUDGET_LEDGER)), 8)


def estimated_request_cost(messages: list[dict[str, str]], max_tokens: int) -> float:
    characters = sum(len(message["content"]) for message in messages)
    conservative_prompt_tokens = math.ceil(characters / 2)
    return conservative_cost(conservative_prompt_tokens, max_tokens)


def api_call(api_key: str, jobs: list[dict[str, Any]], timeout: float, max_tokens: int) -> dict[str, Any]:
    user_payload = {
        "profile": jobs[0]["profile"],
        "profile_brief": jobs[0]["profile_brief"],
        "instruction": "Screen every item and return JSON with one result per exact job_id.",
        "items": [
            {
                "job_id": job["job_id"],
                "source_id": job["source_id"],
                "doi": job["doi"],
                "title": job["title"],
                "year": job["year"],
                "type": job["type"],
                "venue": job["venue"],
                "abstract": job["abstract"],
            }
            for job in jobs
        ],
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]
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


def validate_results(content: str, expected_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = json.loads(content)
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("response does not contain a results array")
    expected = {job["job_id"] for job in expected_jobs}
    received = {result.get("job_id") for result in results if isinstance(result, dict)}
    if received != expected or len(results) != len(expected):
        raise ValueError(f"job ids mismatch: expected {sorted(expected)}, received {sorted(str(v) for v in received)}")
    normalized: list[dict[str, Any]] = []
    for result in results:
        if result.get("decision") not in {"include", "maybe", "exclude"}:
            raise ValueError(f"invalid decision for {result.get('job_id')}")
        relevance = result.get("relevance")
        if not isinstance(relevance, int) or relevance not in {0, 1, 2, 3}:
            raise ValueError(f"invalid relevance for {result.get('job_id')}")
        normalized.append(result)
    return normalized


def apply_deterministic_policy(candidate: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    normalized["model_decision"] = candidate.get("decision")
    normalized["model_relevance"] = candidate.get("relevance")
    overrides: list[str] = []
    if not str(job.get("abstract", "")).strip() and candidate.get("decision") == "include":
        normalized["decision"] = "maybe"
        normalized["relevance"] = min(int(candidate.get("relevance") or 0), 2)
        overrides.append("missing-abstract-cannot-include")
    normalized["policy_overrides"] = overrides
    normalized["review_state"] = "policy-normalized-unreviewed"
    return normalized


def run(
    run_id: str,
    env_file: Path,
    budget_usd: float,
    batch_size: int,
    max_tokens: int,
    timeout: float,
) -> dict[str, Any]:
    if budget_usd <= 0 or budget_usd > 10:
        raise ValueError("budget must be greater than 0 and no more than 10 USD")
    api_key = load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing")
    run_dir = OUTPUT_ROOT / run_id
    manifest_path = run_dir / "manifest.json"
    jobs_path = run_dir / "jobs.jsonl"
    if not manifest_path.exists() or not jobs_path.exists():
        raise ValueError("prepare and freeze the run before calling the API")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if hashlib.sha256(jobs_path.read_bytes()).hexdigest() != manifest["jobs_sha256"]:
        raise ValueError("jobs file does not match the frozen manifest")
    jobs = read_jsonl(jobs_path)
    candidates_path = run_dir / "candidates.jsonl"
    review_queue_path = run_dir / "review-queue.jsonl"
    calls_path = run_dir / "calls.jsonl"
    errors_path = run_dir / "errors.jsonl"
    completed = {row["job_id"] for row in read_jsonl(candidates_path)}
    pending = [job for job in jobs if job["job_id"] not in completed]
    calls = 0
    batches: list[list[dict[str, Any]]] = []
    for profile in PROFILES:
        profile_jobs = [job for job in pending if job["profile"] == profile]
        batches.extend(
            profile_jobs[start : start + batch_size]
            for start in range(0, len(profile_jobs), batch_size)
        )
    for batch in batches:
        user_content = json.dumps(
            {"profile": batch[0]["profile"], "profile_brief": batch[0]["profile_brief"], "items": batch},
            ensure_ascii=False,
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_content}]
        preflight = estimated_request_cost(messages, max_tokens)
        before = ledger_total()
        if before + preflight > budget_usd:
            raise RuntimeError(
                f"hard budget would be exceeded: spent {before:.6f}, next worst case {preflight:.6f}, cap {budget_usd:.2f}"
            )
        started = time.perf_counter()
        try:
            response = api_call(api_key, batch, timeout, max_tokens)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            append_jsonl(
                errors_path,
                {"at": utc_now(), "job_ids": [job["job_id"] for job in batch], "error_type": type(exc).__name__, "error": str(exc)},
            )
            continue
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        usage = response.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        cost = conservative_cost(prompt_tokens, completion_tokens)
        ledger_entry = {
            "at": utc_now(),
            "run_id": run_id,
            "model": response.get("model", MODEL),
            "response_id": response.get("id", ""),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "conservative_cost_usd": round(cost, 8),
            "pricing_basis": "all input charged at configured peak cache-miss rate",
        }
        append_jsonl(BUDGET_LEDGER, ledger_entry)
        append_jsonl(
            calls_path,
            {
                **ledger_entry,
                "latency_ms": elapsed_ms,
                "job_ids": [job["job_id"] for job in batch],
                "system_fingerprint": response.get("system_fingerprint", ""),
                "finish_reason": ((response.get("choices") or [{}])[0]).get("finish_reason", ""),
            },
        )
        try:
            content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            results = validate_results(content, batch)
            jobs_by_id = {job["job_id"]: job for job in batch}
            for result in results:
                job = jobs_by_id[result["job_id"]]
                append_jsonl(
                    candidates_path,
                    {
                        **result,
                        "profile": job["profile"],
                        "source_id": job["source_id"],
                        "doi": job["doi"],
                        "title": job["title"],
                        "content_hash": job["content_hash"],
                        "screened_at": utc_now(),
                        "model": response.get("model", MODEL),
                        "prompt_version": PROMPT_VERSION,
                        "review_state": "model-candidate-unreviewed",
                    },
                )
        except (json.JSONDecodeError, ValueError) as exc:
            append_jsonl(
                errors_path,
                {"at": utc_now(), "job_ids": [job["job_id"] for job in batch], "error_type": "response-validation", "error": str(exc)},
            )
        calls += 1
    candidates = read_jsonl(candidates_path)
    errors = read_jsonl(errors_path)
    all_jobs_by_id = {job["job_id"]: job for job in jobs}
    review_queue = [apply_deterministic_policy(row, all_jobs_by_id[row["job_id"]]) for row in candidates]
    write_jsonl(review_queue_path, review_queue)
    summary = {
        "run_id": run_id,
        "finished_at": utc_now(),
        "jobs": len(jobs),
        "candidate_outputs": len(candidates),
        "review_queue_outputs": len(review_queue),
        "schema_valid_rate": round(len(candidates) / len(jobs), 4) if jobs else 0,
        "calls_this_invocation": calls,
        "errors": len(errors),
        "decisions": {
            decision: sum(1 for row in review_queue if row.get("decision") == decision)
            for decision in ("include", "maybe", "exclude")
        },
        "policy_overrides": sum(1 for row in review_queue if row.get("policy_overrides")),
        "run_conservative_cost_usd": round(
            sum(float(row.get("conservative_cost_usd", 0)) for row in read_jsonl(BUDGET_LEDGER) if row.get("run_id") == run_id),
            8,
        ),
        "all_runs_conservative_cost_usd": ledger_total(),
        "hard_budget_usd": budget_usd,
        "authority": "model candidates only; source-level review required",
    }
    write_json(run_dir / "summary.json", summary)
    return summary


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Budgeted DeepSeek literature-screening worker")
    commands = root.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--run-id", required=True)
    prepare_parser.add_argument("--per-profile", type=int, default=5)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    run_parser.add_argument("--budget-usd", type=float, default=10.0)
    run_parser.add_argument("--batch-size", type=int, default=5)
    run_parser.add_argument("--max-tokens", type=int, default=1800)
    run_parser.add_argument("--timeout", type=float, default=120.0)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.run_id, max(1, min(args.per_profile, 40)))
        else:
            result = run(
                args.run_id,
                args.env_file,
                args.budget_usd,
                max(1, min(args.batch_size, 10)),
                max(300, min(args.max_tokens, 5000)),
                args.timeout,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
