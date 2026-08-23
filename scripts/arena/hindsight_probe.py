"""The window into Hindsight's state, read over the same HTTP the adapter uses.

Their store is a database in another process, so the fingerprint is taken from
what the server will show: the bank's memory list, paged fully and sorted by id,
with the volatile fields dropped.

One ambiguity is recorded rather than resolved. Their server consolidates on a
background worker, so state can change after a query without the query having
caused it. A digest that moved is therefore evidence of *a* write, not of a
write by the recall path, and this probe says so rather than letting the arena
read a scheduler as a memory that learns.
"""

from __future__ import annotations

from typing import Any

from arena.operational_fit import digest

#: Fields that move without the state meaning anything different: retrieval
#: scores, and counters their consolidation touches.
VOLATILE = {"scores", "score", "proof_count", "updated_at", "last_accessed"}


class HindsightStateProbe:
    PAGE = 10_000

    def __init__(self, http: Any, bank: str = "arena-pilot") -> None:
        self._http = http
        self._bank = bank

    def _payload(self) -> dict[str, Any]:
        return self._http.call(
            "GET", f"/v1/default/banks/{self._bank}/memories/list?limit={self.PAGE}")

    def _items(self) -> list[dict[str, Any]]:
        payload = self._payload()
        items = [i for i in (payload.get("items") or []) if isinstance(i, dict)]
        total = payload.get("total")
        if isinstance(total, int) and total > len(items):
            raise RuntimeError(
                f"Hindsight state probe read {len(items)} of {total} memories, so the "
                "fingerprint would cover less than the state. Raise PAGE rather than "
                "measuring a prefix."
            )
        return items

    def fingerprint(self) -> str:
        return digest(sorted(
            ({k: v for k, v in item.items() if k not in VOLATILE} for item in self._items()),
            key=lambda item: str(item.get("id", "")),
        ))

    def stored_times(self) -> list[str]:
        return [str(item.get("date") or item.get("mentioned_at") or "")
                for item in self._items()]

    def stored_ids(self) -> list[str]:
        return [str(item.get("id", "")) for item in self._items() if item.get("id")]
