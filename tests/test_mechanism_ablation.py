"""A Hindsight budget arm must be an exact prefix, and its gold label must
track the positions actually retained -- not positions that merely share text
with something retained.

The defect this pins, measured rather than imagined: `truncate()` used
`continue` on overflow, same as `mem0_breadth_arms.py`'s bug, changing the kept
context for 18 of 30 (unit, budget) pairs across `hindsight_mem0_matched` (6),
`hindsight_500` (5) and `hindsight_1000` (7) -- figures from the actual audit
against the frozen retrieval data, not this file. `gold_state` was called
with `kept_times` computed as
`[times[i] for i, item in enumerate(items) if item in keep][:len(keep)]` --
matching by *text*, not position. Proven safe once `keep` is a true prefix
(the first `len(keep)` matches in iteration order are always exactly
positions `0..len(keep)-1`, because every prefix position trivially satisfies
`item in keep`), but that safety depended entirely on `truncate` never
skipping -- exactly the invariant that had silently broken. Replaced with
`times[:len(keep)]`, which needs no such argument.

No provider call in this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.mechanism_ablation import build_arms, gold_state, truncate  # noqa: E402


def test_stops_at_the_first_item_that_does_not_fit() -> None:
    """[80, 50, 10] words, budget 100: only the 80-word item survives."""
    items = ["w " * 80, "x " * 50, "y " * 10]
    items = [i.strip() for i in items]
    kept = truncate(items, budget=100)
    assert kept == [items[0]]


def test_duplicate_text_items_are_each_considered_by_their_own_position() -> None:
    """Two items with identical text are not collapsed or conflated.

    Sizes 2, 2, 1 (words); budget 3: the first "a b" fits (used=2), the
    second "a b" does not (2+2=4>3) and must stop the scan there, not skip
    it to reach "c".
    """
    items = ["a b", "a b", "c"]
    assert truncate(items, budget=3) == ["a b"]


def test_result_is_always_a_prefix_of_the_input() -> None:
    items = ["a b", "c d e f g", "h i", "j k l"]
    for budget in (0, 1, 2, 5, 8, 100):
        kept = truncate(items, budget)
        assert items[:len(kept)] == kept, (budget, kept)


def test_gold_alignment_survives_a_duplicated_item_text() -> None:
    """The regression, end to end, through the real arm builder.

    Two evidence items share the text "a b c": one at the date that maps to
    the gold session, one at a date that does not. A budget of 3 keeps only
    the first (non-gold) occurrence. A text-matching alignment would have
    matched "a b c" against *either* occurrence and, for a query this small,
    happened to still read correctly by luck of iteration order -- so this
    test is a smaller live tripwire, not the proof; the proof is the counted
    audit in this file's docstring. Position-based alignment reports the
    correct thing regardless of luck: gold is not among what was actually
    kept.
    """
    data = {
        "units": {"q1": {"question_id": "q1", "slot": "test",
                         "question_type": "single-session-user"}},
        "corpus": {"q1": {
            "question_id": "q1", "question": "when?", "answer": "42",
            "haystack_dates": ["2022-01-01", "2022-01-02", "2022-01-03"],
            "haystack_session_ids": ["s0", "s1", "s2"],
            "answer_session_ids": ["s2"],
        }},
        "raw": {
            "mem0": {"q1": {"context_texts": ["x y z"]}},  # drives the matched budget to 3
            "hindsight": {"q1": {
                "context_texts": ["a b c", "d e f g h", "a b c"],
                "evidence_times": ["2022-01-01", "2022-01-02", "2022-01-03"],
            }},
        },
    }

    arms = {a["arm"]: a for a in build_arms(data) if a["question_id"] == "q1"}

    matched = arms["hindsight_mem0_matched"]
    assert matched["budget_tokens"] == 3
    assert matched["context"] == ["a b c"]
    assert matched["gold_state"] == {"observable": True, "gold_in_context": False,
                                     "gold_rank": None}

    # At budget 500 nothing truncates: both "a b c" occurrences and the
    # middle item all survive, and gold sits at the third retained position
    # (the date matching the gold session), not the first.
    wide = arms["hindsight_500"]
    assert wide["context"] == ["a b c", "d e f g h", "a b c"]
    assert wide["gold_state"] == {"observable": True, "gold_in_context": True, "gold_rank": 3}


def test_gold_rank_counts_only_retained_evidence() -> None:
    """`gold_state` itself: rank is 1-based over whatever `times` it is given.

    Callers are responsible for `times` already being the truncated set --
    this pins that `gold_state` does not look past what it was handed.
    """
    row = {
        "haystack_dates": ["2022-01-01", "2022-01-02", "2022-01-03"],
        "haystack_session_ids": ["s0", "s1", "s2"],
        "answer_session_ids": ["s2"],
    }
    full = ["2022-01-01", "2022-01-02", "2022-01-03"]
    assert gold_state(row, full) == {"observable": True, "gold_in_context": True, "gold_rank": 3}

    truncated_before_gold = full[:2]
    assert gold_state(row, truncated_before_gold) == {
        "observable": True, "gold_in_context": False, "gold_rank": None}
