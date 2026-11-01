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


# ---- added after the independent review: the tests below pin what the first suite left free (31 of 35 mutants survived) --------------------------

import copy  # noqa: E402

CONFIG = json.loads((ROOT / "data" / "lab" / "aam-f1-engagement-signal" / "config.json").read_text(encoding="utf-8"))


def test_the_constants_are_the_preregistered_ones() -> None:
    p = CONFIG["parameters"]
    assert (es.SEED, es.RECENT, es.MIN_KNOWN, es.START, es.RIDGE, es.SHRINK, es.PLANTED) == (
        p["seed"], p["recent_baseline_notes"], p["min_known_notes"], p["history_only_notes"], p["ridge"], p["type_shrinkage"], p["planted_factor"])
    assert es.BLOCK == 5 and es.POOL == 100 and es.SKILL_NEEDED == 0.05 and es.LAG.total_seconds() == 72 * 3600
    assert list(es.EARLY_HOURS) == p["early_hours"] and list(es.PER_ARM) == p["power"]["per_arm"] and list(es.EFFECTS) == p["power"]["relative_increase"]


def test_the_golden_numbers_of_the_rolling_origin_and_the_other_measures_on_a_fixed_table() -> None:
    table = es.note_table(make_rows(240, seed=1, category_factor=2.0))
    views, likes = es.evaluate(table, "V", 50, 1), es.evaluate(table, "L", 50, 1)
    assert views["n_eval"] == likes["n_eval"] == 180
    assert views["mse_recent"] == pytest.approx(0.4068, abs=5e-4) and likes["mse_recent"] == pytest.approx(0.5562, abs=5e-4)
    assert {k: v["value"] for k, v in views["skill"].items()} == pytest.approx({"global_mean": -0.1543, "typ": 0.2923, "full": 0.25}, abs=5e-4)
    assert {k: v["value"] for k, v in likes["skill"].items()} == pytest.approx({"global_mean": -0.0198, "typ": 0.1544, "full": 0.1119}, abs=5e-4)
    assert es.dispersion(table, 200, 1)["D"] == pytest.approx(1.02, abs=5e-3)
    assert es.early_vs_final(table)["24"] == {"notes": 240, "views_rho": pytest.approx(0.9999, abs=1e-4), "likes_rho": pytest.approx(0.9445, abs=1e-4)}
    assert es.notes_per_day(table) == 3.0 and es.resolution(table)["share_likes_ge_1"] == pytest.approx(0.9542, abs=1e-4)


def test_a_prediction_never_uses_an_outcome_that_is_not_yet_72_hours_old(monkeypatch: pytest.MonkeyPatch) -> None:
    rows, j = make_rows(240, seed=1), 120
    changed = [dict(r) for r in rows]
    changed[j]["pomiar_72h"] = dict(rows[j]["pomiar_72h"], wyswietlenia=rows[j]["pomiar_72h"]["wyswietlenia"] + 5000)
    a, b = es.note_table(rows), es.note_table(changed)
    monkeypatch.setattr(es, "START", j + 1)
    inside_a, inside_b = es.evaluate(a[: j + 9], "V", 30, 1), es.evaluate(b[: j + 9], "V", 30, 1)      # notes j+1 .. j+8 are less than 72 hours after note j
    assert inside_a["n_eval"] == 8 and inside_a["mse_recent"] == inside_b["mse_recent"] and inside_a["skill"] == inside_b["skill"]
    after_a, after_b = es.evaluate(a[: j + 10], "V", 30, 1), es.evaluate(b[: j + 10], "V", 30, 1)      # note j+9 is exactly 72 hours later: now it is known
    assert after_a["n_eval"] == 9 and after_a["mse_recent"] != after_b["mse_recent"]


