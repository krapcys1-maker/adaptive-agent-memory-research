import json
import subprocess
import sys
from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT
    / "data"
    / "lab"
    / "pmlab-pack-reader-v0"
    / "execution-deepseek-v4-flash-v0"
    / "completion-audit.json"
)


def test_pack_reader_first_reader_branch_has_complete_evidence_chain():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_pack_reader_completion.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert all(report["checks"].values())
    assert report["observed"] == {
        "bilingual_cases": 32,
        "conditions": 128,
        "http_calls": 128,
        "result_exception_count": 1,
        "retries": 0,
        "run_cost_usd": 0.04026,
        "semantic_groups": 16,
    }
