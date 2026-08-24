"""Deterministic tests for SAME_CATEGORY_ENTITY_ENUMERATION (Mechanism E).
No LLM call, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.sibling_entity_enumeration import (  # noqa: E402
    same_category_entity_enumeration, extract_category_entities,
)


def test_flags_two_distinct_entities_sharing_a_category() -> None:
    ctx = ["Curious about Spirit Airlines' baggage policies",
          "Flew Delta Airlines to Boston", "Likes coffee"]
    rendered, trace = same_category_entity_enumeration(ctx)
    assert trace["flagged"] is True
    assert set(trace["plural_categories"]["Airlines"]) == {"Spirit Airlines", "Delta Airlines"}
    assert rendered[:3] == ctx
    assert "Spirit Airlines" in rendered[-1] and "Delta Airlines" in rendered[-1]


def test_inert_with_only_one_entity_in_a_category() -> None:
    ctx = ["Flew Delta Airlines to Boston", "Likes coffee", "Works at Google"]
    rendered, trace = same_category_entity_enumeration(ctx)
    assert rendered == ctx
    assert trace["inert"] is True


def test_inert_when_same_entity_repeated() -> None:
    ctx = ["Visited the Science Museum", "Also went to the Science Museum again"]
    rendered, trace = same_category_entity_enumeration(ctx)
    assert rendered == ctx
    assert trace["inert"] is True


def test_inert_with_no_category_matches() -> None:
    ctx = ["Likes pizza", "The sky is blue"]
    rendered, trace = same_category_entity_enumeration(ctx)
    assert rendered == ctx
    assert trace["inert"] is True


def test_multiple_categories_each_get_their_own_note() -> None:
    ctx = ["Spirit Airlines flight", "Delta Airlines flight",
          "Science Museum visit", "History Museum visit"]
    rendered, trace = same_category_entity_enumeration(ctx)
    assert set(trace["plural_categories"].keys()) == {"Airlines", "Museum"}
    assert len(rendered) == len(ctx) + 2  # one note per plural category


def test_extract_category_entities_basic() -> None:
    found = extract_category_entities("Flew Spirit Airlines and visited the Science Museum")
    names = [name for name, _cat in found]
    assert "Spirit Airlines" in names
    assert "Science Museum" in names


def test_does_not_indicate_which_entity_is_correct() -> None:
    """The note enumerates, it never picks a winner -- no gold-aware logic."""
    ctx = ["Spirit Airlines flight", "Delta Airlines flight"]
    rendered, _ = same_category_entity_enumeration(ctx)
    note = rendered[-1]
    assert "the correct" not in note.lower() and "is the answer" not in note.lower()


def test_real_historical_case_gpt4_f420262c_would_have_fired() -> None:
    """Regression anchor: the one confirmed AAMR HARMFUL_SIBLING_DISTRACTION case
    (Ledger Entry C) -- three airlines present in the mem0_3000 context,
    including the wrong answer actually given (Spirit Airlines)."""
    ctx = ["Curious about Spirit Airlines' baggage policies for an upcoming trip",
          "Flew United Airlines for a business trip",
          "Booked American Airlines for a family vacation"]
    rendered, trace = same_category_entity_enumeration(ctx)
    assert trace["flagged"] is True
    assert "Spirit Airlines" in trace["plural_categories"]["Airlines"]
