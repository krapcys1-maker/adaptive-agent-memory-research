"""A budget arm must be a prefix of the ranking, never a repack of it.

The defect this pins, measured rather than imagined: `truncate()` used `continue`
on an item that did not fit, which skips past it and keeps scanning for a later,
smaller item to pack into the remaining budget instead of stopping. Run against
the clean Mem0 ingest's actual deep rankings, this changed the kept item set for
17 of 30 (unit, budget) pairs at 500 and 1000 tokens -- always by keeping *more*
items than a true prefix, because a skipped big item left room for something
after it. `gold_in_context` and `gold_rank` are computed from
`deep_times[:len(keep)]`, which assumes `keep` is the first `len(keep)` items;
under `continue` that assumption is false whenever a skip occurred, so the
recorded gold metadata for those arms was wrong, not just the token count.

No provider call in this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.mem0_breadth_arms import truncate  # noqa: E402


def test_stops_at_the_first_item_that_does_not_fit() -> None:
    """The regression, exactly: a big item must not be skipped for a small one."""
    items = ["one two three", "a" * 2 + " " + "b c d e f g h i j k", "small"]
    # sizes (words): 3, 11, 1. Budget 5: item 0 fits (3), item 1 does not (3+11>5).
    assert truncate(items, budget=5) == ["one two three"]


def test_does_not_pack_a_later_smaller_item_into_a_skipped_gap() -> None:
    items = ["keep this", "way too large to ever fit the budget here", "tiny"]
    kept = truncate(items, budget=4)
    assert kept == ["keep this"]
    assert "tiny" not in kept


def test_result_is_always_a_prefix_of_the_input() -> None:
    items = ["a b", "c d e f g h", "i j", "k l m"]
    for budget in (0, 1, 2, 4, 6, 100):
        kept = truncate(items, budget)
        assert items[:len(kept)] == kept, (budget, kept)


def test_whole_items_only_never_split() -> None:
    items = ["one two three four five"]
    assert truncate(items, budget=4) == []
    assert truncate(items, budget=5) == items


def test_empty_input() -> None:
    assert truncate([], budget=500) == []
