"""The window into Graphiti's state: its nodes, its edges, and its episodes.

Three collections rather than one, because a write can land in any of them and a
fingerprint over a subset would report read-only for a system that had written
to the part it did not look at — the defect already found once, in the Mem0
probe that read only its first page.

Embeddings are excluded from the digest. They are large, they are derived from
the text already covered, and floating-point noise in them would report a
mutation on every comparison.
"""

from __future__ import annotations

import asyncio
from typing import Any

from arena.operational_fit import digest

#: Derived, large, and numerically noisy. The text they were built from is in the
#: digest, so dropping them loses no state and removes a false-positive source.
EXCLUDED = {"fact_embedding", "name_embedding", "attributes"}


class GraphitiStateProbe:
    def __init__(self, graphiti: Any, group_id: str = "arena-pilot") -> None:
        self._graphiti = graphiti
        self._group = group_id

    @staticmethod
    def _run(coro: Any) -> Any:
        return asyncio.run(coro)

    def _collections(self) -> dict[str, list[dict[str, Any]]]:
        from graphiti_core.edges import EntityEdge
        from graphiti_core.nodes import EntityNode, EpisodicNode

        driver = self._graphiti.driver
        out: dict[str, list[dict[str, Any]]] = {}
        for label, cls in (("nodes", EntityNode), ("edges", EntityEdge),
                           ("episodes", EpisodicNode)):
            try:
                items = self._run(cls.get_by_group_ids(driver, [self._group]))
            except Exception:  # noqa: BLE001 - an empty graph raises in their driver
                items = []
            out[label] = [
                {k: str(v) for k, v in item.model_dump().items() if k not in EXCLUDED}
                for item in (items or [])
            ]
        return out

    def fingerprint(self) -> str:
        collections = self._collections()
        return digest({
            label: sorted(items, key=lambda item: str(item.get("uuid", "")))
            for label, items in collections.items()
        })

    def stored_times(self) -> list[str]:
        collections = self._collections()
        return [str(item.get("valid_at") or item.get("reference_time") or "")
                for label in ("edges", "episodes") for item in collections[label]]

    def stored_ids(self) -> list[str]:
        collections = self._collections()
        return [str(item.get("uuid", "")) for items in collections.values()
                for item in items if item.get("uuid")]
