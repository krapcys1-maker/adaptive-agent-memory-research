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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import ARENA_DECODING, FixedDecoding  # noqa: E402


class _Completions:
    def __init__(self) -> None:
        self.seen: list[dict] = []

    def create(self, **kwargs):
        self.seen.append(kwargs)
        return {"ok": True}

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
    assert client.overrides == [{"model": "m", "overridden": {"temperature": 0.7}}]
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
