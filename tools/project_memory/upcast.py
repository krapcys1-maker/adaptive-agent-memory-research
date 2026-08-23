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

Version 2: bitemporal, and why it is derived rather than stored
---------------------------------------------------------------
Version 2 adopts the SQL:2011 two-axis model, following the comparison in
``docs/04-systems/temporal-memory-model-comparison-v0.md``:

===============  ============  ==================================================
Field            Axis          Meaning
===============  ============  ==================================================
``created_at``   transaction   when the record was written
``expired_at``   transaction   when the record was withdrawn      *(derived)*
``valid_from``   valid         when the fact became true
``valid_to``     valid         when the fact stopped being true   *(derived)*
===============  ============  ==================================================

Graphiti, the reference implementation, sets the prior fact's end by **mutating**
it: ``edge.invalid_at = resolved_edge.valid_at``. A graph database permits that.
An append-only log does not — the prior line cannot be edited, and CI enforces it.

So the two end-of-interval fields are **derived at read time from the successor**,
exactly as the active/superseded view is already derived by replaying events:

- ``valid_to``   of a superseded record = the successor's ``valid_from``
- ``expired_at`` of a superseded record = the successor's ``created_at``

This is a genuine improvement on a literal port. A stored end can drift from the
successor that caused it; a derived end cannot, because there is only one place
the value comes from.

Correction versus succession
----------------------------
The two axes make separate operations unnecessary, but the log must still record
which happened, because it changes what is derived:

- **succession** — the world changed. The prior fact was true and stopped being
  true, so ``valid_to`` is derived and the record remains a historical truth.
- **correction** — the record was wrong. Nothing about the world changed, so
  ``valid_to`` stays ``None`` and only ``expired_at`` is derived.

``supersession_kind`` carries this. Version 1 events never recorded it, so an
upcast v1 supersession is ``"unclassified"`` and derives no ``valid_to``: guessing
would write an interval nobody observed into what reads afterwards as evidence.

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

# Fields version 2 adds. The two marked derived are never authored.
V2_ADDED = ("valid_from", "valid_to", "expired_at", "claim_class", "supersession_kind")
V2_DERIVED = ("valid_to", "expired_at")

CLAIM_CLASSES = ("dispositional", "state", "unclassified")
SUPERSESSION_KINDS = ("succession", "correction", "unclassified")


def v1_to_v2(event: dict[str, Any]) -> dict[str, Any]:
    """Add the bitemporal fields introduced by version 2.

    Version 1 recorded only ``created_at``, which is *transaction time* — when
    the claim was written down. It could not express *valid time*, when the claim
    held in the world. Issue #29 records the consequence, and ``PMLAB-STALE-E1``
    measured it: a superseded fact and its replacement sit at the 99.5th
    percentile of corpus similarity, two pairs at cosine exactly 1.000, so no
    retrieval method can order them from content. Only valid time can.

    The upcast is deliberately conservative and adds no information that is not
    already implied:

    - ``valid_from`` defaults to ``created_at``. A version-1 event asserted
      something believed true when it was written; that is the weakest honest
      reading and never invents an earlier start.
    - ``valid_to`` and ``expired_at`` are left ``None`` here. They are derived
      from the successor by :func:`derive_temporal_view`, not stored, because an
      append-only log cannot edit the prior record the way a graph database can.
    - ``claim_class`` is ``"unclassified"`` rather than guessed. Version 1 did
      not distinguish a dispositional property from a transient state, and
      choosing for it retroactively would put an author's guess into what reads
      as recorded evidence.
    - ``supersession_kind`` is ``"unclassified"`` on a v1 supersession for the
      same reason. The log recorded *that* a conclusion was revised, never
      whether the world changed or the record was wrong.
    """
    upcast = dict(event)
    upcast["schema_version"] = 2
    upcast.setdefault("valid_from", event.get("created_at"))
    upcast.setdefault("valid_to", None)
    upcast.setdefault("expired_at", None)
    upcast.setdefault("claim_class", "unclassified")
    if event.get("operation") == "supersede" or event.get("supersedes"):
        upcast.setdefault("supersession_kind", "unclassified")
    else:
        upcast.setdefault("supersession_kind", None)
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


def derive_temporal_view(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill the derived end-of-interval fields from each record's successor.

    An append-only log cannot write an end date onto a record that already
    exists, so ``valid_to`` and ``expired_at`` are computed here rather than
    stored. The single source of each value is the superseding event, which means
    a derived end can never drift from the revision that caused it.

    ``expired_at`` is filled for every superseded record: the successor's
    ``created_at`` is exactly when the prior record was withdrawn, and that is
    observed rather than guessed.

    ``valid_to`` is filled **only** for a ``succession``. A ``correction`` means
    the record was wrong, so nothing about the world changed and the prior fact
    never had an end. An ``unclassified`` supersession — every version-1 one —
    derives no ``valid_to``, because the log does not say which happened and
    inventing an interval would fabricate evidence.
    """
    upcast = [upcast_event(event, 2) for event in events]
    successor: dict[str, dict[str, Any]] = {}
    for event in upcast:
        target = event.get("supersedes")
        if isinstance(target, str) and target:
            successor[target] = event

    for event in upcast:
        following = successor.get(str(event.get("id")))
        if following is None:
            continue
        event["expired_at"] = following.get("created_at")
        if following.get("supersession_kind") == "succession":
            event["valid_to"] = following.get("valid_from")
    return upcast


def describe_versions(events: list[dict[str, Any]]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for event in events:
        version = event.get("schema_version")
        if isinstance(version, int):
            counts[version] = counts.get(version, 0) + 1
    return dict(sorted(counts.items()))
