"""Sealed held-out splits: independence tier I1.

Implements the commit-and-reveal protocol from
``docs/00-project/independence-ladder.md``. It lets a single author produce a
genuinely held-out evaluation without a second person, by making the split
cryptographically committed before the candidate exists and verifiable by any
third party afterwards.

The problem it solves is recorded in this project's own history: the PMLAB-MAP
challenge was "post-freeze but same-process, not independently held out", and
once the author had seen it, it was spent for tuning.

Protocol
--------
1. ``seal``     — split a case pool with ``HMAC(key, case_id)``, publish the
                  development half and a manifest committing to
                  ``sha256(key)``. The key and the challenge cases stay sealed.
2. ``register`` — commit to the candidate implementation by digest, before the
                  challenge half is visible.
3. ``reveal``   — supply the key. The commitment is checked, the registration
                  must already exist, and only then is the challenge half
                  emitted.
4. ``verify``   — any third party recomputes the whole split from the revealed
                  key and confirms nothing was altered.

Honest limitation
-----------------
Ordering is enforced by artifact digests, not by a trusted clock. A local
timestamp proves nothing on its own: an author with the key could in principle
seal, peek, and re-register. What makes the ordering real is publication — the
sealed manifest and the candidate registration must be committed and pushed
before the key is released. This tool refuses the obviously broken orderings it
can detect and records the rest, rather than pretending to guarantee more than
cryptography alone can.

Subcommands rather than separate seal and reveal scripts: both must compute the
identical split, and duplicating that logic would put a divergence bug in the
one place where it would silently invalidate a result.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SPLIT_RULE = "HMAC-SHA256(key, case_id); development when the first digest byte is even"
PROTOCOL_VERSION = 1

SEALED_MANIFEST = "sealed-manifest.json"
DEVELOPMENT_FILE = "development.jsonl"
CHALLENGE_FILE = "challenge.jsonl"
REGISTRATION_FILE = "candidate-registration.json"
REVEAL_RECEIPT = "reveal-receipt.json"


class SealError(RuntimeError):
    """Raised when a sealed-split invariant is violated."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_pool(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise SealError(f"{path.name} line {number} is not valid JSON: {error}") from error
        if not isinstance(case, dict):
            raise SealError(f"{path.name} line {number} is not a JSON object")
        identifier = case.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise SealError(f"{path.name} line {number} has no usable string 'id'")
        if identifier in seen:
            raise SealError(f"{path.name} line {number} repeats case id {identifier!r}")
        seen.add(identifier)
        cases.append(case)
    if not cases:
        raise SealError(f"{path.name} contains no cases")
    return cases


def assign(key: bytes, case_id: str) -> str:
    """Deterministically assign one case to development or challenge."""
    digest = hmac.new(key, case_id.encode("utf-8"), hashlib.sha256).digest()
    return "development" if digest[0] % 2 == 0 else "challenge"


def _identifier_digest(identifiers: list[str]) -> str:
    return _sha256_bytes("\n".join(sorted(identifiers)).encode("utf-8"))


def _write_bytes(path: Path, text: str) -> str:
    """Write UTF-8 with LF endings on every platform, and return the digest.

    ``Path.write_text`` opens in text mode, which translates ``\\n`` to
    ``\\r\\n`` on Windows. A digest computed in memory would then disagree with
    the bytes on disk, and the same artifact would hash differently depending on
    who produced it. That failure is already recorded in this repository as a
    broken cross-platform freeze, so this tool writes bytes explicitly.
    """
    payload = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256_bytes(payload)


def _write_jsonl(path: Path, cases: list[dict[str, Any]]) -> str:
    payload = "".join(json.dumps(case, sort_keys=True, ensure_ascii=False) + "\n" for case in cases)
    return _write_bytes(path, payload)


def _write_json(path: Path, document: dict[str, Any]) -> str:
    return _write_bytes(path, json.dumps(document, indent=2, sort_keys=True) + "\n")


def _read_key(path: Path) -> bytes:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise SealError(f"{path.name} is empty")
    try:
        return bytes.fromhex(raw)
    except ValueError as error:
        raise SealError(f"{path.name} must contain a hex-encoded key: {error}") from error


def _store_path(path: Path) -> str:
    """Record a path relative to the repository when possible, absolute otherwise.

    Candidate artifacts usually live inside the repository, but not always: a
    test fixture or a build output can sit outside it, and a naive
    ``relative_to`` raises there.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_path(stored: str) -> Path:
    candidate = Path(stored)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _leaf_strings(value: Any) -> list[str]:
    """Every string leaf in a JSON structure, for exact leak checking."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _leaf_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _leaf_strings(child)]
    return []


