#!/usr/bin/env python3
"""Read Mem0's four breadth arms with the reader every other arm already used.

Consumes `mem0-breadth-arms.json`. Same model, same system prompt by hash, same
temperature and max_tokens as the arms that produced Hindsight 4/6/6/7 and the
0/10 baseline — otherwise the curves are not on one axis and comparing them means
nothing.

Blind: the reader sees a question and a context, never which arm, which system,
which budget, or any earlier number.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import PRICE_PER_MTOK, FixedDecoding, SpendCapReached  # noqa: E402
from arena.fixed_reader import READER_PARAMS, READER_PROMPT, prompt_hash, user_message  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402

ARENA = ROOT / "data/lab/arena"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", default=str(ARENA / "mem0-breadth-arms.json"))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cap-usd", type=float, default=0.20,
                        help="this run's own ceiling")
    parser.add_argument("--total-cap-usd", type=float, default=1.00,
                        help="the whole experiment's ceiling, counted over --cap-scope. "
                             "Distinct from --cap-usd: passing this run's ceiling as the "
                             "scope total refuses the first call, because the scope "
                             "already holds the ingest that produced these contexts")
    parser.add_argument("--cap-scope", default="clean-")
    parser.add_argument("--run-id", default="clean-breadth-reader",
                        help="ledger run_id. Must start with --cap-scope's prefix or "
                             "--total-cap-usd silently stops gating this run's own spend "
                             "-- found by reusing this script for the Hindsight ablation "
                             "fix with --cap-scope ablation-fix- while this stayed "
                             "hardcoded to clean-breadth-reader, so the intended cap "
                             "never matched any of this run's own ledger lines")
    parser.add_argument("--out-dir", default=str(ARENA / "raw/mem0-breadth"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    arms = json.loads(Path(args.arms).read_text(encoding="utf-8"))["arms"]
    arms = [a for a in arms if a.get("context")]
    prompts = [user_message(a["question"], a["context"]) for a in arms]
    projected = round(
        sum(len(READER_PROMPT) + len(p) for p in prompts) // 4 / 1e6 * PRICE_PER_MTOK["input"]
        + len(arms) * READER_PARAMS["max_tokens"] / 1e6 * PRICE_PER_MTOK["output"], 6)
    print(f"{len(arms)} reader calls, projected ${projected:.4f} against ${args.cap_usd:.2f}")
    if projected > args.cap_usd:
        raise SystemExit("projection exceeds the cap; stopping")
    if args.project_only:
        return 0

    from openai import OpenAI

    from arena.run_pilot import load_key

    ledger = SpendLedger(total_cap_usd=args.total_cap_usd,
                         run_id=args.run_id, cap_scope=args.cap_scope)
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url=args.base_url),
                           fixed={"temperature": READER_PARAMS["temperature"]},
                           spend_cap_usd=args.cap_usd, shared_ledger=ledger)

    outputs: list[dict[str, Any]] = []
    try:
        for arm, prompt in zip(arms, prompts):
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "system", "content": READER_PROMPT},
                          {"role": "user", "content": prompt}],
                max_tokens=READER_PARAMS["max_tokens"])
            outputs.append({k: v for k, v in arm.items() if k != "context"}
                           | {"answer": (response.choices[0].message.content or "").strip()})
    except SpendCapReached as stop:
        print(f"STOPPED: {stop}")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "outputs.json").write_text(
        json.dumps({"reader": {"model": args.model, "prompt_sha256": prompt_hash(),
                               "parameters": READER_PARAMS,
                               "identical_to": "arena-fixed-reader-v1"},
                    "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "cost_usd": round(client.spent_usd, 6),
                    "outputs": outputs}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    for name in sorted({o["arm"] for o in outputs}):
        rows = [{"question_id": o["question_id"], "question": o["question"],
                 "gold": o["gold"], "answer": o["answer"]}
                for o in outputs if o["arm"] == name]
        (out / f"{name}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"generated {len(outputs)} outputs, ${client.spent_usd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
