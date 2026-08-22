#!/usr/bin/env python3
"""Reveal author/advisory labels only after a valid independent-review receipt."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_mapper_independent_review_v1 as validator  # noqa: E402


PACKET_DIR = validator.PACKET_DIR
CASES_PATH = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1" / "cases.jsonl"
FIRST_COMPARISON = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-map-stage-advisory-review-20260822" / "comparison.jsonl"
SECOND_COMPARISON = ROOT / "data" / "lab" / "api-screening" / "deepseek-v4-flash-map-stage-remaining-review-20260822" / "comparison.jsonl"
DEFAULT_OUTPUT_DIR = PACKET_DIR / "post-label-reveal"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalized_label(stage: str, label: dict[str, Any] | None) -> dict[str, Any] | None:
    if label is None:
        return None
    value = dict(label)
    if stage == "entity_linking" and "selected_ids" not in value:
        value["selected_ids"] = []
    return value


def differing_fields(left: dict[str, Any] | None, right: dict[str, Any] | None) -> list[str]:
    if left is None or right is None:
        return ["missing_label"]
    return sorted(key for key in set(left) | set(right) if canonical(left.get(key)) != canonical(right.get(key)))


def verified_receipt(form_path: Path, attestation_path: Path, receipt_path: Path) -> dict[str, Any]:
    regenerated = validator.validate_completed(form_path, attestation_path)
    stored = json.loads(receipt_path.read_text(encoding="utf-8"))
    if canonical(regenerated) != canonical(stored):
        raise ValueError("stored receipt differs from freshly validated independent form")
    if stored.get("gold_revealed_by_validator") is not False:
        raise ValueError("receipt does not certify pre-reveal validation")
    return stored


def build_reveal(form_path: Path, attestation_path: Path, receipt_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    receipt = verified_receipt(form_path, attestation_path, receipt_path)
    forms = {row["semantic_group_id"]: row for row in read_jsonl(form_path)}
    cases = {row["case_id"]: row for row in read_jsonl(CASES_PATH)}
    advisory = {
        **{row["case_id"]: row for row in read_jsonl(FIRST_COMPARISON)},
        **{row["case_id"]: row for row in read_jsonl(SECOND_COMPARISON)},
    }
    rows: list[dict[str, Any]] = []
    group_queue: list[dict[str, Any]] = []
    for group in sorted(forms):
        form = forms[group]
        group_rows = []
        for language in ("en", "pl"):
            case_id = f"{group}-{language.upper()}"
            case = cases[case_id]
            author = normalized_label(case["stage"], case["gold"])
            independent = normalized_label(case["stage"], form["independent_labels"][language])
            advisory_row = advisory.get(case_id)
            advisory_label = normalized_label(case["stage"], advisory_row.get("advisory_label") if advisory_row else None)
            row = {
                "case_id": case_id,
                "semantic_group_id": group,
                "stage": case["stage"],
                "language": language,
                "criticality": case["criticality"],
                "author_label": author,
                "independent_label": independent,
                "advisory_label": advisory_label,
                "advisory_prediction_status": advisory_row.get("prediction_status", "valid") if advisory_row else "missing",
                "author_independent_exact": canonical(author) == canonical(independent),
                "author_independent_differing_fields": differing_fields(author, independent),
                "independent_advisory_exact": advisory_label is not None and canonical(independent) == canonical(advisory_label),
                "independent_advisory_differing_fields": differing_fields(independent, advisory_label),
                "review_confidence": form["confidence"],
                "review_rationale": form["rationale"],
                "adjudicated_label": None,
                "adjudication_status": "pending",
            }
            rows.append(row); group_rows.append(row)
        requires = (
            not all(row["author_independent_exact"] for row in group_rows)
            or form["language_equivalent"] is False
            or form["stage_isolation"] in {"material_issue", "exclude"}
            or form["exclude_recommendation"] is True
        )
        if requires:
            group_queue.append(
                {
                    "semantic_group_id": group,
                    "stage": group_rows[0]["stage"],
                    "criticality": group_rows[0]["criticality"],
                    "author_independent_exact_rows": sum(row["author_independent_exact"] for row in group_rows),
                    "language_equivalent": form["language_equivalent"],
                    "stage_isolation": form["stage_isolation"],
                    "exclude_recommendation": form["exclude_recommendation"],
                    "disputed_or_underspecified_fields": form["disputed_or_underspecified_fields"],
                    "adjudication_status": "pending",
                    "resolution_required_before_candidate": group_rows[0]["criticality"] == "critical",
                }
            )
    summary = {
        "status": "revealed-awaiting-adjudication",
        "source_commit": receipt["source_commit"],
        "reviewer_id_or_pseudonym": receipt["reviewer_id_or_pseudonym"],
        "reviewer_family_or_affiliation": receipt["reviewer_family_or_affiliation"],
        "reviewed_groups": receipt["reviewed_groups"],
        "reviewed_rows": receipt["reviewed_rows"],
        "author_independent_exact_rows": sum(row["author_independent_exact"] for row in rows),
        "groups_requiring_adjudication": len(group_queue),
        "critical_groups_requiring_adjudication": sum(row["criticality"] == "critical" for row in group_queue),
        "queue_by_stage": dict(sorted(Counter(row["stage"] for row in group_queue).items())),
        "gold_mutated": False,
        "candidate_implementation_permitted": False,
        "authority": "comparison and queue only; no automatic adjudication",
    }
    return rows, group_queue, summary


def write_outputs(output_dir: Path, rows: list[dict[str, Any]], queue: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "three-way-comparison.jsonl").write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    (output_dir / "adjudication-queue.jsonl").write_text("".join(canonical(row) + "\n" for row in queue), encoding="utf-8", newline="\n")
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--form", type=Path, default=validator.DEFAULT_FORM)
    parser.add_argument("--attestation", type=Path, default=validator.DEFAULT_ATTESTATION)
    parser.add_argument("--receipt", type=Path, default=validator.DEFAULT_RECEIPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rows, queue, summary = build_reveal(args.form, args.attestation, args.receipt)
    if args.write:
        write_outputs(args.output_dir, rows, queue, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
