#!/usr/bin/env python3
"""Frozen language/date perturbation challenge for parser v0 at commit 1a43b7a."""

from __future__ import annotations

import hashlib
import json
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.run_forgetting_benchmark import FTS5Retriever
    from scripts.run_forgetting_challenge import DEFAULT_DATASET, TOP_K, make_f2_corpus, write_json, write_jsonl
    from scripts.run_query_parser_baseline import build_catalog, parse_query
except ModuleNotFoundError:
    from run_forgetting_benchmark import FTS5Retriever
    from run_forgetting_challenge import DEFAULT_DATASET, TOP_K, make_f2_corpus, write_json, write_jsonl
    from run_query_parser_baseline import build_catalog, parse_query


OUTPUT = DEFAULT_DATASET / "parser-challenge-v1"
PARSER_FROZEN_COMMIT = "1a43b7a"


def challenge_cases() -> list[dict[str, Any]]:
    raw = [
        ("paraphrase", "Which passphrase is presently active for Aster?", "aster-key", "2026-01-03"),
        ("paraphrase", "Give me Juniper's latest delivery path.", "juniper-route", "2026-01-07"),
        ("paraphrase", "Who owns the current Nimbus incident?", "nimbus-owner", "2026-01-11"),
        ("paraphrase", "What is Vela's presently valid safety limit?", "vela-threshold", "2026-01-19"),
        ("topic-disambiguation", "Current communications channel for the Mercury project?", "mercury-project", "2026-01-31"),
        ("topic-disambiguation", "Current viewing interval for planet Mercury?", "mercury-planet", "2026-02-16"),
        ("topic-disambiguation", "What is Jordan's current review assignment?", "jordan-analyst", "2026-01-13"),
        ("topic-disambiguation", "Which station locker is active now for Jordan?", "jordan-station", "2026-01-23"),
        ("date-format", "Aster access phrase on 01/01/2026?", "aster-key", "2026-01-01"),
        ("date-format", "Juniper delivery route on 3 January 2026?", "juniper-route", "2026-01-03"),
        ("date-format", "Nimbus incident owner on January fifth, 2026?", "nimbus-owner", "2026-01-05"),
        ("date-format", "Vela safety threshold on 2026.01.09?", "vela-threshold", "2026-01-09"),
        ("date-format", "Mercury project channel on the 10th of January 2026?", "mercury-project", "2026-01-10"),
        ("date-format", "Mercury observation window on February 15, 2026?", "mercury-planet", "2026-02-15"),
        ("date-format", "Jordan review duty on Jan 4, 2026?", "jordan-analyst", "2026-01-04"),
        ("date-format", "Jordan station locker at 2026-01-07T12:00Z?", "jordan-station", "2026-01-07"),
        ("relative-time", "Aster access phrase two versions back from newest?", "aster-key", "2026-01-01"),
        ("relative-time", "What was the fifth Juniper delivery route revision?", "juniper-route", "2026-01-05"),
        ("relative-time", "Właściciel incydentu Nimbus dwa wydania przed najnowszym?", "nimbus-owner", "2026-01-09"),
        ("relative-time", "What was the previous Vela safety threshold?", "vela-threshold", "2026-01-18"),
        ("multilingual", "Jaki jest aktualny kod dostępu Aster?", "aster-key", "2026-01-03"),
        ("ambiguous", "What is the current Mercury state?", None, None),
        ("ambiguous", "What is Jordan's current responsibility?", None, None),
        ("unknown-entity", "What is Zephyr's current recovery code?", None, None),
        ("out-of-range", "Aster access phrase on 2025-12-31?", None, None),
        ("underspecified-time", "What was Vela's safety threshold sometime before now?", None, None),
        ("out-of-range", "Mercury project channel on January 1, 2027?", None, None),
        ("missing-entity", "What is the current access phrase?", None, None),
    ]
    return [
        {
            "case_id": f"PCH-{index:03d}",
            "category": category,
            "query": query,
            "answerable": history_id is not None,
            "expected_history_id": history_id,
            "expected_target_date": target_date,
        }
        for index, (category, query, history_id, target_date) in enumerate(raw, start=1)
    ]


