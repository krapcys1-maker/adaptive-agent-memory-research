"""The November 2026 side-run documents and their per-game tables.

Documents: docs/11-research-laboratory/errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md,
.../errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md, .../side-studies-2026-11.md and
.../evidence-summary-2026-11.md. Tables: data/lab/side-runs-2026-11/*.csv (unit, arm, seed, solved).

This test recomputes the solve-rate numbers the documents print from the published tables and the packages'
per_unit.csv, checks the tables' SHA-256 against their README, checks that every unit id is a published game, and checks
the labels and cross-links. Numbers that need the private logs (steps, sources, costs) are not checked here; the
documents say so."""

from __future__ import annotations

import csv
import hashlib
import math
import re
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"
RUNS = LAB / "side-runs-2026-11"
DOCS = ROOT / "docs" / "11-research-laboratory"
V6A = DOCS / "errata" / "2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md"
V5BA = DOCS / "errata" / "2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md"
SIDE = DOCS / "side-studies-2026-11.md"
SUMMARY = DOCS / "evidence-summary-2026-11.md"
TRANSFORM = ("pick_clean", "pick_cool", "pick_heat")


def _text(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def _package(name: str) -> dict:
    out: dict = {}
    with (LAB / name / "per_unit.csv").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["seed"] == "0":
                out[(r["unit"], r["arm"])] = int(r["solved"])
    return out


def _table(name: str, drop_excluded: bool = False) -> dict:
    out: dict = {}
    with (RUNS / name).open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if drop_excluded and r.get("excluded_by_length_rule") == "1":
                continue
            out[(r["unit"], r["arm"])] = int(r["solved"])
    return out


def _kind(unit: str) -> str:
    return unit.split("~", 1)[1].split("/")[1]


def _units(sol: dict, part: str = "all") -> list:
    us = sorted({u for u, _ in sol})
    if part == "transform":
        return [u for u in us if _kind(u).startswith(TRANSFORM)]
    if part == "other":
        return [u for u in us if not _kind(u).startswith(TRANSFORM)]
    return us


def _pair(sol: dict, us: list, a: str, b: str):
    us = [u for u in us if (u, a) in sol and (u, b) in sol]
    g = sum(1 for u in us if sol[(u, a)] and not sol[(u, b)])
    l = sum(1 for u in us if sol[(u, b)] and not sol[(u, a)])
    n = g + l
    p = min(1.0, 2 * sum(comb(n, i) for i in range(min(g, l) + 1)) / 2 ** n) if n else 1.0
    return len(us), g, l, round((g - l) / len(us), 3), p


def _fmt(x: float) -> str:
    return f"{x:+.3f}".replace("-", "−")


def test_tables_match_their_readme_and_use_only_published_games():
    readme = (RUNS / "README.md").read_text(encoding="utf-8")
    published = {u for name in ("autolab-alfworld-ladder-r4-v6", "autolab-alfworld-ladder-r4-v5b") for u, _ in _package(name)}
    tables = sorted(RUNS.glob("*.csv"))
    assert len(tables) == 10
    for path in tables:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert re.search(rf"`{re.escape(path.name)}` \|.*`{digest}`", readme), path.name
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows and set(rows[0]) >= {"unit", "arm", "seed", "solved"}
        assert {r["unit"] for r in rows} <= published, path.name
        assert not any(k in rows[0] for k in ("actions", "evidence", "memory_sources")), path.name


def test_v6_seed1_rows_two_seed_estimate_and_per_type_table():
    s0, s1 = _package("autolab-alfworld-ladder-r4-v6"), _table("v6-seed1.csv")
    text = _text(V6A)
    expected = {"all": ((300, 72, 33), (300, 78, 31)), "transform": ((151, 50, 13), (151, 53, 12)),
                "other": ((149, 22, 20), (149, 25, 19))}
    for part, (e0, e1) in expected.items():
        assert _pair(s0, _units(s1, part), "retrieved_task", "placebo")[:3] == e0, part
        assert _pair(s1, _units(s1, part), "retrieved_task", "placebo")[:3] == e1, part
    for part, (diff, lo, hi) in {"all": (0.143, 0.090, 0.196), "transform": (0.258, 0.180, 0.337),
                                 "other": (0.027, -0.040, 0.094)}.items():
        us = _units(s1, part)
        d = [((s0[(u, "retrieved_task")] + s1[(u, "retrieved_task")]) - (s0[(u, "placebo")] + s1[(u, "placebo")])) / 2 for u in us]
        m = sum(d) / len(d)
        sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1))
        half = 1.97 * sd / math.sqrt(len(d))  # the t quantile for 148 to 299 degrees of freedom is 1.968 to 1.976
        assert round(m, 3) == diff and abs(m - half - lo) < 0.002 and abs(m + half - hi) < 0.002, part
        assert f"{_fmt(diff)} | [{_fmt(lo)}, {_fmt(hi)}]" in text, part
    for kind, (n0, n1) in {"pick_clean": (12, 12), "pick_cool": (15, 24), "pick_heat": (10, 5), "look_at": (7, 4),
                           "pick_and_place": (0, 2), "pick_two": (-5, 0)}.items():
        us = [u for u in _units(s1) if _kind(u).startswith(kind)]
        net0 = sum(s0[(u, "retrieved_task")] - s0[(u, "placebo")] for u in us)
        net1 = sum(s1[(u, "retrieved_task")] - s1[(u, "placebo")] for u in us)
        assert (net0, net1) == (n0, n1), kind
        assert f"| `{kind}` | {len(us)} | {n0} | {n1} |".replace("| -", "| −") in V6A.read_text(encoding="utf-8")


