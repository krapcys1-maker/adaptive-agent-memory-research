"""A frozen artifact must regenerate from the code that claims to produce it.

The gap this closes
-------------------
Integrity checks compared the corpus on disk against its declared digest, and
that check passed while the corpus had become unreproducible. Extending the
subject list from sixteen names to thirty-six changed ``next(stream) %
len(_SERVICES)`` in the noise generator and shifted every noise event. The bytes
on disk were untouched, so every digest still matched — and nothing could make
those bytes again.

> A frozen artifact that cannot be regenerated is not frozen. It is old.

So the assertion is not ``hash(on_disk) == declared``. It is

    hash(regenerate(generator, seed, config)) == declared

which is the only form that notices when the generator drifts away from what it
already produced.

Cost: about a second. It runs the generators into a temporary directory and
touches nothing under ``data/``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "lab" / "corpus-h1"

SPLITS = {
    "dev-a": (20260823, CORPUS / "prefix-v0", CORPUS / "reveal-v0"),
    "valid-b": (20260901, CORPUS / "valid-b" / "prefix", CORPUS / "valid-b" / "reveal"),
}


def _generate(script: str, seed: int, out: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--seed", str(seed), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("split", sorted(SPLITS))
def test_the_corpus_regenerates_byte_for_byte(split: str, tmp_path: Path) -> None:
    seed, prefix, reveal = SPLITS[split]
    if not (prefix / "history.jsonl").is_file():
        pytest.skip(f"{split} not generated")

    _generate("build_history_family.py", seed, tmp_path / "prefix")
    _generate("build_delayed_reveal.py", seed, tmp_path / "reveal")

    for source, produced in (
        (prefix / "history.jsonl", tmp_path / "prefix" / "history.jsonl"),
        (prefix / "construction-labels.jsonl", tmp_path / "prefix" / "construction-labels.jsonl"),
        (reveal / "queries.jsonl", tmp_path / "reveal" / "queries.jsonl"),
        (reveal / "gold.jsonl", tmp_path / "reveal" / "gold.jsonl"),
    ):
        assert source.read_bytes() == produced.read_bytes(), (
            f"{split}/{source.name} no longer regenerates from its generator at seed {seed}. "
            "The bytes on disk are unchanged and their digests still match; the generator has "
            "drifted away from them."
        )


def test_the_registered_digest_matches_a_fresh_generation(tmp_path: Path) -> None:
    """Close the loop: preregistration → generator → bytes, not just → disk."""
    prereg = CORPUS / "preregistration-addr-e2" / "preregistration.json"
    if not prereg.is_file():
        pytest.skip("preregistration not present")
    registered = json.loads(prereg.read_text(encoding="utf-8"))["corpus"]

    _generate("build_history_family.py", registered["seed"], tmp_path / "prefix")
    _generate("build_delayed_reveal.py", registered["seed"], tmp_path / "reveal")

    for field, produced in (
        ("history_sha256", tmp_path / "prefix" / "history.jsonl"),
        ("gold_sha256", tmp_path / "reveal" / "gold.jsonl"),
        ("queries_sha256", tmp_path / "reveal" / "queries.jsonl"),
    ):
        digest = hashlib.sha256(produced.read_bytes()).hexdigest()
        assert registered[field] == digest, (
            f"{field} in the preregistration cannot be reproduced by the current generator. "
            "The thresholds were registered against a corpus this code no longer makes."
        )


def test_the_sealed_split_has_not_been_materialised() -> None:
    """Not looking at a file is discipline. Not having it is a property."""
    commitment = CORPUS / "preregistration-addr-e2" / "sealed-c-commitment.json"
    if not commitment.is_file():
        pytest.skip("no sealed commitment registered")
    assert not (CORPUS / "sealed-c").exists(), (
        "sealed-c exists on disk. It is committed to by seed hash and must not be generated "
        "until the extractor implementation is frozen."
    )


def test_the_secret_seed_is_not_in_the_repository() -> None:
    """A commitment whose secret sits beside it commits to nothing."""
    commitment = CORPUS / "preregistration-addr-e2" / "sealed-c-commitment.json"
    if not commitment.is_file():
        pytest.skip("no sealed commitment registered")
    declared = json.loads(commitment.read_text(encoding="utf-8"))["commitment_sha256_of_secret_seed"]

    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout
    for name in tracked.splitlines():
        path = ROOT / name
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for token in body.split():
            candidate = token.strip('",')
            if len(candidate) == 64 and all(c in "0123456789abcdef" for c in candidate):
                assert hashlib.sha256(candidate.encode("ascii")).hexdigest() != declared, (
                    f"the secret seed appears in {name}; the commitment is void"
                )
