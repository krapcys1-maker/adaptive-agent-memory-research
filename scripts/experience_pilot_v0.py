"""EXP-PILOT-0: does an agent's own experience memory help a local model on BFCL multi-turn base (Vehicle Control)?

Implements data/lab/experience-pilot-v0/PLAN.md (SPEC v1, approved 2026-11-12). Stages: e0, g1, g2, e1a, e1b, build, e2, e3, analyze.

Hard rules kept here: one local model (no paid API, no judge, no model calls to build memory); LocalReader from scripts/nie_reader_pilot.py
unchanged (no retry); BFCL environment and checker code used unchanged from a pinned checkout outside Git; every executor/checker call gets
its own model_name because BFCL keeps environment instances in module globals keyed by model_name and test_entry_id.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib
import importlib.util
import inspect
import json
import math
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/lab/experience-pilot-v0"
WORK = ROOT.parent / "experience-pilot-2026-11-12"          # outside Git: BFCL checkout and raw runs
SEED = 20261112

SYSTEM_TEMPLATE = (
    "You operate tools for a user. In each step return JSON {\"calls\":[...]} with the function calls to execute now.\n"
    "You may return several calls in one step; they run in order and you will see their results.\n"
    "If a result contains an error, correct the problem and continue.\n"
    "When the user's current request is completely done, return {\"calls\":[]}.\n"
    "Never ask the user a question. Use only the functions listed below.\n"
    "\n"
    "FUNCTIONS\n"
)
MEMORY_HEADER = "EXPERIENCE FROM EARLIER TASKS (it may or may not be relevant; use it only if it helps):"
FUNC_DOC_FILES = {"GorillaFileSystem": "gorilla_file_system.json", "MathAPI": "math_api.json", "MessageAPI": "message_api.json",
                  "TwitterAPI": "posting_api.json", "TicketAPI": "ticket_api.json", "VehicleControlAPI": "vehicle_control.json"}
VC_IDS = [f"multi_turn_base_{i}" for i in range(50, 100)]
GFS_IDS = [f"multi_turn_base_{i}" for i in range(0, 50)]
MAX_STEPS = 8
MAX_CALLS_PER_STEP = 6
RESULT_CHARS = 800
STEP_RESULT_CHARS = 160
ITEM_CHARS = 1400
CTX_MARGIN = 592
PRECONDITION_FUNCS = ("startEngine",)                         # confirmed in E0: the only VC method whose errors name hidden preconditions
E2_ARMS = ["N", "P", "R", "R+", "S"]
NPRIME_TASKS = 5


# ----------------------------------------------------------------------------- small helpers

def sha(value) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def append_jsonl(path: Path, row) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path):
    path = Path(path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(text: str, limit: int, marker: str = "...[truncated]") -> str:
    return text if len(text) <= limit else text[: max(0, limit - len(marker))] + marker


def is_error_result(result: str) -> bool:
    if result.startswith("Error during execution"):
        return True
    try:
        value = json.loads(result)
    except (ValueError, TypeError):
        return False
    return isinstance(value, dict) and "error" in value


# ----------------------------------------------------------------------------- BFCL access

class Bfcl:
    """Pinned BFCL checkout (unchanged code). Environments and checker are imported from it with only sys.path added."""

    def __init__(self, root: Path):
        self.root = Path(root)
        if str(self.root) not in sys.path:
            sys.path.insert(0, str(self.root))
        self.utils = importlib.import_module("bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils")
        self.checker = importlib.import_module("bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker")
        self.backend = importlib.import_module("bfcl_eval.constants.executable_backend_config")
        data = self.root / "bfcl_eval/data"
        self.tasks = {r["id"]: r for r in read_jsonl(data / "BFCL_v4_multi_turn_base.json")}
        self.gt = {r["id"]: r["ground_truth"] for r in read_jsonl(data / "possible_answer/BFCL_v4_multi_turn_base.json")}
        self.docs = {c: read_jsonl(data / "multi_turn_func_doc" / f) for c, f in FUNC_DOC_FILES.items()}
        self.signatures = {}
        for cls in FUNC_DOC_FILES:
            module = importlib.import_module(self.backend.CLASS_FILE_PATH_MAPPING[cls])
            klass = getattr(module, cls)
            for name, fn in inspect.getmembers(klass, predicate=inspect.isfunction):
                if not name.startswith("_"):
                    self.signatures[name] = [p for p in inspect.signature(fn).parameters if p != "self"]

    def functions(self, task) -> list:
        excluded = set(task.get("excluded_function") or [])
        return [d for cls in task["involved_classes"] for d in self.docs[cls] if d["name"] not in excluded]

    def execute(self, calls, task, model_name):
        return self.utils.execute_multi_turn_func_call(func_call_list=list(calls), initial_config=copy.deepcopy(task["initial_config"]),
                                                       involved_classes=task["involved_classes"], model_name=model_name, test_entry_id=task["id"])

    def check(self, model_turns, gt_turns, task, model_name):
        return self.checker.multi_turn_checker(model_turns, gt_turns, copy.deepcopy(task), "multi_turn_base", model_name)

    def state_ok(self, model_instances, gt_instances) -> bool:
        return bool(self.checker.state_checker(model_instances, gt_instances)["valid"])


class Names:
    """Unique BFCL model_name per executor/checker call (SPEC v1 8.1). Reuse inside one process is an error."""

    def __init__(self, prefix: str):
        self.prefix = re.sub(r"[^A-Za-z0-9_]", "_", prefix)
        self.used = set()
        self.counter = 0

    def new(self, *parts) -> str:
        self.counter += 1
        name = "xp0_" + "_".join([self.prefix] + [re.sub(r"[^A-Za-z0-9_]", "_", str(p)) for p in parts] + [str(self.counter)])
        if name in self.used:
            raise RuntimeError("BFCL model_name reused: " + name)
        self.used.add(name)
        return name


# ----------------------------------------------------------------------------- prompt, schema, validation

def doc_description(doc) -> str:
    text = doc["description"]
    marker = "Tool description: "
    return text.split(marker, 1)[1] if marker in text else text


def render_function(doc) -> str:
    props = doc["parameters"].get("properties", {})
    required = set(doc["parameters"].get("required", []))
    head = "%s(%s)" % (doc["name"], ", ".join(f"{p}: {s['type']}" for p, s in props.items()))
    lines = [head, doc_description(doc)]
    for p, s in props.items():
        extra = "" if p in required else " [optional]"
        lines.append(f"  {p}{extra}: {s.get('description', '').strip()}")
    return "\n".join(lines)


def system_prompt(bfcl: Bfcl, task) -> str:
    return SYSTEM_TEMPLATE + "\n\n".join(render_function(d) for d in bfcl.functions(task))


def output_schema(bfcl: Bfcl, task) -> dict:
    names = [d["name"] for d in bfcl.functions(task)]
    return {"type": "object", "additionalProperties": False, "required": ["calls"],
            "properties": {"calls": {"type": "array", "maxItems": MAX_CALLS_PER_STEP,
                                     "items": {"type": "object", "additionalProperties": False, "required": ["name", "arguments"],
                                               "properties": {"name": {"type": "string", "enum": names}, "arguments": {"type": "object"}}}}}}


def _type_ok(value, spec) -> bool:
    kind = spec.get("type")
    if kind == "string":
        return isinstance(value, str)
    if kind == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "array":
        if not isinstance(value, list):
            return False
        items = spec.get("items")
        return all(_type_ok(v, items) for v in value) if isinstance(items, dict) and items.get("type") else True
    if kind == "dict":
        return isinstance(value, dict)
    return True


def validate_call(call, docs_by_name):
    """(call_string or None, error or None). Builds name(k=repr(v), ...) in the order of the function description."""
    if not isinstance(call, dict) or set(call) != {"name", "arguments"}:
        return None, "invalid call: a call must have exactly the keys name and arguments"
    name, args = call["name"], call["arguments"]
    if name not in docs_by_name:
        return None, f"invalid call: unknown function {name!r}"
    if not isinstance(args, dict):
        return None, "invalid call: arguments must be an object"
    params = docs_by_name[name]["parameters"]
    props, required = params.get("properties", {}), params.get("required", [])
    unknown = [k for k in args if k not in props]
    if unknown:
        return None, f"invalid call: unknown argument(s) {unknown} for {name}"
    missing = [k for k in required if k not in args]
    if missing:
        return None, f"invalid call: missing required argument(s) {missing} for {name}"
    for k, v in args.items():
        if not _type_ok(v, props[k]):
            return None, f"invalid call: argument {k} of {name} must be of type {props[k].get('type')}"
    parts = [f"{k}={args[k]!r}" for k in props if k in args]
    return f"{name}({', '.join(parts)})", None


def parse_output(text: str, done_reason):
    """List of raw calls, or None when the step output as a whole is invalid (SPEC v1 4.3)."""
    if done_reason == "length":
        return None
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, dict) or set(value) != {"calls"} or not isinstance(value["calls"], list) or len(value["calls"]) > MAX_CALLS_PER_STEP:
        return None
    return value["calls"]


def chars_tokens(messages) -> float:
    return sum(len(m["content"]) for m in messages) / 3.0


# ----------------------------------------------------------------------------- call normalisation (strata, exposure)

def normalise_call(call: str, signatures) -> tuple:
    node = ast.parse(call, mode="eval").body
    name = node.func.id
    args = {}
    names = signatures.get(name, [])
    for i, a in enumerate(node.args):
        args[names[i] if i < len(names) else f"_{i}"] = ast.literal_eval(a)
    for k in node.keywords:
        args[k.arg] = ast.literal_eval(k.value)

    def canon(v):
        if isinstance(v, bool) or v is None or isinstance(v, str):
            return v
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, (list, tuple)):
            return [canon(x) for x in v]
        if isinstance(v, dict):
            return {k: canon(x) for k, x in sorted(v.items())}
        return repr(v)
    return name, json.dumps({k: canon(v) for k, v in sorted(args.items())}, sort_keys=True)


def skeleton(calls_norm) -> tuple:
    return tuple(c[0] for c in calls_norm)


# ----------------------------------------------------------------------------- memory

def load_kernel():
    path = ROOT / "scripts/wmb/kernel/memory_kernel.py"
    name = "xp0_memory_kernel_0_2_0"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    assert module.VERSION == "0.2.0", module.VERSION
    return module


def profile(lex_tau: float, min_evidence: float, name: str) -> dict:
    return {"name": name, "embed": "off", "names": False, "timeout_ms": float("inf"), "k": 2, "lex_tau": lex_tau, "min_evidence": min_evidence}


UNGATED = (1e-9, 0.0)
INDEX_NOW = "2027-01-01T00:00:00Z"


def build_index(mk, items):
    """items: pool rows with 'request', 'source_task', 'turn', 'order'. Returns (index, by_id)."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    kitems, by_id = [], {}
    for row in items:
        created = (base + timedelta(days=row["order"], minutes=row["turn"])).isoformat().replace("+00:00", "Z")
        ident = f"{row['source_task']}:t{row['turn']}"
        it = mk.Item(id=ident, kind="event", origin="account_history", text=row["request"], created_at=created)
        kitems.append(it)
        by_id[ident] = row
    if len(by_id) != len(items):
        raise ValueError("duplicate pool item ids")
    return mk.build_index(kitems, as_of=INDEX_NOW), by_id


