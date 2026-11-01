"""shadow_baseline_measures.py: repetition and callback rates, day-level variance and detectable differences.

Every fixture is synthetic; no agent data is involved.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import shadow_baseline_measures as sbm  # noqa: E402


def item(item_id: str, day: str, text: str, title: str = "") -> sbm.Item:
    return sbm.Item(item_id, date.fromisoformat(day), text, title)


def seq(*items: sbm.Item) -> list:
    return sorted(items, key=lambda i: (i.day, i.item_id))


COPY = "the quarterly price sheet arrived late again and nobody noticed until the audit"


def test_ngram_overlap_has_the_expected_value() -> None:
    items = seq(item("a", "2026-01-01", "one two three four five"), item("b", "2026-01-02", "one two three four five six"))
    # b has two 5-grams, one of which a contains
    assert sbm.repetition_overlap(items, 1, 30, 5) == pytest.approx(0.5)
    assert sbm.repetition_overlap(items, 0, 30, 5) == 0.0  # nothing earlier


def test_repetition_is_flagged_inside_the_window_and_not_outside_it() -> None:
    items = seq(item("a", "2026-01-01", COPY), item("b", "2026-01-10", COPY + " today"), item("c", "2026-03-01", COPY))
    assert sbm.is_repetition(items, 1, window_days=30, n=5, threshold=0.5)
    assert not sbm.is_repetition(items, 2, window_days=30, n=5, threshold=0.5)  # 50 days later
    assert sbm.is_repetition(items, 2, window_days=60, n=5, threshold=0.5)


def test_the_repetition_threshold_is_respected() -> None:
    items = seq(item("a", "2026-01-01", "one two three four five"), item("b", "2026-01-02", "one two three four five six seven eight"))
    assert sbm.repetition_overlap(items, 1, 30, 5) == pytest.approx(0.25)  # one of four 5-grams
    assert not sbm.is_repetition(items, 1, threshold=0.5)
    assert sbm.is_repetition(items, 1, threshold=0.2)


def test_unrelated_texts_are_not_repetitions() -> None:
    items = seq(item("a", "2026-01-01", COPY), item("b", "2026-01-02", "a completely different sentence about something else entirely today"))
    assert not sbm.is_repetition(items, 1)


def test_a_text_shorter_than_the_ngram_is_never_a_repetition() -> None:
    items = seq(item("a", "2026-01-01", "short"), item("b", "2026-01-02", "short"))
    assert sbm.repetition_overlap(items, 1, 30, 5) == 0.0


def test_callback_by_phrase_and_by_quoted_title() -> None:
    items = seq(
        item("a", "2026-01-01", "text", title="Why the price sheet matters"),
        item("b", "2026-01-05", "As I wrote earlier, the audit was the trigger."),
        item("c", "2026-01-06", "I keep coming back to why the price sheet matters in practice."),
        item("d", "2026-01-07", "Nothing refers to anything here."),
        item("e", "2026-01-08", "Jak pisałem w zeszłym tygodniu, tak to działa."),
    )
    assert sbm.is_callback(items, 1)          # phrase
    assert sbm.is_callback(items, 2)          # earlier title quoted in full
    assert not sbm.is_callback(items, 3)
    assert sbm.is_callback(items, 4)          # Polish phrase


def test_a_short_title_does_not_count_as_a_callback() -> None:
    items = seq(item("a", "2026-01-01", "text", title="Prices"), item("b", "2026-01-02", "Prices went up again."))
    assert not sbm.is_callback(items, 1)


def test_daily_counts_group_by_day_in_date_order() -> None:
    items = seq(item("a", "2026-01-02", COPY), item("b", "2026-01-01", "x"), item("c", "2026-01-02", COPY))
    daily = sbm.daily_counts(items, lambda idx: items[idx].text == COPY)
    assert daily == [(date(2026, 1, 1), 1, 0), (date(2026, 1, 2), 2, 2)]


def test_intraclass_correlation_is_zero_for_identical_days_and_one_for_pure_day_effects() -> None:
    same = [(date(2026, 1, d), 4, 2) for d in range(1, 8)]
    assert sbm.intraclass_correlation(same) == pytest.approx(0.0)
    alternating = [(date(2026, 1, d), 4, 4 if d % 2 else 0) for d in range(1, 9)]
    assert sbm.intraclass_correlation(alternating) == pytest.approx(1.0)


def test_intraclass_correlation_needs_more_than_one_day() -> None:
    with pytest.raises(ValueError):
        sbm.intraclass_correlation([(date(2026, 1, 1), 5, 2)])


def test_detectable_difference_has_the_textbook_value() -> None:
    assert sbm.mde_task_randomised(0.5, 100, 100) == pytest.approx(0.1981, abs=0.001)


def test_detectable_difference_shrinks_with_more_tasks_and_balanced_arms() -> None:
    assert sbm.mde_task_randomised(0.3, 400, 400) < sbm.mde_task_randomised(0.3, 100, 100)
    table = sbm.mde_table(0.3, 300)
    values = {row["exposure"]: row["mde"] for row in table}
    assert values[0.5] < values[0.25] < values[0.1]


def test_randomising_whole_days_costs_precision_when_days_are_correlated() -> None:
    by_task = sbm.mde_task_randomised(0.3, 150, 150)
    by_day = sbm.mde_day_randomised(0.3, days_a=15, days_b=15, tasks_per_day=10, icc=0.2)
    assert by_day > by_task
    assert sbm.mde_day_randomised(0.3, 15, 15, 10, icc=0.0) == pytest.approx(by_task)


def test_summary_is_deterministic_and_reports_both_measures() -> None:
    items = seq(*[item("i%02d" % k, "2026-01-%02d" % (1 + k // 2), COPY if k % 3 == 0 else "text number %d is different enough from the rest" % k) for k in range(20)])
    first = sbm.summarise(items, 30, 5, 0.5, 100)
    assert first == sbm.summarise(items, 30, 5, 0.5, 100)
    assert set(first) >= {"items", "days", "repetition", "callback"}
    assert first["items"] == 20


def test_command_line_reads_jsonl_and_rejects_a_malformed_line(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    good = tmp_path / "items.jsonl"
    good.write_text("\n".join(json.dumps({"id": "a%d" % k, "date": "2026-01-%02d" % (1 + k), "text": COPY}) for k in range(5)) + "\n", encoding="utf-8")
    assert sbm.main([str(good), "--tasks-total", "50"]) == 0
    assert json.loads(capsys.readouterr().out)["items"] == 5
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "a", "date": "not-a-date", "text": "x"}\n', encoding="utf-8")
    assert sbm.main([str(bad)]) == 2
    assert "input error" in capsys.readouterr().err
