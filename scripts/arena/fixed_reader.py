#!/usr/bin/env python3
"""One reader over both systems' contexts, to separate memory from the missing reader.

Neither Mem0 nor Hindsight composes an answer. Both return a stored memory, and
the judge has been comparing that memory against a gold answer — so the ten-unit
result may have been measuring the absence of a reader rather than a failure of
memory. Giving both systems' contexts to one identical reader separates those.

Three arms, one reader, one prompt, one set of parameters:

    mem0        the context Mem0 delivered, verbatim and in order
    hindsight   the context Hindsight delivered, verbatim and in order
    baseline    the question alone, no memory at all

The baseline is the arm that can embarrass everything else. If a reader answers
these questions from its own priors, then a difference between two memory systems
was never the thing being measured.

What the reader is not told
----------------------------
Which system a context came from, what it cost, how much of it there is, what any
earlier metric said, or the gold answer. Contexts are addressed by anonymous ids
and the mapping is written to a separate file.

Why an arm can be UNOBSERVABLE
-------------------------------
This experiment consumes frozen artefacts. If the delivered context text was not
persisted for a probe, that probe is UNOBSERVABLE for that arm — it is not
reconstructed from ids, not re-retrieved, and not guessed at. Re-running
retrieval would be a different measurement wearing this one's name.
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
from arena.spend_ledger import SpendLedger  # noqa: E402

ARENA = ROOT / "data/lab/arena"
SYSTEMS = ("mem0", "hindsight")

#: Fixed before any output was seen, and not to be edited afterwards. Given
#: verbatim as the system message to every arm, including the baseline, so the
#: only difference between arms is whether a context follows it.
READER_PROMPT = (
    "You are answering a question using the provided memory context.\n\n"
    "Use the memory context as the primary source of evidence.\n"
    "Answer the question directly and concisely.\n"
    "Do not mention the memory system or the retrieval process.\n"
    "If the context does not contain enough information, say that the answer "
    "cannot be determined from the provided context."
)

READER_PARAMS = {"temperature": 0, "max_tokens": 300}


def prompt_hash() -> str:
    return hashlib.sha256(READER_PROMPT.encode()).hexdigest()


def anonymous(arm: str, salt: str) -> str:
    digest = hashlib.sha256(f"{salt}{arm}".encode()).hexdigest()
    return f"context_{chr(65 + int(digest[:8], 16) % 26)}_{digest[:4]}"


def user_message(question: str, context: list[str] | None) -> str:
    """Question plus context, or question alone. Nothing else ever varies."""
    if context is None:
        return f"Question: {question}"
    joined = "\n".join(f"- {text}" for text in context)
    return f"Memory context:\n{joined}\n\nQuestion: {question}"


def load_arms(selection: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every (arm, probe) pair that can run, and every one that cannot."""
    units = {u["question_id"]: u for u in
             json.loads(selection.read_text(encoding="utf-8"))["units"]}
    raw: dict[str, dict[str, dict[str, Any]]] = {}
    for system in SYSTEMS:
        raw[system] = {}
        # Newest first: the rerun exists to supply the contexts the earlier runs
        # discarded, so its entries win. `setdefault` below keeps the first seen.
        for path in (ARENA / f"raw/arena-expansion-v1/{system}.json",
                     ARENA / f"pilot-raw/{system}.json"):
            if not path.exists():
                continue
            for entry in json.loads(path.read_text(encoding="utf-8")):
                if entry["question_id"] in units:
                    raw[system].setdefault(entry["question_id"], entry)

    # Question and gold come from the corpus, not from a system's raw file. Two
    # of those files were overwritten before this experiment existed, and the
    # baseline arm has no reason to depend on a system's bookkeeping for text the
    # benchmark itself owns.
    corpus = ROOT / ("external/datasets/longmemeval-cleaned-98d7416c24c7"
                     "/longmemeval_s_cleaned.json")
    with corpus.open(encoding="utf-8") as handle:
        by_qid = {row["question_id"]: row for row in json.load(handle)
                  if row.get("question_id") in units}

    # Baselines already generated under an identical reader configuration.
    already_baselined: set[str] = set()
    previous = ARENA / "fixed-reader.json"
    prior_outputs = ARENA / "raw/fixed-reader/outputs.json"
    if previous.exists() and prior_outputs.exists():
        record = json.loads(previous.read_text(encoding="utf-8"))
        same = (record.get("reader", {}).get("system_prompt_sha256") == prompt_hash()
                and record.get("reader", {}).get("parameters") == READER_PARAMS)
        if same:
            already_baselined = {
                o["question_id"] for o in
                json.loads(prior_outputs.read_text(encoding="utf-8"))
                if o.get("_arm") == "baseline"}

    runnable: list[dict[str, Any]] = []
    unobservable: list[dict[str, Any]] = []
    for qid, unit in units.items():
        row = by_qid.get(qid, {})
        question, gold = row.get("question"), str(row.get("answer", ""))
        for system in SYSTEMS:
            entry = raw[system].get(qid)
            context = (entry or {}).get("context_texts")
            case = {"arm": system, "question_id": qid, "slot": unit["slot"],
                    "question_type": unit["question_type"], "question": question,
                    "gold": gold, "context": context}
            if not context:
                unobservable.append(case | {
                    "why": ("the delivered context text was not persisted for this "
                            "probe, and the store was reset per unit, so it cannot "
                            "be looked up. Re-running retrieval would be a different "
                            "measurement")})
            else:
                runnable.append(case)
        if question and qid not in already_baselined:
            # The baseline needs no context and is therefore always runnable —
            # but it is also deterministic in its inputs, so a baseline already
            # generated under the same reader, prompt and parameters is reused
            # rather than paid for again. Reuse is refused if any of those three
            # differ, because then it is not the same arm.
            runnable.append({"arm": "baseline", "question_id": qid,
                             "slot": unit["slot"], "question_type": unit["question_type"],
                             "question": question, "gold": gold, "context": None})
    return runnable, unobservable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", default=str(ARENA / "expansion-selection.json"))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cap-usd", type=float, default=0.30)
    parser.add_argument("--salt", default="arena-fixed-reader-v1")
    parser.add_argument("--out", default=str(ARENA / "fixed-reader.json"))
    parser.add_argument("--raw-out", default=str(ARENA / "raw/fixed-reader/outputs.json"))
    parser.add_argument("--mapping-out", default=str(ARENA / "fixed-reader-blinding.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    runnable, unobservable = load_arms(Path(args.selection))
    messages = [user_message(c["question"], c["context"]) for c in runnable]
    projected_prompt = sum(len(READER_PROMPT) + len(m) for m in messages) // 4
    projected = round(projected_prompt / 1e6 * PRICE_PER_MTOK["input"]
                      + len(runnable) * READER_PARAMS["max_tokens"] / 1e6
                      * PRICE_PER_MTOK["output"], 6)

    print(f"runnable arms: {len(runnable)}  unobservable: {len(unobservable)}")
    for arm in ("mem0", "hindsight", "baseline"):
        print(f"  {arm:10s} runnable {sum(1 for c in runnable if c['arm'] == arm):2d}  "
              f"unobservable {sum(1 for c in unobservable if c['arm'] == arm):2d}")
    print(f"projected ${projected:.4f} against a ${args.cap_usd:.2f} cap")
    if projected > args.cap_usd:
        raise SystemExit(f"projection ${projected} exceeds the cap; stopping")
    if args.project_only or not runnable:
        return 0

    from openai import OpenAI

    from arena.run_pilot import load_key

    ledger = SpendLedger(run_id="fixed-reader")
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url=args.base_url),
                           fixed={"temperature": READER_PARAMS["temperature"]},
                           spend_cap_usd=args.cap_usd, shared_ledger=ledger)
    blinding = {arm: anonymous(arm, args.salt) for arm in ("mem0", "hindsight", "baseline")}

    outputs: list[dict[str, Any]] = []
    stopped = None
    try:
        for case, message in zip(runnable, messages):
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "system", "content": READER_PROMPT},
                          {"role": "user", "content": message}],
                max_tokens=READER_PARAMS["max_tokens"])
            usage = getattr(response, "usage", None)
            outputs.append({
                "context_id": blinding[case["arm"]],
                "question_id": case["question_id"],
                "slot": case["slot"],
                "question_type": case["question_type"],
                "question": case["question"],
                "gold": case["gold"],
                "context_items": 0 if case["context"] is None else len(case["context"]),
                "context_tokens": (0 if case["context"] is None
                                   else sum(len(t.split()) for t in case["context"])),
                "answer": (response.choices[0].message.content or "").strip(),
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
                "_arm": case["arm"],
            })
    except SpendCapReached as stop:
        stopped = str(stop)

    record = {
        "artifact": "arena-fixed-reader",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection": json.loads(Path(args.selection).read_text(encoding="utf-8"))[
            "selection_sha256"],
        "question": ("does a common reader change the Mem0/Hindsight comparison, and "
                     "does memory beat a reader working from its own priors"),
        "reader": {
            "model": args.model, "provider": "DeepSeek",
            "system_prompt": READER_PROMPT,
            "system_prompt_sha256": prompt_hash(),
            "parameters": READER_PARAMS,
            "identical_across_arms": True,
            "one_generation_per_context": True,
            "variance": ("one generation per context at this stage. Any single output "
                         "that turns out to carry a conclusion is marked as needing "
                         "replication rather than multiplied now"),
        },
        "blinding": {"salt": args.salt, "mapping_file": Path(args.mapping_out).name,
                     "note": "the reader is told only the question and the context"},
        "arms": {arm: sum(1 for o in outputs if o["_arm"] == arm)
                 for arm in ("mem0", "hindsight", "baseline")},
        "unobservable": unobservable,
        "unobservable_count": len(unobservable),
        "cost": {
            "calls": len(client.request_log),
            "prompt_tokens": sum(o["prompt_tokens"] for o in outputs),
            "completion_tokens": sum(o["completion_tokens"] for o in outputs),
            "usd": round(client.spent_usd, 6),
            "cap_usd": args.cap_usd,
            "projected_usd": projected,
        },
        "stopped_by_cap": stopped,
    }
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    raw_path = Path(args.raw_out)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    Path(args.mapping_out).write_text(
        json.dumps({"salt": args.salt, "mapping": blinding}, indent=2) + "\n",
        encoding="utf-8")

    print(f"generated {len(outputs)} reader outputs, "
          f"{len(client.request_log)} calls, ${client.spent_usd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
