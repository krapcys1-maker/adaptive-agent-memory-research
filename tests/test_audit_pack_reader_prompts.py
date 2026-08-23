import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "lab" / "pmlab-pack-reader-v0" / "execution-deepseek-v4-flash-v0" / "pre-run-prompt-audit.json"


def test_all_frozen_prompt_locators_resolve_without_named_leakage():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_pack_reader_prompts.py")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["locators_resolved_exactly"] == report["expected_locators"] == 1024
    assert report["model_visible_leak_condition_ids"] == []
