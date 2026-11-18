"""The claim audit protects files declared in publication manifests (PUBLISHED_FILES.json).

An external audit (gpt raport, 2026-11-18) showed that a published table listed in a
PUBLISHED_FILES.json could be edited or deleted without any finding: the digest sits under
the key ``sha256`` next to a ``target`` / ``published_path`` field, which the audit did not
read, and a deleted file named by a path key was silently "unresolvable". These tests build
small real Git repositories, because the audit compares declarations with Git history.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_repository_claims as audit  # noqa: E402
import pinned_files as pf  # noqa: E402

TABLE = b"cycle,unit,arm,seed,solved\nc1,g1,none,1,0\nc1,g1,retrieved_task,1,1\n"
README = b"# Result\n\nOne table.\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         "-c", "core.autocrlf=false", *args],
        cwd=root, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def run_audit() -> tuple[list, Counter]:
    findings: list = []
    counters: Counter = Counter()
    audit.check_declared_hashes(findings, counters)
    return findings, counters


def verdicts(findings: list) -> list[tuple[str, str]]:
    return sorted((item.check, item.severity) for item in findings)


EXPORT_DIR = "data/lab/autolab-x"


def export_manifest(entries: dict[str, bytes], **extra: object) -> bytes:
    """A manifest in the shape scripts/aamr_export.py writes (V3/V4)."""
    published = [
        {"path": name, "target": f"{EXPORT_DIR}/{name}", "sha256": sha(data), "sha256_source": sha(data),
         "bytes": len(data), "edits": ["none"]}
        for name, data in entries.items()
    ]
    document = {"task": "autolab X", "published": published, "private": [], "paths_are_relative": True}
    document.update(extra)
    return (json.dumps(document, indent=1) + "\n").encode()


@pytest.fixture
def exported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "-q")
    write(tmp_path / EXPORT_DIR / "README.md", README)
    write(tmp_path / EXPORT_DIR / "per_unit.csv", TABLE)
    write(tmp_path / EXPORT_DIR / "PUBLISHED_FILES.json", export_manifest({"README.md": README, "per_unit.csv": TABLE}))
    commit_all(tmp_path, "export")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    return tmp_path


def test_a_valid_export_is_checked_and_clean(exported: Path) -> None:
    findings, counters = run_audit()
    assert findings == []
    assert counters["declared_hashes_certain"] == 2
    assert counters["match_working_copy"] == 2
    assert counters["declared_source_digests"] == 2  # counted, never compared with the published bytes
    assert counters["declared_hashes_unresolvable"] == 0


def test_a_one_byte_change_to_a_published_table_is_critical(exported: Path) -> None:
    table = exported / EXPORT_DIR / "per_unit.csv"
    table.write_bytes(TABLE.replace(b"c1,g1,none,1,0", b"c1,g1,none,1,1"))
    commit_all(exported, "edit the published table")
    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-hash", "critical")]
    assert findings[0].path == f"{EXPORT_DIR}/per_unit.csv"


def test_a_deleted_published_table_is_critical(exported: Path) -> None:
    (exported / EXPORT_DIR / "per_unit.csv").unlink()
    commit_all(exported, "delete the published table")
    findings, counters = run_audit()
    assert verdicts(findings) == [("declared-file-missing", "critical")]
    assert findings[0].path == f"{EXPORT_DIR}/per_unit.csv"
    assert counters["declared_files_missing"] == 1


def test_a_deletion_is_critical_before_it_is_committed(exported: Path) -> None:
    (exported / EXPORT_DIR / "per_unit.csv").unlink()
    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-file-missing", "critical")]


def test_the_published_digest_is_compared_not_the_source_digest(exported: Path) -> None:
    """A sanitised export: the source digest differs from the published one, and only the latter binds."""
    manifest = exported / EXPORT_DIR / "PUBLISHED_FILES.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["published"][1]["sha256_source"] = sha(b"the unsanitised source bytes")
    manifest.write_bytes(json.dumps(document).encode())
    commit_all(exported, "sanitised export")
    assert run_audit()[0] == []

    document["published"][1]["sha256"] = sha(b"something else")
    document["published"][1]["sha256_source"] = sha(TABLE)  # matching the source digest is not enough
    manifest.write_bytes(json.dumps(document).encode())
    commit_all(exported, "a manifest whose published digest is wrong")
    assert verdicts(run_audit()[0]) == [("declared-hash", "critical")]


def test_an_unresolvable_digest_in_a_publication_manifest_is_a_finding(exported: Path) -> None:
    manifest = exported / EXPORT_DIR / "PUBLISHED_FILES.json"
    manifest.write_bytes(export_manifest({"README.md": README, "per_unit.csv": TABLE}, bundle_digest=sha(b"x")))
    commit_all(exported, "a digest naming no file")
    findings, counters = run_audit()
    assert verdicts(findings) == [("unresolvable-publication-digest", "critical")]
    assert counters["unresolvable_in_publication_manifest"] == 1


def test_a_publication_record_outside_the_repository_is_not_silent(exported: Path) -> None:
    manifest = exported / EXPORT_DIR / "PUBLISHED_FILES.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["published"][0]["target"] = "../../../../outside/README.md"
    document["published"][0]["path"] = "../../../../outside/README.md"
    manifest.write_bytes(json.dumps(document).encode())
    commit_all(exported, "a record pointing outside")
    assert verdicts(run_audit()[0]) == [("unresolvable-publication-digest", "critical")]


K1_DIR = "data/lab/k1"


@pytest.fixture
def k1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The K1 shape: files[].published_path relative to the manifest, sha256 and sha256_original."""
    git(tmp_path, "init", "-q")
    write(tmp_path / K1_DIR / "report/results.json", b'{"verdict": "null"}\n')
    write(tmp_path / K1_DIR / "eval/A.jsonl", b'{"a": 1}\n')
    files = [
        {"published_path": name, "source": name, "kind": "result", "bytes": len(data), "sha256": sha(data),
         "sha256_original": sha(data + b"/local/path"), "edits": ["replaced 1 machine-local path"], "has_local_path": True}
        for name, data in (("report/results.json", b'{"verdict": "null"}\n'), ("eval/A.jsonl", b'{"a": 1}\n'))
    ]
    write(tmp_path / K1_DIR / "PUBLISHED_FILES.json", json.dumps({"files": files}, indent=1).encode())
    commit_all(tmp_path, "publish K1")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    return tmp_path