def retrieve(mk, index, by_id, query: str, lex_tau: float, min_evidence: float):
    result = mk.retrieve(index, query, task_type="note", now=INDEX_NOW, profile=profile(lex_tau, min_evidence, "xp0"))
    if result.get("status") != "ok":
        raise RuntimeError("kernel retrieval not ok: %s %s" % (result.get("status"), result.get("error")))
    return [by_id[it.id] for it in result["items"]], list(result["scores"])


def render_item(i: int, row) -> str:
    lines = [f"[{i}] Request: {row['request']}", "    Steps:"]
    steps = row["steps"]
    if not steps:
        lines.append("      (none)")
    for s in steps[:8]:
        lines.append(f"      {s['call']} -> {truncate(s['result'], STEP_RESULT_CHARS)}")
    if len(steps) > 8:
        lines.append("      …")
    lines.append(f"    Outcome: {row['label']}")
    return truncate("\n".join(lines), ITEM_CHARS, "…")


def render_block(rows) -> str:
    if not rows:
        return ""
    return "\n".join([MEMORY_HEADER] + [render_item(i + 1, r) for i, r in enumerate(rows)])


def pool_row_id(row) -> str:
    return f"{row['source_task']}:t{row['turn']}"


# ----------------------------------------------------------------------------- the agent loop

