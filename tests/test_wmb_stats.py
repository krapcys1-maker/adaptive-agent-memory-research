"""wmb.stats and wmb.power_tables: intervals, exact tests, minimum detectable effects, agreement and the printed tables."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wmb import power_tables, stats  # noqa: E402


def test_intervals_match_known_values() -> None:
    lo, hi = stats.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-3) and stats.wilson(12, 24) == pytest.approx((0.314, 0.686), abs=1e-3) and stats.wilson(0, 0) == (0.0, 1.0)
    assert stats.clopper_pearson(0, 10) == pytest.approx((0.0, 0.3085), abs=1e-3) and stats.clopper_pearson(5, 10) == pytest.approx((0.187, 0.813), abs=1e-3)
    assert stats.clopper_pearson(10, 10)[1] == 1.0


def test_zero_failures_bound_a_rate_by_about_three_over_n() -> None:
    assert stats.zero_failure_upper_bound(24) == pytest.approx(0.1173, abs=1e-3) and stats.zero_failure_upper_bound(300) == pytest.approx(0.0099, abs=1e-4)
    assert stats.zero_failure_upper_bound(300) < stats.zero_failure_upper_bound(100) < stats.zero_failure_upper_bound(24)


def test_the_sign_test_is_exact_and_ties_are_the_callers_business() -> None:
    assert stats.sign_test_p(10, 0) == pytest.approx(2 * 0.5 ** 10) and stats.sign_test_p(5, 5) == 1.0 and stats.sign_test_p(0, 0) == 1.0
    assert stats.sign_test_p(3, 12) == stats.sign_test_p(12, 3) and stats.sign_test_p(3, 12) < 0.05


def test_minimum_detectable_win_rates_fall_with_the_number_of_decisive_tasks() -> None:
    values = [stats.mde_win_rate(n) for n in (43, 100, 160, 214, 300, 480)]
    assert values[0] == pytest.approx(0.72, abs=5e-3) and values[3] == pytest.approx(0.60, abs=5e-3)
    assert all(a > b for a, b in zip(values, values[1:])) and stats.mde_win_rate(4) is None
    assert stats.sign_test_power(100, 0.5) <= 0.05 and stats.sign_test_power(100, stats.mde_win_rate(100)) >= 0.8 - 1e-3


def test_agreement_statistics_on_hand_computed_cases() -> None:
    assert stats.cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0 and stats.cohen_kappa([1, 1, 0, 0], [1, 0, 0, 0]) == pytest.approx(0.5)
    assert stats.krippendorff_alpha_nominal([[0, 0], [1, 1]]) == 1.0 and stats.krippendorff_alpha_nominal([[0, 1], [0, 1]]) == pytest.approx(-0.5)
    assert stats.krippendorff_alpha_nominal([[0, 0], [1, 1], [0, 1]]) == pytest.approx(0.4444, abs=1e-3)


def test_gap_closed_bootstrap_and_normal_approximation() -> None:
    assert stats.gap_closed(0.8, 0.2, 0.9) == pytest.approx(0.857, abs=1e-3) and stats.gap_closed(0.5, 0.9, 0.9) is None
    assert stats.paired_bootstrap_ci([0.1] * 200) == pytest.approx((0.1, 0.1)) and stats.paired_bootstrap_ci([0.0, 1.0] * 100, draws=500) == stats.paired_bootstrap_ci([0.0, 1.0] * 100, draws=500)
    assert stats.minimum_detectable_difference(1.0, 100) == pytest.approx(0.2802, abs=1e-3)


def test_the_printed_tables_match_the_specification(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    out = tmp_path / "t.json"
    assert power_tables.main(["--json", str(out)]) == 0
    capsys.readouterr()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["mde_win_rate_two_sided_5pct_power_80"]["43"] == pytest.approx(0.72, abs=5e-3) and data["zero_failures_upper_bound_95_one_sided"]["300"] == pytest.approx(0.0099, abs=1e-4)