def passing_result() -> dict:
    power = {"%g:%d" % (d, m): (0.05 if d == 0 else 0.9) for d in (0.0,) + es.EFFECTS for m in es.PER_ARM}
    skill = lambda: {"skill": {"typ": {"value": 0.06, "ci95": [0.01, 0.1]}, "full": {"value": 0.06, "ci95": [0.01, 0.1]}}}   # noqa: E731  (a fresh dict for every use)
    return {"resolution": {"share_likes_ge_1": 0.5}, "dispersion": {"D": 1.5, "p_mc": 0.0099}, "early": {"24": {"notes": 30, "views_rho": 0.9, "likes_rho": 0.8}},
            "skill": {"views": skill(), "likes": skill()}, "planted": {"views": skill(), "likes": skill()}, "power": {"views": dict(power), "likes": dict(power)}}


def test_every_reading_applies_its_threshold_at_the_boundary() -> None:
    read = es.readings(passing_result())
    assert read["likes_usable_per_note"] and read["like_rate_varies_beyond_chance"] and read["early_24h_stands_in"] == {"views": True, "likes": True}
    assert read["features_carry_signal"] == {"views": {"typ": True, "full": True}, "likes": {"typ": True, "full": True}}
    assert read["instrument_detects_planted_effect"] == {"views": True, "likes": True} and read["per_arm_for_80_percent_power"]["views"] == {"0.25": 20, "0.5": 20, "1": 20}

    def changed(path: tuple, value) -> dict:
        result = passing_result()
        node = result
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return es.readings(result)

    assert changed(("resolution", "share_likes_ge_1"), 0.499)["likes_usable_per_note"] is False
    assert changed(("dispersion", "D"), 1.49)["like_rate_varies_beyond_chance"] is False and changed(("dispersion", "p_mc"), 0.01)["like_rate_varies_beyond_chance"] is False
    assert changed(("early", "24", "notes"), 29)["early_24h_stands_in"] == {"views": False, "likes": False}
    assert changed(("early", "24", "views_rho"), 0.899)["early_24h_stands_in"] == {"views": False, "likes": True}
    assert changed(("early", "24", "likes_rho"), 0.799)["early_24h_stands_in"] == {"views": True, "likes": False}
    low, outside = {"value": 0.0499, "ci95": [0.01, 0.1]}, {"value": 0.06, "ci95": [0.0, 0.1]}
    assert changed(("skill", "views", "skill", "typ"), low)["features_carry_signal"]["views"]["typ"] is False
    assert changed(("skill", "likes", "skill", "full"), outside)["features_carry_signal"]["likes"]["full"] is False
    assert changed(("planted", "views", "skill", "typ"), low)["instrument_detects_planted_effect"]["views"] is False
    slow = {"%g:%d" % (d, m): (0.05 if d == 0 else (0.79 if m < 80 else 0.81)) for d in (0.0,) + es.EFFECTS for m in es.PER_ARM}
    assert changed(("power", "likes"), slow)["per_arm_for_80_percent_power"]["likes"] == {"0.25": 80, "0.5": 80, "1": 80}
    assert es.carries_signal({"value": 0.05, "ci95": [0.001, 0.2]}) and not es.carries_signal({"value": 0.05, "ci95": [-0.001, 0.2]})


def test_resolution_and_cadence_are_computed_from_hand_made_rows() -> None:
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    rows = [{"kiedy": (start + timedelta(days=d)).isoformat(), "typ": "A", "slow": 50, "pomiar_72h": {"wyswietlenia": 10, "polubienia": likes, "odpowiedzi": replies, "restacki": 0, "interakcje_razem": likes}}
            for d, (likes, replies) in enumerate([(0, 0), (1, 0), (2, 1), (0, 0)] * 15)]
    table = es.note_table(rows)
    res = es.resolution(table)
    assert len(table) == 60 and res["share_likes_ge_1"] == 0.5 and res["share_replies_ge_1"] == 0.25 and res["share_restacks_ge_1"] == 0.0 and res["likes_q25_50_75"][:2] == [0.0, 0.5]
    assert es.notes_per_day(table) == pytest.approx(1.0, abs=0.04)             # one note a day: 30 notes inside the last 30 days, divided by 30
