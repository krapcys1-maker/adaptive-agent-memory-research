"""followup_memory_sim.py: the stream, the four arms, the threshold calibration, replay and resuming.

A fake embedder (hashed bag of words) and a fake writer stand in for the real models; every text is synthetic.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import followup_memory_sim as fu  # noqa: E402


class FakeEmbedder:
    def encode(self, texts):
        out = []
        for text in texts:
            vec = [0.0] * 256
            for word in re.findall(r"[a-z0-9']+", text.lower()):
                vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % 256] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


def fake_generate(system: str, user: str, seed: int, opts: dict) -> dict:
    if system == fu.TRACE_SYSTEM:
        words = re.findall(r"[a-z]{5,}", user.split("Write a memory note")[0].lower())[:5]
        return {"text": "GIST: a gist of %s\nANGLE: an angle\nOPEN: none\nKEYWORDS: %s" % (words[0] if words else "x", ", ".join(words)),
                "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}
    hook = re.search(r"Item: (.*)", user).group(1)
    return {"text": "Today: %s." % hook[:60], "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}


def test_the_stream_has_a_fifth_follow_ups_each_developing_a_fresh_story_from_one_to_seven_days_back() -> None:
    for seed in (1, 2, 3):
        stream = fu.make_stream(seed)
        assert [t["day"] for t in stream] == list(range(1, 61))
        follows = [t for t in stream if t["kind"] == "followup"]
        assert len(follows) == 12 and min(t["day"] for t in follows) >= 8
        bases = [t["base_day"] for t in follows]
        assert len(set(bases)) == 12 and all(1 <= t["day"] - t["base_day"] <= 7 for t in follows)
        for t in follows:
            base = stream[t["base_day"] - 1]
            assert base["kind"] == "fresh" and base["story"] == t["story"] and base["theme"] == t["theme"]
        assert len({t["story"] for t in stream if t["kind"] == "fresh"}) == 48
    assert fu.make_stream(1) == fu.make_stream(1) and fu.make_stream(1) != fu.make_stream(2)


def test_a_follow_up_item_restates_the_story_it_develops() -> None:
    hook = fu.followup_hook("A paper shows agents forget.", "A replication disagrees.")
    assert hook == "Follow-up on the story that a paper shows agents forget: a replication disagrees."
    stream = fu.make_stream(4)
    t = next(x for x in stream if x["kind"] == "followup")
    core = stream[t["base_day"] - 1]["hook"].rstrip(".")
    assert core[0].lower() + core[1:] in t["hook"]


def test_the_stream_rejects_a_pool_that_is_too_small() -> None:
    with pytest.raises(ValueError):
        fu.make_stream(1, days=100)


def test_the_calibration_reports_a_threshold_in_steps_and_the_spurious_share() -> None:
    result = fu.calibrate_threshold(FakeEmbedder(), seeds=(100, 101), recall=0.9)
    assert result["followup_pairs"] == 24 and 0 < result["threshold"] <= 1
    assert abs(result["threshold"] / 0.05 - round(result["threshold"] / 0.05)) < 1e-6
    assert 0 <= result["spurious_share"] <= 1 and result["fresh_days"] == 2 * 47


def build_state(arm: str, tau: float = 0.3):
    stream = fu.make_stream(1)
    vectors = FakeEmbedder().encode([t["hook"] for t in stream])
    state = fu.ArmState(arm, tau)
    return stream, vectors, state


def fill(stream, state, upto: int) -> None:
    for t in stream[:upto]:
        state.record(t["day"], "NOTE-TEXT-%d about %s" % (t["day"], t["hook"][:40]), {"gist": "gist %d" % t["day"], "angle": "angle", "open": "", "keywords": ["k"]})


def test_a0_shows_nothing_and_a1_always_shows_the_three_most_similar_even_when_none_is_related() -> None:
    stream, vectors, a0 = build_state("A0")
    fill(stream, a0, 20)
    assert a0.memory(21, vectors) == ("", [])
    _, _, a1 = build_state("A1", tau=0.99)
    fill(stream, a1, 20)
    block, ids = a1.memory(21, vectors)
    assert len(ids) == 3 and block.count("[Your note from day") == 3 and ids == sorted(ids)


def test_a2_shows_only_notes_that_reach_the_threshold_and_a3_shows_their_traces() -> None:
    stream, vectors, a2 = build_state("A2", tau=0.5)
    follow = next(t for t in stream if t["kind"] == "followup")
    fill(stream, a2, follow["day"] - 1)
    block, ids = a2.memory(follow["day"], vectors)
    assert follow["base_day"] in ids and "NOTE-TEXT-%d" % follow["base_day"] in block
    fresh = next(t for t in stream if t["kind"] == "fresh" and t["day"] > 15)
    _, _, strict = build_state("A2", tau=0.95)
    fill(stream, strict, fresh["day"] - 1)
    assert strict.memory(fresh["day"], vectors) == ("", [])                                  # nothing reaches the bar: nothing is shown
    _, _, a3 = build_state("A3", tau=0.5)
    fill(stream, a3, follow["day"] - 1)
    traced, ids3 = a3.memory(follow["day"], vectors)
    assert ids3 == ids and "summarised" in traced and "NOTE-TEXT" not in traced and "gist %d" % follow["base_day"] in traced


def test_clean_note_strips_labels_markdown_and_line_breaks() -> None:
    assert fu.clean_note("Note: **Hello**\nthere.") == "Hello there."
    assert fu.clean_note("Today's note:  Short one.") == "Short one."


def test_prompts_differ_only_by_the_notes_block() -> None:
    task = {"hook": "An item."}
    bare, noted = fu.build_prompt(task, ""), fu.build_prompt(task, "[Your note from day 2] x")
    assert "Notes from your own earlier entries" not in bare and "[Your note from day 2] x" in noted
    assert bare.splitlines()[0] == noted.splitlines()[0] == "Item: An item."


def test_a_run_writes_every_note_once_resumes_and_replay_matches_the_live_state(tmp_path: Path) -> None:
    records = tmp_path / "records.jsonl"
    quiet = lambda line: None  # noqa: E731
    assert fu.run(records, fake_generate, FakeEmbedder(), 0.5, (1,), 60, fu.ARMS, 4, log=quiet) == 60 * 4
    assert fu.run(records, fake_generate, FakeEmbedder(), 0.5, (1,), 60, fu.ARMS, 4, log=quiet) == 0
    rows = fu.load_records(records)
    keys = [(r["seed"], r["arm"], r["day"]) for r in rows]
    assert len(keys) == len(set(keys)) == 240
    a3 = [r for r in rows if r["arm"] == "A3"]
    assert all(r["trace"] for r in a3) and not any(r["trace"] for r in rows if r["arm"] != "A3")
    assert all(r["memory_block"] == "" for r in rows if r["arm"] == "A0")
    follow = [r for r in rows if r["arm"] == "A2" and r["kind"] == "followup"]
    assert follow and all(r["base_day"] in r["shown_days"] for r in follow)
    rebuilt = fu.replay(rows, 1, "A3", 0.5)
    assert rebuilt.notes == {r["day"]: r["text"] for r in a3} and set(rebuilt.traces) == set(rebuilt.notes)


def test_the_runner_drives_the_harness_through_a_stub_endpoint_and_refuses_a_changed_threshold(tmp_path: Path) -> None:
    import test_paid_api_plumbing as plumbing
    import run_followup_memory_sim as runner
    provider = plumbing.Provider(content="A short synthetic note about the item.")
    records = tmp_path / "records.jsonl"
    args = ["--records", str(records), "--base-url", provider.url + "/v1", "--model", "stub", "--tau", "0.5", "--seeds", "1", "--days", "60", "--workers", "4"]
    try:
        assert runner.main(args, embedder=FakeEmbedder()) == 0
        assert len(fu.load_records(records)) == 60 * 4 and (tmp_path / "run-meta.json").exists()
        assert runner.main(args, embedder=FakeEmbedder()) == 0 and len(fu.load_records(records)) == 240
        assert runner.main(args[:6] + ["--tau", "0.6"] + args[8:], embedder=FakeEmbedder()) == 2
    finally:
        provider.close()