def run_episode(bfcl: Bfcl, task, client, names: Names, *, stage: str, arm: str, key: str, ctx_limit: int, memory=None, seed: int = 7):
    """One episode. memory(task_id, turn_index, request) -> (rows, meta) or None. Returns the episode record (no checker yet)."""
    docs_by_name = {d["name"]: d for d in bfcl.functions(task)}
    schema = output_schema(bfcl, task)
    live = names.new(stage, arm, task["id"], "live")
    history = [{"role": "system", "content": system_prompt(bfcl, task)}]
    record = {"task": task["id"], "arm": arm, "stage": stage, "key": key, "live_name": live, "turns": [], "status": "completed",
              "system_sha256": sha(history[0]["content"]), "schema_sha256": sha(schema), "started_at": now_iso()}
    for ti, messages in enumerate(task["question"]):
        if len(messages) != 1 or messages[0]["role"] != "user":
            raise ValueError("unexpected turn shape")
        request = messages[0]["content"]
        rows, meta = memory(task["id"], ti, request) if memory else ([], None)
        block = render_block(rows)
        turn = {"index": ti, "request": request, "memory": {"items": [pool_row_id(r) for r in rows], "block_chars": len(block),
                                                            "block_sha256": sha(block) if block else None, "meta": meta}, "steps": []}
        record["turns"].append(turn)
        start = len(history)
        history.append({"role": "user", "content": (block + "\n\n" + request) if block else request})
        ended = False
        for si in range(MAX_STEPS):
            estimate = chars_tokens(history)
            if estimate >= ctx_limit:
                record["status"] = "context_overflow"
                turn["steps"].append({"overflow_estimate": estimate})
                break
            response = client.ask(f"{key}:t{ti}:s{si}", history, seed, output_schema=schema)
            usage = response.get("usage") or {}
            step = {"key": f"{key}:t{ti}:s{si}", "text": response["text"], "done_reason": response.get("done_reason"),
                    "estimate_tokens": estimate, "prompt_eval_count": usage.get("prompt_eval_count"), "eval_count": usage.get("eval_count"),
                    "wall_seconds": response.get("wall_seconds"), "calls": []}
            turn["steps"].append(step)
            history.append({"role": "assistant", "content": response["text"]})
            raw = parse_output(response["text"], response.get("done_reason"))
            if raw is None:
                step["invalid_output"] = True
                results = [{"error": "invalid output: response is not valid JSON for the required schema"}]
            elif not raw:
                ended = True
            else:
                results = []
                for call in raw:
                    call_str, error = validate_call(call, docs_by_name)
                    entry = {"raw": call, "call": call_str, "valid": call_str is not None}
                    if call_str is None:
                        entry["result"] = json.dumps({"error": error})
                    else:
                        out, _ = bfcl.execute([call_str], task, live)
                        entry["result"] = out[0]
                        entry["error"] = is_error_result(out[0])
                    step["calls"].append(entry)
                    results.append({"call": call_str or (call.get("name") if isinstance(call, dict) else None),
                                    "result": truncate(entry["result"], RESULT_CHARS)})
            pec = usage.get("prompt_eval_count")
            if pec is not None and pec >= ctx_limit:
                record["status"] = "context_overflow"
                break
            if ended:
                break
            history.append({"role": "user", "content": "RESULTS: " + json.dumps(results, ensure_ascii=False)})
        else:
            record["status"] = "forced_termination"
        history[start] = {"role": "user", "content": request}             # the memory block of a finished turn leaves the history
        if record["status"] != "completed":
            break
        if not ended:
            record["status"] = "forced_termination"
            break
    record["finished_at"] = now_iso()
    return record


def executed_turns(record):
    """[[ [call strings of one step], ... ] per turn] with only executed calls (SPEC v1 8.1)."""
    out = []
    for turn in record["turns"]:
        steps = [[c["call"] for c in s.get("calls", []) if c["valid"]] for s in turn["steps"]]
        out.append([s for s in steps if s])
    return out


def evaluate_episode(bfcl: Bfcl, record, names: Names):
    task = bfcl.tasks[record["task"]]
    gt = bfcl.gt[record["task"]]
    n = len(gt)
    model = executed_turns(record)
    padded = model + [[] for _ in range(n - len(model))]
    tag = (record["stage"], record["arm"], record["task"])
    main = bfcl.check(padded, gt, task, names.new(*tag, "eval"))
    solved = bool(main["valid"]) and record["status"] == "completed"
    # prefix labels
    first_fail = None
    for k in range(1, len(model) + 1):
        r = bfcl.check(padded[:k], gt[:k], task, names.new(*tag, f"label{k}"))
        if not r["valid"]:
            first_fail = k - 1
            break
    if first_fail is None and record["status"] != "completed":
        first_fail = len(model) - 1                                     # the terminated turn
    labels = []
    for i in range(len(model)):
        if first_fail is None or i < first_fail:
            labels.append("PASSED")
        elif i == first_fail:
            labels.append("FAILED")
        else:
            labels.append("UNVERIFIED")
    progress = (n if solved else (first_fail if first_fail is not None else len(model))) / n
    # state only, every turn, official state_checker
    mname, gname = names.new(*tag, "state_model"), names.new(*tag, "state_gt")
    state_turns = []
    for i in range(n):
        calls = [c for step in padded[i] for c in step]
        _, mi = bfcl.execute(calls, task, mname)
        _, gi = bfcl.execute(gt[i], task, gname)
        state_turns.append(bfcl.state_ok(mi, gi))
    state_all = all(state_turns) and record["status"] == "completed"
    # replay against live results
    rname = names.new(*tag, "replay")
    live = [c["result"] for t in record["turns"] for s in t["steps"] for c in s.get("calls", []) if c["valid"]]
    replay = []
    for t in model:
        for step in t:
            out, _ = bfcl.execute(step, task, rname)
            replay.extend(out)
    errors = sum(1 for t in record["turns"] for s in t["steps"] for c in s.get("calls", []) if c["valid"] and c.get("error"))
    invalid_calls = sum(1 for t in record["turns"] for s in t["steps"] for c in s.get("calls", []) if not c["valid"])
    invalid_outputs = sum(1 for t in record["turns"] for s in t["steps"] if s.get("invalid_output"))
    proposed = sum(len(s.get("calls", [])) for t in record["turns"] for s in t["steps"])
    model_calls = sum(1 for t in record["turns"] for s in t["steps"] if "key" in s)
    return {"task": record["task"], "arm": record["arm"], "stage": record["stage"], "status": record["status"], "solved": solved,
            "checker_valid": bool(main["valid"]), "checker_error_type": main.get("error_type"), "labels": labels, "first_fail": first_fail,
            "progress": progress, "state_turns": state_turns, "state_all": state_all, "replay_mismatch": live != replay,
            "n_turns": n, "turns_started": len(model), "error_results": errors, "invalid_calls": invalid_calls,
            "invalid_outputs": invalid_outputs, "proposed_calls": proposed, "model_calls": model_calls,
            "steps": sum(len(t["steps"]) for t in record["turns"])}


# ----------------------------------------------------------------------------- pools

def pool_rows_from_episode(record, evaluation, order: int):
    rows = []
    for turn, label in zip(record["turns"], evaluation["labels"]):
        steps = [{"call": c["call"], "result": c["result"], "error": bool(c.get("error"))}
                 for s in turn["steps"] for c in s.get("calls", []) if c["valid"]]
        rows.append({"source_task": record["task"], "turn": turn["index"], "order": order, "request": turn["request"], "steps": steps,
                     "label": label, "origin": "A"})
    return rows


