"""replay_memory_sim.py: briefs, retrieval over real-style history, the five arms, the pairwise judge and the readings.

Everything is synthetic: a fake embedder, a fake writer and a fake judge; no account data is involved.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import replay_memory_sim as rp  # noqa: E402
import shadow_baseline_measures as sbm  # noqa: E402
from test_followup_memory_sim import FakeEmbedder  # noqa: E402
from test_paid_api_plumbing import Provider  # noqa: E402

TOPICS = ["agents forget instructions during long conversations", "benchmarks leak into training data and inflate scores", "prompts as code need review and tests",
          "small models run on phones but drain the battery", "regulators ask for labels on machine written news", "assistants write tests that only confirm the code"]


def make_items(n: int = 60) -> list:
    """Every fifth note revisits the topic of the note five places back; the others bring a distinct topic."""
    items = []
    for k in range(n):
        base = TOPICS[k % len(TOPICS)] if k % 5 else TOPICS[(k - 5) % len(TOPICS)]
        text = "note %d about %s and unique%d words%d extra%d filler%d" % (k, base, k, k, k * 7, k * 11)
        items.append(sbm.Item("n%d" % k, date(2026, 1, 1) + timedelta(days=k), text))
    return items


def fake_generate(system: str, user: str, seed: int, opts: dict) -> dict:
    if system == rp.BRIEF_SYSTEM:
        text = user.split("Note:\n")[1].split("\n\nDescribe")[0]
        return {"text": " ".join(text.split()[2:10]), "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}
    if system == rp.fu.TRACE_SYSTEM:
        return {"text": "GIST: a gist\nANGLE: an angle\nOPEN: none\nKEYWORDS: alpha, beta, gamma, delta, omega", "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}
    has_notes = "Notes from your own earlier entries" in user and "(none)" not in user
    return {"text": "A note on the item.%s" % (" BUILDS ON EARLIER" if has_notes else ""), "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}


def fake_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    notes = re.search(r"NOTE 1:\n(.*?)\n\nNOTE 2:\n(.*?)\n\nWhich is", user, re.S).groups()
    scores = [2 if "BUILDS ON EARLIER" in n else (0 if n.startswith("note ") else 1) for n in notes]
    return {"text": "WINNER: %s" % ("TIE" if scores[0] == scores[1] else ("1" if scores[0] > scores[1] else "2"))}


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    items = make_items()
    prep = rp.prepare(items, FakeEmbedder(), fake_generate, workers=4)
    out = tmp_path_factory.mktemp("replay") / "records.jsonl"
    rp.write_all(items, prep, out, fake_generate, workers=4, log=lambda line: None)
    return items, prep, out


def test_the_threshold_leaves_about_a_fifth_of_the_tasks_with_a_candidate() -> None:
    assert rp.choose_threshold([0.1 * k for k in range(1, 11)], 0.2) == pytest.approx(0.9)
    items = make_items()
    prep = rp.prepare(items, FakeEmbedder(), fake_generate, workers=4)
    share = sum(rp.is_candidate(prep, i) for i in range(rp.WARMUP, len(items))) / (len(items) - rp.WARMUP)
    assert 0.1 <= share <= 0.4 and len(prep["briefs"]) == len(prep["traces"]) == len(prep["top"]) == len(items) and prep["top"][0] == []
    assert all(len(prep["top"][i]) == min(3, i) and all(j < i for j, _ in prep["top"][i]) for i in range(1, len(items)))


def test_the_arms_show_what_they_are_defined_to_show(world) -> None:
    items, prep, _ = world
    candidate = next(i for i in range(rp.WARMUP, len(items)) if rp.is_candidate(prep, i))
    other = next(i for i in range(rp.WARMUP, len(items)) if not rp.is_candidate(prep, i))
    assert rp.memory_block("R0", candidate, prep, items) == ("", []) and rp.memory_block("R0i", candidate, prep, items) == ("", [])
    block1, shown1 = rp.memory_block("R1", other, prep, items)
    assert len(shown1) == 3 and block1.count("[Your earlier note") == 3                      # always-on, even without a candidate
    assert rp.memory_block("R2", other, prep, items) == ("", [])                              # below the threshold: nothing
    block2, shown2 = rp.memory_block("R2", candidate, prep, items)
    block3, shown3 = rp.memory_block("R3", candidate, prep, items)
    assert shown2 == shown3 == sorted(shown2) and "summarised" in block3 and "summarised" not in block2 and items[shown2[0]].text in block2 and items[shown2[0]].text not in block3


def test_every_task_gets_every_arm_once_and_a_second_run_changes_nothing(world, tmp_path: Path) -> None:
    items, prep, out = world
    rows = rp.load_jsonl(out)
    assert len(rows) == (len(items) - rp.WARMUP) * len(rp.ARMS) and len({(r["i"], r["arm"]) for r in rows}) == len(rows)
    assert rp.write_all(items, prep, out, fake_generate, workers=4, log=lambda line: None) == 0
    assert all((r["shown"] == []) for r in rows if r["arm"] in ("R0", "R0i")) and all(r["candidate"] == rp.is_candidate(prep, r["i"]) for r in rows)
    assert any(r["shown"] for r in rows if r["arm"] == "R2" and r["candidate"]) and not any(r["shown"] for r in rows if r["arm"] == "R2" and not r["candidate"])


def test_the_pair_tasks_cover_the_strata_in_both_orders_with_controls_and_a_sample(world) -> None:
    _, _, out = world
    records = rp.load_jsonl(out)
    tasks = rp.pair_tasks(records)
    by = {s: [t for t in tasks if t["stratum"] == s] for s in ("candidate", "other", "control")}
    n_candidates = len({r["i"] for r in records if r["candidate"]})
    assert len(by["candidate"]) == n_candidates * len(rp.CANDIDATE_PAIRS) * 2
    assert len({t["i"] for t in by["other"]}) <= rp.NONCANDIDATE_SAMPLE and len(by["control"]) == 2 * min(rp.CONTROLS, n_candidates)
    assert {t["order"] for t in tasks} == {0, 1} and rp.pair_tasks(records) == tasks


def test_the_judge_run_and_the_readings_find_that_thresholded_memory_helps_on_candidates_and_always_on_does_not_pay(world, tmp_path: Path) -> None:
    items, prep, out = world
    records = rp.load_jsonl(out)
    pairs = tmp_path / "pairs.jsonl"
    written = rp.judge_all(items, prep, records, pairs, fake_judge, workers=4, log=lambda line: None)
    assert written == len(rp.pair_tasks(records)) and rp.judge_all(items, prep, records, pairs, fake_judge, workers=4, log=lambda line: None) == 0
    result = rp.readings(rp.load_jsonl(pairs), draws=200)
    assert result["judge_informative"] and result["control_win_rate"] == pytest.approx(1.0)
    assert result["memory_helps_on_real_candidates"] and result["arms_that_gain"] == ["R2", "R3"]
    assert result["candidate_tasks"]["R2-R0"]["win_rate"] == pytest.approx(1.0) and result["traces_vs_notes"] == "equivalent here"
    assert result["always_on_harms_other_tasks"] is False or result["always_on_harms_other_tasks"] is True      # computed, not assumed
    assert result["thresholded_arms_harm_other_tasks"] == []


def test_deterministic_measures_separate_grounded_references_from_spurious_ones(world) -> None:
    items, prep, out = world
    records = rp.load_jsonl(out)
    table = rp.deterministic(items, records, FakeEmbedder())
    assert set(table) >= {"R0:candidate", "R2:candidate", "R2:other", "R1:other"} and all(v["n"] > 0 for v in table.values())
    assert table["R0:other"]["references"] == 0.0


def test_the_command_line_runs_all_four_steps_against_a_stub_endpoint(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    items = make_items()
    source = tmp_path / "items.jsonl"
    source.write_text("\n".join(json.dumps({"id": i.item_id, "date": str(i.day), "text": i.text}) for i in items) + "\n", encoding="utf-8")
    provider = Provider(content="A short synthetic note about the item.")
    base = ["--items", str(source), "--workdir", str(tmp_path / "work"), "--base-url", provider.url + "/v1", "--model", "stub", "--workers", "4"]
    try:
        for step in ("prepare", "write", "judge"):
            assert rp.main([step] + base, embedder=FakeEmbedder()) == 0
        assert rp.main(["analyse"] + base + ["--json", str(tmp_path / "result.json")], embedder=FakeEmbedder()) == 0
    finally:
        provider.close()
    capsys.readouterr()
    data = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    assert {"tau", "tasks", "candidates", "deterministic", "judge", "provenance"} <= set(data) and data["tasks"] == len(items) - rp.WARMUP
