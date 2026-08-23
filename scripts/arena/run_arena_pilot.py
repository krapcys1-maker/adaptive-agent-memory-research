#!/usr/bin/env python3
"""The arena pilot: four frozen units, one system, a hard cap on the money.

What this is for
----------------
Not a leaderboard. Four units cannot be one, and this run is not permitted to
pretend otherwise. It answers three questions, in order of how much they matter:

    does the pipeline work end to end on a real corpus
    what does it actually cost, ingest and query separately
    is there any signal at all worth spending more on

Two rules it enforces rather than trusts
----------------------------------------
**The cap is enforced below the provider, not above it.** `FixedDecoding`
refuses the request that could cross it, so a runaway ingest stops mid-unit
instead of reporting an overspend afterwards.

**Partial results are written as they happen.** A run that stops at the cap must
leave everything it has already paid for. A background run once died after 29 calls with
no result file and the spend was still real.

What may be fixed if this run breaks, and what may not
------------------------------------------------------
Fixable: adapter translation, serialisation, cost accounting, reset and leakage,
a malformed measurement, infrastructure. Not fixable, at any point, from
anything seen here: retrieval, prompts, memory policy, or any benchmark-specific
rule. Changing a competitor because the arena showed it losing voids the run,
and there is no version of that which is only a small amount of tuning.

Where the corpus text goes
--------------------------
Not into git. Question text, gold answers and composed answers are written to an
ignored sibling directory; the committed artefact carries measurements, and a
deliberately crude correctness proxy that is named as crude.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.adapter_v0_1 import CONTRACT_VERSION, contract_digest  # noqa: E402
from arena.cupmem_adapter import CUPMemAdapter  # noqa: E402
from arena.cupmem_probe import CUPMemStateProbe  # noqa: E402
from arena.decoding import (  # noqa: E402
    ARENA_DECODING, PRICE_PER_MTOK, FixedDecoding, SpendCapReached,
)
from arena.record_source_provenance import describe  # noqa: E402

CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")
SELECTION = ROOT / "data/lab/arena/pilot-selection.json"


def load_key() -> str:
    for env in (ROOT / ".env", ROOT.parent / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DEEPSEEK_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DEEPSEEK_API_KEY in .env or ../.env")


def build_engine(model_path: Path, model: str, base_url: str, cap: float):
    from openai import OpenAI

    from cup_mem.llm_layer.client import LLMClient
    from cup_mem.pipeline import CupMemEngine

    llm = LLMClient(
        model=model, api_key=load_key(), base_url=base_url,
        openai_cls=lambda **kwargs: FixedDecoding(OpenAI(**kwargs), spend_cap_usd=cap),
    )
    return CupMemEngine(llm=llm, embedding_model_path=str(model_path))


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


def as_records(session: list[dict[str, Any]], date: str,
               session_index: int) -> list[dict[str, Any]]:
    """One arena record per user turn, all sharing this session's date.

    Assistant turns are dropped here rather than downstream, because CUPMem's
    chunker drops them silently and an adapter that hands over turns it knows
    will vanish is reporting an ingest it did not make.
    """
    return [
        {"id": f"s{session_index}_t{turn_index}", "timestamp": str(date or session_index),
         "text": str(turn.get("content", "")).strip()}
        for turn_index, turn in enumerate(session)
        if str(turn.get("role", "")).strip() == "user"
        and str(turn.get("content", "")).strip()
    ]


def cost_fields(cost) -> dict[str, Any]:
    return {
        "model_calls": cost.model_calls.value,
        "input_tokens": cost.input_tokens.value,
        "output_tokens": cost.output_tokens.value,
        "wall_seconds": round((cost.wall_microseconds.value or 0) / 1e6, 2),
        "fully_known": cost.fully_known,
        "observability": {f: getattr(cost, f).observability
                          for f in ("model_calls", "input_tokens", "output_tokens")},
    }


def crude_match(answer: str, gold: str) -> bool | None:
    """A substring proxy, and nothing more.

    LongMemEval's own metric is a model judge. This is not that, it UNDER-counts
    every correct paraphrase, and it is recorded so the pilot can say something
    about signal without paying for a judge. Any number derived from it must
    carry that sentence.
    """
    if not gold:
        return None
    return gold.strip().lower() in (answer or "").lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cupmem-root", default=str(ROOT / "external/repos/icedreamc__STALE"))
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cap-usd", type=float, default=3.00,
                        help="hard ceiling on new paid calls; enforced below the system")
    parser.add_argument("--calibrate-sessions", type=int, default=0,
                        help="ingest only this many sessions of the first unit, then stop")
    parser.add_argument("--out", default=str(ROOT / "data/lab/arena/pilot-cupmem.json"))
    parser.add_argument("--raw-out", default=str(ROOT / "data/lab/arena/pilot-raw/cupmem.json"))
    args = parser.parse_args()

    root = Path(args.cupmem_root).resolve()
    sys.path.insert(0, str(root))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    units = load_units(SELECTION, CORPUS)
    engine = build_engine(Path(args.embedding_model_path), args.model,
                          args.base_url, args.cap_usd)
    provider = engine.llm.client
    adapter = CUPMemAdapter(engine)
    probe = CUPMemStateProbe(engine)

    mode = "calibration" if args.calibrate_sessions else "pilot"
    record: dict[str, Any] = {
        "artifact": f"arena-{mode}-cupmem",
        "mode": mode,
        "contract_version": CONTRACT_VERSION,
        "contract_digest": contract_digest(),
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection": json.loads(SELECTION.read_text(encoding="utf-8"))["selection_sha256"],
        "system": "CUPMem",
        "source": {k: v for k, v in describe(root, "cup_mem", ("*.py",)).items()
                   if k != "files"},
        "embedding_model_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        "target_model": args.model,
        "decoding": {
            "arena_enforced": ARENA_DECODING,
            "preregistered": False,
            "provenance": ("adopted after a CUPMem run showed a repeated probe "
                           "returning different answers, so it is a control chosen "
                           "in response to an observation. It is not CUPMem's own "
                           "decoding and must not be read as native behaviour"),
            "system_native_requested": "recorded per call in decoding_overrides",
        },
        "spend_cap_usd": args.cap_usd,
        "price_per_mtok": PRICE_PER_MTOK,
        "units": [],
        "status": "running",
        "not_a_leaderboard": ("four units, one run, a crude correctness proxy and a "
                              "decoder that is not reproducible. A difference of a "
                              "few points here is noise, not an advantage"),
    }
    raw: list[dict[str, Any]] = []

    def flush(status: str) -> None:
        record["status"] = status
        record["spend_usd"] = round(provider.spent_usd, 4)
        record["provider_calls"] = len(provider.request_log)
        record["decoding_overrides"] = len(provider.overrides)
        record["decoding_override_values"] = sorted(
            {json.dumps(call["overridden"], sort_keys=True) for call in provider.overrides}
        )
        Path(args.out).write_text(json.dumps(record, indent=2, default=str) + "\n",
                                  encoding="utf-8")
        raw_path = Path(args.raw_out)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")

    try:
        for unit in units:
            meta = unit["_meta"]
            sessions = unit["haystack_sessions"]
            dates = unit["haystack_dates"]
            if args.calibrate_sessions:
                sessions = sessions[:args.calibrate_sessions]
                dates = dates[:args.calibrate_sessions]

            adapter.reset()
            empty_digest = probe.fingerprint()

            unit_record: dict[str, Any] = {
                "question_id": unit["question_id"],
                "question_type": unit["question_type"],
                "slot": meta["slot"],
                "sessions_available": len(unit["haystack_sessions"]),
                "sessions_ingested": 0,
                "user_turns_ingested": 0,
                "sessions_skipped_no_user_turn": 0,
                "ingest": {"model_calls": 0, "input_tokens": 0, "output_tokens": 0,
                           "wall_seconds": 0.0},
                "per_session_calls": [],
                "status": "ingesting",
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
            unit_record["state_digest_after_ingest_differs"] = (
                probe.fingerprint() != empty_digest)
            unit_record["stored_items"] = len(probe.stored_ids())

            if args.calibrate_sessions:
                unit_record["status"] = "calibrated"
                flush("calibration complete")
                break

            # ---------------------------------------------------------- query
            before_state = probe.fingerprint()
            started = time.monotonic()
            answer = adapter.query(unit["question"], unit.get("question_date"))
            after_state = probe.fingerprint()
            repeat = adapter.query(unit["question"], unit.get("question_date"))

            unit_record["query"] = cost_fields(answer.cost)
            unit_record["query"]["repeat"] = cost_fields(repeat.cost)
            unit_record["query"]["wall_seconds_measured"] = round(time.monotonic() - started, 2)
            unit_record["query"]["usd"] = round(
                ((answer.cost.input_tokens.value or 0)
                 + (repeat.cost.input_tokens.value or 0)) / 1e6 * PRICE_PER_MTOK["input"]
                + ((answer.cost.output_tokens.value or 0)
                   + (repeat.cost.output_tokens.value or 0)) / 1e6 * PRICE_PER_MTOK["output"], 4)

            unit_record["memory"] = {
                "evidence_ids": len(answer.evidence_ids),
                "evidence_all_traceable": set(answer.evidence_ids) <= set(probe.stored_ids()),
                "context_tokens": answer.context_tokens,
                "context_tokens_measurable":
                    answer.system_metadata.get("context_tokens_measurable"),
                "context_tokens_is_floor": answer.system_metadata.get("context_tokens_is_floor"),
                "abstained": answer.abstained,
                "abstention_derivable": answer.system_metadata.get("abstention_derivable"),
                "abstention_channel": answer.system_metadata.get("abstention_channel"),
                "premise_status": answer.system_metadata.get("premise_status"),
                # ARENA-0.1: two measurements, never one inference.
                "query_mutates_state": ("read_only" if before_state == after_state
                                        else "mutates_by_design"),
                "output_reproducible": "true" if (answer.text, answer.evidence_ids)
                                       == (repeat.text, repeat.evidence_ids) else "false",
            }

            gold = str(unit.get("answer", ""))
            unit_record["task"] = {
                "crude_substring_match": crude_match(answer.text, gold),
                "metric": ("substring containment of the gold answer, NOT LongMemEval's "
                           "model judge. It under-counts every correct paraphrase and "
                           "is a signal check, not a score"),
                "answer_chars": len(answer.text),
            }
            raw.append({
                "question_id": unit["question_id"],
                "question": unit.get("question"),
                "gold": gold,
                "answer": answer.text,
                "repeat_answer": repeat.text,
                "evidence_ids": answer.evidence_ids,
                "gold_session_ids": unit.get("answer_session_ids"),
            })

            unit_record["status"] = "complete"
            flush("running")

        flush("complete" if not args.calibrate_sessions else "calibration complete")

    except SpendCapReached as stop:
        record["stopped_by_cap"] = str(stop)
        for unit_record in record["units"]:
            if unit_record["status"] not in {"complete", "calibrated"}:
                unit_record["status"] = "stopped at spend cap"
        flush("stopped at spend cap")
        print(f"STOPPED: {stop}")

    done = [u for u in record["units"] if u["status"] in {"complete", "calibrated"}]
    print(f"{record['status']}: {len(done)}/{len(units)} units, "
          f"{record['provider_calls']} calls, ${record['spend_usd']}")
    for unit_record in record["units"]:
        print(f"  {unit_record['slot']:7s} {unit_record['question_id']:13s} "
              f"{unit_record['sessions_ingested']:3d} sessions  "
              f"{unit_record['user_turns_ingested']:4d} turns  "
              f"{unit_record['ingest']['model_calls']:5d} calls  "
              f"${unit_record['ingest'].get('usd', 0)}  {unit_record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
