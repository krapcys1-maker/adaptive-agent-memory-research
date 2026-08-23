"""The window into CUPMem's state that operational fit needs, and nothing more.

Kept out of the adapter deliberately. An adapter translates; if it also exposed
internals, the temptation to translate *from* those internals — and to start
modelling their schema rather than reading their return shape — would be one
edit away.

Duck-typed on purpose: nothing here imports `cup_mem`, so the test suite runs
with the external checkout absent, which it is, because it is a local cache and
not part of this repository.
"""

from __future__ import annotations

from typing import Any

from arena.operational_fit import digest


class CUPMemStateProbe:
    """Everything `CupMemEngine.reset()` clears, hashed as one value.

    The list is taken from their `reset`: the profile store, the chunk bank, the
    delta store and three id counters. Fingerprinting a subset would let a query
    write to the part not looked at and still read as read-only, which is the
    failure this check exists to rule out — so the fields are read from their
    reset rather than chosen by us.
    """

    #: Their `reset()` sets exactly these, so exactly these are the state.
    STATE_FIELDS = ("chunk_bank", "delta_store",
                    "_chunk_counter", "_delta_counter", "_proposal_counter")

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._verify_the_field_list_still_matches_their_reset()

    def _verify_the_field_list_still_matches_their_reset(self) -> None:
        """Fail loudly if their engine grew state this probe does not watch.

        A fingerprint is only a proof of read-only if it covers everything. The
        moment CUPMem gains a fourth counter, a silent partial fingerprint would
        keep reporting `read_only` for a system that had started writing.
        """
        missing = [f for f in ("store", *self.STATE_FIELDS)
                   if not hasattr(self._engine, f)]
        if missing:
            raise AttributeError(
                f"CUPMem state probe expects {missing} on the engine and did not "
                "find them. The fingerprint would cover less than the state, and a "
                "partial fingerprint cannot establish read-only."
            )

    def _snapshot(self) -> dict[str, Any]:
        return self._engine.store.to_snapshot()

    def fingerprint(self) -> str:
        return digest({
            "store": self._snapshot(),
            **{field: getattr(self._engine, field) for field in self.STATE_FIELDS},
        })

    def stored_times(self) -> list[str]:
        """The session time their store recorded on each item it holds.

        Read from stored state rather than from what the adapter passed, because
        the question is whether the record's time *arrived*, not whether it was
        sent.
        """
        return [str(item.get("created_session_time", ""))
                for item in self._items()]

    def stored_ids(self) -> list[str]:
        """Every identifier the system currently holds, in any of its forms.

        Their retrieval refers to an active or stale item by `item_id` and to an
        unknown track by `bucket/local_track`, so both spellings count as real.
        Chunk and delta ids are included because an evidence id naming one is
        still naming something the system holds — the check is *fabricated or
        not*, not *which table*.
        """
        snapshot = self._snapshot()
        ids = [str(item.get("item_id", "")) for item in self._items()]
        ids += [f"{item.get('bucket', '')}/{item.get('local_track', '')}"
                for item in snapshot.get("unknown_current", [])]
        ids += [key for key in snapshot.get("active_profile", {})]
        ids += [str(getattr(chunk, "chunk_id", "")) for chunk in self._engine.chunk_bank]
        ids += [str(getattr(delta, "delta_id", "")) for delta in self._engine.delta_store]
        ids += [str(link.get("stale_item_id", ""))
                for link in snapshot.get("stale_support_links", [])]
        return [value for value in dict.fromkeys(ids) if value and value != "/"]

    def _items(self) -> list[dict[str, Any]]:
        snapshot = self._snapshot()
        items: list[dict[str, Any]] = []
        for group in (snapshot.get("active_profile") or {}).values():
            items.extend(group)
        items.extend(snapshot.get("stale_archive") or [])
        items.extend(snapshot.get("unknown_current") or [])
        return [item for item in items if isinstance(item, dict)]
