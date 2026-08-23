"""Collect the arm runs into one table, and refuse to compare incomparable ones.

Why this is a script and not a paragraph
----------------------------------------
An arm comparison is void unless every arm ran under the same budget, the same
reader and the same corpus. Those three facts sit in three separate result
files, and checking them by eye is exactly the kind of task that gets skipped
once the numbers look interesting.

So this refuses rather than warns. A table that silently mixes a 250-token arm
with a 500-token one is worse than no table: it looks like a finding.

What it reports, and why not just the winner
---------------------------------------------
``answered``  correct, from what the arm retained
``leaked``    answered from the record the case was built to trap — the obsolete
              host, the poisoned instruction. **An arm can lead on `answered`
              and lead on `leaked` at once**, and a ranking by `answered` alone
              would hide it.
``empty``     no answer produced. A harness fact, not a model one, and reported
              separately because the first full run hid five truncated reasoning
              responses inside the failure count.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "lab" / "corpus-h1"

ORDER = ("random", "recency", "frequency", "fts5")


def collect(corpus: Path) -> list[dict[str, Any]]:
    runs = []
    for arm in ORDER:
        path = corpus / f"reader-v0-{arm}" / "results.json"
        if path.is_file():
            runs.append(json.loads(path.read_text(encoding="utf-8"))["summary"])
    return runs


def guard(runs: list[dict[str, Any]]) -> None:
    """Refuse to tabulate arms that were not run under the same conditions."""
    if len(runs) < 2:
        raise SystemExit("fewer than two arms have results; nothing to compare")
    for field, label in (("token_budget", "token budget"), ("reader", "reader"),
                         ("probes", "probe count")):
        values = {run["arm"]: run.get(field) for run in runs}
        if len(set(values.values())) > 1:
            raise SystemExit(
                f"refusing to tabulate: the arms did not share a {label} — {values}. "
                "A comparison across differing conditions measures the condition."
            )


def render(runs: list[dict[str, Any]]) -> str:
    head = runs[0]
    lines = [
        "PMLAB-H1-READ-E1 — retention arms on corpus H1",
        f"  reader {head['reader']}   budget {head['token_budget']} tokens   "
        f"{head['probes']} probes   Tier E, development measurement only",
        "",
        f"  {'arm':<11}{'gold':>8}{'answered':>10}{'leaked':>9}{'empty':>8}{'abstained':>11}  note",
    ]
    for run in runs:
        lines.append(
            f"  {run['arm']:<11}{run['gold_retrieved']:>8.3f}{run['answered']:>10.3f}"
            f"{run['leaked']:>9.3f}{run.get('empty', 0) or 0:>8.3f}"
            f"{run['abstained']:>11.3f}  {run['arm_note']}"
        )

    families = sorted(runs[-1]["by_family"])
    lines += ["", "  answered, by family", "",
              f"  {'arm':<11}" + "".join(f"{f[:9]:>10}" for f in families)]
    for run in runs:
        lines.append(f"  {run['arm']:<11}"
                     + "".join(f"{run['by_family'][f]['answered']:>10.3f}" for f in families))

    lines += ["", "  answered from the trapped record, by family", "",
              f"  {'arm':<11}" + "".join(f"{f[:9]:>10}" for f in families)]
    for run in runs:
        lines.append(f"  {run['arm']:<11}"
                     + "".join(f"{run['by_family'][f]['leaked']:>10.3f}" for f in families))

    spend = sum(run.get("spend_usd", 0) for run in runs)
    lines += ["", f"  total spend across these arms: ${spend:.4f}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    runs = collect(arguments.corpus if arguments.corpus.is_absolute() else ROOT / arguments.corpus)
    guard(runs)
    table = render(runs)
    print(table)

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((table + "\n").encode("utf-8"))
        print(f"\nwritten: {destination.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
