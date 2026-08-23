"""The reference adapter: AAMR itself, proving the contract is implementable.

A contract nobody has implemented is a wish. This one exists so a contributor
writing an adapter for another system has a worked example, and so the validator
is tested against something real rather than a stub.

It wires the pieces this project already has — deterministic addressing from
`corpus.address_extract`, and the temporal resolver's rules — behind the three
methods the contract requires. No model, so `Cost` is genuinely zero rather than
zero by omission.

It is not expected to score well. `CANDIDATE-0` is a registered negative
artifact whose language-to-address bridge does not transfer, and this adapter
carries that limitation deliberately: the arena should measure the thing that
was frozen, not a quietly improved version of it.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter import Answer, Cost  # noqa: E402
from corpus.address_extract import extract, extract_query  # noqa: E402


class AAMRAdapter:
    """Deterministic addressing plus temporal resolution. No model anywhere."""

    name = "AAMR-CANDIDATE-0"

    def __init__(self) -> None:
        self._drawers: dict[str, list[dict[str, Any]]] = {}

    def reset(self) -> None:
        self._drawers = {}

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        started = time.monotonic()
        for record in records:
            address = extract(record["text"], canonicalise=True)
            if address:
                self._drawers.setdefault(address.canonical, []).append(record)
        return Cost(model_calls=0, wall_seconds=round(time.monotonic() - started, 6))

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        address = extract_query(question, canonicalise=True)

        if address is None or address.canonical not in self._drawers:
            # Abstention is a real answer here, not a fallback. A wrong address
            # opens someone else's drawer, which is worse than opening none.
            return Answer(text="", abstained=True,
                          cost=Cost(wall_seconds=round(time.monotonic() - started, 6)),
                          system_metadata={"reason": "no address resolved"})

        chain = [r for r in self._drawers[address.canonical]
                 if asked_at is None or r.get("day", 0) <= asked_at]
        if not chain:
            return Answer(text="", abstained=True,
                          cost=Cost(wall_seconds=round(time.monotonic() - started, 6)),
                          system_metadata={"reason": "chain empty at query time"})

        # Newest first. An addressed chain arrives time-ordered, which is why the
        # resolver is a no-op on simple succession — measured in PMLAB-H1-COMPOSE-E1.
        chain.sort(key=lambda r: -r.get("day", 0))
        return Answer(
            text=chain[0]["text"],
            evidence_ids=[r["id"] for r in chain],
            context_tokens=sum(len(r["text"].split()) for r in chain),
            abstained=False,
            cost=Cost(wall_seconds=round(time.monotonic() - started, 6)),
            system_metadata={"address": address.canonical, "chain_length": len(chain)},
        )