def run() -> dict[str, Any]:
    corpus = make_f2_corpus()
    catalog = build_catalog(corpus)
    cases = challenge_cases()
    record_lookup = {(row["history_id"], row["valid_from"]): row for row in corpus}
    results = []
    with tempfile.TemporaryDirectory(prefix="pmlab-parser-challenge-") as temporary:
        root = Path(temporary)
        for index, case in enumerate(cases):
            parsed = parse_query(case["query"], catalog)
            retrieved: list[str] = []
            raw_backend = FTS5Retriever(corpus, root / f"q{index:03d}-raw.sqlite")
            try:
                raw_retrieved = raw_backend.retrieve(case["query"], TOP_K)
            finally:
                raw_backend.close()
            if parsed["status"] == "parsed":
                backend = FTS5Retriever(corpus, root / f"q{index:03d}.sqlite")
                try:
                    retrieved = backend.retrieve(parsed["retrieval_text"], TOP_K)
                finally:
                    backend.close()
            gold_id = None
            if case["answerable"]:
                gold_id = record_lookup[(case["expected_history_id"], case["expected_target_date"])]["evidence_id"]
            fallback_retrieved = retrieved if parsed["status"] == "parsed" else raw_retrieved
            typed_fallback_retrieved = (
                raw_retrieved if parsed.get("reason") == "unresolved-time" else retrieved
            )
            parse_correct = (
                (
                    parsed["status"] == "parsed"
                    and parsed.get("history_id") == case["expected_history_id"]
                    and parsed.get("target_date") == case["expected_target_date"]
                )
                if case["answerable"]
                else parsed["status"] == "abstain"
            )
            results.append(
                {
                    **case,
                    "parser_output": parsed,
                    "gold_evidence_id": gold_id,
                    "retrieved": retrieved,
                    "raw_retrieved": raw_retrieved,
                    "fallback_retrieved": fallback_retrieved,
                    "typed_fallback_retrieved": typed_fallback_retrieved,
                    "parse_correct": parse_correct,
                    "recall_at_5": (gold_id in retrieved) if case["answerable"] else None,
                    "correct_abstention": (not retrieved) if not case["answerable"] else None,
                }
            )
    answerable = [row for row in results if row["answerable"]]
    unanswerable = [row for row in results if not row["answerable"]]
    by_category: dict[str, list[bool]] = defaultdict(list)
    for row in results:
        by_category[row["category"]].append(row["parse_correct"])
    def arm_summary(field: str) -> dict[str, float]:
        return {
            "answerable_recall_at_5": statistics.mean(
                row["gold_evidence_id"] in row[field] for row in answerable
            ),
            "unanswerable_abstention_rate": statistics.mean(
                not row[field] for row in unanswerable
            ),
        }

    summary = {
        "status": "completed-frozen-parser-challenge",
        "parser_frozen_commit": PARSER_FROZEN_COMMIT,
        "cases": len(results),
        "answerable_cases": len(answerable),
        "unanswerable_cases": len(unanswerable),
        "exact_parse_accuracy": statistics.mean(row["parse_correct"] for row in results),
        "answerable_exact_parse_accuracy": statistics.mean(row["parse_correct"] for row in answerable),
        "answerable_recall_at_5": statistics.mean(row["recall_at_5"] for row in answerable),
        "unanswerable_abstention_rate": statistics.mean(row["correct_abstention"] for row in unanswerable),
        "arms": {
            "raw": arm_summary("raw_retrieved"),
            "parser-strict": arm_summary("retrieved"),
            "parser-fallback-raw": arm_summary("fallback_retrieved"),
            "posthoc-unresolved-time-fallback": arm_summary("typed_fallback_retrieved"),
        },
        "parse_accuracy_by_category": {
            category: statistics.mean(values) for category, values in sorted(by_category.items())
        },
        "posthoc_note": "The unresolved-time-only fallback was defined after inspecting v1 failure reasons and requires a fresh freeze before evidential use.",
        "boundary": "Authored adversarial challenge created after parser v0 was committed, but not independently designed or annotated.",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUTPUT / "cases.jsonl", cases)
    write_jsonl(OUTPUT / "results.jsonl", results)
    write_json(OUTPUT / "summary.json", summary)
    write_json(
        OUTPUT / "manifest.json",
        {
            "status": summary["status"],
            "script": "scripts/run_query_parser_challenge.py",
            "parser_frozen_commit": PARSER_FROZEN_COMMIT,
            "cases_sha256": hashlib.sha256((OUTPUT / "cases.jsonl").read_bytes()).hexdigest(),
            "authority": "post-freeze authored challenge; not independent",
        },
    )
    return summary


def main() -> int:
    print(json.dumps(run(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
