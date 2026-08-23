"""Repair declared digests that were computed from CRLF working copies.

Issue #26. Git's end-of-line conversion meant a declared SHA-256 could describe
the bytes of a Windows working copy rather than the bytes actually stored. After
`.gitattributes` disabled conversion, those declarations describe a byte
sequence that no longer exists anywhere, so the audit reports them as broken.

The content never changed. Only the declaration was of the wrong byte form.

Discriminating repairable from genuinely broken
-----------------------------------------------
A declaration is a CRLF artifact if and only if

    sha256(current_bytes with LF replaced by CRLF) == declared

That is a precise, verifiable test. It proves the declared digest describes the
same content under the other line-ending convention, so re-declaring is a
correction rather than a rewrite of evidence.

Anything that fails this test is a **genuine post-freeze modification** — the
file's content actually differs from what was frozen. Those are left untouched
and reported, because quietly re-declaring them would destroy the evidence that
a freeze broke. They belong to issue #30.

This script writes a repair record naming every old and new digest, so the
change is auditable rather than silent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_repository_claims import (  # noqa: E402
    HEX64,
    iter_files,
    resolve_declared_target,
    walk_json,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def as_crlf(data: bytes) -> bytes:
    """Convert LF to CRLF without doubling an existing CR."""
    return re.sub(rb"(?<!\r)\n", b"\r\n", data)


def collect() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    repairable: list[dict[str, Any]] = []
    genuine: list[dict[str, Any]] = []

    for manifest in iter_files(ROOT / "data", {".json"}):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        for key_path, key, value in walk_json(payload, []):
            if not isinstance(value, str) or not HEX64.match(value):
                continue
            resolved = resolve_declared_target(manifest, key, key_path)
            if resolved is None:
                continue
            target, certain = resolved
            if not certain:
                continue
            data = target.read_bytes()
            actual = sha256_bytes(data)
            if actual == value:
                continue
            entry = {
                "manifest": manifest.relative_to(ROOT).as_posix(),
                "key": key,
                "key_path": key_path,
                "target": target.relative_to(ROOT).as_posix(),
                "declared": value,
                "actual": actual,
            }
            if sha256_bytes(as_crlf(data)) == value:
                repairable.append(entry)
            else:
                genuine.append(entry)
    return repairable, genuine


def apply_repairs(repairable: list[dict[str, Any]]) -> None:
    by_manifest: dict[str, list[dict[str, Any]]] = {}
    for entry in repairable:
        by_manifest.setdefault(entry["manifest"], []).append(entry)

    for manifest_path, entries in by_manifest.items():
        path = ROOT / manifest_path
        text = path.read_text(encoding="utf-8-sig")
        for entry in entries:
            if text.count(entry["declared"]) != 1:
                raise RuntimeError(
                    f"{manifest_path}: digest {entry['declared'][:12]} is not uniquely "
                    f"replaceable; refusing to guess"
                )
            text = text.replace(entry["declared"], entry["actual"])
        path.write_bytes(text.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the repairs (default is a dry run)")
    parser.add_argument("--record", type=Path, default=None, help="where to write the repair record")
    arguments = parser.parse_args(argv)

    repairable, genuine = collect()

    print(f"repairable CRLF-derived declarations : {len(repairable)}")
    print(f"genuine post-freeze modifications    : {len(genuine)}")
    print()
    for entry in genuine:
        print(f"  NOT REPAIRED  {entry['target']}")
        print(f"                declared {entry['declared'][:16]}  actual {entry['actual'][:16]}")

    if arguments.apply and repairable:
        apply_repairs(repairable)
        print(f"\napplied {len(repairable)} repairs")

    if arguments.record:
        record = {
            "issue": 26,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rule": "declared digest equals sha256 of the same content with LF converted to CRLF",
            "applied": bool(arguments.apply),
            "repaired": repairable,
            "not_repaired_genuine_modifications": genuine,
        }
        destination = arguments.record if arguments.record.is_absolute() else ROOT / arguments.record
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(
            (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
        print(f"record: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
