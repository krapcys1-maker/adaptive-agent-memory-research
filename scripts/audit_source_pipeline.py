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

# Classify by structure, never by a list of hosts. Enumerating publication
# hosts produced a misleading number three times in one session: checking only
# arxiv and doi filed NeurIPS, MLR, ACL and OpenReview under "unresolvable";
# adding those then filed PubMed Central, RFC Editor, EUR-Lex and VLDB the same
# way. A hand-written list is never complete, and its gaps look like findings.
#
# A source is resolvable if it is a URL or a repository path. Whether it is
# *catalogued* is a separate question, and the right one to report.
REPOSITORY_HOSTS = ("github.com", "gitlab.com", "huggingface.co")
INTERNAL_PATH = re.compile(r"^(docs|data|scripts|tools|tests|memory)/")


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
    uncatalogued_publications: list[str] = []
    repository_sources: list[str] = []
    internal_artifacts: list[str] = []
    unresolvable: list[str] = []
    declared_sourceless: list[str] = []

    for row in ledger:
        source = normalise(row.get("primary_source", ""))
        claim = row.get("claim_id", "?")
        if not source:
            unresolvable.append(claim)
            continue
        if source.startswith("internal:"):
            # A claim the project derived itself, saying so. Distinct from a
            # claim that merely failed to name a source: one is a declaration,
            # the other is an omission.
            declared_sourceless.append(claim)
            continue
        match = next((u for u in catalog_urls if u and (u in source or source in u)), None)
        if match:
            cited.add(match)
        elif source.startswith(REPOSITORY_HOSTS):
            repository_sources.append(claim)
        elif INTERNAL_PATH.match(source):
            internal_artifacts.append(claim)
        elif "/" in source or "." in source:
            # A URL or a path: a real citation, simply not in the paper catalog.
            uncatalogued_publications.append(claim)
        else:
            unresolvable.append(claim)

    note_files = sorted(NOTES.glob("*.md")) if NOTES.is_dir() else []
    note_text = " ".join(p.read_text(encoding="utf-8", errors="replace").lower() for p in note_files)
    read = {u for u in catalog_urls if u and u in note_text}

    status_is_publication_type = sum(
        1 for row in catalog if PUBLICATION_TYPES.search(row.get("status", ""))
    )

    reading_states: dict[str, int] = {}
    for row in catalog:
        key = (row.get("reading_state") or "absent").strip() or "absent"
        reading_states[key] = reading_states.get(key, 0) + 1

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
        "uncatalogued_publications": len(uncatalogued_publications),
        "repository_sources_belonging_in_the_repo_catalog": len(repository_sources),
        "internal_artifacts_correctly_uncatalogued": len(internal_artifacts),
        "claims_with_no_resolvable_source": len(unresolvable),
        "unresolvable_claim_ids": sorted(unresolvable),
        "claims_declaring_no_external_source": len(declared_sourceless),
        "declared_sourceless_claim_ids": sorted(declared_sourceless),
        "catalog_status_column_holds_publication_type_not_reading_state": status_is_publication_type,
        "ledger_status_levels": dict(sorted(ledger_levels.items())),
        "catalog_reading_states": dict(sorted(reading_states.items())),
        "reading_state_still_unknown": reading_states.get("unknown", 0),
        "gap": (
            "The catalog now carries reading_state alongside status, so the distinction between "
            "publication type and engagement is expressible. Every row starts at unknown, which "
            "means the record does not say rather than that the source is unread. The remaining "
            "gap is that some claims cite publications absent from the catalog. An earlier version "
            "reported that as 36 percent by lumping repository links, internal artifacts and "
            "unrecognised publication hosts together; classifying by host separates them."
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
