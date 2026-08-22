#!/usr/bin/env python3
"""Verify source identity for screening candidates without using an LLM."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "adaptive-agent-memory-research/0.1 (public research source audit)"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(character for character in value if unicodedata.category(character) != "Mn")
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def title_similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, normalize_title(left), normalize_title(right)).ratio()


def fetch_json(url: str, accept: str = "application/json", attempts: int = 3) -> tuple[dict[str, Any] | None, str]:
    last_error = ""
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8")), ""
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    return None, last_error


def csl_title(metadata: dict[str, Any]) -> str:
    title = metadata.get("title", "")
    if isinstance(title, list):
        return str(title[0]) if title else ""
    return str(title)


def audit_record(row: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    doi_url = row.get("doi", "")
    doi = doi_url.removeprefix("https://doi.org/").strip()
    csl = None
    csl_error = ""
    if doi:
        csl, csl_error = fetch_json(
            f"https://doi.org/{doi}",
            accept="application/vnd.citationstyles.csl+json",
        )

    openalex_id = row["source_id"].rstrip("/").split("/")[-1]
    openalex, openalex_error = fetch_json(f"https://api.openalex.org/works/{openalex_id}")
    registered_title = csl_title(csl) if csl else ""
    if not registered_title and openalex:
        registered_title = str(openalex.get("title", ""))
    similarity = title_similarity(row["title"], registered_title) if registered_title else 0.0
    if csl and similarity >= 0.9:
        status = "doi-title-verified"
    elif csl and similarity >= 0.65:
        status = "doi-possible-version"
    elif csl:
        status = "doi-title-mismatch"
    elif openalex and similarity >= 0.9:
        status = "openalex-title-verified-no-doi"
    elif openalex:
        status = "openalex-title-mismatch"
    else:
        status = "unresolved"

    primary_location = (openalex or {}).get("primary_location") or {}
    best_oa = (openalex or {}).get("best_oa_location") or {}
    return {
        "job_id": row["job_id"],
        "profile": row["profile"],
        "screening_title": row["title"],
        "registered_title": registered_title,
        "doi": doi,
        "source_id": row["source_id"],
        "identity_status": status,
        "title_similarity": round(similarity, 4),
        "work_type": (csl or {}).get("type") or (openalex or {}).get("type", ""),
        "publication_date": (openalex or {}).get("publication_date", ""),
        "primary_url": primary_location.get("landing_page_url", ""),
        "open_access_url": best_oa.get("landing_page_url", ""),
        "is_retracted": (openalex or {}).get("is_retracted"),
        "abstract_present": bool(job.get("abstract", "").strip()),
        "doi_metadata_error": csl_error,
        "openalex_error": openalex_error,
        "audit_authority": "identity metadata only; not evidence or full-text review",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queue",
        type=Path,
        default=Path("data/lab/api-screening/deepseek-v4-flash-screening-125-20260822/review-queue.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/lab/api-screening/deepseek-v4-flash-screening-125-20260822/source-identity-audit.jsonl"),
    )
    parser.add_argument(
        "--jobs",
        type=Path,
        default=Path("data/lab/api-screening/deepseek-v4-flash-screening-125-20260822/jobs.jsonl"),
    )
    args = parser.parse_args()
    rows = [row for row in load_jsonl(args.queue) if row["decision"] == "include"]
    jobs = {row["job_id"]: row for row in load_jsonl(args.jobs)}
    audited = [audit_record(row, jobs[row["job_id"]]) for row in rows]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in audited:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    counts: dict[str, int] = {}
    for row in audited:
        counts[row["identity_status"]] = counts.get(row["identity_status"], 0) + 1
    print(json.dumps({"audited": len(audited), "identity_status": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
