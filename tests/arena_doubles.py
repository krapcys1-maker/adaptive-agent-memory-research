"""A CUPMem double built from their code, not from what our adapter expected.

The previous double was written by the author of the adapter, from the same
reading of CUPMem's surface, and it agreed with the adapter everywhere the
adapter was wrong. It certified an ingest that wrote nothing, a cost the system
reports natively as *unobservable*, and an abstention read from two fields that
do not exist in their code. **A double certifies a contract only where it
disagrees with its adapter.**

So every shape here is quoted from a named place in
`external/repos/icedreamc__STALE`, and `test_cupmem_double_tracks_the_real_system`
re-checks each quotation against the real module whenever that checkout is
present. The checkout is a local cache and gitignored, so those checks skip in
CI — which is why the quotations are named here rather than trusted.

    cup_mem/llm_layer/client.py     get_usage_summary / get_call_records /
                                    reset_usage_tracking / cache_dir; no `usage`
    cup_mem/write/chunker.py        session_to_user_turns keeps role == "user"
                                    with non-empty content, drops the rest
    cup_mem/memory/models.py        PremiseVerdict.status ∈ {SUPPORTED,
                                    OUTDATED, UNRESOLVED}; AnswerResult has
                                    `answer` and `brief_rationale`
    cup_mem/query/support.py        hits are {source, id, text, payload}
    cup_mem/store_layer/in_memory.py  to_snapshot has active_profile,
                                    stale_archive, unknown_current,
                                    stale_support_links
    cup_mem/pipeline.py             reset() clears store, chunk_bank,
                                    delta_store and three counters
"""

from __future__ import annotations

from typing import Any

#: `cup_mem/query/premise_verifier.py` line 19 normalises anything else to the last.
PREMISE_STATUSES = ("SUPPORTED", "OUTDATED", "UNRESOLVED")

#: `cup_mem/pipeline.py` reset(); the state a fingerprint must cover.
ENGINE_STATE_FIELDS = ("chunk_bank", "delta_store",
                       "_chunk_counter", "_delta_counter", "_proposal_counter")


def empty_usage() -> dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


class LLMDouble:
    """`LLMClient`'s accounting surface, with its real method names.

    `cache_dir` is here because the adapter refuses to construct against a
    non-None one: a cached completion is billed as zero and would hand one
    system a discount the others do not get.
    """

    def __init__(self, *, expose_usage: bool = True, cache_dir: Any = None) -> None:
        self.cache_dir = cache_dir
        self._expose = expose_usage
        self._calls: list[dict[str, Any]] = []

    # -- their names, spelled their way ------------------------------------
    def reset_usage_tracking(self) -> None:
        self._calls = []

    def get_call_records(self) -> list[dict[str, Any]]:
        return list(self._calls)

    def get_usage_summary(self) -> dict[str, Any]:
        billed, logical = empty_usage(), empty_usage()
        hits = 0
        for call in self._calls:
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                logical[field] += call["usage"].get(field, 0)
                billed[field] += call["billed_usage"].get(field, 0)
            hits += bool(call["cache_hit"])
        return {
            "total_calls": len(self._calls),
            "cache_hits": hits,
            "cache_misses": len(self._calls) - hits,
            "logical_usage": logical,
            "billed_usage": billed,
            "by_phase": {}, "by_query_label": {},
        }

    # -- the double's own lever -------------------------------------------
    def record(self, *, phase: str, prompt: int, completion: int,
               cache_hit: bool = False) -> None:
        usage = {"prompt_tokens": prompt, "completion_tokens": completion,
                 "total_tokens": prompt + completion}
        self._calls.append({
            "phase": phase, "usage": usage, "cache_hit": cache_hit,
            "billed_usage": empty_usage() if cache_hit else usage,
        })


