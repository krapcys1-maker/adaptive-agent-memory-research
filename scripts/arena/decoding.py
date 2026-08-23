"""Hold decoding constant across every system in the arena.

A transplant table is void unless every arm ran under one harness, and decoding
is part of the harness. If CUPMem samples at the provider default while the next
system pins a temperature, a difference between them is partly a difference in
how their tokens were drawn.

This is not tuning a competitor. Tuning would be changing what a system does
because the arena showed it doing it badly. Fixing temperature is the same class
of control as fixing the model and the embedder: a condition the comparison
holds still, declared before any result exists.

It wraps rather than patches
----------------------------
The system under test keeps its own source. This sits between it and the
provider, so nothing in `cup_mem/` differs from the commit the provenance record
names, and the same wrapper serves the next four systems.

What it does not promise
------------------------
Temperature zero is not a determinism guarantee. Providers batch, route and
reorder, and floating-point reduction order is not fixed by any API parameter.
So this reduces variance; whether repeated calls actually agree is *measured*
and reported, never assumed. Assuming it is how a nondeterministic result gets
read as a mutating store.
"""

from __future__ import annotations

from typing import Any


#: Declared before any result exists, per the freeze-before-measuring rule.
ARENA_DECODING: dict[str, Any] = {"temperature": 0}


class _Completions:
    def __init__(self, inner: Any, fixed: dict[str, Any], calls: list[dict[str, Any]]):
        self._inner, self._fixed, self._calls = inner, fixed, calls

    def create(self, **kwargs: Any) -> Any:
        # The system's own kwargs lose to the arena's. A system that pins its own
        # temperature would otherwise silently opt out of the control, and the
        # override is recorded rather than swallowed so the divergence is visible.
        overridden = {k: kwargs[k] for k in self._fixed if k in kwargs
                      and kwargs[k] != self._fixed[k]}
        response = self._inner.create(**{**kwargs, **self._fixed})
        usage = getattr(response, "usage", None)
        self._calls.append({
            "model": kwargs.get("model"),
            "overridden": overridden,
            # Per call, not per run. A background run once died after 29 calls
            # with no result file, and the spend was still real.
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        })
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _Chat:
    def __init__(self, inner: Any, fixed: dict[str, Any], calls: list[dict[str, Any]]):
        self._inner = inner
        self.completions = _Completions(inner.completions, fixed, calls)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class FixedDecoding:
    """An OpenAI-compatible client that cannot be talked out of its decoding.

    Attribute access falls through to the real client, so anything the system
    uses that is not `chat.completions.create` behaves exactly as before.
    """

    def __init__(self, inner: Any, fixed: dict[str, Any] | None = None):
        self._inner = inner
        self.fixed = dict(ARENA_DECODING if fixed is None else fixed)
        #: One entry per request, carrying any system-set value this overrode.
        self.request_log: list[dict[str, Any]] = []
        self.chat = _Chat(inner.chat, self.fixed, self.request_log)

    @property
    def overrides(self) -> list[dict[str, Any]]:
        """Requests where the system asked for decoding the arena refused."""
        return [call for call in self.request_log if call["overridden"]]

    @property
    def ledger(self) -> dict[str, int]:
        """The arena's own spend ledger, which the system cannot reset.

        CUPMem's tracker is cleared by `reset_usage_tracking`, and the adapter
        calls it on every `reset()` so that ingest and query are priced
        separately. Reading a *run* total off that counter therefore reports
        whatever happened after the last reset — four calls for a run that made
        seventy-one. Both numbers are wanted, so both are kept, in ledgers with
        different owners and different lifetimes.
        """
        return {
            "calls": len(self.request_log),
            "prompt_tokens": sum(c["prompt_tokens"] for c in self.request_log),
            "completion_tokens": sum(c["completion_tokens"] for c in self.request_log),
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
