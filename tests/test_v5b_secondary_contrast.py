"""The V5B addendum (docs/11-research-laboratory/errata/2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md)
states the secondary contrast retrieved_task - mismatched_type. This test recomputes it from the published per_unit.csv
with the verifier's own statistics (paired_ci, interval_state) and pins the numbers the addendum prints."""

from __future__ import annotations

import csv
import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data" / "lab" / "autolab-alfworld-ladder-r4-v5b"
ADDENDUM = ROOT / "docs" / "11-research-laboratory" / "errata" / "2026-11-19-alfworld-ladder-r4-v5b-secondary-contrast.md"
Z_RESULT = 2.7777  # the z of the published V5B intervals (sequential threshold of the second look)
SESOI = 0.12


def _verifier():
    spec = importlib.util.spec_from_file_location("verify_autolab_packages", ROOT / "scripts" / "verify_autolab_packages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _solved() -> dict:
    games: dict = defaultdict(dict)
    with (PACKAGE / "per_unit.csv").open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            games[row["unit"]][row["arm"]] = int(row["solved"])
    return games


def _contrast(games: dict, a: str, b: str, z: float):
    v = _verifier()
    gains = sum(g[a] == 1 and g[b] == 0 for g in games.values())
    losses = sum(g[a] == 0 and g[b] == 1 for g in games.values())
    n = len(games)
    lo, hi = v.paired_ci(gains, losses, n, z)
    return n, gains, losses, (gains - losses) / n, lo, hi, v.interval_state(lo, hi, SESOI)


def test_secondary_contrast_numbers():
    games = _solved()
    n, gains, losses, diff, lo, hi, state = _contrast(games, "retrieved_task", "mismatched_type", Z_RESULT)
    assert (n, gains, losses) == (201, 55, 24)
    assert round(diff, 3) == 0.154
    assert (round(lo, 3), round(hi, 3)) == (0.035, 0.273)
    assert state == "positive"


def test_same_method_reproduces_published_primary_contrasts():
    games = _solved()
    for arm, (g, l, lo, hi) in {"retrieved_task": (55, 21, 0.053, 0.285), "mismatched_type": (19, 16, -0.067, 0.097)}.items():
        n, gains, losses, _diff, c_lo, c_hi, _state = _contrast(games, arm, "placebo", Z_RESULT)
        assert (n, gains, losses) == (201, g, l)
        assert (round(c_lo, 3), round(c_hi, 3)) == (lo, hi)


def test_addendum_prints_the_same_numbers():
    text = ADDENDUM.read_text(encoding="utf-8")
    for needle in ("55 / 24", "+0.154", "[+0.035, +0.273]", "[+0.058, +0.250]", "[+0.070, +0.238]", "46 of 402", "131 of 402",
                   "secondary", "post-hoc"):
        assert needle in text, needle
