"""A reset must empty the store, and a later unit must not be able to see an earlier one.

The defect this pins, measured rather than imagined: Mem0's `delete_all` resolves
the rows to remove with `vector_store.list(filters=...)` and passes no limit,
while that method's signature is `list(self, filters=None, limit: int = 100)`. One
call therefore removes at most **100** memories. Every arena unit stored 220-392,
so every reset left 120-292 behind, and by the tenth unit four of ten delivered
evidence items belonged to four different earlier units.

Our own contribution was worse than the cap: the adapter wrapped the call in
`try/except Exception: pass` and never checked the postcondition. A reset that
cannot fail loudly is not a reset.

These tests use `infer=False`, so nothing here calls a model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.mem0_adapter import Mem0Adapter  # noqa: E402


class _CappedStore:
    """A double of the exact defect: deletes at most `cap` rows per call.

    Written as a double rather than against the real Mem0 so the guarantee is
    tested without a venv, an embedder or a model — and so the cap is explicit
    rather than a fact one has to already know.
    """

    def __init__(self, cap: int = 100) -> None:
        self.rows: list[dict] = []
        self.cap = cap

    def add(self, messages, user_id=None, metadata=None, infer=True):
        for message in messages:
            self.rows.append({"id": f"m{len(self.rows)}", "memory": message["content"],
                              "metadata": dict(metadata or {})})

    def search(self, query, user_id=None, limit=100):
        return {"results": [dict(r, score=1.0) for r in self.rows[:limit]]}

    def get_all(self, user_id=None, limit=100):
        return {"results": self.rows[:limit]}

    def delete_all(self, user_id=None):
        # The bug, exactly: a bounded page is resolved and only that page removed.
        doomed = {row["id"] for row in self.rows[:self.cap]}
        self.rows = [row for row in self.rows if row["id"] not in doomed]


def _ingest(adapter, tag: str, n: int) -> None:
    adapter.ingest([{"id": f"{tag}{i}", "text": f"{tag} fact {i}", "timestamp": tag}
                    for i in range(n)])


def test_a_reset_that_cannot_empty_the_store_raises() -> None:
    """Loud, not silent. The old adapter swallowed this and carried on."""
    store = _CappedStore(cap=100)
    adapter = Mem0Adapter(store)
    _ingest(adapter, "A", 250)
    adapter.reset()
    assert store.get_all(limit=100_000)["results"] == [], "reset left rows behind"


def test_a_later_unit_cannot_surface_an_earlier_one() -> None:
    """The measured failure: unit B retrieving unit A's memories."""
    store = _CappedStore(cap=100)
    adapter = Mem0Adapter(store)
    _ingest(adapter, "A", 250)
    adapter.reset()
    _ingest(adapter, "B", 30)
    answer = adapter.query("anything?")
    context = " ".join(answer.system_metadata["context_texts"])
    assert "A fact" not in context, "unit A leaked into unit B's delivered context"
    assert "B fact" in context


def test_the_store_is_empty_between_units_not_merely_smaller() -> None:
    store = _CappedStore(cap=100)
    adapter = Mem0Adapter(store)
    for tag in ("A", "B", "C"):
        adapter.reset()
        assert store.get_all(limit=100_000)["results"] == [], f"residue before {tag}"
        _ingest(adapter, tag, 220)


def test_a_store_that_never_empties_raises_rather_than_looping_forever() -> None:
    """A cap of zero deletes nothing. The reset must give up loudly, not spin."""
    class _Immovable(_CappedStore):
        def delete_all(self, user_id=None):
            pass

    adapter = Mem0Adapter(_Immovable())
    _ingest(adapter, "A", 5)
    with pytest.raises(RuntimeError, match="could not be emptied"):
        adapter.reset()


def test_an_already_empty_store_resets_without_complaint() -> None:
    adapter = Mem0Adapter(_CappedStore())
    adapter.reset()
    adapter.reset()
