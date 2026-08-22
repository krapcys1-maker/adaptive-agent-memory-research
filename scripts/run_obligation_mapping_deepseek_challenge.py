#!/usr/bin/env python3
"""Run the unchanged DeepSeek PMLAB-MAP prompt on the post-freeze challenge."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "data" / "lab" / "pmlab-obligation-mapping-deepseek-challenge-v0"
CORPUS_DIR = ROOT / "data" / "lab" / "pmlab-obligation-mapping-challenge-v0"
CHALLENGE_FREEZE_COMMIT = "adc540f"
MODEL_ARM_RESULT_COMMIT = "0066961"


def load_base():
    path = ROOT / "scripts" / "run_obligation_mapping_deepseek.py"
    spec = importlib.util.spec_from_file_location("frozen_deepseek_map", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module.RUN_ID = "pmlab-map-deepseek-challenge-v0"
    module.RUN_DIR = RUN_DIR
    module.CORPUS_DIR = CORPUS_DIR
    module.CORPUS_FREEZE_COMMIT = CHALLENGE_FREEZE_COMMIT
    return module


def prepare() -> dict:
    base = load_base()
    manifest = base.prepare()
    manifest.update(
        {
            "experiment": "PMLAB-MAP-001-optional-model-post-freeze-challenge",
            "status": "frozen-post-arm-challenge-input",
            "challenge_freeze_commit": CHALLENGE_FREEZE_COMMIT,
            "construction_model_result_commit": MODEL_ARM_RESULT_COMMIT,
            "known_limitations": ["same-process labels", "single model", "small synthetic post-freeze challenge", "no independent review"],
        }
    )
    base.shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def render_challenge_report(api: dict, summary: dict) -> str:
    construction = json.loads(
        (ROOT / "data" / "lab" / "pmlab-obligation-mapping-deepseek-v1" / "score-summary.json").read_text(encoding="utf-8")
    )
    return "\n".join(
        [
            "# DeepSeek V4 Flash PMLAB-MAP post-freeze challenge",
            "",
            "Status: optional replaceable model comparator; post-arm challenge; labels not independently reviewed",
            "",
            f"- valid predictions: {api['valid_predictions']}/{api['jobs']};",
            f"- conservative challenge cost: USD {api['run_conservative_cost_usd']:.8f};",
            f"- cumulative project API cost: USD {api['all_runs_conservative_cost_usd']:.8f};",
            f"- obligation F1: {summary['obligation_f1']:.3f} (construction {construction['obligation_f1']:.3f}, drop {construction['obligation_f1'] - summary['obligation_f1']:.3f});",
            f"- critical full recall: {summary['critical_full_recall']:.3f};",
            f"- end-to-end exact: {summary['end_to_end_exact_rate']:.3f};",
            f"- entity/predicate/time: {summary['link_accuracy']['entity']:.3f} / {summary['link_accuracy']['predicate']:.3f} / {summary['link_accuracy']['time']:.3f};",
            f"- false closure: {summary['false_closure_count']};",
            f"- critical unresolved safe handling: {summary['critical_unresolved_safe_rate']:.3f}.",
            "",
            "The model received the exact frozen construction system prompt with only the challenge's public schema, entity catalog, clock, and model-facing queries substituted. It received no gold graph, split label, criticality, or evaluation metadata. Invalid/missing outputs remain failures and are not repaired.",
            "",
            "Any critical omission, false closure, failure of 0.90 obligation F1 or 0.95 entity/predicate accuracy, or a construction-to-challenge F1 drop above 0.05 rejects promotion. The model remains optional and never supplies gold labels.",
            "",
        ]
    )


def score() -> dict:
    base = load_base()
    result = base.score()
    report = render_challenge_report(result["api"], result["score"])
    (RUN_DIR / "report.md").write_text(report, encoding="utf-8", newline="\n")
    result_manifest = {
        "status": "completed-post-freeze-model-comparator",
        "model": base.MODEL,
        "prompt_version": base.PROMPT_VERSION,
        "prompt_freeze_commit": base.PROMPT_FREEZE_COMMIT,
        "adapter_freeze_commit": "8913667",
        "challenge_freeze_commit": CHALLENGE_FREEZE_COMMIT,
        "construction_model_result_commit": MODEL_ARM_RESULT_COMMIT,
        "prediction_count": result["api"]["valid_predictions"],
        "scored_case_count": result["api"]["jobs"],
        "hashes": {
            label: hashlib.sha256((RUN_DIR / label).read_bytes()).hexdigest()
            for label in ("predictions.jsonl", "scored-results.jsonl", "score-summary.json", "report.md")
        },
        "authority": "optional comparator; never gold; post-freeze but not independently reviewed",
    }
    base.shared.write_json(RUN_DIR / "result-manifest.json", result_manifest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--env-file", type=Path, default=ROOT.parent / ".env")
    run_parser.add_argument("--budget-usd", type=float, default=10.0)
    run_parser.add_argument("--batch-size", type=int, default=7)
    run_parser.add_argument("--max-tokens", type=int, default=8000)
    run_parser.add_argument("--timeout", type=float, default=120.0)
    sub.add_parser("score")
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare()
    elif args.command == "run":
        base = load_base()
        result = base.run(args.env_file, args.budget_usd, args.batch_size, args.max_tokens, args.timeout)
    else:
        result = score()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
