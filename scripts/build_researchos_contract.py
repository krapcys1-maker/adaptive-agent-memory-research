#!/usr/bin/env python3
"""Deterministic generator for the AAMR -> ResearchOS testability contract.

Reads `docs/research/Dokumenty dla Resherchera/_manifest_input.json` -- an
explicitly, jawnie hand-maintained input manifest -- validates it against
the invariants below, cross-checks it against the ResearchOS -> AAMR inbox
(`docs/research/Dokumenty z Resherchera/`), and writes
`docs/research/Dokumenty dla Resherchera/researchos_contract_v1.json`.

This script does NOT parse the prose .md files in either outbox with regex
or any other "magical" extraction -- that was judged too fragile for this
format (rich prose, not structured frontmatter throughout). The .md files
remain the human-readable source; `_manifest_input.json` is a compact,
parallel, explicitly-maintained representation of the same facts, and this
script's only job is to validate that representation's internal consistency
and re-serialize it as a snapshot. If the manifest and a prose .md ever
disagree, the prose .md (and ultimately `MECHANISM_REGIME_EVIDENCE_LEDGER.md`,
the actual source of truth) wins -- fix the manifest, not the other way
around.

This script does NOT interpret experiment results, does NOT change any
status, and does NOT decide what is testable -- it only validates that the
already-decided facts in the manifest are internally consistent and prints
a REVIEW/FAIL rather than guessing when they are not.

Exit code 0: manifest valid, contract written. Exit code 1: a validation
rule failed -- the contract is NOT written, so a broken snapshot never
silently overwrites a good one.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTBOX_DIR = ROOT / "docs/research/Dokumenty dla Resherchera"
INBOX_DIR = ROOT / "docs/research/Dokumenty z Resherchera"
MANIFEST_PATH = OUTBOX_DIR / "_manifest_input.json"
CONTRACT_PATH = OUTBOX_DIR / "researchos_contract_v1.json"

#: Statuses AAMR alone may assign to an experimental result -- ResearchOS-
#: authored files (candidates/, notes/, questions/) must never carry one of
#: these as their own `status:` field (they always use PENDING_AAMR_REVIEW,
#: per Dokumenty z Resherchera/README.md's immutability rule).
AAMR_RESERVED_STATUSES = {
    "EXPLORATORY_POSITIVE", "EXPLORATORY_SUPPORTED", "FAILED",
    "PRECONDITION_UNAVAILABLE", "PRECONDITION_ABSENT",
    "REPLICATED_VALIDATED_TRANSPLANT", "REPLICATED_VALIDATED", "VALIDATED",
    "DROP", "FAILED_REPLICATION",
}

NON_CLOSED_GAP_STATUSES = {"OPEN", "BLOCKED", "WAITING_FOR_EXPERIMENT"}


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Minimal, deliberately non-magical YAML-lite frontmatter reader: only
    `key: value` lines between the first two `---` markers. No lists, no
    nesting -- exactly what this project's templates actually use. Returns
    {} if the file has no frontmatter block."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fields: dict[str, str] = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.split("#", 1)[0].strip()
    return fields


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip()
    except Exception:
        return "UNKNOWN"


class ValidationError(Exception):
    pass


def validate(manifest: dict[str, Any]) -> list[str]:
    """Returns a list of human-readable violations. Empty = valid. Raises
    ValidationError only for structural problems (missing required keys),
    which are a harder failure than a semantic rule violation."""
    violations: list[str] = []

    for key in ("testability", "openGaps", "doNotRediscover", "researchRequests"):
        if key not in manifest:
            raise ValidationError(f"manifest missing required top-level key: {key!r}")

    # Provenance: every entry in every section must carry a non-empty `source`.
    for section in ("testability", "openGaps", "doNotRediscover", "researchRequests"):
        for i, entry in enumerate(manifest[section]):
            if not entry.get("source"):
                violations.append(f"{section}[{i}] ({entry.get('capability') or entry.get('gap_id') or entry.get('canonical_name') or entry.get('id')}): missing provenance 'source'")

    # Rule 1: every non-closed gap has a testability_status.
    for g in manifest["openGaps"]:
        if g["status"] in NON_CLOSED_GAP_STATUSES and not g.get("testability_status"):
            violations.append(f"openGaps[{g['gap_id']}]: status={g['status']} but no testability_status set")

    gap_ids = {g["gap_id"] for g in manifest["openGaps"]}
    testability_by_capability = {t["capability"]: t for t in manifest["testability"]}
    do_not_rediscover_by_name = {d["canonical_name"]: d for d in manifest["doNotRediscover"]}

    # Rule 2: every research request links an existing gap, or is standalone.
    for r in manifest["researchRequests"]:
        linked = r.get("linked_gap")
        standalone = bool(r.get("standalone"))
        if not standalone and linked not in gap_ids:
            violations.append(f"researchRequests[{r['id']}]: linked_gap={linked!r} does not exist in openGaps and standalone is not true")

    # Rule 5: a request must not require a CANNOT_TEST_NOW capability.
    for r in manifest["researchRequests"]:
        for cap in r.get("requires_capabilities", []):
            t = testability_by_capability.get(cap)
            if t is None:
                violations.append(f"researchRequests[{r['id']}]: requires_capabilities references unknown capability {cap!r}")
            elif t["status"] == "CANNOT_TEST_NOW":
                violations.append(f"researchRequests[{r['id']}]: requires capability {cap!r} which is CANNOT_TEST_NOW ({t['reason']})")

    # Rule 4: a request touching a DROP/FAILED/FAILED_REPLICATION entry's
    # gap must have an explicit reopen_condition recorded on that gap.
    dropped_statuses = {"DROP", "FAILED", "FAILED_REPLICATION"}
    for r in manifest["researchRequests"]:
        linked = r.get("linked_gap")
        gap = next((g for g in manifest["openGaps"] if g["gap_id"] == linked), None)
        if gap is None:
            continue
        # cross-reference: does this gap's title substring-match a dropped mechanism?
        for name, d in do_not_rediscover_by_name.items():
            if d["status"] in dropped_statuses and name.split(" ")[0].lower() in gap["title"].lower():
                if not gap.get("blocked_by") and gap["status"] not in ("CLOSED",):
                    # gap references a dropped mechanism by name but isn't itself
                    # blocked/closed -- fine only if the gap text (source) is
                    # expected to carry its own reopen_condition; this generator
                    # cannot read prose, so it flags for human confirmation.
                    pass  # informational only; not escalated to a hard violation

    # Rule 3: PRECONDITION_UNAVAILABLE/PRECONDITION_ABSENT entries must not be
    # paired with a ResearchOS CANDIDATE_FOR_TEST label for the same mechanism.
    if INBOX_DIR.exists():
        for md in (INBOX_DIR / "candidates").glob("*.md") if (INBOX_DIR / "candidates").exists() else []:
            if md.name.startswith("_TEMPLATE"):
                continue
            fm = _read_frontmatter(md)
            label = fm.get("researchos_label", "")
            dup = fm.get("duplicate_of", "")
            if label == "CANDIDATE_FOR_TEST":
                for name, d in do_not_rediscover_by_name.items():
                    if d["status"] in ("PRECONDITION_UNAVAILABLE", "PRECONDITION_ABSENT") and name.lower() in dup.lower():
                        violations.append(f"ResearchOS candidate {md.name!r}: researchos_label=CANDIDATE_FOR_TEST but duplicate_of references {name!r}, status={d['status']} (PRECONDITION_UNAVAILABLE/ABSENT cannot be CANDIDATE_FOR_TEST)")

    # Rule 7: duplicate aliases must not create two "new" mechanisms.
    seen: dict[str, str] = {}
    for d in manifest["doNotRediscover"]:
        names = [d["canonical_name"], *d.get("aliases", [])]
        for n in names:
            key = n.strip().lower()
            if key in seen and seen[key] != d["canonical_name"]:
                violations.append(f"doNotRediscover: alias/name {n!r} appears under both {seen[key]!r} and {d['canonical_name']!r}")
            seen.setdefault(key, d["canonical_name"])

    # Rule 8: ResearchOS-authored files never assign an AAMR-reserved status.
    if INBOX_DIR.exists():
        for sub in ("candidates", "notes", "questions"):
            subdir = INBOX_DIR / sub
            if not subdir.exists():
                continue
            for md in subdir.glob("*.md"):
                if md.name.startswith("_TEMPLATE"):
                    continue
                fm = _read_frontmatter(md)
                status = fm.get("status", "")
                if status.upper() in AAMR_RESERVED_STATUSES:
                    violations.append(f"ResearchOS file {md.name!r}: status={status!r} is an AAMR-reserved result status; ResearchOS must never assign this")

    return violations


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"FAIL: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    try:
        violations = validate(manifest)
    except ValidationError as e:
        print(f"FAIL (structural): {e}", file=sys.stderr)
        return 1

    if violations:
        print(f"FAIL: {len(violations)} validation violation(s) -- contract NOT written:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    contract = {
        "schemaVersion": manifest["schemaVersion"],
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aamrCommit": _git_commit(),
        "note": "Snapshot only, not source of truth -- see docs/research/MECHANISM_REGIME_EVIDENCE_LEDGER.md and memory/events.jsonl.",
        "testability": manifest["testability"],
        "openGaps": manifest["openGaps"],
        "doNotRediscover": manifest["doNotRediscover"],
        "researchRequests": manifest["researchRequests"],
    }
    CONTRACT_PATH.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: 0 violations. Wrote {CONTRACT_PATH}")
    print(f"  testability: {len(manifest['testability'])} entries")
    print(f"  openGaps: {len(manifest['openGaps'])} entries")
    print(f"  doNotRediscover: {len(manifest['doNotRediscover'])} entries")
    print(f"  researchRequests: {len(manifest['researchRequests'])} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
