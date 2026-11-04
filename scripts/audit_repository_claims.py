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

A declared hash that no longer matches can be explained but never silenced. A
note named <manifest>.DRIFT.json, next to the manifest, downgrades the declaration
it names (one manifest, one file, one declared digest) from critical to a low
"explained-drift" finding, and only when the note proves, from Git, that the
declaration was true at an earlier commit and names the commit that changed the
file. See prove_drift.

A companion may contain additional_declarations for the same manifest. Each is
an independently scoped, fully populated note checked by the same Git proofs;
no directory or neighbouring declaration is exempted.

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
from urllib.parse import unquote

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


# A commit id read from a JSON note is passed to Git, so it must look like one. Always
# use fullmatch: a trailing "$" would also accept a trailing newline.
COMMIT_ID = re.compile(r"[0-9a-f]{7,40}")


def git_blob_at(commit: str, relative: str) -> bytes | None:
    """The bytes of ``relative`` at ``commit``. The caller has validated ``commit``."""
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"], cwd=ROOT, capture_output=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def git_commit_exists(commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True, check=False
    )
    return result.returncode == 0


def git_is_ancestor(older: str, newer: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer], cwd=ROOT, capture_output=True, check=False
    )
    return result.returncode == 0


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


DRIFT_SUFFIX = ".DRIFT.json"
DRIFT_STATUS = "declaration-drift-explained"

# A note weakens a check, so like a supersession marker it is fail-closed: every
# field must be present and every claim in it is re-derived from Git, not trusted.
DRIFT_REQUIRED = (
    "status",
    "manifest",
    "path",
    "declared_sha256",
    "declared_matched_at",
    "changed_in",
    "current_sha256",
    "reason",
    "recorded_at",
)


def drift_annotation_for(manifest: Path) -> Path:
    return manifest.with_name(manifest.stem + DRIFT_SUFFIX)


