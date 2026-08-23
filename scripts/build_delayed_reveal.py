"""Build the delayed-task reveal for history family H1.

Issue #41. Deterministic, model-free, no network, no API cost.

The constraint this file exists to satisfy
------------------------------------------
From the compaction protocol:

    The delayed-task reveal is generated and frozen separately from the prefix.
    No write-side component sees the future query, future task, gold labels, or
    consequence weights.

The natural implementation violates it. Write the history, read it back, author
questions against it — and the question author has now seen the history and will
write questions it happens to answer well. The leak is invisible and it
flatters every arm equally, which is worse than a leak that favours one.

So **this module never opens the history.** It reads only
``scripts/corpus/history_family_spec.py``. Gold event identifiers are recomputed
through ``event_id()``, the same pure function the history generator used, so
the reveal can name an event it has never seen.

That is not a promise. ``tests/test_history_family_construction.py`` runs this
generator in a directory where the history file does not exist and asserts the
output is byte-identical. Output unchanged by removing an input did not depend
on that input.

What a forbidden event is
-------------------------
Some cases carry a ``forbidden_event``: a superseded, poisoned, or
outweighed-by-repetition record whose retrieval *in place of* the gold is the
specific failure being measured. Scoring these separately matters, because a
system that retrieves both looks fine on recall and is wrong in practice.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.history_family_spec import (  # noqa: E402
    DEFAULT_INSTANCES,
    DEFAULT_SEED,
    build_cases,
    event_id,
)

DEFAULT_OUT = ROOT / "data" / "lab" / "corpus-h1" / "reveal-v0"


def build(seed: int, instances: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (queries an arm is asked, gold an arm never sees)."""
    queries: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []

    for case in build_cases(seed, instances):
        probe = case.get("probe")
        if not probe:
            continue
        query_id = f"Q-{case['case_id']}"

        # What the arm is given. No gold, no properties, no case family name —
        # the family names the failure mode, and handing it over would tell the
        # arm what kind of mistake to avoid.
        queries.append(
            {
                "query_id": query_id,
                "asked_on_day": probe["day"],
                "question": probe["question"],
            }
        )

        forbidden = probe.get("forbidden_event")
        gold.append(
            {
                "query_id": query_id,
                "case_id": case["case_id"],
                "family": case["family"],
                "gold_event_id": event_id(*probe["gold_event"]),
                "forbidden_event_id": event_id(*forbidden) if forbidden else None,
                "answer_contains": probe["answer_contains"],
                "answer_must_not_contain": probe.get("answer_must_not_contain") or [],
                "why_hard": probe["why_hard"],
            }
        )

    queries.sort(key=lambda q: q["query_id"])
    gold.sort(key=lambda g: g["query_id"])
    return queries, gold


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
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
                        help="must match the history generator, or gold names events "
                             "that were never written")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    arguments = parser.parse_args(argv)

    queries, gold = build(arguments.seed, arguments.instances)
    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out

    query_digest = _write_jsonl(out / "queries.jsonl", queries)
    gold_digest = _write_jsonl(out / "gold.jsonl", gold)

    manifest = {
        "corpus_id": "H1",
        "issue": 41,
        "seed": arguments.seed,
        "instances_per_family": arguments.instances,
        "queries": len(queries),
        "queries_with_a_forbidden_event": sum(1 for g in gold if g["forbidden_event_id"]),
        "queries_sha256": query_digest,
        "gold_sha256": gold_digest,
        "generator": "scripts/build_delayed_reveal.py",
        "spec": "scripts/corpus/history_family_spec.py",
        "independence": (
            "this generator never opens the history; gold event identifiers are recomputed "
            "through the same pure event_id() function the history generator used"
        ),
        "independence_is_proven_by": (
            "tests/test_history_family_construction.py regenerates this output in a directory "
            "where history.jsonl does not exist and asserts byte-identical results"
        ),
    }
    (out / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )

    print(f"delayed reveal written to {_display(out)}")
    print(f"  queries              {len(queries)}")
    print(f"  with a forbidden set {manifest['queries_with_a_forbidden_event']}")
    print(f"  gold sha256          {gold_digest[:16]}…")
    print("\nThis generator never read the history. See the manifest for how that is proven.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
