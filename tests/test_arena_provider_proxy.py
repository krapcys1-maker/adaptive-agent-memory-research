"""The proxy that caps a system the arena does not construct.

`FixedDecoding` reaches a system the arena imports. It reaches nothing at all in
a system that is a server: Hindsight builds its own client in its own process
and would spend without the ledger ever seeing it. A cap the run can walk around
is a report.

These tests run the proxy against a fake upstream, so nothing here costs money.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.provider_proxy import serve  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402

SEEN: list[dict] = []


#: Flipped by one test so the upstream answers with a streamed body the proxy
#: cannot parse. A module-level switch rather than a second server, so the test
#: exercises the same live proxy the others do.
STREAM_INSTEAD = {"on": False}


class _Upstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):  # noqa: A003
        pass

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        SEEN.append(json.loads(self.rfile.read(length) or b"{}"))
        if STREAM_INSTEAD["on"]:
            blank = chr(10) * 2
            body = ('data: {"choices":[]}' + blank + "data: [DONE]" + blank).encode()
            content_type = "text/event-stream"
        else:
            body = json.dumps({
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 100},
            }).encode()
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def upstream():
    SEEN.clear()
    STREAM_INSTEAD["on"] = False
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture()
def proxy(upstream, tmp_path):
    made: list = []

    def build(run_cap_usd=None, total_cap_usd=None, run_id="test"):
        ledger = SpendLedger(tmp_path / "ledger.jsonl", total_cap_usd=total_cap_usd,
                             run_id=run_id)
        server, state = serve(upstream, "sk-test", 0, ledger, run_cap_usd)
        made.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}", state, ledger

    yield build
    for server in made:
        server.shutdown()


def post(url: str, payload: dict):
    request = urllib.request.Request(
        f"{url}/v1/chat/completions", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read())


def test_a_call_reaches_the_upstream_and_comes_back(proxy) -> None:
    url, state, _ = proxy()
    status, body = post(url, {"model": "m", "messages": []})
    assert status == 200 and body["choices"][0]["message"]["content"] == "ok"
    assert state.summary()["calls"] == 1


def test_the_arena_decoding_is_enforced_on_a_system_it_does_not_construct(proxy) -> None:
    url, _, _ = proxy()
    post(url, {"model": "m", "messages": [], "temperature": 0.7})
    assert SEEN[0]["temperature"] == 0


def test_what_the_system_asked_for_is_recorded_beside_what_was_enforced(proxy) -> None:
    url, state, _ = proxy()
    post(url, {"model": "m", "messages": [], "temperature": 0.7})
    summary = state.summary()
    assert summary["decoding_overrides"] == 1
    assert summary["decoding_override_values"] == ['{"temperature": 0.7}']
    assert summary["arena_enforced_decoding"] == {"temperature": 0}


def test_every_call_is_priced_into_the_shared_ledger(proxy) -> None:
    url, state, ledger = proxy(run_id="hindsight")
    for _ in range(3):
        post(url, {"model": "m", "messages": []})
    assert ledger.by_run()["hindsight"] == pytest.approx(state.spent_usd)
    assert state.summary()["prompt_tokens"] == 3000


def test_the_run_cap_refuses_with_402_and_forwards_nothing(proxy) -> None:
    """402 rather than a network error: a system given a payment error stops.

    The refusal happens before the forward, so the refused call cost nothing.
    """
    url, state, _ = proxy(run_cap_usd=0.001)
    for _ in range(20):
        try:
            post(url, {"model": "m", "messages": []})
        except urllib.error.HTTPError as failure:
            assert failure.code == 402
            body = json.loads(failure.read())
            assert body["error"]["type"] == "arena_spend_cap"
            break
    else:
        pytest.fail("the cap never fired")
    assert state.refusals >= 1
    assert len(SEEN) == len(state.calls)  # nothing forwarded that was not counted


def test_the_night_cap_stops_a_run_that_is_within_its_own(proxy, tmp_path) -> None:
    """The case a per-run cap cannot see: this run has spent nothing."""
    SpendLedger(tmp_path / "ledger.jsonl", run_id="earlier").record(9.999)
    url, state, _ = proxy(run_cap_usd=3.0, total_cap_usd=10.0, run_id="later")
    with pytest.raises(urllib.error.HTTPError) as caught:
        post(url, {"model": "m", "messages": []})
    assert caught.value.code == 402
    assert SEEN == []
    assert state.calls == []


def test_an_unparseable_response_counts_the_call_with_unknown_tokens(proxy) -> None:
    """Unknown is not zero. A streamed body still happened and was still billed.

    A first version of this test built a streaming handler and never installed
    it, so it asserted only that one ordinary call was counted: green, and
    incapable of failing for its stated reason. The switch below is read by the
    live upstream, so removing the unknown-usage branch from the proxy breaks it.
    """
    url, state, ledger = proxy()
    STREAM_INSTEAD["on"] = True
    # Read the body without parsing it: the point of the case is that it is not
    # JSON, so the test helper that decodes JSON cannot be the one used here.
    request = urllib.request.Request(
        f"{url}/v1/chat/completions", data=json.dumps({"model": "m", "messages": []}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        assert response.read().startswith(b"data: ")

    summary = state.summary()
    assert summary["calls"] == 1
    assert summary["unknown_usage_calls"] == 1
    assert summary["prompt_tokens"] == 0
    # Counted in the ledger even though its tokens are unknown: a call that
    # cannot be priced is not a call that was free.
    assert len(ledger.entries()) == 1
    assert ledger.entries()[0]["usage_known"] is False


def test_the_proxy_does_not_touch_anything_but_decoding(proxy) -> None:
    """It never reads or rewrites message content. Only the decoding block moves."""
    url, _, _ = proxy()
    sent = {"model": "m", "messages": [{"role": "user", "content": "secret"}],
            "max_tokens": 99, "response_format": {"type": "json_object"}}
    post(url, sent)
    forwarded = SEEN[0]
    assert forwarded["messages"] == sent["messages"]
    assert forwarded["max_tokens"] == 99
    assert forwarded["response_format"] == {"type": "json_object"}
    assert set(forwarded) - set(sent) == {"temperature"}


def test_the_summary_is_readable_over_http(proxy) -> None:
    """The runner needs the count from outside the process that spent it."""
    url, _, _ = proxy()
    post(url, {"model": "m", "messages": []})
    with urllib.request.urlopen(f"{url}/arena/summary", timeout=10) as response:
        summary = json.loads(response.read())
    assert summary["calls"] == 1 and summary["prompt_tokens"] == 1000
