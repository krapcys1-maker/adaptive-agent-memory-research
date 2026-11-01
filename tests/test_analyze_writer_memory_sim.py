"""analyze_writer_memory_sim.py: measures, paired contrasts, the bootstrap and the pre-stated readings.

Every record is synthetic and hand-built, so the expected values can be worked out by hand.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_writer_memory_sim as ana  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

HOOK = "A firm bans meetings before 10 a.m. for a month."


def row(arm: str, day: int, text: str, seed: int = 1, hook: str = HOOK, block: str = "", title: str = "T") -> dict:
    return {"seed": seed, "arm": arm, "day": day, "theme": "meetings", "hook": hook, "title": title + str(day), "text": text,
            "words": len(text.split()), "shown_ids": [], "memory_block": block, "trace": None, "prompt_tokens": 100,
            "gen_tokens": 50, "wall_s": 1.0}


SAME = "the quarterly price sheet arrived late again and nobody noticed until the audit came by"


def distinct(day: int) -> str:
    return " ".join("w%d_%d" % (day, k) for k in range(14))


def test_identical_entries_overlap_completely_and_distinct_ones_not_at_all() -> None:
    rows = [row("M0", d, SAME) for d in range(1, 11)] + [row("M2", d, distinct(d)) for d in range(1, 11)]
    measured = ana.measure_all(rows)
    assert measured[("M0", 1)][10]["overlap4"] == pytest.approx(1.0)
    assert measured[("M0", 1)][1]["overlap4"] == 0.0           # nothing earlier
    assert measured[("M2", 1)][10]["overlap4"] == 0.0
    assert measured[("M0", 1)][10]["union_novelty"] == pytest.approx(0.0)
    assert measured[("M2", 1)][10]["union_novelty"] == pytest.approx(1.0)
    assert measured[("M0", 1)][10]["rep_rate"] == 1.0 and measured[("M2", 1)][10]["rep_rate"] == 0.0


def test_hook_coverage_is_the_share_of_the_hooks_content_words_found_in_the_entry() -> None:
    hook_words = set(sim.content_tokens(HOOK))
    some = sorted(hook_words)[:2]
    text = " ".join(some) + " and other unrelated words appear here as well today"
    measured = ana.measure_all([row("M0", 1, text)])
    assert measured[("M0", 1)][1]["hook_coverage"] == pytest.approx(2 / len(hook_words))
    assert ana.measure_all([row("M0", 1, "nothing in common at all")])[("M0", 1)][1]["hook_coverage"] == 0.0


def test_callbacks_are_counted_by_both_definitions() -> None:
    rows = [row("M1", 1, "first entry", title="Why the price sheet matters"),
            row("M1", 2, "As I wrote earlier, the sheet matters."),
            row("M1", 3, "I keep coming back to why the price sheet matters in practice."),
            row("M1", 4, "Nothing refers to anything here.")]
    for r in rows:
        r["title"] = "Why the price sheet matters" if r["day"] == 1 else r["title"]
    m = ana.measure_all(rows)[("M1", 1)]
    assert m[2]["callback_strict"] == 1.0 and m[2]["callback_ext"] == 1.0   # phrase
    assert m[3]["callback_strict"] == 1.0 and m[3]["callback_ext"] == 0.0   # earlier title quoted in full
    assert m[4]["callback_strict"] == 0.0 and m[4]["callback_ext"] == 0.0


def test_shown_copy8_measures_verbatim_copying_from_the_notes_and_is_undefined_without_notes() -> None:
    block = "[Entry from day 1]\nTITLE: x\n" + SAME
    m = ana.measure_all([row("M2", 1, SAME, block=block), row("M2", 2, distinct(2), block=block), row("M0", 1, SAME)])
    assert m[("M2", 1)][1]["shown_copy8"] == pytest.approx(1.0)
    assert m[("M2", 1)][2]["shown_copy8"] == 0.0
    assert m[("M0", 1)][1]["shown_copy8"] is None


def test_the_bootstrap_is_deterministic_and_collapses_when_every_difference_is_equal() -> None:
    assert ana.bootstrap_indices(5, 3, 1) == ana.bootstrap_indices(5, 3, 1)
    assert ana.bootstrap_indices(5, 3, 1) != ana.bootstrap_indices(5, 3, 2)
    assert all(0 <= i < 5 for picks in ana.bootstrap_indices(5, 50, 1) for i in picks)
    low, high = ana.interval([0.3] * 12, {}, 200)
    assert low == pytest.approx(0.3) and high == pytest.approx(0.3)
    low, high = ana.interval([0.0, 1.0] * 20, {}, 1000)
    assert low < 0.5 < high


def test_contrasts_are_paired_by_stream_and_day_and_use_analysis_days_only() -> None:
    rows = []
    for seed in (1, 2):
        rows += [row("M0", d, SAME, seed=seed) for d in range(1, 13)] + [row("M2", d, distinct(d), seed=seed) for d in range(1, 13)]
    measured = ana.measure_all(rows)
    c = ana.contrast(measured, "M2", "M0", "overlap4", [1, 2], {}, 200)
    assert c["n"] == 2 * 6                      # days 7..12 of two streams
    assert c["mean"] == pytest.approx(-1.0) and c["ci_low"] == pytest.approx(-1.0) and c["ci_high"] == pytest.approx(-1.0)
    assert c["per_seed"] == {"1": pytest.approx(-1.0), "2": pytest.approx(-1.0)}
    assert ana.contrast(measured, "M3a", "M0", "overlap4", [1, 2], {}, 200) is None   # arm absent


def test_readings_follow_the_table_stated_in_advance() -> None:
    rows = []
    for d in range(1, 13):
        rows += [row("M0", d, SAME), row("M2", d, distinct(d), hook=HOOK)]
    # make M2 entries cover the hook as M0 does, so the guard holds
    for r in rows:
        r["text"] += " " + " ".join(sorted(set(sim.content_tokens(HOOK))))
    result = ana.analyse(rows, draws=200)
    assert result["readings"]["raw_history_helps"] is True
    assert result["readings"]["raw_history_hurts"] is False
    assert result["readings"]["nothing_moves"] is False
    assert result["readings"]["traces_beat_entries"] is None          # arms M3a and M2 not both present


def test_a_repetition_win_is_voided_when_the_entry_drifts_off_topic() -> None:
    rows = []
    for d in range(1, 13):
        rows += [row("M0", d, SAME + " " + " ".join(sorted(set(sim.content_tokens(HOOK))))), row("M2", d, distinct(d))]
    result = ana.analyse(rows, draws=200)
    assert result["arm_means"]["M2"]["hook_coverage"] < result["arm_means"]["M0"]["hook_coverage"] - ana.GUARD
    assert result["readings"]["raw_history_helps"] is False


def test_raw_history_that_repeats_more_is_read_as_hurting() -> None:
    rows = []
    for d in range(1, 13):
        rows += [row("M0", d, distinct(d)), row("M2", d, SAME)]
    assert ana.analyse(rows, draws=200)["readings"]["raw_history_hurts"] is True


def test_command_line_writes_json_and_markdown_and_rejects_missing_input(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    records = tmp_path / "records.jsonl"
    records.write_text("\n".join(json.dumps(r) for d in range(1, 10) for r in (row("M0", d, SAME), row("M2", d, distinct(d)))) + "\n",
                       encoding="utf-8")
    assert ana.main([str(records), "--json", str(tmp_path / "r.json"), "--md", str(tmp_path / "r.md")]) == 0
    capsys.readouterr()
    data = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert data["arms"] == ["M0", "M2"] and "provenance" in data and data["provenance"]["bootstrap"]["draws"] == ana.DRAWS
    assert "# AAM-E1-SIM results" in (tmp_path / "r.md").read_text(encoding="utf-8")
    assert ana.main([str(tmp_path / "missing.jsonl")]) == 2
    assert "input error" in capsys.readouterr().err