def gold_rows(bfcl: Bfcl, task_id: str, order: int, names: Names, origin: str):
    task = bfcl.tasks[task_id]
    name = names.new("gold", origin, task_id)
    rows = []
    for ti, calls in enumerate(bfcl.gt[task_id]):
        out, _ = bfcl.execute(calls, task, name)
        rows.append({"source_task": task_id, "turn": ti, "order": order, "request": task["question"][ti][0]["content"],
                     "steps": [{"call": c, "result": r, "error": is_error_result(r)} for c, r in zip(calls, out)], "label": "PASSED",
                     "origin": origin})
    return rows


def row_calls_norm(row, signatures, drop_errors=True):
    return [normalise_call(s["call"], signatures) for s in row["steps"] if not (drop_errors and s["error"])]


# ----------------------------------------------------------------------------- statistics

def binom_tail_ge(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(k, n + 1)) / (2 ** n) if n else 1.0


def mcnemar(x_solved, y_solved):
    """x vs y on the same tasks: b = x only, c = y only; one-sided p for x > y and two-sided p."""
    b = sum(1 for a, c in zip(x_solved, y_solved) if a and not c)
    c = sum(1 for a, cc in zip(x_solved, y_solved) if cc and not a)
    n = b + c
    one = binom_tail_ge(b, n)
    two = min(1.0, 2 * min(binom_tail_ge(b, n), binom_tail_ge(c, n))) if n else 1.0
    return {"x_only": b, "y_only": c, "p_one_sided_x_gt_y": one, "p_two_sided": two}


# ----------------------------------------------------------------------------- configuration and ledger

def load_config():
    return read_json(DATA / "config.json")


def bfcl_from_config(cfg):
    return Bfcl((ROOT / cfg["bfcl_root"]).resolve())


def raw_dir(stage: str, run_id: str) -> Path:
    return WORK / "raw" / stage / run_id


def ledger():
    """Calls (attempts) and seconds over all raw runs. The only source of truth for the 2 000-call/time cap."""
    calls, seconds, runs = 0, 0.0, []
    base = WORK / "raw"
    if base.exists():
        for manifest in sorted(base.glob("*/*/manifest.json")):
            m = read_json(manifest)
            n = len(read_jsonl(manifest.parent / "attempts.jsonl"))
            calls += n
            seconds += m.get("elapsed_seconds") or 0.0
            runs.append({"stage": m["stage"], "run_id": m["run_id"], "calls": n, "elapsed_seconds": m.get("elapsed_seconds"),
                         "status": m.get("status")})
    return {"calls": calls, "seconds": seconds, "runs": runs}


def make_client(cfg, out: Path, max_calls: int):
    sys.path.insert(0, str(ROOT / "scripts"))
    from nie_reader_pilot import LocalReader
    led = ledger()
    remaining_calls = cfg["limits"]["max_calls_total"] - led["calls"]
    remaining_seconds = cfg["limits"]["max_seconds_total"] - led["seconds"]
    if remaining_calls <= 0 or remaining_seconds <= 0:
        raise RuntimeError("Hard cap exhausted.")
    rc = {"base_url": cfg["base_url"], "http_timeout_seconds": cfg["http_timeout_seconds"], "model": cfg["model"],
          "model_digest": cfg["model_digest"], "options": cfg["options"], "max_calls": min(max_calls, remaining_calls),
          "max_seconds": remaining_seconds}
    return LocalReader(rc, out)


class Stage:
    """Raw run folder with a manifest; never reused (no resume, no retry)."""

    def __init__(self, stage: str, cfg, max_calls: int, client_factory=None):
        self.stage, self.cfg = stage, cfg
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.out = raw_dir(stage, self.run_id)
        if self.out.exists():
            raise RuntimeError("run folder exists")
        self.out.mkdir(parents=True)
        self.client = (client_factory or make_client)(cfg, self.out, max_calls)
        self.started = time.monotonic()
        self.manifest = {"stage": stage, "run_id": self.run_id, "started_at": now_iso(), "status": "running",
                         "config_sha256": file_sha(DATA / "config.json") if (DATA / "config.json").exists() else None}
        write_json(self.out / "manifest.json", self.manifest)

    def preflight(self):
        if hasattr(self.client, "preflight"):
            self.manifest["preflight"] = self.client.preflight()
            write_json(self.out / "manifest.json", self.manifest)

    def close(self, status: str, extra=None):
        self.manifest.update({"status": status, "finished_at": now_iso(), "elapsed_seconds": time.monotonic() - self.started})
        if extra:
            self.manifest.update(extra)
        try:
            if status == "completed" and hasattr(self.client, "finish"):
                self.manifest["finish"] = self.client.finish()
        finally:
            if hasattr(self.client, "release"):
                try:
                    self.client.release()
                except Exception as exc:                                 # release must not hide the stage result
                    self.manifest["release_error"] = repr(exc)
            write_json(self.out / "manifest.json", self.manifest)


# ----------------------------------------------------------------------------- stages without a model

