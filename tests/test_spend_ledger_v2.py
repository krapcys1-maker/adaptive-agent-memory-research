"""arena/spend_ledger_v2.py: the shared cap refuses whenever it cannot read what was already spent.

The first test reproduces the version-1 defect on the unchanged frozen module; the rest show that
version 2 refuses the same ledger, refuses past the cap, refuses every kind of damaged ledger
without changing it, and settles correctly. No network, no model.
"""
from __future__ import annotations

import json
import math
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.spend_ledger import SpendLedger, TotalCapReached  # noqa: E402
from arena.spend_ledger_v2 import LedgerUnreadable, SpendLedgerV2, parse  # noqa: E402

GOOD = json.dumps({"run_id": "e1-a", "usd": 1.0}) + "\n"
TORN = '{"run_id": "e1-b", "usd": 2.5'                       # a write killed before its end


def ledger_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(text.encode("utf-8"))
    return path


def v2(path: Path, cap: float = 3.0, run_id: str = "e1-c", scope: str | None = "e1", **kw) -> SpendLedgerV2:
    return SpendLedgerV2(path, total_cap_usd=cap, run_id=run_id, cap_scope=scope, **kw)


# ----------------------------------------------------------------------------- the reproduced defect

def test_version_1_lets_a_call_through_when_a_torn_line_hides_under_the_scope(tmp_path):
    """The defect, on the frozen module as it is: $1.00 + torn $2.50 spent, yet $1.90 more passes a $3.00 cap."""
    old = SpendLedger(ledger_file(tmp_path, GOOD + TORN), total_cap_usd=3.0, run_id="e1-c", cap_scope="e1")
    assert old.scoped_usd() == 1.0                              # the torn line counts zero in the scope
    old.check(1.9)                                              # no exception: authorised


def test_version_2_refuses_the_same_ledger_at_construction_and_at_check(tmp_path):
    path = ledger_file(tmp_path, GOOD + TORN)
    with pytest.raises(LedgerUnreadable, match="newline"):
        v2(path)
    path.write_bytes((GOOD + TORN + "\n").encode())             # even once the line ends, it is not JSON
    with pytest.raises(LedgerUnreadable, match="not valid JSON"):
        v2(path)


def test_an_unreadable_ledger_is_a_cap_refusal_so_the_frozen_proxy_answers_402():
    assert issubclass(LedgerUnreadable, TotalCapReached)


# ----------------------------------------------------------------------------- the cap

def test_the_cap_refuses_before_the_call_and_writes_nothing(tmp_path):
    path = ledger_file(tmp_path, GOOD)
    ledger = v2(path)
    before = path.read_bytes()
    with pytest.raises(TotalCapReached, match="Stopping below it"):
        ledger.check(2.01)                                      # 1.00 + 2.01 > 3.00
    assert path.read_bytes() == before


def test_the_cap_is_inclusive_and_open_reservations_count(tmp_path):
    ledger = v2(ledger_file(tmp_path, GOOD))
    ledger.check(1.5)                                           # 1.00 + 1.50 <= 3.00
    assert ledger.scoped_usd() == 2.5 and ledger.open_reservations() == 1
    ledger.check(0.5)                                           # exactly 3.00
    with pytest.raises(TotalCapReached):
        ledger.check(0.01)


def test_a_second_process_sees_the_first_ones_reservation(tmp_path):
    path = ledger_file(tmp_path, "")
    first, second = v2(path, cap=1.0), v2(path, cap=1.0, run_id="e1-d")
    first.check(0.6)
    with pytest.raises(TotalCapReached):
        second.check(0.6)                                       # version 1 would have let both through


