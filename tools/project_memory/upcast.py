"""Schema evolution for an append-only memory log, by upcasting.

The canonical log may never be rewritten. That is not a convention: CI's
canonical-store guard fails any pull request that removes a line from
``memory/events.jsonl``, and changing a line counts as a removal plus an
addition. In-place migration is therefore mechanically impossible.

That leaves exactly one sound way to evolve the schema, and it is the standard
one for event-sourced systems: **upcasting**. Old events stay on disk exactly as
written. The reader knows how to present a version 1 event in the shape of
version 2. New events are written at the current version. A log containing
several versions at once is the normal steady state, not a defect.

Why not the alternatives
------------------------
*Rewrite in place* destroys the record of what was actually written and is
blocked by CI.

*Append a translated copy of every event* doubles the log, creates two records
of one observation, and makes ``supersedes`` ambiguous — the copy is not a
revision of the original, it is the same claim in another shape.

Adding a version
----------------
Write a function taking an event dict at version N and returning it at N+1,
register it in ``UPCASTERS``, raise ``SCHEMA_VERSION`` in ``memory_store``, and
add a case to ``tests/test_upcast.py``. An upcaster must be **total** — defined
for every event the previous version permitted — and must never drop a field.
Both properties are tested against the real log.
"""

from __future__ import annotations

from typing import Any, Callable

# Fields a version-1 event always carries. Used to prove no upcaster drops data.
V1_REQUIRED = (
    "schema_version",
    "id",
    "operation",
    "kind",
    "title",
    "summary",
    "body",
    "created_at",
    "confidence",
    "status",
    "source_refs",
    "related_ids",
    "tags",
    "supersedes",
)


def v1_to_v2(event: dict[str, Any]) -> dict[str, Any]:
    """Add the bitemporal fields introduced by version 2.

    Version 1 recorded only ``created_at``, which is *transaction time* — when
    the claim was written down. It could not express *valid time*, when the
    claim held in the world. Issue #29 records the consequence: because a
    superseded record leaves ordinary search, the only way to record that a fact
    changed also hid the fact that was true before it.

    The upcast is deliberately conservative and adds no information that is not
    already implied:

    - ``valid_from`` defaults to ``created_at``. A version-1 event asserted
      something believed true when it was written; that is the weakest honest
      reading and never invents an earlier start.
    - ``valid_to`` is ``None``, meaning an interval still open at the right end.
      A superseded version-1 event is *not* given an end time here, because the
      log does not record when the world changed, only when the revision was
      written. Inferring one would fabricate a date.
    - ``claim_class`` is ``"unclassified"`` rather than guessed. Version 1 did
      not distinguish a dispositional property from a transient state, and
      choosing for it retroactively would put an author's guess into what reads
      as recorded evidence.
    """
    upcast = dict(event)
    upcast["schema_version"] = 2
    upcast.setdefault("valid_from", event.get("created_at"))
    upcast.setdefault("valid_to", None)
    upcast.setdefault("claim_class", "unclassified")
    return upcast


UPCASTERS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: v1_to_v2,
}


class UpcastError(ValueError):
    """Raised when an event cannot be brought to the target schema version."""


def upcast_event(event: dict[str, Any], target: int) -> dict[str, Any]:
    """Bring one event up to ``target``, applying each registered step in turn."""
    version = event.get("schema_version")
    if not isinstance(version, int):
        raise UpcastError(f"event {event.get('id')!r} has no integer schema_version")
    if version > target:
        raise UpcastError(
            f"event {event.get('id')!r} is at version {version}, newer than the "
            f"target {target}; this reader is too old for this log"
        )
    current = event
    while version < target:
        step = UPCASTERS.get(version)
        if step is None:
            raise UpcastError(f"no upcaster registered from version {version} to {version + 1}")
        current = step(current)
        version = current["schema_version"]
    return current


def upcast_all(events: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    return [upcast_event(event, target) for event in events]


def describe_versions(events: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for event in events:
        version = event.get("schema_version")
        if isinstance(version, int):
            counts[version] = counts.get(version, 0) + 1
    return dict(sorted(counts.items()))