def stage_e0(cfg):
    bfcl = bfcl_from_config(cfg)
    vc = [bfcl.tasks[i] for i in VC_IDS]
    lengths = {t["id"]: len(system_prompt(bfcl, t)) for t in vc}
    longest = max(lengths.values())
    num_ctx = 8192 if longest / 3 + 3000 <= 7600 else 12288
    src = bfcl.root / "bfcl_eval/eval_checker/multi_turn_eval/func_source_code"
    vc_src = (src / "vehicle_control.py").read_text(encoding="utf-8")
    m = re.search(r"def startEngine.*?(?=\n    def )", vc_src, re.S)
    start_errors = re.findall(r'"error": "([^"]+)', m.group(0))
    random_methods = {}
    for cls, fname in (("VehicleControlAPI", "vehicle_control.py"), ("MessageAPI", "message_api.py"), ("TwitterAPI", "posting_api.py"),
                       ("TicketAPI", "ticket_api.py"), ("MathAPI", "math_api.py")):
        text = (src / fname).read_text(encoding="utf-8")
        bodies = {fm.group(1): fm.group(0) for fm in re.finditer(r"\n    def (\w+)\(.*?(?=\n    def |\Z)", text, re.S)}
        helpers = [n for n, b in bodies.items() if n.startswith("_") and n != "_load_scenario" and "self._random" in b]
        for n, b in bodies.items():
            if not n.startswith("_") and ("self._random" in b or any(f"self.{h}(" in b for h in helpers)):
                random_methods.setdefault(cls, []).append(n)
    random_names = sorted(n for v in random_methods.values() for n in v)
    checker_src = (bfcl.root / "bfcl_eval/eval_checker/multi_turn_eval/multi_turn_checker.py").read_text(encoding="utf-8")
    utils_src = (bfcl.root / "bfcl_eval/eval_checker/multi_turn_eval/multi_turn_utils.py").read_text(encoding="utf-8")
    error_types = sorted(set(re.findall(r'"error_type": "([^"]+)"', checker_src)))
    empty_gt = sum(1 for i in VC_IDS for t in bfcl.gt[i] if not t)
    configs = {i: sha(bfcl.tasks[i]["initial_config"]) for i in VC_IDS}
    shared = {i: sorted(j for j in VC_IDS if j != i and configs[j] == configs[i]) for i in VC_IDS}
    vc_names = {d["name"] for t in vc for d in bfcl.functions(t)}
    gfs_names = {d["name"] for d in bfcl.docs["GorillaFileSystem"]}
    f_turns = 0
    for i in GFS_IDS:
        for t in bfcl.gt[i]:
            fn = [ast.parse(c, mode="eval").body.func.id for c in t]
            f_turns += bool(fn) and all(f in gfs_names for f in fn) and not (set(fn) & vc_names)
    turns = [(i, ti, [normalise_call(c, bfcl.signatures) for c in t]) for i in VC_IDS for ti, t in enumerate(bfcl.gt[i])]
    exact = sum(1 for i, ti, c in turns if any(j != i and c2 == c for j, _, c2 in turns))
    skel = sum(1 for i, ti, c in turns if any(j != i and skeleton(c2) == skeleton(c) for j, _, c2 in turns))
    engine = sum(1 for i in VC_IDS if any("startEngine(" in c for t in bfcl.gt[i] for c in t))
    out = {
        "bfcl_commit": cfg["bfcl_commit"],
        "system_prompt_chars": {"max": longest, "min": min(lengths.values()), "by_task": lengths},
        "num_ctx_rule": {"L": longest, "L_div_3_plus_3000": longest / 3 + 3000, "num_ctx": num_ctx},
        "start_engine_error_messages": start_errors,
        "start_engine_rule_discoverable_from_error": any("doors must be locked" in e for e in start_errors) and any("brake" in e.lower() for e in start_errors),
        "executor_instance_key": "globals()[f'{model_name}_{test_entry_id}_{class_name}_instance'] (checker adds _eval and _ground_truth)"
                                 if "globals()" in utils_src and "{model_name}_{test_entry_id}_{class_name}_instance" in utils_src else "CHANGED",
        "checker_error_types": error_types,
        "empty_ground_truth_turns_50_99": empty_gt,
        "random_methods": random_methods,
        "random_dependent_turns": sum(1 for i in VC_IDS for t in bfcl.gt[i] if any(c.split("(")[0] in random_names for c in t)),
        "tasks_with_shared_initial_config": {i: v for i, v in shared.items() if v},
        "placebo_pool_turns": f_turns,
        "turns_50_99": len(turns), "exact_duplicate_turns": exact, "skeleton_duplicate_turns": skel, "tasks_with_startEngine": engine,
        "known_risk_recorded_before_e1a": "startEngine errors name the missing precondition, so the rule is discoverable inside an episode; "
                                          "memory may mostly save errors and steps rather than flip task success (power risk, thresholds unchanged).",
    }
    write_json(DATA / "e0-static.json", out)
    if f_turns < 40:
        raise SystemExit("STOP: placebo pool below 40 turns")
    return out


def stage_g1(cfg):
    bfcl = bfcl_from_config(cfg)
    names = Names("g1")
    report, excluded = {}, []
    for i in VC_IDS:
        task, gt = bfcl.tasks[i], bfcl.gt[i]
        model = [[t] for t in gt]
        check = bfcl.check(model, gt, task, names.new("g1", i, "check"))
        runs = []
        for rep in ("a", "b"):
            name = names.new("g1", i, rep)
            results, states = [], []
            for t in gt:
                out, inst = bfcl.execute(t, task, name)
                results.append(out)
                states.append({c: {k: v for k, v in vars(o).items() if not k.startswith("_")} for c, o in inst.items()})
            runs.append((results, json.dumps(states, sort_keys=True, default=repr)))
        errors = [c for t, res in zip(gt, runs[0][0]) for c, r in zip(t, res) if is_error_result(r)]
        same = runs[0][0] == runs[1][0] and runs[0][1] == runs[1][1]
        ok = bool(check["valid"]) and not errors and same
        report[i] = {"checker_valid": bool(check["valid"]), "error_calls": errors, "replays_identical": same, "ok": ok}
        if not ok:
            excluded.append(i)
    valid = sorted((i for i in VC_IDS if i not in excluded), key=lambda s: int(s.rsplit("_", 1)[1]))
    out = {"excluded": excluded, "n_valid": len(valid), "valid": valid, "per_task": report}
    write_json(DATA / "g1.json", out)
    if len(excluded) > 5:
        raise SystemExit(f"STOP: G1 excluded {len(excluded)} > 5 tasks")
    # split (SPEC 7)
    order = list(valid)
    random.Random(SEED).shuffle(order)
    if len(order) < 44:
        raise SystemExit("STOP: |V| < 44")
    split = {"seed": SEED, "train": order[:20], "test": order[20:50], "excluded": excluded,
             "method": "V sorted ascending by numeric id, random.Random(20261112).shuffle, first 20 train, next 30 test"}
    write_json(DATA / "split.json", split)
    return out


# ----------------------------------------------------------------------------- G2: transport and GPU fit

def stage_g2(cfg, client_factory=None):
    bfcl = bfcl_from_config(cfg)
    e0 = read_json(DATA / "e0-static.json")
    longest_id = max(e0["system_prompt_chars"]["by_task"], key=lambda k: e0["system_prompt_chars"]["by_task"][k])
    task = bfcl.tasks[longest_id]
    schema = output_schema(bfcl, task)
    long_system = system_prompt(bfcl, task)
    st = Stage("g2", cfg, 4, client_factory)
    checks = []
    try:
        st.preflight()
        probes = [
            ("short-1", [{"role": "system", "content": "Return JSON that matches the schema."},
                         {"role": "user", "content": "Return exactly one call: setHeadlights with argument mode equal to \"on\"."}],
             [{"name": "setHeadlights", "arguments": {"mode": "on"}}]),
            ("long-1", [{"role": "system", "content": long_system},
                        {"role": "user", "content": "Return exactly one call: setHeadlights with argument mode equal to \"off\". Do nothing else."}],
             [{"name": "setHeadlights", "arguments": {"mode": "off"}}]),
            ("long-2", None, None),                                      # the identical request again: prompt cache check
            ("short-2", [{"role": "system", "content": "Return JSON that matches the schema."},
                         {"role": "user", "content": "Return an empty list of calls."}], []),
        ]
        probes[2] = ("long-2", probes[1][1], probes[1][2])
        for key, messages, expected in probes:
            r = st.client.ask("g2:" + key, messages, 7, output_schema=schema)
            calls = parse_output(r["text"], r.get("done_reason"))
            row = {"key": key, "text": r["text"], "expected": expected, "ok": calls == expected, "usage": r.get("usage"),
                   "wall_seconds": r.get("wall_seconds"), "chars_tokens_estimate": chars_tokens(messages)}
            if key == "long-1" and hasattr(st.client, "request"):
                row["api_ps"] = st.client.request("/api/ps")
            checks.append(row)
        ps = next((c.get("api_ps") for c in checks if c.get("api_ps")), None)
        model_ps = (ps or {}).get("models", [{}])[0] if ps else {}
        gpu_full = bool(model_ps) and model_ps.get("size_vram") == model_ps.get("size")
        pe1 = checks[1]["usage"].get("prompt_eval_count")
        pe2 = checks[2]["usage"].get("prompt_eval_count")
        out = {"checks": checks, "all_ok": all(c["ok"] for c in checks), "gpu_full": gpu_full, "api_ps_model": model_ps,
               "prompt_eval_count_repeat": [pe1, pe2], "prompt_cache_lowers_count": pe1 != pe2,
               "use_chars_estimate_only": pe1 != pe2, "chars_per_token_long": (len(long_system) + 100) / pe1 if pe1 else None,
               "num_ctx": cfg["options"]["num_ctx"]}
        write_json(DATA / "g2.json", out)
        st.close("completed", {"gate_all_ok": out["all_ok"], "gate_gpu_full": gpu_full})
    except BaseException as exc:
        st.close("aborted", {"error": repr(exc)})
        raise
    if not out["all_ok"]:
        raise SystemExit("STOP: G2 transport check failed")
    if not gpu_full:
        raise SystemExit("STOP: model not fully on GPU at the chosen num_ctx")
    return out