def _load_manifest(directory: Path) -> dict[str, Any]:
    path = directory / SEALED_MANIFEST
    if not path.is_file():
        raise SealError(f"no sealed manifest at {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def command_seal(arguments: argparse.Namespace) -> int:
    pool_path = Path(arguments.pool)
    output = Path(arguments.out)
    cases = _load_pool(pool_path)

    if arguments.key_file:
        key_path = Path(arguments.key_file)
        key = _read_key(key_path)
        generated = False
    else:
        key = secrets.token_bytes(32)
        key_path = Path(arguments.write_key or (output.parent / f"{output.name}.key"))
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(key.hex() + "\n", encoding="utf-8")
        generated = True

    # An experiment named identically to one of its cases makes the leak check
    # undecidable: a challenge identifier appearing in the manifest could be
    # metadata or a leak, and no scan can tell them apart. Refuse the ambiguity
    # at the source rather than special-casing it later.
    identifiers = {case["id"] for case in cases}
    if arguments.experiment in identifiers:
        raise SealError(
            f"experiment id {arguments.experiment!r} collides with a case id; "
            f"rename the experiment so leak checking stays decidable"
        )

    development = [case for case in cases if assign(key, case["id"]) == "development"]
    challenge = [case for case in cases if assign(key, case["id"]) == "challenge"]
    if not development or not challenge:
        raise SealError(
            f"degenerate split: {len(development)} development and {len(challenge)} challenge cases"
        )

    output.mkdir(parents=True, exist_ok=True)
    development_digest = _write_jsonl(output / DEVELOPMENT_FILE, development)

    generator = Path(arguments.generator) if arguments.generator else None
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "experiment_id": arguments.experiment,
        "sealed_at": _now(),
        "split_rule": SPLIT_RULE,
        "key_commitment": _sha256_bytes(key),
        "pool_identifier_digest": _identifier_digest([case["id"] for case in cases]),
        "pool_content_digest": _sha256_file(pool_path),
        "development_digest": development_digest,
        "development_identifier_digest": _identifier_digest([case["id"] for case in development]),
        "counts": {
            "pool": len(cases),
            "development": len(development),
            "challenge": len(challenge),
        },
        "generator": {
            "path": _store_path(generator) if generator else None,
            "sha256": _sha256_file(generator) if generator else None,
        },
        "tool_sha256": _sha256_file(Path(__file__)),
        "notes": (
            "This manifest deliberately contains no key and no challenge case. "
            "Ordering is enforced by publication, not by the sealed_at value."
        ),
    }
    _write_json(output / SEALED_MANIFEST, manifest)

    print(json.dumps({k: v for k, v in manifest.items() if k != "notes"}, indent=2, sort_keys=True))
    if generated:
        print(f"\nKEY WRITTEN TO {key_path}", file=sys.stderr)
        print(
            "Move it outside the repository now. Publishing it before registering a "
            "candidate destroys the held-out property.",
            file=sys.stderr,
        )
    return 0


def command_register(arguments: argparse.Namespace) -> int:
    directory = Path(arguments.sealed)
    manifest = _load_manifest(directory)

    entries = []
    for raw in arguments.candidate:
        path = Path(raw)
        if not path.is_file():
            raise SealError(f"candidate artifact not found: {path}")
        entries.append({"path": _store_path(path), "sha256": _sha256_file(path)})
    entries.sort(key=lambda entry: entry["path"])

    registration = {
        "protocol_version": PROTOCOL_VERSION,
        "experiment_id": manifest["experiment_id"],
        "registered_at": _now(),
        "sealed_manifest_sha256": _sha256_file(directory / SEALED_MANIFEST),
        "candidate": entries,
        "candidate_digest": _sha256_bytes(
            json.dumps(entries, sort_keys=True).encode("utf-8")
        ),
        "thresholds": json.loads(arguments.thresholds) if arguments.thresholds else None,
    }
    _write_json(directory / REGISTRATION_FILE, registration)
    print(json.dumps(registration, indent=2, sort_keys=True))
    return 0


def _check_commitment(manifest: dict[str, Any], key: bytes) -> None:
    if _sha256_bytes(key) != manifest["key_commitment"]:
        raise SealError("key does not match the sealed commitment")


