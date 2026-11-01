"""flash_only_proxy.py: only the authorised model is forwarded; anything else is refused before any spend. A stub plays the provider."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import flash_only_proxy as fo  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402
from test_paid_api_plumbing import Provider, post  # noqa: E402


def test_the_authorised_model_is_forwarded_and_any_other_is_refused_without_reaching_the_provider(tmp_path: Path) -> None:
    provider = Provider()
    ledger = SpendLedger(tmp_path / "ledger.jsonl", total_cap_usd=1.0, run_id="t", cap_scope="t")
    server, state = fo.serve(provider.url, "dummy-upstream-key", 0, ledger, None, {"thinking": {"type": "disabled"}})
    url = "http://127.0.0.1:%d/v1/chat/completions" % server.server_address[1]
    try:
        allowed = post(url, {"model": "deepseek-flash", "temperature": 0.8, "messages": [{"role": "user", "content": "hi"}]})
        refused = [post(url, {"model": name, "messages": []}) for name in ("deepseek-v4-pro", "deepseek-flash-extra", "")]
        no_model = post(url, {"messages": []})
    finally:
        server.shutdown()
        provider.close()
    assert allowed[0] == 200 and len(provider.seen) == 1
    assert provider.seen[0]["body"]["model"] == "deepseek-flash" and provider.seen[0]["body"]["temperature"] == 0.8
    assert provider.seen[0]["body"]["thinking"] == {"type": "disabled"} and provider.seen[0]["auth"] == "Bearer dummy-upstream-key"
    assert all(status == 403 and body["error"]["type"] == "model_not_authorised" for status, body in refused + [no_model])
    assert len(provider.seen) == 1                                           # nothing else reached the provider
    assert len((tmp_path / "ledger.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_the_command_line_keeps_the_owners_budget_ceiling(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert fo.main(["--ledger", str(tmp_path / "l.jsonl"), "--total-cap-usd", "16"]) == 2
    assert "refusing" in capsys.readouterr().err
