"""Build history family H1: the prefix half of the compaction corpus.

Issue #41. Deterministic, model-free, no network, no API cost.

What this produces
------------------
``history.jsonl``              the event stream every arm sees
``construction-labels.jsonl``  which property each event instantiates
``manifest.json``              seed, counts, and SHA-256 of both files

**The labels live in a separate file on purpose.** If ``properties`` rode along
on each event, an arm could retain exactly the events marked
``rare-critical-exception`` and score perfectly without doing any of the work
being measured. The split is what keeps the corpus honest, and it costs one
extra file.

What this deliberately does not produce
---------------------------------------
The queries and the gold answers. Those come from ``build_delayed_reveal.py``,
which never reads this output. See ``scripts/corpus/history_family_spec.py``
for why that separation is structural rather than a promise, and
``tests/test_history_family_construction.py`` for the proof.

Scale
-----
This is the construction-test tier of the ladder in
``docs/11-research-laboratory/foundation-compaction-memory-benchmark-protocol-v0.md``:
*run construction tests first, then 100K, 1M, 5M and 10M cumulative-token
histories where feasible*. Nothing here needs a model, so it runs on a laptop
in under a second, and a corpus that fails construction tests at this size
would fail them at 10M more expensively.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.history_family_spec import (  # noqa: E402
    DEFAULT_INSTANCES,
    DEFAULT_SEED,
    FAMILIES,
    HISTORY_DAYS,
    build_cases,
    event_id,
    noise_events,
)

DEFAULT_OUT = ROOT / "data" / "lab" / "corpus-h1" / "prefix-v0"
DEFAULT_NOISE = 240


def _day_stamp(day: int) -> str:
    """A calendar time for a simulated day. No clock is read."""
    return f"2026-01-{day:02d}T09:00:00Z" if day < 32 else f"2026-02-{day - 31:02d}T09:00:00Z"


def build(seed: int, instances: int, noise: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (events the arms see, construction labels)."""
    raw: list[dict[str, Any]] = []

    for case in build_cases(seed, instances):
        for index, event in enumerate(case["events"]):
            raw.append({**event, "case_id": case["case_id"], "index": index})

    raw.extend(noise_events(seed, noise))

    # Stable order: by day, then by identifier. Deterministic and independent of
    # the order cases happen to be declared in, so adding a case later does not
    # reshuffle the events already frozen.
    raw.sort(key=lambda e: (e["day"], e["case_id"], e["index"]))

    events: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    for position, item in enumerate(raw):
        identifier = event_id(item["case_id"], item["index"])
        events.append(
            {
                "event_id": identifier,
                "position": position,
                "day": item["day"],
                "timestamp": _day_stamp(item["day"]),
                "channel": item["channel"],
                "text": item["text"],
            }
        )
        labels.append({"event_id": identifier, "properties": sorted(item["properties"])})

    return events, labels


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    """Write with explicit LF and return the digest.

    ``Path.write_text`` translates to CRLF on Windows, which silently changed
    declared digests here once already. Bytes are written directly for that
    reason, and ``.gitattributes`` keeps the checkout byte-stable.
    """
    payload = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows)
    data = payload.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()



def _display(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    ``Path.relative_to`` raises for a path outside the repository, and this
    project has now hit that three times — a print statement is not worth
    aborting a run that already wrote its output.
    """
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--instances", type=int, default=DEFAULT_INSTANCES,
                        help="how many times each case family is instantiated")
    parser.add_argument("--noise", type=int, default=DEFAULT_NOISE,
                        help="filler events carrying no probe")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    arguments = parser.parse_args(argv)

    events, labels = build(arguments.seed, arguments.instances, arguments.noise)
    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out

    history_digest = _write_jsonl(out / "history.jsonl", events)
    label_digest = _write_jsonl(out / "construction-labels.jsonl", labels)

    counts: dict[str, int] = {}
    for label in labels:
        for name in label["properties"]:
            counts[name] = counts.get(name, 0) + 1

    manifest = {
        "corpus_id": "H1",
        "issue": 41,
        "seed": arguments.seed,
        "history_days": HISTORY_DAYS,
        "events": len(events),
        "case_families": len(FAMILIES),
        "instances_per_family": arguments.instances,
        "cases": len(FAMILIES) * arguments.instances,
        "noise_events": arguments.noise,
        "property_counts": dict(sorted(counts.items())),
        "history_sha256": history_digest,
        "construction_labels_sha256": label_digest,
        "generator": "scripts/build_history_family.py",
        "spec": "scripts/corpus/history_family_spec.py",
        "reveal_is_generated_separately": (
            "scripts/build_delayed_reveal.py reads only the spec and never this output; "
            "tests/test_history_family_construction.py proves it by regenerating the reveal "
            "in a directory where this file does not exist"
        ),
        "labels_are_separate_because": (
            "an arm that could read properties would retain exactly the marked events and "
            "score perfectly without performing the selection being measured"
        ),
    }
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out / "manifest.json").write_bytes(payload.encode("utf-8"))

    print(f"history family H1 written to {_display(out)}")
    print(f"  events   {len(events)}")
    print(f"  cases    {len(FAMILIES) * arguments.instances} "
          f"({len(FAMILIES)} families x {arguments.instances})")
    print(f"  sha256   {history_digest[:16]}…")
    print("\nproperty counts")
    for name, count in sorted(counts.items()):
        print(f"  {name:<28} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
