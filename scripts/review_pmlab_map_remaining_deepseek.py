#!/usr/bin/env python3
"""Blind advisory review for PMLAB-MAP rows not covered by the first pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.error
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import screen_literature as shared  # noqa: E402
import review_pmlab_map_stage_deepseek as first  # noqa: E402


MODEL = "deepseek-v4-flash"
RUN_ID = "deepseek-v4-flash-map-stage-remaining-review-20260822"
PROMPT_VERSION = "pmlab-map-stage-remaining-blind-advisory-v1"
CORPUS_FREEZE_COMMIT = "fc9b212"
CORPUS_DIR = ROOT / "data" / "lab" / "pmlab-map-stage-dev-v1"
RUN_DIR = ROOT / "data" / "lab" / "api-screening" / RUN_ID
FIRST_RUN_DIR = ROOT / "data" / "lab" / "api-screening" / first.RUN_ID
GLOBAL_LEDGER = ROOT / "data" / "lab" / "api-screening" / "budget-ledger.jsonl"

SYSTEM_PROMPT = """You are a conservative blind annotation reviewer for a bilingual stage-isolated semantic-memory benchmark.
Return one JSON object and no prose. You do not know author labels, criticality, strata, scores, provenance, or candidate architecture. Label only the named stage using visible input and supplied catalogs. Each PL and EN row is independent.

Return exactly {"results":[{"case_id":"exact id","independent_label":{},"confidence":"high|medium|low","rationale":"brief visible evidence"}]}.

Stage output contracts:
- contract_span: {"decision":"accept|typed_reject","reject_reason":"none|invalid_serialization|missing_required_field|non_source_span|invalid_dependency|unknown_catalog_id|unsafe_unresolved_state"}. Ambiguous or unauthorized payloads may not carry conclusive applicable/negative certificates.
- entity_linking: {"action":"linked|ambiguous_in_catalog|missing_entity|non_entity_phrase|mention_not_detected","candidate_ids":[],"selected_id":"id or ref:O# or null","selected_ids":[]}. Null supplied mention means mention_not_detected. Do not invent IDs.
- obligation_graph: {"query_status":"resolved|ambiguous|unsupported_structure","nodes":[{"obligation_id":"O1","operator":"SELECT|FILTER|PROJECT|AGGREGATE|GROUP|SUPERLATIVE|COMPARATIVE|UNION|INTERSECTION|DIFFERENCE|SORT|BOOLEAN|ARITHMETIC","source_span":"exact substring","depends":[]}]}. Nodes are atomic, sequential, and backward-only. Do not infer authorization.
- predicate_linking: {"action":"linked|ambiguous_schema|unsupported_predicate","ranked_predicates":[],"selected_predicate":"id or null","selected_namespaces":[]}. Include every plausible visible schema candidate; do not select a near neighbor merely because it is topical.
- time_authorization: {"time_status":"resolved|ambiguous|unbounded|unsupported|inherited","authorization_status":"allowed|denied|partial|inherited","raw_span":"exact substring","normalized_time":"explicit normalized value","timezone":"value","reference_clock":"value","principal":"value","policy_basis":"explicit basis","authorized_namespaces":[],"denied_namespaces":[]}. Never turn vague or unscheduled future time into an exact interval, and never expose denied scope.
- certificate_routing: {"certificate_status":"applicable|derived|explicit_negative|requires_complete_scope|ambiguous|inapplicable","action":"answer|continue_search|clarify|partial_with_gap|abstain","basis":"explicit evidence or failure basis"}. No-hit is not falsity. Collection absence requires fresh, complete, exact scope. Matching post-certificate insertion invalidates absence. Denied scope requires abstention.

