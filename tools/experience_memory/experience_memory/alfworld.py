"""Adapter from the lab's ALFWorld bank records to :class:`Trajectory`.

A record (one line of ``tools/alfworld_ladder/data/bank.jsonl``) has ``task`` (the game path, for example
``train/pick_and_place_simple-.../trial_...``), ``family``, ``type``, ``initial_observation`` (the raw first
observation of the game, with the welcome banner and the goal line), ``steps`` (``action``, ``observation``) and
``won``.

Only ``train`` games may enter the bank: any other split (``valid_seen``, ``valid_unseen``) is flagged as test data
and the bank refuses it.
"""
from __future__ import annotations

from typing import Any

from .bank import Step, Trajectory

GOAL_MARK = "Your task is to: "


def goal_of(observation: str) -> str:
    """The goal of an ALFWorld game from its first observation, without the final full stop (V5B ``goal_of``)."""
    i = observation.find(GOAL_MARK)
    return observation[i + len(GOAL_MARK):].strip().rstrip(".") if i >= 0 else ""


def room_of(observation: str) -> str:
    """The room description: the first paragraph that is neither the welcome banner nor the goal line."""
    room = [r for r in observation.split("\n\n")
            if r.strip() and "Welcome to TextWorld" not in r and "Your task is to" not in r]
    return room[0] if room else ""


def task_type_of(task_path: str) -> str:
    """``train/pick_and_place_simple-CD-None-Shelf-330/trial_x`` -> ``pick_and_place_simple``."""
    return task_path.split("/")[1].split("-")[0]


def from_lab_record(record: dict[str, Any]) -> Trajectory:
    task = record["task"]
    split = task.split("/")[0]
    return Trajectory(
        item_id=task,
        goal=goal_of(record["initial_observation"]),
        task_type=record.get("type") or task_type_of(task),
        family_id=record.get("family") or task.split("/")[1],
        steps=tuple(Step(s["action"], s["observation"]) for s in record["steps"]),
        initial_observation=room_of(record["initial_observation"]),
        success=bool(record.get("won", True)),
        is_test=split != "train",
        metadata={"split": split, "all_admissible": record.get("all_admissible")},
    )
