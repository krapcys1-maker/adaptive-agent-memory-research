"""A probe's artefact must survive the store it came from being emptied.

The fixed-reader experiment could not run because the runner recorded
`context_tokens` — a count of the delivered context — and discarded the context.
The ids that remained were useless: the runner resets before every unit, so by
the end Hindsight's bank held zero memories and Mem0's held one unit's remnant.
Twenty of twenty arms were unobservable and the only repair was to pay for the
whole run again.

The rule this pins: **after reset(), nothing from the previous probe may be
needed to analyse it.** A probe's artefact is either self-sufficient or it is a
summary of something that no longer exists.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from arena_doubles import EngineDouble  # noqa: E402
from arena.mem0_adapter import Mem0Adapter  # noqa: E402

#: Everything the fixed-reader experiment needs from one probe, and nothing that
#: can only be resolved by asking a live store.
REQUIRED = ("question_id", "question", "gold", "answer",
            "evidence_ids", "context_texts", "evidence_times")


class _Mem0Double:
    """Mem0's surface, enough to exercise the adapter's reporting."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, messages, user_id=None, metadata=None):
        for message in messages:
            self.rows.append({"id": f"m{len(self.rows)}", "memory": message["content"],
                              "metadata": dict(metadata or {})})

    def search(self, query, user_id=None, limit=100):
        return {"results": [dict(row, score=1.0) for row in self.rows[:limit]]}

    def get_all(self, user_id=None, limit=100):
        return {"results": list(self.rows)}

    def delete_all(self, user_id=None):
        self.rows = []


def _probe_artifact(adapter, memory, question: str) -> dict:
    """What the runner writes for one probe, in the shape it writes it."""
    answer = adapter.query(question)
    return {
        "question_id": "q1", "question": question, "gold": "a gold answer",
        "answer": answer.text,
        "evidence_ids": answer.evidence_ids,
        "context_texts": answer.system_metadata.get("context_texts"),
        "evidence_times": answer.system_metadata.get("evidence_times"),
        "context_tokens": answer.context_tokens,
    }


def test_the_adapter_reports_the_context_and_not_only_its_size() -> None:
    """Counting the context and discarding it is what made a run unrepeatable."""
    memory = _Mem0Double()
    adapter = Mem0Adapter(memory)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "the vault host is b.internal", "timestamp": "d1"}])
    answer = adapter.query("which host?")

    assert answer.system_metadata["context_texts"] == ["the vault host is b.internal"]
    assert answer.context_tokens == 5


def test_a_probe_artifact_survives_the_store_being_reset() -> None:
    """The regression this module exists for.

    Run a probe, keep its artefact, empty the system, and the artefact must still
    carry everything the fixed reader needs. Previously it carried a token count
    and a list of ids that resolved to nothing.
    """
    memory = _Mem0Double()
    adapter = Mem0Adapter(memory)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "the billing host is c.internal", "timestamp": "d1"},
                    {"id": "r2", "text": "the vault host is b.internal", "timestamp": "d1"}])
    artifact = _probe_artifact(adapter, memory, "which host should billing use?")

    # The next unit begins: everything the system held is gone.
    adapter.reset()
    assert memory.rows == []

    for field in REQUIRED:
        assert artifact.get(field) is not None, field
    assert artifact["context_texts"], "the delivered context did not survive the reset"
    assert len(artifact["context_texts"]) == 2
    assert "billing host is c.internal" in " ".join(artifact["context_texts"])


def test_the_artifact_keeps_evidence_order() -> None:
    """Order is part of the context. A reader shown a reordered context is a
    different experiment, and the ordering cannot be recovered from a set of ids."""
    memory = _Mem0Double()
    adapter = Mem0Adapter(memory)
    adapter.reset()
    adapter.ingest([{"id": f"r{n}", "text": f"fact number {n}", "timestamp": "d1"}
                    for n in range(5)])
    artifact = _probe_artifact(adapter, memory, "which fact?")
    assert artifact["context_texts"] == [f"fact number {n}" for n in range(5)]


def test_the_artifact_keeps_session_provenance_per_evidence() -> None:
    """Without it, retrieval cannot be scored against the corpus after the fact."""
    memory = _Mem0Double()
    adapter = Mem0Adapter(memory)
    adapter.reset()
    adapter.ingest([{"id": "r1", "text": "one", "timestamp": "2022-09-01T00:10:00"}])
    artifact = _probe_artifact(adapter, memory, "?")
    assert artifact["evidence_times"] == ["2022-09-01T00:10:00"]


def test_the_committed_runner_persists_every_required_field() -> None:
    """Read from the runner's source, so the guard cannot drift from the writer."""
    source = (ROOT / "scripts/arena/run_pilot.py").read_text(encoding="utf-8")
    block = source[source.index("raw.append({"):]
    block = block[:block.index("})")]
    for field in ("question_id", "question", "gold", "answer", "evidence_ids",
                  "context_texts", "evidence_times"):
        assert f'"{field}"' in block, field


@pytest.mark.parametrize("adapter_file", ["mem0_adapter.py", "hindsight_adapter.py"])
def test_both_promoted_adapters_report_context_texts(adapter_file: str) -> None:
    source = (ROOT / "scripts/arena" / adapter_file).read_text(encoding="utf-8")
    assert '"context_texts"' in source, adapter_file
