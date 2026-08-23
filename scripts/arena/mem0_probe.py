"""The window into Mem0's state that operational fit needs, and nothing more.

Kept out of the adapter for the same reason CUPMem's is: an adapter that could
see internals would start translating from them, and the contract's whole value
is that it translates from a return shape.

Duck-typed — nothing here imports `mem0` — so the suite runs with the venv
absent, which it is, because it is a local cache and not part of this repository.
"""

from __future__ import annotations

from typing import Any

from arena.operational_fit import digest


class Mem0StateProbe:
    """Everything stored under one bank, hashed as one value.

    Mem0 scopes memories by id rather than by store, so the state that matters
    for a reset is the contents of the bank the arena writes to. Fingerprinting
    the whole database would fold in other scopes and report a change that the
    arena did not cause.
    """

    #: `get_all` defaults to `limit=100` and returns a truncated page without
    #: saying so. A first version of this probe took that default, so the
    #: fingerprint covered the first hundred rows of a store that held more,
    #: `stored_items` reported exactly 100 for every unit, and a query that wrote
    #: to row 101 would have read as read-only. A partial fingerprint cannot
    #: establish read-only, which is the whole reason this class exists.
    PAGE = 100_000

    def __init__(self, memory: Any, bank: str = "arena-pilot") -> None:
        self._memory = memory
        self._bank = bank
        if not callable(getattr(memory, "get_all", None)):
            raise AttributeError(
                "Mem0 state probe expects get_all() on the Memory and did not find "
                "it. The fingerprint would cover less than the state, and a partial "
                "fingerprint cannot establish read-only."
            )

    def _items(self) -> list[dict[str, Any]]:
        payload = self._memory.get_all(user_id=self._bank, limit=self.PAGE)
        if isinstance(payload, dict):
            payload = payload.get("results") or []
        items = [item for item in (payload or []) if isinstance(item, dict)]
        if len(items) >= self.PAGE:
            # Truncated again. Raising is the only honest option: silently
            # fingerprinting a page would go back to reporting read-only for a
            # store whose tail was never looked at.
            raise RuntimeError(
                f"Mem0 state probe read {len(items)} rows at its page limit, so the "
                "store may be larger than the fingerprint covers. Raise PAGE rather "
                "than measuring a prefix."
            )
        return items

    def fingerprint(self) -> str:
        # Sorted by id, because their store returns rows in whatever order the
        # backend produced and ordering is not part of the state. A fingerprint
        # that changed with row order would report a mutation on every query.
        return digest(sorted(
            ({k: v for k, v in item.items() if k not in {"score"}} for item in self._items()),
            key=lambda item: str(item.get("id", "")),
        ))

    def stored_times(self) -> list[str]:
        return [str((item.get("metadata") or {}).get("timestamp", ""))
                for item in self._items()]

    def stored_ids(self) -> list[str]:
        return [str(item.get("id", "")) for item in self._items() if item.get("id")]