# ----------------------------------------------------------------------------- training (E1a, E1b)

def ctx_limit(cfg) -> int:
    return cfg["options"]["num_ctx"] - CTX_MARGIN


def run_episodes(cfg, stage: str, plan, memory_for_arm, max_calls: int, client_factory=None, bfcl=None):
    """plan: list of (task_id, arm). Episodes are written as they finish. Returns (records, evaluations, stage)."""
    bfcl = bfcl or bfcl_from_config(cfg)
    st = Stage(stage, cfg, max_calls, client_factory)
    names = Names(stage + "_" + st.run_id)
    records, evals = [], []
    try:
        st.preflight()
        for n, (task_id, arm) in enumerate(plan):
            key = f"{stage}:{arm}:{task_id}"
            rec = run_episode(bfcl, bfcl.tasks[task_id], st.client, names, stage=stage, arm=arm, key=key, ctx_limit=ctx_limit(cfg),
                              memory=memory_for_arm(arm) if memory_for_arm else None)
            ev = evaluate_episode(bfcl, rec, names)
            append_jsonl(st.out / "episodes.jsonl", rec)
            append_jsonl(st.out / "evaluations.jsonl", ev)
            records.append(rec)
            evals.append(ev)
            print(f"[{stage}] {n + 1}/{len(plan)} {task_id} {arm} solved={ev['solved']} status={ev['status']} calls={ev['model_calls']}", flush=True)
        st.close("completed", {"episodes": len(records)})
    except BaseException as exc:
        st.close("aborted", {"error": repr(exc), "episodes": len(records)})
        raise
    return records, evals, st


def invalid_rate(evals) -> float:
    bad = sum(e["invalid_outputs"] + e["invalid_calls"] for e in evals)
    total = sum(e["invalid_outputs"] + e["proposed_calls"] for e in evals)
    return bad / total if total else 0.0


def stage_e1a(cfg, client_factory=None):
    split = read_json(DATA / "split.json")
    plan = [(t, "N") for t in split["train"][:10]]
    _, evals, st = run_episodes(cfg, "e1a", plan, None, 400, client_factory)
    rate = invalid_rate(evals)
    overflow = sum(e["status"] == "context_overflow" for e in evals)
    out = {"run_id": st.run_id, "episodes": len(evals), "solved": sum(e["solved"] for e in evals), "invalid_rate": rate,
           "context_overflow": overflow, "gate_ok": rate <= 0.10 and overflow == 0,
           "calls": sum(e["model_calls"] for e in evals)}
    write_json(DATA / "e1a.json", out)
    if not out["gate_ok"]:
        raise SystemExit(f"STOP: E1a gate failed: invalid_rate={rate:.3f} overflow={overflow}")
    return out


def stage_e1b(cfg, client_factory=None):
    split = read_json(DATA / "split.json")
    plan = [(t, "N") for t in split["train"][10:20]]
    _, evals, st = run_episodes(cfg, "e1b", plan, None, 400, client_factory)
    out = {"run_id": st.run_id, "episodes": len(evals), "solved": sum(e["solved"] for e in evals), "calls": sum(e["model_calls"] for e in evals)}
    write_json(DATA / "e1b.json", out)
    return out


def latest_completed(stage: str) -> Path:
    runs = sorted(p.parent for p in (WORK / "raw" / stage).glob("*/manifest.json") if read_json(p)["status"] == "completed")
    if not runs:
        raise RuntimeError("no completed run for " + stage)
    return runs[-1]


# ----------------------------------------------------------------------------- build: pools, calibration, strata, exposure, placebo, projection

