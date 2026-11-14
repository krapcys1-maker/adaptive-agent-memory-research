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


@pytest.mark.parametrize("bad", ["--output=leak", "abc1234\n", "ABCDEF1", "abc123", "abc1234; ls", ""])
def test_only_a_lowercase_hex_commit_id_ever_reaches_git(drifted: Scenario, bad: str) -> None:
    write_note(drifted, note_for(drifted, changed_in=bad))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    # Rejected by shape, before any commit lookup. With the shape check removed the
    # reason would be "not a commit in this repository" instead.
    reasons = [item.detail for item in findings if item.check == "invalid-drift-annotation"]
    assert reasons
    assert all("must be a commit id" in reason or "missing required field" in reason for reason in reasons)
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


def multi_note(scenario):
    other=scenario.root/'scripts/other.py'
    other.write_bytes(FROZEN)
    (scenario.root/MANIFEST).write_text(json.dumps({'files':{TARGET:sha(FROZEN),'scripts/other.py':sha(FROZEN)}}))
    matched=commit_all(scenario.root,'declare another file')
    other.write_bytes(EDITED)
    changed=commit_all(scenario.root,'edit the other file')
    document=note_for(scenario)
    document['additional_declarations']=[note_for(scenario,path='scripts/other.py',declared_matched_at=[matched],changed_in=changed)]
    return document


def test_multiple_declarations_each_require_their_own_git_proof(drifted):
    write_note(drifted,multi_note(drifted))
    findings,_=run_audit()
    assert verdicts(findings)==[('explained-drift','low'),('explained-drift','low')]


@pytest.mark.parametrize('damage',['wrong_current','wrong_history','foreign_manifest','duplicate','nested'])
def test_bad_additional_note_never_exempts_its_declaration(drifted,damage):
    doc=multi_note(drifted);extra=doc['additional_declarations'][0]
    if damage=='wrong_current':extra['current_sha256']=sha(FROZEN)
    elif damage=='wrong_history':extra['declared_matched_at']=[extra['changed_in']]
    elif damage=='foreign_manifest':extra['manifest']='data/lab/different.json'
    elif damage=='duplicate':doc['additional_declarations'].append(dict(extra))
    else:extra['additional_declarations']=[]
    write_note(drifted,doc)
    findings,_=run_audit()
    assert ('declared-hash','critical') in verdicts(findings)
    assert ('invalid-drift-annotation','high') in verdicts(findings)


def test_further_change_voids_only_its_proved_additional_note(drifted):
    doc=multi_note(drifted);write_note(drifted,doc)
    (drifted.root/'scripts/other.py').write_bytes(EDITED_AGAIN)
    findings,_=run_audit()
    assert ('declared-hash','critical') in verdicts(findings)
    assert ('invalid-drift-annotation','high') in verdicts(findings)
    assert ('explained-drift','low') in verdicts(findings)


@pytest.mark.parametrize('field',['path','declared_sha256'])
def test_non_string_note_identity_is_rejected_without_crashing(drifted,field):
    doc=note_for(drifted);doc[field]=['invalid']
    write_note(drifted,doc)
    findings,_=run_audit()
    assert ('declared-hash','critical') in verdicts(findings)
    assert ('invalid-drift-annotation','high') in verdicts(findings)


def test_a_successor_manifest_that_declares_the_current_bytes_of_that_file_is_accepted(drifted: Scenario) -> None:
    successor = drifted.root / "data" / "lab" / "next.json"
    successor.write_text(json.dumps({"files": {TARGET: sha(EDITED)}}), encoding="utf-8")
    write_note(drifted, note_for(drifted, successor_manifest="data/lab/next.json"))
    findings, _ = run_audit()
    assert verdicts(findings) == [("explained-drift", "low")]


@pytest.mark.parametrize(
    ("successor", "reason"),
    [
        ("data/lab/freeze.DRIFT.json", "cannot be a marker or a drift note"),  # the note itself
        ("../outside.json", "must be a file under data/"),
        ("scripts/address_extract.py", "must be a file under data/"),
        ("data/lab/missing.json", "does not exist"),
        ("data/lab/other.json", "does not declare"),  # holds the digest, but for another path
    ],
)
def test_a_successor_must_be_a_real_manifest_that_declares_this_file(
    drifted: Scenario, successor: str, reason: str
) -> None:
    other = drifted.root / "data" / "lab" / "other.json"
    other.write_text(json.dumps({"files": {"scripts/other.py": sha(EDITED)}}), encoding="utf-8")
    write_note(drifted, note_for(drifted, successor_manifest=successor))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any(reason in item.detail for item in findings if item.check == "invalid-drift-annotation")


