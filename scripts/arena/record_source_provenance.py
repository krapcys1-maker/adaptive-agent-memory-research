"""Record what a system under test actually was, at the moment it was measured.

A frozen run names a system. A name is not a system: `main` moves, a working
tree can be dirty, and a result that says *CUPMem* without saying *which bytes*
cannot be reproduced or challenged.

Written generically rather than for CUPMem, because every remaining system —
Hindsight, Graphiti, Mem0 — needs the same record and writing it four times is
how the four drift apart.

The first CUPMem run was made from a copy in a session-scoped temporary
directory. It produced real numbers against a tree that would vanish with the
session, which is the same defect as an unpinned model revision wearing
different clothes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(("git", *args), cwd=root, capture_output=True,
                             text=True, check=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return None
    return out.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def describe(root: Path, subtree: str, patterns: tuple[str, ...]) -> dict[str, Any]:
    """Everything needed to say which bytes were run, and whether they were pristine."""
    target = root / subtree
    files: dict[str, dict[str, Any]] = {}
    for pattern in patterns:
        for path in sorted(target.rglob(pattern)):
            if "__pycache__" in path.parts or not path.is_file():
                continue
            files[path.relative_to(root).as_posix()] = {
                "sha256": _sha256(path), "bytes": path.stat().st_size,
            }

    dirty = _git(root, "status", "--porcelain")
    # A rolled-up digest over (path, hash) pairs, so one value can be quoted in a
    # result table and compared without re-reading every file.
    rollup = hashlib.sha256(
        "\n".join(f"{name}:{meta['sha256']}" for name, meta in files.items()).encode()
    ).hexdigest()

    return {
        "root": str(root),
        "subtree": subtree,
        "remote": _git(root, "config", "--get", "remote.origin.url"),
        "commit": _git(root, "rev-parse", "HEAD"),
        "commit_date": _git(root, "log", "-1", "--format=%cI"),
        # None means git could not answer, which is not the same as clean.
        "working_tree_clean": None if dirty is None else (dirty == ""),
        "uncommitted": None if dirty is None else [
            line for line in dirty.splitlines() if line.strip()
        ],
        "file_count": len(files),
        "tree_digest_sha256": rollup,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="checkout of the system under test")
    parser.add_argument("--subtree", default=".", help="the part that is actually run")
    parser.add_argument("--pattern", action="append", default=None,
                        help="glob, repeatable; defaults to *.py")
    parser.add_argument("--system", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    record = {
        "artifact": "arena-system-source",
        "system": args.system,
        "purpose": ("Names the exact bytes a frozen run measured. A system name and a "
                    "branch name are both moving targets; a commit and a tree digest "
                    "are not."),
        **describe(Path(args.root).resolve(), args.subtree,
                   tuple(args.pattern or ("*.py",))),
    }
    Path(args.out).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"{args.system}: {record['file_count']} files, commit {record['commit']}, "
          f"clean={record['working_tree_clean']}, digest {record['tree_digest_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
