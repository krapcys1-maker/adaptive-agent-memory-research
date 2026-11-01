"""engagement_signal.py: resolution, dispersion against binomial noise, rolling-origin skill with a planted control, early readings and power.

Everything is synthetic; no account data is involved.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import engagement_signal as es  # noqa: E402

SECRET = "SENTINEL-TEXT-THAT-MUST-NEVER-BE-PRINTED"


def make_rows(n: int = 240, seed: int = 1, category_factor: float = 1.0, rate_spread: float = 0.0) -> list:
    """Three notes a day; views lognormal around a slow trend; likes binomial in views at a constant rate, or at a note-specific one."""
    rng = np.random.default_rng(seed)
    start = datetime(2026, 8, 16, 6, tzinfo=timezone.utc)
    rows = []
    for i in range(n):
        typ = str(rng.choice(["A", "B", "C"]))
        views = int(np.exp(rng.normal(4.0 + 0.004 * i, 0.5)) * (category_factor if typ == "A" else 1.0))
        rate = 0.04 if rate_spread == 0 else float(rng.beta(0.04 / rate_spread, 0.96 / rate_spread))
        likes = int(rng.binomial(views, rate))
        series = [[h, int(views * min(1.0, (h / 72) ** 0.5)), int(likes * min(1.0, h / 72)), 0, 0, None, 0] for h in (3, 9, 20, 25, 48, 72)]
        rows.append({"kiedy": (start + timedelta(hours=8 * i)).isoformat(), "typ": typ, "format": "zwykla", "forma": "x", "konczy_pytaniem": bool(i % 7 == 0),
                     "slow": 40 + int(rng.integers(0, 60)), "model": "m1", "text": SECRET,
                     "pomiar_72h": {"wyswietlenia": views, "polubienia": likes, "odpowiedzi": 0, "restacki": 0, "interakcje_razem": likes},
                     "seria_h_wysw_lajk_odp_restack_odw_subskr": series})
    return rows


def test_the_table_keeps_notes_with_a_72h_measurement_in_time_order() -> None:
    rows = make_rows(30)
    rows[3]["pomiar_72h"] = None
    rows.reverse()
    table = es.note_table(rows)
    assert len(table) == 29 and [r["t"] for r in table] == sorted(r["t"] for r in table)
    res = es.resolution(table)
    assert res["notes"] == 29 and 0.0 <= res["share_likes_ge_1"] <= 1.0 and len(res["views_q25_50_75"]) == 3


def test_dispersion_is_near_one_for_a_constant_like_rate_and_large_when_the_rate_varies() -> None:
    constant = es.dispersion(es.note_table(make_rows()), 2000, 1)
    varying = es.dispersion(es.note_table(make_rows(rate_spread=0.05)), 2000, 1)
    assert constant["p_mc"] > 0.01 and 0.7 < constant["D"] < 1.4 and constant["null_95"][0] < 1 < constant["null_95"][1]
    assert varying["p_mc"] < 0.01 and varying["D"] > 1.5
    assert es.dispersion(es.note_table(make_rows(12))[:5], 100, 1) is None


def test_the_skill_finds_a_planted_category_effect_and_not_a_null() -> None:
    table = es.note_table(make_rows(category_factor=2.0))
    effect = es.evaluate(table, "V", 300, 1)["skill"]
    assert es.carries_signal(effect["typ"]) and es.carries_signal(effect["full"]) and effect["typ"]["ci95"][0] > 0
    null = es.note_table(make_rows())
    skill = es.evaluate(null, "V", 300, 1)["skill"]
    assert not es.carries_signal(skill["typ"]) and not es.carries_signal(skill["full"])
    control = es.planted_control(null, "V", 300, 1)
    assert control["factor"] == es.PLANTED and control["category"] in {"A", "B", "C"} and es.carries_signal(control["skill"]["typ"])


def test_a_reading_near_24_hours_ranks_notes_like_the_final_one() -> None:
    early = es.early_vs_final(es.note_table(make_rows()))
    assert early["24"]["notes"] > 100 and early["24"]["views_rho"] > 0.9 and early["24"]["likes_rho"] > 0.5
    assert early["6"]["notes"] > 100 and set(early) == {"6", "12", "24", "48"}


def test_power_grows_with_the_sample_and_the_effect_and_the_false_positive_rate_is_near_nominal() -> None:
    table = es.note_table(make_rows())
    p = es.power(table, "V", 150, 1)
    assert p["0.5:160"] >= p["0.5:20"] and p["1:160"] >= p["0.25:160"] and p["1:160"] > 0.9
    assert all(0.0 <= p["0:%d" % m] <= 0.15 for m in es.PER_ARM)
    assert es.smallest_per_arm(p, 1.0) in es.PER_ARM and es.smallest_per_arm({"%g:%d" % (d, m): 0.0 for d in es.EFFECTS for m in es.PER_ARM}, 0.5) is None


def test_replies_count_only_after_72_hours() -> None:
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    rows = [{"kiedy": (base + timedelta(hours=i)).isoformat(), "ostatni_pomiar": {"wyswietlenia": 10, "polubienia": 1, "kiedy": (base + timedelta(hours=i + (80 if i % 2 else 10))).isoformat()}}
            for i in range(20)]
    assert len(es.reply_table(rows)) == 10


def test_the_command_line_writes_only_aggregates(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    notes = tmp_path / "notes.jsonl"
    notes.write_text("\n".join(json.dumps(r) for r in make_rows()) + "\n", encoding="utf-8")
    out = tmp_path / "out.json"
    assert es.main(["--notes", str(notes), "--json", str(out), "--draws", "100", "--sims", "40"]) == 0
    printed = capsys.readouterr().out
    data = json.loads(out.read_text(encoding="utf-8"))
    assert SECRET not in printed and SECRET not in out.read_text(encoding="utf-8")
    assert {"resolution", "dispersion", "skill", "planted", "early", "power", "readings", "notes_per_day_last_30_days"} <= set(data)
    assert data["notes"] == 240 and set(data["readings"]["features_carry_signal"]) == {"views", "likes"}