@pytest.fixture
def elsewhere(drifted: Scenario) -> dict[str, str]:
    """Commits on a side branch: they exist, but are not ancestors of the drift."""
    main = git(drifted.root, "branch", "--show-current")
    git(drifted.root, "checkout", "-q", "-b", "side", drifted.created)
    (drifted.root / "side.txt").write_text("another commit\n", encoding="utf-8")
    frozen_again = commit_all(drifted.root, "side: the declared bytes again, in another commit")
    (drifted.root / TARGET).write_bytes(EDITED_AGAIN)
    changed_elsewhere = commit_all(drifted.root, "side: the file changed on another branch")
    git(drifted.root, "checkout", "-q", main)
    return {"frozen_again": frozen_again, "changed_elsewhere": changed_elsewhere}


def test_a_matched_commit_must_precede_the_change(drifted: Scenario, elsewhere: dict[str, str]) -> None:
    write_note(drifted, note_for(drifted, declared_matched_at=[elsewhere["frozen_again"]]))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("not an ancestor" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_the_change_must_be_reachable_from_head(drifted: Scenario, elsewhere: dict[str, str]) -> None:
    write_note(
        drifted,
        note_for(drifted, declared_matched_at=[drifted.created], changed_in=elsewhere["changed_elsewhere"]),
    )
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("not reachable from HEAD" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_an_unknown_matched_commit_is_rejected(drifted: Scenario) -> None:
    write_note(drifted, note_for(drifted, declared_matched_at=["0" * 40]))
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert any("not a commit" in item.detail for item in findings if item.check == "invalid-drift-annotation")


def test_a_note_that_is_not_utf8_is_reported_instead_of_crashing_the_audit(drifted: Scenario) -> None:
    drifted.note.write_bytes(b"\xff\xfe{")
    findings, _ = run_audit()
    assert ("declared-hash", "critical") in verdicts(findings)
    assert ("invalid-drift-annotation", "high") in verdicts(findings)


def test_a_drift_note_with_no_manifest_beside_it_is_audited_like_any_manifest(drifted: Scenario) -> None:
    """A real manifest must not escape the audit by being named like a note."""
    hidden = drifted.root / "data" / "lab" / "hidden.DRIFT.json"
    hidden.write_text(json.dumps({"files": {TARGET: sha(FROZEN)}}), encoding="utf-8")
    findings, _ = run_audit()
    assert verdicts(findings).count(("declared-hash", "critical")) == 2
    assert ("invalid-drift-annotation", "high") in verdicts(findings)


def test_a_percent_encoded_link_to_a_path_with_a_space_resolves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Markdown needs Folder%20Name for a folder called "Folder Name"; the audit must decode it."""
    (tmp_path / "docs" / "Folder Name").mkdir(parents=True)
    (tmp_path / "docs" / "Folder Name" / "b.md").write_text("target\n", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text(
        "[encoded](Folder%20Name/b.md) and [missing](Folder%20Name/nope.md)\n", encoding="utf-8"
    )
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    findings: list = []
    counters: Counter = Counter()
    audit.check_doc_links(findings, counters)
    assert [item.detail for item in findings] == ["link target 'Folder%20Name/nope.md' does not resolve"]
    assert counters["doc_links_checked"] == 2


def test_an_invalid_percent_encoded_target_is_reported_and_does_not_abort_the_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """%00 decodes to an embedded NUL, which makes the path operations raise; a literal % must still work."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "100%.md").write_text("target\n", encoding="utf-8")
    (tmp_path / "docs" / "a.md").write_text("[nul](x%00y.md) and [percent](100%.md)\n", encoding="utf-8")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    findings: list = []
    counters: Counter = Counter()
    audit.check_doc_links(findings, counters)
    assert [item.detail for item in findings] == ["link target 'x%00y.md' does not resolve"]
    assert counters["doc_links_checked"] == 2


def test_a_declared_digest_keyed_by_an_absolute_path_outside_the_repository_is_not_a_crash(tmp_path, monkeypatch) -> None:
    """A frozen artifact can record the absolute path of a file on the machine that wrote it. If that file exists on the
    machine running the audit, it is outside the repository and cannot be checked; it must be skipped, not abort the audit."""
    repo = tmp_path / "repo"
    outside = tmp_path / "elsewhere" / "note.md"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"a file outside the repository")
    manifest = repo / "data" / "lab" / "x" / "FREEZE.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"external_references": {outside.as_posix(): sha(b"a file outside the repository")}}),
                        encoding="utf-8")
    monkeypatch.setattr(audit, "ROOT", repo)

    findings, counters = run_audit()

    assert findings == []
    assert counters["declared_hashes_seen"] == 1
    assert counters["declared_hashes_unresolvable"] == 1
    assert counters["declared_hashes_resolved"] == 0
