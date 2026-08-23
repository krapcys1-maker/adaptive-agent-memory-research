import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "data" / "lab" / "pmlab-pack-reader-v0" / "execution-deepseek-v4-flash-v0"


def test_frozen_pack_reader_result_recomputes_cleanly():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_pack_reader_result.py")],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    audit = json.loads((RUN_DIR / "result-audit.json").read_text(encoding="utf-8"))
    assert audit["passed"] is True
    assert all(audit["checks"].values())
    assert audit["exception_count"] == 1
    mediators = json.loads((RUN_DIR / "registered-descriptive-mediators.json").read_text(encoding="utf-8"))
    assert mediators["compact_relative_utf8_reduction"] > 0
    assert mediators["compact_relative_prompt_token_reduction"] > 0
