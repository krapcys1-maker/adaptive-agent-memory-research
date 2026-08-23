"""What a frozen run would cost, computed from corpus size and a measured rate.

Bound spend before the fact. The runner refuses to start above a ceiling, and
this is what fills the ceiling in with a number rather than a hope.

Two inputs, kept separate because they fail differently:

    corpus shape   sessions and turns per unit, counted from the file. Free.
    unit rate      calls and tokens per session, measured on a real run of the
                   system under test. Not free, and not transferable between
                   systems.

The rate is a **floor**, and the projection says so. CUPMem's measured rate comes
from single-turn sessions; a session with ten turns yields more chunks, and their
write path spends per chunk — one delta extraction, one judge per delta, one
invalidation proposal, one judge per proposal. So the projection under-states,
and a projection that under-states must never be reported as a total. The
distinction is the same one the Cost class exists to keep.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]

PRICE_PER_MTOK = {"input": 0.27, "output": 1.10}


def selected_ids(selection: Path) -> set[str]:
    return {json.loads(line)["question_id"]
            for line in selection.read_text(encoding="utf-8").splitlines() if line.strip()}


def stream_questions(corpus: Path) -> Iterator[dict[str, Any]]:
    """Every question in the corpus. Read the way the bridge already reads it.

    277 MB resident rather than streamed, matching `prepare_longmemeval_bridge`,
    so both read the same file the same way and a difference between their counts
    is a real difference rather than a parser artefact.
    """
    with corpus.open(encoding="utf-8") as handle:
        yield from json.load(handle)


def shape(corpus: Path, wanted: set[str]) -> dict[str, Any]:
    per_unit: list[dict[str, Any]] = []
    for question in stream_questions(corpus):
        qid = str(question.get("question_id", ""))
        if wanted and qid not in wanted:
            continue
        sessions = question.get("haystack_sessions") or []
        turns = [len(session) for session in sessions]
        user_turns = [
            sum(1 for turn in session
                if str((turn or {}).get("role", "")).strip() == "user"
                and str((turn or {}).get("content", "")).strip())
            for session in sessions
        ]
        words = sum(len(str((turn or {}).get("content", "")).split())
                    for session in sessions for turn in session)
        per_unit.append({
            "question_id": qid,
            "question_type": question.get("question_type"),
            "sessions": len(sessions),
            "turns": sum(turns),
            "user_turns": sum(user_turns),
            "words": words,
        })
        if wanted and len(per_unit) == len(wanted):
            break
    return {
        "units": len(per_unit),
        "sessions_total": sum(u["sessions"] for u in per_unit),
        "sessions_median": statistics.median(u["sessions"] for u in per_unit),
        "user_turns_total": sum(u["user_turns"] for u in per_unit),
        "user_turns_median": statistics.median(u["user_turns"] for u in per_unit),
        "words_total": sum(u["words"] for u in per_unit),
        "per_unit": per_unit,
    }


def project(shape_: dict[str, Any], rate: dict[str, float], units: int) -> dict[str, Any]:
    """Scale the measured per-session rate over the corpus, as a floor."""
    if not shape_["units"]:
        return {}
    per_unit_sessions = shape_["sessions_total"] / shape_["units"]
    sessions = per_unit_sessions * units
    calls = sessions * rate["calls_per_session"]
    prompt = sessions * rate["prompt_tokens_per_session"]
    completion = sessions * rate["completion_tokens_per_session"]
    usd = prompt / 1e6 * PRICE_PER_MTOK["input"] + completion / 1e6 * PRICE_PER_MTOK["output"]
    return {
        "units": units,
        "sessions": round(sessions),
        "ingest_calls": round(calls),
        "ingest_prompt_tokens": round(prompt),
        "ingest_completion_tokens": round(completion),
        "ingest_usd": round(usd, 2),
        "is_floor": True,
        "why_a_floor": (
            "the rate was measured on single-turn sessions. Their write path spends "
            "per extracted chunk, and a session of many turns yields more chunks, so "
            "a real session costs at least this and probably several times it"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=str(
        ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7/longmemeval_s_cleaned.json"))
    parser.add_argument("--selection", default=str(
        ROOT / "data/lab/longmemeval-bridge-v0/selection.jsonl"))
    parser.add_argument("--system", default="CUPMem")
    # Measured, from data/lab/arena/cupmem-operational-fit.json: 4 single-turn
    # sessions cost 31 calls, 52,882 prompt and 2,821 completion tokens.
    parser.add_argument("--calls-per-session", type=float, default=31 / 4)
    parser.add_argument("--prompt-per-session", type=float, default=52882 / 4)
    parser.add_argument("--completion-per-session", type=float, default=2821 / 4)
    parser.add_argument("--out", default=str(ROOT / "data/lab/arena/run-cost-projection.json"))
    args = parser.parse_args()

    rate = {
        "calls_per_session": args.calls_per_session,
        "prompt_tokens_per_session": args.prompt_per_session,
        "completion_tokens_per_session": args.completion_per_session,
        "measured_on": ("4 single-turn sessions in the ARENA-0 operational-fit run; "
                        "ingestion only, query cost excluded"),
    }
    bridge = shape(Path(args.corpus), selected_ids(Path(args.selection)))

    record = {
        "artifact": "arena-run-cost-projection",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "system": args.system,
        "corpus": "LongMemEval-S cleaned, restricted to the frozen bridge selection",
        "rate": rate,
        "shape": {k: v for k, v in bridge.items() if k != "per_unit"},
        "projections": {
            f"{units}_units": project(bridge, rate, units)
            for units in (1, 10, 20, 36)
        },
        "excluded_from_every_figure": [
            "query cost, measured at 3 to 7 calls and 9k to 17k prompt tokens per probe",
            "retries, which their client makes up to three of per call",
            "every other system in the arena, whose rate is its own and unmeasured",
        ],
        "per_unit": bridge["per_unit"],
    }
    Path(args.out).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(f"{bridge['units']} units, {bridge['sessions_total']} sessions "
          f"(median {bridge['sessions_median']}/unit), "
          f"{bridge['user_turns_total']} user turns")
    for name, projection in record["projections"].items():
        print(f"  {name:10s} {projection['sessions']:>6} sessions  "
              f"{projection['ingest_calls']:>7} calls  "
              f"{projection['ingest_prompt_tokens']:>10} prompt  "
              f"at least ${projection['ingest_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
