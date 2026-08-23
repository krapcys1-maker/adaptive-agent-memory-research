#!/usr/bin/env python3
"""What the four frozen units will cost, from a rate measured on the same corpus.

Bound spend before the fact, and bound it with a number that came from this
corpus rather than from a fixture. The earlier projection extrapolated from four
single-turn synthetic sessions and was wrong in both directions at once: it
over-stated the per-session call count, and it missed entirely that the count
**grows** as the store fills.

Two models, because the measurement does not settle the shape on its own
-------------------------------------------------------------------------
Calls per session over the calibration prefix: 8 1 1 1 10 7 11 15 14 20 1 15 13
12 15. The first four sessions are cheap and the rest are not, so something
changes once there is state to work against.

    linear     fit calls-per-session against session index and extrapolate.
               Assumes the growth continues to the last session.
    plateau    the ramp is a one-time transition from an empty store to a
               populated one, after which cost is flat.

**The plateau model is the one to believe, and it is not the one reported as the
bound.** Every candidate pool in their config is top-k bounded — candidate_top_k
5, invalidation_global_recall_top_k 4, invalidation_merge_max_keep 2, query_top_k
8 — so per-call prompt size cannot grow without limit, and the last three
calibration sessions (13, 12, 15) are flat rather than still climbing. The linear
figure is carried anyway as the pessimistic bound, because a projection that only
reports the number it prefers is a hope.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PRICE_PER_MTOK = {"input": 0.27, "output": 1.10}

#: Measured on the operational-fit run: 3 to 7 calls and 9k to 17k prompt tokens
#: per probe. Two probes per unit, because ARENA-0.1 measures output
#: reproducibility by repeating one.
QUERY_CALLS_PER_PROBE = 6
QUERY_PROMPT_PER_PROBE = 13_000
QUERY_COMPLETION_PER_PROBE = 750
PROBES_PER_UNIT = 2


def usd(prompt: float, completion: float) -> float:
    return round(prompt / 1e6 * PRICE_PER_MTOK["input"]
                 + completion / 1e6 * PRICE_PER_MTOK["output"], 4)


def linear_fit(values: list[int]) -> tuple[float, float]:
    """Least squares of calls-per-session against session index."""
    n = len(values)
    mean_x = (n - 1) / 2
    mean_y = statistics.mean(values)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(values))
    sxx = sum((x - mean_x) ** 2 for x in range(n))
    slope = sxy / sxx if sxx else 0.0
    return slope, mean_y - slope * mean_x


def project(sessions: int, measured: list[int], tokens_per_call: float,
            completion_per_call: float, model: str) -> dict[str, Any]:
    known = len(measured)
    calls = float(sum(measured[:min(known, sessions)]))
    if model == "linear":
        slope, intercept = linear_fit(measured)
        calls += sum(max(0.0, intercept + slope * index)
                     for index in range(known, sessions))
    else:
        # The tail of the calibration, taken as the steady state.
        plateau = statistics.mean(measured[-5:]) if len(measured) >= 5 else statistics.mean(measured)
        calls += plateau * max(0, sessions - known)
    prompt = calls * tokens_per_call
    completion = calls * completion_per_call
    return {"calls": round(calls), "prompt_tokens": round(prompt),
            "completion_tokens": round(completion), "usd": usd(prompt, completion)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration",
                        default=str(ROOT / "data/lab/arena/pilot-calibration-cupmem.json"))
    parser.add_argument("--selection", default=str(ROOT / "data/lab/arena/pilot-selection.json"))
    parser.add_argument("--cap-usd", type=float, default=3.00)
    parser.add_argument("--tail-token-growth", type=float, default=1.25,
                        help="prompt tokens per call in the tail, relative to the "
                             "calibration mean; pools fill as the store does")
    parser.add_argument("--out", default=str(ROOT / "data/lab/arena/pilot-cost-projection.json"))
    args = parser.parse_args()

    calibration = json.loads(Path(args.calibration).read_text(encoding="utf-8"))
    selection = json.loads(Path(args.selection).read_text(encoding="utf-8"))
    unit = calibration["units"][0]
    measured = unit["per_session_calls"]

    tokens_per_call = unit["ingest"]["input_tokens"] / unit["ingest"]["model_calls"]
    completion_per_call = unit["ingest"]["output_tokens"] / unit["ingest"]["model_calls"]
    tail_tokens = tokens_per_call * args.tail_token_growth

    per_unit: dict[str, dict[str, Any]] = {}
    totals = {model: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0}
              for model in ("plateau", "linear")}
    for entry in selection["units"]:
        estimates = {
            model: project(entry["sessions"], measured, tail_tokens,
                           completion_per_call, model)
            for model in ("plateau", "linear")
        }
        per_unit[entry["question_id"]] = {"slot": entry["slot"],
                                          "sessions": entry["sessions"],
                                          "user_turns": entry["user_turns"],
                                          **estimates}
        for model, estimate in estimates.items():
            for field in ("calls", "prompt_tokens", "completion_tokens"):
                totals[model][field] += estimate[field]
            totals[model]["usd"] = round(totals[model]["usd"] + estimate["usd"], 4)

    units = len(selection["units"])
    query = {
        "probes": units * PROBES_PER_UNIT,
        "calls": units * PROBES_PER_UNIT * QUERY_CALLS_PER_PROBE,
        "prompt_tokens": units * PROBES_PER_UNIT * QUERY_PROMPT_PER_PROBE,
        "completion_tokens": units * PROBES_PER_UNIT * QUERY_COMPLETION_PER_PROBE,
    }
    query["usd"] = usd(query["prompt_tokens"], query["completion_tokens"])

    already = calibration.get("spend_usd", 0.0)
    grand = {model: round(totals[model]["usd"] + query["usd"] + already, 4)
             for model in totals}

    record = {
        "artifact": "arena-pilot-cost-projection",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "system": "CUPMem",
        "selection": selection["selection_sha256"],
        "cap_usd": args.cap_usd,
        "rate": {
            "measured_on": (f"{unit['sessions_ingested']} real sessions of unit "
                            f"{unit['question_id']}, {unit['user_turns_ingested']} user turns"),
            "calls_per_session": unit["per_session_calls"],
            "prompt_tokens_per_call": round(tokens_per_call),
            "completion_tokens_per_call": round(completion_per_call),
            "tail_token_growth_applied": args.tail_token_growth,
            "observation": ("calls per session rise as the store fills, from a mean of "
                            f"{round(statistics.mean(measured[:len(measured)//2]), 1)} over the "
                            f"first half to {round(statistics.mean(measured[len(measured)//2:]), 1)} "
                            "over the second, then flatten"),
        },
        "ingest": {"per_unit": per_unit, "totals": totals},
        "query": query | {"basis": "operational-fit run: 3-7 calls, 9k-17k prompt per probe"},
        "already_spent_on_calibration_usd": already,
        "projection_usd": grand,
        "believed": "plateau",
        "why": ("every candidate pool in their config is top-k bounded, so per-call "
                "prompt size cannot grow without limit, and the last three calibration "
                "sessions are flat rather than still climbing. The linear figure is the "
                "pessimistic bound, carried because a projection that reports only its "
                "preferred number is a hope"),
        "verdict": ("proceed" if grand["plateau"] <= args.cap_usd else "stop: over cap"),
        "guarantee": ("the cap is enforced beneath the provider, so the pessimistic model "
                      "being right costs a truncated run rather than an overspend"),
    }
    Path(args.out).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(f"rate: {round(tokens_per_call)} prompt tokens/call, "
          f"calls/session {measured}")
    for model in ("plateau", "linear"):
        print(f"  {model:8s} ingest {totals[model]['calls']:>6} calls  "
              f"${totals[model]['usd']:.2f}   + query ${query['usd']:.2f}  "
              f"+ calibration ${already}  =  ${grand[model]:.2f}")
    print(f"cap ${args.cap_usd:.2f} -> {record['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