This is label review, not benchmark-case quality scoring. Deliberately malformed or unsafe inputs are valid negative fixtures and should receive their typed negative label."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def prepare() -> dict[str, Any]:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise ValueError(f"run directory is not empty: {RUN_DIR}")
    reviewed = {row["case_id"] for row in shared.read_jsonl(FIRST_RUN_DIR / "predictions.jsonl")}
    queue = shared.read_jsonl(CORPUS_DIR / "independent-review-queue.jsonl")
    remaining = [row for row in queue if row["case_id"] not in reviewed]
    jobs = first.build_jobs(remaining)
    if len(reviewed) != 44 or len(remaining) != 110 or len(jobs) != 55:
        raise ValueError(f"unexpected partition: reviewed={len(reviewed)} remaining={len(remaining)} jobs={len(jobs)}")
    shared.write_jsonl(RUN_DIR / "jobs.jsonl", jobs)
    (RUN_DIR / "prompt.txt").write_text(SYSTEM_PROMPT + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "run_id": RUN_ID,
        "status": "prepared-uncommitted-input",
        "created_at": first.utc_now(),
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "corpus_freeze_commit": CORPUS_FREEZE_COMMIT,
        "prompt_freeze_commit": None,
        "prior_reviewed_cases": len(reviewed),
        "semantic_groups": len(jobs),
        "cases": len(remaining),
        "temperature": 0,
        "thinking": "disabled",
        "hard_cumulative_budget_usd": 10.0,
        "hidden_from_worker": ["gold", "criticality", "stratum", "split", "provenance", "scores", "candidate implementation"],
        "authority": "advisory blind worker; not independent corpus review; cannot change gold",
        "hashes": {
            "jobs.jsonl": sha256(RUN_DIR / "jobs.jsonl"),
            "prompt.txt": sha256(RUN_DIR / "prompt.txt"),
            "independent-review-queue.jsonl": sha256(CORPUS_DIR / "independent-review-queue.jsonl"),
            "entity-catalog-v1.json": sha256(CORPUS_DIR / "entity-catalog-v1.json"),
            "predicate-catalog-v1.json": sha256(CORPUS_DIR / "predicate-catalog-v1.json"),
            "first-pass-predictions.jsonl": sha256(FIRST_RUN_DIR / "predictions.jsonl"),
        },
    }
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    return manifest


def freeze(commit: str) -> dict[str, Any]:
    path = RUN_DIR / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["status"] != "prepared-uncommitted-input":
        raise ValueError("manifest is not awaiting freeze")
    subprocess.check_call(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT)
    for name in ("jobs.jsonl", "prompt.txt"):
        content = subprocess.check_output(["git", "show", f"{commit}:data/lab/api-screening/{RUN_ID}/{name}"], cwd=ROOT)
        if hashlib.sha256(content).hexdigest() != manifest["hashes"][name]:
            raise ValueError(f"{name} differs from prompt freeze commit")
    manifest["prompt_freeze_commit"] = commit
    manifest["status"] = "frozen-input-awaiting-api"
    shared.write_json(path, manifest)
    return manifest


def verify() -> dict[str, Any]:
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] not in {"frozen-input-awaiting-api", "api-run-complete", "api-run-incomplete"}:
        raise ValueError("inputs are not frozen")
    paths = {
        "jobs.jsonl": RUN_DIR / "jobs.jsonl",
        "prompt.txt": RUN_DIR / "prompt.txt",
        "independent-review-queue.jsonl": CORPUS_DIR / "independent-review-queue.jsonl",
        "entity-catalog-v1.json": CORPUS_DIR / "entity-catalog-v1.json",
        "predicate-catalog-v1.json": CORPUS_DIR / "predicate-catalog-v1.json",
        "first-pass-predictions.jsonl": FIRST_RUN_DIR / "predictions.jsonl",
    }
    for name, path in paths.items():
        if sha256(path) != manifest["hashes"][name]:
            raise ValueError(f"frozen input mismatch: {name}")
    return manifest


