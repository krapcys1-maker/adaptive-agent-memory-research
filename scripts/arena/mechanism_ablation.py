#!/usr/bin/env python3
"""Two ablations that separate *how much* context from *what kind* of context.

The fixed-reader run left one question open. Hindsight hands the reader about
thirty times more context than Mem0 and answers 7 of 10 against 4 — but Mem0
puts the gold session at rank 1 in eight of nine observable units, so the
advantage cannot be retrieval accuracy. It is either volume, or something in
what Hindsight returns that Mem0's compacted memory has thrown away.

    A   cut Hindsight's own context to smaller budgets and nothing else.
        If 7/10 survives at Mem0's token count, volume was never the reason.

    B   give Mem0 its own compact memory plus the raw source session its top hit
        came from. If that repairs its failures, the missing thing is provenance
        rather than breadth.

Only the context varies. Same reader, same prompt, same parameters, same judge,
same frozen probes, no new retrieval and no new ingest. Every arm is built by a
rule fixed and written down before a single reader call.

What the truncation rule is, exactly
-------------------------------------
Evidence items are kept in the order the system returned them, whole, adding one
at a time while the next would still fit the budget. Nothing is re-ranked,
nothing is summarised, and **no item is selected using the gold answer** — which
is the only way a context-size curve can mean anything.

Two failure modes that must not be merged
------------------------------------------
    GOLD_DROPPED_BY_BUDGET              the budget cut the gold evidence out
    GOLD_PRESENT_BUT_CONTEXT_INSUFFICIENT  it survived and the answer still fell

The first says the budget was too small to hold the answer. The second says
holding the answer is not sufficient. Reporting them together would hide exactly
the distinction the experiment exists to draw.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import PRICE_PER_MTOK, FixedDecoding, SpendCapReached  # noqa: E402
from arena.fixed_reader import READER_PARAMS, READER_PROMPT, prompt_hash  # noqa: E402
from arena.retrieval_truth import canonical_time, gold_session_indices, session_map  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402

ARENA = ROOT / "data/lab/arena"
CORPUS = (ROOT / "external/datasets/longmemeval-cleaned-98d7416c24c7"
          / "longmemeval_s_cleaned.json")
EXPERIMENT = "arena-mechanism-ablation-v1"

#: Frozen before any reader call. Absolute budgets in whitespace tokens, plus the
#: per-probe Mem0 budget, which is read from Mem0's actual context on the same
#: probe rather than from its 106-token average — a mean would give some probes
#: more than Mem0 had and others less.
BUDGETS: dict[str, int | str] = {
    "hindsight_mem0_matched": "per-probe Mem0 context_tokens",
    "hindsight_500": 500,
    "hindsight_1000": 1000,
}

TOKENS = "whitespace-split words, the same unit context_tokens already uses"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_revision() -> str | None:
    try:
        return subprocess.run(("git", "rev-parse", "HEAD"), cwd=ROOT, check=True,
                              capture_output=True, text=True, timeout=20).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def truncate(items: list[str], budget: int) -> list[str]:
    """Whole items, original order, while the next still fits.

    Never partial items: half a memory is a context no system would ever have
    produced, and a reader shown one is being asked a question about an artefact
    of this script.
    """
    kept: list[str] = []
    used = 0
    for item in items:
        size = len(item.split())
        if used + size > budget:
            continue
        kept.append(item)
        used += size
    return kept


def gold_state(unit: dict[str, Any], times: list[str]) -> dict[str, Any]:
    """Gold presence and rank within whatever evidence survived the budget."""
    mapping = session_map(unit)
    if mapping is None:
        return {"observable": False, "gold_in_context": "UNOBSERVABLE",
                "gold_rank": "UNOBSERVABLE"}
    gold = gold_session_indices(unit)
    hits = [index for index, time in enumerate(times, start=1)
            if mapping.get(canonical_time(time)) in gold]
    return {"observable": True, "gold_in_context": bool(hits),
            "gold_rank": hits[0] if hits else None}


def raw_session(unit: dict[str, Any], time: str) -> tuple[str | None, int | None]:
    """The source session whose date matches this evidence, verbatim.

    Mechanical: the date is the key, and the key is unique or the probe is
    unobservable. No similarity, no model, no reading of the passages.
    """
    mapping = session_map(unit)
    if mapping is None:
        return None, None
    index = mapping.get(canonical_time(time))
    if index is None:
        return None, None
    session = (unit.get("haystack_sessions") or [])[index]
    text = "\n".join(f"{turn.get('role', '')}: {turn.get('content', '')}".strip()
                     for turn in session if (turn or {}).get("content"))
    return text, index


def load_inputs() -> dict[str, Any]:
    selection = json.loads((ARENA / "expansion-selection.json").read_text(encoding="utf-8"))
    units = {u["question_id"]: u for u in selection["units"]}
    with CORPUS.open(encoding="utf-8") as handle:
        corpus = {row["question_id"]: row for row in json.load(handle)
                  if row["question_id"] in units}
    raw = {}
    for system in ("mem0", "hindsight"):
        path = ARENA / f"raw/arena-expansion-v1/{system}.json"
        raw[system] = {e["question_id"]: e for e in
                       json.loads(path.read_text(encoding="utf-8"))}
    return {"selection": selection, "units": units, "corpus": corpus, "raw": raw}


def build_arms(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Every (arm, probe) context this experiment will send, built by the rules."""
    arms: list[dict[str, Any]] = []
    for qid, unit in data["units"].items():
        row = data["corpus"][qid]
        mem0 = data["raw"]["mem0"].get(qid) or {}
        hind = data["raw"]["hindsight"].get(qid) or {}
        mem0_budget = sum(len(t.split()) for t in (mem0.get("context_texts") or []))

        for name, budget in (("hindsight_mem0_matched", mem0_budget),
                             ("hindsight_500", 500), ("hindsight_1000", 1000)):
            items = hind.get("context_texts") or []
            times = hind.get("evidence_times") or []
            keep = truncate(items, int(budget))
            kept_times = [times[i] for i, item in enumerate(items) if item in keep][:len(keep)]
            arms.append({
                "arm": name, "question_id": qid, "slot": unit["slot"],
                "question_type": unit["question_type"], "question": row["question"],
                "gold": str(row.get("answer", "")), "context": keep,
                "budget_tokens": int(budget),
                "gold_state": gold_state(row, kept_times),
                "source": "hindsight persisted context, truncated by budget",
            })

        # Mem0 compact plus the raw source session behind its top hit.
        times = mem0.get("evidence_times") or []
        text, index = raw_session(row, times[0]) if times else (None, None)
        compact = mem0.get("context_texts") or []
        if text:
            arms.append({
                "arm": "mem0_compact_plus_raw", "question_id": qid, "slot": unit["slot"],
                "question_type": unit["question_type"], "question": row["question"],
                "gold": str(row.get("answer", "")),
                "context": compact + [f"[RAW SOURCE PROVENANCE]\n{text}"],
                "budget_tokens": None,
                "gold_state": gold_state(row, times),
                "provenance_session_index": index,
                "provenance_tokens": len(text.split()),
                "source": "mem0 compact context plus the raw session of its top-1 hit",
            })
            arms.append({
                "arm": "mem0_raw_only", "question_id": qid, "slot": unit["slot"],
                "question_type": unit["question_type"], "question": row["question"],
                "gold": str(row.get("answer", "")),
                "context": [f"[RAW SOURCE PROVENANCE]\n{text}"],
                "budget_tokens": None,
                "gold_state": gold_state(row, times[:1]),
                "provenance_session_index": index,
                "provenance_tokens": len(text.split()),
                "source": "the raw session of mem0's top-1 hit, without the compact memory",
            })
        else:
            for name in ("mem0_compact_plus_raw", "mem0_raw_only"):
                arms.append({
                    "arm": name, "question_id": qid, "slot": unit["slot"],
                    "question_type": unit["question_type"], "question": row["question"],
                    "gold": str(row.get("answer", "")), "context": None,
                    "unobservable": ("top-1 provenance could not be resolved "
                                     "mechanically: this unit's haystack dates do not "
                                     "uniquely identify a session"),
                })
    return arms


