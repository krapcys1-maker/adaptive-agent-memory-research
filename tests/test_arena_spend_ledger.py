"""The night's shared budget, and the two ways a cap fails without one.

A per-run cap stops one run. It cannot stop five runs from each stopping politely
at their own ceiling and costing five times what was agreed. And a total kept in
a variable dies with the process that held it, so the next run starts from zero
and the agreement is gone.

Every test here is a way the money escapes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import FixedDecoding  # noqa: E402
from arena.spend_ledger import SpendLedger, TotalCapReached  # noqa: E402


class _Usage:
    prompt_tokens = 100
    completion_tokens = 10


class _Response:
    usage = _Usage()


class _Completions:
    def create(self, **kwargs):
        return _Response()


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class _Client:
    def __init__(self):
        self.chat = _Chat()


def test_the_total_is_read_from_the_file_not_from_memory(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path, run_id="first").record(1.25)
    later = SpendLedger(path, run_id="second")
    assert later.total_usd() == 1.25


def test_each_run_is_counted_separately_and_together(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path, run_id="cupmem").record(0.75)
    SpendLedger(path, run_id="hindsight").record(0.50)
    combined = SpendLedger(path)
    assert combined.by_run() == {"cupmem": 0.75, "hindsight": 0.5}
    assert combined.total_usd() == 1.25
    assert combined.total_usd(since_run="cupmem") == 0.75


def test_the_total_cap_refuses_before_the_request(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path, run_id="earlier").record(9.80)
    ledger = SpendLedger(path, total_cap_usd=10.0, run_id="later")
    with pytest.raises(TotalCapReached, match="Stopping below it"):
        ledger.check(reserve_usd=0.50)


def test_a_run_well_inside_the_total_proceeds(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path, run_id="earlier").record(2.0)
    SpendLedger(path, total_cap_usd=10.0, run_id="later").check(reserve_usd=0.5)


def test_no_total_cap_means_no_refusal(tmp_path: Path) -> None:
    ledger = SpendLedger(tmp_path / "ledger.jsonl", run_id="unbounded")
    ledger.record(1000.0)
    ledger.check(reserve_usd=1000.0)


def test_a_torn_final_line_is_charged_rather_than_skipped(tmp_path: Path) -> None:
    """A kill mid-write must not make the night look cheaper than it was.

    Under-counting is the safe direction for a floor and the dangerous one for a
    cap, so a partial line is charged at the most expensive rate seen.
    """
    path = tmp_path / "ledger.jsonl"
    ledger = SpendLedger(path, run_id="r")
    ledger.record(0.30)
    with path.open("a", encoding="utf-8") as handle:
        handle.write('{"run_id": "r", "usd": 0.3')  # killed mid-write
    assert SpendLedger(path).total_usd() == pytest.approx(0.60)


def test_the_provider_wrapper_writes_every_call_to_the_shared_total(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    client = FixedDecoding(_Client(), shared_ledger=SpendLedger(path, run_id="wired"))
    for _ in range(3):
        client.chat.completions.create(model="m", messages=[])
    assert SpendLedger(path).by_run() == {"wired": pytest.approx(client.spent_usd)}


def test_the_shared_total_stops_a_run_that_is_within_its_own_cap(tmp_path: Path) -> None:
    """The case a per-run cap alone cannot see.

    This run has spent nothing and its own ceiling is generous. The night is
    already spent, so it must not make a single call.
    """
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path, run_id="earlier").record(9.999)
    client = FixedDecoding(
        _Client(), spend_cap_usd=3.0,
        shared_ledger=SpendLedger(path, total_cap_usd=10.0, run_id="later"),
    )
    with pytest.raises(TotalCapReached):
        client.chat.completions.create(model="m", messages=[])
    assert client.request_log == []


def test_the_shared_total_is_checked_before_the_per_run_cap(tmp_path: Path) -> None:
    """Otherwise the last run spends its whole allowance discovering there is none."""
    path = tmp_path / "ledger.jsonl"
    SpendLedger(path, run_id="earlier").record(10.0)
    client = FixedDecoding(
        _Client(), spend_cap_usd=0.0000001,
        shared_ledger=SpendLedger(path, total_cap_usd=10.0, run_id="later"),
    )
    with pytest.raises(TotalCapReached):
        client.chat.completions.create(model="m", messages=[])


def test_the_summary_names_the_file_it_is_the_authority_for(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = SpendLedger(path, total_cap_usd=10.0, run_id="r")
    ledger.record(0.25)
    summary = ledger.summary()
    assert summary["total_usd"] == 0.25
    assert summary["total_cap_usd"] == 10.0
    assert summary["calls"] == 1
    assert summary["path"] == str(path)
