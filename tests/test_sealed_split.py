"""Tampering tests for the I1 sealed held-out split.

The honest path must work, and every tampering attempt the protocol claims to
detect must actually be refused. A commit-and-reveal scheme that accepts a
forged input is worse than none, because it produces a confident false
guarantee.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sealed_split  # noqa: E402

KEY = "a" * 64
OTHER_KEY = "b" * 64


def write_pool(directory: Path, count: int = 40) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "pool.jsonl"
    path.write_text(
        "".join(
            json.dumps({"id": f"CASE-{index:03d}", "text": f"case body {index}"}, sort_keys=True) + "\n"
            for index in range(count)
        ),
        encoding="utf-8",
    )
    return path


def write_key(directory: Path, value: str = KEY) -> Path:
    path = directory / "key.hex"
    path.write_text(value + "\n", encoding="utf-8")
    return path


def write_candidate(directory: Path, body: str = "def solve(): return 1\n") -> Path:
    path = directory / "candidate.py"
    path.write_text(body, encoding="utf-8")
    return path


def seal(tmp_path: Path) -> tuple[Path, Path, Path]:
    pool = write_pool(tmp_path)
    key = write_key(tmp_path)
    sealed = tmp_path / "sealed"
    assert (
        sealed_split.main(
            ["seal", "--pool", str(pool), "--out", str(sealed), "--experiment", "TEST-001", "--key-file", str(key)]
        )
        == 0
    )
    return pool, key, sealed


def register(sealed: Path, candidate: Path) -> None:
    assert sealed_split.main(["register", "--sealed", str(sealed), "--candidate", str(candidate)]) == 0


def reveal(sealed: Path, pool: Path, key: Path) -> int:
    return sealed_split.main(["reveal", "--sealed", str(sealed), "--pool", str(pool), "--key-file", str(key)])


# --------------------------------------------------------------------------- honest path


def test_honest_path_seals_registers_reveals_and_verifies(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    candidate = write_candidate(tmp_path)
    register(sealed, candidate)
    assert reveal(sealed, pool, key) == 0

    manifest = json.loads((sealed / sealed_split.SEALED_MANIFEST).read_text(encoding="utf-8"))
    development = (sealed / sealed_split.DEVELOPMENT_FILE).read_text(encoding="utf-8").splitlines()
    challenge = (sealed / sealed_split.CHALLENGE_FILE).read_text(encoding="utf-8").splitlines()

    assert len(development) == manifest["counts"]["development"]
    assert len(challenge) == manifest["counts"]["challenge"]
    assert len(development) + len(challenge) == manifest["counts"]["pool"] == 40

    assert (
        sealed_split.main(["verify", "--sealed", str(sealed), "--pool", str(pool), "--key-file", str(key)])
        == 0
    )


def test_split_is_reproducible_from_key_and_ids_alone() -> None:
    key = bytes.fromhex(KEY)
    first = [sealed_split.assign(key, f"CASE-{index:03d}") for index in range(40)]
    second = [sealed_split.assign(key, f"CASE-{index:03d}") for index in range(40)]
    assert first == second
    assert set(first) == {"development", "challenge"}


def test_a_different_key_produces_a_different_split() -> None:
    left = [sealed_split.assign(bytes.fromhex(KEY), f"CASE-{i:03d}") for i in range(40)]
    right = [sealed_split.assign(bytes.fromhex(OTHER_KEY), f"CASE-{i:03d}") for i in range(40)]
    assert left != right


# --------------------------------------------------------------------------- the manifest must leak nothing


def test_sealed_manifest_contains_neither_key_nor_challenge_cases(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    text = (sealed / sealed_split.SEALED_MANIFEST).read_text(encoding="utf-8")

    assert KEY not in text

    key_bytes = bytes.fromhex(KEY)
    challenge_ids = [
        f"CASE-{index:03d}"
        for index in range(40)
        if sealed_split.assign(key_bytes, f"CASE-{index:03d}") == "challenge"
    ]
    assert challenge_ids, "fixture must produce at least one challenge case"
    for identifier in challenge_ids:
        assert identifier not in text

    assert not (sealed / sealed_split.CHALLENGE_FILE).exists()


# --------------------------------------------------------------------------- tampering


def test_wrong_key_is_refused(tmp_path: Path) -> None:
    pool, _, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    wrong = tmp_path / "wrong.hex"
    wrong.write_text(OTHER_KEY + "\n", encoding="utf-8")
    assert reveal(sealed, pool, wrong) == 2


def test_reveal_without_registration_is_refused(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    assert reveal(sealed, pool, key) == 2
    assert not (sealed / sealed_split.CHALLENGE_FILE).exists()


def test_pool_altered_after_sealing_is_refused(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    with pool.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"id": "CASE-999", "text": "smuggled"}, sort_keys=True) + "\n")
    assert reveal(sealed, pool, key) == 2


def test_pool_content_edited_without_changing_ids_is_refused(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    lines = pool.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["text"] = "rewritten body"
    lines[0] = json.dumps(first, sort_keys=True)
    pool.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert reveal(sealed, pool, key) == 2


def test_candidate_changed_after_registration_is_refused(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    candidate = write_candidate(tmp_path)
    register(sealed, candidate)
    candidate.write_text("def solve(): return 2  # tuned after seeing nothing yet\n", encoding="utf-8")
    assert reveal(sealed, pool, key) == 2


def test_registration_made_against_another_manifest_is_refused(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    candidate = write_candidate(tmp_path)
    register(sealed, candidate)

    manifest_path = sealed / sealed_split.SEALED_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["experiment_id"] = "TEST-SWAPPED"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert reveal(sealed, pool, key) == 2


def test_missing_registered_candidate_file_is_refused(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    candidate = write_candidate(tmp_path)
    register(sealed, candidate)
    candidate.unlink()
    assert reveal(sealed, pool, key) == 2


def test_verify_reports_failure_when_published_development_is_edited(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    assert reveal(sealed, pool, key) == 0

    published = sealed / sealed_split.DEVELOPMENT_FILE
    published.write_text(published.read_text(encoding="utf-8") + '{"id": "CASE-EXTRA"}\n', encoding="utf-8")

    result = sealed_split.main(
        ["verify", "--sealed", str(sealed), "--pool", str(pool), "--key-file", str(key)]
    )
    assert result == 1


# --------------------------------------------------------------------------- input validation


def test_pool_with_duplicate_identifiers_is_refused(tmp_path: Path) -> None:
    pool = tmp_path / "pool.jsonl"
    pool.write_text(
        json.dumps({"id": "CASE-001"}) + "\n" + json.dumps({"id": "CASE-001"}) + "\n", encoding="utf-8"
    )
    with pytest.raises(sealed_split.SealError, match="repeats case id"):
        sealed_split._load_pool(pool)


def test_pool_case_without_identifier_is_refused(tmp_path: Path) -> None:
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps({"text": "no id here"}) + "\n", encoding="utf-8")
    with pytest.raises(sealed_split.SealError, match="no usable string 'id'"):
        sealed_split._load_pool(pool)


def test_empty_pool_is_refused(tmp_path: Path) -> None:
    pool = tmp_path / "pool.jsonl"
    pool.write_text("\n\n", encoding="utf-8")
    with pytest.raises(sealed_split.SealError, match="no cases"):
        sealed_split._load_pool(pool)


def test_experiment_id_colliding_with_a_case_id_is_refused(tmp_path: Path) -> None:
    """A collision would make the manifest leak check undecidable.

    If the experiment is named after one of its own cases, a challenge
    identifier appearing in the manifest could be ordinary metadata or a real
    leak, and no scan can separate the two. The seal step must refuse it.
    """
    pool = write_pool(tmp_path)
    key = write_key(tmp_path)
    result = sealed_split.main(
        [
            "seal",
            "--pool", str(pool),
            "--out", str(tmp_path / "sealed"),
            "--experiment", "CASE-000",
            "--key-file", str(key),
        ]
    )
    assert result == 2


# --------------------------------------------------------------------------- adversarial review, 2026-08-23
#
# An adversarial review ran a working proof of concept against this protocol:
# seal, register a stub, reveal, read the challenge half off disk, re-register a
# candidate hard-coding the answers, and verify() reported eleven green checks.
# These tests pin the holes closed.


def test_registering_after_reveal_is_refused(tmp_path: Path) -> None:
    """Once the challenge is on disk, the split is spent."""
    pool, key, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    assert reveal(sealed, pool, key) == 0

    tuned = tmp_path / "tuned.py"
    tuned.write_text("LOOKUP = {}\ndef solve(case): return LOOKUP[case]\n", encoding="utf-8")
    assert sealed_split.main(["register", "--sealed", str(sealed), "--candidate", str(tuned)]) == 2


def test_revealing_twice_is_refused(tmp_path: Path) -> None:
    """A second reveal would let a re-registered candidate look pre-dated."""
    pool, key, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    assert reveal(sealed, pool, key) == 0
    assert reveal(sealed, pool, key) == 2


def test_verify_detects_a_registration_swapped_after_reveal(tmp_path: Path) -> None:
    """The last line of defence if the guards above are ever bypassed.

    Every other check compares the registration against itself, so a swapped
    registration stays green without this one.
    """
    pool, key, sealed = seal(tmp_path)
    candidate = write_candidate(tmp_path)
    register(sealed, candidate)
    assert reveal(sealed, pool, key) == 0

    # Simulate a bypass: rewrite the registration directly on disk.
    candidate.write_text("def solve(case): return 'memorised'\n", encoding="utf-8")
    registration = json.loads((sealed / sealed_split.REGISTRATION_FILE).read_text(encoding="utf-8"))
    registration["candidate"][0]["sha256"] = sealed_split._sha256_file(candidate)
    (sealed / sealed_split.REGISTRATION_FILE).write_bytes(
        (json.dumps(registration, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    result = sealed_split.main(
        ["verify", "--sealed", str(sealed), "--pool", str(pool), "--key-file", str(key)]
    )
    assert result == 1


def test_reveal_receipt_binds_the_registration_bytes(tmp_path: Path) -> None:
    pool, key, sealed = seal(tmp_path)
    register(sealed, write_candidate(tmp_path))
    assert reveal(sealed, pool, key) == 0
    receipt = json.loads((sealed / sealed_split.REVEAL_RECEIPT).read_text(encoding="utf-8"))
    assert receipt["registration_sha256_at_reveal"] == sealed_split._sha256_file(
        sealed / sealed_split.REGISTRATION_FILE
    )


def test_manifest_records_whether_the_key_could_have_been_ground(tmp_path: Path) -> None:
    """A self-generated key can be redrawn until the split flatters a candidate.

    Nothing offline can prevent that, so the manifest must at least say which
    guarantee applies.
    """
    _, _, sealed = seal(tmp_path)
    manifest = json.loads((sealed / sealed_split.SEALED_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["key_source"] == "external-witness"
    assert "redrawn" in manifest["key_source_caveat"]

    generated = tmp_path / "generated"
    assert (
        sealed_split.main(
            [
                "seal",
                "--pool", str(write_pool(tmp_path / "second")),
                "--out", str(generated),
                "--experiment", "TEST-GEN",
                "--write-key", str(tmp_path / "gen.key"),
            ]
        )
        == 0
    )
    document = json.loads((generated / sealed_split.SEALED_MANIFEST).read_text(encoding="utf-8"))
    assert document["key_source"] == "self-generated"
