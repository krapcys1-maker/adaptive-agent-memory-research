"""metered_proxy.py, run_writer_memory_sim_openai.py and the OpenAI backend's guards.

A stub HTTP server plays the paid provider; the key is a dummy string made up here and no real credential is ever read.
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import llm_backends as backends  # noqa: E402
import metered_proxy as mp  # noqa: E402
import run_writer_memory_sim_openai as runner  # noqa: E402
import writer_memory_sim as sim  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402


class Provider:
    """A stub provider: records what it receives and answers with a fixed completion and usage."""

    def __init__(self, prompt_tokens: int = 1000, completion_tokens: int = 200, status: int = 200, content: str = "TITLE: Stub\nA short body.") -> None:
        self.seen: list = []
        self.status, self.content = status, content
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
                is_trace = "terse memory notes" in json.dumps(body["messages"])
                text = "GIST: g\nANGLE: a\nOPEN: none\nKEYWORDS: alpha, beta, gamma, delta, omega" if is_trace else outer.content
                payload = json.dumps({"choices": [{"message": {"content": text}, "finish_reason": "stop"}],
                                      "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}}).encode()
                if outer.status != 200:
                    payload = json.dumps({"error": {"message": "refused"}}).encode()
                self.send_response(outer.status)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]

    def close(self) -> None:
        self.server.shutdown()


def post(url: str, payload: dict) -> tuple:
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer client-dummy"})
    try:
        with urllib.request.urlopen(request, timeout=20) as handle:
            return handle.status, json.load(handle)
    except urllib.error.HTTPError as failure:
        return failure.code, json.loads(failure.read())


def test_the_proxy_injects_the_key_and_the_caller_chosen_decoding_and_leaves_the_clients_sampling_alone(tmp_path: Path) -> None:
    provider = Provider()
    ledger = SpendLedger(tmp_path / "ledger.jsonl", total_cap_usd=1.0, run_id="t1", cap_scope="t")
    server, state = mp.serve(provider.url, "dummy-upstream-key", 0, ledger, None, {"thinking": {"type": "disabled"}})
    try:
        status, reply = post("http://127.0.0.1:%d/v1/chat/completions" % server.server_address[1],
                             {"model": "m", "temperature": 0.8, "top_p": 0.95, "messages": [{"role": "user", "content": "secret prompt text"}]})
    finally:
        server.shutdown()
        provider.close()
    assert status == 200 and reply["choices"][0]["message"]["content"].startswith("TITLE")
    seen = provider.seen[0]
    assert seen["auth"] == "Bearer dummy-upstream-key"                       # the client's own key is not forwarded
    assert seen["body"]["thinking"] == {"type": "disabled"} and seen["body"]["temperature"] == 0.8 and seen["body"]["top_p"] == 0.95
    lines = (tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    assert len(lines) == 1 and entry["prompt_tokens"] == 1000 and entry["completion_tokens"] == 200
    assert entry["usd"] == pytest.approx(1000 / 1e6 * 0.27 + 200 / 1e6 * 1.10, abs=1e-7)
    assert "secret prompt text" not in lines[0] and "dummy" not in lines[0]


def test_a_request_that_could_cross_the_cap_is_refused_with_402_and_never_forwarded(tmp_path: Path) -> None:
    provider = Provider(prompt_tokens=50_000, completion_tokens=10_000)      # about $0.0245 a call at the list price
    ledger = SpendLedger(tmp_path / "ledger.jsonl", total_cap_usd=0.03, run_id="t2", cap_scope="t")
    server, state = mp.serve(provider.url, "dummy-upstream-key", 0, ledger, None, {})
    url = "http://127.0.0.1:%d/v1/chat/completions" % server.server_address[1]
    try:
        first = post(url, {"model": "m", "messages": []})
        second = post(url, {"model": "m", "messages": []})
    finally:
        server.shutdown()
        provider.close()
    assert first[0] == 200 and second[0] == 402 and second[1]["error"]["type"] == "arena_spend_cap"
    assert len(provider.seen) == 1 and state.refusals == 1


def test_the_cap_counts_what_is_already_in_the_ledger_for_the_scope(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl", total_cap_usd=0.05, run_id="t3", cap_scope="t")
    ledger.record(0.045, model="earlier", via="proxy")
    provider = Provider()
    server, _ = mp.serve(provider.url, "dummy-upstream-key", 0, ledger, None, {})
    try:
        status, _ = post("http://127.0.0.1:%d/v1/chat/completions" % server.server_address[1], {"model": "m", "messages": []})
    finally:
        server.shutdown()
        provider.close()
    assert status == 402 and provider.seen == []


def test_the_command_line_refuses_a_cap_above_the_owners_budget(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert mp.main(["--ledger", str(tmp_path / "l.jsonl"), "--total-cap-usd", "20"]) == 2
    assert mp.main(["--ledger", str(tmp_path / "l.jsonl"), "--total-cap-usd", "5", "--decoding-json", "[1]"]) == 2
    assert "refusing" in capsys.readouterr().err


def test_the_key_helper_is_retried_from_the_main_checkout_when_a_worktree_has_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []

    def fake_load_key() -> str:
        calls.append(mp.pp.ROOT)
        if mp.pp.ROOT != tmp_path:
            raise SystemExit("no key here")
        return "dummy-key-from-fake-helper"

    monkeypatch.setattr(mp.pp, "load_key", fake_load_key)
    monkeypatch.setattr(mp, "main_checkout", lambda: tmp_path)
    original_root = mp.pp.ROOT
    try:
        assert mp.load_key() == "dummy-key-from-fake-helper"
    finally:
        mp.pp.ROOT = original_root
    assert calls == [original_root, tmp_path]


def test_the_main_checkout_is_found_from_the_repository() -> None:
    assert (mp.main_checkout() / ".git").exists()


def test_an_empty_completion_is_an_error_not_an_empty_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "sleep", lambda s: None)
    provider = Provider(content="   ")
    try:
        with pytest.raises(ValueError):
            backends.openai_chat(provider.url + "/v1", "m", "s", "u", 1, {"temperature": 0.0})
    finally:
        provider.close()
    assert len(provider.seen) == 4                       # tried the full number of attempts, recorded nothing


def test_the_runner_writes_every_entry_once_resumes_and_stops_cleanly_on_the_spend_cap(tmp_path: Path) -> None:
    provider = Provider()
    records = tmp_path / "records.jsonl"
    args = ["--records", str(records), "--base-url", provider.url + "/v1", "--model", "stub-model", "--seeds", "1", "--days", "6", "--workers", "3"]
    try:
        assert runner.main(args) == 0
        first = sim.load_records(records)
        assert len(first) == 6 * len(sim.ARMS) and {r["arm"] for r in first} == set(sim.ARMS)
        assert runner.main(args) == 0 and len(sim.load_records(records)) == len(first)          # nothing repeated
        meta = json.loads((tmp_path / "run-meta.json").read_text(encoding="utf-8"))
        assert meta["model"] == "stub-model" and meta["harness_sha256"] and meta["seeds"] == [1]
        provider.status = 402
        assert runner.main(args[:-6] + ["--seeds", "2", "--days", "6", "--workers", "2"]) == 3
    finally:
        provider.close()
