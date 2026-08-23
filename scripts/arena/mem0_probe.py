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
        payload = self._memory.get_all(user_id=self._bank)
        if isinstance(payload, dict):
            payload = payload.get("results") or []
        return [item for item in (payload or []) if isinstance(item, dict)]

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
