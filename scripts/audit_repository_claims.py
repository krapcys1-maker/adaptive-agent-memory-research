"""Repository-wide mechanical audit of claims that must hold by construction.

This is an I0 gate over the whole repository rather than one artifact. It checks
only properties decidable from bytes and paths: no reviewer, no model, no
network. See docs/00-project/independence-ladder.md.

Checks
------
1. declared-hash      every 64-hex digest declared in a JSON manifest is
                      compared against the bytes of the file it names, and
                      against the bytes stored in the Git blob, so a hash that
                      is only reproducible on one platform is reported.
2. registry-paths     experiment-registry manifest and artifact paths exist.
3. memory-sources     repository paths cited by memory source_refs exist.
4. doc-links          relative Markdown links resolve to real files.
5. orphan-experiments experiment identifiers referenced in docs exist in the
                      registry, and vice versa.

It reports. It never repairs: deciding what to do about a broken freeze is a
provenance decision that belongs to a human and to project memory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]

HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")
EXPERIMENT_ID = re.compile(r"\b(PMLAB-[A-Z0-9-]+-\d{3}|API-[A-Z0-9-]+-\d{3})\b")

SKIP_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", ".index"}

TEXT_SUFFIXES = {".md", ".json", ".jsonl", ".csv", ".txt", ".py", ".yml", ".yaml"}


class Finding:
    __slots__ = ("check", "severity", "path", "detail")

    def __init__(self, check: str, severity: str, path: str, detail: str) -> None:
        self.check = check
        self.severity = severity
        self.path = path
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {"check": self.check, "severity": self.severity, "path": self.path, "detail": self.detail}

    def __str__(self) -> str:
        return f"[{self.severity}] {self.check}: {self.path} — {self.detail}"


def iter_files(base: Path, suffixes: set[str] | None = None) -> Iterable[Path]:
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if suffixes and path.suffix.lower() not in suffixes:
            continue
        yield path


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"HEAD:{relative}"], cwd=ROOT, capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def walk_json(value: Any, key_path: list[str]) -> Iterable[tuple[list[str], str, Any]]:
    """Yield (key_path, key, value) for every leaf in a JSON structure."""
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                yield from walk_json(child, key_path + [str(key)])
            else:
                yield key_path, str(key), child
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                yield from walk_json(child, key_path + [str(index)])
            else:
                yield key_path, str(index), child


def resolve_declared_target(manifest: Path, key: str, key_path: list[str]) -> tuple[Path, bool] | None:
    """Work out which file a declared digest refers to.

    Returns the resolved path plus whether the mapping is *certain*.

    A key that is itself a path names its file unambiguously. A key of the form
    ``<name>_sha256`` is only a guess: this repository also uses that shape for
    derived semantic digests that are deliberately not the digest of any file.
    ``rankings_sha256`` in the reuse-characterization run is one such case — it
    digests the ranking order to prove cross-process reproducibility, and does
    not equal the digest of ``rankings.json``. Treating those as file claims
    produces false positives, so they are reported at a lower severity.
    """
    candidate = key
    if "/" in candidate or candidate.endswith(tuple(TEXT_SUFFIXES)):
        absolute = ROOT / candidate
        if absolute.is_file():
            return absolute, True
        sibling = manifest.parent / candidate
        if sibling.is_file():
            return sibling, True
        return None

    if candidate.endswith("_sha256"):
        stem = candidate[: -len("_sha256")]
        for suffix in (".json", ".jsonl", ".md", ".txt", ".csv"):
            sibling = manifest.parent / f"{stem}{suffix}"
            if sibling.is_file():
                return sibling, False
    return None


SUPERSEDED_MARKER = "SUPERSEDED.json"

# A marker suppresses hash checking, so it is itself a security boundary. These
# fields must all be present and usable or the marker is rejected.
MARKER_REQUIRED = ("status", "superseded_by", "reason", "recorded_at")


def read_marker(marker: Path) -> tuple[dict[str, Any] | None, str]:
    """Validate a supersession marker. Returns (document, reason_if_rejected).

    An adversarial review demonstrated that an empty ``{}`` file placed anywhere
    above a manifest silenced every hash check beneath it, giving a second and
    weaker route to making the audit pass — the very behaviour the marker exists
    to avoid. Validation is therefore **fail-closed**: anything unparseable,
    incomplete, or pointing at a successor that does not exist suppresses
    nothing, and is reported.
    """
    try:
        document = json.loads(marker.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return None, f"unreadable or invalid JSON: {error}"
    if not isinstance(document, dict):
        return None, "must be a JSON object"
    missing = [field for field in MARKER_REQUIRED if not str(document.get(field, "")).strip()]
    if missing:
        return None, f"missing required field(s): {', '.join(missing)}"
    if document.get("status") != "superseded":
        return None, f"status must be 'superseded', got {document.get('status')!r}"
    successor = str(document["superseded_by"])
    if not (ROOT / successor).exists():
        return None, f"superseded_by points at a path that does not exist: {successor}"
    if (ROOT / successor).resolve() == marker.parent.resolve():
        return None, "superseded_by points at the marker's own directory"
    return document, ""


def superseded_by_marker(manifest: Path) -> tuple[Path, dict[str, Any] | None, str] | None:
    """Find the marker governing this manifest, if any, with its validity.

    A superseded packet keeps the bytes it actually declared. Its digests are
    stale rather than false: they described the repository correctly at the
    freeze commit. Reporting them as live breaks would push the project towards
    rewriting historical freezes to silence an audit.
    """
    for directory in (manifest.parent, *manifest.parent.parents):
        marker = directory / SUPERSEDED_MARKER
        if marker.is_file():
            document, reason = read_marker(marker)
            return marker, document, reason
        if directory == ROOT:
            break
    return None


def check_declared_hashes(findings: list[Finding], counters: Counter) -> None:
    for manifest in iter_files(ROOT / "data", {".json"}):
        if manifest.name == SUPERSEDED_MARKER:
            continue
        governing = superseded_by_marker(manifest)
        if governing is not None:
            marker, document, rejection = governing
            if document is None:
                counters["invalid_supersession_markers"] += 1
                findings.append(
                    Finding(
                        "invalid-supersession-marker",
                        "high",
                        marker.relative_to(ROOT).as_posix(),
                        f"{rejection}. Suppressing nothing; declarations below are still checked.",
                    )
                )
                # Fall through: an invalid marker must not silence anything.
            else:
                counters["declarations_in_superseded_packets"] += 1
                findings.append(
                    Finding(
                        "superseded-packet",
                        "low",
                        manifest.relative_to(ROOT).as_posix(),
                        f"declarations not checked; packet superseded by {document['superseded_by']}",
                    )
                )
                continue
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            continue
        relative_manifest = manifest.relative_to(ROOT).as_posix()
        for key_path, key, value in walk_json(payload, []):
            if not isinstance(value, str) or not HEX64.match(value):
                continue
            counters["declared_hashes_seen"] += 1
            resolved = resolve_declared_target(manifest, key, key_path)
            if resolved is None:
                counters["declared_hashes_unresolvable"] += 1
                continue
            target, certain = resolved
            counters["declared_hashes_resolved"] += 1
            counters["declared_hashes_certain" if certain else "declared_hashes_guessed"] += 1
            relative_target = target.relative_to(ROOT).as_posix()
            working = digest_bytes(target.read_bytes())
            if working == value:
                counters["match_working_copy"] += 1
                blob = git_blob(relative_target)
                if blob is not None and digest_bytes(blob) != value:
                    counters["windows_only_freeze"] += 1
                    findings.append(
                        Finding(
                            "declared-hash",
                            "high",
                            relative_target,
                            f"declared digest matches the working copy but not the Git blob; "
                            f"declared in {relative_manifest} under '{key}'. "
                            f"Not reproducible on a checkout without CRLF conversion.",
                        )
                    )
                continue
            blob = git_blob(relative_target)
            if blob is not None and digest_bytes(blob) == value:
                counters["match_blob_only"] += 1
                continue
            if not certain:
                # The key was matched by the <name>_sha256 heuristic, which this
                # repository also uses for derived digests. A mismatch here is
                # more likely to mean "not a file digest" than "broken freeze".
                counters["ambiguous_declaration"] += 1
                findings.append(
                    Finding(
                        "ambiguous-declaration",
                        "low",
                        relative_target,
                        f"'{key}' in {relative_manifest} matches no byte form of this file; "
                        f"it is probably a derived digest rather than a file digest. "
                        f"Declare derived digests under a name that cannot be read as a file.",
                    )
                )
                continue
            counters["match_neither"] += 1
            findings.append(
                Finding(
                    "declared-hash",
                    "critical",
                    relative_target,
                    f"declared digest matches neither the working copy nor the Git blob; "
                    f"declared in {relative_manifest} under '{key}'. "
                    f"The file changed after it was frozen.",
                )
            )


def check_registry_paths(findings: list[Finding], counters: Counter) -> set[str]:
    registry = ROOT / "data" / "lab" / "experiment-registry.csv"
    identifiers: set[str] = set()
    if not registry.is_file():
        findings.append(Finding("registry-paths", "critical", "data/lab/experiment-registry.csv", "missing"))
        return identifiers
    with registry.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            experiment = (row.get("experiment_id") or "").strip()
            if experiment:
                identifiers.add(experiment)
            counters["registry_rows"] += 1
            for column in ("manifest_path", "artifact_path"):
                raw = (row.get(column) or "").strip()
                if not raw or raw.lower() in {"none", "n/a", "-", "tbd", "pending"}:
                    continue
                for candidate in re.split(r"[;\s]+", raw):
                    candidate = candidate.strip().strip('"')
                    if not candidate or candidate.startswith("http"):
                        continue
                    counters["registry_paths_checked"] += 1
                    if not (ROOT / candidate).exists():
                        counters["registry_paths_missing"] += 1
                        findings.append(
                            Finding(
                                "registry-paths",
                                "medium",
                                candidate,
                                f"{column} for {experiment or '<unnamed row>'} does not exist",
                            )
                        )
    return identifiers


def check_memory_sources(findings: list[Finding], counters: Counter) -> None:
    events = ROOT / "memory" / "events.jsonl"
    if not events.is_file():
        return
    for line in events.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for reference in event.get("source_refs") or []:
            if not isinstance(reference, str):
                continue
            if reference.startswith(("http://", "https://", "doi:", "arXiv:", "paper:")):
                continue
            bare = reference.split("#", 1)[0].split(":", 1)[0].strip()
            if not bare or not re.search(r"[/.]", bare):
                continue
            counters["memory_paths_checked"] += 1
            if not (ROOT / bare).exists():
                counters["memory_paths_missing"] += 1
                findings.append(
                    Finding(
                        "memory-sources",
                        "medium",
                        bare,
                        f"cited by {event.get('id')} but does not exist in the working tree",
                    )
                )


def check_doc_links(findings: list[Finding], counters: Counter) -> None:
    for document in iter_files(ROOT / "docs", {".md"}):
        text = document.read_text(encoding="utf-8-sig", errors="replace")
        for match in MARKDOWN_LINK.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            counters["doc_links_checked"] += 1
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                counters["doc_links_broken"] += 1
                findings.append(
                    Finding(
                        "doc-links",
                        "low",
                        document.relative_to(ROOT).as_posix(),
                        f"link target '{target}' does not resolve",
                    )
                )


def check_orphan_experiments(findings: list[Finding], counters: Counter, registered: set[str]) -> None:
    mentioned: dict[str, str] = {}
    for document in iter_files(ROOT / "docs", {".md"}):
        text = document.read_text(encoding="utf-8-sig", errors="replace")
        for match in EXPERIMENT_ID.finditer(text):
            mentioned.setdefault(match.group(1), document.relative_to(ROOT).as_posix())
    for identifier, where in sorted(mentioned.items()):
        counters["experiment_ids_in_docs"] += 1
        if identifier not in registered:
            counters["experiment_ids_unregistered"] += 1
            findings.append(
                Finding(
                    "orphan-experiments",
                    "medium",
                    where,
                    f"{identifier} is described in documentation but absent from the experiment registry",
                )
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when any finding is present (default exits non-zero only on critical findings)",
    )
    parser.add_argument("--check", action="append", default=None, help="run only the named check")
    arguments = parser.parse_args(argv)

    findings: list[Finding] = []
    counters: Counter = Counter()
    selected = set(arguments.check) if arguments.check else None

    def enabled(name: str) -> bool:
        return selected is None or name in selected

    registered: set[str] = set()
    if enabled("registry-paths") or enabled("orphan-experiments"):
        registered = check_registry_paths(findings, counters)
        if not enabled("registry-paths"):
            findings[:] = [item for item in findings if item.check != "registry-paths"]
    if enabled("declared-hash"):
        check_declared_hashes(findings, counters)
    if enabled("memory-sources"):
        check_memory_sources(findings, counters)
    if enabled("doc-links"):
        check_doc_links(findings, counters)
    if enabled("orphan-experiments"):
        check_orphan_experiments(findings, counters, registered)

    by_check = Counter(item.check for item in findings)
    by_severity = Counter(item.severity for item in findings)

    if arguments.format == "json":
        print(
            json.dumps(
                {
                    "counters": dict(sorted(counters.items())),
                    "findings_by_check": dict(sorted(by_check.items())),
                    "findings_by_severity": dict(sorted(by_severity.items())),
                    "findings": [item.as_dict() for item in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("Repository claim audit\n")
        print("Counters")
        for name, value in sorted(counters.items()):
            print(f"  {name:<32} {value}")
        print("\nFindings by check")
        for name, value in sorted(by_check.items()) or [("none", 0)]:
            print(f"  {name:<32} {value}")
        print("\nFindings by severity")
        for name in ("critical", "high", "medium", "low"):
            if by_severity.get(name):
                print(f"  {name:<32} {by_severity[name]}")
        if findings:
            print("\nDetail (first 40)")
            for item in findings[:40]:
                print(f"  {item}")
            if len(findings) > 40:
                print(f"  … {len(findings) - 40} more; use --format json for the full list")
        else:
            print("\nNo findings.")

    if arguments.strict and findings:
        return 1
    if by_severity.get("critical"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
