"""flash_only_proxy_v2.py: the frozen flash-only proxy composed with the fail-closed version-2 ledger.

A local stub plays the provider; nothing leaves 127.0.0.1 and no key is loaded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import flash_only_proxy_v2 as fo2  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402
from arena.spend_ledger_v2 import SpendLedgerV2  # noqa: E402
from test_paid_api_plumbing import Provider, post  # noqa: E402

DECODING = {"thinking": {"type": "disabled"}}
FLASH = {"model": "deepseek-flash", "messages": [{"role": "user", "content": "hi"}]}


def rows(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.fixture()
def proxy(tmp_path):
    started = []

    def start(ledger, run_cap=None, provider=None):
        provider = provider or Provider()
        server, state = fo2.serve(provider.url, "dummy-upstream-key", 0, ledger, run_cap, DECODING)
        started.append((server, provider))
        return "http://127.0.0.1:%d/v1/chat/completions" % server.server_address[1], provider, state

    yield start
    for server, provider in started:
        server.shutdown()
        provider.close()


def test_an_authorised_call_is_reserved_before_and_settled_after_forwarding(tmp_path, proxy):
    path = tmp_path / "ledger.jsonl"
    ledger = SpendLedgerV2(path, total_cap_usd=1.0, run_id="t-1", cap_scope="t", create=True)
    url, provider, _ = proxy(ledger)
    status, _ = post(url, FLASH)
    assert status == 200 and len(provider.seen) == 1 and provider.seen[0]["body"]["thinking"] == DECODING["thinking"]
    reserve, settle = rows(path)
    assert reserve["event"] == "reserve" and settle["event"] == "settle" and reserve["id"] == settle["id"]
    # the stub reports 1000 prompt and 200 completion tokens: 1000 * 0.27e-6 + 200 * 1.10e-6
    assert settle["usd"] == pytest.approx(0.00049) and settle["usage_known"] is True and settle["model"] == "deepseek-flash"
    assert ledger.scoped_usd() == pytest.approx(0.00049) and ledger.open_reservations() == 0


def test_past_the_cap_the_request_is_refused_with_402_and_never_forwarded(tmp_path, proxy):
    path = tmp_path / "ledger.jsonl"
    path.write_text(json.dumps({"run_id": "t-0", "usd": 0.99}) + "\n", encoding="utf-8")
    ledger = SpendLedgerV2(path, total_cap_usd=1.0, run_id="t-1", cap_scope="t")
    url, provider, _ = proxy(ledger)
    status, body = post(url, FLASH)                             # first-call reserve 0.02 > 0.01 left
    assert status == 402 and body["error"]["type"] == "arena_spend_cap"
    assert provider.seen == [] and len(rows(path)) == 1


def test_a_torn_ledger_under_the_scope_is_refused_with_402_where_version_1_forwarded(tmp_path, proxy):
    torn = json.dumps({"run_id": "t-0", "usd": 0.5}) + "\n" + '{"run_id": "t-9", "usd": 0.6'
    old_path, new_path = tmp_path / "v1.jsonl", tmp_path / "v2.jsonl"
    old_path.write_text(torn, encoding="utf-8")
    new_path.write_text(json.dumps({"run_id": "t-0", "usd": 0.5}) + "\n", encoding="utf-8")
    ledger = SpendLedgerV2(new_path, total_cap_usd=1.0, run_id="t-1", cap_scope="t")
    new_path.write_text(torn, encoding="utf-8")                 # torn after the proxy started
    url, provider, _ = proxy(ledger)
    status, body = post(url, FLASH)
    assert status == 402 and "torn" in body["error"]["message"] and provider.seen == []
    assert new_path.read_text(encoding="utf-8") == torn
    # the same file under version 1 authorises the call: 0.5 + 0.02 is below the 1.0 cap, the torn 0.6 is not counted
    SpendLedger(old_path, total_cap_usd=1.0, run_id="t-1", cap_scope="t").check(0.02)


def test_a_model_other_than_flash_is_refused_with_403_and_leaves_no_reservation(tmp_path, proxy):
    path = tmp_path / "ledger.jsonl"
    url, provider, _ = proxy(SpendLedgerV2(path, total_cap_usd=1.0, run_id="t-1", cap_scope="t", create=True))
    status, body = post(url, {"model": "deepseek-v4-pro", "messages": []})
    assert status == 403 and body["error"]["type"] == "model_not_authorised" and provider.seen == [] and rows(path) == []


def test_a_run_cap_refusal_leaves_no_reservation_behind(tmp_path, proxy):
    path = tmp_path / "ledger.jsonl"
    url, provider, _ = proxy(SpendLedgerV2(path, total_cap_usd=1.0, run_id="t-1", cap_scope="t", create=True), run_cap=0.01)
    status, body = post(url, FLASH)                             # first-call reserve 0.02 > run cap 0.01
    assert status == 402 and "this run" in body["error"]["message"] and provider.seen == [] and rows(path) == []


def test_an_answer_without_usage_is_charged_its_reservation(tmp_path, proxy):
    class NoUsage(Provider):
        pass

    provider = NoUsage(status=500)                              # an error body carries no usage
    path = tmp_path / "ledger.jsonl"
    ledger = SpendLedgerV2(path, total_cap_usd=1.0, run_id="t-1", cap_scope="t", create=True)
    url, _, _ = proxy(ledger, provider=provider)
    status, _ = post(url, FLASH)
    assert status == 500
    settle = rows(path)[-1]
    assert settle["event"] == "settle" and settle["usage_known"] is False and settle["usd"] == pytest.approx(0.02)


def test_serve_refuses_a_version_1_ledger(tmp_path):
    with pytest.raises(TypeError):
        fo2.serve("http://127.0.0.1:9", "k", 0, SpendLedger(tmp_path / "l.jsonl", total_cap_usd=1.0), None, DECODING)


def test_the_command_line_refuses_before_touching_the_key(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(fo2.mp, "load_key", lambda: pytest.fail("the key must not be loaded"))
    assert fo2.main(["--ledger", str(tmp_path / "l.jsonl"), "--total-cap-usd", "16"]) == 2
    assert fo2.main(["--ledger", str(tmp_path / "missing.jsonl"), "--total-cap-usd", "5"]) == 2
    assert "does not exist" in capsys.readouterr().err
    (tmp_path / "torn.jsonl").write_text('{"run_id": "proxy", "usd": 1', encoding="utf-8")
    assert fo2.main(["--ledger", str(tmp_path / "torn.jsonl"), "--total-cap-usd", "5"]) == 2
    assert fo2.main(["--ledger", str(tmp_path / "l.jsonl"), "--total-cap-usd", "5", "--cap-scope", "e1"]) == 2
    assert "outside cap_scope" in capsys.readouterr().err
