#!/usr/bin/env python3
"""Score the frozen deterministic PMLAB-MAP arms on the post-arm challenge."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "lab" / "pmlab-obligation-mapping-challenge-v0"
ARTIFACTS_DIR = DATA_DIR / "deterministic-artifacts"
CHALLENGE_FREEZE_COMMIT = "adc540f"
FROZEN_RUNNER_COMMIT = "6a82bd8"
HARNESS_VERSION = "pmlab-map-challenge-harness-v0"


def load_runner():
    path = ROOT / "scripts" / "run_obligation_mapping_construction.py"
    spec = importlib.util.spec_from_file_location("frozen_map_runner", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def render_report(summary: dict[str, Any], construction: dict[str, Any]) -> str:
    lines = [
        "# PMLAB-MAP post-freeze deterministic challenge",
        "",
        "Status: post-arm challenge result; unseen to prediction code but labels are not independently reviewed",
        "",
        f"Challenge freeze: `{CHALLENGE_FREEZE_COMMIT}`. Prediction implementation freeze: `{FROZEN_RUNNER_COMMIT}`.",
        "",
        "| Arm | Obligation F1 | Critical full recall | Structure exact | E2E exact | False closure | F1 drop vs construction |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm, metrics in summary.items():
        before = construction[arm]["obligation_f1"]
        lines.append(
            f"| `{arm}` | {metrics['obligation_f1']:.3f} | {metrics['critical_full_recall']:.3f} | "
            f"{metrics['structure_exact_rate']:.3f} | {metrics['end_to_end_exact_rate']:.3f} | "
            f"{metrics['false_closure_count']} | {before - metrics['obligation_f1']:.3f} |"
        )
    links = summary["qdmr_rules_pipeline"]["link_accuracy"]
    oracle_links = summary["gold_obligations_predicted_links"]["link_accuracy"]
    lines.extend(
        [
            "",
            "## Frozen-arm disposition",
            "",
            f"- QDMR rules: entity {links['entity']:.3f}, predicate {links['predicate']:.3f}, time {links['time']:.3f};",
            f"- gold obligations plus frozen linker: entity {oracle_links['entity']:.3f}, predicate {oracle_links['predicate']:.3f}, time {oracle_links['time']:.3f};",
            f"- QDMR critical safe unresolved handling: {summary['qdmr_rules_pipeline']['critical_unresolved_safe_rate']:.3f};",
            f"- QDMR status exact: {summary['qdmr_rules_pipeline']['status_exact_rate']:.3f}.",
            "",
            "The deployable deterministic arm is rejected if it has any critical omission or false closure, misses the 0.90 obligation-F1 or 0.95 entity/predicate gates, or drops more than 0.05 on unseen schema or 0.10 on unseen composition. Gold arms remain diagnostics, never deployable results.",
            "",
            "No parser rule was changed after the challenge was authored. The harness only loads the frozen prediction functions and scorer. Because the same research process authored the labels, this is stronger than construction evidence but weaker than an independently reviewed benchmark.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_outputs() -> dict[Path, str]:
    runner = load_runner()
    cases = read_jsonl(DATA_DIR / "cases.jsonl")
    arms = ["whole_query_single_scope", "conjunction_splitter", "qdmr_rules_pipeline", "gold_obligations_predicted_links", "gold_oracle"]
    rows = [runner.score_case(case, arm, runner.predict(case, arm)) for case in cases for arm in arms]
    summary = runner.summarize(rows)
    construction = json.loads((ROOT / "data" / "lab" / "pmlab-obligation-mapping-dev-v0" / "artifacts" / "summary.json").read_text(encoding="utf-8"))
    results_text = "".join(canonical_json(row) + "\n" for row in rows)
    summary_text = json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    report_text = render_report(summary, construction)
    challenge_manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "experiment": "PMLAB-MAP-001-post-freeze-challenge",
        "status": "completed-post-freeze-not-independent",
        "harness_version": HARNESS_VERSION,
        "challenge_freeze_commit": CHALLENGE_FREEZE_COMMIT,
        "prediction_runner_freeze_commit": FROZEN_RUNNER_COMMIT,
        "challenge_cases_sha256": challenge_manifest["hashes"]["cases.jsonl"],
        "case_count": len(cases),
        "arms": arms,
        "result_count": len(rows),
        "hashes": {
            "results.jsonl": hashlib.sha256(results_text.encode("utf-8")).hexdigest(),
            "summary.json": hashlib.sha256(summary_text.encode("utf-8")).hexdigest(),
            "report.md": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        },
        "known_limitations": ["same-process labels", "small synthetic challenge", "single post-freeze challenge"],
    }
    return {
        ARTIFACTS_DIR / "results.jsonl": results_text,
        ARTIFACTS_DIR / "summary.json": summary_text,
        ARTIFACTS_DIR / "report.md": report_text,
        ARTIFACTS_DIR / "manifest.json": json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = build_outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, text in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise SystemExit("stale or missing artifacts: " + ", ".join(stale))
    else:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in expected.items():
            path.write_text(content, encoding="utf-8", newline="\n")
    print(canonical_json(json.loads(expected[ARTIFACTS_DIR / "summary.json"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