class _Store:
    """`ProfileStore.to_snapshot()`'s four sections, and nothing invented."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "active_profile": {
                f"{item['bucket']}/{item['local_track']}": [item] for item in self.items
            },
            "stale_archive": [],
            "unknown_current": [],
            "stale_support_links": [],
        }

    def reset(self) -> None:
        self.items = []


class EngineDouble:
    """`CupMemEngine`'s arena-facing surface, in their shapes.

    Deliberately not a simulation of CUPMem. It reproduces the *shape* of what
    their methods accept and return, which is the only thing an adapter can be
    tested against without an endpoint, an embedding model and a corpus.
    """

    def __init__(self, *, abstain: bool = False, expose_usage: bool = True,
                 cache_dir: Any = None, mutate_on_query: bool = False,
                 premise_status: str = "SUPPORTED") -> None:
        self.llm = LLMDouble(expose_usage=expose_usage, cache_dir=cache_dir) \
            if expose_usage else None
        self.store = _Store()
        self.chunk_bank: list[Any] = []
        self.delta_store: list[Any] = []
        self._chunk_counter = 0
        self._delta_counter = 0
        self._proposal_counter = 0
        self._abstain = abstain
        self._mutate_on_query = mutate_on_query
        self._premise_status = premise_status
        self.sessions: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.store.reset()
        self.chunk_bank = []
        self.delta_store = []
        self._chunk_counter = 0
        self._delta_counter = 0
        self._proposal_counter = 0
        self.sessions = []

    def write_session(self, *, session: list[dict[str, Any]], session_index: int,
                      session_time: str) -> dict[str, Any]:
        # `session_to_user_turns`: role must be exactly "user", content non-empty,
        # everything else dropped without a word. The old double appended whatever
        # it was handed, which is why it certified an ingest that stored nothing.
        turns = [message for message in session
                 if str(message.get("role", "")).strip() == "user"
                 and str(message.get("content", "")).strip()]
        self.sessions.append({"index": session_index, "time": session_time,
                              "turns": len(turns)})
        for turn in turns:
            self._chunk_counter += 1
            self.store.items.append({
                "item_id": f"i_{self._chunk_counter:05d}",
                "bucket": "profile", "local_track": f"t_{self._chunk_counter}",
                "value": turn["content"], "status": "ACTIVE", "confidence": 1.0,
                "first_seen": session_time, "last_updated": session_time,
                "created_session_id": f"s_{session_index:03d}",
                "created_session_index": session_index,
                "created_session_time": session_time,
                "evidence_chunk_ids": [], "source_delta_ids": [],
                "active_strength": "STRONG", "revision_history": [],
            })
        if self.llm:
            self.llm.record(phase="session_chunker", prompt=100, completion=30)
        return {"session_index": session_index, "session_time": session_time}

    def answer_query(self, *, query_label: str, query_text: str) -> dict[str, Any]:
        if self.llm:
            self.llm.record(phase="premise_verifier", prompt=50, completion=10)
            self.llm.record(phase="answer_composer", prompt=50, completion=10)
        if self._mutate_on_query:
            self._proposal_counter += 1

        # Their query path renders a hit with `text_preview`, a 160-character
        # truncation, and ships the item as `payload` — so the record's own text
        # arrives as `payload["value"]` and never under a key called `text`. The
        # first adapter looked only for `text` and reported zero context tokens
        # for a system that had just delivered four records.
        hits = [{"rank_index": n, "score": 1.0, "source": "active",
                 "source_detail": "strong_active", "id": item["item_id"],
                 "payload": item, "bucket": item["bucket"],
                 "local_track": item["local_track"],
                 "text_preview": item["value"][:160]}
                for n, item in enumerate(self.store.items, start=1)]
        answer = "" if self._abstain else (
            hits[-1]["payload"]["value"] if hits else "")
        return {
            "query_label": query_label,
            "query_text": query_text,
            "parsed_query": {"intent_type": "CURRENT_STATE"},
            "relevant_context": {
                "query_readout_mode": "premise_centered_primary_hits",
                "query_topk_results": hits,
                "topk_primary_hits": hits,
                "active_items": [hit["payload"] for hit in hits],
                "stale_items": [], "unknown_items": [],
            },
            # PremiseVerdict.to_dict(): no `unknown_current` anywhere in it.
            "verdict": {"status": self._premise_status, "confidence": 0.9,
                        "reasoning_summary": "", "unknown_tracks": [],
                        "old_premise_safe": True},
            # AnswerResult.to_dict(): `answer` and `brief_rationale`, not `text`.
            "answer": {"answer": answer, "brief_rationale": ""},
        }