def stage_build(cfg):
    bfcl = bfcl_from_config(cfg)
    mk = load_kernel()
    split = read_json(DATA / "split.json")
    train, test = split["train"], split["test"]
    order = {t: i for i, t in enumerate(train)}
    names = Names("build")
    records, evals = {}, {}
    for stage in ("e1a", "e1b"):
        run = latest_completed(stage)
        for r in read_jsonl(run / "episodes.jsonl"):
            records[r["task"]] = r
        for e in read_jsonl(run / "evaluations.jsonl"):
            evals[e["task"]] = e
    if sorted(records) != sorted(train):
        raise RuntimeError("training episodes do not cover the training split")
    train_solved = sum(evals[t]["solved"] for t in train)
    mean_progress = sum(evals[t]["progress"] for t in train) / len(train)
    A = [row for t in train for row in pool_rows_from_episode(records[t], evals[t], order[t])]
    A_plus = [r for r in A if r["label"] == "PASSED"]
    G = [row for t in train for row in gold_rows(bfcl, t, order[t], names, "G")]
    vc_names = {d["name"] for t in VC_IDS for d in bfcl.functions(bfcl.tasks[t])}
    gfs_names = {d["name"] for d in bfcl.docs["GorillaFileSystem"]}
    F = []
    for k, t in enumerate(GFS_IDS):
        for row in gold_rows(bfcl, t, k, names, "F"):
            fn = [s["call"].split("(")[0] for s in row["steps"]]
            if fn and all(f in gfs_names for f in fn) and not (set(fn) & vc_names):
                F.append(row)
    pools_dir = DATA / "pools"
    pools = {}
    for name, rows in (("A", A), ("A_plus", A_plus), ("G", G), ("F", F)):
        path = pools_dir / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
        pools[name] = {"rows": len(rows), "sha256": file_sha(path), "chars": sum(len(render_item(1, r)) for r in rows)}
    # context check after E1b (SPEC 4): largest prompt + 1000 tokens reaches the limit
    g2 = read_json(DATA / "g2.json")
    limit = ctx_limit(cfg)
    near = 0
    for t in train:
        sizes = []
        for turn in records[t]["turns"]:
            for s in turn["steps"]:
                if "key" in s:
                    sizes.append(s["estimate_tokens"] if g2["use_chars_estimate_only"] else max(s["estimate_tokens"], s["prompt_eval_count"] or 0))
        near += bool(sizes) and max(sizes) + 1000 >= limit
    context_share = near / len(train)
    # gate calibration (SPEC 5.3)
    sig = bfcl.signatures
    gt_skel = {(t, ti): skeleton([normalise_call(c, sig) for c in turn]) for t in train + test for ti, turn in enumerate(bfcl.gt[t])}
    grid = []
    queries = [(t, ti, bfcl.tasks[t]["question"][ti][0]["content"]) for t in train for ti in range(len(bfcl.gt[t]))]
    loo = {}
    for t in train:
        rows = [r for r in A_plus if r["source_task"] != t]
        loo[t] = build_index(mk, rows) if rows else None
    taus = [round(0.10 + 0.05 * i, 2) for i in range(9)]
    for tau in taus:
        for me in (0.8, 1.4):
            tp = fp = fn = 0
            for t, ti, q in queries:
                if loo[t] is None:
                    y = pred = False
                else:
                    idx, by_id = loo[t]
                    top, _ = retrieve(mk, idx, by_id, q, *UNGATED)
                    y = any(gt_skel[(r["source_task"], r["turn"])] == gt_skel[(t, ti)] for r in top)
                    gated, _ = retrieve(mk, idx, by_id, q, tau, me)
                    pred = bool(gated)
                tp += y and pred
                fp += pred and not y
                fn += y and not pred
            f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0
            grid.append({"lex_tau": tau, "min_evidence": me, "tp": tp, "fp": fp, "fn": fn, "f1": f1})
    best = max(grid, key=lambda g: (g["f1"], g["lex_tau"], g["min_evidence"]))
    calibration = {"grid": grid, "chosen": {"lex_tau": best["lex_tau"], "min_evidence": best["min_evidence"], "f1": best["f1"]},
                   "n_queries": len(queries), "positives": sum(1 for _ in queries) and None}
    write_json(DATA / "gate-calibration.json", calibration)
    gate = (best["lex_tau"], best["min_evidence"])
    # deterministic retrieval for every test turn and arm
    idx_A, idx_Ap, idx_G = build_index(mk, A), build_index(mk, A_plus), build_index(mk, G)
    plan_mem = {}
    for t in test:
        for ti, msg in enumerate(bfcl.tasks[t]["question"]):
            q = msg[0]["content"]
            r_rows, r_sc = retrieve(mk, *idx_A, q, *UNGATED)
            rp_rows, rp_sc = retrieve(mk, *idx_Ap, q, *UNGATED)
            s_rows, s_sc = retrieve(mk, *idx_Ap, q, *gate)
            o_rows, o_sc = retrieve(mk, *idx_G, q, *UNGATED)
            plan_mem[f"{t}:{ti}"] = {"R": [pool_row_id(r) for r in r_rows], "R+": [pool_row_id(r) for r in rp_rows],
                                     "S": [pool_row_id(r) for r in s_rows], "O": [pool_row_id(r) for r in o_rows],
                                     "scores": {"R": r_sc, "R+": rp_sc, "S": s_sc, "O": o_sc}}
    # placebo plan (SPEC v1 5.5)
    by_A = {pool_row_id(r): r for r in A}
    placebo = {}
    for key, mem in plan_mem.items():
        t, ti = key.rsplit(":", 1)
        r_block = render_block([by_A[i] for i in mem["R"]])
        n_r, len_r = len(mem["R"]), len(r_block)
        if n_r == 0:
            placebo[key] = {"items": [], "target_chars": 0, "chars": 0, "draws": 0, "within_15pct": True}
            continue
        rng = random.Random(int(hashlib.sha256(f"{t}:{ti}".encode()).hexdigest()[:16], 16))
        tried, best_pick, chosen, draws = set(), None, None, 0
        while draws < 50 and len(tried) < math.comb(len(F), n_r):
            pick = tuple(rng.sample(range(len(F)), n_r))
            if frozenset(pick) in tried:
                continue
            tried.add(frozenset(pick))
            draws += 1
            length = len(render_block([F[i] for i in pick]))
            if best_pick is None or abs(length - len_r) < abs(best_pick[1] - len_r):
                best_pick = (pick, length)
            if abs(length - len_r) <= 0.15 * len_r:
                chosen = (pick, length)
                break
        pick, length = chosen or best_pick
        placebo[key] = {"items": [pool_row_id(F[i]) for i in pick], "target_chars": len_r, "chars": length, "draws": draws,
                        "within_15pct": chosen is not None}
    write_json(DATA / "placebo-plan.json", placebo)
    # strata (SPEC v1 9.3)
    train_gt_norm = [[normalise_call(c, sig) for c in turn] for t in train for turn in bfcl.gt[t]]
    ap_norm = [row_calls_norm(r, sig) for r in A_plus]
    by_pool = {"A": by_A, "A_plus": {pool_row_id(r): r for r in A_plus}, "G": {pool_row_id(r): r for r in G}, "F": {pool_row_id(r): r for r in F}}
    random_names = {n for v in read_json(DATA / "e0-static.json")["random_methods"].values() for n in v}
    configs_train = {sha(bfcl.tasks[t]["initial_config"]) for t in train}
    strata, exposure = {}, {}
    for t in test:
        for ti, turn in enumerate(bfcl.gt[t]):
            key = f"{t}:{ti}"
            norm = [normalise_call(c, sig) for c in turn]
            sk = skeleton(norm)
            gt_layer = "A" if any(norm == x for x in train_gt_norm) else ("B" if any(sk == skeleton(x) for x in train_gt_norm) else "C")
            m_layer = "A" if any(norm == x for x in ap_norm) else ("B" if any(sk == skeleton(x) for x in ap_norm) else "C")
            strata[key] = {"gt_layer": gt_layer, "mem_layer": m_layer,
                           "c_rule": m_layer == "C" and any(n[0] in PRECONDITION_FUNCS for n in norm),
                           "random_dependent": any(n[0] in random_names for n in norm),
                           "same_world": sha(bfcl.tasks[t]["initial_config"]) in configs_train}
            exp = {}
            for arm, pool, ids in (("R", "A", plan_mem[key]["R"]), ("R+", "A_plus", plan_mem[key]["R+"]), ("S", "A_plus", plan_mem[key]["S"]),
                                   ("O", "G", plan_mem[key]["O"]), ("P", "F", placebo[key]["items"])):
                shown = [row_calls_norm(by_pool[pool][i], sig) for i in ids]
                if not ids:
                    exp[arm] = "empty"
                elif any(s == norm for s in shown):
                    exp[arm] = "exact"
                elif any(skeleton(s) == sk for s in shown):
                    exp[arm] = "skeleton"
                else:
                    exp[arm] = "none"
            exposure[key] = exp
    counts = {}
    for field in ("gt_layer", "mem_layer"):
        counts[field] = {k: sum(1 for s in strata.values() if s[field] == k) for k in "ABC"}
    counts["c_rule"] = sum(s["c_rule"] for s in strata.values())
    counts["random_dependent"] = sum(s["random_dependent"] for s in strata.values())
    counts["same_world_turns"] = sum(s["same_world"] for s in strata.values())
    write_json(DATA / "strata.json", {"counts": counts, "turns": strata})
    write_json(DATA / "exposure.json", {"retrieval": plan_mem, "exposure": exposure,
                                        "s_injection_rate": sum(bool(m["S"]) for m in plan_mem.values()) / len(plan_mem)})
    # projection (SPEC v1 8.4)
    led = ledger()
    calls_per_ep = sum(evals[t]["model_calls"] for t in train) / len(train)
    secs = [s["wall_seconds"] for t in train for turn in records[t]["turns"] for s in turn["steps"] if s.get("wall_seconds")]
    sec_per_call = sum(secs) / len(secs)
    proj_calls = calls_per_ep * (len(E2_ARMS) * len(test) + NPRIME_TASKS) * 1.15
    proj_secs = proj_calls * sec_per_call
    limits = cfg["limits"]
    projection = {"calls_used": led["calls"], "seconds_used": led["seconds"], "calls_per_episode": calls_per_ep, "seconds_per_call": sec_per_call,
                  "e2_projected_calls": proj_calls, "e2_projected_seconds": proj_secs,
                  "ok": led["calls"] + proj_calls <= limits["max_calls_total"] and led["seconds"] + proj_secs <= limits["max_seconds_total"]}
    gates = {"train_solved": train_solved, "mean_progress": mean_progress, "a_passed_turns": len(A_plus),
             "context_share_near_limit": context_share, "context_ok": context_share <= 0.10,
             "solved_range_ok": 2 <= train_solved <= 16, "progress_fallback": train_solved < 2 and mean_progress >= 0.25,
             "a_passed_ok": len(A_plus) >= 10, "projection_ok": projection["ok"]}
    gates["primary_metric"] = "progress" if gates["progress_fallback"] else "solved"
    gates["proceed"] = (gates["solved_range_ok"] or gates["progress_fallback"]) and gates["a_passed_ok"] and gates["context_ok"] and gates["projection_ok"]
    out = {"pools": pools, "gate": {"lex_tau": gate[0], "min_evidence": gate[1]}, "gates": gates, "projection": projection,
           "strata_counts": counts, "placebo_within_15pct": sum(p["within_15pct"] for p in placebo.values()), "placebo_turns": len(placebo)}
    write_json(DATA / "build.json", out)
    if not gates["proceed"]:
        raise SystemExit("STOP before E2: " + json.dumps(gates))
    return out