def test_k1_shape_is_resolved_against_the_manifest_directory(k1: Path) -> None:
    findings, counters = run_audit()
    assert findings == []
    assert counters["declared_hashes_certain"] == 2
    assert counters["declared_source_digests"] == 2


def test_k1_shape_detects_a_change_and_a_deletion(k1: Path) -> None:
    write(k1 / K1_DIR / "report/results.json", b'{"verdict": "confirmed"}\n')
    (k1 / K1_DIR / "eval/A.jsonl").unlink()
    commit_all(k1, "tamper")
    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-file-missing", "critical"), ("declared-hash", "critical")]
    assert {item.path for item in findings} == {f"{K1_DIR}/report/results.json", f"{K1_DIR}/eval/A.jsonl"}


def test_pinned_files_reports_publication_records_as_frozen(k1: Path) -> None:
    table = pf.declarations(k1)
    answer = pf.verdict(f"{K1_DIR}/report/results.json", table[f"{K1_DIR}/report/results.json"])
    assert answer["frozen"] is True
    assert answer["pinning_manifests"] == [f"{K1_DIR}/PUBLISHED_FILES.json"]


# Path-keyed manifests: the older freeze format.

@pytest.fixture
def path_keyed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "-q")
    write(tmp_path / "scripts/tool.py", b"X = 1\n")
    write(tmp_path / "data/lab/run/manifest.json", json.dumps({
        "inputs": {"scripts/tool.py": sha(b"X = 1\n"),
                   "raw/never-committed.jsonl": sha(b"private capture")},  # an external input: never in the repo
    }).encode())
    commit_all(tmp_path, "freeze")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    return tmp_path


def test_a_path_key_never_committed_stays_unresolvable(path_keyed: Path) -> None:
    findings, counters = run_audit()
    assert findings == []
    assert counters["declared_hashes_unresolvable"] == 1


def test_a_deleted_path_keyed_freeze_is_critical(path_keyed: Path) -> None:
    (path_keyed / "scripts/tool.py").unlink()
    commit_all(path_keyed, "delete a frozen helper")
    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-file-missing", "critical")]
    assert findings[0].path == "scripts/tool.py"


