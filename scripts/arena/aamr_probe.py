"""The window into the reference adapter's state.

Trivial, and included for a reason that is not trivial: without it the pilot
records `query_mutates_state: unknown` for a system whose entire state is one
dictionary this repository owns. Unknown is the honest answer when nothing can
be observed, and the wrong answer when something can.
"""

from __future__ import annotations

from typing import Any

from arena.operational_fit import digest


class AAMRStateProbe:
    """Its drawers are its state. There is nothing else to fingerprint."""

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter
        if not hasattr(adapter, "_drawers"):
            raise AttributeError(
                "AAMR state probe expects _drawers on the adapter and did not find "
                "it. A partial fingerprint cannot establish read-only."
            )

    def fingerprint(self) -> str:
        return digest(self._adapter._drawers)

    def stored_times(self) -> list[str]:
        return [str(record.get("timestamp", record.get("day", "")))
                for chain in self._adapter._drawers.values() for record in chain]

    def stored_ids(self) -> list[str]:
        return [str(record.get("id", ""))
                for chain in self._adapter._drawers.values() for record in chain]