# ----------------------------------------------------------------------------- E2 / E3

def memory_provider(arm: str):
    """memory(task_id, turn_index, request) -> (rows, meta) read from the frozen plan files."""
    if arm in ("N", "N'"):
        return None
    exposure = read_json(DATA / "exposure.json")["retrieval"]
    placebo = read_json(DATA / "placebo-plan.json")
    pool_name = {"R": "A", "R+": "A_plus", "S": "A_plus", "O": "G", "P": "F"}[arm]
    path = DATA / "pools" / f"{pool_name}.jsonl"
    rows = {pool_row_id(r): r for r in read_jsonl(path)}
    pool_sha = file_sha(path)

    def memory(task_id, ti, request):
        key = f"{task_id}:{ti}"
        ids = placebo[key]["items"] if arm == "P" else exposure[key][arm]
        return [rows[i] for i in ids], {"pool": pool_name, "pool_sha256": pool_sha}
    return memory


def e2_plan(test, with_nprime=True):
    plan = []
    for i, t in enumerate(test):
        arms = list(E2_ARMS) + (["N'"] if with_nprime and i < NPRIME_TASKS else [])
        random.Random(SEED + i).shuffle(arms)
        plan.extend((t, a) for a in arms)
    return plan


def stage_e2(cfg, client_factory=None):
    build = read_json(DATA / "build.json")
    if not build["gates"]["proceed"]:
        raise SystemExit("STOP: build gates not passed")
    split = read_json(DATA / "split.json")
    plan = e2_plan(split["test"])
    providers = {a: memory_provider(a) for a in set(a for _, a in plan)}
    led = ledger()
    cap = cfg["limits"]["max_calls_total"] - led["calls"]
    _, evals, st = run_episodes(cfg, "e2", plan, lambda a: providers[a], cap, client_factory)
    return {"run_id": st.run_id, "episodes": len(evals)}


def stage_nprime_rest(cfg, client_factory=None):
    split = read_json(DATA / "split.json")
    plan = [(t, "N'") for t in split["test"][NPRIME_TASKS:]]
    _, evals, st = run_episodes(cfg, "e2n", plan, None, cfg["limits"]["max_calls_total"] - ledger()["calls"], client_factory)
    return {"run_id": st.run_id, "episodes": len(evals)}


def stage_e3(cfg, client_factory=None):
    split = read_json(DATA / "split.json")
    plan = [(t, "O") for t in split["test"]]
    provider = memory_provider("O")
    _, evals, st = run_episodes(cfg, "e3", plan, lambda a: provider, cfg["limits"]["max_calls_total"] - ledger()["calls"], client_factory)
    return {"run_id": st.run_id, "episodes": len(evals)}


# ----------------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["e0", "g1", "g2", "e1a", "e1b", "build", "e2", "e2n", "e3", "analyze", "ledger"])
    a = p.parse_args(argv)
    cfg = load_config()
    if a.stage == "ledger":
        print(json.dumps(ledger(), indent=2))
        return
    if a.stage == "analyze":
        import experience_pilot_v0_analysis as an
        an.main(cfg)
        return
    fn = {"e0": stage_e0, "g1": stage_g1, "g2": stage_g2, "e1a": stage_e1a, "e1b": stage_e1b, "build": stage_build,
          "e2": stage_e2, "e2n": stage_nprime_rest, "e3": stage_e3}[a.stage]
    out = fn(cfg)
    print(json.dumps(out, indent=2, default=str)[:4000])


if __name__ == "__main__":
    main()