def user_message(question: str, context: list[str]) -> str:
    joined = "\n".join(f"- {text}" for text in context)
    return f"Memory context:\n{joined}\n\nQuestion: {question}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cap-usd", type=float, default=0.50)
    parser.add_argument("--salt", default="arena-mechanism-ablation-v1")
    parser.add_argument("--out", default=str(ARENA / "mechanism-ablation.json"))
    parser.add_argument("--raw-out", default=str(ARENA / "raw/mechanism-ablation"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    data = load_inputs()
    arms = build_arms(data)
    runnable = [a for a in arms if a.get("context")]
    blocked = [a for a in arms if not a.get("context")]

    prompts = [user_message(a["question"], a["context"]) for a in runnable]
    projected_prompt = sum(len(READER_PROMPT) + len(p) for p in prompts) // 4
    judge_calls = len(runnable) * 2
    projected = round(
        projected_prompt / 1e6 * PRICE_PER_MTOK["input"]
        + len(runnable) * READER_PARAMS["max_tokens"] / 1e6 * PRICE_PER_MTOK["output"]
        + judge_calls * 600 / 1e6 * PRICE_PER_MTOK["input"]
        + judge_calls * 10 / 1e6 * PRICE_PER_MTOK["output"], 6)

    by_arm: dict[str, int] = {}
    for arm in arms:
        by_arm[arm["arm"]] = by_arm.get(arm["arm"], 0) + (1 if arm.get("context") else 0)
    print(f"new reader arms: {len(runnable)}   unobservable: {len(blocked)}")
    for name, count in sorted(by_arm.items()):
        print(f"  {name:26s} {count:2d}")
    print(f"reused without payment: hindsight_full, mem0_compact, question_only")
    print(f"projected ${projected:.4f} (reader + judging) against ${args.cap_usd:.2f}")
    if projected > args.cap_usd:
        raise SystemExit(f"projection ${projected} exceeds the cap; stopping")

    # ---- the rules are frozen here, before any call ------------------------
    manifest = {
        "artifact": EXPERIMENT,
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": ("does Hindsight's advantage come from context VOLUME, or from "
                     "information Mem0's compaction discards"),
        "code_revision": git_revision(),
        "source_selection_sha256": data["selection"]["selection_sha256"],
        "source_context_artifacts": {
            system: sha256_file(ARENA / f"raw/arena-expansion-v1/{system}.json")
            for system in ("mem0", "hindsight")
        },
        "reader": {"model": args.model, "system_prompt_sha256": prompt_hash(),
                   "parameters": READER_PARAMS,
                   "identical_to": "arena-fixed-reader-v1"},
        "judge_protocol_sha256": sha256_file(ROOT / "scripts/arena/judge_pilot.py"),
        "token_unit": TOKENS,
        "transformation_rules": {
            "truncation": ("whole evidence items, original order, add while the next "
                           "fits the budget. No re-ranking, no summarising, and no "
                           "item chosen using the gold answer"),
            "budgets": BUDGETS,
            "mem0_provenance": ("the raw source session whose date matches Mem0's "
                                "TOP-1 retrieved memory, verbatim, appended after the "
                                "compact context. Chosen by rank, never by gold"),
            "provenance_mapping": ("session date only. A unit whose haystack repeats a "
                                   "date is UNOBSERVABLE rather than guessed"),
        },
        "failure_modes_kept_apart": {
            "GOLD_DROPPED_BY_BUDGET": "the budget cut the gold evidence out",
            "GOLD_PRESENT_BUT_CONTEXT_INSUFFICIENT":
                "it survived the budget and the answer still fell",
        },
        "reused_arms": {
            "hindsight_full": "arena-fixed-reader, identical reader config",
            "mem0_compact": "arena-fixed-reader, identical reader config",
            "question_only": "arena-fixed-reader baseline, 0/10",
        },
        "arms_planned": by_arm,
        "unobservable": blocked,
        "projected_usd": projected,
        "cap_usd": args.cap_usd,
    }
    Path(args.out).write_text(json.dumps(manifest, indent=2, default=str) + "\n",
                              encoding="utf-8")
    if args.project_only:
        return 0

    from openai import OpenAI

    from arena.run_pilot import load_key

    ledger = SpendLedger(total_cap_usd=args.cap_usd, run_id="ablation-reader",
                         cap_scope="ablation-")
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url=args.base_url),
                           fixed={"temperature": READER_PARAMS["temperature"]},
                           spend_cap_usd=args.cap_usd, shared_ledger=ledger)

    outputs: list[dict[str, Any]] = []
    stopped = None
    try:
        for arm, prompt in zip(runnable, prompts):
            response = client.chat.completions.create(
                model=args.model,
                messages=[{"role": "system", "content": READER_PROMPT},
                          {"role": "user", "content": prompt}],
                max_tokens=READER_PARAMS["max_tokens"])
            usage = getattr(response, "usage", None)
            outputs.append({
                **{k: v for k, v in arm.items() if k != "context"},
                "context_items": len(arm["context"]),
                "context_tokens": sum(len(t.split()) for t in arm["context"]),
                "answer": (response.choices[0].message.content or "").strip(),
                "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
                "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            })
    except SpendCapReached as stop:
        stopped = str(stop)

    out_dir = Path(args.raw_out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "outputs.json").write_text(
        json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name in sorted({o["arm"] for o in outputs}):
        rows = [{"question_id": o["question_id"], "question": o["question"],
                 "gold": o["gold"], "answer": o["answer"]}
                for o in outputs if o["arm"] == name]
        (out_dir / f"{name}.json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest |= {
        "generated": len(outputs),
        "stopped_by_cap": stopped,
        "reader_cost": {
            "calls": len(client.request_log),
            "prompt_tokens": sum(o["prompt_tokens"] for o in outputs),
            "completion_tokens": sum(o["completion_tokens"] for o in outputs),
            "usd": round(client.spent_usd, 6),
        },
    }
    Path(args.out).write_text(json.dumps(manifest, indent=2, default=str) + "\n",
                              encoding="utf-8")
    print(f"generated {len(outputs)} reader outputs, ${client.spent_usd:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
