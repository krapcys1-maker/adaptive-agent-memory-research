"""Reproduce PR 90 run-identity defects with synthetic fixtures and fake models.

Run from the repository root: python scripts/reviews/pr90_run_identity_repro.py
No network, private data, API key, or paid model is used. The original scripts,
config, results and tests are not edited. A successful exit means the observed
defects were reproduced on the reviewed implementation, not that they are fixed.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
import test_persona_battery as fixture  # noqa: E402

pb, ps = fixture.pb, fixture.ps


def frozen_env(folder: Path):
    folder.mkdir()
    env = fixture.Env(folder)
    card = folder / "card.md"
    card.write_text(fixture.SYSTEM, encoding="utf-8", newline="")
    cfg = json.loads(env.config.read_text(encoding="utf-8"))
    cfg["freeze"] = {"enforce": True}
    cfg["private_inputs_sha256"] = {
        "items.json": pb.contract.sha256_file(env.items_path),
        "card": pb.contract.sha256_file(card),
        "notes": None,
        "persona_system": pb.sha256_text(env.items["persona"]["system"]),
        "persona_system_untagged": pb.sha256_text(env.items["persona"]["system_untagged"]),
    }
    env.config.write_text(json.dumps(cfg), encoding="utf-8")
    return env, card


def context(env, card):
    return fixture.ctx_for(env, card=card)


def run(env, card, stage, model=None):
    return env.run(stage, model, None, None, "--card", str(card))


def profile_resume(folder: Path) -> dict:
    env, card = frozen_env(folder)
    assert run(env, card, "prepare") == 0
    ctx = context(env, card)
    assert pb.frozen_problems(ctx, env.items_path) == []
    original_tasks = pb.p1_tasks(ctx)
    first = next(t for t in original_tasks if t["meta"]["arm"] == "K" and t["meta"]["injected"])
    model = fixture.Model()
    ps.run_tasks([first], model, env.work / "p1.jsonl", 1, lambda _: None)
    os.environ["PERSONA_BATTERY_PROFILE"] = '{"min_evidence": 1000.0}'
    changed = context(env, card)
    problems = pb.frozen_problems(changed, env.items_path)
    changed_tasks = {t["key"]: t for t in pb.p1_tasks(changed)}
    assert changed_tasks[first["key"]]["meta"]["psha"] != first["meta"]["psha"]
    status = run(env, card, "run-p1", model)
    records = env.records("p1.jsonl")
    stale = [r for r in records if r["psha"] != changed_tasks[r["key"]]["meta"]["psha"]]
    assert problems == [] and status == 0 and len(stale) == 1
    os.environ.pop("PERSONA_BATTERY_PROFILE")
    return {
        "freeze_enforced": True,
        "changed_profile_accepted": True,
        "frozen_problems": problems,
        "exit_code": status,
        "records": len(records),
        "records_with_previous_prompt_fingerprint": len(stale),
        "fresh_records_with_changed_profile": len(records) - len(stale),
    }


def analysis_identity(folder: Path) -> dict:
    env, card = frozen_env(folder)
    pb.HONOUR_RECORD = True
    assert run(env, card, "prepare") == 0
    tasks = pb.p1_tasks(context(env, card))
    first = next(t for t in tasks if t["meta"]["arm"] == "K" and t["meta"]["injected"])
    ps.run_tasks([first], fixture.Model(), env.work / "p1.jsonl", 1, lambda _: None)
    baseline = json.loads((env.work / "baseline.json").read_text(encoding="utf-8"))
    # Equivalent to starting the CLI in a fresh shell without the environment flag.
    pb.HONOUR_RECORD = False
    out = folder / "aggregates.json"
    status = env.run("analyse", None, None, None, "--card", str(card), "--json", str(out))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert baseline["honour_record"] is True and report["provenance"]["honour_record"] is False and status == 0
    return {
        "exit_code": status,
        "prepared_honour_record": baseline["honour_record"],
        "reported_honour_record": report["provenance"]["honour_record"],
        "record_prompt_contains_sentence": pb.HONOUR_TEXT in first["system"],
    }


def incomplete_analysis(folder: Path) -> dict:
    env, card = frozen_env(folder)
    assert run(env, card, "prepare") == 0
    ctx = context(env, card)
    first = next(t for t in pb.p1_tasks(ctx) if t["meta"]["arm"] == "F")
    ps.run_tasks([first], fixture.Model(), env.work / "p1.jsonl", 1, lambda _: None)
    out = folder / "aggregates.json"
    status = env.run("analyse", None, None, None, "--card", str(card), "--json", str(out))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert status == 0 and report["records"]["p1"] == 1 and report["readings"]["p1"]["instrument_ok"] is True
    return {
        "exit_code": status,
        "expected_records": len(pb.p1_tasks(ctx)),
        "actual_records": report["records"]["p1"],
        "instrument_ok": report["readings"]["p1"]["instrument_ok"],
    }


def main() -> None:
    names = ("PERSONA_BATTERY_PROFILE", "PERSONA_BATTERY_HONOUR", "PERSONA_BATTERY_KERNEL")
    if any(os.environ.get(name) for name in names):
        raise SystemExit("Run this reproducer without PERSONA_BATTERY_* overrides.")
    with tempfile.TemporaryDirectory(prefix="pr90-review-") as tmp:
        root = Path(tmp)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                result = {
                    "profile_resume": profile_resume(root / "profile"),
                    "analysis_identity": analysis_identity(root / "identity"),
                    "incomplete_analysis": incomplete_analysis(root / "incomplete"),
                }
        finally:
            os.environ.pop("PERSONA_BATTERY_PROFILE", None)
            pb.HONOUR_RECORD = False
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