def test_concurrent_checks_never_authorise_more_than_the_cap(tmp_path):
    path = ledger_file(tmp_path, "")
    ledgers = [v2(path, cap=1.0, run_id=f"e1-{i}") for i in range(4)]
    granted, refused = [], []

    def worker(ledger):
        for _ in range(10):
            try:
                ledger.check(0.1)
                granted.append(1)
            except TotalCapReached:
                refused.append(1)

    threads = [threading.Thread(target=worker, args=(ledger,)) for ledger in ledgers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(granted) == 10 and len(refused) == 30
    assert ledgers[0].scoped_usd() == pytest.approx(1.0)


def test_scope_counts_its_own_runs_including_version_1_lines(tmp_path):
    text = "".join(json.dumps(r) + "\n" for r in ({"run_id": "e1-a", "usd": 1.0}, {"run_id": "other", "usd": 50.0},
                                                    {"run_id": "e1-b", "usd": 0.25}))
    ledger = v2(ledger_file(tmp_path, text))
    assert ledger.scoped_usd() == 1.25 and ledger.total_usd() == 51.25
    assert ledger.by_run() == {"e1-a": 1.0, "other": 50.0, "e1-b": 0.25}


# ----------------------------------------------------------------------------- damaged ledgers

DAMAGED = {
    "torn last line": GOOD + TORN,
    "invalid JSON in the middle": GOOD + "{nope}\n" + GOOD,
    "not an object": GOOD + "[1, 2]\n",
    "missing run_id": json.dumps({"usd": 0.5}) + "\n",
    "empty run_id": json.dumps({"run_id": "", "usd": 0.5}) + "\n",
    "missing usd": json.dumps({"run_id": "e1-a"}) + "\n",
    "negative usd": json.dumps({"run_id": "e1-a", "usd": -1}) + "\n",
    "NaN usd": '{"run_id": "e1-a", "usd": NaN}\n',
    "infinite usd": '{"run_id": "e1-a", "usd": Infinity}\n',
    "boolean usd": json.dumps({"run_id": "e1-a", "usd": True}) + "\n",
    "string usd": json.dumps({"run_id": "e1-a", "usd": "0.5"}) + "\n",
    "unknown version": json.dumps({"v": 3, "event": "reserve", "id": "x", "run_id": "e1-a", "usd": 0.1}) + "\n",
    "unknown event": json.dumps({"v": 2, "event": "refund", "id": "x", "run_id": "e1-a", "usd": 0.1}) + "\n",
    "another ledger format": json.dumps({"event": "reserve", "key": "k", "model": "deepseek-flash", "usd": 0.004}) + "\n",
    "settlement without reservation": json.dumps({"v": 2, "event": "settle", "id": "x", "run_id": "e1-a", "usd": 0.1}) + "\n",
    "reservation id twice": 2 * (json.dumps({"v": 2, "event": "reserve", "id": "x", "run_id": "e1-a", "usd": 0.1}) + "\n"),
    "settled twice": "".join(json.dumps(r) + "\n" for r in (
        {"v": 2, "event": "reserve", "id": "x", "run_id": "e1-a", "usd": 0.1},
        {"v": 2, "event": "settle", "id": "x", "run_id": "e1-a", "usd": 0.1},
        {"v": 2, "event": "settle", "id": "x", "run_id": "e1-a", "usd": 0.1})),
    "settled under another run": "".join(json.dumps(r) + "\n" for r in (
        {"v": 2, "event": "reserve", "id": "x", "run_id": "e1-a", "usd": 0.1},
        {"v": 2, "event": "settle", "id": "x", "run_id": "e1-b", "usd": 0.1})),
}


@pytest.mark.parametrize("name", sorted(DAMAGED))
def test_every_damaged_ledger_refuses_and_stays_byte_identical(tmp_path, name):
    good = ledger_file(tmp_path, GOOD)
    ledger = v2(good)                                           # constructed while the file was readable
    good.write_bytes(DAMAGED[name].encode("utf-8"))
    before = good.read_bytes()
    with pytest.raises(LedgerUnreadable):
        ledger.check(0.01)
    with pytest.raises(LedgerUnreadable):
        ledger.scoped_usd()
    with pytest.raises(LedgerUnreadable):
        v2(good)
    assert good.read_bytes() == before


def test_damage_in_another_scope_still_refuses(tmp_path):
    """The point of the fix: a line that cannot be attributed might belong to this scope."""
    path = ledger_file(tmp_path, json.dumps({"run_id": "other-x", "usd": 1.0}) + "\n" + '{"run_id": "other-y", "usd"\n')
    with pytest.raises(LedgerUnreadable):
        v2(path, scope="e1")


def test_non_utf8_bytes_refuse(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(GOOD.encode() + b"\xff\xfe\n")
    with pytest.raises(LedgerUnreadable, match="UTF-8"):
        v2(path)


def test_a_missing_ledger_is_refused_unless_a_new_one_is_asked_for(tmp_path):
    with pytest.raises(LedgerUnreadable, match="does not exist"):
        v2(tmp_path / "typo.jsonl")
    assert not (tmp_path / "typo.jsonl").exists()
    ledger = v2(tmp_path / "new" / "ledger.jsonl", create=True)
    assert ledger.scoped_usd() == 0.0


def test_a_held_lock_refuses_instead_of_waiting_forever(tmp_path):
    path = ledger_file(tmp_path, GOOD)
    ledger = v2(path, lock_timeout_s=0.2)
    (tmp_path / "ledger.jsonl.lock").write_text("12345")
    with pytest.raises(LedgerUnreadable, match="is held"):
        ledger.check(0.01)
    assert path.read_bytes() == GOOD.encode()


def test_construction_refuses_unusable_settings(tmp_path):
    path = ledger_file(tmp_path, "")
    for cap in (0, -1, float("nan"), float("inf"), None, True):
        with pytest.raises(ValueError):
            SpendLedgerV2(path, total_cap_usd=cap, run_id="e1-a", cap_scope="e1")
    with pytest.raises(ValueError, match="outside cap_scope"):
        SpendLedgerV2(path, total_cap_usd=1.0, run_id="proxy", cap_scope="e1")
    with pytest.raises(ValueError):
        SpendLedgerV2(path, total_cap_usd=1.0, run_id="")


# ----------------------------------------------------------------------------- settlement

def test_a_settled_call_counts_its_reported_cost_not_its_reservation(tmp_path):
    path = ledger_file(tmp_path, "")
    ledger = v2(path)
    ident = ledger.check(0.5)
    assert ledger.scoped_usd() == 0.5
    ledger.record(0.12, usage_known=True, prompt_tokens=100, completion_tokens=20, model="deepseek-flash", via="proxy")
    assert ledger.scoped_usd() == 0.12 and ledger.open_reservations() == 0
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [r["event"] for r in rows] == ["reserve", "settle"] and rows[0]["id"] == rows[1]["id"] == ident
    assert rows[1]["reported_usd"] == 0.12 and rows[1]["reserved_usd"] == 0.5 and rows[1]["prompt_tokens"] == 100


def test_unknown_usage_is_charged_at_least_its_reservation(tmp_path):
    ledger = v2(ledger_file(tmp_path, ""))
    ledger.check(0.5)
    ledger.record(0.0, usage_known=False)
    assert ledger.scoped_usd() == 0.5
    ledger.check(0.5)
    ledger.record(0.7)                                          # usage not reported as known: the larger amount
    assert ledger.scoped_usd() == 1.2
    ledger.check(0.5)
    ledger.record(float("nan"), usage_known=True)               # an unusable amount is an unknown cost
    assert ledger.scoped_usd() == 1.7


def test_the_cheapest_reservation_is_settled_first_so_what_stays_open_is_not_understated(tmp_path):
    ledger = v2(ledger_file(tmp_path, ""))
    ledger.check(0.02)
    ledger.check(0.30)
    ledger.record(0.01, usage_known=True)                       # one of the two answered; which one is not known
    assert ledger.scoped_usd() == pytest.approx(0.31)           # 0.01 settled + the larger 0.30 still open


def test_a_crash_in_flight_leaves_the_reservation_counted_for_everyone(tmp_path):
    path = ledger_file(tmp_path, "")
    v2(path).check(0.4)                                         # the process dies before record()
    assert v2(path, run_id="e1-z").scoped_usd() == 0.4


def test_a_call_recorded_without_a_reservation_is_charged_not_lost(tmp_path):
    path = ledger_file(tmp_path, "")
    ledger = v2(path)
    ledger.record(0.05, usage_known=True)
    assert ledger.scoped_usd() == 0.05
    assert json.loads(path.read_text(encoding="utf-8"))["event"] == "charge"


def test_a_record_behind_an_unreadable_line_is_refused_and_appends_nothing(tmp_path):
    path = ledger_file(tmp_path, "")
    ledger = v2(path)
    ledger.check(0.1)
    with path.open("ab") as handle:
        handle.write(TORN.encode())
    before = path.read_bytes()
    with pytest.raises(LedgerUnreadable):
        ledger.record(0.05, usage_known=True)
    assert path.read_bytes() == before


def test_the_written_lines_parse_back_and_summary_names_the_format(tmp_path):
    path = ledger_file(tmp_path, GOOD)
    ledger = v2(path)
    ledger.check(0.2)
    ledger.record(0.1, usage_known=True)
    state = parse(path.read_text(encoding="utf-8"))
    assert state.lines == 3 and not state.open
    summary = ledger.summary()
    assert summary["format"] == "spend-ledger-v2" and summary["scoped_usd"] == 1.1 and summary["open_reservations"] == 0


# ----------------------------------------------------------------------------- the ledgers already in the repository

@pytest.mark.parametrize("relative", ["data/lab/aam-deepseek-2026-11/spend-ledger.jsonl", "data/lab/arena/spend-ledger.jsonl"])
def test_committed_version_1_ledgers_read_to_the_same_totals(relative):
    """Same total as version 1, and per run the exact sum (version 1's by_run rounds at every addition and drifts)."""
    path = ROOT / relative
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    new = parse(path.read_text(encoding="utf-8"), relative)
    assert not new.open and new.lines == len(rows)
    assert float(sum(u for _, u in new.settled)) == pytest.approx(SpendLedger(path, run_id="read-only").total_usd(), abs=1e-6)
    for run in {r["run_id"] for r in rows}:
        exact = math.fsum(r["usd"] for r in rows if r["run_id"] == run)
        assert float(sum(u for r, u in new.settled if r == run)) == pytest.approx(exact, abs=1e-9)


@pytest.mark.parametrize("relative", ["data/lab/api-screening/budget-ledger.jsonl", "data/lab/hard-memory-external-v1/api-ledger.jsonl",
                                      "data/lab/reader-model-compare-v1/api-spend-ledger.jsonl"])
def test_ledgers_of_other_formats_are_refused_not_misread(relative):
    with pytest.raises(LedgerUnreadable):
        parse((ROOT / relative).read_text(encoding="utf-8"), relative)
