#!/usr/bin/env python3
"""Judge Mem0's four breadth arms with the same corrected LongMemEval judge.

Reuses `judge_pilot`'s protocol byte-for-byte -- the prompt templates, the
`n=1, temperature=0, max_tokens=10` parameters, the `'yes' in response.lower()`
label rule, and the `degenerate()` guard that scores an empty response to an
answerable question as wrong -- by importing it rather than restating it, so
`judge_protocol_sha256` computed over `judge_pilot.py` still means what it says.

The only thing this file adds is spend-cap wiring: a run cap, a scope-wide total
cap, and a cap scope, mirroring `run_breadth_reader.py` rather than
`judge_pilot.main()`'s untracked, unscoped ledger.

No change to: templates, parameters, label rule, degenerate rule, or blinding
method.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import PRICE_PER_MTOK, FixedDecoding, SpendCapReached  # noqa: E402
from arena.judge_pilot import (  # noqa: E402
    ABSTENTION,
    GENERIC,
    JUDGE_PARAMS,
    KNOWLEDGE_UPDATE,
    PREFERENCE,
    TEMPORAL,
    anonymous_label,
    degenerate,
    label_of,
    load_cases,
    prompt_for,
)
from arena.spend_ledger import SpendLedger  # noqa: E402

ARENA = ROOT / "data/lab/arena"
ARMS = ("mem0_original", "mem0_500", "mem0_1000", "mem0_3000")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", default=str(ARENA / "expansion-selection.json"))
    parser.add_argument("--raw-dir", default=str(ARENA / "raw/mem0-breadth"))
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cap-usd", type=float, default=0.20, help="this run's own ceiling")
    parser.add_argument("--total-cap-usd", type=float, default=1.00,
                        help="the whole experiment's ceiling, counted over --cap-scope")
    parser.add_argument("--cap-scope", default="clean-")
    parser.add_argument("--salt", default="arena-mem0-breadth-judge-v1")
    parser.add_argument("--out", default=str(ARENA / "mem0-breadth-judged.json"))
    parser.add_argument("--mapping-out", default=str(ARENA / "mem0-breadth-judge-blinding.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    arms = tuple(a.strip() for a in args.arms.split(",") if a.strip())
    raw_files = {arm: [Path(args.raw_dir) / f"{arm}.json"] for arm in arms}
    cases = load_cases(Path(args.selection), arms, raw_files)
    blinding = {arm: anonymous_label(arm, args.salt) for arm in arms}

    prompts = [prompt_for(c["question_type"], c["question"], c["gold"], c["response"],
                          c["abstention"]) for c in cases]
    projected_prompt_tokens = sum(len(p) for p in prompts) // 4 * 2
    projected_usd = round(
        projected_prompt_tokens / 1e6 * PRICE_PER_MTOK["input"]
        + len(cases) * 2 * JUDGE_PARAMS["max_tokens"] / 1e6 * PRICE_PER_MTOK["output"], 6)

    print(f"{len(cases)} answers x up to 2(+1) passes")
    print(f"projected ${projected_usd:.4f} against a ${args.cap_usd:.2f} run cap, "
         f"${args.total_cap_usd:.2f} scope {args.cap_scope!r} total cap")
    if projected_usd > args.cap_usd:
        raise SystemExit(f"projection ${projected_usd} exceeds the run cap; stopping")
    if args.project_only:
        return 0

    from openai import OpenAI

    from arena.run_pilot import load_key

    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id="clean-breadth-judge",
                         cap_scope=args.cap_scope)
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url=args.base_url),
                           fixed={"temperature": JUDGE_PARAMS["temperature"]},
                           spend_cap_usd=args.cap_usd, shared_ledger=ledger)

    def judge(prompt: str, pass_name: str) -> dict[str, Any]:
        response = client.chat.completions.create(
            model=args.model, messages=[{"role": "user", "content": prompt}],
            n=JUDGE_PARAMS["n"], max_tokens=JUDGE_PARAMS["max_tokens"])
        text = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        return {"pass": pass_name, "raw": text, "label": label_of(text),
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0)}

    judged: list[dict[str, Any]] = []
    stopped = None
    try:
        for case, prompt in zip(cases, prompts):
            reason = degenerate(case["response"], case["abstention"])
            if reason is not None:
                judged.append({
                    "candidate": blinding[case["system"]], "question_id": case["question_id"],
                    "question_type": case["question_type"], "slot": case["slot"],
                    "response_chars": len(case["response"]), "abstention_prompt": case["abstention"],
                    "run": case["run"], "passes": [], "stable": True, "disputed": False,
                    "label": False, "not_sent_to_judge": reason, "_arm": case["system"],
                })
                continue
            passes = [judge(prompt, "A"), judge(prompt, "B")]
            if passes[0]["label"] != passes[1]["label"]:
                passes.append(judge(prompt, "C"))
            votes = [p["label"] for p in passes]
            final = sum(votes) > len(votes) / 2
            judged.append({
                "candidate": blinding[case["system"]], "question_id": case["question_id"],
                "question_type": case["question_type"], "slot": case["slot"],
                "response_chars": len(case["response"]), "abstention_prompt": case["abstention"],
                "run": case["run"], "passes": passes,
                "stable": passes[0]["label"] == passes[1]["label"],
                "disputed": len(passes) == 3, "label": final, "_arm": case["system"],
            })
    except SpendCapReached as stop:
        stopped = str(stop)

    prompt_tokens = sum(p["prompt_tokens"] for j in judged for p in j["passes"])
    completion_tokens = sum(p["completion_tokens"] for j in judged for p in j["passes"])
    record = {
        "artifact": "arena-mem0-breadth-judged",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection": json.loads(Path(args.selection).read_text(encoding="utf-8"))["selection_sha256"],
        "arms_judged": list(arms),
        "protocol": {
            "source": "LongMemEval src/evaluation/evaluate_qa.py, reused via judge_pilot.py import",
            "repository": "xiaowu0162/LongMemEval",
            "commit": "9e0b455f4ef0e2ab8f2e582289761153549043fc",
            "template_sha256": {
                name: hashlib.sha256(t.encode()).hexdigest()
                for name, t in (("generic", GENERIC), ("temporal", TEMPORAL),
                               ("knowledge_update", KNOWLEDGE_UPDATE),
                               ("preference", PREFERENCE), ("abstention", ABSTENTION))
            },
            "label_rule": "'yes' in response.lower(); binary, no partial credit",
            "parameters": JUDGE_PARAMS,
            "identical_to": "arena-pilot-judge / arena-fixed-reader-v1 judge protocol",
        },
        "blinding": {"salt": args.salt, "mapping_file": Path(args.mapping_out).name},
        "cost": {"calls": len(client.request_log), "prompt_tokens": prompt_tokens,
                 "completion_tokens": completion_tokens, "usd": round(client.spent_usd, 6),
                 "cap_usd": args.cap_usd, "projected_usd": projected_usd},
        "stopped_by_cap": stopped,
        "judgements": judged,
    }
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    Path(args.mapping_out).write_text(
        json.dumps({"salt": args.salt, "mapping": blinding}, indent=2) + "\n", encoding="utf-8")

    print(f"judged {len(judged)}/{len(cases)}  {len(client.request_log)} calls  "
         f"${client.spent_usd:.4f}")
    print(f"stable {sum(1 for j in judged if j['stable'])}  "
         f"disputed {sum(1 for j in judged if j['disputed'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
