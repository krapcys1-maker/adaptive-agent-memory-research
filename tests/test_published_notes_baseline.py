"""published_notes_baseline.py: cadence, lexical and semantic profiles, day clustering and detectable shifts.

Every fixture is synthetic; no agent data is involved, and the optional embedding model is replaced by hand-made unit vectors.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import published_notes_baseline as pnb  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402


def item(item_id: str, day: str, text: str, title: str = "") -> sbm.Item:
    return sbm.Item(item_id, date.fromisoformat(day), text, title)


COPY = "the quarterly price sheet arrived late again and nobody noticed until the audit came by"


def corpus() -> list:
    return sorted([
        item("a", "2026-01-01", COPY),
        item("b", "2026-01-01", "gardening notes about tomatoes and soil that has nothing to do with anything else here today"),
        item("c", "2026-01-02", COPY + " today"),                      # copies a on an earlier day
        item("d", "2026-01-03", "a completely different sentence about harbours, tides and the long wait for a late ferry"),
        item("e", "2026-01-05", "As I wrote earlier, the ferry was late again and nobody was surprised by it at all"),
    ], key=lambda i: (i.day, i.item_id))


def test_cadence_counts_days_words_and_exact_duplicates() -> None:
    items = corpus() + [item("f", "2026-01-06", COPY)]            # an exact duplicate of a
    c = pnb.cadence(items)
    assert c["items"] == 6 and c["days_with_items"] == 5 and c["first"] == "2026-01-01" and c["last"] == "2026-01-06"
    assert c["items_per_day"]["max"] == 2 and c["items_per_day"]["min"] == 1 and c["exact_duplicate_texts"] == 1


def test_lexical_profile_finds_the_planted_copy_and_nothing_else() -> None:
    profile = pnb.lexical_profile(corpus(), grams=(4,), windows=(30,), thresholds=(0.5, 0.9))
    row = profile["n=4,window=30d"]
    assert row["share_at_least"]["0.5"] == pytest.approx(1 / 5)       # only c repeats a
    assert row["share_at_least"]["0.9"] == pytest.approx(1 / 5)
    assert row["percentiles"]["99"] >= 0.9 and 0 < row["mean"] < 0.5


def test_callbacks_are_counted_with_the_strict_definition() -> None:
    result = pnb.callback_profile(corpus())
    assert result["count"] == 1 and result["rate"] == pytest.approx(0.2)


def unit(*values: float) -> list:
    norm = sum(v * v for v in values) ** 0.5
    return [v / norm for v in values]


def test_semantic_profile_reads_top_cosine_shares_gaps_and_leaves_the_first_item_out() -> None:
    items = [item("a", "2026-01-01", "x"), item("b", "2026-01-02", "x"), item("c", "2026-01-03", "x"), item("d", "2026-01-20", "x")]
    vectors = [unit(1, 0, 0), unit(0, 1, 0), unit(1, 0.1, 0), unit(0, 0, 1)]
    s = pnb.semantic_profile(items, vectors, thresholds=(0.5, 0.6, 0.7, 0.8), tasks=(200,), exposures=(0.5,))
    assert s["items_with_history"] == 3
    # b: best earlier is a with cosine 0; c: best is a (about 0.995); d: orthogonal to everything
    assert s["top1_cosine"]["mean"] == pytest.approx((0.0 + 0.995 + 0.0) / 3, abs=0.01)
    assert s["shares_at_least"]["0.8"]["any_earlier"] == pytest.approx(1 / 3, abs=1e-3)
    assert s["shares_at_least"]["0.8"]["median_gap_days_of_those"] == 2
    assert s["shares_at_least"]["0.8"]["partner_within_7_days_of_those"] == 1.0
    assert s["mde_mean_shift_of_top1_cosine"]["200_tasks_50%_in_memory_arm"] > 0


def test_a_neighbour_more_than_a_week_back_counts_for_any_earlier_but_not_for_the_recent_window() -> None:
    items = [item("a", "2026-01-01", "x"), item("b", "2026-01-30", "x")]
    s = pnb.semantic_profile(items, [unit(1, 0), unit(1, 0)], tasks=(100,), exposures=(0.5,))
    assert s["shares_at_least"]["0.8"]["any_earlier"] == 1.0 and s["shares_at_least"]["0.8"]["within_7_days"] == 0.0


def test_continuous_icc_is_zero_for_identical_days_and_one_for_pure_day_effects() -> None:
    assert pnb.continuous_icc([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]) == pytest.approx(0.0)
    assert pnb.continuous_icc([[0.1, 0.1], [0.9, 0.9], [0.1, 0.1], [0.9, 0.9]]) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        pnb.continuous_icc([[0.5, 0.4]])


def test_detectable_mean_shift_has_the_textbook_value_and_shrinks_with_more_tasks() -> None:
    assert pnb.mde_mean_shift(0.16, 200, 0.5) == pytest.approx(2.8 * 0.16 * (2 / 100) ** 0.5)
    assert pnb.mde_mean_shift(0.16, 400, 0.5) < pnb.mde_mean_shift(0.16, 200, 0.5) < pnb.mde_mean_shift(0.16, 200, 0.1)


def test_the_profile_never_contains_text_or_ids(capsys: pytest.CaptureFixture, tmp_path: Path) -> None:
    path = tmp_path / "items.jsonl"
    path.write_text("\n".join(json.dumps({"id": "secret-id-%d" % k, "date": "2026-01-%02d" % (1 + k // 2), "text": COPY + " marker%d" % k}) for k in range(10)) + "\n",
                    encoding="utf-8")
    out_file = tmp_path / "out.json"
    assert pnb.main([str(path), "--json", str(out_file)]) == 0
    printed = capsys.readouterr().out
    written = out_file.read_text(encoding="utf-8")
    for forbidden in ("secret-id", "marker", "quarterly", "price sheet"):
        assert forbidden not in printed and forbidden not in written
    data = json.loads(printed)
    assert set(data) >= {"cadence", "lexical", "callbacks", "provisional_repetition_rule"} and "semantic" not in data


def test_malformed_input_and_too_few_items_are_rejected(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "a", "date": "nope", "text": "x"}\n', encoding="utf-8")
    assert pnb.main([str(bad)]) == 2
    short = tmp_path / "short.jsonl"
    short.write_text('{"id": "a", "date": "2026-01-01", "text": "x"}\n', encoding="utf-8")
    assert pnb.main([str(short)]) == 2
    assert "input error" in capsys.readouterr().err
