#!/usr/bin/env python3
"""Label-free byte/token inventory from an exact Git snapshot; never builds a retrieval corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "lab" / "pmlab-natural-history-v0" / "token-feasibility-v0"
MODEL_ROOT = ROOT / "external" / "models"
CEILINGS = (512, 768, 1024, 1536, 2048, 3072, 4096)
CATALOGS = {
    "data/catalogs/repositories-current.csv",
    "data/catalogs/repository-revisions.csv",
    "data/catalogs/dense-retrieval-candidates.csv",
    "docs/07-literature/evidence-ledger.csv",
}
MODELS = {
    "C1A_E5": {
        "path": MODEL_ROOT / "multilingual-e5-small", "revision": "614241f622f53c4eeff9890bdc4f31cfecc418b3",
        "prefix": "passage: ", "registered_limit": 512,
    },
    "C1B_BGE_M3": {
        "path": MODEL_ROOT / "bge-m3", "revision": "5617a9f61b028005a4858fdac845db406aefb181",
        "prefix": "", "registered_limit": 8192,
    },
    "C0_MINILM": {
        "path": MODEL_ROOT / "paraphrase-multilingual-MiniLM-L12-v2", "revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
        "prefix": "", "registered_limit": 128,
    },
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def trim_outer_blank(lines: list[str]) -> list[str]:
    start, end = 0, len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def markdown_units(text: str) -> list[dict[str, str]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    tokens = MarkdownIt("commonmark").parse(normalized)
    headings = []
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.map is None:
            continue
        inline = tokens[index + 1]
        headings.append({"level": int(token.tag[1:]), "title": inline.content.strip(), "start": token.map[0], "body_start": token.map[1]})
    result: list[dict[str, str]] = []
    first_start = headings[0]["start"] if headings else len(lines)
    preamble = trim_outer_blank(lines[:first_start])
    if preamble:
        result.append({"locator": "preamble#1", "search_text": "Preamble\n" + "\n".join(preamble)})
    stack: list[tuple[int, str]] = []
    occurrences: Counter[str] = Counter()
    for index, heading in enumerate(headings):
        stack = [item for item in stack if item[0] < heading["level"]]
        stack.append((heading["level"], heading["title"]))
        heading_path = " > ".join(item[1] for item in stack)
        occurrences[heading_path] += 1
        next_start = headings[index + 1]["start"] if index + 1 < len(headings) else len(lines)
        body = trim_outer_blank(lines[heading["body_start"]:next_start])
        search_text = heading_path + (("\n" + "\n".join(body)) if body else "")
        result.append({"locator": f"{heading_path}#{occurrences[heading_path]}", "search_text": search_text})
    if not headings and preamble:
        return result
    return result


def memory_event_text(row: dict[str, Any]) -> str:
    lines = [f"Title: {row.get('title', '')}", f"Summary: {row.get('summary', '')}"]
    if str(row.get("body") or "").strip():
        lines.append(f"Body: {row['body']}")
    tags = row.get("tags") or []
    if tags:
        lines.append("Tags: " + ", ".join(str(item) for item in tags))
    return "\n".join(lines)


def eligible_class(path: str) -> str | None:
    if path == "memory/CURRENT_STATE.md":
        return "registered_summary_secondary"
    if path in {"README.md", "START_HERE.md", "RESEARCH_PLAN.md", "CONTRIBUTING.md"} or (path.startswith("docs/") and path.endswith(".md")):
        return "canonical_research"
    if path == "memory/events.jsonl" or (path.startswith("memory/records/") and path.endswith(".md")):
        return "canonical_memory"
    if path in CATALOGS:
        return "reviewed_catalog"
    if path.startswith("data/lab/") and path.endswith(("/README.md", "/report.md")):
        lower = path.lower()
        forbidden = ("/blind/", "/artifacts/", "/raw/", "/api-screening/", "gold", "annotation")
        if not any(item in lower for item in forbidden):
            return "reviewed_lab_summary"
    return None


def snapshot_entries(commit: str) -> list[dict[str, str]]:
    raw = git("ls-tree", "-rz", "--full-tree", commit)
    entries = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, encoded_path = item.split(b"\t", 1)
        mode, object_type, object_id = meta.decode("ascii").split(" ")
        path = encoded_path.decode("utf-8")
        eligibility = eligible_class(path)
        if eligibility:
            entries.append({"mode": mode, "object_type": object_type, "object_id": object_id, "path": path, "eligibility_class": eligibility})
    return entries


def logical_units(commit: str) -> tuple[list[dict[str, str]], Counter[str]]:
    units = []
    exclusions: Counter[str] = Counter()
    for entry in snapshot_entries(commit):
        if entry["object_type"] != "blob" or entry["mode"] not in {"100644", "100755"}:
            exclusions["unsupported_git_entry"] += 1
            continue
        blob = git("show", f"{commit}:{entry['path']}")
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            exclusions["non_utf8"] += 1
            continue
        path = entry["path"]
        if path.endswith(".md"):
            for row in markdown_units(text):
                units.append({"source_type": "markdown_section", "eligibility_class": entry["eligibility_class"], **row})
        elif path == "memory/events.jsonl":
            for line_number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                units.append({
                    "source_type": "project_memory_event", "eligibility_class": entry["eligibility_class"],
                    "locator": str(row.get("id") or f"line-{line_number}"), "search_text": memory_event_text(row),
                })
        elif path.endswith(".csv"):
            reader = csv.reader(io.StringIO(text, newline=""))
            rows = list(reader)
            if not rows or len(set(rows[0])) != len(rows[0]):
                exclusions["csv_missing_or_duplicate_header"] += 1
                continue
            header = rows[0]
            for line_number, values in enumerate(rows[1:], start=2):
                if len(values) != len(header):
                    exclusions["csv_width_mismatch"] += 1
                    continue
                search_text = "\n".join(f"{name}: {value}" for name, value in zip(header, values))
                units.append({
                    "source_type": "catalog_row", "eligibility_class": entry["eligibility_class"],
                    "locator": f"row-{line_number}", "search_text": search_text,
                })
    return units, exclusions


def quantiles(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    def nearest(p: float) -> int:
        return ordered[min(len(ordered) - 1, max(0, round((len(ordered) - 1) * p)))]
    return {"min": ordered[0], "p50": nearest(0.50), "p90": nearest(0.90), "p95": nearest(0.95), "p99": nearest(0.99), "max": ordered[-1]}


def tokenizer_files(path: Path) -> dict[str, str]:
    return {
        file.relative_to(path).as_posix(): sha256_bytes(file.read_bytes())
        for file in sorted(path.rglob("*"))
        if file.is_file() and ".cache" not in file.parts
    }


def run(commit: str) -> dict[str, Any]:
    resolved_commit = git("rev-parse", f"{commit}^{{commit}}").decode("ascii").strip()
    units, exclusions = logical_units(resolved_commit)
    if not units:
        raise ValueError("no label-free logical units found")
    model_receipts = {}
    token_lengths: dict[str, list[int]] = {}
    for model_id, spec in MODELS.items():
        tokenizer = AutoTokenizer.from_pretrained(spec["path"], local_files_only=True, trust_remote_code=False)
        lengths = [len(tokenizer(spec["prefix"] + row["search_text"], add_special_tokens=True, truncation=False)["input_ids"]) for row in units]
        token_lengths[model_id] = lengths
        model_receipts[model_id] = {
            "revision": spec["revision"], "registered_limit": spec["registered_limit"], "prefix": spec["prefix"],
            "tokenizer_class": tokenizer.__class__.__name__, "files": tokenizer_files(spec["path"]),
        }
    byte_lengths = [len(row["search_text"].encode("utf-8")) for row in units]
    by_class = Counter(row["eligibility_class"] for row in units)
    by_type = Counter(row["source_type"] for row in units)
    ceiling_rows = []
    for ceiling in CEILINGS:
        selected = [index for index, size in enumerate(byte_lengths) if size <= ceiling]
        ceiling_rows.append({
            "utf8_byte_ceiling": ceiling,
            "unsplit_logical_units_within": len(selected),
            "unsplit_fraction_within": len(selected) / len(units),
            "observed_unsplit_token_checks": {
                model_id: {
                    "max_tokens": max((token_lengths[model_id][index] for index in selected), default=0),
                    "over_registered_limit": sum(token_lengths[model_id][index] > MODELS[model_id]["registered_limit"] for index in selected),
                }
                for model_id in MODELS
            },
        })
    summary = {
        "status": "label-free-logical-unit-and-tokenizer-feasibility-only-no-ceiling-selected",
        "snapshot_commit": resolved_commit, "logical_units": len(units),
        "counts_by_eligibility_class": dict(sorted(by_class.items())), "counts_by_source_type": dict(sorted(by_type.items())),
        "exclusions": dict(sorted(exclusions.items())), "utf8_byte_distribution": quantiles(byte_lengths),
        "token_distributions": {model_id: quantiles(values) for model_id, values in token_lengths.items()},
        "over_limit_unsplit": {
            model_id: sum(value > MODELS[model_id]["registered_limit"] for value in values)
            for model_id, values in token_lengths.items()
        },
        "candidate_ceiling_diagnostics": ceiling_rows,
        "limitations": [
            "No query, label, gold evidence, backend score, embedding, vector, or retrieval output was read or produced.",
            "Logical units are measured before the registered oversize split algorithm; heading repetition may change final chunk token counts.",
            "This inventory cannot freeze the byte ceiling or authorize the source-unit builder before independent contract review.",
            "MiniLM is a 128-token diagnostic and does not set the common C1A/C1B unit ceiling; its truncation exposure is reported.",
        ],
    }
    write_json(OUT / "tokenizer-files.json", model_receipts)
    write_json(OUT / "summary.json", summary)
    manifest = {
        "audit_id": "PMLAB-NATURAL-RET-001-TOKEN-FEAS-V0", "status": summary["status"],
        "snapshot_commit": resolved_commit, "tokenizer_receipts_sha256": sha256_bytes((OUT / "tokenizer-files.json").read_bytes()),
        "summary_sha256": sha256_bytes((OUT / "summary.json").read_bytes()),
        "authority": "label-free feasibility only; no byte ceiling, builder, backend, or model selection authority",
    }
    write_json(OUT / "manifest.json", manifest)
    print(json.dumps({"logical_units": len(units), "snapshot_commit": resolved_commit, "summary_sha256": manifest["summary_sha256"]}))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="HEAD")
    args = parser.parse_args()
    run(args.commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
