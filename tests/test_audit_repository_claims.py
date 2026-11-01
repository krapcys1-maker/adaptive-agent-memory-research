"""How the claim audit treats a freeze that was edited after it was declared.

A declared hash that matches neither the working copy nor the Git blob is critical,
and must stay critical unless a drift note proves, from Git, that the declaration
was true once and names the commit that changed the file. These tests build a small
real repository, because the note is checked against actual history.

Every rejection case exists because a note weakens the check: it must never
become a cheap way to make the audit pass.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_repository_claims as audit  # noqa: E402

TARGET = "scripts/address_extract.py"
MANIFEST = "data/lab/freeze.json"
NOTE = "data/lab/freeze.DRIFT.json"

FROZEN = b"def extract(text):\n    return text\n"
EDITED = b"def extract(text, canonicalise=False):\n    return text\n"
EDITED_AGAIN = b"def extract(text, canonicalise=True):\n    return text\n"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.autocrlf=false",
            *args,
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


@dataclass
class Scenario:
    root: Path
    created: str
    froze: str
    changed: str

    @property
    def note(self) -> Path:
        return self.root / NOTE


@pytest.fixture
def drifted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Scenario:
    """A repository whose manifest declares FROZEN bytes for a file later edited to EDITED."""
    git(tmp_path, "init", "-q")
    target = tmp_path / TARGET
    target.parent.mkdir(parents=True)
    target.write_bytes(FROZEN)
    created = commit_all(tmp_path, "create the file")

    manifest = tmp_path / MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"files": {TARGET: sha(FROZEN)}}), encoding="utf-8")
    froze = commit_all(tmp_path, "freeze: declare its bytes")

    target.write_bytes(EDITED)
    changed = commit_all(tmp_path, "edit the file after the freeze")

    monkeypatch.setattr(audit, "ROOT", tmp_path)
    return Scenario(root=tmp_path, created=created, froze=froze, changed=changed)


def note_for(scenario: Scenario, **overrides: object) -> dict:
    document: dict = {
        "status": "declaration-drift-explained",
        "manifest": MANIFEST,
        "path": TARGET,
        "declared_sha256": sha(FROZEN),
        "declared_matched_at": [scenario.created, scenario.froze],
        "changed_in": scenario.changed,
        "current_sha256": sha(EDITED),
        "reason": "the file was edited after its manifest was committed",
        "recorded_at": "2026-11-01T00:00:00Z",
    }
    document.update(overrides)
    return document


def write_note(scenario: Scenario, document: object) -> None:
    scenario.note.write_text(json.dumps(document), encoding="utf-8")


def run_audit() -> tuple[list, Counter]:
    findings: list = []
    counters: Counter = Counter()
    audit.check_declared_hashes(findings, counters)
    return findings, counters


def verdicts(findings: list) -> list[tuple[str, str]]:
    return sorted((item.check, item.severity) for item in findings)


def test_a_drifted_declaration_without_a_note_is_critical(drifted: Scenario) -> None:
    findings, counters = run_audit()
    assert verdicts(findings) == [("declared-hash", "critical")]
    assert counters["match_neither"] == 1


def test_a_valid_note_downgrades_that_declaration_and_keeps_it_visible(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted))
    findings, counters = run_audit()
    assert verdicts(findings) == [("explained-drift", "low")]
    assert counters["explained_drift"] == 1
    assert counters["match_neither"] == 0
    # The note is not itself read as a manifest, so its digests are not counted as declarations.
    assert counters["declared_hashes_seen"] == 1
    assert drifted.changed in findings[0].detail


def test_a_note_about_another_digest_explains_nothing(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted, declared_sha256=sha(b"something else")))
    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-hash", "critical")]


def test_an_empty_note_suppresses_nothing_and_is_reported(drifted: Scenario) -> None:
    write_note(drifted, {})
    findings, counters = run_audit()
    assert verdicts(findings) == [("declared-hash", "critical"), ("invalid-drift-annotation", "high")]
    assert counters["invalid_drift_annotations"] == 1


def test_a_note_that_is_not_json_suppresses_nothing(drifted: Scenario) -> None:
    drifted.note.write_text("not json", encoding="utf-8")
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert ("invalid-drift-annotation", "high") in verdicts(findings)


def test_a_note_is_void_once_the_file_changes_again(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted))
    (drifted.root / TARGET).write_bytes(EDITED_AGAIN)
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("changed again" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_a_note_must_prove_the_declaration_was_once_true(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted, declared_matched_at=[drifted.changed]))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("never true" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_a_note_naming_an_unknown_commit_is_rejected(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted, changed_in="0" * 40))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("not a commit" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_a_note_cannot_claim_a_change_in_a_commit_that_holds_the_frozen_bytes(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted, changed_in=drifted.froze))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("nothing changed" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_a_note_cannot_pass_an_option_to_git_as_a_commit(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted, changed_in="--output=leak"))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert not (drifted.root / "leak").exists()


def test_a_note_explains_one_declaration_and_leaves_its_neighbour_critical(drifted: Scenario) -> None:
    other = drifted.root / "scripts" / "other.py"
    other.write_bytes(b"x = 1\n")
    commit_all(drifted.root, "add a second file")
    (drifted.root / MANIFEST).write_text(
        json.dumps({"files": {TARGET: sha(FROZEN), "scripts/other.py": sha(b"x = 1\n")}}),
        encoding="utf-8",
    )
    other.write_bytes(b"x = 2\n")
    commit_all(drifted.root, "edit the second file as well")
    write_note(drifted, note_for(drifted))

    findings, _ = run_audit()
    assert verdicts(findings) == [("declared-hash", "critical"), ("explained-drift", "low")]
    critical = next(item for item in findings if item.severity == "critical")
    assert critical.path == "scripts/other.py"


def test_a_successor_manifest_must_declare_the_current_bytes(drifted: Scenario) -> None:
    successor = drifted.root / "data" / "lab" / "next.json"
    successor.write_text(json.dumps({"digest": sha(EDITED)}), encoding="utf-8")
    write_note(drifted, note_for(drifted, successor_manifest="data/lab/next.json"))
    findings, _ = run_audit()
    assert verdicts(findings) == [("explained-drift", "low")]

    successor.write_text(json.dumps({"digest": sha(b"not the current bytes")}), encoding="utf-8")
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("does not declare" in item.detail for item in findings if item.check == "invalid-drift-annotation")
