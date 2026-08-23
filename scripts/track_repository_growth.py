"""Record repository reach as a time series, so growth can be attributed.

Why a series and not a glance
-----------------------------
A weekly look at the star count tells you the number. It does not tell you
which of the things done that week produced it, and that is the only question
worth asking — the point of measuring reach is to stop guessing which
publications work.

So each run appends one row and the report prints deltas against the previous
row. A week with a delta and no recorded event is a prompt to go and find out
what happened; a week with an event and no delta is evidence that the event did
not work, which is equally useful and much easier to ignore.

What it records
---------------
Reach, and the contribution funnel underneath it, because stars without
contributors is vanity:

    stars, forks, watchers          reach
    unique non-author contributors  the funnel actually converting
    open/closed issues, open PRs    whether the work is visible
    good-first-issues open          whether there is a way in

Deliberately not recorded
-------------------------
Traffic views and clones. GitHub retains them for 14 days only, so a weekly
series built on them would silently become a series of partial windows. If they
are wanted, they need daily collection, which is a different tool.

No token is embedded here; it shells out to ``gh``, which the maintainer
already has authenticated.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "data" / "community" / "repository-growth.csv"

FIELDS = [
    "captured_at",
    "stars",
    "forks",
    "watchers",
    "open_issues",
    "closed_issues",
    "open_prs",
    "merged_prs",
    "good_first_issues_open",
    "contributors_excluding_author",
    "note",
]


def gh(*args: str) -> Any:
    """Run a gh command and parse its JSON output."""
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout or "null")


def collect(owner_repo: str, author: str) -> dict[str, Any]:
    repo = gh(
        "repo", "view", owner_repo,
        "--json", "stargazerCount,forkCount,watchers,issues,pullRequests",
    )

    def count(query: list[str]) -> int:
        rows = gh(*query)
        return len(rows) if isinstance(rows, list) else 0

    open_issues = count(["issue", "list", "--repo", owner_repo, "--state", "open",
                         "--limit", "500", "--json", "number"])
    closed_issues = count(["issue", "list", "--repo", owner_repo, "--state", "closed",
                           "--limit", "500", "--json", "number"])
    open_prs = count(["pr", "list", "--repo", owner_repo, "--state", "open",
                      "--limit", "200", "--json", "number"])
    merged_prs = count(["pr", "list", "--repo", owner_repo, "--state", "merged",
                        "--limit", "200", "--json", "number"])
    gfi = count(["issue", "list", "--repo", owner_repo, "--state", "open",
                 "--label", "good first issue", "--limit", "200", "--json", "number"])

    # Contributors from merged pull requests rather than the commit graph: a
    # commit authored by the maintainer on someone's behalf is not a
    # contributor, and the funnel this measures is people, not commits.
    prs = gh("pr", "list", "--repo", owner_repo, "--state", "merged",
             "--limit", "200", "--json", "author")
    logins = {
        (p.get("author") or {}).get("login", "")
        for p in (prs or [])
    }
    logins.discard("")
    logins.discard(author)

    return {
        "stars": repo.get("stargazerCount", 0),
        "forks": repo.get("forkCount", 0),
        "watchers": (repo.get("watchers") or {}).get("totalCount", 0),
        "open_issues": open_issues,
        "closed_issues": closed_issues,
        "open_prs": open_prs,
        "merged_prs": merged_prs,
        "good_first_issues_open": gfi,
        "contributors_excluding_author": len(logins),
    }


def read_series() -> list[dict[str, str]]:
    if not SERIES.is_file():
        return []
    with SERIES.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def append(row: dict[str, Any]) -> None:
    SERIES.parent.mkdir(parents=True, exist_ok=True)
    exists = SERIES.is_file()
    # newline="" plus an explicit terminator, because the default on Windows
    # would write CRLF into a file the repository declares as byte-stable.
    with SERIES.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in FIELDS})


def report(previous: dict[str, str] | None, current: dict[str, Any]) -> str:
    lines = ["Repository growth\n"]
    numeric = [f for f in FIELDS if f not in {"captured_at", "note"}]
    width = max(len(f) for f in numeric)
    for field in numeric:
        now = current.get(field, 0)
        if previous is None:
            lines.append(f"  {field:<{width}}  {now:>6}")
            continue
        try:
            was = int(previous.get(field, 0) or 0)
        except ValueError:
            was = 0
        delta = int(now) - was
        marker = f"{delta:+d}" if delta else "  ·"
        lines.append(f"  {field:<{width}}  {now:>6}   {marker:>5}")
    if previous is not None:
        lines.append(f"\n  compared against {previous.get('captured_at', '?')}")
        if previous.get("note"):
            lines.append(f"  that row noted: {previous['note']}")
    else:
        lines.append("\n  first row; no comparison available yet")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", default="krapcys1-maker/adaptive-agent-memory-research")
    parser.add_argument("--author", default="krapcys1-maker",
                        help="excluded from the contributor count")
    parser.add_argument("--at", required=True,
                        help="ISO-8601 UTC capture time; passed in rather than read "
                             "from the clock so a run is reproducible")
    parser.add_argument("--note", default="",
                        help="what was done since the last row, so a delta can be attributed")
    parser.add_argument("--dry-run", action="store_true",
                        help="report without appending")
    arguments = parser.parse_args(argv)

    try:
        current = collect(arguments.repo, arguments.author)
    except (RuntimeError, FileNotFoundError) as error:
        print(f"could not reach GitHub: {error}", file=sys.stderr)
        return 1

    series = read_series()
    print(report(series[-1] if series else None, current))

    if arguments.dry_run:
        print("\ndry run; nothing appended")
        return 0

    append({"captured_at": arguments.at, "note": arguments.note, **current})
    print(f"\nappended to {SERIES.relative_to(ROOT).as_posix()} ({len(series) + 1} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
