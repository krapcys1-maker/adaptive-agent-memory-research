#!/usr/bin/env python3
"""MECHANISM_B_STATE_SUPERSESSION_V1 -- REPAIR + ONE RETEST.

Per data/lab/arena/mechanism-b-state-supersession-v1/stage1-archaeology.json:
V1's FAIL (net repairs = 0) was traced to a harness precondition, not a
mechanism flaw -- Mem0 1.0.6's own write-time ADD/UPDATE reconciliation fully
consolidated 8 of 9 R1/R2/R3 probes' sequential same-key statements into a
single surviving memory before CURRENT_STATE_OVER_HISTORY ever saw multiple
competing items. Diagnosed root cause: probe turns were packed in immediate
adjacency with nothing else in the store, unlike real multi-session
conversations where related statements sit far apart with many unrelated
turns between them.

The one, uniform, deterministic repair: insert exactly 2 unrelated filler
turns (from a fixed 10-sentence pool, verified to trigger none of the 9
state-key templates) between every pair of consecutive state-changing turns
in the 9 R1/R2/R3 probes. R4 controls are unchanged -- they were never part
of the diagnosed failure. This is a harness-precondition fix applied
identically to every affected probe by one rule, not per-probe wording
tuning, not gold-aware, not a host-specific exception.

One retest only. Repair budget: $0.30 (data/lab/arena/
mechanism-b-state-supersession-v1/stage1-archaeology.json repair_decision).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

PREREG = ROOT / "data/lab/arena/mechanism-b-state-supersession-v1/preregistration.json"

#: Verified at $0 (no template match) before use -- see the archaeology's
#: repair_spec.filler_pool note.
FILLER_POOL = [
    "I watched a great documentary about space last night.",
    "I tried a new pasta recipe for dinner.",
    "I went for a long walk in the park this morning.",
    "I finished reading an interesting novel.",
    "I organized my bookshelf over the weekend.",
    "I listened to a new podcast episode.",
    "I painted a small canvas for fun.",
    "I played chess with a friend.",
    "I baked chocolate chip cookies.",
    "I fixed a leaky faucet at home.",
]


def _parse(d: str) -> date:
    y, m, dd = (int(x) for x in d.split("-"))
    return date(y, m, dd)


def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def build_repaired_probes(probes: list[dict]) -> list[dict]:
    repaired = []
    filler_i = 0
    for probe in probes:
        p = copy.deepcopy(probe)
        if probe["regime"] == "R4_NO_UPDATE_CONTROL":
            repaired.append(p)
            continue
        new_turns = [p["turns"][0]]
        for i in range(1, len(p["turns"])):
            prev_date = _parse(p["turns"][i - 1]["date"])
            next_date = _parse(p["turns"][i]["date"])
            span = (next_date - prev_date).days
            offsets = (max(1, span // 3), max(2, 2 * span // 3))
            for off in offsets:
                filler_date = prev_date + timedelta(days=min(off, max(span - 1, 1)))
                new_turns.append({"date": _fmt(filler_date),
                                  "text": FILLER_POOL[filler_i % len(FILLER_POOL)],
                                  "filler": True})
                filler_i += 1
            new_turns.append(p["turns"][i])
        p["turns"] = new_turns
        p["repair_note"] = ("2 unrelated filler turns inserted per gap, per "
                            "stage1-archaeology.json's repair_spec")
        repaired.append(p)
    return repaired


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.30)
    parser.add_argument("--total-cap-usd", type=float, default=0.30)
    parser.add_argument("--cap-scope", default="mechb-v1-repair-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/mechanism-b-v1-repair-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/mechanism-b-state-supersession-v1/stage1-repair-raw.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    probes = build_repaired_probes(prereg["probe_plan"])
    assert len(probes) == 12

    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import build_mem0
    from arena.state_supersession import current_state_over_history
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    ingest_calls = sum(len(p["turns"]) for p in probes)
    reader_calls = len(probes) * 2
    judge_calls_min = len(probes) * 2 * 2
    print("=== COST GATE (repair + one retest) ===")
    print("RESEARCH_QUESTION: does the harness-precondition fix (filler-spaced turns) "
          "let >=2 items survive Mem0's write path, giving CURRENT_STATE_OVER_HISTORY "
          "material to actually act on, and does net repairs become measurable?")
    print("WHY_THIS_CALL_IS_NEEDED: stage1-archaeology.json diagnosed a single, "
          "deterministic harness flaw (not a mechanism flaw); this is the one "
          "permitted retest per the repair budget rule")
    print("EXPECTED_INFORMATION_GAIN: whether Mechanism B is EXPLORATORY_SUPPORTED "
          "or FAIL under conditions that actually exercise it")
    print("CHEAPEST_ALTERNATIVE: none -- already confirmed at $0 that the store "
          "genuinely holds only 1 item per probe pre-repair (memory.get_all() reads)")
    print(f"PROJECTED_CALLS: {ingest_calls} ingest + {reader_calls} reader + "
          f"~{judge_calls_min}-{judge_calls_min + 6} judge")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f} (repair budget, separate from Stage 1's "
          f"own $0.40 cap, already spent $0.022315 there)")
    if args.project_only:
        return 0

    run_id = f"{args.cap_scope}run"
    assert run_id.startswith(args.cap_scope)
    ledger = SpendLedger(total_cap_usd=args.total_cap_usd, run_id=run_id,
                         cap_scope=args.cap_scope)
    before_scope = ledger.scoped_usd()
    print(f"GLOBAL_SPEND_SO_FAR (this scope): ${before_scope:.6f}")
    print(f"GLOBAL_REMAINING (this scope cap): ${args.total_cap_usd - before_scope:.6f}")
    print("=== END COST GATE -- proceeding ===\n")

    built = build_mem0(args, ledger)
    adapter = built["adapter"]

    from openai import OpenAI
    from arena.decoding import FixedDecoding, SpendCapReached
    from arena.spend_ledger import TotalCapReached
    from arena.run_pilot import load_key
    from arena.judge_pilot import prompt_for, label_of, JUDGE_PARAMS

    client = FixedDecoding(OpenAI(api_key=load_key(), base_url="https://api.deepseek.com/v1"),
                           fixed={"temperature": 0}, spend_cap_usd=None, shared_ledger=ledger)

    def reader_call(question: str, context: list[str] | None) -> str:
        msg = user_message(question, context)
        resp = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "system", "content": READER_PROMPT},
                      {"role": "user", "content": msg}],
            max_tokens=READER_PARAMS["max_tokens"])
        return (resp.choices[0].message.content or "").strip()

    def judge_call(qtype: str, question: str, gold: str, response: str) -> dict:
        prompt = prompt_for(qtype, question, gold, response, abstention=False)

        def one_pass(name: str) -> dict:
            resp = client.chat.completions.create(
                model=args.model, messages=[{"role": "user", "content": prompt}],
                n=JUDGE_PARAMS["n"], max_tokens=JUDGE_PARAMS["max_tokens"])
            text = (resp.choices[0].message.content or "").strip()
            return {"pass": name, "raw": text, "label": label_of(text)}

        passes = [one_pass("A"), one_pass("B")]
        if passes[0]["label"] != passes[1]["label"]:
            passes.append(one_pass("C"))
        votes = [p["label"] for p in passes]
        final = sum(votes) > len(votes) / 2
        return {"passes": passes, "label": final,
               "stable": passes[0]["label"] == passes[1]["label"],
               "disputed": len(passes) == 3}

    results = []
    stopped = None
    try:
        for probe in probes:
            bank = f"mechb-repair-{probe['probe_id']}"
            adapter._bank = bank
            adapter.reset()
            assert adapter.stored_count() == 0

            for turn in probe["turns"]:
                adapter.ingest([{"text": turn["text"], "timestamp": turn["date"]}])

            retrieved = adapter.query(probe["question"])
            context_texts = list(retrieved.system_metadata["context_texts"])
            evidence_times = list(retrieved.system_metadata["evidence_times"])
            stored_after = adapter.stored_count()

            plus_b_context, trace = current_state_over_history(context_texts, evidence_times)

            base_answer = reader_call(probe["question"], context_texts)
            plus_b_answer = reader_call(probe["question"], plus_b_context)

            qtype = ("knowledge-update" if probe["regime"] != "R4_NO_UPDATE_CONTROL"
                     else "multi-session")
            gold = probe["expected_current"]
            base_judged = judge_call(qtype, probe["question"], gold, base_answer)
            plus_b_judged = judge_call(qtype, probe["question"], gold, plus_b_answer)

            results.append({
                "probe_id": probe["probe_id"], "regime": probe["regime"],
                "state_key": probe["state_key"], "question": probe["question"],
                "expected_current": gold, "question_type_used": qtype,
                "n_turns": len(probe["turns"]), "stored_after_ingest": stored_after,
                "context_texts": context_texts, "evidence_times": evidence_times,
                "plus_b_context": plus_b_context, "mechanism_trace": trace,
                "base_answer": base_answer, "plus_b_answer": plus_b_answer,
                "base_judged": base_judged, "plus_b_judged": plus_b_judged,
                "base_correct": base_judged["label"], "plus_b_correct": plus_b_judged["label"],
                "context_tokens_base": sum(len(t.split()) for t in context_texts),
                "context_tokens_plus_b": sum(len(t.split()) for t in plus_b_context),
            })
            print(f"{probe['probe_id']:24s} stored={stored_after}  "
                  f"BASE={'OK ' if base_judged['label'] else 'WRONG'}"
                  f"  +B={'OK ' if plus_b_judged['label'] else 'WRONG'}"
                  f"  cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    record = {
        "artifact": "arena-mechanism-b-state-supersession-v1-stage1-repair",
        "repair_of": "stage1-archaeology.json",
        "preregistration": str(PREREG.relative_to(ROOT)),
        "reader_prompt_sha256": prompt_hash(),
        "n_probes_run": len(results), "n_probes_expected": 12,
        "stopped_by_cap": stopped,
        "spend": {"total_usd": total_spend, "cap_usd": args.total_cap_usd,
                  "remaining_usd": round(args.total_cap_usd - total_spend, 6)},
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"\nran {len(results)}/12 probes, total spend ${total_spend:.6f} "
          f"against cap ${args.total_cap_usd:.2f}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
