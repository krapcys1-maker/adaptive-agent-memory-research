#!/usr/bin/env python3
"""Resolve every frozen PMLAB-PACK-READER-001 locator before API execution."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
RUN_DIR = BASE / "execution-deepseek-v4-flash-v0"
EVIDENCE_RE = re.compile(r"^\[(R\d{2})\|([^]]+)] <([^>]+)> (.*)$")
FULL_RE = re.compile(r"^(.+):L(\d+)-L(\d+)$")
COMPACT_RE = re.compile(r"^(S\d{2}):L(\d+)-L(\d+)$")
ALIAS_RE = re.compile(r"^\[(S\d{2})]=(.+)$")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    packets = {row["condition_id"]: row for row in load_jsonl(RUN_DIR / "prompt-packets.jsonl")}
    mappings = {row["condition_id"]: row for row in load_jsonl(BASE / "internal" / "condition-map.jsonl")}
    cases = {row["case_id"]: row for row in load_jsonl(BASE / "cases.jsonl")}
    corpus = load_jsonl(BASE / "corpus.jsonl")
    resolved = 0
    packet_passes = []
    model_visible_leaks = []
    for condition_id, mapping in mappings.items():
        packet = packets[condition_id]
        visible = "\n".join(message["content"] for message in packet["messages"])
        if condition_id in visible or any(label in visible for label in ("F0_FULL", "F1_COMPACT", "O0_RETRIEVAL", "O1_GOVERNED", "expected_answer", "stale_atoms", "required_local_ids")):
            model_visible_leaks.append(condition_id)
        user = packet["messages"][1]["content"]
        evidence_part, question_part = user.split("\n\nQUESTION\n", 1)
        lines = evidence_part.splitlines()[1:]
        aliases = {}
        if "SOURCE DICTIONARY" in lines:
            dictionary_index = lines.index("SOURCE DICTIONARY")
            evidence_lines, alias_lines = lines[:dictionary_index], lines[dictionary_index + 1:]
            for line in alias_lines:
                match = ALIAS_RE.fullmatch(line)
                if not match:
                    raise ValueError(f"invalid alias line in {condition_id}: {line}")
                aliases[match.group(1)] = match.group(2)
        else:
            evidence_lines = lines
        case = cases[mapping["case_id"]]
        expected_rows = {
            row["local_id"]: row for row in corpus
            if row["group_id"] == case["group_id"] and row["language"] == case["language"]
        }
        seen = set()
        ok = len(evidence_lines) == 8 and question_part == case["question"]
        for line in evidence_lines:
            match = EVIDENCE_RE.fullmatch(line)
            if not match:
                ok = False
                continue
            record_id, locator, bucket, text = match.groups()
            if record_id in seen or record_id not in expected_rows:
                ok = False
                continue
            seen.add(record_id)
            expected = expected_rows[record_id]
            if mapping["format_arm"] == "F0_FULL":
                locator_match = FULL_RE.fullmatch(locator)
                resolved_path = locator_match.group(1) if locator_match else ""
                start = int(locator_match.group(2)) if locator_match else -1
                end = int(locator_match.group(3)) if locator_match else -1
                ok = ok and not aliases
            else:
                locator_match = COMPACT_RE.fullmatch(locator)
                alias = locator_match.group(1) if locator_match else ""
                resolved_path = aliases.get(alias, "")
                start = int(locator_match.group(2)) if locator_match else -1
                end = int(locator_match.group(3)) if locator_match else -1
            exact = (
                resolved_path == expected["source_path"]
                and start == expected["line_start"] and end == expected["line_end"]
                and bucket == expected["bucket"] and text == expected["text"]
            )
            if exact:
                source_lines = (ROOT / resolved_path).read_text(encoding="utf-8").splitlines()
                exact = start == end and source_lines[start - 1] == text
            ok = ok and exact
            resolved += int(exact)
        packet_passes.append(ok and seen == set(expected_rows))
    report = {
        "experiment_id": "PMLAB-PACK-READER-001",
        "audit": "frozen prompt locator resolution and model-visible leakage audit",
        "passed": len(packet_passes) == 128 and all(packet_passes) and resolved == 1024 and not model_visible_leaks,
        "packets": len(packet_passes),
        "locators_resolved_exactly": resolved,
        "expected_locators": 1024,
        "model_visible_leak_condition_ids": model_visible_leaks,
        "gold_joined": False,
        "boundary": "Checks serialization, exact resolution, prompt layout, and named leakage only; it does not validate reader behavior.",
    }
    (RUN_DIR / "pre-run-prompt-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
