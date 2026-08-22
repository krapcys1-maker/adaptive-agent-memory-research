#!/usr/bin/env python3
"""Run deterministic PMLAB-MAP baselines on the frozen construction corpus."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


RUNNER_VERSION = "pmlab-map-construction-runner-v1"
CORPUS_FREEZE_COMMIT = "4b6c47e"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


def token_jaccard(left: str, right: str) -> float:
    a, b = set(normalize(left).split()), set(normalize(right).split())
    return len(a & b) / len(a | b) if a or b else 1.0


def role_for_text(text: str) -> str:
    q = normalize(text)
    if ("no current approval" in q or "nie ma aktualnego zatwierdzenia" in q) and ("alex" in q):
        return "approver-absence"
    if any(cue in q for cue in ("recur every", "every monday", "latest failures", "najnowsze awarie", "każdy poniedziałek")):
        return "backend-failure"
    ordered = [
        (("secret note", "tajna notatka"), "secret-note"),
        (("who manages", "przełożonym"), "manager"),
        (("who owns", "właścicielem"), "owner"),
        (("when", "kiedy", "approval date", "data zatwierdzenia"), "approval-date"),
        (("signed off", "podpisał zgodę", "who approved", "kto zatwierdził"), "approver"),
        (("recall@5", "recall 5", "czułość"), "recall"),
        (("cost", "koszt"), "cost"),
        (("planned", "zaplanowane"), "planned"),
        (("completed", "ukończone"), "completed"),
        (("explicitly", "jawnie"), "polarity"),
        (("reviewed", "zrecenzowane"), "reviewed"),
        (("current", "aktualne", "status"), "status"),
        (("findings", "ustalenia"), "finding"),
        (("decisions", "decyzje"), "decision"),
        (("failure", "failures", "failed", "awari", "niepowodzen"), "failure"),
        (("approved", "zatwierdzony", "zatwierdzenia"), "approval-status"),
    ]
    for cues, role in ordered:
        if any(normalize(cue) in q for cue in cues):
            return role
    return "unknown"


def role_for_obligation(operator: str, span: str, query: str) -> str:
    if operator in {"AGGREGATE", "GROUP", "SUPERLATIVE", "COMPARATIVE", "UNION", "INTERSECTION", "DIFFERENCE", "ARITHMETIC"}:
        return "derived"
    if operator == "FILTER":
        return "event-time"
    if operator == "SORT":
        return "failure-time"
    joined = f"{span} {query}"
    q, s = normalize(query), normalize(span)
    if ("who approved" in q or "kto zatwierdził" in q or "signed off" in q or "podpisał zgodę" in q) and not any(cue in s for cue in ("when", "kiedy", "status")):
        return "approver"
    if ("no current approval" in q or "nie ma aktualnego zatwierdzenia" in q) and "alex" in q:
        return "approver-absence"
    if operator == "BOOLEAN" and ("approved" in q or "zatwierdzony" in q):
        return "approval-status"
    if any(cue in q for cue in ("for each backend", "dla każdego backendu", "latest failures", "najnowsze awarie", "every monday", "każdy poniedziałek", "yesterday evening", "wczoraj wieczorem")) and any(cue in normalize(joined) for cue in ("failure", "awari", "niepowodzen", "monday", "poniedziałek", "yesterday", "wczoraj")):
        return "backend-failure"
    return role_for_text(span if role_for_text(span) != "unknown" else joined)


def spec(op: str, span: str, role: str, depends: list[str] | None = None) -> dict[str, Any]:
    return {"operator": op, "span_text": span.strip(" ,.?"), "role": role, "depends": depends or []}


def qdmr_specs(query: str) -> tuple[list[dict[str, Any]], str]:
    q = normalize(query)
    if any(cue in q for cue in ("would have happened", "co stałoby się", "if every future", "jeśli każdy przyszły")):
        return [], "unsupported_structure"
    if ("who owns" in q and "manages" in q) or ("właścicielem" in q and "przełożonym" in q):
        left, right = re.split(r"\b(?:and|i)\b", query, maxsplit=1, flags=re.IGNORECASE)
        return [spec("SELECT", left, "owner"), spec("PROJECT", right, "manager", ["O1"])], "resolved"
    if ("completed experiments" in q or "ukończone eksperymenty" in q) and ("after" in q or " po " in f" {q} "):
        marker = "after" if "after" in query.casefold() else "po"
        left, right = re.split(rf"\b{marker}\b", query, maxsplit=1, flags=re.IGNORECASE)
        return [spec("SELECT", left, "completed"), spec("FILTER", marker + " " + right, "event-time", ["O1"])], "resolved"
    if ("how many" in q or q.startswith("ile ")) and ("for each" in q or "dla każdego" in q):
        return [spec("SELECT", query, "failure"), spec("GROUP", query, "derived", ["O1"])], "resolved"
    if "how many" in q or q.startswith("ile "):
        return [spec("SELECT", query, "failure"), spec("AGGREGATE", query, "derived", ["O1"])], "resolved"
    if "highest" in q or "najwyższy" in q:
        return [spec("SELECT", query, "cost"), spec("SUPERLATIVE", query, "derived", ["O1"])], "resolved"
    if "higher than" in q or "wyższe niż" in q:
        return [spec("SELECT", "FTS5 Recall@5", "recall-fts5"), spec("SELECT", "rg Recall@5", "recall-rg"), spec("COMPARATIVE", query, "derived", ["O1", "O2"])], "resolved"
    if "difference between" in q or "różnica między" in q:
        return [spec("SELECT", "FTS5", "recall-fts5"), spec("SELECT", "rg", "recall-rg"), spec("ARITHMETIC", query, "derived", ["O1", "O2"])], "resolved"
    if ("findings or decisions" in q) or ("ustalenia lub decyzje" in q):
        return [spec("SELECT", "findings" if "findings" in q else "ustalenia", "finding"), spec("SELECT", "decisions" if "decisions" in q else "decyzje", "decision"), spec("UNION", query, "derived", ["O1", "O2"])], "resolved"
    if ("both reviewed and current" in q) or ("zrecenzowane i aktualne" in q):
        return [spec("SELECT", "reviewed" if "reviewed" in q else "zrecenzowane", "reviewed"), spec("SELECT", "current" if "current" in q else "aktualne", "current"), spec("INTERSECTION", query, "derived", ["O1", "O2"])], "resolved"
    if ("planned but not completed" in q) or ("zaplanowane ale nie zostały ukończone" in q):
        return [spec("SELECT", "planned" if "planned" in q else "zaplanowane", "planned"), spec("SELECT", "completed" if "completed" in q else "ukończone", "completed"), spec("DIFFERENCE", query, "derived", ["O1", "O2"])], "resolved"
    if ("latest failures" in q) or ("najnowsze awarie" in q):
        return [spec("SELECT", "failures" if "failures" in q else "awarie", "failure"), spec("SORT", query, "failure-time", ["O1"])], "resolved"
    if ("who approved umber" in q and "current status" in q and "when" in q) or ("kto zatwierdził umber" in q and "aktualny status" in q and "kiedy" in q):
        parts = re.split(r",|\b(?:and|i)\b", query, flags=re.IGNORECASE)
        parts = [part.strip() for part in parts if part.strip()]
        return [spec("SELECT", parts[0], "approver"), spec("SELECT", parts[1], "status"), spec("SELECT", parts[2], "approval-date", ["O2"])], "resolved"
    if ("who approved" in q or "kto zatwierdził" in q) and ("when" in q or "kiedy" in q):
        parts = re.split(r"\b(?:and|i)\b", query, maxsplit=1, flags=re.IGNORECASE)
        return [spec("SELECT", parts[0], "approver"), spec("SELECT", parts[1], "approval-date", ["O1"])], "resolved"
    if "since the scope audit" in q or "od audytu zakresu" in q:
        return [spec("SELECT", "decisions" if "decisions" in q else "decyzje", "decision")], "resolved"

    role = role_for_text(query)
    operator = "BOOLEAN" if q.startswith(("was ", "is ", "czy ")) else "SELECT"
    if "nebula" in q or ("mercury" in q and role == "owner") or "yesterday evening local time" in q or "wczoraj wieczorem czasu lokalnego" in q:
        status = "ambiguous"
    elif role == "secret-note":
        status = "unauthorized"
    else:
        status = "resolved"
    return [spec(operator, query, role)], status


def conjunction_specs(query: str) -> tuple[list[dict[str, Any]], str]:
    q = normalize(query)
    if any(cue in q for cue in ("would have happened", "co stałoby się", "if every future", "jeśli każdy przyszły")):
        return [], "unsupported_structure"
    parts = [part.strip() for part in re.split(r"\b(?:and|or|but|i|lub|ale)\b", query, flags=re.IGNORECASE) if part.strip()]
    result = []
    for part in parts:
        op = "BOOLEAN" if normalize(part).startswith(("was ", "is ", "czy ")) else "SELECT"
        result.append(spec(op, part, role_for_text(part)))
    _, status = qdmr_specs(query)
    return result, status


def entity_for_role(role: str, query: str, span: str) -> str:
    q, s = normalize(query), normalize(span)
    if "nebula" in q:
        return "nil:Nebula"
    if "mercury" in q and role == "owner":
        return "ambiguous:project:mercury,person:mercury"
    if role == "recall-fts5" or "fts5" in s:
        return "backend:fts5"
    if role == "recall-rg" or s == "rg":
        return "backend:rg"
    if role in {"recall", "failure"} and "fts5" in s:
        return "backend:fts5"
    if role in {"recall", "failure"} and re.search(r"\brg\b", s):
        return "backend:rg"
    if role == "secret-note":
        return "person:anna-kowalska|project:umber"
    if role == "approver-absence":
        return "project:umber|person:alex-lee"
    if role in {"approver", "approval-date", "approval-status", "status", "owner"} and "umber" in q:
        return "project:umber"
    if role == "manager":
        return "ref:O1"
    if role in {"completed", "planned"}:
        return "type:experiment"
    if role == "failure":
        return "type:experiment" if "experiment" in q or "eksperyment" in q else "type:failure"
    if role == "backend-failure":
        return "type:backend" if "each backend" in q or "każdego backendu" in q else "type:failure"
    if role in {"finding", "decision", "reviewed", "current"}:
        return {"finding": "experiment:closure-v1", "decision": "type:decision", "reviewed": "type:record", "current": "type:record"}[role]
    if role == "cost":
        return "type:run"
    if role == "polarity":
        return "type:claim"
    if role == "event-time":
        return "ref:O1"
    if role == "failure-time":
        return "ref:O1"
    if role == "derived":
        return "ref:derived"
    return "type:unknown"


ROLE_PREDICATE = {
    "approver": "approval.approver",
    "approver-absence": "approval.approver",
    "approval-date": "approval.date",
    "approval-status": "approval.status",
    "status": "approval.status",
    "owner": "project.owner",
    "manager": "person.manager",
    "completed": "experiment.status",
    "planned": "experiment.planned",
    "failure": "experiment.status",
    "backend-failure": "backend.failure_events",
    "cost": "run.cost_usd",
    "recall": "benchmark.recall_at_5",
    "recall-fts5": "benchmark.recall_at_5",
    "recall-rg": "benchmark.recall_at_5",
    "finding": "record.kind",
    "decision": "record.kind",
    "reviewed": "record.review_status",
    "current": "record.review_status",
    "polarity": "claim.polarity",
    "secret-note": "authorization.secret_note",
    "event-time": "temporal.event",
    "failure-time": "failure.occurred_at",
}


PREDICATE_NAMESPACE = {
    "approval.approver": ["approvals"],
    "approval.date": ["approvals"],
    "approval.status": ["approvals"],
    "project.owner": ["canonical-events"],
    "person.manager": ["canonical-events"],
    "experiment.status": ["experiments"],
    "experiment.planned": ["experiments"],
    "backend.failure_events": ["failures"],
    "run.cost_usd": ["experiments"],
    "benchmark.recall_at_5": ["benchmarks"],
    "record.kind": ["decisions"],
    "record.review_status": ["canonical-events"],
    "claim.polarity": ["findings"],
    "authorization.secret_note": ["private-notes"],
    "temporal.event": ["canonical-events"],
    "failure.occurred_at": ["failures"],
}


def predict_time(query: str, role: str, depends: list[str]) -> str:
    q = normalize(query)
    if "last month" in q or "zeszłym miesiącu" in q:
        return "relative:last-month"
    if "every monday" in q or "każdy poniedziałek" in q:
        return "recurrence:weekly-monday"
    if "since the scope audit" in q or "od audytu zakresu" in q:
        return "event-anchor:audit:scope"
    if "yesterday evening local time" in q or "wczoraj wieczorem czasu lokalnego" in q:
        return "ambiguous:local-timezone-and-evening-boundary"
    if "after august 1 2026" in q or "po 1 sierpnia 2026" in q:
        return "after:2026-08-01" if role == "event-time" else "all"
    if role in {"approval-date", "failure-time", "cost", "finding", "decision", "planned", "completed"}:
        return "all"
    if role == "derived":
        return "inherit:" + ",".join(depends)
    return "current"


def prediction_from_specs(query: str, specs: list[dict[str, Any]], status: str) -> dict[str, Any]:
    nodes = []
    for index, item in enumerate(specs, start=1):
        role = item["role"]
        predicate = ROLE_PREDICATE.get(role)
        entity = entity_for_role(role, query, item["span_text"])
        if role == "derived":
            entity = ("refs:" if len(item["depends"]) > 1 else "ref:") + ",".join(item["depends"])
        if role == "derived":
            predicate = None
        namespaces = PREDICATE_NAMESPACE.get(predicate, [])
        if role == "finding":
            namespaces = ["findings"]
        authorization = "denied" if role == "secret-note" else ("inherit:" + ",".join(item["depends"]) if role == "derived" else "allowed")
        if status == "ambiguous":
            certificate = "inapplicable" if entity.startswith("nil:") else "ambiguous"
        elif status in {"unauthorized", "unsupported_structure"}:
            certificate = "inapplicable"
        elif "no current approval" in normalize(query) or "nie ma aktualnego zatwierdzenia" in normalize(query):
            certificate = "requires-complete-scope"
        elif role == "polarity":
            certificate = "explicit-negative"
        elif role == "derived":
            certificate = "derived"
        else:
            certificate = "applicable"
        nodes.append(
            {
                "obligation_id": f"O{index}",
                "operator": item["operator"],
                "span_text": item["span_text"],
                "depends": item["depends"],
                "entity": entity,
                "predicate": predicate,
                "namespaces": namespaces,
                "time": predict_time(query, role, item["depends"]),
                "authorization": authorization,
                "certificate": certificate,
            }
        )
    return {"query_status": status, "nodes": nodes}


def flat_gold(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "query_status": case["query_status"],
        "nodes": [
            {
                "obligation_id": node["obligation_id"],
                "operator": node["operator"],
                "span_text": node["natural_spans"][0]["text"],
                "depends": node["arguments"],
                "entity": node["certificate_query"]["entity_basis"],
                "predicate": node["certificate_query"]["predicate"],
                "namespaces": node["certificate_query"]["namespaces"],
                "time": node["certificate_query"]["time_basis"],
                "authorization": node["scope"]["authorization"]["status"],
                "certificate": node["certificate_query"]["status"],
            }
            for node in case["graph"]["nodes"]
        ],
    }


def predict(case: dict[str, Any], arm: str) -> dict[str, Any]:
    query = case["raw_query"]
    if arm == "gold_oracle":
        return flat_gold(case)
    if arm == "gold_obligations_predicted_links":
        gold = flat_gold(case)
        specs = [spec(node["operator"], node["span_text"], role_for_obligation(node["operator"], node["span_text"], query), node["depends"]) for node in gold["nodes"]]
        return prediction_from_specs(query, specs, gold["query_status"])
    if arm == "whole_query_single_scope":
        _, status = qdmr_specs(query)
        op = "BOOLEAN" if normalize(query).startswith(("was ", "is ", "czy ")) else "SELECT"
        return prediction_from_specs(query, [spec(op, query, role_for_text(query))] if status != "unsupported_structure" else [], status)
    if arm == "conjunction_splitter":
        specs, status = conjunction_specs(query)
        return prediction_from_specs(query, specs, status)
    if arm == "qdmr_rules_pipeline":
        specs, status = qdmr_specs(query)
        return prediction_from_specs(query, specs, status)
    raise ValueError(f"unknown arm: {arm}")


def match_nodes(gold_nodes: list[dict[str, Any]], pred_nodes: list[dict[str, Any]]) -> list[tuple[int, int]]:
    candidates = []
    for gi, gold in enumerate(gold_nodes):
        for pi, pred in enumerate(pred_nodes):
            if gold["operator"] != pred["operator"]:
                continue
            overlap = token_jaccard(gold["span_text"], pred["span_text"])
            if overlap >= 0.15:
                candidates.append((overlap, gi, pi))
    candidates.sort(reverse=True)
    used_g, used_p, matches = set(), set(), []
    for _, gi, pi in candidates:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
            matches.append((gi, pi))
    return sorted(matches)


def score_case(case: dict[str, Any], arm: str, prediction: dict[str, Any]) -> dict[str, Any]:
    gold = flat_gold(case)
    matches = match_nodes(gold["nodes"], prediction["nodes"])
    matched = len(matches)
    precision = matched / len(prediction["nodes"]) if prediction["nodes"] else (1.0 if not gold["nodes"] else 0.0)
    recall = matched / len(gold["nodes"]) if gold["nodes"] else (1.0 if not prediction["nodes"] else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    link_fields = ["entity", "predicate", "namespaces", "time", "authorization", "certificate"]
    link_correct = Counter()
    for gi, pi in matches:
        for field in link_fields:
            link_correct[field] += gold["nodes"][gi][field] == prediction["nodes"][pi][field]
    structure_exact = (
        [node["operator"] for node in gold["nodes"]] == [node["operator"] for node in prediction["nodes"]]
        and [node["depends"] for node in gold["nodes"]] == [node["depends"] for node in prediction["nodes"]]
    )
    all_links_exact = matched == len(gold["nodes"]) == len(prediction["nodes"]) and all(
        gold["nodes"][gi][field] == prediction["nodes"][pi][field]
        for gi, pi in matches
        for field in link_fields
    )
    status_exact = gold["query_status"] == prediction["query_status"]
    unresolved_gold = gold["query_status"] != "resolved"
    unsafe_resolution = unresolved_gold and prediction["query_status"] == "resolved"
    false_closure = unsafe_resolution or any(
        gold["nodes"][gi]["certificate"] in {"ambiguous", "inapplicable"}
        and prediction["nodes"][pi]["certificate"] in {"applicable", "explicit-negative", "requires-complete-scope"}
        for gi, pi in matches
    )
    critical = case["evaluation_metadata"]["criticality"] == "critical"
    critical_omission = critical and recall < 1.0
    return {
        "query_id": case["query_id"],
        "arm": arm,
        "critical": critical,
        "gold_status": gold["query_status"],
        "gold_count": len(gold["nodes"]),
        "predicted_count": len(prediction["nodes"]),
        "matched_count": matched,
        "obligation_precision": precision,
        "obligation_recall": recall,
        "obligation_f1": f1,
        "critical_omission": critical_omission,
        "structure_exact": structure_exact,
        "status_exact": status_exact,
        "false_closure": false_closure,
        "safe_abstention": unresolved_gold and prediction["query_status"] != "resolved",
        "end_to_end_exact": structure_exact and all_links_exact and status_exact,
        "link_correct": dict(link_correct),
        "link_denominator": matched,
        "prediction": prediction,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_arm.setdefault(row["arm"], []).append(row)
    result = {}
    for arm, items in by_arm.items():
        obligations = sum(item["gold_count"] for item in items)
        matched = sum(item["matched_count"] for item in items)
        predicted = sum(item["predicted_count"] for item in items)
        critical_items = [item for item in items if item["critical"]]
        critical_unresolved = [item for item in items if item["critical"] and item["gold_status"] != "resolved"]
        link_denominator = sum(item["link_denominator"] for item in items)
        link_totals = Counter()
        for item in items:
            link_totals.update(item["link_correct"])
        precision = matched / predicted if predicted else (1.0 if obligations == 0 else 0.0)
        recall = matched / obligations if obligations else (1.0 if predicted == 0 else 0.0)
        result[arm] = {
            "case_count": len(items),
            "obligation_precision": precision,
            "obligation_recall": recall,
            "obligation_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
            "critical_full_recall": sum(not item["critical_omission"] for item in critical_items) / len(critical_items),
            "critical_omission_count": sum(item["critical_omission"] for item in items),
            "structure_exact_rate": sum(item["structure_exact"] for item in items) / len(items),
            "status_exact_rate": sum(item["status_exact"] for item in items) / len(items),
            "false_closure_count": sum(item["false_closure"] for item in items),
            "critical_unresolved_safe_rate": sum(item["safe_abstention"] for item in critical_unresolved) / len(critical_unresolved) if critical_unresolved else None,
            "end_to_end_exact_rate": sum(item["end_to_end_exact"] for item in items) / len(items),
            "link_accuracy": {field: link_totals[field] / link_denominator if link_denominator else None for field in ["entity", "predicate", "namespaces", "time", "authorization", "certificate"]},
        }
    return result


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# PMLAB-MAP construction baseline report",
        "",
        "Status: deterministic development result; corpus was inspectable and is not held out",
        "",
        f"Corpus freeze commit: `{CORPUS_FREEZE_COMMIT}`. Runner: `{RUNNER_VERSION}`.",
        "",
        "| Arm | Obligation F1 | Critical full recall | Structure exact | E2E exact | False closure |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for arm, metrics in summary.items():
        lines.append(
            f"| `{arm}` | {metrics['obligation_f1']:.3f} | {metrics['critical_full_recall']:.3f} | "
            f"{metrics['structure_exact_rate']:.3f} | {metrics['end_to_end_exact_rate']:.3f} | {metrics['false_closure_count']} |"
        )
    lines.extend(
        [
            "",
            "## Link-stage diagnostic",
            "",
            "| Arm | Entity | Predicate | Namespace | Time | Authorization | Certificate |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for arm in ("gold_obligations_predicted_links", "qdmr_rules_pipeline"):
        links = summary[arm]["link_accuracy"]
        lines.append(
            f"| `{arm}` | {links['entity']:.3f} | {links['predicate']:.3f} | {links['namespaces']:.3f} | "
            f"{links['time']:.3f} | {links['authorization']:.3f} | {links['certificate']:.3f} |"
        )
    qdmr = summary["qdmr_rules_pipeline"]
    links = qdmr["link_accuracy"]
    lines.extend(
        [
            "",
            "## Construction-gate disposition",
            "",
            f"- critical full recall: {qdmr['critical_full_recall']:.3f} — {'pass' if qdmr['critical_full_recall'] >= 0.95 else 'fail'};",
            f"- obligation F1: {qdmr['obligation_f1']:.3f} — {'pass' if qdmr['obligation_f1'] >= 0.90 else 'fail'};",
            f"- false closure: {qdmr['false_closure_count']} — {'pass' if qdmr['false_closure_count'] == 0 else 'fail'};",
            f"- entity top-1 proxy: {links['entity']:.3f} — {'pass' if links['entity'] >= 0.95 else 'fail'};",
            f"- predicate top-1 proxy: {links['predicate']:.3f} — {'pass' if links['predicate'] >= 0.95 else 'fail'};",
            f"- exact supported temporal mapping proxy: {links['time']:.3f} — {'pass' if links['time'] >= 0.90 else 'fail'};",
            f"- critical unresolved safe handling: {qdmr['critical_unresolved_safe_rate']:.3f} — {'pass' if qdmr['critical_unresolved_safe_rate'] == 1.0 else 'fail'}.",
            "",
            "The construction arm is rejected for promotion because entity and predicate linking miss the preregistered 0.95 thresholds. The apparent temporal pass is only a coarse exact-label proxy on authored cases, not the registered supported-expression interval metric.",
            "",
            "## Interpretation boundary",
            "",
            "The rules were written after the construction corpus was inspectable. Scores measure instrument behavior and expose stage failures; they are not estimates of generalization. No arm may be promoted until its implementation is frozen and evaluated on a new grouped challenge with unseen compound signatures and schemas.",
            "",
            "`gold_obligations_predicted_links` isolates the linker ceiling after perfect decomposition. `gold_oracle` is a scorer contract check. Any false closure or critical omission blocks promotion regardless of average F1.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data_dir = root / "data" / "lab" / "pmlab-obligation-mapping-dev-v0"
    artifacts_dir = data_dir / "artifacts"
    cases = read_jsonl(data_dir / "cases.jsonl")
    arms = ["whole_query_single_scope", "conjunction_splitter", "qdmr_rules_pipeline", "gold_obligations_predicted_links", "gold_oracle"]
    rows = [score_case(case, arm, predict(case, arm)) for case in cases for arm in arms]
    summary = summarize(rows)
    results_text = "".join(canonical_json(row) + "\n" for row in rows)
    summary_text = json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    report_text = render_report(summary)
    corpus_manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    run_manifest = {
        "experiment": "PMLAB-MAP-001-construction",
        "status": "completed-development-not-held-out",
        "runner_version": RUNNER_VERSION,
        "corpus_freeze_commit": CORPUS_FREEZE_COMMIT,
        "corpus_cases_sha256": corpus_manifest["hashes"]["cases.jsonl"],
        "case_count": len(cases),
        "arms": arms,
        "result_count": len(rows),
        "hashes": {
            "results.jsonl": hashlib.sha256(results_text.encode("utf-8")).hexdigest(),
            "summary.json": hashlib.sha256(summary_text.encode("utf-8")).hexdigest(),
            "report.md": hashlib.sha256(report_text.encode("utf-8")).hexdigest(),
        },
        "known_limitations": ["inspectable construction corpus", "tailored deterministic rules", "no independent labels", "no held-out challenge"],
    }
    expected = {
        artifacts_dir / "results.jsonl": results_text,
        artifacts_dir / "summary.json": summary_text,
        artifacts_dir / "report.md": report_text,
        artifacts_dir / "manifest.json": json.dumps(run_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }
    if args.check:
        stale = [str(path.relative_to(root)) for path, text in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise SystemExit("stale or missing artifacts: " + ", ".join(stale))
    else:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        for path, text in expected.items():
            path.write_text(text, encoding="utf-8", newline="\n")
    print(canonical_json(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
