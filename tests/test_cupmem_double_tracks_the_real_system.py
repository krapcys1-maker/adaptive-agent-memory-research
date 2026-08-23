"""Does the double still describe the system it claims to describe?

The rule this module exists to enforce: **a double certifies a contract only
where it disagrees with its adapter.** The previous CUPMem double was written by
the author of the adapter, from the same reading of their surface, and agreed
with the adapter in every place the adapter was wrong. It certified an ingest
that stored nothing, a cost reported as unobservable that the system reports
natively, and an abstention read from two fields that do not exist.

Nothing in the suite could have said so, because nothing in the suite ever
looked at CUPMem's code. These checks do. Each one names the module it quotes
and fails when that module stops saying it.

The checkout is a local cache and is gitignored, so every check here skips when
it is absent — which is why `arena_doubles` states each quotation in prose as
well. A skipped check is not a passed one, and the docstring is what remains
when the check cannot run.
"""

from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CUPMEM = ROOT / "external/repos/icedreamc__STALE"
sys.path.insert(0, str(ROOT / "scripts"))

from arena_doubles import ENGINE_STATE_FIELDS, EngineDouble, PREMISE_STATUSES  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (CUPMEM / "cup_mem").is_dir(),
    reason="CUPMem checkout absent; it is a gitignored local cache",
)


def _cupmem(module: str):
    if str(CUPMEM) not in sys.path:
        sys.path.insert(0, str(CUPMEM))
    import importlib

    return importlib.import_module(module)


# ------------------------------------------------------------------ their accounting


def test_their_client_exposes_usage_by_the_names_the_adapter_calls() -> None:
    """`get_usage_summary` is real. `llm.usage`, which the adapter probed, is not."""
    client = _cupmem("cup_mem.llm_layer.client").LLMClient
    for method in ("get_usage_summary", "get_call_records", "reset_usage_tracking"):
        assert callable(getattr(client, method, None)), method


def test_the_attribute_the_first_adapter_probed_does_not_exist() -> None:
    """This is the check that would have caught the unobservable-cost claim."""
    client = _cupmem("cup_mem.llm_layer.client").LLMClient
    assert not hasattr(client, "usage")


def test_their_usage_summary_has_the_keys_the_double_reproduces() -> None:
    summarize = _cupmem("cup_mem.llm_layer.client").summarize_call_records
    real = summarize([])
    assert set(EngineDouble().llm.get_usage_summary()) == set(real)


def test_their_summary_separates_billed_from_logical_usage() -> None:
    """A cache hit is billed as zero, which is why the adapter refuses a cache."""
    summarize = _cupmem("cup_mem.llm_layer.client").summarize_call_records
    real = summarize([{"cache_hit": True,
                       "usage": {"prompt_tokens": 100, "completion_tokens": 10},
                       "billed_usage": {"prompt_tokens": 0, "completion_tokens": 0}}])
    assert real["logical_usage"]["prompt_tokens"] == 100
    assert real["billed_usage"]["prompt_tokens"] == 0
    assert real["cache_hits"] == 1


def test_their_client_takes_a_cache_dir_at_all() -> None:
    client = _cupmem("cup_mem.llm_layer.client").LLMClient
    assert "cache_dir" in inspect.signature(client.__init__).parameters


# --------------------------------------------------------------------- their shapes


def test_their_verdict_has_a_status_and_no_unknown_current() -> None:
    """The two facts the first abstention mapping got backwards.

    `unknown_current` is a section of their *store*, never a field of the
    verdict, and their status vocabulary judges the question's premise.
    """
    verdict = _cupmem("cup_mem.memory.models").PremiseVerdict
    fields = {f.name for f in dataclasses.fields(verdict)}
    assert "status" in fields
    assert "unknown_current" not in fields
    assert not fields & {"abstained", "declined", "is_unknown"}


