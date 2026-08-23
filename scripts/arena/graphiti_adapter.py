"""Graphiti adapter. Translates their surface to the arena contract, nothing more.

    contract            Graphiti
    reset()             clear_data(driver) + build_indices_and_constraints()
    ingest(records)     add_episode(name=…, episode_body=…, reference_time=…)
    query(question)     search(query=…) -> list[EntityEdge]

What this system returns, and why the arena must say so
--------------------------------------------------------
**Graphiti answers with edges, not with text and not with records.** `search`
returns `EntityEdge` objects — a fact asserted between two entities, carrying
`valid_at` and `invalid_at`. It composes nothing, and unlike Mem0 it does not
even return the source passage: the unit of recall is a relation their extractor
built.

So `text` is the top edge's fact string, `evidence_ids` are edge uuids, and
`answer_channel` says exactly that. Two consequences the harness must not be
allowed to miss, both recorded rather than smoothed over:

- an edge id names nothing that was ingested. It is not traceable to a record
  the way CUPMem's item ids are traceable to its own store, let alone to an
  arena record. Whose id space `evidence_ids` lives in is already an open
  question for this arena, and this system is the sharpest case of it.
- their temporal fields are the thing this system is famous for, so `valid_at`
  and `invalid_at` are reported per edge in the metadata rather than collapsed
  into the answer. Reading them is the harness's job, and interpreting them is
  Phase B's.

Everything local
-----------------
Kuzu embedded rather than Neo4j, so no database service. Embeddings and reranking
are pinned to the same local checkpoint the other systems run on, which is an
arena control recorded beside their native defaults — Graphiti's own are an
OpenAI embedding endpoint and an LLM-based reranker, and either would put a
second provider and a second bill inside one comparison.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from arena.adapter import Answer, Cost, Measure

GROUP = "arena-pilot"

ANSWER_CHANNEL = ("top retrieved entity edge; this system returns relations, "
                  "not passages and not composed prose")


def _elapsed_us(started: float) -> int:
    return int(round((time.monotonic() - started) * 1_000_000))


_DATE_FORMATS = (
    "%Y/%m/%d (%a) %H:%M", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
)


def _reference_time(value: Any) -> datetime | None:
    """The instant a record carries, or None if it carries none we can read.

    None rather than *now*: defaulting an unreadable date to the present would
    put every such memory at the top of a system whose whole subject is when
    facts were true.
    """
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
        for fmt in _DATE_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _edge_field(edge: Any, *names: str) -> Any:
    for name in names:
        value = getattr(edge, name, None)
        if value is not None:
            return value
    return None


class GraphitiAdapter:
    """Requires a constructed `Graphiti`. This file does not build one."""

    #: Their search path reads the graph. Whether it writes is settled by the
    #: state probe on a live run, never by comparing two answers.
    query_mutates_state = "unknown"

    name = "Graphiti"

    def __init__(self, graphiti: Any, meter: Any = None, *, group_id: str | None = None,
                 text_field: str = "text", num_results: int = 10) -> None:
        self._graphiti = graphiti
        self._meter = meter
        # Their provider's default group, not one of ours.
        #
        # Passing any explicit group_id sends add_episode down a branch that
        # reads `driver._database`, which their Kuzu driver does not define, and
        # every episode raises AttributeError. Kuzu is also the only embedded
        # backend they ship and it is deprecated upstream — "the upstream Kuzu
        # project is no longer maintained" — so this is their bug in their
        # deprecated backend, not something translation can repair.
        #
        # Using the default group is a choice about where to write, which is the
        # adapter's to make. Patching their file would not be.
        from graphiti_core.helpers import get_default_group_id

        self._group = group_id or get_default_group_id(graphiti.driver.provider)
        self._text_field = text_field
        self._num_results = num_results
        self.unparsed_timestamps = 0
        self._episodes = 0
        self._indices_built_after_ingest = False

    @staticmethod
    def _run(coro: Any) -> Any:
        """Their API is async and the contract is not. One loop per call.

        `asyncio.run` rather than a shared loop, so a failure inside one
        operation cannot leave a half-closed loop for the next to inherit.
        """
        return asyncio.run(coro)

    # ---------------------------------------------------------------- contract

    def reset(self) -> None:
        from graphiti_core.utils.maintenance.graph_data_operations import clear_data

        # Schema first, then clear. On a store that has never been written,
        # `clear_data` reaches for tables their driver has not created yet and
        # fails with an AttributeError about a private field — which reads as a
        # broken adapter rather than as an empty database.
        self._run(self._graphiti.build_indices_and_constraints())
        # Scoped to this group rather than the whole database: the arena writes
        # one group, and deleting everything would be a claim about state the
        # arena did not create.
        self._run(clear_data(self._graphiti.driver, [self._group]))
        self._episodes = 0
        self.unparsed_timestamps = 0
        self._indices_built_after_ingest = False

    def ingest(self, records: list[dict[str, Any]]) -> Cost:
        started = time.monotonic()
        before = self._meter_snapshot()

        kept = [
            (str(record.get(self._text_field, "")).strip(), record.get("timestamp"))
            for record in records
        ]
        kept = [(text, stamp) for text, stamp in kept if text]
        if records and not kept:
            raise ValueError(
                f"{self.name}: ingest translated {len(records)} records into zero "
                "usable episodes. Answering probes after this would measure the "
                "model's priors, not the system's memory."
            )

        for text, stamp in kept:
            reference = _reference_time(stamp)
            if reference is None and stamp:
                self.unparsed_timestamps += 1
            self._run(self._graphiti.add_episode(
                name=f"arena-{self._episodes}",
                episode_body=text,
                source_description="arena record",
                reference_time=reference or datetime.now(timezone.utc),
                # Deliberately absent: see the constructor. An explicit group_id
                # raises on their Kuzu driver.
            ))
            self._episodes += 1

        return self._cost_since(before, started)

    def query(self, question: str, asked_at: Any = None) -> Answer:
        started = time.monotonic()
        before = self._meter_snapshot()

        # Their Kuzu backend creates node tables lazily on first write, so indices
        # built on an empty store are built on tables that do not exist yet and
        # search then fails with "Table RelatesToNode_ doesn't have an index".
        # Rebuilding once after ingest is idempotent and is the adapter deciding
        # when to call their setup, not changing what it does.
        if not self._indices_built_after_ingest:
            self._run(self._graphiti.build_indices_and_constraints())
            self._indices_built_after_ingest = True

        edges = self._run(self._graphiti.search(
            query=question, group_ids=[self._group], num_results=self._num_results))
        edges = list(edges or [])
        facts = [str(_edge_field(edge, "fact", "name") or "") for edge in edges]
        facts = [fact for fact in facts if fact.strip()]

        return Answer(
            text=facts[0] if facts else "",
            evidence_ids=[str(_edge_field(edge, "uuid", "id") or "") for edge in edges
                          if _edge_field(edge, "uuid", "id")],
            context_tokens=sum(len(fact.split()) for fact in dict.fromkeys(facts)),
            abstained=not facts,
            cost=self._cost_since(before, started),
            system_metadata={
                "answer_channel": ANSWER_CHANNEL,
                "retrieved": len(edges),
                # Reported, never interpreted. Temporal validity is what this
                # system is for, and turning it into a verdict is Phase B's job.
                "edge_validity": [
                    {"valid_at": str(_edge_field(edge, "valid_at") or ""),
                     "invalid_at": str(_edge_field(edge, "invalid_at") or "")}
                    for edge in edges][:10],
                "evidence_id_space": ("entity edge uuids. An edge is a relation their "
                                      "extractor built and names nothing that was "
                                      "ingested, so these are not traceable to an "
                                      "arena record"),
                "abstention_derivable": True,
                "abstention_channel": "empty edge set",
                "cost_observability": self._cost_observability(),
                "context_tokens_basis": "distinct edge fact strings, whitespace-split",
                "context_tokens_is_floor": False,
                "context_tokens_measurable": True,
                "unparsed_timestamps": self.unparsed_timestamps,
            },
        )

    # ----------------------------------------------------------------- helpers

    def _meter_snapshot(self) -> dict[str, int] | None:
        return None if self._meter is None else self._meter.snapshot()

    def _cost_observability(self) -> dict[str, str]:
        source = "instrumented" if self._meter is not None else "unobservable"
        return {field: source for field in ("calls", "prompt_tokens", "completion_tokens")}

    def _cost_since(self, before: dict[str, int] | None, started: float) -> Cost:
        after = self._meter_snapshot()
        if before is None or after is None:
            unknown = Measure(None, "unobservable")
            return Cost(unknown, unknown, unknown,
                        Measure(_elapsed_us(started), "instrumented"))
        return Cost(
            model_calls=Measure(max(0, after["calls"] - before["calls"]), "instrumented"),
            input_tokens=Measure(max(0, after["prompt_tokens"] - before["prompt_tokens"]),
                                 "instrumented"),
            output_tokens=Measure(
                max(0, after["completion_tokens"] - before["completion_tokens"]),
                "instrumented"),
            wall_microseconds=Measure(_elapsed_us(started), "instrumented"),
        )
