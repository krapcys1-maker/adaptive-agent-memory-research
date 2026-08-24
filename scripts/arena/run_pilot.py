#!/usr/bin/env python3
"""The screening pilot, one runner for every system.

Four frozen units of LongMemEval-S — `arena-pilot-v1` — run through identical
measurement code for each system, because a comparison is void unless every arm
ran on one harness. The measurement loop is lifted verbatim from
`run_arena_pilot.py`, which is the file CUPMem's own pilot ran under and is left
untouched so that what CUPMem ran remains exactly what CUPMem ran.

**Four units is a screening sample, not a leaderboard.** At n=4, with a crude
correctness proxy and a decoder that is measurably not reproducible, "system A
beat system B" is a sentence this data cannot support. What it can support is
*this system cannot be run at all*, *this one costs forty times that one*, and
*these two fail on different units* — which is what a screen is for.

Two budgets, both enforced beneath the provider
-----------------------------------------------
A per-system cap stops one system. It cannot stop five systems from each
stopping politely at their own ceiling and costing five times what was agreed,
so a shared ledger on disk carries the night's total and every run consults it
before asking the provider for anything.

What may be fixed, and what may not
------------------------------------
Fixable: translation, serialisation, cost accounting, reset and leakage, usage
instrumentation, provenance, timeouts, evidence mapping, a malformed return
shape, a silent zero-ingest, an unknown collapsed into a zero. Not fixable from
anything seen here: retrieval, prompts, memory policy, temporal rules, ranking,
or any benchmark-specific rule. Tuning a competitor on the arena voids the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter_v0_1 import CONTRACT_VERSION, contract_digest  # noqa: E402
from arena.decoding import (  # noqa: E402
    ARENA_DECODING, PRICE_PER_MTOK, FixedDecoding, SpendCapReached,
)
from arena.retrieval_truth import measure as retrieval_measure  # noqa: E402
from arena.run_arena_pilot import as_records, cost_fields, crude_match  # noqa: E402
from arena.spend_ledger import SpendLedger, TotalCapReached  # noqa: E402

CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")
SELECTION = ROOT / "data/lab/arena/pilot-selection.json"


def digest_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_units(selection: Path, corpus: Path) -> list[dict[str, Any]]:
    manifest = json.loads(selection.read_text(encoding="utf-8"))
    wanted = {unit["question_id"]: unit for unit in manifest["units"]}
    with corpus.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    found = [row for row in rows if row.get("question_id") in wanted]
    if len(found) != len(wanted):
        missing = set(wanted) - {row["question_id"] for row in found}
        raise SystemExit(f"selection names units absent from the corpus: {sorted(missing)}")
    order = {unit["question_id"]: n for n, unit in enumerate(manifest["units"])}
    found.sort(key=lambda row: order[row["question_id"]])
    return [dict(row, _meta=wanted[row["question_id"]]) for row in found]


# --------------------------------------------------------------------- systems


def build_aamr(_args, _ledger):
    """Our own reference. No model anywhere, so its pilot is free.

    Included precisely because it is expected to do badly: `CANDIDATE-0` is a
    registered negative whose language-to-address bridge does not transfer, and
    the arena should measure what was frozen rather than a quietly improved
    version. A floor arm that costs nothing is worth having.
    """
    from arena.aamr_adapter import AAMRAdapter
    from arena.aamr_probe import AAMRStateProbe

    adapter = AAMRAdapter()
    # A probe even here. Without one the pilot would record `unknown` for a
    # system whose whole state is a dictionary this repository owns, and unknown
    # is the honest answer only when nothing can be observed.
    return {"adapter": adapter, "probe": AAMRStateProbe(adapter), "provider": None,
            "source": {"system": "AAMR-CANDIDATE-0", "in_repo": True,
                       "note": ("CANDIDATE-0 is a registered negative: its "
                                "language-to-address bridge reached 1.000 internally "
                                "and does not transfer. It is in the pilot as a free "
                                "floor arm, measured as frozen rather than improved")}}


def build_cupmem(args, ledger):
    from openai import OpenAI

    sys.path.insert(0, str(Path(args.cupmem_root).resolve()))
    from cup_mem.llm_layer.client import LLMClient
    from cup_mem.pipeline import CupMemEngine

    from arena.cupmem_adapter import CUPMemAdapter
    from arena.cupmem_probe import CUPMemStateProbe
    from arena.record_source_provenance import describe

    llm = LLMClient(
        model=args.model, api_key=load_key(), base_url=args.base_url,
        openai_cls=lambda **kwargs: FixedDecoding(
            OpenAI(**kwargs), spend_cap_usd=args.cap_usd, shared_ledger=ledger),
    )
    engine = CupMemEngine(llm=llm, embedding_model_path=str(args.embedding_model_path))
    return {
        "adapter": CUPMemAdapter(engine),
        "probe": CUPMemStateProbe(engine),
        "provider": engine.llm.client,
        "source": {k: v for k, v in describe(
            Path(args.cupmem_root).resolve(), "cup_mem", ("*.py",)).items() if k != "files"},
    }


def build_mem0(args, ledger):
    """Mem0, in its own venv, metered by the arena's proxy.

    It exposes no usage counter, so the proxy is not an optimisation here — it is
    the only place this system's cost can be read from. Its model calls are
    pointed at `http://127.0.0.1:PORT/v1`, which enforces the arena decoding,
    prices every response into the shared ledger, and refuses the request that
    would cross either ceiling.

    The embedder is pinned to the same local checkpoint CUPMem runs on. That is
    an arena control of the same class as the decoding, recorded as enforced
    rather than native: Mem0's own default is an OpenAI embedding endpoint, which
    would put a second provider and a second bill inside one comparison.
    """
    # Mem0 posts usage telemetry to an external analytics service on import and
    # on every operation, and it is on by default. The arena does not send a
    # third party a record of a run it was not asked to send, and a background
    # queue competing with the measured calls is not a condition anyone chose.
    # Off before the import that reads it.
    os.environ["MEM0_TELEMETRY"] = "False"

    from mem0 import Memory

    from arena.mem0_adapter import BANK, Mem0Adapter
    from arena.mem0_probe import Mem0StateProbe
    from arena.provider_proxy import serve

    _server, meter = serve("https://api.deepseek.com", load_key(), 0, ledger, args.cap_usd)
    port = _server.server_address[1]

    store = Path(args.mem0_store).resolve()
    store.mkdir(parents=True, exist_ok=True)
    memory = Memory.from_config({
        "llm": {"provider": "openai", "config": {
            "model": args.model, "api_key": "routed-through-the-arena-proxy",
            "openai_base_url": f"http://127.0.0.1:{port}/v1"}},
        "embedder": {"provider": "huggingface", "config": {
            "model": str(Path(args.embedding_model_path).resolve())}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": "arena_pilot", "embedding_model_dims": 384,
            "path": str(store), "on_disk": True}},
    })
    return {
        "adapter": Mem0Adapter(memory, meter),
        "probe": Mem0StateProbe(memory, BANK),
        "provider": None,
        "meter": meter,
        "source": {
            "system": "Mem0", "version": "1.0.6",
            "vector_store": "qdrant, local path, on_disk",
            "embedder_enforced": str(Path(args.embedding_model_path).resolve()),
            "embedder_native_default": "openai text-embedding-3-small",
            "embedder_override_reason": ("held constant with CUPMem's; the native "
                                         "default would add a second provider and a "
                                         "second bill inside one comparison"),
            "telemetry": "disabled by the arena; this system posts usage analytics "
                         "to an external service by default",
        },
    }


def build_hindsight(args, ledger):
    """Hindsight, already running as a server, metered by the arena's proxy.

    It is a service, not a library, so the in-process wrapper reaches nothing in
    it. Its provider client is pointed at the proxy by environment before the
    server starts; the proxy is the only place the arena can price it, and it is
    also the only place the cap can stop it.

    Its embedder is pinned to the same local checkpoint the others run on — an
    arena control, recorded as enforced beside its native default of
    BAAI/bge-small-en-v1.5.
    """
    from arena.hindsight_adapter import BANK, HindsightAdapter, HindsightHTTP
    from arena.hindsight_probe import HindsightStateProbe
    from arena.provider_proxy import ProxyState

    http = HindsightHTTP(args.hindsight_url)
    #: The proxy runs in its own process for this system, so its counters are
    #: read over HTTP rather than shared in memory.
    meter = _RemoteMeter(args.proxy_url)
    return {
        "adapter": HindsightAdapter(http, meter),
        "probe": HindsightStateProbe(http, BANK),
        "provider": None,
        "meter": meter,
        "source": {
            "system": "Hindsight", "version": "0.9.1",
            "repo": "vectorize-io/hindsight", "commit": "3295716c",
            "database": "pg0 embedded PostgreSQL",
            "embedder_enforced": str(Path(args.embedding_model_path).resolve()),
            "embedder_native_default": "BAAI/bge-small-en-v1.5",
            "retain_mode": "async=false requested, then settled on a stable count",
        },
    }


class _RemoteMeter:
    """The proxy's counters, read over HTTP because it is a separate process.

    Presents the one surface a meter needs — `snapshot()` — so adapters and the
    runner never have to know which side of a process boundary the money is
    counted on.
    """

    def __init__(self, url: str) -> None:
        self._url = url.rstrip("/")

    def _get(self) -> dict[str, Any]:
        import urllib.request

        with urllib.request.urlopen(f"{self._url}/arena/summary", timeout=30) as response:
            return json.loads(response.read())

    def snapshot(self) -> dict[str, int]:
        summary = self._get()
        return {"calls": summary["calls"],
                "prompt_tokens": summary["prompt_tokens"],
                "completion_tokens": summary["completion_tokens"]}

    @property
    def spent_usd(self) -> float:
        return self._get()["usd"]

    def summary(self) -> dict[str, Any]:
        return self._get()


def build_graphiti(args, ledger):
    """Graphiti on embedded Kuzu, metered by an in-process proxy.

    Kuzu rather than Neo4j, so no database service. Its embedder and reranker are
    pinned to the same local checkpoint the other systems run on — an arena
    control, recorded beside their native defaults, which are an OpenAI embedding
    endpoint and an LLM-based reranker. Either would put a second provider and a
    second bill inside one comparison, and the reranker would put a model call in
    the query path of one system and not the others.
    """
    from graphiti_core import Graphiti
    from graphiti_core.cross_encoder.bge_reranker_client import BGERerankerClient
    from graphiti_core.driver.kuzu_driver import KuzuDriver
    from graphiti_core.embedder.client import EmbedderClient
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

    from arena.graphiti_adapter import GROUP, GraphitiAdapter
    from arena.graphiti_probe import GraphitiStateProbe
    from arena.provider_proxy import serve

    _server, meter = serve("https://api.deepseek.com", load_key(), 0, ledger, args.cap_usd)
    port = _server.server_address[1]

    class _LocalEmbedder(EmbedderClient):
        """The same checkpoint the others embed with, wrapped in their interface."""

        def __init__(self, path: str) -> None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(path, device="cpu")

        async def create(self, input_data):  # noqa: ANN001
            texts = input_data if isinstance(input_data, list) else [input_data]
            texts = [t if isinstance(t, str) else " ".join(map(str, t)) for t in texts]
            vectors = self._model.encode(texts, show_progress_bar=False)
            return vectors[0].tolist() if not isinstance(input_data, list) else [
                v.tolist() for v in vectors]

        async def create_batch(self, input_data_list):  # noqa: ANN001
            vectors = self._model.encode(list(input_data_list), show_progress_bar=False)
            return [v.tolist() for v in vectors]

    store = Path(args.graphiti_store).resolve()
    store.parent.mkdir(parents=True, exist_ok=True)
    graphiti = Graphiti(
        graph_driver=KuzuDriver(db=str(store)),
        # `json_object` rather than their default `json_schema`. This is their own
        # switch, provided for exactly this case: DeepSeek answers a json_schema
        # response_format with "This response_format type is unavailable now", and
        # in json_object mode Graphiti injects the schema into the prompt instead.
        # Choosing between two modes the system ships is configuration; the
        # alternative — having the arena's proxy rewrite the request — would be
        # the arena editing what a system asked its provider for.
        llm_client=OpenAIGenericClient(
            config=LLMConfig(api_key="routed-through-the-arena-proxy",
                             model=args.model,
                             base_url=f"http://127.0.0.1:{port}/v1"),
            structured_output_mode="json_object"),
        embedder=_LocalEmbedder(str(Path(args.embedding_model_path).resolve())),
        cross_encoder=BGERerankerClient(),
    )
    return {
        "adapter": GraphitiAdapter(graphiti, meter),
        "probe": GraphitiStateProbe(graphiti, GROUP),
        "provider": None,
        "meter": meter,
        "source": {
            "system": "Graphiti", "repo": "getzep/graphiti",
            "commit": "993e081a6d7948a0d8851c12a5fbdbeb49fed862",
            "graph_backend": "kuzu, embedded",
            "embedder_enforced": str(Path(args.embedding_model_path).resolve()),
            "embedder_native_default": "openai text-embedding-3-small",
            "reranker_enforced": "BGE local cross-encoder",
            "reranker_native_default": "OpenAIRerankerClient, an LLM call per candidate",
            "structured_output_mode": "json_object, their own switch; the provider "
                                      "rejects the json_schema default",
            "group_id": "their provider default; an explicit one raises on their "
                        "deprecated Kuzu driver",
        },
    }


SYSTEMS = {"aamr": build_aamr, "cupmem": build_cupmem, "mem0": build_mem0,
           "hindsight": build_hindsight, "graphiti": build_graphiti}


def load_key() -> str:
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DEEPSEEK_API_KEY in .env or ../.env")


# ------------------------------------------------------------------------ main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", required=True, choices=sorted(SYSTEMS))
    parser.add_argument("--cap-usd", type=float, default=3.00)
    parser.add_argument("--total-cap-usd", type=float, default=10.00)
    parser.add_argument("--calibrate-sessions", type=int, default=0)
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cupmem-root", default=str(ROOT / "external/repos/icedreamc__STALE"))
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store", default=str(ROOT / "external/venvs/mem0-store"))
    parser.add_argument("--graphiti-store", default=str(ROOT / "external/venvs/graphiti-store"))
    parser.add_argument("--hindsight-url", default="http://127.0.0.1:8801")
    parser.add_argument("--proxy-url", default="http://127.0.0.1:8799")
    parser.add_argument("--out", default=None)
    parser.add_argument("--selection", default=str(SELECTION),
                        help="frozen selection manifest to run")
    parser.add_argument("--only-origin", default=None,
                        help="run only units whose manifest origin matches, so a "
                             "reused unit is not paid for twice")
    args = parser.parse_args()
    selection_path = Path(args.selection)

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    mode = "calibration" if args.calibrate_sessions else "pilot"
    out = Path(args.out or ROOT / f"data/lab/arena/pilot-{args.system}.json")
    raw_out = ROOT / f"data/lab/arena/pilot-raw/{args.system}.json"

    ledger = SpendLedger(total_cap_usd=args.total_cap_usd,
                         run_id=f"{args.system}-{mode}")
    units = load_units(selection_path, CORPUS)
    if args.only_origin:
        units = [u for u in units if u["_meta"].get("origin") == args.only_origin]
        if not units:
            raise SystemExit(f"no units with origin {args.only_origin!r}")
    built = SYSTEMS[args.system](args, ledger)
    adapter, probe, provider = built["adapter"], built["probe"], built["provider"]
    #: Either the in-process wrapper or the proxy, whichever this system is
    #: metered by. Both count calls and price them; neither is the system's own.
    meter = built.get("meter") or provider
    #: What the meter had already counted before this run began. A long-lived
    #: proxy serves the calibration and then the pilot, so its running totals are
    #: not this run's spend — Hindsight's first pilot artefact reported its
    #: calibration inside its pilot figure until this was subtracted.
    meter_baseline = meter.snapshot() if meter is not None else None
    baseline_usd = meter.spent_usd if meter is not None else 0.0

    record: dict[str, Any] = {
        "artifact": f"arena-{mode}-{args.system}",
        "mode": mode,
        "system": getattr(adapter, "name", args.system),
        "contract_version": CONTRACT_VERSION,
        "contract_digest": contract_digest(),
        "runner_digest": digest_of(Path(__file__)),
        "adapter_digest": digest_of(ROOT / f"scripts/arena/{args.system}_adapter.py")
        if (ROOT / f"scripts/arena/{args.system}_adapter.py").exists() else None,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection": json.loads(selection_path.read_text(encoding="utf-8"))["selection_sha256"],
        "selection_id": json.loads(selection_path.read_text(encoding="utf-8")).get("selection_id"),
        "only_origin": args.only_origin,
        "source": built["source"],
        "target_model": args.model if meter else "none — this system calls no model",
        "decoding": {
            "arena_enforced": ARENA_DECODING if meter else None,
            "preregistered": False,
            "provenance": ("adopted after a CUPMem run showed a repeated probe "
                           "returning different answers, so it is a control chosen "
                           "in response to an observation, not before one. It is not "
                           "any system's own decoding"),
        },
        "spend_cap_usd": args.cap_usd,
        "total_cap_usd": args.total_cap_usd,
        "state_probe_available": probe is not None,
        "units": [],
        "status": "running",
        "not_a_leaderboard": ("four units, one run, a crude correctness proxy and a "
                              "decoder that is not reproducible. A difference of a "
                              "few points here is noise, not an advantage"),
    }
    raw: list[dict[str, Any]] = []

    def flush(status: str) -> None:
        record["status"] = status
        record["spend_usd"] = round(meter.spent_usd - baseline_usd, 4) if meter else 0.0
        record["meter_baseline"] = meter_baseline
        record["meter_baseline_usd"] = round(baseline_usd, 6)
        if provider is not None:
            record["provider_calls"] = len(provider.request_log)
            record["decoding_overrides"] = len(provider.overrides)
            record["decoding_override_values"] = sorted(
                {json.dumps(c["overridden"], sort_keys=True) for c in provider.overrides})
        elif built.get("meter") is not None:
            meter_summary = built["meter"].summary()
            record["provider_calls"] = meter_summary["calls"] - (meter_baseline or {}).get("calls", 0)
            record["meter"] = meter_summary
            record["meter_note"] = ("`meter` holds the proxy's running totals, which "
                                    "include anything it served before this run. "
                                    "`spend_usd` and `provider_calls` are this run's "
                                    "own, taken as a delta from the baseline")
        else:
            record["provider_calls"] = 0
        record["night_ledger"] = ledger.summary()
        out.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
        raw_out.parent.mkdir(parents=True, exist_ok=True)
        raw_out.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")

    def fingerprint() -> str | None:
        return probe.fingerprint() if probe else None

    try:
        for unit in units:
            meta = unit["_meta"]
            sessions, dates = unit["haystack_sessions"], unit["haystack_dates"]
            if args.calibrate_sessions:
                sessions, dates = sessions[:args.calibrate_sessions], dates[:args.calibrate_sessions]

            adapter.reset()
            empty_digest = fingerprint()

            unit_record: dict[str, Any] = {
                "question_id": unit["question_id"], "question_type": unit["question_type"],
                "slot": meta["slot"], "sessions_available": len(unit["haystack_sessions"]),
                "sessions_ingested": 0, "user_turns_ingested": 0,
                "sessions_skipped_no_user_turn": 0,
                "ingest": {"model_calls": 0, "input_tokens": 0, "output_tokens": 0,
                           "wall_seconds": 0.0},
                "per_session_calls": [], "status": "ingesting",
            }
            record["units"].append(unit_record)
            flush("running")

            for index, (session, date) in enumerate(zip(sessions, dates)):
                records = as_records(session, date, index)
                if not records:
                    unit_record["sessions_skipped_no_user_turn"] += 1
                    continue
                cost = adapter.ingest(records)
                unit_record["sessions_ingested"] += 1
                unit_record["user_turns_ingested"] += len(records)
                unit_record["ingest"]["model_calls"] += cost.model_calls.value or 0
                unit_record["ingest"]["input_tokens"] += cost.input_tokens.value or 0
                unit_record["ingest"]["output_tokens"] += cost.output_tokens.value or 0
                unit_record["ingest"]["wall_seconds"] += round(
                    (cost.wall_microseconds.value or 0) / 1e6, 2)
                unit_record["per_session_calls"].append(cost.model_calls.value)
                if index % 5 == 0:
                    flush("running")

            unit_record["ingest"]["usd"] = round(
                unit_record["ingest"]["input_tokens"] / 1e6 * PRICE_PER_MTOK["input"]
                + unit_record["ingest"]["output_tokens"] / 1e6 * PRICE_PER_MTOK["output"], 4)
            after_ingest = fingerprint()
            unit_record["state_digest_after_ingest_differs"] = (
                None if probe is None else after_ingest != empty_digest)
            unit_record["stored_items"] = len(probe.stored_ids()) if probe else None

            if args.calibrate_sessions:
                unit_record["status"] = "calibrated"
                flush("calibration complete")
                break

            before_state = fingerprint()
            started = time.monotonic()
            answer = adapter.query(unit["question"], unit.get("question_date"))
            after_state = fingerprint()
            repeat = adapter.query(unit["question"], unit.get("question_date"))

            unit_record["query"] = cost_fields(answer.cost)
            unit_record["query"]["repeat"] = cost_fields(repeat.cost)
            unit_record["query"]["wall_seconds_measured"] = round(time.monotonic() - started, 2)
            unit_record["query"]["usd"] = round(
                ((answer.cost.input_tokens.value or 0) + (repeat.cost.input_tokens.value or 0))
                / 1e6 * PRICE_PER_MTOK["input"]
                + ((answer.cost.output_tokens.value or 0) + (repeat.cost.output_tokens.value or 0))
                / 1e6 * PRICE_PER_MTOK["output"], 4)

            stored = set(probe.stored_ids()) if probe else set()
            unit_record["memory"] = {
                "evidence_ids": len(answer.evidence_ids),
                "evidence_all_traceable": (set(answer.evidence_ids) <= stored
                                           if probe else None),
                "context_tokens": answer.context_tokens,
                "context_tokens_measurable":
                    answer.system_metadata.get("context_tokens_measurable"),
                "context_tokens_is_floor": answer.system_metadata.get("context_tokens_is_floor"),
                "abstained": answer.abstained,
                "abstention_derivable": answer.system_metadata.get("abstention_derivable"),
                "abstention_channel": answer.system_metadata.get("abstention_channel"),
                "premise_status": answer.system_metadata.get("premise_status"),
                # ARENA-0.1: two measurements, never one inference. Without a
                # state probe this is `unknown`, which is recorded and is not a
                # failure — it is not silently turned into read_only.
                "query_mutates_state": (
                    "unknown" if probe is None
                    else "read_only" if before_state == after_state else "mutates_by_design"),
                "output_reproducible": "true" if (answer.text, answer.evidence_ids)
                                       == (repeat.text, repeat.evidence_ids) else "false",
                "declared_mutation_mode": getattr(adapter, "query_mutates_state", "unknown"),
            }

            # Retrieval against the corpus's own gold sessions, mapped by session
            # date. Mechanical: no guessing which passage a memory came from.
            unit_record["retrieval"] = retrieval_measure(
                unit, answer.system_metadata.get("evidence_times") or [])

            gold = str(unit.get("answer", ""))
            unit_record["task"] = {
                "crude_substring_match": crude_match(answer.text, gold),
                "metric": ("substring containment of the gold answer, NOT LongMemEval's "
                           "model judge. It under-counts every correct paraphrase and "
                           "is a signal check, not a score"),
                "answer_chars": len(answer.text),
            }
            raw.append({
                "question_id": unit["question_id"], "question": unit.get("question"),
                "gold": gold, "answer": answer.text, "repeat_answer": repeat.text,
                "evidence_ids": answer.evidence_ids,
                "gold_session_ids": unit.get("answer_session_ids"),
            })

            unit_record["status"] = "complete"
            flush("running")

            adapter.reset()
            unit_record["reset_returns_to_empty"] = (
                None if probe is None else fingerprint() == empty_digest)

        flush("complete" if not args.calibrate_sessions else "calibration complete")

    except (SpendCapReached, TotalCapReached) as stop:
        record["stopped_by_cap"] = str(stop)
        for unit_record in record["units"]:
            if unit_record["status"] not in {"complete", "calibrated"}:
                unit_record["status"] = "stopped at spend cap"
        flush("stopped at spend cap")
        print(f"STOPPED: {stop}")
    except Exception as failure:  # noqa: BLE001 - a crash must not lose paid work
        record["failed_with"] = f"{type(failure).__name__}: {failure}"
        record["traceback"] = traceback.format_exc()[-4000:]
        flush("failed")
        print(f"FAILED: {record['failed_with']}")

    done = [u for u in record["units"] if u["status"] in {"complete", "calibrated"}]
    print(f"{args.system}: {record['status']}, {len(done)}/{len(units)} units, "
          f"{record['provider_calls']} calls, ${record['spend_usd']}, "
          f"night total ${ledger.total_usd():.4f}")
    for unit_record in record["units"]:
        print(f"  {unit_record['slot']:7s} {unit_record['sessions_ingested']:3d} sessions  "
              f"{unit_record['ingest']['model_calls']:5d} calls  "
              f"${unit_record['ingest'].get('usd', 0)}  "
              f"match={unit_record.get('task', {}).get('crude_substring_match')}  "
              f"{unit_record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
