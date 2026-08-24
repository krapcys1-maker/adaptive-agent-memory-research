#!/usr/bin/env python3
"""MECHANISM_B_STATE_SUPERSESSION_V1 -- the preregistered Stage 1 exploratory
test. Runs exactly the 12 probes frozen in data/lab/arena/
mechanism-b-state-supersession-v1/preregistration.json, no probe changes.

Per probe: reset an isolated Mem0 bank, ingest each turn as its own add()
call (so each fact gets its own turn's timestamp -- Mem0Adapter.ingest()
applies one metadata timestamp per call), retrieve once (shared by both
arms), then:

    BASE  = the raw retrieved context, unmodified (fixed_reader.py's own join)
    +B    = arena.state_supersession.current_state_over_history(...) applied
            to the same retrieved list

Reader: fixed_reader.py's own frozen READER_PROMPT/READER_PARAMS/
user_message(), called once per arm per probe (24 calls). Judge:
judge_pilot.py's own frozen per-question-type templates and 2-pass
(+3rd-on-disagreement) protocol -- 'knowledge-update' template for R1/R2/R3
probes (built for exactly this: "if the response contains some previous
information along with an updated answer... correct as long as the updated
answer is the required answer"), 'multi-session' (generic) template for R4
controls, matching LongMemEval's own category semantics. No new criterion
invented.

Hard cap enforced via SpendLedger(cap_scope="mechb-v1-", total_cap_usd=...)
plus the provider proxy's independent per-process cap, same mechanism used
throughout this arena.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

PREREG = ROOT / "data/lab/arena/mechanism-b-state-supersession-v1/preregistration.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--cap-usd", type=float, default=0.40)
    parser.add_argument("--total-cap-usd", type=float, default=0.40)
    parser.add_argument("--cap-scope", default="mechb-v1-")
    parser.add_argument("--embedding-model-path",
                        default=str(ROOT / "external/models/all-MiniLM-L6-v2"))
    parser.add_argument("--mem0-store",
                        default=str(ROOT / "data/lab/arena/raw/mechanism-b-v1-store"))
    parser.add_argument("--out", default=str(
        ROOT / "data/lab/arena/mechanism-b-state-supersession-v1/stage1-raw.json"))
    parser.add_argument("--project-only", action="store_true")
    args = parser.parse_args()

    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    probes = prereg["probe_plan"]
    assert len(probes) == 12, f"preregistration changed shape: {len(probes)} probes"

    from arena.decoding import PRICE_PER_MTOK
    from arena.spend_ledger import SpendLedger
    from arena.run_pilot import build_mem0
    from arena.state_supersession import current_state_over_history
    from arena.fixed_reader import READER_PROMPT, READER_PARAMS, user_message, prompt_hash

    sys.path.insert(0, str(ROOT / "external/venvs/mem0/Lib/site-packages"))

    # -- projection, before any call --------------------------------------
    n_probes = len(probes)
    ingest_calls = sum(len(p["turns"]) for p in probes)
    reader_calls = n_probes * 2
    judge_calls_min = n_probes * 2 * 2  # 2 arms x 2 passes minimum
    print("=== COST GATE (before first paid call) ===")
    print("RESEARCH_QUESTION: does CURRENT_STATE_OVER_HISTORY (+B) repair "
          "STALE_STATE_CONFUSION relative to BASE on the 12 preregistered probes?")
    print("WHY_THIS_CALL_IS_NEEDED: no deterministic or $0 analysis can measure "
          "reader behavior on real generated answers -- this is the exploratory "
          "test itself, per PM-20260824-7df2bf4e / preregistration.json")
    print("EXPECTED_INFORMATION_GAIN: GO/FAIL gate resolution for Mechanism B "
          "(MECHANISM_B_EXPLORATORY_SUPPORTED vs MECHANISM_B_FAIL)")
    print("CHEAPEST_ALTERNATIVE: none cheaper that answers the actual question -- "
          "the render transform itself was already verified at $0 (tests/"
          "test_state_supersession.py, 11/11 passing, no LLM)")
    print(f"PROJECTED_CALLS: {ingest_calls} ingest + {reader_calls} reader + "
          f"~{judge_calls_min}-{judge_calls_min + 6} judge = "
          f"~{ingest_calls + reader_calls + judge_calls_min}-"
          f"{ingest_calls + reader_calls + judge_calls_min + 6} total")
    print(f"STAGE_CAP: ${args.total_cap_usd:.2f} (preregistered recommended $0.30, "
          f"absolute Stage 1 cap $0.40)")
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
            bank = f"mechb-{probe['probe_id']}"
            adapter._bank = bank
            adapter.reset()
            assert adapter.stored_count() == 0, f"{bank}: scratch bank not empty"

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
                "stored_after_ingest": stored_after,
                "context_texts": context_texts, "evidence_times": evidence_times,
                "plus_b_context": plus_b_context, "mechanism_trace": trace,
                "base_answer": base_answer, "plus_b_answer": plus_b_answer,
                "base_judged": base_judged, "plus_b_judged": plus_b_judged,
                "base_correct": base_judged["label"], "plus_b_correct": plus_b_judged["label"],
                "context_tokens_base": sum(len(t.split()) for t in context_texts),
                "context_tokens_plus_b": sum(len(t.split()) for t in plus_b_context),
            })
            print(f"{probe['probe_id']:24s} BASE={'OK ' if base_judged['label'] else 'WRONG'}"
                  f"  +B={'OK ' if plus_b_judged['label'] else 'WRONG'}"
                  f"  cumulative ${ledger.scoped_usd():.6f}")
    except (SpendCapReached, TotalCapReached) as stop:
        stopped = str(stop)
        print(f"STOPPED BY CAP: {stopped}")

    after_scope = ledger.scoped_usd()
    total_spend = round(after_scope - before_scope, 6)

    record = {
        "artifact": "arena-mechanism-b-state-supersession-v1-stage1",
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
