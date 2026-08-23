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

from pathlib import Path
from typing import Any

from arena.spend_ledger import SpendLedger


#: The arena's decoding, applied to every system alike.
#:
#: Its provenance is stated because it changes how it may be read. This was NOT
#: preregistered. It was introduced after a CUPMem run showed a repeated probe
#: returning different answers, so it is a control adopted in response to an
#: observation, not before one. It is kept because holding decoding constant is
#: what makes two systems' numbers the same kind of number — not because it makes
#: any system reproducible, which it measurably does not.
#:
#: It is not the instrument for the question it was first reached for. Whether a
#: query mutates memory is settled by a state fingerprint, not by making two
#: answers match.
ARENA_DECODING: dict[str, Any] = {"temperature": 0}

#: DeepSeek list price per million tokens, for the cap below.
PRICE_PER_MTOK = {"input": 0.27, "output": 1.10}


class SpendCapReached(RuntimeError):
    """Raised instead of making the request that would cross the cap.

    Before, not after. A cap checked after the fact is a report of an overspend,
    and this project is funded out of someone's pocket.
    """


class _Completions:
    def __init__(self, inner: Any, fixed: dict[str, Any], calls: list[dict[str, Any]],
                 owner: "FixedDecoding"):
        self._inner, self._fixed, self._calls = inner, fixed, calls
        self._owner = owner

    def create(self, **kwargs: Any) -> Any:
        self._owner.check_cap()
        # The system's own kwargs lose to the arena's. A system that pins its own
        # temperature would otherwise silently opt out of the control, and the
        # override is recorded rather than swallowed so the divergence is visible.
        overridden = {k: kwargs[k] for k in self._fixed if k in kwargs
                      and kwargs[k] != self._fixed[k]}
        response = self._inner.create(**{**kwargs, **self._fixed})
        usage = getattr(response, "usage", None)
        self._calls.append({
            "model": kwargs.get("model"),
            # What the system asked for, beside what the arena enforced. Both, so
            # a reader can tell a system's own decoding from the arena's.
            "requested": {k: kwargs.get(k) for k in self._fixed},
            "enforced": dict(self._fixed),
            "overridden": overridden,
            # Per call, not per run. A background run once died after 29 calls
            # with no result file, and the spend was still real.
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        })
        if self._owner.shared_ledger is not None:
            self._owner.shared_ledger.record(
                self._owner.call_cost(self._calls[-1]),
                model=kwargs.get("model"),
                prompt_tokens=self._calls[-1]["prompt_tokens"],
                completion_tokens=self._calls[-1]["completion_tokens"],
            )
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _Chat:
    def __init__(self, inner: Any, fixed: dict[str, Any], calls: list[dict[str, Any]],
                 owner: "FixedDecoding"):
        self._inner = inner
        self.completions = _Completions(inner.completions, fixed, calls, owner)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class FixedDecoding:
    """An OpenAI-compatible client that cannot be talked out of its decoding.

    Attribute access falls through to the real client, so anything the system
    uses that is not `chat.completions.create` behaves exactly as before.
    """

    def __init__(self, inner: Any, fixed: dict[str, Any] | None = None,
                 spend_cap_usd: float | None = None,
                 first_call_reserve_usd: float = 0.01,
                 shared_ledger: SpendLedger | None = None):
        self._inner = inner
        self.fixed = dict(ARENA_DECODING if fixed is None else fixed)
        #: One entry per request, carrying what was asked, what was enforced, and
        #: what it cost.
        self.request_log: list[dict[str, Any]] = []
        self.spend_cap_usd = spend_cap_usd
        self._first_call_reserve = first_call_reserve_usd
        #: The night's shared total, if one was opened. A per-run cap stops one
        #: run; it cannot stop five runs from each stopping politely at their own
        #: ceiling and costing five times what was agreed.
        self.shared_ledger = shared_ledger
        self.chat = _Chat(inner.chat, self.fixed, self.request_log, self)

    # ------------------------------------------------------------------- money

    def call_cost(self, call: dict[str, Any]) -> float:
        return (call["prompt_tokens"] / 1e6 * PRICE_PER_MTOK["input"]
                + call["completion_tokens"] / 1e6 * PRICE_PER_MTOK["output"])

    @property
    def spent_usd(self) -> float:
        return sum(self.call_cost(call) for call in self.request_log)

    def check_cap(self) -> None:
        """Refuse the next request if it could cross the cap.

        The cost of a request is not known until it returns, so the cap is
        enforced with a reserve: the most expensive call seen so far, with half
        again for headroom. That stops *below* the limit rather than just past
        it, which is the only version of a hard cap worth the name.
        """
        seen = [self.call_cost(call) for call in self.request_log]
        reserve = max(seen) * 1.5 if seen else self._first_call_reserve
        # The shared total first: exhausting the night's budget stops every run,
        # and finding that out from the per-run cap would mean the last run
        # spends its whole allowance discovering there was none left.
        if self.shared_ledger is not None:
            self.shared_ledger.check(reserve)
        if self.spend_cap_usd is None:
            return
        if self.spent_usd + reserve > self.spend_cap_usd:
            raise SpendCapReached(
                f"spent ${self.spent_usd:.4f} over {len(self.request_log)} calls; the "
                f"next could cost up to ${reserve:.4f} and the cap is "
                f"${self.spend_cap_usd:.2f}. Stopping below it rather than past it."
            )

    @property
    def overrides(self) -> list[dict[str, Any]]:
        """Requests where the system asked for decoding the arena refused."""
        return [call for call in self.request_log if call["overridden"]]

    @property
    def ledger(self) -> dict[str, int]:
        """This run's own call ledger, which the system cannot reset.

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