def test_d8_rows_and_the_filler_comparison():
    s0 = _package("autolab-alfworld-ladder-r4-v6")
    sol = dict(s0)
    sol.update(_table("d8-v6.csv"))
    text = _text(V6A)
    assert _pair(sol, _units(s0, "transform"), "d8_instruction", "none")[:4] == (151, 29, 19, 0.066)
    assert _pair(sol, _units(s0, "transform"), "retrieved_task", "d8_instruction")[:4] == (151, 40, 17, 0.152)
    assert _pair(sol, _units(s0, "other"), "d8_instruction", "none")[:4] == (149, 13, 29, -0.107)
    n, g, l, d, p = _pair(s0, _units(s0, "other"), "placebo", "none")
    assert (n, g, l, d, round(p, 3)) == (149, 12, 25, -0.087, 0.047)
    assert _pair(sol, _units(s0, "other"), "d8_instruction", "placebo")[:4] == (149, 16, 19, -0.02)
    for needle in ("−0.087 (12 / 25, p = 0.047)", "−0.020 (16 / 19, p = 0.74)", "The result shows no harm specific to the sentence"):
        assert needle in text, needle
    pilot = _package("autolab-alfworld-ladder-r4-v5b")
    pilot.update(_table("d8-v5b-pilot.csv"))
    assert _pair(pilot, _units(_table("d8-v5b-pilot.csv")), "d8_instruction", "none")[:4] == (114, 25, 9, 0.14)


def test_v5b_seed1_rows():
    s0, s1 = _package("autolab-alfworld-ladder-r4-v5b"), _table("v5b-seed1.csv")
    text = V5BA.read_text(encoding="utf-8")
    for part, n, (g0, l0), (g1, l1) in (("all", 201, (48, 26), (55, 20)), ("transform", 114, (36, 13), (36, 12)),
                                        ("other", 87, (12, 13), (19, 8))):
        us = _units(s1, part)
        assert _pair(s0, us, "retrieved_task", "none")[:3] == (n, g0, l0), part
        assert _pair(s1, us, "retrieved_task", "none")[:3] == (n, g1, l1), part
        for seed, (g, l), sol in ((0, (g0, l0), s0), (1, (g1, l1), s1)):
            none = sum(sol[(u, "none")] for u in us) / n
            task = sum(sol[(u, "retrieved_task")] for u in us) / n
            row = f"| {n} | {seed} | {none:.3f} | {task:.3f} | {_fmt((g - l) / n)} | {g} / {l} |"
            assert row in text, row


def test_side_study_headlines():
    h1 = _table("ds-hard-1.csv")
    h1q2 = _table("ds-hard-1.csv", drop_excluded=True)
    us = _units(h1)
    assert _pair(h1, us, "retrieved_task", "placebo")[:4] == (193, 43, 1, 0.218)
    assert _pair(h1q2, us, "retrieved_task", "mismatched_type")[:4] == (189, 32, 2, 0.159)
    assert _pair(h1q2, us, "mismatched_type", "none")[:4] == (189, 21, 9, 0.063)
    h2 = _table("ds-hard-2.csv")
    us2 = _units(h2)
    assert _pair(h2, us2, "retrieved_plan", "placebo")[:4] == (100, 15, 2, 0.13)
    assert _pair(h2, us2, "retrieved_steps", "placebo")[:4] == (100, 18, 3, 0.15)
    assert _pair(h2, us2, "retrieved_plan", "retrieved_steps")[:4] == (100, 3, 5, -0.02)
    assert _pair(h2, us2, "retrieved_plan", "retrieved_task")[:3] == (100, 1, 7)
    nf = _table("nemo-floor.csv")
    assert _pair(nf, _units(nf), "retrieved_task", "placebo")[:4] == (100, 20, 0, 0.2)
    assert [sum(v for (u, a), v in nf.items() if a == arm) for arm in ("none", "placebo", "retrieved_task")] == [1, 2, 22]
    for name, none, task in (("ds-pilot-normal.csv", 17, 20), ("ds-pilot-hard.csv", 13, 18)):
        t = _table(name)
        solved = {arm: sum(v for (u, a), v in t.items() if a == arm) for arm in ("none", "retrieved_task")}
        assert (solved["none"], solved["retrieved_task"]) == (none, task)
    text = _text(SIDE)
    for needle in ("43 / 1", "32 / 2", "15 / 2", "18 / 3", "20 / 0", "17 / 20", "13 / 20"):
        assert needle in text, needle


def test_labels_and_links():
    add, v5, side, summary = (p.read_text(encoding="utf-8") for p in (V6A, V5BA, SIDE, SUMMARY))
    flat = re.sub(r"\s+", " ", add)
    assert "exploratory side runs outside the lab pipeline" in flat
    assert "It is not an independent replication" in flat
    for text in (add, v5, side, summary):
        assert "pre-registered" not in text
        assert "side-runs-2026-11" in text
    for link in ("errata/2026-11-23-alfworld-ladder-r4-v5b-seed1-addendum.md", "side-studies-2026-11.md",
                 "errata/2026-11-23-alfworld-ladder-r4-v6-seed1-and-d8-addendum.md"):
        assert link in summary, link