def test_their_premise_status_vocabulary_is_the_one_the_double_uses() -> None:
    source = (CUPMEM / "cup_mem/query/premise_verifier.py").read_text(encoding="utf-8")
    for status in PREMISE_STATUSES:
        assert f'"{status}"' in source, status


def test_their_answer_carries_answer_and_rationale_not_text() -> None:
    result = _cupmem("cup_mem.memory.models").AnswerResult
    assert [f.name for f in dataclasses.fields(result)] == ["answer", "brief_rationale"]


def test_their_stored_item_carries_the_session_time_the_probe_reads() -> None:
    item = _cupmem("cup_mem.memory.models").ProfileItem
    fields = {f.name for f in dataclasses.fields(item)}
    assert {"item_id", "bucket", "local_track", "created_session_time"} <= fields


def test_their_snapshot_has_the_four_sections_the_probe_walks() -> None:
    store = _cupmem("cup_mem.store_layer").ProfileStore()
    assert set(store.to_snapshot()) == {
        "active_profile", "stale_archive", "unknown_current", "stale_support_links",
    }


def test_the_doubles_snapshot_shape_matches_theirs() -> None:
    store = _cupmem("cup_mem.store_layer").ProfileStore()
    assert set(EngineDouble().store.to_snapshot()) == set(store.to_snapshot())


# ----------------------------------------------------------------- their chunker


def test_their_chunker_drops_everything_that_is_not_a_user_turn() -> None:
    """The filter that silently ingested nothing, quoted from their code."""
    keep = _cupmem("cup_mem.write.chunker").ChunkerMixin.session_to_user_turns
    assert keep([{"id": "r1", "day": 1, "text": "the shape the arena passes"}]) == []
    assert keep([{"role": "assistant", "content": "not a user turn"}]) == []
    assert keep([{"role": "user", "content": "   "}]) == []
    assert len(keep([{"role": "user", "content": "kept"}])) == 1


def test_the_double_drops_exactly_what_their_chunker_drops() -> None:
    keep = _cupmem("cup_mem.write.chunker").ChunkerMixin.session_to_user_turns
    session = [
        {"role": "user", "content": "kept"},
        {"role": "assistant", "content": "dropped"},
        {"role": "user", "content": "  "},
        {"id": "r1", "day": 1, "text": "the arena's own record shape"},
    ]
    engine = EngineDouble()
    engine.write_session(session=session, session_index=0, session_time="1")
    assert engine.sessions[0]["turns"] == len(keep(session)) == 1


# ------------------------------------------------------------------- their state


def test_the_probes_state_list_is_exactly_what_their_reset_clears() -> None:
    """A fingerprint over a subset cannot establish read-only.

    If their engine grows a fourth counter, a probe that does not watch it keeps
    reporting `read_only` for a system that has started writing.
    """
    source = inspect.getsource(_cupmem("cup_mem.pipeline").CupMemEngine.reset)
    assigned = {line.split("=")[0].strip().removeprefix("self.")
                for line in source.splitlines() if "=" in line and "self." in line}
    assigned |= {"store"} if "store.reset()" in source else set()

    from arena.cupmem_probe import CUPMemStateProbe

    assert set(CUPMemStateProbe.STATE_FIELDS) | {"store"} == assigned
    assert set(ENGINE_STATE_FIELDS) | {"store"} == assigned


def test_their_query_path_never_writes_the_store() -> None:
    """The construction argument behind the read-only reading, checked mechanically.

    Grep-shaped rather than semantic, and it is not the proof — the proof is the
    state fingerprint taken either side of a live query. This is the cheap check
    that fails first when their query path starts writing.
    """
    writes = ("store.apply_", "chunk_bank.append", "chunk_bank.extend",
              "delta_store.append", "delta_store.extend", "_next_chunk_id",
              "_next_delta_id", "store.reset")
    offenders = [
        f"{path.name}:{number}"
        for path in sorted((CUPMEM / "cup_mem/query").glob("*.py"))
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if any(marker in line for marker in writes)
    ]
    assert offenders == []
