"""Audit the distinction between discovered, cited, and read sources.

A registered project priority reads: *repair the distinction between discovered,
screened, read, and independently reviewed sources*. This makes the gap
measurable instead of described.

The gap
-------
``data/catalogs/papers-curated.csv`` has a ``status`` column, but it records
**publication type** — peer-reviewed, preprint, review — not reading state.
Nothing anywhere records whether a source was actually read, even though
``CONTRIBUTING.md`` requires that a reading note follow reading the source
rather than its abstract.

So the catalog can say a paper is peer-reviewed and cannot say whether anyone
opened it.

What this measures, all decidable from files
--------------------------------------------
``discovered``  present in the curated catalog
``cited``       named by at least one evidence-ledger claim
``read``        has a note under ``docs/07-literature/full-read-notes/``
``orphan``      a ledger claim whose source is in no catalog

It also separates claims the ledger itself marks as abstract-level from those
marked as extracted, because that distinction already exists in one place and
not the other.

This reports. It does not repair, because assigning a reading state to 174
sources is a judgement about what was actually read, and guessing would put a
fabricated state into what reads afterwards as a record.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalogs" / "papers-curated.csv"
LEDGER = ROOT / "docs" / "07-literature" / "evidence-ledger.csv"
NOTES = ROOT / "docs" / "07-literature" / "full-read-notes"

# Publication types, so the audit can say plainly that this column is not a
# reading state.
PUBLICATION_TYPES = re.compile(
    r"peer-reviewed|preprint|review|official|foundational|thesis|book", re.IGNORECASE
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalise(value: str) -> str:
    """Strip a URL to something comparable across catalog and ledger."""
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(www\.)?", "", value)
    return value.rstrip("/.")


def run() -> dict[str, Any]:
    catalog = read_csv(CATALOG)
    ledger = read_csv(LEDGER)

    catalog_urls = {normalise(row.get("url", "")) for row in catalog if row.get("url")}
    catalog_urls.discard("")

    cited: set[str] = set()
    orphan_claims: list[str] = []
    for row in ledger:
        source = normalise(row.get("primary_source", ""))
        if not source:
            continue
        match = next((u for u in catalog_urls if u and (u in source or source in u)), None)
        if match:
            cited.add(match)
        else:
            orphan_claims.append(row.get("claim_id", "?"))

    note_files = sorted(NOTES.glob("*.md")) if NOTES.is_dir() else []
    note_text = " ".join(p.read_text(encoding="utf-8", errors="replace").lower() for p in note_files)
    read = {u for u in catalog_urls if u and u in note_text}

    status_is_publication_type = sum(
        1 for row in catalog if PUBLICATION_TYPES.search(row.get("status", ""))
    )

    ledger_levels: dict[str, int] = {}
    for row in ledger:
        key = (row.get("status") or "?").strip()
        ledger_levels[key] = ledger_levels.get(key, 0) + 1

    return {
        "catalog_entries": len(catalog),
        "catalog_entries_with_url": len(catalog_urls),
        "ledger_claims": len(ledger),
        "sources_cited_by_a_claim": len(cited),
        "sources_never_cited": len(catalog_urls) - len(cited),
        "sources_with_a_full_read_note": len(read),
        "full_read_note_files": len(note_files),
        "ledger_claims_whose_source_is_in_no_catalog": len(orphan_claims),
        "orphan_claim_ids": sorted(orphan_claims)[:20],
        "catalog_status_column_holds_publication_type_not_reading_state": status_is_publication_type,
        "ledger_status_levels": dict(sorted(ledger_levels.items())),
        "gap": (
            "The catalog cannot express whether a source was read. Its status column records "
            "publication type. The ledger distinguishes abstract-extracted from extracted, but only "
            "for claims, never for sources, so a source read in full and one skimmed for a single "
            "claim are indistinguishable in the catalog."
        ),
        "not_repaired": (
            "Assigning a reading state to every catalogued source is a judgement about what was "
            "actually read. Guessing it would write a fabricated state into what reads afterwards "
            "as a record, so this audit reports and stops."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args(argv)

    report = run()
    if arguments.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Source pipeline audit\n")
        for key, value in report.items():
            if isinstance(value, (int, str)) and not isinstance(value, bool):
                if isinstance(value, str) and len(value) > 60:
                    continue
                print(f"  {key:<58} {value}")
        print(f"\n  ledger status levels: {report['ledger_status_levels']}")
        print(f"\nGap\n  {report['gap']}")
        print(f"\nNot repaired\n  {report['not_repaired']}")

    if arguments.output:
        destination = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
