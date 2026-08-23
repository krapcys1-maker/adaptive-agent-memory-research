#!/usr/bin/env python3
"""Freeze an audited PMLAB-PACK-READER-001 fixture manifest before runner work."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
MANIFEST = BASE / "manifest.json"
AUDIT = BASE / "internal" / "construction-audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_pack_reader_fixture.py")], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit("Construction audit failed; fixture was not frozen.")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit.get("passed") is not True:
        raise SystemExit("Construction audit did not report passed=true.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["status"] = "fixture-and-opaque-schedule-frozen-before-runner"
    manifest["construction_audit"] = {
        "path": str(AUDIT.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256(AUDIT),
        "passed": True,
    }
    manifest["hashes"][str(AUDIT.relative_to(ROOT)).replace("\\", "/")] = sha256(AUDIT)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": manifest["status"], "audit_sha256": sha256(AUDIT)}))


if __name__ == "__main__":
    main()
