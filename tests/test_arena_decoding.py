"""Decoding is a condition of the arena, so it is fixed before any result exists.

A transplant table is void unless every arm ran on one harness, and how tokens
were drawn is part of the harness. This is the same class of control as fixing
the model and the embedder — not tuning, which would be changing a system
because the arena showed it doing badly.

It wraps rather than patches, so nothing in a system's own checkout differs from
the commit its provenance record names.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import ARENA_DECODING, FixedDecoding, SpendCapReached  # noqa: E402


class _Usage:
    prompt_tokens = 100
    completion_tokens = 10


class _Response:
    usage = _Usage()


class _Completions:
    def __init__(self) -> None:
        self.seen: list[dict] = []

    def create(self, **kwargs):
        self.seen.append(kwargs)
        return _Response()

    def other_method(self) -> str:
        return "untouched"


class _Chat:
    def __init__(self) -> None:
        self.completions = _Completions()


class _Client:
    def __init__(self) -> None:
        self.chat = _Chat()
        self.api_key = "sk-not-a-real-key"

    def some_other_surface(self) -> str:
        return "untouched"


def test_the_arena_decoding_is_declared_before_any_result() -> None:
    """Freeze before measuring. After seeing a number it is easy to prefer another."""
    assert ARENA_DECODING == {"temperature": 0}


def test_every_request_carries_the_fixed_decoding() -> None:
    client = FixedDecoding(_Client())
    client.chat.completions.create(model="m", messages=[])
    assert client._inner.chat.completions.seen[0]["temperature"] == 0


def test_a_system_setting_its_own_temperature_loses() -> None:
    """Otherwise one system silently opts out of the control the others are under."""
    client = FixedDecoding(_Client())
    client.chat.completions.create(model="m", messages=[], temperature=0.7)
    assert client._inner.chat.completions.seen[0]["temperature"] == 0


def test_an_override_is_recorded_rather_than_swallowed() -> None:
    """A divergence the arena resolved is still a fact about the system."""
    client = FixedDecoding(_Client())
    client.chat.completions.create(model="m", messages=[], temperature=0.7)
    client.chat.completions.create(model="m", messages=[])
    assert [c["overridden"] for c in client.overrides] == [{"temperature": 0.7}]
    assert len(client.request_log) == 2


def test_a_system_already_asking_for_the_fixed_value_is_not_an_override() -> None:
    client = FixedDecoding(_Client())
    client.chat.completions.create(model="m", messages=[], temperature=0)
    assert client.overrides == []


def test_everything_else_reaches_the_real_client_untouched() -> None:
    """A wrapper that hid part of the surface would change the system under test."""
    client = FixedDecoding(_Client())
    assert client.some_other_surface() == "untouched"
    assert client.chat.completions.other_method() == "untouched"
    assert client.api_key == "sk-not-a-real-key"


def test_the_fixed_parameters_can_be_stated_explicitly() -> None:
    client = FixedDecoding(_Client(), {"temperature": 0, "top_p": 1})
    client.chat.completions.create(model="m", messages=[])
    sent = client._inner.chat.completions.seen[0]
    assert sent["temperature"] == 0 and sent["top_p"] == 1


# ------------------------------------------------------------------- the ledger


def test_the_ledger_counts_every_request_the_run_made() -> None:
    client = FixedDecoding(_Client())
    for _ in range(3):
        client.chat.completions.create(model="m", messages=[])
    assert client.ledger == {"calls": 3, "prompt_tokens": 300, "completion_tokens": 30}


def test_the_ledger_survives_what_the_system_can_reset() -> None:
    """The bug this exists for, stated as a test.

    CUPMem's own counter is cleared by `reset_usage_tracking`, and the adapter
    calls it on every reset so ingest and query price separately. A run total
    read from that counter reported four calls for a run that made seventy-one.
    """
    client = FixedDecoding(_Client())
    client.chat.completions.create(model="m", messages=[])

    class SystemThatResets:
        def __init__(self, provider): self.client, self._n = provider, 0
        def reset_usage_tracking(self): self._n = 0
        def get_usage_summary(self): return {"total_calls": self._n}

    system = SystemThatResets(client)
    system.reset_usage_tracking()

    assert system.get_usage_summary()["total_calls"] == 0
    assert client.ledger["calls"] == 1


def test_a_response_without_usage_counts_the_call_and_no_tokens() -> None:
    """Unknown tokens are not zero tokens, but an uncounted call is a lost call."""
    class NoUsage:
        usage = None

    class Bare(_Completions):
        def create(self, **kwargs):
            self.seen.append(kwargs)
            return NoUsage()

    client = FixedDecoding(_Client())
    client.chat.completions._inner = Bare()
    client.chat.completions.create(model="m", messages=[])
    assert client.ledger == {"calls": 1, "prompt_tokens": 0, "completion_tokens": 0}


# --------------------------------------------------------------------- the cap


def test_no_cap_means_no_refusal() -> None:
    client = FixedDecoding(_Client())
    for _ in range(50):
        client.chat.completions.create(model="m", messages=[])
    assert len(client.request_log) == 50


def test_the_cap_refuses_before_crossing_rather_than_reporting_after() -> None:
    """A cap checked after the fact is a report of an overspend.

    Each call here costs 100 prompt and 10 completion tokens: $0.000027 +
    $0.000011 = $0.000038. A cap of $0.0002 buys five, and the reserve stops the
    sixth while still under the line.
    """
    client = FixedDecoding(_Client(), spend_cap_usd=0.0002,
                           first_call_reserve_usd=0.00004)
    made = 0
    with pytest.raises(SpendCapReached):
        for _ in range(100):
            client.chat.completions.create(model="m", messages=[])
            made += 1
    assert 0 < made < 100
    assert client.spent_usd < client.spend_cap_usd


def test_the_reserve_comes_from_the_most_expensive_call_seen() -> None:
    """The next call's cost is unknowable, so the bound is the worst one so far."""
    client = FixedDecoding(_Client(), spend_cap_usd=1.0)
    client.chat.completions.create(model="m", messages=[])
    one_call = client.spent_usd
    # Cap set just above what is spent, with no room for another call of that size.
    client.spend_cap_usd = one_call * 1.2
    with pytest.raises(SpendCapReached, match="Stopping below it"):
        client.chat.completions.create(model="m", messages=[])


def test_a_cap_smaller_than_the_first_call_reserve_stops_immediately() -> None:
    """Nothing is spent at all, rather than one call's worth being spent to find out."""
    client = FixedDecoding(_Client(), spend_cap_usd=0.001, first_call_reserve_usd=0.01)
    with pytest.raises(SpendCapReached):
        client.chat.completions.create(model="m", messages=[])
    assert client.request_log == []


def test_what_the_system_asked_for_is_recorded_beside_what_was_enforced() -> None:
    """Native decoding and arena decoding are different facts and both are wanted."""
    client = FixedDecoding(_Client())
    client.chat.completions.create(model="m", messages=[], temperature=0.3)
    call = client.request_log[0]
    assert call["requested"] == {"temperature": 0.3}
    assert call["enforced"] == {"temperature": 0}
    assert call["overridden"] == {"temperature": 0.3}
