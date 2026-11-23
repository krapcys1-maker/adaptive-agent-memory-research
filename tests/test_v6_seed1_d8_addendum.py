"""The November addenda (docs/11-research-laboratory/errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md,
2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md), the side-studies note and the evidence summary
(docs/11-research-laboratory/side-studies-2026-11.md, evidence-summary-2026-11.md) quote seed-0 numbers of V6 and V5B
next to runs whose per-episode outputs are not published. This test recomputes every number that comes from a published
per_unit.csv and checks that the documents print it. The seed-1, D8 and side-study numbers themselves cannot be
recomputed from this repository (the documents say so and give the SHA-256 of their sources)."""

from __future__ import annotations

import csv
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
ADDENDUM = ROOT / "docs" / "11-research-laboratory" / "errata" / "2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md"
SIDE = ROOT / "docs" / "11-research-laboratory" / "side-studies-2026-11.md"
V5B_ADDENDUM = ROOT / "docs" / "11-research-laboratory" / "errata" / "2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md"
SUMMARY = ROOT / "docs" / "11-research-laboratory" / "evidence-summary-2026-11.md"
TRANSFORM = ("pick_clean", "pick_cool", "pick_heat")


def _solved(package: str) -> dict:
    games: dict = {}
    with (LAB / package / "per_unit.csv").open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            if row["seed"] == "0":
                games.setdefault(row["unit"], {})[row["arm"]] = int(row["solved"])
    return games


def _ttype(unit: str) -> str:
    return unit.split("~", 1)[1].split("/")[1]


def _split(games: dict, part: str) -> dict:
    if part == "all":
        return games
    keep = (lambda u: _ttype(u).startswith(TRANSFORM)) if part == "transform" else (lambda u: not _ttype(u).startswith(TRANSFORM))
    return {u: a for u, a in games.items() if keep(u)}


def _pair(games: dict, a: str, b: str):
    gains = sum(g[a] == 1 and g[b] == 0 for g in games.values())
    losses = sum(g[a] == 0 and g[b] == 1 for g in games.values())
    n = gains + losses
    p = min(1.0, 2 * sum(comb(n, i) for i in range(min(gains, losses) + 1)) / 2 ** n)
    return len(games), gains, losses, (gains - losses) / len(games), p


def _rate(games: dict, arm: str) -> float:
    return sum(g[arm] for g in games.values()) / len(games)


def test_v6_seed0_rows_of_the_addendum():
    games = _solved("autolab-alfworld-ladder-r4-v6")
    expected = {"all": (300, 0.477, 0.607, 72, 33, "0.0002", "{:.4f}"),
                "transform": (151, 0.404, 0.649, 50, 13, "3.0e-06", "{:.1e}"),
                "other": (149, 0.550, 0.564, 22, 20, "0.88", "{:.2f}")}
    text = ADDENDUM.read_text(encoding="utf-8")
    for part, (n, placebo, task, gains, losses, p_text, p_format) in expected.items():
        sub = _split(games, part)
        got_n, g, l, _diff, p = _pair(sub, "retrieved_task", "placebo")
        assert (got_n, g, l) == (n, gains, losses), part
        assert (round(_rate(sub, "placebo"), 3), round(_rate(sub, "retrieved_task"), 3)) == (placebo, task), part
        assert p_format.format(p) == p_text, part
        row = f"| {n} | 0 | {placebo:.3f} | {task:.3f} | {(gains - losses) / n:+.3f} | {gains} / {losses} | {p_text} |"
        assert row in text, row


def test_v6_seed0_arms_used_by_the_d8_comparison():
    games = _solved("autolab-alfworld-ladder-r4-v6")
    text = ADDENDUM.read_text(encoding="utf-8")
    for part, none, task in (("transform", 0.430, 0.649), ("other", 0.638, 0.564)):
        sub = _split(games, part)
        assert (round(_rate(sub, "none"), 3), round(_rate(sub, "retrieved_task"), 3)) == (none, task)
        assert f"| {none:.3f} | {task:.3f} |" in text
    other = _split(games, "other")
    assert round(_pair(other, "retrieved_task", "none")[3], 3) == -0.074
    assert "is −0.074" in text


def test_v5b_transform_rates_of_the_first_d8_pilot():
    games = _split(_solved("autolab-alfworld-ladder-r4-v5b"), "transform")
    assert len(games) == 114
    assert sum(g["none"] for g in games.values()) == 44 and sum(g["retrieved_task"] for g in games.values()) == 67


def test_v6_net_gain_by_type_quoted_in_the_side_note():
    games = _solved("autolab-alfworld-ladder-r4-v6")
    net = {}
    for unit, arms in games.items():
        kind = next((t for t in TRANSFORM if _ttype(unit).startswith(t)), "other")
        net[kind] = net.get(kind, 0) + arms["retrieved_task"] - arms["placebo"]
    assert sum(net.values()) == 39
    assert net["pick_clean"] + net["pick_cool"] == 27 and net["pick_heat"] == 10
    assert "10 of its net 39 in heat (26%) and 27 in clean and cool" in SIDE.read_text(encoding="utf-8")
    assert "27 of its net 39 in clean and cool, 10 in heat" in SUMMARY.read_text(encoding="utf-8")


def test_v6_pick_two_and_d8_memory_gain():
    games = _solved("autolab-alfworld-ladder-r4-v6")
    pick_two = sum(a["retrieved_task"] - a["placebo"] for u, a in games.items() if _ttype(u).startswith("pick_two"))
    assert pick_two == -5 and "−5 at seed 0" in SUMMARY.read_text(encoding="utf-8")
    n, gains, losses, diff, _p = _pair(_split(games, "transform"), "retrieved_task", "none")
    assert (n, gains, losses, round(diff, 3)) == (151, 44, 11, 0.219)
    assert "+0.219, 44 / 11" in ADDENDUM.read_text(encoding="utf-8")


def test_v5b_seed0_rows_of_the_v5b_addendum():
    games = _solved("autolab-alfworld-ladder-r4-v5b")
    text = V5B_ADDENDUM.read_text(encoding="utf-8")
    for part, n, none, task, gains, losses in (("all", 201, 0.507, 0.617, 48, 26), ("transform", 114, 0.386, 0.588, 36, 13),
                                                ("other", 87, 0.667, 0.655, 12, 13)):
        sub = _split(games, part)
        got = _pair(sub, "retrieved_task", "none")
        assert got[:3] == (n, gains, losses), part
        assert (round(_rate(sub, "none"), 3), round(_rate(sub, "retrieved_task"), 3)) == (none, task), part
        row = f"| {n} | 0 | {none:.3f} | {task:.3f} | {(gains - losses) / n:+.3f} | {gains} / {losses} |".replace("-0.011", "−0.011")
        assert row in text, row


def test_both_documents_label_the_runs_as_exploratory_and_link_each_other():
    add, side = ADDENDUM.read_text(encoding="utf-8"), SIDE.read_text(encoding="utf-8")
    assert "exploratory side runs outside the lab pipeline" in add.replace("\n", " ")
    assert "It is not an independent replication" in add.replace("\n", " ")
    assert "exploratory side studies" in side
    assert "../side-studies-2026-11.md" in add and "errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md" in side
    summary = SUMMARY.read_text(encoding="utf-8")
    for link in ("errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md", "side-studies-2026-11.md",
                 "errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md"):
        assert link in summary, link
    for text in (side, summary, V5B_ADDENDUM.read_text(encoding="utf-8")):
        assert "pre-registered" not in text
