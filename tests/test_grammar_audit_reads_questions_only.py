"""The grammar audit must not be able to read gold, labels or families.

An external benchmark is spent once. Reading its answer key while building an
instrument spends it early and invisibly, and no one can later tell whether the
instrument was shaped by what it saw.

So the constraint is structural rather than a promise: ``_questions_only``
extracts one field and discards the record. These tests build a fixture whose
gold and label values are distinctive strings and assert none of them survives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_grammar_coverage as audit  # noqa: E402

POISON = "GOLD-MUST-NEVER-LEAK"


@pytest.fixture()
def fixture(tmp_path: Path) -> Path:
    path = tmp_path / "benchmark.json"
    path.write_bytes(json.dumps([
        {"question": "Which host should a billing deploy target?",
         "answer": POISON, "label": POISON, "family": POISON,
         "gold_evidence": [POISON], "meta": {"nested_gold": POISON}},
        {"query": "What is the current retention window?",
         "correct": POISON, "type": POISON},
    ]).encode("utf-8"))
    return path


def test_only_question_strings_are_returned(fixture: Path) -> None:
    questions = audit._questions_only(fixture)
    assert len(questions) == 2
    assert all(POISON not in q for q in questions)


def test_no_gold_reaches_the_report(fixture: Path) -> None:
    report = audit.run(audit._questions_only(fixture))
    assert POISON not in json.dumps(report)


def test_a_named_field_is_honoured_and_nothing_else_is_taken(fixture: Path) -> None:
    questions = audit._questions_only(fixture, field="question")
    assert questions == ["Which host should a billing deploy target?"]


def test_coverage_is_a_share_of_questions_not_of_patterns(fixture: Path) -> None:
    report = audit.run(audit._questions_only(fixture))
    for block in report["by_layer"].values():
        assert 0.0 <= block["coverage"] <= 1.0
        assert block["questions_matched"] <= report["questions"]


def test_every_layer_under_audit_is_reported() -> None:
    """A layer silently absent from the table would look like it was not needed."""
    assert set(audit.LAYERS) == {
        "entity_canon (0% domain vocabulary)",
        "address_extract entity (83% domain)",
        "address_extract property (93% domain)",
        "property_canon (84% domain)",
    }
