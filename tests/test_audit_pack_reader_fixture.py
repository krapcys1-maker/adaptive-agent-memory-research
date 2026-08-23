import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "lab" / "pmlab-pack-reader-v0" / "internal" / "construction-audit.json"


def test_construction_audit_passes_fail_closed():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_pack_reader_fixture.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert all(report["checks"].values())
