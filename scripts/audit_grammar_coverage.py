"""Do our entity patterns even fire on an external benchmark's questions?

This runs **before** anything is scored, and it separates two findings a single
accuracy number would merge:

    the mechanism failed          it fired and chose wrongly
    the mechanism never fired     no pattern matched the question at all

Those need different work. The first is a rule that is wrong; the second is a
rule that was written for a grammar the benchmark does not use.

The constraint, enforced structurally
--------------------------------------
It reads **only the question text**. Not gold answers, not labels, not the
success key, not the family. That is not a promise about what was looked at —
``_questions_only`` extracts one field and discards the record, so nothing else
reaches the matching code, and a test asserts the loader never returns anything
else.

The reason is the same one that put the benchmark behind a commitment: an
external test is spent once, and reading its answer key while building an
instrument spends it early and invisibly.

What a result means
-------------------
``coverage = 0.06``   the six constructions match almost nothing, so the layer
                      that took internal coverage from 0.571 to 1.000 never gets
                      to run. Any external failure would then be uninformative
                      about the mechanism.
``coverage = 0.72``   the layer gets a fair chance. It still says nothing about
                      whether its answers are right — only that it fires.

Registered prediction, from ``candidate-0-addendum-prediction.json``: the
property layer carries 84–93% H1/H2 domain vocabulary and should transfer badly;
``entity_canon`` carries none. That is a comparison between layers, not a claim
that either generalises — and zero domain tokens means domain-independent, never
grammar-independent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus.address_extract import _ENTITY_PATTERNS, _PROPERTY_RULES  # noqa: E402
from corpus.entity_canon import _QUESTION_POSITIONS  # noqa: E402
from corpus.property_canon import _COMPILED as _PROPERTY_FORMS  # noqa: E402

# Field names an external benchmark might use for the question. Anything not
# named here is never read.
QUESTION_FIELDS = ("question", "query", "prompt", "q", "text", "instruction")


def _questions_only(path: Path, field: str | None = None) -> list[str]:
    """Every question string, and nothing else from the file.

    The record is discarded after one field is taken. Gold answers, labels and
    family names exist in the file and do not reach the caller, which is what
    makes the constraint structural rather than a matter of discipline.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else list(raw.values())

    questions: list[str] = []

    def harvest(node: Any) -> None:
        if isinstance(node, dict):
            for name in ([field] if field else QUESTION_FIELDS):
                value = node.get(name)
                if isinstance(value, str) and value.strip():
                    questions.append(value.strip())
                    return
            for value in node.values():
                harvest(value)
        elif isinstance(node, list):
            for value in node:
                harvest(value)

    for row in rows:
        harvest(row)
    return questions


LAYERS = {
    "entity_canon (0% domain vocabulary)": [p for p in _QUESTION_POSITIONS],
    "address_extract entity (83% domain)": [p for p in _ENTITY_PATTERNS],
    "address_extract property (93% domain)": [p for p, _ in _PROPERTY_RULES],
    "property_canon (84% domain)": [p for _, p in _PROPERTY_FORMS],
}


def run(questions: list[str]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "audit": "grammar coverage of an external benchmark's questions",
        "reads": "question text only; gold, labels and families are never loaded",
        "questions": len(questions),
        "by_layer": {},
    }

    for label, patterns in LAYERS.items():
        matched = [q for q in questions if any(p.search(q) for p in patterns)]
        per_pattern = Counter()
        for question in questions:
            for index, pattern in enumerate(patterns):
                if pattern.search(question):
                    per_pattern[index] += 1
        report["by_layer"][label] = {
            "patterns": len(patterns),
            "questions_matched": len(matched),
            "coverage": round(len(matched) / len(questions), 4) if questions else None,
            "patterns_that_never_fire": sum(1 for i in range(len(patterns)) if not per_pattern[i]),
            "example_matched": matched[:2],
        }

    entity = report["by_layer"]["entity_canon (0% domain vocabulary)"]["coverage"]
    both = report["by_layer"]["property_canon (84% domain)"]["coverage"]
    report["reading"] = (
        "coverage is whether a layer fires at all, never whether it is right. A layer at near zero "
        "cannot produce an informative failure, because it never ran"
    )
    report["against_the_registered_prediction"] = (
        f"entity_canon fires on {entity}, the property layer on {both}. The prediction was that "
        "entity_canon has a stronger reason to transfer because it carries no domain vocabulary. "
        "If both are near zero the prediction is falsified and those constructions were specific to "
        "our question grammar rather than our domain"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--field", default=None, help="question field name, if known")
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    questions = _questions_only(arguments.dataset, arguments.field)
    if not questions:
        raise SystemExit("no question field found; pass --field with the right name")

    report = run(questions)
    print(f"Grammar coverage — {report['questions']} questions, question text only\n")
    print(f"  {'layer':<40}{'patterns':>9}{'matched':>9}{'coverage':>10}{'dead':>6}")
    for label, block in report["by_layer"].items():
        print(f"  {label:<40}{block['patterns']:>9}{block['questions_matched']:>9}"
              f"{block['coverage']:>10.4f}{block['patterns_that_never_fire']:>6}")
    print(f"\n  {report['reading']}")
    print(f"\n  {report['against_the_registered_prediction']}")

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