def validate_label(result: dict[str, Any], case: dict[str, Any], entity_ids: set[str], predicate_ids: set[str], namespaces: set[str]) -> dict[str, Any]:
    if result.get("case_id") != case["case_id"] or result.get("confidence") not in {"high", "medium", "low"} or not str(result.get("rationale", "")).strip():
        raise ValueError("invalid review envelope")
    label = result.get("independent_label")
    if not isinstance(label, dict):
        raise ValueError("independent_label must be object")
    stage = case["stage"]
    if stage in {"contract_span", "entity_linking"}:
        enriched = {**result, "case_validity": "valid", "disputed_field": None}
        return {key: result[key] for key in result} if first.validate_label(enriched, case, entity_ids) else result
    if stage == "obligation_graph":
        if set(label) != {"query_status", "nodes"} or label["query_status"] not in {"resolved", "ambiguous", "unsupported_structure"} or not isinstance(label["nodes"], list):
            raise ValueError("invalid graph label")
        previous = []
        for index, node in enumerate(label["nodes"], start=1):
            if set(node) != {"obligation_id", "operator", "source_span", "depends"} or node["obligation_id"] != f"O{index}":
                raise ValueError("invalid graph node contract")
            if node["operator"] not in first.OPERATORS if hasattr(first, "OPERATORS") else node["operator"] not in {"SELECT","FILTER","PROJECT","AGGREGATE","GROUP","SUPERLATIVE","COMPARATIVE","UNION","INTERSECTION","DIFFERENCE","SORT","BOOLEAN","ARITHMETIC"}:
                raise ValueError("invalid graph operator")
            if not node["source_span"] or node["source_span"] not in case["input"]["raw_query"] or any(dep not in previous for dep in node["depends"]):
                raise ValueError("graph span or dependency invalid")
            previous.append(node["obligation_id"])
    elif stage == "predicate_linking":
        if set(label) != {"action", "ranked_predicates", "selected_predicate", "selected_namespaces"} or label["action"] not in {"linked", "ambiguous_schema", "unsupported_predicate"}:
            raise ValueError("invalid predicate label")
        if set(label["ranked_predicates"]) - predicate_ids or set(label["selected_namespaces"]) - namespaces:
            raise ValueError("unknown predicate or namespace")
        if label["selected_predicate"] is not None and label["selected_predicate"] not in predicate_ids:
            raise ValueError("unknown selected predicate")
    elif stage == "time_authorization":
        fields = {"time_status","authorization_status","raw_span","normalized_time","timezone","reference_clock","principal","policy_basis","authorized_namespaces","denied_namespaces"}
        if set(label) != fields or label["time_status"] not in {"resolved","ambiguous","unbounded","unsupported","inherited"} or label["authorization_status"] not in {"allowed","denied","partial","inherited"}:
            raise ValueError("invalid time/auth label")
        if not label["raw_span"] or label["raw_span"] not in case["input"]["raw_query"] or not label["normalized_time"]:
            raise ValueError("invalid temporal span or normalization")
    elif stage == "certificate_routing":
        if set(label) != {"certificate_status", "action", "basis"} or label["certificate_status"] not in {"applicable","derived","explicit_negative","requires_complete_scope","ambiguous","inapplicable"} or label["action"] not in {"answer","continue_search","clarify","partial_with_gap","abstain"} or not label["basis"]:
            raise ValueError("invalid certificate label")
    return result


