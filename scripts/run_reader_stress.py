#!/usr/bin/env python3
"""Budgeted reader stress curve over stale count and validity-cue quality."""
from __future__ import annotations
import argparse, hashlib, json, math, sys, time, urllib.request
from pathlib import Path
from typing import Any
try:
    from scripts import screen_literature as shared
except ImportError:
    import screen_literature as shared

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"data"/"lab"/"reader-interference-stress-v5"
MODEL="deepseek-v4-flash"; API_URL="https://api.deepseek.com/chat/completions"
COUNTS=(1,4,16,64); CUES=("full","weak","absent","contradictory"); ORDERS=("gold-first","gold-last"); SIMILARITIES=("high","low"); INSTRUCTIONS=("explicit","minimal")
PROMPTS={
"explicit":"Use only supplied records. Full cues use valid_from/valid_to at query_time; weak cues use the highest version. List position is never evidence. If cues are absent or two records claim current, abstain. Return JSON only.",
"minimal":"Answer the current value using only supplied records. If evidence is insufficient, abstain. Return JSON only.",
}
SCHEMA='{"results":[{"case_id":"exact","answer":"value or empty","evidence_id":"ID or empty","abstain":true|false}]}'

def write_json(path:Path,value:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def value(index:int,similarity:str,salt:str)->str:
    digest=hashlib.sha256(f"value-{salt}-{index}".encode()).hexdigest()
    if similarity=="high": return "amber-"+digest[:6]
    return "token-"+digest[8:18]

def evidence_id(index:int,salt:str)->str:
    return "E-"+hashlib.sha256(f"evidence-{salt}-{index}".encode()).hexdigest()[:10]

def make_cases()->list[dict[str,Any]]:
    cases=[]
    for count in COUNTS:
      for cue in CUES:
       for order in ORDERS:
        for similarity in SIMILARITIES:
         for instruction in INSTRUCTIONS:
          salt=f"{count}-{cue}-{order}-{similarity}-{instruction}"
          stale=[]
          for version in range(1,count+1):
            row={"evidence_id":evidence_id(version,salt),"value":value(version,similarity,salt)}
            if cue=="full": row|={"valid_from":f"2026-01-{min(version,28):02d}","valid_to":"2026-02-01"}
            elif cue=="weak": row["version"]=version
            elif cue=="contradictory": row["status"]="stale"
            stale.append(row)
          gv=count+1; gold={"evidence_id":evidence_id(gv,salt),"value":value(gv,similarity,salt)}
          if cue=="full": gold|={"valid_from":"2026-02-01","valid_to":None}
          elif cue=="weak": gold["version"]=gv
          elif cue=="contradictory": gold["status"]="current"; stale[count//2]["status"]="current"
          records=[gold,*stale] if order=="gold-first" else [*stale,gold]
          answerable=cue in {"full","weak"}
          case_id="RS-"+hashlib.sha256(f"case-{salt}".encode()).hexdigest()[:12]
          cases.append({"case_id":case_id,"stale_count":count,"cue_quality":cue,"gold_order":order,"value_similarity":similarity,"instruction":instruction,"query_time":"2026-03-01","query":"What is the current access value?","records":records,"expected_answer":gold["value"] if answerable else "","expected_evidence_id":gold["evidence_id"] if answerable else "","expected_abstain":not answerable})
    return cases

def model_item(case:dict[str,Any])->dict[str,Any]:
    return {key:case[key] for key in ("case_id","query_time","query","records")}

def prepare()->dict[str,Any]:
    if OUT.exists() and any(OUT.iterdir()): raise ValueError(f"output directory is not empty: {OUT}")
    cases=make_cases(); shared.write_jsonl(OUT/"cases.jsonl",cases)
    manifest={"status":"frozen-input","model":MODEL,"thinking":"disabled","temperature":0,"cases":len(cases),"factors":{"stale_count":list(COUNTS),"cue_quality":list(CUES),"gold_order":list(ORDERS),"value_similarity":list(SIMILARITIES),"instruction":list(INSTRUCTIONS)},"cases_sha256":hashlib.sha256((OUT/"cases.jsonl").read_bytes()).hexdigest(),"data_class":"public deterministic synthetic records","authority":"single-model exploratory stress result","hard_cumulative_budget_usd":10}
    write_json(OUT/"manifest.json",manifest); return manifest

def validate(content:str,batch:list[dict[str,Any]])->list[dict[str,Any]]:
    rows=json.loads(content).get("results"); expected={x["case_id"] for x in batch}
    if not isinstance(rows,list) or {x.get("case_id") for x in rows}!=expected or len(rows)!=len(expected): raise ValueError("result IDs mismatch")
    if any(not isinstance(x.get("abstain"),bool) for x in rows): raise ValueError("invalid abstain")
    return rows

def run(env_file:Path,budget:float,max_tokens:int,timeout:float)->dict[str,Any]:
    if not 0<budget<=10: raise ValueError("budget must be >0 and <=10")
    key=shared.load_env_value(env_file,"DEEPSEEK_API_KEY")
    if not key: raise ValueError("DEEPSEEK_API_KEY missing")
    manifest=json.loads((OUT/"manifest.json").read_text(encoding="utf-8")); path=OUT/"cases.jsonl"
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest["cases_sha256"]: raise ValueError("cases hash mismatch")
    cases=shared.read_jsonl(path); outputs=[]
    for count in COUNTS:
      for instruction in INSTRUCTIONS:
        batch=[x for x in cases if x["stale_count"]==count and x["instruction"]==instruction]
        system=PROMPTS[instruction]+" Shape: "+SCHEMA
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps({"items":[model_item(case) for case in batch]},ensure_ascii=False)}]
        pre=shared.conservative_cost(math.ceil(sum(len(x["content"]) for x in messages)/2),max_tokens)
        if shared.ledger_total()+pre>budget: raise RuntimeError("hard cumulative budget exceeded")
        body=json.dumps({"model":MODEL,"messages":messages,"thinking":{"type":"disabled"},"temperature":0,"max_tokens":max_tokens,"response_format":{"type":"json_object"},"stream":False}).encode()
        request=urllib.request.Request(API_URL,data=body,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},method="POST"); started=time.perf_counter()
        with urllib.request.urlopen(request,timeout=timeout) as response: payload=json.load(response)
        usage=payload.get("usage") or {}; pt=int(usage.get("prompt_tokens") or 0); ct=int(usage.get("completion_tokens") or 0); cost=shared.conservative_cost(pt,ct)
        ledger={"at":shared.utc_now(),"run_id":"reader-interference-stress-v5","model":payload.get("model",MODEL),"response_id":payload.get("id",""),"prompt_tokens":pt,"completion_tokens":ct,"conservative_cost_usd":round(cost,8),"pricing_basis":"all input charged at configured peak cache-miss rate"}
        shared.append_jsonl(shared.BUDGET_LEDGER,ledger); shared.append_jsonl(OUT/"calls.jsonl",{**ledger,"stale_count":count,"instruction":instruction,"latency_ms":round((time.perf_counter()-started)*1000,2)})
        content=((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or ""; outputs.extend(validate(content,batch))
    gold={x["case_id"]:x for x in cases}; scored=[]
    for row in outputs:
        case=gold[row["case_id"]]; scored.append({**row,**{k:case[k] for k in ("stale_count","cue_quality","gold_order","value_similarity","instruction")},"answer_correct":row.get("answer","")==case["expected_answer"],"evidence_correct":row.get("evidence_id","")==case["expected_evidence_id"],"abstain_correct":row["abstain"]==case["expected_abstain"]})
    shared.write_jsonl(OUT/"results.jsonl",scored)
    def accuracy(rows,key): return sum(x[key] for x in rows)/len(rows)
    cells=[]
    for cue in CUES:
      for instruction in INSTRUCTIONS:
        rows=[x for x in scored if x["cue_quality"]==cue and x["instruction"]==instruction]
        cells.append({"cue_quality":cue,"instruction":instruction,"cases":len(rows),"answer_accuracy":accuracy(rows,"answer_correct"),"evidence_accuracy":accuracy(rows,"evidence_correct"),"abstain_accuracy":accuracy(rows,"abstain_correct")})
    curves=[]
    for cue in CUES:
      for count in COUNTS:
        rows=[x for x in scored if x["cue_quality"]==cue and x["stale_count"]==count]
        curves.append({"cue_quality":cue,"stale_count":count,"cases":len(rows),"decision_accuracy":sum(x["answer_correct"] and x["evidence_correct"] and x["abstain_correct"] for x in rows)/len(rows)})
    costs=shared.read_jsonl(OUT/"calls.jsonl"); summary={"status":"completed-exploratory-single-model","cases":len(scored),"cells":cells,"curves":curves,"run_cost_usd":round(sum(x["conservative_cost_usd"] for x in costs),8),"cumulative_cost_usd":shared.ledger_total(),"boundary":"One model; one case per full factorial cell; batched evaluation; explicit expected abstention for underdetermined cues."}
    write_json(OUT/"summary.json",summary); return summary

def main()->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True); sub.add_parser("prepare"); r=sub.add_parser("run"); r.add_argument("--env-file",type=Path,default=ROOT.parent/".env"); r.add_argument("--budget-usd",type=float,default=10); r.add_argument("--max-tokens",type=int,default=3000); r.add_argument("--timeout",type=float,default=120); a=p.parse_args()
    try: result=prepare() if a.command=="prepare" else run(a.env_file,a.budget_usd,a.max_tokens,a.timeout)
    except Exception as exc: print(f"error: {exc}",file=sys.stderr); return 2
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
