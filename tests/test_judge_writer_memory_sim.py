"""judge_writer_memory_sim.py and llm_backends.py: parsing, the blind prompt, planted controls, resuming, analysis and the two backends.

A fake judge stands in for the model and a stub HTTP server for the endpoints; every text is synthetic.
"""

from __future__ import annotations

import json
import re
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import judge_writer_memory_sim as judge  # noqa: E402
import llm_backends as backends  # noqa: E402
import writer_memory_sim as sim  # noqa: E402

THEMES = list(sim.THEMES)


def make_rows(arm: str, seed: int = 1, days: int = 18, repeat: bool = False) -> list:
    rows = []
    for day in range(1, days + 1):
        theme = THEMES[(day - 1) % 6]
        hook = sim.THEMES[theme][(day - 1) // 6]
        words = sim.content_tokens(hook)
        text = ("same old paragraph about %s again and again" % theme) if repeat else \
            "%s %s %s and a brand new thought number %d" % (words[0], words[-1], theme, day)
        rows.append({"seed": seed, "arm": arm, "day": day, "theme": theme, "hook": hook, "title": "T%d" % day, "text": text,
                     "words": len(text.split()), "shown_ids": [], "memory_block": "", "trace": None})
    return rows


def fake_judge(system: str, user: str, seed: int, opts: dict) -> dict:
    entry = re.search(r"Entry to score:\nTITLE: .*?\n(.*?)\n\nScore the entry", user, re.S).group(1)
    earlier = user.split("Earlier entries by the same author on this theme (oldest first):")[1].split("Entry to score:")[0]
    hook = re.search(r"Today's trigger \(theme: .*?\): (.*)", user).group(1)
    fresh = 1 if entry.strip() in earlier else 4
    fit = 4 if set(sim.content_tokens(hook)) & set(sim.content_tokens(entry)) else 1
    return {"text": "FIT: %d\nFRESH: %d\nVOICE: 3\nQUALITY: %d" % (fit, fresh, 2 if fresh == 1 else 4), "prompt_tokens": 1, "gen_tokens": 1, "wall_s": 0.0}


def test_scores_are_read_from_plain_bold_and_slash_forms_and_missing_ones_are_none() -> None:
    assert judge.parse_scores("FIT: 4\nFRESH: 2\nVOICE: 5\nQUALITY: 3") == {"fit": 4, "fresh": 2, "voice": 5, "quality": 3}
    assert judge.parse_scores("**FIT**: 4/5\n- fresh = 2\nVoice: 5.\nQUALITY: 3") == {"fit": 4, "fresh": 2, "voice": 5, "quality": 3}
    assert judge.parse_scores("FIT: 4, FRESH: 3, VOICE: 3, QUALITY: 3") == {"fit": 4, "fresh": 3, "voice": 3, "quality": 3}   # one-line reply
    partial = judge.parse_scores("FIT: 7\nFRESH: 3")
    assert partial == {"fit": None, "fresh": 3, "voice": None, "quality": None}


def test_earlier_entries_are_the_same_authors_latest_on_the_same_theme_oldest_first() -> None:
    rows = make_rows("M0") + make_rows("M2")
    row = next(r for r in rows if r["arm"] == "M0" and r["day"] == 15)
    got = judge.earlier_entries(rows, row, 2)
    assert [e["day"] for e in got] == [3, 9] and all(e["arm"] == "M0" and e["theme"] == row["theme"] for e in got)
    assert judge.earlier_entries(rows, next(r for r in rows if r["arm"] == "M0" and r["day"] == 2), 2) == []


def test_the_judge_prompt_shows_persona_trigger_entry_and_history_but_never_the_arm() -> None:
    rows = make_rows("M3b")
    row = next(r for r in rows if r["day"] == 13)
    prompt = judge.judge_prompt(row, judge.earlier_entries(rows, row))
    assert sim.PERSONA in prompt and row["hook"] in prompt and row["text"] in prompt and "[Earlier entry, day 7]" in prompt
    assert "M3b" not in prompt and "arm" not in prompt.lower().replace("started", "")
    assert "(none)" in judge.judge_prompt(rows[0], [])


def test_planted_controls_are_deterministic_and_built_as_described() -> None:
    rows = make_rows("M0") + make_rows("M2")
    first, second = judge.build_controls(rows, each=3), judge.build_controls(rows, each=3)
    assert first == second and [c["control"] for c in first] == ["copy", "offtopic"] * 3
    m0 = [r for r in rows if r["arm"] == "M0"]
    for c in first:
        assert c["arm"] == "M0" and c["day"] >= judge.ANALYSIS_FROM
        original = next(r for r in m0 if r["day"] == c["day"])
        source = next(r for r in m0 if r["day"] == c["source_day"])
        assert c["text"] == source["text"] and c["text"] != original["text"]
        assert (source["theme"] == c["theme"]) == (c["control"] == "copy")


def test_a_run_judges_every_analysis_day_entry_and_every_control_once_and_resumes(tmp_path: Path) -> None:
    rows = make_rows("M0") + make_rows("M2", repeat=True)
    out = tmp_path / "judgments.jsonl"
    first = judge.run(rows, out, fake_judge, workers=3, log=lambda line: None, controls_each=4)
    expected = sum(1 for r in rows if r["day"] >= judge.ANALYSIS_FROM) + 8
    assert first == expected
    assert judge.run(rows, out, fake_judge, workers=3, log=lambda line: None, controls_each=4) == 0
    keys = [judge.task_key(j) for j in judge.load_jsonl(out)]
    assert len(keys) == len(set(keys)) == expected
    assert sum(1 for j in judge.load_jsonl(out) if j["control"]) == 8


def test_analysis_reads_repetition_and_off_topic_entries_off_the_scores_and_checks_the_controls(tmp_path: Path) -> None:
    rows = make_rows("M0") + make_rows("M2", repeat=True)
    out = tmp_path / "judgments.jsonl"
    judge.run(rows, out, fake_judge, workers=2, log=lambda line: None, controls_each=4)
    result = judge.analyse(judge.load_jsonl(out), draws=200)
    assert result["unparsed"] == 0 and result["arms"] == ["M0", "M2"]
    assert result["controls_check"]["fresh_informative"] is True and result["controls_check"]["fit_informative"] is True
    assert result["arm_means"]["M0"]["fresh"] == pytest.approx(4.0) and result["arm_means"]["M2"]["fresh"] < 4.0
    assert result["contrasts"]["M2-M0"]["fresh"]["mean"] < 0 and result["contrasts"]["M2-M0"]["fresh"]["ci_high"] < 0
    assert result["quality_guard_holds"]["M2"] is False       # the repeating arm also loses overall quality in this fake judge
    assert "# AAM-E1-SIM judge results" in judge.report(result)


def test_analysis_re_derives_missing_scores_from_the_stored_reply() -> None:
    rows = [{"control": None, "seed": 1, "arm": "M0", "day": 7 + i, "fit": 4, "fresh": None, "voice": None, "quality": None,
             "raw": "FIT: 4, FRESH: 3, VOICE: 2, QUALITY: 5"} for i in range(4)]
    result = judge.analyse(rows, draws=50)
    assert result["unparsed"] == 0 and result["arm_means"]["M0"] == {"fit": 4, "fresh": 3, "voice": 2, "quality": 5}


def test_a_judge_that_cannot_tell_is_declared_uninformative() -> None:
    blind = [{"control": kind, "seed": 1, "arm": "M0", "day": 8 + i, "fit": 4, "fresh": 4, "voice": 3, "quality": 4, "raw": ""}
             for kind in ("copy", "offtopic") for i in range(6)]
    real = [{"control": None, "seed": 1, "arm": "M0", "day": 7 + i, "fit": 4, "fresh": 4, "voice": 3, "quality": 4, "raw": ""} for i in range(6)]
    check = judge.analyse(real + blind, draws=100)["controls_check"]
    assert check["fresh_informative"] is False and check["fit_informative"] is False


def serve(handler_class):
    server = HTTPServer(("127.0.0.1", 0), handler_class)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


def make_handler(status: int, seen: dict):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            seen["path"] = self.path
            seen["auth"] = self.headers.get("Authorization")
            seen["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["calls"] = seen.get("calls", 0) + 1
            if self.path.startswith("/v1"):
                payload = {"choices": [{"message": {"content": "hello"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
            else:
                payload = {"message": {"content": "hello"}, "prompt_eval_count": 5, "eval_count": 2}
            body = json.dumps(payload if status == 200 else {"error": {"message": "refused"}}).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass
    return Handler


def test_the_openai_backend_posts_to_chat_completions_with_a_dummy_key_and_reads_usage() -> None:
    seen: dict = {}
    server, url = serve(make_handler(200, seen))
    try:
        reply = backends.openai_chat(url + "/v1", "some-model", "sys", "usr", 5, {"temperature": 0.8, "top_p": 0.95, "num_predict": 60})
    finally:
        server.shutdown()
    assert seen["path"] == "/v1/chat/completions" and seen["auth"] == "Bearer routed-through-the-local-proxy"
    assert seen["body"]["max_tokens"] == 60 and seen["body"]["temperature"] == 0.8 and seen["body"]["model"] == "some-model"
    assert reply["text"] == "hello" and reply["prompt_tokens"] == 5 and reply["gen_tokens"] == 2


def test_a_refused_spend_is_raised_at_once_and_never_retried_and_a_bad_key_is_not_retried_either() -> None:
    for status, expected in ((402, backends.SpendCapRefused), (401, urllib.error.HTTPError)):
        seen: dict = {}
        server, url = serve(make_handler(status, seen))
        try:
            with pytest.raises(expected):
                backends.openai_chat(url + "/v1", "m", "s", "u", 1, {"temperature": 0.0})
        finally:
            server.shutdown()
        assert seen["calls"] == 1


def test_the_ollama_backend_uses_the_chat_endpoint_and_passes_the_options() -> None:
    seen: dict = {}
    server, url = serve(make_handler(200, seen))
    try:
        reply = backends.ollama_chat("m", "s", "u", 9, {"temperature": 0.0, "num_predict": 10}, url=url)
    finally:
        server.shutdown()
    assert seen["path"] == "/api/chat" and seen["body"]["options"]["seed"] == 9 and reply["text"] == "hello" and reply["gen_tokens"] == 2
