#!/usr/bin/env python3
"""Budgeted synthetic reader-level stale-value interference pilot."""

from __future__ import annotations

import argparse, hashlib, json, math, sys, time, urllib.request
from pathlib import Path
from typing import Any

try:
    from scripts import screen_literature as shared
    from scripts.run_forgetting_challenge import HISTORIES, make_f2_corpus
except ImportError:
    import screen_literature as shared
    from run_forgetting_challenge import HISTORIES, make_f2_corpus

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "data" / "lab" / "reader-interference-deepseek-v0"
MODEL = "deepseek-v4-flash"
API_URL = "https://api.deepseek.com/chat/completions"
CONDITIONS = ("gold-only", "gold-unrelated", "gold-first-stale", "gold-last-stale", "stale-only")
SYSTEM = """Use only the supplied synthetic memory records. A record is valid at query_time when valid_from <= query_time and valid_to is null or query_time < valid_to. Return one JSON object: {"results":[{"case_id":"exact","answer":"exact value or empty","evidence_id":"exact ID or empty","abstain":true|false}]}. Never infer a missing value."""


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_cases() -> list[dict[str, Any]]:
    corpus = make_f2_corpus()
    by_history: dict[str, list[dict[str, Any]]] = {}
    for row in corpus:
        by_history.setdefault(row["history_id"], []).append(row)
    cases=[]
    for history_id, entity, topic, _length, _prefix in HISTORIES:
        rows=sorted(by_history[history_id], key=lambda row: row["version"])
        gold=rows[-1]
        stale=[rows[i] for i in sorted({0, max(0,len(rows)//3), max(0,2*len(rows)//3), len(rows)-2})]
        unrelated=[]
        for other_id in by_history:
            if other_id != history_id:
                unrelated.append(sorted(by_history[other_id], key=lambda row: row["version"])[-1])
            if len(unrelated)==4: break
        for condition in CONDITIONS:
            if condition == "gold-only": context=[gold]
            elif condition == "gold-unrelated": context=[gold,*unrelated]
            elif condition == "gold-first-stale": context=[gold,*stale]
            elif condition == "gold-last-stale": context=[*stale,gold]
            else: context=stale
            cases.append({
                "case_id":f"READER-{history_id}-{condition}", "condition":condition,
                "query_time":"2026-03-01", "query":f"What is the current {topic} for {entity}?",
                "records":[{key:row[key] for key in ("evidence_id","value","valid_from","valid_to","title")} for row in context],
                "expected_answer":"" if condition=="stale-only" else gold["value"],
                "expected_evidence_id":"" if condition=="stale-only" else gold["evidence_id"],
                "expected_abstain":condition=="stale-only",
            })
    return cases


def prepare() -> dict[str, Any]:
    if OUTPUT_ROOT.exists() and any(OUTPUT_ROOT.iterdir()):
        raise ValueError(f"output directory is not empty: {OUTPUT_ROOT}")
    cases=make_cases()
    shared.write_jsonl(OUTPUT_ROOT / "cases.jsonl", cases)
    manifest={
        "status":"frozen-input", "model":MODEL, "thinking":"disabled", "temperature":0,
        "conditions":list(CONDITIONS), "cases":len(cases),
        "cases_sha256":hashlib.sha256((OUTPUT_ROOT/"cases.jsonl").read_bytes()).hexdigest(),
        "data_class":"public deterministic synthetic records", "authority":"single-model exploratory reader result only",
        "hard_cumulative_budget_usd":10,
    }
    write_json(OUTPUT_ROOT/"manifest.json",manifest)
    return manifest


def validate(content: str, expected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows=json.loads(content).get("results")
    if not isinstance(rows,list): raise ValueError("missing results array")
    ids={case["case_id"] for case in expected}
    if {row.get("case_id") for row in rows} != ids or len(rows)!=len(ids): raise ValueError("case IDs mismatch")
    if any(not isinstance(row.get("abstain"),bool) for row in rows): raise ValueError("invalid abstain")
    return rows


def run(env_file: Path, budget_usd: float, max_tokens: int, timeout: float) -> dict[str, Any]:
    if budget_usd <= 0 or budget_usd > 10: raise ValueError("budget must be >0 and <=10")
    key=shared.load_env_value(env_file,"DEEPSEEK_API_KEY")
    if not key: raise ValueError("DEEPSEEK_API_KEY is missing")
    manifest=json.loads((OUTPUT_ROOT/"manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256((OUTPUT_ROOT/"cases.jsonl").read_bytes()).hexdigest()!=manifest["cases_sha256"]: raise ValueError("cases hash mismatch")
    cases=shared.read_jsonl(OUTPUT_ROOT/"cases.jsonl")
    outputs=[]
    for condition in CONDITIONS:
        batch=[case for case in cases if case["condition"]==condition]
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps({"items":batch},ensure_ascii=False)}]
        preflight=shared.conservative_cost(math.ceil(sum(len(m["content"]) for m in messages)/2),max_tokens)
        if shared.ledger_total()+preflight>budget_usd: raise RuntimeError("hard cumulative budget would be exceeded")
        body=json.dumps({"model":MODEL,"messages":messages,"thinking":{"type":"disabled"},"temperature":0,"max_tokens":max_tokens,"response_format":{"type":"json_object"},"stream":False}).encode()
        request=urllib.request.Request(API_URL,data=body,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method="POST")
        started=time.perf_counter()
        with urllib.request.urlopen(request,timeout=timeout) as response: payload=json.load(response)
        usage=payload.get("usage") or {}; pt=int(usage.get("prompt_tokens") or 0); ct=int(usage.get("completion_tokens") or 0)
        cost=shared.conservative_cost(pt,ct)
        ledger={"at":shared.utc_now(),"run_id":"reader-interference-deepseek-v0","model":payload.get("model",MODEL),"response_id":payload.get("id",""),"prompt_tokens":pt,"completion_tokens":ct,"conservative_cost_usd":round(cost,8),"pricing_basis":"all input charged at configured peak cache-miss rate"}
        shared.append_jsonl(shared.BUDGET_LEDGER,ledger); shared.append_jsonl(OUTPUT_ROOT/"calls.jsonl",{**ledger,"condition":condition,"latency_ms":round((time.perf_counter()-started)*1000,2)})
        content=((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        outputs.extend(validate(content,batch))
    expected={case["case_id"]:case for case in cases}; scored=[]
    for row in outputs:
        gold=expected[row["case_id"]]
        scored.append({**row,"condition":gold["condition"],"answer_correct":row.get("answer","")==gold["expected_answer"],"evidence_correct":row.get("evidence_id","")==gold["expected_evidence_id"],"abstain_correct":row["abstain"]==gold["expected_abstain"]})
    shared.write_jsonl(OUTPUT_ROOT/"results.jsonl",scored)
    summary={"status":"completed-exploratory-single-model","cases":len(scored),"by_condition":{condition:{metric:sum(row[metric] for row in scored if row["condition"]==condition)/sum(row["condition"]==condition for row in scored) for metric in ("answer_correct","evidence_correct","abstain_correct")} for condition in CONDITIONS},"run_cost_usd":round(sum(row["conservative_cost_usd"] for row in shared.read_jsonl(OUTPUT_ROOT/"calls.jsonl")),8),"cumulative_cost_usd":shared.ledger_total(),"boundary":"One synthetic model snapshot; batched cases; no general reader claim."}
    write_json(OUTPUT_ROOT/"summary.json",summary); return summary


def main() -> int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True); sub.add_parser("prepare")
    runner=sub.add_parser("run"); runner.add_argument("--env-file",type=Path,default=ROOT.parent/".env"); runner.add_argument("--budget-usd",type=float,default=10); runner.add_argument("--max-tokens",type=int,default=2200); runner.add_argument("--timeout",type=float,default=120)
    args=parser.parse_args()
    try: result=prepare() if args.command=="prepare" else run(args.env_file,args.budget_usd,args.max_tokens,args.timeout)
    except Exception as exc: print(f"error: {exc}",file=sys.stderr); return 2
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