def test_a_deleted_freeze_that_arrived_by_rename_is_critical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file that reached its frozen path through `git mv` was never "added" there with rename detection on."""
    git(tmp_path, "init", "-q")
    write(tmp_path / "scripts/old_tool.py", b"X = 1\n")
    commit_all(tmp_path, "add helper")
    git(tmp_path, "mv", "scripts/old_tool.py", "scripts/tool.py")
    write(tmp_path / "data/lab/run/manifest.json", json.dumps({"inputs": {"scripts/tool.py": sha(b"X = 1\n")}}).encode())
    commit_all(tmp_path, "rename and freeze")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    (tmp_path / "scripts/tool.py").unlink()
    commit_all(tmp_path, "delete the frozen helper")
    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-file-missing", "critical")]


def deletion_note(root: Path, **overrides: object) -> dict:
    log = git(root, "log", "--format=%H").split()
    document = {
        "status": "declaration-drift-explained",
        "manifest": "data/lab/run/manifest.json",
        "path": "scripts/tool.py",
        "declared_sha256": sha(b"X = 1\n"),
        "declared_matched_at": [log[-1]],
        "changed_in": log[0],
        "current_sha256": audit.ABSENT,
        "moved_to": "scripts/tools/tool.py",
        "reason": "moved",
        "recorded_at": "2026-11-18",
    }
    document.update(overrides)
    return document


@pytest.fixture
def moved(path_keyed: Path) -> Path:
    (path_keyed / "scripts/tool.py").unlink()
    write(path_keyed / "scripts/tools/tool.py", b"X = 1\n")
    commit_all(path_keyed, "move a frozen helper")
    return path_keyed


def write_note(root: Path, document: dict) -> None:
    (root / "data/lab/run/manifest.DRIFT.json").write_text(json.dumps(document), encoding="utf-8")


def test_a_git_proved_deletion_note_downgrades_the_deletion(moved: Path) -> None:
    write_note(moved, deletion_note(moved))
    findings, _ = run_audit()
    assert verdicts(findings) == [("explained-drift", "low")]


@pytest.mark.parametrize(
    "overrides",
    [
        {"current_sha256": "0" * 64},           # a deleted file has no current bytes
        {"declared_sha256": sha(b"X = 2\n")},  # names another declaration
        {"moved_to": "scripts/nowhere.py"},     # the claimed new location does not exist
        {"successor_manifest": "data/lab/run/manifest.json"},
    ],
)
def test_a_deletion_note_that_does_not_hold_suppresses_nothing(moved: Path, overrides: dict) -> None:
    write_note(moved, deletion_note(moved, **overrides))
    assert ("declared-file-missing", "critical") in verdicts(run_audit()[0])


def test_a_deletion_note_must_name_the_commit_that_removed_the_file(moved: Path) -> None:
    first = git(moved, "log", "--format=%H").split()[-1]
    write_note(moved, deletion_note(moved, changed_in=first, declared_matched_at=[first]))
    assert ("declared-file-missing", "critical") in verdicts(run_audit()[0])


def test_an_absent_note_for_a_file_that_exists_is_rejected(path_keyed: Path) -> None:
    write(path_keyed / "scripts/tool.py", b"X = 2\n")
    commit_all(path_keyed, "edit")
    write_note(path_keyed, deletion_note(path_keyed, moved_to=None))
    assert verdicts(run_audit()[0]) == [("declared-hash", "critical"), ("invalid-drift-annotation", "high")]


def test_a_crlf_only_declaration_is_high_not_critical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A digest taken on a Windows checkout before .gitattributes disabled EOL conversion."""
    git(tmp_path, "init", "-q")
    report = b'{\n "ok": true\n}\n'
    write(tmp_path / "data/lab/r/report.json", report)
    write(tmp_path / "data/lab/r/receipt.json", json.dumps(
        {"artifacts": [{"path": "data/lab/r/report.json", "sha256": sha(report.replace(b"\n", b"\r\n"))}]}).encode())
    commit_all(tmp_path, "receipt")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    assert verdicts(run_audit()[0]) == [("declared-hash", "high")]
    write(tmp_path / "data/lab/r/report.json", b'{\n "ok": false\n}\n')
    commit_all(tmp_path, "a real change")
    assert verdicts(run_audit()[0]) == [("declared-hash", "critical")]


# The real repository.

@pytest.mark.parametrize(
    "manifest",
    [
        "data/lab/autolab-alfworld-ladder-r4-v3/PUBLISHED_FILES.json",
        "data/lab/autolab-alfworld-ladder-r4-v4/PUBLISHED_FILES.json",
        "data/lab/aamr-k1/PUBLISHED_FILES.json",
    ],
)
def test_the_real_v3_v4_and_k1_manifests_resolve_every_published_file_and_match(manifest: str) -> None:
    path = ROOT / manifest
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("published") or payload.get("files")
    checked = 0
    for key_path, key, value in audit.walk_json(payload, []):
        if not isinstance(value, str) or not audit.HEX64.match(value):
            continue
        kind, target, certain, _ = audit.classify_declaration(path, key, key_path, audit.container_at(payload, key_path))
        assert kind in {"file", "source"}, (key_path, key)
        if kind == "file":
            assert certain
            assert sha(target.read_bytes()) == value, target
            checked += 1
    assert checked == len(records)
