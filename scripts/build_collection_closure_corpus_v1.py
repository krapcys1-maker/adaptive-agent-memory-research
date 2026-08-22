#!/usr/bin/env python3
"""Build PMLAB-CLOSURE-001 construction corpus v1.

V1 preserves every v0 case and artifact except the two bilingual
counterexample-insertion cases. Their certificates now *declare* complete so
the later benchmark can isolate whether an insertion-independence check catches
an unsound completeness claim. Frozen v0 remains in Git unchanged.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from scripts.build_collection_closure_corpus import ROOT, canonical_json, content_hash, make_corpus
except ModuleNotFoundError:
    from build_collection_closure_corpus import ROOT, canonical_json, content_hash, make_corpus


DEFAULT_OUTPUT = ROOT / "data" / "lab" / "pmlab-collection-closure-dev-v1"
PARENT_CORPUS_SHA256 = "3599635e6e66cd1f98a2d7bcae98f97369aa5e4c412590f697a126f124253e58"


def make_corpus_v1() -> dict[str, list[dict[str, Any]]]:
    bundle = deepcopy(make_corpus())
    target_case_ids = {
        row["case_id"]
        for row in bundle["cases"]
        if row["gold"]["stratum"] == "admissible-insertion-changes-negative-answer"
    }
    for case in bundle["cases"]:
        case["gold"]["adversarial_certificate_claim"] = case["case_id"] in target_case_ids
    for certificate in bundle["certificates"]:
        case_id = certificate["certificate_id"].removesuffix("-CRT")
        if case_id in target_case_ids:
            certificate["status"] = "complete"
    return bundle


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def write_corpus(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    bundle = make_corpus_v1()
    for key, rows in bundle.items():
        write_jsonl(output / f"{key}.jsonl", rows)

    cases = bundle["cases"]
    manifest = {
        "experiment_id": "PMLAB-CLOSURE-001",
        "dataset": "pmlab-collection-closure-dev-v1",
        "status": "authored-construction-freeze",
        "parent_dataset": "pmlab-collection-closure-dev-v0",
        "parent_corpus_sha256": PARENT_CORPUS_SHA256,
        "change_reason": "v0 did not isolate insertion-independence because counterexample certificates already declared partial",
        "changes": [
            "two bilingual insertion-counterexample certificates now declare status complete",
            "all cases receive an evaluation-only adversarial_certificate_claim boolean",
            "queries inventories probes insertions expected tiers and expected actions are unchanged",
        ],
        "freeze_boundary": "first git commit containing v1 builder, tests, manifest, and all five v1 JSONL artifacts",
        "case_count": len(cases),
        "corpus_sha256": content_hash(bundle),
        "artifact_sha256": {key: content_hash(rows) for key, rows in bundle.items()},
        "strata": dict(sorted(Counter(row["gold"]["stratum"] for row in cases).items())),
        "languages": dict(sorted(Counter(row["language"] for row in cases).items())),
        "negative_tiers": dict(sorted(Counter(row["gold"]["expected_negative_tier"] for row in cases).items())),
        "expected_actions": dict(sorted(Counter(row["gold"]["expected_action"] for row in cases).items())),
        "critical_cases": sum(row["gold"]["critical"] for row in cases),
        "adversarial_certificate_claims": sum(row["gold"]["adversarial_certificate_claim"] for row in cases),
        "limitations": [
            "authored construction corpus with visible gold labels",
            "v1 was repaired before any runner existed but after v0 freeze",
            "bilingual pairs share semantics and must be split by pair_group",
            "inventories certificates probes and insertions are synthetic diagnostic artifacts",
            "no natural-language scope mapper policy or scoring runner is implemented",
            "passing can validate only state-machine and artifact-contract semantics",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(write_corpus(), ensure_ascii=False, indent=2))
