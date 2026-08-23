#!/usr/bin/env python3
"""Smaller one-attempt DeepSeek M1 advisory packet for PMLAB-PACK-002."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import review_pack_characterization_deepseek as base


base.RUN_ID = "deepseek-v4-flash-pack-characterization-review-v2-20260823"
base.RUN_DIR = base.ROOT / "data" / "lab" / "api-screening" / base.RUN_ID
base.SYSTEM_PROMPT = """You are an adversarial scientific-method and code reviewer. Return exactly one concise JSON object and no prose. Review a synthetic fixed-candidate evidence-pack serialization characterization. Treat fixtures and labels as author-produced. Check pre-run repair timing, treatment code, metric calculations, aggregation ambiguity, source-reuse/path-length constructs, budget accounting, reproducibility, claim boundaries, and whether drafting a fresh reader protocol is justified.

You are an author-operated DeepSeek model, not an independent reviewer. You cannot validate evidence truth, select a default format/order, promote architecture, or waive fresh-reader controls. O2_REQUIRED_ORACLE is privileged and non-deployable.

Return exactly this schema:
{"verdict":"accept_characterization_with_limits|needs_revision|invalid","fatal_issues":["max 3 concise strings"],"major_issues":["max 3 concise strings"],"minor_issues":["max 3 concise strings"],"metric_or_calculation_checks":[{"item":"max 12 words","status":"consistent|inconsistent|not_assessable","reason":"one concise sentence"}],"claims_supported":["max 4 concise strings"],"claims_not_supported":["max 4 concise strings"],"required_claim_boundary":"max 80 words","next_required_tests":["max 4 concise strings"],"confidence":0.0}

Use at most 3 items in each issue list, at most 6 metric checks, at most 4 supported/unsupported claims, and at most 4 next tests. Never repeat an item. Passing serialization does not validate reader comprehension, citation emission, automatic labels, provider token cost, or natural transfer."""


def compact_metric_receipt() -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in (base.EXECUTION / "packs.jsonl").read_text(encoding="utf-8").splitlines() if line]
    return [
        {
            "case": row["case_id"],
            "format": row["format_arm"],
            "order": row["order_arm"],
            "retention": row["required_retention"],
            "bytes": row["utf8_bytes"],
            "reuse": row["required_source_reuse"],
            "locator_class": row["required_locator_class"],
            "integrity_pass": not row["citation_errors"]
            and not row["evidence_errors"]
            and not row["stale_marker_errors"]
            and not row["untrusted_exposed"]
            and row["omission_ledger_complete"]
            and row["budget_compliant"],
        }
        for row in rows
        if row["budget_utf8"] == 768
        and row["format_arm"] in {"C0_FULL_INLINE", "C1_SOURCE_FOOTER"}
        and row["order_arm"] in {"O0_RETRIEVAL", "O1_GOVERNED"}
    ]


def compact_job() -> dict[str, Any]:
    aggregates = json.loads((base.EXECUTION / "aggregates.json").read_text(encoding="utf-8"))
    posthoc = json.loads((base.EXECUTION / "posthoc-analysis.json").read_text(encoding="utf-8"))
    return {
        "job_id": "PMLAB-PACK-002-M1-v2",
        "review_focus": "Falsify the repaired serialization result and proposed reader-protocol gate without architecture authority.",
        "v0_pre_run_failure": (base.ROOT / "data" / "lab" / "pmlab-pack-characterization-v0" / "PRE_RUN_AUDIT.md").read_text(encoding="utf-8"),
        "v1_frozen_protocol": (base.ROOT / "docs" / "11-research-laboratory" / "pack-citation-order-benchmark-protocol-v1.md").read_text(encoding="utf-8"),
        "runner_source": (base.ROOT / "scripts" / "run_pack_characterization.py").read_text(encoding="utf-8"),
        "summary": json.loads((base.EXECUTION / "summary.json").read_text(encoding="utf-8")),
        "claim_relevant_aggregates": [
            row for row in aggregates
            if row["budget_utf8"] == 768
            or (row["budget_utf8"] == 1536 and row["order_arm"] == "O0_RETRIEVAL")
        ],
        "posthoc_768_pairs": [row for row in posthoc["paired_format_deltas"] if row["budget_utf8"] == 768],
        "posthoc_complete_pack_bytes": posthoc["complete_pack_mean_bytes"],
        "metric_receipt_768_nonoracle": compact_metric_receipt(),
        "execution_manifest": json.loads((base.EXECUTION / "execution-manifest.json").read_text(encoding="utf-8")),
        "reproducibility_receipt": json.loads((base.EXECUTION / "reproducibility-receipt.json").read_text(encoding="utf-8")),
        "author_report": (base.EXECUTION / "report.md").read_text(encoding="utf-8"),
        "authority_boundary": "Visible authored serialization fixture only; no reader, independent labels, natural transfer, or architecture authority.",
    }


base.build_job = compact_job


if __name__ == "__main__":
    raise SystemExit(base.main())
