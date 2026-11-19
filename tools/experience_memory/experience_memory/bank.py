"""An append-only bank of successful trajectories.

Each item is one solved episode: its goal, its task type, the family it belongs to (the group of episodes that
share a setting, so that a test task never sees a demonstration of its own family) and its steps.

The bank refuses three kinds of item at insertion:
- an item flagged as test data (``is_test=True``);
- an item that was not solved (``success=False``): the measured arm shows successful walkthroughs only;
- a second item with an ``item_id`` already in the bank.

Retrieval (``retrieval.py``) additionally refuses, per query, every item of the query's own family.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator


class LeakageError(ValueError):
    """An item would put test data into the memory bank."""


@dataclass(frozen=True)
class Step:
    """One step of a trajectory: the action taken and the observation that followed it."""

    action: str
    observation: str


@dataclass(frozen=True)
class Trajectory:
    """One successful episode stored in the bank.

    ``initial_observation`` is the observation before the first action, without the goal line (for ALFWorld: the
    room description). ``steps`` are (action, observation) pairs in order; the observation of the last step is the
    final observation.
    """

    item_id: str
    goal: str
    task_type: str
    family_id: str
    steps: tuple[Step, ...]
    initial_observation: str = ""
    success: bool = True
    is_test: bool = False
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def __post_init__(self) -> None:
        if not isinstance(self.steps, tuple):
            object.__setattr__(self, "steps", tuple(self.steps))
        for s in self.steps:
            if not isinstance(s, Step):
                raise TypeError(f"{self.item_id}: steps must be Step objects, got {type(s).__name__}")
        for name in ("item_id", "family_id", "task_type"):
            if not getattr(self, name):
                raise ValueError(f"trajectory field {name!r} must be a non-empty string")

    def to_dict(self) -> dict[str, Any]:
        return {"item_id": self.item_id, "goal": self.goal, "task_type": self.task_type,
                "family_id": self.family_id, "initial_observation": self.initial_observation,
                "steps": [{"action": s.action, "observation": s.observation} for s in self.steps],
                "success": self.success, "is_test": self.is_test, "metadata": dict(self.metadata)}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Trajectory":
        return cls(item_id=d["item_id"], goal=d["goal"], task_type=d["task_type"], family_id=d["family_id"],
                   steps=tuple(Step(s["action"], s["observation"]) for s in d["steps"]),
                   initial_observation=d.get("initial_observation", ""), success=d.get("success", True),
                   is_test=d.get("is_test", False), metadata=dict(d.get("metadata", {})))


class ExperienceBank:
    """Append-only, ordered collection of :class:`Trajectory` items.

    Order matters: retrieval breaks ties with a seeded random stream drawn in bank order (as the measured V5B
    instrument does), so the same items in the same order always give the same picks.
    """

    def __init__(self, items: Iterable[Trajectory] = ()) -> None:
        self._items: list[Trajectory] = []
        self._ids: set[str] = set()
        for it in items:
            self.add(it)

    def add(self, item: Trajectory) -> None:
        if not isinstance(item, Trajectory):
            raise TypeError(f"expected Trajectory, got {type(item).__name__}")
        if item.is_test:
            raise LeakageError(f"refusing {item.item_id!r}: it is flagged as test data")
        if not item.success:
            raise ValueError(f"refusing {item.item_id!r}: the bank holds successful trajectories only")
        if item.item_id in self._ids:
            raise ValueError(f"refusing {item.item_id!r}: an item with this id is already in the bank")
        self._items.append(item)
        self._ids.add(item.item_id)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Trajectory]:
        return iter(self._items)

    def __getitem__(self, i: int) -> Trajectory:
        return self._items[i]

    def __contains__(self, item_id: object) -> bool:
        return item_id in self._ids

    @property
    def families(self) -> frozenset[str]:
        return frozenset(it.family_id for it in self._items)

    def to_jsonl(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for it in self._items:
                f.write(json.dumps(it.to_dict(), ensure_ascii=False) + "\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "ExperienceBank":
        with open(path, encoding="utf-8") as f:
            return cls(Trajectory.from_dict(json.loads(line)) for line in f if line.strip())