def run(env_file: Path, budget_usd: float, batch_size: int, max_tokens: int, timeout: float) -> dict[str, Any]:
    manifest = verify()
    key = shared.load_env_value(env_file, "DEEPSEEK_API_KEY")
    if not key or not 0 < budget_usd <= 10:
        raise ValueError("missing key or invalid budget")
    jobs = shared.read_jsonl(RUN_DIR / "jobs.jsonl")
    entities = json.loads((CORPUS_DIR / "entity-catalog-v1.json").read_text(encoding="utf-8"))
    predicates = json.loads((CORPUS_DIR / "predicate-catalog-v1.json").read_text(encoding="utf-8"))
    entity_ids = {row["id"] for row in entities["entities"]}
    predicate_ids = {row["id"] for row in predicates["predicates"]}
    namespaces = set(predicates["namespaces"])
    done = {row["case_id"] for row in shared.read_jsonl(RUN_DIR / "predictions.jsonl")}
    pending = [job for job in jobs if any(case["case_id"] not in done for case in job["cases"])]
    calls = 0
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        cases = [case for job in batch for case in job["cases"] if case["case_id"] not in done]
        payload = {"instruction":"Return one label per exact case_id.","entity_catalog":entities,"predicate_catalog":predicates,"groups":[{"job_id":job["job_id"],"stage":job["stage"],"cases":[case for case in job["cases"] if case in cases]} for job in batch]}
        messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}]
        before = shared.ledger_total()
        preflight = shared.estimated_request_cost(messages, max_tokens)
        if before + preflight > budget_usd:
            raise RuntimeError("hard cumulative budget would be exceeded")
        started = time.perf_counter()
        try:
            response = first.request_payload(key, messages, timeout, max_tokens)
            usage = response.get("usage") or {}
            ledger = {"at":first.utc_now(),"run_id":RUN_ID,"model":response.get("model",MODEL),"response_id":response.get("id",""),"prompt_tokens":int(usage.get("prompt_tokens") or 0),"completion_tokens":int(usage.get("completion_tokens") or 0)}
            ledger["conservative_cost_usd"] = round(shared.conservative_cost(ledger["prompt_tokens"],ledger["completion_tokens"]),8)
            ledger["pricing_basis"] = "all input charged at configured peak cache-miss rate"
            shared.append_jsonl(GLOBAL_LEDGER, ledger)
            ids = [case["case_id"] for case in cases]
            shared.append_jsonl(RUN_DIR / "calls.jsonl", {**ledger,"latency_ms":round((time.perf_counter()-started)*1000,2),"case_ids":ids})
            content = ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            shared.append_jsonl(RUN_DIR / "raw-responses.jsonl", {"at":first.utc_now(),"response_id":response.get("id",""),"case_ids":ids,"content":content})
            results = json.loads(content).get("results")
            if not isinstance(results, list):
                raise ValueError("missing results")
            by_id = {row.get("case_id"):row for row in results if isinstance(row,dict)}
            for case in cases:
                try:
                    validated = validate_label(by_id[case["case_id"]], case, entity_ids, predicate_ids, namespaces)
                    shared.append_jsonl(RUN_DIR / "predictions.jsonl", {**validated,"model":response.get("model",MODEL),"prompt_version":PROMPT_VERSION,"reviewed_at":first.utc_now()})
                    done.add(case["case_id"])
                except (KeyError, ValueError, TypeError) as exc:
                    shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at":first.utc_now(),"case_id":case["case_id"],"error_type":"result-validation","error":str(exc),"raw_result":by_id.get(case["case_id"])})
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            shared.append_jsonl(RUN_DIR / "errors.jsonl", {"at":first.utc_now(),"case_ids":[case["case_id"] for case in cases],"error_type":type(exc).__name__,"error":str(exc)})
        calls += 1
    predictions = shared.read_jsonl(RUN_DIR / "predictions.jsonl")
    status = "api-run-complete" if len({row["case_id"] for row in predictions}) == manifest["cases"] else "api-run-incomplete"
    manifest["status"] = status
    shared.write_json(RUN_DIR / "manifest.json", manifest)
    summary = {"status":status,"cases":manifest["cases"],"valid_predictions":len(predictions),"errors_logged":len(shared.read_jsonl(RUN_DIR/"errors.jsonl")),"calls_this_invocation":calls,"run_conservative_cost_usd":round(sum(float(row["conservative_cost_usd"]) for row in shared.read_jsonl(GLOBAL_LEDGER) if row.get("run_id")==RUN_ID),8),"all_runs_conservative_cost_usd":shared.ledger_total(),"hard_cumulative_budget_usd":budget_usd,"authority":"advisory only"}
    shared.write_json(RUN_DIR / "api-summary.json", summary)
    return summary


