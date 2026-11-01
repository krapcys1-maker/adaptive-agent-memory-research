"""writer_memory_sim.py: the stream, retrieval, the five arms, the importance dynamics, replay and resuming.

A fake generator stands in for the model, so nothing here needs a network model or a GPU. Every text is synthetic.
"""

from __future__ import annotations

import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import writer_memory_sim as sim  # noqa: E402


def fake_generate(system: str, user: str, seed: int, opts: dict) -> dict:
    if system == sim.TRACE_SYSTEM:
        title = re.search(r"TITLE: (.*)", user).group(1)
        words: list = []
        for word in sim.content_tokens(user.split("Write a memory note")[0]):
            if word not in words and word not in ("entry", "title"):
                words.append(word)
        text = "GIST: %s\nANGLE: an example\nOPEN: none\nKEYWORDS: %s" % (title, ", ".join(words[:5]))
        return {"text": text, "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}
    hook = re.search(r"Today's trigger: (.*)", user).group(1)
    opening = "As I wrote earlier, " if "Notes from your own earlier entries" in user else ""
    return {"text": "TITLE: On %s\n%s%s This is the body of the entry." % (hook.split()[2], opening, hook),
            "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}


def trace(gist: str, keywords: list) -> dict:
    return {"gist": gist, "angle": "", "open": "", "keywords": keywords}


def test_stream_has_every_theme_once_per_round_with_fresh_hooks_and_is_deterministic() -> None:
    for seed in (1, 2, 3):
        stream = sim.make_stream(seed)
        assert [item["day"] for item in stream] == list(range(1, 37))
        for round_ in range(6):
            assert sorted(i["theme"] for i in stream[round_ * 6:(round_ + 1) * 6]) == sorted(sim.THEMES)
        for theme in sim.THEMES:
            hooks = [i["hook"] for i in stream if i["theme"] == theme]
            assert len(hooks) == 6 and len(set(hooks)) == 6
    assert sim.make_stream(1) == sim.make_stream(1)
    assert sim.make_stream(1) != sim.make_stream(2)


def test_stream_rejects_day_counts_the_themes_cannot_fill() -> None:
    with pytest.raises(ValueError):
        sim.make_stream(1, 35)
    with pytest.raises(ValueError):
        sim.make_stream(1, 42)


def test_the_generator_is_deterministic_and_shuffles_into_a_permutation() -> None:
    assert sim.Lcg(5).shuffled(range(10)) == sim.Lcg(5).shuffled(range(10))
    assert sorted(sim.Lcg(5).shuffled(range(10))) == list(range(10))
    assert sim.Lcg(5).shuffled(range(10)) != sim.Lcg(6).shuffled(range(10))


def test_bm25_scores_the_matching_document_and_nothing_else() -> None:
    docs = {1: sim.content_tokens("meetings agenda meetings chairs"), 2: sim.content_tokens("tomatoes soil allotment")}
    scores = sim.bm25_scores(sim.content_tokens("agenda for meetings"), docs)
    assert scores[1] > 0 and scores[2] == 0
    assert sim.bm25_scores(["x"], {}) == {}


def test_top_ids_drops_zero_scores_and_prefers_the_more_recent_on_ties() -> None:
    assert sim.top_ids({1: 0.5, 2: 0.5, 3: 0.0, 4: 0.9}, 3) == [4, 2, 1]
    assert sim.top_ids({1: 0.0}, 3) == []


def test_parse_entry_handles_labels_markdown_and_a_missing_body() -> None:
    assert sim.parse_entry('TITLE: A "quoted" title\nFirst line.\nSecond line.') == ('A "quoted" title', "First line. Second line.")
    assert sim.parse_entry("Plain first line\nbody text") == ("Plain first line", "body text")
    assert sim.parse_entry("**TITLE: Bold**\nText **bold** here") == ("Bold", "Text bold here")
    assert sim.parse_entry("# Title: Header style\nbody") == ("Header style", "body")
    assert sim.parse_entry("TITLE: only a title") == ("only a title", "only a title")
    assert sim.parse_entry("TITLE: T\n\nText: Body here") == ("T", "Body here")
    assert sim.parse_entry("TITLE: T\nThe text of it is long.") == ("T", "The text of it is long.")


def test_parse_trace_reads_four_lines_and_falls_back_when_the_model_does_not() -> None:
    raw = "GIST: Meetings before ten were banned.\nANGLE: the firm's calendar\nOPEN: none\nKEYWORDS: Meetings, Calendar, Ban, firm, morning"
    parsed = sim.parse_trace(raw, "entry text")
    assert parsed["gist"] == "Meetings before ten were banned."
    assert parsed["open"] == "" and parsed["keywords"] == ["meetings", "calendar", "ban", "firm", "morning"]
    fallback = sim.parse_trace("nonsense", "Tomatoes tomatoes allotment soil soil soil bench. Second sentence.")
    assert fallback["keywords"][0] == "soil" and fallback["gist"] == "Tomatoes tomatoes allotment soil soil soil bench."


@pytest.mark.parametrize("text", [
    "As I wrote earlier, the clock is slow.",
    "I mentioned this a few days ago and nobody noticed.",
    "In my last post I promised a tomato update.",
    "Back in the previous entry, the watch lost four minutes.",
    "When I first wrote about meetings I was wrong.",
    "I've written about this before.",
])
def test_explicit_references_to_earlier_writing_count_as_callbacks(text: str) -> None:
    assert sim.callback_extended(text)


@pytest.mark.parametrize("text", [
    "A study last week found that people check messages every six minutes.",
    "Last week I tried standing meetings and my knees complained.",
    "My grandfather's pocket watch runs four minutes slow.",
    "The firm wrote a memo about the ban.",
])
def test_narrated_life_events_and_news_do_not_count_as_callbacks(text: str) -> None:
    assert not sim.callback_extended(text)


def test_a_bare_day_number_counts_only_when_it_points_backwards() -> None:
    assert sim.callback_extended("On day 3 the clock stopped.", day=8)
    assert not sim.callback_extended("On day 3 the clock stopped.", day=3)
    assert not sim.callback_extended("On day 3 the clock stopped.")


def test_m0_shows_nothing_and_m1_shows_the_last_three_entries() -> None:
    m0, m1 = sim.ArmState("M0"), sim.ArmState("M1")
    for day in range(1, 6):
        m0.record(day, "T%d" % day, "body %d" % day, [], None)
        m1.record(day, "T%d" % day, "body %d" % day, [], None)
    assert m0.memory(6, "meetings", "hook") == ("", [])
    block, ids = m1.memory(6, "meetings", "hook")
    assert ids == [3, 4, 5] and "body 3" in block and "body 2" not in block


def test_m2_retrieves_by_similarity_to_the_trigger_not_by_recency() -> None:
    m2 = sim.ArmState("M2")
    for day, (title, text) in enumerate([("Standing meetings", "meetings meetings agenda chairs"), ("Tomatoes", "allotment tomatoes soil"),
                                         ("Prices", "supermarket packages prices"), ("Walks", "ten minute walk break"),
                                         ("Email", "inbox delay group email")], 1):
        m2.record(day, title, text, [], None)
    block, ids = m2.memory(6, "meetings", "A team tries no agenda, no meeting for a quarter.")
    assert ids == [1] and "Standing meetings" in block and "allotment" not in block


def test_m3_arms_show_the_trace_and_never_the_body_of_the_entry() -> None:
    for name in ("M3a", "M3b"):
        state = sim.ArmState(name)
        state.record(1, "Meeting ban", "BODYWORDS " * 30, [], {"gist": "a firm bans early meetings", "angle": "the calendar",
                                                              "open": "whether it lasts", "keywords": ["meetings", "calendar", "firm", "ban", "early"]})
        block, ids = state.memory(5, "meetings", "A firm bans meetings before 10 a.m.")
        assert ids == [1] and "BODYWORDS" not in block
        assert "[Note from day 1]" in block and "Angle: the calendar" in block and "Left open: whether it lasts" in block


def test_importance_grows_with_an_explicit_callback_and_falls_with_age() -> None:
    state = sim.ArmState("M3b")
    state.record(1, "T1", "text one", [], trace("g1", ["clock", "watch", "slow", "tomato", "bench"]))
    assert state.importance(1, 1) == pytest.approx(1.0)
    assert state.importance(1, 31) == pytest.approx(0.5)
    state.record(2, "T2", "As I wrote earlier, my clock and watch ran slow again.", [1],
                 trace("g2", ["clock", "watch", "morning", "walk", "pond"]))
    assert state.traces[1].uses == 1 and state.traces[1].last_used == 2
    assert state.importance(1, 2) == pytest.approx(1.0 + 0.5 - 0.5 / 30)
    assert state.edges[(1, 2)] == pytest.approx(0.5)  # 0.25 for shared keywords, 0.25 more for joint use


def test_a_trace_is_not_reinforced_without_a_callback_or_without_shared_keywords() -> None:
    state = sim.ArmState("M3b")
    state.record(1, "T1", "text one", [], trace("g1", ["clock", "watch", "slow", "tomato", "bench"]))
    state.record(2, "T2", "Clock and watch and slow again, with no reference to anything.", [1], trace("g2", ["a1", "b1", "c1", "d1", "e1"]))
    state.record(3, "T3", "As I wrote earlier, something unrelated entirely happened.", [1], trace("g3", ["a2", "b2", "c2", "d2", "e2"]))
    assert state.traces[1].uses == 0


def test_m3b_pulls_in_an_associated_trace_that_m3a_does_not_show() -> None:
    def build(name: str) -> sim.ArmState:
        state = sim.ArmState(name)
        state.record(1, "Meetings ban", "x", [], trace("firm bans early meetings", ["meetings", "ban", "morning", "firm", "calendar"]))
        state.record(2, "Standing meetings", "y", [], trace("standing meetings run short", ["meetings", "standing", "short", "decide", "calendar"]))
        state.record(3, "Calendar rules", "z", [], trace("mornings stay free", ["calendar", "morning", "free", "stay", "rules"]))
        return state
    assert build("M3a").memory(10, "meetings", "A firm bans meetings before 10 a.m.")[1] == [1, 2]
    assert build("M3b").memory(10, "meetings", "A firm bans meetings before 10 a.m.")[1] == [1, 2, 3]


def test_every_memory_arm_gets_the_same_instruction_and_m0_gets_none() -> None:
    item = {"day": 7, "theme": "meetings", "hook": "A firm bans meetings."}
    bare, noted = sim.build_user_prompt(item, ""), sim.build_user_prompt(item, "[Note from day 2] x")
    assert "Notes from" not in bare and "Do not repeat" not in bare
    assert "[Note from day 2] x" in noted and "Do not repeat what you have already said" in noted
    assert bare.splitlines()[0] == noted.splitlines()[0]


def test_replay_rebuilds_exactly_the_state_a_live_run_ends_with() -> None:
    live = {arm: sim.ArmState(arm) for arm in sim.ARMS}
    rows = [sim.write_entry(live[arm], item, 1, fake_generate) for item in sim.make_stream(1, 12) for arm in sim.ARMS]
    for arm in sim.ARMS:
        assert sim.replay(rows, 1, arm) == live[arm]
    assert any(trace_.uses for trace_ in live["M3b"].traces.values()) or live["M3b"].edges


def test_a_stopped_run_resumes_without_repeating_or_skipping_and_matches_an_uninterrupted_run(tmp_path: Path) -> None:
    quiet = lambda line: None  # noqa: E731
    stopped, whole = tmp_path / "stopped.jsonl", tmp_path / "whole.jsonl"
    assert sim.run(stopped, fake_generate, (1,), 12, sim.ARMS, 3, max_days=5, log=quiet) == 25
    assert sim.run(stopped, fake_generate, (1,), 12, sim.ARMS, 3, log=quiet) == 35
    assert sim.run(whole, fake_generate, (1,), 12, sim.ARMS, 3, log=quiet) == 60
    resumed, uninterrupted = sim.load_records(stopped), sim.load_records(whole)
    keys = [(r["seed"], r["arm"], r["day"]) for r in resumed]
    assert len(keys) == len(set(keys)) == 60

    def view(rows: list) -> list:
        return sorted(((r["seed"], r["arm"], r["day"], r["text"], tuple(r["shown_ids"]), json.dumps(r["trace"])) for r in rows))
    assert view(resumed) == view(uninterrupted)


def test_memory_arms_actually_differ_in_what_the_writer_is_shown(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    sim.run(path, fake_generate, (1,), 12, sim.ARMS, 3, log=lambda line: None)
    rows = sim.load_records(path)
    late = {r["arm"]: r for r in rows if r["day"] == 12}
    assert late["M0"]["memory_block"] == "" and late["M0"]["shown_ids"] == []
    assert all(late[arm]["memory_block"] for arm in ("M1", "M2", "M3a", "M3b"))
    assert "[Entry from day" in late["M1"]["memory_block"] and "[Note from day" in late["M3a"]["memory_block"]


def test_ollama_chat_sends_the_documented_request_and_reads_the_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            seen["path"] = self.path
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            payload = json.dumps({"message": {"content": "TITLE: x\nbody"}, "prompt_eval_count": 3, "eval_count": 2}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(sim, "OLLAMA_URL", "http://127.0.0.1:%d" % server.server_address[1])
        reply = sim.ollama_chat("some-model", "system text", "user text", 11, {"temperature": 0.8, "top_p": 0.95, "num_predict": 50})
    finally:
        server.shutdown()
    assert seen["path"] == "/api/chat" and seen["body"]["model"] == "some-model" and seen["body"]["stream"] is False
    assert seen["body"]["options"]["seed"] == 11 and seen["body"]["options"]["temperature"] == 0.8
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]
    assert reply["text"] == "TITLE: x\nbody" and reply["prompt_tokens"] == 3 and reply["gen_tokens"] == 2
