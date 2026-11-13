#!/usr/bin/env python3
"""Which experiment manifests freeze a file: ask before you edit it.

A file is frozen when a JSON manifest under ``data/`` declares its SHA-256 under a key
that is the file's path. Committing any change to such a file makes
``scripts/audit_repository_claims.py`` report a critical ``declared-hash`` finding and
fails CI, unless a ``<manifest>.DRIFT.json`` note next to every pinning manifest proves
the change from Git. Shared helpers are frozen this way too, not only experiment code:
an experiment that used a helper pins its digest. The audit tells you after the commit;
this command tells you before the edit, so that a change to a frozen helper becomes a
new versioned file (the project's documented route) instead of a red build.

It applies the audit's own rules: manifests under ``data/`` only, packets governed by a
valid ``SUPERSEDED.json`` skipped, and only path keys counted (a ``<name>_sha256`` key is
a guess the audit reports at low severity, so it is listed separately and never decides
the verdict). The rules are imported from the audit module, not copied, so the two
cannot drift apart. It reads files and runs read-only ``git show``; it writes nothing.

"Not frozen" here means only that no manifest pins the bytes. A file can also be frozen
by policy without a digest, for example code that a running or later experiment imports
by commit, or a file a protocol or README declares frozen. Read the experiment's README
before editing code it uses; this command cannot see such rules.

Usage::

    python scripts/pinned_files.py scripts/llm_backends.py tools/project_memory/cli.py
    python scripts/pinned_files.py --under scripts          # every frozen file below a directory
    python scripts/pinned_files.py --check PATH [PATH ...]  # exit 1 if any PATH is frozen (pre-commit use)
    python scripts/pinned_files.py --format json --under scripts
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_repository_claims as audit  # noqa: E402  (same directory; the audit is the authority)


def _live_manifests(root: Path) -> Iterable[Path]:
    """The manifests whose declarations the audit checks: JSON under data/, not markers, drift notes or superseded packets."""
    for manifest in sorted(audit.iter_files(root / "data", {".json"})):
        if manifest.name == audit.SUPERSEDED_MARKER:
            continue
        if manifest.name.endswith(audit.DRIFT_SUFFIX):
            companion = manifest.with_name(manifest.name[: -len(audit.DRIFT_SUFFIX)] + ".json")
            if companion.is_file():
                continue  # a drift note; an orphan one is checked as an ordinary manifest, as the audit does
        governing = audit.superseded_by_marker(manifest)
        if governing is not None and governing[1] is not None:
            continue  # a valid marker: the audit does not check this packet
        yield manifest


def declarations(root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Map each declared file (repository-relative POSIX path) to the declarations that name it.

    Each declaration: ``manifest``, ``key``, ``digest``, ``certain`` (a path key, the audit's
    critical case) and ``current`` (the digest equals the working copy or the Git blob, so a
    committed change would break it now).
    """
    root = Path(root or audit.ROOT)
    found: dict[str, list[dict[str, Any]]] = {}
    working: dict[Path, str] = {}
    for manifest in _live_manifests(root):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for key_path, key, value in audit.walk_json(payload, []):
            if not isinstance(value, str) or not audit.HEX64.match(value):
                continue
            resolved = audit.resolve_declared_target(manifest, key, key_path)
            if resolved is None:
                continue
            target, certain = resolved
            target = target.resolve()
            try:
                relative = target.relative_to(root.resolve()).as_posix()
            except ValueError:
                continue
            if target not in working:
                working[target] = audit.digest_bytes(target.read_bytes())
            current = working[target] == value
            if not current:
                blob = audit.git_blob(relative)
                current = blob is not None and audit.digest_bytes(blob) == value
            found.setdefault(relative, []).append({
                "manifest": manifest.resolve().relative_to(root.resolve()).as_posix(),
                "key": key,
                "digest": value,
                "certain": certain,
                "current": current,
            })
    return found


def verdict(relative: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    """One file's answer: frozen when at least one certain declaration is current."""
    binding = [e for e in entries if e["certain"] and e["current"]]
    return {
        "path": relative,
        "frozen": bool(binding),
        "pinning_manifests": sorted({e["manifest"] for e in binding}),
        "guessed_declarations": sorted({e["manifest"] for e in entries if not e["certain"]}),
        "stale_declarations": sorted({e["manifest"] for e in entries if e["certain"] and not e["current"]}),
    }


def normalise(path: str, root: Path) -> str:
    candidate = Path(path)
    absolute = (candidate if candidate.is_absolute() else Path.cwd() / candidate).resolve()
    try:
        return absolute.relative_to(root.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def render(answers: list[dict[str, Any]]) -> str:
    lines = []
    for a in answers:
        if a["frozen"]:
            n = len(a["pinning_manifests"])
            lines.append(f"{a['path']}: FROZEN by {n} manifest(s). A committed change fails the claim audit "
                         f"(critical declared-hash) unless each manifest gets a .DRIFT.json note; "
                         f"prefer a new versioned file.")
            lines.extend(f"    {m}" for m in a["pinning_manifests"])
        else:
            lines.append(f"{a['path']}: not frozen by any live manifest")
        if a["stale_declarations"]:
            lines.append("    already drifted or superseded in: " + ", ".join(a["stale_declarations"]))
        if a["guessed_declarations"]:
            lines.append("    low-severity guessed declarations in: " + ", ".join(a["guessed_declarations"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="files to ask about, relative to the current directory or the repository root")
    parser.add_argument("--under", help="list every frozen file below this repository-relative directory")
    parser.add_argument("--check", action="store_true", help="exit 1 when any named path is frozen")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if not args.paths and not args.under:
        parser.error("name at least one path or use --under DIRECTORY")

    root = Path(audit.ROOT)
    table = declarations(root)
    answers = []
    for path in args.paths:
        relative = normalise(path, root)
        if not (root / relative).is_file():
            print(f"{path}: not a file in this repository", file=sys.stderr)
            return 2
        answers.append(verdict(relative, table.get(relative, [])))
    if args.under:
        prefix = Path(args.under).as_posix().rstrip("/") + "/"
        listed = {a["path"] for a in answers}
        for relative in sorted(table):
            if relative.startswith(prefix) and relative not in listed:
                answer = verdict(relative, table[relative])
                if answer["frozen"]:
                    answers.append(answer)

    if args.format == "json":
        print(json.dumps({"answers": answers, "frozen": sum(a["frozen"] for a in answers)}, indent=2))
    else:
        print(render(answers) if answers else "no frozen files found")
        if args.under:
            print(f"\n{sum(a['frozen'] for a in answers)} frozen file(s) listed")
    if args.check and any(a["frozen"] for a in answers if a["path"] in {normalise(p, root) for p in args.paths}):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