def load_drift_annotation(annotation: Path) -> tuple[dict[str, Any] | None, str]:
    """Parse a drift note and check its shape. Says nothing yet about whether it is true."""
    try:
        document = json.loads(annotation.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        # ValueError covers both invalid JSON and undecodable bytes.
        return None, f"unreadable or invalid JSON: {error}"
    if not isinstance(document, dict):
        return None, "must be a JSON object"
    missing = [field for field in DRIFT_REQUIRED if not document.get(field)]
    if missing:
        return None, f"missing required field(s): {', '.join(missing)}"
    if document["status"] != DRIFT_STATUS:
        return None, f"status must be {DRIFT_STATUS!r}, got {document['status']!r}"
    additional = document.get("additional_declarations", [])
    if not isinstance(additional, list):
        return None, "additional_declarations must be a list"
    seen = {(document["path"], document["declared_sha256"])}
    for entry in additional:
        if not isinstance(entry, dict) or any(not entry.get(field) for field in DRIFT_REQUIRED):
            return None, "additional declaration is missing required fields"
        if entry["status"] != DRIFT_STATUS or entry["manifest"] != document["manifest"]:
            return None, "additional declaration must have the same status and manifest"
        if "additional_declarations" in entry:
            return None, "nested additional declarations are not permitted"
        if not isinstance(entry["path"], str) or not isinstance(entry["declared_sha256"], str):
            return None, "additional declaration path and digest must be strings"
        key = (entry["path"], entry["declared_sha256"])
        if key in seen:
            return None, "duplicate drift declaration"
        seen.add(key)
    return document, ""


def matching_drift_declaration(document: dict, manifest: str, target: str, declared: str) -> dict | None:
    for entry in [document, *document.get("additional_declarations", [])]:
        if entry["manifest"] == manifest and entry["path"] == target and entry["declared_sha256"] == declared:
            return entry
    return None


def prove_drift(document: dict[str, Any], target_relative: str, declared: str, working_digest: str) -> str:
    """Re-derive every claim in a drift note. Returns "" when all hold, else the first that fails.

    A freeze can be broken honestly: the file was edited after its manifest was
    committed, and the manifest was never rewritten. Rewriting the manifest to
    match would destroy the evidence, and a directory-wide supersession marker
    would silence every declaration beside it. A drift note explains exactly one
    declaration instead, and keeps it visible as a low finding.

    It is accepted only if all of the following re-derive from Git:

    * every commit in ``declared_matched_at`` holds bytes that hash to the declared
      digest, so the declaration was once true, and precedes ``changed_in``;
    * ``changed_in`` exists, is reachable from HEAD, and holds different bytes;
    * ``current_sha256`` equals the file's bytes today, so a further edit voids the
      note and has to be explained again;
    * if ``successor_manifest`` is given, it is a manifest under data/ (not a note or a
      marker) that declares ``current_sha256`` for this very file.

    What it does not prove: that ``changed_in`` is the first change after the freeze, or
    that it follows the manifest's own commit. Those stay the author's claim, recorded in
    the note; the audit insists on the Git-derived facts above.
    """
    if document["current_sha256"] != working_digest:
        return "the file changed again after this note was written (current_sha256 no longer matches its bytes)"
    matched = document["declared_matched_at"]
    changed_in = document["changed_in"]
    if not isinstance(matched, list) or not all(
        isinstance(item, str) and COMMIT_ID.fullmatch(item) for item in matched
    ):
        return "declared_matched_at must be a list of commit ids"
    if not isinstance(changed_in, str) or not COMMIT_ID.fullmatch(changed_in):
        return "changed_in must be a commit id"
    if not git_commit_exists(changed_in):
        return f"changed_in {changed_in} is not a commit in this repository"
    for commit in matched:
        if not git_commit_exists(commit):
            return f"declared_matched_at names {commit}, which is not a commit in this repository"
        blob = git_blob_at(commit, target_relative)
        if blob is None or digest_bytes(blob) != declared:
            return f"{target_relative} at {commit} does not hash to the declared digest, so it was never true there"
        if not git_is_ancestor(commit, changed_in):
            return f"{commit} is not an ancestor of changed_in {changed_in}"
    changed_blob = git_blob_at(changed_in, target_relative)
    if changed_blob is None or digest_bytes(changed_blob) == declared:
        return f"{target_relative} at changed_in {changed_in} still holds the declared bytes, so nothing changed there"
    if not git_is_ancestor(changed_in, "HEAD"):
        return f"changed_in {changed_in} is not reachable from HEAD"
    successor = document.get("successor_manifest")
    if successor:
        path = (ROOT / str(successor)).resolve()
        if (ROOT / "data").resolve() not in path.parents:
            return f"successor_manifest must be a file under data/: {successor}"
        if not path.is_file():
            return f"successor_manifest does not exist: {successor}"
        if path.name == SUPERSEDED_MARKER or path.name.endswith(DRIFT_SUFFIX):
            return f"successor_manifest cannot be a marker or a drift note: {successor}"
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            return f"successor_manifest is unreadable: {error}"
        target = (ROOT / target_relative).resolve()
        for key_path, key, value in walk_json(payload, []):
            if value != working_digest:
                continue
            resolved = resolve_declared_target(path, key, key_path)
            if resolved is not None and resolved[1] and resolved[0].resolve() == target:
                break
        else:
            return f"successor_manifest {successor} does not declare current_sha256 for {target_relative}"
    return ""


def check_declared_hashes(findings: list[Finding], counters: Counter) -> None:
    for manifest in iter_files(ROOT / "data", {".json"}):
        if manifest.name == SUPERSEDED_MARKER:
            continue
        if manifest.name.endswith(DRIFT_SUFFIX):
            companion = manifest.with_name(manifest.name[: -len(DRIFT_SUFFIX)] + ".json")
            if companion.is_file():
                continue  # a drift note: it is read when its own manifest is checked
            counters["invalid_drift_annotations"] += 1
            findings.append(
                Finding(
                    "invalid-drift-annotation",
                    "high",
                    manifest.relative_to(ROOT).as_posix(),
                    f"there is no {companion.name} beside it, so it explains nothing. "
                    f"It is checked as an ordinary manifest instead.",
                )
            )
        reported_invalid_notes: set[str] = set()
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
            note = drift_annotation_for(manifest)
            if note.is_file():
                relative_note = note.relative_to(ROOT).as_posix()
                document, rejection = load_drift_annotation(note)
                if document is None:
                    if relative_note not in reported_invalid_notes:
                        reported_invalid_notes.add(relative_note)
                        counters["invalid_drift_annotations"] += 1
                        findings.append(
                            Finding(
                                "invalid-drift-annotation",
                                "high",
                                relative_note,
                                f"{rejection}. Suppressing nothing; declarations are still checked.",
                            )
                        )
                elif (document := matching_drift_declaration(document, relative_manifest, relative_target, value)) is not None:
                    problem = prove_drift(document, relative_target, value, working)
                    if not problem:
                        counters["explained_drift"] += 1
                        findings.append(
                            Finding(
                                "explained-drift",
                                "low",
                                relative_target,
                                f"declared digest in {relative_manifest} under '{key}' no longer matches; "
                                f"explained by {relative_note}: it matched at "
                                f"{', '.join(document['declared_matched_at'])} and changed in {document['changed_in']}.",
                            )
                        )
                        continue
                    counters["invalid_drift_annotations"] += 1
                    findings.append(
                        Finding(
                            "invalid-drift-annotation",
                            "high",
                            relative_note,
                            f"{problem}. Suppressing nothing; the declaration is still reported as broken.",
                        )
                    )
                # A note that concerns a different declaration explains nothing here.
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
            # A link to a path with a space is written percent-encoded (Folder%20Name) to be
            # valid Markdown, so decode it before looking for the file.
            try:
                exists = (document.parent / unquote(target)).resolve().exists()
            except (ValueError, OSError):
                exists = False  # for example an embedded NUL written as %00: report it, never abort the audit
            if not exists:
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