def _recompute(pool: list[dict[str, Any]], key: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    development = [case for case in pool if assign(key, case["id"]) == "development"]
    challenge = [case for case in pool if assign(key, case["id"]) == "challenge"]
    return development, challenge


def command_reveal(arguments: argparse.Namespace) -> int:
    directory = Path(arguments.sealed)
    manifest = _load_manifest(directory)
    key = _read_key(Path(arguments.key_file))
    _check_commitment(manifest, key)

    registration_path = directory / REGISTRATION_FILE
    if not registration_path.is_file():
        raise SealError(
            "no candidate registration; a candidate must be registered before the challenge "
            "half is revealed, otherwise the split is not held out"
        )
    registration = json.loads(registration_path.read_text(encoding="utf-8-sig"))
    if registration.get("sealed_manifest_sha256") != _sha256_file(directory / SEALED_MANIFEST):
        raise SealError("the registration was made against a different sealed manifest")

    for entry in registration["candidate"]:
        path = _resolve_path(entry["path"])
        if not path.is_file():
            raise SealError(f"registered candidate artifact is missing: {entry['path']}")
        if _sha256_file(path) != entry["sha256"]:
            raise SealError(
                f"registered candidate artifact changed after registration: {entry['path']}"
            )

    pool = _load_pool(Path(arguments.pool))
    if _identifier_digest([case["id"] for case in pool]) != manifest["pool_identifier_digest"]:
        raise SealError("pool case identifiers do not match the sealed manifest")
    if _sha256_file(Path(arguments.pool)) != manifest["pool_content_digest"]:
        raise SealError("pool content changed after sealing")

    development, challenge = _recompute(pool, key)
    if _identifier_digest([case["id"] for case in development]) != manifest["development_identifier_digest"]:
        raise SealError("recomputed development half does not match the sealed manifest")

    challenge_digest = _write_jsonl(directory / CHALLENGE_FILE, challenge)
    receipt = {
        "protocol_version": PROTOCOL_VERSION,
        "experiment_id": manifest["experiment_id"],
        "revealed_at": _now(),
        "key_sha256": manifest["key_commitment"],
        "candidate_digest": registration["candidate_digest"],
        "challenge_digest": challenge_digest,
        "counts": manifest["counts"],
    }
    _write_json(directory / REVEAL_RECEIPT, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def command_verify(arguments: argparse.Namespace) -> int:
    directory = Path(arguments.sealed)
    manifest = _load_manifest(directory)
    key = _read_key(Path(arguments.key_file))
    pool = _load_pool(Path(arguments.pool))

    checks: dict[str, bool] = {}
    checks["key_matches_commitment"] = _sha256_bytes(key) == manifest["key_commitment"]
    checks["pool_identifiers_match"] = (
        _identifier_digest([case["id"] for case in pool]) == manifest["pool_identifier_digest"]
    )
    checks["pool_content_matches"] = _sha256_file(Path(arguments.pool)) == manifest["pool_content_digest"]

    development, challenge = _recompute(pool, key)
    checks["development_recomputes"] = (
        _identifier_digest([case["id"] for case in development])
        == manifest["development_identifier_digest"]
    )
    checks["counts_match"] = manifest["counts"] == {
        "pool": len(pool),
        "development": len(development),
        "challenge": len(challenge),
    }

    published = directory / DEVELOPMENT_FILE
    checks["published_development_matches"] = (
        published.is_file() and _sha256_file(published) == manifest["development_digest"]
    )

    manifest_text = json.dumps(manifest, sort_keys=True)
    checks["manifest_leaks_no_key"] = key.hex() not in manifest_text

    # Exact leaf-value comparison, not substring search over the serialized
    # manifest. A leaked case would appear as a value; a substring test instead
    # fires whenever an experiment identifier shares a prefix with case
    # identifiers, which is a false alarm rather than a leak.
    challenge_ids = {case["id"] for case in challenge}
    checks["manifest_leaks_no_challenge_case"] = not (
        challenge_ids & set(_leaf_strings(manifest))
    )

    registration_path = directory / REGISTRATION_FILE
    checks["candidate_registered"] = registration_path.is_file()
    if checks["candidate_registered"]:
        registration = json.loads(registration_path.read_text(encoding="utf-8-sig"))
        checks["registration_binds_this_manifest"] = registration.get(
            "sealed_manifest_sha256"
        ) == _sha256_file(directory / SEALED_MANIFEST)
        checks["candidate_unchanged_since_registration"] = all(
            _resolve_path(entry["path"]).is_file()
            and _sha256_file(_resolve_path(entry["path"])) == entry["sha256"]
            for entry in registration["candidate"]
        )

    passed = all(checks.values())
    print(json.dumps({"passed": passed, "checks": checks}, indent=2, sort_keys=True))
    return 0 if passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal = subparsers.add_parser("seal", help="split a pool and publish only the development half")
    seal.add_argument("--pool", required=True)
    seal.add_argument("--out", required=True)
    seal.add_argument("--experiment", required=True)
    seal.add_argument("--key-file", default=None, help="existing hex key; generated when omitted")
    seal.add_argument("--write-key", default=None, help="where to write a generated key")
    seal.add_argument("--generator", default=None, help="script that produced the pool")
    seal.set_defaults(handler=command_seal)

    register = subparsers.add_parser("register", help="commit to a candidate before reveal")
    register.add_argument("--sealed", required=True)
    register.add_argument("--candidate", required=True, nargs="+")
    register.add_argument("--thresholds", default=None, help="JSON of preregistered thresholds")
    register.set_defaults(handler=command_register)

    reveal = subparsers.add_parser("reveal", help="unseal the challenge half")
    reveal.add_argument("--sealed", required=True)
    reveal.add_argument("--pool", required=True)
    reveal.add_argument("--key-file", required=True)
    reveal.set_defaults(handler=command_reveal)

    verify = subparsers.add_parser("verify", help="third-party verification of a revealed split")
    verify.add_argument("--sealed", required=True)
    verify.add_argument("--pool", required=True)
    verify.add_argument("--key-file", required=True)
    verify.set_defaults(handler=command_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        return arguments.handler(arguments)
    except SealError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