def compare() -> dict[str, Any]:
    verify()
    cases = {row["case_id"]:row for row in shared.read_jsonl(CORPUS_DIR/"cases.jsonl")}
    predictions = {row["case_id"]:row for row in shared.read_jsonl(RUN_DIR/"predictions.jsonl")}
    expected_ids = {case["case_id"] for job in shared.read_jsonl(RUN_DIR/"jobs.jsonl") for case in job["cases"]}
    rows=[]
    for case_id in sorted(expected_ids):
        case=cases[case_id]; prediction=predictions.get(case_id); gold=case["gold"]
        if prediction is None:
            rows.append({"case_id":case_id,"semantic_group_id":case["semantic_group_id"],"stage":case["stage"],"language":case["language"],"criticality":case["criticality"],"gold":gold,"advisory_label":None,"prediction_status":"schema_invalid_after_retries","exact_agreement":False,"authority":"advisory-model-disagreement-only"})
            continue
        proposed=prediction["independent_label"]
        rows.append({"case_id":case_id,"semantic_group_id":case["semantic_group_id"],"stage":case["stage"],"language":case["language"],"criticality":case["criticality"],"gold":gold,"advisory_label":proposed,"prediction_status":"valid","exact_agreement":canonical(gold)==canonical(proposed),"confidence":prediction["confidence"],"rationale":prediction["rationale"],"authority":"advisory-model-disagreement-only"})
    shared.write_jsonl(RUN_DIR/"comparison.jsonl",rows)
    exact=sum(row["exact_agreement"] for row in rows); critical=[row for row in rows if row["criticality"]=="critical"]
    by_stage={stage:{"cases":len(items),"exact":sum(row["exact_agreement"] for row in items),"rate":sum(row["exact_agreement"] for row in items)/len(items)} for stage in sorted({row["stage"] for row in rows}) for items in [[row for row in rows if row["stage"]==stage]]}
    summary={"status":"advisory-comparison-incomplete" if len(predictions)<110 else "advisory-comparison-complete","cases":110,"valid_predictions":len(predictions),"schema_valid_rate":len(predictions)/110,"exact_agreement":exact,"exact_agreement_rate":exact/110,"critical_exact_agreement":sum(row["exact_agreement"] for row in critical),"critical_cases":len(critical),"by_stage":by_stage,"authority":"disagreement queue only; independent review required","gold_mutated":False}
    shared.write_json(RUN_DIR/"comparison-summary.json",summary)
    def field_checks(row: dict[str, Any]) -> dict[str, bool]:
        if row["prediction_status"] != "valid": return {}
        gold=row["gold"]; proposed=row["advisory_label"]; stage=row["stage"]
        if stage=="contract_span": return {field:gold.get(field)==proposed.get(field) for field in ("decision","reject_reason")}
        if stage=="entity_linking": return {"action":gold.get("action")==proposed.get("action"),"candidate_set":set(gold.get("candidate_ids",[]))==set(proposed.get("candidate_ids",[])),"selected_id":gold.get("selected_id")==proposed.get("selected_id"),"selected_ids":set(gold.get("selected_ids",[]))==set(proposed.get("selected_ids",[]))}
        if stage=="obligation_graph":
            gn=gold.get("nodes",[]); pn=proposed.get("nodes",[])
            return {"query_status":gold.get("query_status")==proposed.get("query_status"),"node_count":len(gn)==len(pn),"operator_sequence":[n.get("operator") for n in gn]==[n.get("operator") for n in pn],"dependency_structure":[n.get("depends") for n in gn]==[n.get("depends") for n in pn],"source_spans":[n.get("source_span") for n in gn]==[n.get("source_span") for n in pn]}
        if stage=="predicate_linking": return {"action":gold.get("action")==proposed.get("action"),"candidate_set":set(gold.get("ranked_predicates",[]))==set(proposed.get("ranked_predicates",[])),"selected_predicate":gold.get("selected_predicate")==proposed.get("selected_predicate"),"namespace_set":set(gold.get("selected_namespaces",[]))==set(proposed.get("selected_namespaces",[]))}
        if stage=="time_authorization": return {field:(set(gold.get(field,[]))==set(proposed.get(field,[])) if field in {"authorized_namespaces","denied_namespaces"} else gold.get(field)==proposed.get(field)) for field in ("time_status","authorization_status","raw_span","normalized_time","timezone","reference_clock","principal","policy_basis","authorized_namespaces","denied_namespaces")}
        return {field:gold.get(field)==proposed.get(field) for field in ("certificate_status","action","basis")}
    field_rows=[]
    for row in rows:
        for field,agree in field_checks(row).items(): field_rows.append({"stage":row["stage"],"field":field,"agree":agree})
    field_summary={}
    for stage in sorted({item["stage"] for item in field_rows}):
        field_summary[stage]={}
        for field in sorted({item["field"] for item in field_rows if item["stage"]==stage}):
            items=[item for item in field_rows if item["stage"]==stage and item["field"]==field]; agreed=sum(item["agree"] for item in items); field_summary[stage][field]={"agree":agreed,"valid_predictions":len(items),"rate":agreed/len(items)}
    shared.write_json(RUN_DIR/"field-agreement-summary.json",{"authority":"descriptive field-level comparison; not independent validation","schema_invalid_cases":110-len(predictions),"by_stage":field_summary})
    disagreements=[row for row in rows if not row["exact_agreement"]]
    report=["# Remaining PMLAB-MAP stage blind advisory review","","Status: advisory disagreement queue; not independent corpus review","",f"- schema-valid predictions: {len(predictions)}/110;",f"- exact object agreement: {exact}/110 ({exact/110:.3f});",f"- critical exact agreement: {summary['critical_exact_agreement']}/{len(critical)};",f"- disagreements or invalid predictions: {len(disagreements)}.","","Exact object agreement is intentionally strict and confounds semantic disagreement with canonical representation differences. Use `field-agreement-summary.json` to localize status, action, graph, span, time, and scope agreement. Gold was revealed only during this post-response comparison; no disagreement automatically changes it.","","## Disagreements",""]+[f"- `{row['case_id']}` ({row['stage']}, {row['criticality']}): {row.get('rationale','schema-invalid after two attempts')}" for row in disagreements]
    (RUN_DIR/"report.md").write_text("\n".join(report)+"\n",encoding="utf-8",newline="\n")
    artifacts=["api-summary.json","calls.jsonl","raw-responses.jsonl","predictions.jsonl","comparison.jsonl","comparison-summary.json","field-agreement-summary.json","report.md"]
    api=json.loads((RUN_DIR/"api-summary.json").read_text(encoding="utf-8")); manifest=verify()
    shared.write_json(RUN_DIR/"result-manifest.json",{"run_id":RUN_ID,"status":summary["status"],"corpus_freeze_commit":CORPUS_FREEZE_COMMIT,"prompt_freeze_commit":manifest["prompt_freeze_commit"],"cases":110,"valid_predictions":len(predictions),"run_conservative_cost_usd":api["run_conservative_cost_usd"],"all_runs_conservative_cost_usd_at_completion":api["all_runs_conservative_cost_usd"],"authority":"advisory only; independent review required","gold_mutated":False,"hashes":{name:sha256(RUN_DIR/name) for name in artifacts}})
    return summary


def main() -> int:
    parser=argparse.ArgumentParser(); commands=parser.add_subparsers(dest="command",required=True); commands.add_parser("prepare"); f=commands.add_parser("freeze"); f.add_argument("--prompt-freeze-commit",required=True); r=commands.add_parser("run"); r.add_argument("--env-file",type=Path,default=ROOT.parent/".env"); r.add_argument("--budget-usd",type=float,default=10.0); r.add_argument("--batch-size",type=int,default=3); r.add_argument("--max-tokens",type=int,default=6000); r.add_argument("--timeout",type=float,default=120.0); commands.add_parser("compare"); args=parser.parse_args()
    result=prepare() if args.command=="prepare" else freeze(args.prompt_freeze_commit) if args.command=="freeze" else run(args.env_file,args.budget_usd,args.batch_size,args.max_tokens,args.timeout) if args.command=="run" else compare(); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
