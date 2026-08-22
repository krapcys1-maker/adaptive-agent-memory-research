#!/usr/bin/env python3
"""Download openly accessible PDFs listed in the curated paper catalog."""

from __future__ import annotations

import csv
import pathlib
import re
import time
import urllib.error
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalogs" / "papers-curated.csv"
OUTPUT = ROOT / "sources" / "papers"


def safe_name(value: str, limit: int = 120) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return value[:limit] or "paper"


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    downloaded = skipped = failed = 0

    with CATALOG.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        url = (row.get("pdf_url") or "").strip()
        if not url:
            skipped += 1
            continue
        filename = f"{row.get('year', 'unknown')}-{safe_name(row.get('title', 'paper'))}.pdf"
        destination = OUTPUT / filename
        if destination.exists() and destination.stat().st_size > 1024:
            skipped += 1
            continue
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "adaptive-agent-memory-research/0.1",
                "Accept": "application/pdf,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            if not payload.startswith(b"%PDF"):
                print(f"SKIP non-PDF: {url}")
                skipped += 1
                continue
            destination.write_bytes(payload)
            print(f"DOWNLOADED {filename} ({len(payload)} bytes)")
            downloaded += 1
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            print(f"FAILED {url}: {error}")
            failed += 1
        time.sleep(0.2)

    print(f"Downloaded={downloaded} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
