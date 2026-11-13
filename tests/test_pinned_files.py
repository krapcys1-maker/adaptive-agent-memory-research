"""scripts/pinned_files.py: which manifests freeze a file, under the claim audit's own rules.

Synthetic trees only, except one check against this repository's own frozen kernel line.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_repository_claims as audit  # noqa: E402
import pinned_files as pf  # noqa: E402


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


@pytest.fixture()
def tree(tmp_path, monkeypatch):
    """A repository-shaped tree outside Git, with the audit pointed at it."""
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    a = write(tmp_path / "scripts/a.py", "A = 1\n")
    write(tmp_path / "scripts/b.py", "B = 2\n")
    write(tmp_path / "scripts/c.py", "C = 3\n")
    write(tmp_path / "scripts/free.py", "F = 4\n")
    notes = write(tmp_path / "data/lab/x/notes.json", "{}\n")
    write(tmp_path / "data/lab/x/manifest.json", json.dumps({
        "inputs": {"scripts/a.py": sha(a.read_bytes()),            # certain and current: frozen
                   "scripts/b.py": "0" * 64},                       # certain, already drifted: not binding
        "notes_sha256": sha(notes.read_bytes()),                    # a guess by key shape: never decides
    }))
    write(tmp_path / "data/lab/old/manifest.json", json.dumps({"scripts/c.py": sha(b"C = 3\n")}))
    write(tmp_path / "data/lab/new/README.md", "successor\n")
    write(tmp_path / "data/lab/old/SUPERSEDED.json", json.dumps({
        "status": "superseded", "superseded_by": "data/lab/new", "reason": "test", "recorded_at": "2026-11-13"}))
    return tmp_path


def test_path_key_with_current_digest_freezes_the_file(tree):
    table = pf.declarations(tree)
    answer = pf.verdict("scripts/a.py", table["scripts/a.py"])
    assert answer["frozen"] is True
    assert answer["pinning_manifests"] == ["data/lab/x/manifest.json"]


def test_drifted_declaration_is_reported_but_does_not_freeze(tree):
    answer = pf.verdict("scripts/b.py", pf.declarations(tree)["scripts/b.py"])
    assert answer["frozen"] is False
    assert answer["stale_declarations"] == ["data/lab/x/manifest.json"]


def test_guessed_sha256_key_is_listed_separately_and_never_freezes(tree):
    answer = pf.verdict("data/lab/x/notes.json", pf.declarations(tree)["data/lab/x/notes.json"])
    assert answer["frozen"] is False
    assert answer["guessed_declarations"] == ["data/lab/x/manifest.json"]


def test_valid_supersession_marker_releases_its_packet(tree):
    assert "scripts/c.py" not in pf.declarations(tree)


def test_invalid_supersession_marker_suppresses_nothing(tree):
    write(tree / "data/lab/old/SUPERSEDED.json", "{}")                 # the audit rejects an empty marker
    answer = pf.verdict("scripts/c.py", pf.declarations(tree)["scripts/c.py"])
    assert answer["frozen"] is True


def test_drift_notes_are_not_read_as_manifests(tree):
    write(tree / "data/lab/x/manifest.DRIFT.json", json.dumps({"scripts/free.py": sha(b"F = 4\n")}))
    assert "scripts/free.py" not in pf.declarations(tree)


def test_orphan_drift_note_is_checked_as_an_ordinary_manifest_like_the_audit_does(tree):
    write(tree / "data/lab/y/lonely.DRIFT.json", json.dumps({"scripts/free.py": sha(b"F = 4\n")}))
    assert pf.verdict("scripts/free.py", pf.declarations(tree)["scripts/free.py"])["frozen"] is True


def test_check_exit_code_separates_frozen_from_free(tree, capsys):
    assert pf.main(["--check", str(tree / "scripts/a.py")]) == 1
    assert pf.main(["--check", str(tree / "scripts/free.py")]) == 0
    assert "not frozen" in capsys.readouterr().out


def test_under_lists_only_frozen_files_and_json_is_parseable(tree, capsys):
    assert pf.main(["--under", "scripts", "--format", "json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [a["path"] for a in out["answers"]] == ["scripts/a.py"]
    assert out["frozen"] == 1


def test_unknown_path_is_an_error(tree, capsys):
    assert pf.main(["scripts/missing.py"]) == 2


def test_this_repositorys_live_kernel_line_is_reported_frozen():
    """The kernel README calls 0.2.0 the live line; manifests pin its bytes, so the audit forbids editing it in place."""
    table = pf.declarations(ROOT)
    answer = pf.verdict("scripts/wmb/kernel/memory_kernel.py", table.get("scripts/wmb/kernel/memory_kernel.py", []))
    assert answer["frozen"] is True
    assert all(m.startswith("data/") for m in answer["pinning_manifests"])
